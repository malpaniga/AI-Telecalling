"""Call service — initiate, track, and finalize AI calls.

This service bridges the SaaS infrastructure (org, campaign, credits, leads)
with the existing transport-agnostic CallSession (the real-time AI call engine).

Flow:
  1. Validate: campaign running, credits available, lead valid, concurrency gate
  2. Reserve credits
  3. Create Call record in MongoDB
  4. Start CallSession (existing real-time pipeline)
  5. On completion: finalize Call record, settle credits, update lead/campaign

The CallSession itself is preserved from the original repo — we only adapt
the scaffolding around it, not the audio/VAD/STT/LLM/TTS pipeline.
"""

import logging
from statistics import mean
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.base import new_id, utcnow
from backend.models.call import CALL_OUTCOMES
from backend.repositories.call_repo import CallRepository
from backend.repositories.lead_repo import LeadRepository
from backend.repositories.campaign_repo import CampaignRepository

log = logging.getLogger("service.call")

# Default credit reservation per call: 5 minutes = 300 seconds
DEFAULT_RESERVE_CREDITS = 5


class CallService:
    def __init__(self, db: AsyncIOMotorDatabase, redis=None):
        self.db = db
        self._redis = redis
        self.call_repo = CallRepository(db)
        self.lead_repo = LeadRepository(db)
        self.campaign_repo = CampaignRepository(db)

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from backend.core.redis import get_redis
            return get_redis()
        except Exception:  # noqa: BLE001
            return None

    async def initiate_call(
        self,
        organization_id: str,
        to_number: str,
        from_number: str,
        campaign_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_version: Optional[int] = None,
        provider: str = "mock",
        reserve_credits: int = DEFAULT_RESERVE_CREDITS,
        slot_already_acquired: bool = False,
    ) -> dict:
        """
        Initiate an outbound call.
        1. Reserve credits
        2. Create call record
        3. Increment campaign active call counter
        Returns the call record.
        """
        # Look up phone number to verify assignment & provider
        phone_doc = None
        if from_number:
            from backend.repositories.phone_number_repo import PhoneNumberRepository
            pn_repo = PhoneNumberRepository(self.db)
            phone_doc = await pn_repo.find_by_number(from_number)
            if phone_doc:
                assigned_orgs = getattr(phone_doc, "assigned_org_ids", []) or []
                if phone_doc.organization_id != organization_id and organization_id not in assigned_orgs:
                    raise ValueError(f"Number {from_number} is not assigned to organization {organization_id}")
                if phone_doc.provider:
                    provider = phone_doc.provider

        # Reserve credits
        call_id = new_id()
        try:
            from backend.services.credit_service import CreditService
            credit_svc = CreditService(self.db, redis=self._get_redis())
            credit_result = await credit_svc.reserve(
                organization_id=organization_id,
                call_id=call_id,
                max_credits=reserve_credits,
            )
        except ValueError as exc:
            raise ValueError(f"Cannot start call: {exc}") from exc

        # Create call record
        call = await self.call_repo.create(
            call_id=call_id,
            organization_id=organization_id,
            to_number=to_number,
            from_number=from_number,
            campaign_id=campaign_id,
            lead_id=lead_id,
            agent_id=agent_id,
            agent_version=agent_version,
            provider=provider,
            credits_reserved=reserve_credits,
        )

        # Dispatch call via Vobiz telephony provider if configured
        if provider == "vobiz" and phone_doc:
            from backend.providers.telephony.vobiz import VobizTelephonyProvider
            from backend.config import settings
            base_public = (
                settings.public_base_url.rstrip("/")
                if getattr(settings, "public_base_url", None) and "ngrok" not in settings.public_base_url
                else "https://92.5.149.29.sslip.io"
            )
            call_lang = "en-IN"
            if agent_id:
                try:
                    agent_doc = await self.db.agents.find_one({"_id": agent_id})
                    if agent_doc:
                        active_vid = agent_doc.get("active_version_id")
                        ver_doc = None
                        if active_vid:
                            ver_doc = await self.db.agent_versions.find_one({"_id": active_vid})
                        if not ver_doc:
                            ver_doc = await self.db.agent_versions.find_one(
                                {"agent_id": agent_id}, sort=[("version", -1)]
                            )
                        if ver_doc:
                            cfg = ver_doc.get("configuration") or {}
                            call_lang = cfg.get("primary_language") or call_lang
                except Exception as e:
                    log.warning("could not resolve agent language: %s", e)

            answer_url = f"{base_public}/vobiz/voice?call_id={call.id}&agent_id={agent_id or ''}&lang={call_lang}"
            metadata = phone_doc.provider_metadata or {}
            auth_id = metadata.get("vobiz_auth_id")
            auth_token = metadata.get("vobiz_auth_token")

            if not auth_id or not auth_token:
                raise ValueError("Vobiz phone number is missing API credentials in provider_metadata")

            vobiz_provider = VobizTelephonyProvider()
            try:
                dispatch_res = await vobiz_provider.initiate_call(
                    to=to_number,
                    from_number=from_number,
                    auth_id=auth_id,
                    auth_token=auth_token,
                    url=answer_url,
                )
                await self.call_repo.update_by_id(call.id, {
                    "provider": "vobiz",
                    "provider_resource_id": dispatch_res.get("provider_resource_id"),
                })
            except Exception as exc:
                log.error("Failed to dispatch call %s via Vobiz: %s", call.id, exc)
                await self.call_repo.update_by_id(call.id, {
                    "status": "failed",
                    "error_message": str(exc),
                })
                try:
                    await credit_svc.release(
                        organization_id=organization_id,
                        call_id=call.id,
                    )
                except Exception as rel_exc:
                    log.warning("Failed releasing credits after dispatch failure: %s", rel_exc)
                err_msg = str(exc)
                if "answer_url parameter is not valid" in err_msg:
                    err_msg += (
                        " (Vobiz requires a publicly accessible HTTPS answer_url. "
                        "Please configure PUBLIC_BASE_URL in backend/.env with a public HTTPS domain or ngrok tunnel URL)."
                    )
                raise RuntimeError(f"Telephony dispatch failed: {err_msg}") from exc

        # Dispatch call via Plivo telephony provider if configured
        elif provider == "plivo" and phone_doc:
            from backend.providers.telephony.plivo import PlivoTelephonyProvider
            from backend.config import settings
            base_public = (
                settings.public_base_url.rstrip("/")
                if getattr(settings, "public_base_url", None) and "ngrok" not in settings.public_base_url
                else "https://92.5.149.29.sslip.io"
            )
            call_lang = "en-IN"
            if agent_id:
                try:
                    agent_doc = await self.db.agents.find_one({"_id": agent_id})
                    if agent_doc:
                        active_vid = agent_doc.get("active_version_id")
                        ver_doc = None
                        if active_vid:
                            ver_doc = await self.db.agent_versions.find_one({"_id": active_vid})
                        if not ver_doc:
                            ver_doc = await self.db.agent_versions.find_one(
                                {"agent_id": agent_id}, sort=[("version", -1)]
                            )
                        if ver_doc:
                            cfg = ver_doc.get("configuration") or {}
                            call_lang = cfg.get("primary_language") or call_lang
                except Exception as e:
                    log.warning("could not resolve agent language: %s", e)

            answer_url = f"{base_public}/plivo/voice?call_id={call.id}&agent_id={agent_id or ''}&lang={call_lang}"
            metadata = phone_doc.provider_metadata or {}
            auth_id = metadata.get("plivo_auth_id") or metadata.get("auth_id")
            auth_token = metadata.get("plivo_auth_token") or metadata.get("auth_token")

            if not auth_id or not auth_token:
                raise ValueError("Plivo phone number is missing API credentials in provider_metadata")

            plivo_provider = PlivoTelephonyProvider()
            try:
                dispatch_res = await plivo_provider.initiate_call(
                    to=to_number,
                    from_number=from_number,
                    auth_id=auth_id,
                    auth_token=auth_token,
                    url=answer_url,
                )
                await self.call_repo.update_by_id(call.id, {
                    "provider": "plivo",
                    "provider_resource_id": dispatch_res.get("provider_resource_id"),
                })
            except Exception as exc:
                log.error("Failed to dispatch call %s via Plivo: %s", call.id, exc)
                await self.call_repo.update_by_id(call.id, {
                    "status": "failed",
                    "error_message": str(exc),
                })
                try:
                    await credit_svc.release(
                        organization_id=organization_id,
                        call_id=call.id,
                    )
                except Exception as rel_exc:
                    log.warning("Failed releasing credits after dispatch failure: %s", rel_exc)
                err_msg = str(exc)
                if "answer_url parameter is not valid" in err_msg:
                    err_msg += (
                        " (Plivo requires a publicly accessible HTTPS answer_url. "
                        "Please configure PUBLIC_BASE_URL in backend/.env with a public HTTPS domain or ngrok tunnel URL)."
                    )
                raise RuntimeError(f"Telephony dispatch failed: {err_msg}") from exc

        # Increment campaign concurrency counter if not already acquired by caller
        if campaign_id and not slot_already_acquired:
            from backend.services.campaign_service import CampaignService
            camp_svc = CampaignService(self.db, redis=self._get_redis())
            await camp_svc.increment_active_calls(campaign_id)

        # Update lead status
        if lead_id:
            await self.lead_repo.update_status(lead_id, organization_id, "calling")
            await self.lead_repo.increment_attempts(lead_id, organization_id)

        log.info("call initiated id=%s org=%s to=%s campaign=%s",
                 call.id, organization_id, to_number, campaign_id)
        return {"call_id": call.id, "status": "initiating"}

    async def finalize_call(
        self,
        call_id: str,
        organization_id: str,
        status: str = "completed",
        outcome: Optional[str] = None,
        actual_credits: int = 0,
        avg_latency_ms: Optional[int] = None,
        turn_count: int = 0,
        score: int = 0,
        qualification: Optional[dict] = None,
        summary: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> dict:
        """
        Finalize a call after it ends.
        1. Settle credits
        2. Finalize call record
        3. Update lead status
        4. Decrement campaign concurrency counter
        5. Update campaign counters
        """
        call = await self.call_repo.get_for_org(call_id, organization_id)
        if call is None:
            raise ValueError(f"Call {call_id} not found")

        if call.status in ("completed", "cancelled", "failed"):
            log.info("call %s already in terminal status '%s'; skipping duplicate finalize", call_id, call.status)
            return {
                "call_id": call_id,
                "status": call.status,
                "outcome": call.outcome,
                "duration_s": call.duration_s,
                "credits_consumed": call.credits_consumed,
            }

        # Calculate duration
        duration_s = None
        if call.started_at:
            now = utcnow()
            started = call.started_at
            # Handle mongomock returning naive datetimes
            if started.tzinfo is None:
                from datetime import timezone as _tz
                started = started.replace(tzinfo=_tz.utc)
            ref = call.connected_at or started
            if ref.tzinfo is None:
                from datetime import timezone as _tz
                ref = ref.replace(tzinfo=_tz.utc)
            duration_s = max(0, int((now - ref).total_seconds()))

        # Settle credits
        actual_credits = actual_credits or (max(0, (duration_s + 59) // 60) if duration_s else 0)
        try:
            from backend.services.credit_service import CreditService
            credit_svc = CreditService(self.db, redis=self._get_redis())
            await credit_svc.settle(
                organization_id=organization_id,
                call_id=call_id,
                actual_credits=actual_credits,
                idempotency_key=f"settle:{call_id}",
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("credit settlement failed for call=%s: %s", call_id, exc)

        # Finalize call record
        await self.call_repo.finalize(
            call_id=call_id,
            organization_id=organization_id,
            status=status,
            outcome=outcome,
            duration_s=duration_s,
            avg_latency_ms=avg_latency_ms,
            turn_count=turn_count,
            score=score,
            qualification=qualification,
            credits_consumed=actual_credits,
            summary=summary,
            error_message=error_message,
        )

        # Update lead status based on outcome
        if call.lead_id and outcome:
            lead_status_map = {
                "qualified": "qualified",
                "not_interested": "not_interested",
                "callback": "callback",
                "appointment_set": "qualified",
                "no_answer": "failed",
                "failed": "failed",
                "transferred": "contacted",
            }
            new_lead_status = lead_status_map.get(outcome, "contacted")
            await self.lead_repo.update_status(
                call.lead_id, organization_id, new_lead_status,
                qualification=qualification, score=score,
            )

        # Decrement campaign concurrency and update campaign stats
        if call.campaign_id:
            from backend.services.campaign_service import CampaignService
            camp_svc = CampaignService(self.db, redis=self._get_redis())
            await camp_svc.release_call_slot(call.campaign_id)
            await self.campaign_repo.increment_counter(call.campaign_id, "leads_dialed")
            if status == "completed":
                await self.campaign_repo.increment_counter(call.campaign_id, "leads_completed")
            if outcome in ("qualified", "appointment_set"):
                await self.campaign_repo.increment_counter(call.campaign_id, "leads_connected")

            # Auto-complete campaign if all leads have been dialed/completed and no calls active
            campaign = await self.campaign_repo.get_for_org(call.campaign_id, organization_id)
            if campaign and campaign.status == "running":
                query = {
                    "organization_id": organization_id,
                    "status": {"$in": ["new", "callback", "scheduled"]},
                }
                if campaign.lead_filter:
                    query.update(campaign.lead_filter)
                if campaign.campaign_id_filter:
                    query["campaign_id"] = campaign.campaign_id_filter
                remaining_leads = await self.lead_repo.count(query)
                active_calls = await camp_svc.get_active_call_count(call.campaign_id)
                if remaining_leads == 0 and active_calls == 0:
                    log.info("Auto-completing campaign=%s: all leads dialed and 0 active calls", call.campaign_id)
                    await camp_svc.complete_campaign(call.campaign_id, organization_id)

        log.info("call finalized id=%s status=%s outcome=%s credits=%d",
                 call_id, status, outcome, actual_credits)

        return {
            "call_id": call_id,
            "status": status,
            "outcome": outcome,
            "duration_s": duration_s,
            "credits_consumed": actual_credits,
        }

    async def get_call(
        self, call_id: str, organization_id: str
    ):
        return await self.call_repo.get_for_org(call_id, organization_id)

    async def list_calls(
        self,
        organization_id: str,
        campaign_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list:
        return await self.call_repo.list_for_org(
            organization_id, campaign_id=campaign_id,
            lead_id=lead_id, status=status,
            limit=limit, skip=skip,
        )
