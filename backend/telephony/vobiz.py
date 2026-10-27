"""Vobiz.ai Telephony webhook and Media Streams over WebSocket.

Vobiz speaks a JSON-over-WebSocket protocol carrying 8 kHz mu-law audio in base64.
We bridge that to our 16 kHz PCM `CallSession`:

  inbound  : mu-law 8k  -> PCM16 8k -> PCM16 16k  (fed to session/VAD/STT)
  outbound : PCM16 @tts -> PCM16 8k -> mu-law 8k -> base64 (played via playAudio)

Barge-in:
  When the caller interrupts, we send Vobiz a `clearAudio` event to instantly
  flush buffered audio.
"""

import audioop
import base64
import json
import logging
from typing import Optional

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from backend.config import settings
from backend.core.db import get_db

log = logging.getLogger("telephony.vobiz")

router = APIRouter()

VOBIZ_SR = 8000  # Vobiz media is 8 kHz mu-law mono
_OUT_CHUNK = 160  # 20 ms of 8 kHz mu-law = 160 bytes


def _mulaw8k_to_pcm16k(mulaw: bytes, state) -> tuple[bytes, object]:
    pcm8 = audioop.ulaw2lin(mulaw, 2)
    pcm16, state = audioop.ratecv(pcm8, 2, 1, VOBIZ_SR, 16000, state)
    return pcm16, state


class VobizTransport:
    """Speaks the Vobiz Media Streams protocol over the websocket."""

    streaming = True

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.stream_id: Optional[str] = None
        self._resample_state = None

    async def play(self, pcm16: bytes, sample_rate: int) -> None:
        if self.stream_id is None or not pcm16:
            return
        pcm8, self._resample_state = audioop.ratecv(
            pcm16, 2, 1, sample_rate, VOBIZ_SR, self._resample_state
        )
        mulaw = audioop.lin2ulaw(pcm8, 2)
        for i in range(0, len(mulaw), _OUT_CHUNK):
            chunk = mulaw[i : i + _OUT_CHUNK]
            payload = base64.b64encode(chunk).decode("ascii")
            msg = {
                "event": "playAudio",
                "streamId": self.stream_id,
                "media": {
                    "contentType": "audio/x-mulaw",
                    "sampleRate": VOBIZ_SR,
                    "payload": payload,
                },
            }
            await self.ws.send_text(json.dumps(msg))

    async def clear(self) -> None:
        self._resample_state = None
        if self.stream_id is None:
            return
        msg = {
            "event": "clearAudio",
            "streamId": self.stream_id,
        }
        await self.ws.send_text(json.dumps(msg))

    async def notify(self, event: dict) -> None:
        if event.get("type") == "hangup":
            # Schedule delayed websocket close to give time for final TTS sentence to be heard by caller
            async def _close():
                import asyncio
                await asyncio.sleep(3.5)
                await self.close()
            import asyncio
            asyncio.create_task(_close())

    async def close(self, code: int = 1000, reason: str = "call_completed") -> None:
        try:
            await self.ws.close(code=code, reason=reason)
        except Exception:
            pass


_active_transports: dict[str, VobizTransport] = {}


def get_active_transport(call_id: str) -> Optional[VobizTransport]:
    return _active_transports.get(call_id)


async def hangup_vobiz_call(call_id: str, db: object = None) -> bool:
    """Terminates an active Vobiz call via WebSocket close and REST API fallback."""
    terminated = False
    transport = _active_transports.get(call_id)
    if transport:
        try:
            await transport.close()
            terminated = True
        except Exception as exc:
            log.warning("Failed closing vobiz transport for call %s: %s", call_id, exc)

    if db is not None:
        try:
            call_doc = await db.calls.find_one({"_id": call_id})
            if call_doc and call_doc.get("provider") == "vobiz":
                provider_res_id = call_doc.get("provider_resource_id") or call_doc.get("provider_call_id")
                from_num = call_doc.get("from_number")
                if provider_res_id and from_num:
                    pn_doc = await db.phone_numbers.find_one({"number": from_num})
                    if pn_doc:
                        meta = pn_doc.get("provider_metadata") or {}
                        auth_id = meta.get("vobiz_auth_id")
                        auth_token = meta.get("vobiz_auth_token")
                        if auth_id and auth_token:
                            from backend.providers.telephony.vobiz import VobizTelephonyProvider
                            vobiz_provider = VobizTelephonyProvider()
                            await vobiz_provider.hangup_call(
                                provider_resource_id=provider_res_id,
                                auth_id=auth_id,
                                auth_token=auth_token,
                            )
                            terminated = True
        except Exception as exc:
            log.warning("Failed REST API hangup for vobiz call %s: %s", call_id, exc)

    return terminated


def _stream_wss_url(call_id: Optional[str] = None, agent_id: Optional[str] = None, lang: str = "en-IN", base_url: Optional[str] = None) -> str:
    if base_url:
        base = base_url.rstrip("/")
    elif settings.public_base_url and "ngrok" not in settings.public_base_url:
        base = settings.public_base_url.rstrip("/")
    else:
        base = "https://92.5.149.29.sslip.io"
    base = base.replace("https://", "wss://").replace("http://", "ws://")
    params = []
    if call_id:
        params.append(f"call_id={call_id}")
    if agent_id:
        params.append(f"agent_id={agent_id}")
    params.append(f"lang={lang}")
    query = "&".join(params)
    return f"{base}/ws/vobiz?{query}"


def _vobiz_xml(call_id: Optional[str] = None, agent_id: Optional[str] = None, lang: str = "en-IN", base_url: Optional[str] = None) -> str:
    wss_url = _stream_wss_url(call_id, agent_id, lang, base_url=base_url)
    xml_url = wss_url.replace("&", "&amp;")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Response>\n'
        f'  <Stream bidirectional="true" keepCallAlive="true" streamTimeout="7200" contentType="audio/x-l16;rate=8000">{xml_url}</Stream>\n'
        '  <Hangup/>\n'
        '</Response>'
    )


def _vobiz_unavailable_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Response>\n'
        '  <Speak>This number is temporarily unavailable.</Speak>\n'
        '  <Hangup/>\n'
        '</Response>'
    )


@router.api_route("/vobiz/voice", methods=["GET", "POST"], include_in_schema=False)
async def vobiz_voice(request: Request) -> Response:
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "https"
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "92.5.149.29.sslip.io"
    request_base_url = f"{proto}://{host}"
    """Vobiz calls this when an outbound or inbound call connects."""
    call_id = request.query_params.get("call_id")
    agent_id = request.query_params.get("agent_id")
    language = request.query_params.get("lang", "en-IN")

    form_data = {}
    if request.method == "POST":
        try:
            form = await request.form()
            form_data = dict(form)
            call_id = call_id or form_data.get("call_id")
            agent_id = agent_id or form_data.get("agent_id")
            language = language or form_data.get("lang", "en-IN")
        except Exception:
            pass

    log.info("Vobiz voice webhook invoked: method=%s call_id=%s agent_id=%s lang=%s",
             request.method, call_id, agent_id, language)

    # Outbound call: already has call_id and agent configured
    if call_id:
        db = get_db()
        if db is not None:
            try:
                c_doc = await db.calls.find_one({"_id": call_id})
                if c_doc and c_doc.get("status") in ("completed", "failed", "cancelled"):
                    return Response(
                        content='<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n  <Hangup/>\n</Response>',
                        media_type="application/xml",
                    )
            except Exception:
                pass
        return Response(
            content=_vobiz_xml(call_id=call_id, agent_id=agent_id, lang=language, base_url=request_base_url),
            media_type="application/xml",
        )

    # Inbound call: resolve dialed number (To) and caller (From)
    to_number = form_data.get("To") or request.query_params.get("To") or ""
    from_number = form_data.get("From") or request.query_params.get("From") or ""

    if not to_number:
        return Response(content=_vobiz_unavailable_xml(), media_type="application/xml")

    db = get_db()
    if db is None:
        return Response(content=_vobiz_unavailable_xml(), media_type="application/xml")

    from backend.repositories.phone_number_repo import PhoneNumberRepository
    from backend.services.credit_service import CreditService
    from backend.repositories.lead_repo import LeadRepository
    from backend.repositories.call_repo import CallRepository
    from backend.repositories.agent_repo import AgentRepository

    pn_repo = PhoneNumberRepository(db)
    pn = await pn_repo.find_by_number(to_number)
    if not pn or pn.status != "assigned":
        return Response(content=_vobiz_unavailable_xml(), media_type="application/xml")

    # Inbound organization resolution
    inbound_org = pn.inbound_organization_id or (pn.assigned_org_ids[0] if getattr(pn, "assigned_org_ids", None) else pn.organization_id)
    if not inbound_org:
        return Response(content=_vobiz_unavailable_xml(), media_type="application/xml")

    # Credit check
    credit_svc = CreditService(db)
    credit_check = await credit_svc.can_start_call(inbound_org, required_credits=5)
    if not credit_check.get("can_start"):
        log.warning("Inbound call rejected for org %s: insufficient credits", inbound_org)
        return Response(content=_vobiz_unavailable_xml(), media_type="application/xml")

    # Inbound agent resolution
    agent_repo = AgentRepository(db)
    selected_agent = None
    if pn.inbound_agent_id:
        selected_agent = await agent_repo.find_by_id(pn.inbound_agent_id)
    if not selected_agent:
        org_agents = await agent_repo.list_by_org(inbound_org)
        active_agents = [a for a in org_agents if a.is_active]
        if active_agents:
            selected_agent = active_agents[0]

    agent_id = selected_agent.id if selected_agent else None
    agent_version = selected_agent.active_version if selected_agent else 1

    # Lead matching / creation
    lead_repo = LeadRepository(db)
    lead = None
    if from_number:
        lead = await lead_repo.find_by_phone(inbound_org, from_number)
        if not lead:
            lead = await lead_repo.create(
                organization_id=inbound_org,
                name=f"Inbound Caller {from_number[-4:]}",
                phone=from_number,
                metadata={"source": "vobiz_inbound"},
            )

    # Create Call record
    call_repo = CallRepository(db)
    call = await call_repo.create(
        organization_id=inbound_org,
        to_number=to_number,
        from_number=from_number,
        direction="inbound",
        agent_id=agent_id,
        agent_version=agent_version,
        lead_id=lead.id if lead else None,
        provider="vobiz",
    )

    # Reserve credits
    try:
        await credit_svc.reserve(
            organization_id=inbound_org,
            call_id=call.id,
            max_credits=5,
        )
    except Exception as exc:
        log.warning("Failed to reserve credits for inbound call %s: %s", call.id, exc)

    return Response(
        content=_vobiz_xml(call_id=call.id, agent_id=agent_id, lang=language, base_url=request_base_url),
        media_type="application/xml",
    )


@router.websocket("/ws/vobiz")
async def ws_vobiz(ws: WebSocket):
    await ws.accept()
    transport = VobizTransport(ws)
    resample_state = None
    started = False
    session = None
    call_id = ws.query_params.get("call_id")
    agent_id = ws.query_params.get("agent_id")
    language = ws.query_params.get("lang", "en-IN")

    db = get_db()
    app = ws.app

    # Ensure cloud call pipeline components are loaded
    try:
        from backend.memory.session import SessionStore
        from backend.agent.engine import ConversationEngine
        from backend.services.provider_runtime import CloudProviderRuntime

        if db is not None:
            components = await CloudProviderRuntime(db).load_call_components()
            app.state.stt = components.stt
            app.state.engine = ConversationEngine(llm=components.llm)
            app.state.tts = components.tts
            if not getattr(app.state, "session_store", None):
                app.state.session_store = SessionStore()
    except Exception as exc:  # noqa: BLE001
        log.warning("failed to load cloud call pipeline: %s", exc)

    log.info("Vobiz websocket connected: call_id=%s agent_id=%s lang=%s", call_id, agent_id, language)
    if call_id:
        _active_transports[call_id] = transport
        try:
            from backend.telephony.broadcaster import call_broadcaster
            await call_broadcaster.broadcast(call_id, {"type": "connected", "call_id": call_id})
        except Exception:
            pass

    media_format = {}
    encoding = "audio/x-l16"
    inbound_sample_rate = 16000
    media_frame_count = 0

    try:
        while True:
            text_data = await ws.receive_text()
            data = json.loads(text_data)
            event = data.get("event")

            if event == "start":
                start_obj = data.get("start") or {}
                transport.stream_id = data.get("streamId") or start_obj.get("streamId")
                custom_params = start_obj.get("customParameters") or {}
                language = custom_params.get("lang", language)
                agent_id = custom_params.get("agent_id", agent_id)
                call_id = custom_params.get("call_id", call_id)
                media_format = start_obj.get("mediaFormat") or {}
                if media_format:
                    encoding = media_format.get("encoding", encoding).lower()
                    inbound_sample_rate = int(media_format.get("sampleRate", inbound_sample_rate))
                log.info("Vobiz stream started: stream_id=%s call_id=%s agent_id=%s lang=%s encoding=%s sr=%s",
                         transport.stream_id, call_id, agent_id, language, encoding, inbound_sample_rate)

                if call_id and db is not None:
                    try:
                        from backend.repositories.call_repo import CallRepository
                        await CallRepository(db).mark_connected(call_id)
                    except Exception as e:
                        log.warning("failed marking call connected for %s: %s", call_id, e)

                custom_greeting = None
                system_prompt = None
                agent_name = None
                voice_id = None
                variables = {}
                barge_in_sensitivity = 70
                direction = "outbound"

                # Lookup call record for direction and agent if available
                if call_id and db is not None:
                    try:
                        call_doc = await db.calls.find_one({"_id": call_id})
                        if call_doc:
                            direction = call_doc.get("direction", "outbound")
                            if not agent_id:
                                agent_id = call_doc.get("agent_id")
                    except Exception as e:
                        log.warning("failed looking up call_doc for vobiz stream: %s", e)

                # Resolve agent prompt, greeting, and KB context
                if agent_id and db is not None:
                    try:
                        agent_doc = await db.agents.find_one({"_id": agent_id})
                        if agent_doc:
                            agent_name = agent_doc.get("name")
                            org_id = agent_doc.get("organization_id")
                            active_vid = agent_doc.get("active_version_id")
                            version_doc = None
                            if active_vid:
                                version_doc = await db.agent_versions.find_one({"_id": active_vid})
                            if not version_doc:
                                version_doc = await db.agent_versions.find_one(
                                    {"agent_id": agent_id}, sort=[("version", -1)]
                                )

                            if version_doc:
                                cfg = version_doc.get("configuration") or {}
                                custom_greeting = cfg.get("greeting")
                                system_prompt = cfg.get("system_prompt")
                                language = cfg.get("primary_language", language)
                                voice_id = cfg.get("voice_id")
                                variables = cfg.get("input_variables") or {}
                                strictness = cfg.get("knowledge_strictness", "flexible")
                                if "sensitivity" in cfg:
                                    try:
                                        barge_in_sensitivity = int(cfg["sensitivity"])
                                    except Exception:
                                        pass

                                # Ground with Knowledge Base if associated
                                if org_id:
                                    from backend.services.knowledge_service import KnowledgeService
                                    kb_svc = KnowledgeService(db)
                                    kb_context = await kb_svc.get_context_for_agent(agent_id, org_id, mode=strictness)
                                    if kb_context:
                                        system_prompt = (system_prompt or "") + f"\n\n{kb_context}"
                                        log.info("injected knowledge base context into vobiz call for agent=%s", agent_id)
                    except Exception as exc:
                        log.warning("failed resolving agent config for vobiz stream: %s", exc)

                if not started and getattr(app.state, "stt", None) and getattr(app.state, "tts", None):
                    from backend.call_session import CallSession

                    session = CallSession(
                        transport=transport,
                        stt=app.state.stt,
                        engine=app.state.engine,
                        tts=app.state.tts,
                        store=app.state.session_store,
                        direction=direction,
                        language=language,
                        agent_name=agent_name,
                        custom_greeting=custom_greeting,
                        system_prompt=system_prompt,
                        variables=variables,
                        voice_id=voice_id,
                        barge_in_sensitivity=barge_in_sensitivity,
                        call_id=call_id,
                    )
                    await session.start()
                    if call_id:
                        from backend.telephony.broadcaster import call_broadcaster
                        await call_broadcaster.broadcast(call_id, {"type": "connected", "call_id": call_id})
                    started = True
                    log.info("CallSession started for vobiz call %s", call_id)

            elif event == "media":
                if not started or session is None:
                    continue
                media_info = data.get("media", {})
                b64_payload = media_info.get("payload", "")
                if b64_payload:
                    media_frame_count += 1
                    raw_bytes = base64.b64decode(b64_payload)
                    if media_frame_count == 1:
                        log.info(
                            "First Vobiz media packet: size=%d bytes, encoding=%s, sr=%d",
                            len(raw_bytes), encoding, inbound_sample_rate
                        )
                    # Adaptive audio decoding:
                    # If Vobiz sends 16kHz Linear PCM (audio/x-l16 or 20ms frame >= 500 bytes):
                    if ("l16" in encoding or "linear" in encoding or "pcm" in encoding) or len(raw_bytes) >= 500:
                        if inbound_sample_rate == 8000 or (len(raw_bytes) in (320, 160) and "l16" in encoding):
                            pcm16, resample_state = audioop.ratecv(raw_bytes, 2, 1, 8000, 16000, resample_state)
                        else:
                            pcm16 = raw_bytes
                    else:
                        pcm8 = audioop.ulaw2lin(raw_bytes, 2)
                        pcm16, resample_state = audioop.ratecv(pcm8, 2, 1, inbound_sample_rate or 8000, 16000, resample_state)
                    await session.feed_pcm16(pcm16)

            elif event in ("stop", "closed"):
                log.info("Vobiz stream event %s received for call %s", event, call_id)
                break

    except WebSocketDisconnect:
        log.info("Vobiz websocket disconnected for call %s", call_id)
    except Exception as exc:
        log.exception("Vobiz streaming error: %s", exc)
    finally:
        if call_id:
            _active_transports.pop(call_id, None)
        if session is not None:
            await session.finalize()
        if call_id:
            try:
                from backend.telephony.broadcaster import call_broadcaster
                await call_broadcaster.broadcast(call_id, {"type": "hangup", "reason": "call_disconnected", "call_id": call_id})
            except Exception:
                pass
        # Finalize call status and settle credits if call record exists
        if call_id and db is not None:
            try:
                from backend.repositories.call_repo import CallRepository
                from backend.services.credit_service import CreditService
                from backend.models.base import utcnow
                call_repo = CallRepository(db)
                c_doc = await call_repo.find_by_id(call_id)
                if c_doc:
                    started_at = c_doc.started_at or c_doc.created_at
                    duration = int((utcnow() - started_at).total_seconds()) if started_at else 60
                    consumed = max(0, (duration + 59) // 60) if duration > 0 else 0
                    qualification = session.state.get("output_variables") if session else None
                    await call_repo.finalize(
                        call_id=call_id,
                        organization_id=c_doc.organization_id,
                        status="completed",
                        duration_s=duration,
                        credits_consumed=consumed,
                        qualification=qualification,
                    )
                    credit_svc = CreditService(db)
                    await credit_svc.settle_duration(
                        organization_id=c_doc.organization_id,
                        call_id=call_id,
                        duration_seconds=duration,
                    )
            except Exception as e:
                log.warning("Failed finalizing/settling Vobiz call %s: %s", call_id, e)
