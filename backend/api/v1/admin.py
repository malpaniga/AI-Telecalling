"""Super Admin API — platform_admin / platform_owner only.

All endpoints require platform-level roles (enforced via require_platform dependency).
Customer-facing data is returned WITHOUT provider details where appropriate.
Admin can see EVERYTHING including provider costs and margins.

Navigation sections per spec:
  /admin/dashboard           — platform overview (MRR, org count, usage)
  /admin/organizations       — list/view/suspend/reactivate orgs
  /admin/subscriptions       — all subscriptions with plan/org info
  /admin/plans               — manage subscription plans
  /admin/calling-packs       — manage calling packs
  /admin/payments            — all payments platform-wide
  /admin/invoices            — all invoices platform-wide
  /admin/wallets             — view/adjust any org wallet
  /admin/phone-numbers       — full phone inventory with provider details
  /admin/voice-profiles      — platform voice profiles
  /admin/providers           — provider health (stub for M26)
  /admin/usage               — platform-wide usage with provider costs
  /admin/revenue             — revenue summary
  /admin/costs               — provider cost summary
  /admin/margins             — gross margin by org / period
  /admin/audit-logs          — system-wide audit trail
  /admin/system-health       — MongoDB, Redis, provider key checks
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, field_validator

from backend.core.auth import CurrentUser, get_current_user
from backend.core.rbac import require_platform
from backend.core.db import get_db
from backend.core.health import check_all

log = logging.getLogger("api.admin")
router = APIRouter(
    prefix="/admin",
    tags=["super-admin"],
    dependencies=[Depends(require_platform())],
)


# ---------------------------------------------------------------------------
# Dashboard — platform overview
# ---------------------------------------------------------------------------
@router.get("/dashboard")
async def admin_dashboard():
    """Platform-level overview: org count, revenue, usage."""
    db = get_db()
    import asyncio
    (
        org_count, sub_stats, usage_stats, recent_orgs
    ) = await asyncio.gather(
        db["organizations"].count_documents({"status": "active"}),
        _sub_stats(db),
        _platform_usage_stats(db),
        db["organizations"].find({}).sort("created_at", -1).limit(5).to_list(5),
    )

    return {
        "organizations": {
            "total_active": org_count,
            "recent": [_org_brief(o) for o in recent_orgs],
        },
        "subscriptions": sub_stats,
        "usage": usage_stats,
    }


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------
@router.get("/organizations")
async def list_organizations(
    org_status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    skip: int = 0,
):
    db = get_db()
    from backend.repositories.organization_repo import OrganizationRepository
    repo = OrganizationRepository(db)
    orgs = await repo.list_all(limit=limit, skip=skip, status=org_status)
    return [_org_full(o) for o in orgs]


@router.get("/organizations/{org_id}")
async def get_organization(org_id: str):
    db = get_db()
    from backend.repositories.organization_repo import OrganizationRepository
    org = await OrganizationRepository(db).find_by_id(org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _org_full(org)


@router.post("/organizations/{org_id}/suspend")
async def suspend_org(org_id: str, reason: str = "policy violation",
                      user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    from backend.repositories.organization_repo import OrganizationRepository
    from backend.repositories.audit_log_repo import AuditLogRepository
    ok = await OrganizationRepository(db).suspend(org_id, reason)
    if not ok:
        raise HTTPException(status_code=404, detail="Organization not found")
    await AuditLogRepository(db).log(
        action="admin.org.suspend", organization_id=org_id,
        user_id=user.user_id, user_email=user.email, user_role=user.role,
        resource_type="organization", resource_id=org_id,
        changes={"reason": reason},
    )
    return {"status": "suspended", "org_id": org_id}


@router.post("/organizations/{org_id}/reactivate")
async def reactivate_org(org_id: str, user: CurrentUser = Depends(get_current_user)):
    db = get_db()
    from backend.repositories.organization_repo import OrganizationRepository
    from backend.repositories.audit_log_repo import AuditLogRepository
    ok = await OrganizationRepository(db).reactivate(org_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Organization not found")
    await AuditLogRepository(db).log(
        action="admin.org.reactivate", organization_id=org_id,
        user_id=user.user_id, user_email=user.email, user_role=user.role,
        resource_type="organization", resource_id=org_id,
    )
    return {"status": "active", "org_id": org_id}


class AdminUpdateOrgPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


@router.post("/organizations/{org_id}/password")
async def update_org_password(
    org_id: str,
    body: AdminUpdateOrgPasswordRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    """Update / reset password for the owner/primary user of an organization."""
    db = get_db()
    from backend.repositories.organization_repo import OrganizationRepository
    from backend.repositories.user_repo import UserRepository
    from backend.repositories.audit_log_repo import AuditLogRepository

    org = await OrganizationRepository(db).find_by_id(org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    user_repo = UserRepository(db)

    # 1. Try finding user matching organization email
    target_user = await user_repo.find_by_email(org.email)

    # 2. If not found or belongs to another org, search users within this org
    if not target_user or target_user.organization_id != org_id:
        users = await user_repo.find_by_org(org_id)
        owner_users = [u for u in users if u.role == "organization_owner"]
        target_user = owner_users[0] if owner_users else (users[0] if users else None)

    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="No user account found associated with this organization",
        )

    await user_repo.update_password(target_user.id, body.new_password)

    ip = request.client.host if request.client else None
    await AuditLogRepository(db).log(
        action="admin.org.update_password",
        organization_id=org_id,
        user_id=user.user_id,
        user_email=user.email,
        user_role=user.role,
        resource_type="user",
        resource_id=target_user.id,
        status="success",
        changes={"target_email": target_user.email},
        ip_address=ip,
    )

    log.info(
        "admin %s updated password for org %s (user %s)",
        user.user_id,
        org_id,
        target_user.email,
    )
    return {
        "status": "success",
        "org_id": org_id,
        "user_email": target_user.email,
        "message": f"Password updated successfully for {target_user.email}",
    }



# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------
@router.get("/subscriptions")
async def list_subscriptions(
    sub_status: Optional[str] = None,
    limit: int = 100, skip: int = 0,
):
    db = get_db()
    from backend.repositories.subscription_repo import SubscriptionRepository
    subs = await SubscriptionRepository(db).list_all(
        status=sub_status, limit=limit, skip=skip
    )
    return [_sub_brief(s) for s in subs]


# ---------------------------------------------------------------------------
# Plans management
# ---------------------------------------------------------------------------
@router.get("/plans")
async def list_plans(include_inactive: bool = False):
    db = get_db()
    from backend.repositories.subscription_repo import SubscriptionPlanRepository
    plans = await SubscriptionPlanRepository(db).list_all(
        include_inactive=include_inactive
    )
    return [_plan_full(p) for p in plans]


@router.patch("/plans/{plan_id}")
async def update_plan(plan_id: str, updates: dict):
    db = get_db()
    from backend.repositories.subscription_repo import SubscriptionPlanRepository
    repo = SubscriptionPlanRepository(db)
    if not await repo.find_by_id(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")
    await repo.update_by_id(plan_id, updates)
    return await repo.find_by_id(plan_id)


# ---------------------------------------------------------------------------
# Calling packs
# ---------------------------------------------------------------------------
@router.get("/calling-packs")
async def list_calling_packs(include_inactive: bool = False):
    db = get_db()
    from backend.repositories.wallet_repo import CallingPackRepository
    packs = await CallingPackRepository(db).list_all(
        include_inactive=include_inactive
    )
    return [_pack_full(p) for p in packs]


@router.post("/calling-packs")
async def admin_create_calling_pack(body: dict):
    from backend.api.v1.wallet import admin_create_pack, PackCreateRequest
    return await admin_create_pack(PackCreateRequest(**body))


@router.patch("/calling-packs/{pack_id}")
async def admin_update_calling_pack(pack_id: str, body: dict):
    from backend.api.v1.wallet import admin_update_pack, PackUpdateRequest
    return await admin_update_pack(pack_id, PackUpdateRequest(**body))


@router.delete("/calling-packs/{pack_id}")
async def admin_delete_calling_pack(pack_id: str):
    from backend.api.v1.wallet import admin_delete_pack
    return await admin_delete_pack(pack_id)


# ---------------------------------------------------------------------------
# Payments & Invoices
# ---------------------------------------------------------------------------
@router.get("/payments")
async def list_payments(
    org_id: Optional[str] = None,
    limit: int = 100, skip: int = 0,
):
    db = get_db()
    from backend.repositories.billing_repo import PaymentRepository
    query: dict = {}
    if org_id:
        query["organization_id"] = org_id
    from pymongo import DESCENDING
    payments = await db["payments"].find(query).sort(
        "created_at", DESCENDING
    ).skip(skip).limit(limit).to_list(limit)
    return [_payment_brief(p) for p in payments]


@router.get("/invoices")
async def list_invoices(
    org_id: Optional[str] = None,
    limit: int = 100, skip: int = 0,
):
    db = get_db()
    from pymongo import DESCENDING
    query: dict = {}
    if org_id:
        query["organization_id"] = org_id
    invoices = await db["invoices"].find(query).sort(
        "created_at", DESCENDING
    ).skip(skip).limit(limit).to_list(limit)
    return [_invoice_brief(i) for i in invoices]


# ---------------------------------------------------------------------------
# Wallets
# ---------------------------------------------------------------------------
@router.get("/wallets/{org_id}")
async def get_org_wallet(org_id: str):
    db = get_db()
    from backend.services.wallet_service import WalletService
    return await WalletService(db).get_wallet_summary(org_id)


@router.post("/wallets/{org_id}/adjust")
async def admin_adjust_wallet(
    org_id: str,
    credits_delta: int,
    reason: str,
    user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    from backend.services.wallet_service import WalletService
    try:
        result = await WalletService(db).admin_adjustment(
            org_id, credits_delta, reason, user.user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


# ---------------------------------------------------------------------------
# Phone numbers
# ---------------------------------------------------------------------------
@router.get("/phone-numbers")
async def list_phone_numbers(
    pn_status: Optional[str] = None,
    provider: Optional[str] = None,
    limit: int = 100, skip: int = 0,
):
    db = get_db()
    from backend.services.phone_number_service import PhoneNumberService
    return await PhoneNumberService(db).list_all_admin(
        status=pn_status, provider=provider, limit=limit, skip=skip
    )


@router.get("/phone-numbers/stats")
async def phone_number_stats():
    db = get_db()
    from backend.services.phone_number_service import PhoneNumberService
    return await PhoneNumberService(db).get_inventory_stats()


# ---------------------------------------------------------------------------
# Voice profiles
# ---------------------------------------------------------------------------
@router.get("/voice-profiles")
async def list_voice_profiles():
    db = get_db()
    from backend.repositories.voice_profile_repo import VoiceProfileRepository
    profiles = await VoiceProfileRepository(db).list_all_admin()
    return [
        {
            "id": p.id,
            "display_name": p.display_name,
            "language": p.language,
            "is_platform": p.is_platform,
            "is_active": p.is_active,
            "active_version": p.active_version,
            "organization_id": p.organization_id,
            "created_at": p.created_at.isoformat(),
        }
        for p in profiles
    ]


# ---------------------------------------------------------------------------
# Usage / Revenue / Costs / Margins
# ---------------------------------------------------------------------------
@router.get("/usage")
async def admin_usage(
    org_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    """Platform usage including provider costs (admin only)."""
    db = get_db()
    from backend.services.usage_service import UsageService
    from datetime import datetime
    fd = datetime.fromisoformat(from_date) if from_date else None
    td = datetime.fromisoformat(to_date) if to_date else None
    return await UsageService(db).get_admin_summary(org_id, fd, td)


@router.get("/revenue")
async def admin_revenue(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    """Platform revenue from subscriptions + calling packs."""
    db = get_db()
    from datetime import datetime
    fd = datetime.fromisoformat(from_date) if from_date else None
    td = datetime.fromisoformat(to_date) if to_date else None

    pipeline = [
        {"$match": _date_match(fd, td)},
        {"$group": {
            "_id": "$event_type",
            "count": {"$sum": 1},
            "total_charge_paise": {"$sum": "$customer_charge_paise"},
            "total_credits": {"$sum": "$credits_consumed"},
        }},
    ]
    rows = await db["usage_events"].aggregate(pipeline).to_list(None)
    by_type = {r["_id"]: r for r in rows}
    total_revenue = sum(r["total_charge_paise"] for r in rows)

    # Subscription revenue from invoices
    sub_pipeline = [
        {"$match": _date_match(fd, td, field="issued_at")},
        {"$group": {"_id": None, "total": {"$sum": "$total_paise"}}},
    ]
    sub_rows = await db["invoices"].aggregate(sub_pipeline).to_list(1)
    sub_revenue = sub_rows[0]["total"] if sub_rows else 0

    return {
        "subscription_revenue_paise": sub_revenue,
        "subscription_revenue_inr": sub_revenue / 100,
        "calling_revenue_paise": total_revenue,
        "calling_revenue_inr": total_revenue / 100,
        "total_revenue_paise": sub_revenue + total_revenue,
        "total_revenue_inr": (sub_revenue + total_revenue) / 100,
        "by_event_type": by_type,
    }


@router.get("/costs")
async def admin_costs(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    """Provider cost breakdown (admin only)."""
    db = get_db()
    from backend.services.usage_service import UsageService
    from datetime import datetime
    fd = datetime.fromisoformat(from_date) if from_date else None
    td = datetime.fromisoformat(to_date) if to_date else None
    summary = await UsageService(db).get_admin_summary(None, fd, td)
    provider_agg = await UsageService(db).get_provider_aggregates()
    return {
        "total_provider_cost_paise": summary["total_provider_cost_paise"],
        "total_provider_cost_inr": summary["total_provider_cost_paise"] / 100,
        "provider_breakdown": provider_agg,
    }


@router.get("/margins")
async def admin_margins(
    org_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    """Gross profit and margin (admin only)."""
    db = get_db()
    from backend.services.usage_service import UsageService
    from datetime import datetime
    fd = datetime.fromisoformat(from_date) if from_date else None
    td = datetime.fromisoformat(to_date) if to_date else None
    return await UsageService(db).get_admin_summary(org_id, fd, td)


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------
@router.get("/audit-logs")
async def list_audit_logs(
    org_id: Optional[str] = None,
    limit: int = 100, skip: int = 0,
):
    db = get_db()
    from backend.repositories.audit_log_repo import AuditLogRepository
    repo = AuditLogRepository(db)
    if org_id:
        logs = await repo.list_for_org(org_id, limit=limit, skip=skip)
    else:
        logs = await repo.list_platform(limit=limit, skip=skip)
    return [
        {
            "id": l.id,
            "action": l.action,
            "organization_id": l.organization_id,
            "user_email": l.user_email,
            "user_role": l.user_role,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "status": l.status,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


# ---------------------------------------------------------------------------
# System health
# ---------------------------------------------------------------------------
@router.get("/system-health")
async def system_health():
    """MongoDB, Redis, and provider key health checks."""
    return await check_all()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _org_brief(o) -> dict:
    oid = str(o.get("_id") if isinstance(o, dict) else o.id)
    name = o.get("name") if isinstance(o, dict) else o.name
    status = o.get("status") if isinstance(o, dict) else o.status
    created = o.get("created_at") if isinstance(o, dict) else o.created_at
    return {
        "id": oid,
        "name": name,
        "status": status,
        "created_at": created.isoformat() if hasattr(created, "isoformat") else str(created),
    }


def _org_full(org) -> dict:
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "email": org.email,
        "status": org.status,
        "is_verified": org.is_verified,
        "max_concurrent_calls": org.max_concurrent_calls,
        "max_campaigns": org.max_campaigns,
        "max_agents": org.max_agents,
        "created_at": org.created_at.isoformat(),
    }


def _sub_brief(s) -> dict:
    return {
        "id": s.id,
        "organization_id": s.organization_id,
        "plan_slug": s.plan_slug,
        "billing_cycle": s.billing_cycle,
        "status": s.status,
        "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
        "cancel_at_period_end": s.cancel_at_period_end,
    }


def _plan_full(p) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "slug": p.slug,
        "price_monthly_paise": p.price_monthly_paise,
        "price_monthly_inr": p.price_monthly_paise / 100,
        "price_yearly_paise": p.price_yearly_paise,
        "max_concurrent_calls": p.max_concurrent_calls,
        "max_campaigns": p.max_campaigns,
        "is_active": p.is_active,
        "is_public": p.is_public,
        "sort_order": p.sort_order,
    }


def _pack_full(p) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "slug": p.slug,
        "description": getattr(p, "description", "") or "",
        "credits": p.credits,
        "bonus_credits": p.bonus_credits,
        "total_credits": getattr(p, "total_credits", p.credits + p.bonus_credits),
        "price_paise": p.price_paise,
        "price_inr": p.price_paise / 100,
        "validity_days": p.validity_days,
        "is_active": p.is_active,
        "is_public": getattr(p, "is_public", True),
        "sort_order": getattr(p, "sort_order", 0),
    }


def _payment_brief(p) -> dict:
    if isinstance(p, dict):
        return {
            "id": str(p.get("_id")),
            "organization_id": p.get("organization_id"),
            "amount_paise": p.get("amount_paise", 0),
            "amount_inr": p.get("amount_paise", 0) / 100,
            "status": p.get("status"),
            "provider": p.get("provider"),
            "paid_at": p.get("paid_at").isoformat() if hasattr(p.get("paid_at"), "isoformat") else str(p.get("paid_at")),
        }
    return {
        "id": p.id, "organization_id": p.organization_id,
        "amount_paise": p.amount_paise, "amount_inr": p.amount_paise / 100,
        "status": p.status, "provider": p.provider,
        "paid_at": p.paid_at.isoformat(),
    }


def _invoice_brief(i) -> dict:
    if isinstance(i, dict):
        return {
            "id": str(i.get("_id")),
            "organization_id": i.get("organization_id"),
            "invoice_number": i.get("invoice_number"),
            "total_paise": i.get("total_paise", 0),
            "total_inr": i.get("total_paise", 0) / 100,
            "status": i.get("status"),
        }
    return {
        "id": i.id, "organization_id": i.organization_id,
        "invoice_number": i.invoice_number,
        "total_paise": i.total_paise, "total_inr": i.total_paise / 100,
        "status": i.status,
    }


def _date_match(
    from_date=None, to_date=None, field: str = "created_at"
) -> dict:
    match: dict = {}
    if from_date or to_date:
        df: dict = {}
        if from_date:
            df["$gte"] = from_date
        if to_date:
            df["$lte"] = to_date
        match[field] = df
    return match


async def _sub_stats(db) -> dict:
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    rows = await db["subscriptions"].aggregate(pipeline).to_list(None)
    by_status = {r["_id"]: r["count"] for r in rows}
    return {
        "total": sum(by_status.values()),
        "active": by_status.get("active", 0),
        "trialing": by_status.get("trialing", 0),
        "cancelled": by_status.get("cancelled", 0),
        "by_status": by_status,
    }


async def _platform_usage_stats(db) -> dict:
    pipeline = [
        {"$group": {
            "_id": None,
            "total_events": {"$sum": 1},
            "total_credits": {"$sum": "$credits_consumed"},
            "total_charge_paise": {"$sum": "$customer_charge_paise"},
            "total_provider_cost_paise": {"$sum": "$provider_cost_paise"},
        }},
    ]
    rows = await db["usage_events"].aggregate(pipeline).to_list(1)
    if not rows:
        return {"total_events": 0, "total_credits": 0,
                "total_charge_paise": 0, "total_provider_cost_paise": 0}
    r = rows[0]
    return {
        "total_events": r["total_events"],
        "total_credits": r["total_credits"],
        "total_charge_paise": r["total_charge_paise"],
        "total_charge_inr": r["total_charge_paise"] / 100,
        "total_provider_cost_paise": r["total_provider_cost_paise"],
        "gross_profit_paise": r["total_charge_paise"] - r["total_provider_cost_paise"],
    }


# ---------------------------------------------------------------------------
# Billing Settings & Manual Payment Request Management
# ---------------------------------------------------------------------------
class UpdateBillingSettingsRequest(BaseModel):
    payment_mode: Optional[str] = None
    admin_upi_id: Optional[str] = None
    admin_payee_name: Optional[str] = None

    @field_validator("payment_mode")
    @classmethod
    def valid_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("manual", "razorpay"):
            raise ValueError("payment_mode must be 'manual' or 'razorpay'")
        return v


class RejectManualRequestSchema(BaseModel):
    reason: str = ""


@router.get("/billing/settings")
async def admin_get_billing_settings():
    """Get full platform payment settings."""
    db = get_db()
    from backend.repositories.billing_repo import PlatformBillingSettingsRepository
    repo = PlatformBillingSettingsRepository(db)
    doc = await repo.get()
    return {
        "payment_mode": doc.payment_mode,
        "admin_upi_id": doc.admin_upi_id,
        "admin_payee_name": doc.admin_payee_name,
        "updated_at": doc.updated_at.isoformat() if hasattr(doc.updated_at, "isoformat") else str(doc.updated_at),
        "updated_by": doc.updated_by,
    }


@router.put("/billing/settings")
async def admin_update_billing_settings(
    body: UpdateBillingSettingsRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Update platform payment mode (razorpay/manual) and UPI payee details."""
    db = get_db()
    from backend.repositories.billing_repo import PlatformBillingSettingsRepository
    repo = PlatformBillingSettingsRepository(db)
    updated = await repo.update(
        payment_mode=body.payment_mode,
        admin_upi_id=body.admin_upi_id,
        admin_payee_name=body.admin_payee_name,
        updated_by=user.user_id,
    )
    return {
        "payment_mode": updated.payment_mode,
        "admin_upi_id": updated.admin_upi_id,
        "admin_payee_name": updated.admin_payee_name,
        "updated_at": updated.updated_at.isoformat() if hasattr(updated.updated_at, "isoformat") else str(updated.updated_at),
        "updated_by": updated.updated_by,
    }


@router.get("/billing/manual-requests")
async def admin_list_manual_requests(
    status: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
):
    """List manual subscription payment requests."""
    db = get_db()
    from backend.repositories.billing_repo import ManualSubscriptionRequestRepository
    from backend.api.v1.billing import _manual_request_response
    repo = ManualSubscriptionRequestRepository(db)
    reqs = await repo.list_all(status=status, limit=limit, skip=skip)
    return [_manual_request_response(r) for r in reqs]


@router.post("/billing/manual-requests/{request_id}/approve")
async def admin_approve_manual_request(
    request_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Approve a manual subscription request, activating the plan and creating orders/invoices."""
    db = get_db()
    from backend.repositories.billing_repo import (
        ManualSubscriptionRequestRepository,
        OrderRepository,
        PaymentRepository,
        InvoiceRepository,
    )
    from backend.services.subscription_service import SubscriptionService
    from backend.models.base import utcnow

    req_repo = ManualSubscriptionRequestRepository(db)
    req = await req_repo.find_by_id(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    # 1. Activate subscription
    sub_svc = SubscriptionService(db)
    try:
        sub = await sub_svc.activate_plan(
            organization_id=req.organization_id,
            plan_id=req.plan_id,
            billing_cycle=req.billing_cycle,
        )
    except Exception as e:
        log.exception("Failed to activate plan for manual request %s: %s", request_id, e)
        raise HTTPException(status_code=400, detail=f"Activation failed: {str(e)}")

    # 2. Record Order marked as paid
    order_repo = OrderRepository(db)
    payment_repo = PaymentRepository(db)
    invoice_repo = InvoiceRepository(db)

    order = await order_repo.create(
        organization_id=req.organization_id,
        order_type="subscription",
        amount_paise=req.amount_paise,
        description=f"{req.plan_name} subscription ({req.billing_cycle}) - Manual UPI",
        provider="manual_upi",
        plan_id=req.plan_id,
        currency=req.currency,
        created_by=req.user_id,
    )
    await order_repo.update_by_id(order.id, {
        "status": "paid",
        "provider_order_id": f"upi_{req.utr_number}",
    })

    # 3. Record Payment
    payment = await payment_repo.create(
        organization_id=req.organization_id,
        order_id=order.id,
        amount_paise=req.amount_paise,
        provider="manual_upi",
        provider_payment_id=f"pay_upi_{req.utr_number}",
        provider_order_id=f"upi_{req.utr_number}",
        created_by=req.user_id,
    )
    await payment_repo.update_by_id(payment.id, {"paid_at": utcnow()})

    # 4. Record Invoice
    invoice = await invoice_repo.create(
        organization_id=req.organization_id,
        order_id=order.id,
        payment_id=payment.id,
        description=order.description,
        subtotal_paise=req.amount_paise,
        tax_paise=0,
        currency=req.currency,
        org_name=req.org_name,
    )
    await invoice_repo.update_by_id(invoice.id, {"paid_at": utcnow()})
    await order_repo.mark_paid(order.id, payment.id, invoice.id)

    # 5. Mark request approved
    await req_repo.set_status(request_id, "approved", reviewed_by=user.user_id)

    log.info("manual subscription request approved id=%s org=%s sub_id=%s", request_id, req.organization_id, sub.id)
    return {"ok": True, "status": "approved", "subscription_id": sub.id}


@router.post("/billing/manual-requests/{request_id}/reject")
async def admin_reject_manual_request(
    request_id: str,
    body: RejectManualRequestSchema,
    user: CurrentUser = Depends(get_current_user),
):
    """Reject a manual subscription request with a reason."""
    db = get_db()
    from backend.repositories.billing_repo import ManualSubscriptionRequestRepository
    req_repo = ManualSubscriptionRequestRepository(db)
    req = await req_repo.find_by_id(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    await req_repo.set_status(
        request_id,
        "rejected",
        reviewed_by=user.user_id,
        rejection_reason=body.reason or "Payment verification failed",
    )
    log.info("manual subscription request rejected id=%s org=%s reason=%s", request_id, req.organization_id, body.reason)
    return {"ok": True, "status": "rejected"}

