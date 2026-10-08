"""Human handoff service.

Packages complete call context for transfer to a human agent.
Called when transfer_to_human tool is invoked or triggered by rules.

Transfer triggers (from spec):
  - caller requests human
  - low confidence
  - complex objection
  - anger
  - high-value lead
  - sensitive situation
  - configured rule
  - repeated misunderstanding

Context package includes:
  - lead details (qualification, score, history)
  - conversation summary
  - transcript excerpt
  - call state (stage, slots)
  - recommended action
"""

import logging
from datetime import datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.base import new_id, utcnow

log = logging.getLogger("service.handoff")

TRANSFER_TRIGGERS = {
    "caller_request",
    "low_confidence",
    "complex_objection",
    "anger",
    "high_value_lead",
    "sensitive_situation",
    "configured_rule",
    "repeated_misunderstanding",
    "max_attempts_reached",
    "manual",
}


class HandoffService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def initiate_transfer(
        self,
        call_id: str,
        organization_id: str,
        trigger: str,
        lead_id: Optional[str] = None,
        call_state: Optional[dict] = None,
        transcript_excerpt: Optional[list] = None,
        priority: str = "normal",
        notes: str = "",
    ) -> dict:
        """
        Package call context and record a human transfer request.

        Returns the complete context package that should be shown to the
        human agent picking up the call.
        """
        now = utcnow()

        if trigger not in TRANSFER_TRIGGERS:
            log.warning("unknown transfer trigger: %s (proceeding anyway)", trigger)

        # Fetch lead details
        lead_context: dict = {}
        if lead_id:
            lead = await self.db["leads"].find_one({"_id": lead_id})
            if lead:
                lead_context = {
                    "id": lead_id,
                    "name": lead.get("name"),
                    "phone": lead.get("phone"),
                    "email": lead.get("email"),
                    "status": lead.get("status"),
                    "qualification": lead.get("qualification", {}),
                    "score": lead.get("score", 0),
                    "custom_fields": lead.get("custom_fields", {}),
                    "tags": lead.get("tags", []),
                    "attempts": lead.get("attempts", 0),
                }

        # Build conversation context
        conversation_context: dict = {}
        if call_state:
            conversation_context = {
                "stage": call_state.get("stage", "unknown"),
                "slots": call_state.get("slots", {}),
                "flags": call_state.get("flags", {}),
                "turns": len(call_state.get("messages", [])),
            }

        # Recommended action based on trigger
        recommended_action = _recommended_action(trigger, lead_context)

        context_package = {
            "call_id": call_id,
            "organization_id": organization_id,
            "trigger": trigger,
            "priority": priority,
            "notes": notes,
            "transferred_at": now.isoformat(),
            "lead": lead_context,
            "conversation": conversation_context,
            "transcript_excerpt": transcript_excerpt or [],
            "recommended_action": recommended_action,
        }

        # Store transfer record
        transfer_doc = {
            "_id": new_id(),
            "organization_id": organization_id,
            "call_id": call_id,
            "lead_id": lead_id,
            "trigger": trigger,
            "priority": priority,
            "notes": notes,
            "context_package": context_package,
            "status": "pending",
            "created_at": now,
        }
        await self.db["call_transfers"].insert_one(transfer_doc)

        # Update lead status to "contacted" (human taking over)
        if lead_id:
            await self.db["leads"].update_one(
                {"_id": lead_id, "organization_id": organization_id},
                {"$set": {"status": "contacted", "updated_at": now}},
            )

        log.info("handoff initiated call=%s trigger=%s priority=%s",
                 call_id, trigger, priority)

        return {
            "transfer_id": transfer_doc["_id"],
            "status": "initiated",
            "priority": priority,
            "context_package": context_package,
        }

    async def complete_transfer(
        self,
        transfer_id: str,
        organization_id: str,
        assigned_to: Optional[str] = None,
        outcome: str = "completed",
    ) -> bool:
        result = await self.db["call_transfers"].update_one(
            {"_id": transfer_id, "organization_id": organization_id},
            {
                "$set": {
                    "status": outcome,
                    "assigned_to": assigned_to,
                    "completed_at": utcnow(),
                }
            },
        )
        return result.modified_count > 0

    async def get_pending_transfers(
        self, organization_id: str, limit: int = 50
    ) -> list[dict]:
        docs = await self.db["call_transfers"].find(
            {"organization_id": organization_id, "status": "pending"}
        ).sort("created_at", -1).limit(limit).to_list(length=limit)
        return docs


def _recommended_action(trigger: str, lead: dict) -> str:
    """Generate a recommended action string based on transfer trigger."""
    score = lead.get("score", 0)
    name = lead.get("name", "the lead")

    actions = {
        "caller_request": f"Lead {name} requested to speak with a human. Continue qualification.",
        "low_confidence": "AI had low confidence — review conversation and clarify.",
        "complex_objection": "Complex objection raised — experienced agent needed.",
        "anger": f"Lead {name} expressed frustration. De-escalate and listen.",
        "high_value_lead": f"High-value lead (score {score}). Prioritize engagement.",
        "sensitive_situation": "Sensitive situation detected. Handle with care.",
        "configured_rule": "Transfer triggered by configured campaign rule.",
        "repeated_misunderstanding": "Repeated misunderstanding — clarify requirements.",
        "max_attempts_reached": "Maximum AI attempts reached. Human follow-up needed.",
        "manual": "Manual transfer initiated by system.",
    }
    return actions.get(trigger, f"Transfer trigger: {trigger}. Review conversation context.")
