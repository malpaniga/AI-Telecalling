"""Agent, AgentVersion, BusinessTemplate repositories."""

import logging
from typing import Any, Optional

from pymongo import ASCENDING, DESCENDING

from backend.models.base import new_id, utcnow
from backend.models.agent import Agent, AgentVersion, BusinessTemplate
from backend.repositories.base import BaseRepository

log = logging.getLogger("repo.agent")


class BusinessTemplateRepository(BaseRepository):
    collection_name = "business_templates"
    model_class = BusinessTemplate

    async def upsert(
        self,
        slug: str,
        name: str,
        description: str = "",
        configuration: Optional[dict] = None,
        slot_definitions: Optional[list] = None,
    ) -> BusinessTemplate:
        existing = await self.find_one({"slug": slug})
        if existing:
            return existing
        tmpl = BusinessTemplate(
            _id=new_id(),
            slug=slug,
            name=name,
            description=description,
            configuration=configuration or {},
            slot_definitions=slot_definitions or [],
        )
        await self.insert(tmpl)
        return tmpl

    async def list_active(self) -> list[BusinessTemplate]:
        return await self.find_many({"is_active": True}, sort=[("name", ASCENDING)])

    async def find_by_slug(self, slug: str) -> Optional[BusinessTemplate]:
        return await self.find_one({"slug": slug})


class AgentRepository(BaseRepository):
    collection_name = "agents"
    model_class = Agent

    async def create(
        self,
        organization_id: str,
        name: str,
        template_slug: str,
        voice_profile_id: str,
        voice_profile_version: int,
        description: str = "",
    ) -> Agent:
        agent = Agent(
            _id=new_id(),
            organization_id=organization_id,
            name=name,
            description=description,
            template_slug=template_slug,
            voice_profile_id=voice_profile_id,
            voice_profile_version=voice_profile_version,
        )
        await self.insert(agent)
        log.info("agent created id=%s org=%s name=%s", agent.id, organization_id, name)
        return agent

    async def list_for_org(self, organization_id: str) -> list[Agent]:
        return await self.find_many(
            {"organization_id": organization_id, "is_active": True},
            sort=[("created_at", DESCENDING)],
        )

    async def get_for_org(self, agent_id: str, organization_id: str) -> Optional[Agent]:
        """Get agent only if it belongs to this org (tenant isolation)."""
        return await self.find_one({
            "_id": agent_id,
            "organization_id": organization_id,
            "is_active": True,
        })

    async def set_active_version(
        self, agent_id: str, version: int, version_id: str
    ) -> bool:
        return await self.update_by_id(agent_id, {
            "active_version": version,
            "active_version_id": version_id,
        })

    async def deactivate(self, agent_id: str) -> bool:
        return await self.update_by_id(agent_id, {"is_active": False})


class AgentVersionRepository(BaseRepository):
    collection_name = "agent_versions"
    model_class = AgentVersion

    async def next_version_number(self, agent_id: str) -> int:
        existing = await self.find_many(
            {"agent_id": agent_id},
            sort=[("version", DESCENDING)],
            limit=1,
        )
        return (existing[0].version if existing else 0) + 1

    async def create_version(
        self,
        agent_id: str,
        configuration: dict[str, Any],
        description: str = "",
    ) -> AgentVersion:
        version_number = await self.next_version_number(agent_id)
        version = AgentVersion(
            _id=new_id(),
            agent_id=agent_id,
            version=version_number,
            configuration=configuration,
            description=description,
            status="draft",
        )
        await self.insert(version)
        return version

    async def publish_version(self, version_id: str) -> bool:
        """Mark a version as published (immutable after this)."""
        return await self.update_by_id(version_id, {"status": "published"})

    async def update_draft(
        self, version_id: str, configuration: dict[str, Any]
    ) -> Optional[AgentVersion]:
        """Update draft configuration. Raises if already published."""
        version = await self.find_by_id(version_id)
        if version is None:
            raise ValueError("Agent version not found")
        if version.status == "published":
            raise ValueError("Published agent versions are immutable. Create a new version.")
        await self.update_by_id(version_id, {"configuration": configuration})
        return await self.find_by_id(version_id)

    async def list_for_agent(self, agent_id: str) -> list[AgentVersion]:
        return await self.find_many(
            {"agent_id": agent_id},
            sort=[("version", DESCENDING)],
        )

    async def get_for_agent(
        self, agent_id: str, version_number: int
    ) -> Optional[AgentVersion]:
        return await self.find_one({
            "agent_id": agent_id,
            "version": version_number,
        })
