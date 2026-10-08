"""M13 tests — Campaign Engine.

Tests:
1.  Campaign model — status validation, FSM properties (can_pause, can_resume, etc.)
2.  Status transition rules — invalid transitions raise ValueError
3.  CampaignRepository — CRUD, org-scoped queries, tenant isolation
4.  CampaignService.start → running
5.  start from invalid status raises
6.  CampaignService.pause → paused; pause_low_credits → paused_low_credits
7.  pause from terminal status raises
8.  CampaignService.resume → running
9.  resume from non-paused raises
10. CampaignService.cancel — any non-terminal status
11. cancel from terminal status raises
12. Concurrency gate: acquire_call_slot / release_call_slot
13. Never exceed max_concurrent_calls (concurrent acquire attempts)
14. Release restores available slot
15. Tenant isolation: Org A cannot access Org B campaigns
16. HTTP: create, list, get, start, pause, resume, cancel, stats
17. HTTP: tenant isolation 404 for cross-org
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


def _make_redis():
    """In-memory Redis mock."""
    store: dict = {}

    async def get(key): return store.get(key)
    async def set(key, val, ex=None): store[key] = str(val)
    async def delete(*keys):
        for k in keys: store.pop(k, None)
    async def incr(key):
        store[key] = str(int(store.get(key, 0)) + 1)
        return int(store[key])
    async def decr(key):
        store[key] = str(max(0, int(store.get(key, 0)) - 1))
        return int(store[key])
    async def expire(key, ttl): pass

    r = MagicMock()
    r.get = AsyncMock(side_effect=get)
    r.set = AsyncMock(side_effect=set)
    r.delete = AsyncMock(side_effect=delete)
    r.incr = AsyncMock(side_effect=incr)
    r.decr = AsyncMock(side_effect=decr)
    r.expire = AsyncMock(side_effect=expire)
    r._store = store
    return r


_CAMPAIGN_DEFAULTS = dict(
    name="Test Campaign",
    agent_id="agent-1",
    agent_version=1,
    voice_profile_id="voice-1",
    voice_profile_version=1,
    calling_number_id="pn-1",
    calling_number="+911800123001",
    max_concurrent_calls=3,
)


# ---------------------------------------------------------------------------
# Test: Campaign model FSM properties
# ---------------------------------------------------------------------------
class TestCampaignModel:
    def _make(self, status="draft"):
        from backend.models.campaign import Campaign
        from backend.models.base import new_id
        return Campaign(
            _id=new_id(), organization_id="org-1",
            **{**_CAMPAIGN_DEFAULTS, "status": status}
        )

    def test_valid_statuses(self):
        from backend.models.campaign import CAMPAIGN_STATUSES
        from backend.models.campaign import Campaign
        from backend.models.base import new_id
        for s in CAMPAIGN_STATUSES:
            c = Campaign(_id=new_id(), organization_id="o", **{**_CAMPAIGN_DEFAULTS, "status": s})
            assert c.status == s

    def test_invalid_status_raises(self):
        from backend.models.campaign import Campaign
        from backend.models.base import new_id
        with pytest.raises(Exception):
            Campaign(_id=new_id(), organization_id="o",
                     **{**_CAMPAIGN_DEFAULTS, "status": "invalid_xyz"})

    def test_can_pause_running(self):
        c = self._make("running")
        assert c.can_pause is True

    def test_cannot_pause_completed(self):
        c = self._make("completed")
        assert c.can_pause is False

    def test_cannot_pause_cancelled(self):
        c = self._make("cancelled")
        assert c.can_pause is False

    def test_can_resume_paused(self):
        assert self._make("paused").can_resume is True
        assert self._make("paused_low_credits").can_resume is True

    def test_cannot_resume_running(self):
        assert self._make("running").can_resume is False

    def test_is_terminal(self):
        assert self._make("completed").is_terminal is True
        assert self._make("cancelled").is_terminal is True
        assert self._make("failed").is_terminal is True
        assert self._make("running").is_terminal is False

    def test_can_cancel_any_non_terminal(self):
        for s in ["draft", "scheduled", "running", "paused", "paused_low_credits"]:
            assert self._make(s).can_cancel is True

    def test_cannot_cancel_terminal(self):
        for s in ["completed", "cancelled", "failed"]:
            assert self._make(s).can_cancel is False

    def test_concurrency_minimum_1(self):
        from backend.models.campaign import Campaign
        from backend.models.base import new_id
        with pytest.raises(Exception):
            Campaign(_id=new_id(), organization_id="o",
                     **{**_CAMPAIGN_DEFAULTS, "max_concurrent_calls": 0})


# ---------------------------------------------------------------------------
# Test: Repository — tenant isolation
# ---------------------------------------------------------------------------
@SKIP
class TestCampaignRepository:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_create_and_find(self):
        from backend.repositories.campaign_repo import CampaignRepository
        repo = CampaignRepository(self.db)
        async def _t():
            c = await repo.create(organization_id="org-1", **_CAMPAIGN_DEFAULTS)
            assert c.id is not None
            assert c.status == "draft"
            found = await repo.find_by_id(c.id)
            assert found.name == "Test Campaign"
        run(_t())

    def test_get_for_org_tenant_isolation(self):
        from backend.repositories.campaign_repo import CampaignRepository
        repo = CampaignRepository(self.db)
        async def _t():
            c = await repo.create(organization_id="org-A", **_CAMPAIGN_DEFAULTS)
            # Same org: OK
            assert await repo.get_for_org(c.id, "org-A") is not None
            # Different org: None
            assert await repo.get_for_org(c.id, "org-B") is None
        run(_t())

    def test_list_for_org_scoped(self):
        from backend.repositories.campaign_repo import CampaignRepository
        repo = CampaignRepository(self.db)
        async def _t():
            await repo.create(organization_id="org-X", **{**_CAMPAIGN_DEFAULTS, "name": "CX1"})
            await repo.create(organization_id="org-X", **{**_CAMPAIGN_DEFAULTS, "name": "CX2"})
            await repo.create(organization_id="org-Y", **{**_CAMPAIGN_DEFAULTS, "name": "CY1"})
            cx = await repo.list_for_org("org-X")
            cy = await repo.list_for_org("org-Y")
            assert len(cx) == 2
            assert len(cy) == 1
            # org-X cannot see org-Y campaign
            ids_x = {c.id for c in cx}
            assert all(c.organization_id == "org-X" for c in cx)
        run(_t())

    def test_transition_status(self):
        from backend.repositories.campaign_repo import CampaignRepository
        repo = CampaignRepository(self.db)
        async def _t():
            c = await repo.create(organization_id="org-1", **_CAMPAIGN_DEFAULTS)
            ok = await repo.transition_status(c.id, "org-1", "running")
            assert ok
            updated = await repo.find_by_id(c.id)
            assert updated.status == "running"
        run(_t())

    def test_transition_status_wrong_org_fails(self):
        from backend.repositories.campaign_repo import CampaignRepository
        repo = CampaignRepository(self.db)
        async def _t():
            c = await repo.create(organization_id="org-owner", **_CAMPAIGN_DEFAULTS)
            ok = await repo.transition_status(c.id, "org-other", "running")
            assert not ok  # tenant isolation
            unchanged = await repo.find_by_id(c.id)
            assert unchanged.status == "draft"
        run(_t())


# ---------------------------------------------------------------------------
# Test: CampaignService state machine
# ---------------------------------------------------------------------------
@SKIP
class TestCampaignStateMachine:
    def setup_method(self):
        self.db = _get_mock_db()
        self.redis = _make_redis()

    def _svc(self):
        from backend.services.campaign_service import CampaignService
        return CampaignService(self.db, redis=self.redis)

    async def _create(self, org="org-1", **kwargs):
        svc = self._svc()
        return await svc.create_campaign(
            organization_id=org, **{**_CAMPAIGN_DEFAULTS, **kwargs}
        )

    def test_start_draft_campaign(self):
        async def _t():
            svc = self._svc()
            c = await self._create()
            started = await svc.start_campaign(c.id, "org-1")
            assert started.status == "running"
            assert started.started_at is not None
        run(_t())

    def test_start_invalid_status_raises(self):
        async def _t():
            svc = self._svc()
            c = await self._create()
            await svc.start_campaign(c.id, "org-1")  # running
            with pytest.raises(ValueError, match="Cannot start"):
                await svc.start_campaign(c.id, "org-1")  # already running
        run(_t())

    def test_pause_running_campaign(self):
        async def _t():
            svc = self._svc()
            c = await self._create()
            await svc.start_campaign(c.id, "org-1")
            paused = await svc.pause_campaign(c.id, "org-1")
            assert paused.status == "paused"
        run(_t())

    def test_pause_low_credits(self):
        async def _t():
            svc = self._svc()
            c = await self._create()
            await svc.start_campaign(c.id, "org-1")
            paused = await svc.pause_campaign(c.id, "org-1", reason="low_credits")
            assert paused.status == "paused_low_credits"
        run(_t())

    def test_pause_terminal_raises(self):
        async def _t():
            svc = self._svc()
            c = await self._create()
            await svc.cancel_campaign(c.id, "org-1")
            with pytest.raises(ValueError, match="Cannot pause"):
                await svc.pause_campaign(c.id, "org-1")
        run(_t())

    def test_resume_paused_campaign(self):
        async def _t():
            svc = self._svc()
            c = await self._create()
            await svc.start_campaign(c.id, "org-1")
            await svc.pause_campaign(c.id, "org-1")
            resumed = await svc.resume_campaign(c.id, "org-1")
            assert resumed.status == "running"
        run(_t())

    def test_resume_paused_low_credits(self):
        async def _t():
            svc = self._svc()
            c = await self._create()
            await svc.start_campaign(c.id, "org-1")
            await svc.pause_campaign(c.id, "org-1", reason="low_credits")
            resumed = await svc.resume_campaign(c.id, "org-1")
            assert resumed.status == "running"
        run(_t())

    def test_resume_running_raises(self):
        async def _t():
            svc = self._svc()
            c = await self._create()
            await svc.start_campaign(c.id, "org-1")
            with pytest.raises(ValueError, match="Cannot resume"):
                await svc.resume_campaign(c.id, "org-1")
        run(_t())

    def test_cancel_draft(self):
        async def _t():
            svc = self._svc()
            c = await self._create()
            cancelled = await svc.cancel_campaign(c.id, "org-1")
            assert cancelled.status == "cancelled"
        run(_t())

    def test_cancel_running(self):
        async def _t():
            svc = self._svc()
            c = await self._create()
            await svc.start_campaign(c.id, "org-1")
            cancelled = await svc.cancel_campaign(c.id, "org-1")
            assert cancelled.status == "cancelled"
        run(_t())

    def test_cancel_completed_raises(self):
        async def _t():
            svc = self._svc()
            c = await self._create()
            await svc.start_campaign(c.id, "org-1")
            await svc.complete_campaign(c.id, "org-1")
            with pytest.raises(ValueError, match="terminal"):
                await svc.cancel_campaign(c.id, "org-1")
        run(_t())

    def test_full_lifecycle(self):
        """draft → running → paused → running → completed"""
        async def _t():
            svc = self._svc()
            c = await self._create()
            assert c.status == "draft"
            c = await svc.start_campaign(c.id, "org-1")
            assert c.status == "running"
            c = await svc.pause_campaign(c.id, "org-1")
            assert c.status == "paused"
            c = await svc.resume_campaign(c.id, "org-1")
            assert c.status == "running"
            c = await svc.complete_campaign(c.id, "org-1")
            assert c.status == "completed"
        run(_t())

    def test_tenant_isolation_start(self):
        """Org B cannot start Org A's campaign."""
        async def _t():
            svc = self._svc()
            c = await self._create(org="org-A")
            with pytest.raises(ValueError, match="not found"):
                await svc.start_campaign(c.id, "org-B")
        run(_t())


# ---------------------------------------------------------------------------
# Test: Concurrency gate
# ---------------------------------------------------------------------------
@SKIP
class TestConcurrencyGate:
    def setup_method(self):
        self.db = _get_mock_db()
        self.redis = _make_redis()

    def _svc(self):
        from backend.services.campaign_service import CampaignService
        return CampaignService(self.db, redis=self.redis)

    def test_acquire_slot_within_limit(self):
        async def _t():
            svc = self._svc()
            c = await svc.create_campaign(
                organization_id="org-1",
                **{**_CAMPAIGN_DEFAULTS, "max_concurrent_calls": 3}
            )
            await svc.start_campaign(c.id, "org-1")
            assert await svc.acquire_call_slot(c.id) is True
            assert await svc.acquire_call_slot(c.id) is True
            assert await svc.acquire_call_slot(c.id) is True
            assert await svc.get_active_call_count(c.id) == 3
        run(_t())

    def test_acquire_slot_beyond_limit_rejected(self):
        """Never exceed max_concurrent_calls."""
        async def _t():
            svc = self._svc()
            c = await svc.create_campaign(
                organization_id="org-1",
                **{**_CAMPAIGN_DEFAULTS, "max_concurrent_calls": 2}
            )
            await svc.start_campaign(c.id, "org-1")
            ok1 = await svc.acquire_call_slot(c.id)
            ok2 = await svc.acquire_call_slot(c.id)
            ok3 = await svc.acquire_call_slot(c.id)  # exceeds limit
            assert ok1 is True
            assert ok2 is True
            assert ok3 is False  # rejected
            # Active count must not exceed 2
            assert await svc.get_active_call_count(c.id) == 2
        run(_t())

    def test_release_restores_slot(self):
        async def _t():
            svc = self._svc()
            c = await svc.create_campaign(
                organization_id="org-1",
                **{**_CAMPAIGN_DEFAULTS, "max_concurrent_calls": 1}
            )
            await svc.start_campaign(c.id, "org-1")
            assert await svc.acquire_call_slot(c.id) is True   # fills the 1 slot
            assert await svc.acquire_call_slot(c.id) is False  # no slot
            await svc.release_call_slot(c.id)                  # release
            assert await svc.acquire_call_slot(c.id) is True   # slot restored
        run(_t())

    def test_10_concurrent_acquires_max_5(self):
        """10 concurrent acquire attempts with max=5: exactly 5 succeed."""
        async def _t():
            svc = self._svc()
            c = await svc.create_campaign(
                organization_id="org-conc",
                **{**_CAMPAIGN_DEFAULTS, "max_concurrent_calls": 5}
            )
            await svc.start_campaign(c.id, "org-conc")
            results = await asyncio.gather(
                *[svc.acquire_call_slot(c.id) for _ in range(10)]
            )
            successes = sum(1 for r in results if r is True)
            failures = sum(1 for r in results if r is False)
            assert successes == 5, f"Expected 5 successes, got {successes}"
            assert failures == 5, f"Expected 5 failures, got {failures}"
            assert await svc.get_active_call_count(c.id) == 5
        run(_t())

    def test_can_start_call_check(self):
        async def _t():
            svc = self._svc()
            c = await svc.create_campaign(
                organization_id="org-check",
                **{**_CAMPAIGN_DEFAULTS, "max_concurrent_calls": 2}
            )
            await svc.start_campaign(c.id, "org-check")
            check = await svc.can_start_call(c.id, "org-check")
            assert check["allowed"] is True
            # Fill slots
            await svc.acquire_call_slot(c.id)
            await svc.acquire_call_slot(c.id)
            check2 = await svc.can_start_call(c.id, "org-check")
            assert check2["allowed"] is False
            assert "concurrency_limit" in check2["reason"]
        run(_t())

    def test_can_start_call_paused(self):
        async def _t():
            svc = self._svc()
            c = await svc.create_campaign(
                organization_id="org-paused",
                **{**_CAMPAIGN_DEFAULTS}
            )
            await svc.start_campaign(c.id, "org-paused")
            await svc.pause_campaign(c.id, "org-paused")
            check = await svc.can_start_call(c.id, "org-paused")
            assert check["allowed"] is False
            assert "not_running" in check["reason"]
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestCampaignHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.campaigns import router as camp_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(camp_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        self.mock_redis = _make_redis()
        redis_module._redis = self.mock_redis

        self.client = TestClient(self.test_app)

        # Two orgs
        r1 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Campaign Org",
            "org_email": "camp@org.com",
            "email": "user@camp.com",
            "password": "CampPass1!",
        })
        self.token_a = r1.json()["access_token"]
        self.org_id_a = r1.json()["organization_id"]

        r2 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Other Org",
            "org_email": "other3@org.com",
            "email": "user@other3.com",
            "password": "OtherPass1!",
        })
        self.token_b = r2.json()["access_token"]

    def _auth(self, t): return {"Authorization": f"Bearer {t}"}

    def _create_body(self, **kwargs):
        base = {
            "name": "Test Campaign",
            "agent_id": "agent-1",
            "agent_version": 1,
            "voice_profile_id": "voice-1",
            "voice_profile_version": 1,
            "calling_number_id": "pn-1",
            "calling_number": "+911800123001",
            "max_concurrent_calls": 3,
        }
        return {**base, **kwargs}

    def test_create_campaign(self):
        resp = self.client.post("/api/v1/campaigns",
                                json=self._create_body(),
                                headers=self._auth(self.token_a))
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["status"] == "draft"
        assert data["organization_id"] == self.org_id_a

    def test_list_campaigns(self):
        self.client.post("/api/v1/campaigns", json=self._create_body(),
                         headers=self._auth(self.token_a))
        resp = self.client.get("/api/v1/campaigns",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_campaign(self):
        r = self.client.post("/api/v1/campaigns", json=self._create_body(),
                             headers=self._auth(self.token_a))
        cid = r.json()["id"]
        resp = self.client.get(f"/api/v1/campaigns/{cid}",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert resp.json()["id"] == cid

    def test_tenant_isolation_get(self):
        r = self.client.post("/api/v1/campaigns", json=self._create_body(),
                             headers=self._auth(self.token_a))
        cid = r.json()["id"]
        resp = self.client.get(f"/api/v1/campaigns/{cid}",
                               headers=self._auth(self.token_b))
        assert resp.status_code == 404

    def test_start_campaign(self):
        r = self.client.post("/api/v1/campaigns", json=self._create_body(),
                             headers=self._auth(self.token_a))
        cid = r.json()["id"]
        resp = self.client.post(f"/api/v1/campaigns/{cid}/start",
                                headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_pause_campaign(self):
        r = self.client.post("/api/v1/campaigns", json=self._create_body(),
                             headers=self._auth(self.token_a))
        cid = r.json()["id"]
        self.client.post(f"/api/v1/campaigns/{cid}/start",
                         headers=self._auth(self.token_a))
        resp = self.client.post(f"/api/v1/campaigns/{cid}/pause",
                                headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    def test_resume_campaign(self):
        r = self.client.post("/api/v1/campaigns", json=self._create_body(),
                             headers=self._auth(self.token_a))
        cid = r.json()["id"]
        self.client.post(f"/api/v1/campaigns/{cid}/start",
                         headers=self._auth(self.token_a))
        self.client.post(f"/api/v1/campaigns/{cid}/pause",
                         headers=self._auth(self.token_a))
        resp = self.client.post(f"/api/v1/campaigns/{cid}/resume",
                                headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_cancel_campaign(self):
        r = self.client.post("/api/v1/campaigns", json=self._create_body(),
                             headers=self._auth(self.token_a))
        cid = r.json()["id"]
        resp = self.client.post(f"/api/v1/campaigns/{cid}/cancel",
                                headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_cancel_terminal_returns_400(self):
        r = self.client.post("/api/v1/campaigns", json=self._create_body(),
                             headers=self._auth(self.token_a))
        cid = r.json()["id"]
        self.client.post(f"/api/v1/campaigns/{cid}/cancel",
                         headers=self._auth(self.token_a))
        resp = self.client.post(f"/api/v1/campaigns/{cid}/cancel",
                                headers=self._auth(self.token_a))
        assert resp.status_code == 400

    def test_campaign_stats(self):
        r = self.client.post("/api/v1/campaigns", json=self._create_body(),
                             headers=self._auth(self.token_a))
        cid = r.json()["id"]
        self.client.post(f"/api/v1/campaigns/{cid}/start",
                         headers=self._auth(self.token_a))
        resp = self.client.get(f"/api/v1/campaigns/{cid}/stats",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        stats = resp.json()
        assert "status" in stats
        assert "active_calls" in stats
        assert "max_concurrent_calls" in stats

    def test_tenant_isolation_org_b_start_org_a(self):
        r = self.client.post("/api/v1/campaigns", json=self._create_body(),
                             headers=self._auth(self.token_a))
        cid = r.json()["id"]
        resp = self.client.post(f"/api/v1/campaigns/{cid}/start",
                                headers=self._auth(self.token_b))
        assert resp.status_code == 400  # not found for org-B

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/v1/campaigns")
        assert resp.status_code == 401

    def test_list_filter_by_status(self):
        r = self.client.post("/api/v1/campaigns",
                             json=self._create_body(name="C1"),
                             headers=self._auth(self.token_a))
        cid = r.json()["id"]
        self.client.post(f"/api/v1/campaigns/{cid}/start",
                         headers=self._auth(self.token_a))
        self.client.post("/api/v1/campaigns",
                         json=self._create_body(name="C2"),
                         headers=self._auth(self.token_a))

        running = self.client.get("/api/v1/campaigns?status=running",
                                  headers=self._auth(self.token_a)).json()
        draft = self.client.get("/api/v1/campaigns?status=draft",
                                headers=self._auth(self.token_a)).json()
        assert all(c["status"] == "running" for c in running)
        assert all(c["status"] == "draft" for c in draft)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
