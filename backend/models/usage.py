"""Usage and provider cost models.

CRITICAL SEPARATION:
  customer_charge_paise  — what the customer pays (from credits)
  provider_cost_paise    — what the platform pays the provider
  gross_profit_paise     — customer_charge - provider_cost

Customer API responses NEVER include provider_cost_paise or gross_margin.
Admin API includes all fields.

All monetary values in integer paise. Never float.

UsageEvent:
  One per call, per message, per number rental, etc.
  Records BOTH customer charge and provider cost.
  Used for: billing reconstruction, dispute resolution, analytics.

ProviderUsage:
  Granular per-call provider breakdown (telephony, STT, LLM, TTS).
  Used for: cost analysis, provider health, routing decisions.
  ADMIN ONLY.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from backend.models.base import DocumentModel, utcnow


class UsageEvent(DocumentModel):
    """One billable usage event. Immutable after creation."""

    organization_id: str
    call_id: Optional[str] = None
    campaign_id: Optional[str] = None

    # Event classification
    event_type: str                     # call_completed | sms_sent | whatsapp_sent
                                        # number_rental | addon_purchase
    description: str = ""

    # Billing (integer paise)
    customer_charge_paise: int = 0      # what org is charged (credits × rate)
    credits_consumed: int = 0           # calling credits used

    # Provider cost (ADMIN ONLY — never in customer responses)
    provider_cost_paise: int = 0        # what platform pays provider
    provider: Optional[str] = None      # which provider (telephony/STT/etc.)

    # Derived (computed on read, not stored as float)
    # gross_profit = customer_charge - provider_cost  → computed
    # gross_margin = gross_profit / customer_charge   → computed

    # Duration
    duration_s: Optional[int] = None

    # Idempotency
    idempotency_key: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)

    @field_validator("customer_charge_paise", "provider_cost_paise", "credits_consumed")
    @classmethod
    def non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Usage amounts must be non-negative")
        return v

    @property
    def gross_profit_paise(self) -> int:
        return self.customer_charge_paise - self.provider_cost_paise

    @property
    def gross_margin_pct(self) -> Optional[float]:
        if self.customer_charge_paise == 0:
            return None
        return round(self.gross_profit_paise / self.customer_charge_paise * 100, 2)


class ProviderUsage(DocumentModel):
    """Per-call provider cost breakdown. ADMIN ONLY."""

    organization_id: str
    call_id: str

    # Per-layer costs (integer paise)
    telephony_cost_paise: int = 0       # Twilio/Exotel per-minute
    stt_cost_paise: int = 0             # Sarvam/Groq per-second
    llm_cost_paise: int = 0             # OpenAI/Groq per-token
    tts_cost_paise: int = 0             # ElevenLabs/Sarvam per-char

    # Provider names (for routing/health analysis)
    telephony_provider: Optional[str] = None
    stt_provider: Optional[str] = None
    llm_provider: Optional[str] = None
    tts_provider: Optional[str] = None

    # Consumption metrics
    duration_s: Optional[int] = None
    stt_seconds: int = 0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    tts_characters: int = 0

    @property
    def total_provider_cost_paise(self) -> int:
        return (self.telephony_cost_paise + self.stt_cost_paise
                + self.llm_cost_paise + self.tts_cost_paise)

    created_at: datetime = Field(default_factory=utcnow)
