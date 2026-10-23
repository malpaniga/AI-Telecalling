"""Unit tests for VobizTelephonyProvider adapter."""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.providers.telephony.vobiz import VobizTelephonyProvider


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestVobizTelephonyProvider:
    def test_provider_name_and_capabilities(self):
        provider = VobizTelephonyProvider()
        assert provider.provider_name == "vobiz"
        caps = provider.get_capabilities()
        assert caps["outbound_calling"] is True
        assert caps["inbound_calling"] is True
        assert caps["streaming_audio"] is True

    @patch("httpx.AsyncClient.post")
    def test_initiate_call_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "call_id": "call_vobiz_uuid_999",
            "status": "queued",
            "message": "Call queued successfully",
        }
        mock_post.return_value = mock_resp

        provider = VobizTelephonyProvider()

        async def _t():
            result = await provider.initiate_call(
                to="+919876543210",
                from_number="+911234567890",
                auth_id="v_aid_test",
                auth_token="v_token_test",
                url="https://api.domain.com/vobiz/voice?call_id=c123",
            )
            assert result["provider_resource_id"] == "call_vobiz_uuid_999"
            assert result["status"] == "queued"

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            endpoint = call_args[0][0]
            assert "https://api.vobiz.ai/api/v1/Account/v_aid_test/Call/" in endpoint
            headers = call_args[1]["headers"]
            assert headers["X-Auth-ID"] == "v_aid_test"
            assert headers["X-Auth-Token"] == "v_token_test"
            payload = call_args[1]["json"]
            assert payload["from"] == "+911234567890"
            assert payload["to"] == "+919876543210"
            assert payload["answer_url"] == "https://api.domain.com/vobiz/voice?call_id=c123"

        run(_t())

    @patch("httpx.AsyncClient.post")
    def test_hangup_call_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        provider = VobizTelephonyProvider()

        async def _t():
            await provider.hangup_call(
                provider_resource_id="call_vobiz_uuid_999",
                auth_id="v_aid_test",
                auth_token="v_token_test",
            )
            mock_post.assert_called_once()

        run(_t())
