"""Runtime variable resolution for live call sessions.

Hierarchically merges:
1. Agent default input_variables
2. Master Lead attributes (name, phone, email, and custom_fields)
3. Campaign-scoped overrides (CampaignLead.custom_fields)
"""

import logging
from typing import Any, Optional

log = logging.getLogger("telephony.variables")


async def resolve_call_variables(
    db: Any,
    call_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    default_variables: Optional[dict[str, Any]] = None,
) -> dict[str, str]:
    """Resolve hierarchical call variables for CallSession prompt interpolation."""
    runtime_vars: dict[str, str] = {}
    if default_variables:
        for k, v in default_variables.items():
            if v is not None:
                runtime_vars[k] = str(v)

    if not db or not call_id:
        return runtime_vars

    try:
        call_doc = await db.calls.find_one({"_id": call_id})
        if not call_doc:
            return runtime_vars

        lead_id = call_doc.get("lead_id")
        campaign_id = call_doc.get("campaign_id")

        # 1. If agent version has default variables and not provided
        if not default_variables:
            target_agent_id = agent_id or call_doc.get("agent_id")
            if target_agent_id:
                agent_doc = await db.agents.find_one({"_id": target_agent_id})
                if agent_doc:
                    vid = agent_doc.get("active_version_id")
                    ver_doc = None
                    if vid:
                        ver_doc = await db.agent_versions.find_one({"_id": vid})
                    if not ver_doc:
                        ver_doc = await db.agent_versions.find_one(
                            {"agent_id": target_agent_id}, sort=[("version", -1)]
                        )
                    if ver_doc:
                        cfg = ver_doc.get("configuration") or {}
                        input_vars = cfg.get("input_variables") or {}
                        for k, v in input_vars.items():
                            if v is not None:
                                runtime_vars[k] = str(v)

        # 2. Master Lead attributes & custom_fields
        if lead_id:
            lead_doc = await db.leads.find_one({"_id": lead_id})
            if lead_doc:
                name = lead_doc.get("name")
                phone = lead_doc.get("phone")
                email = lead_doc.get("email")

                if name:
                    runtime_vars["name"] = name
                    runtime_vars["user_name"] = name
                    runtime_vars["customer_name"] = name
                    runtime_vars["lead_name"] = name
                if phone:
                    runtime_vars["phone"] = phone
                    runtime_vars["phone_number"] = phone
                if email:
                    runtime_vars["email"] = email

                for k, v in (lead_doc.get("custom_fields") or {}).items():
                    if v is not None:
                        str_val = str(v)
                        runtime_vars[k] = str_val
                        norm_k = k.strip().lower().replace(" ", "_")
                        runtime_vars[norm_k] = str_val

        # 3. CampaignLead overrides
        if campaign_id and lead_id:
            camp_lead = await db.campaign_leads.find_one(
                {"campaign_id": campaign_id, "lead_id": lead_id}
            )
            if camp_lead:
                for k, v in (camp_lead.get("custom_fields") or {}).items():
                    if v is not None:
                        str_val = str(v)
                        runtime_vars[k] = str_val
                        norm_k = k.strip().lower().replace(" ", "_")
                        runtime_vars[norm_k] = str_val
    except Exception as exc:
        log.warning("error resolving call variables for call=%s: %s", call_id, exc)

    return runtime_vars
