"""Lead and DNC models.

Leads are org-scoped (organization_id on every document).
Tenant isolation is enforced at every query.

Lead statuses:
  new           → imported, not yet contacted
  scheduled     → call scheduled
  calling       → call in progress
  contacted     → spoke to lead but not yet qualified
  qualified     → meets qualification criteria
  not_interested → explicitly declined
  callback      → requested callback at a later time
  dnc           → added to DNC list
  failed        → multiple failed attempts, no contact

DNC = Do Not Call. Organization-scoped.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from backend.models.base import TimestampedModel, new_id, utcnow

LEAD_STATUSES = {
    "new", "scheduled", "calling", "contacted",
    "qualified", "not_interested", "callback", "dnc", "failed",
}


class Lead(TimestampedModel):
    """A single lead record owned by an organization."""

    organization_id: str
    campaign_id: Optional[str] = None       # set when added to a campaign

    # Contact info
    phone: str                              # E.164 format or local — normalized on import
    name: Optional[str] = None
    email: Optional[str] = None

    # Status
    status: str = "new"

    # Qualification
    score: int = 0
    qualification: dict[str, Any] = Field(default_factory=dict)   # extracted slot values

    # Custom fields (business-specific)
    custom_fields: dict[str, Any] = Field(default_factory=dict)

    # Call tracking
    attempts: int = 0
    last_contact_at: Optional[datetime] = None
    next_contact_at: Optional[datetime] = None

    # Source
    source: str = "import"                  # import | api | manual | webhook
    tags: list[str] = Field(default_factory=list)

    # Import metadata
    import_batch_id: Optional[str] = None   # groups leads from same import
    original_row: Optional[int] = None      # row number in source file

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in LEAD_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Valid: {LEAD_STATUSES}")
        return v

    @field_validator("phone")
    @classmethod
    def phone_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("phone cannot be empty")
        return v


class DNCEntry(TimestampedModel):
    """Do Not Call entry — organization-scoped.

    Unique constraint: (organization_id, phone).
    Once added, this phone number must never be called again by this org.
    """
    organization_id: str
    phone: str                              # normalized E.164
    reason: Optional[str] = None
    added_by: Optional[str] = None          # user_id or "system" (caller opt-out)
    source: str = "manual"                  # manual | opt_out | import
    added_at: datetime = Field(default_factory=utcnow)
