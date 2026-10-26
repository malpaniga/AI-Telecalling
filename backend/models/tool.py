"""Tool models — generic callable actions the AI agent can invoke during a call.

Tools are:
  - Registered in the ToolRegistry (per-org config overrides)
  - Validated before invocation (permissions, input schema)
  - Audited — every invocation creates an immutable ToolCall record

Built-in tools (always available, org can enable/disable):
  book_appointment     — create an appointment record
  schedule_callback    — schedule a callback at a specific time
  transfer_to_human    — transfer call to a human agent (with context)
  update_lead          — update qualification data on the lead
  add_note             — add a note to the lead record
  send_whatsapp        — send a WhatsApp message (requires integration)
  send_sms             — send an SMS (requires integration)
  get_customer_details — fetch existing customer record

Tools are generic — no solar/real-estate specific behavior in tool code.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from backend.models.base import TimestampedModel, DocumentModel, utcnow

BUILT_IN_TOOLS = {
    "book_appointment",
    "schedule_callback",
    "transfer_to_human",
    "update_lead",
    "add_note",
    "send_whatsapp",
    "send_sms",
    "get_customer_details",
}


class ToolConfig(TimestampedModel):
    """Organization-level tool configuration (enable/disable, override params)."""
    organization_id: str
    tool_name: str                          # must be in BUILT_IN_TOOLS or custom
    is_enabled: bool = True
    config_overrides: dict[str, Any] = Field(default_factory=dict)
    # Which roles can invoke this tool
    allowed_roles: list[str] = Field(default_factory=lambda: ["agent"])


class ToolCall(DocumentModel):
    """Immutable record of a single tool invocation during a call."""
    organization_id: str
    call_id: str
    lead_id: Optional[str] = None

    tool_name: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: Optional[dict[str, Any]] = None
    status: str = "pending"         # pending | success | failed
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None

    invoked_at: datetime = Field(default_factory=utcnow)
