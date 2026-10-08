"""Wallet and calling packs API.

Customer:
  GET  /api/v1/wallet                      — wallet balance + summary
  GET  /api/v1/wallet/transactions         — ledger (recent 100)
  GET  /api/v1/wallet/lots                 — active credit lots
  GET  /api/v1/wallet/packs                — public calling packs
  GET  /api/v1/wallet/packs/{slug}         — single pack
  POST /api/v1/wallet/packs/{id}/order     — create order to buy a pack
  POST /api/v1/wallet/packs/{id}/verify    — (same as /billing/verify but pack context)

Admin:
  POST /api/v1/wallet/admin/bonus          — grant bonus credits to org
  POST /api/v1/wallet/admin/adjust         — manual credit adjustment
  GET  /api/v1/wallet/admin/orgs/{org_id}  — view any org's wallet
  POST /api/v1/wallet/admin/packs          — create calling pack
  PATCH /api/v1/wallet/admin/packs/{id}    — update pack
  POST /api/v1/wallet/admin/expire         — run expiry for an org
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from backend.core.auth import CurrentUser, get_current_user
from backend.core.rbac import require_platform
from backend.core.db import get_db
from backend.services.wallet_service import WalletService
from backend.services.payment_service import PaymentService

log = logging.getLogger("api.wallet")
router = APIRouter(prefix="/wallet", tags=["wallet"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class BonusRequest(BaseModel):
    organization_id: str
    credits: int
    description: str = "Platform bonus"
    validity_days: int = 90

    @field_validator("credits")
    @classmethod
    def positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("credits must be positive")
        return v


class AdjustRequest(BaseModel):
    organization_id: str
    credits_delta: int
    reason: str

    @field_validator("credits_delta")
    @classmethod
    def nonzero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("credits_delta cannot be zero")
        return v


class PackCreateRequest(BaseModel):
    name: str
    slug: str
    credits: int
    price_paise: int
    description: str = ""
    validity_days: int = 365
    bonus_credits: int = 0
    is_public: bool = True
    sort_order: int = 0

    @field_validator("credits")
    @classmethod
    def credits_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("credits must be positive")
        return v

    @field_validator("price_paise", "bonus_credits")
    @classmethod
    def non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("must be non-negative")
        return v


class PackUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_paise: Optional[int] = None
    credits: Optional[int] = None
    bonus_credits: Optional[int] = None
    validity_days: Optional[int] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    sort_order: Optional[int] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _pack_response(p) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "slug": p.slug,
        "description": p.description,
        "credits": p.credits,
        "bonus_credits": p.bonus_credits,
        "total_credits": p.total_credits,
        "price_paise": p.price_paise,
        "price_inr": p.price_paise / 100,
        "validity_days": p.validity_days,
        "is_active": p.is_active,
        "is_public": p.is_public,
        "sort_order": p.sort_order,
    }


def _txn_response(t) -> dict:
    return {
        "id": t.id,
        "transaction_type": t.transaction_type,
        "credits_delta": t.credits_delta,
        "balance_after": t.balance_after,
        "description": t.description,
        "call_id": t.call_id,
        "order_id": t.order_id,
        "created_at": t.created_at.isoformat(),
    }


def _lot_response(l) -> dict:
    return {
        "id": l.id,
        "original_credits": l.original_credits,
        "remaining_credits": l.remaining_credits,
        "source": l.source,
        "expires_at": l.expires_at.isoformat() if l.expires_at else None,
        "is_expired": l.is_expired,
        "purchased_at": l.purchased_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Customer endpoints
# ---------------------------------------------------------------------------
@router.get("")
async def get_wallet(user: CurrentUser = Depends(get_current_user)):
    """Get wallet balance and summary for current org."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = WalletService(db)
    return await svc.get_wallet_summary(user.org_id)


@router.get("/transactions")
async def get_transactions(
    limit: int = 100,
    skip: int = 0,
    txn_type: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = WalletService(db)
    txns = await svc.txn_repo.list_for_org(
        user.org_id, limit=limit, skip=skip, txn_type=txn_type
    )
    return [_txn_response(t) for t in txns]


@router.get("/lots")
async def get_lots(user: CurrentUser = Depends(get_current_user)):
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = WalletService(db)
    lots = await svc.lot_repo.list_active(user.org_id)
    return [_lot_response(l) for l in lots]


@router.get("/packs")
async def list_packs():
    """List public calling packs (no auth required)."""
    db = get_db()
    svc = WalletService(db)
    packs = await svc.pack_repo.list_public()
    return [_pack_response(p) for p in packs]


@router.get("/packs/{pack_id_or_slug}")
async def get_pack(pack_id_or_slug: str):
    db = get_db()
    svc = WalletService(db)
    pack = await svc.pack_repo.find_by_id(pack_id_or_slug)
    if pack is None:
        pack = await svc.pack_repo.find_by_slug(pack_id_or_slug)
    if pack is None or not pack.is_active:
        raise HTTPException(status_code=404, detail="Pack not found")
    return _pack_response(pack)


@router.post("/packs/{pack_id}/order")
async def create_pack_order(
    pack_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a payment order for a calling pack purchase."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = PaymentService(db)
    try:
        result = await svc.create_calling_pack_order(
            organization_id=user.org_id,
            calling_pack_id=pack_id,
            created_by=user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------
@router.get("/admin/orgs/{org_id}",
            dependencies=[Depends(require_platform())])
async def admin_get_wallet(org_id: str):
    db = get_db()
    svc = WalletService(db)
    return await svc.get_wallet_summary(org_id)


@router.post("/admin/bonus",
             dependencies=[Depends(require_platform("platform_owner", "platform_admin", "billing_admin"))])
async def admin_grant_bonus(
    body: BonusRequest,
    user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    svc = WalletService(db)
    result = await svc.grant_bonus(
        organization_id=body.organization_id,
        credits=body.credits,
        description=body.description,
        validity_days=body.validity_days,
        created_by=user.user_id,
    )
    return result


@router.post("/admin/adjust",
             dependencies=[Depends(require_platform("platform_owner", "platform_admin", "billing_admin"))])
async def admin_adjust_credits(
    body: AdjustRequest,
    user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    svc = WalletService(db)
    try:
        result = await svc.admin_adjustment(
            organization_id=body.organization_id,
            credits_delta=body.credits_delta,
            reason=body.reason,
            admin_user_id=user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.post("/admin/packs", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_platform("platform_owner", "platform_admin"))])
async def admin_create_pack(body: PackCreateRequest):
    db = get_db()
    svc = WalletService(db)
    if await svc.pack_repo.find_by_slug(body.slug):
        raise HTTPException(status_code=409, detail="Pack with this slug already exists")
    pack = await svc.pack_repo.create(**body.model_dump())
    return _pack_response(pack)


@router.patch("/admin/packs/{pack_id}",
              dependencies=[Depends(require_platform("platform_owner", "platform_admin"))])
async def admin_update_pack(pack_id: str, body: PackUpdateRequest):
    db = get_db()
    svc = WalletService(db)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    ok = await svc.pack_repo.update_by_id(pack_id, updates)
    if not ok:
        raise HTTPException(status_code=404, detail="Pack not found")
    pack = await svc.pack_repo.find_by_id(pack_id)
    return _pack_response(pack)


@router.post("/admin/expire",
             dependencies=[Depends(require_platform("platform_owner", "platform_admin"))])
async def admin_run_expiry(organization_id: str):
    db = get_db()
    svc = WalletService(db)
    result = await svc.process_expiry(organization_id)
    return result
