"""Agent builder service.

Handles creation and management of AI calling agents and their versions.
Business templates are generic (Solar, Real Estate, etc. are configurations,
not code paths). No core business logic contains template-specific branches.
"""

import logging
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.agent import TEMPLATE_SLUGS, Agent, AgentVersion, BusinessTemplate
from backend.repositories.agent_repo import (
    AgentRepository,
    AgentVersionRepository,
    BusinessTemplateRepository,
)

log = logging.getLogger("service.agent")

# Default template configurations — generic scaffolding only
DEFAULT_TEMPLATES = [
    {
        "slug": "generic",
        "name": "Generic",
        "description": "Generic AI calling agent. Customise goal, tone and slots.",
        "configuration": {
            "goal": "Qualify leads and book appointments",
            "tone": "warm_professional",
            "stages": ["greeting", "qualification", "objection", "action", "end"],
        },
        "slot_definitions": [
            {"key": "name", "label": "Name", "required": False},
            {"key": "interest", "label": "Interest level", "required": False},
        ],
    },
    {
        "slug": "solar",
        "name": "Solar Energy",
        "description": "Solar lead qualification and appointment booking.",
        "configuration": {
            "goal": "Qualify homeowners for solar panel installation",
            "tone": "consultative",
            "stages": ["greeting", "qualification", "objection", "appointment", "end"],
        },
        "slot_definitions": [
            {"key": "monthly_bill", "label": "Monthly electricity bill", "required": True},
            {"key": "roof_type", "label": "Roof type", "required": True},
            {"key": "home_ownership", "label": "Owns/rents home", "required": True},
            {"key": "timeline", "label": "Decision timeline", "required": False},
        ],
    },
    {
        "slug": "real-estate",
        "name": "Real Estate",
        "description": "Real estate lead qualification.",
        "configuration": {
            "goal": "Qualify property buyers and book viewings",
            "tone": "warm_professional",
        },
        "slot_definitions": [
            {"key": "budget", "label": "Budget", "required": True},
            {"key": "timeline", "label": "Move-in timeline", "required": True},
            {"key": "city", "label": "Preferred city", "required": True},
            {"key": "property_type", "label": "Property type", "required": True},
        ],
    },
    {
        "slug": "insurance",
        "name": "Insurance",
        "description": "Insurance lead qualification.",
        "configuration": {"goal": "Qualify insurance prospects"},
        "slot_definitions": [
            {"key": "coverage_type", "label": "Coverage type", "required": True},
            {"key": "current_insurer", "label": "Current insurer", "required": False},
        ],
    },
    {
        "slug": "education",
        "name": "Education",
        "description": "Education admissions and lead qualification.",
        "configuration": {"goal": "Qualify prospective students"},
        "slot_definitions": [
            {"key": "course", "label": "Course interest", "required": True},
            {"key": "qualification", "label": "Current qualification", "required": False},
        ],
    },
    {
        "slug": "home-services",
        "name": "Home Services",
        "description": "Home services lead qualification and booking.",
        "configuration": {"goal": "Qualify and book home service appointments"},
        "slot_definitions": [
            {"key": "service_type", "label": "Service needed", "required": True},
            {"key": "location", "label": "Location", "required": True},
        ],
    },
    {
        "slug": "automotive",
        "name": "Automotive",
        "description": "Automotive sales lead qualification.",
        "configuration": {"goal": "Qualify car buyers"},
        "slot_definitions": [
            {"key": "vehicle_type", "label": "Vehicle type", "required": True},
            {"key": "budget", "label": "Budget", "required": False},
        ],
    },
]


async def seed_templates(db: AsyncIOMotorDatabase) -> list[BusinessTemplate]:
    """Seed default business templates. Idempotent."""
    repo = BusinessTemplateRepository(db)
    created = []
    for tmpl in DEFAULT_TEMPLATES:
        existing = await repo.find_by_slug(tmpl["slug"])
        if existing is None:
            result = await repo.upsert(**tmpl)
            created.append(result)
            log.info("seeded template: %s", tmpl["slug"])
    return created


class AgentService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.templates = BusinessTemplateRepository(db)
        self.agents = AgentRepository(db)
        self.versions = AgentVersionRepository(db)

    async def list_templates(self) -> list[BusinessTemplate]:
        return await self.templates.list_active()

    async def create_agent(
        self,
        organization_id: str,
        name: str,
        template_slug: str,
        voice_profile_id: str,
        voice_profile_version: int,
        description: str = "",
    ) -> Agent:
        # Validate template exists
        tmpl = await self.templates.find_by_slug(template_slug)
        if tmpl is None or not tmpl.is_active:
            raise ValueError(
                f"Business template '{template_slug}' not found. "
                f"Valid templates: {', '.join(TEMPLATE_SLUGS)}"
            )
        return await self.agents.create(
            organization_id=organization_id,
            name=name,
            template_slug=template_slug,
            voice_profile_id=voice_profile_id,
            voice_profile_version=voice_profile_version,
            description=description,
        )

    async def list_agents(self, organization_id: str) -> list[Agent]:
        return await self.agents.list_for_org(organization_id)

    async def get_agent(
        self, agent_id: str, organization_id: str
    ) -> Optional[Agent]:
        """Returns agent only if it belongs to this org (tenant isolation)."""
        return await self.agents.get_for_org(agent_id, organization_id)

    async def create_version(
        self,
        agent_id: str,
        organization_id: str,
        configuration: dict[str, Any],
        description: str = "",
        auto_activate: bool = False,
    ) -> AgentVersion:
        """Create a new draft version. Optionally publish and activate it."""
        agent = await self.agents.get_for_org(agent_id, organization_id)
        if agent is None:
            raise ValueError("Agent not found or does not belong to your organization")
        version = await self.versions.create_version(
            agent_id=agent_id,
            configuration=configuration,
            description=description,
        )
        if auto_activate:
            await self._publish_and_activate(agent_id, version)
        return version

    async def _publish_and_activate(
        self, agent_id: str, version: AgentVersion
    ) -> None:
        await self.versions.publish_version(version.id)
        await self.agents.set_active_version(agent_id, version.version, version.id)

    async def publish_version(
        self, agent_id: str, version_id: str, organization_id: str
    ) -> AgentVersion:
        """Publish a draft version and set it as active. Immutable after this."""
        agent = await self.agents.get_for_org(agent_id, organization_id)
        if agent is None:
            raise ValueError("Agent not found")
        version = await self.versions.find_by_id(version_id)
        if version is None or version.agent_id != agent_id:
            raise ValueError("Version not found")
        if version.status == "published":
            raise ValueError("Version is already published")
        await self._publish_and_activate(agent_id, version)
        return await self.versions.find_by_id(version_id)

    async def update_draft_version(
        self,
        version_id: str,
        organization_id: str,
        configuration: dict[str, Any],
    ) -> AgentVersion:
        """Update a draft version's configuration. Fails if already published."""
        version = await self.versions.find_by_id(version_id)
        if version is None:
            raise ValueError("Version not found")
        # Verify ownership via agent
        agent = await self.agents.get_for_org(version.agent_id, organization_id)
        if agent is None:
            raise ValueError("Agent not found or does not belong to your organization")
        return await self.versions.update_draft(version_id, configuration)

    async def list_versions(
        self, agent_id: str, organization_id: str
    ) -> list[AgentVersion]:
        agent = await self.agents.get_for_org(agent_id, organization_id)
        if agent is None:
            raise ValueError("Agent not found")
        return await self.versions.list_for_agent(agent_id)

    async def delete_agent(
        self, agent_id: str, organization_id: str
    ) -> bool:
        agent = await self.agents.get_for_org(agent_id, organization_id)
        if agent is None:
            raise ValueError("Agent not found")
        return await self.agents.deactivate(agent_id)
