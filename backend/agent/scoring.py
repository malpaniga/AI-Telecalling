"""Lead scoring: a simple, explainable 0-100 heuristic.

Each filled qualification slot is worth points (a fully qualified lead is more
valuable), with bonuses for booking intent and interest, and a penalty for
wanting to end / not being interested. Sprint 6 can replace this with a learned
model once we have labelled outcomes.
"""

from backend.agent.state import SLOT_KEYS

# 15 points per slot -> 60 for a fully qualified lead.
_SLOT_POINTS = 15
_BOOK_BONUS = 30
_INTEREST_BONUS = 10
_END_PENALTY = 25


def score_lead(slots: dict[str, str | None], flags: dict[str, bool]) -> int:
    score = _SLOT_POINTS * sum(1 for k in SLOT_KEYS if slots.get(k))
    if flags.get("wants_to_book"):
        score += _BOOK_BONUS
    if flags.get("interested"):
        score += _INTEREST_BONUS
    if flags.get("wants_to_end") or flags.get("not_interested"):
        score -= _END_PENALTY
    return max(0, min(100, score))


def lead_status(slots: dict[str, str | None], flags: dict[str, bool], stage: str) -> str:
    """Map conversation state to a CRM status."""
    if stage == "booking" or flags.get("wants_to_book"):
        return "booked"
    if flags.get("wants_to_end"):
        return "lost"
    if all(slots.get(k) for k in SLOT_KEYS):
        return "qualified"
    if any(slots.get(k) for k in SLOT_KEYS):
        return "qualifying"
    return "new"


def call_outcome(flags: dict[str, bool], stage: str) -> str:
    if stage == "booking" or flags.get("wants_to_book"):
        return "booked"
    if flags.get("wants_to_end"):
        return "not_interested"
    return "callback"
