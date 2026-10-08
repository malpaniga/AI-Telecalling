"""M17 tests — Tools + Human Handoff.

Tests:
1.  All 8 built-in tools registered in registry
2.  Registry.list_tools() returns all tools with schemas
3.  Tool invocation creates immutable ToolCall audit record
4.  Unknown tool raises ValueError
5.  Disabled tool raises PermissionError
6.  book_appointment creates appointment record and updates lead
7.  schedule_callback updates lead next_contact_at
8.  transfer_to_human packages complete context (lead + conversation + slots)
9.  update_lead updates qualification/score/status
10. add_note creates note record
11. send_sms / send_whatsapp queue message records
12. get_customer_details returns lead info
13. HandoffService.initiate_transfer creates transfer record with context
14. Transfer context includes: lead, conversation, stage, slots, trigger, recommendation
15. Transfer trigger classification covers all required reasons
16. Complete transfer updates status
17. Tool implementations are generic (no solar/business-specific code)
"""

import asyncio
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _mongomock_available():
    try:
        import mongomock_motor
        return True
    except ImportError:
        return False


SKIP = pytest.mark.skipif(not _mongomock_available(), reason="mongomock_motor not installed")


def _get_mock_db():
    import mongomock_motor
    return mongomock_motor.AsyncMongoMockClient()["test"]


def _make_context(db, call_id="call-t1", org_id="org-t1", lead_id=None,
                  call_state=None):
    from backend.services.tools.registry import ToolContext
    return ToolContext(
        db=db,
        call_id=call_id,
        organization_id=org_id,
        lead_id=lead_id,
        call_state=call_state or {"stage": "qualification", "slots": {}, "flags": {},
                                   "messages": []},
    )


# ---------------------------------------------------------------------------
# Test: Tool Registry
# ---------------------------------------------------------------------------
@SKIP
class TestToolRegistry:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_all_builtin_tools_registered(self):
        from backend.models.tool import BUILT_IN_TOOLS
        from backend.services.tools.registry import build_registry
        async def _t():
            registry = build_registry(self.db)
            for tool in BUILT_IN_TOOLS:
                assert registry.has_tool(tool), f"Tool '{tool}' not registered"
        run(_t())

    def test_list_tools_returns_all(self):
        from backend.services.tools.registry import build_registry
        from backend.models.tool import BUILT_IN_TOOLS
        async def _t():
            registry = build_registry(self.db)
            tools = registry.list_tools()
            names = {t["name"] for t in tools}
            assert BUILT_IN_TOOLS.issubset(names)
            for t in tools:
                assert "name" in t
                assert "description" in t
                assert "input_schema" in t
        run(_t())

    def test_unknown_tool_raises(self):
        from backend.services.tools.registry import build_registry
        async def _t():
            registry = build_registry(self.db)
            ctx = _make_context(self.db)
            with pytest.raises(ValueError, match="Unknown tool"):
                await registry.invoke("nonexistent_tool", {}, ctx)
        run(_t())

    def test_disabled_tool_raises(self):
        from backend.services.tools.registry import build_registry
        async def _t():
            # Disable add_note for this org
            await self.db["tool_configs"].insert_one({
                "_id": "tc-1",
                "organization_id": "org-disabled",
                "tool_name": "add_note",
                "is_enabled": False,
            })
            registry = build_registry(self.db)
            ctx = _make_context(self.db, org_id="org-disabled")
            with pytest.raises(PermissionError, match="not enabled"):
                await registry.invoke("add_note", {"note": "test"}, ctx)
        run(_t())

    def test_invocation_creates_audit_record(self):
        from backend.services.tools.registry import build_registry
        async def _t():
            registry = build_registry(self.db)
            ctx = _make_context(self.db, org_id="org-audit")
            # Use add_note (simple, no side effects needed)
            await registry.invoke("add_note", {"note": "audit test"}, ctx)
            # Check audit record was created
            record = await self.db["tool_calls"].find_one({
                "tool_name": "add_note",
                "call_id": "call-t1",
            })
            assert record is not None
            assert record["status"] == "success"
            assert record["inputs"]["note"] == "audit test"
        run(_t())

    def test_failed_invocation_recorded_as_failed(self):
        from backend.services.tools.registry import build_registry
        async def _t():
            registry = build_registry(self.db)
            ctx = _make_context(self.db)
            # add_note with empty note raises
            try:
                await registry.invoke("add_note", {"note": ""}, ctx)
            except ValueError:
                pass
            record = await self.db["tool_calls"].find_one({
                "tool_name": "add_note",
                "call_id": "call-t1",
                "status": "failed",
            })
            assert record is not None
            assert record["error_message"] is not None
        run(_t())

    def test_tool_enabled_by_default_for_builtins(self):
        from backend.services.tools.registry import build_registry
        async def _t():
            registry = build_registry(self.db)
            # No config entry → built-ins enabled by default
            assert await registry.is_enabled_for_org("add_note", "org-new") is True
            assert await registry.is_enabled_for_org("transfer_to_human", "org-new") is True
        run(_t())


# ---------------------------------------------------------------------------
# Test: Individual tool implementations
# ---------------------------------------------------------------------------
@SKIP
class TestBookAppointment:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_book_appointment_creates_record(self):
        from backend.services.tools.implementations import book_appointment
        async def _t():
            ctx = _make_context(self.db, lead_id="lead-appt-1")
            # Insert lead
            await self.db["leads"].insert_one({
                "_id": "lead-appt-1", "organization_id": "org-t1",
                "phone": "+919001000001", "status": "new",
            })
            result = await book_appointment(
                {"datetime_iso": "2027-01-15T10:00:00+05:30",
                 "appointment_type": "site_survey"},
                ctx,
            )
            assert result["status"] == "success"
            assert "appointment_id" in result
            appt = await self.db["appointments"].find_one({"_id": result["appointment_id"]})
            assert appt is not None
            assert appt["appointment_type"] == "site_survey"
        run(_t())

    def test_book_appointment_missing_datetime_raises(self):
        from backend.services.tools.implementations import book_appointment
        async def _t():
            ctx = _make_context(self.db)
            with pytest.raises(ValueError, match="datetime_iso"):
                await book_appointment({"appointment_type": "demo"}, ctx)
        run(_t())

    def test_book_appointment_updates_lead_status(self):
        from backend.services.tools.implementations import book_appointment
        async def _t():
            await self.db["leads"].insert_one({
                "_id": "lead-appt-2", "organization_id": "org-t1",
                "phone": "+919001000002", "status": "new",
            })
            ctx = _make_context(self.db, lead_id="lead-appt-2")
            await book_appointment(
                {"datetime_iso": "2027-01-15T10:00:00+05:30",
                 "appointment_type": "site_survey"},
                ctx,
            )
            lead = await self.db["leads"].find_one({"_id": "lead-appt-2"})
            assert lead["status"] == "qualified"
        run(_t())


@SKIP
class TestScheduleCallback:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_schedule_callback(self):
        from backend.services.tools.implementations import schedule_callback
        async def _t():
            await self.db["leads"].insert_one({
                "_id": "lead-cb-1", "organization_id": "org-t1",
                "phone": "+919001000010", "status": "new",
            })
            ctx = _make_context(self.db, lead_id="lead-cb-1")
            result = await schedule_callback(
                {"datetime_iso": "2027-01-16T14:00:00+05:30"}, ctx
            )
            assert result["status"] == "success"
            lead = await self.db["leads"].find_one({"_id": "lead-cb-1"})
            assert lead["status"] == "callback"
            assert lead["next_contact_at"] is not None
        run(_t())

    def test_schedule_callback_missing_datetime(self):
        from backend.services.tools.implementations import schedule_callback
        async def _t():
            ctx = _make_context(self.db)
            with pytest.raises(ValueError, match="datetime_iso"):
                await schedule_callback({}, ctx)
        run(_t())


@SKIP
class TestTransferToHuman:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_transfer_creates_record(self):
        from backend.services.tools.implementations import transfer_to_human
        async def _t():
            await self.db["leads"].insert_one({
                "_id": "lead-tr-1", "organization_id": "org-t1",
                "phone": "+919001000020", "name": "John",
                "status": "new", "qualification": {"budget": "50L"},
                "score": 75,
            })
            call_state = {
                "stage": "objection",
                "slots": {"budget": "50L", "city": "Mumbai"},
                "flags": {"raised_objection": True},
                "messages": [{"role": "user", "content": "I need to talk to someone"}],
            }
            ctx = _make_context(self.db, lead_id="lead-tr-1", call_state=call_state)
            result = await transfer_to_human(
                {"reason": "Customer requested human", "priority": "high"},
                ctx,
            )
            assert result["status"] == "success"
            assert "transfer_id" in result
            assert "context_package" in result
        run(_t())

    def test_transfer_context_includes_lead(self):
        from backend.services.tools.implementations import transfer_to_human
        async def _t():
            await self.db["leads"].insert_one({
                "_id": "lead-tr-2", "organization_id": "org-t1",
                "phone": "+919001000021", "name": "Alice",
                "status": "new", "qualification": {"interest": "high"},
                "score": 80,
            })
            ctx = _make_context(self.db, lead_id="lead-tr-2")
            result = await transfer_to_human({"reason": "test"}, ctx)
            pkg = result["context_package"]
            assert pkg["lead"]["name"] == "Alice"
            assert pkg["lead"]["score"] == 80
            assert pkg["lead"]["qualification"]["interest"] == "high"
        run(_t())

    def test_transfer_context_includes_conversation(self):
        from backend.services.tools.implementations import transfer_to_human
        async def _t():
            call_state = {
                "stage": "objection",
                "slots": {"budget": "90L", "city": "Pune"},
                "flags": {},
                "messages": [{"role": "user", "content": "hi"}] * 5,
            }
            ctx = _make_context(self.db, call_state=call_state)
            result = await transfer_to_human({"reason": "test"}, ctx)
            pkg = result["context_package"]
            assert pkg["conversation"]["stage"] == "objection"
            assert pkg["conversation"]["slots"]["budget"] == "90L"
            # Either "turns" or "message_count" key is acceptable
            turn_count = pkg["conversation"].get("turns") or pkg["conversation"].get("message_count")
            assert turn_count == 5
        run(_t())

    def test_transfer_is_generic_no_business_logic(self):
        """transfer_to_human must not contain business-specific logic."""
        import inspect
        from backend.services.tools import implementations
        source = inspect.getsource(implementations.transfer_to_human)
        assert "solar" not in source.lower()
        assert "real estate" not in source.lower()
        assert "elevenlabs" not in source.lower()


@SKIP
class TestUpdateLead:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_update_lead_qualification(self):
        from backend.services.tools.implementations import update_lead
        async def _t():
            await self.db["leads"].insert_one({
                "_id": "lead-ul-1", "organization_id": "org-t1",
                "phone": "+919001000030", "status": "new",
                "qualification": {}, "score": 0,
            })
            ctx = _make_context(self.db, lead_id="lead-ul-1")
            result = await update_lead(
                {"qualification": {"budget": "50L", "city": "Delhi"}, "score": 70},
                ctx,
            )
            assert result["status"] == "success"
            lead = await self.db["leads"].find_one({"_id": "lead-ul-1"})
            assert lead["qualification"]["budget"] == "50L"
            assert lead["score"] == 70
        run(_t())

    def test_update_lead_invalid_score_raises(self):
        from backend.services.tools.implementations import update_lead
        async def _t():
            ctx = _make_context(self.db, lead_id="lead-ul-2")
            with pytest.raises(ValueError, match="score"):
                await update_lead({"score": 150}, ctx)
        run(_t())

    def test_update_lead_without_lead_id_raises(self):
        from backend.services.tools.implementations import update_lead
        async def _t():
            ctx = _make_context(self.db, lead_id=None)
            with pytest.raises(ValueError, match="lead_id"):
                await update_lead({"score": 50}, ctx)
        run(_t())


@SKIP
class TestAddNote:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_add_note_creates_record(self):
        from backend.services.tools.implementations import add_note
        async def _t():
            ctx = _make_context(self.db)
            result = await add_note(
                {"note": "Customer very interested, follow up Monday",
                 "note_type": "follow_up"},
                ctx,
            )
            assert result["status"] == "success"
            note = await self.db["lead_notes"].find_one({"_id": result["note_id"]})
            assert note["note"] == "Customer very interested, follow up Monday"
            assert note["note_type"] == "follow_up"
        run(_t())

    def test_add_note_empty_raises(self):
        from backend.services.tools.implementations import add_note
        async def _t():
            ctx = _make_context(self.db)
            with pytest.raises(ValueError, match="empty"):
                await add_note({"note": ""}, ctx)
        run(_t())


@SKIP
class TestMessaging:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_send_sms_queues_message(self):
        from backend.services.tools.implementations import send_sms
        async def _t():
            ctx = _make_context(self.db)
            result = await send_sms(
                {"message": "Thank you for your interest", "to_number": "+919001000050"},
                ctx,
            )
            assert result["status"] == "success"
            assert result["channel"] == "sms"
            msg = await self.db["outbound_messages"].find_one({"_id": result["message_id"]})
            assert msg["message"] == "Thank you for your interest"
            assert msg["channel"] == "sms"
        run(_t())

    def test_send_whatsapp_queues_message(self):
        from backend.services.tools.implementations import send_whatsapp
        async def _t():
            ctx = _make_context(self.db)
            result = await send_whatsapp(
                {"message": "Your appointment is confirmed", "to_number": "+919001000051"},
                ctx,
            )
            assert result["status"] == "success"
            assert result["channel"] == "whatsapp"
        run(_t())

    def test_send_sms_no_number_raises(self):
        from backend.services.tools.implementations import send_sms
        async def _t():
            ctx = _make_context(self.db, lead_id=None)  # no lead, no number in inputs
            with pytest.raises(ValueError, match="phone number"):
                await send_sms({"message": "test"}, ctx)
        run(_t())


# ---------------------------------------------------------------------------
# Test: HandoffService
# ---------------------------------------------------------------------------
@SKIP
class TestHandoffService:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_initiate_transfer_creates_record(self):
        from backend.services.handoff_service import HandoffService
        async def _t():
            svc = HandoffService(self.db)
            result = await svc.initiate_transfer(
                call_id="call-hf-1",
                organization_id="org-hf",
                trigger="caller_request",
                priority="high",
            )
            assert result["status"] == "initiated"
            assert "transfer_id" in result
            assert "context_package" in result
            doc = await self.db["call_transfers"].find_one({"_id": result["transfer_id"]})
            assert doc is not None
            assert doc["trigger"] == "caller_request"
            assert doc["priority"] == "high"
        run(_t())

    def test_transfer_context_includes_lead_and_conversation(self):
        from backend.services.handoff_service import HandoffService
        async def _t():
            await self.db["leads"].insert_one({
                "_id": "lead-hf-1", "organization_id": "org-hf",
                "phone": "+919001000060", "name": "Bob",
                "status": "new", "qualification": {"budget": "1cr"},
                "score": 85,
            })
            call_state = {
                "stage": "booking",
                "slots": {"budget": "1cr", "city": "Mumbai"},
                "flags": {"wants_to_book": True},
                "messages": [{"role": "user", "content": "Yes I want"}] * 3,
            }
            svc = HandoffService(self.db)
            result = await svc.initiate_transfer(
                call_id="call-hf-2",
                organization_id="org-hf",
                trigger="high_value_lead",
                lead_id="lead-hf-1",
                call_state=call_state,
            )
            pkg = result["context_package"]
            assert pkg["lead"]["name"] == "Bob"
            assert pkg["lead"]["score"] == 85
            assert pkg["conversation"]["stage"] == "booking"
            assert pkg["conversation"]["slots"]["budget"] == "1cr"
            assert pkg["conversation"]["turns"] == 3
            assert "recommended_action" in pkg
            assert "high" in pkg["recommended_action"].lower() or "value" in pkg["recommended_action"].lower()
        run(_t())

    def test_all_triggers_valid(self):
        from backend.services.handoff_service import TRANSFER_TRIGGERS
        required = {
            "caller_request", "low_confidence", "complex_objection",
            "anger", "high_value_lead", "sensitive_situation",
            "configured_rule", "repeated_misunderstanding",
        }
        assert required.issubset(TRANSFER_TRIGGERS)

    def test_complete_transfer(self):
        from backend.services.handoff_service import HandoffService
        async def _t():
            svc = HandoffService(self.db)
            result = await svc.initiate_transfer(
                call_id="call-hf-3",
                organization_id="org-hf",
                trigger="manual",
            )
            tid = result["transfer_id"]
            ok = await svc.complete_transfer(tid, "org-hf", assigned_to="agent-001")
            assert ok
            doc = await self.db["call_transfers"].find_one({"_id": tid})
            assert doc["status"] == "completed"
            assert doc["assigned_to"] == "agent-001"
        run(_t())

    def test_recommended_action_is_specific(self):
        from backend.services.handoff_service import _recommended_action
        action = _recommended_action("anger", {"name": "Alice", "score": 50})
        assert "alice" in action.lower() or "frustration" in action.lower() or "anger" in action.lower()

    def test_tools_are_generic_no_business_branches(self):
        """Tool implementations must not contain business-specific branches (if/else on business type)."""
        import inspect
        from backend.services.tools import implementations
        source = inspect.getsource(implementations)
        # These should not appear as code logic — comments mentioning them as negative examples are ok
        # Check for conditional branching on business type, not doc comments
        import re
        # No if/elif blocks checking for solar/real-estate as a condition
        assert not re.search(r'if.*solar', source, re.IGNORECASE)
        assert not re.search(r'if.*real.estate', source, re.IGNORECASE)
        # Provider names should not appear as conditional checks
        assert not re.search(r'if provider', source, re.IGNORECASE)
        assert "elevenlabs" not in source.lower()
        assert "twilio" not in source.lower()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
