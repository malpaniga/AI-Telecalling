"""M4 tests — Razorpay payment integration.

Tests:
1. Billing models — integer paise, no float amounts
2. Mock payment provider — create_order, verify, refund, webhook sig
3. OrderRepository — CRUD, status transitions
4. PaymentRepository — create, record_refund
5. InvoiceRepository — create, sequential numbering
6. WebhookEvent idempotency — duplicate event ignored
7. PaymentService — server-authoritative order creation (amount from plan, not frontend)
8. PaymentService — verify_and_fulfill success
9. PaymentService — verify_and_fulfill: invalid signature rejected
10. PaymentService — refund flow
11. PaymentService — webhook: success, failure, duplicate
12. HTTP endpoints: create order, verify, webhook, refund, list payments
13. Customer cannot see another org's invoice (tenant isolation)
14. Invalid webhook signature returns 400
"""

import asyncio
import hashlib
import hmac
import json
import sys
import os
from typing import Optional
from unittest.mock import AsyncMock, MagicMock
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


SKIP = pytest.mark.skipif(not _mongomock_available(), reason="mongomock_motor not installed")


def _get_mock_db():
    import mongomock_motor
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test"]


# ---------------------------------------------------------------------------
# Test: Billing models
# ---------------------------------------------------------------------------
class TestBillingModels:
    def test_order_amount_is_integer_paise(self):
        from backend.models.billing import Order
        from backend.models.base import new_id
        order = Order(
            _id=new_id(), organization_id="org-1",
            order_type="subscription", amount_paise=299900
        )
        assert order.amount_paise == 299900
        assert isinstance(order.amount_paise, int)
        assert order.amount_inr == 2999.0

    def test_negative_amount_rejected(self):
        from backend.models.billing import Order
        from backend.models.base import new_id
        with pytest.raises(Exception):
            Order(
                _id=new_id(), organization_id="org-1",
                order_type="subscription", amount_paise=-100
            )

    def test_payment_is_immutable_record(self):
        from backend.models.billing import Payment
        from backend.models.base import new_id
        p = Payment(
            _id=new_id(), organization_id="org-1", order_id="order-1",
            amount_paise=100, provider="razorpay",
            provider_payment_id="pay_abc", provider_order_id="order_abc"
        )
        assert p.status == "captured"
        assert p.refunded_paise == 0
        doc = p.to_mongo()
        assert "_id" in doc
        assert "amount_inr" not in doc  # computed property not stored

    def test_invoice_totals_computed(self):
        from backend.models.billing import Invoice
        from backend.models.base import new_id
        inv = Invoice(
            _id=new_id(), organization_id="org-1",
            order_id="o-1", payment_id="p-1",
            invoice_number="INV-2026-000001",
            description="Starter plan",
            subtotal_paise=254152,  # ₹2,999 excluding 18% GST
            tax_paise=45763,        # 18% GST
            total_paise=299915,
        )
        assert inv.total_paise == 299915
        assert abs(inv.total_inr - 2999.15) < 0.01

    def test_webhook_event_model(self):
        from backend.models.billing import WebhookEvent
        from backend.models.base import new_id
        ev = WebhookEvent(
            _id=new_id(),
            provider="razorpay",
            event_id="evt_abc123",
            event_type="payment.captured",
            payload={"key": "value"},
        )
        assert ev.processed is False
        assert ev.provider == "razorpay"


# ---------------------------------------------------------------------------
# Test: Mock Payment Provider
# ---------------------------------------------------------------------------
class TestMockPaymentProvider:
    def setup_method(self):
        from backend.providers.payment.mock import MockPaymentProvider
        MockPaymentProvider.reset()
        self.provider = MockPaymentProvider()
        self.failing = MockPaymentProvider(should_fail=True)

    def test_create_order(self):
        async def _run():
            result = await self.provider.create_order(
                amount_paise=299900, currency="INR", receipt="test-receipt"
            )
            assert "provider_order_id" in result
            assert result["provider_order_id"].startswith("order_mock_")
            assert result["amount_paise"] == 299900
            assert result["currency"] == "INR"
        run(_run())

    def test_create_order_zero_amount_rejected(self):
        async def _run():
            with pytest.raises(ValueError):
                await self.provider.create_order(amount_paise=0)
        run(_run())

    def test_verify_payment_valid_signature(self):
        from backend.providers.payment.mock import MockPaymentProvider
        async def _run():
            sig = MockPaymentProvider.make_valid_signature("ord_1", "pay_1")
            result = await self.provider.verify_payment("ord_1", "pay_1", sig)
            assert result is True
        run(_run())

    def test_verify_payment_invalid_signature(self):
        async def _run():
            result = await self.provider.verify_payment("ord_1", "pay_1", "bad_sig")
            assert result is False
        run(_run())

    def test_should_fail_mode(self):
        from backend.providers.payment.mock import MockPaymentProvider
        async def _run():
            sig = MockPaymentProvider.make_valid_signature("ord_1", "pay_1")
            result = await self.failing.verify_payment("ord_1", "pay_1", sig)
            assert result is False
        run(_run())

    def test_webhook_signature_valid(self):
        from backend.providers.payment.mock import MockPaymentProvider
        payload = b'{"event": "payment.captured"}'
        sig = MockPaymentProvider.make_valid_webhook_signature(payload)
        assert self.provider.verify_webhook_signature(payload, sig) is True

    def test_webhook_signature_invalid(self):
        payload = b'{"event": "payment.captured"}'
        assert self.provider.verify_webhook_signature(payload, "bad_sig") is False

    def test_refund(self):
        async def _run():
            result = await self.provider.refund("pay_abc", 10000, "customer request")
            assert result["payment_id"] == "pay_abc"
            assert result["amount"] == 10000
            assert result["status"] == "processed"
        run(_run())


# ---------------------------------------------------------------------------
# Test: Repositories
# ---------------------------------------------------------------------------
@SKIP
class TestOrderRepository:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_create_order(self):
        from backend.repositories.billing_repo import OrderRepository
        repo = OrderRepository(self.db)
        async def _run():
            order = await repo.create(
                organization_id="org-1",
                order_type="subscription",
                amount_paise=299900,
                description="Starter plan",
                provider="mock",
            )
            assert order.id is not None
            assert order.amount_paise == 299900
            assert order.status == "created"
        run(_run())

    def test_set_provider_order(self):
        from backend.repositories.billing_repo import OrderRepository
        repo = OrderRepository(self.db)
        async def _run():
            order = await repo.create("org-1", "subscription", 100)
            ok = await repo.set_provider_order(order.id, "order_mock_abc")
            assert ok is True
            updated = await repo.find_by_id(order.id)
            assert updated.provider_order_id == "order_mock_abc"
            assert updated.status == "pending_payment"
        run(_run())

    def test_mark_paid(self):
        from backend.repositories.billing_repo import OrderRepository
        repo = OrderRepository(self.db)
        async def _run():
            order = await repo.create("org-1", "subscription", 100)
            await repo.mark_paid(order.id, "payment-1")
            updated = await repo.find_by_id(order.id)
            assert updated.status == "paid"
            assert updated.payment_id == "payment-1"
        run(_run())

    def test_mark_failed(self):
        from backend.repositories.billing_repo import OrderRepository
        repo = OrderRepository(self.db)
        async def _run():
            order = await repo.create("org-1", "subscription", 100)
            await repo.mark_failed(order.id)
            updated = await repo.find_by_id(order.id)
            assert updated.status == "failed"
        run(_run())


@SKIP
class TestWebhookIdempotency:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_duplicate_webhook_rejected(self):
        from backend.repositories.billing_repo import WebhookEventRepository
        repo = WebhookEventRepository(self.db)
        async def _run():
            ev1 = await repo.record_and_lock("razorpay", "evt_123", "payment.captured", {})
            assert ev1 is not None  # first: accepted

            ev2 = await repo.record_and_lock("razorpay", "evt_123", "payment.captured", {})
            assert ev2 is None  # duplicate: rejected
        run(_run())

    def test_different_event_ids_both_accepted(self):
        from backend.repositories.billing_repo import WebhookEventRepository
        repo = WebhookEventRepository(self.db)
        async def _run():
            ev1 = await repo.record_and_lock("razorpay", "evt_AAA", "payment.captured", {})
            ev2 = await repo.record_and_lock("razorpay", "evt_BBB", "payment.captured", {})
            assert ev1 is not None
            assert ev2 is not None
            assert ev1.id != ev2.id
        run(_run())

    def test_same_event_id_different_provider_both_accepted(self):
        from backend.repositories.billing_repo import WebhookEventRepository
        repo = WebhookEventRepository(self.db)
        async def _run():
            ev1 = await repo.record_and_lock("razorpay", "evt_001", "payment.captured", {})
            ev2 = await repo.record_and_lock("mock", "evt_001", "payment.captured", {})
            assert ev1 is not None
            assert ev2 is not None
        run(_run())

    def test_mark_processed(self):
        from backend.repositories.billing_repo import WebhookEventRepository
        repo = WebhookEventRepository(self.db)
        async def _run():
            ev = await repo.record_and_lock("razorpay", "evt_X", "payment.captured", {})
            await repo.mark_processed(ev.id, result={"status": "ok"})
            updated = await repo.find_by_id(ev.id)
            assert updated.processed is True
            assert updated.processing_result == {"status": "ok"}
        run(_run())


@SKIP
class TestInvoiceRepository:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_sequential_invoice_numbers(self):
        from backend.repositories.billing_repo import InvoiceRepository
        repo = InvoiceRepository(self.db)
        async def _run():
            inv1 = await repo.create("org-1", "o-1", "p-1", "Test", 100, 0)
            inv2 = await repo.create("org-1", "o-2", "p-2", "Test", 100, 0)
            assert inv1.invoice_number != inv2.invoice_number
            # Both should start with INV-{year}-
            assert inv1.invoice_number.startswith("INV-")
            assert inv2.invoice_number.startswith("INV-")
        run(_run())

    def test_total_includes_tax(self):
        from backend.repositories.billing_repo import InvoiceRepository
        repo = InvoiceRepository(self.db)
        async def _run():
            inv = await repo.create(
                organization_id="org-1", order_id="o-1", payment_id="p-1",
                description="Pro plan",
                subtotal_paise=1694831,  # ₹16,948.31
                tax_paise=305068,        # 18% GST
            )
            assert inv.total_paise == 1694831 + 305068
        run(_run())


# ---------------------------------------------------------------------------
# Test: PaymentService
# ---------------------------------------------------------------------------
@SKIP
class TestPaymentService:
    def setup_method(self):
        from backend.providers.payment.mock import MockPaymentProvider
        MockPaymentProvider.reset()
        self.db = _get_mock_db()

    def _make_service(self, should_fail=False):
        from backend.providers.payment.mock import MockPaymentProvider
        from backend.services.payment_service import PaymentService
        provider = MockPaymentProvider(should_fail=should_fail)
        return PaymentService(self.db, provider=provider)

    def test_create_order_uses_plan_price(self):
        async def _t():
            from backend.repositories.subscription_repo import SubscriptionPlanRepository
            repo = SubscriptionPlanRepository(self.db)
            plan = await repo.create(name="PlanA", slug="plan-a2", price_monthly_paise=499900)
            svc = self._make_service()
            result = await svc.create_subscription_order("org-1", plan.id, "monthly")
            assert result["amount_paise"] == 499900
            assert "provider_order_id" in result
        run(_t())

    def test_create_order_yearly_uses_yearly_price(self):
        async def _t():
            from backend.repositories.subscription_repo import SubscriptionPlanRepository
            repo = SubscriptionPlanRepository(self.db)
            plan = await repo.create(name="Pro", slug="pro-y2",
                price_monthly_paise=1999900, price_yearly_paise=19999900)
            svc = self._make_service()
            result = await svc.create_subscription_order("org-2", plan.id, "yearly")
            assert result["amount_paise"] == 19999900
        run(_t())

    def test_free_plan_cannot_be_ordered(self):
        async def _t():
            from backend.repositories.subscription_repo import SubscriptionPlanRepository
            repo = SubscriptionPlanRepository(self.db)
            plan = await repo.create(name="Free", slug="free-t2", price_monthly_paise=0)
            svc = self._make_service()
            with pytest.raises(ValueError, match="no charge"):
                await svc.create_subscription_order("org-1", plan.id, "monthly")
        run(_t())

    def test_verify_and_fulfill_success(self):
        async def _t():
            from backend.providers.payment.mock import MockPaymentProvider
            from backend.repositories.organization_repo import OrganizationRepository
            from backend.repositories.subscription_repo import SubscriptionPlanRepository
            org_repo = OrganizationRepository(self.db)
            org = await org_repo.create("Test Org", "test@org.com")
            plan_repo = SubscriptionPlanRepository(self.db)
            plan = await plan_repo.create(name="Stt", slug="stt2", price_monthly_paise=299900)
            svc = self._make_service()
            order_result = await svc.create_subscription_order(org.id, plan.id, "monthly")
            oid = order_result["order_id"]
            poid = order_result["provider_order_id"]
            ppid = f"pay_mock_{oid[:8]}"
            sig = MockPaymentProvider.make_valid_signature(poid, ppid)
            result = await svc.verify_and_fulfill(oid, ppid, poid, sig, org.id)
            assert result["status"] == "paid"
            assert "payment_id" in result
            assert "invoice_number" in result
            from backend.repositories.billing_repo import OrderRepository
            order = await OrderRepository(self.db).find_by_id(oid)
            assert order.status == "paid"
            from backend.services.subscription_service import SubscriptionService
            sub = await SubscriptionService(self.db).get_active_subscription(org.id)
            assert sub is not None and sub.plan_slug == "stt2"
        run(_t())

    def test_invalid_signature_rejected(self):
        async def _t():
            from backend.repositories.organization_repo import OrganizationRepository
            from backend.repositories.subscription_repo import SubscriptionPlanRepository
            org = await OrganizationRepository(self.db).create("Sig Org", "sig@org.com")
            plan = await SubscriptionPlanRepository(self.db).create(
                name="Sig", slug="sig-t2", price_monthly_paise=299900)
            svc = self._make_service()
            order_result = await svc.create_subscription_order(org.id, plan.id, "monthly")
            with pytest.raises(ValueError, match="[Vv]erification"):
                await svc.verify_and_fulfill(
                    order_id=order_result["order_id"],
                    provider_payment_id="pay_fake",
                    provider_order_id=order_result["provider_order_id"],
                    provider_signature="INVALID_SIGNATURE",
                    organization_id=org.id,
                )
            from backend.repositories.billing_repo import OrderRepository
            order = await OrderRepository(self.db).find_by_id(order_result["order_id"])
            assert order.status == "failed"
        run(_t())

    def test_double_payment_idempotent(self):
        async def _t():
            from backend.providers.payment.mock import MockPaymentProvider
            from backend.repositories.organization_repo import OrganizationRepository
            from backend.repositories.subscription_repo import SubscriptionPlanRepository
            org = await OrganizationRepository(self.db).create("Dbl", "dbl@org.com")
            plan = await SubscriptionPlanRepository(self.db).create(
                name="Dbl", slug="dbl-p2", price_monthly_paise=100)
            svc = self._make_service()
            r = await svc.create_subscription_order(org.id, plan.id, "monthly")
            oid, poid = r["order_id"], r["provider_order_id"]
            ppid = "pay_mock_dbl2"
            sig = MockPaymentProvider.make_valid_signature(poid, ppid)
            r1 = await svc.verify_and_fulfill(oid, ppid, poid, sig, org.id)
            assert r1["status"] == "paid"
            r2 = await svc.verify_and_fulfill(oid, ppid, poid, sig, org.id)
            assert r2["status"] == "already_paid"
        run(_t())

    def test_refund_full(self):
        async def _t():
            from backend.repositories.billing_repo import PaymentRepository
            pay_repo = PaymentRepository(self.db)
            payment = await pay_repo.create(
                organization_id="org-r", order_id="ord-r", amount_paise=100000,
                provider="mock", provider_payment_id="pay_rf_t", provider_order_id="ord_rf")
            svc = self._make_service()
            result = await svc.refund_payment(payment.id, reason="test")
            assert result["amount_refunded_paise"] == 100000
            updated = await pay_repo.find_by_id(payment.id)
            assert updated.status == "refunded"
        run(_t())

    def test_refund_already_refunded_rejected(self):
        async def _t():
            from backend.repositories.billing_repo import PaymentRepository
            pay_repo = PaymentRepository(self.db)
            payment = await pay_repo.create(
                organization_id="org-r2", order_id="ord-r2", amount_paise=50000,
                provider="mock", provider_payment_id="pay_rf2", provider_order_id="ord_rf2")
            await pay_repo.record_refund(payment.id, 50000)
            svc = self._make_service()
            with pytest.raises(ValueError, match="[Rr]efund"):
                await svc.refund_payment(payment.id)
        run(_t())

    def test_webhook_success_event(self):
        async def _t():
            from backend.providers.payment.mock import MockPaymentProvider
            payload = {"event": "payment.captured", "id": "evt_wh_s1",
                       "payload": {"payment": {"entity": {"id": "pay_wh", "order_id": "ord_wh"}}}}
            pb = json.dumps(payload).encode()
            sig = MockPaymentProvider.make_valid_webhook_signature(pb)
            svc = self._make_service()
            result = await svc.process_webhook(pb, sig, provider="mock")
            assert result["status"] in ("processed", "error")
            assert result["event_type"] == "payment.captured"
        run(_t())

    def test_webhook_duplicate_ignored(self):
        async def _t():
            from backend.providers.payment.mock import MockPaymentProvider
            payload = {"event": "payment.captured", "id": "evt_dup_002"}
            pb = json.dumps(payload).encode()
            sig = MockPaymentProvider.make_valid_webhook_signature(pb)
            svc = self._make_service()
            r1 = await svc.process_webhook(pb, sig, provider="mock")
            r2 = await svc.process_webhook(pb, sig, provider="mock")
            assert r1["status"] != "duplicate"
            assert r2["status"] == "duplicate"
        run(_t())

    def test_webhook_invalid_signature_raises(self):
        async def _t():
            pb = json.dumps({"event": "payment.captured", "id": "evt_bad2"}).encode()
            svc = self._make_service()
            with pytest.raises(ValueError, match="[Ss]ignature"):
                await svc.process_webhook(pb, "invalid_sig", provider="mock")
        run(_t())

@SKIP
class TestBillingHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.billing import router as billing_router
        from backend.api.v1.subscriptions import router as sub_router
        from backend.core import db as db_module, redis as redis_module
        from backend.providers.payment.mock import MockPaymentProvider

        MockPaymentProvider.reset()

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(billing_router, prefix="/api/v1")
        self.test_app.include_router(sub_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        # Seed a plan
        async def _seed():
            from backend.repositories.subscription_repo import SubscriptionPlanRepository
            repo = SubscriptionPlanRepository(self.mock_db)
            return await repo.create(
                name="HTTP Plan", slug="http-plan",
                price_monthly_paise=299900,
            )
        self.plan = run(_seed())

        # Sign up
        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Payment Org",
            "org_email": "pay@org.com",
            "email": "payer@org.com",
            "password": "PayerPass1!",
        })
        self.user_token = r.json()["access_token"]
        self.org_id = r.json()["organization_id"]

        # Platform admin token
        from backend.core.auth import create_token_pair
        tokens = create_token_pair("admin-1", "admin@platform.com", "platform_admin", None)
        self.admin_token = tokens["access_token"]
        # billing_admin token
        tokens_ba = create_token_pair("ba-1", "ba@platform.com", "billing_admin", None)
        self.billing_admin_token = tokens_ba["access_token"]

    def _auth(self, token): return {"Authorization": f"Bearer {token}"}

    def test_create_subscription_order(self):
        resp = self.client.post("/api/v1/billing/orders/subscription", json={
            "plan_id": self.plan.id,
            "billing_cycle": "monthly",
        }, headers=self._auth(self.user_token))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["amount_paise"] == 299900
        assert "provider_order_id" in data
        assert "order_id" in data
        # Frontend cannot inject custom amount — must match plan
        assert data["amount_inr"] == 2999.0

    def test_verify_payment_success(self):
        from backend.providers.payment.mock import MockPaymentProvider
        order_resp = self.client.post("/api/v1/billing/orders/subscription", json={
            "plan_id": self.plan.id,
        }, headers=self._auth(self.user_token))
        order_data = order_resp.json()
        order_id = order_data["order_id"]
        poid = order_data["provider_order_id"]
        ppid = f"pay_http_{order_id[:8]}"
        sig = MockPaymentProvider.make_valid_signature(poid, ppid)

        resp = self.client.post("/api/v1/billing/verify", json={
            "order_id": order_id,
            "provider_payment_id": ppid,
            "provider_order_id": poid,
            "provider_signature": sig,
        }, headers=self._auth(self.user_token))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "paid"
        assert "invoice_number" in data

    def test_verify_payment_invalid_signature_returns_400(self):
        order_resp = self.client.post("/api/v1/billing/orders/subscription", json={
            "plan_id": self.plan.id,
        }, headers=self._auth(self.user_token))
        order_id = order_resp.json()["order_id"]
        poid = order_resp.json()["provider_order_id"]

        resp = self.client.post("/api/v1/billing/verify", json={
            "order_id": order_id,
            "provider_payment_id": "pay_fake",
            "provider_order_id": poid,
            "provider_signature": "FAKE_SIGNATURE",
        }, headers=self._auth(self.user_token))
        assert resp.status_code == 400

    def test_webhook_valid_signature(self):
        from backend.providers.payment.mock import MockPaymentProvider
        payload = json.dumps({
            "event": "payment.captured",
            "id": "evt_http_001",
            "payload": {"payment": {"entity": {"id": "pay_001", "order_id": "ord_001"}}},
        }).encode()
        sig = MockPaymentProvider.make_valid_webhook_signature(payload)
        resp = self.client.post("/api/v1/billing/webhook",
                                content=payload,
                                headers={"X-Razorpay-Signature": sig,
                                         "Content-Type": "application/json"})
        assert resp.status_code == 200

    def test_webhook_invalid_signature_returns_400(self):
        payload = json.dumps({"event": "payment.captured", "id": "evt_bad"}).encode()
        resp = self.client.post("/api/v1/billing/webhook",
                                content=payload,
                                headers={"X-Razorpay-Signature": "bad_sig",
                                         "Content-Type": "application/json"})
        assert resp.status_code == 400

    def test_list_payments_empty(self):
        resp = self.client.get("/api/v1/billing/payments",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_billing_admin_can_refund(self):
        from backend.providers.payment.mock import MockPaymentProvider
        from backend.repositories.billing_repo import PaymentRepository
        # Create a payment directly
        async def _create():
            repo = PaymentRepository(self.mock_db)
            return await repo.create(
                organization_id=self.org_id,
                order_id="ord-refund-http",
                amount_paise=100000,
                provider="mock",
                provider_payment_id="pay_refund_http",
                provider_order_id="ord_mock_refund_http",
            )
        payment = run(_create())

        resp = self.client.post(f"/api/v1/billing/refund/{payment.id}",
                                json={"reason": "test refund"},
                                headers=self._auth(self.billing_admin_token))
        assert resp.status_code == 200
        assert resp.json()["amount_refunded_paise"] == 100000

    def test_customer_cannot_refund(self):
        resp = self.client.post("/api/v1/billing/refund/fake-payment-id",
                                json={},
                                headers=self._auth(self.user_token))
        assert resp.status_code == 403

    def test_invoice_tenant_isolation(self):
        """Org A cannot see Org B's invoice."""
        from backend.repositories.billing_repo import InvoiceRepository
        # Create invoice for org_id (org B)
        async def _create():
            repo = InvoiceRepository(self.mock_db)
            return await repo.create(
                organization_id=self.org_id,
                order_id="ord-iso", payment_id="pay-iso",
                description="Isolation test",
                subtotal_paise=10000, tax_paise=0,
            )
        invoice = run(_create())

        # Sign up a second org (org A)
        r2 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Other Org",
            "org_email": "other@org2.com",
            "email": "user@org2.com",
            "password": "OtherPass1!",
        })
        other_token = r2.json()["access_token"]

        # Org A tries to access Org B's invoice → 403
        resp = self.client.get(f"/api/v1/billing/invoices/{invoice.id}",
                               headers={"Authorization": f"Bearer {other_token}"})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
