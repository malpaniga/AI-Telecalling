"""M21 tests — Usage + Cost.

Tests:
1.  UsageEvent model — integer paise, gross_profit/margin computed properties
2.  Negative amounts rejected
3.  ProviderUsage — total_provider_cost_paise sum
4.  UsageEventRepository — record, idempotency, list_for_org (tenant isolation)
5.  aggregate_for_org — counts and totals (customer-safe, no provider cost)
6.  aggregate_admin — includes provider cost, gross profit, margin
7.  ProviderUsageRepository — record and get_for_call
8.  CRITICAL: provider_cost_paise NEVER in customer API response
9.  UsageService.record_call_usage — both event and provider breakdown created
10. record_call_usage is idempotent (same call_id)
11. get_customer_summary — correct credits/counts, no provider cost
12. get_admin_summary — correct gross profit and margin
13. get_provider_breakdown — admin-only breakdown
14. Margin computation: charge=100, cost=30 → margin=70%
15. HTTP: summary, events (no cost), admin summary (with cost), record-call
16. HTTP: customer cannot access admin endpoints
17. Billing reconstruction: usage event has call_id + idempotency_key
"""

import asyncio
import sys
import os
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
# Test: Models
# ---------------------------------------------------------------------------
class TestUsageModels:
    def test_usage_event_paise_integer(self):
        from backend.models.usage import UsageEvent
        from backend.models.base import new_id
        e = UsageEvent(
            _id=new_id(), organization_id="org-1",
            event_type="call_completed",
            customer_charge_paise=120,
            provider_cost_paise=40,
            credits_consumed=120,
        )
        assert isinstance(e.customer_charge_paise, int)
        assert isinstance(e.provider_cost_paise, int)

    def test_gross_profit_computed(self):
        from backend.models.usage import UsageEvent
        from backend.models.base import new_id
        e = UsageEvent(
            _id=new_id(), organization_id="org-1",
            event_type="call_completed",
            customer_charge_paise=200,
            provider_cost_paise=60,
        )
        assert e.gross_profit_paise == 140
        assert abs(e.gross_margin_pct - 70.0) < 0.01

    def test_gross_margin_zero_charge(self):
        from backend.models.usage import UsageEvent
        from backend.models.base import new_id
        e = UsageEvent(_id=new_id(), organization_id="o",
                       event_type="call_completed",
                       customer_charge_paise=0, provider_cost_paise=0)
        assert e.gross_margin_pct is None

    def test_negative_amounts_rejected(self):
        from backend.models.usage import UsageEvent
        from backend.models.base import new_id
        with pytest.raises(Exception):
            UsageEvent(_id=new_id(), organization_id="o",
                       event_type="call_completed",
                       customer_charge_paise=-1)

    def test_provider_usage_total(self):
        from backend.models.usage import ProviderUsage
        from backend.models.base import new_id
        pu = ProviderUsage(
            _id=new_id(), organization_id="o", call_id="c-1",
            telephony_cost_paise=50,
            stt_cost_paise=20,
            llm_cost_paise=15,
            tts_cost_paise=10,
        )
        assert pu.total_provider_cost_paise == 95

    def test_margin_computation(self):
        """charge=100 paise, cost=30 paise → margin=70%"""
        from backend.models.usage import UsageEvent
        from backend.models.base import new_id
        e = UsageEvent(_id=new_id(), organization_id="o",
                       event_type="call_completed",
                       customer_charge_paise=100,
                       provider_cost_paise=30)
        assert e.gross_profit_paise == 70
        assert abs(e.gross_margin_pct - 70.0) < 0.01


# ---------------------------------------------------------------------------
# Test: Repository
# ---------------------------------------------------------------------------
@SKIP
class TestUsageEventRepository:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_record_event(self):
        from backend.repositories.usage_repo import UsageEventRepository
        repo = UsageEventRepository(self.db)
        async def _t():
            e = await repo.record("org-1", "call_completed",
                                  customer_charge_paise=120,
                                  credits_consumed=120,
                                  provider_cost_paise=40,
                                  call_id="call-1")
            assert e is not None
            assert e.customer_charge_paise == 120
        run(_t())

    def test_record_idempotent(self):
        from backend.repositories.usage_repo import UsageEventRepository
        repo = UsageEventRepository(self.db)
        async def _t():
            e1 = await repo.record("org-1", "call_completed",
                                   idempotency_key="idem-1")
            e2 = await repo.record("org-1", "call_completed",
                                   idempotency_key="idem-1")
            assert e1 is not None
            assert e2 is None  # duplicate suppressed
        run(_t())

    def test_tenant_isolation_list(self):
        from backend.repositories.usage_repo import UsageEventRepository
        repo = UsageEventRepository(self.db)
        async def _t():
            await repo.record("org-A", "call_completed", credits_consumed=60)
            await repo.record("org-A", "call_completed", credits_consumed=90)
            await repo.record("org-B", "call_completed", credits_consumed=30)
            events_a = await repo.list_for_org("org-A")
            events_b = await repo.list_for_org("org-B")
            assert len(events_a) == 2
            assert len(events_b) == 1
            assert all(e.organization_id == "org-A" for e in events_a)
        run(_t())

    def test_aggregate_for_org_no_provider_cost(self):
        from backend.repositories.usage_repo import UsageEventRepository
        repo = UsageEventRepository(self.db)
        async def _t():
            for i in range(3):
                await repo.record("org-agg", "call_completed",
                                  credits_consumed=60,
                                  customer_charge_paise=60,
                                  provider_cost_paise=20,
                                  duration_s=60)
            result = await repo.aggregate_for_org("org-agg")
            call_stats = result.get("call_completed", {})
            assert call_stats["count"] == 3
            assert call_stats["total_credits"] == 180
            # provider_cost NOT in aggregate_for_org result
            assert "provider_cost" not in str(call_stats)
        run(_t())

    def test_aggregate_admin_includes_margin(self):
        from backend.repositories.usage_repo import UsageEventRepository
        repo = UsageEventRepository(self.db)
        async def _t():
            await repo.record("org-margin", "call_completed",
                               customer_charge_paise=200,
                               provider_cost_paise=60)
            result = await repo.aggregate_admin("org-margin")
            assert result["total_customer_charge_paise"] == 200
            assert result["total_provider_cost_paise"] == 60
            assert result["gross_profit_paise"] == 140
            assert abs(result["gross_margin_pct"] - 70.0) < 0.01
        run(_t())


# ---------------------------------------------------------------------------
# Test: UsageService
# ---------------------------------------------------------------------------
@SKIP
class TestUsageService:
    def setup_method(self):
        self.db = _get_mock_db()

    def _svc(self):
        from backend.services.usage_service import UsageService
        return UsageService(self.db)

    def test_record_call_usage(self):
        async def _t():
            svc = self._svc()
            result = await svc.record_call_usage(
                "org-1", "call-1", duration_s=120, credits_consumed=120,
                telephony_provider="twilio", stt_provider="sarvam",
                llm_provider="openai", tts_provider="elevenlabs",
            )
            assert "usage_event_id" in result
            assert result["credits_consumed"] == 120
            assert "gross_profit_paise" in result
            # gross_profit = customer_charge - provider_cost (must be >= 0 for viable business)
        run(_t())

    def test_record_call_idempotent(self):
        async def _t():
            svc = self._svc()
            r1 = await svc.record_call_usage("org-1", "call-idem",
                                             duration_s=60, credits_consumed=60)
            r2 = await svc.record_call_usage("org-1", "call-idem",
                                             duration_s=60, credits_consumed=60)
            assert r1.get("usage_event_id") is not None
            assert r2.get("idempotent") is True
        run(_t())

    def test_provider_breakdown_recorded(self):
        async def _t():
            svc = self._svc()
            await svc.record_call_usage(
                "org-1", "call-prov", duration_s=90, credits_consumed=90,
                telephony_provider="twilio", stt_provider="sarvam",
            )
            breakdown = await svc.get_provider_breakdown("call-prov")
            assert breakdown is not None
            assert breakdown["telephony"]["provider"] == "twilio"
            assert breakdown["stt"]["provider"] == "sarvam"
            assert "total_provider_cost_paise" in breakdown
        run(_t())

    def test_customer_summary_no_provider_cost(self):
        async def _t():
            svc = self._svc()
            await svc.record_call_usage("org-2", "call-cs1",
                                        duration_s=60, credits_consumed=60)
            await svc.record_call_usage("org-2", "call-cs2",
                                        duration_s=90, credits_consumed=90)
            summary = await svc.get_customer_summary("org-2")
            assert summary["calls"]["count"] == 2
            assert summary["calls"]["total_credits"] == 150
            # Provider cost must NOT appear in customer summary
            summary_str = str(summary)
            assert "provider_cost" not in summary_str
            assert "gross_profit" not in summary_str
            assert "gross_margin" not in summary_str
        run(_t())

    def test_admin_summary_includes_costs(self):
        async def _t():
            svc = self._svc()
            await svc.record_call_usage(
                "org-3", "call-admin", duration_s=60, credits_consumed=60,
                provider_costs={"telephony": 10, "stt": 5, "llm": 5, "tts": 5}
            )
            admin_summary = await svc.get_admin_summary("org-3")
            assert "total_provider_cost_paise" in admin_summary
            assert "gross_profit_paise" in admin_summary
            assert "gross_margin_pct" in admin_summary
        run(_t())

    def test_provider_cost_not_in_customer_events(self):
        """CRITICAL: provider_cost_paise must NEVER appear in customer event list."""
        async def _t():
            svc = self._svc()
            await svc.record_call_usage("org-4", "call-priv",
                                        duration_s=60, credits_consumed=60,
                                        provider_costs={"telephony": 999, "stt": 500,
                                                         "llm": 300, "tts": 200})
            events = await svc.list_usage_events("org-4")
            assert len(events) == 1
            event = events[0]
            assert "provider_cost_paise" not in event
            assert "999" not in str(event)
            assert "500" not in str(event)
        run(_t())

    def test_billing_reconstruction(self):
        """Each usage event has call_id + idempotency_key for billing reconstruction."""
        async def _t():
            svc = self._svc()
            result = await svc.record_call_usage(
                "org-5", "call-recon", duration_s=60, credits_consumed=60
            )
            from backend.repositories.usage_repo import UsageEventRepository
            repo = UsageEventRepository(self.db)
            event = await repo.find_by_id(result["usage_event_id"])
            assert event.call_id == "call-recon"
            assert event.idempotency_key == "call_usage:call-recon"
            assert event.credits_consumed == 60
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestUsageHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.usage import router as usage_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(usage_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Usage Org",
            "org_email": "usage@org.com",
            "email": "user@usage.com",
            "password": "UsagePass1!",
        })
        self.user_token = r.json()["access_token"]
        self.org_id = r.json()["organization_id"]

        from backend.core.auth import create_token_pair
        tokens = create_token_pair("admin-1", "admin@platform.com", "platform_admin", None)
        self.admin_token = tokens["access_token"]

    def _auth(self, t): return {"Authorization": f"Bearer {t}"}

    def test_customer_summary_empty(self):
        resp = self.client.get("/api/v1/usage/summary",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "calls" in data
        assert "provider_cost" not in str(data)

    def test_customer_events_empty(self):
        resp = self.client.get("/api/v1/usage/events",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_record_call_usage(self):
        resp = self.client.post("/api/v1/usage/record-call", json={
            "call_id": "call-http-1",
            "duration_s": 120,
            "credits_consumed": 120,
            "telephony_provider": "twilio",
        }, headers=self._auth(self.user_token))
        assert resp.status_code == 200
        data = resp.json()
        # Response must NOT include provider cost
        assert "provider_cost" not in data
        assert "gross_profit" not in data
        assert "usage_event_id" in data or data.get("idempotent")

    def test_record_call_idempotent_via_http(self):
        body = {"call_id": "call-http-idem", "duration_s": 60, "credits_consumed": 60}
        r1 = self.client.post("/api/v1/usage/record-call", json=body,
                              headers=self._auth(self.user_token))
        r2 = self.client.post("/api/v1/usage/record-call", json=body,
                              headers=self._auth(self.user_token))
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r2.json().get("idempotent") is True

    def test_admin_summary_includes_margins(self):
        resp = self.client.get("/api/v1/usage/admin/summary",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_provider_cost_paise" in data
        assert "gross_profit_paise" in data
        assert "gross_margin_pct" in data

    def test_customer_cannot_access_admin_endpoints(self):
        resp = self.client.get("/api/v1/usage/admin/summary",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/v1/usage/summary")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
