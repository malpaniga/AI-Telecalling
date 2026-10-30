import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest
import mongomock_motor
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.v1.auth import router as auth_router
from backend.api.v1.billing import router as billing_router
from backend.api.v1.admin import router as admin_router
from backend.core import db as db_module, redis as redis_module
from backend.core.auth import create_token_pair
from backend.repositories.subscription_repo import SubscriptionPlanRepository


class TestManualBillingAPI:
    def setup_method(self):
        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(billing_router, prefix="/api/v1")
        self.test_app.include_router(admin_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        self.mock_redis = MagicMock()
        self.mock_redis.set = AsyncMock()
        self.mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = self.mock_redis

        self.client = TestClient(self.test_app)

        # Seed plan
        loop = asyncio.new_event_loop()
        plan_repo = SubscriptionPlanRepository(self.mock_db)
        self.plan = loop.run_until_complete(
            plan_repo.create(
                name="Starter Plan",
                slug="starter",
                price_monthly_paise=99900,
            )
        )
        loop.close()

        # Sign up customer org
        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Test Org",
            "org_email": "test@org.com",
            "email": "owner@org.com",
            "password": "Password123!",
        })
        self.user_token = r.json()["access_token"]
        self.org_id = r.json()["organization_id"]

        # Admin token
        tokens = create_token_pair("admin-1", "admin@platform.com", "platform_admin", None)
        self.admin_token = tokens["access_token"]

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_public_and_admin_settings(self):
        # Admin gets full settings
        res = self.client.get("/api/v1/admin/billing/settings", headers=self._auth(self.admin_token))
        assert res.status_code == 200
        data = res.json()
        assert data["payment_mode"] in ("manual", "razorpay")

        # Admin updates settings
        update_res = self.client.put("/api/v1/admin/billing/settings", json={
            "payment_mode": "manual",
            "admin_upi_id": "custom@upi",
            "admin_payee_name": "Custom Payee",
        }, headers=self._auth(self.admin_token))
        assert update_res.status_code == 200
        assert update_res.json()["payment_mode"] == "manual"
        assert update_res.json()["admin_upi_id"] == "custom@upi"

        # Public endpoint reflects updated settings
        pub_res = self.client.get("/api/v1/billing/settings")
        assert pub_res.status_code == 200
        pub_data = pub_res.json()
        assert pub_data["payment_mode"] == "manual"
        assert pub_data["admin_upi_id"] == "custom@upi"
        assert pub_data["admin_payee_name"] == "Custom Payee"

    def test_mode_enforcement_on_automated_order(self):
        # Set mode to manual
        self.client.put("/api/v1/admin/billing/settings", json={"payment_mode": "manual"}, headers=self._auth(self.admin_token))

        # Attempt to create Razorpay order -> 400
        res = self.client.post("/api/v1/billing/orders/subscription", json={
            "plan_id": self.plan.id,
            "billing_cycle": "monthly",
        }, headers=self._auth(self.user_token))
        assert res.status_code == 400
        assert "Manual payment mode is active" in res.json()["detail"]

    def test_manual_request_lifecycle(self):
        # Set mode to manual
        self.client.put("/api/v1/admin/billing/settings", json={"payment_mode": "manual"}, headers=self._auth(self.admin_token))

        # 1. Customer submits request
        res = self.client.post("/api/v1/billing/manual-request", json={
            "plan_id": self.plan.id,
            "billing_cycle": "monthly",
            "utr_number": "123456789012",
            "payer_note": "Paid via PhonePe",
        }, headers=self._auth(self.user_token))
        assert res.status_code == 200
        req_data = res.json()
        assert req_data["status"] == "pending"
        assert req_data["utr_number"] == "123456789012"
        req_id = req_data["id"]

        # 2. Duplicate submission blocked
        dup_res = self.client.post("/api/v1/billing/manual-request", json={
            "plan_id": self.plan.id,
            "billing_cycle": "monthly",
            "utr_number": "999999999999",
        }, headers=self._auth(self.user_token))
        assert dup_res.status_code == 400
        assert "already have a pending" in dup_res.json()["detail"].lower()

        # 3. Customer lists their requests
        list_res = self.client.get("/api/v1/billing/my-manual-requests", headers=self._auth(self.user_token))
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1
        assert list_res.json()[0]["id"] == req_id

        # 4. Admin lists requests
        admin_list = self.client.get("/api/v1/admin/billing/manual-requests", headers=self._auth(self.admin_token))
        assert admin_list.status_code == 200
        assert any(r["id"] == req_id for r in admin_list.json())

        # 5. Admin approves request
        appr_res = self.client.post(f"/api/v1/admin/billing/manual-requests/{req_id}/approve", headers=self._auth(self.admin_token))
        assert appr_res.status_code == 200

        # Verify request status approved
        admin_list_after = self.client.get("/api/v1/admin/billing/manual-requests?status=approved", headers=self._auth(self.admin_token))
        assert any(r["id"] == req_id and r["status"] == "approved" for r in admin_list_after.json())

    def test_manual_request_cancellation(self):
        # Customer creates request
        res = self.client.post("/api/v1/billing/manual-request", json={
            "plan_id": self.plan.id,
            "billing_cycle": "monthly",
            "utr_number": "UTR_CANCEL_123",
        }, headers=self._auth(self.user_token))
        req_id = res.json()["id"]

        # Cancel request
        cancel_res = self.client.post(f"/api/v1/billing/manual-request/{req_id}/cancel", headers=self._auth(self.user_token))
        assert cancel_res.status_code == 200

        # Now can submit a new request
        new_res = self.client.post("/api/v1/billing/manual-request", json={
            "plan_id": self.plan.id,
            "billing_cycle": "monthly",
            "utr_number": "UTR_NEW_456",
        }, headers=self._auth(self.user_token))
        assert new_res.status_code == 200

    def test_manual_request_rejection(self):
        # Customer creates request
        res = self.client.post("/api/v1/billing/manual-request", json={
            "plan_id": self.plan.id,
            "billing_cycle": "monthly",
            "utr_number": "UTR_REJECT_123",
        }, headers=self._auth(self.user_token))
        req_id = res.json()["id"]

        # Admin rejects with reason
        rej_res = self.client.post(f"/api/v1/admin/billing/manual-requests/{req_id}/reject", json={
            "reason": "Payment not found in bank statement",
        }, headers=self._auth(self.admin_token))
        assert rej_res.status_code == 200

        # Customer sees rejected status
        list_res = self.client.get("/api/v1/billing/my-manual-requests", headers=self._auth(self.user_token))
        rejected_req = next(r for r in list_res.json() if r["id"] == req_id)
        assert rejected_req["status"] == "rejected"
        assert rejected_req["rejection_reason"] == "Payment not found in bank statement"

    def test_razorpay_error_returns_502(self):
        # Set mode to razorpay
        self.client.put("/api/v1/admin/billing/settings", json={"payment_mode": "razorpay"}, headers=self._auth(self.admin_token))

        from unittest.mock import patch
        with patch("backend.services.payment_service.PaymentService.create_subscription_order", side_effect=Exception("Razorpay gateway unreachable")):
            res = self.client.post("/api/v1/billing/orders/subscription", json={
                "plan_id": self.plan.id,
                "billing_cycle": "monthly",
            }, headers=self._auth(self.user_token))
            assert res.status_code == 502
            assert "Payment gateway error: Razorpay gateway unreachable" in res.json()["detail"]

