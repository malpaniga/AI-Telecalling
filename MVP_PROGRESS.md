# MVP_PROGRESS.md
# AI Telecalling SaaS — Development Progress

**Last updated:** 2026-10-08  
**Current checkpoint:** M0 PASS — Repository Audit Complete  
**Next checkpoint:** M1 — MongoDB Foundation  

---

## CHECKPOINT HISTORY

---

### M0 — REPOSITORY AUDIT

```
Checkpoint: M0
Status: PASS
Started: 2026-10-08
Completed: 2026-10-08
Objective: Inspect entire existing repository; document architecture; 
           determine what to reuse vs change; create MVP_ARCHITECTURE.md

Implementation:
  - Cloned https://github.com/Risabkshetri/AI-Telecalling
  - Inspected all 30+ source files (backend + frontend)
  - Documented existing architecture in MVP_ARCHITECTURE.md
  - Documented technical decisions in MVP_DECISIONS.md
  - Documented test status in MVP_TEST_STATUS.md
  - Created this MVP_PROGRESS.md

Files changed:
  - MVP_ARCHITECTURE.md (created)
  - MVP_DECISIONS.md (created)
  - MVP_TEST_STATUS.md (created)
  - MVP_PROGRESS.md (created)

Database changes:
  - None (PostgreSQL still in place; MongoDB migration is M1)

API changes:
  - None

Environment variables:
  - None added yet

Tests:
  - Repository structure verified
  - All source files readable and understood
  - Existing codebase documented

Tests passed: 2
Tests failed: 0

Manual verification:
  - PASS: repository cloned and fully inspected
  - PASS: architecture documented

Known issues:
  - Backend uses PostgreSQL → will be replaced with MongoDB in M1
  - No authentication system
  - No multi-tenancy
  - No billing
  - Providers not abstracted
  - Real-estate-specific prompts and business logic

Remaining work:
  - None for M0 (audit only)

Next checkpoint: M1

Git commit: (see below)
```

---

## EXISTING CODEBASE SUMMARY

### What exists and works
- ✅ FastAPI application with async WebSocket support
- ✅ Transport-agnostic call session pipeline (`call_session.py`)
- ✅ Silero VAD endpointer with barge-in (`audio/vad.py`) — **excellent, preserve**
- ✅ LangGraph conversation state machine (`agent/engine.py`)
- ✅ Groq Whisper STT + Sarvam STT router (`audio/stt.py`)
- ✅ Sarvam TTS with streaming (`audio/tts.py`)
- ✅ Twilio Media Streams bridge (`telephony/twilio.py`)
- ✅ Redis session store (`memory/session.py`)
- ✅ PostgreSQL repository (`memory/repository.py`)
- ✅ 11 Indian languages support (`languages.py`)
- ✅ Next.js 14 dashboard with calls/leads/overview
- ✅ Structured logging with per-turn trace IDs

### What needs to be built
- ❌ MongoDB foundation (replace PostgreSQL)
- ❌ Authentication + JWT
- ❌ Multi-tenancy (organization_id isolation)
- ❌ RBAC
- ❌ Subscription plans (database-driven)
- ❌ Razorpay payment integration
- ❌ Wallet + calling credits
- ❌ Credit reservation + settlement
- ❌ Phone number inventory
- ❌ Provider abstractions (Telephony, STT, TTS, LLM, Payment)
- ❌ ElevenLabs TTS adapter
- ❌ Exotel telephony adapter
- ❌ OpenAI LLM adapter
- ❌ Mock providers for DEMO_MODE
- ❌ AI Voice Profiles (customer-facing)
- ❌ Provider Router (primary/fallback)
- ❌ Generic Agent Builder (templates)
- ❌ Lead CRM (import CSV/XLSX, DNC, deduplication)
- ❌ Campaign engine (state machine, concurrency, Redis workers)
- ❌ Campaign pre-flight validation
- ❌ Post-call processing (async)
- ❌ Usage tracking + cost accounting
- ❌ Customer dashboard (full SaaS)
- ❌ Super admin panel
- ❌ Appointments module
- ❌ Knowledge base
- ❌ Analytics
- ❌ Demo mode (DEMO_MODE=true)
- ❌ Fly.io deployment config
- ❌ Full documentation

### Key architectural changes required
- PostgreSQL → MongoDB Atlas (M1)
- Groq-only → OpenAI-compatible LLM provider abstraction (M8)
- Sarvam-only → TTS provider abstraction with ElevenLabs (M8)
- Twilio-only → Telephony provider abstraction with Exotel (M8)
- Real-estate prompts → template-driven generic prompts (M11)
- No auth → JWT + RBAC (M2)
- No billing → Razorpay + wallet (M4, M5)

---

## CHECKPOINT ROADMAP

| Checkpoint | Title | Status | Dependency |
|---|---|---|---|
| M0 | Repository Audit | **PASS** | — |
| M1 | MongoDB Foundation | TODO | M0 |
| M2 | Auth + Multi-Tenancy + RBAC | TODO | M1 |
| M3 | Plans + Subscriptions | TODO | M2 |
| M4 | Razorpay | TODO | M3 |
| M5 | Calling Packs + Wallet | TODO | M4 |
| M6 | Credit Reservation + Settlement | TODO | M5 |
| M7 | Phone Number Inventory | TODO | M6 |
| M8 | Provider Abstraction | TODO | M7 |
| M9 | AI Voice Profiles | TODO | M8 |
| M10 | Provider Router | TODO | M9 |
| M11 | Agent Builder | TODO | M10 |
| M12 | Lead CRM | TODO | M11 |
| M13 | Campaign Engine | TODO | M12 |
| M14 | Campaign Pre-flight | TODO | M13 |
| M15 | Real-Time AI Calling | TODO | M14 |
| M16 | Barge-In + Latency | TODO | M15 |
| M17 | Tools + Human Handoff | TODO | M16 |
| M18 | Appointments | TODO | M17 |
| M19 | Knowledge Base | TODO | M18 |
| M20 | Post-Call Processing | TODO | M19 |
| M21 | Usage + Cost | TODO | M20 |
| M22 | Customer Dashboard | TODO | M21 |
| M23 | Customer Billing | TODO | M22 |
| M24 | Super Admin | TODO | M23 |
| M25 | Revenue + Margin Analytics | TODO | M24 |
| M26 | Provider Operations | TODO | M25 |
| M27 | Reconciliation | TODO | M26 |
| M28 | Security Hardening | TODO | M27 |
| M29 | Automated Testing | TODO | M28 |
| M30 | Demo Mode | TODO | M29 |
| M31 | Production Deployment | TODO | M30 |
| M32 | Documentation | TODO | M31 |
| M33 | Final E2E Acceptance | TODO | M32 |
