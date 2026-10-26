"""Campaign model.

A campaign is a scheduled outbound calling operation that dials a filtered
set of leads using a specific agent and calling number.

States (strict FSM — transitions enforced in CampaignService):
  draft                 → configured but not started
  scheduled             → start time set, waiting
  running               → actively dialing
  paused                → paused by user
  paused_low_credits    → auto-paused (insufficient credits)
  completed             → all leads processed
  cancelled             → stopped by user before completion
  failed                → unrecoverable error

MongoDB is source of truth. Redis holds:
  campaign_state:{campaign_id}    → current status (fast read for workers)
  campaign_active_calls:{id}      → current active call count (atomic $inc)
  campaign_lock:{id}              → distributed lock for state transitions
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from backend.models.base import TimestampedModel

CAMPAIGN_STATUSES = {
    "draft", "scheduled", "running", "paused",
    "paused_low_credits", "completed", "cancelled", "failed",
}

TERMINAL_STATUSES = {"completed", "cancelled", "failed"}
ACTIVE_STATUSES = {"running", "scheduled"}
PAUSABLE_STATUSES = {"running", "scheduled", "paused_low_credits"}


class CallingHours(TimestampedModel):
    """Time window during which calls are allowed."""
    start_time: str = "09:00"   # HH:MM in campaign timezone
    end_time: str = "19:00"
    days_of_week: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    # 0=Sunday, 1=Monday, ..., 6=Saturday


class RetryPolicy(TimestampedModel):
    """How to retry leads that didn't connect."""
    max_attempts: int = 3
    retry_delay_minutes: int = 60       # wait between retries
    retry_on: list[str] = Field(
        default_factory=lambda: ["no_answer", "busy", "failed"]
    )


class Campaign(TimestampedModel):
    """An outbound calling campaign."""

    organization_id: str
    name: str
    description: str = ""

    # Configuration
    agent_id: str
    agent_version: int
    voice_profile_id: str
    voice_profile_version: int
    calling_number_id: str              # PhoneNumber._id
    calling_number: str                 # E.164 — denormalized for workers

    # Lead targeting
    lead_filter: dict[str, Any] = Field(default_factory=dict)  # MongoDB query fragment
    campaign_id_filter: Optional[str] = None  # limit to leads tagged with this campaign

    # Concurrency / pace
    max_concurrent_calls: int = 1
    calls_per_minute: int = 10          # rate limiting

    # Calling hours (interpreted in timezone)
    timezone: str = "Asia/Kolkata"
    calling_hours: CallingHours = Field(default_factory=CallingHours)

    # Retry
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)

    # Schedule
    scheduled_at: Optional[datetime] = None   # None = start immediately on "start"

    # Status
    status: str = "draft"

    # Runtime counters (updated as campaign runs)
    total_leads: int = 0
    leads_dialed: int = 0
    leads_connected: int = 0
    leads_completed: int = 0

    # Timestamps
    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    # Who
    created_by: Optional[str] = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in CAMPAIGN_STATUSES:
            raise ValueError(f"Invalid campaign status: {v}")
        return v

    @field_validator("max_concurrent_calls")
    @classmethod
    def concurrency_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_concurrent_calls must be >= 1")
        return v

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    @property
    def can_pause(self) -> bool:
        return self.status in PAUSABLE_STATUSES

    @property
    def can_resume(self) -> bool:
        return self.status in ("paused", "paused_low_credits")

    @property
    def can_cancel(self) -> bool:
        return self.status not in TERMINAL_STATUSES
