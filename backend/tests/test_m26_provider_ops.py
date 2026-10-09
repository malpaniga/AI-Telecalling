"""M26 tests — Provider Operations.

Tests:
1.  _compute_health — healthy/degraded/unhealthy/unknown from thresholds
2.  _overall_health — worst health of all providers
3.  ProviderOpsService.get_provider_health_summary — structure and counts
4.  ProviderOpsService.get_provider_metrics — empty when no data
5.  ProviderOpsService.get_provider_metrics — aggregates per provider
6.  ProviderOpsService.get_latency_stats — empty state
7.  ProviderOpsService.get_latency_stats — computes avg/min/max grade
8.  ProviderOpsService.get_voice_profile_health — lists active profiles
9.  HTTP: all endpoints require platform role (403 for customers)
10. HTTP: health, metrics, latency, voice-profiles all return 200
11. Provider cost/ID details stay internal (not customer-facing)
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _mongomock_available():
    try:
        import mongomock_motor
        return True
    except ImportError:
        return False


SKIP = pytest.mark.skipif(not _mongomock_available(), reason="mongomock_motor not installed")


def _get_mock_db():
    import mongomock_motor
    return mongomock_motor.AsyncMongoMockClient()["test"]


# ---------------------------------------------------------------------------
# Test: Health computation logic
# ---------------------------------------------------------------------------
class TestHealthComputation:
    def test_healthy(self):
        from backend.services.provider_ops_service import _compute_health
        assert _compute_health(98.0, 600) == "healthy"

    def test_degraded_low_success(self):
        from backend.services.provider_ops_service import _compute_health
        assert _compute_health(85.0, 800) == "degraded"

    def test_degraded_high_latency(self):
        from backend.services.provider_ops_service import _compute_health
        assert _compute_health(97.0, 2000) == "degraded"

    def test_unhealthy_very_low_success(self):
        from backend.services.provider_ops_service import _compute_health
        assert _compute_health(70.0, 800) == "unhealthy"

    def test_unhealthy_very_high_latency(self):
        from backend.services.provider_ops_service import _compute_health
        assert _compute_health(98.0, 4000) == "unhealthy"

    def test_unknown_no_data(self):
        from backend.services.provider_ops_service import _compute_health
        assert _compute_health(None, None) == "unknown"

    def test_overall_unhealthy_wins(self):
        from backend.services.provider_ops_service import _overall_health
        by_health = {
            "healthy": [{"provider": "twilio"}],
            "degraded": [{"provider": "sarvam"}],
            "unhealthy": [{"provider": "broken"}],
            "unknown": [],
        }
        assert _overall_health(by_health) == "unhealthy"

    def test_overall_degraded(self):
        from backend.services.provider_ops_service import _overall_health
        by_health = {
            "healthy": [{"provider": "twilio"}],
            "degraded": [{"provider": "sarvam"}],
            "unhealthy": [],
            "unknown": [],
        }
        assert _overall_health(by_health) == "degraded"

    def test_overall_healthy(self):
        from backend.services.provider_ops_service import _overall_health
        by_health = {
            "healthy": [{"provider": "twilio"}],
            "degraded": [],
            "unhealthy": [],
            "unknown": [],
        }
        assert _overall_health(by_health) == "healthy"

    def test_overall_unknown(self):
        from backend.services.provider_ops_service import _overall_health
        by_health = {"healthy": [], "degraded": [], "unhealthy": [], "unknown": []}
        assert _overall_health(by_health) == "unknown"


# ---------------------------------------------------------------------------
# Test: ProviderOpsService
# ---------------------------------------------------------------------------
@SKIP
class TestProviderOpsService:
    def setup_method(self):
        self.db = _get_mock_db()

    def _svc(self):
        from backend.services.provider_ops_service import ProviderOpsService
        return ProviderOpsService(self.db)

    def test_health_summary_empty(self):
        async def _t():
            svc = self._svc()
            result = await svc.get_provider_health_summary()
            assert "summary" in result
            assert "by_health" in result
            assert "overall" in result
            assert result["summary"]["healthy_count"] == 0
            assert result["overall"] == "unknown"
        run(_t())

    def test_health_summary_structure(self):
        async def _t():
            svc = self._svc()
            result = await svc.get_provider_health_summary(hours=24)
            assert "checked_at" in result
            assert "hours_window" in result
            assert result["hours_window"] == 24
        run(_t())

    def test_metrics_empty(self):
        async def _t():
            svc = self._svc()
            metrics = await svc.get_provider_metrics()
            assert isinstance(metrics, list)
            assert len(metrics) == 0
        run(_t())

    def test_metrics_with_data(self):
        async def _t():
            from backend.models.base import new_id, utcnow
            await self.db["provider_usage"].insert_one({
                "_id": new_id(),
                "organization_id": "org-1", "call_id": "call-1",
                "telephony_provider": "twilio", "telephony_cost_paise": 120,
                "stt_provider": "sarvam", "stt_cost_paise": 40,
                "llm_provider": "openai", "llm_cost_paise": 30,
                "tts_provider": "elevenlabs", "tts_cost_paise": 50,
                "duration_s": 60, "created_at": utcnow(),
            })
            svc = self._svc()
            metrics = await svc.get_provider_metrics()
            assert len(metrics) > 0
            # Should have entries for each provider type
            provider_types = {m["provider_type"] for m in metrics}
            assert "telephony" in provider_types
        run(_t())

    def test_latency_stats_empty(self):
        async def _t():
            svc = self._svc()
            result = await svc.get_latency_stats()
            assert result["call_count"] == 0
            assert result["avg_latency_ms"] is None
            assert result["grade"] == "unknown"
        run(_t())

    def test_latency_stats_with_calls(self):
        async def _t():
            from backend.models.base import new_id, utcnow
            for lat in [600, 800, 900]:
                await self.db["calls"].insert_one({
                    "_id": new_id(), "organization_id": "org-1",
                    "to_number": "+91987", "status": "completed",
                    "avg_latency_ms": lat, "created_at": utcnow(),
                })
            svc = self._svc()
            result = await svc.get_latency_stats()
            assert result["call_count"] == 3
            assert result["avg_latency_ms"] is not None
            assert result["min_latency_ms"] == 600
            assert result["max_latency_ms"] == 900
            assert result["grade"] in ("great", "good", "needs_improvement")
        run(_t())

    def test_latency_grade_great(self):
        async def _t():
            from backend.models.base import new_id, utcnow
            await self.db["calls"].insert_one({
                "_id": new_id(), "organization_id": "org-1",
                "to_number": "+91987", "status": "completed",
                "avg_latency_ms": 500, "created_at": utcnow(),
            })
            svc = self._svc()
            result = await svc.get_latency_stats()
            assert result["grade"] == "great"
        run(_t())

    def test_voice_profile_health_empty(self):
        async def _t():
            svc = self._svc()
            result = await svc.get_voice_profile_health()
            assert isinstance(result, list)
        run(_t())

    def test_voice_profile_health_with_profile(self):
        async def _t():
            from backend.models.base import new_id, utcnow
            await self.db["voice_profiles"].insert_one({
                "_id": new_id(), "display_name": "Marathi AI Voice",
                "language": "mr-IN", "is_active": True,
                "is_platform": True, "active_version": 1,
                "created_at": utcnow(), "updated_at": utcnow(),
            })
            svc = self._svc()
            result = await svc.get_voice_profile_health()
            assert len(result) == 1
            assert result[0]["display_name"] == "Marathi AI Voice"
            assert result[0]["language"] == "mr-IN"
            # Provider details should not expose secrets
            assert "provider_resource_id" not in str(result[0])
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestProviderOpsHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.provider_ops import router as ops_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(ops_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        from backend.core.auth import create_token_pair
        tokens = create_token_pair("admin-1", "admin@p.com", "platform_admin", None)
        self.admin_token = tokens["access_token"]

        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Ops Org",
            "org_email": "ops@org.com",
            "email": "user@ops.com",
            "password": "OpsPass1!",
        })
        self.customer_token = r.json()["access_token"]

    def _auth(self, t): return {"Authorization": f"Bearer {t}"}

    def test_customer_blocked(self):
        for ep in ["/api/v1/provider-ops/health", "/api/v1/provider-ops/metrics",
                   "/api/v1/provider-ops/latency", "/api/v1/provider-ops/voice-profiles"]:
            resp = self.client.get(ep, headers=self._auth(self.customer_token))
            assert resp.status_code == 403, f"Expected 403 for {ep}"

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/v1/provider-ops/health")
        assert resp.status_code == 401

    def test_health_endpoint(self):
        resp = self.client.get("/api/v1/provider-ops/health",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "overall" in data
        assert "by_health" in data

    def test_metrics_endpoint(self):
        resp = self.client.get("/api/v1/provider-ops/metrics",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_latency_endpoint(self):
        resp = self.client.get("/api/v1/provider-ops/latency",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "avg_latency_ms" in data
        assert "grade" in data

    def test_voice_profiles_endpoint(self):
        resp = self.client.get("/api/v1/provider-ops/voice-profiles",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_metrics_with_hours_param(self):
        resp = self.client.get("/api/v1/provider-ops/metrics?hours=48",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200

    def test_latency_with_hours_param(self):
        resp = self.client.get("/api/v1/provider-ops/latency?hours=12",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        assert resp.json()["hours_window"] == 12

    def test_health_thresholds_in_constants(self):
        from backend.services.provider_ops_service import HEALTH_THRESHOLDS
        assert "success_rate_healthy" in HEALTH_THRESHOLDS
        assert "latency_healthy_ms" in HEALTH_THRESHOLDS
        assert HEALTH_THRESHOLDS["success_rate_healthy"] == 95.0
        assert HEALTH_THRESHOLDS["latency_healthy_ms"] == 1500


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
