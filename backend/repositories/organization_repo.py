"""Organization repository."""

import re
from datetime import datetime, timezone
from typing import Optional

from pymongo import DESCENDING

from backend.models.base import new_id, utcnow
from backend.models.organization import Organization, OrganizationSettings
from backend.repositories.base import BaseRepository


def _slugify(name: str) -> str:
    """Simple slugifier: lowercase, alphanumeric + hyphens."""
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")[:50]


class OrganizationRepository(BaseRepository):
    collection_name = "organizations"
    model_class = Organization

    async def create(
        self,
        name: str,
        email: str,
        slug: Optional[str] = None,
        phone: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Organization:
        final_slug = slug or _slugify(name)
        # Ensure slug uniqueness
        base_slug = final_slug
        counter = 1
        while await self.exists({"slug": final_slug}):
            final_slug = f"{base_slug}-{counter}"
            counter += 1

        org = Organization(
            _id=new_id(),
            name=name,
            slug=final_slug,
            email=email,
            phone=phone,
            created_by=created_by,
            settings=OrganizationSettings(_id=new_id()),
        )
        await self.insert(org)
        return org

    async def find_by_slug(self, slug: str) -> Optional[Organization]:
        return await self.find_one({"slug": slug})

    async def find_by_email(self, email: str) -> Optional[Organization]:
        return await self.find_one({"email": email})

    async def list_all(
        self, limit: int = 50, skip: int = 0, status: Optional[str] = None
    ) -> list[Organization]:
        query: dict = {}
        if status:
            query["status"] = status
        return await self.find_many(
            query,
            sort=[("created_at", DESCENDING)],
            limit=limit,
            skip=skip,
        )

    async def suspend(self, org_id: str, reason: str) -> bool:
        return await self.update_by_id(org_id, {
            "status": "suspended",
            "suspended_at": utcnow(),
            "suspended_reason": reason,
        })

    async def reactivate(self, org_id: str) -> bool:
        return await self.update_by_id(org_id, {
            "status": "active",
            "suspended_at": None,
            "suspended_reason": None,
        })

    async def update_limits(
        self,
        org_id: str,
        max_concurrent_calls: Optional[int] = None,
        max_campaigns: Optional[int] = None,
        max_agents: Optional[int] = None,
        max_leads_per_campaign: Optional[int] = None,
    ) -> bool:
        updates: dict = {}
        if max_concurrent_calls is not None:
            updates["max_concurrent_calls"] = max_concurrent_calls
        if max_campaigns is not None:
            updates["max_campaigns"] = max_campaigns
        if max_agents is not None:
            updates["max_agents"] = max_agents
        if max_leads_per_campaign is not None:
            updates["max_leads_per_campaign"] = max_leads_per_campaign
        if not updates:
            return False
        return await self.update_by_id(org_id, updates)
