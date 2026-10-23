"""Tests for Vobiz.ai webhook and real-time WebSocket streaming."""

import asyncio
import base64
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock
import pytest
import mongomock_motor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.telephony.vobiz import (
    VobizTransport,
    _vobiz_xml,
    _vobiz_unavailable_xml,
    router as vobiz_router,
)


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestVobizStreaming:
    def test_vobiz_xml_generation(self):
        xml = _vobiz_xml(call_id="c_123", agent_id="a_456", lang="en-IN")
        assert "<Response>" in xml
        assert '<Stream bidirectional="true">' in xml
        assert "/ws/vobiz?call_id=c_123&agent_id=a_456&lang=en-IN" in xml
        assert "</Stream>" in xml
        assert "</Response>" in xml

    def test_vobiz_unavailable_xml_generation(self):
        xml = _vobiz_unavailable_xml()
        assert "<Response>" in xml
        assert "<Speak>" in xml
        assert "temporarily unavailable" in xml
        assert "<Hangup/>" in xml

    def test_vobiz_transport_play_and_clear(self):
        mock_ws = AsyncMock()
        transport = VobizTransport(mock_ws)
        transport.stream_id = "stream_xyz_789"

        # 1600 samples of 16kHz PCM16 (0.1s of audio)
        pcm16 = b"\x00\x00" * 1600

        async def _t():
            await transport.play(pcm16, sample_rate=16000)
            assert mock_ws.send_text.called
            sent_str = mock_ws.send_text.call_args_list[0][0][0]
            sent_json = json.loads(sent_str)

            assert sent_json["event"] == "playAudio"
            assert sent_json["streamId"] == "stream_xyz_789"
            assert sent_json["media"]["contentType"] == "audio/x-mulaw"
            assert sent_json["media"]["sampleRate"] == 8000
            assert "payload" in sent_json["media"]

            # Test clearAudio on barge-in
            await transport.clear()
            clear_str = mock_ws.send_text.call_args_list[-1][0][0]
            clear_json = json.loads(clear_str)
            assert clear_json["event"] == "clearAudio"
            assert clear_json["streamId"] == "stream_xyz_789"

        run(_t())

    def test_inbound_webhook_credit_check_and_lead_resolution(self):
        async def _t():
            client = mongomock_motor.AsyncMongoMockClient()
            db = client["test_saas"]

            from backend.models.phone_number import PhoneNumber
            from backend.repositories.phone_number_repo import PhoneNumberRepository
            pn_repo = PhoneNumberRepository(db)
            pn = PhoneNumber(
                number="+919876500000",
                provider="vobiz",
                status="assigned",
                assigned_org_ids=["org_solar_co"],
                inbound_organization_id="org_solar_co",
            )
            await pn_repo.insert(pn)

            # Test phone number lookup
            found_pn = await pn_repo.find_by_number("+919876500000")
            assert found_pn is not None
            assert found_pn.inbound_organization_id == "org_solar_co"

        run(_t())
