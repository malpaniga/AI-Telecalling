"""Customer Dashboard API.

GET /api/v1/dashboard                — full dashboard summary (main metrics)
GET /api/v1/dashboard/calls          — call stats summary
GET /api/v1/dashboard/campaigns      — campaign status summary
GET /api/v1/dashboard/leads          — lead pipeline summary
GET /api/v1/dashboard/credits        — wallet / credits summary
GET /api/v1/dashboard/appointments   — upcoming appointments
GET /api/v1/dashboard/analytics      — analytics over time

All endpoints are org-scoped (tenant isolation).
Provider details, costs, and margins are NEVER included.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from fastapi import HTTPException

log = logging.getLogger("api.dashboard")
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _require_org(user: CurrentUser) -> str:
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    return user.org_id


def _utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Main dashboard — aggregates everything in one call
# ---------------------------------------------------------------------------
@router.get("")
async def dashboard(user: CurrentUser = Depends(get_current_user)):
    """Full dashboard summary. All key metrics in one request."""
    org_id = _require_org(user)
    db = get_db()

    # Parallel fetch all sections
    import asyncio
    (calls_stats, campaigns_stats, leads_stats,
     credits_stats, appointments_list, recent_calls) = await asyncio.gather(
        _get_call_stats(db, org_id),
        _get_campaign_stats(db, org_id),
        _get_lead_stats(db, org_id),
        _get_credits_stats(db, org_id),
        _get_upcoming_appointments(db, org_id, limit=5),
        _get_recent_calls(db, org_id, limit=8),
    )

    return {
        "organization_id": org_id,
        "calls": calls_stats,
        "campaigns": campaigns_stats,
        "leads": leads_stats,
        "credits": credits_stats,
        "upcoming_appointments": appointments_list,
        "recent_calls": recent_calls,
        "generated_at": _utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Per-section endpoints
# ---------------------------------------------------------------------------
@router.get("/calls")
async def dashboard_calls(
    days: int = Query(default=7, ge=1, le=90),
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    db = get_db()
    since = _utcnow() - timedelta(days=days)
    stats = await _get_call_stats(db, org_id, since=since)
    return {**stats, "period_days": days}


@router.get("/campaigns")
async def dashboard_campaigns(user: CurrentUser = Depends(get_current_user)):
    org_id = _require_org(user)
    db = get_db()
    return await _get_campaign_stats(db, org_id)


@router.get("/leads")
async def dashboard_leads(user: CurrentUser = Depends(get_current_user)):
    org_id = _require_org(user)
    db = get_db()
    return await _get_lead_stats(db, org_id)


@router.get("/credits")
async def dashboard_credits(user: CurrentUser = Depends(get_current_user)):
    org_id = _require_org(user)
    db = get_db()
    return await _get_credits_stats(db, org_id)


@router.get("/appointments")
async def dashboard_appointments(
    limit: int = Query(default=10, le=50),
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    db = get_db()
    appts = await _get_upcoming_appointments(db, org_id, limit=limit)
    return {"upcoming": appts, "count": len(appts)}


@router.get("/analytics")
async def dashboard_analytics(
    days: int = Query(default=30, ge=1, le=365),
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    db = get_db()
    return await _get_analytics(db, org_id, days=days)


# ---------------------------------------------------------------------------
# Data aggregation helpers
# ---------------------------------------------------------------------------
async def _get_call_stats(db, org_id: str, since: Optional[datetime] = None) -> dict:
    query: dict = {"organization_id": org_id}
    if since:
        query["started_at"] = {"$gte": since}

    total = await db["calls"].count_documents(query)
    connected = await db["calls"].count_documents(
        {**query, "status": {"$in": ["connected", "completed"]}}
    )
    completed = await db["calls"].count_documents(
        {**query, "status": "completed"}
    )

    # Average duration from completed calls
    pipeline = [
        {"$match": {**query, "status": "completed", "duration_s": {"$ne": None}}},
        {"$group": {"_id": None,
                    "avg_duration": {"$avg": "$duration_s"},
                    "avg_latency": {"$avg": "$avg_latency_ms"}}},
    ]
    agg = await db["calls"].aggregate(pipeline).to_list(1)
    avg_duration = int(agg[0]["avg_duration"]) if agg and agg[0].get("avg_duration") is not None else None
    avg_latency = int(agg[0]["avg_latency"]) if agg and agg[0].get("avg_latency") is not None else None

    # Outcome breakdown
    outcome_pipeline = [
        {"$match": query},
        {"$group": {"_id": "$outcome", "count": {"$sum": 1}}},
    ]
    outcomes_raw = await db["calls"].aggregate(outcome_pipeline).to_list(None)
    outcomes = {(r["_id"] or "in_progress"): r["count"] for r in outcomes_raw}

    connected_rate = round(connected / total * 100, 1) if total > 0 else 0.0

    return {
        "total": total,
        "connected": connected,
        "completed": completed,
        "connected_rate_pct": connected_rate,
        "avg_duration_s": avg_duration,
        "avg_latency_ms": avg_latency,
        "outcomes": outcomes,
        "qualified": outcomes.get("qualified", 0) + outcomes.get("appointment_set", 0),
        "not_interested": outcomes.get("not_interested", 0),
    }


async def _get_campaign_stats(db, org_id: str) -> dict:
    status_pipeline = [
        {"$match": {"organization_id": org_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    rows = await db["campaigns"].aggregate(status_pipeline).to_list(None)
    by_status = {r["_id"]: r["count"] for r in rows}
    total = sum(by_status.values())

    running = await db["campaigns"].find(
        {"organization_id": org_id, "status": "running"},
        {"name": 1, "leads_dialed": 1, "leads_completed": 1,
         "max_concurrent_calls": 1, "status": 1}
    ).limit(5).to_list(5)

    return {
        "total": total,
        "by_status": by_status,
        "running": len([r for r in rows if r["_id"] == "running"]),
        "running_campaigns": [
            {
                "id": str(c["_id"]),
                "name": c.get("name"),
                "leads_dialed": c.get("leads_dialed", 0),
                "leads_completed": c.get("leads_completed", 0),
                "status": c.get("status"),
            }
            for c in running
        ],
    }


async def _get_lead_stats(db, org_id: str) -> dict:
    pipeline = [
        {"$match": {"organization_id": org_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    rows = await db["leads"].aggregate(pipeline).to_list(None)
    by_status = {r["_id"]: r["count"] for r in rows}
    total = sum(by_status.values())

    # Average score
    score_agg = await db["leads"].aggregate([
        {"$match": {"organization_id": org_id, "score": {"$gt": 0}}},
        {"$group": {"_id": None, "avg_score": {"$avg": "$score"}}},
    ]).to_list(1)
    avg_score = round(float(score_agg[0]["avg_score"]), 1) if score_agg and score_agg[0].get("avg_score") is not None else 0.0

    return {
        "total": total,
        "by_status": by_status,
        "new": by_status.get("new", 0),
        "qualified": by_status.get("qualified", 0),
        "not_interested": by_status.get("not_interested", 0),
        "callback": by_status.get("callback", 0),
        "avg_score": avg_score,
    }


async def _get_credits_stats(db, org_id: str) -> dict:
    wallet = await db["wallets"].find_one({"organization_id": org_id})
    if wallet is None:
        return {
            "available_credits": 0,
            "reserved_credits": 0,
            "total_credits": 0,
            "total_consumed": 0,
            "is_low": True,
            "low_threshold": 100,
        }
    available = wallet.get("available_credits", 0)
    reserved = wallet.get("reserved_credits", 0)
    threshold = wallet.get("low_credit_threshold", 100)
    return {
        "available_credits": available,
        "reserved_credits": reserved,
        "total_credits": available + reserved,
        "total_consumed": wallet.get("total_consumed", 0),
        "total_purchased": wallet.get("total_purchased", 0),
        "is_low": available <= threshold,
        "low_threshold": threshold,
    }


async def _get_upcoming_appointments(db, org_id: str, limit: int = 5) -> list:
    now = datetime.now(timezone.utc)
    appts = await db["appointments"].find(
        {
            "organization_id": org_id,
            "status": {"$in": ["scheduled", "confirmed"]},
            "scheduled_at": {"$gte": now},
        }
    ).sort("scheduled_at", 1).limit(limit).to_list(limit)

    return [
        {
            "id": str(a["_id"]),
            "appointment_type": a.get("appointment_type"),
            "title": a.get("title"),
            "scheduled_at": a["scheduled_at"].isoformat() if hasattr(a.get("scheduled_at"), "isoformat") else str(a.get("scheduled_at")),
            "timezone": a.get("timezone", "Asia/Kolkata"),
            "status": a.get("status"),
            "lead_name": a.get("lead_name"),
            "lead_phone": a.get("lead_phone"),
        }
        for a in appts
    ]


async def _get_recent_calls(db, org_id: str, limit: int = 8) -> list:
    calls = await db["calls"].find(
        {"organization_id": org_id}
    ).sort("started_at", -1).limit(limit).to_list(limit)

    return [
        {
            "id": str(c["_id"]),
            "to_number": c.get("to_number"),
            "status": c.get("status"),
            "outcome": c.get("outcome"),
            "duration_s": c.get("duration_s"),
            "score": c.get("score", 0),
            "started_at": c["started_at"].isoformat() if hasattr(c.get("started_at"), "isoformat") else str(c.get("started_at")),
        }
        for c in calls
    ]


async def _get_analytics(db, org_id: str, days: int = 30) -> dict:
    """Daily analytics for the last N days."""
    from datetime import date, timedelta as td
    end_date = date.today()
    start_date = end_date - td(days=days)

    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "date": {"$gte": start_date.isoformat(),
                          "$lte": end_date.isoformat()},
            }
        },
        {"$sort": {"date": 1}},
        {
            "$project": {
                "_id": 0,
                "date": 1,
                "calls_total": {"$ifNull": ["$calls_total", 0]},
                "calls_qualified": {"$ifNull": ["$calls_qualified", 0]},
                "credits_consumed": {"$ifNull": ["$credits_consumed", 0]},
            }
        },
    ]
    daily = await db["analytics_daily"].aggregate(pipeline).to_list(None)

    # Totals
    total_calls = sum(d.get("calls_total", 0) for d in daily)
    total_qualified = sum(d.get("calls_qualified", 0) for d in daily)
    total_credits = sum(d.get("credits_consumed", 0) for d in daily)

    qualified_rate = round(total_qualified / total_calls * 100, 1) if total_calls > 0 else 0.0

    return {
        "period_days": days,
        "daily": daily,
        "totals": {
            "calls": total_calls,
            "qualified": total_qualified,
            "qualified_rate_pct": qualified_rate,
            "credits_consumed": total_credits,
        },
    }
