import asyncio
from functools import wraps
from unittest.mock import AsyncMock

import pytest

from backend.agent.engine import ConversationEngine
from backend.agent.state import new_conversation_state


def run_async(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapped


class FakeLLM:
    def __init__(self):
        self.complete_json = AsyncMock(return_value={"timeline": "tomorrow"})
        self.prompts = []

    async def stream_sentences(self, messages, prompt):
        self.prompts.append(prompt)
        yield "How can I help?"


@pytest.mark.parametrize("utterance", ["yes tomorrow", "not busy", "no problem", "right in Pune"])
@run_async
async def test_meaningful_short_utterances_are_extracted(utterance):
    llm = FakeLLM()
    engine = ConversationEngine(llm)
    state = new_conversation_state()
    await engine._understand({**state, "last_user": utterance})
    llm.complete_json.assert_awaited_once()


@pytest.mark.parametrize("utterance", ["yes", "हो", "stop", "फोन ठेवा"])
@run_async
async def test_exact_acknowledgments_and_stop_requests_keep_fast_path(utterance):
    llm = FakeLLM()
    engine = ConversationEngine(llm)
    result = await engine._understand({**new_conversation_state(), "last_user": utterance})
    llm.complete_json.assert_not_awaited()
    assert result["flags"]["wants_to_end"] == (utterance in {"stop", "फोन ठेवा"})


@run_async
async def test_voice_guidance_is_not_solar_specific():
    llm = FakeLLM()
    engine = ConversationEngine(llm)
    async for _ in engine.run_turn(new_conversation_state(), "yes", system_prompt="You book car repairs."):
        pass
    await asyncio.sleep(0.05)
    assert "site survey" not in llm.prompts[0]
    assert "bill savings" not in llm.prompts[0]
    assert "one question" in llm.prompts[0].lower()


@run_async
async def test_background_extractions_keep_turn_order_and_accumulate_slots():
    engine = ConversationEngine(FakeLLM())
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    second_finished = asyncio.Event()
    seen = []

    async def extract(data):
        seen.append(data["last_user"])
        if data["last_user"] == "Pune":
            first_started.set()
            await release_first.wait()
            slots = {**data["slots"], "city": "Pune"}
        else:
            slots = {**data["slots"], "timeline": "tomorrow"}
            second_finished.set()
        return {**data, "slots": slots}

    engine.graph = AsyncMock()
    engine.graph.ainvoke.side_effect = extract
    state = new_conversation_state()
    try:
        async for _ in engine.run_turn(state, "Pune", system_prompt="Helpful assistant"):
            pass
        await asyncio.wait_for(first_started.wait(), 1)
        async for _ in engine.run_turn(state, "tomorrow", system_prompt="Helpful assistant"):
            pass
        await asyncio.sleep(0)
        assert seen == ["Pune"]
    finally:
        release_first.set()
        await asyncio.wait_for(second_finished.wait(), 1)
        await asyncio.sleep(0.05)
    assert state["slots"]["city"] == "Pune"
    assert state["slots"]["timeline"] == "tomorrow"
    assert not engine._extraction_tasks


@run_async
async def test_slow_extraction_does_not_block_speech_or_another_call():
    engine = ConversationEngine(FakeLLM())
    slow_started = asyncio.Event()
    release_slow = asyncio.Event()
    fast_finished = asyncio.Event()

    async def extract(data):
        if data["last_user"] == "slow":
            slow_started.set()
            await release_slow.wait()
        else:
            fast_finished.set()
        return data

    engine.graph = AsyncMock()
    engine.graph.ainvoke.side_effect = extract
    slow_state = new_conversation_state()
    fast_state = new_conversation_state()
    try:
        async for _ in engine.run_turn(slow_state, "slow", system_prompt="Be helpful"):
            pass
        await asyncio.wait_for(slow_started.wait(), 1)
        reply = [part async for part in engine.run_turn(fast_state, "fast", system_prompt="Be helpful")]
        assert reply == ["How can I help?"]
        await asyncio.wait_for(fast_finished.wait(), 1)
        assert not release_slow.is_set()
    finally:
        release_slow.set()
        await asyncio.gather(*engine._extraction_tasks.values())
    assert not engine._extraction_tasks
