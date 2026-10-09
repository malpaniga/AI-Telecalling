"""Usage event and provider usage repositories."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from backend.models.base import new_id, utcnow
from backend.models.usage import ProviderUsage, UsageEvent
from backend.repositories.base import BaseRepository

log = logging.getLogger("repo.usage")


class UsageEventRepository(BaseRepository):
    collection_name = "usage_events"
    model_class = UsageEvent

    async def record(
        self,
        organization_id: str,
        event_type: str,
        customer_charge_paise: int = 0,
        credits_consumed: int = 0,
        provider_cost_paise: int = 0,
        provider: Optional[str] = None,
        call_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        duration_s: Optional[int] = None,
        description: str = "",
        idempotency_key: Optional[str] = None,
    ) -> Optional[UsageEvent]:
        """Record a usage event. Returns None if idempotency_key already exists."""
        if idempotency_key:
            existing = await self.find_one({"idempotency_key": idempotency_key})
            if existing:
                log.debug("usage_event idempotent skip key=%s", idempotency_key)
                return None

        event = UsageEvent(
            _id=new_id(),
            organization_id=organization_id,
            event_type=event_type,
            customer_charge_paise=customer_charge_paise,
            credits_consumed=credits_consumed,
            provider_cost_paise=provider_cost_paise,
            provider=provider,
            call_id=call_id,
            campaign_id=campaign_id,
            duration_s=duration_s,
            description=description,
            idempotency_key=idempotency_key,
        )
        await self.insert(event)
        return event

    async def list_for_org(
        self,
        organization_id: str,
        event_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[UsageEvent]:
        query: dict = {"organization_id": organization_id}
        if event_type:
            query["event_type"] = event_type
        if from_date or to_date:
            date_f: dict = {}
            if from_date:
                date_f["$gte"] = from_date
            if to_date:
                date_f["$lte"] = to_date
            query["created_at"] = date_f
        return await self.find_many(
            query, sort=[("created_at", DESCENDING)], limit=limit, skip=skip
        )

    async def aggregate_for_org(
        self,
        organization_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> dict:
        """Aggregate customer-facing usage stats (no provider costs)."""
        match: dict = {"organization_id": organization_id}
        if from_date or to_date:
            date_f: dict = {}
            if from_date:
                date_f["$gte"] = from_date
            if to_date:
                date_f["$lte"] = to_date
            match["created_at"] = date_f

        pipeline = [
            {"$match": match},
            {"$group": {
                "_id": "$event_type",
                "count": {"$sum": 1},
                "total_credits": {"$sum": "$credits_consumed"},
                "total_charge_paise": {"$sum": "$customer_charge_paise"},
                "total_duration_s": {"$sum": "$duration_s"},
            }},
        ]
        rows = await self.col.aggregate(pipeline).to_list(None)
        result: dict = {}
        for row in rows:
            result[row["_id"]] = {
                "count": row["count"],
                "total_credits": row["total_credits"],
                "total_charge_paise": row["total_charge_paise"],
                "total_duration_s": row["total_duration_s"] or 0,
            }
        return result

    async def aggregate_admin(
        self,
        organization_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> dict:
        """Admin aggregation including provider costs and margins."""
        match: dict = {}
        if organization_id:
            match["organization_id"] = organization_id
        if from_date or to_date:
            date_f: dict = {}
            if from_date:
                date_f["$gte"] = from_date
            if to_date:
                date_f["$lte"] = to_date
            match["created_at"] = date_f

        pipeline = [
            {"$match": match},
            {"$group": {
                "_id": None,
                "total_events": {"$sum": 1},
                "total_credits": {"$sum": "$credits_consumed"},
                "total_customer_charge_paise": {"$sum": "$customer_charge_paise"},
                "total_provider_cost_paise": {"$sum": "$provider_cost_paise"},
            }},
        ]
        rows = await self.col.aggregate(pipeline).to_list(1)
        if not rows:
            return {
                "total_events": 0,
                "total_credits": 0,
                "total_customer_charge_paise": 0,
                "total_provider_cost_paise": 0,
                "gross_profit_paise": 0,
                "gross_margin_pct": None,
            }
        row = rows[0]
        charge = row["total_customer_charge_paise"]
        cost = row["total_provider_cost_paise"]
        profit = charge - cost
        margin = round(profit / charge * 100, 2) if charge > 0 else None
        return {
            "total_events": row["total_events"],
            "total_credits": row["total_credits"],
            "total_customer_charge_paise": charge,
            "total_provider_cost_paise": cost,
            "gross_profit_paise": profit,
            "gross_margin_pct": margin,
        }


class ProviderUsageRepository(BaseRepository):
    collection_name = "provider_usage"
    model_class = ProviderUsage

    async def record(
        self,
        organization_id: str,
        call_id: str,
        telephony_cost_paise: int = 0,
        stt_cost_paise: int = 0,
        llm_cost_paise: int = 0,
        tts_cost_paise: int = 0,
        telephony_provider: Optional[str] = None,
        stt_provider: Optional[str] = None,
        llm_provider: Optional[str] = None,
        tts_provider: Optional[str] = None,
        duration_s: Optional[int] = None,
        stt_seconds: int = 0,
        llm_input_tokens: int = 0,
        llm_output_tokens: int = 0,
        tts_characters: int = 0,
    ) -> ProviderUsage:
        pu = ProviderUsage(
            _id=new_id(),
            organization_id=organization_id,
            call_id=call_id,
            telephony_cost_paise=telephony_cost_paise,
            stt_cost_paise=stt_cost_paise,
            llm_cost_paise=llm_cost_paise,
            tts_cost_paise=tts_cost_paise,
            telephony_provider=telephony_provider,
            stt_provider=stt_provider,
            llm_provider=llm_provider,
            tts_provider=tts_provider,
            duration_s=duration_s,
            stt_seconds=stt_seconds,
            llm_input_tokens=llm_input_tokens,
            llm_output_tokens=llm_output_tokens,
            tts_characters=tts_characters,
        )
        await self.insert(pu)
        return pu

    async def get_for_call(self, call_id: str) -> Optional[ProviderUsage]:
        return await self.find_one({"call_id": call_id})

    async def aggregate_by_provider(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[dict]:
        """Admin: cost breakdown by provider layer."""
        match: dict = {}
        if from_date or to_date:
            date_f: dict = {}
            if from_date:
                date_f["$gte"] = from_date
            if to_date:
                date_f["$lte"] = to_date
            match["created_at"] = date_f

        pipeline = [
            {"$match": match} if match else {"$match": {}},
            {"$group": {
                "_id": {
                    "telephony": "$telephony_provider",
                    "stt": "$stt_provider",
                    "llm": "$llm_provider",
                    "tts": "$tts_provider",
                },
                "calls": {"$sum": 1},
                "telephony_cost": {"$sum": "$telephony_cost_paise"},
                "stt_cost": {"$sum": "$stt_cost_paise"},
                "llm_cost": {"$sum": "$llm_cost_paise"},
                "tts_cost": {"$sum": "$tts_cost_paise"},
                "total_duration_s": {"$sum": "$duration_s"},
            }},
        ]
        return await self.col.aggregate(pipeline).to_list(None)
