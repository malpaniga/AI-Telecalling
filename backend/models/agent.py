"""Agent builder models.

An Agent is an AI calling agent configuration tied to a business template.
Agents are versioned — active campaigns pin a specific agent version.

Business templates provide the generic structure; they are NOT business-specific
code. Solar, real-estate, etc. are configuration/prompt templates, not code paths.

Agent configuration (stored in AgentVersion.configuration):
  {
    "goal": "Qualify solar leads",
    "tone": "warm_professional",
    "greeting": "Hi, this is {agent_name} from {company_name}...",
    "primary_language": "en-IN",
    "fallback_languages": ["hi-IN"],
    "qualification_schema": [...slots...],
    "objection_handlers": [...],
    "calling_rules": {...},
    "transfer_rules": {...},
    "knowledge_base_ids": [...],
    "tool_configs": {...},
  }
"""

from typing import Any, Optional
from pydantic import Field
from backend.models.base import TimestampedModel


class BusinessTemplate(TimestampedModel):
    """A generic business template (Solar, Real Estate, Collections, etc.).
    Configuration-driven — not special code paths.
    """
    slug: str                                   # e.g. "solar", "real-estate"
    name: str                                   # e.g. "Solar Energy"
    description: str = ""
    category: str = "Lead qualification"        # "Lead qualification", "Collections", "Reminder", "Recovery"
    icon_color: str = "blue"                    # "blue", "green", "orange", "red", "gold"
    # Default configuration values for agents using this template
    configuration: dict[str, Any] = Field(default_factory=dict)
    # Qualification slot definitions for this template
    slot_definitions: list[dict[str, Any]] = Field(default_factory=list)
    is_active: bool = True


# Built-in template slugs
TEMPLATE_SLUGS = [
    "generic",
    "solar",
    "real-estate",
    "insurance",
    "education",
    "home-services",
    "automotive",
]


class Agent(TimestampedModel):
    """Customer-owned AI calling agent."""
    organization_id: str
    name: str                                   # e.g. "Solar Lead Qualifier"
    description: str = ""
    template_slug: str                          # references BusinessTemplate.slug

    # Voice profile linkage (customer-facing IDs only)
    voice_profile_id: str
    voice_profile_version: int

    # Active configuration version
    active_version: Optional[int] = None
    active_version_id: Optional[str] = None

    is_active: bool = True


class AgentVersion(TimestampedModel):
    """Immutable-once-published snapshot of an agent's configuration."""
    agent_id: str
    version: int
    configuration: dict[str, Any] = Field(default_factory=dict)
    # draft → published (published = immutable)
    status: str = "draft"
    description: str = ""
