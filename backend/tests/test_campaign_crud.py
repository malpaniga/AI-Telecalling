"""Unit and API tests for Campaign CRUD operations."""

import asyncio
import mongomock_motor
import pytest
from datetime import datetime, timezone

from backend.repositories.campaign_repo import CampaignRepository
from backend.services.campaign_service import CampaignService


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestCampaignCRUD:
    def setup_method(self):
        self.client = mongomock_motor.AsyncMongoMockClient()
        self.db = self.client["test_campaign_crud"]
        self.repo = CampaignRepository(self.db)
        self.svc = CampaignService(self.db)

    def test_campaign_create_read_update_delete(self):
        async def _test():
            # 1. Create
            campaign = await self.repo.create(
                organization_id="org_1",
                name="Test Outbound",
                agent_id="ag_1",
                agent_version=1,
                voice_profile_id="vp_1",
                voice_profile_version=1,
                calling_number_id="pn_1",
                calling_number="+918000000000",
                max_concurrent_calls=2,
                timezone="Asia/Kolkata",
                description="Original description",
            )
            assert campaign.id is not None
            assert campaign.name == "Test Outbound"
            assert campaign.status == "draft"

            # 2. Read
            fetched = await self.svc.get_campaign(campaign.id, "org_1")
            assert fetched is not None
            assert fetched.name == "Test Outbound"

            # Tenant isolation
            cross_org = await self.svc.get_campaign(campaign.id, "org_other")
            assert cross_org is None

            # 3. Update
            await self.repo.update_by_id(campaign.id, {
                "name": "Updated Outbound Title",
                "max_concurrent_calls": 5,
            })
            updated = await self.svc.get_campaign(campaign.id, "org_1")
            assert updated.name == "Updated Outbound Title"
            assert updated.max_concurrent_calls == 5

            # 4. Enroll lead and verify junction cleanup on delete
            await self.db.campaign_leads.insert_one({
                "campaign_id": campaign.id,
                "lead_id": "lead_1",
                "organization_id": "org_1",
                "phone": "+919876543210",
                "status": "new",
            })
            assert await self.db.campaign_leads.count_documents({"campaign_id": campaign.id}) == 1

            # 5. Delete
            deleted = await self.svc.delete_campaign(campaign.id, "org_1")
            assert deleted is True

            # Verify deleted from DB and junction records removed
            assert await self.svc.get_campaign(campaign.id, "org_1") is None
            assert await self.db.campaign_leads.count_documents({"campaign_id": campaign.id}) == 0

        run(_test())

    def test_delete_running_campaign_prevented(self):
        async def _test():
            campaign = await self.repo.create(
                organization_id="org_1",
                name="Running Campaign",
                agent_id="ag_1",
                agent_version=1,
                voice_profile_id="vp_1",
                voice_profile_version=1,
                calling_number_id="pn_1",
                calling_number="+918000000000",
            )
            await self.repo.transition_status(campaign.id, "org_1", "running")

            with pytest.raises(ValueError, match="Cannot delete a running campaign"):
                await self.svc.delete_campaign(campaign.id, "org_1")

            # Pausing allows deletion
            await self.repo.transition_status(campaign.id, "org_1", "paused")
            deleted = await self.svc.delete_campaign(campaign.id, "org_1")
            assert deleted is True

        run(_test())
