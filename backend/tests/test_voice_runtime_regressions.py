import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.call_session import CallSession, _looks_like_noise


def make_session(**kwargs):
    transport = MagicMock(streaming=False)
    transport.notify = AsyncMock()
    transport.play = AsyncMock()
    transport.clear = AsyncMock()
    engine = MagicMock()
    stt = MagicMock(transcribe=AsyncMock(return_value="please tell me more"))
    tts = MagicMock(synthesize=AsyncMock(return_value=(b"\x00\x00", 16000)))
    with patch("backend.call_session.VADEndpointer"):
        session = CallSession(transport, stt, engine, tts, MagicMock(), **kwargs)
    return session


@pytest.mark.parametrize("text", ["0", "42", "9876543210", "thanks", "bye", "thank you"])
def test_meaningful_short_answers_are_not_noise(text):
    assert not _looks_like_noise(text)


def test_zero_sensitivity_is_preserved():
    assert make_session(barge_in_sensitivity=0).barge_in_sensitivity == 0


def test_sensitivity_controls_sustained_speech_confirmation():
    low = make_session(barge_in_sensitivity=0)
    high = make_session(barge_in_sensitivity=100)
    # Inspect the actual constructor parameters used for the endpointer.
    with patch("backend.call_session.VADEndpointer") as vad:
        CallSession(low.t, low.stt, low.engine, low.tts, low.store, barge_in_sensitivity=0)
        low_confirmation = vad.call_args.kwargs["confirm_ms"]
        CallSession(high.t, high.stt, high.engine, high.tts, high.store, barge_in_sensitivity=100)
        high_confirmation = vad.call_args.kwargs["confirm_ms"]
    assert 40 <= high_confirmation < low_confirmation <= 250


def test_interrupt_clears_playback_before_slow_cancellation_cleanup():
    async def scenario():
        session = make_session()
        cleanup_started = asyncio.Event()
        release_cleanup = asyncio.Event()

        async def responder():
            try:
                await asyncio.Event().wait()
            finally:
                cleanup_started.set()
                await release_cleanup.wait()

        session.responder = asyncio.create_task(responder())
        await asyncio.sleep(0)
        interruption = asyncio.create_task(session.handle_interrupt())
        await cleanup_started.wait()
        cleared = session.t.clear.await_count
        release_cleanup.set()
        await interruption
        assert cleared == 1

    asyncio.run(scenario())


def test_interrupt_cancels_filler_waiting_for_first_llm_sentence():
    async def scenario():
        session = make_session()
        filler_started = asyncio.Event()
        filler_cancelled = asyncio.Event()

        async def synthesize(*args, **kwargs):
            filler_started.set()
            try:
                await asyncio.Event().wait()
            finally:
                filler_cancelled.set()

        async def turn(*args, **kwargs):
            await asyncio.Event().wait()
            yield "Unreachable"

        session.tts.synthesize = synthesize
        session.engine.run_turn = turn
        session.responder = asyncio.create_task(session._handle_utterance(b"\x00\x00"))
        await filler_started.wait()
        await session.handle_interrupt()
        assert filler_cancelled.is_set()
        session.t.play.assert_not_awaited()

    asyncio.run(scenario())


def test_vad_reset_discards_partial_frame():
    from backend.audio.vad import VADEndpointer

    with patch("backend.audio.vad.settings.vad_backend", "webrtc"), patch("backend.audio.vad._WebRTCVAD") as classifier:
        classifier.return_value.window = 320
        vad = VADEndpointer()
        list(vad.process(b"\x01\x00"))
        assert vad._buf
        vad.reset()
        assert not vad._buf


def test_slow_filler_does_not_delay_ready_answer():
    async def scenario():
        session = make_session()
        filler_started = asyncio.Event()
        filler_cancelled = asyncio.Event()

        async def synthesize(text, *args, **kwargs):
            if text == "The actual answer.":
                return b"\x01\x00", 16000
            filler_started.set()
            try:
                await asyncio.Event().wait()
            finally:
                filler_cancelled.set()

        async def turn(*args, **kwargs):
            await filler_started.wait()
            yield "The actual answer."

        session.tts.synthesize = synthesize
        session.engine.run_turn = turn
        await asyncio.wait_for(session._handle_utterance(b"\x00\x00"), timeout=1)
        assert filler_cancelled.is_set()
        session.t.play.assert_awaited_once_with(b"\x01\x00", 16000)

    asyncio.run(scenario())


def test_first_audio_latency_measures_first_chunk_not_completed_synthesis():
    async def scenario():
        session = make_session()
        session.t.streaming = True
        session.stt.transcribe.return_value = "Hello"
        clock = [1000.0]

        async def turn(*args, **kwargs):
            yield "Hello there."

        async def synthesize(*args, **kwargs):
            clock[0] = 1000.125
            yield b"\x01\x00", 16000
            clock[0] = 1001.0
            yield b"\x02\x00", 16000

        session.engine.run_turn = turn
        session.tts.synthesize_stream = synthesize
        with patch("backend.call_session.time.perf_counter", side_effect=lambda: clock[0]):
            await session._handle_utterance(b"\x00\x00")
        end_event = next(call.args[0] for call in session.t.notify.await_args_list if call.args[0]["type"] == "turn_end")
        assert end_event["first_audio_ms"] == 125
        assert end_event["total_ms"] == 1000

    asyncio.run(scenario())


def test_greeting_is_cancellable_without_blocking_microphone_receiver():
    async def scenario():
        session = make_session(custom_greeting="Hello there.")
        session.call_id = "test-call"
        session._persist_turn = AsyncMock()
        session._save_session = AsyncMock()
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def synthesize(*args, **kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        session.tts.synthesize = synthesize
        with patch("backend.telephony.broadcaster.call_broadcaster.broadcast", new=AsyncMock()):
            await asyncio.wait_for(session.start(), timeout=1)
            await started.wait()
            await session.handle_interrupt()
        assert cancelled.is_set()
        session.t.play.assert_not_awaited()

    asyncio.run(scenario())
