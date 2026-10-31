"""Tests for Plivo Phone Number provider and multi-organization assignment."""

import asyncio
import os
import sys
import pytest
import mongomock_motor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.models.phone_number import PhoneNumber
from backend.services.phone_number_service import PhoneNumberService, _to_customer_view
from backend.repositories.phone_number_repo import PhoneNumberRepository


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestPlivoPhoneNumbers:
    def setup_method(self):
        self.client = mongomock_motor.AsyncMongoMockClient()
        self.db = self.client["test_saas"]
        self.repo = PhoneNumberRepository(self.db)
        self.service = PhoneNumberService(self.db)

    def test_plivo_number_model_and_customer_view_privacy(self):
        """Plivo credentials must be stored in provider_metadata and NEVER exposed in customer view."""
        pn = PhoneNumber(
            number="+919876543210",
            provider="plivo",
            provider_metadata={
                "plivo_auth_id": "plivo_sec_auth_123",
                "plivo_auth_token": "plivo_secret_token_abc",
                "plivo_app_id": "app_sid_12345",
            },
            assigned_org_ids=["org_alpha", "org_beta"],
            inbound_organization_id="org_alpha",
            inbound_agent_id="agent_solar_1",
        )
        assert pn.provider == "plivo"
        assert pn.provider_metadata["plivo_auth_id"] == "plivo_sec_auth_123"
        assert pn.provider_metadata["plivo_auth_token"] == "plivo_secret_token_abc"
        assert pn.assigned_org_ids == ["org_alpha", "org_beta"]
        assert pn.inbound_organization_id == "org_alpha"
        assert pn.inbound_agent_id == "agent_solar_1"

        view = _to_customer_view(pn)
        assert "provider" not in view
        assert "provider_metadata" not in view
        assert "plivo_auth_id" not in str(view)
        assert "plivo_auth_token" not in str(view)
        assert "app_sid_12345" not in str(view)
        assert view["number"] == "+919876543210"

    def test_multi_organization_assignment_and_listing(self):
        async def _t():
            # 1. Add number with Plivo provider
            pn = await self.service.add_to_inventory(
                number="+919988776655",
                provider="plivo",
                provider_metadata={
                    "plivo_auth_id": "plivo_aid_test",
                    "plivo_auth_token": "plivo_tok_test",
                },
                display_name="Plivo Shared DID",
            )
            assert pn.status == "available"

            # 2. Assign to multiple orgs
            assigned = await self.service.assign_to_orgs(
                phone_number_id=pn.id,
                org_ids=["org_alpha", "org_beta"],
                inbound_org_id="org_alpha",
                inbound_agent_id="agent_alpha_inbound",
                performed_by="admin_user_1",
            )
            assert assigned["status"] == "assigned"

            # 3. Both orgs can list and see this number
            alpha_numbers = await self.service.list_org_numbers("org_alpha")
            beta_numbers = await self.service.list_org_numbers("org_beta")
            gamma_numbers = await self.service.list_org_numbers("org_gamma")

            assert len(alpha_numbers) == 1
            assert alpha_numbers[0]["number"] == "+919988776655"
            assert len(beta_numbers) == 1
            assert beta_numbers[0]["number"] == "+919988776655"
            assert len(gamma_numbers) == 0

        run(_t())
