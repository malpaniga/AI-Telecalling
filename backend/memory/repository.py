"""Legacy persistence layer — updated to use MongoDB.

Provides the same function signatures as the original PostgreSQL-based repo
so the existing CallSession and routes continue to work. Data is now stored
in MongoDB collections.

NOTE: This module handles the interim period (M0→M15). Once the full
campaign/call infrastructure is built in M13-M15, this will be replaced
by the proper repositories in backend/repositories/.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.core.db import get_db
from backend.models.base import new_id, utcnow

log = logging.getLogger("legacy_repo")


# ---------------------------------------------------------------------------
# Minimal data classes (replace SQLAlchemy models)
# ---------------------------------------------------------------------------
class _Call:
    def __init__(self, data: dict):
        self.id = data.get("_id")
        self.lead_id = data.get("lead_id")
        self.direction = data.get("direction", "inbound")
        self.status = data.get("status", "active")
        self.outcome = data.get("outcome")
        self.started_at = data.get("started_at")
        self.ended_at = data.get("ended_at")
        self.duration_s = data.get("duration_s")
        self.avg_latency_ms = data.get("avg_latency_ms")
        self.turns = []  # loaded separately


class _Lead:
    def __init__(self, data: dict):
        self.id = data.get("_id")
        self.phone = data.get("phone")
        self.name = data.get("name")
        self.email = data.get("email")
        self.budget = data.get("budget")
        self.timeline = data.get("timeline")
        self.city = data.get("city")
        self.property_type = data.get("property_type")
        self.score = data.get("score", 0)
        self.status = data.get("status", "new")
        self.created_at = data.get("created_at")
        self.updated_at = data.get("updated_at")


class _Turn:
    def __init__(self, data: dict):
        self.id = data.get("_id")
        self.call_id = data.get("call_id")
        self.role = data.get("role")
        self.text = data.get("text")
        self.stage = data.get("stage")
        self.latency_ms = data.get("latency_ms")
        self.ts = data.get("ts")


# ---------------------------------------------------------------------------
# Call / Lead operations
# ---------------------------------------------------------------------------
async def start_call(
    direction: str = "inbound", phone: Optional[str] = None
) -> tuple[_Call, _Lead]:
    """Create a fresh lead + active call at the start of a conversation."""
    db = get_db()
    now = utcnow()

    lead_doc = {
        "_id": new_id(),
        "phone": phone,
        "status": "new",
        "score": 0,
        "created_at": now,
        "updated_at": now,
        # No organization_id for legacy browser calls (demo)
        "organization_id": "demo",
    }
    await db["leads"].insert_one(lead_doc)

    call_doc = {
        "_id": new_id(),
        "lead_id": lead_doc["_id"],
        "direction": direction,
        "status": "active",
        "started_at": now,
        "organization_id": "demo",
    }
    await db["calls"].insert_one(call_doc)

    log.info("started call=%s lead=%s", call_doc["_id"], lead_doc["_id"])
    return _Call(call_doc), _Lead(lead_doc)


async def add_turn(
    call_id: str,
    role: str,
    text: str,
    stage: Optional[str] = None,
    latency_ms: Optional[int] = None,
) -> None:
    db = get_db()
    turn_doc = {
        "_id": new_id(),
        "call_id": call_id,
        "role": role,
        "text": text,
        "stage": stage,
        "latency_ms": latency_ms,
        "ts": utcnow(),
    }
    await db["turns"].insert_one(turn_doc)


async def finalize_call(
    call_id: str,
    lead_id: str,
    state: dict,
    avg_latency_ms: Optional[int] = None,
) -> int:
    """Persist final slots/score on lead, close call. Returns lead score."""
    db = get_db()
    slots = state.get("slots", {})
    flags = state.get("flags", {})
    stage = state.get("stage", "")

    from backend.agent.scoring import call_outcome, lead_status, score_lead
    score = score_lead(slots, flags)
    status = lead_status(slots, flags, stage)
    outcome = call_outcome(flags, stage)

    now = utcnow()

    # Update lead
    lead_updates: dict = {
        "score": score,
        "status": status,
        "updated_at": now,
    }
    for key in ["budget", "timeline", "city", "property_type"]:
        if slots.get(key):
            lead_updates[key] = slots[key]
    await db["leads"].update_one({"_id": lead_id}, {"$set": lead_updates})

    # Close call
    call_doc = await db["calls"].find_one({"_id": call_id})
    duration_s = None
    if call_doc and call_doc.get("started_at"):
        started = call_doc["started_at"]
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        duration_s = int((now - started).total_seconds())

    await db["calls"].update_one(
        {"_id": call_id},
        {"$set": {
            "status": "completed",
            "outcome": outcome,
            "ended_at": now,
            "duration_s": duration_s,
            "avg_latency_ms": avg_latency_ms,
        }},
    )

    if outcome == "booked":
        await db["appointments"].insert_one({
            "_id": new_id(),
            "lead_id": lead_id,
            "call_id": call_id,
            "status": "proposed",
            "organization_id": "demo",
            "created_at": now,
        })

    log.info("finalized call=%s outcome=%s score=%d status=%s", call_id, outcome, score, status)
    return score


# ---------------------------------------------------------------------------
# Read helpers for legacy dashboard API (/api/stats, /api/calls, /api/leads)
# ---------------------------------------------------------------------------
async def list_calls_with_leads(limit: int = 50) -> list[dict]:
    db = get_db()
    calls = await db["calls"].find(
        {"organization_id": "demo"}
    ).sort("started_at", -1).limit(limit).to_list(length=limit)

    out = []
    for call in calls:
        lead = None
        if call.get("lead_id"):
            lead = await db["leads"].find_one({"_id": call["lead_id"]})
        out.append({
            "id": str(call["_id"]),
            "direction": call.get("direction", "inbound"),
            "status": call.get("status", ""),
            "outcome": call.get("outcome"),
            "started_at": call.get("started_at"),
            "ended_at": call.get("ended_at"),
            "duration_s": call.get("duration_s"),
            "avg_latency_ms": call.get("avg_latency_ms"),
            "lead_city": lead.get("city") if lead else None,
            "lead_budget": lead.get("budget") if lead else None,
            "lead_score": lead.get("score") if lead else None,
            "lead_status": lead.get("status") if lead else None,
        })
    return out


async def get_call(call_id: str) -> Optional[_Call]:
    db = get_db()
    call_doc = await db["calls"].find_one({"_id": call_id})
    if call_doc is None:
        return None
    call = _Call(call_doc)
    turns_docs = await db["turns"].find({"call_id": call_id}).sort("ts", 1).to_list(length=None)
    call.turns = [_Turn(t) for t in turns_docs]
    return call


async def list_leads(limit: int = 100) -> list[_Lead]:
    db = get_db()
    docs = await db["leads"].find(
        {"organization_id": "demo"}
    ).sort("created_at", -1).limit(limit).to_list(length=limit)
    return [_Lead(d) for d in docs]


async def get_stats() -> dict:
    db = get_db()
    query = {"organization_id": "demo"}

    total_calls = await db["calls"].count_documents(query)
    total_leads = await db["leads"].count_documents(query)
    booked = await db["leads"].count_documents({**query, "status": "booked"})
    qualified = await db["leads"].count_documents({**query, "status": {"$in": ["qualified", "booked"]}})

    # Average score
    pipeline = [
        {"$match": query},
        {"$group": {"_id": None, "avg_score": {"$avg": "$score"}}},
    ]
    score_result = await db["leads"].aggregate(pipeline).to_list(1)
    avg_score = score_result[0]["avg_score"] if score_result else 0.0

    # Average latency
    latency_pipeline = [
        {"$match": {**query, "avg_latency_ms": {"$ne": None}}},
        {"$group": {"_id": None, "avg_latency": {"$avg": "$avg_latency_ms"}}},
    ]
    latency_result = await db["calls"].aggregate(latency_pipeline).to_list(1)
    avg_latency = int(latency_result[0]["avg_latency"]) if latency_result else None

    # Outcome breakdown
    outcome_pipeline = [
        {"$match": query},
        {"$group": {"_id": "$outcome", "count": {"$sum": 1}}},
    ]
    outcome_docs = await db["calls"].aggregate(outcome_pipeline).to_list(None)
    outcomes = {(d["_id"] or "in_progress"): d["count"] for d in outcome_docs}

    return {
        "total_calls": total_calls,
        "total_leads": total_leads,
        "booked": booked,
        "qualified": qualified,
        "avg_score": round(float(avg_score), 1) if avg_score else 0.0,
        "avg_latency_ms": avg_latency,
        "outcomes": outcomes,
    }
