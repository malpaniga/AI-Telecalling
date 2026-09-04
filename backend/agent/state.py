"""Conversation state shared across the LangGraph engine and the call loop.

Sprint 2 keeps state in-memory per websocket connection. Sprint 3 will persist
it to Redis (live session) and Postgres (durable record).
"""

from typing import TypedDict

# The five conversation stages (the state machine).
GREETING = "greeting"
QUALIFICATION = "qualification"
OBJECTION = "objection"
BOOKING = "booking"
END = "end"

STAGES = [GREETING, QUALIFICATION, OBJECTION, BOOKING, END]

# The qualification payload we must collect.
SLOT_KEYS = ["budget", "timeline", "city", "property_type"]

Message = dict[str, str]


class ConversationState(TypedDict):
    stage: str
    slots: dict[str, str | None]
    flags: dict[str, bool]
    messages: list[Message]


def new_conversation_state() -> ConversationState:
    return {
        "stage": GREETING,
        "slots": {k: None for k in SLOT_KEYS},
        "flags": {},
        "messages": [],
    }


def slots_filled(slots: dict[str, str | None]) -> bool:
    return all(slots.get(k) for k in SLOT_KEYS)


def missing_slots(slots: dict[str, str | None]) -> list[str]:
    return [k for k in SLOT_KEYS if not slots.get(k)]
