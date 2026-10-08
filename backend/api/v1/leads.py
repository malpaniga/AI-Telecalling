"""Leads API.

GET    /api/v1/leads              — list leads
POST   /api/v1/leads              — create single lead
GET    /api/v1/leads/{id}         — get lead
PATCH  /api/v1/leads/{id}         — update lead
DELETE /api/v1/leads/{id}         — delete lead
POST   /api/v1/leads/import       — bulk import (CSV/XLSX/JSON)
GET    /api/v1/leads/dnc          — list DNC entries
POST   /api/v1/leads/dnc          — add to DNC
DELETE /api/v1/leads/dnc/{phone}  — remove from DNC
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.services.lead_service import LeadService

log = logging.getLogger("api.leads")
router = APIRouter(prefix="/leads", tags=["leads"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class CreateLeadRequest(BaseModel):
    phone: str
    name: Optional[str] = None
    email: Optional[str] = None
    custom_fields: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    source: str = "manual"


class UpdateLeadRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    score: Optional[int] = None
    qualification: Optional[dict[str, Any]] = None
    custom_fields: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    next_contact_at: Optional[str] = None


class DNCAddRequest(BaseModel):
    phone: str
    reason: Optional[str] = None
    source: str = "manual"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _require_org(user: CurrentUser) -> str:
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    return user.org_id


def _lead_response(lead) -> dict:
    return {
        "id": lead.id,
        "organization_id": lead.organization_id,
        "campaign_id": lead.campaign_id,
        "phone": lead.phone,
        "name": lead.name,
        "email": lead.email,
        "status": lead.status,
        "score": lead.score,
        "qualification": lead.qualification,
        "custom_fields": lead.custom_fields,
        "tags": lead.tags,
        "attempts": lead.attempts,
        "source": lead.source,
        "last_contact_at": lead.last_contact_at.isoformat() if lead.last_contact_at else None,
        "next_contact_at": lead.next_contact_at.isoformat() if lead.next_contact_at else None,
        "import_batch_id": lead.import_batch_id,
        "created_at": lead.created_at.isoformat(),
        "updated_at": lead.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Lead CRUD
# ---------------------------------------------------------------------------
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_lead(
    body: CreateLeadRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = LeadService(get_db())
    try:
        lead = await svc.create_lead(
            organization_id=org_id,
            phone=body.phone,
            name=body.name,
            email=body.email,
            custom_fields=body.custom_fields,
            tags=body.tags,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _lead_response(lead)


@router.get("")
async def list_leads(
    campaign_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = LeadService(get_db())
    leads, total = await svc.list_leads(
        org_id, campaign_id=campaign_id, status=status,
        limit=limit, skip=skip,
    )
    return {
        "total": total,
        "limit": limit,
        "skip": skip,
        "leads": [_lead_response(l) for l in leads],
    }


@router.get("/dnc")
async def list_dnc(
    limit: int = 100,
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = LeadService(get_db())
    entries = await svc.dnc_repo.list_for_org(org_id, limit=limit, skip=skip)
    return [{"phone": e.phone, "reason": e.reason, "added_at": e.added_at.isoformat()} for e in entries]


@router.post("/dnc", status_code=status.HTTP_201_CREATED)
async def add_to_dnc(
    body: DNCAddRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = LeadService(get_db())
    added = await svc.add_to_dnc(
        org_id, body.phone, reason=body.reason,
        added_by=user.user_id, source=body.source,
    )
    return {"added": added, "phone": body.phone}


@router.delete("/dnc/{phone}")
async def remove_from_dnc(
    phone: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = LeadService(get_db())
    removed = await svc.dnc_repo.remove(org_id, phone)
    if not removed:
        raise HTTPException(status_code=404, detail="Phone not on DNC list")
    return {"removed": True, "phone": phone}


@router.post("/import")
async def import_leads(
    file: UploadFile = File(...),
    column_mapping: Optional[str] = Form(default=None),
    campaign_id: Optional[str] = Form(default=None),
    tags: Optional[str] = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
):
    """Import leads from CSV, XLSX, or JSON file."""
    org_id = _require_org(user)

    content = await file.read()
    filename = file.filename or ""

    # Detect format from extension
    if filename.endswith(".csv"):
        fmt = "csv"
    elif filename.endswith((".xlsx", ".xls")):
        fmt = "xlsx"
    elif filename.endswith(".json"):
        fmt = "json"
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Use .csv, .xlsx, or .json",
        )

    # Parse column_mapping JSON string if provided
    mapping = None
    if column_mapping:
        import json
        try:
            mapping = json.loads(column_mapping)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid column_mapping JSON")

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    svc = LeadService(get_db())
    result = await svc.import_leads(
        organization_id=org_id,
        content=content,
        file_format=fmt,
        column_mapping=mapping,
        campaign_id=campaign_id,
        tags=tag_list,
    )
    return result


@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = LeadService(get_db())
    lead = await svc.get_lead(lead_id, org_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _lead_response(lead)


@router.patch("/{lead_id}")
async def update_lead(
    lead_id: str,
    body: UpdateLeadRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = LeadService(get_db())
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    lead = await svc.update_lead(lead_id, org_id, updates)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _lead_response(lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = LeadService(get_db())
    deleted = await svc.delete_lead(lead_id, org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lead not found")
