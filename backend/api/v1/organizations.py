"""Organizations API — RBAC-protected."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from backend.core.auth import CurrentUser, get_current_user
from backend.core.rbac import OrgContext, require_org_access, require_platform
from backend.core.db import get_db
from backend.models.organization import Organization
from backend.repositories.audit_log_repo import AuditLogRepository
from backend.repositories.organization_repo import OrganizationRepository

log = logging.getLogger("api.organizations")
router = APIRouter(prefix="/organizations", tags=["organizations"])


class OrgCreateRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    slug: Optional[str] = None


class OrgUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


def _to_public(org: Organization) -> dict:
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "email": org.email,
        "phone": org.phone,
        "status": org.status,
        "is_verified": org.is_verified,
        "max_concurrent_calls": org.max_concurrent_calls,
        "max_campaigns": org.max_campaigns,
        "max_agents": org.max_agents,
        "created_at": org.created_at.isoformat(),
    }


# ---- Platform-only: create org (platform admins provision orgs directly) ----
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: OrgCreateRequest,
    request: Request,
    user: CurrentUser = Depends(require_platform("platform_owner", "platform_admin")),
):
    """Create a new organization (platform admin only)."""
    db = get_db()
    repo = OrganizationRepository(db)
    audit = AuditLogRepository(db)

    if await repo.find_by_email(body.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Organization with this email already exists")

    org = await repo.create(
        name=body.name,
        email=body.email,
        slug=body.slug,
        phone=body.phone,
        created_by=user.user_id,
    )
    await audit.log(
        action="organization.create",
        organization_id=org.id,
        user_id=user.user_id,
        user_email=user.email,
        user_role=user.role,
        resource_type="organization",
        resource_id=org.id,
        ip_address=request.client.host if request.client else None,
    )
    log.info("platform org created id=%s by=%s", org.id, user.user_id)
    return _to_public(org)


# ---- Platform-only: list all orgs ----
@router.get("", dependencies=[Depends(require_platform())])
async def list_organizations(
    limit: int = 50,
    skip: int = 0,
    org_status: Optional[str] = None,
):
    db = get_db()
    repo = OrganizationRepository(db)
    orgs = await repo.list_all(limit=limit, skip=skip, status=org_status)
    return [_to_public(o) for o in orgs]


# ---- Org member or platform: get one org ----
@router.get("/{org_id}")
async def get_organization(
    org_id: str,
    ctx: OrgContext = Depends(require_org_access("viewer")),
):
    db = get_db()
    repo = OrganizationRepository(db)
    org = await repo.find_by_id(org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _to_public(org)


# ---- Org admin or platform: update org ----
@router.patch("/{org_id}")
async def update_organization(
    org_id: str,
    body: OrgUpdateRequest,
    request: Request,
    ctx: OrgContext = Depends(require_org_access("organization_admin")),
):
    db = get_db()
    repo = OrganizationRepository(db)
    audit = AuditLogRepository(db)

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    ok = await repo.update_by_id(org_id, updates)
    if not ok:
        raise HTTPException(status_code=404, detail="Organization not found")

    await audit.log(
        action="organization.update",
        organization_id=org_id,
        user_id=ctx.user.user_id,
        user_email=ctx.user.email,
        user_role=ctx.user.role,
        resource_type="organization",
        resource_id=org_id,
        changes=updates,
        ip_address=request.client.host if request.client else None,
    )
    updated = await repo.find_by_id(org_id)
    return _to_public(updated)


# ---- Platform admin: suspend / reactivate ----
@router.post("/{org_id}/suspend",
             dependencies=[Depends(require_platform("platform_owner", "platform_admin"))])
async def suspend_organization(org_id: str, reason: str = "policy violation"):
    db = get_db()
    repo = OrganizationRepository(db)
    ok = await repo.suspend(org_id, reason)
    if not ok:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"status": "suspended", "org_id": org_id}


@router.post("/{org_id}/reactivate",
             dependencies=[Depends(require_platform("platform_owner", "platform_admin"))])
async def reactivate_organization(org_id: str):
    db = get_db()
    repo = OrganizationRepository(db)
    ok = await repo.reactivate(org_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"status": "active", "org_id": org_id}
