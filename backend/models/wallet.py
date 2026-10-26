"""Wallet, credit ledger, credit lots, and calling pack models.

KEY RULES:
- 1 credit = 1 billable second (integer, never float)
- All monetary values in integer paise
- Every credit movement requires an immutable WalletTransaction ledger entry
- Wallet available_credits + reserved_credits must always be ≥ 0
- CreditLot tracks expiry; FIFO consumption order
- CallingPacks are platform-managed; customers buy packs to get credits

Wallet balance:
  available_credits — credits ready to use
  reserved_credits  — credits held for in-progress calls (not yet consumed)
  total = available + reserved

Operations that generate ledger entries:
  purchase      — buying a calling pack
  bonus         — free credits granted by platform
  reserve       — holding credits for an active call
  release       — returning reserved credits (call cancelled/failed before billing)
  consume       — finalizing credit usage after call completes
  refund        — returning consumed credits (disputed charge, admin action)
  expiry        — credits removed when a lot expires
  admin_adjustment — manual platform admin credit grant or deduction
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from backend.models.base import TimestampedModel, new_id, utcnow


# ---------------------------------------------------------------------------
# CallingPack — platform-managed pack definition
# ---------------------------------------------------------------------------
class CallingPack(TimestampedModel):
    """A calling credit pack offered for purchase."""

    name: str                           # e.g. "Starter Pack"
    slug: str                           # unique, url-safe
    description: str = ""

    credits: int                        # number of credits (= billable seconds) in this pack
    price_paise: int                    # price in integer paise (never float)
    currency: str = "INR"
    validity_days: int = 365            # credits expire N days after purchase (0 = never)

    is_active: bool = True
    is_public: bool = True
    sort_order: int = 0

    # Bonus credits on purchase (e.g. 10% extra on large packs)
    bonus_credits: int = 0

    @field_validator("credits", "price_paise", "bonus_credits")
    @classmethod
    def non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Value must be non-negative integer")
        return v

    @field_validator("credits")
    @classmethod
    def credits_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("credits must be positive")
        return v

    @property
    def total_credits(self) -> int:
        """Base + bonus credits."""
        return self.credits + self.bonus_credits

    @property
    def price_inr(self) -> float:
        return self.price_paise / 100

    @property
    def cost_per_credit_paise(self) -> float:
        """Platform cost analysis only — not exposed to customers."""
        if self.total_credits == 0:
            return 0.0
        return self.price_paise / self.total_credits


# ---------------------------------------------------------------------------
# Wallet — one per organization
# ---------------------------------------------------------------------------
class Wallet(TimestampedModel):
    """Organization wallet. Always one per org."""

    organization_id: str

    # Integer credits only — never float
    available_credits: int = 0
    reserved_credits: int = 0

    # Lifetime totals for analytics
    total_purchased: int = 0
    total_consumed: int = 0
    total_expired: int = 0
    total_bonus: int = 0

    # Low credit alert threshold (driven by org settings)
    low_credit_threshold: int = 100

    @property
    def total_credits(self) -> int:
        return self.available_credits + self.reserved_credits

    @field_validator("available_credits", "reserved_credits")
    @classmethod
    def must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Credit values must be non-negative")
        return v


# ---------------------------------------------------------------------------
# WalletTransaction — immutable ledger entry
# ---------------------------------------------------------------------------
TRANSACTION_TYPES = {
    "purchase",         # buying a calling pack
    "bonus",            # free credits from platform
    "reserve",          # hold credits for active call
    "release",          # return reserved credits
    "consume",          # finalize usage after call
    "refund",           # return consumed credits
    "expiry",           # remove expired credits
    "admin_adjustment", # manual platform admin action
}


class WalletTransaction(TimestampedModel):
    """Immutable ledger record. Never updated after creation."""

    organization_id: str
    wallet_id: str

    transaction_type: str           # one of TRANSACTION_TYPES
    credits_delta: int              # positive = credit in; negative = credit out
    # Which bucket changes
    available_delta: int = 0        # change to available_credits
    reserved_delta: int = 0         # change to reserved_credits

    # Running balance after this transaction
    balance_after: int = 0          # available_credits after this transaction

    # Context
    description: str = ""
    call_id: Optional[str] = None   # for reserve/release/consume
    order_id: Optional[str] = None  # for purchase
    credit_lot_id: Optional[str] = None
    idempotency_key: Optional[str] = None   # prevents double-posting

    # Who
    created_by: Optional[str] = None  # user_id for admin adjustments

    @field_validator("transaction_type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        if v not in TRANSACTION_TYPES:
            raise ValueError(f"Invalid transaction_type: {v}. Valid: {TRANSACTION_TYPES}")
        return v


# ---------------------------------------------------------------------------
# CreditLot — tracks individual purchase batches for expiry
# ---------------------------------------------------------------------------
class CreditLot(TimestampedModel):
    """A batch of credits from a single purchase or grant.
    Consumed FIFO by billing. Expires after validity_days from purchase.
    """

    organization_id: str
    wallet_id: str
    transaction_id: str             # the WalletTransaction that created this lot

    original_credits: int           # credits granted when purchased/bonused
    remaining_credits: int          # credits not yet consumed from this lot
    reserved_from_lot: int = 0      # credits currently reserved from this lot

    source: str = "purchase"        # "purchase" | "bonus" | "admin_adjustment"
    order_id: Optional[str] = None
    calling_pack_id: Optional[str] = None

    # Expiry (UTC)
    purchased_at: datetime = Field(default_factory=utcnow)
    expires_at: Optional[datetime] = None   # None = never expires

    is_active: bool = True          # False once fully consumed or expired

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        now = utcnow()
        exp = self.expires_at
        # Handle mongomock returning naive datetimes
        if exp.tzinfo is None:
            from datetime import timezone
            exp = exp.replace(tzinfo=timezone.utc)
        return now >= exp

    @property
    def available_from_lot(self) -> int:
        return self.remaining_credits - self.reserved_from_lot
