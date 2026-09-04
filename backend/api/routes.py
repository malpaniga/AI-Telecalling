"""REST API backing the Next.js dashboard.

All routes are read-only and namespaced under /api. Data comes from the same
Postgres the call loop writes to.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_session
from backend.memory import repository as repo

router = APIRouter(prefix="/api", tags=["dashboard"])


# ---- response schemas ----
class Stats(BaseModel):
    total_calls: int
    total_leads: int
    booked: int
    qualified: int
    avg_score: float
    avg_latency_ms: int | None
    outcomes: dict[str, int]


class CallRow(BaseModel):
    id: str
    direction: str
    status: str
    outcome: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_s: int | None
    avg_latency_ms: int | None
    lead_city: str | None
    lead_budget: str | None
    lead_score: int | None
    lead_status: str | None


class TurnOut(BaseModel):
    role: str
    text: str
    stage: str | None
    latency_ms: int | None
    ts: datetime | None


class CallDetail(BaseModel):
    id: str
    direction: str
    status: str
    outcome: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_s: int | None
    avg_latency_ms: int | None
    turns: list[TurnOut]


class LeadOut(BaseModel):
    id: str
    phone: str | None
    city: str | None
    budget: str | None
    timeline: str | None
    property_type: str | None
    score: int
    status: str
    created_at: datetime | None


# ---- routes ----
@router.get("/stats", response_model=Stats)
async def stats(session: AsyncSession = Depends(get_session)):
    return await repo.get_stats(session)


@router.get("/calls", response_model=list[CallRow])
async def calls(limit: int = 50, session: AsyncSession = Depends(get_session)):
    return await repo.list_calls_with_leads(session, limit)


@router.get("/calls/{call_id}", response_model=CallDetail)
async def call_detail(call_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    call = await repo.get_call(session, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="call not found")
    return CallDetail(
        id=str(call.id),
        direction=call.direction,
        status=call.status,
        outcome=call.outcome,
        started_at=call.started_at,
        ended_at=call.ended_at,
        duration_s=call.duration_s,
        avg_latency_ms=call.avg_latency_ms,
        turns=[
            TurnOut(role=t.role, text=t.text, stage=t.stage, latency_ms=t.latency_ms, ts=t.ts)
            for t in call.turns
        ],
    )


@router.get("/leads", response_model=list[LeadOut])
async def leads(limit: int = 100, session: AsyncSession = Depends(get_session)):
    rows = await repo.list_leads(session, limit)
    return [
        LeadOut(
            id=str(lead.id),
            phone=lead.phone,
            city=lead.city,
            budget=lead.budget,
            timeline=lead.timeline,
            property_type=lead.property_type,
            score=lead.score,
            status=lead.status,
            created_at=lead.created_at,
        )
        for lead in rows
    ]
