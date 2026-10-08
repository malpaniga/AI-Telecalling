"""Built-in tool implementations.

Every tool:
  - Receives (inputs: dict, context: ToolContext)
  - Returns a dict with at minimum {"status": "success"|"error", ...}
  - Is generic — no solar/real-estate specific logic

Transfer to human is the most critical: it packages the complete call context
so the human agent receives full lead info, qualification, transcript summary.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from backend.models.base import new_id, utcnow
from backend.services.tools.registry import ToolContext

log = logging.getLogger("tools.impl")


async def book_appointment(inputs: dict, ctx: ToolContext) -> dict:
    """Create an appointment record for this lead."""
    from backend.models.base import new_id, utcnow
    now = utcnow()

    datetime_iso = inputs.get("datetime_iso")
    appointment_type = inputs.get("appointment_type", "general")
    duration_minutes = inputs.get("duration_minutes", 30)
    notes = inputs.get("notes", "")
    timezone = inputs.get("timezone", "Asia/Kolkata")

    if not datetime_iso:
        raise ValueError("datetime_iso is required for book_appointment")

    # Parse the datetime
    try:
        from datetime import timezone as _tz
        scheduled_at = datetime.fromisoformat(datetime_iso.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid datetime_iso format: {exc}") from exc

    appointment = {
        "_id": new_id(),
        "organization_id": ctx.organization_id,
        "call_id": ctx.call_id,
        "lead_id": ctx.lead_id,
        "appointment_type": appointment_type,
        "scheduled_at": scheduled_at,
        "duration_minutes": duration_minutes,
        "timezone": timezone,
        "notes": notes,
        "status": "scheduled",
        "created_at": now,
        "updated_at": now,
    }

    await ctx.db["appointments"].insert_one(appointment)

    # Update lead status if we have a lead
    if ctx.lead_id:
        await ctx.db["leads"].update_one(
            {"_id": ctx.lead_id, "organization_id": ctx.organization_id},
            {"$set": {"status": "qualified", "updated_at": now}},
        )

    log.info("appointment booked call=%s lead=%s type=%s at=%s",
             ctx.call_id, ctx.lead_id, appointment_type, datetime_iso)

    return {
        "status": "success",
        "appointment_id": appointment["_id"],
        "appointment_type": appointment_type,
        "scheduled_at": datetime_iso,
        "message": f"Appointment booked for {datetime_iso}",
    }


async def schedule_callback(inputs: dict, ctx: ToolContext) -> dict:
    """Schedule a callback for the lead."""
    now = utcnow()
    datetime_iso = inputs.get("datetime_iso")
    notes = inputs.get("notes", "")
    timezone = inputs.get("timezone", "Asia/Kolkata")

    if not datetime_iso:
        raise ValueError("datetime_iso is required for schedule_callback")

    try:
        callback_at = datetime.fromisoformat(datetime_iso.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid datetime_iso: {exc}") from exc

    # Update lead with callback time
    if ctx.lead_id:
        await ctx.db["leads"].update_one(
            {"_id": ctx.lead_id, "organization_id": ctx.organization_id},
            {
                "$set": {
                    "status": "callback",
                    "next_contact_at": callback_at,
                    "updated_at": now,
                }
            },
        )

    log.info("callback scheduled call=%s lead=%s at=%s", ctx.call_id, ctx.lead_id, datetime_iso)

    return {
        "status": "success",
        "callback_at": datetime_iso,
        "timezone": timezone,
        "message": f"Callback scheduled for {datetime_iso}",
    }


async def transfer_to_human(inputs: dict, ctx: ToolContext) -> dict:
    """
    Transfer the call to a human agent with complete context.

    Context package passed to human:
      - Lead details (phone, name, email, qualification)
      - Call summary (stage, slots, conversation history excerpt)
      - Reason for transfer
      - Priority
    """
    reason = inputs.get("reason", "Customer requested human agent")
    priority = inputs.get("priority", "normal")
    notes = inputs.get("notes", "")
    now = utcnow()

    # Build context package for the human agent
    context_package: dict[str, Any] = {
        "transfer_reason": reason,
        "priority": priority,
        "notes": notes,
        "call_id": ctx.call_id,
        "organization_id": ctx.organization_id,
        "transferred_at": now.isoformat(),
    }

    # Fetch lead details
    lead = None
    if ctx.lead_id:
        lead = await ctx.db["leads"].find_one({"_id": ctx.lead_id})
        if lead:
            context_package["lead"] = {
                "id": ctx.lead_id,
                "name": lead.get("name"),
                "phone": lead.get("phone"),
                "email": lead.get("email"),
                "status": lead.get("status"),
                "qualification": lead.get("qualification", {}),
                "score": lead.get("score", 0),
                "custom_fields": lead.get("custom_fields", {}),
                "attempts": lead.get("attempts", 0),
            }

    # Include call state (slots, stage) from conversation context
    if ctx.call_state:
        context_package["conversation"] = {
            "stage": ctx.call_state.get("stage", "unknown"),
            "slots": ctx.call_state.get("slots", {}),
            "flags": ctx.call_state.get("flags", {}),
            "message_count": len(ctx.call_state.get("messages", [])),
        }

    # Record transfer event
    transfer_record = {
        "_id": new_id(),
        "organization_id": ctx.organization_id,
        "call_id": ctx.call_id,
        "lead_id": ctx.lead_id,
        "transfer_type": "human",
        "reason": reason,
        "priority": priority,
        "context_package": context_package,
        "status": "initiated",
        "created_at": now,
    }
    await ctx.db["call_transfers"].insert_one(transfer_record)

    # Update lead status
    if ctx.lead_id:
        await ctx.db["leads"].update_one(
            {"_id": ctx.lead_id, "organization_id": ctx.organization_id},
            {"$set": {"status": "contacted", "updated_at": now}},
        )

    log.info("transfer_to_human call=%s lead=%s reason=%s priority=%s",
             ctx.call_id, ctx.lead_id, reason, priority)

    return {
        "status": "success",
        "transfer_id": transfer_record["_id"],
        "priority": priority,
        "context_package": context_package,
        "message": f"Transferring to human agent. Reason: {reason}",
    }


async def update_lead(inputs: dict, ctx: ToolContext) -> dict:
    """Update lead qualification data."""
    if not ctx.lead_id:
        raise ValueError("No lead_id in context — cannot update lead")

    now = utcnow()
    updates: dict[str, Any] = {"updated_at": now}

    if "qualification" in inputs:
        updates["qualification"] = inputs["qualification"]
    if "score" in inputs:
        score = int(inputs["score"])
        if not 0 <= score <= 100:
            raise ValueError("score must be 0–100")
        updates["score"] = score
    if "status" in inputs:
        updates["status"] = inputs["status"]
    if "custom_fields" in inputs:
        updates["custom_fields"] = inputs["custom_fields"]
    if "tags" in inputs:
        updates["tags"] = list(inputs["tags"])

    if len(updates) <= 1:  # only updated_at
        return {"status": "success", "message": "No fields to update"}

    result = await ctx.db["leads"].update_one(
        {"_id": ctx.lead_id, "organization_id": ctx.organization_id},
        {"$set": updates},
    )

    log.info("update_lead call=%s lead=%s fields=%s",
             ctx.call_id, ctx.lead_id, list(updates.keys()))

    return {
        "status": "success",
        "updated_fields": list(updates.keys()),
        "modified": result.modified_count > 0,
    }


async def add_note(inputs: dict, ctx: ToolContext) -> dict:
    """Add a note to the lead record."""
    note = inputs.get("note", "").strip()
    if not note:
        raise ValueError("note cannot be empty")

    note_type = inputs.get("note_type", "general")
    now = utcnow()

    note_doc = {
        "_id": new_id(),
        "organization_id": ctx.organization_id,
        "call_id": ctx.call_id,
        "lead_id": ctx.lead_id,
        "note": note,
        "note_type": note_type,
        "created_at": now,
    }
    await ctx.db["lead_notes"].insert_one(note_doc)

    log.info("note added call=%s lead=%s type=%s", ctx.call_id, ctx.lead_id, note_type)

    return {
        "status": "success",
        "note_id": note_doc["_id"],
        "message": "Note added",
    }


async def send_sms(inputs: dict, ctx: ToolContext) -> dict:
    """Send an SMS to the lead (stub — provider integration in M8/M15)."""
    message = inputs.get("message", "").strip()
    if not message:
        raise ValueError("message is required for send_sms")

    # Determine recipient number
    to_number = inputs.get("to_number")
    if not to_number and ctx.lead_id:
        lead = await ctx.db["leads"].find_one({"_id": ctx.lead_id})
        to_number = lead.get("phone") if lead else None
    if not to_number:
        raise ValueError("No recipient phone number available")

    # In production: invoke SMS provider via M8 provider abstraction
    # For MVP: record the intent and return success
    now = utcnow()
    sms_doc = {
        "_id": new_id(),
        "organization_id": ctx.organization_id,
        "call_id": ctx.call_id,
        "lead_id": ctx.lead_id,
        "channel": "sms",
        "to_number": to_number,
        "message": message,
        "status": "queued",
        "created_at": now,
    }
    await ctx.db["outbound_messages"].insert_one(sms_doc)

    log.info("sms queued call=%s to=%s", ctx.call_id, to_number)

    return {
        "status": "success",
        "message_id": sms_doc["_id"],
        "to": to_number,
        "channel": "sms",
    }


async def send_whatsapp(inputs: dict, ctx: ToolContext) -> dict:
    """Send a WhatsApp message to the lead (stub)."""
    message = inputs.get("message", "").strip()
    template_name = inputs.get("template_name")
    if not message and not template_name:
        raise ValueError("message or template_name is required for send_whatsapp")

    to_number = inputs.get("to_number")
    if not to_number and ctx.lead_id:
        lead = await ctx.db["leads"].find_one({"_id": ctx.lead_id})
        to_number = lead.get("phone") if lead else None
    if not to_number:
        raise ValueError("No recipient phone number available")

    now = utcnow()
    wa_doc = {
        "_id": new_id(),
        "organization_id": ctx.organization_id,
        "call_id": ctx.call_id,
        "lead_id": ctx.lead_id,
        "channel": "whatsapp",
        "to_number": to_number,
        "message": message,
        "template_name": template_name,
        "status": "queued",
        "created_at": now,
    }
    await ctx.db["outbound_messages"].insert_one(wa_doc)

    log.info("whatsapp queued call=%s to=%s", ctx.call_id, to_number)

    return {
        "status": "success",
        "message_id": wa_doc["_id"],
        "to": to_number,
        "channel": "whatsapp",
    }


async def get_customer_details(inputs: dict, ctx: ToolContext) -> dict:
    """Fetch existing customer/lead record."""
    phone = inputs.get("phone")
    email = inputs.get("email")

    if not phone and not email and not ctx.lead_id:
        raise ValueError("phone, email, or lead context required")

    lead = None
    if ctx.lead_id:
        lead = await ctx.db["leads"].find_one({"_id": ctx.lead_id})
    elif phone:
        lead = await ctx.db["leads"].find_one({
            "phone": phone,
            "organization_id": ctx.organization_id,
        })
    elif email:
        lead = await ctx.db["leads"].find_one({
            "email": email,
            "organization_id": ctx.organization_id,
        })

    if not lead:
        return {"status": "not_found", "message": "No existing record found"}

    return {
        "status": "success",
        "lead_id": str(lead.get("_id")),
        "name": lead.get("name"),
        "phone": lead.get("phone"),
        "email": lead.get("email"),
        "status_label": lead.get("status"),
        "qualification": lead.get("qualification", {}),
        "score": lead.get("score", 0),
        "attempts": lead.get("attempts", 0),
        "custom_fields": lead.get("custom_fields", {}),
        "tags": lead.get("tags", []),
    }
