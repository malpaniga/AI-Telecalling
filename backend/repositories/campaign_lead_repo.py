"""Repository for CampaignLead collection."""

import logging
from datetime import datetime
from typing import Any, Optional

from pymongo import ASCENDING, DESCENDING, UpdateOne
from pymongo.errors import BulkWriteError, DuplicateKeyError

from backend.models.base import new_id, utcnow
from backend.models.campaign_lead import CampaignLead
from backend.repositories.base import BaseRepository

log = logging.getLogger("repo.campaign_lead")


class CampaignLeadRepository(BaseRepository):
    collection_name = "campaign_leads"
    model_class = CampaignLead

    @property
    def collection(self):
        return self.col

    async def ensure_indexes(self) -> None:
        """Create required indexes."""
        await self.collection.create_index(
            [("campaign_id", ASCENDING), ("lead_id", ASCENDING)],
            unique=True,
        )
        await self.collection.create_index(
            [("campaign_id", ASCENDING), ("status", ASCENDING), ("next_attempt_at", ASCENDING)]
        )
        await self.collection.create_index(
            [("organization_id", ASCENDING), ("campaign_id", ASCENDING)]
        )
        await self.collection.create_index(
            [("organization_id", ASCENDING), ("phone", ASCENDING)]
        )

    async def enroll_lead(
        self,
        campaign_id: str,
        lead_id: str,
        organization_id: str,
        phone: str,
        custom_fields: Optional[dict[str, Any]] = None,
        max_attempts: int = 3,
    ) -> CampaignLead:
        """Enroll or re-enroll a lead in a campaign."""
        now = utcnow()
        doc = {
            "_id": new_id(),
            "organization_id": organization_id,
            "campaign_id": campaign_id,
            "lead_id": lead_id,
            "phone": phone.strip(),
            "status": "new",
            "attempts": 0,
            "max_attempts": max_attempts,
            "last_called_at": None,
            "next_attempt_at": None,
            "call_id": None,
            "disposition": None,
            "notes": None,
            "custom_fields": custom_fields or {},
            "created_at": now,
            "updated_at": now,
        }
        await self.collection.update_one(
            {"campaign_id": campaign_id, "lead_id": lead_id},
            {"$setOnInsert": doc},
            upsert=True,
        )
        return await self.find_by_campaign_lead(campaign_id, lead_id)

    async def bulk_enroll(
        self,
        campaign_id: str,
        organization_id: str,
        items: list[dict[str, Any]],
        max_attempts: int = 3,
    ) -> dict[str, int]:
        """Bulk enroll leads into a campaign.
        
        items: list of dicts with:
          lead_id: str
          phone: str
          custom_fields: Optional[dict]
        """
        if not items:
            return {"enrolled": 0, "skipped": 0}

        lead_ids = [item["lead_id"] for item in items]
        cursor = self.col.find(
            {"campaign_id": campaign_id, "lead_id": {"$in": lead_ids}},
            {"lead_id": 1},
        )
        existing_docs = await cursor.to_list(length=len(items))
        existing_lead_ids = {d["lead_id"] for d in existing_docs}

        now = utcnow()
        new_docs = []
        for item in items:
            if item["lead_id"] in existing_lead_ids:
                continue
            doc = {
                "_id": new_id(),
                "organization_id": organization_id,
                "campaign_id": campaign_id,
                "lead_id": item["lead_id"],
                "phone": item["phone"].strip(),
                "status": "new",
                "attempts": 0,
                "max_attempts": max_attempts,
                "last_called_at": None,
                "next_attempt_at": None,
                "call_id": None,
                "disposition": None,
                "notes": None,
                "custom_fields": item.get("custom_fields") or {},
                "created_at": now,
                "updated_at": now,
            }
            new_docs.append(doc)

        enrolled = 0
        if new_docs:
            try:
                res = await self.col.insert_many(new_docs, ordered=False)
                enrolled = len(res.inserted_ids)
            except BulkWriteError as exc:
                enrolled = exc.details.get("nInserted", 0)
            except Exception as e:
                log.warning("bulk_enroll insert_many error: %s", e)

        return {
            "enrolled": enrolled,
            "skipped": len(items) - enrolled,
        }

    async def find_by_campaign_lead(
        self, campaign_id: str, lead_id: str
    ) -> Optional[CampaignLead]:
        doc = await self.collection.find_one(
            {"campaign_id": campaign_id, "lead_id": lead_id}
        )
        if not doc:
            return None
        return CampaignLead.model_validate(doc)

    async def list_for_campaign(
        self,
        campaign_id: str,
        organization_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> tuple[list[dict], int]:
        query: dict[str, Any] = {
            "campaign_id": campaign_id,
            "organization_id": organization_id,
        }
        if status:
            query["status"] = status

        total = await self.collection.count_documents(query)
        cursor = (
            self.collection.find(query)
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return docs, total

    async def pick_next_eligible(self, campaign_id: str) -> Optional[dict]:
        """Atomically pick the next eligible lead to dial and mark scheduled."""
        now = utcnow()
        query = {
            "campaign_id": campaign_id,
            "status": {"$in": ["new", "callback"]},
            "$or": [
                {"next_attempt_at": None},
                {"next_attempt_at": {"$lte": now}},
            ],
        }
        return await self.collection.find_one_and_update(
            query,
            {"$set": {"status": "scheduled", "last_called_at": now, "updated_at": now}},
            return_document=True,
        )

    async def update_status(
        self,
        campaign_id: str,
        lead_id: str,
        status: str,
        extra_updates: Optional[dict[str, Any]] = None,
    ) -> bool:
        updates = {"status": status, "updated_at": utcnow()}
        if extra_updates:
            updates.update(extra_updates)

        res = await self.collection.update_one(
            {"campaign_id": campaign_id, "lead_id": lead_id},
            {"$set": updates},
        )
        return res.modified_count > 0

    async def mark_dnc_for_phone(self, organization_id: str, phone: str) -> int:
        """Mark all active enrollments for a phone number as DNC across all campaigns."""
        res = await self.collection.update_many(
            {
                "organization_id": organization_id,
                "phone": phone.strip(),
                "status": {"$in": ["new", "scheduled", "callback"]},
            },
            {"$set": {"status": "dnc", "updated_at": utcnow()}},
        )
        return res.modified_count

    async def remove_lead(self, campaign_id: str, lead_id: str, organization_id: str) -> bool:
        """Remove a lead from a campaign if it hasn't been dialed or completed."""
        res = await self.collection.delete_one({
            "campaign_id": campaign_id,
            "lead_id": lead_id,
            "organization_id": organization_id,
            "status": {"$in": ["new", "callback"]},
        })
        return res.deleted_count > 0
