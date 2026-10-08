"""Credit reservation/settlement API — internal call billing endpoints.

These are called by the call pipeline, not directly by customers.

POST /api/v1/credits/reserve          — reserve credits for a call
POST /api/v1/credits/release          — release reservation (call failed/cancelled)
POST /api/v1/credits/settle           — settle actual usage after call
GET  /api/v1/credits/check            — preflight credit check (no state change)
GET  /api/v1/credits/reservations     — active reservations for org
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from backend.core.auth import CurrentUser, get_current_user
from backend.core.rbac import require_platform
from backend.core.db import get_db
from backend.services.credit_service import CreditService

log = logging.getLogger("api.credits")
router = APIRouter(prefix="/credits", tags=["credits"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ReserveRequest(BaseModel):
    call_id: str
    max_credits: int

    @field_validator("max_credits")
    @classmethod
    def positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("max_credits must be positive")
        return v


class ReleaseRequest(BaseModel):
    call_id: str


class SettleRequest(BaseModel):
    call_id: str
    actual_credits: int
    idempotency_key: Optional[str] = None

    @field_validator("actual_credits")
    @classmethod
    def non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("actual_credits cannot be negative")
        return v


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/reserve")
async def reserve_credits(
    body: ReserveRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Reserve credits for an outbound call. Fails if insufficient credits."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = CreditService(db)
    try:
        result = await svc.reserve(
            organization_id=user.org_id,
            call_id=body.call_id,
            max_credits=body.max_credits,
        )
    except ValueError as e:
        raise HTTPException(status_code=402, detail=str(e))
    return result


@router.post("/release")
async def release_credits(
    body: ReleaseRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Release reserved credits (call cancelled/failed before billing)."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = CreditService(db)
    result = await svc.release(
        organization_id=user.org_id,
        call_id=body.call_id,
    )
    return result


@router.post("/settle")
async def settle_credits(
    body: SettleRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Settle exact credits after call completes. Idempotent."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = CreditService(db)
    try:
        result = await svc.settle(
            organization_id=user.org_id,
            call_id=body.call_id,
            actual_credits=body.actual_credits,
            idempotency_key=body.idempotency_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/check")
async def check_credits(
    required_credits: int = 60,
    user: CurrentUser = Depends(get_current_user),
):
    """Pre-flight credit check. No state change."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = CreditService(db)
    return await svc.can_start_call(user.org_id, required_credits)


@router.get("/reservations")
async def active_reservations(
    user: CurrentUser = Depends(get_current_user),
):
    """List active call credit reservations for the current org."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = CreditService(db)
    return await svc.get_active_reservations(user.org_id)


@router.get("/admin/orgs/{org_id}/reservations",
            dependencies=[Depends(require_platform())])
async def admin_active_reservations(org_id: str):
    """Platform admin: view active reservations for any org."""
    db = get_db()
    svc = CreditService(db)
    return await svc.get_active_reservations(org_id)
