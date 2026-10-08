"""Appointments API.

POST /api/v1/appointments              — create appointment
GET  /api/v1/appointments              — list appointments
GET  /api/v1/appointments/upcoming     — next N upcoming
GET  /api/v1/appointments/summary      — dashboard summary
GET  /api/v1/appointments/{id}         — get appointment
PATCH /api/v1/appointments/{id}        — update fields
POST /api/v1/appointments/{id}/confirm  — confirm
POST /api/v1/appointments/{id}/complete — complete (with outcome notes)
POST /api/v1/appointments/{id}/cancel   — cancel
POST /api/v1/appointments/{id}/no-show  — mark no-show
POST /api/v1/appointments/{id}/reschedule — reschedule to new time
"""

import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.services.appointment_service import AppointmentService

log = logging.getLogger("api.appointments")
router = APIRouter(prefix="/appointments", tags=["appointments"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class CreateAppointmentRequest(BaseModel):
    scheduled_at: datetime
    appointment_type: str = "general"
    lead_id: Optional[str] = None
    call_id: Optional[str] = None
    campaign_id: Optional[str] = None
    assigned_user_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: int = 30
    timezone: str = "Asia/Kolkata"
    location: Optional[str] = None
    location_type: str = "phone"
    notes: Optional[str] = None
    custom_fields: Optional[dict[str, Any]] = None

    @field_validator("duration_minutes")
    @classmethod
    def positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("duration_minutes must be >= 1")
        return v


class UpdateAppointmentRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    timezone: Optional[str] = None
    location: Optional[str] = None
    location_type: Optional[str] = None
    notes: Optional[str] = None
    assigned_user_id: Optional[str] = None
    custom_fields: Optional[dict[str, Any]] = None


class CompleteRequest(BaseModel):
    outcome_notes: Optional[str] = None


class CancelRequest(BaseModel):
    reason: Optional[str] = None


class RescheduleRequest(BaseModel):
    scheduled_at: datetime
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _require_org(user: CurrentUser) -> str:
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    return user.org_id


def _appt_response(a) -> dict:
    return {
        "id": a.id,
        "organization_id": a.organization_id,
        "appointment_type": a.appointment_type,
        "title": a.title,
        "description": a.description,
        "scheduled_at": a.scheduled_at.isoformat(),
        "duration_minutes": a.duration_minutes,
        "timezone": a.timezone,
        "status": a.status,
        "lead_id": a.lead_id,
        "lead_name": a.lead_name,
        "lead_phone": a.lead_phone,
        "lead_email": a.lead_email,
        "call_id": a.call_id,
        "campaign_id": a.campaign_id,
        "assigned_user_id": a.assigned_user_id,
        "location": a.location,
        "location_type": a.location_type,
        "notes": a.notes,
        "outcome_notes": a.outcome_notes,
        "custom_fields": a.custom_fields,
        "reminder_sent": a.reminder_sent,
        "created_at": a.created_at.isoformat(),
        "updated_at": a.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_appointment(
    body: CreateAppointmentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = AppointmentService(get_db())
    try:
        appt = await svc.create(
            organization_id=org_id,
            scheduled_at=body.scheduled_at,
            appointment_type=body.appointment_type,
            lead_id=body.lead_id,
            call_id=body.call_id,
            campaign_id=body.campaign_id,
            assigned_user_id=body.assigned_user_id,
            title=body.title,
            description=body.description,
            duration_minutes=body.duration_minutes,
            appt_timezone=body.timezone,
            location=body.location,
            location_type=body.location_type,
            notes=body.notes,
            custom_fields=body.custom_fields,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _appt_response(appt)


@router.get("/upcoming")
async def list_upcoming(
    limit: int = Query(default=10, le=50),
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = AppointmentService(get_db())
    appts = await svc.list_upcoming(org_id, limit=limit)
    return [_appt_response(a) for a in appts]


@router.get("/summary")
async def appointment_summary(user: CurrentUser = Depends(get_current_user)):
    org_id = _require_org(user)
    svc = AppointmentService(get_db())
    return await svc.dashboard_summary(org_id)


@router.get("")
async def list_appointments(
    appt_status: Optional[str] = None,
    appointment_type: Optional[str] = None,
    lead_id: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = AppointmentService(get_db())
    appts = await svc.list(
        org_id,
        status=appt_status,
        appointment_type=appointment_type,
        lead_id=lead_id,
        limit=limit,
        skip=skip,
    )
    return [_appt_response(a) for a in appts]


@router.get("/{appointment_id}")
async def get_appointment(
    appointment_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = AppointmentService(get_db())
    appt = await svc.get(appointment_id, org_id)
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return _appt_response(appt)


@router.patch("/{appointment_id}")
async def update_appointment(
    appointment_id: str,
    body: UpdateAppointmentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = AppointmentService(get_db())
    appt = await svc.get(appointment_id, org_id)
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await svc.repo.update_by_id(appointment_id, updates)
    updated = await svc.get(appointment_id, org_id)
    return _appt_response(updated)


@router.post("/{appointment_id}/confirm")
async def confirm_appointment(
    appointment_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = AppointmentService(get_db())
    try:
        appt = await svc.confirm(appointment_id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _appt_response(appt)


@router.post("/{appointment_id}/complete")
async def complete_appointment(
    appointment_id: str,
    body: CompleteRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = AppointmentService(get_db())
    try:
        appt = await svc.complete(appointment_id, org_id, outcome_notes=body.outcome_notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _appt_response(appt)


@router.post("/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: str,
    body: CancelRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = AppointmentService(get_db())
    try:
        appt = await svc.cancel(appointment_id, org_id, reason=body.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _appt_response(appt)


@router.post("/{appointment_id}/no-show")
async def no_show_appointment(
    appointment_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = AppointmentService(get_db())
    try:
        appt = await svc.mark_no_show(appointment_id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _appt_response(appt)


@router.post("/{appointment_id}/reschedule")
async def reschedule_appointment(
    appointment_id: str,
    body: RescheduleRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = AppointmentService(get_db())
    try:
        new_appt = await svc.reschedule(
            appointment_id, org_id, body.scheduled_at, body.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _appt_response(new_appt)
