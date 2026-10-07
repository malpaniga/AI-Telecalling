# MVP_ARCHITECTURE.md
# AI Telecalling SaaS — Architecture Reference

Last updated: M0 (Initial Audit)

---

## 1. Repository Origin

**Source:** https://github.com/Risabkshetri/AI-Telecalling

The existing codebase is a working **Real Estate Voice Agent** demo ("Kavya") built
with FastAPI + LangGraph + Groq (STT/LLM) + Sarvam (TTS) + Twilio (telephony) +
PostgreSQL + Redis + Next.js 14 dashboard.

---

## 2. Existing Architecture (AS-IS)

### 2.1 Backend — Python / FastAPI

```
backend/
├── main.py               — FastAPI app, lifespan, /ws/call (BrowserTransport),
│                           /health (checks Postgres + Redis + Groq key), /api/languages
├── config.py             — pydantic-settings; loads backend/.env
├── logging_setup.py      — structured logging, per-turn trace_id (ContextVar)
├── languages.py          — 11 Indian BCP-47 language codes (Sarvam-backed)
├── call_session.py       — transport-agnostic call pipeline (VAD, barge-in,
│                           STT, LLM, TTS, persistence). Works with any Transport.
├── audio/
│   ├── vad.py            — Silero VAD (onnxruntime, no torch) + webrtcvad fallback;
│   │                       endpointer state machine: speech_start / utterance events
│   ├── stt.py            — STTClient (Groq Whisper), SarvamSTT (Saaras v3 codemix),
│   │                       STTRouter (routes by language)
│   └── tts.py            — TTSEngine ABC; PiperEngine (local CPU), SarvamEngine
│                           (REST + streaming), OrpheusEngine (stub/future)
├── agent/
│   ├── state.py          — ConversationState TypedDict; stages: greeting/
│   │                       qualification/objection/booking/end; SLOT_KEYS
│   ├── engine.py         — LangGraph graph (understand → route); run_turn()
│   │                       yields sentences for streaming TTS
│   ├── llm.py            — LLMClient (Groq AsyncGroq); stream_sentences(),
│   │                       complete_json() for structured extraction
│   ├── prompts.py        — PERSONA, per-stage system prompts, EXTRACTION_SYSTEM_PROMPT
│   │                       (real-estate-specific / India-aware)
│   └── scoring.py        — score_lead(), lead_status(), call_outcome()
├── memory/
│   ├── session.py        — SessionStore (Redis asyncio); save/load/delete
│   │                       live call state (session:{call_id}, 1h TTL)
│   └── repository.py     — Postgres CRUD: start_call, add_turn, finalize_call,
│                           list_calls, get_call, list_leads, get_stats
├── telephony/
│   └── twilio.py         — TwilioTransport; TwiML webhook (/twiml/voice);
│                           /ws/twilio (Media Streams bridge); /calls/outbound
├── db/
│   ├── models.py         — SQLAlchemy async models: Lead, Call, Turn, Booking
│   ├── database.py       — async engine + async_session factory (psycopg3)
│   └── migrations/       — Alembic; one migration: initial schema
├── api/
│   └── routes.py         — /api/stats, /api/calls, /api/calls/{id}, /api/leads
└── static/               — minimal browser test page (index.html)
```

### 2.2 Frontend — Next.js 14 / TypeScript / Tailwind

```
frontend/
├── app/
│   ├── page.tsx          — Overview dashboard (stats + recent calls)
│   ├── call/             — Browser test call page (WebSocket mic)
│   ├── calls/            — Call list page
│   │   └── [id]/         — Call detail / transcript
│   └── leads/            — Lead pipeline table
├── components/
│   ├── nav.tsx           — Topbar
│   └── ui.tsx            — Badge, Metric, Panel, Score components
└── lib/api.ts            — Typed fetch wrappers for all backend endpoints
```

### 2.3 Database (Current) — PostgreSQL

Collections/tables (Alembic-managed):
- `leads` — id, name, phone, email, budget, timeline, city, property_type, score, status
- `calls` — id, lead_id, direction, status, outcome, started_at, ended_at, duration_s, avg_latency_ms
- `turns` — id, call_id, role, text, stage, latency_ms, ts
- `bookings` — id, lead_id, call_id, scheduled_for, property_ref, status

### 2.4 Runtime (Current) — Redis

- `session:{call_id}` → JSON-serialized ConversationState (1h TTL)

---

## 3. Target Architecture (TO-BE)

### 3.1 Core Changes

| Concern | Current | Target |
|---|---|---|
| Primary database | PostgreSQL (psycopg3/SQLAlchemy) | **MongoDB Atlas** (motor/pymongo) |
| Schema management | Alembic migrations | MongoDB collections + indexes created in code |
| Config | Flat pydantic-settings + Groq-specific fields | Extended settings + MongoDB URI |
| Authentication | None | JWT + org-scoped RBAC |
| Multi-tenancy | None | organization_id on every document |
| Business domain | Real estate only | Generic SaaS (templates-based) |
| Telephony | Twilio only (hardcoded) | Provider abstraction (Exotel, Twilio, Mock) |
| STT | Groq Whisper + Sarvam (hardcoded) | Provider abstraction (Sarvam, Mock) |
| TTS | Piper / Sarvam (hardcoded) | Provider abstraction (ElevenLabs, Sarvam, Mock) |
| LLM | Groq only (hardcoded) | Provider abstraction (OpenAI, OpenAI-compat, Mock) |
| Billing | None | Razorpay + wallet + credits |
| Admin | None | Super admin panel |
| Payments | None | Razorpay (server-authoritative) |
| Deployment | Local / ngrok | Fly.io |
| Frontend | Real estate dashboard | Full SaaS customer + admin dashboard |

### 3.2 Target Module Layout

```
backend/
├── config.py                     — extended; MongoDB URI, Redis, all providers
├── main.py                       — updated; MongoDB lifespan, new routers
├── core/
│   ├── db.py                     — MongoDB motor client + collection helpers
│   ├── redis.py                  — Redis client factory
│   ├── auth.py                   — JWT issue/verify, FastAPI dependencies
│   ├── rbac.py                   — role checks, tenant isolation middleware
│   ├── errors.py                 — standardized error responses
│   └── health.py                 — health check endpoints (all providers)
├── providers/
│   ├── base.py                   — Abstract interfaces (Telephony, STT, TTS, LLM, Payment, PhoneNumber)
│   ├── registry.py               — ProviderRegistry + ProviderRouter
│   ├── telephony/
│   │   ├── twilio.py             — adapted from existing telephony/twilio.py
│   │   ├── exotel.py             — new
│   │   └── mock.py               — new (DEMO_MODE)
│   ├── stt/
│   │   ├── sarvam.py             — adapted from existing audio/stt.py
│   │   └── mock.py
│   ├── tts/
│   │   ├── elevenlabs.py         — new
│   │   ├── sarvam.py             — adapted from existing audio/tts.py
│   │   └── mock.py
│   ├── llm/
│   │   ├── openai.py             — new (replaces groq-specific llm.py)
│   │   └── mock.py
│   └── payment/
│       ├── razorpay.py           — new
│       └── mock.py
├── models/                       — Pydantic models / MongoDB document schemas
│   ├── organization.py
│   ├── user.py
│   ├── subscription.py
│   ├── billing.py                — wallet, credit_lot, order, payment, invoice
│   ├── phone_number.py
│   ├── voice_profile.py
│   ├── agent.py
│   ├── lead.py
│   ├── campaign.py
│   ├── call.py
│   ├── appointment.py
│   └── ...
├── repositories/                 — MongoDB data access layer
│   ├── base.py
│   ├── organization_repo.py
│   ├── user_repo.py
│   ├── billing_repo.py
│   ├── lead_repo.py
│   ├── campaign_repo.py
│   ├── call_repo.py
│   └── ...
├── services/                     — Business logic (calls repos, providers)
│   ├── auth_service.py
│   ├── billing_service.py
│   ├── wallet_service.py
│   ├── campaign_service.py
│   ├── call_service.py
│   └── ...
├── api/
│   ├── v1/
│   │   ├── auth.py
│   │   ├── organizations.py
│   │   ├── subscriptions.py
│   │   ├── billing.py
│   │   ├── voice_profiles.py
│   │   ├── agents.py
│   │   ├── leads.py
│   │   ├── campaigns.py
│   │   ├── calls.py
│   │   ├── appointments.py
│   │   ├── analytics.py
│   │   └── admin/
│   │       ├── organizations.py
│   │       ├── providers.py
│   │       ├── revenue.py
│   │       └── ...
├── audio/                        — PRESERVED from existing (vad.py, core pipeline)
│   ├── vad.py                    — unchanged (Silero/webrtcvad)
│   └── ...
├── agent/                        — PRESERVED and GENERALIZED
│   ├── engine.py                 — generalized from real-estate to generic
│   ├── state.py                  — generalized stages + generic slots
│   ├── prompts.py                — template-driven prompts (not real-estate-specific)
│   ├── llm.py                    — generalized to use LLM provider abstraction
│   └── scoring.py                — generalized scoring
├── call_session.py               — PRESERVED; uses provider abstractions
├── workers/
│   ├── campaign_worker.py        — campaign execution (Redis-coordinated)
│   └── post_call_worker.py       — async post-call processing
└── ...
```

### 3.3 MongoDB Collections (Target)

Implemented incrementally per checkpoint:

| Collection | Checkpoint |
|---|---|
| organizations | M1 |
| users | M1 |
| audit_logs | M1 |
| subscription_plans | M3 |
| subscriptions | M3 |
| orders | M4 |
| payments | M4 |
| invoices | M4 |
| webhook_events | M4 |
| wallets | M5 |
| wallet_transactions | M5 |
| credit_lots | M5 |
| usage_events | M6 |
| phone_numbers | M7 |
| phone_number_assignments | M7 |
| provider_configs | M8 |
| voice_profiles | M9 |
| voice_profile_versions | M9 |
| provider_routes | M10 |
| agents | M11 |
| agent_versions | M11 |
| business_templates | M11 |
| knowledge_bases | M19 |
| knowledge_documents | M19 |
| leads | M12 |
| dnc_entries | M12 |
| campaigns | M13 |
| calls | M15 |
| transcripts | M15 |
| appointments | M18 |
| provider_usage | M21 |
| analytics_daily | M25 |
| notifications | M22 |

---

## 4. Provider Abstraction Model

### 4.1 Key Principle

Customer selects → "Marathi AI Voice"  
Platform internally resolves → Telephony provider + STT provider + LLM + TTS + voice ID

Customer API responses NEVER contain:
- provider name (ElevenLabs, Sarvam, etc.)
- provider model IDs
- provider API keys
- provider costs
- internal routing config

Customer-facing fields:
- `voice_profile_id` (UUID)
- `voice_profile_version` (integer)
- `display_name` ("Marathi AI Voice")
- `language` ("mr-IN")

Internal-only fields (admin only):
- `provider` ("elevenlabs")
- `provider_resource_id` ("21m00Tcm4TlvDq8ikWAM")
- `provider_metadata` ({...})
- `provider_cost_per_char` (integer paise)

### 4.2 Provider Registry Pattern

```python
# NEVER in core code:
if provider == "elevenlabs":
    voice_id = agent.elevenlabs_voice_id  # WRONG

# ALWAYS:
route = registry.get_tts_route(voice_profile_version)
await route.provider.synthesize(text, route.provider_resource_id)  # RIGHT
```

---

## 5. Billing Model

```
Subscription (plan entitlements)
+
Calling Packs (calling credits)
+
Phone Number Rental (per number per month)
+
Add-ons (optional)
```

### 5.1 Credits

- 1 credit = 1 billable second (integer, never float)
- UI shows approximate minutes
- Stored in `wallets` (available_credits, reserved_credits)
- Every movement = immutable ledger entry in `wallet_transactions`
- Lots tracked in `credit_lots` (for expiry)

### 5.2 Money

- All monetary values in integer paise (never float)
- `1 INR = 100 paise`
- `price_paise: int` (never `price: float`)

---

## 6. Multi-Tenancy

Every customer-owned document has `organization_id` (string UUID).

Roles:
```
Platform: platform_owner, platform_admin, support, billing_admin
Organization: organization_owner, organization_admin, manager, agent, viewer
```

Authorization is server-side RBAC. Frontend role restrictions are display-only.

---

## 7. Real-Time Call Pipeline (PRESERVED)

The existing transport-agnostic `call_session.py` architecture is excellent and
will be preserved with minimal changes:

```
Transport (Twilio/Exotel/Mock/Browser)
↓ PCM16
VAD Endpointer (Silero — PRESERVED)
↓ utterance
STTProvider (via abstraction)
↓ transcript
ConversationEngine / LangGraph (GENERALIZED)
↓ sentences
LLMProvider (via abstraction)
↓ text
TTSProvider (via abstraction)
↓ PCM16
Transport.play()
```

Barge-in: SPEECH_START → cancel responder → Transport.clear() — PRESERVED.

---

## 8. Deployment Target

```
Fly.io:
  app (FastAPI/uvicorn)     — /api, /ws, /health
  worker (campaign worker)  — Redis queue consumer
  Redis                     — Fly Redis (or Upstash)
  MongoDB Atlas             — external (not on Fly.io)

HTTPS/WSS: Fly.io auto-TLS
Webhooks: Fly.io public URL
```

---

## 9. Environment Variables (Target .env.example)

```
APP_ENV=development
SECRET_KEY=change-me

MONGODB_URI=mongodb+srv://...
MONGODB_DATABASE=telecalling_saas

REDIS_URL=redis://localhost:6379/0

RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...

EXOTEL_API_KEY=...
EXOTEL_API_TOKEN=...
EXOTEL_SID=...

TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

SARVAM_API_KEY=...

ELEVENLABS_API_KEY=...

OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1

GROQ_API_KEY=...

DEMO_MODE=false

PUBLIC_BASE_URL=https://your-domain.fly.dev
```

---

## 10. Reuse vs. Replace Decision Table

| Component | Decision | Reason |
|---|---|---|
| `audio/vad.py` | PRESERVE AS-IS | Excellent Silero VAD; battle-tested |
| `call_session.py` | PRESERVE / MINOR ADAPT | Transport-agnostic design is correct |
| `telephony/twilio.py` | ADAPT into provider | Move to `providers/telephony/twilio.py` |
| `audio/stt.py` | ADAPT into provider | Move to `providers/stt/sarvam.py` etc. |
| `audio/tts.py` | ADAPT into provider | Move to `providers/tts/sarvam.py` etc. |
| `agent/engine.py` | GENERALIZE | Remove real-estate hardcoding |
| `agent/llm.py` | ADAPT → LLMProvider | Replace Groq-specific with OpenAI-compat |
| `agent/state.py` | GENERALIZE | Generic slots + stages |
| `agent/prompts.py` | TEMPLATE-DRIVE | Remove hardcoded real-estate content |
| `agent/scoring.py` | GENERALIZE | Template-configurable scoring |
| `db/models.py` | REPLACE | PostgreSQL → MongoDB (motor) |
| `db/database.py` | REPLACE | SQLAlchemy → motor async |
| `memory/repository.py` | REPLACE | MongoDB repositories |
| `memory/session.py` | PRESERVE / MINOR ADAPT | Redis session store pattern is correct |
| `api/routes.py` | REPLACE / EXTEND | New versioned API under /api/v1 |
| `config.py` | EXTEND | Add MongoDB URI, Redis URL, provider keys |
| `frontend/` | EXTEND | Keep Next.js; add SaaS pages |
| Alembic | REMOVE | Not needed for MongoDB |
| `alembic.ini` | REMOVE | Not needed |
| `docker-compose.yml` | UPDATE | Postgres → not needed; keep Redis |
