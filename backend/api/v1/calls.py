"""Calls API.

GET  /api/v1/calls              — list calls for org
GET  /api/v1/calls/{id}         — get call detail
POST /api/v1/calls/initiate     — initiate an outbound call
POST /api/v1/calls/{id}/finalize — finalize call (internal, called by call worker)

The actual real-time call is handled by the existing WebSocket endpoint
(/ws/call for browser, /ws/twilio for Twilio) — those are preserved from
the original repo and wired in main.py.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.services.call_service import CallService

log = logging.getLogger("api.calls")
router = APIRouter(prefix="/calls", tags=["calls"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class InitiateCallRequest(BaseModel):
    to_number: str
    from_number: str
    campaign_id: Optional[str] = None
    lead_id: Optional[str] = None
    agent_id: Optional[str] = None
    agent_version: Optional[int] = None
    provider: str = "mock"
    reserve_credits: int = 300


class FinalizeCallRequest(BaseModel):
    status: str = "completed"
    outcome: Optional[str] = None
    actual_credits: int = 0
    avg_latency_ms: Optional[int] = None
    turn_count: int = 0
    score: int = 0
    qualification: Optional[dict] = None
    summary: Optional[str] = None
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _require_org(user: CurrentUser) -> str:
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    return user.org_id


def _call_response(call) -> dict:
    return {
        "id": call.id,
        "organization_id": call.organization_id,
        "campaign_id": call.campaign_id,
        "lead_id": call.lead_id,
        "to_number": call.to_number,
        "from_number": call.from_number,
        "direction": call.direction,
        "status": call.status,
        "outcome": call.outcome,
        "duration_s": call.duration_s,
        "talk_time_s": call.talk_time_s,
        "avg_latency_ms": call.avg_latency_ms,
        "turn_count": call.turn_count,
        "score": call.score,
        "qualification": call.qualification,
        "credits_reserved": call.credits_reserved,
        "credits_consumed": call.credits_consumed,
        "summary": call.summary,
        "started_at": call.started_at.isoformat() if call.started_at else None,
        "connected_at": call.connected_at.isoformat() if call.connected_at else None,
        "ended_at": call.ended_at.isoformat() if call.ended_at else None,
        "created_at": call.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/initiate", status_code=status.HTTP_201_CREATED)
async def initiate_call(
    body: InitiateCallRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CallService(get_db())
    try:
        result = await svc.initiate_call(
            organization_id=org_id,
            to_number=body.to_number,
            from_number=body.from_number,
            campaign_id=body.campaign_id,
            lead_id=body.lead_id,
            agent_id=body.agent_id,
            agent_version=body.agent_version,
            provider=body.provider,
            reserve_credits=body.reserve_credits,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.post("/{call_id}/finalize")
async def finalize_call(
    call_id: str,
    body: FinalizeCallRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CallService(get_db())
    try:
        result = await svc.finalize_call(
            call_id=call_id,
            organization_id=org_id,
            status=body.status,
            outcome=body.outcome,
            actual_credits=body.actual_credits,
            avg_latency_ms=body.avg_latency_ms,
            turn_count=body.turn_count,
            score=body.score,
            qualification=body.qualification,
            summary=body.summary,
            error_message=body.error_message,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.get("")
async def list_calls(
    campaign_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    call_status: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CallService(get_db())
    calls = await svc.list_calls(
        org_id, campaign_id=campaign_id, lead_id=lead_id,
        status=call_status, limit=limit, skip=skip,
    )
    return [_call_response(c) for c in calls]


@router.get("/{call_id}")
async def get_call(
    call_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CallService(get_db())
    call = await svc.get_call(call_id, org_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return _call_response(call)
