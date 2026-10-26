"""Subscription plan and subscription models.

KEY RULES:
- All prices stored as INTEGER PAISE (1 INR = 100 paise). Never float.
- Plans are database-driven. Changing a plan changes behaviour with zero code changes.
- Subscriptions are org-scoped; one active subscription per org.
- Entitlements are derived from the plan at runtime; never stored flat on the org.

Plan features are a free-form dict so new feature gates can be added without
schema migrations:
  {
    "max_concurrent_calls": 3,
    "max_campaigns": 5,
    "max_agents": 10,
    "max_leads_per_campaign": 5000,
    "max_team_members": 10,
    "analytics_retention_days": 90,
    "knowledge_base_enabled": true,
    "api_access": false,
    "custom_voice_profiles": false,
    "priority_support": false,
  }
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from backend.models.base import TimestampedModel, new_id, utcnow


# ---------------------------------------------------------------------------
# SubscriptionPlan — platform-managed, applies to all organizations
# ---------------------------------------------------------------------------
class SubscriptionPlan(TimestampedModel):
    """A plan offered on the platform. Managed by platform admins only."""

    name: str                           # e.g. "Starter", "Growth", "Pro"
    slug: str                           # unique, url-safe e.g. "starter"
    description: str = ""

    # Pricing (integer paise — NEVER float)
    price_monthly_paise: int = 0        # monthly subscription price
    price_yearly_paise: int = 0         # yearly (may offer discount)

    # Entitlement limits
    max_concurrent_calls: int = 1
    max_campaigns: int = 1
    max_agents: int = 1
    max_leads_per_campaign: int = 500
    max_team_members: int = 3
    analytics_retention_days: int = 30

    # Feature flags
    knowledge_base_enabled: bool = False
    api_access: bool = False
    custom_voice_profiles: bool = False
    priority_support: bool = False
    white_label: bool = False

    # Free-form extras (for future feature gates without schema changes)
    features: dict[str, Any] = Field(default_factory=dict)

    # Admin controls
    is_active: bool = True              # inactive plans can't be purchased
    is_public: bool = True              # False = private/custom plan
    sort_order: int = 0                 # display ordering
    trial_days: int = 0                 # 0 = no trial

    @field_validator("price_monthly_paise", "price_yearly_paise")
    @classmethod
    def must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Price must be non-negative (integer paise)")
        return v

    @property
    def price_monthly_inr(self) -> float:
        """Convenience for display — never use for billing calculations."""
        return self.price_monthly_paise / 100

    @property
    def price_yearly_inr(self) -> float:
        return self.price_yearly_paise / 100


# ---------------------------------------------------------------------------
# Subscription — one per organization, tracks current plan + billing cycle
# ---------------------------------------------------------------------------
class Subscription(TimestampedModel):
    """An organization's active subscription to a plan."""

    organization_id: str
    plan_id: str
    plan_slug: str                      # denormalized for quick access

    # Billing cycle
    billing_cycle: str = "monthly"      # "monthly" | "yearly"
    status: str = "active"             # active | trialing | past_due | cancelled | expired

    # Dates (UTC)
    started_at: datetime = Field(default_factory=utcnow)
    current_period_start: datetime = Field(default_factory=utcnow)
    current_period_end: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_at_period_end: bool = False

    # Snapshot of plan limits at subscription time (so plan changes don't
    # retroactively affect active subscriptions mid-period)
    snapshot_max_concurrent_calls: int = 1
    snapshot_max_campaigns: int = 1
    snapshot_max_agents: int = 1
    snapshot_max_leads_per_campaign: int = 500
    snapshot_max_team_members: int = 3
    snapshot_features: dict[str, Any] = Field(default_factory=dict)

    # Payment linkage (filled after first payment)
    last_payment_id: Optional[str] = None
    last_payment_at: Optional[datetime] = None

    # Internal
    created_by: Optional[str] = None   # user_id that activated the subscription

    @property
    def is_active_or_trialing(self) -> bool:
        return self.status in ("active", "trialing")

    @property
    def is_in_grace(self) -> bool:
        return self.status == "past_due"


# ---------------------------------------------------------------------------
# EntitlementCheck — returned by the entitlement service
# ---------------------------------------------------------------------------
class EntitlementCheck:
    """Result of an entitlement check. Not stored in DB."""
    __slots__ = ("allowed", "reason", "limit", "current")

    def __init__(
        self,
        allowed: bool,
        reason: str = "",
        limit: Optional[int] = None,
        current: Optional[int] = None,
    ):
        self.allowed = allowed
        self.reason = reason
        self.limit = limit
        self.current = current

    def raise_if_denied(self) -> None:
        if not self.allowed:
            from fastapi import HTTPException
            raise HTTPException(status_code=402, detail=self.reason)
