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


def score_lead(
    slots: dict[str, str | None],
    flags: dict[str, bool],
    output_variables: dict[str, str | None] | None = None,
) -> int:
    score = _SLOT_POINTS * sum(1 for k in SLOT_KEYS if slots.get(k))
    ov = output_variables or {}
    discovery_filled = sum(1 for k, v in ov.items() if v and k != "disposition")
    score += min(40, discovery_filled * 15)

    if ov.get("disposition") in ("qualified", "appointment_set"):
        score += 30
    elif ov.get("disposition") == "not_interested":
        score -= 25

    if flags.get("wants_to_book"):
        score += _BOOK_BONUS
    if flags.get("interested"):
        score += _INTEREST_BONUS
    if flags.get("wants_to_end") or flags.get("not_interested"):
        score -= _END_PENALTY
    return max(0, min(100, score))


def lead_status(
    slots: dict[str, str | None],
    flags: dict[str, bool],
    stage: str,
    output_variables: dict[str, str | None] | None = None,
) -> str:
    """Map conversation state to a CRM status."""
    ov = output_variables or {}
    disp = ov.get("disposition")
    if disp in ("qualified", "appointment_set", "booked") or stage == "booking" or flags.get("wants_to_book"):
        return "qualified"
    if disp == "not_interested" or flags.get("wants_to_end") or flags.get("not_interested"):
        return "not_interested"
    if disp == "callback_requested" or flags.get("callback"):
        return "callback"
    if flags.get("interested"):
        return "qualified"
    if all(slots.get(k) for k in SLOT_KEYS):
        return "qualified"
    if any(slots.get(k) for k in SLOT_KEYS):
        return "qualifying"
    return "contacted"


def call_outcome(
    flags: dict[str, bool],
    stage: str,
    output_variables: dict[str, str | None] | None = None,
) -> str:
    ov = output_variables or {}
    disp = ov.get("disposition")
    if disp in ("qualified", "appointment_set", "booked"):
        return "qualified"
    if stage == "booking" or flags.get("wants_to_book"):
        return "qualified"
    if disp == "not_interested" or flags.get("wants_to_end") or flags.get("not_interested"):
        return "not_interested"
    if disp == "callback_requested" or flags.get("callback"):
        return "callback"
    if flags.get("interested"):
        return "qualified"
    return "contacted"
