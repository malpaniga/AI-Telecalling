"""Phone number inventory and assignment repositories.

Concurrent reservation safety:
  atomic_reserve() uses a single find_one_and_update with query filter
  {status: "available"} so only ONE request can win the reservation.
  No explicit locking needed — MongoDB's single-document atomicity guarantees it.
"""

import logging
from datetime import datetime
from typing import Optional

from pymongo import ASCENDING, DESCENDING

from backend.models.base import new_id, utcnow
from backend.models.phone_number import PhoneNumber, PhoneNumberAssignment
from backend.repositories.base import BaseRepository

log = logging.getLogger("repo.phone_number")


class PhoneNumberRepository(BaseRepository):
    collection_name = "phone_numbers"
    model_class = PhoneNumber

    async def create(
        self,
        number: str,
        provider: str,
        provider_resource_id: Optional[str] = None,
        display_name: Optional[str] = None,
        country_code: str = "IN",
        number_type: str = "local",
        can_voice: bool = True,
        can_sms: bool = False,
        can_whatsapp: bool = False,
        rental_paise_per_month: int = 0,
        provider_metadata: Optional[dict] = None,
    ) -> PhoneNumber:
        pn = PhoneNumber(
            _id=new_id(),
            number=number,
            display_name=display_name or number,
            country_code=country_code,
            number_type=number_type,
            can_voice=can_voice,
            can_sms=can_sms,
            can_whatsapp=can_whatsapp,
            status="available",
            provider=provider,
            provider_resource_id=provider_resource_id,
            provider_metadata=provider_metadata or {},
            rental_paise_per_month=rental_paise_per_month,
        )
        await self.insert(pn)
        log.info("phone number added id=%s number=%s provider=%s", pn.id, number, provider)
        return pn

    async def find_by_number(self, number: str) -> Optional[PhoneNumber]:
        return await self.find_one({"number": number})

    async def list_available(
        self,
        country_code: Optional[str] = None,
        number_type: Optional[str] = None,
        can_sms: Optional[bool] = None,
        can_whatsapp: Optional[bool] = None,
        limit: int = 50,
    ) -> list[PhoneNumber]:
        query: dict = {"status": "available"}
        if country_code:
            query["country_code"] = country_code
        if number_type:
            query["number_type"] = number_type
        if can_sms is not None:
            query["can_sms"] = can_sms
        if can_whatsapp is not None:
            query["can_whatsapp"] = can_whatsapp
        return await self.find_many(query, sort=[("created_at", ASCENDING)], limit=limit)

    async def list_for_org(self, organization_id: str) -> list[PhoneNumber]:
        return await self.find_many(
            {"organization_id": organization_id,
             "status": {"$in": ["assigned", "suspended"]}},
            sort=[("assigned_at", DESCENDING)],
        )

    async def list_all(
        self,
        status: Optional[str] = None,
        provider: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[PhoneNumber]:
        query: dict = {}
        if status:
            query["status"] = status
        if provider:
            query["provider"] = provider
        return await self.find_many(
            query, sort=[("created_at", DESCENDING)], limit=limit, skip=skip
        )

    async def atomic_reserve(self, phone_number_id: str) -> Optional[PhoneNumber]:
        """
        Atomically mark a number as 'reserved' only if it is currently 'available'.
        Returns the updated PhoneNumber if successful, None if already taken.
        This is the concurrent-safe reservation primitive.
        """
        result = await self.col.find_one_and_update(
            {"_id": phone_number_id, "status": "available"},
            {"$set": {"status": "reserved", "updated_at": utcnow()}},
            return_document=True,
        )
        if result is None:
            return None
        return PhoneNumber(**result)

    async def atomic_assign(
        self,
        phone_number_id: str,
        organization_id: str,
    ) -> Optional[PhoneNumber]:
        """Finalize assignment: reserved → assigned."""
        now = utcnow()
        result = await self.col.find_one_and_update(
            {"_id": phone_number_id, "status": {"$in": ["reserved", "available"]}},
            {"$set": {
                "status": "assigned",
                "organization_id": organization_id,
                "assigned_at": now,
                "updated_at": now,
            }},
            return_document=True,
        )
        if result is None:
            return None
        return PhoneNumber(**result)

    async def release(self, phone_number_id: str) -> bool:
        """Return number to available pool."""
        return await self.update_by_id(phone_number_id, {
            "status": "available",
            "organization_id": None,
            "assigned_at": None,
            "released_at": utcnow(),
        })

    async def suspend(self, phone_number_id: str) -> bool:
        return await self.update_by_id(phone_number_id, {
            "status": "suspended",
            "suspended_at": utcnow(),
        })

    async def reactivate(self, phone_number_id: str) -> bool:
        return await self.update_by_id(phone_number_id, {
            "status": "assigned",
            "suspended_at": None,
        })

    async def retire(self, phone_number_id: str) -> bool:
        return await self.update_by_id(phone_number_id, {"status": "retired"})

    async def count_by_status(self) -> dict[str, int]:
        pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        rows = await self.col.aggregate(pipeline).to_list(None)
        return {r["_id"]: r["count"] for r in rows}


class PhoneNumberAssignmentRepository(BaseRepository):
    collection_name = "phone_number_assignments"
    model_class = PhoneNumberAssignment

    async def record(
        self,
        phone_number_id: str,
        number: str,
        organization_id: str,
        action: str,
        performed_by: Optional[str] = None,
        rental_paise_per_month: int = 0,
        notes: Optional[str] = None,
    ) -> PhoneNumberAssignment:
        entry = PhoneNumberAssignment(
            _id=new_id(),
            phone_number_id=phone_number_id,
            number=number,
            organization_id=organization_id,
            action=action,
            performed_by=performed_by,
            rental_paise_per_month=rental_paise_per_month,
            notes=notes,
        )
        await self.insert(entry)
        return entry

    async def history_for_number(self, phone_number_id: str) -> list[PhoneNumberAssignment]:
        return await self.find_many(
            {"phone_number_id": phone_number_id},
            sort=[("created_at", DESCENDING)],
        )

    async def history_for_org(self, organization_id: str, limit: int = 50) -> list[PhoneNumberAssignment]:
        return await self.find_many(
            {"organization_id": organization_id},
            sort=[("created_at", DESCENDING)],
            limit=limit,
        )
