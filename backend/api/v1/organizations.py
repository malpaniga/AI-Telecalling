"""Organizations API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from backend.core.db import get_db
from backend.models.organization import Organization, OrganizationPublic
from backend.repositories.organization_repo import OrganizationRepository
from backend.repositories.audit_log_repo import AuditLogRepository

log = logging.getLogger("api.organizations")
router = APIRouter(prefix="/organizations", tags=["organizations"])


class OrgCreateRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    slug: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(body: OrgCreateRequest, request: Request):
    """Create a new organization (platform admin only — auth enforced in M2)."""
    db = get_db()
    repo = OrganizationRepository(db)
    audit = AuditLogRepository(db)

    # Check duplicate email
    if await repo.find_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organization with this email already exists",
        )

    org = await repo.create(
        name=body.name,
        email=body.email,
        slug=body.slug,
        phone=body.phone,
    )

    await audit.log(
        action="organization.create",
        organization_id=org.id,
        resource_type="organization",
        resource_id=org.id,
        ip_address=request.client.host if request.client else None,
    )

    log.info("organization created id=%s slug=%s", org.id, org.slug)
    return _to_public(org)


@router.get("/{org_id}")
async def get_organization(org_id: str):
    """Get organization by ID."""
    db = get_db()
    repo = OrganizationRepository(db)
    org = await repo.find_by_id(org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _to_public(org)


@router.get("")
async def list_organizations(limit: int = 50, skip: int = 0, status: Optional[str] = None):
    """List all organizations (platform admin only — auth enforced in M2)."""
    db = get_db()
    repo = OrganizationRepository(db)
    orgs = await repo.list_all(limit=limit, skip=skip, status=status)
    return [_to_public(o) for o in orgs]


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
        "created_at": org.created_at.isoformat(),
    }
