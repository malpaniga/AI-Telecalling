"""M27 tests — Reconciliation.

Tests:
1.  ReconciliationResult.add_failure sets status=fail and increments count
2.  run_all returns overall pass when no issues
3.  check_payment_without_credits — detects captured payment with no wallet credit
4.  check_credits_without_payment — detects wallet credit with no payment
5.  check_duplicate_webhooks — detects same event processed multiple times
6.  check_invoice_mismatch — detects invoice total != payment amount
7.  check_wallet_ledger_mismatch — detects ledger sum != wallet balance
8.  check_usage_mismatch — detects negative usage credits
9.  check_provider_cost_mismatch — detects provider breakdown != usage event cost
10. run_all — when an inconsistency is injected, overall_status=fail
11. run_all — when all consistent, overall_status=pass
12. HTTP: /reconciliation/run requires platform role (403 for customer)
13. HTTP: report returns check list with all 7 check names
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
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


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Test: ReconciliationResult
# ---------------------------------------------------------------------------
class TestReconciliationResult:
    def test_initial_pass(self):
        from backend.services.reconciliation_service import ReconciliationResult
        r = ReconciliationResult("test")
        assert r.status == "pass"
        assert r.count == 0

    def test_add_failure(self):
        from backend.services.reconciliation_service import ReconciliationResult
        r = ReconciliationResult("test")
        r.add_failure({"issue": "broken"})
        assert r.status == "fail"
        assert r.count == 1

    def test_to_dict(self):
        from backend.services.reconciliation_service import ReconciliationResult
        r = ReconciliationResult("test")
        r.add_failure({"issue": "broken"})
        d = r.to_dict()
        assert d["check"] == "test"
        assert d["status"] == "fail"
        assert d["count"] == 1


# ---------------------------------------------------------------------------
# Test: Individual checks
# ---------------------------------------------------------------------------
@SKIP
class TestReconciliationChecks:
    def setup_method(self):
        self.db = _get_mock_db()

    def _svc(self):
        from backend.services.reconciliation_service import ReconciliationService
        return ReconciliationService(self.db)

    def test_payment_without_credits_pass(self):
        async def _t():
            svc = self._svc()
            result = await svc.check_payment_without_credits(datetime(2000,1,1,tzinfo=timezone.utc))
            assert result.status == "pass"
        run(_t())

    def test_payment_without_credits_fail(self):
        async def _t():
            from backend.models.base import new_id
            await self.db["payments"].insert_one({
                "_id": new_id(), "organization_id": "org-1",
                "order_id": "ord-1", "amount_paise": 100,
                "status": "captured", "created_at": _now(),
            })
            svc = self._svc()
            result = await svc.check_payment_without_credits(datetime(2000,1,1,tzinfo=timezone.utc))
            assert result.status == "fail"
            assert result.count == 1
        run(_t())

    def test_credits_without_payment_pass(self):
        async def _t():
            svc = self._svc()
            result = await svc.check_credits_without_payment(datetime(2000,1,1,tzinfo=timezone.utc))
            assert result.status == "pass"
        run(_t())

    def test_credits_without_payment_fail(self):
        async def _t():
            from backend.models.base import new_id
            await self.db["wallet_transactions"].insert_one({
                "_id": new_id(), "organization_id": "org-1",
                "wallet_id": "w-1", "transaction_type": "purchase",
                "order_id": "ord-missing", "credits_delta": 100,
                "created_at": _now(),
            })
            svc = self._svc()
            result = await svc.check_credits_without_payment(datetime(2000,1,1,tzinfo=timezone.utc))
            assert result.status == "fail"
        run(_t())

    def test_duplicate_webhook_pass(self):
        async def _t():
            svc = self._svc()
            result = await svc.check_duplicate_webhooks(datetime(2000,1,1,tzinfo=timezone.utc))
            assert result.status == "pass"
        run(_t())

    def test_duplicate_webhook_fail(self):
        async def _t():
            from backend.models.base import new_id
            for _ in range(2):
                await self.db["webhook_events"].insert_one({
                    "_id": new_id(), "provider": "razorpay",
                    "event_id": "evt-dup-1", "event_type": "payment.captured",
                    "received_at": _now(),
                })
            svc = self._svc()
            result = await svc.check_duplicate_webhooks(datetime(2000,1,1,tzinfo=timezone.utc))
            assert result.status == "fail"
            assert result.count == 1
        run(_t())

    def test_invoice_mismatch_pass(self):
        async def _t():
            from backend.models.base import new_id
            pay_id = new_id()
            await self.db["payments"].insert_one({
                "_id": pay_id, "amount_paise": 100, "status": "captured",
                "created_at": _now(),
            })
            await self.db["invoices"].insert_one({
                "_id": new_id(), "payment_id": pay_id,
                "total_paise": 100, "issued_at": _now(),
            })
            svc = self._svc()
            result = await svc.check_invoice_mismatch(datetime(2000,1,1,tzinfo=timezone.utc))
            assert result.status == "pass"
        run(_t())

    def test_invoice_mismatch_fail(self):
        async def _t():
            from backend.models.base import new_id
            pay_id = new_id()
            await self.db["payments"].insert_one({
                "_id": pay_id, "amount_paise": 200, "status": "captured",
                "created_at": _now(),
            })
            await self.db["invoices"].insert_one({
                "_id": new_id(), "payment_id": pay_id,
                "total_paise": 100, "issued_at": _now(),
            })
            svc = self._svc()
            result = await svc.check_invoice_mismatch(datetime(2000,1,1,tzinfo=timezone.utc))
            assert result.status == "fail"
        run(_t())

    def test_wallet_ledger_mismatch_pass(self):
        async def _t():
            from backend.models.base import new_id
            wallet_id = new_id()
            await self.db["wallets"].insert_one({
                "_id": wallet_id, "organization_id": "org-1",
                "available_credits": 100, "reserved_credits": 0,
            })
            await self.db["wallet_transactions"].insert_one({
                "_id": new_id(), "wallet_id": wallet_id,
                "available_delta": 100, "created_at": _now(),
            })
            svc = self._svc()
            result = await svc.check_wallet_ledger_mismatch()
            assert result.status == "pass"
        run(_t())

    def test_wallet_ledger_mismatch_fail(self):
        async def _t():
            from backend.models.base import new_id
            wallet_id = new_id()
            await self.db["wallets"].insert_one({
                "_id": wallet_id, "organization_id": "org-1",
                "available_credits": 100, "reserved_credits": 0,
            })
            # Ledger says 50, wallet says 100 — mismatch
            await self.db["wallet_transactions"].insert_one({
                "_id": new_id(), "wallet_id": wallet_id,
                "available_delta": 50, "created_at": _now(),
            })
            svc = self._svc()
            result = await svc.check_wallet_ledger_mismatch()
            assert result.status == "fail"
        run(_t())

    def test_usage_mismatch_pass(self):
        async def _t():
            from backend.models.base import new_id
            await self.db["wallets"].insert_one({
                "_id": new_id(), "organization_id": "org-1",
                "available_credits": 0, "reserved_credits": 0,
            })
            svc = self._svc()
            result = await svc.check_usage_mismatch(datetime(2000,1,1,tzinfo=timezone.utc))
            assert result.status == "pass"
        run(_t())

    def test_provider_cost_mismatch_pass(self):
        async def _t():
            from backend.models.base import new_id
            await self.db["provider_usage"].insert_one({
                "_id": new_id(), "organization_id": "org-1",
                "call_id": "call-match",
                "telephony_cost_paise": 50, "stt_cost_paise": 30,
                "llm_cost_paise": 20, "tts_cost_paise": 10,
                "created_at": _now(),
            })
            await self.db["usage_events"].insert_one({
                "_id": new_id(), "call_id": "call-match",
                "provider_cost_paise": 110, "created_at": _now(),
            })
            svc = self._svc()
            result = await svc.check_provider_cost_mismatch(datetime(2000,1,1,tzinfo=timezone.utc))
            assert result.status == "pass"
        run(_t())

    def test_provider_cost_mismatch_fail(self):
        async def _t():
            from backend.models.base import new_id
            await self.db["provider_usage"].insert_one({
                "_id": new_id(), "organization_id": "org-1",
                "call_id": "call-mism",
                "telephony_cost_paise": 50, "stt_cost_paise": 30,
                "llm_cost_paise": 20, "tts_cost_paise": 10,
                "created_at": _now(),
            })
            # ProviderUsage total = 110, but usage_events says 200 — mismatch
            await self.db["usage_events"].insert_one({
                "_id": new_id(), "call_id": "call-mism",
                "provider_cost_paise": 200, "created_at": _now(),
            })
            svc = self._svc()
            result = await svc.check_provider_cost_mismatch(datetime(2000,1,1,tzinfo=timezone.utc))
            assert result.status == "fail"
        run(_t())


# ---------------------------------------------------------------------------
# Test: run_all
# ---------------------------------------------------------------------------
@SKIP
class TestRunAll:
    def setup_method(self):
        self.db = _get_mock_db()

    def _svc(self):
        from backend.services.reconciliation_service import ReconciliationService
        return ReconciliationService(self.db)

    def test_run_all_pass_when_clean(self):
        async def _t():
            svc = self._svc()
            report = await svc.run_all(hours=24)
            assert report["overall_status"] == "pass"
            assert len(report["checks"]) == 7
        run(_t())

    def test_run_all_fail_when_inconsistent(self):
        async def _t():
            from backend.models.base import new_id
            await self.db["payments"].insert_one({
                "_id": new_id(), "organization_id": "org-1",
                "order_id": "ord-bad", "amount_paise": 100,
                "status": "captured", "created_at": _now(),
            })
            svc = self._svc()
            report = await svc.run_all(hours=24)
            assert report["overall_status"] == "fail"
        run(_t())

    def test_run_all_has_all_7_checks(self):
        async def _t():
            svc = self._svc()
            report = await svc.run_all()
            check_names = {c["check"] for c in report["checks"]}
            required = {
                "payment_without_credits",
                "credits_without_payment",
                "duplicate_webhook",
                "invoice_mismatch",
                "wallet_ledger_mismatch",
                "usage_mismatch",
                "provider_cost_mismatch",
            }
            assert required.issubset(check_names)
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestReconciliationHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.reconciliation import router as recon_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(recon_router, prefix="/api/v1")

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
            "org_name": "Recon Org",
            "org_email": "recon@org.com",
            "email": "user@recon.com",
            "password": "ReconPass1!",
        })
        self.customer_token = r.json()["access_token"]

    def _auth(self, t): return {"Authorization": f"Bearer {t}"}

    def test_customer_blocked(self):
        resp = self.client.get("/api/v1/reconciliation/run",
                               headers=self._auth(self.customer_token))
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/v1/reconciliation/run")
        assert resp.status_code == 401

    def test_run_endpoint_clean(self):
        resp = self.client.get("/api/v1/reconciliation/run",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_status"] == "pass"
        assert len(data["checks"]) == 7

    def test_report_endpoint_alias(self):
        resp = self.client.get("/api/v1/reconciliation/report",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        assert "overall_status" in resp.json()

    def test_run_with_hours_param(self):
        resp = self.client.get("/api/v1/reconciliation/run?hours=48",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        assert resp.json()["hours_window"] == 48

    def test_all_7_check_names_present(self):
        resp = self.client.get("/api/v1/reconciliation/run",
                               headers=self._auth(self.admin_token))
        names = {c["check"] for c in resp.json()["checks"]}
        required = {
            "payment_without_credits", "credits_without_payment",
            "duplicate_webhook", "invoice_mismatch",
            "wallet_ledger_mismatch", "usage_mismatch",
            "provider_cost_mismatch",
        }
        assert required.issubset(names)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
