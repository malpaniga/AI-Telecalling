"""Lead and DNC repositories.

Key design:
- All queries include organization_id (tenant isolation)
- bulk_insert uses ordered=False so one bad doc doesn't fail the whole batch
- DNC checks use the unique (organization_id, phone) index
- Deduplication uses the same (organization_id, phone) unique index
"""

import logging
from datetime import datetime
from typing import Any, Optional

from pymongo import ASCENDING, DESCENDING, UpdateOne
from pymongo.errors import BulkWriteError, DuplicateKeyError

from backend.models.base import new_id, utcnow
from backend.models.lead import DNCEntry, Lead
from backend.repositories.base import BaseRepository

log = logging.getLogger("repo.lead")


class LeadRepository(BaseRepository):
    collection_name = "leads"
    model_class = Lead

    async def create(
        self,
        organization_id: str,
        phone: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        campaign_id: Optional[str] = None,
        source: str = "manual",
        custom_fields: Optional[dict] = None,
        tags: Optional[list] = None,
        import_batch_id: Optional[str] = None,
        original_row: Optional[int] = None,
    ) -> Lead:
        lead = Lead(
            _id=new_id(),
            organization_id=organization_id,
            phone=phone.strip(),
            name=name,
            email=email,
            campaign_id=campaign_id,
            source=source,
            custom_fields=custom_fields or {},
            tags=tags or [],
            import_batch_id=import_batch_id,
            original_row=original_row,
        )
        await self.insert(lead)
        return lead

    async def bulk_insert(
        self,
        leads: list[dict],
        organization_id: str,
    ) -> dict:
        """
        Insert multiple lead documents. Skips duplicates (same org + phone).
        Returns {inserted, skipped, errors}.
        """
        if not leads:
            return {"inserted": 0, "skipped": 0, "errors": []}

        # Ensure organization_id on every doc
        for doc in leads:
            doc["organization_id"] = organization_id
            if "_id" not in doc:
                doc["_id"] = new_id()
            now = utcnow()
            doc.setdefault("created_at", now)
            doc.setdefault("updated_at", now)

        inserted = 0
        skipped = 0
        errors = []

        try:
            result = await self.col.insert_many(leads, ordered=False)
            inserted = len(result.inserted_ids)
        except BulkWriteError as exc:
            write_errors = exc.details.get("writeErrors", [])
            inserted = exc.details.get("nInserted", 0)
            for we in write_errors:
                if we.get("code") == 11000:  # duplicate key
                    skipped += 1
                else:
                    errors.append({
                        "row": we.get("index"),
                        "error": we.get("errmsg", "Unknown error"),
                    })
        except Exception as exc:  # noqa: BLE001
            log.error("bulk_insert failed: %s", exc)
            errors.append({"row": None, "error": str(exc)})

        log.info("bulk_insert org=%s inserted=%d skipped=%d errors=%d",
                 organization_id, inserted, skipped, len(errors))
        return {"inserted": inserted, "skipped": skipped, "errors": errors}

    async def find_by_phone_org(
        self, phone: str, organization_id: str
    ) -> Optional[Lead]:
        return await self.find_one({
            "phone": phone,
            "organization_id": organization_id,
        })

    async def list_for_org(
        self,
        organization_id: str,
        campaign_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[Lead]:
        query: dict = {"organization_id": organization_id}
        if campaign_id:
            query["campaign_id"] = campaign_id
        if status:
            query["status"] = status
        return await self.find_many(
            query,
            sort=[("created_at", DESCENDING)],
            limit=limit,
            skip=skip,
        )

    async def count_for_org(
        self, organization_id: str, campaign_id: Optional[str] = None
    ) -> int:
        query: dict = {"organization_id": organization_id}
        if campaign_id:
            query["campaign_id"] = campaign_id
        return await self.count(query)

    async def update_status(
        self,
        lead_id: str,
        organization_id: str,
        status: str,
        qualification: Optional[dict] = None,
        score: Optional[int] = None,
    ) -> bool:
        updates: dict = {"status": status}
        if qualification is not None:
            updates["qualification"] = qualification
        if score is not None:
            updates["score"] = score
        # Tenant-safe update
        result = await self.col.update_one(
            {"_id": lead_id, "organization_id": organization_id},
            {"$set": {**updates, "updated_at": utcnow()}},
        )
        return result.modified_count > 0

    async def increment_attempts(
        self, lead_id: str, organization_id: str
    ) -> bool:
        result = await self.col.update_one(
            {"_id": lead_id, "organization_id": organization_id},
            {
                "$inc": {"attempts": 1},
                "$set": {"last_contact_at": utcnow(), "updated_at": utcnow()},
            },
        )
        return result.modified_count > 0

    async def phones_in_org(
        self, organization_id: str, phones: list[str]
    ) -> set[str]:
        """Return the subset of phones that already exist in this org."""
        docs = await self.col.find(
            {"organization_id": organization_id, "phone": {"$in": phones}},
            {"phone": 1},
        ).to_list(length=None)
        return {d["phone"] for d in docs}

    async def delete_for_org(
        self, lead_id: str, organization_id: str
    ) -> bool:
        result = await self.col.delete_one({
            "_id": lead_id,
            "organization_id": organization_id,
        })
        return result.deleted_count > 0

    async def bulk_assign_campaign(
        self,
        lead_ids: list[str],
        campaign_id: str,
        organization_id: str,
    ) -> int:
        result = await self.col.update_many(
            {"_id": {"$in": lead_ids}, "organization_id": organization_id},
            {"$set": {"campaign_id": campaign_id, "updated_at": utcnow()}},
        )
        return result.modified_count


class DNCRepository(BaseRepository):
    collection_name = "dnc_entries"
    model_class = DNCEntry

    async def add(
        self,
        organization_id: str,
        phone: str,
        reason: Optional[str] = None,
        added_by: Optional[str] = None,
        source: str = "manual",
    ) -> Optional[DNCEntry]:
        """Add phone to DNC. Returns None if already on DNC."""
        existing = await self.find_one({
            "organization_id": organization_id,
            "phone": phone,
        })
        if existing:
            return None  # already on DNC

        entry = DNCEntry(
            _id=new_id(),
            organization_id=organization_id,
            phone=phone,
            reason=reason,
            added_by=added_by,
            source=source,
        )
        await self.insert(entry)
        log.info("DNC added org=%s phone=%s", organization_id, phone)
        return entry

    async def is_dnc(self, organization_id: str, phone: str) -> bool:
        return await self.exists({
            "organization_id": organization_id,
            "phone": phone,
        })

    async def bulk_check(
        self, organization_id: str, phones: list[str]
    ) -> set[str]:
        """Return the subset of phones that are on DNC for this org."""
        docs = await self.col.find(
            {"organization_id": organization_id, "phone": {"$in": phones}},
            {"phone": 1},
        ).to_list(length=None)
        return {d["phone"] for d in docs}

    async def remove(self, organization_id: str, phone: str) -> bool:
        result = await self.col.delete_one({
            "organization_id": organization_id,
            "phone": phone,
        })
        return result.deleted_count > 0

    async def list_for_org(
        self, organization_id: str, limit: int = 100, skip: int = 0
    ) -> list[DNCEntry]:
        return await self.find_many(
            {"organization_id": organization_id},
            sort=[("added_at", DESCENDING)],
            limit=limit,
            skip=skip,
        )
