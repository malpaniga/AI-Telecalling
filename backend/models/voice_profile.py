"""Voice profile models.

CORE ABSTRACTION — the most important thing in the whole system:
  Customer selects: "Marathi AI Voice"
  Platform internally decides: Telephony, STT, LLM, TTS, provider, voice IDs

Customer API NEVER exposes:
  - provider names (ElevenLabs, Sarvam, OpenAI, Twilio, Exotel)
  - provider resource IDs (voice IDs, model names, API keys)
  - provider costs
  - internal routing configuration
  - route version internals

Versioning:
  VoiceProfile      — the customer-facing object (display_name, language)
  VoiceProfileVersion — immutable snapshot of the internal route configuration.
    Once published, a version is NEVER modified. Changing a provider route
    creates a new version. Active campaigns pin a version_id so provider
    changes don't affect running campaigns.

ProviderRoute (embedded in VoiceProfileVersion.routes):
  Stores which provider handles each layer (telephony, stt, llm, tts) and
  the provider-specific resource IDs. This entire structure is ADMIN-ONLY.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from backend.models.base import TimestampedModel, new_id, utcnow


class ProviderRoute(TimestampedModel):
    """Internal provider route for one layer of a voice profile version.
    NEVER included in customer API responses.
    """
    provider_type: str          # telephony | stt | llm | tts
    provider: str               # e.g. elevenlabs | sarvam | openai | twilio | exotel | mock
    provider_resource_id: Optional[str] = None  # e.g. voice ID, model name
    provider_model: Optional[str] = None        # e.g. "bulbul:v3", "gpt-4o-mini"
    provider_language: Optional[str] = None     # provider-specific language code
    provider_metadata: dict = Field(default_factory=dict)

    # Fallback provider (used if primary fails)
    fallback_provider: Optional[str] = None
    fallback_resource_id: Optional[str] = None

    # Cost tracking (admin only, never customer-facing)
    estimated_cost_per_second_paise: int = 0

    is_active: bool = True


class VoiceProfileVersion(TimestampedModel):
    """Immutable snapshot of a voice profile's provider configuration.

    Once published, this document is NEVER modified.
    Campaigns pin a specific version_id; provider changes create new versions.

    The `routes` dict keys are provider_type values:
      routes = {
        "telephony": ProviderRoute(...),
        "stt": ProviderRoute(...),
        "llm": ProviderRoute(...),
        "tts": ProviderRoute(...),
      }
    This entire structure is ADMIN-ONLY.
    """
    voice_profile_id: str
    version: int                # monotonically increasing per profile
    description: str = ""       # admin notes about this version (e.g. "Switched to ElevenLabs")

    # Internal routing — ADMIN ONLY, never in customer responses
    routes: dict[str, Any] = Field(default_factory=dict)

    is_published: bool = True
    published_at: datetime = Field(default_factory=utcnow)
    deprecated_at: Optional[datetime] = None   # when a newer version supersedes this


class VoiceProfile(TimestampedModel):
    """Customer-facing voice profile object.

    The customer sees only: id, display_name, language, status.
    All internal routing is hidden in VoiceProfileVersion.routes.
    """
    display_name: str           # "Marathi AI Voice" — what customer sees
    language: str               # BCP-47 e.g. "mr-IN", "hi-IN", "en-IN"
    description: str = ""       # customer-facing description
    avatar_url: Optional[str] = None

    # Scope
    organization_id: Optional[str] = None  # None = platform-shared (all orgs can use)
    is_platform: bool = True               # True = available to all orgs

    # Status
    is_active: bool = True

    # Active version reference
    active_version: Optional[int] = None        # current published version number
    active_version_id: Optional[str] = None     # _id of active VoiceProfileVersion
