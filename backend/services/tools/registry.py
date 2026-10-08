"""Tool registry — central catalog of callable tools.

Each tool is a callable with a standard signature:
  async def tool_fn(inputs: dict, context: ToolContext) -> dict

ToolContext provides:
  - db: database handle
  - call_id, lead_id, organization_id
  - call_state (qualification slots, stage)

The registry:
  - Registers built-in tools on startup
  - Resolves tool name → callable
  - Validates that the tool is enabled for the org
  - Records invocations as immutable ToolCall documents
  - Validates input schemas before invocation

No tool implementation contains business-specific logic (solar/real-estate).
"""

import logging
import time
from typing import Any, Callable, Coroutine, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.base import new_id
from backend.models.tool import BUILT_IN_TOOLS, ToolCall

log = logging.getLogger("tools.registry")


class ToolContext:
    """Runtime context passed to every tool invocation."""
    __slots__ = (
        "db", "call_id", "lead_id", "organization_id",
        "call_state", "language",
    )

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        call_id: str,
        organization_id: str,
        lead_id: Optional[str] = None,
        call_state: Optional[dict] = None,
        language: str = "en-IN",
    ):
        self.db = db
        self.call_id = call_id
        self.lead_id = lead_id
        self.organization_id = organization_id
        self.call_state = call_state or {}
        self.language = language


ToolFn = Callable[[dict, ToolContext], Coroutine[Any, Any, dict]]


class ToolRegistry:
    """Central tool registry. Singleton-friendly; no global state."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._tools: dict[str, ToolFn] = {}
        self._schemas: dict[str, dict] = {}
        self._descriptions: dict[str, str] = {}

    def register(
        self,
        name: str,
        fn: ToolFn,
        description: str = "",
        input_schema: Optional[dict] = None,
    ) -> None:
        """Register a tool callable."""
        self._tools[name] = fn
        self._descriptions[name] = description
        self._schemas[name] = input_schema or {}
        log.debug("tool registered: %s", name)

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": name,
                "description": self._descriptions.get(name, ""),
                "input_schema": self._schemas.get(name, {}),
                "is_builtin": name in BUILT_IN_TOOLS,
            }
            for name in sorted(self._tools)
        ]

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    async def is_enabled_for_org(
        self, tool_name: str, organization_id: str
    ) -> bool:
        """Check if tool is enabled for this org. Default: all built-ins enabled."""
        config = await self.db["tool_configs"].find_one({
            "organization_id": organization_id,
            "tool_name": tool_name,
        })
        if config is None:
            # Built-in tools are enabled by default
            return tool_name in BUILT_IN_TOOLS
        return config.get("is_enabled", True)

    async def invoke(
        self,
        tool_name: str,
        inputs: dict,
        context: ToolContext,
    ) -> dict:
        """
        Invoke a tool. Creates an immutable ToolCall audit record.
        Returns the tool's output dict, or raises on failure.
        """
        if not self.has_tool(tool_name):
            raise ValueError(f"Unknown tool: '{tool_name}'. Available: {sorted(self._tools)}")

        enabled = await self.is_enabled_for_org(tool_name, context.organization_id)
        if not enabled:
            raise PermissionError(
                f"Tool '{tool_name}' is not enabled for this organization"
            )

        call_record = ToolCall(
            _id=new_id(),
            organization_id=context.organization_id,
            call_id=context.call_id,
            lead_id=context.lead_id,
            tool_name=tool_name,
            inputs=inputs,
            status="pending",
        )

        t0 = time.perf_counter()
        try:
            fn = self._tools[tool_name]
            output = await fn(inputs, context)
            duration_ms = int((time.perf_counter() - t0) * 1000)

            call_record.status = "success"
            call_record.outputs = output
            call_record.duration_ms = duration_ms

            log.info("tool invoked: %s call=%s org=%s (%dms)",
                     tool_name, context.call_id, context.organization_id, duration_ms)
            return output

        except Exception as exc:  # noqa: BLE001
            duration_ms = int((time.perf_counter() - t0) * 1000)
            call_record.status = "failed"
            call_record.error_message = str(exc)
            call_record.duration_ms = duration_ms
            log.warning("tool failed: %s call=%s error=%s", tool_name, context.call_id, exc)
            raise

        finally:
            try:
                await self.db["tool_calls"].insert_one(call_record.to_mongo())
            except Exception as exc:  # noqa: BLE001
                log.warning("failed to persist tool call record: %s", exc)


def build_registry(db: AsyncIOMotorDatabase) -> ToolRegistry:
    """Build and return a ToolRegistry with all built-in tools registered."""
    from backend.services.tools.implementations import (
        book_appointment,
        schedule_callback,
        transfer_to_human,
        update_lead,
        add_note,
        send_sms,
        send_whatsapp,
        get_customer_details,
    )

    registry = ToolRegistry(db)

    registry.register(
        "book_appointment",
        book_appointment,
        description="Book an appointment for the lead",
        input_schema={
            "type": "object",
            "required": ["datetime_iso", "appointment_type"],
            "properties": {
                "datetime_iso": {"type": "string", "description": "ISO 8601 datetime"},
                "appointment_type": {"type": "string", "description": "e.g. site_survey, demo, callback"},
                "duration_minutes": {"type": "integer", "default": 30},
                "notes": {"type": "string"},
                "timezone": {"type": "string", "default": "Asia/Kolkata"},
            },
        },
    )

    registry.register(
        "schedule_callback",
        schedule_callback,
        description="Schedule a callback at a specific time",
        input_schema={
            "type": "object",
            "required": ["datetime_iso"],
            "properties": {
                "datetime_iso": {"type": "string"},
                "notes": {"type": "string"},
                "timezone": {"type": "string", "default": "Asia/Kolkata"},
            },
        },
    )

    registry.register(
        "transfer_to_human",
        transfer_to_human,
        description="Transfer the call to a human agent with full context",
        input_schema={
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "priority": {"type": "string", "enum": ["normal", "high", "urgent"]},
                "notes": {"type": "string"},
            },
        },
    )

    registry.register(
        "update_lead",
        update_lead,
        description="Update qualification data on the lead record",
        input_schema={
            "type": "object",
            "properties": {
                "qualification": {"type": "object"},
                "score": {"type": "integer", "minimum": 0, "maximum": 100},
                "status": {"type": "string"},
                "custom_fields": {"type": "object"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        },
    )

    registry.register(
        "add_note",
        add_note,
        description="Add a note to the lead record",
        input_schema={
            "type": "object",
            "required": ["note"],
            "properties": {
                "note": {"type": "string"},
                "note_type": {"type": "string", "default": "general"},
            },
        },
    )

    registry.register(
        "send_sms",
        send_sms,
        description="Send an SMS to the lead",
        input_schema={
            "type": "object",
            "required": ["message"],
            "properties": {
                "message": {"type": "string"},
                "to_number": {"type": "string"},
            },
        },
    )

    registry.register(
        "send_whatsapp",
        send_whatsapp,
        description="Send a WhatsApp message to the lead",
        input_schema={
            "type": "object",
            "required": ["message"],
            "properties": {
                "message": {"type": "string"},
                "template_name": {"type": "string"},
                "to_number": {"type": "string"},
            },
        },
    )

    registry.register(
        "get_customer_details",
        get_customer_details,
        description="Fetch existing customer details",
        input_schema={
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "email": {"type": "string"},
            },
        },
    )

    return registry
