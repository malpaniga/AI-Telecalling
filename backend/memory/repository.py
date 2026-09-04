"""Persistence layer: turns conversation events into durable rows.

Kept deliberately thin — plain async functions over an AsyncSession, so the call
loop and (later) the REST API share the same operations.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.agent.scoring import call_outcome, lead_status, score_lead
from backend.agent.state import SLOT_KEYS, ConversationState
from backend.db.models import Booking, Call, Lead, Turn

log = logging.getLogger("repo")


async def start_call(
    session: AsyncSession, direction: str = "inbound", phone: str | None = None
) -> tuple[Call, Lead]:
    """Create a fresh lead + active call at the start of a conversation."""
    lead = Lead(phone=phone, status="new")
    session.add(lead)
    await session.flush()  # assigns lead.id

    call = Call(lead_id=lead.id, direction=direction, status="active")
    session.add(call)
    await session.flush()
    await session.commit()
    log.info("started call=%s lead=%s", call.id, lead.id)
    return call, lead


async def add_turn(
    session: AsyncSession,
    call_id: uuid.UUID,
    role: str,
    text: str,
    stage: str | None = None,
    latency_ms: int | None = None,
) -> None:
    session.add(
        Turn(call_id=call_id, role=role, text=text, stage=stage, latency_ms=latency_ms)
    )
    await session.commit()


async def finalize_call(
    session: AsyncSession,
    call_id: uuid.UUID,
    lead_id: uuid.UUID,
    state: ConversationState,
    avg_latency_ms: int | None = None,
) -> int:
    """Persist final slots/score/status on the lead, close out the call, and
    create a booking if the call reached booking intent. Returns the lead score."""
    slots = state["slots"]
    flags = state.get("flags", {})
    stage = state["stage"]

    score = score_lead(slots, flags)
    status = lead_status(slots, flags, stage)
    outcome = call_outcome(flags, stage)

    lead = await session.get(Lead, lead_id)
    if lead is not None:
        for key in SLOT_KEYS:
            if slots.get(key):
                setattr(lead, key, slots[key])
        lead.score = score
        lead.status = status

    call = await session.get(Call, call_id)
    if call is not None:
        now = datetime.now(timezone.utc)
        call.status = "completed"
        call.outcome = outcome
        call.ended_at = now
        started = call.started_at
        if started is not None:
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            call.duration_s = int((now - started).total_seconds())
        call.avg_latency_ms = avg_latency_ms

    if outcome == "booked":
        session.add(Booking(lead_id=lead_id, call_id=call_id, status="proposed"))

    await session.commit()
    log.info("finalized call=%s outcome=%s score=%d status=%s", call_id, outcome, score, status)
    return score


# ---- read helpers (used by the Sprint 6 dashboard API) ----
async def list_calls(session: AsyncSession, limit: int = 50) -> list[Call]:
    result = await session.execute(
        select(Call).order_by(Call.started_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_call(session: AsyncSession, call_id: uuid.UUID) -> Call | None:
    result = await session.execute(
        select(Call).options(selectinload(Call.turns)).where(Call.id == call_id)
    )
    return result.scalar_one_or_none()


async def list_leads(session: AsyncSession, limit: int = 100) -> list[Lead]:
    result = await session.execute(
        select(Lead).order_by(Lead.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_stats(session: AsyncSession) -> dict:
    """Aggregate metrics for the dashboard overview."""
    from sqlalchemy import func

    total_calls = (await session.execute(select(func.count(Call.id)))).scalar_one()
    total_leads = (await session.execute(select(func.count(Lead.id)))).scalar_one()
    booked = (
        await session.execute(select(func.count(Lead.id)).where(Lead.status == "booked"))
    ).scalar_one()
    qualified = (
        await session.execute(
            select(func.count(Lead.id)).where(Lead.status.in_(["qualified", "booked"]))
        )
    ).scalar_one()
    avg_score = (await session.execute(select(func.avg(Lead.score)))).scalar_one()
    avg_latency = (
        await session.execute(select(func.avg(Call.avg_latency_ms)))
    ).scalar_one()

    # Outcome breakdown.
    outcome_rows = await session.execute(
        select(Call.outcome, func.count(Call.id)).group_by(Call.outcome)
    )
    outcomes = {row[0] or "in_progress": row[1] for row in outcome_rows}

    return {
        "total_calls": total_calls,
        "total_leads": total_leads,
        "booked": booked,
        "qualified": qualified,
        "avg_score": round(float(avg_score), 1) if avg_score is not None else 0.0,
        "avg_latency_ms": int(avg_latency) if avg_latency is not None else None,
        "outcomes": outcomes,
    }


async def list_calls_with_leads(session: AsyncSession, limit: int = 50) -> list[dict]:
    """Recent calls joined with their lead's key fields (for the calls table)."""
    rows = await session.execute(
        select(Call, Lead)
        .join(Lead, Call.lead_id == Lead.id, isouter=True)
        .order_by(Call.started_at.desc())
        .limit(limit)
    )
    out: list[dict] = []
    for call, lead in rows:
        out.append(
            {
                "id": str(call.id),
                "direction": call.direction,
                "status": call.status,
                "outcome": call.outcome,
                "started_at": call.started_at,
                "ended_at": call.ended_at,
                "duration_s": call.duration_s,
                "avg_latency_ms": call.avg_latency_ms,
                "lead_city": lead.city if lead else None,
                "lead_budget": lead.budget if lead else None,
                "lead_score": lead.score if lead else None,
                "lead_status": lead.status if lead else None,
            }
        )
    return out
