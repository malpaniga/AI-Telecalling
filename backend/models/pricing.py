"""MongoDB document models for provider pricing, FX rates, and rate cards.

Tracks live vendor rates, daily USD/INR FX conversions, turn-taking distributions,
and loss-protection safety margins.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import Field

from backend.models.base import TimestampedModel, new_id, utcnow


class ProviderRateCard(TimestampedModel):
    """Stores the effective cost and billable rate for a provider/model."""

    id: str = Field(default_factory=new_id, alias="_id")

    provider_name: str
    model_id: str
    capability: str  # 'stt' | 'llm' | 'tts' | 'telephony'
    display_name: str = ""

    # Base pricing
    base_currency: str = "INR"  # 'INR' | 'USD'
    billing_unit: str = "audio_minute"  # 'audio_minute' | '1k_characters' | '1m_tokens_input' | '1m_tokens_output' | 'pstn_minute' | 'runtime'
    base_unit_rate: float = 0.0

    # FX conversion
    fx_rate_usd_inr: float = 84.85
    effective_unit_rate_inr: float = 0.0

    # Per-second derivatives
    active_cost_per_sec_inr: float = 0.0  # Cost per second of active audio/synthesis
    blended_cost_per_sec_inr: float = 0.0  # Turn-taking blended cost per call-second

    # Loss prevention & retail pricing
    safety_margin_pct: float = 15.0  # Loss protection buffer markup (default 15%)
    retail_rate_per_sec_inr: float = 0.0  # Billed rate = blended * (1 + margin)

    # Sync metadata
    last_synced_at: datetime = Field(default_factory=utcnow)
    sync_source: str = "daily_auto_sync"  # 'daily_auto_sync' | 'admin_override' | 'published_rate_card'
    notes: Optional[str] = None


class PricingSettings(TimestampedModel):
    """Global platform pricing and loss-protection settings."""

    id: str = Field(default="global_pricing_settings", alias="_id")

    usd_to_inr_fx_rate: float = 84.85
    fx_last_updated_at: datetime = Field(default_factory=utcnow)
    default_safety_margin_pct: float = 15.0
    min_retail_paise_per_sec: float = 1.0
    auto_sync_enabled: bool = True
    last_daily_sync_at: Optional[datetime] = None
