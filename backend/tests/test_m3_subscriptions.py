"""M3 tests — Plans + Subscriptions.

Tests:
1. SubscriptionPlan model — price validation (paise, non-negative)
2. SubscriptionPlanRepository — CRUD, slug uniqueness, list_public
3. SubscriptionRepository — create, find_active, cancel, upgrade
4. SubscriptionService — entitlement checks (campaign, agent, concurrent calls, features)
5. Plan change (upgrade / downgrade) logic
6. Config-driven pricing: changing plan DB record changes entitlements
7. One active subscription per org enforcement
8. HTTP endpoints: list plans, get plan, my subscription, admin create plan
9. Admin cannot set negative prices
10. Customer cannot access admin endpoints
"""

import asyncio
import sys
import os
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _mongomock_available():
    try:
        import mongomock_motor
        return True
    except ImportError:
        return False


SKIP_IF_NO_MONGOMOCK = pytest.mark.skipif(
    not _mongomock_available(), reason="mongomock_motor not installed"
)


def _get_mock_db():
    import mongomock_motor
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test"]


# ---------------------------------------------------------------------------
# Test: SubscriptionPlan model
# ---------------------------------------------------------------------------
class TestSubscriptionPlanModel:
    def test_price_must_be_integer_paise(self):
        from backend.models.subscription import SubscriptionPlan
        from backend.models.base import new_id
        plan = SubscriptionPlan(
            _id=new_id(),
            name="Test",
            slug="test",
            price_monthly_paise=299900,   # ₹2,999 in paise
            price_yearly_paise=2999900,
        )
        assert plan.price_monthly_paise == 299900
        assert plan.price_monthly_inr == 2999.0

    def test_negative_price_rejected(self):
        from backend.models.subscription import SubscriptionPlan
        from backend.models.base import new_id
        with pytest.raises(Exception):
            SubscriptionPlan(
                _id=new_id(),
                name="Bad",
                slug="bad",
                price_monthly_paise=-100,
            )

    def test_default_limits(self):
        from backend.models.subscription import SubscriptionPlan
        from backend.models.base import new_id
        plan = SubscriptionPlan(_id=new_id(), name="Free", slug="free")
        assert plan.max_concurrent_calls == 1
        assert plan.max_campaigns == 1
        assert plan.max_agents == 1
        assert plan.is_active is True

    def test_to_mongo_no_float_prices(self):
        from backend.models.subscription import SubscriptionPlan
        from backend.models.base import new_id
        plan = SubscriptionPlan(
            _id=new_id(), name="X", slug="x", price_monthly_paise=500
        )
        doc = plan.to_mongo()
        # Price must be stored as integer, not float
        assert isinstance(doc["price_monthly_paise"], int)
        assert "price_monthly_inr" not in doc  # computed property, not stored

    def test_subscription_model_defaults(self):
        from backend.models.subscription import Subscription
        from backend.models.base import new_id
        sub = Subscription(
            _id=new_id(),
            organization_id="org-1",
            plan_id="plan-1",
            plan_slug="starter",
        )
        assert sub.status == "active"
        assert sub.billing_cycle == "monthly"
        assert sub.cancel_at_period_end is False
        assert sub.is_active_or_trialing is True

    def test_trialing_is_active_or_trialing(self):
        from backend.models.subscription import Subscription
        from backend.models.base import new_id
        sub = Subscription(
            _id=new_id(),
            organization_id="org-1",
            plan_id="plan-1",
            plan_slug="starter",
            status="trialing",
        )
        assert sub.is_active_or_trialing is True

    def test_cancelled_not_active(self):
        from backend.models.subscription import Subscription
        from backend.models.base import new_id
        sub = Subscription(
            _id=new_id(),
            organization_id="org-1",
            plan_id="plan-1",
            plan_slug="starter",
            status="cancelled",
        )
        assert sub.is_active_or_trialing is False


# ---------------------------------------------------------------------------
# Test: SubscriptionPlanRepository
# ---------------------------------------------------------------------------
@SKIP_IF_NO_MONGOMOCK
class TestSubscriptionPlanRepository:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_create_plan(self):
        from backend.repositories.subscription_repo import SubscriptionPlanRepository
        repo = SubscriptionPlanRepository(self.db)

        async def _run():
            plan = await repo.create(
                name="Starter",
                slug="starter",
                price_monthly_paise=299900,
                max_concurrent_calls=2,
            )
            assert plan.id is not None
            assert plan.price_monthly_paise == 299900
            assert plan.max_concurrent_calls == 2
            return plan

        run(_run())

    def test_find_by_slug(self):
        from backend.repositories.subscription_repo import SubscriptionPlanRepository
        repo = SubscriptionPlanRepository(self.db)

        async def _run():
            await repo.create(name="Growth", slug="growth", price_monthly_paise=799900)
            found = await repo.find_by_slug("growth")
            assert found is not None
            assert found.name == "Growth"

        run(_run())

    def test_list_public_excludes_inactive(self):
        from backend.repositories.subscription_repo import SubscriptionPlanRepository
        repo = SubscriptionPlanRepository(self.db)

        async def _run():
            await repo.create(name="Active", slug="active-plan", is_public=True)
            inactive = await repo.create(name="Inactive", slug="inactive-plan", is_public=True)
            await repo.set_active(inactive.id, False)

            plans = await repo.list_public()
            slugs = [p.slug for p in plans]
            assert "active-plan" in slugs
            assert "inactive-plan" not in slugs

        run(_run())

    def test_list_public_excludes_private(self):
        from backend.repositories.subscription_repo import SubscriptionPlanRepository
        repo = SubscriptionPlanRepository(self.db)

        async def _run():
            await repo.create(name="Public", slug="pub-plan", is_public=True)
            await repo.create(name="Private", slug="priv-plan", is_public=False)
            plans = await repo.list_public()
            slugs = [p.slug for p in plans]
            assert "pub-plan" in slugs
            assert "priv-plan" not in slugs

        run(_run())

    def test_update_price(self):
        from backend.repositories.subscription_repo import SubscriptionPlanRepository
        repo = SubscriptionPlanRepository(self.db)

        async def _run():
            plan = await repo.create(name="Changeable", slug="changeable",
                                     price_monthly_paise=500)
            await repo.update_price(plan.id, price_monthly_paise=1000)
            updated = await repo.find_by_id(plan.id)
            assert updated.price_monthly_paise == 1000

        run(_run())

    def test_price_change_does_not_affect_existing_snapshot(self):
        """Changing plan price in DB must not change an existing subscription snapshot."""
        from backend.repositories.subscription_repo import (
            SubscriptionPlanRepository, SubscriptionRepository
        )
        plan_repo = SubscriptionPlanRepository(self.db)
        sub_repo = SubscriptionRepository(self.db)

        async def _run():
            plan = await plan_repo.create(
                name="Volatile", slug="volatile",
                price_monthly_paise=100, max_concurrent_calls=3
            )
            sub = await sub_repo.create_for_org("org-snapshot", plan)
            # Now update the plan limits
            await plan_repo.update_limits(plan.id, max_concurrent_calls=10)
            # Existing subscription snapshot must be unchanged
            refreshed = await sub_repo.find_by_id(sub.id)
            assert refreshed.snapshot_max_concurrent_calls == 3  # original, not 10

        run(_run())


# ---------------------------------------------------------------------------
# Test: SubscriptionRepository
# ---------------------------------------------------------------------------
@SKIP_IF_NO_MONGOMOCK
class TestSubscriptionRepository:
    def setup_method(self):
        self.db = _get_mock_db()

    def _make_plan(self, **kwargs):
        from backend.models.subscription import SubscriptionPlan
        from backend.models.base import new_id
        return SubscriptionPlan(
            _id=new_id(),
            name="Test Plan",
            slug="test-plan",
            max_concurrent_calls=3,
            max_campaigns=5,
            max_agents=5,
            **kwargs,
        )

    def test_create_subscription(self):
        from backend.repositories.subscription_repo import SubscriptionRepository
        repo = SubscriptionRepository(self.db)
        plan = self._make_plan()

        async def _run():
            sub = await repo.create_for_org("org-1", plan, billing_cycle="monthly")
            assert sub.organization_id == "org-1"
            assert sub.plan_slug == "test-plan"
            assert sub.snapshot_max_concurrent_calls == 3
            assert sub.snapshot_max_campaigns == 5
            return sub

        run(_run())

    def test_find_active_for_org(self):
        from backend.repositories.subscription_repo import SubscriptionRepository
        repo = SubscriptionRepository(self.db)
        plan = self._make_plan()

        async def _run():
            sub = await repo.create_for_org("org-findactive", plan)
            found = await repo.find_active_for_org("org-findactive")
            assert found is not None
            assert found.id == sub.id

        run(_run())

    def test_find_active_returns_none_for_no_subscription(self):
        from backend.repositories.subscription_repo import SubscriptionRepository
        repo = SubscriptionRepository(self.db)

        async def _run():
            result = await repo.find_active_for_org("org-nosub")
            assert result is None

        run(_run())

    def test_cancel_at_period_end(self):
        from backend.repositories.subscription_repo import SubscriptionRepository
        repo = SubscriptionRepository(self.db)
        plan = self._make_plan()

        async def _run():
            sub = await repo.create_for_org("org-cancel", plan)
            await repo.cancel(sub.id, at_period_end=True)
            updated = await repo.find_by_id(sub.id)
            # Status stays active (cancel is scheduled)
            assert updated.status == "active"
            assert updated.cancel_at_period_end is True
            assert updated.cancelled_at is not None

        run(_run())

    def test_cancel_immediately(self):
        from backend.repositories.subscription_repo import SubscriptionRepository
        repo = SubscriptionRepository(self.db)
        plan = self._make_plan()

        async def _run():
            sub = await repo.create_for_org("org-imm-cancel", plan)
            await repo.cancel(sub.id, at_period_end=False)
            updated = await repo.find_by_id(sub.id)
            assert updated.status == "cancelled"

        run(_run())

    def test_upgrade_updates_snapshot(self):
        from backend.repositories.subscription_repo import SubscriptionRepository
        from backend.models.subscription import SubscriptionPlan
        from backend.models.base import new_id
        repo = SubscriptionRepository(self.db)

        plan_old = SubscriptionPlan(
            _id=new_id(), name="Old", slug="old",
            max_concurrent_calls=1, max_campaigns=1
        )
        plan_new = SubscriptionPlan(
            _id=new_id(), name="New", slug="new",
            max_concurrent_calls=10, max_campaigns=20
        )

        async def _run():
            sub = await repo.create_for_org("org-upgrade", plan_old)
            assert sub.snapshot_max_concurrent_calls == 1
            await repo.upgrade(sub.id, plan_new, "monthly")
            updated = await repo.find_by_id(sub.id)
            assert updated.snapshot_max_concurrent_calls == 10
            assert updated.snapshot_max_campaigns == 20
            assert updated.plan_slug == "new"

        run(_run())


# ---------------------------------------------------------------------------
# Test: SubscriptionService — entitlement checks
# ---------------------------------------------------------------------------
@SKIP_IF_NO_MONGOMOCK
class TestSubscriptionServiceEntitlements:
    def setup_method(self):
        self.db = _get_mock_db()

    def _make_plan(self, concurrent=3, campaigns=5, agents=5, leads=1000,
                   kb=False, trial_days=0):
        from backend.models.subscription import SubscriptionPlan
        from backend.models.base import new_id
        return SubscriptionPlan(
            _id=new_id(), name="P", slug="p",
            max_concurrent_calls=concurrent,
            max_campaigns=campaigns,
            max_agents=agents,
            max_leads_per_campaign=leads,
            knowledge_base_enabled=kb,
            trial_days=trial_days,
        )

    def test_no_subscription_blocks_all(self):
        from backend.services.subscription_service import SubscriptionService
        svc = SubscriptionService(self.db)

        async def _run():
            check = await svc.check_subscription_active("org-nosub")
            assert check.allowed is False
            assert "subscription" in check.reason.lower()

        run(_run())

    def test_active_subscription_passes(self):
        from backend.services.subscription_service import SubscriptionService
        from backend.repositories.subscription_repo import SubscriptionRepository
        svc = SubscriptionService(self.db)
        repo = SubscriptionRepository(self.db)

        async def _run():
            plan = self._make_plan()
            await repo.create_for_org("org-active", plan)
            check = await svc.check_subscription_active("org-active")
            assert check.allowed is True

        run(_run())

    def test_campaign_limit_enforced(self):
        from backend.services.subscription_service import SubscriptionService
        from backend.repositories.subscription_repo import SubscriptionRepository
        svc = SubscriptionService(self.db)

        async def _run():
            plan = self._make_plan(campaigns=3)
            await svc.sub_repo.create_for_org("org-camp", plan)

            ok = await svc.check_can_add_campaign("org-camp", current_campaign_count=2)
            assert ok.allowed is True

            blocked = await svc.check_can_add_campaign("org-camp", current_campaign_count=3)
            assert blocked.allowed is False
            assert blocked.limit == 3

        run(_run())

    def test_agent_limit_enforced(self):
        from backend.services.subscription_service import SubscriptionService
        svc = SubscriptionService(self.db)

        async def _run():
            plan = self._make_plan(agents=2)
            await svc.sub_repo.create_for_org("org-agent", plan)

            ok = await svc.check_can_add_agent("org-agent", 1)
            assert ok.allowed is True
            blocked = await svc.check_can_add_agent("org-agent", 2)
            assert blocked.allowed is False

        run(_run())

    def test_concurrent_call_limit_enforced(self):
        from backend.services.subscription_service import SubscriptionService
        svc = SubscriptionService(self.db)

        async def _run():
            plan = self._make_plan(concurrent=5)
            await svc.sub_repo.create_for_org("org-concurrent", plan)

            ok = await svc.check_concurrent_calls("org-concurrent", 4)
            assert ok.allowed is True
            blocked = await svc.check_concurrent_calls("org-concurrent", 5)
            assert blocked.allowed is False

        run(_run())

    def test_feature_gate_knowledge_base(self):
        from backend.services.subscription_service import SubscriptionService
        svc = SubscriptionService(self.db)

        async def _run():
            plan_no_kb = self._make_plan(kb=False)
            await svc.sub_repo.create_for_org("org-nokb", plan_no_kb)
            check = await svc.check_feature("org-nokb", "knowledge_base_enabled")
            assert check.allowed is False

            plan_with_kb = self._make_plan(kb=True)
            await svc.sub_repo.create_for_org("org-kb", plan_with_kb)
            check2 = await svc.check_feature("org-kb", "knowledge_base_enabled")
            assert check2.allowed is True

        run(_run())

    def test_leads_per_campaign_limit(self):
        from backend.services.subscription_service import SubscriptionService
        svc = SubscriptionService(self.db)

        async def _run():
            plan = self._make_plan(leads=1000)
            await svc.sub_repo.create_for_org("org-leads", plan)

            ok = await svc.check_leads_per_campaign("org-leads", 999)
            assert ok.allowed is True
            blocked = await svc.check_leads_per_campaign("org-leads", 1001)
            assert blocked.allowed is False

        run(_run())

    def test_entitlement_check_raise_if_denied(self):
        from backend.models.subscription import EntitlementCheck
        from fastapi import HTTPException

        ok = EntitlementCheck(allowed=True)
        ok.raise_if_denied()  # should not raise

        denied = EntitlementCheck(allowed=False, reason="No subscription")
        with pytest.raises(HTTPException) as exc_info:
            denied.raise_if_denied()
        assert exc_info.value.status_code == 402

    def test_config_driven_behavior(self):
        """Changing plan config in DB changes entitlements without code changes."""
        from backend.services.subscription_service import SubscriptionService
        from backend.repositories.subscription_repo import (
            SubscriptionPlanRepository, SubscriptionRepository
        )
        svc = SubscriptionService(self.db)

        async def _run():
            # Create plan with limit 3
            plan = await svc.plan_repo.create(
                name="Config", slug="config-plan",
                max_campaigns=3,
            )
            sub = await svc.sub_repo.create_for_org("org-config", plan)

            # At 3 campaigns, blocked
            c1 = await svc.check_can_add_campaign("org-config", 3)
            assert c1.allowed is False

            # Admin upgrades plan limit via DB (no code change)
            await svc.plan_repo.update_limits(plan.id, max_campaigns=10)

            # Existing subscription uses SNAPSHOT — still blocked at 3
            c2 = await svc.check_can_add_campaign("org-config", 3)
            assert c2.allowed is False  # snapshot not changed

            # New subscription picks up new limit
            new_sub = await svc.activate_plan("org-config2", plan.id, "monthly")
            c3 = await svc.check_can_add_campaign("org-config2", 3)
            assert c3.allowed is True  # new snapshot reflects updated limit

        run(_run())

    def test_upgrade_plan_updates_entitlements(self):
        from backend.services.subscription_service import SubscriptionService
        svc = SubscriptionService(self.db)

        async def _run():
            starter = await svc.plan_repo.create(
                name="Starter", slug="starter2", max_campaigns=2
            )
            growth = await svc.plan_repo.create(
                name="Growth", slug="growth2", max_campaigns=10
            )
            await svc.activate_plan("org-upgrade", starter.id, "monthly")

            blocked = await svc.check_can_add_campaign("org-upgrade", 2)
            assert blocked.allowed is False

            await svc.change_plan("org-upgrade", growth.id, "monthly")
            allowed = await svc.check_can_add_campaign("org-upgrade", 2)
            assert allowed.allowed is True

        run(_run())

    def test_one_active_subscription_per_org(self):
        """Activating a new plan cancels the previous one."""
        from backend.services.subscription_service import SubscriptionService
        from backend.repositories.subscription_repo import SubscriptionRepository
        svc = SubscriptionService(self.db)

        async def _run():
            p1 = await svc.plan_repo.create(name="P1", slug="p1x")
            p2 = await svc.plan_repo.create(name="P2", slug="p2x")

            await svc.activate_plan("org-one", p1.id)
            await svc.activate_plan("org-one", p2.id)  # should cancel p1

            active = await svc.sub_repo.find_active_for_org("org-one")
            assert active.plan_slug == "p2x"

            # Only one active subscription
            all_subs = await svc.sub_repo.list_all(status="active")
            org_subs = [s for s in all_subs if s.organization_id == "org-one"]
            assert len(org_subs) == 1

        run(_run())


# ---------------------------------------------------------------------------
# Test: Seed default plans
# ---------------------------------------------------------------------------
@SKIP_IF_NO_MONGOMOCK
class TestSeedDefaultPlans:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_seed_creates_default_plans(self):
        from backend.services.subscription_service import seed_default_plans, DEFAULT_PLANS

        async def _run():
            created = await seed_default_plans(self.db)
            assert len(created) == len(DEFAULT_PLANS)
            slugs = [p.slug for p in created]
            assert "starter" in slugs
            assert "growth" in slugs
            assert "pro" in slugs

        run(_run())

    def test_seed_is_idempotent(self):
        from backend.services.subscription_service import seed_default_plans, DEFAULT_PLANS

        async def _run():
            first = await seed_default_plans(self.db)
            second = await seed_default_plans(self.db)
            # Second call should create nothing
            assert len(second) == 0

        run(_run())

    def test_default_plans_have_correct_tiers(self):
        from backend.services.subscription_service import seed_default_plans

        async def _run():
            plans = await seed_default_plans(self.db)
            plan_map = {p.slug: p for p in plans}

            # Starter < Growth < Pro in concurrent calls
            assert plan_map["starter"].max_concurrent_calls < plan_map["growth"].max_concurrent_calls
            assert plan_map["growth"].max_concurrent_calls < plan_map["pro"].max_concurrent_calls

            # Pro has API access, Starter does not
            assert plan_map["pro"].api_access is True
            assert plan_map["starter"].api_access is False

            # All prices in paise (integers, > 0)
            for plan in plans:
                assert isinstance(plan.price_monthly_paise, int)
                assert plan.price_monthly_paise > 0

        run(_run())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP_IF_NO_MONGOMOCK
class TestSubscriptionHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.subscriptions import router as sub_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(sub_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        # Mock Redis
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        # Create a platform admin token directly
        from backend.core.auth import create_token_pair
        tokens = create_token_pair("platform-admin-1", "admin@platform.com",
                                   "platform_admin", None)
        self.admin_token = tokens["access_token"]

        # Create org user via signup
        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Sub Test Org",
            "org_email": "sub@test.com",
            "email": "owner@sub.com",
            "password": "OwnerPass1!",
        })
        self.user_token = r.json()["access_token"]
        self.org_id = r.json()["organization_id"]

    def _auth(self, token): return {"Authorization": f"Bearer {token}"}

    def test_list_plans_public_no_auth(self):
        # Seed plans first
        run_seed = lambda: asyncio.get_event_loop().run_until_complete(
            __import__("backend.services.subscription_service",
                       fromlist=["seed_default_plans"]).seed_default_plans(self.mock_db)
        )
        run_seed()
        resp = self.client.get("/api/v1/subscriptions/plans")
        assert resp.status_code == 200
        plans = resp.json()
        assert isinstance(plans, list)
        assert len(plans) >= 1

    def test_get_plan_by_slug(self):
        from backend.services.subscription_service import seed_default_plans
        run(seed_default_plans(self.mock_db))
        resp = self.client.get("/api/v1/subscriptions/plans/starter")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "starter"
        assert isinstance(data["price_monthly_paise"], int)

    def test_get_nonexistent_plan_404(self):
        resp = self.client.get("/api/v1/subscriptions/plans/does-not-exist")
        assert resp.status_code == 404

    def test_my_subscription_no_sub(self):
        resp = self.client.get("/api/v1/subscriptions/my",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        assert resp.json()["has_subscription"] is False

    def test_admin_create_plan(self):
        resp = self.client.post("/api/v1/subscriptions/admin/plans", json={
            "name": "Custom Enterprise",
            "slug": "enterprise",
            "price_monthly_paise": 4999900,
            "max_concurrent_calls": 50,
            "max_campaigns": 100,
            "max_agents": 50,
            "max_leads_per_campaign": 100000,
        }, headers=self._auth(self.admin_token))
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["slug"] == "enterprise"
        assert data["price_monthly_paise"] == 4999900

    def test_customer_cannot_create_plan(self):
        resp = self.client.post("/api/v1/subscriptions/admin/plans", json={
            "name": "Fake Plan",
            "slug": "fake",
            "price_monthly_paise": 0,
        }, headers=self._auth(self.user_token))
        assert resp.status_code == 403

    def test_admin_activate_plan_for_org(self):
        from backend.services.subscription_service import seed_default_plans
        run(seed_default_plans(self.mock_db))
        # Get starter plan id
        plans_resp = self.client.get("/api/v1/subscriptions/plans")
        starter = next(p for p in plans_resp.json() if p["slug"] == "starter")

        resp = self.client.post(
            f"/api/v1/subscriptions/admin/orgs/{self.org_id}/activate",
            json={"plan_id": starter["id"], "billing_cycle": "monthly"},
            headers=self._auth(self.admin_token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["plan_slug"] == "starter"
        assert data["organization_id"] == self.org_id

    def test_admin_negative_price_rejected(self):
        resp = self.client.post("/api/v1/subscriptions/admin/plans", json={
            "name": "Bad",
            "slug": "bad-price",
            "price_monthly_paise": -1,
        }, headers=self._auth(self.admin_token))
        assert resp.status_code == 422  # validation error

    def test_entitlements_after_activation(self):
        from backend.services.subscription_service import seed_default_plans
        run(seed_default_plans(self.mock_db))
        plans_resp = self.client.get("/api/v1/subscriptions/plans")
        starter = next(p for p in plans_resp.json() if p["slug"] == "starter")

        # Activate
        self.client.post(
            f"/api/v1/subscriptions/admin/orgs/{self.org_id}/activate",
            json={"plan_id": starter["id"]},
            headers=self._auth(self.admin_token),
        )

        # Check entitlements
        resp = self.client.get("/api/v1/subscriptions/my/entitlements",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_subscription"] is True
        assert data["plan_slug"] == "starter"
        assert "limits" in data
        assert data["limits"]["max_concurrent_calls"] >= 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
