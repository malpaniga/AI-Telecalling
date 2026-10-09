"""FastAPI entrypoint.

Routes:
  /health            — MongoDB + Redis + provider key checks
  /                  — browser test page
  /ws/call           — browser realtime call (continuous PCM + VAD + barge-in)
  /api/v1/...        — versioned REST API
  /twiml/voice       — Twilio webhook (TwiML)
  /ws/twilio         — Twilio Media Streams

The heavy call pipeline lives in CallSession; each transport is a thin wrapper.
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
from backend.core.db import init_db, close_db
from backend.core.redis import init_redis, close_redis
from backend.core.health import check_all

configure_logging(settings.log_level)
log = logging.getLogger("app")

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("starting AI Telecalling SaaS on %s:%s", settings.app_host, settings.app_port)
    log.info("env=%s demo_mode=%s", settings.app_env, settings.demo_mode)

    # Core infrastructure
    await init_db()
    await init_redis()

    # Seed default subscription plans (idempotent)
    try:
        from backend.core.db import get_db
        from backend.services.subscription_service import seed_default_plans
        from backend.services.wallet_service import seed_default_packs
        db = get_db()
        seeded_plans = await seed_default_plans(db)
        seeded_packs = await seed_default_packs(db)
        if seeded_plans:
            log.info("seeded %d default subscription plans", len(seeded_plans))
        if seeded_packs:
            log.info("seeded %d default calling packs", len(seeded_packs))

        # Auto-seed demo environment in DEMO_MODE
        if settings.demo_mode:
            from backend.services.demo_seed_service import DemoSeedService
            demo_svc = DemoSeedService(db)
            if not await demo_svc.is_seeded():
                result = await demo_svc.seed_all()
                log.info("demo environment seeded: org=%s",
                         result.get("organization_id"))
            else:
                log.info("demo environment already seeded")
    except Exception as exc:  # noqa: BLE001
        log.warning("seeding failed (non-fatal): %s", exc)

    # Audio/call pipeline (only if keys are available or demo mode)
    if settings.demo_mode or settings.groq_api_key or settings.effective_sarvam_key:
        try:
            from backend.audio.stt import STTClient, SarvamSTT, STTRouter
            from backend.audio.tts import get_tts_engine
            from backend.memory.session import SessionStore
            from backend.agent.engine import ConversationEngine

            groq_stt = STTClient() if settings.groq_api_key else None
            sarvam_stt = SarvamSTT() if settings.effective_sarvam_key else None

            if groq_stt or sarvam_stt:
                app.state.stt = STTRouter(groq_stt, sarvam_stt) if groq_stt else sarvam_stt
            else:
                app.state.stt = None

            app.state.engine = ConversationEngine()
            app.state.tts = get_tts_engine() if not settings.demo_mode else None
            app.state.session_store = SessionStore()
            log.info("call pipeline ready")
        except Exception as exc:  # noqa: BLE001
            log.warning("call pipeline init failed (non-fatal in partial config): %s", exc)
            app.state.stt = None
            app.state.engine = None
            app.state.tts = None
            app.state.session_store = None
    else:
        log.info("call pipeline disabled (no API keys configured)")
        app.state.stt = None
        app.state.engine = None
        app.state.tts = None
        app.state.session_store = None

    yield

    # Cleanup
    if getattr(app.state, "session_store", None):
        await app.state.session_store.close()
    await close_redis()
    await close_db()
    log.info("shutdown complete")


app = FastAPI(
    title="AI Telecalling SaaS",
    version="0.1.0",
    description="Multi-tenant AI Voice Telecalling Platform",
    lifespan=lifespan,
)

# CORS — allow the Next.js dashboard and any configured frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API routers
# ---------------------------------------------------------------------------
from backend.api.v1 import router as api_v1_router  # noqa: E402
app.include_router(api_v1_router)

# Legacy API routes (preserved for frontend compatibility during migration)
from backend.api.routes import router as legacy_router  # noqa: E402
app.include_router(legacy_router)

# ---------------------------------------------------------------------------
# Health & static
# ---------------------------------------------------------------------------
@app.get("/health", tags=["system"])
async def health():
    result = await check_all()
    status_code = 200 if result["status"] == "healthy" else 503
    return JSONResponse(status_code=status_code, content=result)


@app.get("/", include_in_schema=False)
async def index():
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {"service": "ai-telecalling-saas", "docs": "/docs", "health": "/health"}


@app.get("/info", tags=["system"])
async def info():
    return {
        "service": "ai-telecalling-saas",
        "version": "0.1.0",
        "env": settings.app_env,
        "demo_mode": settings.demo_mode,
        "docs": "/docs",
        "health": "/health",
    }


# ---------------------------------------------------------------------------
# Browser transport (existing call pipeline — preserved)
# ---------------------------------------------------------------------------
class BrowserTransport:
    """Speaks to the browser. Streams PCM chunks (4-byte sample-rate header + PCM)."""

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
    if app.state.stt is None or app.state.engine is None:
        await ws.close(code=1011, reason="call pipeline not configured")
        return
    await ws.accept()
    language = ws.query_params.get("lang", "en-IN")

    from backend.call_session import CallSession

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
        log.info("browser call disconnected")
    except Exception as exc:  # noqa: BLE001
        log.exception("browser call error: %s", exc)
    finally:
        await session.finalize()


# ---------------------------------------------------------------------------
# Twilio telephony routes (preserved)
# ---------------------------------------------------------------------------
try:
    from backend.telephony.twilio import router as twilio_router  # noqa: E402
    app.include_router(twilio_router)
except Exception as exc:  # noqa: BLE001
    log.warning("Twilio router not loaded (ok if Twilio not configured): %s", exc)
