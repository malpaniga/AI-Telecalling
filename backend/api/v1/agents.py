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
    voice_profile_id: Optional[str] = None
    voice_profile_version: Optional[int] = None
    description: str = ""
    auto_init_version: bool = False
    initial_configuration: Optional[dict[str, Any]] = None


class CreateVersionRequest(BaseModel):
    configuration: dict[str, Any]
    description: str = ""
    auto_activate: bool = False


class UpdateVersionRequest(BaseModel):
    configuration: dict[str, Any]


class ImportAgentRequest(BaseModel):
    name: str
    template_slug: str = "generic"
    configuration: dict[str, Any]
    description: str = ""
    voice_profile_id: Optional[str] = None


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
        "category": getattr(tmpl, "category", "Lead qualification"),
        "icon_color": getattr(tmpl, "icon_color", "blue"),
        "slot_definitions": tmpl.slot_definitions,
        "default_configuration": tmpl.configuration,
    }


def _require_org(user: CurrentUser):
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    return user.org_id


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    voice_profile_id: Optional[str] = None
    voice_profile_version: Optional[int] = None


class ImproveInstructionsRequest(BaseModel):
    instructions: str
    greeting: Optional[str] = None
    persona_focus: Optional[str] = None


class TranslateGreetingRequest(BaseModel):
    text: str
    target_language: str  # e.g. "hi-IN", "mr-IN", "ta-IN", "te-IN"


# ---------------------------------------------------------------------------
# Template endpoints (public within authenticated context)
# ---------------------------------------------------------------------------
@router.get("/templates")
async def list_templates(user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    svc = AgentService(db)
    templates = await svc.list_templates()
    return [_template_response(t) for t in templates]


@router.get("/pipeline-status")
async def get_pipeline_status(user: CurrentUser = Depends(get_current_user)):
    """Return whether STT, LLM, and TTS pipeline components are configured and ready.

    Deliberately conceals internal cloud provider names and model IDs from
    tenant organizations to maintain multi-tenant abstraction.
    """
    from backend.services.model_directory_service import ModelDirectoryService

    db = get_db()
    svc = ModelDirectoryService(db)

    stt_active = await svc.get_active_config("stt")
    llm_active = await svc.get_active_config("llm")
    tts_active = await svc.get_active_config("tts")

    return {
        "stt": {"connected": stt_active is not None},
        "llm": {"connected": llm_active is not None},
        "tts": {"connected": tts_active is not None},
        "all_ready": bool(stt_active and llm_active and tts_active),
    }


@router.post("/improve-instructions")
async def improve_instructions(
    body: ImproveInstructionsRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Use active LLM (Genie) to optimize agent instructions and prompt."""
    from backend.services.provider_runtime import CloudProviderRuntime

    db = get_db()
    runtime = CloudProviderRuntime(db)
    try:
        llm = await runtime.load_provider("llm")
    except Exception:
        return {
            "improved_instructions": body.instructions,
            "suggestions": [
                "Keep speech under 25 words per turn for natural phone rhythm.",
                "Always acknowledge what the prospect said before asking the next question.",
                "Ask strictly one question per turn.",
            ],
        }

    prompt = (
        "You are Genie, Sarvam AI's prompt optimization assistant for voice telecalling agents in India. "
        "Review and optimize the following telecalling instructions. "
        "Strict voice conversational guidelines: "
        "1. Under 25 words per conversational turn. "
        "2. Strictly ONE clear question per turn. "
        "3. Acknowledge before asking. "
        "4. Structure cleanly with Persona, Environment & Situation, Objective, Speaking Style, and Conversation Phases. "
        "5. Keep variable placeholders intact like {partnerName}, {salesRepName}, {productCategory}. "
        "Return only the polished markdown instructions:\n\n"
        f"{body.instructions}"
    )
    try:
        reply = await llm.generate([{"role": "user", "content": prompt}])
        return {
            "improved_instructions": reply,
            "suggestions": [
                "Streamlined conversational turns to under 25 words.",
                "Reinforced strict single-question discipline.",
                "Added objection handling and graceful closing phases.",
            ],
        }
    except Exception as exc:
        log.warning("Genie instruction improvement failed: %s", exc)
        return {"improved_instructions": body.instructions, "suggestions": []}


_LANG_NAMES = {
    "hi-IN": "Hindi",
    "mr-IN": "Marathi",
    "en-IN": "English",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "kn-IN": "Kannada",
    "bn-IN": "Bengali",
    "gu-IN": "Gujarati",
    "ml-IN": "Malayalam",
    "pa-IN": "Punjabi",
}


@router.post("/translate-greeting")
async def translate_greeting(
    body: TranslateGreetingRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Use active LLM to translate the greeting text into the target language.

    Variable placeholders like {partnerName}, {salesRepName}, etc. are
    preserved verbatim in the translated output.
    """
    from backend.services.provider_runtime import CloudProviderRuntime

    lang_name = _LANG_NAMES.get(body.target_language, body.target_language)

    db = get_db()
    runtime = CloudProviderRuntime(db)
    try:
        llm = await runtime.load_provider("llm")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM provider is not configured. Please set up an LLM in the Model Directory.",
        )

    prompt = (
        f"Translate the following telecalling greeting into {lang_name}. "
        "Rules:\n"
        "1. This is a voice telecalling greeting spoken on the phone — keep it natural and conversational.\n"
        "2. Preserve ALL variable placeholders exactly as-is (e.g. {user_name}, {partnerName}, {salesRepName}, {productCategory}). "
        "Do NOT translate, rename, or remove any placeholder.\n"
        "3. The translated text must convey the SAME meaning as the original — do NOT change the content, add or remove information.\n"
        "4. Return ONLY the translated text, nothing else — no explanations, no quotes, no markdown.\n\n"
        f"Original text:\n{body.text}"
    )
    try:
        translated = await llm.generate([{"role": "user", "content": prompt}])
        return {"translated_text": translated.strip()}
    except Exception as exc:
        log.warning("Greeting translation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Translation failed. Please try again.",
        )


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
        vp_id = body.voice_profile_id
        vp_version = body.voice_profile_version
        if not vp_id:
            from backend.services.voice_profile_service import VoiceProfileService
            vp_svc = VoiceProfileService(db)
            profiles = await vp_svc.list_customer_profiles(org_id)
            if profiles:
                vp_id = profiles[0]["id"]
                vp_version = profiles[0].get("active_version") or 1
            else:
                vp_id = "default"
                vp_version = 1
        if not vp_version:
            vp_version = 1

        agent = await svc.create_agent(
            organization_id=org_id,
            name=body.name,
            template_slug=body.template_slug,
            voice_profile_id=vp_id,
            voice_profile_version=vp_version,
            description=body.description,
        )
        # Optionally auto-seed v1 with template default configuration or provided configuration
        if body.auto_init_version:
            config = body.initial_configuration
            if not config:
                tmpl = await svc.templates.find_by_slug(body.template_slug)
                if tmpl and tmpl.configuration:
                    config = tmpl.configuration
            if config:
                await svc.create_version(
                    agent_id=agent.id,
                    organization_id=org_id,
                    configuration=config,
                    description="Initial version",
                    auto_activate=True,
                )
                agent = await svc.get_agent(agent.id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _agent_response(agent)


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: str,
    body: UpdateAgentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    db = get_db()
    svc = AgentService(db)
    agent = await svc.get_agent(agent_id, org_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    if update_data:
        await svc.agents.col.update_one({"_id": agent_id}, {"$set": update_data})
    agent = await svc.get_agent(agent_id, org_id)
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


@router.get("/{agent_id}/export")
async def export_agent(
    agent_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Export agent configuration as a portable JSON package conforming to sarvam_agent_export_v1."""
    org_id = _require_org(user)
    db = get_db()
    svc = AgentService(db)
    try:
        return await svc.export_agent(agent_id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_agent(
    body: ImportAgentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Import an agent configuration into the current organization."""
    org_id = _require_org(user)
    if not body.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent name is required")
    if not body.configuration:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Configuration is required")

    db = get_db()
    svc = AgentService(db)
    try:
        agent = await svc.import_agent(
            organization_id=org_id,
            name=body.name.strip(),
            template_slug=body.template_slug,
            configuration=body.configuration,
            description=body.description,
            voice_profile_id=body.voice_profile_id,
        )
        return _agent_response(agent)
    except ValueError as e:
        err_msg = str(e)
        if "limit reached" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)


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
