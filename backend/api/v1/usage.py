"""Usage API.

Customer endpoints (NO provider costs):
  GET /api/v1/usage/summary      — credits consumed, call/message counts
  GET /api/v1/usage/events       — list usage events (no provider cost)

Admin endpoints (includes provider costs, margins):
  GET /api/v1/usage/admin/summary                    — org or platform summary
  GET /api/v1/usage/admin/provider-breakdown/{call}  — per-call provider costs
  GET /api/v1/usage/admin/providers                  — aggregate by provider
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.core.auth import CurrentUser, get_current_user
from backend.core.rbac import require_platform
from backend.core.db import get_db
from backend.services.usage_service import UsageService

log = logging.getLogger("api.usage")
router = APIRouter(prefix="/usage", tags=["usage"])


def _require_org(user: CurrentUser) -> str:
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    return user.org_id


# ---------------------------------------------------------------------------
# Customer endpoints — NO provider costs
# ---------------------------------------------------------------------------
@router.get("/summary")
async def usage_summary(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    user: CurrentUser = Depends(get_current_user),
):
    """Usage summary for current org. No provider costs."""
    org_id = _require_org(user)
    svc = UsageService(get_db())
    return await svc.get_customer_summary(org_id, from_date, to_date)


@router.get("/events")
async def list_usage_events(
    event_type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = Query(default=100, le=500),
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    """List usage events for current org. Provider costs stripped."""
    org_id = _require_org(user)
    svc = UsageService(get_db())
    return await svc.list_usage_events(
        org_id, event_type, from_date, to_date, limit, skip
    )


# ---------------------------------------------------------------------------
# Admin endpoints — includes provider costs
# ---------------------------------------------------------------------------
@router.get("/admin/summary",
            dependencies=[Depends(require_platform())])
async def admin_usage_summary(
    organization_id: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
):
    """Admin: full usage summary with provider costs and gross margin."""
    svc = UsageService(get_db())
    return await svc.get_admin_summary(organization_id, from_date, to_date)


@router.get("/admin/provider-breakdown/{call_id}",
            dependencies=[Depends(require_platform())])
async def provider_breakdown(call_id: str):
    """Admin: per-call provider cost breakdown."""
    svc = UsageService(get_db())
    result = await svc.get_provider_breakdown(call_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No provider usage found for this call")
    return result


@router.get("/admin/providers",
            dependencies=[Depends(require_platform())])
async def provider_aggregates():
    """Admin: aggregate provider costs by provider combination."""
    svc = UsageService(get_db())
    return await svc.get_provider_aggregates()


# ---- Internal: record usage (called by post-call processing) ----
class RecordCallUsageRequest(BaseModel):
    call_id: str
    duration_s: int
    credits_consumed: int
    campaign_id: Optional[str] = None
    telephony_provider: Optional[str] = None
    stt_provider: Optional[str] = None
    llm_provider: Optional[str] = None
    tts_provider: Optional[str] = None


@router.post("/record-call")
async def record_call_usage(
    body: RecordCallUsageRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Record usage for a completed call (called internally by call pipeline)."""
    org_id = _require_org(user)
    svc = UsageService(get_db())
    result = await svc.record_call_usage(
        organization_id=org_id,
        call_id=body.call_id,
        duration_s=body.duration_s,
        credits_consumed=body.credits_consumed,
        campaign_id=body.campaign_id,
        telephony_provider=body.telephony_provider,
        stt_provider=body.stt_provider,
        llm_provider=body.llm_provider,
        tts_provider=body.tts_provider,
    )
    # Return customer-safe portion only
    return {
        "usage_event_id": result.get("usage_event_id"),
        "credits_consumed": result.get("credits_consumed"),
        "idempotent": result.get("idempotent", False),
    }
