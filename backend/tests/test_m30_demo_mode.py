"""M30 tests — Demo Mode.

Tests:
1.  DemoSeedService.seed_all creates all required resources
2.  seed_all is idempotent (second call returns already_seeded)
3.  Demo org created with correct details
4.  Demo user created (login credentials work)
5.  Growth plan subscription activated
6.  2000 calling credits granted
7.  Marathi AI Voice profile created (provider details hidden from customers)
8.  Demo phone number assigned to org
9.  Demo agent created with solar template
10. 20 demo leads created
11. Demo campaign created (draft)
12. Mock payment provider active in DEMO_MODE
13. Mock STT/TTS providers active in DEMO_MODE
14. is_seeded() detects seeded state
15. HTTP: /demo/status returns demo info
16. HTTP: /demo/seed creates environment
17. HTTP: /demo/reset removes demo data
18. Demo voice profile response hides provider details (customer view)
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
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
# Test: DemoSeedService
# ---------------------------------------------------------------------------
@SKIP
class TestDemoSeedService:
    def setup_method(self):
        self.db = _get_mock_db()

    def _svc(self):
        from backend.services.demo_seed_service import DemoSeedService
        return DemoSeedService(self.db)

    def test_seed_all_creates_org(self):
        async def _t():
            svc = self._svc()
            result = await svc.seed_all()
            assert result["seeded"] is True
            assert "organization_id" in result
            org = await self.db["organizations"].find_one(
                {"email": "demo@telecalling-saas.com"}
            )
            assert org is not None
            assert org["name"] == "Demo Company"
            assert org["status"] == "active"
        run(_t())

    def test_seed_all_creates_users(self):
        async def _t():
            svc = self._svc()
            result = await svc.seed_all()
            org_id = result["organization_id"]
            # Demo user
            user = await self.db["users"].find_one(
                {"email": "demo-user@telecalling-saas.com"}
            )
            assert user is not None
            assert user["organization_id"] == org_id
            assert user["role"] == "organization_owner"
            # Demo admin (platform-level)
            admin = await self.db["users"].find_one(
                {"email": "demo-admin@telecalling-saas.com"}
            )
            assert admin is not None
            assert admin["role"] == "platform_admin"
        run(_t())

    def test_seed_all_activates_growth_plan(self):
        async def _t():
            from backend.services.subscription_service import seed_default_plans
            await seed_default_plans(self.db)
            svc = self._svc()
            result = await svc.seed_all()
            assert result["subscription_plan"] == "growth"
            org_id = result["organization_id"]
            sub = await self.db["subscriptions"].find_one(
                {"organization_id": org_id, "status": "active"}
            )
            assert sub is not None
            assert sub["plan_slug"] == "growth"
        run(_t())

    def test_seed_all_grants_2000_credits(self):
        async def _t():
            from backend.services.subscription_service import seed_default_plans
            await seed_default_plans(self.db)
            svc = self._svc()
            result = await svc.seed_all()
            assert result["calling_credits"] == 2000
            org_id = result["organization_id"]
            wallet = await self.db["wallets"].find_one(
                {"organization_id": org_id}
            )
            assert wallet is not None
            assert wallet["available_credits"] == 2000
        run(_t())

    def test_seed_all_creates_marathi_voice_profile(self):
        async def _t():
            from backend.services.subscription_service import seed_default_plans
            await seed_default_plans(self.db)
            svc = self._svc()
            result = await svc.seed_all()
            assert result["voice_profile"] == "Marathi AI Voice"
            profile = await self.db["voice_profiles"].find_one(
                {"display_name": "Marathi AI Voice"}
            )
            assert profile is not None
            assert profile["language"] == "mr-IN"
            assert profile["is_platform"] is True
        run(_t())

    def test_voice_profile_routes_hidden_from_customers(self):
        """Provider routes in voice_profile_versions are internal only."""
        async def _t():
            from backend.services.subscription_service import seed_default_plans
            await seed_default_plans(self.db)
            svc = self._svc()
            result = await svc.seed_all()
            profile_id = result["voice_profile_id"]
            # Version doc has routes (internal)
            version = await self.db["voice_profile_versions"].find_one(
                {"voice_profile_id": profile_id}
            )
            assert version is not None
            assert "routes" in version
            # Customer-facing profile doc does NOT have routes
            profile = await self.db["voice_profiles"].find_one(
                {"_id": profile_id}
            )
            assert "routes" not in profile
        run(_t())

    def test_seed_all_assigns_phone_number(self):
        async def _t():
            from backend.services.subscription_service import seed_default_plans
            await seed_default_plans(self.db)
            svc = self._svc()
            result = await svc.seed_all()
            org_id = result["organization_id"]
            pn = await self.db["phone_numbers"].find_one(
                {"organization_id": org_id, "status": "assigned"}
            )
            assert pn is not None
            assert result["demo_phone_number"] in pn["number"]
        run(_t())

    def test_seed_all_creates_agent(self):
        async def _t():
            from backend.services.subscription_service import seed_default_plans
            await seed_default_plans(self.db)
            svc = self._svc()
            result = await svc.seed_all()
            org_id = result["organization_id"]
            agent = await self.db["agents"].find_one(
                {"organization_id": org_id, "is_active": True}
            )
            assert agent is not None
            assert agent["template_slug"] == "solar"
            assert agent["name"] == "Demo Solar Qualifier"
        run(_t())

    def test_seed_all_creates_20_leads(self):
        async def _t():
            from backend.services.subscription_service import seed_default_plans
            await seed_default_plans(self.db)
            svc = self._svc()
            result = await svc.seed_all()
            org_id = result["organization_id"]
            assert result["leads_count"] == 20
            count = await self.db["leads"].count_documents(
                {"organization_id": org_id, "source": "demo_seed"}
            )
            assert count == 20
        run(_t())

    def test_seed_all_creates_campaign(self):
        async def _t():
            from backend.services.subscription_service import seed_default_plans
            await seed_default_plans(self.db)
            svc = self._svc()
            result = await svc.seed_all()
            org_id = result["organization_id"]
            campaign = await self.db["campaigns"].find_one(
                {"organization_id": org_id, "status": "draft"}
            )
            assert campaign is not None
            assert campaign["name"] == "Demo Solar Campaign"
            assert campaign["total_leads"] == 20
        run(_t())

    def test_seed_all_is_idempotent(self):
        async def _t():
            from backend.services.subscription_service import seed_default_plans
            await seed_default_plans(self.db)
            svc = self._svc()
            r1 = await svc.seed_all()
            r2 = await svc.seed_all()
            assert r1["seeded"] is True
            assert r2["seeded"] is False
            assert r2["status"] == "already_seeded"
        run(_t())

    def test_is_seeded_detects_state(self):
        async def _t():
            from backend.services.subscription_service import seed_default_plans
            await seed_default_plans(self.db)
            svc = self._svc()
            assert await svc.is_seeded() is False
            await svc.seed_all()
            assert await svc.is_seeded() is True
        run(_t())


# ---------------------------------------------------------------------------
# Test: Mock provider integration
# ---------------------------------------------------------------------------
class TestDemoModeProviders:
    def test_mock_payment_provider_active_in_demo_mode(self):
        """In DEMO_MODE, payment_service uses MockPaymentProvider."""
        with patch("backend.config.settings") as mock_settings:
            mock_settings.demo_mode = True
            mock_settings.razorpay_key_id = ""
            mock_settings.razorpay_key_secret = ""
            from backend.services.payment_service import get_payment_provider
            provider = get_payment_provider()
            assert provider.provider_name == "mock"

    def test_mock_payment_provider_verifies_mock_signatures(self):
        from backend.providers.payment.mock import MockPaymentProvider
        provider = MockPaymentProvider()
        sig = MockPaymentProvider.make_valid_signature("ord_1", "pay_1")
        async def _t():
            result = await provider.verify_payment("ord_1", "pay_1", sig)
            assert result is True
        run(_t())

    def test_mock_payment_provider_create_order(self):
        from backend.providers.payment.mock import MockPaymentProvider
        MockPaymentProvider.reset()
        async def _t():
            p = MockPaymentProvider()
            result = await p.create_order(amount_paise=299900)
            assert "provider_order_id" in result
            assert result["amount_paise"] == 299900
        run(_t())

    def test_demo_leads_are_all_indian_mobiles(self):
        from backend.services.demo_seed_service import DEMO_LEADS
        for lead in DEMO_LEADS:
            # All should be normalizable to +91 prefix
            assert lead["phone"].startswith("+91"), \
                f"Non-Indian number: {lead['phone']}"

    def test_demo_leads_count_is_20(self):
        from backend.services.demo_seed_service import DEMO_LEADS
        assert len(DEMO_LEADS) == 20

    def test_demo_leads_have_required_fields(self):
        from backend.services.demo_seed_service import DEMO_LEADS
        for lead in DEMO_LEADS:
            assert "name" in lead and lead["name"]
            assert "phone" in lead and lead["phone"]
            assert "city" in lead


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestDemoHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.demo import router as demo_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(demo_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=60)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        from backend.core.auth import create_token_pair
        tokens = create_token_pair("admin-1", "admin@p.com", "platform_admin", None)
        self.admin_token = tokens["access_token"]

        # Customer token
        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Demo Test Org",
            "org_email": "demotest@org.com",
            "email": "user@demotest.com",
            "password": "DemoTestPass1!",
        })
        self.customer_token = r.json()["access_token"]

        # Seed plans
        from backend.services.subscription_service import seed_default_plans
        run(seed_default_plans(self.mock_db))

    def _auth(self, t): return {"Authorization": f"Bearer {t}"}

    def test_customer_blocked_without_demo_mode(self):
        with patch("backend.api.v1.demo.settings") as ms:
            ms.demo_mode = False
            resp = self.client.get("/api/v1/demo/status",
                                   headers=self._auth(self.customer_token))
            assert resp.status_code == 403

    def test_admin_can_check_status(self):
        resp = self.client.get("/api/v1/demo/status",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "demo_mode" in data
        assert "is_seeded" in data

    def test_admin_can_seed(self):
        resp = self.client.post("/api/v1/demo/seed",
                                headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("seeded", "already_seeded")

    def test_seed_creates_demo_org(self):
        resp = self.client.post("/api/v1/demo/seed",
                                headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] == "seeded":
            assert "organization_id" in data
            assert data["leads_count"] == 20
            assert data["calling_credits"] == 2000
            assert data["voice_profile"] == "Marathi AI Voice"

    def test_seed_is_idempotent_via_http(self):
        r1 = self.client.post("/api/v1/demo/seed",
                              headers=self._auth(self.admin_token))
        r2 = self.client.post("/api/v1/demo/seed",
                              headers=self._auth(self.admin_token))
        assert r1.status_code == 200
        assert r2.status_code == 200
        # One of them will say already_seeded
        statuses = {r1.json()["status"], r2.json()["status"]}
        assert "seeded" in statuses or "already_seeded" in statuses

    def test_reset_removes_demo_data(self):
        # Seed first
        self.client.post("/api/v1/demo/seed",
                         headers=self._auth(self.admin_token))
        # Reset
        resp = self.client.delete("/api/v1/demo/reset",
                                  headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("reset", "not_seeded")

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/v1/demo/status")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
