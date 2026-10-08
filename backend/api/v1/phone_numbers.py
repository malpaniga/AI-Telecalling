"""Phone numbers API.

Customer endpoints (provider details NEVER included):
  GET  /api/v1/phone-numbers/available       — browse available numbers
  GET  /api/v1/phone-numbers/my              — org's assigned numbers
  GET  /api/v1/phone-numbers/my/{id}         — single assigned number

Admin endpoints (includes provider details):
  GET    /api/v1/phone-numbers/admin         — full inventory
  POST   /api/v1/phone-numbers/admin         — add number to inventory
  POST   /api/v1/phone-numbers/admin/{id}/assign     — assign to org
  POST   /api/v1/phone-numbers/admin/{id}/release    — return to pool
  POST   /api/v1/phone-numbers/admin/{id}/suspend    — suspend
  POST   /api/v1/phone-numbers/admin/{id}/reactivate — reactivate
  GET    /api/v1/phone-numbers/admin/stats   — inventory counts
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.core.auth import CurrentUser, get_current_user
from backend.core.rbac import require_platform
from backend.core.db import get_db
from backend.services.phone_number_service import PhoneNumberService

log = logging.getLogger("api.phone_numbers")
router = APIRouter(prefix="/phone-numbers", tags=["phone-numbers"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class AddNumberRequest(BaseModel):
    number: str
    provider: str
    provider_resource_id: Optional[str] = None
    display_name: Optional[str] = None
    country_code: str = "IN"
    number_type: str = "local"
    can_voice: bool = True
    can_sms: bool = False
    can_whatsapp: bool = False
    rental_paise_per_month: int = 0
    provider_metadata: Optional[dict] = None


class AssignRequest(BaseModel):
    organization_id: str


class ReleaseRequest(BaseModel):
    notes: Optional[str] = None


class SuspendRequest(BaseModel):
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Customer endpoints — NO provider details
# ---------------------------------------------------------------------------
@router.get("/available")
async def list_available_numbers(
    country_code: Optional[str] = None,
    number_type: Optional[str] = None,
    limit: int = 20,
    user: CurrentUser = Depends(get_current_user),
):
    """Browse available numbers to rent (no provider details)."""
    db = get_db()
    svc = PhoneNumberService(db)
    return await svc.list_available(
        country_code=country_code, number_type=number_type, limit=limit
    )


@router.get("/my")
async def list_my_numbers(user: CurrentUser = Depends(get_current_user)):
    """Numbers assigned to the current org (no provider details)."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = PhoneNumberService(db)
    return await svc.list_org_numbers(user.org_id)


@router.get("/my/{phone_number_id}")
async def get_my_number(
    phone_number_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = PhoneNumberService(db)
    result = await svc.get_number_for_org(phone_number_id, user.org_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Number not found or not assigned to your organization")
    return result


# ---------------------------------------------------------------------------
# Admin endpoints — includes provider details
# ---------------------------------------------------------------------------
@router.get("/admin/stats",
            dependencies=[Depends(require_platform())])
async def inventory_stats():
    db = get_db()
    svc = PhoneNumberService(db)
    return await svc.get_inventory_stats()


@router.get("/admin",
            dependencies=[Depends(require_platform())])
async def admin_list_numbers(
    status: Optional[str] = None,
    provider: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
):
    db = get_db()
    svc = PhoneNumberService(db)
    return await svc.list_all_admin(status=status, provider=provider, limit=limit, skip=skip)


@router.post("/admin", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_platform("platform_owner", "platform_admin"))])
async def add_number_to_inventory(body: AddNumberRequest):
    db = get_db()
    svc = PhoneNumberService(db)
    try:
        pn = await svc.add_to_inventory(**body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    # Admin response includes provider details
    from backend.services.phone_number_service import _to_admin_view
    return _to_admin_view(pn)


@router.post("/admin/{phone_number_id}/assign",
             dependencies=[Depends(require_platform("platform_owner", "platform_admin"))])
async def assign_number(
    phone_number_id: str,
    body: AssignRequest,
    user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    svc = PhoneNumberService(db)
    try:
        result = await svc.assign_to_org(
            phone_number_id=phone_number_id,
            organization_id=body.organization_id,
            performed_by=user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return result


@router.post("/admin/{phone_number_id}/release",
             dependencies=[Depends(require_platform("platform_owner", "platform_admin"))])
async def release_number(
    phone_number_id: str,
    body: ReleaseRequest,
    user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    svc = PhoneNumberService(db)
    try:
        await svc.release_from_org(
            phone_number_id=phone_number_id,
            performed_by=user.user_id,
            notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "released", "phone_number_id": phone_number_id}


@router.post("/admin/{phone_number_id}/suspend",
             dependencies=[Depends(require_platform("platform_owner", "platform_admin"))])
async def suspend_number(
    phone_number_id: str,
    body: SuspendRequest,
    user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    svc = PhoneNumberService(db)
    try:
        await svc.suspend_number(
            phone_number_id=phone_number_id,
            performed_by=user.user_id,
            reason=body.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "suspended", "phone_number_id": phone_number_id}


@router.post("/admin/{phone_number_id}/reactivate",
             dependencies=[Depends(require_platform("platform_owner", "platform_admin"))])
async def reactivate_number(
    phone_number_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    svc = PhoneNumberService(db)
    try:
        await svc.reactivate_number(
            phone_number_id=phone_number_id,
            performed_by=user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "active", "phone_number_id": phone_number_id}
