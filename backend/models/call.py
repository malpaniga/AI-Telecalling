"""Call model — an outbound AI call record.

Each call is scoped to an organization, campaign, and lead.
Call records are immutable once finalized (status: completed/failed/no_answer).

Transcript turns are stored in the separate 'turns' collection (legacy)
or as embedded documents via the transcript service (M20).

Call statuses:
  initiating  — call request sent to telephony provider
  ringing     — phone is ringing at lead's end
  connected   — lead answered, AI conversation active
  completed   — call ended normally
  no_answer   — lead didn't pick up
  busy        — lead's line busy
  failed      — technical failure
  cancelled   — cancelled before connection

Outcomes (set on completion):
  qualified         — lead meets qualification criteria
  not_interested    — lead declined
  callback          — lead asked to call back
  appointment_set   — appointment booked
  no_answer         — no pickup
  voicemail         — left voicemail
  transferred       — transferred to human agent
  failed            — call failed technically
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from backend.models.base import TimestampedModel

CALL_STATUSES = {
    "initiating", "ringing", "connected",
    "completed", "no_answer", "busy", "failed", "cancelled",
}

CALL_OUTCOMES = {
    "qualified", "not_interested", "callback", "appointment_set",
    "no_answer", "voicemail", "transferred", "failed",
}


class Call(TimestampedModel):
    """An outbound AI call record."""

    organization_id: str
    campaign_id: Optional[str] = None
    lead_id: Optional[str] = None
    agent_id: Optional[str] = None
    agent_version: Optional[int] = None

    # Phone numbers
    from_number: Optional[str] = None      # calling number (E.164)
    to_number: Optional[str] = None        # lead's number (E.164)

    # Status
    status: str = "initiating"
    outcome: Optional[str] = None
    direction: str = "outbound"            # outbound | inbound

    # Provider linkage (internal — never exposed to customers)
    provider: str = "mock"
    provider_call_id: Optional[str] = None      # e.g. Twilio call SID
    provider_metadata: dict = Field(default_factory=dict)

    # Duration and timing
    started_at: Optional[datetime] = None
    connected_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_s: Optional[int] = None            # total call duration
    talk_time_s: Optional[int] = None           # time caller was connected
    ring_time_s: Optional[int] = None

    # AI performance
    avg_latency_ms: Optional[int] = None
    turn_count: int = 0

    # Qualification result
    score: int = 0
    qualification: dict[str, Any] = Field(default_factory=dict)

    # Credits
    credits_reserved: int = 0
    credits_consumed: int = 0
    credit_reservation_id: Optional[str] = None

    # Recording
    recording_url: Optional[str] = None

    # Notes
    summary: Optional[str] = None
    error_message: Optional[str] = None
