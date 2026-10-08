"""M5 tests — Calling Packs + Wallet.

Tests:
1. CallingPack model — integer credits/paise, bonus, total_credits
2. Wallet model — non-negative credits, total = available + reserved
3. WalletTransaction — all required fields, immutable
4. CreditLot — expiry computation, available_from_lot
5. WalletService.purchase_credits — buy 2000 credits → wallet=2000, ledger=+2000, lot=2000
6. WalletService.grant_bonus — every movement has ledger entry
7. WalletService.admin_adjustment — add and deduct
8. WalletService.admin_adjustment — deduct beyond balance → raises
9. WalletService.process_expiry — expired lots removed from wallet
10. Idempotency — same idempotency_key is safe to call multiple times
11. No negative balance — wallet never goes below zero
12. Seed calling packs — idempotent
13. HTTP: list packs, get wallet, buy pack order, admin bonus, admin adjust
14. Customer cannot see another org's wallet
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone
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
# Test: Models
# ---------------------------------------------------------------------------
class TestWalletModels:
    def test_calling_pack_total_credits(self):
        from backend.models.wallet import CallingPack
        from backend.models.base import new_id
        pack = CallingPack(_id=new_id(), name="X", slug="x", credits=1000,
                           price_paise=99900, bonus_credits=100)
        assert pack.total_credits == 1100
        assert pack.credits == 1000
        assert pack.bonus_credits == 100

    def test_calling_pack_zero_bonus(self):
        from backend.models.wallet import CallingPack
        from backend.models.base import new_id
        pack = CallingPack(_id=new_id(), name="Y", slug="y", credits=500, price_paise=50000)
        assert pack.total_credits == 500
        assert pack.bonus_credits == 0

    def test_negative_credits_rejected(self):
        from backend.models.wallet import CallingPack
        from backend.models.base import new_id
        with pytest.raises(Exception):
            CallingPack(_id=new_id(), name="Z", slug="z", credits=-1, price_paise=100)

    def test_zero_credits_rejected(self):
        from backend.models.wallet import CallingPack
        from backend.models.base import new_id
        with pytest.raises(Exception):
            CallingPack(_id=new_id(), name="Z", slug="z", credits=0, price_paise=100)

    def test_wallet_total_credits(self):
        from backend.models.wallet import Wallet
        from backend.models.base import new_id
        w = Wallet(_id=new_id(), organization_id="org-1",
                   available_credits=1800, reserved_credits=200)
        assert w.total_credits == 2000
        assert w.available_credits == 1800
        assert w.reserved_credits == 200

    def test_wallet_negative_credits_rejected(self):
        from backend.models.wallet import Wallet
        from backend.models.base import new_id
        with pytest.raises(Exception):
            Wallet(_id=new_id(), organization_id="org-1", available_credits=-1)

    def test_wallet_transaction_valid_types(self):
        from backend.models.wallet import WalletTransaction, TRANSACTION_TYPES
        from backend.models.base import new_id
        for txn_type in TRANSACTION_TYPES:
            txn = WalletTransaction(
                _id=new_id(), organization_id="org-1", wallet_id="w-1",
                transaction_type=txn_type, credits_delta=100,
                balance_after=100,
            )
            assert txn.transaction_type == txn_type

    def test_wallet_transaction_invalid_type(self):
        from backend.models.wallet import WalletTransaction
        from backend.models.base import new_id
        with pytest.raises(Exception):
            WalletTransaction(
                _id=new_id(), organization_id="org-1", wallet_id="w-1",
                transaction_type="invalid_type", credits_delta=100, balance_after=100,
            )

    def test_credit_lot_expiry(self):
        from backend.models.wallet import CreditLot
        from backend.models.base import new_id
        # Past expiry
        past = CreditLot(
            _id=new_id(), organization_id="org-1", wallet_id="w-1",
            transaction_id="t-1", original_credits=100, remaining_credits=50,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert past.is_expired is True

        # Future expiry
        future = CreditLot(
            _id=new_id(), organization_id="org-1", wallet_id="w-1",
            transaction_id="t-2", original_credits=100, remaining_credits=50,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        assert future.is_expired is False

        # No expiry
        never = CreditLot(
            _id=new_id(), organization_id="org-1", wallet_id="w-1",
            transaction_id="t-3", original_credits=100, remaining_credits=50,
            expires_at=None,
        )
        assert never.is_expired is False

    def test_credit_lot_available_from_lot(self):
        from backend.models.wallet import CreditLot
        from backend.models.base import new_id
        lot = CreditLot(
            _id=new_id(), organization_id="o", wallet_id="w", transaction_id="t",
            original_credits=1000, remaining_credits=800, reserved_from_lot=200,
        )
        assert lot.available_from_lot == 600


# ---------------------------------------------------------------------------
# Test: WalletService — purchase, bonus, admin, expiry
# ---------------------------------------------------------------------------
@SKIP
class TestWalletServicePurchase:
    def setup_method(self):
        self.db = _get_mock_db()

    async def _seed_pack_async(self, slug="test-pack", credits=2000, bonus=0, price=199900, validity=90):
        from backend.repositories.wallet_repo import CallingPackRepository
        return await CallingPackRepository(self.db).create(
            name=slug, slug=slug, credits=credits, price_paise=price,
            bonus_credits=bonus, validity_days=validity,
        )

    def test_purchase_2000_credits(self):
        """Buy 2000 credits → wallet=2000, ledger=+2000, lot=2000"""
        async def _t():
            from backend.services.wallet_service import WalletService
            pack = await self._seed_pack_async(credits=2000)
            svc = WalletService(self.db)

            result = await svc.purchase_credits("org-1", pack.id, "order-1")
            assert result["credits_granted"] == 2000

            # Wallet
            balance = await svc.get_balance("org-1")
            assert balance["available_credits"] == 2000

            # Ledger — exactly one transaction
            txns = await svc.txn_repo.list_for_org("org-1")
            assert len(txns) == 1
            assert txns[0].transaction_type == "purchase"
            assert txns[0].credits_delta == 2000
            assert txns[0].balance_after == 2000

            # Credit lot
            lots = await svc.lot_repo.list_active("org-1")
            assert len(lots) == 1
            assert lots[0].original_credits == 2000
            assert lots[0].remaining_credits == 2000
        run(_t())

    def test_purchase_with_bonus_credits(self):
        """2000 base + 200 bonus = 2200 total credits granted"""
        async def _t():
            from backend.services.wallet_service import WalletService
            pack = await self._seed_pack_async(credits=2000, bonus=200)
            svc = WalletService(self.db)

            result = await svc.purchase_credits("org-b", pack.id, "order-b")
            assert result["credits_granted"] == 2200  # 2000 + 200 bonus

            balance = await svc.get_balance("org-b")
            assert balance["available_credits"] == 2200
        run(_t())

    def test_purchase_creates_lot_with_expiry(self):
        async def _t():
            from backend.services.wallet_service import WalletService
            pack = await self._seed_pack_async(credits=500, validity=30)
            svc = WalletService(self.db)
            result = await svc.purchase_credits("org-exp", pack.id, "order-exp")
            assert result["expires_at"] is not None
            lots = await svc.lot_repo.list_active("org-exp")
            assert lots[0].expires_at is not None
        run(_t())

    def test_every_purchase_has_ledger_entry(self):
        """Every credit movement requires an immutable WalletTransaction."""
        async def _t():
            from backend.services.wallet_service import WalletService
            pack = await self._seed_pack_async(credits=1000, slug="ledger-pack")
            svc = WalletService(self.db)

            # Three purchases
            await svc.purchase_credits("org-led", pack.id, "order-l1")
            await svc.purchase_credits("org-led", pack.id, "order-l2")
            await svc.purchase_credits("org-led", pack.id, "order-l3")

            txns = await svc.txn_repo.list_for_org("org-led")
            assert len(txns) == 3
            # All are purchase type with positive delta
            for t in txns:
                assert t.transaction_type == "purchase"
                assert t.credits_delta > 0

            balance = await svc.get_balance("org-led")
            assert balance["available_credits"] == 3000
        run(_t())

    def test_purchase_idempotency(self):
        """Same idempotency_key does not double-grant credits."""
        async def _t():
            from backend.services.wallet_service import WalletService
            pack = await self._seed_pack_async(credits=500, slug="idem-pack")
            svc = WalletService(self.db)

            idem_key = "purchase:order-idem:pack-idem"
            r1 = await svc.purchase_credits("org-idem", pack.id, "order-idem",
                                            idempotency_key=idem_key)
            r2 = await svc.purchase_credits("org-idem", pack.id, "order-idem",
                                            idempotency_key=idem_key)

            assert r1["credits_granted"] == 500
            # Second call is idempotent (may return 0 or flag)
            balance = await svc.get_balance("org-idem")
            assert balance["available_credits"] == 500  # not 1000
        run(_t())


@SKIP
class TestWalletServiceBonus:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_grant_bonus_credits(self):
        async def _t():
            from backend.services.wallet_service import WalletService
            svc = WalletService(self.db)
            result = await svc.grant_bonus("org-bon", 300, "Welcome bonus", validity_days=30)
            assert result["credits_granted"] == 300
            balance = await svc.get_balance("org-bon")
            assert balance["available_credits"] == 300
            txns = await svc.txn_repo.list_for_org("org-bon")
            assert any(t.transaction_type == "bonus" for t in txns)
        run(_t())

    def test_bonus_zero_credits_rejected(self):
        async def _t():
            from backend.services.wallet_service import WalletService
            svc = WalletService(self.db)
            with pytest.raises(ValueError):
                await svc.grant_bonus("org-bon2", 0, "zero")
        run(_t())


@SKIP
class TestWalletServiceAdminAdjustment:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_admin_add_credits(self):
        async def _t():
            from backend.services.wallet_service import WalletService
            svc = WalletService(self.db)
            result = await svc.admin_adjustment("org-adj", 500, "Test add", "admin-1")
            assert result["credits_delta"] == 500
            assert result["new_balance"] == 500
        run(_t())

    def test_admin_deduct_credits(self):
        async def _t():
            from backend.services.wallet_service import WalletService
            svc = WalletService(self.db)
            # First add some credits
            await svc.grant_bonus("org-ded", 1000, "setup")
            result = await svc.admin_adjustment("org-ded", -300, "Deduct", "admin-1")
            assert result["credits_delta"] == -300
            balance = await svc.get_balance("org-ded")
            assert balance["available_credits"] == 700
        run(_t())

    def test_admin_deduct_beyond_balance_rejected(self):
        """Wallet must never go negative."""
        async def _t():
            from backend.services.wallet_service import WalletService
            svc = WalletService(self.db)
            await svc.grant_bonus("org-neg", 100, "setup")
            with pytest.raises(ValueError, match="[Ii]nsufficient"):
                await svc.admin_adjustment("org-neg", -200, "Over-deduct", "admin-1")
            # Balance unchanged
            balance = await svc.get_balance("org-neg")
            assert balance["available_credits"] == 100
        run(_t())

    def test_admin_zero_adjustment_rejected(self):
        async def _t():
            from backend.services.wallet_service import WalletService
            svc = WalletService(self.db)
            with pytest.raises(ValueError):
                await svc.admin_adjustment("org-zero", 0, "noop", "admin-1")
        run(_t())

    def test_every_adjustment_has_ledger_entry(self):
        async def _t():
            from backend.services.wallet_service import WalletService
            svc = WalletService(self.db)
            await svc.admin_adjustment("org-led2", 200, "add", "admin-1")
            await svc.admin_adjustment("org-led2", 300, "add2", "admin-1")
            await svc.admin_adjustment("org-led2", -100, "deduct", "admin-1")
            txns = await svc.txn_repo.list_for_org("org-led2")
            assert len(txns) == 3
            assert all(t.transaction_type == "admin_adjustment" for t in txns)
            final_balance = await svc.get_balance("org-led2")
            assert final_balance["available_credits"] == 400
        run(_t())


@SKIP
class TestWalletExpiry:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_expiry_removes_credits(self):
        async def _t():
            from backend.services.wallet_service import WalletService
            from backend.repositories.wallet_repo import CreditLotRepository
            svc = WalletService(self.db)

            # Add 500 credits and manually backdate lot expiry
            await svc.grant_bonus("org-ex", 500, "to expire", validity_days=30,
                                  created_by="admin-1")
            # Manually backdate the lot
            lot_repo = CreditLotRepository(self.db)
            lots = await lot_repo.list_active("org-ex")
            assert len(lots) == 1
            past = datetime.now(timezone.utc) - timedelta(days=1)
            await lot_repo.update_by_id(lots[0].id, {"expires_at": past})

            # Run expiry
            result = await svc.process_expiry("org-ex")
            assert result["expired_credits"] == 500
            assert result["expired_lots"] == 1

            # Wallet should be 0
            balance = await svc.get_balance("org-ex")
            assert balance["available_credits"] == 0

            # Ledger should have expiry entry
            txns = await svc.txn_repo.list_for_org("org-ex")
            expiry_txns = [t for t in txns if t.transaction_type == "expiry"]
            assert len(expiry_txns) == 1
            assert expiry_txns[0].credits_delta == -500
        run(_t())

    def test_non_expired_credits_untouched(self):
        async def _t():
            from backend.services.wallet_service import WalletService
            svc = WalletService(self.db)
            await svc.grant_bonus("org-nex", 500, "future", validity_days=365)
            result = await svc.process_expiry("org-nex")
            assert result["expired_credits"] == 0
            balance = await svc.get_balance("org-nex")
            assert balance["available_credits"] == 500
        run(_t())


@SKIP
class TestSeedCallingPacks:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_seed_creates_default_packs(self):
        from backend.services.wallet_service import seed_default_packs, DEFAULT_CALLING_PACKS
        async def _t():
            created = await seed_default_packs(self.db)
            assert len(created) == len(DEFAULT_CALLING_PACKS)
            slugs = [p.slug for p in created]
            assert "starter-pack" in slugs
            assert "growth-pack" in slugs
            assert "pro-pack" in slugs
        run(_t())

    def test_seed_is_idempotent(self):
        from backend.services.wallet_service import seed_default_packs
        async def _t():
            first = await seed_default_packs(self.db)
            second = await seed_default_packs(self.db)
            assert len(second) == 0  # nothing created on second call
        run(_t())

    def test_packs_have_integer_paise(self):
        from backend.services.wallet_service import seed_default_packs
        async def _t():
            packs = await seed_default_packs(self.db)
            for pack in packs:
                assert isinstance(pack.price_paise, int)
                assert isinstance(pack.credits, int)
                if pack.slug != "trial":
                    assert pack.price_paise > 0
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestWalletHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.wallet import router as wallet_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(wallet_router, prefix="/api/v1")

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
        tokens = create_token_pair("admin-1", "admin@platform.com", "platform_admin", None)
        self.admin_token = tokens["access_token"]
        tokens_ba = create_token_pair("ba-1", "ba@platform.com", "billing_admin", None)
        self.billing_admin_token = tokens_ba["access_token"]

        # Seed packs
        from backend.services.wallet_service import seed_default_packs
        run(seed_default_packs(self.mock_db))

        # Customer signup
        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Wallet Org",
            "org_email": "wallet@org.com",
            "email": "user@wallet.com",
            "password": "WalletPass1!",
        })
        self.user_token = r.json()["access_token"]
        self.org_id = r.json()["organization_id"]

    def _auth(self, token): return {"Authorization": f"Bearer {token}"}

    def test_list_packs_no_auth(self):
        resp = self.client.get("/api/v1/wallet/packs")
        assert resp.status_code == 200
        packs = resp.json()
        assert isinstance(packs, list)
        assert len(packs) >= 1
        # Prices must be integer paise
        for p in packs:
            assert isinstance(p["price_paise"], int)
            assert isinstance(p["credits"], int)

    def test_get_wallet_empty(self):
        resp = self.client.get("/api/v1/wallet", headers=self._auth(self.user_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["available_credits"] == 0
        assert data["reserved_credits"] == 0

    def test_get_transactions_empty(self):
        resp = self.client.get("/api/v1/wallet/transactions",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_admin_grant_bonus(self):
        resp = self.client.post("/api/v1/wallet/admin/bonus", json={
            "organization_id": self.org_id,
            "credits": 2000,
            "description": "Welcome bonus",
            "validity_days": 90,
        }, headers=self._auth(self.billing_admin_token))
        assert resp.status_code == 200, resp.text
        assert resp.json()["credits_granted"] == 2000

        # Wallet updated
        wallet_resp = self.client.get("/api/v1/wallet", headers=self._auth(self.user_token))
        assert wallet_resp.json()["available_credits"] == 2000

    def test_admin_adjust_credits_add(self):
        # First add some credits
        self.client.post("/api/v1/wallet/admin/bonus", json={
            "organization_id": self.org_id, "credits": 1000,
        }, headers=self._auth(self.admin_token))

        resp = self.client.post("/api/v1/wallet/admin/adjust", json={
            "organization_id": self.org_id,
            "credits_delta": 500,
            "reason": "Test add",
        }, headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        assert resp.json()["credits_delta"] == 500

    def test_admin_adjust_deduct_beyond_balance(self):
        resp = self.client.post("/api/v1/wallet/admin/adjust", json={
            "organization_id": self.org_id,
            "credits_delta": -999999,
            "reason": "Over-deduct",
        }, headers=self._auth(self.admin_token))
        assert resp.status_code == 400

    def test_customer_cannot_admin_adjust(self):
        resp = self.client.post("/api/v1/wallet/admin/adjust", json={
            "organization_id": self.org_id,
            "credits_delta": 1000,
            "reason": "Hack",
        }, headers=self._auth(self.user_token))
        assert resp.status_code == 403

    def test_admin_create_pack(self):
        resp = self.client.post("/api/v1/wallet/admin/packs", json={
            "name": "Custom Pack",
            "slug": "custom-pack",
            "credits": 3000,
            "price_paise": 249900,
        }, headers=self._auth(self.admin_token))
        assert resp.status_code == 201
        data = resp.json()
        assert data["credits"] == 3000
        assert isinstance(data["price_paise"], int)

    def test_transactions_recorded_after_bonus(self):
        # Grant bonus
        self.client.post("/api/v1/wallet/admin/bonus", json={
            "organization_id": self.org_id, "credits": 777,
        }, headers=self._auth(self.admin_token))

        resp = self.client.get("/api/v1/wallet/transactions",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        txns = resp.json()
        assert len(txns) >= 1
        bonus_txns = [t for t in txns if t["transaction_type"] == "bonus"]
        assert len(bonus_txns) >= 1
        assert bonus_txns[0]["credits_delta"] == 777

    def test_admin_view_any_org_wallet(self):
        resp = self.client.get(f"/api/v1/wallet/admin/orgs/{self.org_id}",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200

    def test_wallet_tenant_isolation(self):
        """Customer cannot view another org's wallet via admin endpoint."""
        resp = self.client.get(f"/api/v1/wallet/admin/orgs/{self.org_id}",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 403

    def test_unauthenticated_wallet_rejected(self):
        resp = self.client.get("/api/v1/wallet")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
