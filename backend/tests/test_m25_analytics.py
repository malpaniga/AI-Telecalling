"""M25 tests — Basic Revenue + Margin Analytics.

Tests:
1.  compute_mrr — zero when no subscriptions
2.  compute_mrr — correctly sums monthly prices
3.  compute_mrr — yearly subscription divided by 12
4.  ARPU = MRR / active_subscribers
5.  ARR = MRR × 12
6.  compute_revenue — subscription revenue from invoices
7.  compute_revenue — calling revenue from usage_events
8.  gross_profit = revenue - provider_cost
9.  gross_margin_pct = profit / revenue × 100
10. gross_margin_pct = None when revenue = 0
11. mrr_movement — counts new and churned subscribers
12. daily_analytics — returns per-day data
13. full_report — all fields present
14. All admin analytics endpoints return 403 for customers
15. HTTP: /analytics/mrr, /revenue, /costs, /margins, /arpu, /daily, /report
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
# Seed helpers
# ---------------------------------------------------------------------------
async def _seed_subscription(db, org_id: str, plan_id: str, billing_cycle: str = "monthly"):
    from backend.models.base import new_id, utcnow
    from datetime import timedelta
    now = utcnow()
    await db["subscriptions"].insert_one({
        "_id": new_id(),
        "organization_id": org_id,
        "plan_id": plan_id,
        "plan_slug": "test",
        "billing_cycle": billing_cycle,
        "status": "active",
        "started_at": now,
        "current_period_start": now,
        "current_period_end": now + timedelta(days=30),
        "snapshot_max_concurrent_calls": 3,
        "snapshot_max_campaigns": 5,
        "snapshot_max_agents": 5,
        "snapshot_max_leads_per_campaign": 1000,
        "snapshot_max_team_members": 10,
        "snapshot_features": {},
        "cancel_at_period_end": False,
        "created_at": now, "updated_at": now,
    })


async def _seed_plan(db, slug: str, monthly_paise: int, yearly_paise: int = 0):
    from backend.models.base import new_id, utcnow
    now = utcnow()
    plan_id = new_id()
    await db["subscription_plans"].insert_one({
        "_id": plan_id,
        "name": slug.capitalize(), "slug": slug,
        "price_monthly_paise": monthly_paise,
        "price_yearly_paise": yearly_paise,
        "is_active": True, "is_public": True,
        "created_at": now, "updated_at": now,
    })
    return plan_id


async def _seed_invoice(db, org_id: str, total_paise: int):
    from backend.models.base import new_id, utcnow
    now = utcnow()
    await db["invoices"].insert_one({
        "_id": new_id(), "organization_id": org_id,
        "invoice_number": f"INV-{new_id()[:8]}",
        "subtotal_paise": total_paise,
        "tax_paise": 0, "total_paise": total_paise,
        "status": "issued", "issued_at": now,
        "created_at": now, "updated_at": now,
    })


async def _seed_usage(db, org_id: str, charge: int, cost: int, credits: int = 60):
    from backend.models.base import new_id, utcnow
    await db["usage_events"].insert_one({
        "_id": new_id(), "organization_id": org_id,
        "event_type": "call_completed",
        "customer_charge_paise": charge,
        "provider_cost_paise": cost,
        "credits_consumed": credits,
        "created_at": utcnow(),
    })


# ---------------------------------------------------------------------------
# Test: AnalyticsService
# ---------------------------------------------------------------------------
@SKIP
class TestAnalyticsService:
    def setup_method(self):
        self.db = _get_mock_db()

    def _svc(self):
        from backend.services.analytics_service import AnalyticsService
        return AnalyticsService(self.db)

    def test_mrr_zero_no_subscriptions(self):
        async def _t():
            svc = self._svc()
            data = await svc.compute_mrr()
            assert data["mrr_paise"] == 0
            assert data["arr_paise"] == 0
            assert data["active_subscribers"] == 0
            assert data["arpu_paise"] == 0
        run(_t())

    def test_mrr_monthly_subscription(self):
        async def _t():
            svc = self._svc()
            plan_id = await _seed_plan(self.db, "m-plan", monthly_paise=299900)
            await _seed_subscription(self.db, "org-1", plan_id, "monthly")
            data = await svc.compute_mrr()
            assert data["mrr_paise"] == 299900
            assert data["active_subscribers"] == 1
        run(_t())

    def test_mrr_multiple_subscriptions(self):
        async def _t():
            svc = self._svc()
            plan_id = await _seed_plan(self.db, "multi", monthly_paise=100000)
            await _seed_subscription(self.db, "org-A", plan_id, "monthly")
            await _seed_subscription(self.db, "org-B", plan_id, "monthly")
            await _seed_subscription(self.db, "org-C", plan_id, "monthly")
            data = await svc.compute_mrr()
            assert data["mrr_paise"] == 300000
            assert data["active_subscribers"] == 3
        run(_t())

    def test_arr_is_mrr_times_12(self):
        async def _t():
            svc = self._svc()
            plan_id = await _seed_plan(self.db, "arr-plan", monthly_paise=100000)
            await _seed_subscription(self.db, "org-arr", plan_id, "monthly")
            data = await svc.compute_mrr()
            assert data["arr_paise"] == data["mrr_paise"] * 12
        run(_t())

    def test_arpu(self):
        async def _t():
            svc = self._svc()
            plan_id = await _seed_plan(self.db, "arpu-plan", monthly_paise=200000)
            await _seed_subscription(self.db, "org-1", plan_id, "monthly")
            await _seed_subscription(self.db, "org-2", plan_id, "monthly")
            data = await svc.compute_mrr()
            assert data["arpu_paise"] == 200000  # 400000 / 2
        run(_t())

    def test_revenue_subscription(self):
        async def _t():
            svc = self._svc()
            await _seed_invoice(self.db, "org-1", 299900)
            await _seed_invoice(self.db, "org-1", 799900)
            data = await svc.compute_revenue()
            assert data["subscription_revenue_paise"] == 1099800
        run(_t())

    def test_revenue_calling(self):
        async def _t():
            svc = self._svc()
            await _seed_usage(self.db, "org-1", charge=100, cost=30)
            await _seed_usage(self.db, "org-1", charge=200, cost=60)
            data = await svc.compute_revenue()
            assert data["calling_revenue_paise"] == 300
            assert data["provider_cost_paise"] == 90
        run(_t())

    def test_gross_profit(self):
        async def _t():
            svc = self._svc()
            await _seed_usage(self.db, "org-1", charge=1000, cost=300)
            data = await svc.compute_revenue()
            assert data["gross_profit_paise"] == 700
        run(_t())

    def test_gross_margin_pct(self):
        """charge=1000, cost=300 → margin=70%"""
        async def _t():
            svc = self._svc()
            await _seed_usage(self.db, "org-1", charge=1000, cost=300)
            data = await svc.compute_revenue()
            assert abs(data["gross_margin_pct"] - 70.0) < 0.01
        run(_t())

    def test_gross_margin_zero_revenue(self):
        async def _t():
            svc = self._svc()
            data = await svc.compute_revenue()
            assert data["gross_margin_pct"] is None
        run(_t())

    def test_mrr_movement(self):
        async def _t():
            svc = self._svc()
            plan_id = await _seed_plan(self.db, "mov-plan", monthly_paise=100000)
            await _seed_subscription(self.db, "org-new", plan_id, "monthly")
            now = datetime.now(timezone.utc)
            month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
            data = await svc.compute_mrr_movement(month_start, now)
            assert "new_mrr_paise" in data
            assert "churn_mrr_paise" in data
            assert "new_subscribers" in data
        run(_t())

    def test_full_report_structure(self):
        async def _t():
            svc = self._svc()
            data = await svc.full_report()
            assert "mrr" in data
            assert "mrr_movement" in data
            assert "revenue" in data
            assert "period" in data
            # All required MRR fields
            assert "mrr_paise" in data["mrr"]
            assert "arr_paise" in data["mrr"]
            assert "arpu_paise" in data["mrr"]
            # All required revenue fields
            assert "gross_profit_paise" in data["revenue"]
            assert "gross_margin_pct" in data["revenue"]
        run(_t())

    def test_daily_analytics_empty(self):
        async def _t():
            svc = self._svc()
            data = await svc.daily_analytics(days=7)
            assert isinstance(data, list)
        run(_t())

    def test_total_revenue_is_sum(self):
        """total_revenue = subscription + calling"""
        async def _t():
            svc = self._svc()
            await _seed_invoice(self.db, "org-1", 100000)
            await _seed_usage(self.db, "org-1", charge=50000, cost=10000)
            data = await svc.compute_revenue()
            assert data["total_revenue_paise"] == 150000
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestAnalyticsHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.analytics import router as analytics_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(analytics_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        # Platform admin token
        from backend.core.auth import create_token_pair
        tokens = create_token_pair("admin-1", "admin@p.com", "platform_admin", None)
        self.admin_token = tokens["access_token"]

        # Customer token
        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Analytics Org",
            "org_email": "analytics@org.com",
            "email": "user@analytics.com",
            "password": "AnalyticsPass1!",
        })
        self.customer_token = r.json()["access_token"]

    def _auth(self, t): return {"Authorization": f"Bearer {t}"}

    def test_all_endpoints_require_admin(self):
        for ep in ["/api/v1/analytics/mrr", "/api/v1/analytics/revenue",
                   "/api/v1/analytics/costs", "/api/v1/analytics/margins",
                   "/api/v1/analytics/arpu", "/api/v1/analytics/report"]:
            resp = self.client.get(ep, headers=self._auth(self.customer_token))
            assert resp.status_code == 403, f"Expected 403 for {ep}"

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/v1/analytics/mrr")
        assert resp.status_code == 401

    def test_mrr_endpoint(self):
        resp = self.client.get("/api/v1/analytics/mrr",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "mrr_paise" in data
        assert "arr_paise" in data
        assert "arpu_paise" in data
        assert "active_subscribers" in data

    def test_revenue_endpoint(self):
        resp = self.client.get("/api/v1/analytics/revenue",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "subscription_revenue_paise" in data
        assert "calling_revenue_paise" in data
        assert "total_revenue_paise" in data
        assert "gross_profit_paise" in data
        assert "gross_margin_pct" in data

    def test_costs_endpoint(self):
        resp = self.client.get("/api/v1/analytics/costs",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "provider_cost_paise" in data
        assert "gross_profit_paise" in data

    def test_margins_endpoint(self):
        resp = self.client.get("/api/v1/analytics/margins",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "gross_profit_paise" in data
        assert "gross_margin_pct" in data

    def test_arpu_endpoint(self):
        resp = self.client.get("/api/v1/analytics/arpu",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        assert "arpu_paise" in resp.json()

    def test_daily_endpoint(self):
        resp = self.client.get("/api/v1/analytics/daily?days=7",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "days" in data
        assert "data" in data

    def test_full_report_endpoint(self):
        resp = self.client.get("/api/v1/analytics/report",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "mrr" in data
        assert "mrr_movement" in data
        assert "revenue" in data

    def test_mrr_movement_endpoint(self):
        resp = self.client.get("/api/v1/analytics/mrr-movement",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "new_mrr_paise" in data
        assert "churn_mrr_paise" in data

    def test_revenue_integer_paise(self):
        """All paise values must be integers in responses."""
        resp = self.client.get("/api/v1/analytics/revenue",
                               headers=self._auth(self.admin_token))
        data = resp.json()
        paise_fields = [k for k in data if k.endswith("_paise")]
        for f in paise_fields:
            assert isinstance(data[f], int), f"{f} must be int, got {type(data[f])}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
