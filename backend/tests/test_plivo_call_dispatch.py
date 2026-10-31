"""Tests for CallService Plivo outbound dispatch and failure handling."""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
import mongomock_motor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.models.phone_number import PhoneNumber
from backend.repositories.phone_number_repo import PhoneNumberRepository
from backend.services.call_service import CallService


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestPlivoCallDispatch:
    def setup_method(self):
        self.client = mongomock_motor.AsyncMongoMockClient()
        self.db = self.client["test_saas"]
        self.pn_repo = PhoneNumberRepository(self.db)
        self.call_service = CallService(self.db)

        async def _seed():
            from backend.repositories.wallet_repo import WalletRepository
            w_repo = WalletRepository(self.db)
            w1 = await w_repo.get_or_create("org_1")
            await w_repo.atomic_credit_available(w1.id, 5000)
            w2 = await w_repo.get_or_create("org_attacker")
            await w_repo.atomic_credit_available(w2.id, 5000)
        run(_seed())

    @patch("backend.providers.telephony.plivo.PlivoTelephonyProvider.initiate_call")
    def test_initiate_call_dispatches_via_plivo(self, mock_plivo_initiate):
        mock_plivo_initiate.return_value = {
            "provider_resource_id": "plivo_call_req_uuid_123",
            "status": "queued",
        }

        async def _t():
            # 1. Seed a Plivo phone number assigned to org_1
            pn = PhoneNumber(
                number="+911234567890",
                provider="plivo",
                status="assigned",
                assigned_org_ids=["org_1"],
                provider_metadata={
                    "plivo_auth_id": "auth_plivo_key_123",
                    "plivo_auth_token": "token_plivo_secret_456",
                },
            )
            await self.pn_repo.insert(pn)

            # 2. Initiate call from org_1
            result = await self.call_service.initiate_call(
                organization_id="org_1",
                to_number="+919876543210",
                from_number="+911234567890",
                agent_id="agent_solar",
            )
            assert "call_id" in result

            # Verify PlivoTelephonyProvider.initiate_call was invoked with number's credentials
            mock_plivo_initiate.assert_called_once()
            call_kwargs = mock_plivo_initiate.call_args[1]
            assert call_kwargs["to"] == "+919876543210"
            assert call_kwargs["from_number"] == "+911234567890"
            assert call_kwargs["auth_id"] == "auth_plivo_key_123"
            assert call_kwargs["auth_token"] == "token_plivo_secret_456"
            assert "answer_url" in call_kwargs.get("url", "") or "plivo/voice" in call_kwargs.get("url", "")

            # Verify call record was updated
            call_doc = await self.db.calls.find_one({"_id": result["call_id"]})
            assert call_doc["provider"] == "plivo"
            assert call_doc["provider_resource_id"] == "plivo_call_req_uuid_123"

        run(_t())

    @patch("backend.providers.telephony.plivo.PlivoTelephonyProvider.initiate_call")
    def test_plivo_dispatch_failure_rolls_back_credits(self, mock_plivo_initiate):
        mock_plivo_initiate.side_effect = RuntimeError("Plivo authentication failed")

        async def _t():
            pn = PhoneNumber(
                number="+911234567890",
                provider="plivo",
                status="assigned",
                assigned_org_ids=["org_1"],
                provider_metadata={
                    "plivo_auth_id": "auth_plivo_bad",
                    "plivo_auth_token": "token_plivo_bad",
                },
            )
            await self.pn_repo.insert(pn)

            with pytest.raises(RuntimeError, match="Telephony dispatch failed"):
                await self.call_service.initiate_call(
                    organization_id="org_1",
                    to_number="+919876543210",
                    from_number="+911234567890",
                )

            # Check that call record is marked failed
            call_doc = await self.db.calls.find_one({"organization_id": "org_1"})
            assert call_doc is not None
            assert call_doc["status"] == "failed"

        run(_t())

    def test_unauthorized_number_rejected(self):
        async def _t():
            pn = PhoneNumber(
                number="+911234567890",
                provider="plivo",
                status="assigned",
                assigned_org_ids=["org_allowed"],
            )
            await self.pn_repo.insert(pn)

            with pytest.raises(ValueError, match="not assigned to organization"):
                await self.call_service.initiate_call(
                    organization_id="org_attacker",
                    to_number="+919876543210",
                    from_number="+911234567890",
                )

        run(_t())
