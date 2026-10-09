"""Customer Billing Portal API.

A unified billing surface that assembles subscription, wallet, payments,
and invoices into one clean customer-facing API.

Provider details, provider costs, and gross margins are NEVER exposed here.

GET  /api/v1/billing-portal/overview       — full billing summary
GET  /api/v1/billing-portal/subscription   — current subscription + renewal info
GET  /api/v1/billing-portal/plans          — available plans for upgrade/downgrade
POST /api/v1/billing-portal/subscribe      — subscribe or change plan (creates order)
POST /api/v1/billing-portal/cancel         — cancel subscription
GET  /api/v1/billing-portal/wallet         — wallet balance + credit lots
GET  /api/v1/billing-portal/packs          — calling packs available to buy
POST /api/v1/billing-portal/packs/{id}/buy — buy a calling pack (creates order)
GET  /api/v1/billing-portal/payments       — payment history
GET  /api/v1/billing-portal/invoices       — invoice list
GET  /api/v1/billing-portal/invoices/{id}  — single invoice (PDF-ready data)
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db

log = logging.getLogger("api.billing_portal")
router = APIRouter(prefix="/billing-portal", tags=["billing-portal"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class SubscribeRequest(BaseModel):
    plan_id: str
    billing_cycle: str = "monthly"

    @field_validator("billing_cycle")
    @classmethod
    def valid_cycle(cls, v: str) -> str:
        if v not in ("monthly", "yearly"):
            raise ValueError("billing_cycle must be 'monthly' or 'yearly'")
        return v


class CancelRequest(BaseModel):
    at_period_end: bool = True
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _require_org(user: CurrentUser) -> str:
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    return user.org_id


def _plan_response(plan) -> dict:
    return {
        "id": plan.id,
        "name": plan.name,
        "slug": plan.slug,
        "description": plan.description,
        "price_monthly_paise": plan.price_monthly_paise,
        "price_monthly_inr": plan.price_monthly_paise / 100,
        "price_yearly_paise": plan.price_yearly_paise,
        "price_yearly_inr": plan.price_yearly_paise / 100,
        "max_concurrent_calls": plan.max_concurrent_calls,
        "max_campaigns": plan.max_campaigns,
        "max_agents": plan.max_agents,
        "max_leads_per_campaign": plan.max_leads_per_campaign,
        "max_team_members": plan.max_team_members,
        "knowledge_base_enabled": plan.knowledge_base_enabled,
        "api_access": plan.api_access,
        "trial_days": plan.trial_days,
    }


def _sub_response(sub) -> dict:
    return {
        "id": sub.id,
        "plan_id": sub.plan_id,
        "plan_slug": sub.plan_slug,
        "billing_cycle": sub.billing_cycle,
        "status": sub.status,
        "started_at": sub.started_at.isoformat(),
        "current_period_start": sub.current_period_start.isoformat(),
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
        "limits": {
            "max_concurrent_calls": sub.snapshot_max_concurrent_calls,
            "max_campaigns": sub.snapshot_max_campaigns,
            "max_agents": sub.snapshot_max_agents,
            "max_leads_per_campaign": sub.snapshot_max_leads_per_campaign,
            "max_team_members": sub.snapshot_max_team_members,
        },
        "features": sub.snapshot_features,
    }


def _payment_response(p) -> dict:
    return {
        "id": p.id,
        "amount_paise": p.amount_paise,
        "amount_inr": p.amount_paise / 100,
        "status": p.status,
        "description": p.description,
        "paid_at": p.paid_at.isoformat(),
        "refunded_paise": p.refunded_paise,
    }


def _invoice_response(i) -> dict:
    return {
        "id": i.id,
        "invoice_number": i.invoice_number,
        "description": i.description,
        "subtotal_paise": i.subtotal_paise,
        "tax_paise": i.tax_paise,
        "total_paise": i.total_paise,
        "total_inr": i.total_paise / 100,
        "status": i.status,
        "org_name": i.org_name,
        "org_email": i.org_email,
        "org_gstin": i.org_gstin,
        "issued_at": i.issued_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/overview")
async def billing_overview(user: CurrentUser = Depends(get_current_user)):
    """Full billing summary: subscription + wallet + recent payments."""
    org_id = _require_org(user)
    db = get_db()

    from backend.services.subscription_service import SubscriptionService
    from backend.services.wallet_service import WalletService
    from backend.repositories.billing_repo import PaymentRepository, InvoiceRepository

    sub_svc = SubscriptionService(db)
    wallet_svc = WalletService(db)

    sub = await sub_svc.sub_repo.find_for_org(org_id)
    wallet_summary = await wallet_svc.get_wallet_summary(org_id)
    recent_payments = await PaymentRepository(db).list_for_org(org_id, limit=5)
    recent_invoices = await InvoiceRepository(db).list_for_org(org_id, limit=3)

    return {
        "organization_id": org_id,
        "subscription": _sub_response(sub) if sub else None,
        "wallet": wallet_summary,
        "recent_payments": [_payment_response(p) for p in recent_payments],
        "recent_invoices": [_invoice_response(i) for i in recent_invoices],
    }


@router.get("/subscription")
async def get_subscription(user: CurrentUser = Depends(get_current_user)):
    """Current subscription with renewal details."""
    org_id = _require_org(user)
    db = get_db()

    from backend.services.subscription_service import SubscriptionService
    svc = SubscriptionService(db)
    sub = await svc.sub_repo.find_for_org(org_id)

    if sub is None:
        return {"has_subscription": False, "subscription": None}

    return {
        "has_subscription": True,
        "subscription": _sub_response(sub),
        "is_active": sub.is_active_or_trialing,
        "days_remaining": _days_remaining(sub.current_period_end),
    }


@router.get("/plans")
async def list_plans_for_upgrade(user: CurrentUser = Depends(get_current_user)):
    """Available plans with current plan highlighted."""
    org_id = _require_org(user)
    db = get_db()

    from backend.services.subscription_service import SubscriptionService
    svc = SubscriptionService(db)
    plans = await svc.plan_repo.list_public()
    current_sub = await svc.sub_repo.find_for_org(org_id)
    current_plan_id = current_sub.plan_id if current_sub else None

    return [
        {**_plan_response(p), "is_current": p.id == current_plan_id}
        for p in plans
    ]


@router.post("/subscribe")
async def subscribe_or_change_plan(
    body: SubscribeRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Subscribe to a plan or change the current plan.
    Creates a Razorpay order. Frontend completes checkout, then calls /billing/verify.
    """
    if user.role not in ("organization_owner", "organization_admin") and not user.is_platform:
        raise HTTPException(status_code=403, detail="Only org owners can manage subscriptions")
    org_id = _require_org(user)
    db = get_db()

    from backend.services.payment_service import PaymentService
    svc = PaymentService(db)
    try:
        result = await svc.create_subscription_order(
            organization_id=org_id,
            plan_id=body.plan_id,
            billing_cycle=body.billing_cycle,
            created_by=user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.post("/cancel")
async def cancel_subscription(
    body: CancelRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Cancel subscription (default: at period end)."""
    if user.role not in ("organization_owner", "organization_admin") and not user.is_platform:
        raise HTTPException(status_code=403, detail="Only org owners can cancel subscriptions")
    org_id = _require_org(user)
    db = get_db()

    from backend.services.subscription_service import SubscriptionService
    svc = SubscriptionService(db)
    sub = await svc.cancel_subscription(
        org_id, at_period_end=body.at_period_end
    )
    if sub is None:
        raise HTTPException(status_code=404, detail="No active subscription to cancel")
    return {
        "status": "cancellation_scheduled" if body.at_period_end else "cancelled",
        "cancel_at_period_end": body.at_period_end,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
    }


@router.get("/wallet")
async def wallet_overview(user: CurrentUser = Depends(get_current_user)):
    """Wallet balance, credit lots, and recent transactions."""
    org_id = _require_org(user)
    db = get_db()

    from backend.services.wallet_service import WalletService
    svc = WalletService(db)
    summary = await svc.get_wallet_summary(org_id)
    recent_txns = await svc.txn_repo.list_for_org(org_id, limit=10)

    return {
        **summary,
        "recent_transactions": [
            {
                "id": t.id,
                "transaction_type": t.transaction_type,
                "credits_delta": t.credits_delta,
                "balance_after": t.balance_after,
                "description": t.description,
                "created_at": t.created_at.isoformat(),
            }
            for t in recent_txns
        ],
    }


@router.get("/packs")
async def list_calling_packs(user: CurrentUser = Depends(get_current_user)):
    """Public calling packs available to purchase."""
    _require_org(user)
    db = get_db()

    from backend.services.wallet_service import WalletService
    svc = WalletService(db)
    packs = await svc.pack_repo.list_public()
    return [
        {
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
        }
        for p in packs
    ]


@router.post("/packs/{pack_id}/buy")
async def buy_calling_pack(
    pack_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a payment order to buy a calling pack."""
    org_id = _require_org(user)
    db = get_db()

    from backend.services.payment_service import PaymentService
    svc = PaymentService(db)
    try:
        result = await svc.create_calling_pack_order(
            organization_id=org_id,
            calling_pack_id=pack_id,
            created_by=user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/payments")
async def payment_history(
    limit: int = 50,
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    """Payment history for the org."""
    org_id = _require_org(user)
    db = get_db()

    from backend.repositories.billing_repo import PaymentRepository
    repo = PaymentRepository(db)
    payments = await repo.list_for_org(org_id, limit=limit, skip=skip)
    return [_payment_response(p) for p in payments]


@router.get("/invoices")
async def list_invoices(
    limit: int = 50,
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    """Invoice list for the org."""
    org_id = _require_org(user)
    db = get_db()

    from backend.repositories.billing_repo import InvoiceRepository
    repo = InvoiceRepository(db)
    invoices = await repo.list_for_org(org_id, limit=limit, skip=skip)
    return [_invoice_response(i) for i in invoices]


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a single invoice with all fields (for PDF generation)."""
    org_id = _require_org(user)
    db = get_db()

    from backend.repositories.billing_repo import InvoiceRepository
    repo = InvoiceRepository(db)
    invoice = await repo.find_by_id(invoice_id)
    if invoice is None or invoice.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _invoice_response(invoice)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _days_remaining(period_end) -> Optional[int]:
    if period_end is None:
        return None
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    ep = period_end
    if ep.tzinfo is None:
        from datetime import timezone as _tz
        ep = ep.replace(tzinfo=_tz.utc)
    delta = ep - now
    return max(0, delta.days)
