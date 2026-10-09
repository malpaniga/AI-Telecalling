"""M23 tests — Customer Billing Portal.

Tests:
1.  /billing-portal/overview — returns subscription + wallet + recent payments
2.  /billing-portal/subscription — current plan details, days_remaining
3.  /billing-portal/plans — public plans list with is_current flag
4.  /billing-portal/subscribe — creates Razorpay order (amount from plan, not frontend)
5.  /billing-portal/cancel — cancels at period end
6.  /billing-portal/wallet — balance + recent transactions
7.  /billing-portal/packs — calling packs list with price_inr
8.  /billing-portal/packs/{id}/buy — creates order for calling pack
9.  /billing-portal/payments — payment history
10. /billing-portal/invoices — invoice list
11. /billing-portal/invoices/{id} — single invoice (tenant isolation)
12. Provider costs NEVER in any billing portal response
13. Non-owner cannot cancel/subscribe (403)
14. Tenant isolation: invoice from org B not visible to org A
15. No subscription returns has_subscription: false (not an error)
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
# HTTP test setup
# ---------------------------------------------------------------------------
@SKIP
class TestCustomerBillingPortal:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.billing_portal import router as bp_router
        from backend.api.v1.billing import router as billing_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(bp_router, prefix="/api/v1")
        self.test_app.include_router(billing_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        self.mock_redis = MagicMock()
        self.mock_redis.set = AsyncMock()
        self.mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = self.mock_redis

        self.client = TestClient(self.test_app)

        # Owner org
        r1 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Billing Org",
            "org_email": "billing@org.com",
            "email": "owner@billing.com",
            "password": "BillingPass1!",
        })
        self.owner_token = r1.json()["access_token"]
        self.org_id = r1.json()["organization_id"]

        # Viewer (non-owner)
        from backend.core.auth import create_token_pair
        from backend.models.base import new_id
        tokens = create_token_pair(new_id(), "viewer@billing.com", "viewer", self.org_id)
        self.viewer_token = tokens["access_token"]

        # Second org for isolation tests
        r2 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Other Billing",
            "org_email": "other8@org.com",
            "email": "user@other8.com",
            "password": "Other8Pass1!",
        })
        self.other_token = r2.json()["access_token"]
        self.other_org_id = r2.json()["organization_id"]

        # Seed plans and packs
        run(self._seed_data())

    async def _seed_data(self):
        from backend.services.subscription_service import seed_default_plans
        from backend.services.wallet_service import seed_default_packs, WalletService
        await seed_default_plans(self.mock_db)
        await seed_default_packs(self.mock_db)
        await WalletService(self.mock_db).grant_bonus(self.org_id, 1000, "test")

    def _auth(self, t): return {"Authorization": f"Bearer {t}"}

    # ---- Overview ----
    def test_overview_no_subscription(self):
        resp = self.client.get("/api/v1/billing-portal/overview",
                               headers=self._auth(self.owner_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["subscription"] is None
        assert "wallet" in data
        assert "recent_payments" in data

    def test_overview_no_provider_costs(self):
        resp = self.client.get("/api/v1/billing-portal/overview",
                               headers=self._auth(self.owner_token))
        body_str = str(resp.json()).lower()
        assert "provider_cost" not in body_str
        assert "gross_profit" not in body_str
        assert "gross_margin" not in body_str

    # ---- Subscription ----
    def test_subscription_no_plan(self):
        resp = self.client.get("/api/v1/billing-portal/subscription",
                               headers=self._auth(self.owner_token))
        assert resp.status_code == 200
        assert resp.json()["has_subscription"] is False

    def test_subscription_after_activate(self):
        # Get plan id
        plans = self.client.get("/api/v1/billing-portal/plans",
                                headers=self._auth(self.owner_token)).json()
        starter = next(p for p in plans if p["slug"] == "starter")

        # Admin-activate via subscriptions endpoint
        from backend.core.auth import create_token_pair
        admin_tok = create_token_pair("adm-1", "a@p.com", "platform_admin", None)["access_token"]

        # Use the subscription admin endpoint (from M3)
        from backend.api.v1.subscriptions import router as sub_router
        self.test_app.include_router(sub_router, prefix="/api/v1")
        self.client.post(
            f"/api/v1/subscriptions/admin/orgs/{self.org_id}/activate",
            json={"plan_id": starter["id"]},
            headers=self._auth(admin_tok),
        )

        resp = self.client.get("/api/v1/billing-portal/subscription",
                               headers=self._auth(self.owner_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_subscription"] is True
        assert data["subscription"]["plan_slug"] == "starter"
        assert "days_remaining" in data
        assert "limits" in data["subscription"]

    # ---- Plans ----
    def test_plans_list(self):
        resp = self.client.get("/api/v1/billing-portal/plans",
                               headers=self._auth(self.owner_token))
        assert resp.status_code == 200
        plans = resp.json()
        assert len(plans) >= 3
        slugs = {p["slug"] for p in plans}
        assert "starter" in slugs
        assert "growth" in slugs
        assert "pro" in slugs

    def test_plans_have_is_current_field(self):
        resp = self.client.get("/api/v1/billing-portal/plans",
                               headers=self._auth(self.owner_token))
        plans = resp.json()
        assert all("is_current" in p for p in plans)

    def test_plans_have_pricing_in_paise_and_inr(self):
        resp = self.client.get("/api/v1/billing-portal/plans",
                               headers=self._auth(self.owner_token))
        for plan in resp.json():
            assert isinstance(plan["price_monthly_paise"], int)
            assert isinstance(plan["price_monthly_inr"], float)
            assert plan["price_monthly_inr"] == plan["price_monthly_paise"] / 100

    # ---- Subscribe ----
    def test_subscribe_creates_order(self):
        plans = self.client.get("/api/v1/billing-portal/plans",
                                headers=self._auth(self.owner_token)).json()
        starter = next(p for p in plans if p["slug"] == "starter")
        resp = self.client.post("/api/v1/billing-portal/subscribe",
                                json={"plan_id": starter["id"], "billing_cycle": "monthly"},
                                headers=self._auth(self.owner_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "order_id" in data
        assert "provider_order_id" in data
        assert data["amount_paise"] == starter["price_monthly_paise"]
        assert "provider_cost" not in str(data)

    def test_subscribe_amount_from_server_not_frontend(self):
        """Amount MUST come from server (plan lookup), not frontend."""
        plans = self.client.get("/api/v1/billing-portal/plans",
                                headers=self._auth(self.owner_token)).json()
        starter = next(p for p in plans if p["slug"] == "starter")
        resp = self.client.post("/api/v1/billing-portal/subscribe",
                                json={"plan_id": starter["id"]},
                                headers=self._auth(self.owner_token))
        assert resp.status_code == 200
        # Amount must equal plan price (server-determined)
        assert resp.json()["amount_paise"] == starter["price_monthly_paise"]

    def test_viewer_cannot_subscribe(self):
        plans = self.client.get("/api/v1/billing-portal/plans",
                                headers=self._auth(self.owner_token)).json()
        resp = self.client.post("/api/v1/billing-portal/subscribe",
                                json={"plan_id": plans[0]["id"]},
                                headers=self._auth(self.viewer_token))
        assert resp.status_code == 403

    # ---- Cancel ----
    def test_cancel_no_subscription_returns_404(self):
        resp = self.client.post("/api/v1/billing-portal/cancel",
                                json={"at_period_end": True},
                                headers=self._auth(self.owner_token))
        assert resp.status_code == 404

    def test_viewer_cannot_cancel(self):
        resp = self.client.post("/api/v1/billing-portal/cancel",
                                json={},
                                headers=self._auth(self.viewer_token))
        assert resp.status_code == 403

    # ---- Wallet ----
    def test_wallet_overview(self):
        resp = self.client.get("/api/v1/billing-portal/wallet",
                               headers=self._auth(self.owner_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["available_credits"] == 1000
        assert "recent_transactions" in data
        # Must not contain provider costs
        assert "provider_cost" not in str(data)

    # ---- Calling packs ----
    def test_list_packs(self):
        resp = self.client.get("/api/v1/billing-portal/packs",
                               headers=self._auth(self.owner_token))
        assert resp.status_code == 200
        packs = resp.json()
        assert len(packs) >= 1
        for p in packs:
            assert isinstance(p["price_paise"], int)
            assert isinstance(p["price_inr"], float)
            assert "total_credits" in p
            # No provider costs
            assert "provider_cost" not in str(p)

    def test_buy_pack_creates_order(self):
        packs = self.client.get("/api/v1/billing-portal/packs",
                                headers=self._auth(self.owner_token)).json()
        paid_packs = [p for p in packs if p["price_paise"] > 0]
        if not paid_packs:
            pytest.skip("No paid packs available")
        pack = paid_packs[0]
        resp = self.client.post(f"/api/v1/billing-portal/packs/{pack['id']}/buy",
                                headers=self._auth(self.owner_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "order_id" in data
        assert data["amount_paise"] == pack["price_paise"]

    # ---- Payment history ----
    def test_payment_history_empty(self):
        resp = self.client.get("/api/v1/billing-portal/payments",
                               headers=self._auth(self.owner_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    # ---- Invoices ----
    def test_invoices_empty(self):
        resp = self.client.get("/api/v1/billing-portal/invoices",
                               headers=self._auth(self.owner_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_invoice_tenant_isolation(self):
        """Org A cannot see Org B's invoice."""
        from backend.repositories.billing_repo import InvoiceRepository
        inv = run(InvoiceRepository(self.mock_db).create(
            organization_id=self.org_id,
            order_id="ord-1", payment_id="pay-1",
            description="Test Invoice", subtotal_paise=100000, tax_paise=0,
            org_name="Billing Org", org_email="billing@org.com",
        ))
        resp = self.client.get(f"/api/v1/billing-portal/invoices/{inv.id}",
                               headers=self._auth(self.other_token))
        assert resp.status_code == 404

    def test_owner_can_see_own_invoice(self):
        from backend.repositories.billing_repo import InvoiceRepository
        inv = run(InvoiceRepository(self.mock_db).create(
            organization_id=self.org_id,
            order_id="ord-2", payment_id="pay-2",
            description="Owner Invoice", subtotal_paise=200000, tax_paise=36000,
            org_name="Billing Org", org_email="billing@org.com",
        ))
        resp = self.client.get(f"/api/v1/billing-portal/invoices/{inv.id}",
                               headers=self._auth(self.owner_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_paise"] == 236000
        assert data["total_inr"] == 2360.0

    # ---- Auth ----
    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/v1/billing-portal/overview")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
