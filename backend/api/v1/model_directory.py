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
