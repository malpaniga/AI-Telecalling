"""Unit tests for PlivoTelephonyProvider adapter."""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.providers.telephony.plivo import PlivoTelephonyProvider


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestPlivoTelephonyProvider:
    def test_provider_name_and_capabilities(self):
        provider = PlivoTelephonyProvider()
        assert provider.provider_name == "plivo"
        caps = provider.get_capabilities()
        assert caps["outbound_calling"] is True
        assert caps["inbound_calling"] is True
        assert caps["streaming_audio"] is True

    @patch("httpx.AsyncClient.post")
    def test_initiate_call_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "message": "call fired",
            "request_uuid": "plivo_req_uuid_12345",
            "api_id": "plivo_api_id_67890",
        }
        mock_post.return_value = mock_resp

        provider = PlivoTelephonyProvider()

        async def _t():
            result = await provider.initiate_call(
                to="+919876543210",
                from_number="+911234567890",
                auth_id="plivo_auth_id_test",
                auth_token="plivo_auth_token_test",
                url="https://api.domain.com/plivo/voice?call_id=c123",
            )
            assert result["provider_resource_id"] == "plivo_req_uuid_12345"
            assert result["status"] == "queued"

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            endpoint = call_args[0][0]
            assert "https://api.plivo.com/v1/Account/plivo_auth_id_test/Call/" in endpoint
            assert call_args[1]["auth"] == ("plivo_auth_id_test", "plivo_auth_token_test")
            payload = call_args[1]["json"]
            assert payload["from"] == "+911234567890"
            assert payload["to"] == "+919876543210"
            assert payload["answer_url"] == "https://api.domain.com/plivo/voice?call_id=c123"
            assert payload["answer_method"] == "POST"

        run(_t())

    @patch("httpx.AsyncClient.delete")
    def test_hangup_call_success(self, mock_delete):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_delete.return_value = mock_resp

        provider = PlivoTelephonyProvider()

        async def _t():
            await provider.hangup_call(
                provider_resource_id="plivo_req_uuid_12345",
                auth_id="plivo_auth_id_test",
                auth_token="plivo_auth_token_test",
            )
            mock_delete.assert_called_once()
            call_args = mock_delete.call_args
            endpoint = call_args[0][0]
            assert "https://api.plivo.com/v1/Account/plivo_auth_id_test/Call/plivo_req_uuid_12345/" in endpoint
            assert call_args[1]["auth"] == ("plivo_auth_id_test", "plivo_auth_token_test")

        run(_t())

    @patch("httpx.AsyncClient.get")
    def test_get_call_status_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "call_status": "in-progress",
            "call_uuid": "plivo_req_uuid_12345",
        }
        mock_get.return_value = mock_resp

        provider = PlivoTelephonyProvider()

        async def _t():
            status = await provider.get_call_status(
                provider_resource_id="plivo_req_uuid_12345",
                auth_id="plivo_auth_id_test",
                auth_token="plivo_auth_token_test",
            )
            assert status["provider_resource_id"] == "plivo_req_uuid_12345"
            assert status["status"] == "in-progress"
            mock_get.assert_called_once()

        run(_t())
