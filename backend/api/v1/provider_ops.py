"""Provider Operations API — admin only.

GET /api/v1/provider-ops/health        — overall provider health summary
GET /api/v1/provider-ops/metrics       — per-provider metrics (latency/success/cost)
GET /api/v1/provider-ops/latency       — platform latency stats
GET /api/v1/provider-ops/voice-profiles — voice profile health
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from backend.core.rbac import require_platform
from backend.core.db import get_db
from backend.services.provider_ops_service import ProviderOpsService

log = logging.getLogger("api.provider_ops")
router = APIRouter(
    prefix="/provider-ops",
    tags=["provider-ops"],
    dependencies=[Depends(require_platform())],
)


@router.get("/health")
async def provider_health(hours: int = Query(default=24, ge=1, le=168)):
    """Health summary across all providers."""
    return await ProviderOpsService(get_db()).get_provider_health_summary(hours=hours)


@router.get("/metrics")
async def provider_metrics(
    hours: int = Query(default=24, ge=1, le=168),
    provider_type: Optional[str] = None,
):
    """Per-provider metrics: success rate, latency, cost, call count."""
    return await ProviderOpsService(get_db()).get_provider_metrics(
        hours=hours, provider_type=provider_type
    )


@router.get("/latency")
async def platform_latency(hours: int = Query(default=24, ge=1, le=168)):
    """Platform-wide call latency statistics."""
    return await ProviderOpsService(get_db()).get_latency_stats(hours=hours)


@router.get("/voice-profiles")
async def voice_profile_health():
    """Health status of active voice profiles and their provider routes."""
    return await ProviderOpsService(get_db()).get_voice_profile_health()
