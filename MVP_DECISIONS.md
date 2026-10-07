# MVP_DECISIONS.md
# AI Telecalling SaaS — Technical Decisions Log

---

## D001 — MongoDB Atlas as primary database (not PostgreSQL)
**Status:** DECIDED  
**Reason:** Commercial SaaS requirement. MongoDB's document model fits multi-tenant
SaaS well (organization-scoped documents, flexible custom_fields on leads, provider
metadata on routes). PostgreSQL from existing repo is removed.  
**Impact:** Remove SQLAlchemy/Alembic/psycopg3; add motor (async MongoDB driver).

## D002 — Redis for runtime coordination only
**Status:** DECIDED  
**Reason:** Redis is ephemeral. Live call sessions, campaign worker locks, credit
reservation locks. NOT for durable data. MongoDB is source of truth.  
**Impact:** Preserve `memory/session.py` pattern; add campaign worker coordination.

## D003 — Provider abstractions (no core provider branching)
**Status:** DECIDED  
**Reason:** Customer must never see provider details. "Marathi AI Voice" must be
reroutable to a different TTS provider without customer config changes.  
**Impact:** All provider-specific code lives in `providers/` adapters. Core code
uses abstract interfaces only.

## D004 — Existing VAD + call pipeline preserved
**Status:** DECIDED  
**Reason:** The Silero VAD endpointer, barge-in logic, and transport-agnostic
`CallSession` are well-tested and production-quality. No reason to replace.  
**Impact:** `audio/vad.py` and `call_session.py` kept; only minor adaptations for
provider abstractions.

## D005 — Money in integer paise; credits in integer seconds
**Status:** DECIDED  
**Reason:** Float arithmetic must never touch billing. 1 INR = 100 paise (integer).
1 credit = 1 billable second (integer).  
**Impact:** All pricing fields in MongoDB are `int` (paise). Wallet fields are `int`.

## D006 — Subscription + calling packs are separate
**Status:** DECIDED  
**Reason:** Subscription controls entitlements (feature gates). Calling packs control
usage (credits). They must not be conflated.  
**Impact:** `subscriptions` and `wallets/credit_lots` are separate collections.

## D007 — Razorpay is server-authoritative
**Status:** DECIDED  
**Reason:** Frontend must never determine payment amount. Backend creates orders,
verifies payment, verifies webhook signatures.  
**Impact:** Frontend sends `plan_id` or `calling_pack_id`. Backend looks up price.

## D008 — Real-estate prompts replaced with template-driven generic prompts
**Status:** DECIDED  
**Reason:** SaaS must serve any business. Solar, real estate, insurance etc. are
templates, not core logic.  
**Impact:** `agent/prompts.py` becomes template-driven. Business templates stored in
`business_templates` collection.

## D009 — Groq client replaced with OpenAI-compatible abstraction
**Status:** DECIDED  
**Reason:** Groq is OpenAI-compatible. The LLMProvider abstraction uses the OpenAI
SDK with configurable base_url. Groq is just one route configuration.  
**Impact:** `agent/llm.py` refactored to use `providers/llm/openai.py` adapter.

## D010 — Frontend: Next.js 14 preserved, pages extended
**Status:** DECIDED  
**Reason:** Working Next.js app with good component structure. Adding SaaS pages
(subscription, billing, admin) on top rather than rewriting.  
**Impact:** Extend existing frontend; add new route groups for SaaS features.

## D011 — Demo mode (DEMO_MODE=true) mocks all external providers
**Status:** DECIDED  
**Reason:** Full SaaS workflow must be testable without paid external APIs.  
**Impact:** Mock providers for telephony, STT, TTS, LLM, payment. Seed data in M30.

## D012 — Fly.io for deployment; MongoDB Atlas external
**Status:** DECIDED  
**Reason:** MongoDB Atlas must NOT run on Fly.io (managed Atlas is the right choice).
Fly.io hosts API + worker + Redis.  
**Impact:** Fly.io deployment config created in M31.

## D013 — LangGraph engine generalized, not removed
**Status:** DECIDED  
**Reason:** LangGraph state machine is well-structured. Generalized to support
configurable stages and template-driven slots instead of hardcoded real-estate fields.  
**Impact:** `agent/engine.py` adapted; stages and slot_keys become agent configuration.

## D014 — JWT authentication with organization-scoped tokens
**Status:** DECIDED  
**Reason:** Standard JWT with organization_id and role in claims. No session store
for auth (stateless JWT); refresh tokens stored in Redis for revocation.  
**Impact:** New `core/auth.py`. Each API endpoint checks org isolation.

## D015 — Credit reservation uses Redis atomic operations
**Status:** DECIDED  
**Reason:** Prevent double-spending during concurrent calls. Reserve credits in Redis
(fast, atomic) before call starts. Settle to MongoDB after call ends.  
**Impact:** Redis keys: `wallet_reserve:{org_id}:{call_id}`. Lua scripts for atomic ops.

## D016 — Solar is a business template, not special code
**Status:** DECIDED  
**Reason:** The SaaS must be generic. Solar-specific workflows (site survey, energy
savings, etc.) are configured via `business_templates` collection, not code paths.  
**Impact:** No `if business_type == "solar"` in core code.

## D017 — Alembic and PostgreSQL removed entirely
**Status:** DECIDED  
**Reason:** Target is MongoDB Atlas. No Alembic, no psycopg3, no SQLAlchemy.  
**Impact:** M1 removes these deps; adds motor, pymongo.

## D018 — Phone number inventory as platform resource
**Status:** DECIDED  
**Reason:** Customers rent numbers from platform inventory. Platform buys/provisions
numbers from telephony providers. Customers never see provider resource IDs.  
**Impact:** `phone_numbers` collection with `organization_id=null` (available) or
assigned to org. `phone_number_assignments` tracks history.

## D019 — Voice profile versions pin active campaigns
**Status:** DECIDED  
**Reason:** Campaigns must not break if admin changes a voice profile. Active
campaigns pin `voice_profile_version` at campaign creation. Changing a profile
creates a new version; old version remains valid for running campaigns.  
**Impact:** `voice_profiles` → `voice_profile_versions` (immutable once published).

## D020 — Webhook events stored with idempotency keys
**Status:** DECIDED  
**Reason:** Razorpay (and other providers) may send duplicate webhooks. Processing
must be idempotent.  
**Impact:** `webhook_events` collection with `event_id` unique index. Processed flag.
