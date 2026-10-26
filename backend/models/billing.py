"""Billing models: Order, Payment, Invoice, WebhookEvent.

ALL monetary amounts are stored as INTEGER PAISE. Never float.
1 INR = 100 paise.

Order lifecycle:
  created → pending_payment → paid → failed | refunded

Payment is immutable after creation (financial ledger record).
Invoice is generated after payment confirmation.
WebhookEvent tracks every provider webhook for idempotency.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from backend.models.base import DocumentModel, TimestampedModel, new_id, utcnow


# ---------------------------------------------------------------------------
# Order — created server-side before payment
# ---------------------------------------------------------------------------
class Order(TimestampedModel):
    """An order created before payment. Tracks what the customer is buying."""

    organization_id: str

    # What is being purchased
    order_type: str                     # "subscription" | "calling_pack" | "addon"
    plan_id: Optional[str] = None       # for subscription orders
    calling_pack_id: Optional[str] = None
    description: str = ""

    # Pricing (integer paise)
    amount_paise: int                   # total amount to charge
    currency: str = "INR"
    tax_paise: int = 0                  # GST (18%)
    discount_paise: int = 0

    # Provider linkage
    provider: str = "razorpay"          # "razorpay" | "mock"
    provider_order_id: Optional[str] = None    # Razorpay order_id
    provider_metadata: dict = Field(default_factory=dict)

    # Status
    status: str = "created"            # created | pending_payment | paid | failed | refunded

    # Links
    payment_id: Optional[str] = None   # our Payment doc id
    invoice_id: Optional[str] = None

    # User context
    created_by: Optional[str] = None   # user_id

    @field_validator("amount_paise", "tax_paise", "discount_paise")
    @classmethod
    def must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Amount fields must be non-negative paise integers")
        return v

    @property
    def amount_inr(self) -> float:
        """Display only — never use for billing calculations."""
        return self.amount_paise / 100


# ---------------------------------------------------------------------------
# Payment — immutable financial record
# ---------------------------------------------------------------------------
class Payment(TimestampedModel):
    """Immutable record of a completed payment. Never updated after creation."""

    organization_id: str
    order_id: str                       # our Order doc id

    # Amounts (integer paise)
    amount_paise: int
    currency: str = "INR"
    refunded_paise: int = 0

    # Provider
    provider: str = "razorpay"
    provider_payment_id: Optional[str] = None   # Razorpay payment_id
    provider_order_id: Optional[str] = None
    provider_signature: Optional[str] = None    # stored for audit
    provider_metadata: dict = Field(default_factory=dict)

    # Status
    status: str = "captured"           # captured | failed | refunded | partially_refunded

    # Context
    paid_at: datetime = Field(default_factory=utcnow)
    description: str = ""
    created_by: Optional[str] = None

    @field_validator("amount_paise", "refunded_paise")
    @classmethod
    def non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Amount must be non-negative paise integer")
        return v

    @property
    def amount_inr(self) -> float:
        return self.amount_paise / 100


# ---------------------------------------------------------------------------
# Invoice — generated after payment
# ---------------------------------------------------------------------------
class Invoice(TimestampedModel):
    """Invoice generated after a successful payment."""

    organization_id: str
    order_id: str
    payment_id: str

    # Invoice number: INV-{year}-{sequential}
    invoice_number: str

    # Line items
    description: str
    subtotal_paise: int                 # before tax
    tax_paise: int = 0                  # GST amount
    total_paise: int                    # subtotal + tax

    currency: str = "INR"
    status: str = "issued"             # issued | void

    # Org billing details (snapshot at invoice time)
    org_name: str = ""
    org_email: str = ""
    org_gstin: Optional[str] = None
    org_address: Optional[str] = None

    # Dates
    issued_at: datetime = Field(default_factory=utcnow)
    due_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None

    @property
    def total_inr(self) -> float:
        return self.total_paise / 100


# ---------------------------------------------------------------------------
# WebhookEvent — idempotency guard for provider webhooks
# ---------------------------------------------------------------------------
class WebhookEvent(DocumentModel):
    """Every inbound provider webhook is recorded for idempotency.

    Unique index: (provider, event_id) — prevents double-processing.
    """

    provider: str                       # "razorpay" | "mock"
    event_id: str                       # provider's event ID
    event_type: str                     # e.g. "payment.captured"
    payload: dict = Field(default_factory=dict)

    # Processing state
    processed: bool = False
    processed_at: Optional[datetime] = None
    processing_result: Optional[dict] = None
    error_message: Optional[str] = None

    # Received at
    received_at: datetime = Field(default_factory=utcnow)

    # Raw signature for audit
    signature: Optional[str] = None
