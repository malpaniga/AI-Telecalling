"""M22 tests — Customer Dashboard API.

Tests:
1.  Dashboard returns required sections: calls, campaigns, leads, credits, appointments
2.  Calls section: total, connected_rate, avg_duration, outcomes
3.  Campaigns section: total, running campaigns list
4.  Leads section: total, by_status, avg_score
5.  Credits section: available, reserved, is_low flag
6.  Appointments: upcoming list (future only)
7.  Analytics: daily aggregation, totals
8.  Tenant isolation: Org A data invisible to Org B
9.  Provider costs / gross margin NEVER in dashboard response
10. Dashboard works when org has no data (empty state)
11. HTTP: all endpoints return 200 for authenticated user
12. HTTP: unauthenticated rejected (401)
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
async def _seed_calls(db, org_id: str, count: int = 5, outcome: str = "qualified"):
    from backend.repositories.call_repo import CallRepository
    repo = CallRepository(db)
    for i in range(count):
        call = await repo.create(org_id, f"+9190000{i:05d}", "+911800123001")
        await repo.update_by_id(call.id, {
            "status": "completed",
            "outcome": outcome,
            "duration_s": 90,
            "avg_latency_ms": 800,
        })


async def _seed_leads(db, org_id: str):
    from backend.repositories.lead_repo import LeadRepository
    repo = LeadRepository(db)
    statuses = ["new", "new", "qualified", "not_interested", "callback"]
    for i, status in enumerate(statuses):
        lead = await repo.create(org_id, f"+9190010{i:05d}", name=f"Lead {i}")
        await repo.update_by_id(lead.id, {"status": status, "score": 60 if status == "qualified" else 0})


async def _seed_wallet(db, org_id: str, available: int = 500):
    from backend.services.wallet_service import WalletService
    await WalletService(db).grant_bonus(org_id, available, "seed")


async def _seed_campaign(db, org_id: str, status: str = "running"):
    from backend.repositories.campaign_repo import CampaignRepository
    c = await CampaignRepository(db).create(
        organization_id=org_id, name="Test Campaign",
        agent_id="a", agent_version=1, voice_profile_id="v", voice_profile_version=1,
        calling_number_id="p", calling_number="+911800000001",
    )
    await CampaignRepository(db).transition_status(c.id, org_id, status)
    return c


async def _seed_appointment(db, org_id: str):
    from backend.repositories.appointment_repo import AppointmentRepository
    return await AppointmentRepository(db).create(
        org_id,
        datetime.now(timezone.utc) + timedelta(days=3),
        appointment_type="site_survey",
        lead_name="Test Lead",
    )


# ---------------------------------------------------------------------------
# Test: Dashboard data helpers
# ---------------------------------------------------------------------------
@SKIP
class TestDashboardHelpers:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_call_stats_empty(self):
        from backend.api.v1.dashboard import _get_call_stats
        async def _t():
            stats = await _get_call_stats(self.db, "org-empty")
            assert stats["total"] == 0
            assert stats["connected_rate_pct"] == 0.0
        run(_t())

    def test_call_stats_with_data(self):
        from backend.api.v1.dashboard import _get_call_stats
        async def _t():
            await _seed_calls(self.db, "org-calls", count=4, outcome="qualified")
            await _seed_calls(self.db, "org-calls", count=2, outcome="not_interested")
            stats = await _get_call_stats(self.db, "org-calls")
            assert stats["total"] == 6
            assert stats["completed"] == 6
            assert stats["avg_duration_s"] == 90
            assert stats["qualified"] == 4
        run(_t())

    def test_campaign_stats(self):
        from backend.api.v1.dashboard import _get_campaign_stats
        async def _t():
            await _seed_campaign(self.db, "org-camp", "running")
            await _seed_campaign(self.db, "org-camp", "draft")
            stats = await _get_campaign_stats(self.db, "org-camp")
            assert stats["total"] == 2
            assert stats["running"] == 1
            assert len(stats["running_campaigns"]) == 1
        run(_t())

    def test_lead_stats(self):
        from backend.api.v1.dashboard import _get_lead_stats
        async def _t():
            await _seed_leads(self.db, "org-leads")
            stats = await _get_lead_stats(self.db, "org-leads")
            assert stats["total"] == 5
            assert stats["new"] == 2
            assert stats["qualified"] == 1
            assert stats["not_interested"] == 1
        run(_t())

    def test_credits_stats(self):
        from backend.api.v1.dashboard import _get_credits_stats
        async def _t():
            await _seed_wallet(self.db, "org-credits", 500)
            stats = await _get_credits_stats(self.db, "org-credits")
            assert stats["available_credits"] == 500
            assert stats["is_low"] is False
        run(_t())

    def test_credits_low_flag(self):
        from backend.api.v1.dashboard import _get_credits_stats
        async def _t():
            await _seed_wallet(self.db, "org-low", 50)  # below 100 threshold
            stats = await _get_credits_stats(self.db, "org-low")
            assert stats["is_low"] is True
        run(_t())

    def test_credits_no_wallet(self):
        from backend.api.v1.dashboard import _get_credits_stats
        async def _t():
            stats = await _get_credits_stats(self.db, "org-no-wallet")
            assert stats["available_credits"] == 0
            assert stats["is_low"] is True
        run(_t())

    def test_upcoming_appointments_future_only(self):
        from backend.api.v1.dashboard import _get_upcoming_appointments
        async def _t():
            from backend.repositories.appointment_repo import AppointmentRepository
            repo = AppointmentRepository(self.db)
            # Future appointment
            await repo.create("org-appt", datetime.now(timezone.utc) + timedelta(days=2))
            # Past appointment — should NOT appear
            await repo.create("org-appt", datetime.now(timezone.utc) - timedelta(days=1))
            appts = await _get_upcoming_appointments(self.db, "org-appt")
            assert len(appts) == 1
        run(_t())

    def test_no_provider_costs_in_any_section(self):
        """Dashboard response must never include provider cost data."""
        from backend.api.v1.dashboard import (
            _get_call_stats, _get_campaign_stats,
            _get_lead_stats, _get_credits_stats,
        )
        async def _t():
            await _seed_calls(self.db, "org-noprov", count=2)
            call_stats = await _get_call_stats(self.db, "org-noprov")
            lead_stats = await _get_lead_stats(self.db, "org-noprov")
            cred_stats = await _get_credits_stats(self.db, "org-noprov")

            for section in [call_stats, lead_stats, cred_stats]:
                s = str(section).lower()
                assert "provider_cost" not in s
                assert "gross_profit" not in s
                assert "gross_margin" not in s
        run(_t())

    def test_tenant_isolation(self):
        """Org A stats do not leak into Org B."""
        from backend.api.v1.dashboard import _get_call_stats, _get_lead_stats
        async def _t():
            await _seed_calls(self.db, "org-iso-A", count=10)
            await _seed_leads(self.db, "org-iso-A")

            stats_b_calls = await _get_call_stats(self.db, "org-iso-B")
            stats_b_leads = await _get_lead_stats(self.db, "org-iso-B")

            assert stats_b_calls["total"] == 0
            assert stats_b_leads["total"] == 0
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestDashboardHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.dashboard import router as dash_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(dash_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        # Two orgs
        r1 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Dashboard Org",
            "org_email": "dash@org.com",
            "email": "user@dash.com",
            "password": "DashPass1!",
        })
        self.token_a = r1.json()["access_token"]
        self.org_id_a = r1.json()["organization_id"]

        r2 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Other Dash",
            "org_email": "other7@org.com",
            "email": "user@other7.com",
            "password": "Other7Pass1!",
        })
        self.token_b = r2.json()["access_token"]

        # Seed some data for org A
        run(_seed_calls(self.mock_db, self.org_id_a, count=3))
        run(_seed_leads(self.mock_db, self.org_id_a))
        run(_seed_wallet(self.mock_db, self.org_id_a, 500))

    def _auth(self, t): return {"Authorization": f"Bearer {t}"}

    def test_main_dashboard(self):
        resp = self.client.get("/api/v1/dashboard",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        data = resp.json()
        assert "calls" in data
        assert "campaigns" in data
        assert "leads" in data
        assert "credits" in data
        assert "upcoming_appointments" in data
        assert "recent_calls" in data
        assert "generated_at" in data

    def test_dashboard_has_required_metrics(self):
        resp = self.client.get("/api/v1/dashboard",
                               headers=self._auth(self.token_a))
        data = resp.json()
        # Calls section
        assert "total" in data["calls"]
        assert "connected_rate_pct" in data["calls"]
        assert "outcomes" in data["calls"]
        # Leads section
        assert "total" in data["leads"]
        assert "qualified" in data["leads"]
        # Credits section
        assert "available_credits" in data["credits"]
        assert "is_low" in data["credits"]

    def test_no_provider_costs_in_dashboard(self):
        resp = self.client.get("/api/v1/dashboard",
                               headers=self._auth(self.token_a))
        body = str(resp.json()).lower()
        assert "provider_cost" not in body
        assert "gross_profit" not in body
        assert "gross_margin" not in body

    def test_calls_section(self):
        resp = self.client.get("/api/v1/dashboard/calls",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3
        assert "period_days" in data

    def test_calls_section_period_filter(self):
        resp = self.client.get("/api/v1/dashboard/calls?days=1",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200

    def test_campaigns_section(self):
        resp = self.client.get("/api/v1/dashboard/campaigns",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "running_campaigns" in data

    def test_leads_section(self):
        resp = self.client.get("/api/v1/dashboard/leads",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 5
        assert "by_status" in data

    def test_credits_section(self):
        resp = self.client.get("/api/v1/dashboard/credits",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        data = resp.json()
        assert data["available_credits"] == 500

    def test_appointments_section(self):
        resp = self.client.get("/api/v1/dashboard/appointments",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert "upcoming" in resp.json()

    def test_analytics_section(self):
        resp = self.client.get("/api/v1/dashboard/analytics",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        data = resp.json()
        assert "totals" in data
        assert "daily" in data

    def test_tenant_isolation_main(self):
        """Org B dashboard shows 0 calls (Org A's calls not visible)."""
        resp = self.client.get("/api/v1/dashboard",
                               headers=self._auth(self.token_b))
        assert resp.status_code == 200
        data = resp.json()
        # Org B has no calls/leads
        assert data["calls"]["total"] == 0
        assert data["leads"]["total"] == 0

    def test_empty_org_dashboard(self):
        """Empty state: dashboard works when org has no data."""
        resp = self.client.get("/api/v1/dashboard",
                               headers=self._auth(self.token_b))
        assert resp.status_code == 200
        data = resp.json()
        assert data["calls"]["total"] == 0
        assert data["credits"]["available_credits"] == 0

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/v1/dashboard")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
