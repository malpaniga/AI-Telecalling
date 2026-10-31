"""Tests for CampaignLead model and CampaignLeadRepository."""

import asyncio
import pytest
import mongomock_motor

from backend.models.campaign_lead import CampaignLead
from backend.repositories.campaign_lead_repo import CampaignLeadRepository


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestCampaignLeadRepo:
    def setup_method(self):
        self.client = mongomock_motor.AsyncMongoMockClient()
        self.db = self.client["test_campaign_leads"]
        self.repo = CampaignLeadRepository(self.db)

    def test_enroll_and_find_campaign_lead(self):
        async def _test():
            lead = await self.repo.enroll_lead(
                campaign_id="camp_1",
                lead_id="lead_1",
                organization_id="org_1",
                phone="+919876543210",
                custom_fields={"city": "Mumbai", "loan_amount": "50000"},
            )
            assert lead.campaign_id == "camp_1"
            assert lead.status == "new"
            assert lead.custom_fields["city"] == "Mumbai"

            found = await self.repo.find_by_campaign_lead("camp_1", "lead_1")
            assert found is not None
            assert found.phone == "+919876543210"
            assert found.custom_fields["loan_amount"] == "50000"

        run(_test())

    def test_multi_campaign_enrollment_isolation(self):
        async def _test():
            # Enroll same lead into camp_1 and camp_2
            await self.repo.enroll_lead("camp_1", "lead_1", "org_1", "+919876543210")
            await self.repo.enroll_lead("camp_2", "lead_1", "org_1", "+919876543210")

            # Update camp_1 to contacted
            await self.repo.update_status("camp_1", "lead_1", "contacted")

            lead_1 = await self.repo.find_by_campaign_lead("camp_1", "lead_1")
            lead_2 = await self.repo.find_by_campaign_lead("camp_2", "lead_1")
            assert lead_1.status == "contacted"
            assert lead_2.status == "new"

        run(_test())

    def test_bulk_enroll_and_list_for_campaign(self):
        async def _test():
            items = [
                {
                    "lead_id": f"lead_{i}",
                    "phone": f"+91987654321{i}",
                    "custom_fields": {"index": i},
                }
                for i in range(5)
            ]
            result = await self.repo.bulk_enroll("camp_bulk", "org_1", items)
            assert result["enrolled"] == 5

            leads, total = await self.repo.list_for_campaign("camp_bulk", "org_1")
            assert total == 5
            assert len(leads) == 5

        run(_test())

    def test_mark_dnc_for_phone(self):
        async def _test():
            await self.repo.enroll_lead("camp_1", "lead_1", "org_1", "+919999999999")
            await self.repo.enroll_lead("camp_2", "lead_1", "org_1", "+919999999999")

            updated = await self.repo.mark_dnc_for_phone("org_1", "+919999999999")
            assert updated >= 2

            l1 = await self.repo.find_by_campaign_lead("camp_1", "lead_1")
            l2 = await self.repo.find_by_campaign_lead("camp_2", "lead_1")
            assert l1.status == "dnc"
            assert l2.status == "dnc"

        run(_test())
