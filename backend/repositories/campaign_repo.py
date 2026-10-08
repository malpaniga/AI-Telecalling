"""Campaign repository."""

import logging
from datetime import datetime
from typing import Optional

from pymongo import ASCENDING, DESCENDING

from backend.models.base import new_id, utcnow
from backend.models.campaign import Campaign, CallingHours, RetryPolicy
from backend.repositories.base import BaseRepository

log = logging.getLogger("repo.campaign")


class CampaignRepository(BaseRepository):
    collection_name = "campaigns"
    model_class = Campaign

    async def create(
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
        campaign = Campaign(
            _id=new_id(),
            organization_id=organization_id,
            name=name,
            description=description,
            agent_id=agent_id,
            agent_version=agent_version,
            voice_profile_id=voice_profile_id,
            voice_profile_version=voice_profile_version,
            calling_number_id=calling_number_id,
            calling_number=calling_number,
            max_concurrent_calls=max_concurrent_calls,
            timezone=timezone,
            lead_filter=lead_filter or {},
            calling_hours=CallingHours(**(calling_hours or {})),
            retry_policy=RetryPolicy(**(retry_policy or {})),
            scheduled_at=scheduled_at,
            created_by=created_by,
            status="draft",
        )
        await self.insert(campaign)
        log.info("campaign created id=%s org=%s name=%s", campaign.id, organization_id, name)
        return campaign

    async def list_for_org(
        self,
        organization_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list[Campaign]:
        query: dict = {"organization_id": organization_id}
        if status:
            query["status"] = status
        return await self.find_many(
            query,
            sort=[("created_at", DESCENDING)],
            limit=limit,
            skip=skip,
        )

    async def get_for_org(
        self, campaign_id: str, organization_id: str
    ) -> Optional[Campaign]:
        return await self.find_one({
            "_id": campaign_id,
            "organization_id": organization_id,
        })

    async def transition_status(
        self,
        campaign_id: str,
        organization_id: str,
        new_status: str,
        extra_updates: Optional[dict] = None,
    ) -> bool:
        """Atomic status update scoped to org."""
        updates = {"status": new_status}
        if extra_updates:
            updates.update(extra_updates)
        result = await self.col.update_one(
            {"_id": campaign_id, "organization_id": organization_id},
            {"$set": {**updates, "updated_at": utcnow()}},
        )
        return result.modified_count > 0

    async def increment_counter(
        self, campaign_id: str, field: str, amount: int = 1
    ) -> bool:
        result = await self.col.update_one(
            {"_id": campaign_id},
            {"$inc": {field: amount}, "$set": {"updated_at": utcnow()}},
        )
        return result.modified_count > 0

    async def list_active(self) -> list[Campaign]:
        """All running/scheduled campaigns — for worker polling."""
        return await self.find_many(
            {"status": {"$in": ["running", "scheduled"]}},
            sort=[("scheduled_at", ASCENDING)],
        )

    async def list_all_admin(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[Campaign]:
        query: dict = {}
        if status:
            query["status"] = status
        return await self.find_many(
            query,
            sort=[("created_at", DESCENDING)],
            limit=limit,
            skip=skip,
        )
