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

# Sarvam AI enterprise discovery output variables
OUTPUT_VARIABLE_KEYS = [
    "disposition",
    "pain_points_mentioned",
    "current_state_of_solving",
    "budget_indication",
    "timeline_to_decide",
    "chosen_next_step",
    "next_step_date_time",
]

Message = dict[str, str]


class ConversationState(TypedDict, total=False):
    stage: str
    slots: dict[str, str | None]
    flags: dict[str, bool]
    messages: list[Message]
    output_variables: dict[str, str | None]


def new_conversation_state() -> ConversationState:
    return {
        "stage": GREETING,
        "slots": {k: None for k in SLOT_KEYS},
        "flags": {},
        "messages": [],
        "output_variables": {k: None for k in OUTPUT_VARIABLE_KEYS},
    }


def slots_filled(slots: dict[str, str | None]) -> bool:
    return all(slots.get(k) for k in SLOT_KEYS)


def missing_slots(slots: dict[str, str | None]) -> list[str]:
    return [k for k in SLOT_KEYS if not slots.get(k)]
