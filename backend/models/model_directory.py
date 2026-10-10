"""MongoDB document models for the AI Models Directory.

Three collections:
  ai_model_catalogue      — static metadata about known AI models
  provider_configurations — per-capability provider activation records
  provider_credentials    — encrypted API keys (Fernet)
"""

from datetime import datetime
from typing import Any

from pydantic import Field

from backend.models.base import TimestampedModel, new_id


class AIModelCatalogue(TimestampedModel):
    """One entry per (provider_name, model_id) in the catalogue."""

    id: str = Field(default_factory=new_id, alias="_id")

    provider_name: str
    model_id: str
    capability: str  # 'tts' | 'stt' | 'llm'
    hosting_mode: str  # 'managed_api' | 'local_runtime' | 'self_hosted'
    supported_languages: list[str] = Field(default_factory=list)
    streaming_supported: bool = False
    credential_requirements: list[str] = Field(default_factory=list)
    setup_requirements: str = ""
    license_spdx: str = ""
    commercial_use_allowed: bool = False
    free_tier_info: dict[str, Any] | None = None
    free_tier_verified_date: str | None = None
    pricing_per_minute_usd: float | None = None
    doc_url: str = ""
    model_card_url: str | None = None
    implementation_status: str = "unavailable"  # 'supported' | 'experimental' | 'unavailable'
    notes: str | None = None


class ProviderConfiguration(TimestampedModel):
    """A configured provider/model for a given capability (tts/stt/llm)."""

    id: str = Field(default_factory=new_id, alias="_id")

    org_id: str | None = None  # None = platform-level config
    capability: str  # 'tts' | 'stt' | 'llm'
    provider_name: str
    model_id: str
    is_active: bool = False
    is_fallback: bool = False
    voice: str | None = None
    language: str | None = None
    extra_params: dict[str, Any] = Field(default_factory=dict)
    last_tested_at: datetime | None = None
    last_test_result: str | None = None  # 'ok' | 'error' | 'unavailable'
    last_test_latency_ms: int | None = None
    activated_at: datetime | None = None


class ProviderCredential(TimestampedModel):
    """Fernet-encrypted credential for a provider.

    Multiple rows per provider_name are allowed (rotation history). Only
    entries where rotated_at is None are considered current.
    """

    id: str = Field(default_factory=new_id, alias="_id")

    provider_name: str
    encrypted_value: bytes  # Fernet token — never returned to browser
    key_hint: str  # last 4 chars of the plaintext
    created_by: str  # user_id of who created/rotated this credential
    rotated_at: datetime | None = None  # set when superseded by a new credential
