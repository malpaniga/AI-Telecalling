"""The conversation engine: a LangGraph state machine that drives the call.

Per user turn the graph runs two nodes:
  understand -> extract slots + intent flags from what the caller just said
  route      -> decide the next stage (greeting/qualification/objection/booking/end)

The graph owns the *state* (stage + slots). The spoken reply is then generated
with the stage-specific prompt and streamed sentence-by-sentence to TTS, keeping
the low-latency path from Sprint 1 intact.
"""

import asyncio
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
    OUTPUT_VARIABLE_KEYS,
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
    output_variables: dict[str, str | None]
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
        """Extract slots + output variables + intent flags from the latest user message."""
        user_clean = (state.get("last_user") or "").strip().lower().rstrip(".!?,।॥")

        # Fast-path for common 1-2 word affirmations & acknowledgments:
        # Avoids an expensive 4-8s LLM call when user simply says "Yes", "हो", "okay", etc.
        AFFIRMATIONS = {
            "हो", "होय", "yes", "yeah", "yep", "sure", "ok", "okay", "haan", "ha",
            "बोला", "सांगा", "चालू द्या", "ठीक आहे", "done", "alright", "right"
        }
        REJECTIONS = {
            "नाही", "नको", "no", "nope", "stop", "don't", "dont", "काहीच नको", "फोन ठेवा",
            "not interested", "busy"
        }

        words = user_clean.split()
        is_short_affirmation = user_clean in AFFIRMATIONS or (len(words) <= 3 and any(w in AFFIRMATIONS for w in words) and not any(w in REJECTIONS for w in words))
        is_short_rejection = user_clean in REJECTIONS or (len(words) <= 3 and any(w in REJECTIONS for w in words))

        if is_short_affirmation:
            slots = dict(state["slots"])
            output_vars = dict(state.get("output_variables") or {})
            if not output_vars.get("disposition"):
                output_vars["disposition"] = "needs_more_discovery"
            flags = {
                "raised_objection": False,
                "wants_to_book": False,
                "wants_to_end": False,
                "interested": True,
            }
            log.info("understand (fast-path): affirmation detected for %r -> interested=True", state["last_user"])
            return {"slots": slots, "output_variables": output_vars, "flags": flags}

        if is_short_rejection:
            slots = dict(state["slots"])
            output_vars = dict(state.get("output_variables") or {})

            # Context-aware rejection: a single "no" to a booking/survey
            # question does NOT mean the caller wants to end the call.
            # Only mark wants_to_end if the caller already declined once
            # before (disposition was "declined_booking" or "not_interested"),
            # or if the utterance is a hard stop phrase.
            previous_disposition = output_vars.get("disposition")
            already_declined_once = previous_disposition in (
                "not_interested", "declined_booking",
            )
            hard_rejections = {"काहीच नको", "फोन ठेवा", "not interested", "stop"}
            is_hard_rejection = user_clean in hard_rejections

            wants_to_end = already_declined_once or is_hard_rejection
            flags = {
                "raised_objection": False,
                "wants_to_book": False,
                "wants_to_end": wants_to_end,
                "interested": not wants_to_end,
            }
            if wants_to_end:
                output_vars["disposition"] = "not_interested"
            else:
                output_vars["disposition"] = "declined_booking"

            log.info(
                "understand (fast-path): rejection for %r -> wants_to_end=%s (prev=%s)",
                state["last_user"], wants_to_end, previous_disposition,
            )
            return {"slots": slots, "output_variables": output_vars, "flags": flags}

        known_context = dict(state["slots"])
        if state.get("output_variables"):
            known_context.update({k: v for k, v in state["output_variables"].items() if v})

        data = await self.llm.complete_json(
            EXTRACTION_SYSTEM_PROMPT,
            extraction_user_content(known_context, state["last_user"]),
        )
        # Merge slots: only overwrite when the extraction found a real value.
        slots = dict(state["slots"])
        for key in SLOT_KEYS:
            value = data.get(key)
            if value:
                slots[key] = str(value)

        # Merge output variables
        output_vars = dict(state.get("output_variables") or {})
        for key in OUTPUT_VARIABLE_KEYS:
            value = data.get(key)
            if value:
                output_vars[key] = str(value)

        flags = {
            "raised_objection": bool(data.get("raised_objection")),
            "wants_to_book": bool(data.get("wants_to_book")),
            "wants_to_end": bool(data.get("wants_to_end")),
            "interested": bool(data.get("interested")),
        }
        log.info("understand: slots=%s output_vars=%s flags=%s", slots, output_vars, flags)
        return {"slots": slots, "output_variables": output_vars, "flags": flags}

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
        self,
        state: ConversationState,
        user_text: str,
        language_name: str | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Advance the conversation by one user turn.

        Updates `state` in place (stage, slots, flags, messages) and yields the
        agent's reply sentence-by-sentence for TTS.
        """
        state["messages"].append({"role": "user", "content": user_text})

        graph_input = {
            "last_user": user_text,
            "stage": state["stage"],
            "slots": state["slots"],
            "output_variables": state.get("output_variables", {k: None for k in OUTPUT_VARIABLE_KEYS}),
            "flags": {},
        }

        if system_prompt:
            prompt = system_prompt
            voice_guidelines = (
                f"\n\nCRITICAL LIVE VOICE RULES (STRICT):\n"
                f"1. Spoken turn MUST be concise: 1 to 2 short sentences maximum (under 25 words total).\n"
                f"2. Vary your opening acknowledgments naturally (never repeat the exact same acknowledgment twice in a row).\n"
                f"3. If the caller asks a question or affirms to hear information, EXPLAIN the information first. Do NOT jump to offering a site survey before explaining what they asked.\n"
                f"4. If the caller says 'नाही' (no) to a site survey, do NOT hang up or say goodbye. Acknowledge politely in one short sentence, and gently offer bill savings information or ask if they have another question.\n"
            )
            if language_name and language_name != "English":
                voice_guidelines += (
                    f"5. The caller speaks {language_name}. Reply ONLY in natural, conversational {language_name}, "
                    f"written in that language's NATIVE SCRIPT (e.g. Devanagari for Marathi/Hindi) — never romanized Latin text."
                )
            prompt = prompt + voice_guidelines
            reply_parts: list[str] = []
            async for sentence in self.llm.stream_sentences(state["messages"], prompt):
                reply_parts.append(sentence)
                yield sentence
            state["messages"].append({"role": "assistant", "content": " ".join(reply_parts)})

            # Run extraction as background task so caller speech stream has zero concurrency contention
            async def _run_bg_extraction() -> None:
                try:
                    result = await self.graph.ainvoke(graph_input)
                    state["slots"] = result["slots"]
                    state["output_variables"] = result.get("output_variables", {})
                    state["flags"] = result["flags"]
                    state["stage"] = result["stage"]
                except Exception as exc:
                    log.warning("background extraction error: %s", exc)

            asyncio.create_task(_run_bg_extraction())
        else:
            result = await self.graph.ainvoke(graph_input)
            state["slots"] = result["slots"]
            state["output_variables"] = result.get("output_variables", {})
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
