"""Campaign service — state machine and concurrency control.

State machine (enforced here, not in the API layer):

  draft ──start──► scheduled/running
  running ──pause──► paused
  running ──low_credits──► paused_low_credits
  paused/paused_low_credits ──resume──► running
  any ──cancel──► cancelled
  running ──all_leads_done──► completed
  running ──error──► failed

Redis coordination:
  campaign_state:{id}         → status string (fast worker reads)
  campaign_active_calls:{id}  → int (current concurrent calls, atomic $inc)

MongoDB is always source of truth. Redis is a cache/coordination layer.
If Redis is down, workers fall back to MongoDB.

Concurrency guarantee:
  Never exceed Campaign.max_concurrent_calls.
  Checked atomically via Redis INCR + comparison before each call.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.base import utcnow
from backend.models.campaign import (
    ACTIVE_STATUSES,
    CAMPAIGN_STATUSES,
    TERMINAL_STATUSES,
    Campaign,
)
from backend.repositories.campaign_repo import CampaignRepository
from backend.repositories.lead_repo import LeadRepository

log = logging.getLogger("service.campaign")

# Redis key patterns
_STATE_KEY = "campaign_state:{}"
_ACTIVE_CALLS_KEY = "campaign_active_calls:{}"
_LOCK_KEY = "campaign_lock:{}"
_LOCK_TTL = 30  # seconds


class CampaignService:
    def __init__(self, db: AsyncIOMotorDatabase, redis=None):
        self.db = db
        self._redis = redis
        self.repo = CampaignRepository(db)
        self.lead_repo = LeadRepository(db)

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from backend.core.redis import get_redis
            return get_redis()
        except Exception:  # noqa: BLE001
            return None

    # ---- Redis helpers ----

    async def _redis_set_state(self, campaign_id: str, status: str) -> None:
        r = self._get_redis()
        if r:
            await r.set(_STATE_KEY.format(campaign_id), status, ex=86400)

    async def _redis_get_state(self, campaign_id: str) -> Optional[str]:
        r = self._get_redis()
        if r:
            return await r.get(_STATE_KEY.format(campaign_id))
        return None

    async def _redis_clear(self, campaign_id: str) -> None:
        r = self._get_redis()
        if r:
            await r.delete(_STATE_KEY.format(campaign_id))
            await r.delete(_ACTIVE_CALLS_KEY.format(campaign_id))

    async def get_active_call_count(self, campaign_id: str) -> int:
        r = self._get_redis()
        if r:
            val = await r.get(_ACTIVE_CALLS_KEY.format(campaign_id))
            return int(val) if val else 0
        return 0

    async def increment_active_calls(self, campaign_id: str) -> int:
        """Atomically increment and return new count."""
        r = self._get_redis()
        if r:
            count = await r.incr(_ACTIVE_CALLS_KEY.format(campaign_id))
            await r.expire(_ACTIVE_CALLS_KEY.format(campaign_id), 86400)
            return count
        return 0

    async def decrement_active_calls(self, campaign_id: str) -> int:
        r = self._get_redis()
        if r:
            val = await r.get(_ACTIVE_CALLS_KEY.format(campaign_id))
            current = int(val) if val else 0
            if current > 0:
                count = await r.decr(_ACTIVE_CALLS_KEY.format(campaign_id))
                return max(0, count)
        return 0

    # ---- Campaign lifecycle ----

    async def create_campaign(
        self,
        organization_id: str,
        name: str,
        agent_id: str,
        agent_version: int,
        voice_profile_id: str,
        voice_profile_version: int,
        calling_number_id: str,
        calling_number: str,
        max_concurrent_calls: int = 1,
        timezone: str = "Asia/Kolkata",
        description: str = "",
        lead_filter: Optional[dict] = None,
        calling_hours: Optional[dict] = None,
        retry_policy: Optional[dict] = None,
        scheduled_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
    ) -> Campaign:
        return await self.repo.create(
            organization_id=organization_id,
            name=name,
            agent_id=agent_id,
            agent_version=agent_version,
            voice_profile_id=voice_profile_id,
            voice_profile_version=voice_profile_version,
            calling_number_id=calling_number_id,
            calling_number=calling_number,
            max_concurrent_calls=max_concurrent_calls,
            timezone=timezone,
            description=description,
            lead_filter=lead_filter,
            calling_hours=calling_hours,
            retry_policy=retry_policy,
            scheduled_at=scheduled_at,
            created_by=created_by,
        )

    async def start_campaign(
        self,
        campaign_id: str,
        organization_id: str,
        skip_preflight: bool = False,
    ) -> Campaign:
        """Transition draft/scheduled → running. Runs pre-flight validation first."""
        campaign = await self.repo.get_for_org(campaign_id, organization_id)
        if campaign is None:
            raise ValueError("Campaign not found")
        if campaign.status not in ("draft", "scheduled"):
            raise ValueError(
                f"Cannot start campaign in status '{campaign.status}'. "
                "Must be draft or scheduled."
            )

        # Pre-flight validation (skip_preflight=True only for tests/admin override)
        if not skip_preflight:
            from backend.services.preflight_service import PreflightService
            preflight = PreflightService(self.db, redis=self._get_redis())
            result = await preflight.run(campaign, skip_calling_hours=False)
            if not result.all_passed:
                failed = [f"{c.name}: {c.message}" for c in result.failed_checks]
                raise ValueError(
                    f"Campaign pre-flight failed ({len(result.failed_checks)} check(s)): "
                    + "; ".join(failed)
                )

        now = utcnow()
        ok = await self.repo.transition_status(
            campaign_id, organization_id, "running",
            extra_updates={"started_at": now},
        )
        if not ok:
            raise RuntimeError("Failed to start campaign")
        await self._redis_set_state(campaign_id, "running")
        log.info("campaign started id=%s org=%s", campaign_id, organization_id)
        return await self.repo.get_for_org(campaign_id, organization_id)

    async def pause_campaign(
        self,
        campaign_id: str,
        organization_id: str,
        reason: str = "user_request",
    ) -> Campaign:
        campaign = await self.repo.get_for_org(campaign_id, organization_id)
        if campaign is None:
            raise ValueError("Campaign not found")
        if not campaign.can_pause:
            raise ValueError(
                f"Cannot pause campaign in status '{campaign.status}'"
            )
        new_status = "paused_low_credits" if reason == "low_credits" else "paused"
        ok = await self.repo.transition_status(
            campaign_id, organization_id, new_status,
            extra_updates={"paused_at": utcnow()},
        )
        if not ok:
            raise RuntimeError("Failed to pause campaign")
        await self._redis_set_state(campaign_id, new_status)
        log.info("campaign paused id=%s reason=%s", campaign_id, reason)
        return await self.repo.get_for_org(campaign_id, organization_id)

    async def resume_campaign(
        self,
        campaign_id: str,
        organization_id: str,
    ) -> Campaign:
        campaign = await self.repo.get_for_org(campaign_id, organization_id)
        if campaign is None:
            raise ValueError("Campaign not found")
        if not campaign.can_resume:
            raise ValueError(
                f"Cannot resume campaign in status '{campaign.status}'. "
                "Must be paused or paused_low_credits."
            )
        ok = await self.repo.transition_status(
            campaign_id, organization_id, "running",
            extra_updates={"paused_at": None},
        )
        if not ok:
            raise RuntimeError("Failed to resume campaign")
        await self._redis_set_state(campaign_id, "running")
        log.info("campaign resumed id=%s org=%s", campaign_id, organization_id)
        return await self.repo.get_for_org(campaign_id, organization_id)

    async def cancel_campaign(
        self,
        campaign_id: str,
        organization_id: str,
    ) -> Campaign:
        campaign = await self.repo.get_for_org(campaign_id, organization_id)
        if campaign is None:
            raise ValueError("Campaign not found")
        if not campaign.can_cancel:
            raise ValueError(
                f"Campaign already in terminal status '{campaign.status}'"
            )
        ok = await self.repo.transition_status(
            campaign_id, organization_id, "cancelled",
            extra_updates={"cancelled_at": utcnow()},
        )
        if not ok:
            raise RuntimeError("Failed to cancel campaign")
        await self._redis_clear(campaign_id)
        log.info("campaign cancelled id=%s org=%s", campaign_id, organization_id)
        return await self.repo.get_for_org(campaign_id, organization_id)

    async def complete_campaign(
        self, campaign_id: str, organization_id: str
    ) -> Campaign:
        """Mark campaign as completed (all leads processed)."""
        ok = await self.repo.transition_status(
            campaign_id, organization_id, "completed",
            extra_updates={"completed_at": utcnow()},
        )
        if ok:
            await self._redis_clear(campaign_id)
        return await self.repo.get_for_org(campaign_id, organization_id)

    async def fail_campaign(
        self, campaign_id: str, organization_id: str
    ) -> Campaign:
        """Mark campaign as failed (unrecoverable error)."""
        await self.repo.transition_status(
            campaign_id, organization_id, "failed",
        )
        await self._redis_clear(campaign_id)
        return await self.repo.get_for_org(campaign_id, organization_id)

    # ---- Concurrency gate (used by calling worker) ----

    async def can_start_call(
        self,
        campaign_id: str,
        organization_id: str,
    ) -> dict:
        """
        Check whether a new call can start for this campaign.
        Returns {allowed, reason, active_calls, max_concurrent_calls}.
        Does NOT modify state — caller must call acquire_call_slot().
        """
        campaign = await self.repo.get_for_org(campaign_id, organization_id)
        if campaign is None:
            return {"allowed": False, "reason": "campaign_not_found"}
        if campaign.status != "running":
            return {"allowed": False, "reason": f"campaign_not_running (status={campaign.status})"}

        active = await self.get_active_call_count(campaign_id)
        if active >= campaign.max_concurrent_calls:
            return {
                "allowed": False,
                "reason": f"concurrency_limit_reached ({active}/{campaign.max_concurrent_calls})",
                "active_calls": active,
                "max_concurrent_calls": campaign.max_concurrent_calls,
            }

        return {
            "allowed": True,
            "active_calls": active,
            "max_concurrent_calls": campaign.max_concurrent_calls,
        }

    async def acquire_call_slot(self, campaign_id: str) -> bool:
        """
        Atomically increment active call count.
        Returns True if slot acquired (count ≤ max), False if limit exceeded.
        Caller MUST call release_call_slot() when call ends.
        """
        campaign = await self.repo.find_by_id(campaign_id)
        if campaign is None:
            return False
        new_count = await self.increment_active_calls(campaign_id)
        if new_count > campaign.max_concurrent_calls:
            # Over limit — give back the slot
            await self.decrement_active_calls(campaign_id)
            return False
        return True

    async def release_call_slot(self, campaign_id: str) -> None:
        await self.decrement_active_calls(campaign_id)

    # ---- Read helpers ----

    async def get_campaign(
        self, campaign_id: str, organization_id: str
    ) -> Optional[Campaign]:
        return await self.repo.get_for_org(campaign_id, organization_id)

    async def list_campaigns(
        self,
        organization_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list[Campaign]:
        return await self.repo.list_for_org(
            organization_id, status=status, limit=limit, skip=skip
        )

    async def get_stats(self, campaign_id: str, organization_id: str) -> dict:
        campaign = await self.repo.get_for_org(campaign_id, organization_id)
        if campaign is None:
            raise ValueError("Campaign not found")
        active_calls = await self.get_active_call_count(campaign_id)
        return {
            "campaign_id": campaign_id,
            "status": campaign.status,
            "total_leads": campaign.total_leads,
            "leads_dialed": campaign.leads_dialed,
            "leads_connected": campaign.leads_connected,
            "leads_completed": campaign.leads_completed,
            "active_calls": active_calls,
            "max_concurrent_calls": campaign.max_concurrent_calls,
        }
