"""Subscriptions API.

Customer endpoints:
  GET  /api/v1/subscriptions/plans         — list public plans
  GET  /api/v1/subscriptions/plans/{slug}  — get plan detail
  GET  /api/v1/subscriptions/my            — current org subscription
  GET  /api/v1/subscriptions/my/entitlements — entitlement summary
  POST /api/v1/subscriptions/my/cancel     — cancel at period end
  POST /api/v1/subscriptions/my/change     — upgrade/downgrade

Platform admin endpoints:
  GET    /api/v1/subscriptions/admin/plans         — all plans (incl inactive)
  POST   /api/v1/subscriptions/admin/plans         — create plan
  PATCH  /api/v1/subscriptions/admin/plans/{plan_id} — update plan
  GET    /api/v1/subscriptions/admin/all           — all org subscriptions
  POST   /api/v1/subscriptions/admin/orgs/{org_id}/activate — activate a plan for org
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from backend.core.auth import CurrentUser, get_current_user
from backend.core.rbac import OrgContext, require_org_access, require_platform
from backend.core.db import get_db
from backend.services.subscription_service import SubscriptionService

log = logging.getLogger("api.subscriptions")
router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class PlanCreateRequest(BaseModel):
    name: str
    slug: str
    description: str = ""
    price_monthly_paise: int = 0
    price_yearly_paise: int = 0
    max_concurrent_calls: int = 1
    max_campaigns: int = 1
    max_agents: int = 1
    max_leads_per_campaign: int = 500
    max_team_members: int = 3
    analytics_retention_days: int = 30
    knowledge_base_enabled: bool = False
    api_access: bool = False
    custom_voice_profiles: bool = False
    priority_support: bool = False
    trial_days: int = 0
    is_public: bool = True
    sort_order: int = 0

    @field_validator("price_monthly_paise", "price_yearly_paise")
    @classmethod
    def non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v


class PlanUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_monthly_paise: Optional[int] = None
    price_yearly_paise: Optional[int] = None
    max_concurrent_calls: Optional[int] = None
    max_campaigns: Optional[int] = None
    max_agents: Optional[int] = None
    max_leads_per_campaign: Optional[int] = None
    max_team_members: Optional[int] = None
    analytics_retention_days: Optional[int] = None
    knowledge_base_enabled: Optional[bool] = None
    api_access: Optional[bool] = None
    custom_voice_profiles: Optional[bool] = None
    priority_support: Optional[bool] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    sort_order: Optional[int] = None
    trial_days: Optional[int] = None


class ChangePlanRequest(BaseModel):
    plan_id: str
    billing_cycle: str = "monthly"

    @field_validator("billing_cycle")
    @classmethod
    def valid_cycle(cls, v: str) -> str:
        if v not in ("monthly", "yearly"):
            raise ValueError("billing_cycle must be 'monthly' or 'yearly'")
        return v


class AdminActivateRequest(BaseModel):
    plan_id: str
    billing_cycle: str = "monthly"
    payment_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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
        "analytics_retention_days": plan.analytics_retention_days,
        "knowledge_base_enabled": plan.knowledge_base_enabled,
        "api_access": plan.api_access,
        "custom_voice_profiles": plan.custom_voice_profiles,
        "priority_support": plan.priority_support,
        "trial_days": plan.trial_days,
        "is_active": plan.is_active,
        "is_public": plan.is_public,
        "sort_order": plan.sort_order,
    }


def _sub_response(sub, include_snapshot: bool = True) -> dict:
    d = {
        "id": sub.id,
        "organization_id": sub.organization_id,
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
        "created_at": sub.created_at.isoformat(),
    }
    if include_snapshot:
        d["limits"] = {
            "max_concurrent_calls": sub.snapshot_max_concurrent_calls,
            "max_campaigns": sub.snapshot_max_campaigns,
            "max_agents": sub.snapshot_max_agents,
            "max_leads_per_campaign": sub.snapshot_max_leads_per_campaign,
            "max_team_members": sub.snapshot_max_team_members,
        }
        d["features"] = sub.snapshot_features
    return d


# ---------------------------------------------------------------------------
# Public / customer plan endpoints
# ---------------------------------------------------------------------------
@router.get("/plans")
async def list_plans():
    """List all active public plans (no auth required)."""
    db = get_db()
    svc = SubscriptionService(db)
    plans = await svc.plan_repo.list_public()
    return [_plan_response(p) for p in plans]


@router.get("/plans/{slug}")
async def get_plan(slug: str):
    """Get a single plan by slug (no auth required)."""
    db = get_db()
    svc = SubscriptionService(db)
    plan = await svc.get_plan_by_slug(slug)
    if plan is None or not plan.is_active:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _plan_response(plan)


# ---------------------------------------------------------------------------
# Customer subscription endpoints (scoped to org)
# ---------------------------------------------------------------------------
@router.get("/my")
async def get_my_subscription(
    user: CurrentUser = Depends(get_current_user),
):
    """Get the current organization's subscription."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization associated with this account")
    db = get_db()
    svc = SubscriptionService(db)
    sub = await svc.sub_repo.find_for_org(user.org_id)
    if sub is None:
        return {"has_subscription": False}
    return _sub_response(sub)


@router.get("/my/entitlements")
async def get_my_entitlements(
    user: CurrentUser = Depends(get_current_user),
):
    """Get entitlement summary for the current org."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = SubscriptionService(db)
    return await svc.get_entitlements(user.org_id)


@router.post("/my/cancel")
async def cancel_my_subscription(
    at_period_end: bool = True,
    user: CurrentUser = Depends(get_current_user),
):
    """Cancel subscription (defaults to at period end)."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    # Only org_owner or org_admin can cancel
    if user.role not in ("organization_owner", "organization_admin") and not user.is_platform:
        from backend.core.auth import PermissionError
        raise PermissionError("Only organization owners can cancel subscriptions")
    db = get_db()
    svc = SubscriptionService(db)
    sub = await svc.cancel_subscription(user.org_id, at_period_end=at_period_end)
    if sub is None:
        raise HTTPException(status_code=404, detail="No active subscription to cancel")
    return {
        "status": "cancellation_scheduled" if at_period_end else "cancelled",
        "cancel_at_period_end": at_period_end,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
    }


@router.post("/my/change")
async def change_my_plan(
    body: ChangePlanRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Upgrade or downgrade plan. Payment is handled via M4 (Razorpay)."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    if user.role not in ("organization_owner", "organization_admin") and not user.is_platform:
        from backend.core.auth import PermissionError
        raise PermissionError("Only organization owners can change plans")
    db = get_db()
    svc = SubscriptionService(db)
    try:
        sub = await svc.change_plan(user.org_id, body.plan_id, body.billing_cycle)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _sub_response(sub)


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------
@router.get("/admin/plans",
            dependencies=[Depends(require_platform("platform_owner", "platform_admin"))])
async def admin_list_plans(include_inactive: bool = False):
    """List all plans including inactive (platform admin only)."""
    db = get_db()
    svc = SubscriptionService(db)
    plans = await svc.plan_repo.list_all(include_inactive=include_inactive)
    return [_plan_response(p) for p in plans]


@router.post("/admin/plans", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_platform("platform_owner", "platform_admin"))])
async def admin_create_plan(body: PlanCreateRequest):
    """Create a new subscription plan (platform admin only)."""
    db = get_db()
    svc = SubscriptionService(db)
    if await svc.plan_repo.find_by_slug(body.slug):
        raise HTTPException(status_code=409, detail="A plan with this slug already exists")
    plan = await svc.plan_repo.create(**body.model_dump())
    return _plan_response(plan)


@router.patch("/admin/plans/{plan_id}",
              dependencies=[Depends(require_platform("platform_owner", "platform_admin"))])
async def admin_update_plan(plan_id: str, body: PlanUpdateRequest):
    """Update plan limits, pricing, or feature flags (platform admin only)."""
    db = get_db()
    svc = SubscriptionService(db)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    ok = await svc.plan_repo.update_by_id(plan_id, updates)
    if not ok:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan = await svc.plan_repo.find_by_id(plan_id)
    return _plan_response(plan)


@router.get("/admin/all",
            dependencies=[Depends(require_platform())])
async def admin_list_subscriptions(
    sub_status: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
):
    """List all org subscriptions (platform admin only)."""
    db = get_db()
    svc = SubscriptionService(db)
    subs = await svc.sub_repo.list_all(status=sub_status, limit=limit, skip=skip)
    return [_sub_response(s, include_snapshot=False) for s in subs]


@router.post("/admin/orgs/{org_id}/activate",
             dependencies=[Depends(require_platform("platform_owner", "platform_admin"))])
async def admin_activate_subscription(
    org_id: str,
    body: AdminActivateRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Activate a plan for an org (platform admin — e.g. after offline payment)."""
    db = get_db()
    svc = SubscriptionService(db)
    try:
        sub = await svc.activate_plan(
            organization_id=org_id,
            plan_id=body.plan_id,
            billing_cycle=body.billing_cycle,
            created_by=user.user_id,
            payment_id=body.payment_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _sub_response(sub)
