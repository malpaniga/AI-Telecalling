"""Agents API.

GET  /api/v1/agents/templates              — list available business templates
GET  /api/v1/agents                        — list org's agents
POST /api/v1/agents                        — create agent
GET  /api/v1/agents/{id}                   — get agent
DELETE /api/v1/agents/{id}                 — deactivate agent

POST /api/v1/agents/{id}/versions          — create version (draft)
GET  /api/v1/agents/{id}/versions          — list versions
POST /api/v1/agents/{id}/versions/{vid}/publish — publish + activate
PATCH /api/v1/agents/{id}/versions/{vid}   — update draft
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.services.agent_service import AgentService

log = logging.getLogger("api.agents")
router = APIRouter(prefix="/agents", tags=["agents"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class CreateAgentRequest(BaseModel):
    name: str
    template_slug: str
    voice_profile_id: str
    voice_profile_version: int
    description: str = ""


class CreateVersionRequest(BaseModel):
    configuration: dict[str, Any]
    description: str = ""
    auto_activate: bool = False


class UpdateVersionRequest(BaseModel):
    configuration: dict[str, Any]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _agent_response(agent) -> dict:
    return {
        "id": agent.id,
        "organization_id": agent.organization_id,
        "name": agent.name,
        "description": agent.description,
        "template_slug": agent.template_slug,
        "voice_profile_id": agent.voice_profile_id,
        "voice_profile_version": agent.voice_profile_version,
        "active_version": agent.active_version,
        "active_version_id": agent.active_version_id,
        "is_active": agent.is_active,
        "created_at": agent.created_at.isoformat(),
    }


def _version_response(version) -> dict:
    return {
        "id": version.id,
        "agent_id": version.agent_id,
        "version": version.version,
        "status": version.status,
        "description": version.description,
        "configuration": version.configuration,
        "created_at": version.created_at.isoformat(),
    }


def _template_response(tmpl) -> dict:
    return {
        "slug": tmpl.slug,
        "name": tmpl.name,
        "description": tmpl.description,
        "slot_definitions": tmpl.slot_definitions,
        "default_configuration": tmpl.configuration,
    }


def _require_org(user: CurrentUser):
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    return user.org_id


# ---------------------------------------------------------------------------
# Template endpoints (public within authenticated context)
# ---------------------------------------------------------------------------
@router.get("/templates")
async def list_templates(user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    svc = AgentService(db)
    templates = await svc.list_templates()
    return [_template_response(t) for t in templates]


# ---------------------------------------------------------------------------
# Agent CRUD
# ---------------------------------------------------------------------------
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: CreateAgentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    db = get_db()
    svc = AgentService(db)
    try:
        agent = await svc.create_agent(
            organization_id=org_id,
            name=body.name,
            template_slug=body.template_slug,
            voice_profile_id=body.voice_profile_id,
            voice_profile_version=body.voice_profile_version,
            description=body.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _agent_response(agent)


@router.get("")
async def list_agents(user: CurrentUser = Depends(get_current_user)):
    org_id = _require_org(user)
    db = get_db()
    svc = AgentService(db)
    agents = await svc.list_agents(org_id)
    return [_agent_response(a) for a in agents]


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    db = get_db()
    svc = AgentService(db)
    agent = await svc.get_agent(agent_id, org_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _agent_response(agent)


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    db = get_db()
    svc = AgentService(db)
    try:
        await svc.delete_agent(agent_id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "deactivated", "agent_id": agent_id}


# ---------------------------------------------------------------------------
# Agent versions
# ---------------------------------------------------------------------------
@router.post("/{agent_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_version(
    agent_id: str,
    body: CreateVersionRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    db = get_db()
    svc = AgentService(db)
    try:
        version = await svc.create_version(
            agent_id=agent_id,
            organization_id=org_id,
            configuration=body.configuration,
            description=body.description,
            auto_activate=body.auto_activate,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _version_response(version)


@router.get("/{agent_id}/versions")
async def list_versions(
    agent_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    db = get_db()
    svc = AgentService(db)
    try:
        versions = await svc.list_versions(agent_id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return [_version_response(v) for v in versions]


@router.post("/{agent_id}/versions/{version_id}/publish")
async def publish_version(
    agent_id: str,
    version_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    db = get_db()
    svc = AgentService(db)
    try:
        version = await svc.publish_version(agent_id, version_id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _version_response(version)


@router.patch("/{agent_id}/versions/{version_id}")
async def update_draft_version(
    agent_id: str,
    version_id: str,
    body: UpdateVersionRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    db = get_db()
    svc = AgentService(db)
    try:
        version = await svc.update_draft_version(version_id, org_id, body.configuration)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _version_response(version)
