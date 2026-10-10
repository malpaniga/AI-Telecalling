# AI Telecalling SaaS — Developer Guide

Complete reference for setting up, configuring, and extending the platform.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Installation](#installation)
3. [Environment Variables](#environment-variables)
4. [Local Development](#local-development)
5. [MongoDB Atlas Setup](#mongodb-atlas-setup)
6. [Redis Setup](#redis-setup)
7. [Provider Configuration](#provider-configuration)
   - [Razorpay (Payments)](#razorpay-payments)
   - [Twilio (Telephony)](#twilio-telephony)
   - [Exotel (Telephony)](#exotel-telephony)
   - [Sarvam (STT + TTS)](#sarvam-stt--tts)
   - [ElevenLabs (TTS)](#elevenlabs-tts)
   - [OpenAI / Groq (LLM)](#openai--groq-llm)
8. [AI Voice Profiles](#ai-voice-profiles)
9. [Business Templates & Agents](#business-templates--agents)
10. [Campaign Engine](#campaign-engine)
11. [Demo Mode](#demo-mode)
12. [Deployment (Fly.io)](#deployment-flyio)
13. [Testing](#testing)
14. [Adding a New Provider](#adding-a-new-provider)
15. [Creating a Voice Profile](#creating-a-voice-profile)
16. [Security Notes](#security-notes)

---

## Architecture Overview

```
Customer
  ↓ signup → org → subscription
  ↓ import leads → create campaign
  ↓ campaign starts → worker dials leads

Campaign Worker (Redis-coordinated)
  ↓ reserve credits → initiate call
  ↓ telephony provider → real-time call
  ↓ VAD → STT → LangGraph engine → LLM → TTS → caller
  ↓ post-call → transcript → qualification → lead update
  ↓ settle credits → analytics → usage event
```

**Key abstraction:** Customer selects "Marathi AI Voice" — the platform
internally routes to the configured providers (Telephony, STT, LLM, TTS).
Provider details are never exposed to customers.

---

## Installation

### Prerequisites

- Python 3.13+
- Node 20+ (frontend)
- Docker (Redis)
- MongoDB Atlas account (free tier works for dev)

### Backend

```bash
git clone https://github.com/Risabkshetri/AI-Telecalling
cd AI-Telecalling

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Copy and configure environment
cp .env.example backend/.env
# Edit backend/.env with your keys
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

---

## Environment Variables

All variables go in `backend/.env`. Required for full functionality:

| Variable | Required | Description |
|---|---|---|
| `MONGODB_URI` | ✅ | MongoDB Atlas connection string |
| `MONGODB_DATABASE` | ✅ | Database name (default: `telecalling_saas`) |
| `REDIS_URL` | ✅ | Redis connection (default: `redis://localhost:6379/0`) |
| `SECRET_KEY` | ✅ | JWT signing key — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `RAZORPAY_KEY_ID` | Billing | Razorpay API key ID |
| `RAZORPAY_KEY_SECRET` | Billing | Razorpay API key secret |
| `RAZORPAY_WEBHOOK_SECRET` | Billing | Razorpay webhook signing secret |
| `SARVAM_API_KEY` | Calls | Sarvam STT + TTS API key |
| `GROQ_API_KEY` | Calls | Groq STT + LLM API key |
| `ELEVENLABS_API_KEY` | TTS | ElevenLabs voice API key |
| `OPENAI_API_KEY` | LLM | OpenAI API key |
| `TWILIO_ACCOUNT_SID` | Telephony | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Telephony | Twilio Auth Token |
| `TWILIO_PHONE_NUMBER` | Telephony | Twilio phone number (E.164) |
| `PUBLIC_BASE_URL` | Telephony | Public HTTPS URL for webhooks |
| `DEMO_MODE` | Dev | Set `true` to use mock providers |

See `.env.example` for all options.

---

## Local Development

### Start infrastructure

```bash
docker compose up -d   # Starts Redis (MongoDB Atlas is external)
```

### Run the API server

```bash
cd /path/to/AI-Telecalling
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: http://localhost:8000/docs

### Run the campaign worker

```bash
python -m backend.workers.campaign_worker
```

### Seed demo data

```bash
# Set DEMO_MODE=true in backend/.env, then:
curl -X POST http://localhost:8000/api/v1/demo/seed \
  -H "Authorization: Bearer <platform-admin-token>"
```

Or via the demo API after login as platform admin.

---

## MongoDB Atlas Setup

1. Create a free cluster at https://cloud.mongodb.com
2. Create a database user with read/write access
3. Whitelist your IP (or use 0.0.0.0/0 for dev)
4. Get the connection string: **Drivers > Python**
5. Set `MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/`
6. Set `MONGODB_DATABASE=telecalling_saas`

Indexes are created automatically on startup via `core/db.py::_ensure_indexes()`.

---

## Redis Setup

### Local (Docker)

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

Set `REDIS_URL=redis://localhost:6379/0`

### Production (Fly.io)

```bash
flyctl redis create
```

Redis is used for:
- JWT refresh token revocation keys (`refresh_revoked:{jti}`)
- Live call session state (`session:{call_id}`)
- Credit reservations (`credit_reserve:{org}:{call}`)
- Campaign active call counter (`campaign_active_calls:{id}`)
- Rate limiting counters (`rate_limit:{type}:{key}`)

---

## Provider Configuration

### Razorpay (Payments)

1. Create account at https://razorpay.com
2. Dashboard → Settings → API Keys → Generate Key
3. Set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`
4. Webhooks → Add webhook URL: `https://yourdomain.com/api/v1/billing/webhook`
5. Events to subscribe: `payment.captured`, `payment.failed`, `refund.processed`
6. Copy webhook secret → `RAZORPAY_WEBHOOK_SECRET`

**Security:** The platform verifies every webhook with HMAC-SHA256.
Amount is ALWAYS looked up from the database — never trusted from frontend.

### Twilio (Telephony)

1. Create account at https://twilio.com
2. Get Account SID and Auth Token from console
3. Buy a phone number with Voice capability
4. Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
5. Expose backend with ngrok for local: `ngrok http 8000`
6. Set `PUBLIC_BASE_URL=https://your-subdomain.ngrok-free.app`

Twilio bridges 8kHz μ-law audio to the 16kHz PCM call pipeline via Media Streams.

### Exotel (Telephony)

1. Create account at https://exotel.com
2. Get API Key, API Token, and Account SID
3. Set `EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`, `EXOTEL_SID`

### Sarvam (STT + TTS)

1. Create account at https://dashboard.sarvam.ai
2. Get API key → `SARVAM_API_KEY`
3. STT: Saaras v3 (`saaras:v3`) — Indic languages with code-mixing
4. TTS: Bulbul v3 (`bulbul:v3`) — 10+ Indian voices
5. Set `TTS_ENGINE=sarvam`

Best for Indian languages (Hindi, Marathi, Tamil, etc.).

### ElevenLabs (TTS)

1. Create account at https://elevenlabs.io
2. API Keys → Generate → `ELEVENLABS_API_KEY`
3. Voice profiles use ElevenLabs via `provider_resource_id` (voice ID)
4. Customer-facing: they see "Marathi AI Voice", not the ElevenLabs voice ID

### OpenAI / Groq (LLM)

Groq (OpenAI-compatible):
1. https://console.groq.com → API Keys → `GROQ_API_KEY`
2. Models: `openai/gpt-oss-20b` (conversation), `llama-3.1-8b-instant` (extraction)

OpenAI:
1. https://platform.openai.com → API Keys → `OPENAI_API_KEY`
2. Set `OPENAI_BASE_URL=https://api.openai.com/v1`, `OPENAI_MODEL=gpt-4o-mini`

---

## AI Voice Profiles

Voice profiles hide all provider complexity from customers.

**Customer sees:** "Marathi AI Voice"
**Platform controls:** Telephony + STT + LLM + TTS provider + model + voice ID

### Creating a voice profile (admin)

```bash
# 1. Create profile
POST /api/v1/voice-profiles
{
  "display_name": "Marathi AI Voice",
  "language": "mr-IN",
  "description": "Native Marathi AI voice"
}

# 2. Create version with provider routes (admin only)
POST /api/v1/voice-profiles/{id}/versions
{
  "routes": {
    "telephony": {"provider": "twilio"},
    "stt": {"provider": "sarvam", "provider_language": "mr-IN"},
    "llm": {"provider": "openai", "provider_model": "gpt-4o-mini"},
    "tts": {"provider": "elevenlabs", "provider_resource_id": "voice_id_here"}
  }
}
```

**Provider details (routes) are never returned to customer API calls.**
Changing provider routes creates a new version. Active campaigns pin a version.

---

## Business Templates & Agents

7 built-in templates (configuration-driven, not code):

| Template | Slug | Primary slots |
|---|---|---|
| Generic | `generic` | name, interest |
| Solar | `solar` | monthly_bill, roof_type, home_ownership |
| Real Estate | `real-estate` | budget, timeline, city, property_type |
| Insurance | `insurance` | coverage_type, current_insurer |
| Education | `education` | course, qualification |
| Home Services | `home-services` | service_type, location |
| Automotive | `automotive` | vehicle_type, budget |

Creating an agent:
```bash
POST /api/v1/agents
{
  "name": "Solar Lead Qualifier",
  "template_slug": "solar",
  "voice_profile_id": "<marathi-voice-id>",
  "voice_profile_version": 1
}
```

Publish a version to lock configuration before campaigns run.

---

## Campaign Engine

```
draft → start → running
running → pause → paused
paused → resume → running
any → cancel → cancelled
running (auto) → completed
```

**Pre-flight checks** run before start:
- Active subscription
- Sufficient credits (≥60)
- Agent published
- Voice profile active
- Phone number assigned
- Leads available
- Concurrency within plan

**Credit model:** 1 credit = 1 billable second. Credits reserved at call start, settled after.

---

## Demo Mode

Set `DEMO_MODE=true` in `backend/.env` to run without paid external providers.

Mock providers simulate:
- Telephony (outbound calls)
- STT (speech-to-text)
- TTS (text-to-speech)
- LLM (conversation)
- Razorpay (payments)

Auto-seeded on startup:
- Demo company org
- Growth plan subscription
- 2000 calling credits
- Marathi AI Voice profile
- Demo phone number
- 20 Indian leads
- Demo campaign

Login credentials (after seeding):
- **Org user:** `demo-user@telecalling-saas.com` / `Demo@1234`
- **Platform admin:** `demo-admin@telecalling-saas.com` / `DemoAdmin@1234`

---

## Deployment (Fly.io)

### First deploy

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login

# Create app
flyctl launch --name ai-telecalling-saas --region bom

# Set secrets
flyctl secrets set \
  MONGODB_URI="mongodb+srv://..." \
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  RAZORPAY_KEY_ID="rzp_live_..." \
  RAZORPAY_KEY_SECRET="..." \
  RAZORPAY_WEBHOOK_SECRET="..." \
  SARVAM_API_KEY="..." \
  ELEVENLABS_API_KEY="..."

# Create Redis
flyctl redis create

# Create volume for models
flyctl volumes create models_data --region bom --size 2

# Deploy
flyctl deploy
```

### Deploy campaign worker

```bash
flyctl deploy --config fly.worker.toml --app ai-telecalling-saas-worker
```

### Health check

```bash
curl https://ai-telecalling-saas.fly.dev/health
```

### Logs

```bash
flyctl logs                        # API logs
flyctl logs --app ai-telecalling-saas-worker   # Worker logs
```

---

## Testing

### Run all tests

```bash
cd /path/to/AI-Telecalling
.venv/Scripts/python.exe -m pytest backend/tests/ -v
```

### Run specific checkpoint

```bash
.venv/Scripts/python.exe -m pytest backend/tests/test_m12_leads.py -v
```

### Run with coverage

```bash
.venv/Scripts/python.exe -m pytest backend/tests/ --cov=backend --cov-report=html
```

### Test without external providers

All tests use `mongomock_motor` for in-memory MongoDB and mock Redis.
No real API keys needed for the test suite.

---

## Adding a New Provider

Example: adding a new TTS provider "CustomTTS".

### 1. Create the adapter

```python
# backend/providers/tts/custom_tts.py
from backend.providers.base import TTSProvider

class CustomTTSProvider(TTSProvider):
    @property
    def provider_name(self) -> str:
        return "custom_tts"

    async def synthesize(self, text: str, language: str = None) -> tuple[bytes, int]:
        # Call your TTS API
        ...

    async def stream(self, text: str, language: str = None):
        # Stream audio chunks
        ...
```

### 2. Register in the provider registry

```python
# backend/providers/registry.py
from backend.providers.tts.custom_tts import CustomTTSProvider

def build_registry(...):
    registry.register_tts("custom_tts", CustomTTSProvider())
```

### 3. Create a voice profile version using the new provider

```bash
POST /api/v1/voice-profiles/{id}/versions
{
  "routes": {
    "tts": {"provider": "custom_tts", "provider_resource_id": "voice_name"}
  }
}
```

**No customer-facing code changes.** The customer still sees "Marathi AI Voice".

---

## Creating a Voice Profile (Step-by-Step)

1. **Login as platform admin** or use `/api/v1/auth/login`
2. **Create profile:**
   ```bash
   POST /api/v1/voice-profiles
   {"display_name": "Telugu AI Voice", "language": "te-IN"}
   ```
3. **Create version with routes** (admin only — routes hidden from customers):
   ```bash
   POST /api/v1/voice-profiles/{id}/versions
   ```
4. **Verify customer view** — call `GET /api/v1/voice-profiles` as a customer.
   You should see `display_name`, `language`, `active_version` — no provider details.
5. **Assign to agent** when creating or updating an agent.

---

## Security Notes

- **JWT:** Access tokens expire in 60 minutes. Refresh tokens expire in 30 days.
  Logout revokes the refresh token via Redis.
- **Rate limiting:** Auth endpoints limited to 10/min per IP.
  General API: 120/min per user.
- **Tenant isolation:** Every database query includes `organization_id`.
  Cross-org data access returns 403 or 404 — never the other org's data.
- **Provider secrets:** API keys are in environment variables only.
  They never appear in database records, API responses, or logs.
- **Webhook verification:** All Razorpay webhooks verified with HMAC-SHA256
  before any processing.
- **Audit logs:** Every admin action (suspend org, adjust credits, etc.)
  creates an immutable audit log entry.
- **Reconciliation:** The `/reconciliation/run` endpoint checks for
  payment/credit inconsistencies without modifying any data.
