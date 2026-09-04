"""The conversation engine: a LangGraph state machine that drives the call.

Per user turn the graph runs two nodes:
  understand -> extract slots + intent flags from what the caller just said
  route      -> decide the next stage (greeting/qualification/objection/booking/end)

The graph owns the *state* (stage + slots). The spoken reply is then generated
with the stage-specific prompt and streamed sentence-by-sentence to TTS, keeping
the low-latency path from Sprint 1 intact.
"""

import logging
from collections.abc import AsyncIterator
from typing import TypedDict

from langgraph.graph import END as GRAPH_END
from langgraph.graph import START, StateGraph

from backend.agent.llm import LLMClient
from backend.agent.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    extraction_user_content,
    stage_system_prompt,
)
from backend.agent.state import (
    BOOKING,
    END,
    GREETING,
    OBJECTION,
    QUALIFICATION,
    SLOT_KEYS,
    ConversationState,
    slots_filled,
)

log = logging.getLogger("engine")


class TurnState(TypedDict):
    """Ephemeral state passed through the graph for a single turn."""

    last_user: str
    stage: str
    slots: dict[str, str | None]
    flags: dict[str, bool]


def _decide_stage(stage: str, slots: dict, flags: dict) -> str:
    """Pure transition logic. Order matters: end > objection > booking > qualify."""
    if flags.get("wants_to_end"):
        return END
    if flags.get("raised_objection"):
        return OBJECTION
    filled = slots_filled(slots)
    if filled and (flags.get("wants_to_book") or flags.get("interested", True)):
        return BOOKING
    if filled:
        return BOOKING
    # Greeting, objection, OR a premature 'end' all funnel back into qualification
    # while the caller is still talking and we don't yet have everything. Without
    # the END case here, one "that's all" would trap the whole rest of the call.
    if stage in (GREETING, OBJECTION, END):
        return QUALIFICATION
    return stage


class ConversationEngine:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()
        self.graph = self._build_graph()

    # ---- graph nodes ----
    async def _understand(self, state: TurnState) -> dict:
        """Extract slots + intent flags from the latest user message."""
        data = await self.llm.complete_json(
            EXTRACTION_SYSTEM_PROMPT,
            extraction_user_content(state["slots"], state["last_user"]),
        )
        # Merge slots: only overwrite when the extraction found a real value.
        slots = dict(state["slots"])
        for key in SLOT_KEYS:
            value = data.get(key)
            if value:
                slots[key] = str(value)
        flags = {
            "raised_objection": bool(data.get("raised_objection")),
            "wants_to_book": bool(data.get("wants_to_book")),
            "wants_to_end": bool(data.get("wants_to_end")),
            "interested": bool(data.get("interested")),
        }
        log.info("understand: slots=%s flags=%s", slots, flags)
        return {"slots": slots, "flags": flags}

    async def _route(self, state: TurnState) -> dict:
        next_stage = _decide_stage(state["stage"], state["slots"], state["flags"])
        log.info("route: %s -> %s", state["stage"], next_stage)
        return {"stage": next_stage}

    def _build_graph(self):
        g = StateGraph(TurnState)
        g.add_node("understand", self._understand)
        g.add_node("route", self._route)
        g.add_edge(START, "understand")
        g.add_edge("understand", "route")
        g.add_edge("route", GRAPH_END)
        return g.compile()

    # ---- public API ----
    async def run_turn(
        self, state: ConversationState, user_text: str, language_name: str | None = None
    ) -> AsyncIterator[str]:
        """Advance the conversation by one user turn.

        Updates `state` in place (stage, slots, flags, messages) and yields the
        agent's reply sentence-by-sentence for TTS.
        """
        state["messages"].append({"role": "user", "content": user_text})

        result = await self.graph.ainvoke(
            {
                "last_user": user_text,
                "stage": state["stage"],
                "slots": state["slots"],
                "flags": {},
            }
        )
        state["slots"] = result["slots"]
        state["flags"] = result["flags"]
        state["stage"] = result["stage"]

        prompt = stage_system_prompt(state["stage"], state["slots"], language_name)
        reply_parts: list[str] = []
        async for sentence in self.llm.stream_sentences(state["messages"], prompt):
            reply_parts.append(sentence)
            yield sentence
        state["messages"].append({"role": "assistant", "content": " ".join(reply_parts)})


async def _smoke_test() -> None:
    import logging as _logging

    from backend.agent.state import new_conversation_state

    _logging.basicConfig(level="INFO")
    engine = ConversationEngine()
    state = new_conversation_state()
    state["stage"] = GREETING

    turns = [
        "Hi, I'm looking for a place to buy.",
        "My budget is around 90 lakhs and I want to move in about 3 months.",
        "I'm looking in Pune, ideally a 3 BHK apartment.",
        "Isn't that going to be really expensive though?",
        "Okay that sounds reasonable, yes let's set up a viewing.",
    ]
    for t in turns:
        print(f"\nUSER: {t}")
        reply = []
        async for s in engine.run_turn(state, t):
            reply.append(s)
        print(f"[stage={state['stage']}] AVA:", " ".join(reply))
    print("\nFINAL SLOTS:", state["slots"])


if __name__ == "__main__":
    import asyncio

    asyncio.run(_smoke_test())
