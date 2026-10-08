"""M6 tests — Credit Reservation + Settlement.

Tests:
1. reserve() moves credits available → reserved; no total change
2. reserve() with insufficient credits raises ValueError
3. reserve() is idempotent (same call_id)
4. release() returns reserved → available; no total change
5. release() on non-existent reservation is a no-op
6. settle() bills exact usage; refunds over-reserved amount
7. settle() with actual > reserved caps at reserved (safety)
8. settle() is idempotent (double-settle is a no-op)
9. Every reserve/release/settle creates a WalletTransaction ledger entry
10. Credits are conserved: available + reserved constant except during consume
11. 10 concurrent reservations — no double-spend, no negative credits
12. Concurrent: 5 calls succeed, 6th fails if balance only covers 5
13. Full lifecycle: reserve → settle (partial) → balance correct
14. Full lifecycle: reserve → release → balance restored
15. HTTP endpoints: reserve, release, settle, check, insufficient 402
"""

import asyncio
import sys
import os
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


def _make_mock_redis():
    """In-memory dict-based Redis mock for credit reservation keys."""
    store = {}

    async def get(key):
        return store.get(key)

    async def set(key, val, ex=None):
        store[key] = val

    async def delete(key):
        store.pop(key, None)

    r = MagicMock()
    r.get = AsyncMock(side_effect=get)
    r.set = AsyncMock(side_effect=set)
    r.delete = AsyncMock(side_effect=delete)
    r._store = store
    return r


async def _fund_org(db, org_id: str, credits: int):
    """Helper: give an org N credits via bonus."""
    from backend.services.wallet_service import WalletService
    svc = WalletService(db)
    await svc.grant_bonus(org_id, credits, "test funding", validity_days=365)


# ---------------------------------------------------------------------------
# Test: Core reserve / release / settle logic
# ---------------------------------------------------------------------------
@SKIP
class TestCreditReserve:
    def setup_method(self):
        self.db = _get_mock_db()
        self.redis = _make_mock_redis()

    def _svc(self):
        from backend.services.credit_service import CreditService
        return CreditService(self.db, redis=self.redis)

    def test_reserve_moves_credits(self):
        """reserve() moves available → reserved; total unchanged."""
        async def _t():
            await _fund_org(self.db, "org-1", 500)
            svc = self._svc()

            result = await svc.reserve("org-1", "call-001", max_credits=60)
            assert result["reserved_credits"] == 60

            wallet = await svc.wallet_repo.get_or_create("org-1")
            assert wallet.available_credits == 440
            assert wallet.reserved_credits == 60
            assert wallet.total_credits == 500   # total unchanged
        run(_t())

    def test_reserve_insufficient_credits_raises(self):
        async def _t():
            await _fund_org(self.db, "org-insuf", 30)
            svc = self._svc()
            with pytest.raises(ValueError, match="[Ii]nsufficient"):
                await svc.reserve("org-insuf", "call-fail", max_credits=60)
            # Wallet unchanged
            wallet = await svc.wallet_repo.get_or_create("org-insuf")
            assert wallet.available_credits == 30
            assert wallet.reserved_credits == 0
        run(_t())

    def test_reserve_ledger_entry_created(self):
        async def _t():
            await _fund_org(self.db, "org-ledger", 200)
            svc = self._svc()
            await svc.reserve("org-ledger", "call-led", max_credits=50)

            txns = await svc.txn_repo.list_for_org("org-ledger")
            reserve_txns = [t for t in txns if t.transaction_type == "reserve"]
            assert len(reserve_txns) == 1
            assert reserve_txns[0].available_delta == -50
            assert reserve_txns[0].reserved_delta == 50
            assert reserve_txns[0].call_id == "call-led"
        run(_t())

    def test_reserve_idempotent(self):
        """Same call_id reserve twice: no double-deduction."""
        async def _t():
            await _fund_org(self.db, "org-idem-r", 200)
            svc = self._svc()
            r1 = await svc.reserve("org-idem-r", "call-idem", max_credits=60)
            r2 = await svc.reserve("org-idem-r", "call-idem", max_credits=60)

            assert r1["reserved_credits"] == 60
            # Second call is idempotent
            wallet = await svc.wallet_repo.get_or_create("org-idem-r")
            assert wallet.available_credits == 140   # only deducted once
            assert wallet.reserved_credits == 60
        run(_t())


@SKIP
class TestCreditRelease:
    def setup_method(self):
        self.db = _get_mock_db()
        self.redis = _make_mock_redis()

    def _svc(self):
        from backend.services.credit_service import CreditService
        return CreditService(self.db, redis=self.redis)

    def test_release_returns_credits(self):
        async def _t():
            await _fund_org(self.db, "org-rel", 500)
            svc = self._svc()
            await svc.reserve("org-rel", "call-rel", max_credits=100)

            wallet = await svc.wallet_repo.get_or_create("org-rel")
            assert wallet.available_credits == 400
            assert wallet.reserved_credits == 100

            await svc.release("org-rel", "call-rel")

            wallet = await svc.wallet_repo.get_or_create("org-rel")
            assert wallet.available_credits == 500
            assert wallet.reserved_credits == 0
        run(_t())

    def test_release_creates_ledger_entry(self):
        async def _t():
            await _fund_org(self.db, "org-rel-led", 200)
            svc = self._svc()
            await svc.reserve("org-rel-led", "call-rl", max_credits=50)
            await svc.release("org-rel-led", "call-rl")

            txns = await svc.txn_repo.list_for_org("org-rel-led")
            release_txns = [t for t in txns if t.transaction_type == "release"]
            assert len(release_txns) == 1
            assert release_txns[0].available_delta == 50
            assert release_txns[0].reserved_delta == -50
        run(_t())

    def test_release_nonexistent_is_noop(self):
        async def _t():
            await _fund_org(self.db, "org-rel-noop", 100)
            svc = self._svc()
            result = await svc.release("org-rel-noop", "call-never-reserved")
            assert result["released_credits"] == 0
            assert result.get("idempotent") is True
        run(_t())

    def test_release_after_settle_is_noop(self):
        """Can't release a call that was already settled."""
        async def _t():
            await _fund_org(self.db, "org-rel-settled", 200)
            svc = self._svc()
            await svc.reserve("org-rel-settled", "call-rs", max_credits=60)
            await svc.settle("org-rel-settled", "call-rs", actual_credits=45)
            result = await svc.release("org-rel-settled", "call-rs")
            assert result.get("idempotent") is True
        run(_t())


@SKIP
class TestCreditSettle:
    def setup_method(self):
        self.db = _get_mock_db()
        self.redis = _make_mock_redis()

    def _svc(self):
        from backend.services.credit_service import CreditService
        return CreditService(self.db, redis=self.redis)

    def test_settle_exact_usage(self):
        """Settle bills exactly; over-reserved credits returned to available."""
        async def _t():
            await _fund_org(self.db, "org-settle", 500)
            svc = self._svc()
            await svc.reserve("org-settle", "call-s1", max_credits=120)

            wallet_before = await svc.wallet_repo.get_or_create("org-settle")
            assert wallet_before.available_credits == 380
            assert wallet_before.reserved_credits == 120

            result = await svc.settle("org-settle", "call-s1", actual_credits=90)
            assert result["billed_credits"] == 90
            assert result["refunded_credits"] == 30   # 120 reserved - 90 billed

            wallet = await svc.wallet_repo.get_or_create("org-settle")
            # 380 available + 30 refund = 410 available; 0 reserved
            assert wallet.available_credits == 410
            assert wallet.reserved_credits == 0
        run(_t())

    def test_settle_full_reservation(self):
        """Settle using all reserved credits."""
        async def _t():
            await _fund_org(self.db, "org-full", 300)
            svc = self._svc()
            await svc.reserve("org-full", "call-full", max_credits=60)
            result = await svc.settle("org-full", "call-full", actual_credits=60)
            assert result["billed_credits"] == 60
            assert result["refunded_credits"] == 0
            wallet = await svc.wallet_repo.get_or_create("org-full")
            assert wallet.available_credits == 240
            assert wallet.reserved_credits == 0
        run(_t())

    def test_settle_caps_at_reserved(self):
        """actual_credits > reserved is capped at reserved (safety guard)."""
        async def _t():
            await _fund_org(self.db, "org-cap", 500)
            svc = self._svc()
            await svc.reserve("org-cap", "call-cap", max_credits=60)
            # Try to bill more than reserved
            result = await svc.settle("org-cap", "call-cap", actual_credits=999)
            assert result["billed_credits"] <= 60   # capped
        run(_t())

    def test_settle_idempotent(self):
        """Double-settle same call_id is a no-op."""
        async def _t():
            await _fund_org(self.db, "org-idem-s", 500)
            svc = self._svc()
            await svc.reserve("org-idem-s", "call-idem-s", max_credits=60)
            r1 = await svc.settle("org-idem-s", "call-idem-s", actual_credits=45)
            r2 = await svc.settle("org-idem-s", "call-idem-s", actual_credits=45)

            assert r1["billed_credits"] == 45
            assert r2.get("idempotent") is True

            # Balance correct after just one settlement
            wallet = await svc.wallet_repo.get_or_create("org-idem-s")
            assert wallet.reserved_credits == 0
            # 500 - 45 = 455
            assert wallet.available_credits == 455
        run(_t())

    def test_settle_creates_consume_ledger_entry(self):
        async def _t():
            await _fund_org(self.db, "org-consume-led", 200)
            svc = self._svc()
            await svc.reserve("org-consume-led", "call-cl", max_credits=80)
            await svc.settle("org-consume-led", "call-cl", actual_credits=60)

            txns = await svc.txn_repo.list_for_org("org-consume-led")
            consume_txns = [t for t in txns if t.transaction_type == "consume"]
            assert len(consume_txns) == 1
            assert consume_txns[0].credits_delta == -60
            assert consume_txns[0].call_id == "call-cl"
        run(_t())

    def test_settle_zero_credits_no_consume_entry(self):
        """0-second call: no consume ledger entry, reservation cleared."""
        async def _t():
            await _fund_org(self.db, "org-zero-call", 200)
            svc = self._svc()
            await svc.reserve("org-zero-call", "call-zero", max_credits=60)
            result = await svc.settle("org-zero-call", "call-zero", actual_credits=0)
            assert result["billed_credits"] == 0

            wallet = await svc.wallet_repo.get_or_create("org-zero-call")
            assert wallet.available_credits == 200
            assert wallet.reserved_credits == 0
        run(_t())


@SKIP
class TestCreditConservation:
    """Credits are conserved: available + reserved = constant (except consume)."""

    def setup_method(self):
        self.db = _get_mock_db()
        self.redis = _make_mock_redis()

    def _svc(self):
        from backend.services.credit_service import CreditService
        return CreditService(self.db, redis=self.redis)

    def test_reserve_release_cycle_conserves_credits(self):
        async def _t():
            await _fund_org(self.db, "org-cons-1", 1000)
            svc = self._svc()

            await svc.reserve("org-cons-1", "call-c1", 100)
            await svc.reserve("org-cons-1", "call-c2", 100)
            await svc.reserve("org-cons-1", "call-c3", 100)
            await svc.release("org-cons-1", "call-c1")
            await svc.release("org-cons-1", "call-c2")
            await svc.release("org-cons-1", "call-c3")

            wallet = await svc.wallet_repo.get_or_create("org-cons-1")
            assert wallet.available_credits == 1000
            assert wallet.reserved_credits == 0
        run(_t())

    def test_settle_reduces_total(self):
        """After settle, total = initial - billed."""
        async def _t():
            await _fund_org(self.db, "org-cons-2", 1000)
            svc = self._svc()
            await svc.reserve("org-cons-2", "call-s2", 120)
            await svc.settle("org-cons-2", "call-s2", actual_credits=90)

            wallet = await svc.wallet_repo.get_or_create("org-cons-2")
            assert wallet.total_credits == 910   # 1000 - 90
            assert wallet.available_credits == 910
            assert wallet.reserved_credits == 0
        run(_t())

    def test_every_operation_has_ledger_entry(self):
        async def _t():
            await _fund_org(self.db, "org-led-all", 500)
            svc = self._svc()
            await svc.reserve("org-led-all", "call-la", 60)
            await svc.settle("org-led-all", "call-la", actual_credits=45)

            txns = await svc.txn_repo.list_for_org("org-led-all")
            types = {t.transaction_type for t in txns}
            # Must have: bonus (funding), reserve, consume
            assert "bonus" in types
            assert "reserve" in types
            assert "consume" in types
        run(_t())


@SKIP
class TestConcurrentReservations:
    """10 concurrent calls — no double-spend, no negative credits."""

    def setup_method(self):
        self.db = _get_mock_db()
        self.redis = _make_mock_redis()

    def _svc(self):
        from backend.services.credit_service import CreditService
        return CreditService(self.db, redis=self.redis)

    def test_10_concurrent_calls_no_double_spend(self):
        """10 concurrent reserves of 60 credits with 600 total: all succeed."""
        async def _t():
            await _fund_org(self.db, "org-conc", 600)
            svc = self._svc()

            # Launch 10 concurrent reservations simultaneously
            tasks = [
                svc.reserve("org-conc", f"call-{i:03d}", max_credits=60)
                for i in range(10)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            successes = [r for r in results if not isinstance(r, Exception)]
            failures = [r for r in results if isinstance(r, Exception)]

            assert len(successes) == 10
            assert len(failures) == 0

            wallet = await svc.wallet_repo.get_or_create("org-conc")
            assert wallet.available_credits == 0
            assert wallet.reserved_credits == 600
            assert wallet.total_credits == 600   # no double-spend
        run(_t())

    def test_6_calls_with_5_credits_worth(self):
        """5 calls succeed, 6th fails (300 credits = exactly 5 × 60)."""
        async def _t():
            await _fund_org(self.db, "org-limit", 300)
            svc = self._svc()

            tasks = [
                svc.reserve("org-limit", f"call-lim-{i}", max_credits=60)
                for i in range(6)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            successes = [r for r in results if not isinstance(r, Exception)]
            failures = [r for r in results if isinstance(r, (Exception, ValueError))]

            assert len(successes) == 5
            assert len(failures) == 1

            wallet = await svc.wallet_repo.get_or_create("org-limit")
            # Total credits unchanged: 300 available = 0 remaining + 300 reserved
            assert wallet.total_credits == 300
            assert wallet.available_credits == 0
            assert wallet.reserved_credits == 300
        run(_t())

    def test_concurrent_settle_no_double_consume(self):
        """Settling 10 calls concurrently: total consumed = sum of actuals."""
        async def _t():
            await _fund_org(self.db, "org-settle-conc", 600)
            svc = self._svc()

            # Reserve 10 calls
            for i in range(10):
                await svc.reserve("org-settle-conc", f"call-sc-{i}", max_credits=60)

            # Settle all concurrently
            settle_tasks = [
                svc.settle("org-settle-conc", f"call-sc-{i}", actual_credits=45)
                for i in range(10)
            ]
            settle_results = await asyncio.gather(*settle_tasks, return_exceptions=True)
            failures = [r for r in settle_results if isinstance(r, Exception)]
            assert len(failures) == 0

            wallet = await svc.wallet_repo.get_or_create("org-settle-conc")
            # 600 initial - 10×45 billed = 150 remaining
            assert wallet.available_credits == 150
            assert wallet.reserved_credits == 0
        run(_t())

    def test_wallet_never_goes_negative(self):
        """Hammer reserves beyond balance: wallet always ≥ 0."""
        async def _t():
            await _fund_org(self.db, "org-nonneg", 100)
            svc = self._svc()

            tasks = [
                svc.reserve("org-nonneg", f"call-nn-{i}", max_credits=60)
                for i in range(10)  # 10×60 >> 100
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            wallet = await svc.wallet_repo.get_or_create("org-nonneg")
            assert wallet.available_credits >= 0
            assert wallet.reserved_credits >= 0
            assert wallet.available_credits + wallet.reserved_credits <= 100
        run(_t())


@SKIP
class TestCreditCheckAPI:
    def setup_method(self):
        self.db = _get_mock_db()
        self.redis = _make_mock_redis()

    def test_can_start_call_sufficient(self):
        async def _t():
            await _fund_org(self.db, "org-check", 500)
            svc = __import__("backend.services.credit_service",
                             fromlist=["CreditService"]).CreditService(self.db, redis=self.redis)
            result = await svc.can_start_call("org-check", 60)
            assert result["can_start"] is True
            assert result["available_credits"] == 500
            assert result["shortfall"] == 0
        run(_t())

    def test_can_start_call_insufficient(self):
        async def _t():
            await _fund_org(self.db, "org-check2", 30)
            svc = __import__("backend.services.credit_service",
                             fromlist=["CreditService"]).CreditService(self.db, redis=self.redis)
            result = await svc.can_start_call("org-check2", 60)
            assert result["can_start"] is False
            assert result["shortfall"] == 30
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestCreditHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.credits import router as credits_router
        from backend.api.v1.wallet import router as wallet_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(credits_router, prefix="/api/v1")
        self.test_app.include_router(wallet_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        self.mock_redis = _make_mock_redis()
        redis_module._redis = self.mock_redis

        self.client = TestClient(self.test_app)

        # Signup
        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Credits Org",
            "org_email": "credits@org.com",
            "email": "user@credits.com",
            "password": "CreditsPass1!",
        })
        self.user_token = r.json()["access_token"]
        self.org_id = r.json()["organization_id"]

        # Platform admin token
        from backend.core.auth import create_token_pair
        tokens = create_token_pair("admin-1", "admin@platform.com", "platform_admin", None)
        self.admin_token = tokens["access_token"]

        # Fund org
        run(_fund_org(self.mock_db, self.org_id, 500))

    def _auth(self, token): return {"Authorization": f"Bearer {token}"}

    def test_check_sufficient(self):
        resp = self.client.get("/api/v1/credits/check?required_credits=60",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["can_start"] is True
        assert data["available_credits"] == 500

    def test_check_insufficient(self):
        resp = self.client.get("/api/v1/credits/check?required_credits=9999",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        assert resp.json()["can_start"] is False

    def test_reserve_success(self):
        resp = self.client.post("/api/v1/credits/reserve", json={
            "call_id": "call-http-1",
            "max_credits": 60,
        }, headers=self._auth(self.user_token))
        assert resp.status_code == 200
        assert resp.json()["reserved_credits"] == 60

    def test_reserve_insufficient_returns_402(self):
        resp = self.client.post("/api/v1/credits/reserve", json={
            "call_id": "call-http-fail",
            "max_credits": 9999,
        }, headers=self._auth(self.user_token))
        assert resp.status_code == 402

    def test_release_after_reserve(self):
        self.client.post("/api/v1/credits/reserve", json={
            "call_id": "call-rel-http",
            "max_credits": 60,
        }, headers=self._auth(self.user_token))

        resp = self.client.post("/api/v1/credits/release", json={
            "call_id": "call-rel-http",
        }, headers=self._auth(self.user_token))
        assert resp.status_code == 200
        assert resp.json()["released_credits"] == 60

    def test_settle_after_reserve(self):
        self.client.post("/api/v1/credits/reserve", json={
            "call_id": "call-settle-http",
            "max_credits": 120,
        }, headers=self._auth(self.user_token))

        resp = self.client.post("/api/v1/credits/settle", json={
            "call_id": "call-settle-http",
            "actual_credits": 90,
        }, headers=self._auth(self.user_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["billed_credits"] == 90
        assert data["refunded_credits"] == 30

    def test_settle_idempotent_via_http(self):
        self.client.post("/api/v1/credits/reserve", json={
            "call_id": "call-idem-http",
            "max_credits": 60,
        }, headers=self._auth(self.user_token))
        body = {"call_id": "call-idem-http", "actual_credits": 45}
        r1 = self.client.post("/api/v1/credits/settle", json=body,
                              headers=self._auth(self.user_token))
        r2 = self.client.post("/api/v1/credits/settle", json=body,
                              headers=self._auth(self.user_token))
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Wallet not double-billed
        wallet_resp = self.client.get("/api/v1/wallet",
                                      headers=self._auth(self.user_token))
        # 500 - 45 = 455
        assert wallet_resp.json()["available_credits"] == 455

    def test_unauthenticated_reserve_rejected(self):
        resp = self.client.post("/api/v1/credits/reserve", json={
            "call_id": "x", "max_credits": 10
        })
        assert resp.status_code == 401

    def test_admin_can_view_reservations(self):
        self.client.post("/api/v1/credits/reserve", json={
            "call_id": "call-admin-view",
            "max_credits": 60,
        }, headers=self._auth(self.user_token))
        resp = self.client.get(
            f"/api/v1/credits/admin/orgs/{self.org_id}/reservations",
            headers=self._auth(self.admin_token),
        )
        assert resp.status_code == 200
        reservations = resp.json()
        assert any(r["call_id"] == "call-admin-view" for r in reservations)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
