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

import os
import sys

# Ensure UTF-8 output on Windows console so Indic scripts (Marathi/Hindi) do not fail with charmap UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Increase WebSocket header/line limit from 8KB to 64KB to support rich prompt payloads
os.environ.setdefault("WEBSOCKETS_MAX_LINE_LENGTH", "65536")

import asyncio
import logging
import struct
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.config import settings
from backend.logging_setup import configure_logging
from backend.core.db import init_db, close_db, get_db
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
        from backend.services.model_catalogue_seed import seed_model_catalogue, seed_m42_catalogue
        from backend.services.voice_profile_service import seed_default_voice_profiles
        db = get_db()
        seeded_plans = await seed_default_plans(db)
        seeded_packs = await seed_default_packs(db)
        if seeded_plans:
            log.info("seeded %d default subscription plans", len(seeded_plans))
        if seeded_packs:
            log.info("seeded %d default calling packs", len(seeded_packs))
        await seed_model_catalogue(db)
        await seed_m42_catalogue(db)
        seeded_voices = await seed_default_voice_profiles(db)
        if seeded_voices:
            log.info("seeded %d default platform voice profiles", len(seeded_voices))

        # Seed and sync provider rate cards + daily FX rates (M43)
        from backend.services.pricing_sync_service import PricingSyncService
        pricing_svc = PricingSyncService(db)
        await pricing_svc.sync_all_rates()
        log.info("daily provider rates and FX rates synchronized")

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

    # Audio/call pipeline: active Super Admin configurations are the sole
    # inference source. This intentionally does not fall back to Piper, Ollama,
    # or any other local/self-hosted runtime in cloud-only deployments.
    if not settings.demo_mode:
        try:
            from backend.memory.session import SessionStore
            from backend.agent.engine import ConversationEngine
            from backend.services.provider_runtime import CloudProviderRuntime

            components = await CloudProviderRuntime(db).load_call_components()
            app.state.stt = components.stt
            app.state.engine = ConversationEngine(llm=components.llm)
            app.state.tts = components.tts
            app.state.session_store = SessionStore()
            log.info("cloud call pipeline ready")
        except Exception as exc:  # noqa: BLE001
            log.warning("cloud call pipeline unavailable: %s", type(exc).__name__)
            app.state.stt = None
            app.state.engine = None
            app.state.tts = None
            app.state.session_store = None
    else:
        log.info("call pipeline disabled in demo mode")
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
    allow_origins=["*"],
    allow_origin_regex=r"https?://.*",
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

    async def close(self, code: int = 1000, reason: str = "call_completed") -> None:
        try:
            await self.ws.close(code=code, reason=reason)
        except Exception:
            pass


@app.websocket("/ws/call")
async def ws_call(ws: WebSocket):
    # Always accept the handshake first so ASGI never rejects with 400 Bad Request
    await ws.accept()

    try:
        from backend.core.db import get_db
        from backend.memory.session import SessionStore
        from backend.agent.engine import ConversationEngine
        from backend.services.provider_runtime import CloudProviderRuntime

        db = get_db()
        components = await CloudProviderRuntime(db).load_call_components()
        app.state.stt = components.stt
        app.state.engine = ConversationEngine(llm=components.llm)
        app.state.tts = components.tts
        if not getattr(app.state, "session_store", None):
            app.state.session_store = SessionStore()
    except Exception as exc:  # noqa: BLE001
        log.warning("failed to load cloud call pipeline: %s", exc)

    if app.state.stt is None or app.state.engine is None or app.state.tts is None:
        await ws.send_json({
            "type": "error",
            "message": "Call pipeline not configured: missing active STT, LLM or TTS in Model Directory",
        })
        await ws.close(code=1011, reason="call pipeline not configured: missing active STT, LLM or TTS")
        return

    # Base configuration from query parameters (if short)
    language = ws.query_params.get("lang", "en-IN")
    agent_name = ws.query_params.get("agent_name")
    custom_greeting = ws.query_params.get("greeting")
    system_prompt = ws.query_params.get("prompt")
    raw_sensitivity = ws.query_params.get("sensitivity")
    voice_profile_id = ws.query_params.get("voice_profile_id")
    voice_id = ws.query_params.get("voice_id") or ws.query_params.get("speaker")
    agent_id = ws.query_params.get("agent_id")
    org_id = ws.query_params.get("org_id")
    try:
        barge_in_sensitivity = int(raw_sensitivity) if raw_sensitivity else 70
    except Exception:
        barge_in_sensitivity = 70
    raw_vars = ws.query_params.get("variables")
    variables = {}
    if raw_vars:
        try:
            import json
            variables = json.loads(raw_vars)
        except Exception:
            variables = {}

    # Wait for incoming handshake messages (which can be a rich 'init' frame with full prompts/variables)
    buffered_frames = []
    import asyncio
    try:
        # Check initial frames for 'init' message, buffering any early audio frames
        for _ in range(15):
            msg = await asyncio.wait_for(ws.receive(), timeout=1.5)
            if msg.get("type") == "websocket.disconnect":
                return
            if msg.get("text"):
                try:
                    import json
                    data = json.loads(msg["text"])
                    if data.get("type") == "init":
                        language = data.get("lang", language)
                        agent_name = data.get("agent_name", agent_name)
                        custom_greeting = data.get("greeting", custom_greeting)
                        system_prompt = data.get("prompt", system_prompt)
                        voice_profile_id = data.get("voice_profile_id", voice_profile_id)
                        voice_id = data.get("voice_id", voice_id) or data.get("speaker", voice_id)
                        agent_id = data.get("agent_id", agent_id)
                        org_id = data.get("org_id", org_id)
                        if "variables" in data and isinstance(data["variables"], dict):
                            variables = data["variables"]
                        if "sensitivity" in data:
                            try:
                                barge_in_sensitivity = int(data["sensitivity"])
                            except Exception:
                                pass
                        break
                except Exception:
                    pass
            elif msg.get("bytes"):
                buffered_frames.append(msg["bytes"])
    except asyncio.TimeoutError:
        pass
    except Exception as exc:  # noqa: BLE001
        log.warning("ws handshake receive error: %s", exc)
        return

    # Resolve voice persona / speaker
    resolved_voice_id = voice_id
    if not resolved_voice_id and voice_profile_id:
        try:
            vp = await db.voice_profiles.find_one({"_id": voice_profile_id})
            if vp and vp.get("active_version_id"):
                vpv = await db.voice_profile_versions.find_one({"_id": vp["active_version_id"]})
                if vpv and "routes" in vpv and "tts" in vpv["routes"]:
                    resolved_voice_id = vpv["routes"]["tts"].get("provider_resource_id")
        except Exception as exc:
            log.warning("failed to resolve voice from voice_profile_id: %s", exc)

    if not resolved_voice_id and agent_id:
        try:
            agent_doc = await db.agents.find_one({"_id": agent_id})
            if agent_doc:
                agent_vpid = agent_doc.get("voice_profile_id")
                if agent_vpid:
                    vp = await db.voice_profiles.find_one({"_id": agent_vpid})
                    if vp and vp.get("active_version_id"):
                        vpv = await db.voice_profile_versions.find_one({"_id": vp["active_version_id"]})
                        if vpv and "routes" in vpv and "tts" in vpv["routes"]:
                            resolved_voice_id = vpv["routes"]["tts"].get("provider_resource_id")
        except Exception as exc:
            log.warning("failed to resolve voice from agent_id: %s", exc)

    # Smart persona mapping fallback based on agent name
    if not resolved_voice_id and agent_name:
        aname_lower = agent_name.lower()
        if "chitra" in aname_lower or "chaitra" in aname_lower:
            resolved_voice_id = "chaitra_hi_customer"
        elif "ishita" in aname_lower:
            resolved_voice_id = "ishita_mr_conversational"
        elif "kavya" in aname_lower:
            resolved_voice_id = "kavya_hi_conversational"
        elif "aditi" in aname_lower:
            resolved_voice_id = "aditi_en_stories"

    # Resolve agent prompt and knowledge base context
    if agent_id:
        try:
            agent_doc = await db.agents.find_one({"_id": agent_id})
            if agent_doc:
                if not org_id:
                    org_id = agent_doc.get("organization_id")
                strictness = "flexible"

                # Check requested version_id from query params, then active_version_id, then latest version
                target_vid = ws.query_params.get("version_id")
                version_doc = None
                if target_vid:
                    version_doc = await db.agent_versions.find_one({"_id": target_vid})
                if not version_doc:
                    active_vid = agent_doc.get("active_version_id")
                    if active_vid:
                        version_doc = await db.agent_versions.find_one({"_id": active_vid})
                if not version_doc:
                    # Fallback to latest draft or published version
                    version_doc = await db.agent_versions.find_one(
                        {"agent_id": agent_id}, sort=[("version", -1)]
                    )

                if version_doc:
                    cfg = version_doc.get("configuration") or {}
                    strictness = cfg.get("knowledge_strictness", "flexible")
                    if not system_prompt and cfg.get("system_prompt"):
                        system_prompt = cfg.get("system_prompt")
                    if not custom_greeting and cfg.get("greeting"):
                        custom_greeting = cfg.get("greeting")
                    if not resolved_voice_id and cfg.get("voice_id"):
                        resolved_voice_id = cfg.get("voice_id")
                    if not variables and cfg.get("input_variables"):
                        variables = cfg.get("input_variables")

                if org_id:
                    from backend.services.knowledge_service import KnowledgeService
                    kb_svc = KnowledgeService(db)
                    kb_context = await kb_svc.get_context_for_agent(agent_id, org_id, mode=strictness)
                    if kb_context:
                        system_prompt = (system_prompt or "") + f"\n\n{kb_context}"
                        log.info("injected knowledge base context into call session for agent=%s (mode=%s)", agent_id, strictness)
        except Exception as exc:
            log.warning("failed to resolve knowledge base for agent_id=%s: %s", agent_id, exc)

    log.info("ws call starting: lang=%s agent=%s voice_id=%s", language, agent_name, resolved_voice_id)

    # Credit / Trial Session Enforcement
    from backend.services.credit_service import CreditService
    import uuid
    import time

    credit_svc = CreditService(db)
    is_free_trial = True
    test_call_id = None
    session_start_time = 0
    max_duration_seconds = 180

    if org_id:
        org_doc = await db.organizations.find_one({"_id": org_id})
        free_tests_remaining = org_doc.get("settings", {}).get("free_test_sessions_remaining", 0) if org_doc else 0
        if free_tests_remaining > 0:
            await db.organizations.update_one(
                {"_id": org_id, "settings.free_test_sessions_remaining": {"$gt": 0}},
                {"$inc": {"settings.free_test_sessions_remaining": -1}}
            )
            is_free_trial = True
            max_duration_seconds = 180
            log.info("started free trial test session for org=%s, remaining was %s", org_id, free_tests_remaining)
        else:
            check = await credit_svc.can_start_call(org_id, required_credits=5)
            if not check.get("can_start", False):
                await ws.send_json({
                    "type": "error",
                    "message": "Minimum 5 credits required to run a test call. Free trial sessions exhausted.",
                })
                await ws.close(code=4002, reason="insufficient_credits")
                return
            test_call_id = f"test_{uuid.uuid4().hex[:12]}"
            await credit_svc.reserve(org_id, test_call_id, max_credits=5)
            is_free_trial = False
            org_max_mins = org_doc.get("settings", {}).get("max_call_duration_minutes", 7) if org_doc else 7
            max_duration_seconds = org_max_mins * 60
            log.info("started paid test session for org=%s with 5-credit hold (call_id=%s, cap=%sm)", org_id, test_call_id, org_max_mins)
    else:
        is_free_trial = True
        max_duration_seconds = 180

    from backend.call_session import CallSession

    session = CallSession(
        transport=BrowserTransport(ws),
        stt=app.state.stt,
        engine=app.state.engine,
        tts=app.state.tts,
        store=app.state.session_store,
        direction="inbound",
        language=language,
        agent_name=agent_name,
        custom_greeting=custom_greeting,
        system_prompt=system_prompt,
        variables=variables,
        barge_in_sensitivity=barge_in_sensitivity,
        voice_id=resolved_voice_id,
    )
    try:
        session_start_time = time.time()
        enforce_task = None

        async def _enforcement_monitor():
            try:
                if is_free_trial:
                    await asyncio.sleep(180.0)
                    try:
                        await ws.send_json({"type": "info", "text": "3-minute testing session ending now."})
                        await asyncio.sleep(0.5)
                        await ws.close(code=1000, reason="3-minute testing session ending now")
                    except Exception:
                        pass
                else:
                    if max_duration_seconds > 285:
                        await asyncio.sleep(285.0)
                        try:
                            await credit_svc.extend_hold(org_id, test_call_id, additional_credits=5)
                        except Exception as e:
                            log.warning("failed to extend hold on paid browser test: %s", e)
                        remaining = max_duration_seconds - 285.0
                        await asyncio.sleep(remaining)
                    else:
                        await asyncio.sleep(max_duration_seconds)
                    try:
                        await ws.send_json({"type": "info", "text": "Maximum call duration reached."})
                        await asyncio.sleep(0.5)
                        await ws.close(code=1000, reason="max_duration_reached")
                    except Exception:
                        pass
            except asyncio.CancelledError:
                pass
            except Exception as e:
                log.warning("session enforcement error: %s", e)

        enforce_task = asyncio.create_task(_enforcement_monitor())
        await session.start()
        for frame in buffered_frames:
            await session.feed_pcm16(frame)
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            text_data = msg.get("text")
            if text_data:
                try:
                    import json
                    d = json.loads(text_data)
                    if d.get("type") == "interrupt":
                        await session.handle_interrupt()
                except Exception:
                    pass
            frame = msg.get("bytes")
            if frame:
                await session.feed_pcm16(frame)
    except WebSocketDisconnect:
        log.info("browser call disconnected")
    except Exception as exc:  # noqa: BLE001
        log.exception("browser call error: %s", exc)
    finally:
        if enforce_task and not enforce_task.done():
            enforce_task.cancel()
        await session.finalize()
        if not is_free_trial and test_call_id and org_id:
            try:
                duration_s = int(time.time() - session_start_time) if session_start_time > 0 else 0
                await credit_svc.settle_duration(org_id, test_call_id, duration_seconds=duration_s)
            except Exception as e:
                log.warning("failed to settle test session credits: %s", e)


# ---------------------------------------------------------------------------
# Twilio telephony routes (preserved)
# ---------------------------------------------------------------------------
try:
    from backend.telephony.twilio import router as twilio_router  # noqa: E402
    app.include_router(twilio_router)
except Exception as exc:  # noqa: BLE001
    log.warning("Twilio router not loaded (ok if Twilio not configured): %s", exc)

# ---------------------------------------------------------------------------
# Vobiz telephony routes
# ---------------------------------------------------------------------------
try:
    from backend.telephony.vobiz import router as vobiz_router  # noqa: E402
    app.include_router(vobiz_router)
except Exception as exc:  # noqa: BLE001
    log.warning("Vobiz router not loaded: %s", exc)

# ---------------------------------------------------------------------------
# Plivo telephony routes
# ---------------------------------------------------------------------------
try:
    from backend.telephony.plivo import router as plivo_router  # noqa: E402
    app.include_router(plivo_router)
except Exception as exc:  # noqa: BLE001
    log.warning("Plivo router not loaded: %s", exc)

# ---------------------------------------------------------------------------
# Real-time Call Live Stream / Monitoring (for Studio Phone Testing & Live Dash)
# ---------------------------------------------------------------------------
@app.websocket("/ws/calls/{call_id}")
async def ws_call_monitor(ws: WebSocket, call_id: str):
    await ws.accept()
    from backend.telephony.broadcaster import call_broadcaster

    queue = call_broadcaster.subscribe(call_id)
    try:
        # Replay in-memory recent history so frontend immediately gets past turns
        history = call_broadcaster.get_history(call_id)
        if history:
            for evt in history:
                await ws.send_json(evt)
        else:
            # If broadcaster was restarted or empty, read turns from MongoDB
            db = get_db()
            if db is not None:
                turns = await db.turns.find({"call_id": call_id}).sort("ts", 1).to_list(60)
                for t in turns:
                    await ws.send_json({
                        "type": t.get("role"),
                        "text": t.get("text"),
                    })

        while True:
            event = await queue.get()
            await ws.send_json(event)
            if event.get("type") == "hangup":
                await asyncio.sleep(1.0)
                break
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log.warning("ws_call_monitor error for call %s: %s", call_id, exc)
    finally:
        call_broadcaster.unsubscribe(call_id, queue)

