"""Usage and cost accounting service.

KEY SEPARATION (enforced here):
  - customer_charge_paise  → visible to customer (their billing)
  - provider_cost_paise    → NEVER in customer responses (platform cost)
  - gross_profit / margin  → ADMIN ONLY

Credit-to-paise conversion:
  For MVP: 1 credit = 1 billable second.
  Customer charge = credits × credit_rate_paise (configurable, default 1 paise/credit).
  Provider cost is tracked separately for actual cost (varies by provider).

Records allow full billing reconstruction:
  UsageEvent has call_id + idempotency_key → each call uniquely reconstructable.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.base import utcnow
from backend.repositories.usage_repo import ProviderUsageRepository, UsageEventRepository

log = logging.getLogger("service.usage")

# Default credit rate: 1 credit (1 second) = 1 paise customer charge
# Platform can change this per plan; MVP uses flat rate
DEFAULT_CREDIT_RATE_PAISE = 1   # 1 paise per credit (1 INR = 100 paise = 100 credits)

# Default provider cost estimates (paise per second of call duration)
# These are rough estimates for MVP; M26 adds real provider pricing
DEFAULT_PROVIDER_COSTS = {
    "telephony_paise_per_s": 2,     # ~₹0.02/s = ₹1.20/min Twilio/Exotel
    "stt_paise_per_s": 1,           # ~₹0.01/s Sarvam STT
    "llm_paise_per_s": 1,           # ~₹0.01/s (token-based; simplified to per-s)
    "tts_paise_per_s": 1,           # ~₹0.01/s ElevenLabs/Sarvam
}


class UsageService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.usage_repo = UsageEventRepository(db)
        self.provider_repo = ProviderUsageRepository(db)

    # ---- Record usage ----

    async def record_call_usage(
        self,
        organization_id: str,
        call_id: str,
        duration_s: int,
        credits_consumed: int,
        campaign_id: Optional[str] = None,
        telephony_provider: Optional[str] = None,
        stt_provider: Optional[str] = None,
        llm_provider: Optional[str] = None,
        tts_provider: Optional[str] = None,
        credit_rate_paise: int = DEFAULT_CREDIT_RATE_PAISE,
        provider_costs: Optional[dict] = None,
    ) -> dict:
        """
        Record usage for a completed call.
        - customer_charge = credits_consumed × credit_rate_paise
        - provider_cost = sum of provider-layer costs
        - Both tracked in UsageEvent; provider breakdown in ProviderUsage
        Idempotent via idempotency_key.
        """
        idem_key = f"call_usage:{call_id}"
        customer_charge = credits_consumed * credit_rate_paise

        # Estimate provider costs
        costs = provider_costs or {}
        tel_cost = costs.get("telephony", duration_s * DEFAULT_PROVIDER_COSTS["telephony_paise_per_s"])
        stt_cost = costs.get("stt", duration_s * DEFAULT_PROVIDER_COSTS["stt_paise_per_s"])
        llm_cost = costs.get("llm", duration_s * DEFAULT_PROVIDER_COSTS["llm_paise_per_s"])
        tts_cost = costs.get("tts", duration_s * DEFAULT_PROVIDER_COSTS["tts_paise_per_s"])
        total_provider_cost = tel_cost + stt_cost + llm_cost + tts_cost

        # Record usage event (customer charge + provider cost)
        event = await self.usage_repo.record(
            organization_id=organization_id,
            event_type="call_completed",
            customer_charge_paise=customer_charge,
            credits_consumed=credits_consumed,
            provider_cost_paise=total_provider_cost,
            provider=telephony_provider or "unknown",
            call_id=call_id,
            campaign_id=campaign_id,
            duration_s=duration_s,
            description=f"Call completed: {duration_s}s, {credits_consumed} credits",
            idempotency_key=idem_key,
        )

        if event is None:
            log.debug("call_usage idempotent skip call=%s", call_id)
            return {"idempotent": True}

        # Record provider breakdown (admin-only detail)
        await self.provider_repo.record(
            organization_id=organization_id,
            call_id=call_id,
            telephony_cost_paise=tel_cost,
            stt_cost_paise=stt_cost,
            llm_cost_paise=llm_cost,
            tts_cost_paise=tts_cost,
            telephony_provider=telephony_provider,
            stt_provider=stt_provider,
            llm_provider=llm_provider,
            tts_provider=tts_provider,
            duration_s=duration_s,
            stt_seconds=duration_s,
        )

        log.info("usage recorded call=%s org=%s charge=%d cost=%d",
                 call_id, organization_id, customer_charge, total_provider_cost)

        return {
            "usage_event_id": event.id,
            "credits_consumed": credits_consumed,
            "customer_charge_paise": customer_charge,
            "provider_cost_paise": total_provider_cost,
            "gross_profit_paise": customer_charge - total_provider_cost,
        }

    async def record_message_usage(
        self,
        organization_id: str,
        message_type: str,       # "sms" | "whatsapp"
        call_id: Optional[str] = None,
        customer_charge_paise: int = 0,
        provider_cost_paise: int = 0,
        provider: Optional[str] = None,
    ) -> Optional[str]:
        event = await self.usage_repo.record(
            organization_id=organization_id,
            event_type=f"{message_type}_sent",
            customer_charge_paise=customer_charge_paise,
            provider_cost_paise=provider_cost_paise,
            provider=provider,
            call_id=call_id,
            description=f"{message_type.upper()} sent",
        )
        return event.id if event else None

    # ---- Customer-facing queries (NO provider costs) ----

    async def get_customer_summary(
        self,
        organization_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> dict:
        """Usage summary safe to return to customer (no provider costs)."""
        agg = await self.usage_repo.aggregate_for_org(
            organization_id, from_date, to_date
        )
        call_stats = agg.get("call_completed", {})
        return {
            "organization_id": organization_id,
            "period": {
                "from": from_date.isoformat() if from_date else None,
                "to": to_date.isoformat() if to_date else None,
            },
            "calls": {
                "count": call_stats.get("count", 0),
                "total_credits": call_stats.get("total_credits", 0),
                "total_duration_s": call_stats.get("total_duration_s", 0),
            },
            "messages": {
                "sms_count": agg.get("sms_sent", {}).get("count", 0),
                "whatsapp_count": agg.get("whatsapp_sent", {}).get("count", 0),
            },
            # NOTE: customer_charge_paise intentionally omitted for MVP
            # (customers see credits, not paise)
        }

    async def list_usage_events(
        self,
        organization_id: str,
        event_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list:
        """Customer-safe usage event list (strips provider cost)."""
        events = await self.usage_repo.list_for_org(
            organization_id, event_type, from_date, to_date, limit, skip
        )
        return [_customer_event(e) for e in events]

    # ---- Admin-only queries (includes provider costs) ----

    async def get_admin_summary(
        self,
        organization_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> dict:
        """Full admin summary with provider costs and margin."""
        return await self.usage_repo.aggregate_admin(
            organization_id, from_date, to_date
        )

    async def get_provider_breakdown(
        self,
        call_id: str,
    ) -> Optional[dict]:
        """Admin: per-call provider cost breakdown."""
        pu = await self.provider_repo.get_for_call(call_id)
        if pu is None:
            return None
        return {
            "call_id": call_id,
            "telephony": {"provider": pu.telephony_provider,
                          "cost_paise": pu.telephony_cost_paise},
            "stt":       {"provider": pu.stt_provider,
                          "cost_paise": pu.stt_cost_paise},
            "llm":       {"provider": pu.llm_provider,
                          "cost_paise": pu.llm_cost_paise},
            "tts":       {"provider": pu.tts_provider,
                          "cost_paise": pu.tts_cost_paise},
            "total_provider_cost_paise": pu.total_provider_cost_paise,
            "duration_s": pu.duration_s,
        }

    async def get_provider_aggregates(self) -> list[dict]:
        """Admin: provider cost by provider combination."""
        return await self.provider_repo.aggregate_by_provider()


def _customer_event(event) -> dict:
    """Strip provider cost from event before sending to customer."""
    return {
        "id": event.id,
        "event_type": event.event_type,
        "description": event.description,
        "credits_consumed": event.credits_consumed,
        "call_id": event.call_id,
        "duration_s": event.duration_s,
        "created_at": event.created_at.isoformat(),
        # provider_cost_paise intentionally omitted
    }
