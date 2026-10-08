"""Call service — initiate, track, and finalize AI calls.

This service bridges the SaaS infrastructure (org, campaign, credits, leads)
with the existing transport-agnostic CallSession (the real-time AI call engine).

Flow:
  1. Validate: campaign running, credits available, lead valid, concurrency gate
  2. Reserve credits
  3. Create Call record in MongoDB
  4. Start CallSession (existing real-time pipeline)
  5. On completion: finalize Call record, settle credits, update lead/campaign

The CallSession itself is preserved from the original repo — we only adapt
the scaffolding around it, not the audio/VAD/STT/LLM/TTS pipeline.
"""

import logging
from statistics import mean
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.base import utcnow
from backend.models.call import CALL_OUTCOMES
from backend.repositories.call_repo import CallRepository
from backend.repositories.lead_repo import LeadRepository
from backend.repositories.campaign_repo import CampaignRepository

log = logging.getLogger("service.call")

# Default credit reservation per call: 5 minutes = 300 seconds
DEFAULT_RESERVE_CREDITS = 300


class CallService:
    def __init__(self, db: AsyncIOMotorDatabase, redis=None):
        self.db = db
        self._redis = redis
        self.call_repo = CallRepository(db)
        self.lead_repo = LeadRepository(db)
        self.campaign_repo = CampaignRepository(db)

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from backend.core.redis import get_redis
            return get_redis()
        except Exception:  # noqa: BLE001
            return None

    async def initiate_call(
        self,
        organization_id: str,
        to_number: str,
        from_number: str,
        campaign_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_version: Optional[int] = None,
        provider: str = "mock",
        reserve_credits: int = DEFAULT_RESERVE_CREDITS,
    ) -> dict:
        """
        Initiate an outbound call.
        1. Reserve credits
        2. Create call record
        3. Increment campaign active call counter
        Returns the call record.
        """
        # Reserve credits
        try:
            from backend.services.credit_service import CreditService
            credit_svc = CreditService(self.db, redis=self._get_redis())
            call_id_placeholder = f"init_{organization_id[:8]}_{to_number[-4:]}"
            credit_result = await credit_svc.reserve(
                organization_id=organization_id,
                call_id=call_id_placeholder,
                max_credits=reserve_credits,
            )
        except ValueError as exc:
            raise ValueError(f"Cannot start call: {exc}") from exc

        # Create call record
        call = await self.call_repo.create(
            organization_id=organization_id,
            to_number=to_number,
            from_number=from_number,
            campaign_id=campaign_id,
            lead_id=lead_id,
            agent_id=agent_id,
            agent_version=agent_version,
            provider=provider,
        )

        # Update call with actual call_id for credit reservation
        await self.call_repo.update_by_id(call.id, {
            "credits_reserved": reserve_credits,
            "credit_reservation_id": call_id_placeholder,
        })

        # Re-reserve with actual call ID
        try:
            r2 = self._get_redis()
            if r2:
                old_key = f"credit_reserve:{organization_id}:{call_id_placeholder}"
                new_key = f"credit_reserve:{organization_id}:{call.id}"
                val = await r2.get(old_key)
                if val:
                    await r2.set(new_key, val, ex=4 * 3600)
                    await r2.delete(old_key)
        except Exception:  # noqa: BLE001
            pass

        # Increment campaign concurrency counter
        if campaign_id:
            from backend.services.campaign_service import CampaignService
            camp_svc = CampaignService(self.db, redis=self._get_redis())
            await camp_svc.increment_active_calls(campaign_id)

        # Update lead status
        if lead_id:
            await self.lead_repo.update_status(lead_id, organization_id, "calling")
            await self.lead_repo.increment_attempts(lead_id, organization_id)

        log.info("call initiated id=%s org=%s to=%s campaign=%s",
                 call.id, organization_id, to_number, campaign_id)
        return {"call_id": call.id, "status": "initiating"}

    async def finalize_call(
        self,
        call_id: str,
        organization_id: str,
        status: str = "completed",
        outcome: Optional[str] = None,
        actual_credits: int = 0,
        avg_latency_ms: Optional[int] = None,
        turn_count: int = 0,
        score: int = 0,
        qualification: Optional[dict] = None,
        summary: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> dict:
        """
        Finalize a call after it ends.
        1. Settle credits
        2. Finalize call record
        3. Update lead status
        4. Decrement campaign concurrency counter
        5. Update campaign counters
        """
        call = await self.call_repo.get_for_org(call_id, organization_id)
        if call is None:
            raise ValueError(f"Call {call_id} not found")

        # Calculate duration
        duration_s = None
        if call.started_at:
            now = utcnow()
            started = call.started_at
            # Handle mongomock returning naive datetimes
            if started.tzinfo is None:
                from datetime import timezone as _tz
                started = started.replace(tzinfo=_tz.utc)
            ref = call.connected_at or started
            if ref.tzinfo is None:
                from datetime import timezone as _tz
                ref = ref.replace(tzinfo=_tz.utc)
            duration_s = max(0, int((now - ref).total_seconds()))

        # Settle credits
        actual_credits = actual_credits or duration_s or 0
        try:
            from backend.services.credit_service import CreditService
            credit_svc = CreditService(self.db, redis=self._get_redis())
            await credit_svc.settle(
                organization_id=organization_id,
                call_id=call_id,
                actual_credits=actual_credits,
                idempotency_key=f"settle:{call_id}",
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("credit settlement failed for call=%s: %s", call_id, exc)

        # Finalize call record
        await self.call_repo.finalize(
            call_id=call_id,
            organization_id=organization_id,
            status=status,
            outcome=outcome,
            duration_s=duration_s,
            avg_latency_ms=avg_latency_ms,
            turn_count=turn_count,
            score=score,
            qualification=qualification,
            credits_consumed=actual_credits,
            summary=summary,
            error_message=error_message,
        )

        # Update lead status based on outcome
        if call.lead_id and outcome:
            lead_status_map = {
                "qualified": "qualified",
                "not_interested": "not_interested",
                "callback": "callback",
                "appointment_set": "qualified",
                "no_answer": "failed",
                "failed": "failed",
                "transferred": "contacted",
            }
            new_lead_status = lead_status_map.get(outcome, "contacted")
            await self.lead_repo.update_status(
                call.lead_id, organization_id, new_lead_status,
                qualification=qualification, score=score,
            )

        # Decrement campaign concurrency
        if call.campaign_id:
            from backend.services.campaign_service import CampaignService
            camp_svc = CampaignService(self.db, redis=self._get_redis())
            await camp_svc.release_call_slot(call.campaign_id)
            await self.campaign_repo.increment_counter(call.campaign_id, "leads_dialed")
            if status == "completed":
                await self.campaign_repo.increment_counter(call.campaign_id, "leads_completed")
            if outcome in ("qualified", "appointment_set"):
                await self.campaign_repo.increment_counter(call.campaign_id, "leads_connected")

        log.info("call finalized id=%s status=%s outcome=%s credits=%d",
                 call_id, status, outcome, actual_credits)

        return {
            "call_id": call_id,
            "status": status,
            "outcome": outcome,
            "duration_s": duration_s,
            "credits_consumed": actual_credits,
        }

    async def get_call(
        self, call_id: str, organization_id: str
    ):
        return await self.call_repo.get_for_org(call_id, organization_id)

    async def list_calls(
        self,
        organization_id: str,
        campaign_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list:
        return await self.call_repo.list_for_org(
            organization_id, campaign_id=campaign_id,
            lead_id=lead_id, status=status,
            limit=limit, skip=skip,
        )
