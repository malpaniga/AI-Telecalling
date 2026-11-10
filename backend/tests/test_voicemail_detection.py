import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.call_session import CallSession, _is_voicemail_or_screening

def test_siri_live_voicemail_patterns():
    assert _is_voicemail_or_screening("Hi, please state your name and why you're calling") is True
    assert _is_voicemail_or_screening("State your name and why you are calling and I'll see if they are available") is True
    assert _is_voicemail_or_screening("The person you are trying to reach is not available, please leave a message") is True
    assert _is_voicemail_or_screening("Tell them who is calling and I'll connect you") is True

def test_google_call_screen_patterns():
    assert _is_voicemail_or_screening("Hi, the person you're reaching is using a screening service from Google") is True
    assert _is_voicemail_or_screening("Google screening service, please say why you are calling") is True
    assert _is_voicemail_or_screening("Will get a copy of this conversation, go ahead and say why you're calling") is True

def test_carrier_voicemail_patterns():
    assert _is_voicemail_or_screening("Please leave your message after the tone") is True
    assert _is_voicemail_or_screening("At the tone, please record your message") is True
    assert _is_voicemail_or_screening("You have reached the voicemail of 8698732771") is True
    assert _is_voicemail_or_screening("The party you are trying to reach is not available to take your call") is True
    assert _is_voicemail_or_screening("कृपया संदेश छोड़ें") is True
    assert _is_voicemail_or_screening("कृपया संदेश ठेवा") is True

def test_human_answers_not_detected_as_voicemail():
    assert _is_voicemail_or_screening("Hello, who is calling?") is False
    assert _is_voicemail_or_screening("Yes, speaking, what is this about?") is False
    assert _is_voicemail_or_screening("Namaste, kaun bol raha hai?") is False
    assert _is_voicemail_or_screening("Sure, tell me more about the project") is False
    assert _is_voicemail_or_screening("I am busy right now, call me later") is False

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_call_session_voicemail_detected_hangup():
    mock_transport = AsyncMock()
    mock_transport.play = AsyncMock()
    mock_transport.notify = AsyncMock()
    mock_transport.clear = AsyncMock()
    mock_transport.close = AsyncMock()

    mock_stt = AsyncMock()
    mock_stt.transcribe = AsyncMock(return_value="Hi, please state your name and why you're calling")

    mock_engine = MagicMock()
    mock_engine.run_turn = MagicMock()

    mock_tts = AsyncMock()
    mock_store = AsyncMock()

    session = CallSession(
        transport=mock_transport,
        stt=mock_stt,
        engine=mock_engine,
        tts=mock_tts,
        store=mock_store,
        detect_voicemail=True,
    )

    await session._handle_utterance(b"\x00" * 3200)

    # Must set disposition to voicemail
    assert session.state["output_variables"].get("disposition") == "voicemail"
    assert session._call_ending is True

    # Must notify hangup with voicemail_detected
    hangup_notifications = [
        call.args[0] for call in mock_transport.notify.call_args_list
        if call.args[0].get("type") == "hangup"
    ]
    assert len(hangup_notifications) > 0
    assert hangup_notifications[0]["reason"] == "voicemail_detected"

    # Must NOT call the LLM engine
    mock_engine.run_turn.assert_not_called()

@pytest.mark.anyio
async def test_call_session_voicemail_detection_disabled_pitches():
    mock_transport = AsyncMock()
    mock_transport.play = AsyncMock()
    mock_transport.notify = AsyncMock()
    mock_transport.clear = AsyncMock()
    mock_transport.close = AsyncMock()

    mock_stt = AsyncMock()
    mock_stt.transcribe = AsyncMock(return_value="Hi, please state your name and why you're calling")

    async def fake_turn(*args, **kwargs):
        yield "Hello, I am calling regarding your real estate inquiry."

    mock_engine = MagicMock()
    mock_engine.run_turn = MagicMock(side_effect=fake_turn)

    mock_tts = AsyncMock()
    mock_tts.synthesize = AsyncMock(return_value=(b"\x00" * 1600, 16000))
    mock_store = AsyncMock()

    session = CallSession(
        transport=mock_transport,
        stt=mock_stt,
        engine=mock_engine,
        tts=mock_tts,
        store=mock_store,
        detect_voicemail=False, # Disabled!
    )

    await session._handle_utterance(b"\x00" * 3200)

    # When disabled, it does NOT treat it as voicemail disposition
    assert session.state["output_variables"].get("disposition") != "voicemail"
    # LLM engine WAS called to pitch
    mock_engine.run_turn.assert_called_once()
