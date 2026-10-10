# AI Telecalling SaaS

Multi-tenant AI Voice Telecalling Platform — production-grade MVP.

---

## What it does

An AI calling agent dials leads, qualifies them through natural conversation,
books appointments, and handles objections — in English and 10 Indian languages.
Built as a commercial SaaS: organizations subscribe, buy calling credits, manage
campaigns, and get analytics.

**Key features:**
- Multi-tenant (full org isolation)
- AI voice profiles (customers see "Marathi AI Voice", never provider details)
- Real-time calling with VAD, barge-in, low-latency STT/LLM/TTS pipeline
- Campaign engine with concurrency control, DNC, calling hours
- Razorpay billing (server-authoritative — amount never from frontend)
- Wallet + credit system (reserve/release/settle per call)
- Provider abstraction (Twilio, Exotel, Sarvam, ElevenLabs, OpenAI, Groq)
- Demo mode (full workflow without paid APIs)

---

## Quick start (Demo Mode)

```bash
# 1. Clone
git clone https://github.com/Risabkshetri/AI-Telecalling
cd AI-Telecalling

# 2. Python env
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# 3. Configure
cp .env.example backend/.env
# Edit backend/.env:
#   MONGODB_URI=mongodb://localhost:27017   (or Atlas URI)
#   REDIS_URL=redis://localhost:6379/0
#   SECRET_KEY=your-random-secret
#   DEMO_MODE=true

# 4. Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# 5. Run
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 6. Seed demo data
curl -X POST http://localhost:8000/api/v1/demo/seed \
  -H "Authorization: Bearer $(curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"email":"demo-admin@telecalling-saas.com","password":"DemoAdmin@1234"}' \
    | python -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')"
```

API docs: http://localhost:8000/docs

**Demo credentials:**
- Org user: `demo-user@telecalling-saas.com` / `Demo@1234`
- Platform admin: `demo-admin@telecalling-saas.com` / `DemoAdmin@1234`

---

## Tech stack

| Layer | Choice |
|---|---|
| **API** | FastAPI + uvicorn |
| **Database** | MongoDB Atlas (motor async driver) |
| **Cache/Coordination** | Redis |
| **Auth** | JWT (python-jose) + bcrypt |
| **Telephony** | Twilio Media Streams / Exotel / Mock |
| **STT** | Sarvam Saaras v3 (Indic) / Groq Whisper |
| **LLM** | OpenAI / Groq gpt-oss / Mock |
| **TTS** | ElevenLabs / Sarvam Bulbul / Piper / Mock |
| **VAD** | Silero VAD (onnxruntime, no torch) |
| **Conversation** | LangGraph state machine |
| **Billing** | Razorpay (server-authoritative) |
| **Deployment** | Fly.io |
| **Frontend** | Next.js 14 + Tailwind |

---

## Architecture

```
Customer → Organization → Subscription → Credits
                              ↓
                         AI Voice Profile (hidden provider routes)
                              ↓
                         Agent (template + config)
                              ↓
                         Campaign (leads + schedule + concurrency)
                              ↓
                         Campaign Worker (Redis-coordinated)
                              ↓
                    Telephony → VAD → STT → LangGraph → LLM → TTS
                              ↓
                    Post-call: transcript → score → lead update → settle credits
```

---

## Project structure

```
backend/
├── api/v1/          # 26 REST API routers
├── core/            # db, redis, auth, rbac, rate_limit, health
├── models/          # Pydantic MongoDB document models
├── repositories/    # MongoDB data access layer
├── services/        # Business logic
│   ├── wallet_service.py
│   ├── credit_service.py
│   ├── campaign_service.py
│   ├── post_call_service.py
│   ├── analytics_service.py
│   └── ...
├── providers/       # Provider abstractions
│   ├── payment/     # Razorpay, Mock
│   ├── telephony/   # Twilio, Exotel, Mock
│   ├── stt/         # Sarvam, Mock
│   ├── tts/         # ElevenLabs, Sarvam, Mock
│   └── llm/         # OpenAI, Mock
├── workers/         # campaign_worker.py
├── scripts/         # ensure_indexes.py (deploy release command)
├── audio/           # VAD, STT, TTS (preserved from original repo)
├── agent/           # LangGraph conversation engine
└── tests/           # 829 tests, 0 failures
frontend/            # Next.js 14 dashboard
```

---

## Running tests

```bash
# All tests (829)
python -m pytest backend/tests/ -v

# Specific checkpoint
python -m pytest backend/tests/test_m13_campaigns.py -v
```

No real API keys required — tests use mongomock and mock providers.

---

## Deployment

See [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for full Fly.io deployment.

```bash
flyctl deploy              # API server
flyctl deploy --config fly.worker.toml   # Campaign worker
```

---

## Checkpoints completed

M0 → M31 fully implemented. See [MVP_PROGRESS.md](MVP_PROGRESS.md).

---

## License

Private — commercial SaaS MVP.
