"""Phone number inventory models.

IMPORTANT ABSTRACTION:
- Customers see: number (E.164), display_name, capabilities, status
- Customers NEVER see: provider, provider_resource_id, provider_metadata,
  provider_cost, internal routing

Phone numbers are platform resources. Organizations rent them.
One number can only be assigned to one organization at a time.

Statuses:
  available   — in inventory, not assigned
  reserved    — held during assignment process (brief window)
  assigned    — actively rented by an organization
  suspended   — temporarily disabled (non-payment, policy)
  released    — returned to pool (may be recycled)
  retired     — permanently removed from service
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from backend.models.base import TimestampedModel, new_id, utcnow


class PhoneNumber(TimestampedModel):
    """A phone number in the platform inventory."""

    # Customer-visible fields
    number: str                             # E.164 format, e.g. "+919876543210"
    display_name: Optional[str] = None      # Human label, e.g. "Mumbai DID"
    country_code: str = "IN"
    number_type: str = "local"              # local | toll_free | mobile | short_code

    # Capabilities (customer-visible)
    can_sms: bool = False
    can_voice: bool = True
    can_whatsapp: bool = False

    # Status
    status: str = "available"              # see docstring above
    organization_id: Optional[str] = None  # primary set when assigned (backward compatibility)
    assigned_org_ids: list[str] = Field(default_factory=list)  # multi-org assignment
    inbound_organization_id: Optional[str] = None  # org receiving inbound calls
    inbound_agent_id: Optional[str] = None  # optional specific agent for inbound calls

    # Monthly rental cost (in paise — for billing, NOT shown to customer)
    rental_paise_per_month: int = 0        # platform cost, never exposed

    # Internal provider details — NEVER in customer API responses
    provider: str = "mock"                  # twilio | exotel | mock
    provider_resource_id: Optional[str] = None  # e.g. Twilio SID
    provider_metadata: dict = Field(default_factory=dict)

    # Timestamps
    assigned_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    released_at: Optional[datetime] = None


class PhoneNumberAssignment(TimestampedModel):
    """Immutable record of a number assignment to an org. History tracking."""

    phone_number_id: str
    number: str                             # denormalized E.164 for easy querying
    organization_id: str

    action: str                             # assigned | released | suspended | reactivated
    performed_by: Optional[str] = None      # user_id

    # Monthly cost at time of assignment (internal, never exposed)
    rental_paise_per_month: int = 0

    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
