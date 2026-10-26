"""REST API for the AI Models Directory.

All endpoints require platform_owner or platform_admin role.
Credentials are never returned in responses — only key_hint + metadata.

Prefix: /model-directory
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.auth import CurrentUser
from backend.core.db import get_db
from backend.core.rbac import require_platform
from backend.services.model_directory_service import (
    ModelDirectoryService,
    RateLimitError,
)

log = logging.getLogger("api.model_directory")

router = APIRouter(prefix="/model-directory", tags=["model-directory"])

# ---------------------------------------------------------------------------
# Request body schemas
# ---------------------------------------------------------------------------

class ConfigureProviderBody(BaseModel):
    provider_name: str
    model_id: str
    capability: str  # 'tts' | 'stt' | 'llm'
    credential_plaintext: str | None = None
    voice: str | None = None
    language: str | None = None
    extra_params: dict[str, Any] = Field(default_factory=dict)
    is_fallback: bool = False


class FallbackBody(BaseModel):
    fallback_config_id: str


class RotateCredentialBody(BaseModel):
    new_plaintext: str


# ---------------------------------------------------------------------------
# Dependency helper
# ---------------------------------------------------------------------------

def _get_service() -> ModelDirectoryService:
    db = get_db()
    return ModelDirectoryService(db)


# ---------------------------------------------------------------------------
# Catalogue endpoints
# ---------------------------------------------------------------------------

@router.get("/catalogue")
async def list_catalogue(
    capability: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> list[dict]:
    """List all catalogue entries, optionally filtered by capability/status/search."""
    svc = _get_service()
    return await svc.list_catalogue(capability=capability, status=status, search=search)


@router.get("/catalogue/{provider_name}/{model_id}")
async def get_catalogue_entry(
    provider_name: str,
    model_id: str,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> dict:
    """Get a single catalogue entry by provider_name and model_id."""
    svc = _get_service()
    try:
        return await svc.get_model(provider_name, model_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/providers/{provider_name}/live-models")
async def list_provider_live_models(
    provider_name: str,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> list[str]:
    """Return available live models for a provider using stored credentials if present."""
    svc = _get_service()
    return await svc.list_provider_live_models(provider_name)


# ---------------------------------------------------------------------------
# Configuration endpoints
# ---------------------------------------------------------------------------

@router.post("/configurations")
async def configure_provider(
    body: ConfigureProviderBody,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> dict:
    """Create a new provider configuration. Returns the saved config (no credentials)."""
    svc = _get_service()
    try:
        return await svc.connect_provider(body.model_dump(), body.credential_plaintext, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/configurations")
async def list_configurations(
    capability: str | None = Query(None),
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> list[dict]:
    """List all provider configurations (credentials stripped)."""
    svc = _get_service()
    return await svc.list_configs(capability=capability)


@router.get("/configurations/{config_id}")
async def get_configuration(
    config_id: str,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> dict:
    """Get a single configuration (credentials masked)."""
    svc = _get_service()
    try:
        return await svc.get_config(config_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/configurations/{config_id}/test")
async def test_configuration(
    config_id: str,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> dict:
    """Run a connectivity + inference test for this configuration."""
    svc = _get_service()
    try:
        return await svc.test_provider(config_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))


@router.post("/configurations/{config_id}/activate")
async def activate_configuration(
    config_id: str,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> dict:
    """Activate a tested configuration (deactivates the previous active one)."""
    svc = _get_service()
    try:
        return await svc.activate_provider(config_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/configurations/{config_id}/fallback")
async def set_fallback(
    config_id: str,
    body: FallbackBody,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> dict:
    """Set the fallback configuration for a capability."""
    svc = _get_service()
    try:
        return await svc.update_fallback(config_id, body.fallback_config_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/configurations/{config_id}")
async def delete_configuration(
    config_id: str,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> dict:
    """Delete a provider configuration."""
    svc = _get_service()
    try:
        await svc.delete_config(config_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status": "deleted", "config_id": config_id}


# ---------------------------------------------------------------------------
# Credential endpoints
# ---------------------------------------------------------------------------

@router.get("/credentials/{provider_name}")
async def list_credentials(
    provider_name: str,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> list[dict]:
    """List credential metadata (key_hint only — never plaintext or encrypted bytes)."""
    svc = _get_service()
    return await svc.list_credentials(provider_name)


@router.post("/credentials/{provider_name}/rotate")
async def rotate_credential(
    provider_name: str,
    body: RotateCredentialBody,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> dict:
    """Rotate the credential for a provider. Old credential is marked as rotated."""
    svc = _get_service()
    try:
        await svc.rotate_credential(provider_name, body.new_plaintext, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "rotated"}


@router.delete("/credentials/{provider_name}")
async def delete_credential(
    provider_name: str,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> dict:
    """Delete all credentials and configurations for a provider."""
    svc = _get_service()
    await svc.delete_credential(provider_name, user)
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Wizard endpoint
# ---------------------------------------------------------------------------

@router.get("/wizard-status")
async def wizard_status(
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> dict:
    """Return per-capability setup progress for the provider wizard.

    Response shape:
    {
        "capabilities": {
            "stt": {"connected": bool, "tested": bool, "active": bool, "active_provider": str|null, "configs": int},
            "tts": { ... },
            "llm": { ... },
        },
        "all_ready": bool  # True if all three capabilities have an active provider
    }
    """
    svc = _get_service()
    caps = {}
    for cap in ("stt", "tts", "llm"):
        configs = await svc.list_configs(capability=cap)
        active = await svc.get_active_config(cap)
        any_tested = any(c.get("last_test_result") == "ok" for c in configs)
        caps[cap] = {
            "connected": len(configs) > 0,
            "tested": any_tested,
            "active": active is not None,
            "active_provider": f"{active['provider_name']}/{active['model_id']}" if active else None,
            "active_latency_ms": active.get("last_test_latency_ms") if active else None,
            "configs": len(configs),
        }
    return {
        "capabilities": caps,
        "all_ready": all(c["active"] for c in caps.values()),
    }


# ---------------------------------------------------------------------------
# Test Agent Endpoints
# ---------------------------------------------------------------------------

class TestChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    system_prompt: str | None = None
    language: str | None = "en-IN"


@router.get("/test-agent/info")
async def get_test_agent_info(
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> dict:
    """Return pipeline components, readiness, and presets for the in-browser test agent."""
    svc = _get_service()
    stt_active = await svc.get_active_config("stt")
    llm_active = await svc.get_active_config("llm")
    tts_active = await svc.get_active_config("tts")

    all_ready = bool(stt_active and llm_active and tts_active)

    return {
        "all_ready": all_ready,
        "pipeline": {
            "stt": stt_active,
            "llm": llm_active,
            "tts": tts_active,
        },
        "languages": [
            {"code": "mr-IN", "name": "Marathi", "native": "मराठी"},
            {"code": "hi-IN", "name": "Hindi", "native": "हिन्दी"},
            {"code": "en-IN", "name": "English", "native": "English (India)"},
            {"code": "gu-IN", "name": "Gujarati", "native": "ગુજરાતી"},
            {"code": "ta-IN", "name": "Tamil", "native": "தமிழ்"},
            {"code": "te-IN", "name": "Telugu", "native": "తెలుగు"},
            {"code": "kn-IN", "name": "Kannada", "native": "ಕನ್ನಡ"},
            {"code": "bn-IN", "name": "Bengali", "native": "বাংলা"},
            {"code": "pa-IN", "name": "Punjabi", "native": "ਪੰਜਾਬੀ"},
        ],
        "default_scenarios": [
            {
                "id": "solar",
                "name": "Rooftop Solar Consultation (Priya)",
                "agent_name": "Priya",
                "language": "mr-IN",
                "input_variables": {
                    "partnerName": "सोलरशिप एनर्जीज",
                    "userName": "",
                    "companyName": "सोलरशिप एनर्जीज प्रा. लि.",
                    "productCategory": "छतावर सोलर पॅनेल",
                    "role": "सोलर सल्लागार",
                    "salesRepName": "प्रिया",
                    "customerCareNumber": "1800-209-7652",
                },
                "output_variables": [
                    "disposition",
                    "pain_points_mentioned",
                    "current_state_of_solving",
                    "budget_indication",
                    "timeline_to_decide",
                    "chosen_next_step",
                    "next_step_date_time",
                ],
                "greeting": "नमस्कार, मी {partnerName} टीममधून {salesRepName} बोलतेय.",
                "system_prompt": (
                    "Persona: {salesRepName}, a warm, consultative rooftop solar advisor at {partnerName} calling homeowners and business owners in Maharashtra, India. "
                    "Tone: warm, polite, consultative, curious. Discovery is 70% listening, 30% talking. "
                    "If asked whether you are AI: State clearly that you are an AI solar consultation assistant from the {partnerName} team, then continue. "
                    "Language: Always speak natural, fluent Marathi (मराठी) in Devanagari script. Keep industry terms natural (kW, subsidy, WhatsApp, solar panel). "
                    "\nCRITICAL CONVERSATIONAL RULES: "
                    "1. NEVER RE-GREET: The greeting was already spoken. NEVER say 'नमस्कार' or re-introduce yourself mid-call. "
                    "2. UNDER 25 WORDS PER TURN: Keep all turns short, snappy, and conversational. Talk; do not read. "
                    "3. STRICTLY ONE QUESTION PER TURN: A turn may carry a short acknowledgment plus exactly ONE question, nothing more. Never ask two questions at once. "
                    "4. ACKNOWLEDGE BEFORE YOU ASK: After each answer, reflect it back in a few words first, then ask the next question. "
                    "\nCONVERSATION PHASES: "
                    "- Phase 1 (Frame Call on 'बोला' / 'सांगा'): When caller says 'बोला', 'हो बोला', 'सांगा', 'काय काम आहे' or listens: State value proposition: 'पंतप्रधान सूर्य घर योजनेअंतर्गत ₹७८,००० पर्यंत सरकारी सबसिडी मिळवून तुम्ही {productCategory} बसवून वीज बिल ८० ते ९०% कमी करू शकता.' Then ask: 'सध्या तुमचं महिन्याचं सरासरी वीज बिल किती येतं?' "
                    "- Phase 2 (Discover Bill & Annual Math): When they state their bill (e.g. ₹2,000): Calculate annual savings: 'दोन हजार म्हणजे वर्षाला तुमचे जवळपास ₹२४,००० विजेवर खर्च होतात! २ kW सोलरने हे बिल जवळपास शून्य होईल आणि ₹७८,००० सबसिडीही मिळेल.' Then ask: 'तुमच्या छतावर स्वतःची मोकळी जागा आहे का, जिथे चांगलं ऊन असतं?' "
                    "- Phase 3 (Free Site Survey Offer): When they confirm rooftop space / sunlight: Offer free evaluation: 'छान! मग आमच्या कंपनीकडून एका इंजिनिअरला तुमच्या घरी मोफत साईट व्हिजिटसाठी पाठवू का, जेणेकरून ते येऊन अचूक अंदाज सांगू शकतील?' "
                    "- Phase 4 (Zero-Pressure WhatsApp Offer on 'नाही'): If they decline a site visit ('नाही', 'नको'): DO NOT HANG UP OR ARGUE. Offer a zero-pressure WhatsApp calculation: 'काही हरकत नाही! मी कोणताही आग्रह करत नाही. तुमच्या याच नंबरवर व्हॉट्सॲप आहे का? मी २ मिनिटांत २ kW सोलरचा खर्च, सबसिडी आणि बचतीची संपूर्ण माहिती पाठवून देते, जेणेकरून तुम्ही निवांत पाहू शकाल.' "
                    "- Phase 5 (Farewell): When caller agrees to WhatsApp ('हो', 'पाठवा', 'ठीक आहे') OR firmly rejects everything ('काही नको', 'फोन ठेवा'): Conclude warmly: 'नक्कीच, मी लगेच व्हॉट्सॲपवर माहिती पाठवते. {partnerName} शी बोलल्याबद्दल धन्यवाद, तुमचा दिवस शुभ जावो! [HANGUP]'."
                ),
            },
            {
                "id": "realestate",
                "name": "Real Estate Advisory (Kavya)",
                "agent_name": "Kavya",
                "language": "en-IN",
                "input_variables": {
                    "partnerName": "Rishab Developers",
                    "userName": "",
                    "productCategory": "Residential Apartments & Villas",
                    "salesRepName": "Kavya",
                },
                "output_variables": [
                    "disposition",
                    "budget_indication",
                    "timeline_to_decide",
                    "chosen_next_step",
                ],
                "greeting": "Hello, and thank you so much for calling {partnerName}! This is {salesRepName}. Are you looking to buy or rent {productCategory}?",
                "system_prompt": (
                    "Persona: {salesRepName}, customer support specialist at {partnerName}. "
                    "Goal: Qualify buyer/renter, budget, preferred Indian locality, and timeline. "
                    "Keep answers concise, conversational, and warm. Under 25 words per turn. "
                    "Strictly one question per turn. Include [HANGUP] on final farewell."
                ),
            },
        ],
    }


@router.post("/test-chat")
async def test_agent_chat(
    body: TestChatRequest,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> dict:
    """Run an interactive chat turn against the active reasoning engine (LLM)."""
    import time
    from backend.core.db import get_db
    from backend.services.provider_runtime import CloudProviderRuntime

    db = get_db()
    runtime = CloudProviderRuntime(db)
    try:
        llm = await runtime.load_provider("llm")
    except LookupError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot test chat: {exc}. Please configure and activate an LLM provider first in the Setup Wizard.",
        )

    svc = _get_service()
    active_llm = await svc.get_active_config("llm")

    # Build conversation history
    messages = list(body.history)
    messages.append({"role": "user", "content": body.message})

    t0 = time.perf_counter()
    try:
        reply = await llm.generate(
            messages,
            system_prompt=body.system_prompt,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "reply": reply,
            "latency_ms": latency_ms,
            "provider_name": active_llm["provider_name"] if active_llm else "llm",
            "model_id": active_llm["model_id"] if active_llm else "unknown",
        }
    except Exception as exc:
        log.warning("Test chat failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {exc}")
