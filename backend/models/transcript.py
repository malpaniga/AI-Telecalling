"""Transcript model — full turn-by-turn call record.

One Transcript document per call (unique by call_id).
Turns are stored as embedded array (max ~100 turns per call — safe for MongoDB).

Stored separately from Call to keep Call documents small.
Post-call processing populates summary, qualification, score, outcome.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from backend.models.base import TimestampedModel


class Turn(TimestampedModel):
    """A single turn (user or agent utterance) in the call transcript."""
    role: str               # "user" | "agent"
    text: str
    stage: Optional[str] = None
    latency_ms: Optional[int] = None
    ts: Optional[datetime] = None


class Transcript(TimestampedModel):
    """Full transcript for a single call. Unique per call_id."""
    organization_id: str
    call_id: str
    lead_id: Optional[str] = None
    campaign_id: Optional[str] = None

    turns: list[Turn] = Field(default_factory=list)
    turn_count: int = 0

    # Post-call processing results
    summary: Optional[str] = None
    qualification: dict[str, Any] = Field(default_factory=dict)
    score: int = 0
    outcome: Optional[str] = None

    # Processing state
    processing_status: str = "pending"   # pending | processing | completed | failed
    processed_at: Optional[datetime] = None
    processing_error: Optional[str] = None

    # Language
    language: str = "en-IN"
