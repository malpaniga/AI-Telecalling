"""Tests for Admin Calling Packs CRUD & Seed cleanup."""

import asyncio
import os
import sys
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


@pytest.mark.skipif(not _mongomock_available(), reason="mongomock_motor not installed")
class TestCallingPacksCRUD:
    def setup_method(self):
        import mongomock_motor
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.wallet import router as wallet_router
        from backend.api.v1.admin import router as admin_router
        from backend.core import db as db_module, redis as redis_module
        from backend.core.auth import create_token_pair

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(wallet_router, prefix="/api/v1")
        self.test_app.include_router(admin_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        tokens = create_token_pair("admin-1", "admin@platform.com", "platform_admin", None)
        self.admin_token = tokens["access_token"]

        user_tokens = create_token_pair("user-1", "user@org.com", "customer_admin", "org-1")
        self.customer_token = user_tokens["access_token"]

    def _auth_header(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_admin_create_update_delete_calling_pack(self):
        # 1. Create Pack
        payload = {
            "name": "Super Pack",
            "slug": "super-pack",
            "credits": 2500,
            "bonus_credits": 250,
            "price_paise": 149900,
            "description": "2,500 credits for high-volume calling",
            "validity_days": 180,
            "sort_order": 5,
            "is_public": True,
        }
        res = self.client.post(
            "/api/v1/wallet/admin/packs",
            json=payload,
            headers=self._auth_header(self.admin_token),
        )
        assert res.status_code == 201, res.text
        data = res.json()
        pack_id = data["id"]
        assert data["name"] == "Super Pack"
        assert data["credits"] == 2500
        assert data["price_paise"] == 149900
        assert data["price_inr"] == 1499.0

        # 2. Update Pack
        update_payload = {
            "credits": 3000,
            "price_paise": 199900,
            "description": "3,000 credits updated",
            "is_active": False,
        }
        res_update = self.client.patch(
            f"/api/v1/wallet/admin/packs/{pack_id}",
            json=update_payload,
            headers=self._auth_header(self.admin_token),
        )
        assert res_update.status_code == 200, res_update.text
        updated = res_update.json()
        assert updated["credits"] == 3000
        assert updated["price_paise"] == 199900
        assert updated["description"] == "3,000 credits updated"
        assert updated["is_active"] is False

        # 3. List via admin endpoint includes all details
        res_list = self.client.get(
            "/api/v1/admin/calling-packs?include_inactive=true",
            headers=self._auth_header(self.admin_token),
        )
        assert res_list.status_code == 200
        packs = res_list.json()
        match = next((p for p in packs if p["id"] == pack_id), None)
        assert match is not None
        assert match["description"] == "3,000 credits updated"

        # 4. Delete Pack
        res_del = self.client.delete(
            f"/api/v1/wallet/admin/packs/{pack_id}",
            headers=self._auth_header(self.admin_token),
        )
        assert res_del.status_code == 200
        assert res_del.json()["success"] is True

        # Verify gone
        res_list_after = self.client.get(
            "/api/v1/admin/calling-packs?include_inactive=true",
            headers=self._auth_header(self.admin_token),
        )
        packs_after = res_list_after.json()
        assert not any(p["id"] == pack_id for p in packs_after)

    def test_customer_cannot_modify_packs(self):
        res = self.client.post(
            "/api/v1/wallet/admin/packs",
            json={"name": "Hacker Pack", "slug": "hacker", "credits": 100, "price_paise": 100},
            headers=self._auth_header(self.customer_token),
        )
        assert res.status_code == 403

    def test_seed_updates_legacy_descriptions(self):
        from backend.repositories.wallet_repo import CallingPackRepository
        from backend.services.wallet_service import seed_default_packs

        repo = CallingPackRepository(self.mock_db)
        # Seed an old legacy pack with ~17 minutes in description
        run(repo.create(
            name="Starter Pack",
            slug="starter-pack",
            credits=1000,
            price_paise=99900,
            description="1,000 calling credits (~17 minutes of AI calls).",
        ))

        # Re-run seed
        run(seed_default_packs(self.mock_db))

        # Check that legacy description was cleaned up
        pack = run(repo.find_by_slug("starter-pack"))
        assert pack is not None
        assert "~17 minutes" not in pack.description
        assert "calling credits" in pack.description
