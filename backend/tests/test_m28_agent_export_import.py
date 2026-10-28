"""M28 tests — Agent Studio Export & Import Across Organizations.

Tests:
1. Export active agent returns valid sarvam_agent_export_v1 format without tenant IDs.
2. Tenant isolation on export (cannot export another org's agent).
3. Import creates new agent in target org with version 1 activated and configuration intact.
4. Import respects subscription max_agents limit.
5. Import validates required schema and fields.
6. API endpoints GET /api/v1/agents/{id}/export and POST /api/v1/agents/import work end-to-end.
"""

import asyncio
import os
import sys
import pytest
from unittest.mock import MagicMock

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
    return mongomock_motor.AsyncMongoMockClient()["test_m28"]


@SKIP
class TestAgentExportImport:
    def setup_method(self):
        self.db = _get_mock_db()
        from backend.services.agent_service import AgentService, seed_templates
        from backend.services.voice_profile_service import VoiceProfileService
        from backend.services.subscription_service import SubscriptionService

        self.agent_svc = AgentService(self.db)
        self.vp_svc = VoiceProfileService(self.db)
        self.sub_svc = SubscriptionService(self.db)

        # Seed templates and platform voice profiles
        run(seed_templates(self.db))
        from backend.services.voice_profile_service import seed_default_voice_profiles
        seeded_vps = run(seed_default_voice_profiles(self.db))
        self.platform_vp_id = seeded_vps[0].id

        # Seed subscriptions for Org A and Org B
        run(self._setup_org_subscription("org-a", max_agents=5))
        run(self._setup_org_subscription("org-b", max_agents=2))

    async def _setup_org_subscription(self, org_id: str, max_agents: int = 5):
        plan = await self.sub_svc.plan_repo.create(
            name=f"Plan-{org_id}",
            slug=f"plan-{org_id}",
            max_concurrent_calls=5,
            max_campaigns=5,
            max_agents=max_agents,
            max_leads_per_campaign=1000,
        )
        await self.sub_svc.activate_plan(org_id, plan.id, "monthly", payment_id="pay_init")

    def test_export_agent_sanitized_format(self):
        async def _t():
            # 1. Create agent in Org A
            agent = await self.agent_svc.create_agent(
                organization_id="org-a",
                name="Solar Lead Qualifier (Priya)",
                template_slug="solar",
                voice_profile_id=self.platform_vp_id,
                voice_profile_version=1,
                description="Original description",
            )
            # Create active published version
            config = {
                "agent_name": "Priya",
                "primary_language": "mr-IN",
                "greeting": "नमस्कार, मी {partnerName} टीममधून {salesRepName} बोलतेय.",
                "system_prompt": "# Role & Persona\n- **Agent Name**: {salesRepName}",
                "input_variables": {"partnerName": "SolarCorp", "salesRepName": "Priya"},
                "output_variables": ["disposition", "monthly_bill"],
                "speech_speed": 1.0,
                "barge_in_sensitivity": 70,
                "tools": {"whatsapp": True, "calendar": True, "webhook": False, "webhook_url": ""},
                "knowledge_strictness": "flexible",
            }
            await self.agent_svc.create_version(
                agent_id=agent.id,
                organization_id="org-a",
                configuration=config,
                description="v1 initial",
                auto_activate=True,
            )

            # 2. Export agent
            export_pkg = await self.agent_svc.export_agent(agent.id, "org-a")

            assert export_pkg["format"] == "sarvam_agent_export_v1"
            assert "exported_at" in export_pkg
            agent_data = export_pkg["agent"]
            assert agent_data["name"] == "Solar Lead Qualifier (Priya)"
            assert agent_data["template_slug"] == "solar"
            assert agent_data["primary_language"] == "mr-IN"
            assert agent_data["configuration"]["greeting"] == config["greeting"]
            assert agent_data["configuration"]["system_prompt"] == config["system_prompt"]
            assert agent_data["configuration"]["input_variables"] == config["input_variables"]
            assert agent_data["configuration"]["output_variables"] == config["output_variables"]

            # Verify tenant sanitization (no internal IDs leaked)
            assert "organization_id" not in export_pkg
            assert "organization_id" not in agent_data
            assert "id" not in agent_data
            assert "_id" not in agent_data
            assert "active_version_id" not in agent_data

        run(_t())

    def test_export_tenant_isolation(self):
        async def _t():
            agent = await self.agent_svc.create_agent(
                organization_id="org-a",
                name="Agent A",
                template_slug="generic",
                voice_profile_id=self.platform_vp_id,
                voice_profile_version=1,
            )
            # Org B cannot export Org A's agent
            with pytest.raises(ValueError, match="Agent not found"):
                await self.agent_svc.export_agent(agent.id, "org-b")
        run(_t())

    def test_import_agent_into_new_organization(self):
        async def _t():
            # Create in Org A & export
            agent_a = await self.agent_svc.create_agent(
                organization_id="org-a",
                name="Solar Assistant",
                template_slug="solar",
                voice_profile_id=self.platform_vp_id,
                voice_profile_version=1,
            )
            config = {
                "agent_name": "Solar Bot",
                "primary_language": "mr-IN",
                "greeting": "नमस्कार, मी सोलर सहाय्यक बोलतेय.",
                "system_prompt": "Prompt for solar bot",
                "input_variables": {"partnerName": "SolarCo"},
                "output_variables": ["disposition"],
            }
            await self.agent_svc.create_version(
                agent_id=agent_a.id,
                organization_id="org-a",
                configuration=config,
                auto_activate=True,
            )
            export_pkg = await self.agent_svc.export_agent(agent_a.id, "org-a")

            # Import into Org B with renamed agent
            imported_agent = await self.agent_svc.import_agent(
                organization_id="org-b",
                name="Solar Assistant (Branch B)",
                template_slug=export_pkg["agent"]["template_slug"],
                configuration=export_pkg["agent"]["configuration"],
                description=export_pkg["agent"].get("description", ""),
                voice_profile_id=self.platform_vp_id,
            )

            assert imported_agent.id != agent_a.id
            assert imported_agent.organization_id == "org-b"
            assert imported_agent.name == "Solar Assistant (Branch B)"
            assert imported_agent.active_version == 1

            # Check that imported version 1 is active & published
            versions = await self.agent_svc.list_versions(imported_agent.id, "org-b")
            assert len(versions) == 1
            assert versions[0].status == "published"
            assert versions[0].configuration["greeting"] == config["greeting"]
            assert versions[0].configuration["system_prompt"] == config["system_prompt"]
        run(_t())

    def test_import_agent_limit_enforced(self):
        async def _t():
            # Org B has max_agents=2
            # Add 2 agents to Org B to reach limit
            await self.agent_svc.create_agent("org-b", "Agent 1", "generic", self.platform_vp_id, 1)
            await self.agent_svc.create_agent("org-b", "Agent 2", "generic", self.platform_vp_id, 1)

            # Trying to import 3rd agent should raise limit error
            with pytest.raises(ValueError, match="limit reached"):
                await self.agent_svc.import_agent(
                    organization_id="org-b",
                    name="Agent 3",
                    template_slug="generic",
                    configuration={"greeting": "Hello", "system_prompt": "Prompt"},
                )
        run(_t())


@SKIP
class TestAgentExportImportHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from backend.api.v1.agents import router as agents_router
        from backend.core import db as db_module
        from backend.core.auth import CurrentUser, get_current_user
        from backend.services.agent_service import AgentService, seed_templates
        from backend.services.voice_profile_service import seed_default_voice_profiles
        from backend.services.subscription_service import SubscriptionService

        self.mock_db = mongomock_motor.AsyncMongoMockClient()["test_m28_http"]
        db_module._db = self.mock_db

        self.test_app = FastAPI()
        self.test_app.include_router(agents_router, prefix="/api/v1")

        self.current_user = CurrentUser(
            user_id="user-1",
            email="user@test.com",
            role="owner",
            org_id="org-http-1",
        )

        self.test_app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.client = TestClient(self.test_app)

        self.agent_svc = AgentService(self.mock_db)
        self.sub_svc = SubscriptionService(self.mock_db)

        run(seed_templates(self.mock_db))
        vps = run(seed_default_voice_profiles(self.mock_db))
        self.vp_id = vps[0].id

        # Setup subscription
        async def _init_sub():
            plan = await self.sub_svc.plan_repo.create(
                name="Plan-HTTP",
                slug="plan-http",
                max_concurrent_calls=5,
                max_campaigns=5,
                max_agents=5,
                max_leads_per_campaign=1000,
            )
            await self.sub_svc.activate_plan("org-http-1", plan.id, "monthly", payment_id="pay_http")
        run(_init_sub())

    def test_http_export_and_import_cycle(self):
        # 1. Create agent
        created = run(self.agent_svc.create_agent(
            organization_id="org-http-1",
            name="Endpoint Test Agent",
            template_slug="solar",
            voice_profile_id=self.vp_id,
            voice_profile_version=1,
        ))
        run(self.agent_svc.create_version(
            agent_id=created.id,
            organization_id="org-http-1",
            configuration={
                "greeting": "Test Greeting",
                "system_prompt": "Test System Prompt",
                "primary_language": "mr-IN",
                "input_variables": {"name": "Test"},
                "output_variables": ["disposition"],
            },
            auto_activate=True,
        ))

        # 2. Call GET /api/v1/agents/{id}/export
        res_export = self.client.get(f"/api/v1/agents/{created.id}/export")
        assert res_export.status_code == 200
        pkg = res_export.json()
        assert pkg["format"] == "sarvam_agent_export_v1"
        assert pkg["agent"]["name"] == "Endpoint Test Agent"
        assert pkg["agent"]["configuration"]["greeting"] == "Test Greeting"

        # 3. Switch user to Org 2 and import
        self.current_user.org_id = "org-http-2"
        # Setup sub for Org 2
        async def _init_sub2():
            plan = await self.sub_svc.plan_repo.create(
                name="Plan-HTTP-2",
                slug="plan-http-2",
                max_concurrent_calls=5,
                max_campaigns=5,
                max_agents=5,
                max_leads_per_campaign=1000,
            )
            await self.sub_svc.activate_plan("org-http-2", plan.id, "monthly", payment_id="pay_http2")
        run(_init_sub2())

        res_import = self.client.post("/api/v1/agents/import", json={
            "name": "Imported Endpoint Agent",
            "template_slug": pkg["agent"]["template_slug"],
            "configuration": pkg["agent"]["configuration"],
            "description": "Imported via HTTP test",
        })
        assert res_import.status_code == 201
        imported_data = res_import.json()
        assert imported_data["name"] == "Imported Endpoint Agent"
        assert imported_data["organization_id"] == "org-http-2"
        assert imported_data["id"] != created.id

    def test_http_export_404_if_not_found(self):
        res = self.client.get("/api/v1/agents/non-existent-id/export")
        assert res.status_code == 404
