"""FastAPI entrypoint.

- /health            : Postgres + Redis + Groq key checks
- /                  : browser test page
- /ws/call           : browser realtime call (continuous PCM + VAD + barge-in)
- Twilio routes      : registered from backend.telephony.twilio (Sprint 5)

The heavy lifting lives in CallSession; each transport is thin.
"""

import logging
import struct
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.config import settings
from backend.logging_setup import configure_logging
from backend.api.routes import router as api_router
from backend.call_session import CallSession
from backend.agent.engine import ConversationEngine
from backend.audio.stt import STTClient, SarvamSTT, STTRouter
from backend.audio.tts import get_tts_engine
from backend.memory.session import SessionStore

configure_logging(settings.log_level)
log = logging.getLogger("app")

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("starting voice-agent backend on %s:%s", settings.app_host, settings.app_port)
    # Instantiate once; Piper loads its model here, not per connection.
    groq_stt = STTClient()
    sarvam_stt = SarvamSTT() if settings.sarvam_tts_api_key else None
    app.state.stt = STTRouter(groq_stt, sarvam_stt)
    app.state.engine = ConversationEngine()
    app.state.tts = get_tts_engine()
    app.state.session_store = SessionStore()
    log.info("clients ready (stt=groq:%s + sarvam:%s, llm=%s, tts=%s)",
             settings.groq_stt_model,
             settings.sarvam_stt_model if sarvam_stt else "off",
             settings.groq_llm_model, settings.tts_engine)
    yield
    await app.state.session_store.close()
    log.info("shutting down")


app = FastAPI(title="Real Estate Voice Agent", version="0.1.0", lifespan=lifespan)

# Allow the Next.js dashboard (dev) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


# ---------------------------------------------------------------------------
# Health & static
# ---------------------------------------------------------------------------
async def _check_postgres() -> bool:
    try: 
        import psycopg

        with psycopg.connect(
            settings.database_url.replace("+psycopg", ""), connect_timeout=2
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("postgres check failed: %s", exc)
        return False


async def _check_redis() -> bool:
    try:
        import redis

        client = redis.Redis(
            host=settings.redis_host, port=settings.redis_port, socket_connect_timeout=2
        )
        return bool(client.ping())
    except Exception as exc:  # noqa: BLE001
        log.warning("redis check failed: %s", exc)
        return False


@app.get("/health")
async def health():
    pg_ok = await _check_postgres()
    redis_ok = await _check_redis()
    groq_ok = bool(settings.groq_api_key)
    healthy = pg_ok and redis_ok and groq_ok
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "healthy" if healthy else "degraded",
            "checks": {"postgres": pg_ok, "redis": redis_ok, "groq_api_key": groq_ok},
        },
    )


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/info")
async def info():
    return {"service": "real-estate-voice-agent", "docs": "/docs", "health": "/health"}


@app.get("/api/languages")
async def languages():
    """Languages the admin can pick for a call (Sarvam-backed Indian languages)."""
    from backend.languages import DEFAULT_LANGUAGE, LANGUAGES

    return {
        "default": DEFAULT_LANGUAGE,
        "languages": [
            {"code": code, "name": info["name"], "native": info["native"]}
            for code, info in LANGUAGES.items()
        ],
    }


# ---------------------------------------------------------------------------
# Browser transport + realtime call websocket
# ---------------------------------------------------------------------------
class BrowserTransport:
    """Speaks to the browser page. Streams progressive PCM chunks (4-byte little-
    endian sample rate header + int16 PCM) so the browser can play them seamlessly
    via Web Audio with low latency; events go as JSON."""

    streaming = True

    def __init__(self, ws: WebSocket):
        self.ws = ws

    async def play(self, pcm16: bytes, sample_rate: int) -> None:
        if not pcm16:
            return
        await self.ws.send_bytes(struct.pack("<I", sample_rate) + pcm16)

    async def clear(self) -> None:
        await self.ws.send_json({"type": "interrupt"})

    async def notify(self, event: dict) -> None:
        await self.ws.send_json(event)


@app.websocket("/ws/call")
async def ws_call(ws: WebSocket):
    await ws.accept()
    language = ws.query_params.get("lang", "en-IN")
    session = CallSession(
        transport=BrowserTransport(ws),
        stt=app.state.stt,
        engine=app.state.engine,
        tts=app.state.tts,
        store=app.state.session_store,
        direction="inbound",
        language=language,
    )
    try:
        await session.start()
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            frame = msg.get("bytes")
            if frame:
                await session.feed_pcm16(frame)
    except WebSocketDisconnect:
        log.info("call disconnected")
    except Exception as exc:  # noqa: BLE001
        log.exception("call error: %s", exc)
    finally:
        await session.finalize()


# ---------------------------------------------------------------------------
# Twilio telephony routes (Sprint 5)
# ---------------------------------------------------------------------------
from backend.telephony.twilio import router as twilio_router  # noqa: E402

app.include_router(twilio_router)
