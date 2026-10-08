"""Call repository — org-scoped call records."""

import logging
from datetime import datetime
from typing import Any, Optional

from pymongo import DESCENDING

from backend.models.base import new_id, utcnow
from backend.models.call import Call
from backend.repositories.base import BaseRepository

log = logging.getLogger("repo.call")


class CallRepository(BaseRepository):
    collection_name = "calls"
    model_class = Call

    async def create(
        self,
        organization_id: str,
        to_number: str,
        from_number: Optional[str] = None,
        campaign_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_version: Optional[int] = None,
        provider: str = "mock",
        direction: str = "outbound",
    ) -> Call:
        call = Call(
            _id=new_id(),
            organization_id=organization_id,
            campaign_id=campaign_id,
            lead_id=lead_id,
            agent_id=agent_id,
            agent_version=agent_version,
            from_number=from_number,
            to_number=to_number,
            provider=provider,
            direction=direction,
            status="initiating",
            started_at=utcnow(),
        )
        await self.insert(call)
        log.info("call created id=%s org=%s to=%s", call.id, organization_id, to_number)
        return call

    async def set_provider_id(
        self, call_id: str, provider_call_id: str
    ) -> bool:
        return await self.update_by_id(call_id, {
            "provider_call_id": provider_call_id,
            "status": "ringing",
        })

    async def mark_connected(self, call_id: str) -> bool:
        return await self.update_by_id(call_id, {
            "status": "connected",
            "connected_at": utcnow(),
        })

    async def finalize(
        self,
        call_id: str,
        organization_id: str,
        status: str,
        outcome: Optional[str] = None,
        duration_s: Optional[int] = None,
        talk_time_s: Optional[int] = None,
        avg_latency_ms: Optional[int] = None,
        turn_count: int = 0,
        score: int = 0,
        qualification: Optional[dict] = None,
        credits_consumed: int = 0,
        summary: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Finalize a call. Tenant-safe (org check on update)."""
        updates: dict = {
            "status": status,
            "ended_at": utcnow(),
        }
        if outcome:
            updates["outcome"] = outcome
        if duration_s is not None:
            updates["duration_s"] = duration_s
        if talk_time_s is not None:
            updates["talk_time_s"] = talk_time_s
        if avg_latency_ms is not None:
            updates["avg_latency_ms"] = avg_latency_ms
        updates["turn_count"] = turn_count
        updates["score"] = score
        if qualification:
            updates["qualification"] = qualification
        updates["credits_consumed"] = credits_consumed
        if summary:
            updates["summary"] = summary
        if error_message:
            updates["error_message"] = error_message

        result = await self.col.update_one(
            {"_id": call_id, "organization_id": organization_id},
            {"$set": {**updates, "updated_at": utcnow()}},
        )
        return result.modified_count > 0

    async def get_for_org(
        self, call_id: str, organization_id: str
    ) -> Optional[Call]:
        return await self.find_one({
            "_id": call_id,
            "organization_id": organization_id,
        })

    async def list_for_org(
        self,
        organization_id: str,
        campaign_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list[Call]:
        query: dict = {"organization_id": organization_id}
        if campaign_id:
            query["campaign_id"] = campaign_id
        if lead_id:
            query["lead_id"] = lead_id
        if status:
            query["status"] = status
        return await self.find_many(
            query,
            sort=[("started_at", DESCENDING)],
            limit=limit,
            skip=skip,
        )

    async def count_active_for_org(self, organization_id: str) -> int:
        return await self.count({
            "organization_id": organization_id,
            "status": {"$in": ["initiating", "ringing", "connected"]},
        })

    async def count_active_for_campaign(self, campaign_id: str) -> int:
        return await self.count({
            "campaign_id": campaign_id,
            "status": {"$in": ["initiating", "ringing", "connected"]},
        })
