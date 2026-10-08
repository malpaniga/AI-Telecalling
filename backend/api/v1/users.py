"""Users API — RBAC-protected."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from backend.core.auth import CurrentUser, get_current_user
from backend.core.rbac import OrgContext, require_org_access, require_platform, assert_org_access
from backend.core.db import get_db
from backend.models.user import ALL_ROLES, ORGANIZATION_ROLES
from backend.repositories.audit_log_repo import AuditLogRepository
from backend.repositories.organization_repo import OrganizationRepository
from backend.repositories.user_repo import UserRepository

log = logging.getLogger("api.users")
router = APIRouter(prefix="/users", tags=["users"])


class UserInviteRequest(BaseModel):
    """Invite a user to an organization."""
    email: str
    password: str
    role: str = "agent"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None


def _to_public(user) -> dict:
    return {
        "id": user.id,
        "organization_id": user.organization_id,
        "email": user.email,
        "role": user.role,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_email_verified": user.is_email_verified,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat(),
    }


# ---- Org admin: invite user to org ----
@router.post("/org/{org_id}/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    org_id: str,
    body: UserInviteRequest,
    request: Request,
    ctx: OrgContext = Depends(require_org_access("organization_admin")),
):
    """Invite a user to the organization (org_admin or higher)."""
    # Only org roles can be assigned via invite
    if body.role not in ORGANIZATION_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Org roles: {sorted(ORGANIZATION_ROLES)}",
        )

    db = get_db()
    user_repo = UserRepository(db)
    audit = AuditLogRepository(db)

    if await user_repo.find_by_email(body.email):
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    user = await user_repo.create(
        email=body.email,
        password=body.password,
        role=body.role,
        organization_id=org_id,
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
    )

    await audit.log(
        action="user.invite",
        organization_id=org_id,
        user_id=ctx.user.user_id,
        user_email=ctx.user.email,
        user_role=ctx.user.role,
        resource_type="user",
        resource_id=user.id,
        changes={"email": body.email, "role": body.role},
        ip_address=request.client.host if request.client else None,
    )
    log.info("user invited id=%s org=%s by=%s", user.id, org_id, ctx.user.user_id)
    return _to_public(user)


# ---- Org member: list users in org ----
@router.get("/org/{org_id}")
async def list_org_users(
    org_id: str,
    ctx: OrgContext = Depends(require_org_access("viewer")),
):
    db = get_db()
    repo = UserRepository(db)
    users = await repo.find_by_org(org_id)
    return [_to_public(u) for u in users]


# ---- Self or org_admin: get a user ----
@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    repo = UserRepository(db)
    user = await repo.find_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Must be self, org_admin of same org, or platform
    is_self = current_user.user_id == user_id
    is_org_admin = (
        current_user.org_id == user.organization_id
        and current_user.role in ("organization_admin", "organization_owner")
    )
    if not (is_self or is_org_admin or current_user.is_platform):
        from backend.core.auth import PermissionError
        raise PermissionError("Cannot view this user")

    return _to_public(user)


# ---- Self or org_admin: update user ----
@router.patch("/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    repo = UserRepository(db)
    audit = AuditLogRepository(db)

    user = await repo.find_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    is_self = current_user.user_id == user_id
    is_org_admin = (
        current_user.org_id == user.organization_id
        and current_user.role in ("organization_admin", "organization_owner")
    )
    if not (is_self or is_org_admin or current_user.is_platform):
        from backend.core.auth import PermissionError
        raise PermissionError("Cannot update this user")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}

    # Only org_admin can change roles
    if "role" in updates and not (is_org_admin or current_user.is_platform):
        raise HTTPException(status_code=403, detail="Only admins can change roles")

    if updates:
        await repo.update_by_id(user_id, updates)
        await audit.log(
            action="user.update",
            organization_id=user.organization_id,
            user_id=current_user.user_id,
            user_email=current_user.email,
            user_role=current_user.role,
            resource_type="user",
            resource_id=user_id,
            changes=updates,
            ip_address=request.client.host if request.client else None,
        )

    updated = await repo.find_by_id(user_id)
    return _to_public(updated)


# ---- Org admin: deactivate user ----
@router.delete("/{user_id}")
async def deactivate_user(
    user_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    db = get_db()
    repo = UserRepository(db)
    audit = AuditLogRepository(db)

    user = await repo.find_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Can't deactivate yourself
    if current_user.user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    is_org_admin = (
        current_user.org_id == user.organization_id
        and current_user.role in ("organization_admin", "organization_owner")
    )
    if not (is_org_admin or current_user.is_platform):
        from backend.core.auth import PermissionError
        raise PermissionError("Cannot deactivate this user")

    await repo.deactivate(user_id)
    await audit.log(
        action="user.deactivate",
        organization_id=user.organization_id,
        user_id=current_user.user_id,
        user_email=current_user.email,
        user_role=current_user.role,
        resource_type="user",
        resource_id=user_id,
        ip_address=request.client.host if request.client else None,
    )
    return {"status": "deactivated", "user_id": user_id}
