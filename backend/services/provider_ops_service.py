"""Provider Operations Service.

Tracks per-provider health, latency, success/error rates, usage and costs.
This is an ADMIN-ONLY service — customer data never includes provider details.

Metrics aggregated from:
  - provider_usage collection (per-call provider cost breakdown)
  - calls collection (status, avg_latency_ms, duration_s)
  - voice_profile_versions (which provider routes are in use)

Health status:
  healthy     — success_rate >= 95%, avg_latency <= 1500ms
  degraded    — success_rate 80-95% OR avg_latency 1500-3000ms
  unhealthy   — success_rate < 80% OR avg_latency > 3000ms
  unknown     — no data
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

log = logging.getLogger("service.provider_ops")

HEALTH_THRESHOLDS = {
    "success_rate_healthy": 95.0,
    "success_rate_degraded": 80.0,
    "latency_healthy_ms": 1500,
    "latency_degraded_ms": 3000,
}


def _compute_health(success_rate: Optional[float], avg_latency_ms: Optional[int]) -> str:
    if success_rate is None and avg_latency_ms is None:
        return "unknown"
    sr = success_rate or 100.0
    lat = avg_latency_ms or 0
    if sr >= HEALTH_THRESHOLDS["success_rate_healthy"] and lat <= HEALTH_THRESHOLDS["latency_healthy_ms"]:
        return "healthy"
    if sr < HEALTH_THRESHOLDS["success_rate_degraded"] or lat > HEALTH_THRESHOLDS["latency_degraded_ms"]:
        return "unhealthy"
    return "degraded"


class ProviderOpsService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    # ---- Per-provider aggregated metrics ----

    async def get_provider_metrics(
        self,
        hours: int = 24,
        provider_type: Optional[str] = None,
    ) -> list[dict]:
        """
        Aggregate metrics per provider from the last N hours.
        Returns: [{provider, provider_type, call_count, success_rate,
                   avg_latency_ms, total_cost_paise, error_rate, health}]
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        # From provider_usage (cost breakdown)
        cost_pipeline = [
            {"$match": {"created_at": {"$gte": since}}},
            {"$project": {
                "telephony_provider": 1, "telephony_cost_paise": 1,
                "stt_provider": 1, "stt_cost_paise": 1,
                "llm_provider": 1, "llm_cost_paise": 1,
                "tts_provider": 1, "tts_cost_paise": 1,
                "duration_s": 1, "call_id": 1,
            }},
        ]
        pu_rows = await self.db["provider_usage"].aggregate(cost_pipeline).to_list(None)

        # From calls (status / latency)
        call_pipeline = [
            {"$match": {"created_at": {"$gte": since},
                        "status": {"$in": ["completed", "failed", "no_answer"]}}},
            {"$group": {
                "_id": "$provider",
                "total": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
                "avg_latency": {"$avg": "$avg_latency_ms"},
            }},
        ]
        call_rows = await self.db["calls"].aggregate(call_pipeline).to_list(None)
        call_by_provider = {r["_id"]: r for r in call_rows}

        # Build per-provider summary for each type
        result = {}

        for ptype in ["telephony", "stt", "llm", "tts"]:
            if provider_type and ptype != provider_type:
                continue
            provider_field = f"{ptype}_provider"
            cost_field = f"{ptype}_cost_paise"

            # Aggregate cost by provider
            cost_by_prov: dict = {}
            for row in pu_rows:
                prov = row.get(provider_field)
                if not prov:
                    continue
                if prov not in cost_by_prov:
                    cost_by_prov[prov] = {"cost": 0, "calls": 0}
                cost_by_prov[prov]["cost"] += row.get(cost_field, 0)
                cost_by_prov[prov]["calls"] += 1

            for prov, data in cost_by_prov.items():
                key = f"{ptype}:{prov}"
                call_data = call_by_provider.get(prov, {})
                total_calls = call_data.get("total", data["calls"])
                completed = call_data.get("completed", data["calls"])
                failed = call_data.get("failed", 0)
                avg_latency = int(call_data["avg_latency"]) if call_data.get("avg_latency") else None

                success_rate = round(completed / total_calls * 100, 2) if total_calls > 0 else None
                error_rate = round(failed / total_calls * 100, 2) if total_calls > 0 else None

                result[key] = {
                    "provider": prov,
                    "provider_type": ptype,
                    "call_count": total_calls,
                    "completed_calls": completed,
                    "failed_calls": failed,
                    "success_rate_pct": success_rate,
                    "error_rate_pct": error_rate,
                    "avg_latency_ms": avg_latency,
                    "total_cost_paise": data["cost"],
                    "total_cost_inr": data["cost"] / 100,
                    "health": _compute_health(success_rate, avg_latency),
                }

        return list(result.values())

    async def get_provider_health_summary(self, hours: int = 24) -> dict:
        """Quick health summary: which providers are healthy/degraded/unhealthy."""
        metrics = await self.get_provider_metrics(hours=hours)

        by_health: dict = {"healthy": [], "degraded": [], "unhealthy": [], "unknown": []}
        for m in metrics:
            by_health[m["health"]].append({
                "provider": m["provider"],
                "provider_type": m["provider_type"],
                "success_rate_pct": m["success_rate_pct"],
                "avg_latency_ms": m["avg_latency_ms"],
            })

        return {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "hours_window": hours,
            "summary": {
                "healthy_count": len(by_health["healthy"]),
                "degraded_count": len(by_health["degraded"]),
                "unhealthy_count": len(by_health["unhealthy"]),
                "unknown_count": len(by_health["unknown"]),
            },
            "by_health": by_health,
            "overall": _overall_health(by_health),
        }

    async def get_voice_profile_health(self) -> list[dict]:
        """Health check for each active voice profile version's provider routes."""
        profiles = await self.db["voice_profiles"].find(
            {"is_active": True}
        ).to_list(None)

        result = []
        for profile in profiles:
            pid = str(profile["_id"])
            active_version = profile.get("active_version")
            active_version_id = profile.get("active_version_id")

            routes = {}
            if active_version_id:
                version_doc = await self.db["voice_profile_versions"].find_one(
                    {"_id": active_version_id}
                )
                if version_doc:
                    routes = version_doc.get("routes", {})

            # Collect provider names (hide IDs from output)
            providers_used = {
                ptype: route.get("provider", "unknown")
                for ptype, route in routes.items()
                if isinstance(route, dict)
            }

            result.append({
                "profile_id": pid,
                "display_name": profile.get("display_name"),
                "language": profile.get("language"),
                "active_version": active_version,
                "providers_used": providers_used,
                "is_platform": profile.get("is_platform", False),
                # Health is unknown without recent usage data
                "health": "unknown",
            })

        return result

    async def get_latency_stats(self, hours: int = 24) -> dict:
        """Platform-wide latency stats from recent calls."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": since},
                    "avg_latency_ms": {"$ne": None},
                    "status": "completed",
                }
            },
            {
                "$group": {
                    "_id": None,
                    "count": {"$sum": 1},
                    "avg_ms": {"$avg": "$avg_latency_ms"},
                    "min_ms": {"$min": "$avg_latency_ms"},
                    "max_ms": {"$max": "$avg_latency_ms"},
                }
            },
        ]
        rows = await self.db["calls"].aggregate(pipeline).to_list(1)
        if not rows:
            return {
                "hours_window": hours,
                "call_count": 0,
                "avg_latency_ms": None,
                "min_latency_ms": None,
                "max_latency_ms": None,
                "grade": "unknown",
            }
        r = rows[0]
        avg = int(r["avg_ms"]) if r.get("avg_ms") else None
        if avg is None:
            grade = "unknown"
        elif avg <= 800:
            grade = "great"
        elif avg <= 1200:
            grade = "good"
        else:
            grade = "needs_improvement"
        return {
            "hours_window": hours,
            "call_count": r["count"],
            "avg_latency_ms": avg,
            "min_latency_ms": int(r["min_ms"]) if r.get("min_ms") else None,
            "max_latency_ms": int(r["max_ms"]) if r.get("max_ms") else None,
            "grade": grade,
        }


def _overall_health(by_health: dict) -> str:
    if by_health["unhealthy"]:
        return "unhealthy"
    if by_health["degraded"]:
        return "degraded"
    if by_health["healthy"]:
        return "healthy"
    return "unknown"
