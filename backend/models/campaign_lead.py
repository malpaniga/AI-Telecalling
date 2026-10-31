"""CampaignLead junction model.

Represents enrollment of a Lead in a specific Campaign.
Decouples contact-level attributes from campaign-level dialing lifecycle,
enabling the same contact to participate in multiple independent campaigns.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from backend.models.base import TimestampedModel, new_id, utcnow

CAMPAIGN_LEAD_STATUSES = {
    "new", "scheduled", "calling", "contacted",
    "qualified", "not_interested", "callback", "dnc", "failed",
}


class CampaignLead(TimestampedModel):
    """Enrollment of a Lead in a specific Campaign."""

    organization_id: str
    campaign_id: str
    lead_id: str
    phone: str                          # Denormalized for worker performance
    status: str = "new"                 # new | scheduled | calling | contacted | qualified | callback | not_interested | failed | dnc
    attempts: int = 0
    max_attempts: int = 3
    last_called_at: Optional[datetime] = None
    next_attempt_at: Optional[datetime] = None
    call_id: Optional[str] = None
    disposition: Optional[str] = None
    notes: Optional[str] = None
    # Scoped variables specifically for this campaign execution
    custom_fields: dict[str, Any] = Field(default_factory=dict)

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in CAMPAIGN_LEAD_STATUSES:
            raise ValueError(f"Invalid campaign lead status: {v}")
        return v
