"""End-to-End integration test for Agent Multi-KB association and Prompt Grounding."""

import asyncio
import sys
import os
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


@SKIP
class TestAgentKBIntegration:
    def setup_method(self):
        import mongomock_motor
        from backend.services.knowledge_service import KnowledgeService
        self.client = mongomock_motor.AsyncMongoMockClient()
        self.db = self.client["test_saas"]
        self.kb_svc = KnowledgeService(self.db)

    def test_multi_kb_association_and_prompt_grounding(self):
        async def _t():
            org_id = "org-enterprise-1"
            agent_id = "agent-priya-solar"

            # 1. Create two separate KBs
            kb_pricing = await self.kb_svc.create_kb(
                organization_id=org_id,
                name="Solar Pricing & Packages",
                description="Commercial and residential solar pricing breakdown",
            )
            kb_objections = await self.kb_svc.create_kb(
                organization_id=org_id,
                name="Rooftop Objections Handbook",
                description="Handling customer doubts regarding cost and shadow",
            )

            # 2. Add documents to each KB
            await self.kb_svc.add_document(
                organization_id=org_id,
                knowledge_base_id=kb_pricing.id,
                title="2 kW Home Solar Package",
                content="Standard 2 kW system costs ₹1,20,000. Subsidy is ₹78,000. Net customer cost is ₹42,000.",
                document_type="product_info",
            )
            await self.kb_svc.add_document(
                organization_id=org_id,
                knowledge_base_id=kb_objections.id,
                title="Monsoon & Cloudy Weather",
                content="Solar panels still generate 25-35% power during heavy rain and overcast days in Maharashtra.",
                document_type="objection",
            )

            # 3. Associate both KBs with the agent
            await self.kb_svc.associate_agent(org_id, kb_pricing.id, agent_id, priority=0)
            await self.kb_svc.associate_agent(org_id, kb_objections.id, agent_id, priority=1)

            # Check associated KBs
            associated_kbs = await self.kb_svc.get_kbs_for_agent(agent_id, org_id)
            assert len(associated_kbs) == 2
            kb_names = [k.name for k in associated_kbs]
            assert "Solar Pricing & Packages" in kb_names
            assert "Rooftop Objections Handbook" in kb_names

            # 4. Verify context in Flexible Mode
            flex_context = await self.kb_svc.get_context_for_agent(
                agent_id=agent_id,
                organization_id=org_id,
                mode="flexible",
            )
            assert "# Reference Knowledge Base" in flex_context
            assert "2 kW Home Solar Package" in flex_context
            assert "Monsoon & Cloudy Weather" in flex_context
            assert "primary source of truth" in flex_context
            assert "Strict Mode" not in flex_context

            # 5. Verify context in Strict Mode
            strict_context = await self.kb_svc.get_context_for_agent(
                agent_id=agent_id,
                organization_id=org_id,
                mode="strict",
            )
            assert "# Reference Knowledge Base (Strict Mode)" in strict_context
            assert "CRITICAL INSTRUCTION" in strict_context
            assert "2 kW Home Solar Package" in strict_context
            assert "Monsoon & Cloudy Weather" in strict_context
            assert "Do not fabricate facts." in strict_context

            # 6. Disassociate one KB (pricing)
            await self.kb_svc.disassociate_agent(org_id, kb_pricing.id, agent_id)
            remaining_kbs = await self.kb_svc.get_kbs_for_agent(agent_id, org_id)
            assert len(remaining_kbs) == 1
            assert remaining_kbs[0].id == kb_objections.id

            # 7. Verify updated context only contains the remaining KB
            updated_context = await self.kb_svc.get_context_for_agent(
                agent_id=agent_id,
                organization_id=org_id,
                mode="strict",
            )
            assert "Monsoon & Cloudy Weather" in updated_context
            assert "2 kW Home Solar Package" not in updated_context

        run(_t())
