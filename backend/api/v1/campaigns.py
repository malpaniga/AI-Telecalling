"""Campaigns API.

POST /api/v1/campaigns              — create campaign (draft)
GET  /api/v1/campaigns              — list campaigns
GET  /api/v1/campaigns/{id}         — get campaign
PATCH /api/v1/campaigns/{id}        — update draft campaign config
POST /api/v1/campaigns/{id}/start   — start (draft → running)
POST /api/v1/campaigns/{id}/pause   — pause (running → paused)
POST /api/v1/campaigns/{id}/resume  — resume (paused → running)
POST /api/v1/campaigns/{id}/cancel  — cancel
GET  /api/v1/campaigns/{id}/stats   — runtime stats
"""

import logging
import re
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.services.campaign_service import CampaignService

log = logging.getLogger("api.campaigns")
router = APIRouter(prefix="/campaigns", tags=["campaigns"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class CreateCampaignRequest(BaseModel):
    name: str
    agent_id: str
    agent_version: int
    voice_profile_id: str
    voice_profile_version: int
    calling_number_id: str
    calling_number: str
    max_concurrent_calls: int = 1
    timezone: str = "Asia/Kolkata"
    description: str = ""
    lead_filter: Optional[dict[str, Any]] = None
    calling_hours: Optional[dict[str, Any]] = None
    retry_policy: Optional[dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    qualification_schema: Optional[list[dict[str, Any]]] = None

    @field_validator("max_concurrent_calls")
    @classmethod
    def positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_concurrent_calls must be >= 1")
        return v


class EnrollCampaignLeadsRequest(BaseModel):
    lead_ids: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    city: Optional[str] = None
    status: Optional[str] = None
    all_contacts: bool = False


class UpdateCampaignRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    max_concurrent_calls: Optional[int] = None
    timezone: Optional[str] = None
    calling_hours: Optional[dict[str, Any]] = None
    retry_policy: Optional[dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    agent_id: Optional[str] = None
    calling_number_id: Optional[str] = None
    calling_number: Optional[str] = None
    qualification_schema: Optional[list[dict[str, Any]]] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _require_org(user: CurrentUser) -> str:
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    return user.org_id


def _campaign_response(c) -> dict:
    calling_hours_data = None
    if getattr(c, "calling_hours", None):
        if hasattr(c.calling_hours, "model_dump"):
            calling_hours_data = c.calling_hours.model_dump()
        elif isinstance(c.calling_hours, dict):
            calling_hours_data = c.calling_hours

    retry_policy_data = None
    if getattr(c, "retry_policy", None):
        if hasattr(c.retry_policy, "model_dump"):
            retry_policy_data = c.retry_policy.model_dump()
        elif isinstance(c.retry_policy, dict):
            retry_policy_data = c.retry_policy

    return {
        "id": c.id,
        "organization_id": c.organization_id,
        "name": c.name,
        "description": c.description,
        "agent_id": c.agent_id,
        "agent_version": c.agent_version,
        "voice_profile_id": c.voice_profile_id,
        "voice_profile_version": c.voice_profile_version,
        "calling_number_id": c.calling_number_id,
        "calling_number": c.calling_number,
        "max_concurrent_calls": c.max_concurrent_calls,
        "timezone": c.timezone,
        "calling_hours": calling_hours_data,
        "retry_policy": retry_policy_data,
        "status": c.status,
        "qualification_schema": getattr(c, "qualification_schema", []) or [],
        "total_leads": c.total_leads,
        "leads_dialed": c.leads_dialed,
        "leads_connected": c.leads_connected,
        "leads_completed": c.leads_completed,
        "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "completed_at": c.completed_at.isoformat() if c.completed_at else None,
        "cancelled_at": c.cancelled_at.isoformat() if c.cancelled_at else None,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CreateCampaignRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CampaignService(get_db())
    campaign = await svc.create_campaign(
        organization_id=org_id,
        name=body.name,
        agent_id=body.agent_id,
        agent_version=body.agent_version,
        voice_profile_id=body.voice_profile_id,
        voice_profile_version=body.voice_profile_version,
        calling_number_id=body.calling_number_id,
        calling_number=body.calling_number,
        max_concurrent_calls=body.max_concurrent_calls,
        timezone=body.timezone,
        description=body.description,
        lead_filter=body.lead_filter,
        calling_hours=body.calling_hours,
        retry_policy=body.retry_policy,
        scheduled_at=body.scheduled_at,
        created_by=user.user_id,
        qualification_schema=body.qualification_schema,
    )
    return _campaign_response(campaign)


@router.get("")
async def list_campaigns(
    status: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CampaignService(get_db())
    campaigns = await svc.list_campaigns(org_id, status=status, limit=limit, skip=skip)
    return [_campaign_response(c) for c in campaigns]


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CampaignService(get_db())
    campaign = await svc.get_campaign(campaign_id, org_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if not getattr(campaign, "qualification_schema", None):
        schema = await svc.get_agent_qualification_schema(campaign.agent_id, org_id)
        if schema:
            campaign.qualification_schema = schema
    return _campaign_response(campaign)


@router.patch("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    body: UpdateCampaignRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CampaignService(get_db())
    campaign = await svc.get_campaign(campaign_id, org_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == "running":
        raise HTTPException(status_code=400, detail="Cannot edit a running campaign. Please pause it first.")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}

    # Resolve agent version if agent_id updated
    if updates.get("agent_id") and updates["agent_id"] != campaign.agent_id:
        agent_doc = await svc.db.agents.find_one({"_id": updates["agent_id"]})
        if not agent_doc:
            raise HTTPException(status_code=404, detail="Agent not found")
        updates["agent_version"] = agent_doc.get("active_version") or 1
        if agent_doc.get("voice_profile_id"):
            updates["voice_profile_id"] = agent_doc["voice_profile_id"]
            vp_doc = await svc.db.voice_profiles.find_one({"_id": agent_doc["voice_profile_id"]})
            if vp_doc:
                updates["voice_profile_version"] = vp_doc.get("active_version") or 1

    # Resolve calling number if calling_number_id updated
    if updates.get("calling_number_id") and not updates.get("calling_number"):
        pn_doc = await svc.db.phone_numbers.find_one({"_id": updates["calling_number_id"]})
        if pn_doc:
            updates["calling_number"] = pn_doc.get("number")

    if "calling_hours" in updates and updates["calling_hours"]:
        from backend.models.campaign import CallingHours
        try:
            updates["calling_hours"] = CallingHours(**updates["calling_hours"]).model_dump()
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=f"Invalid calling_hours: {exc}")

    if updates:
        await svc.repo.update_by_id(campaign_id, updates)
    updated = await svc.get_campaign(campaign_id, org_id)
    return _campaign_response(updated)


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CampaignService(get_db())
    try:
        deleted = await svc.delete_campaign(campaign_id, org_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return {"deleted": True, "campaign_id": campaign_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{campaign_id}/preflight")
async def preflight_campaign(
    campaign_id: str,
    skip_calling_hours: bool = False,
    user: CurrentUser = Depends(get_current_user),
):
    """Run pre-flight validation without starting the campaign."""
    org_id = _require_org(user)
    svc = CampaignService(get_db())
    campaign = await svc.get_campaign(campaign_id, org_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    from backend.services.preflight_service import PreflightService
    preflight = PreflightService(get_db())
    result = await preflight.run(campaign, skip_calling_hours=skip_calling_hours)
    return result.to_dict()


@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: str,
    skip_preflight: bool = False,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CampaignService(get_db())
    try:
        campaign = await svc.start_campaign(campaign_id, org_id,
                                            skip_preflight=skip_preflight)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _campaign_response(campaign)


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CampaignService(get_db())
    try:
        campaign = await svc.pause_campaign(campaign_id, org_id)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _campaign_response(campaign)


@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CampaignService(get_db())
    try:
        campaign = await svc.resume_campaign(campaign_id, org_id)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _campaign_response(campaign)


@router.post("/{campaign_id}/cancel")
async def cancel_campaign(
    campaign_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CampaignService(get_db())
    try:
        campaign = await svc.cancel_campaign(campaign_id, org_id)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _campaign_response(campaign)


@router.get("/{campaign_id}/stats")
async def campaign_stats(
    campaign_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CampaignService(get_db())
    try:
        return await svc.get_stats(campaign_id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Campaign Leads Management Endpoints
# ---------------------------------------------------------------------------
@router.get("/{campaign_id}/leads")
async def list_campaign_leads(
    campaign_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    db = get_db()
    from backend.repositories.campaign_repo import CampaignRepository
    from backend.repositories.campaign_lead_repo import CampaignLeadRepository

    campaign = await CampaignRepository(db).get_for_org(campaign_id, org_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    repo = CampaignLeadRepository(db)
    docs, total = await repo.list_for_campaign(campaign_id, org_id, status=status, limit=limit, skip=skip)

    # Fetch corresponding lead details
    lead_ids = [d["lead_id"] for d in docs]
    leads_cursor = db["leads"].find({"_id": {"$in": lead_ids}, "organization_id": org_id})
    leads_list = await leads_cursor.to_list(length=len(lead_ids))
    lead_map = {str(l["_id"]): l for l in leads_list}

    items = []
    for d in docs:
        lid = d["lead_id"]
        master = lead_map.get(lid, {})
        items.append({
            "id": str(d.get("_id", "")),
            "lead_id": lid,
            "campaign_id": campaign_id,
            "phone": d.get("phone") or master.get("phone", ""),
            "name": master.get("name") or d.get("custom_fields", {}).get("user_name"),
            "email": master.get("email"),
            "status": d.get("status", "new"),
            "attempts": d.get("attempts", 0),
            "max_attempts": d.get("max_attempts", 3),
            "last_called_at": d["last_called_at"].isoformat() if d.get("last_called_at") else None,
            "next_attempt_at": d["next_attempt_at"].isoformat() if d.get("next_attempt_at") else None,
            "disposition": d.get("disposition"),
            "custom_fields": d.get("custom_fields", {}),
            "created_at": d["created_at"].isoformat() if d.get("created_at") else None,
        })

    return {"items": items, "total": total}


@router.post("/{campaign_id}/leads")
async def enroll_campaign_leads(
    campaign_id: str,
    body: EnrollCampaignLeadsRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    db = get_db()
    from backend.repositories.campaign_repo import CampaignRepository
    from backend.repositories.campaign_lead_repo import CampaignLeadRepository

    campaign = await CampaignRepository(db).get_for_org(campaign_id, org_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query: dict[str, Any] = {"organization_id": org_id}
    if body.all_contacts:
        pass
    elif body.lead_ids:
        query["_id"] = {"$in": body.lead_ids}
    else:
        has_filter = False
        conditions = []
        if body.tags:
            tag_list = [t.strip() for t in body.tags if isinstance(t, str) and t.strip()]
            if tag_list:
                conditions.append({"tags": {"$in": tag_list}})
                has_filter = True
        if body.city:
            c_str = str(body.city).strip()
            if c_str:
                escaped_c = re.escape(c_str)
                conditions.append({
                    "$or": [
                        {"custom_fields.city": {"$regex": f"^{escaped_c}$", "$options": "i"}},
                        {"custom_fields.Town": {"$regex": f"^{escaped_c}$", "$options": "i"}},
                    ]
                })
                has_filter = True
        if body.status:
            conditions.append({"status": body.status})
            has_filter = True

        if not has_filter:
            raise HTTPException(
                status_code=400,
                detail="Must specify lead_ids, tags, city, status, or all_contacts=true",
            )

        if len(conditions) == 1:
            query.update(conditions[0])
        elif len(conditions) > 1:
            query["$and"] = conditions

    cursor = db["leads"].find(query)
    leads = await cursor.to_list(length=5000)
    if not leads:
        return {"enrolled": 0, "skipped": 0}

    items = [
        {
            "lead_id": str(l["_id"]),
            "phone": l["phone"],
            "custom_fields": l.get("custom_fields") or {},
        }
        for l in leads
    ]

    repo = CampaignLeadRepository(db)
    res = await repo.bulk_enroll(campaign_id, org_id, items)
    return res


@router.delete("/{campaign_id}/leads/{lead_id}")
async def remove_campaign_lead(
    campaign_id: str,
    lead_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    db = get_db()
    from backend.repositories.campaign_lead_repo import CampaignLeadRepository
    repo = CampaignLeadRepository(db)
    removed = await repo.remove_lead(campaign_id, lead_id, org_id)
    return {"removed": removed}
