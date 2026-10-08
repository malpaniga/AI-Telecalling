"""Appointment repository."""

import logging
from datetime import datetime, timezone
from typing import Optional

from pymongo import ASCENDING, DESCENDING

from backend.models.appointment import Appointment
from backend.models.base import new_id, utcnow
from backend.repositories.base import BaseRepository

log = logging.getLogger("repo.appointment")


class AppointmentRepository(BaseRepository):
    collection_name = "appointments"
    model_class = Appointment

    async def create(
        self,
        organization_id: str,
        scheduled_at: datetime,
        appointment_type: str = "general",
        lead_id: Optional[str] = None,
        call_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        assigned_user_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        duration_minutes: int = 30,
        timezone: str = "Asia/Kolkata",
        lead_name: Optional[str] = None,
        lead_phone: Optional[str] = None,
        lead_email: Optional[str] = None,
        location: Optional[str] = None,
        location_type: str = "phone",
        notes: Optional[str] = None,
        custom_fields: Optional[dict] = None,
    ) -> Appointment:
        appt = Appointment(
            _id=new_id(),
            organization_id=organization_id,
            scheduled_at=scheduled_at,
            appointment_type=appointment_type,
            lead_id=lead_id,
            call_id=call_id,
            campaign_id=campaign_id,
            assigned_user_id=assigned_user_id,
            title=title or f"{appointment_type.replace('_', ' ').title()} appointment",
            description=description,
            duration_minutes=duration_minutes,
            timezone=timezone,
            lead_name=lead_name,
            lead_phone=lead_phone,
            lead_email=lead_email,
            location=location,
            location_type=location_type,
            notes=notes,
            custom_fields=custom_fields or {},
            status="scheduled",
        )
        await self.insert(appt)
        log.info("appointment created id=%s org=%s type=%s at=%s",
                 appt.id, organization_id, appointment_type, scheduled_at)
        return appt

    async def get_for_org(
        self, appointment_id: str, organization_id: str
    ) -> Optional[Appointment]:
        return await self.find_one({
            "_id": appointment_id,
            "organization_id": organization_id,
        })

    async def list_for_org(
        self,
        organization_id: str,
        status: Optional[str] = None,
        appointment_type: Optional[str] = None,
        lead_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list[Appointment]:
        query: dict = {"organization_id": organization_id}
        if status:
            query["status"] = status
        if appointment_type:
            query["appointment_type"] = appointment_type
        if lead_id:
            query["lead_id"] = lead_id
        if from_date or to_date:
            date_filter: dict = {}
            if from_date:
                date_filter["$gte"] = from_date
            if to_date:
                date_filter["$lte"] = to_date
            query["scheduled_at"] = date_filter

        return await self.find_many(
            query,
            sort=[("scheduled_at", ASCENDING)],
            limit=limit,
            skip=skip,
        )

    async def list_upcoming(
        self,
        organization_id: str,
        limit: int = 10,
    ) -> list[Appointment]:
        """Upcoming scheduled/confirmed appointments."""
        now = utcnow()
        return await self.find_many(
            {
                "organization_id": organization_id,
                "status": {"$in": ["scheduled", "confirmed"]},
                "scheduled_at": {"$gte": now},
            },
            sort=[("scheduled_at", ASCENDING)],
            limit=limit,
        )

    async def transition_status(
        self,
        appointment_id: str,
        organization_id: str,
        new_status: str,
        outcome_notes: Optional[str] = None,
    ) -> bool:
        updates: dict = {"status": new_status}
        if outcome_notes:
            updates["outcome_notes"] = outcome_notes
        result = await self.col.update_one(
            {"_id": appointment_id, "organization_id": organization_id},
            {"$set": {**updates, "updated_at": utcnow()}},
        )
        return result.modified_count > 0

    async def reschedule(
        self,
        appointment_id: str,
        organization_id: str,
        new_scheduled_at: datetime,
        notes: Optional[str] = None,
    ) -> Optional[Appointment]:
        """Mark existing as rescheduled and create a new one."""
        old = await self.get_for_org(appointment_id, organization_id)
        if old is None:
            return None

        # Mark old as rescheduled
        await self.transition_status(appointment_id, organization_id, "rescheduled")

        # Create new appointment
        new_appt = await self.create(
            organization_id=organization_id,
            scheduled_at=new_scheduled_at,
            appointment_type=old.appointment_type,
            lead_id=old.lead_id,
            call_id=old.call_id,
            campaign_id=old.campaign_id,
            assigned_user_id=old.assigned_user_id,
            title=old.title,
            description=old.description,
            duration_minutes=old.duration_minutes,
            timezone=old.timezone,
            lead_name=old.lead_name,
            lead_phone=old.lead_phone,
            lead_email=old.lead_email,
            location=old.location,
            location_type=old.location_type,
            notes=notes or old.notes,
            custom_fields=old.custom_fields,
        )
        log.info("appointment rescheduled old=%s new=%s at=%s",
                 appointment_id, new_appt.id, new_scheduled_at)
        return new_appt

    async def count_by_status(self, organization_id: str) -> dict[str, int]:
        pipeline = [
            {"$match": {"organization_id": organization_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        rows = await self.col.aggregate(pipeline).to_list(None)
        return {r["_id"]: r["count"] for r in rows}
