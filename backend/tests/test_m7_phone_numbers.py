"""M7 tests — Phone Number Inventory.

Tests:
1. PhoneNumber model — status transitions, customer vs admin view
2. Provider details NEVER in customer response (critical abstraction)
3. add_to_inventory — duplicate number rejected
4. assign_to_org — atomic, only one concurrent winner
5. assign_to_org — already-assigned number raises
6. release_from_org — number returns to available pool
7. suspend / reactivate lifecycle
8. Concurrent reservation: only ONE of N requests can claim the same number
9. Tenant isolation: Org A cannot see Org B numbers
10. Seed demo numbers — idempotent
11. HTTP endpoints: list available, my numbers, admin assign/release/stats
12. Customer cannot access admin endpoints (403)
13. Provider fields absent from all customer responses
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


# ---------------------------------------------------------------------------
# Test: Models
# ---------------------------------------------------------------------------
class TestPhoneNumberModel:
    def test_default_status_available(self):
        from backend.models.phone_number import PhoneNumber
        from backend.models.base import new_id
        pn = PhoneNumber(_id=new_id(), number="+919876543210",
                         provider="mock")
        assert pn.status == "available"
        assert pn.organization_id is None

    def test_customer_view_strips_provider_fields(self):
        """Provider details must NEVER appear in customer-facing responses."""
        from backend.services.phone_number_service import _to_customer_view
        from backend.models.phone_number import PhoneNumber
        from backend.models.base import new_id
        pn = PhoneNumber(
            _id=new_id(), number="+919876543210", provider="twilio",
            provider_resource_id="PN_SECRET_SID",
            rental_paise_per_month=50000,
            provider_metadata={"account_sid": "AC_SECRET"},
        )
        view = _to_customer_view(pn)
        assert "provider" not in view
        assert "provider_resource_id" not in view
        assert "provider_metadata" not in view
        assert "rental_paise_per_month" not in view

    def test_customer_view_includes_required_fields(self):
        from backend.services.phone_number_service import _to_customer_view
        from backend.models.phone_number import PhoneNumber
        from backend.models.base import new_id
        pn = PhoneNumber(_id=new_id(), number="+919876543210",
                         provider="mock", display_name="Mumbai DID")
        view = _to_customer_view(pn)
        assert view["number"] == "+919876543210"
        assert view["display_name"] == "Mumbai DID"
        assert view["can_voice"] is True
        assert view["status"] == "available"

    def test_admin_view_includes_provider_fields(self):
        from backend.services.phone_number_service import _to_admin_view
        from backend.models.phone_number import PhoneNumber
        from backend.models.base import new_id
        pn = PhoneNumber(
            _id=new_id(), number="+919876543210", provider="exotel",
            provider_resource_id="EX_12345",
            rental_paise_per_month=50000,
        )
        view = _to_admin_view(pn)
        assert view["provider"] == "exotel"
        assert view["provider_resource_id"] == "EX_12345"
        assert view["rental_paise_per_month"] == 50000

    def test_assignment_model(self):
        from backend.models.phone_number import PhoneNumberAssignment
        from backend.models.base import new_id
        asgn = PhoneNumberAssignment(
            _id=new_id(),
            phone_number_id="pn-1",
            number="+919876543210",
            organization_id="org-1",
            action="assigned",
        )
        assert asgn.action == "assigned"
        assert asgn.organization_id == "org-1"


# ---------------------------------------------------------------------------
# Test: Repository
# ---------------------------------------------------------------------------
@SKIP
class TestPhoneNumberRepository:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_create_and_find(self):
        from backend.repositories.phone_number_repo import PhoneNumberRepository
        repo = PhoneNumberRepository(self.db)
        async def _t():
            pn = await repo.create("+919001000001", "mock")
            assert pn.status == "available"
            found = await repo.find_by_number("+919001000001")
            assert found is not None
            assert found.id == pn.id
        run(_t())

    def test_list_available_filters(self):
        from backend.repositories.phone_number_repo import PhoneNumberRepository
        repo = PhoneNumberRepository(self.db)
        async def _t():
            await repo.create("+919001000002", "mock", country_code="IN", number_type="local")
            await repo.create("+919001000003", "mock", country_code="IN", number_type="toll_free")
            available = await repo.list_available(number_type="local")
            types = {p.number_type for p in available}
            assert "toll_free" not in types
        run(_t())

    def test_atomic_reserve_concurrent_safety(self):
        """Two concurrent atomic_reserve calls on same number: only ONE wins."""
        from backend.repositories.phone_number_repo import PhoneNumberRepository
        repo = PhoneNumberRepository(self.db)
        async def _t():
            pn = await repo.create("+919001000010", "mock")
            # Concurrent reserve attempts
            results = await asyncio.gather(
                repo.atomic_reserve(pn.id),
                repo.atomic_reserve(pn.id),
                repo.atomic_reserve(pn.id),
            )
            winners = [r for r in results if r is not None]
            losers = [r for r in results if r is None]
            assert len(winners) == 1
            assert len(losers) == 2
            # Number is now reserved
            updated = await repo.find_by_id(pn.id)
            assert updated.status == "reserved"
        run(_t())

    def test_release_returns_to_available(self):
        from backend.repositories.phone_number_repo import PhoneNumberRepository
        repo = PhoneNumberRepository(self.db)
        async def _t():
            pn = await repo.create("+919001000020", "mock")
            await repo.atomic_assign(pn.id, "org-release-test")
            await repo.release(pn.id)
            updated = await repo.find_by_id(pn.id)
            assert updated.status == "available"
            assert updated.organization_id is None
        run(_t())

    def test_suspend_and_reactivate(self):
        from backend.repositories.phone_number_repo import PhoneNumberRepository
        repo = PhoneNumberRepository(self.db)
        async def _t():
            pn = await repo.create("+919001000030", "mock")
            await repo.atomic_assign(pn.id, "org-susp-test")
            await repo.suspend(pn.id)
            susp = await repo.find_by_id(pn.id)
            assert susp.status == "suspended"
            await repo.reactivate(pn.id)
            reactd = await repo.find_by_id(pn.id)
            assert reactd.status == "assigned"
        run(_t())


# ---------------------------------------------------------------------------
# Test: Service
# ---------------------------------------------------------------------------
@SKIP
class TestPhoneNumberService:
    def setup_method(self):
        self.db = _get_mock_db()

    def _svc(self):
        from backend.services.phone_number_service import PhoneNumberService
        return PhoneNumberService(self.db)

    def test_add_to_inventory(self):
        async def _t():
            svc = self._svc()
            pn = await svc.add_to_inventory(
                "+919002000001", "mock",
                display_name="Test DID",
                rental_paise_per_month=50000,
            )
            assert pn.number == "+919002000001"
            assert pn.status == "available"
        run(_t())

    def test_duplicate_number_rejected(self):
        async def _t():
            svc = self._svc()
            await svc.add_to_inventory("+919002000002", "mock")
            with pytest.raises(ValueError, match="already in inventory"):
                await svc.add_to_inventory("+919002000002", "mock")
        run(_t())

    def test_assign_to_org(self):
        async def _t():
            svc = self._svc()
            pn = await svc.add_to_inventory("+919002000010", "mock")
            result = await svc.assign_to_org(pn.id, "org-A", performed_by="admin-1")
            assert result["status"] == "assigned"
            assert result["organization_id"] == "org-A"
            # Provider fields NOT in result
            assert "provider" not in result
            assert "provider_resource_id" not in result
        run(_t())

    def test_assign_already_assigned_raises(self):
        async def _t():
            svc = self._svc()
            pn = await svc.add_to_inventory("+919002000011", "mock")
            await svc.assign_to_org(pn.id, "org-A")
            with pytest.raises(ValueError, match="not available"):
                await svc.assign_to_org(pn.id, "org-B")
        run(_t())

    def test_release_from_org(self):
        async def _t():
            svc = self._svc()
            pn = await svc.add_to_inventory("+919002000020", "mock")
            await svc.assign_to_org(pn.id, "org-C")
            await svc.release_from_org(pn.id)
            updated = await svc.repo.find_by_id(pn.id)
            assert updated.status == "available"
            assert updated.organization_id is None
        run(_t())

    def test_release_creates_audit_record(self):
        async def _t():
            svc = self._svc()
            pn = await svc.add_to_inventory("+919002000021", "mock")
            await svc.assign_to_org(pn.id, "org-audit")
            await svc.release_from_org(pn.id, notes="Org cancelled")
            history = await svc.assignment_repo.history_for_number(pn.id)
            actions = [h.action for h in history]
            assert "assigned" in actions
            assert "released" in actions
        run(_t())

    def test_suspend_and_reactivate(self):
        async def _t():
            svc = self._svc()
            pn = await svc.add_to_inventory("+919002000030", "mock")
            await svc.assign_to_org(pn.id, "org-D")
            await svc.suspend_number(pn.id, reason="Non-payment")
            susp = await svc.repo.find_by_id(pn.id)
            assert susp.status == "suspended"
            await svc.reactivate_number(pn.id)
            reactd = await svc.repo.find_by_id(pn.id)
            assert reactd.status == "assigned"
        run(_t())

    def test_reactivate_non_suspended_raises(self):
        async def _t():
            svc = self._svc()
            pn = await svc.add_to_inventory("+919002000031", "mock")
            await svc.assign_to_org(pn.id, "org-E")
            with pytest.raises(ValueError, match="not suspended"):
                await svc.reactivate_number(pn.id)
        run(_t())

    def test_list_org_numbers_tenant_isolation(self):
        """Org A cannot see Org B numbers."""
        async def _t():
            svc = self._svc()
            pn_a = await svc.add_to_inventory("+919002000040", "mock")
            pn_b = await svc.add_to_inventory("+919002000041", "mock")
            await svc.assign_to_org(pn_a.id, "org-iso-A")
            await svc.assign_to_org(pn_b.id, "org-iso-B")

            numbers_a = await svc.list_org_numbers("org-iso-A")
            numbers_b = await svc.list_org_numbers("org-iso-B")

            ids_a = {n["id"] for n in numbers_a}
            ids_b = {n["id"] for n in numbers_b}

            assert pn_a.id in ids_a
            assert pn_b.id not in ids_a  # CRITICAL: Org A cannot see Org B number

            assert pn_b.id in ids_b
            assert pn_a.id not in ids_b  # CRITICAL: Org B cannot see Org A number
        run(_t())

    def test_get_number_for_org_wrong_org_returns_none(self):
        """get_number_for_org returns None if number belongs to a different org."""
        async def _t():
            svc = self._svc()
            pn = await svc.add_to_inventory("+919002000050", "mock")
            await svc.assign_to_org(pn.id, "org-owner")
            result = await svc.get_number_for_org(pn.id, "org-other")
            assert result is None
        run(_t())

    def test_provider_fields_never_in_customer_response(self):
        """Provider details must not leak into any customer-facing response."""
        async def _t():
            svc = self._svc()
            pn = await svc.add_to_inventory(
                "+919002000060", "twilio",
                provider_resource_id="PN_TWILIO_SECRET_123",
                rental_paise_per_month=75000,
            )
            await svc.assign_to_org(pn.id, "org-provider-check")
            numbers = await svc.list_org_numbers("org-provider-check")
            assert len(numbers) == 1
            num = numbers[0]
            assert "provider" not in num
            assert "provider_resource_id" not in num
            assert "provider_metadata" not in num
            assert "rental_paise_per_month" not in num
            assert "PN_TWILIO_SECRET_123" not in str(num)
        run(_t())

    def test_inventory_stats(self):
        async def _t():
            svc = self._svc()
            await svc.add_to_inventory("+919002000070", "mock")
            await svc.add_to_inventory("+919002000071", "mock")
            pn = await svc.add_to_inventory("+919002000072", "mock")
            await svc.assign_to_org(pn.id, "org-stats")
            stats = await svc.get_inventory_stats()
            assert stats["available"] >= 2
            assert stats["assigned"] >= 1
            assert stats["total"] >= 3
        run(_t())


@SKIP
class TestConcurrentAssignment:
    """Only one org can claim the same number — concurrent request safety."""

    def setup_method(self):
        self.db = _get_mock_db()

    def test_concurrent_assign_only_one_wins(self):
        """5 concurrent assign attempts for the same number: exactly 1 wins."""
        async def _t():
            from backend.services.phone_number_service import PhoneNumberService
            svc = PhoneNumberService(self.db)
            pn = await svc.add_to_inventory("+919003000001", "mock")

            async def try_assign(org_id: str):
                try:
                    return await svc.assign_to_org(pn.id, org_id)
                except (ValueError, RuntimeError) as e:
                    return str(e)

            results = await asyncio.gather(
                try_assign("org-conc-1"),
                try_assign("org-conc-2"),
                try_assign("org-conc-3"),
                try_assign("org-conc-4"),
                try_assign("org-conc-5"),
            )

            # Exactly one success (dict), rest are error strings
            successes = [r for r in results if isinstance(r, dict)]
            failures = [r for r in results if isinstance(r, str)]

            assert len(successes) == 1, f"Expected 1 winner, got {len(successes)}: {successes}"
            assert len(failures) == 4, f"Expected 4 failures, got {len(failures)}"

            # Number is assigned to exactly one org
            updated = await svc.repo.find_by_id(pn.id)
            assert updated.status == "assigned"
            assert updated.organization_id in [
                "org-conc-1", "org-conc-2", "org-conc-3", "org-conc-4", "org-conc-5"
            ]
        run(_t())

    def test_different_numbers_concurrent_all_succeed(self):
        """5 concurrent assigns for 5 different numbers: all succeed."""
        async def _t():
            from backend.services.phone_number_service import PhoneNumberService
            svc = PhoneNumberService(self.db)
            numbers = []
            for i in range(5):
                pn = await svc.add_to_inventory(f"+91900400000{i}", "mock")
                numbers.append(pn)

            async def assign(pn, org_id):
                return await svc.assign_to_org(pn.id, org_id)

            results = await asyncio.gather(
                *[assign(numbers[i], f"org-diff-{i}") for i in range(5)]
            )
            assert all(isinstance(r, dict) for r in results)
            assert all(r["status"] == "assigned" for r in results)
        run(_t())


@SKIP
class TestSeedDemoNumbers:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_seed_creates_numbers(self):
        from backend.services.phone_number_service import seed_demo_numbers, SEED_NUMBERS
        async def _t():
            created = await seed_demo_numbers(self.db)
            assert len(created) == len(SEED_NUMBERS)
        run(_t())

    def test_seed_is_idempotent(self):
        from backend.services.phone_number_service import seed_demo_numbers
        async def _t():
            first = await seed_demo_numbers(self.db)
            second = await seed_demo_numbers(self.db)
            assert len(first) > 0
            assert len(second) == 0  # nothing created on second call
        run(_t())

    def test_seeded_numbers_have_no_provider_leak(self):
        """Even seed numbers: customer view must not expose provider."""
        from backend.services.phone_number_service import (
            seed_demo_numbers, PhoneNumberService, _to_customer_view
        )
        async def _t():
            nums = await seed_demo_numbers(self.db)
            for pn in nums:
                view = _to_customer_view(pn)
                assert "provider" not in view
                assert "provider_resource_id" not in view
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestPhoneNumberHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.phone_numbers import router as pn_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(pn_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        # Customer signup
        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Phone Org",
            "org_email": "phone@org.com",
            "email": "user@phone.com",
            "password": "PhonePass1!",
        })
        self.user_token = r.json()["access_token"]
        self.org_id = r.json()["organization_id"]

        # Platform admin token
        from backend.core.auth import create_token_pair
        t = create_token_pair("admin-1", "admin@platform.com", "platform_admin", None)
        self.admin_token = t["access_token"]

        # Seed some numbers via service
        from backend.services.phone_number_service import seed_demo_numbers
        run(seed_demo_numbers(self.mock_db))

    def _auth(self, token): return {"Authorization": f"Bearer {token}"}

    def test_list_available_requires_auth(self):
        resp = self.client.get("/api/v1/phone-numbers/available")
        assert resp.status_code == 401

    def test_list_available_returns_numbers(self):
        resp = self.client.get("/api/v1/phone-numbers/available",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        numbers = resp.json()
        assert isinstance(numbers, list)
        assert len(numbers) > 0

    def test_available_numbers_no_provider_fields(self):
        """CRITICAL: provider details must never appear in customer API response."""
        resp = self.client.get("/api/v1/phone-numbers/available",
                               headers=self._auth(self.user_token))
        for num in resp.json():
            assert "provider" not in num
            assert "provider_resource_id" not in num
            assert "provider_metadata" not in num
            assert "rental_paise_per_month" not in num

    def test_my_numbers_empty_initially(self):
        resp = self.client.get("/api/v1/phone-numbers/my",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_admin_can_view_inventory(self):
        resp = self.client.get("/api/v1/phone-numbers/admin",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        numbers = resp.json()
        assert len(numbers) > 0
        # Admin view DOES include provider
        assert any("provider" in n for n in numbers)

    def test_admin_add_number(self):
        resp = self.client.post("/api/v1/phone-numbers/admin", json={
            "number": "+919005000001",
            "provider": "twilio",
            "provider_resource_id": "PN_TEST_SID",
            "display_name": "Test Twilio DID",
        }, headers=self._auth(self.admin_token))
        assert resp.status_code == 201
        data = resp.json()
        assert data["number"] == "+919005000001"
        assert data["provider"] == "twilio"   # admin sees provider

    def test_admin_assign_to_org(self):
        # Get first available number id
        avail_resp = self.client.get("/api/v1/phone-numbers/available",
                                     headers=self._auth(self.user_token))
        pn_id = avail_resp.json()[0]["id"]

        resp = self.client.post(f"/api/v1/phone-numbers/admin/{pn_id}/assign", json={
            "organization_id": self.org_id,
        }, headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "assigned"
        assert data["organization_id"] == self.org_id
        # No provider fields in response (customer-safe assignment response)
        assert "provider" not in data

    def test_my_numbers_after_assignment(self):
        # Assign a number to org first
        avail_resp = self.client.get("/api/v1/phone-numbers/available",
                                     headers=self._auth(self.user_token))
        pn_id = avail_resp.json()[0]["id"]
        self.client.post(f"/api/v1/phone-numbers/admin/{pn_id}/assign",
                         json={"organization_id": self.org_id},
                         headers=self._auth(self.admin_token))

        resp = self.client.get("/api/v1/phone-numbers/my",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        numbers = resp.json()
        assert len(numbers) == 1
        assert numbers[0]["organization_id"] == self.org_id
        # Still no provider fields
        assert "provider" not in numbers[0]

    def test_customer_cannot_add_inventory(self):
        resp = self.client.post("/api/v1/phone-numbers/admin", json={
            "number": "+919005999999",
            "provider": "mock",
        }, headers=self._auth(self.user_token))
        assert resp.status_code == 403

    def test_customer_cannot_assign(self):
        avail_resp = self.client.get("/api/v1/phone-numbers/available",
                                     headers=self._auth(self.user_token))
        pn_id = avail_resp.json()[0]["id"]
        resp = self.client.post(f"/api/v1/phone-numbers/admin/{pn_id}/assign",
                                json={"organization_id": self.org_id},
                                headers=self._auth(self.user_token))
        assert resp.status_code == 403

    def test_admin_inventory_stats(self):
        resp = self.client.get("/api/v1/phone-numbers/admin/stats",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        stats = resp.json()
        assert "available" in stats
        assert "assigned" in stats
        assert "total" in stats

    def test_admin_release_number(self):
        # Assign then release
        avail_resp = self.client.get("/api/v1/phone-numbers/available",
                                     headers=self._auth(self.user_token))
        pn_id = avail_resp.json()[0]["id"]
        self.client.post(f"/api/v1/phone-numbers/admin/{pn_id}/assign",
                         json={"organization_id": self.org_id},
                         headers=self._auth(self.admin_token))

        resp = self.client.post(f"/api/v1/phone-numbers/admin/{pn_id}/release",
                                json={"notes": "test release"},
                                headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "released"

    def test_tenant_isolation_my_numbers(self):
        """Org A cannot see Org B's assigned numbers via /my endpoint."""
        # Signup second org
        r2 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Second Org",
            "org_email": "second@org2.com",
            "email": "user@org2.com",
            "password": "SecondPass1!",
        })
        token_b = r2.json()["access_token"]
        org_id_b = r2.json()["organization_id"]

        # Assign a number to org A
        avail = self.client.get("/api/v1/phone-numbers/available",
                                headers=self._auth(self.user_token)).json()
        if avail:
            pn_id = avail[0]["id"]
            self.client.post(f"/api/v1/phone-numbers/admin/{pn_id}/assign",
                             json={"organization_id": self.org_id},
                             headers=self._auth(self.admin_token))

        # Org B should see 0 numbers
        resp = self.client.get("/api/v1/phone-numbers/my",
                               headers=self._auth(token_b))
        numbers_b = resp.json()
        org_ids_seen = {n.get("organization_id") for n in numbers_b}
        assert self.org_id not in org_ids_seen, \
            f"TENANT ISOLATION FAILURE: Org B saw Org A number"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
