"""M11 tests — Agent Builder.

Tests:
1. BusinessTemplate — 7 templates seeded, idempotent, all generic (no solar code)
2. Agent creation — valid template required
3. Agent creation — invalid template raises
4. Agent tenant isolation — Org A cannot see Org B agents
5. AgentVersion — create draft, update draft, publish (immutable after)
6. Published version is immutable (update raises ValueError)
7. Auto-activate on version create
8. Version listing scoped to org
9. Template slugs cover all required business types
10. HTTP: create agent, list, get, delete, versions, publish, tenant isolation
11. Template configuration is generic — no solar-specific code in AgentService
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
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test"]


async def _seed(db):
    from backend.services.agent_service import seed_templates
    return await seed_templates(db)


# ---------------------------------------------------------------------------
# Test: Template seeding
# ---------------------------------------------------------------------------
@SKIP
class TestBusinessTemplates:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_seed_all_7_templates(self):
        async def _t():
            from backend.services.agent_service import seed_templates, DEFAULT_TEMPLATES
            templates = await seed_templates(self.db)
            # All 7 default templates seeded
            assert len(templates) == len(DEFAULT_TEMPLATES)
            slugs = {t.slug for t in templates}
            required = {"generic", "solar", "real-estate", "insurance",
                        "education", "home-services", "automotive"}
            assert required == slugs
        run(_t())

    def test_seed_is_idempotent(self):
        async def _t():
            from backend.services.agent_service import seed_templates
            first = await seed_templates(self.db)
            second = await seed_templates(self.db)
            assert len(first) == 7
            assert len(second) == 0   # nothing new on second call
        run(_t())

    def test_templates_are_configuration_driven(self):
        """Solar template is configuration, not code. No if/else in service."""
        import inspect
        from backend.services import agent_service
        source = inspect.getsource(agent_service.AgentService)
        # No business-specific branching in core service code
        assert "solar" not in source.lower()
        assert "real-estate" not in source.lower()
        assert "insurance" not in source.lower()

    def test_solar_template_has_slot_definitions(self):
        async def _t():
            from backend.services.agent_service import seed_templates
            from backend.repositories.agent_repo import BusinessTemplateRepository
            await seed_templates(self.db)
            repo = BusinessTemplateRepository(self.db)
            solar = await repo.find_by_slug("solar")
            assert solar is not None
            assert len(solar.slot_definitions) > 0
            slot_keys = {s["key"] for s in solar.slot_definitions}
            assert "monthly_bill" in slot_keys or "roof_type" in slot_keys
        run(_t())

    def test_all_templates_active(self):
        async def _t():
            from backend.services.agent_service import seed_templates, AgentService
            await seed_templates(self.db)
            svc = AgentService(self.db)
            templates = await svc.list_templates()
            assert len(templates) == 7
            assert all(t.is_active for t in templates)
        run(_t())


# ---------------------------------------------------------------------------
# Test: Agent creation
# ---------------------------------------------------------------------------
@SKIP
class TestAgentCreation:
    def setup_method(self):
        self.db = _get_mock_db()

    def _svc(self):
        from backend.services.agent_service import AgentService
        return AgentService(self.db)

    def test_create_agent_valid_template(self):
        async def _t():
            await _seed(self.db)
            svc = self._svc()
            agent = await svc.create_agent(
                organization_id="org-1",
                name="Solar Qualifier",
                template_slug="solar",
                voice_profile_id="voice-1",
                voice_profile_version=1,
            )
            assert agent.id is not None
            assert agent.organization_id == "org-1"
            assert agent.template_slug == "solar"
            assert agent.is_active is True
        run(_t())

    def test_create_agent_invalid_template_raises(self):
        async def _t():
            await _seed(self.db)
            svc = self._svc()
            with pytest.raises(ValueError, match="template"):
                await svc.create_agent(
                    organization_id="org-1",
                    name="Bad Agent",
                    template_slug="nonexistent-template",
                    voice_profile_id="voice-1",
                    voice_profile_version=1,
                )
        run(_t())

    def test_list_agents_for_org(self):
        async def _t():
            await _seed(self.db)
            svc = self._svc()
            await svc.create_agent("org-2", "Agent A", "generic", "v1", 1)
            await svc.create_agent("org-2", "Agent B", "solar", "v1", 1)
            agents = await svc.list_agents("org-2")
            assert len(agents) == 2
        run(_t())

    def test_tenant_isolation_agents(self):
        """Org A cannot see Org B agents."""
        async def _t():
            await _seed(self.db)
            svc = self._svc()
            await svc.create_agent("org-iso-A", "Agent A", "generic", "v1", 1)
            await svc.create_agent("org-iso-B", "Agent B", "generic", "v1", 1)

            agents_a = await svc.list_agents("org-iso-A")
            agents_b = await svc.list_agents("org-iso-B")

            ids_a = {a.id for a in agents_a}
            ids_b = {a.id for a in agents_b}

            assert not ids_a & ids_b, "TENANT ISOLATION FAILURE: org A saw org B agent"
            assert len(agents_a) == 1
            assert len(agents_b) == 1
        run(_t())

    def test_get_agent_wrong_org_returns_none(self):
        async def _t():
            await _seed(self.db)
            svc = self._svc()
            agent = await svc.create_agent("org-owner", "Agent", "generic", "v1", 1)
            result = await svc.get_agent(agent.id, "org-other")
            assert result is None
        run(_t())

    def test_delete_agent(self):
        async def _t():
            await _seed(self.db)
            svc = self._svc()
            agent = await svc.create_agent("org-del", "To Delete", "generic", "v1", 1)
            await svc.delete_agent(agent.id, "org-del")
            result = await svc.get_agent(agent.id, "org-del")
            assert result is None  # deactivated
        run(_t())


# ---------------------------------------------------------------------------
# Test: Agent versions
# ---------------------------------------------------------------------------
@SKIP
class TestAgentVersions:
    def setup_method(self):
        self.db = _get_mock_db()

    def _svc(self):
        from backend.services.agent_service import AgentService
        return AgentService(self.db)

    async def _make_agent(self):
        await _seed(self.db)
        svc = self._svc()
        return await svc.create_agent("org-ver", "V Agent", "generic", "v1", 1), svc

    def test_create_draft_version(self):
        async def _t():
            agent, svc = await self._make_agent()
            version = await svc.create_version(
                agent.id, "org-ver",
                configuration={"goal": "qualify leads"},
            )
            assert version.version == 1
            assert version.status == "draft"
            assert version.configuration["goal"] == "qualify leads"
        run(_t())

    def test_update_draft_version(self):
        async def _t():
            agent, svc = await self._make_agent()
            version = await svc.create_version(agent.id, "org-ver",
                                               configuration={"goal": "old"})
            updated = await svc.update_draft_version(version.id, "org-ver",
                                                     configuration={"goal": "new"})
            assert updated.configuration["goal"] == "new"
            assert updated.status == "draft"
        run(_t())

    def test_published_version_is_immutable(self):
        """Once published, a version cannot be modified."""
        async def _t():
            agent, svc = await self._make_agent()
            version = await svc.create_version(agent.id, "org-ver",
                                               configuration={"goal": "original"})
            await svc.publish_version(agent.id, version.id, "org-ver")
            with pytest.raises(ValueError, match="[Ii]mmutable|[Pp]ublished"):
                await svc.update_draft_version(version.id, "org-ver",
                                               configuration={"goal": "hacked"})
        run(_t())

    def test_publish_activates_agent(self):
        async def _t():
            agent, svc = await self._make_agent()
            version = await svc.create_version(agent.id, "org-ver",
                                               configuration={"goal": "qualify"})
            published = await svc.publish_version(agent.id, version.id, "org-ver")
            assert published.status == "published"
            updated_agent = await svc.get_agent(agent.id, "org-ver")
            assert updated_agent.active_version == 1
            assert updated_agent.active_version_id == version.id
        run(_t())

    def test_auto_activate_on_create(self):
        async def _t():
            agent, svc = await self._make_agent()
            version = await svc.create_version(agent.id, "org-ver",
                                               configuration={"goal": "auto"},
                                               auto_activate=True)
            # Should be published and active
            updated_agent = await svc.get_agent(agent.id, "org-ver")
            assert updated_agent.active_version == version.version
        run(_t())

    def test_version_numbers_increment(self):
        async def _t():
            agent, svc = await self._make_agent()
            v1 = await svc.create_version(agent.id, "org-ver", configuration={})
            v2 = await svc.create_version(agent.id, "org-ver", configuration={})
            v3 = await svc.create_version(agent.id, "org-ver", configuration={})
            assert v1.version == 1
            assert v2.version == 2
            assert v3.version == 3
        run(_t())

    def test_list_versions_scoped_to_org(self):
        async def _t():
            agent, svc = await self._make_agent()
            await svc.create_version(agent.id, "org-ver", configuration={"v": 1})
            await svc.create_version(agent.id, "org-ver", configuration={"v": 2})
            versions = await svc.list_versions(agent.id, "org-ver")
            assert len(versions) == 2
            # Cross-org: should raise
            with pytest.raises(ValueError):
                await svc.list_versions(agent.id, "org-other")
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestAgentHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.agents import router as agents_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(agents_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        # Seed templates
        run(_seed(self.mock_db))

        # Signup
        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Agent Org",
            "org_email": "agent@org.com",
            "email": "user@agent.com",
            "password": "AgentPass1!",
        })
        self.user_token = r.json()["access_token"]
        self.org_id = r.json()["organization_id"]

        # Second org for isolation tests
        r2 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Other Org",
            "org_email": "other@org.com",
            "email": "user@other.com",
            "password": "OtherPass1!",
        })
        self.other_token = r2.json()["access_token"]

    def _auth(self, token): return {"Authorization": f"Bearer {token}"}

    def test_list_templates(self):
        resp = self.client.get("/api/v1/agents/templates",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        slugs = {t["slug"] for t in resp.json()}
        assert "generic" in slugs
        assert "solar" in slugs
        assert len(slugs) == 7

    def test_create_agent(self):
        resp = self.client.post("/api/v1/agents", json={
            "name": "My Solar Agent",
            "template_slug": "solar",
            "voice_profile_id": "voice-1",
            "voice_profile_version": 1,
        }, headers=self._auth(self.user_token))
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "My Solar Agent"
        assert data["template_slug"] == "solar"
        assert data["organization_id"] == self.org_id

    def test_create_agent_invalid_template(self):
        resp = self.client.post("/api/v1/agents", json={
            "name": "Bad Agent",
            "template_slug": "does-not-exist",
            "voice_profile_id": "voice-1",
            "voice_profile_version": 1,
        }, headers=self._auth(self.user_token))
        assert resp.status_code == 400

    def test_list_agents(self):
        self.client.post("/api/v1/agents", json={
            "name": "Agent A", "template_slug": "generic",
            "voice_profile_id": "v1", "voice_profile_version": 1,
        }, headers=self._auth(self.user_token))
        resp = self.client.get("/api/v1/agents",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_agent_by_id(self):
        r = self.client.post("/api/v1/agents", json={
            "name": "Get Me", "template_slug": "generic",
            "voice_profile_id": "v1", "voice_profile_version": 1,
        }, headers=self._auth(self.user_token))
        agent_id = r.json()["id"]
        resp = self.client.get(f"/api/v1/agents/{agent_id}",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        assert resp.json()["id"] == agent_id

    def test_tenant_isolation_get(self):
        r = self.client.post("/api/v1/agents", json={
            "name": "Private Agent", "template_slug": "generic",
            "voice_profile_id": "v1", "voice_profile_version": 1,
        }, headers=self._auth(self.user_token))
        agent_id = r.json()["id"]
        # Other org cannot access
        resp = self.client.get(f"/api/v1/agents/{agent_id}",
                               headers=self._auth(self.other_token))
        assert resp.status_code == 404

    def test_create_and_list_versions(self):
        r = self.client.post("/api/v1/agents", json={
            "name": "Version Agent", "template_slug": "generic",
            "voice_profile_id": "v1", "voice_profile_version": 1,
        }, headers=self._auth(self.user_token))
        agent_id = r.json()["id"]

        # Create version
        rv = self.client.post(f"/api/v1/agents/{agent_id}/versions", json={
            "configuration": {"goal": "qualify leads"},
        }, headers=self._auth(self.user_token))
        assert rv.status_code == 201
        assert rv.json()["status"] == "draft"
        assert rv.json()["version"] == 1

        # List versions
        resp = self.client.get(f"/api/v1/agents/{agent_id}/versions",
                               headers=self._auth(self.user_token))
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_publish_version(self):
        r = self.client.post("/api/v1/agents", json={
            "name": "Publish Agent", "template_slug": "generic",
            "voice_profile_id": "v1", "voice_profile_version": 1,
        }, headers=self._auth(self.user_token))
        agent_id = r.json()["id"]

        rv = self.client.post(f"/api/v1/agents/{agent_id}/versions",
                              json={"configuration": {"goal": "qualify"}},
                              headers=self._auth(self.user_token))
        version_id = rv.json()["id"]

        resp = self.client.post(f"/api/v1/agents/{agent_id}/versions/{version_id}/publish",
                                headers=self._auth(self.user_token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"

    def test_update_draft_version(self):
        r = self.client.post("/api/v1/agents", json={
            "name": "Draft Agent", "template_slug": "generic",
            "voice_profile_id": "v1", "voice_profile_version": 1,
        }, headers=self._auth(self.user_token))
        agent_id = r.json()["id"]

        rv = self.client.post(f"/api/v1/agents/{agent_id}/versions",
                              json={"configuration": {"goal": "old"}},
                              headers=self._auth(self.user_token))
        version_id = rv.json()["id"]

        resp = self.client.patch(f"/api/v1/agents/{agent_id}/versions/{version_id}",
                                 json={"configuration": {"goal": "new"}},
                                 headers=self._auth(self.user_token))
        assert resp.status_code == 200
        assert resp.json()["configuration"]["goal"] == "new"

    def test_cannot_update_published_version(self):
        r = self.client.post("/api/v1/agents", json={
            "name": "Immutable Agent", "template_slug": "generic",
            "voice_profile_id": "v1", "voice_profile_version": 1,
        }, headers=self._auth(self.user_token))
        agent_id = r.json()["id"]

        rv = self.client.post(f"/api/v1/agents/{agent_id}/versions",
                              json={"configuration": {"goal": "final"}},
                              headers=self._auth(self.user_token))
        version_id = rv.json()["id"]
        self.client.post(f"/api/v1/agents/{agent_id}/versions/{version_id}/publish",
                         headers=self._auth(self.user_token))

        # Attempt to update published version → should fail
        resp = self.client.patch(f"/api/v1/agents/{agent_id}/versions/{version_id}",
                                 json={"configuration": {"goal": "hacked"}},
                                 headers=self._auth(self.user_token))
        assert resp.status_code == 400

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/v1/agents")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
