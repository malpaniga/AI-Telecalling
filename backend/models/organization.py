"""Organization model — the top-level tenant unit.

Every customer is an organization. All data is scoped by organization_id.
"""

from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field

from backend.models.base import TimestampedModel, utcnow


class OrganizationSettings(TimestampedModel):
    """Mutable settings nested inside an organization."""
    # Calling rules
    calling_hours_start: str = "09:00"   # HH:MM local time
    calling_hours_end: str = "19:00"
    timezone: str = "Asia/Kolkata"
    max_daily_calls_per_lead: int = 3
    retry_delay_hours: int = 24

    # Compliance
    dnc_enabled: bool = True

    # Notifications
    low_credit_threshold: int = 100   # credits remaining to trigger alert


class Organization(TimestampedModel):
    """Represents a customer organization (tenant)."""
    name: str
    slug: str                           # URL-safe unique identifier
    email: str                          # primary billing email
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "IN"
    gstin: Optional[str] = None         # GST number for Indian billing

    # Status
    status: str = "active"              # active | suspended | cancelled
    is_verified: bool = False

    # Limits driven by subscription
    max_concurrent_calls: int = 1
    max_campaigns: int = 1
    max_agents: int = 1
    max_leads_per_campaign: int = 500

    # Settings
    settings: OrganizationSettings = Field(default_factory=OrganizationSettings)

    # Internal metadata
    created_by: Optional[str] = None    # platform admin user_id
    suspended_at: Optional[datetime] = None
    suspended_reason: Optional[str] = None


class OrganizationCreate(TimestampedModel):
    """Input schema for creating an organization (used by signup)."""
    name: str
    slug: str
    email: str
    phone: Optional[str] = None


class OrganizationPublic(TimestampedModel):
    """Safe organization response (no sensitive internal fields)."""
    name: str
    slug: str
    email: str
    phone: Optional[str] = None
    status: str
    is_verified: bool
    max_concurrent_calls: int
    created_at: datetime
