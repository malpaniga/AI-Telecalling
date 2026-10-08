"""Users API — signup, basic user management.

Full auth (JWT, RBAC) implemented in M2. These endpoints provide scaffolding
for the user model and repository with minimal auth guards for now.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from backend.core.db import get_db
from backend.models.user import ALL_ROLES, ORGANIZATION_ROLES
from backend.repositories.user_repo import UserRepository
from backend.repositories.organization_repo import OrganizationRepository
from backend.repositories.audit_log_repo import AuditLogRepository

log = logging.getLogger("api.users")
router = APIRouter(prefix="/users", tags=["users"])


class UserCreateRequest(BaseModel):
    organization_id: Optional[str] = None
    email: str
    password: str
    role: str = "organization_owner"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreateRequest, request: Request):
    """Create a user. Full auth/RBAC enforcement in M2."""
    if body.role not in ALL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Valid roles: {sorted(ALL_ROLES)}",
        )

    db = get_db()
    user_repo = UserRepository(db)
    audit = AuditLogRepository(db)

    # Check org exists (if provided)
    if body.organization_id:
        org_repo = OrganizationRepository(db)
        org = await org_repo.find_by_id(body.organization_id)
        if org is None:
            raise HTTPException(status_code=404, detail="Organization not found")

    # Check duplicate email
    if await user_repo.find_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = await user_repo.create(
        email=body.email,
        password=body.password,
        role=body.role,
        organization_id=body.organization_id,
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
    )

    await audit.log(
        action="user.create",
        organization_id=body.organization_id,
        resource_type="user",
        resource_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    log.info("user created id=%s email=%s role=%s", user.id, user.email, user.role)
    return {
        "id": user.id,
        "organization_id": user.organization_id,
        "email": user.email,
        "role": user.role,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "created_at": user.created_at.isoformat(),
    }


@router.get("/{user_id}")
async def get_user(user_id: str):
    db = get_db()
    repo = UserRepository(db)
    user = await repo.find_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
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
