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

    @field_validator("max_concurrent_calls")
    @classmethod
    def positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_concurrent_calls must be >= 1")
        return v


class UpdateCampaignRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    max_concurrent_calls: Optional[int] = None
    timezone: Optional[str] = None
    calling_hours: Optional[dict[str, Any]] = None
    retry_policy: Optional[dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _require_org(user: CurrentUser) -> str:
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    return user.org_id


def _campaign_response(c) -> dict:
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
        "status": c.status,
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
    if campaign.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft campaigns can be updated")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await svc.repo.update_by_id(campaign_id, updates)
    updated = await svc.get_campaign(campaign_id, org_id)
    return _campaign_response(updated)


@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = CampaignService(get_db())
    try:
        campaign = await svc.start_campaign(campaign_id, org_id)
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
