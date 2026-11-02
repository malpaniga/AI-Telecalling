"""Tests for handling greeting interruptions, barge-in on pickup, and noise filtering."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.call_session import CallSession, _looks_like_noise
from backend.agent.engine import ConversationEngine


def _make_mock_session(**kwargs):
    transport = AsyncMock()
    transport.streaming = True
    transport.play = AsyncMock()
    transport.clear = AsyncMock()
    transport.notify = AsyncMock()

    stt = AsyncMock()
    engine = MagicMock()

    async def _default_run_turn(state, user_text, language_name=None, system_prompt=None):
        state["messages"].append({"role": "user", "content": user_text})
        yield "Hello back"

    engine.run_turn = _default_run_turn
    engine.llm = AsyncMock()
    tts = AsyncMock()
    tts.synthesize_stream = MagicMock()

    # Async generator for synthesize_stream
    async def _dummy_stream(*args, **kws):
        yield b"\x00" * 320, 8000

    tts.synthesize_stream.return_value = _dummy_stream()
    store = AsyncMock()
    store.save = AsyncMock()

    session = CallSession(
        transport=transport,
        stt=stt,
        engine=engine,
        tts=tts,
        store=store,
        direction=kwargs.get("direction", "outbound"),
        agent_name=kwargs.get("agent_name", "Parijat"),
        custom_greeting=kwargs.get("custom_greeting", "Hello, welcome to our store! We have a special discount today."),
        system_prompt=kwargs.get("system_prompt", None),
    )
    return session, transport, engine, tts


def test_carrier_recording_announcement_filtered_as_noise():
    """Automated telecom recording disclaimers must be treated as noise."""
    assert _looks_like_noise("This call is now being recorded.") is True
    assert _looks_like_noise("this call is being recorded") is True
    assert _looks_like_noise("Call is now being recorded") is True
    assert _looks_like_noise("call recording has started") is True
    assert _looks_like_noise("recording started") is True
    # Real user speech must NOT be filtered
    assert _looks_like_noise("Hello") is False
    assert _looks_like_noise("हा बोला") is False
    assert _looks_like_noise("कोण आहे?") is False


@pytest.mark.anyio
async def test_completed_greeting_records_in_messages():
    """A fully delivered greeting is recorded in state['messages'] and marked completed."""
    session, transport, engine, tts = _make_mock_session()

    # Run greeting to completion
    await session._run_greeting()

    assert session._greeting_completed is True
    assert len(session.state["messages"]) == 1
    assert session.state["messages"][0]["role"] == "assistant"
    assert session.state["messages"][0]["content"] == "Hello, welcome to our store! We have a special discount today."


@pytest.mark.anyio
async def test_interrupted_greeting_does_not_leave_unheard_pitch_in_messages():
    """If greeting is cancelled mid-flight, state['messages'] must not retain the full pitch as heard."""
    session, transport, engine, tts = _make_mock_session()

    # Slow down synthesis so we can interrupt it
    async def _slow_say(*args, **kws):
        await asyncio.sleep(2.0)
        return 2.0

    session._say = _slow_say

    # Start greeting task
    session.responder = asyncio.create_task(session._run_greeting())
    await asyncio.sleep(0.05)  # Let it start

    # Caller interrupts (e.g. says 'Hello' or 'Who is this?')
    await session.handle_interrupt()

    # Greeting was interrupted: must NOT be marked completed
    assert session._greeting_completed is False

    # state['messages'] must NOT retain the full greeting as if it were fully delivered
    assert not any(
        m.get("content") == "Hello, welcome to our store! We have a special discount today."
        for m in session.state.get("messages", [])
    )


@pytest.mark.anyio
async def test_greeting_interruption_then_user_hello_allows_proper_opening():
    """When greeting is interrupted by user saying Hello / who's this, agent provides introduction rather than middle of script."""
    session, transport, engine, tts = _make_mock_session(
        system_prompt=(
            "Phase 1: Open with greeting and offer.\n"
            "Phase 2: Visit store.\n"
            "Phase 3: Questions."
        )
    )

    # Simulate interrupted greeting
    session._greeting_completed = False
    session.state["messages"] = []

    # Mock STT to return 'Hello.'
    session.stt.transcribe = AsyncMock(return_value="Hello.")

    # Mock engine.run_turn
    received_messages_snapshot = []

    async def _fake_run_turn(state, user_text, language_name=None, system_prompt=None):
        # Record what messages existed when run_turn was called
        received_messages_snapshot.extend(list(state["messages"]))
        state["messages"].append({"role": "user", "content": user_text})
        yield "नमस्कार! मी Parijat मधून बोलत आहे."

    session.engine.run_turn = _fake_run_turn
    session._can_pass_prompt = True

    # Process utterance
    await session._handle_utterance(b"\x00" * 3200)

    # In the messages before run_turn appended user_text, there was NO unplayed greeting
    assert received_messages_snapshot == []
    # And after turn, the first user message is Hello
    assert session.state["messages"][0]["role"] == "user"
    assert session.state["messages"][0]["content"] == "Hello."


@pytest.mark.anyio
async def test_engine_prompt_guidelines_include_interrupted_greeting_recovery():
    """Voice guidelines in engine.py must instruct LLM to introduce identity and purpose if greeting was interrupted."""
    mock_llm = AsyncMock()

    captured_prompt = []

    async def _fake_stream(messages, prompt):
        captured_prompt.append(prompt)
        yield "Namaskar!"

    mock_llm.stream_sentences = _fake_stream
    engine = ConversationEngine(llm=mock_llm)

    state = {
        "stage": "greeting",
        "slots": {},
        "output_variables": {},
        "flags": {},
        "messages": [],
    }

    async for _ in engine.run_turn(
        state,
        "हा बोला कोण आहे?",
        language_name="Marathi",
        system_prompt="Phase 1: Open with offer. Phase 2: Visit store.",
    ):
        pass

    assert len(captured_prompt) == 1
    p = captured_prompt[0]
    assert "interrupted" in p.lower()
    assert "who is speaking" in p.lower() or "who you are" in p.lower()
