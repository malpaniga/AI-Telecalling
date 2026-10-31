"""Tests for custom column mapping, contact upsert, and campaign enrollment."""

import asyncio
import pytest
import mongomock_motor

from backend.services.lead_service import LeadService, _apply_mapping


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestLeadImportMapping:
    def setup_method(self):
        self.client = mongomock_motor.AsyncMongoMockClient()
        self.db = self.client["test_lead_import"]
        self.service = LeadService(self.db)

    def test_apply_mapping_custom_variables(self):
        headers = ["Mobile Number", "Customer Name", "Residence City", "Balance Due"]
        rows = [["+919876543210", "Aarav Sharma", "Delhi", "15000"]]
        mapping = {
            "Mobile Number": "phone",
            "Customer Name": "user_name",
            "Residence City": "city",
            "Balance Due": "due_amount",
        }
        mapped = _apply_mapping(headers, rows, mapping)
        assert len(mapped) == 1
        assert mapped[0]["phone"] == "+919876543210"
        assert mapped[0]["name"] == "Aarav Sharma"
        assert mapped[0]["_custom"]["city"] == "Delhi"
        assert mapped[0]["_custom"]["due_amount"] == "15000"
        assert mapped[0]["_custom"]["user_name"] == "Aarav Sharma"

    def test_import_leads_upsert_and_campaign_enrollment(self):
        async def _test():
            csv_content = b"phone,name,city\n+919876543210,Aarav,Delhi\n"
            res1 = await self.service.import_leads(
                organization_id="org_test",
                content=csv_content,
                file_format="csv",
                campaign_id="camp_A",
                column_mapping={"phone": "phone", "name": "name", "city": "city"},
            )
            assert res1["imported"] == 1

            # Re-import same phone for camp_B with updated custom field
            csv_content_b = b"phone,name,city,offer\n+919876543210,Aarav Sharma,Mumbai,DISCOUNT50\n"
            res2 = await self.service.import_leads(
                organization_id="org_test",
                content=csv_content_b,
                file_format="csv",
                campaign_id="camp_B",
                column_mapping={
                    "phone": "phone",
                    "name": "name",
                    "city": "city",
                    "offer": "offer",
                },
            )
            assert res2["skipped_duplicate"] == 0
            assert res2["imported"] == 1

            # Check both campaigns have the lead in campaign_leads
            camp_lead_a = await self.db["campaign_leads"].find_one({"campaign_id": "camp_A"})
            camp_lead_b = await self.db["campaign_leads"].find_one({"campaign_id": "camp_B"})
            assert camp_lead_a is not None
            assert camp_lead_b is not None
            assert camp_lead_b["custom_fields"]["offer"] == "DISCOUNT50"

            # Check master lead is updated
            master = await self.db["leads"].find_one({"phone": "+919876543210"})
            assert master is not None
            assert master["name"] == "Aarav Sharma"
            assert master["custom_fields"]["city"] == "Mumbai"

        run(_test())
