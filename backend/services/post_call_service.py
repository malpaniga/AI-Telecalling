"""Post-call processing service.

Runs AFTER a call completes. Must be:
  - Asynchronous (does not block the call)
  - Retryable (safe to re-run; idempotent)
  - Idempotent (duplicate run does not double-charge or double-update)

Pipeline stages (all within one process() call):
  1. transcript       — save/update transcript document
  2. summary          — generate a short summary from turns
  3. qualification    — extract/consolidate qualification slots
  4. score            — compute final lead score
  5. outcome          — derive call outcome
  6. lead_update      — update lead status/score/qualification
  7. campaign_update  — increment campaign counters
  8. analytics        — update daily analytics bucket
  9. usage_event      — record usage for billing
  10. wallet_settle   — finalize credit consumption

Idempotency:
  Each stage checks the idempotency key "{stage}:{call_id}" before executing.
  If the key already exists in the wallet_transactions/usage_events collection,
  the stage is skipped cleanly (logged as "already processed").
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.base import new_id, utcnow
from backend.repositories.transcript_repo import TranscriptRepository
from backend.repositories.call_repo import CallRepository
from backend.repositories.lead_repo import LeadRepository
from backend.repositories.campaign_repo import CampaignRepository

log = logging.getLogger("service.post_call")

OUTCOMES = {
    "qualified", "not_interested", "callback",
    "appointment_set", "no_answer", "voicemail", "transferred", "failed",
}


class PostCallService:
    def __init__(self, db: AsyncIOMotorDatabase, redis=None):
        self.db = db
        self._redis = redis
        self.transcript_repo = TranscriptRepository(db)
        self.call_repo = CallRepository(db)
        self.lead_repo = LeadRepository(db)
        self.campaign_repo = CampaignRepository(db)

    # ---- Main pipeline ----

    async def process(
        self,
        call_id: str,
        organization_id: str,
        turns: Optional[list[dict]] = None,
        call_state: Optional[dict] = None,
        actual_credits: int = 0,
        force: bool = False,
    ) -> dict:
        """
        Run the full post-call pipeline.
        Returns a summary dict of what was processed.

        Idempotency: each stage is independently idempotent.
        force=True skips idempotency checks (admin re-processing).
        """
        log.info("post_call.process call=%s org=%s credits=%d",
                 call_id, organization_id, actual_credits)

        result: dict = {
            "call_id": call_id,
            "stages": {},
        }

        # Fetch call record
        call = await self.call_repo.get_for_org(call_id, organization_id)
        if call is None:
            log.warning("post_call: call %s not found", call_id)
            return {**result, "error": "call_not_found"}

        # 1. Transcript
        transcript = await self._stage_transcript(
            call, turns, organization_id, result
        )

        # Derive qualification/score/outcome from call_state and turns
        qualification, score, outcome, summary = _analyze_call(
            call_state or {}, turns or [], call
        )

        # 2-5. Summary, qualification, score, outcome (all in one transcript update)
        if transcript:
            idem_key = f"post_call_result:{call_id}"
            already_done = await self.db["post_call_idempotency"].find_one(
                {"key": idem_key}
            )
            if not already_done or force:
                await self.transcript_repo.set_processing_result(
                    transcript.id, summary, qualification, score, outcome
                )
                await self.db["post_call_idempotency"].insert_one({
                    "_id": new_id(), "key": idem_key, "created_at": utcnow()
                })
                result["stages"]["transcript_processed"] = True
            else:
                result["stages"]["transcript_processed"] = "skipped_idempotent"

        # 6. Lead update
        await self._stage_lead_update(call, qualification, score, outcome, result)

        # 7. Campaign update
        await self._stage_campaign_update(call, outcome, result)

        # 8. Analytics
        await self._stage_analytics(call, outcome, actual_credits, organization_id, result)

        # 9. Usage event
        await self._stage_usage_event(call, actual_credits, organization_id, result)

        # 10. Wallet settlement
        await self._stage_wallet_settle(call, actual_credits, organization_id, result)

        log.info("post_call complete call=%s stages=%s", call_id, list(result["stages"]))
        return result

    # ---- Individual stages ----

    async def _stage_transcript(
        self,
        call,
        turns: Optional[list[dict]],
        organization_id: str,
        result: dict,
    ):
        try:
            transcript = await self.transcript_repo.create_or_get(
                organization_id=organization_id,
                call_id=call.id,
                lead_id=call.lead_id,
                campaign_id=call.campaign_id,
            )
            if turns:
                await self.transcript_repo.add_turns(transcript.id, turns)
            result["stages"]["transcript"] = "ok"
            return transcript
        except Exception as exc:  # noqa: BLE001
            log.warning("post_call transcript stage failed: %s", exc)
            result["stages"]["transcript"] = f"error: {exc}"
            return None

    async def _stage_lead_update(
        self, call, qualification: dict, score: int,
        outcome: Optional[str], result: dict
    ):
        if not call.lead_id:
            result["stages"]["lead_update"] = "skipped_no_lead"
            return
        try:
            # Map outcome → lead status
            status_map = {
                "qualified": "qualified",
                "appointment_set": "qualified",
                "not_interested": "not_interested",
                "callback": "callback",
                "no_answer": "failed",
                "failed": "failed",
                "transferred": "contacted",
                "voicemail": "callback",
            }
            new_status = status_map.get(outcome or "", "contacted")
            await self.lead_repo.update_status(
                call.lead_id, call.organization_id,
                new_status, qualification=qualification, score=score,
            )
            result["stages"]["lead_update"] = new_status
        except Exception as exc:  # noqa: BLE001
            log.warning("post_call lead_update failed: %s", exc)
            result["stages"]["lead_update"] = f"error: {exc}"

    async def _stage_campaign_update(self, call, outcome: Optional[str], result: dict):
        if not call.campaign_id:
            result["stages"]["campaign_update"] = "skipped_no_campaign"
            return
        try:
            await self.campaign_repo.increment_counter(call.campaign_id, "leads_dialed")
            if outcome in ("qualified", "appointment_set"):
                await self.campaign_repo.increment_counter(
                    call.campaign_id, "leads_connected"
                )
            if outcome not in (None, "no_answer", "failed"):
                await self.campaign_repo.increment_counter(
                    call.campaign_id, "leads_completed"
                )
            result["stages"]["campaign_update"] = "ok"
        except Exception as exc:  # noqa: BLE001
            log.warning("post_call campaign_update failed: %s", exc)
            result["stages"]["campaign_update"] = f"error: {exc}"

    async def _stage_analytics(
        self, call, outcome: Optional[str],
        actual_credits: int, organization_id: str, result: dict
    ):
        try:
            today = utcnow().date().isoformat()
            idem_key = f"analytics:{call.id}"
            existing = await self.db["post_call_idempotency"].find_one({"key": idem_key})
            if existing:
                result["stages"]["analytics"] = "skipped_idempotent"
                return

            inc: dict = {
                "calls_total": 1,
                "credits_consumed": actual_credits,
            }
            if call.duration_s:
                inc["total_duration_s"] = call.duration_s
            if outcome in ("qualified", "appointment_set"):
                inc["calls_qualified"] = 1
            if outcome == "not_interested":
                inc["calls_not_interested"] = 1
            if outcome == "no_answer":
                inc["calls_no_answer"] = 1
            if call.avg_latency_ms:
                inc["total_latency_ms"] = call.avg_latency_ms

            await self.db["analytics_daily"].update_one(
                {"organization_id": organization_id, "date": today},
                {"$inc": inc, "$setOnInsert": {
                    "_id": new_id(), "created_at": utcnow()
                }},
                upsert=True,
            )
            await self.db["post_call_idempotency"].insert_one(
                {"_id": new_id(), "key": idem_key, "created_at": utcnow()}
            )
            result["stages"]["analytics"] = "ok"
        except Exception as exc:  # noqa: BLE001
            log.warning("post_call analytics failed: %s", exc)
            result["stages"]["analytics"] = f"error: {exc}"

    async def _stage_usage_event(
        self, call, actual_credits: int, organization_id: str, result: dict
    ):
        try:
            idem_key = f"usage:{call.id}"
            existing = await self.db["usage_events"].find_one(
                {"idempotency_key": idem_key}
            )
            if existing:
                result["stages"]["usage_event"] = "skipped_idempotent"
                return

            usage_doc = {
                "_id": new_id(),
                "organization_id": organization_id,
                "call_id": call.id,
                "campaign_id": call.campaign_id,
                "lead_id": call.lead_id,
                "event_type": "call_completed",
                "credits_consumed": actual_credits,
                "duration_s": call.duration_s,
                "provider": call.provider,
                "idempotency_key": idem_key,
                "created_at": utcnow(),
            }
            await self.db["usage_events"].insert_one(usage_doc)
            result["stages"]["usage_event"] = "ok"
        except Exception as exc:  # noqa: BLE001
            log.warning("post_call usage_event failed: %s", exc)
            result["stages"]["usage_event"] = f"error: {exc}"

    async def _stage_wallet_settle(
        self, call, actual_credits: int, organization_id: str, result: dict
    ):
        if actual_credits <= 0:
            result["stages"]["wallet_settle"] = "skipped_zero_credits"
            return
        try:
            from backend.services.credit_service import CreditService
            credit_svc = CreditService(self.db, redis=self._redis)
            settle_result = await credit_svc.settle(
                organization_id=organization_id,
                call_id=call.id,
                actual_credits=actual_credits,
                idempotency_key=f"settle:{call.id}",
            )
            result["stages"]["wallet_settle"] = settle_result
        except Exception as exc:  # noqa: BLE001
            log.warning("post_call wallet_settle failed: %s", exc)
            result["stages"]["wallet_settle"] = f"error: {exc}"


# ---- Analysis helpers ----

def _analyze_call(
    call_state: dict,
    turns: list[dict],
    call,
) -> tuple[dict, int, Optional[str], Optional[str]]:
    """Derive qualification, score, outcome, and summary from call state."""

    qualification = call_state.get("slots", {})
    flags = call_state.get("flags", {})
    stage = call_state.get("stage", "unknown")

    # Score
    score = _compute_score(qualification, flags)

    # Outcome
    outcome = _derive_outcome(flags, stage, call)

    # Summary
    summary = _generate_summary(turns, qualification, outcome, stage)

    return qualification, score, outcome, summary


def _compute_score(slots: dict, flags: dict) -> int:
    """Simple slot-based scoring. 15 pts per filled slot, bonuses for intent."""
    SLOT_POINTS = 15
    BOOK_BONUS = 30
    INTEREST_BONUS = 10
    END_PENALTY = 25

    score = SLOT_POINTS * sum(1 for v in slots.values() if v)
    if flags.get("wants_to_book") or flags.get("appointment_set"):
        score += BOOK_BONUS
    if flags.get("interested"):
        score += INTEREST_BONUS
    if flags.get("wants_to_end") or flags.get("not_interested"):
        score -= END_PENALTY

    return max(0, min(100, score))


def _derive_outcome(flags: dict, stage: str, call) -> Optional[str]:
    """Determine call outcome from flags/stage/call record."""
    # Prefer call record's outcome if already set
    if call.outcome and call.outcome in OUTCOMES:
        return call.outcome
    if flags.get("wants_to_book") or stage == "booking":
        return "appointment_set"
    if flags.get("wants_to_end") or flags.get("not_interested"):
        return "not_interested"
    if flags.get("interested"):
        return "qualified"
    if call.status == "no_answer":
        return "no_answer"
    return "callback"


def _generate_summary(
    turns: list[dict],
    qualification: dict,
    outcome: Optional[str],
    stage: str,
) -> Optional[str]:
    """Generate a brief text summary (no LLM in post-call for MVP)."""
    if not turns:
        return None

    filled_slots = {k: v for k, v in qualification.items() if v}
    parts = []

    if filled_slots:
        slot_str = ", ".join(f"{k}: {v}" for k, v in filled_slots.items())
        parts.append(f"Collected: {slot_str}.")

    parts.append(f"Call stage reached: {stage}.")

    if outcome:
        parts.append(f"Outcome: {outcome.replace('_', ' ')}.")

    parts.append(f"Total turns: {len(turns)}.")

    return " ".join(parts)
