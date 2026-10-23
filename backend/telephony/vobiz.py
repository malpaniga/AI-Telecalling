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
        return


def _stream_wss_url(call_id: Optional[str] = None, agent_id: Optional[str] = None, lang: str = "en-IN") -> str:
    base = settings.public_base_url.rstrip("/") if settings.public_base_url else "http://localhost:8000"
    base = base.replace("https://", "wss://").replace("http://", "ws://")
    params = []
    if call_id:
        params.append(f"call_id={call_id}")
    if agent_id:
        params.append(f"agent_id={agent_id}")
    params.append(f"lang={lang}")
    query = "&".join(params)
    return f"{base}/ws/vobiz?{query}"


def _vobiz_xml(call_id: Optional[str] = None, agent_id: Optional[str] = None, lang: str = "en-IN") -> str:
    wss_url = _stream_wss_url(call_id, agent_id, lang)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Response>\n'
        f'  <Stream bidirectional="true">{wss_url}</Stream>\n'
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

    # Outbound call: already has call_id and agent configured
    if call_id:
        return Response(
            content=_vobiz_xml(call_id=call_id, agent_id=agent_id, lang=language),
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
    credit_check = await credit_svc.can_start_call(inbound_org, required_credits=60)
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
            max_credits=300,
        )
    except Exception as exc:
        log.warning("Failed to reserve credits for inbound call %s: %s", call.id, exc)

    return Response(
        content=_vobiz_xml(call_id=call.id, agent_id=agent_id, lang=language),
        media_type="application/xml",
    )


@router.websocket("/ws/vobiz")
async def ws_vobiz(ws: WebSocket):
    await ws.accept()
    transport = VobizTransport(ws)
    resample_state = None
    started = False
    session: Optional[CallSession] = None
    call_id = ws.query_params.get("call_id")
    agent_id = ws.query_params.get("agent_id")
    language = ws.query_params.get("lang", "en-IN")

    db = get_db()
    app = ws.app

    try:
        while True:
            text_data = await ws.receive_text()
            data = json.loads(text_data)
            event = data.get("event")

            if event == "start":
                transport.stream_id = data.get("streamId") or data.get("start", {}).get("streamId")
                if not started and getattr(app.state, "stt", None) and getattr(app.state, "tts", None):
                    # Inject Knowledge Base context if agent exists
                    system_prompt = None
                    if agent_id and db is not None:
                        try:
                            from backend.services.knowledge_service import KnowledgeService
                            kb_svc = KnowledgeService(db)
                            agent_doc = await db.agents.find_one({"_id": agent_id})
                            if agent_doc:
                                org_id = agent_doc.get("organization_id")
                                kb_context = await kb_svc.get_context_for_agent(agent_id, org_id)
                                if kb_context:
                                    system_prompt = kb_context
                        except Exception as e:
                            log.warning("Error fetching KB context for vobiz stream: %s", e)

                    session = CallSession(
                        transport=transport,
                        stt=app.state.stt,
                        engine=app.state.engine,
                        tts=app.state.tts,
                        call_id=call_id,
                        language=language,
                        system_prompt=system_prompt,
                    )
                    await session.start()
                    started = True

            elif event == "media":
                media_info = data.get("media", {})
                b64_payload = media_info.get("payload", "")
                if b64_payload and session is not None:
                    raw_mulaw = base64.b64decode(b64_payload)
                    pcm16, resample_state = _mulaw8k_to_pcm16k(raw_mulaw, resample_state)
                    await session.push_audio(pcm16)

            elif event in ("stop", "closed"):
                break

    except WebSocketDisconnect:
        log.info("Vobiz websocket disconnected for call %s", call_id)
    except Exception as exc:
        log.exception("Vobiz streaming error: %s", exc)
    finally:
        if session:
            await session.finalize()
        # Settle credits if call record exists
        if call_id and db is not None:
            try:
                from backend.repositories.call_repo import CallRepository
                from backend.services.credit_service import CreditService
                call_repo = CallRepository(db)
                c_doc = await call_repo.find_by_id(call_id)
                if c_doc:
                    credit_svc = CreditService(db)
                    duration = c_doc.duration_s or 60
                    consumed = max(1, (duration + 59) // 60) * 10
                    await credit_svc.settle(
                        organization_id=c_doc.organization_id,
                        call_id=call_id,
                        actual_credits=consumed,
                    )
            except Exception as e:
                log.warning("Failed settling credits for Vobiz call %s: %s", call_id, e)
