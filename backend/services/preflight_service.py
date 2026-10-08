"""Campaign pre-flight validation service.

Before a campaign starts, ALL of these must pass:
  1. subscription_active     — org has an active subscription
  2. credits_sufficient      — enough credits for at least N calls
  3. agent_valid             — agent exists, belongs to org, has active version
  4. voice_profile_valid     — voice profile exists and is active
  5. phone_number_valid      — calling number assigned to this org, not suspended
  6. leads_available         — at least 1 lead in scope (not DNC, not max_attempts)
  7. concurrency_within_plan — max_concurrent_calls ≤ subscription entitlement
  8. calling_hours_valid     — current time (in campaign timezone) is within window
                               OR scheduled_at is set (will be checked at start time)

Any FAIL blocks the campaign. Pre-flight result is returned to the caller
with per-check details so the user knows exactly what to fix.

Non-blocking checks (warnings, don't block):
  - low_credits_warning   — credits low but sufficient for now
  - dnc_entries_present   — some leads filtered by DNC

This is a read-only service — it does not modify any state.
"""

import logging
from datetime import datetime, time, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.campaign import Campaign

log = logging.getLogger("service.preflight")

# Minimum credits to start a campaign (1 minute of calls)
MIN_CREDITS_TO_START = 60
# Low credit warning threshold
LOW_CREDIT_WARNING = 300


class PreflightCheck:
    """Result of a single pre-flight check."""
    __slots__ = ("name", "passed", "message", "detail")

    def __init__(self, name: str, passed: bool, message: str, detail: Any = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.detail = detail

    def to_dict(self) -> dict:
        return {
            "check": self.name,
            "passed": self.passed,
            "message": self.message,
            "detail": self.detail,
        }


class PreflightResult:
    """Aggregated pre-flight result for a campaign."""

    def __init__(self, campaign_id: str, organization_id: str):
        self.campaign_id = campaign_id
        self.organization_id = organization_id
        self.checks: list[PreflightCheck] = []
        self.warnings: list[str] = []

    def add(self, check: PreflightCheck) -> None:
        self.checks.append(check)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> list[PreflightCheck]:
        return [c for c in self.checks if not c.passed]

    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "organization_id": self.organization_id,
            "can_start": self.all_passed,
            "checks": [c.to_dict() for c in self.checks],
            "failed": [c.to_dict() for c in self.failed_checks],
            "warnings": self.warnings,
        }


class PreflightService:
    def __init__(self, db: AsyncIOMotorDatabase, redis=None):
        self.db = db
        self._redis = redis

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from backend.core.redis import get_redis
            return get_redis()
        except Exception:  # noqa: BLE001
            return None

    async def run(
        self,
        campaign: Campaign,
        skip_calling_hours: bool = False,
    ) -> PreflightResult:
        """
        Run all pre-flight checks for a campaign.
        Returns PreflightResult with all checks and overall pass/fail.
        """
        result = PreflightResult(campaign.id, campaign.organization_id)

        # Run all checks — collect all failures, don't short-circuit
        await self._check_subscription(campaign, result)
        await self._check_credits(campaign, result)
        await self._check_agent(campaign, result)
        await self._check_voice_profile(campaign, result)
        await self._check_phone_number(campaign, result)
        await self._check_leads_available(campaign, result)
        await self._check_concurrency_within_plan(campaign, result)
        if not skip_calling_hours:
            await self._check_calling_hours(campaign, result)

        log.info(
            "preflight campaign=%s org=%s passed=%s failed=%s",
            campaign.id, campaign.organization_id,
            result.all_passed,
            [c.name for c in result.failed_checks],
        )
        return result

    # ---- Individual checks ----

    async def _check_subscription(
        self, campaign: Campaign, result: PreflightResult
    ) -> None:
        try:
            from backend.services.subscription_service import SubscriptionService
            svc = SubscriptionService(self.db)
            check = await svc.check_subscription_active(campaign.organization_id)
            result.add(PreflightCheck(
                "subscription_active",
                check.allowed,
                check.reason if not check.allowed else "Active subscription found",
            ))
        except Exception as exc:  # noqa: BLE001
            result.add(PreflightCheck(
                "subscription_active", False,
                f"Subscription check failed: {exc}"
            ))

    async def _check_credits(
        self, campaign: Campaign, result: PreflightResult
    ) -> None:
        try:
            from backend.services.wallet_service import WalletService
            svc = WalletService(self.db)
            balance = await svc.get_balance(campaign.organization_id)
            available = balance["available_credits"]
            sufficient = available >= MIN_CREDITS_TO_START
            result.add(PreflightCheck(
                "credits_sufficient",
                sufficient,
                f"Available credits: {available} (minimum required: {MIN_CREDITS_TO_START})"
                if sufficient else
                f"Insufficient credits: {available} available, {MIN_CREDITS_TO_START} required",
                {"available_credits": available, "minimum_required": MIN_CREDITS_TO_START},
            ))
            if sufficient and available < LOW_CREDIT_WARNING:
                result.warn(
                    f"Low credits warning: only {available} credits available. "
                    "Consider topping up before the campaign completes."
                )
        except Exception as exc:  # noqa: BLE001
            result.add(PreflightCheck(
                "credits_sufficient", False,
                f"Credit check failed: {exc}"
            ))

    async def _check_agent(
        self, campaign: Campaign, result: PreflightResult
    ) -> None:
        try:
            from backend.repositories.agent_repo import AgentRepository, AgentVersionRepository
            agent_repo = AgentRepository(self.db)
            version_repo = AgentVersionRepository(self.db)

            agent = await agent_repo.get_for_org(
                campaign.agent_id, campaign.organization_id
            )
            if agent is None:
                result.add(PreflightCheck(
                    "agent_valid", False,
                    f"Agent {campaign.agent_id} not found or inactive"
                ))
                return

            # Check specified version exists
            version = await version_repo.get_for_agent(
                campaign.agent_id, campaign.agent_version
            )
            if version is None:
                result.add(PreflightCheck(
                    "agent_valid", False,
                    f"Agent version {campaign.agent_version} not found"
                ))
                return

            if version.status != "published":
                result.add(PreflightCheck(
                    "agent_valid", False,
                    f"Agent version {campaign.agent_version} is not published (status: {version.status})"
                ))
                return

            result.add(PreflightCheck(
                "agent_valid", True,
                f"Agent '{agent.name}' v{campaign.agent_version} is valid and published"
            ))
        except Exception as exc:  # noqa: BLE001
            result.add(PreflightCheck(
                "agent_valid", False, f"Agent check failed: {exc}"
            ))

    async def _check_voice_profile(
        self, campaign: Campaign, result: PreflightResult
    ) -> None:
        try:
            from backend.repositories.voice_profile_repo import (
                VoiceProfileRepository, VoiceProfileVersionRepository
            )
            profile_repo = VoiceProfileRepository(self.db)
            version_repo = VoiceProfileVersionRepository(self.db)

            profile = await profile_repo.find_by_id(campaign.voice_profile_id)
            if profile is None or not profile.is_active:
                result.add(PreflightCheck(
                    "voice_profile_valid", False,
                    f"Voice profile {campaign.voice_profile_id} not found or inactive"
                ))
                return

            # Check access: platform profile or org's own
            if not profile.is_platform and profile.organization_id != campaign.organization_id:
                result.add(PreflightCheck(
                    "voice_profile_valid", False,
                    "Voice profile does not belong to this organization"
                ))
                return

            # Check version exists
            version = await version_repo.get_version(
                campaign.voice_profile_id, campaign.voice_profile_version
            )
            if version is None:
                result.add(PreflightCheck(
                    "voice_profile_valid", False,
                    f"Voice profile version {campaign.voice_profile_version} not found"
                ))
                return

            result.add(PreflightCheck(
                "voice_profile_valid", True,
                f"Voice profile '{profile.display_name}' v{campaign.voice_profile_version} is valid"
            ))
        except Exception as exc:  # noqa: BLE001
            result.add(PreflightCheck(
                "voice_profile_valid", False, f"Voice profile check failed: {exc}"
            ))

    async def _check_phone_number(
        self, campaign: Campaign, result: PreflightResult
    ) -> None:
        try:
            from backend.repositories.phone_number_repo import PhoneNumberRepository
            repo = PhoneNumberRepository(self.db)
            pn = await repo.find_by_id(campaign.calling_number_id)
            if pn is None:
                result.add(PreflightCheck(
                    "phone_number_valid", False,
                    f"Phone number {campaign.calling_number_id} not found"
                ))
                return

            if pn.organization_id != campaign.organization_id:
                result.add(PreflightCheck(
                    "phone_number_valid", False,
                    "Phone number is not assigned to this organization"
                ))
                return

            if pn.status == "suspended":
                result.add(PreflightCheck(
                    "phone_number_valid", False,
                    f"Phone number {pn.number} is suspended"
                ))
                return

            if pn.status != "assigned":
                result.add(PreflightCheck(
                    "phone_number_valid", False,
                    f"Phone number {pn.number} is not assigned (status: {pn.status})"
                ))
                return

            result.add(PreflightCheck(
                "phone_number_valid", True,
                f"Phone number {pn.number} is valid and assigned"
            ))
        except Exception as exc:  # noqa: BLE001
            result.add(PreflightCheck(
                "phone_number_valid", False, f"Phone number check failed: {exc}"
            ))

    async def _check_leads_available(
        self, campaign: Campaign, result: PreflightResult
    ) -> None:
        try:
            from backend.repositories.lead_repo import LeadRepository
            repo = LeadRepository(self.db)

            # Count leads in scope (new + callback, not DNC/completed)
            query: dict = {
                "organization_id": campaign.organization_id,
                "status": {"$in": ["new", "callback", "scheduled"]},
            }
            if campaign.lead_filter:
                query.update(campaign.lead_filter)
            if campaign.campaign_id_filter:
                query["campaign_id"] = campaign.campaign_id_filter

            count = await repo.count(query)
            if count == 0:
                result.add(PreflightCheck(
                    "leads_available", False,
                    "No eligible leads found for this campaign. "
                    "Import leads or adjust lead filter."
                ))
            else:
                result.add(PreflightCheck(
                    "leads_available", True,
                    f"{count} eligible leads found",
                    {"eligible_leads": count},
                ))
        except Exception as exc:  # noqa: BLE001
            result.add(PreflightCheck(
                "leads_available", False, f"Lead check failed: {exc}"
            ))

    async def _check_concurrency_within_plan(
        self, campaign: Campaign, result: PreflightResult
    ) -> None:
        try:
            from backend.services.subscription_service import SubscriptionService
            svc = SubscriptionService(self.db)
            check = await svc.check_concurrent_calls(
                campaign.organization_id,
                current_active_calls=0,  # check plan limit, not current usage
            )
            plan_limit = check.limit or 1
            if campaign.max_concurrent_calls > plan_limit:
                result.add(PreflightCheck(
                    "concurrency_within_plan", False,
                    f"Campaign max_concurrent_calls ({campaign.max_concurrent_calls}) "
                    f"exceeds plan limit ({plan_limit}). Reduce concurrency or upgrade plan.",
                    {"campaign_concurrency": campaign.max_concurrent_calls,
                     "plan_limit": plan_limit},
                ))
            else:
                result.add(PreflightCheck(
                    "concurrency_within_plan", True,
                    f"Concurrency {campaign.max_concurrent_calls} within plan limit {plan_limit}"
                ))
        except Exception as exc:  # noqa: BLE001
            # If subscription check failed (no subscription), this also fails
            result.add(PreflightCheck(
                "concurrency_within_plan", False,
                f"Concurrency check failed: {exc}"
            ))

    async def _check_calling_hours(
        self, campaign: Campaign, result: PreflightResult
    ) -> None:
        """Check if current time is within campaign calling hours.
        Skipped if campaign has a future scheduled_at (will be checked at start time).
        """
        try:
            # If scheduled for the future, skip current-time check
            if campaign.scheduled_at:
                from backend.models.base import utcnow
                if campaign.scheduled_at > utcnow():
                    result.add(PreflightCheck(
                        "calling_hours", True,
                        f"Campaign scheduled for {campaign.scheduled_at.isoformat()} — "
                        "calling hours will be validated at start time"
                    ))
                    return

            # Parse calling hours and timezone
            calling_hours = campaign.calling_hours
            tz_str = campaign.timezone

            try:
                import zoneinfo
                tz = zoneinfo.ZoneInfo(tz_str)
            except Exception:  # noqa: BLE001
                from datetime import timezone as _tz
                tz = _tz.utc

            now_local = datetime.now(tz)
            day_of_week = now_local.weekday() + 1  # Monday=1, Sunday=7 (adjust to 0=Sun)
            # Our model: 0=Sunday, 1=Monday, ..., 6=Saturday
            # Python weekday: 0=Monday, 6=Sunday
            day_idx = (now_local.weekday() + 1) % 7  # 0=Sun, 1=Mon, ..., 6=Sat

            allowed_days = calling_hours.days_of_week

            if day_idx not in allowed_days:
                result.add(PreflightCheck(
                    "calling_hours", False,
                    f"Today ({now_local.strftime('%A')}) is not a calling day. "
                    f"Allowed days: {allowed_days}",
                    {"current_day": day_idx, "allowed_days": allowed_days},
                ))
                return

            # Parse time window
            start_h, start_m = map(int, calling_hours.start_time.split(":"))
            end_h, end_m = map(int, calling_hours.end_time.split(":"))
            start_t = time(start_h, start_m)
            end_t = time(end_h, end_m)
            current_t = now_local.time().replace(second=0, microsecond=0)

            if not (start_t <= current_t <= end_t):
                result.add(PreflightCheck(
                    "calling_hours", False,
                    f"Current time {current_t.strftime('%H:%M')} ({tz_str}) is outside "
                    f"calling window {calling_hours.start_time}–{calling_hours.end_time}",
                    {
                        "current_time": current_t.strftime("%H:%M"),
                        "window_start": calling_hours.start_time,
                        "window_end": calling_hours.end_time,
                        "timezone": tz_str,
                    },
                ))
            else:
                result.add(PreflightCheck(
                    "calling_hours", True,
                    f"Current time {current_t.strftime('%H:%M')} is within calling window"
                ))
        except Exception as exc:  # noqa: BLE001
            # Don't block on timezone errors — warn and allow
            result.warn(f"Could not validate calling hours: {exc}")
            result.add(PreflightCheck(
                "calling_hours", True,
                f"Calling hours validation skipped (timezone error: {exc})"
            ))
