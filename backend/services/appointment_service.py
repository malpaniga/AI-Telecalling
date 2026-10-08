"""Appointment service.

Handles:
- Creating appointments (standalone or from a call/tool)
- Status lifecycle (confirm, complete, cancel, no_show, reschedule)
- Dashboard summary (upcoming, by status)
- Timezone-aware display helpers

Appointments are generic. The appointment_type field is free-form
and configured by the business template, not this service.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.appointment import Appointment, APPOINTMENT_STATUSES
from backend.repositories.appointment_repo import AppointmentRepository

log = logging.getLogger("service.appointment")

# Valid status transitions
_TRANSITIONS: dict[str, set[str]] = {
    "scheduled":   {"confirmed", "cancelled", "rescheduled"},
    "confirmed":   {"completed", "cancelled", "no_show", "rescheduled"},
    "completed":   set(),       # terminal
    "cancelled":   {"scheduled"},  # can re-open by creating new
    "no_show":     {"rescheduled"},
    "rescheduled": set(),       # terminal (new appt created)
}


class AppointmentService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.repo = AppointmentRepository(db)

    # ---- Create ----

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
        appt_timezone: str = "Asia/Kolkata",
        location: Optional[str] = None,
        location_type: str = "phone",
        notes: Optional[str] = None,
        custom_fields: Optional[dict] = None,
    ) -> Appointment:
        # Auto-populate lead info if lead_id provided
        lead_name = lead_phone = lead_email = None
        if lead_id:
            lead = await self.db["leads"].find_one({
                "_id": lead_id,
                "organization_id": organization_id,
            })
            if lead is None:
                raise ValueError(f"Lead {lead_id} not found or not owned by org")
            lead_name = lead.get("name")
            lead_phone = lead.get("phone")
            lead_email = lead.get("email")

        appt = await self.repo.create(
            organization_id=organization_id,
            scheduled_at=scheduled_at,
            appointment_type=appointment_type,
            lead_id=lead_id,
            call_id=call_id,
            campaign_id=campaign_id,
            assigned_user_id=assigned_user_id,
            title=title,
            description=description,
            duration_minutes=duration_minutes,
            timezone=appt_timezone,
            lead_name=lead_name,
            lead_phone=lead_phone,
            lead_email=lead_email,
            location=location,
            location_type=location_type,
            notes=notes,
            custom_fields=custom_fields,
        )

        # Update lead status if creating from a call
        if lead_id and call_id:
            await self.db["leads"].update_one(
                {"_id": lead_id, "organization_id": organization_id},
                {"$set": {"status": "qualified"}},
            )

        return appt

    # ---- Status transitions ----

    async def confirm(
        self, appointment_id: str, organization_id: str
    ) -> Appointment:
        return await self._transition(appointment_id, organization_id, "confirmed")

    async def complete(
        self,
        appointment_id: str,
        organization_id: str,
        outcome_notes: Optional[str] = None,
    ) -> Appointment:
        return await self._transition(
            appointment_id, organization_id, "completed",
            outcome_notes=outcome_notes,
        )

    async def cancel(
        self,
        appointment_id: str,
        organization_id: str,
        reason: Optional[str] = None,
    ) -> Appointment:
        return await self._transition(
            appointment_id, organization_id, "cancelled",
            outcome_notes=reason,
        )

    async def mark_no_show(
        self,
        appointment_id: str,
        organization_id: str,
    ) -> Appointment:
        return await self._transition(appointment_id, organization_id, "no_show")

    async def reschedule(
        self,
        appointment_id: str,
        organization_id: str,
        new_scheduled_at: datetime,
        notes: Optional[str] = None,
    ) -> Appointment:
        new_appt = await self.repo.reschedule(
            appointment_id, organization_id, new_scheduled_at, notes
        )
        if new_appt is None:
            raise ValueError(f"Appointment {appointment_id} not found")
        return new_appt

    async def _transition(
        self,
        appointment_id: str,
        organization_id: str,
        new_status: str,
        outcome_notes: Optional[str] = None,
    ) -> Appointment:
        appt = await self.repo.get_for_org(appointment_id, organization_id)
        if appt is None:
            raise ValueError(f"Appointment {appointment_id} not found")

        allowed = _TRANSITIONS.get(appt.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition appointment from '{appt.status}' to '{new_status}'. "
                f"Allowed transitions: {sorted(allowed) or 'none (terminal state)'}"
            )

        ok = await self.repo.transition_status(
            appointment_id, organization_id, new_status, outcome_notes
        )
        if not ok:
            raise RuntimeError(f"Failed to update appointment status")

        return await self.repo.get_for_org(appointment_id, organization_id)

    # ---- Read ----

    async def get(
        self, appointment_id: str, organization_id: str
    ) -> Optional[Appointment]:
        return await self.repo.get_for_org(appointment_id, organization_id)

    async def list(
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
        return await self.repo.list_for_org(
            organization_id,
            status=status,
            appointment_type=appointment_type,
            lead_id=lead_id,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            skip=skip,
        )

    async def list_upcoming(
        self, organization_id: str, limit: int = 10
    ) -> list[Appointment]:
        return await self.repo.list_upcoming(organization_id, limit=limit)

    async def dashboard_summary(self, organization_id: str) -> dict:
        counts = await self.repo.count_by_status(organization_id)
        upcoming = await self.repo.list_upcoming(organization_id, limit=5)
        total = sum(counts.values())
        return {
            "total": total,
            "by_status": counts,
            "scheduled": counts.get("scheduled", 0),
            "confirmed": counts.get("confirmed", 0),
            "completed": counts.get("completed", 0),
            "cancelled": counts.get("cancelled", 0),
            "no_show": counts.get("no_show", 0),
            "upcoming": [_appt_brief(a) for a in upcoming],
        }


def _appt_brief(a: Appointment) -> dict:
    return {
        "id": a.id,
        "appointment_type": a.appointment_type,
        "title": a.title,
        "scheduled_at": a.scheduled_at.isoformat(),
        "timezone": a.timezone,
        "status": a.status,
        "lead_name": a.lead_name,
        "lead_phone": a.lead_phone,
    }
