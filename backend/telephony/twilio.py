"""Twilio telephony via Media Streams.

Twilio speaks a websocket protocol carrying 8 kHz mu-law audio in base64. We
bridge that to our 16 kHz PCM `CallSession`:

  inbound  : mu-law 8k  -> PCM16 8k -> PCM16 16k  (fed to the session/VAD/STT)
  outbound : PCM16 @tts -> PCM16 8k -> mu-law 8k -> base64 (played to the caller)

Barge-in maps cleanly: when the caller speaks over Ava we send Twilio a `clear`
message to flush already-buffered audio. On a phone line the inbound track is the
caller only, so there's no echo to fight.

Routes:
  POST /twiml/voice     -> TwiML that connects the call to our media stream
  WS   /ws/twilio       -> the media stream itself
  POST /calls/outbound  -> place an outbound call to a (verified, on trial) number
"""

import audioop
import base64
import json
import logging

from fastapi import APIRouter, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse

from backend.call_session import CallSession
from backend.config import settings

log = logging.getLogger("twilio")

router = APIRouter()

TWILIO_SR = 8000  # Twilio media is 8 kHz mu-law mono
# 20 ms of 8 kHz mu-law = 160 bytes; chunk outbound audio so barge-in stays snappy.
_OUT_CHUNK = 160


def _mulaw8k_to_pcm16k(mulaw: bytes, state) -> tuple[bytes, object]:
    pcm8 = audioop.ulaw2lin(mulaw, 2)
    pcm16, state = audioop.ratecv(pcm8, 2, 1, TWILIO_SR, settings.audio_sample_rate, state)
    return pcm16, state


class TwilioTransport:
    """Speaks the Twilio Media Streams protocol over the websocket.

    `streaming = True` tells the CallSession to feed us progressive TTS chunks.
    We keep one continuous resampler state across chunks so 22 kHz→8 kHz has no
    clicks at chunk boundaries, and reset it on barge-in.
    """

    streaming = True

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.stream_sid: str | None = None
        self._resample_state = None

    async def play(self, pcm16: bytes, sample_rate: int) -> None:
        if self.stream_sid is None or not pcm16:
            return
        pcm8, self._resample_state = audioop.ratecv(
            pcm16, 2, 1, sample_rate, TWILIO_SR, self._resample_state
        )
        mulaw = audioop.lin2ulaw(pcm8, 2)
        for i in range(0, len(mulaw), _OUT_CHUNK):
            payload = base64.b64encode(mulaw[i : i + _OUT_CHUNK]).decode("ascii")
            await self.ws.send_text(
                json.dumps(
                    {
                        "event": "media",
                        "streamSid": self.stream_sid,
                        "media": {"payload": payload},
                    }
                )
            )

    async def clear(self) -> None:
        self._resample_state = None
        if self.stream_sid is None:
            return
        await self.ws.send_text(
            json.dumps({"event": "clear", "streamSid": self.stream_sid})
        )

    async def notify(self, event: dict) -> None:
        # Phone calls have no side-channel UI; transcripts are already persisted.
        return


def _stream_wss_url() -> str:
    base = settings.public_base_url.rstrip("/")
    return base.replace("https://", "wss://").replace("http://", "ws://") + "/ws/twilio"


def _voice_twiml(language: str) -> str:
    response = VoiceResponse()
    connect = Connect()
    stream = Stream(url=_stream_wss_url())
    # Twilio delivers this back to us in the "start" event customParameters.
    stream.parameter(name="lang", value=language)
    connect.append(stream)
    response.append(connect)
    return str(response)


@router.api_route("/twiml/voice", methods=["GET", "POST"], include_in_schema=False)
async def twiml_voice(request: Request) -> Response:
    """Twilio fetches this when a call connects; we hand it a media stream."""
    language = request.query_params.get("lang", "en-IN")
    log.info("serving voice TwiML (lang=%s) -> %s", language, _stream_wss_url())
    return Response(content=_voice_twiml(language), media_type="application/xml")


@router.websocket("/ws/twilio")
async def ws_twilio(ws: WebSocket):
    await ws.accept()
    transport = TwilioTransport(ws)
    resample_state = None
    started = False
    session: CallSession | None = None
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            event = msg.get("event")

            if event == "start":
                start = msg["start"]
                transport.stream_sid = start["streamSid"]
                language = (start.get("customParameters") or {}).get("lang", "en-IN")
                log.info("twilio stream started sid=%s lang=%s", transport.stream_sid, language)
                session = CallSession(
                    transport=transport,
                    stt=ws.app.state.stt,
                    engine=ws.app.state.engine,
                    tts=ws.app.state.tts,
                    store=ws.app.state.session_store,
                    direction="outbound",
                    language=language,
                )
                await session.start()  # greet once the stream is live
                started = True
            elif event == "media":
                if not started or session is None:
                    continue
                mulaw = base64.b64decode(msg["media"]["payload"])
                pcm16, resample_state = _mulaw8k_to_pcm16k(mulaw, resample_state)
                await session.feed_pcm16(pcm16)
            elif event == "stop":
                log.info("twilio stream stopped")
                break
            # "connected" and "mark" events need no action.
    except WebSocketDisconnect:
        log.info("twilio ws disconnected")
    except Exception as exc:  # noqa: BLE001
        log.exception("twilio stream error: %s", exc)
    finally:
        if session is not None:
            await session.finalize()


@router.post("/calls/outbound")
async def place_outbound_call(to: str = Form(...), lang: str = Form("en-IN")) -> JSONResponse:
    """Dial `to` (must be verified while on a Twilio trial) and connect Ava."""
    missing = [
        name
        for name, val in {
            "TWILIO_ACCOUNT_SID": settings.twilio_account_sid,
            "TWILIO_AUTH_TOKEN": settings.twilio_auth_token,
            "TWILIO_PHONE_NUMBER": settings.twilio_phone_number,
            "PUBLIC_BASE_URL": settings.public_base_url,
        }.items()
        if not val
    ]
    if missing:
        return JSONResponse(status_code=400, content={"error": f"missing config: {missing}"})

    from urllib.parse import quote

    to = "".join(to.split())  # strip any spaces the admin typed in the number
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    call = client.calls.create(
        to=to,
        from_=settings.twilio_phone_number,
        url=f"{settings.public_base_url.rstrip('/')}/twiml/voice?lang={quote(lang)}",
    )
    log.info("placed outbound call sid=%s to=%s lang=%s", call.sid, to, lang)
    return JSONResponse({"status": "calling", "call_sid": call.sid, "to": to, "lang": lang})
