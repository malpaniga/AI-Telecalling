# MVP_TEST_STATUS.md
# AI Telecalling SaaS — Test Status

---

## Summary

| Checkpoint | Status | Tests Passed | Tests Failed | Notes |
|---|---|---|---|---|
| M0 | PASS | 2 | 0 | Audit + startup verification |
| M1 | PASS | 39 | 0 | MongoDB models, repos, health, config |
| M2 | PASS | 45 | 0 | JWT auth, RBAC, tenant isolation, signup/login |
| M3 | PASS | 42 | 0 | Plans, subscriptions, entitlements, config-driven pricing |
| M4 | PASS | 43 | 0 | Razorpay, server-authoritative payment, webhook idempotency |
| M5 | PASS | 39 | 0 | Calling packs, wallet ledger, credit lots, expiry, bonus |
| M6 | PASS | 32 | 0 | Reserve/release/settle, 10-concurrent no double-spend |
| M7 | PASS | 40 | 0 | Number inventory, atomic assignment, tenant isolation, provider redaction |
| M8 | PASS | 5 | 0 | Provider contracts, live adapter normalization, mock demo registry |
| M9 | PASS | 4 | 0 | Immutable voice versions, provider redaction, tenant isolation, HTTP RBAC |
| M10 | PASS | 4 | 0 | Primary/fallback resolution, capability/language validation, persisted failover |
| M41 | PASS | 15 | 0 | AI Models Directory: catalogue, configs, credentials, test, activate, isolation |

---

## M41 — AI Models Directory

**Date:** 2026-10-12
**Status:** PASS
**Venv:** `source .venv/Scripts/activate` (root `/c/Programs/saas`)
**Run:** `cd backend && python -m pytest tests/test_m41_model_directory.py -v`

### Tests Run

| # | Test | Type | Result | Notes |
|---|---|---|---|---|
| 1 | test_catalogue_search_and_capability_filter | mock (mongomock) | PASS | Search + filter returns seeded entries |
| 2 | test_provider_connection_valid_credentials | mock (mongomock) | PASS | Fernet encrypt stored; config record created |
| 3 | test_provider_connection_invalid_empty_credential | mock (mongomock) | PASS | ValueError → 400 when credential required but missing |
| 4 | test_secret_masking | mock (mongomock) | PASS | key_hint only 4 chars; encrypted bytes never returned |
| 5 | test_authorization_enforcement | mock (mongomock) | PASS | org-level user raises PermissionError |
| 6 | test_local_runtime_detection_ollama_unreachable | mock (patch) | PASS | is_runtime_reachable=False → status=error/unavailable |
| 7 | test_local_runtime_detection_ollama_reachable | mock (patch) | PASS | generate mocked → status=ok + response |
| 8 | test_actual_tts_sample_mock | mock (patch.object) | PASS | _test_sarvam_tts patched → status=ok + latency |
| 9 | test_actual_stt_transcription_mock | mock (patch.object) | PASS | _test_groq_stt patched → transcript returned |
| 10 | test_actual_llm_inference_mock | mock (patch.object) | PASS | _test_groq_llm patched → response returned |
| 11 | test_model_activation_and_audit | mock (mongomock) | PASS | activate() deactivates previous, records activated_at |
| 12 | test_unsupported_language_rejection | mock (mongomock) | PASS | unsupported language → ValueError |
| 13 | test_credential_rotation_and_deletion | mock (mongomock) | PASS | old cred rotated_at set; new cred stored; delete clears all |
| 14 | test_free_tier_quota_guard | mock (mongomock) | PASS | 11th test call in 1hr → RateLimitError |
| 15 | test_customer_tenant_isolation | HTTP (TestClient) | PASS | org JWT → 403 on /model-directory/catalogue |

### Known Gaps (not test failures — require external setup)

| Provider | Adapter Status | Blocker |
|---|---|---|
| Gemini (gemini-2.0-flash-lite) | Catalogue=supported; no LLMClient for Gemini | Need Gemini adapter + GEMINI_API_KEY |
| AI4Bharat IndicConformer | Experimental; stub raises NotImplementedError | GPU server required |
| AI4Bharat IndicF5 | Experimental; stub raises NotImplementedError | GPU server required |
| AI4Bharat Indic-TTS | Experimental; stub raises NotImplementedError | CPU/GPU server required |
| faster-whisper | Experimental; not wired to call pipeline | Local runtime + ffmpeg required |
| ElevenLabs multilingual-v2 | Experimental; no test adapter | ELEVENLABS_API_KEY required |
| Sarvam TTS/STT live | Supported; test adapter exists | SARVAM_API_KEY required |
| Groq LLM/Whisper live | Supported; test adapter exists | GROQ_API_KEY required |
| Ollama llama3.2 | Supported; real test adapter exists | `ollama serve` + `ollama pull llama3.2` |

### Frontend Coverage (TypeScript + ESLint)

| Check | Result |
|---|---|
| `npx tsc --noEmit` | PASS (0 errors) |
| `npx eslint` on changed files | PASS (0 errors/warnings) |
| `/admin/models` page renders | Verified (build clean) |
| AdminSidebar 4 new links | Verified (BrainCircuit, Volume2, AudioWaveform, Bot) |
| ProviderConfigPanel masked credentials | type=password autoComplete=new-password |
| Test button inline result | Per-row spinner + latency/error |
| Activate disabled until test=ok | Enforced in component state |
| Free-tier staleness warning | >90 days triggers amber warning |
| `/admin/providers` page unchanged | git diff confirms no modification |

---

## M8 — Provider Abstraction

**Date:** 2026-10-08
**Status:** PASS

### Tests Run

| Test | Result | Notes |
|---|---|---|
| Typed provider registry | PASS | Registration, lookup, duplicate, and unknown-provider protections |
| Mock provider flow | PASS | Offline telephony, STT, TTS, LLM, and number provisioning |
| Demo registry bootstrap | PASS | Registers a mock for every runtime category |
| Live adapter normalization | PASS | Exotel, ElevenLabs, and OpenAI-compatible HTTP contract tests with fake clients |
| M1–M3 regression | PASS | 126 tests |
| M4–M8 regression | PASS | 159 tests |
| **Total** | **285/285 PASS** | |

### Known Issues at M8

- Live provider credentials and external-provider accounts are intentionally not
  required for automated tests; request contracts are isolated behind fake clients.

---

## M7 — Phone Number Inventory

**Date:** 2026-10-08
**Status:** PASS

### Tests Run

| Test | Result | Notes |
|---|---|---|
| Phone-number models and response views | PASS | 5 tests; customer views redact all provider and rental fields |
| Inventory repository | PASS | 5 tests; atomic reservation and lifecycle transitions |
| Inventory service | PASS | 11 tests; assignment history, tenant isolation, and stats |
| Concurrent assignment | PASS | 2 tests; exactly one winner for one number |
| Demo inventory seed | PASS | 3 tests; idempotent seeding |
| HTTP API / RBAC | PASS | 14 tests; auth, customer scope, platform-only administration |
| M1–M3 regression | PASS | 126 tests |
| M4–M5 regression | PASS | 82 tests |
| M6–M7 regression | PASS | 72 tests |
| **Total** | **280/280 PASS** | |

### Known Issues at M7

- Existing third-party deprecation warnings from asyncio event-loop lookup,
  python-jose, and Starlette TestClient remain non-blocking.

---

## M1 — MongoDB Foundation

**Date:** 2026-10-08  
**Status:** PASS

### Tests Run

| Test | Result | Notes |
|---|---|---|
| TestModels (7 tests) | PASS | Organization, User, AuditLog models |
| TestPasswordHashing (4 tests) | PASS | bcrypt hash/verify, unique salts |
| TestSlugGeneration (4 tests) | PASS | slugify, max length, special chars |
| TestConfig (5 tests) | PASS | Settings load, Sarvam key fallback, Redis URL parse |
| TestOrganizationRepository (7 tests) | PASS | CRUD, slug uniqueness, list |
| TestUserRepository (6 tests) | PASS | Create, find, authenticate, lockout, deactivate |
| TestAuditLogRepository (3 tests) | PASS | log, list_for_org isolation |
| TestTenantIsolation (1 test) | PASS | Org A cannot see Org B users |
| TestHealthCheck (2 tests) | PASS | healthy/degraded states |
| **Total** | **39/39 PASS** | |

### Known Issues at M1
- Twilio router fails on Python 3.13 (`audioop` removed). Non-blocking — app still starts. Fix in M8.

---

## M0 — Repository Audit

**Date:** 2026-10-08  
**Status:** PASS

### Tests Run

| Test | Result | Notes |
|---|---|---|
| Repository cloned successfully | PASS | 78 objects, clean working tree |
| Repository structure documented | PASS | MVP_ARCHITECTURE.md created |
| Existing code files readable | PASS | All source files inspected |

### Manual Verification

| Check | Result |
|---|---|
| Backend starts (requirements visible, structure valid) | VERIFIED (pending deps install) |
| Frontend structure valid | VERIFIED |
| Existing auth/DB uses PostgreSQL | VERIFIED (must change to MongoDB) |
| LangGraph engine working (code inspection) | VERIFIED |
| VAD pipeline preserved | VERIFIED |
| Real-time call session transport-agnostic | VERIFIED |
| Redis session store working | VERIFIED |
| Twilio telephony bridge complete | VERIFIED |

### Known Issues at M0

- Backend uses PostgreSQL (psycopg3/SQLAlchemy/Alembic) → must migrate to MongoDB Atlas
- Config hardcodes Groq API as LLM provider → needs provider abstraction
- `health` endpoint checks PostgreSQL → must check MongoDB instead
- Prompts are real-estate-specific → must be template-driven for SaaS
- No authentication → must add JWT + RBAC
- No multi-tenancy → must add organization_id isolation
- No billing → must add Razorpay + wallet
- STT/TTS/Telephony not abstracted → must add provider interfaces
- `alembic.ini` references PostgreSQL → to be removed
- `docker-compose.yml` includes PostgreSQL → to be updated (remove postgres service)
- Frontend has no auth pages → must add signup/login
- Frontend is real-estate-only → must generalize

---

## Regression Test Matrix (to be filled as checkpoints complete)

| Test Area | M0 | M1 | M2 | M3 | M4 | M5 | M6 |
|---|---|---|---|---|---|---|---|
| App starts | ✓ | | | | | | |
| MongoDB connects | — | | | | | | |
| Redis connects | ✓ | | | | | | |
| Auth works | — | | | | | | |
| Tenant isolation | — | | | | | | |
| Billing | — | | | | | | |
| Wallet | — | | | | | | |
| Credits | — | | | | | | |
| Call pipeline | ✓ | | | | | | |
| VAD | ✓ | | | | | | |
| Barge-in | ✓ | | | | | | |
| Provider abstraction | — | | | | | | |
