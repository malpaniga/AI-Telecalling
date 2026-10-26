"""Appointment model — generic scheduling.

Appointments are generic. Solar uses appointment_type="site_survey", 
real estate uses "property_viewing", etc. The type is free-form string — 
no business logic in this model.

Statuses:
  scheduled   → created, awaiting
  confirmed   → lead/customer confirmed
  completed   → happened
  cancelled   → cancelled by either party
  no_show     → lead didn't show up
  rescheduled → moved (old appt cancelled, new one created)

All times stored in UTC. timezone field stores the display/local timezone.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from backend.models.base import TimestampedModel

APPOINTMENT_STATUSES = {
    "scheduled", "confirmed", "completed",
    "cancelled", "no_show", "rescheduled",
}


class Appointment(TimestampedModel):
    """A generic appointment record."""

    organization_id: str

    # References
    lead_id: Optional[str] = None
    call_id: Optional[str] = None          # call that created this appointment
    campaign_id: Optional[str] = None
    assigned_user_id: Optional[str] = None # team member responsible

    # Appointment details
    appointment_type: str = "general"       # site_survey, demo, callback, general, etc.
    title: Optional[str] = None            # display title
    description: Optional[str] = None

    # Scheduling (stored UTC, displayed in timezone)
    scheduled_at: datetime
    duration_minutes: int = 30
    timezone: str = "Asia/Kolkata"

    # Status
    status: str = "scheduled"

    # Contact info (denormalized for convenience)
    lead_name: Optional[str] = None
    lead_phone: Optional[str] = None
    lead_email: Optional[str] = None

    # Location / join info
    location: Optional[str] = None          # address or video link
    location_type: str = "phone"            # phone | in_person | video

    # Notes
    notes: Optional[str] = None
    outcome_notes: Optional[str] = None     # filled after completion

    # Metadata
    reminder_sent: bool = False
    custom_fields: dict[str, Any] = Field(default_factory=dict)

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in APPOINTMENT_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Valid: {APPOINTMENT_STATUSES}")
        return v

    @field_validator("duration_minutes")
    @classmethod
    def positive_duration(cls, v: int) -> int:
        if v < 1:
            raise ValueError("duration_minutes must be >= 1")
        return v
