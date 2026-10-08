"""Legacy REST API — dashboard routes.

Updated to use MongoDB. Same endpoints, same response shapes, so the existing
Next.js frontend continues to work during migration.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.memory import repository as repo

router = APIRouter(prefix="/api", tags=["dashboard-legacy"])


# ---- response schemas ----
class Stats(BaseModel):
    total_calls: int
    total_leads: int
    booked: int
    qualified: int
    avg_score: float
    avg_latency_ms: Optional[int]
    outcomes: dict[str, int]


class CallRow(BaseModel):
    id: str
    direction: str
    status: str
    outcome: Optional[str]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_s: Optional[int]
    avg_latency_ms: Optional[int]
    lead_city: Optional[str]
    lead_budget: Optional[str]
    lead_score: Optional[int]
    lead_status: Optional[str]


class TurnOut(BaseModel):
    role: str
    text: str
    stage: Optional[str]
    latency_ms: Optional[int]
    ts: Optional[datetime]


class CallDetail(BaseModel):
    id: str
    direction: str
    status: str
    outcome: Optional[str]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_s: Optional[int]
    avg_latency_ms: Optional[int]
    turns: list[TurnOut]


class LeadOut(BaseModel):
    id: str
    phone: Optional[str]
    city: Optional[str]
    budget: Optional[str]
    timeline: Optional[str]
    property_type: Optional[str]
    score: int
    status: str
    created_at: Optional[datetime]


# ---- routes ----
@router.get("/stats", response_model=Stats)
async def stats():
    return await repo.get_stats()


@router.get("/calls", response_model=list[CallRow])
async def calls(limit: int = 50):
    return await repo.list_calls_with_leads(limit)


@router.get("/calls/{call_id}", response_model=CallDetail)
async def call_detail(call_id: str):
    call = await repo.get_call(call_id)
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
async def leads(limit: int = 100):
    rows = await repo.list_leads(limit)
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


@router.get("/languages")
async def languages():
    from backend.languages import DEFAULT_LANGUAGE, LANGUAGES
    return {
        "default": DEFAULT_LANGUAGE,
        "languages": [
            {"code": code, "name": info["name"], "native": info["native"]}
            for code, info in LANGUAGES.items()
        ],
    }
