"""REST API for dynamic provider rate cards, daily FX updates, and loss prevention.

Prefix: /pricing
"""

import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.core.rbac import require_platform
from backend.services.pricing_sync_service import PricingSyncService

log = logging.getLogger("api.pricing")

router = APIRouter(prefix="/pricing", tags=["pricing"])


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class SyncRatesRequest(BaseModel):
    force_fx_rate: Optional[float] = Field(None, description="Optional manual USD/INR FX rate to force")
    force_safety_margin_pct: Optional[float] = Field(None, description="Optional platform-wide safety margin %")


class OverrideRateRequest(BaseModel):
    capability: str  # 'stt' | 'llm' | 'tts' | 'telephony'
    provider_name: str
    model_id: str
    base_unit_rate: float
    safety_margin_pct: Optional[float] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/rates")
async def get_all_rates(
    current_user: Optional[CurrentUser] = Depends(get_current_user),
) -> dict:
    """Return all active provider rate cards, latest daily FX rate, and safety margins."""
    db = get_db()
    svc = PricingSyncService(db)
    return await svc.get_all_rates()


@router.get("/pipeline-cost")
async def get_pipeline_cost(
    stt_provider: str = Query("sarvam"),
    stt_model: str = Query("saaras-v3"),
    llm_provider: str = Query("gemini"),
    llm_model: str = Query("gemini-2.0-flash-lite"),
    tts_provider: str = Query("sarvam"),
    tts_model: str = Query("bulbul:v3"),
    telephony_provider: str = Query("webrtc"),
    margin: Optional[float] = Query(None, description="Custom safety margin percentage"),
) -> dict:
    """Compute real-time 3-step pipeline cost including turn-taking and loss-protection margin."""
    db = get_db()
    svc = PricingSyncService(db)
    return await svc.calculate_pipeline_cost(
        stt_provider=stt_provider,
        stt_model=stt_model,
        llm_provider=llm_provider,
        llm_model=llm_model,
        tts_provider=tts_provider,
        tts_model=tts_model,
        telephony_provider=telephony_provider,
        custom_safety_margin_pct=margin,
    )


@router.post("/sync")
async def trigger_daily_sync(
    body: Optional[SyncRatesRequest] = None,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> dict:
    """Trigger an on-demand sync of USD/INR foreign exchange and provider rate cards."""
    db = get_db()
    svc = PricingSyncService(db)
    req = body or SyncRatesRequest()
    return await svc.sync_all_rates(
        force_fx_rate=req.force_fx_rate,
        force_safety_margin_pct=req.force_safety_margin_pct,
    )


@router.post("/override")
async def override_rate(
    body: OverrideRateRequest,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
) -> dict:
    """Immediately override a provider's rate to guard against sudden price hikes."""
    db = get_db()
    svc = PricingSyncService(db)
    card = await svc.override_provider_rate(
        capability=body.capability,
        provider_name=body.provider_name,
        model_id=body.model_id,
        base_unit_rate=body.base_unit_rate,
        safety_margin_pct=body.safety_margin_pct,
        notes=body.notes,
    )
    return {"status": "ok", "card": card.model_dump()}
