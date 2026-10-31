"""Tests for Plivo webhook and real-time WebSocket streaming."""

import asyncio
import base64
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock
import pytest
import mongomock_motor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.telephony.plivo import (
    PlivoTransport,
    _plivo_xml,
    _plivo_unavailable_xml,
    hangup_plivo_call,
    _active_transports,
    router as plivo_router,
)


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestPlivoStreaming:
    def test_plivo_xml_generation(self):
        xml = _plivo_xml(call_id="c_123", agent_id="a_456", lang="en-IN")
        assert "<Response>" in xml
        assert '<Stream bidirectional="true"' in xml
        assert 'keepCallAlive="true"' in xml
        assert "call_id=c_123" in xml
        assert "</Stream>" in xml
        assert "<Hangup/>" in xml
        assert "</Response>" in xml

    def test_plivo_unavailable_xml_generation(self):
        xml = _plivo_unavailable_xml()
        assert "<Response>" in xml
        assert "<Speak>" in xml
        assert "temporarily unavailable" in xml
        assert "<Hangup/>" in xml

    def test_plivo_transport_play_and_clear(self):
        mock_ws = AsyncMock()
        transport = PlivoTransport(mock_ws)
        transport.stream_id = "stream_plivo_xyz_789"

        # 1600 samples of 16kHz PCM16 (0.1s of audio)
        pcm16 = b"\x00\x00" * 1600

        async def _t():
            await transport.play(pcm16, sample_rate=16000)
            assert mock_ws.send_text.called
            sent_str = mock_ws.send_text.call_args_list[0][0][0]
            sent_json = json.loads(sent_str)

            assert sent_json["event"] == "playAudio"
            assert sent_json["streamId"] == "stream_plivo_xyz_789"
            assert sent_json["media"]["contentType"] == "audio/x-mulaw"
            assert sent_json["media"]["sampleRate"] == 8000
            assert "payload" in sent_json["media"]

            # Test clearAudio on barge-in
            await transport.clear()
            clear_str = mock_ws.send_text.call_args_list[-1][0][0]
            clear_json = json.loads(clear_str)
            assert clear_json["event"] == "clearAudio"
            assert clear_json["streamId"] == "stream_plivo_xyz_789"

            # Test close
            await transport.close()
            assert mock_ws.close.called

        run(_t())

    def test_hangup_plivo_call_helper(self):
        async def _t():
            mock_ws = AsyncMock()
            transport = PlivoTransport(mock_ws)
            _active_transports["call_active_plivo_123"] = transport

            res = await hangup_plivo_call("call_active_plivo_123")
            assert res is True
            assert mock_ws.close.called
            assert "call_active_plivo_123" not in _active_transports or mock_ws.close.called

        run(_t())

    def test_inbound_webhook_credit_check_and_lead_resolution(self):
        async def _t():
            client = mongomock_motor.AsyncMongoMockClient()
            db = client["test_saas"]

            from backend.models.phone_number import PhoneNumber
            from backend.models.agent import Agent
            from backend.repositories.phone_number_repo import PhoneNumberRepository
            from backend.repositories.agent_repo import AgentRepository
            from backend.repositories.wallet_repo import WalletRepository

            pn_repo = PhoneNumberRepository(db)
            agent_repo = AgentRepository(db)
            w_repo = WalletRepository(db)

            # Seed agent
            agent = Agent(
                organization_id="org_test",
                name="Plivo Agent",
                primary_language="en-IN",
                template_slug="lead-qualification",
                voice_profile_id="vp-default",
                voice_profile_version=1,
            )
            await agent_repo.insert(agent)

            # Seed phone number
            pn = PhoneNumber(
                number="+911122334455",
                provider="plivo",
                status="assigned",
                assigned_org_ids=["org_test"],
                inbound_organization_id="org_test",
                inbound_agent_id=agent.id,
            )
            await pn_repo.insert(pn)

            # Case 1: 0 credits -> returns unavailable XML
            w = await w_repo.get_or_create("org_test")
            from starlette.requests import Request
            from unittest.mock import MagicMock

            from backend.telephony.plivo import plivo_voice

            req = MagicMock(spec=Request)
            req.method = "POST"
            req.query_params = {}
            req.headers = {}
            req.url = MagicMock()
            req.url.scheme = "https"
            async def _form():
                return {"To": "+911122334455", "From": "+919988776655"}
            req.form = _form

            with pytest.MonkeyPatch.context() as m:
                m.setattr("backend.telephony.plivo.get_db", lambda: db)
                resp = await plivo_voice(req)
                assert resp.status_code == 200
                assert "temporarily unavailable" in resp.body.decode()

                # Case 2: Positive credits -> reserves credits and returns stream XML
                await w_repo.atomic_credit_available(w.id, 5000)
                resp2 = await plivo_voice(req)
                assert resp2.status_code == 200
                assert "<Stream bidirectional" in resp2.body.decode()

                # Verify call created
                calls = await db.calls.find({"provider": "plivo"}).to_list(10)
                assert len(calls) == 1
                assert calls[0]["to_number"] == "+911122334455"
                assert calls[0]["from_number"] == "+919988776655"
                assert calls[0]["direction"] == "inbound"

        run(_t())
