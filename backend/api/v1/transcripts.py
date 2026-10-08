"""Transcripts API.

GET  /api/v1/transcripts              — list transcripts for org
GET  /api/v1/transcripts/{call_id}    — get transcript for a specific call
POST /api/v1/transcripts/{call_id}/process — trigger post-call processing
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.repositories.transcript_repo import TranscriptRepository
from backend.services.post_call_service import PostCallService

log = logging.getLogger("api.transcripts")
router = APIRouter(prefix="/transcripts", tags=["transcripts"])


class ProcessCallRequest(BaseModel):
    turns: Optional[list[dict]] = None
    call_state: Optional[dict] = None
    actual_credits: int = 0
    force: bool = False


def _require_org(user: CurrentUser) -> str:
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    return user.org_id


def _transcript_response(t) -> dict:
    return {
        "id": t.id,
        "call_id": t.call_id,
        "organization_id": t.organization_id,
        "lead_id": t.lead_id,
        "campaign_id": t.campaign_id,
        "turn_count": t.turn_count,
        "turns": [
            {
                "role": turn.role,
                "text": turn.text,
                "stage": turn.stage,
                "latency_ms": turn.latency_ms,
                "ts": turn.ts.isoformat() if turn.ts else None,
            }
            for turn in t.turns
        ] if hasattr(t, 'turns') and t.turns else [],
        "summary": t.summary,
        "qualification": t.qualification,
        "score": t.score,
        "outcome": t.outcome,
        "processing_status": t.processing_status,
        "processed_at": t.processed_at.isoformat() if t.processed_at else None,
        "language": t.language,
        "created_at": t.created_at.isoformat(),
    }


@router.get("")
async def list_transcripts(
    campaign_id: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    repo = TranscriptRepository(get_db())
    transcripts = await repo.list_for_org(
        org_id, campaign_id=campaign_id, limit=limit, skip=skip
    )
    return [_transcript_response(t) for t in transcripts]


@router.get("/{call_id}")
async def get_transcript(
    call_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    repo = TranscriptRepository(get_db())
    transcript = await repo.get_for_call(call_id, org_id)
    if transcript is None:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return _transcript_response(transcript)


@router.post("/{call_id}/process")
async def process_call(
    call_id: str,
    body: ProcessCallRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Trigger post-call processing pipeline for a completed call."""
    org_id = _require_org(user)
    svc = PostCallService(get_db())
    result = await svc.process(
        call_id=call_id,
        organization_id=org_id,
        turns=body.turns,
        call_state=body.call_state,
        actual_credits=body.actual_credits,
        force=body.force,
    )
    return result
