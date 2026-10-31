"""Plivo Telephony webhook and Media Streams over WebSocket.

Plivo speaks a JSON-over-WebSocket protocol carrying 8 kHz mu-law audio in base64.
We bridge that to our 16 kHz PCM `CallSession`:

  inbound  : mu-law 8k  -> PCM16 8k -> PCM16 16k  (fed to session/VAD/STT)
  outbound : PCM16 @tts -> PCM16 8k -> mu-law 8k -> base64 (played via playAudio)

Barge-in:
  When the caller interrupts, we send Plivo a `clearAudio` event to instantly
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

log = logging.getLogger("telephony.plivo")

router = APIRouter()

PLIVO_SR = 8000  # Plivo media stream is 8 kHz mu-law mono
_OUT_CHUNK = 160  # 20 ms of 8 kHz mu-law = 160 bytes


def _mulaw8k_to_pcm16k(mulaw: bytes, state) -> tuple[bytes, object]:
    pcm8 = audioop.ulaw2lin(mulaw, 2)
    pcm16, state = audioop.ratecv(pcm8, 2, 1, PLIVO_SR, 16000, state)
    return pcm16, state


class PlivoTransport:
    """Speaks the Plivo Media Streams protocol over the websocket."""

    streaming = True

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.stream_id: Optional[str] = None
        self._resample_state = None

    async def play(self, pcm16: bytes, sample_rate: int) -> None:
        if self.stream_id is None or not pcm16:
            return
        pcm8, self._resample_state = audioop.ratecv(
            pcm16, 2, 1, sample_rate, PLIVO_SR, self._resample_state
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
                    "sampleRate": PLIVO_SR,
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


_active_transports: dict[str, PlivoTransport] = {}


def get_active_transport(call_id: str) -> Optional[PlivoTransport]:
    return _active_transports.get(call_id)


async def hangup_plivo_call(call_id: str, db: object = None) -> bool:
    """Terminates an active Plivo call via WebSocket close and REST API fallback."""
    terminated = False
    transport = _active_transports.get(call_id)
    if transport:
        try:
            await transport.close()
            terminated = True
        except Exception as exc:
            log.warning("Failed closing plivo transport for call %s: %s", call_id, exc)

    if db is not None:
        try:
            call_doc = await db.calls.find_one({"_id": call_id})
            if call_doc and call_doc.get("provider") == "plivo":
                provider_res_id = call_doc.get("provider_resource_id") or call_doc.get("provider_call_id")
                from_number = call_doc.get("from_number")
                if provider_res_id and from_number:
                    pn_doc = await db.phone_numbers.find_one({"number": from_number})
                    metadata = (pn_doc or {}).get("provider_metadata") or {}
                    auth_id = metadata.get("plivo_auth_id") or metadata.get("auth_id")
                    auth_token = metadata.get("plivo_auth_token") or metadata.get("auth_token")
                    if auth_id and auth_token:
                        from backend.providers.telephony.plivo import PlivoTelephonyProvider
                        provider = PlivoTelephonyProvider()
                        await provider.hangup_call(provider_resource_id=provider_res_id, auth_id=auth_id, auth_token=auth_token)
                        terminated = True
        except Exception as exc:
            log.warning("REST hangup failed for plivo call %s: %s", call_id, exc)

    return terminated


def _stream_wss_url(call_id: Optional[str] = None, agent_id: Optional[str] = None, lang: str = "en-IN", base_url: Optional[str] = None) -> str:
    base = base_url or getattr(settings, "public_base_url", None) or "https://92.5.149.29.sslip.io"
    base = base.rstrip("/")
    if "ngrok" in base:
        base = "https://92.5.149.29.sslip.io"
    base = base.replace("https://", "wss://").replace("http://", "ws://")
    params = []
    if call_id:
        params.append(f"call_id={call_id}")
    if agent_id:
        params.append(f"agent_id={agent_id}")
    params.append(f"lang={lang}")
    query = "&".join(params)
    return f"{base}/ws/plivo?{query}"


def _plivo_xml(call_id: Optional[str] = None, agent_id: Optional[str] = None, lang: str = "en-IN", base_url: Optional[str] = None) -> str:
    wss_url = _stream_wss_url(call_id, agent_id, lang, base_url=base_url)
    xml_url = wss_url.replace("&", "&amp;")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Response>\n'
        f'  <Stream bidirectional="true" keepCallAlive="true" streamTimeout="7200" contentType="audio/x-l16;rate=8000">{xml_url}</Stream>\n'
        '  <Hangup/>\n'
        '</Response>'
    )


def _plivo_unavailable_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Response>\n'
        '  <Speak>This number is temporarily unavailable.</Speak>\n'
        '  <Hangup/>\n'
        '</Response>'
    )


@router.api_route("/plivo/voice", methods=["GET", "POST"], include_in_schema=False)
async def plivo_voice(request: Request) -> Response:
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme or "https"
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "92.5.149.29.sslip.io"
    request_base_url = f"{proto}://{host}"
    """Plivo calls this when an outbound or inbound call connects."""
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

    log.info("Plivo voice webhook invoked: method=%s call_id=%s agent_id=%s lang=%s",
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
            content=_plivo_xml(call_id=call_id, agent_id=agent_id, lang=language, base_url=request_base_url),
            media_type="application/xml",
        )

    # Inbound call: resolve dialed number (To) and caller (From)
    to_number = form_data.get("To") or request.query_params.get("To") or ""
    from_number = form_data.get("From") or request.query_params.get("From") or ""

    if not to_number:
        return Response(content=_plivo_unavailable_xml(), media_type="application/xml")

    db = get_db()
    if db is None:
        return Response(content=_plivo_unavailable_xml(), media_type="application/xml")

    from backend.repositories.phone_number_repo import PhoneNumberRepository
    from backend.services.credit_service import CreditService
    from backend.repositories.lead_repo import LeadRepository
    from backend.repositories.call_repo import CallRepository
    from backend.repositories.agent_repo import AgentRepository

    pn_repo = PhoneNumberRepository(db)
    pn = await pn_repo.find_by_number(to_number)
    if not pn or pn.status != "assigned":
        return Response(content=_plivo_unavailable_xml(), media_type="application/xml")

    # Inbound organization resolution
    inbound_org = pn.inbound_organization_id or (pn.assigned_org_ids[0] if getattr(pn, "assigned_org_ids", None) else pn.organization_id)
    if not inbound_org:
        return Response(content=_plivo_unavailable_xml(), media_type="application/xml")

    # Credit check
    credit_svc = CreditService(db)
    credit_check = await credit_svc.can_start_call(inbound_org, required_credits=5)
    if not credit_check.get("can_start"):
        log.warning("Inbound call rejected for org %s: insufficient credits", inbound_org)
        return Response(content=_plivo_unavailable_xml(), media_type="application/xml")

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
        lead = await lead_repo.find_by_phone_org(phone=from_number, organization_id=inbound_org)
        if not lead:
            lead = await lead_repo.create(
                organization_id=inbound_org,
                phone=from_number,
                name=f"Inbound Caller {from_number[-4:]}",
                source="plivo_inbound",
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
        provider="plivo",
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
        content=_plivo_xml(call_id=call.id, agent_id=agent_id, lang=language, base_url=request_base_url),
        media_type="application/xml",
    )


@router.websocket("/ws/plivo")
async def ws_plivo(ws: WebSocket):
    await ws.accept()
    transport = PlivoTransport(ws)
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
                app.state.session_store = SessionStore(db)
    except Exception as exc:
        log.error("Failed to initialize cloud call components: %s", exc)

    from backend.call_session import CallSession
    from backend.telephony.broadcaster import call_broadcaster

    agent_name = "AI Assistant"
    custom_greeting = None
    system_prompt = None
    variables = {}
    barge_in_sensitivity = 0.5
    resolved_voice_id = None

    if agent_id and db is not None:
        try:
            agent = await db.agents.find_one({"_id": agent_id})
            if agent:
                agent_name = agent.get("name", agent_name)
                active_vid = agent.get("active_version_id")
                ver_doc = None
                if active_vid:
                    ver_doc = await db.agent_versions.find_one({"_id": active_vid})
                if not ver_doc:
                    ver_doc = await db.agent_versions.find_one({"agent_id": agent_id}, sort=[("version", -1)])
                if ver_doc:
                    cfg = ver_doc.get("configuration") or {}
                    agent_name = cfg.get("agent_name") or agent_name
                    custom_greeting = cfg.get("custom_greeting")
                    system_prompt = cfg.get("system_prompt")
                    variables = cfg.get("variables") or {}
                    barge_in_sensitivity = cfg.get("barge_in_sensitivity", 0.5)
                    resolved_voice_id = cfg.get("voice_id")
                    language = cfg.get("primary_language", language)
        except Exception as exc:
            log.warning("Failed to load agent configuration: %s", exc)

    if call_id:
        _active_transports[call_id] = transport

    # Subscribe to hangup / cancel events from call broadcaster
    hangup_sub_task = None
    if call_id:
        async def _hangup_listener():
            try:
                queue = call_broadcaster.subscribe(call_id)
                while True:
                    event = await queue.get()
                    if event.get("type") == "hangup":
                        log.info("Received hangup broadcast for plivo call %s", call_id)
                        await transport.close(code=1000, reason="user_cancelled")
                        break
            except Exception:
                pass
        import asyncio
        hangup_sub_task = asyncio.create_task(_hangup_listener())

    # Create CallSession
    session = CallSession(
        transport=transport,
        stt=getattr(app.state, "stt", None),
        engine=getattr(app.state, "engine", None),
        tts=getattr(app.state, "tts", None),
        store=getattr(app.state, "session_store", None),
        direction="inbound" if not call_id else "outbound",
        language=language,
        agent_name=agent_name,
        custom_greeting=custom_greeting,
        system_prompt=system_prompt,
        variables=variables,
        barge_in_sensitivity=barge_in_sensitivity,
        voice_id=resolved_voice_id,
        call_id=call_id,
        db=db,
    )

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            event = data.get("event")

            if event == "start":
                transport.stream_id = data.get("streamId")
                log.info("Plivo stream started: stream_id=%s call_id=%s", transport.stream_id, call_id)
                if not started:
                    started = True
                    await session.start()

            elif event == "media":
                if not started:
                    transport.stream_id = data.get("streamId") or transport.stream_id
                    started = True
                    await session.start()

                media = data.get("media", {})
                b64 = media.get("payload")
                if b64:
                    mulaw = base64.b64decode(b64)
                    pcm16, resample_state = _mulaw8k_to_pcm16k(mulaw, resample_state)
                    await session.push_audio(pcm16)

            elif event == "clearAudio":
                await session.handle_barge_in()

            elif event == "stop":
                log.info("Plivo stream stopped for call_id=%s", call_id)
                break

    except WebSocketDisconnect:
        log.info("Plivo WebSocket disconnected for call_id=%s", call_id)
    except Exception as exc:
        log.warning("Plivo streaming loop error for call_id=%s: %s", call_id, exc)
    finally:
        if hangup_sub_task:
            hangup_sub_task.cancel()
        if call_id and call_id in _active_transports:
            _active_transports.pop(call_id, None)

        if session:
            try:
                await session.finalize()
            except Exception as exc:
                log.warning("Session finalize error for call_id=%s: %s", call_id, exc)

        # Finalize and settle credits / campaign counters for call in DB
        if call_id and db is not None:
            try:
                call_doc = await db.calls.find_one({"_id": call_id})
                if call_doc:
                    from backend.services.call_service import CallService
                    call_svc = CallService(db)
                    await call_svc.finalize_call(
                        call_id=call_id,
                        organization_id=call_doc["organization_id"],
                        status="completed",
                    )
            except Exception as exc:
                log.warning("Failed finalizing plivo call %s via CallService: %s", call_id, exc)
