# Kavya — Real Estate Voice Agent

An AI calling agent for a real estate business. **Kavya** greets callers, qualifies
leads through a real conversation (budget, timeline, city, property type), handles
objections, books viewings, and persists everything — over the browser **or a real
phone line**, in **English or 10 Indian languages** (Hindi, Tamil, Telugu, Bengali,
Marathi, Kannada, Malayalam, Gujarati, Punjabi, Odia), with native Hinglish
code-switching.

Built to survive real-world conditions: neural VAD for noisy rooms, barge-in
(interrupt the agent mid-sentence), streaming TTS for low latency, and a live
dashboard to watch it all.

---

## Table of contents
- [What it does](#what-it-does)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [How a turn works](#how-a-turn-works)
- [Conversation design](#conversation-design)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Configuration (.env)](#configuration-env)
- [Running & testing](#running--testing)
- [Making a real phone call (Twilio)](#making-a-real-phone-call-twilio)
- [API reference](#api-reference)
- [Notable engineering decisions](#notable-engineering-decisions)
- [Known limitations / production notes](#known-limitations--production-notes)
- [Further docs](#further-docs)

---

## What it does
- **Answers/places calls** and holds a natural, warm conversation (not a Q&A form).
- **Qualifies the lead** — extracts budget, timeline, city, and property type, scores
  the lead 0-100, and drives a stage machine toward booking a viewing.
- **Multilingual + Hinglish** — the admin picks the call language; Kavya listens,
  thinks, and replies in it, keeping English terms in English where natural.
- **Realtime & interruptible** — continuous audio, neural VAD turn-taking, and
  barge-in (talk over her and she stops).
- **Persists everything** — every call, transcript, extracted lead, and booking lands
  in Postgres and is browsable in a dashboard.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| **STT (English)** | Groq **Whisper** `whisper-large-v3-turbo` | Fast, cheap, good on English |
| **STT (Indian langs)** | Sarvam **Saaras v3** (`codemix` mode) | Indic-tuned, handles Hinglish + phone audio; Whisper garbles code-mixed Hindi |
| **LLM (conversation)** | Groq **gpt-oss-20b** (`reasoning_effort=low`) | Quality replies, low latency; low reasoning avoids empty/slow turns |
| **LLM (slot extraction)** | Groq **llama-3.1-8b-instant** (JSON mode) | Cheap, fast, reliable structured output |
| **TTS** | Sarvam **Bulbul v3** (streaming) | Native Indian voices, Hinglish, ~0.5 s first-audio (streaming) |
| **TTS (alt)** | **Piper** (local CPU) · Orpheus (planned) | Pluggable engine interface; Piper for offline English |
| **VAD / turn-taking** | **Silero VAD** via onnxruntime (webrtcvad fallback) | Neural; rejects TV/traffic/fan noise that energy VADs can't |
| **Conversation engine** | **LangGraph** state machine | Stage routing + slot state, cleanly modeled |
| **Durable store** | **Postgres 16** (SQLAlchemy async + Alembic) | Leads, calls, turns, bookings |
| **Live session** | **Redis 7** | Per-call state, crash-resilient |
| **Telephony** | **Twilio Media Streams** | Real phone calls (µ-law 8 kHz bridge) |
| **Frontend** | **Next.js 14** + Tailwind | Dashboard: overview, calls, transcripts, leads, new call |

Everything runs on a modest laptop (tested on an RTX 3050 6 GB): the heavy models
(STT + LLM) are on Groq/Sarvam APIs, and Silero VAD + Piper run on CPU.

---

## Architecture

The core is a **transport-agnostic `CallSession`** — it owns VAD, the engine,
barge-in, latency tracking, and persistence, and talks to the outside world through
a thin `Transport` (browser or phone). The audio contract is **16 kHz mono PCM**.

```
 Caller audio (mic / phone)
        │  16 kHz PCM frames
        ▼
 ┌──────────────────────┐   speech_start ─► barge-in (cancel + flush)
 │ Silero VAD endpointer │
 │ energy gate·debounce  │
 └──────────┬───────────┘
            │ utterance (on end-of-speech)
            ▼
   STT  ── English → Groq Whisper
        └─ Indic   → Sarvam Saaras (codemix)
            │  transcript
            ▼
 ┌───────────────────────────────┐    slots ↔ Redis (live) + Postgres (durable)
 │ LangGraph engine              │
 │  understand → route(stage)    │  extraction: llama-3.1-8b (JSON)
 │  greeting→qualify→objection→  │
 │  booking→end                  │
 └──────────────┬────────────────┘
                │ stage-specific prompt
                ▼
      gpt-oss-20b (streamed sentences, reasoning_effort=low)
                │ sentence
                ▼
      Sarvam Bulbul TTS (streamed audio chunks)
                │ PCM
                ▼
        Transport ── browser: Web Audio (PCM + sr header)
                   └─ phone : µ-law 8 kHz media frames  ─► Caller
```

Two transports, one brain:
- **`BrowserTransport`** (`/ws/call`) — streams PCM to a Web Audio player; half-duplex
  mic gating avoids speaker echo.
- **`TwilioTransport`** (`/ws/twilio`) — bridges µ-law 8 kHz ↔ 16 kHz PCM; full-duplex
  with barge-in.

---

## How a turn works
1. The transport streams 16 kHz PCM into `CallSession.feed_pcm16`.
2. **Silero VAD** classifies 32 ms windows; an **energy floor** rejects quiet noise.
   After ~200 ms of *sustained* speech it emits `speech_start` → **barge-in** (cancels
   any in-flight reply and flushes playback). After ~800 ms of trailing silence it
   emits the complete **utterance** (a max-length flush prevents steady noise from
   freezing a turn).
3. The utterance is transcribed by the **STT router** (Whisper for English, Saaras for
   Indic). Junk/hallucination and confidence filters drop noise.
4. The **LangGraph engine** runs `understand` (extract slots + intent flags via the
   small JSON model) → `route` (pick the next stage).
5. **gpt-oss** generates the reply with the stage-specific prompt, streamed
   sentence-by-sentence.
6. Each sentence is spoken by **Sarvam Bulbul** (streaming), sent to the caller.
7. Turn, slots, and latency are persisted; Redis holds the live session; the call is
   finalized (lead score, outcome, booking) on hang-up.

---

## Conversation design

State machine (LangGraph):

```
greeting → qualification → booking → end
                 │  ▲          
          objection ┘  (re-engages back to qualification/booking)
```

**Qualification slots:** `budget` · `timeline` · `city` · `property_type`
(India-aware: ₹ lakh/crore, Indian cities/localities, BHK sizing; "villa" is a
property type, not a city).

**Lead scoring (0-100):** 15 pts per filled slot + 30 booking intent + 10 interest
− 25 for wanting out → mapped to `new / qualifying / qualified / booked / lost`.

---

## Repository layout

```
ai_calling_assistant/
├── docker-compose.yml            # Postgres + Redis
├── .env.example                  # config template
├── alembic.ini                   # migrations
├── backend/
│   ├── main.py                   # FastAPI app, /ws/call, BrowserTransport, routes
│   ├── config.py                 # all settings (pydantic-settings, loads backend/.env)
│   ├── languages.py              # 11 Sarvam-backed languages
│   ├── call_session.py           # transport-agnostic call pipeline (the "brain")
│   ├── logging_setup.py          # structured logs + per-turn trace id
│   ├── audio/
│   │   ├── vad.py                # Silero VAD + endpointer (webrtc fallback)
│   │   ├── stt.py                # Groq Whisper, Sarvam Saaras, STTRouter
│   │   └── tts.py                # TTSEngine interface: Piper / Sarvam / Orpheus
│   ├── agent/
│   │   ├── engine.py             # LangGraph state machine
│   │   ├── prompts.py            # persona + per-stage + extraction prompts
│   │   ├── llm.py                # Groq client (stream + JSON extraction)
│   │   ├── state.py              # stages, slots, ConversationState
│   │   └── scoring.py            # lead scoring
│   ├── memory/
│   │   ├── repository.py         # Postgres CRUD + stats
│   │   └── session.py            # Redis live session store
│   ├── db/
│   │   ├── models.py             # Lead, Call, Turn, Booking
│   │   ├── database.py           # async engine/session
│   │   └── migrations/           # Alembic
│   ├── telephony/twilio.py       # Media Streams bridge, TwiML, outbound
│   ├── api/routes.py             # /api/stats, /calls, /leads (dashboard)
│   └── static/index.html         # minimal browser test page
├── frontend/                     # Next.js dashboard (Groq-styled)
│   ├── app/                      # overview, /call, /calls, /calls/[id], /leads
│   ├── components/ · lib/api.ts
│   └── tailwind.config.ts
├── models/                       # silero_vad.onnx, piper voice (git-ignored)
└── docs/                         # EXECUTION_PLAN, INSTRUCTIONS, ISSUES
```

---

## Prerequisites
- **Docker** (Postgres + Redis)
- **Python 3.12**
- **Node 20+** (dashboard)
- A **Groq API key** — https://console.groq.com (STT + LLM)
- A **Sarvam API key** — https://dashboard.sarvam.ai (TTS + Indic STT)
- *(optional)* **Twilio** account + number + **ngrok** for real phone calls

---

## Quick start

```bash
# 1) Infra
docker compose up -d                     # Postgres + Redis

# 2) Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example backend/.env             # then fill in keys (see below)

#    Models (git-ignored):
mkdir -p models/silero models/piper
curl -sL -o models/silero/silero_vad.onnx \
  https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
curl -sL -o models/piper/en_US-lessac-medium.onnx      "$BASE/en_US-lessac-medium.onnx"
curl -sL -o models/piper/en_US-lessac-medium.onnx.json "$BASE/en_US-lessac-medium.onnx.json"

#    Migrate + run
alembic upgrade head
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 3) Dashboard (separate terminal)
cd frontend && npm install && npm run dev   # http://localhost:3000
```

Open **http://localhost:3000/call**, pick a language, and **Start call** (use
headphones for the browser test).

---

## Configuration (.env)

Lives in `backend/.env` (git-ignored). Key settings:

```bash
# Groq (STT + LLM)
GROQ_API_KEY=gsk_...
GROQ_STT_MODEL=whisper-large-v3-turbo
GROQ_LLM_MODEL=openai/gpt-oss-20b
GROQ_EXTRACTION_MODEL=llama-3.1-8b-instant
GROQ_REASONING_EFFORT=low

# Sarvam (TTS + Indic STT) — one key
SARVAM_TTS_API_KEY=sk_...
TTS_ENGINE=sarvam            # piper | sarvam
SARVAM_SPEAKER=kavya         # bulbul:v3 voice
SARVAM_STT_MODEL=saaras:v3
SARVAM_STT_MODE=codemix      # keeps English words in English

# VAD / turn-taking
VAD_BACKEND=silero           # silero | webrtc
VAD_SILENCE_MS=800           # end-of-turn silence (tolerates natural pauses)
VAD_SPEECH_CONFIRM_MS=200    # barge-in debounce

# Postgres / Redis (match docker-compose defaults)
POSTGRES_USER=voice ... REDIS_HOST=localhost ...

# Twilio (optional, for phone calls)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
PUBLIC_BASE_URL=https://<subdomain>.ngrok-free.app
```

The config loader (`backend/config.py`) has sane defaults for everything except the
API keys.

---

## Running & testing
- **Browser test:** `http://localhost:3000/call` → select language → *Start call*.
  Half-duplex in the browser (Kavya listens after she finishes); use headphones.
- **Health:** `curl http://localhost:8000/health`
- **Inspect data:**
  ```bash
  docker exec voiceagent_postgres psql -U voice -d voiceagent \
    -c "SELECT status, score, city, property_type FROM leads ORDER BY created_at DESC LIMIT 5;"
  ```

---

## Making a real phone call (Twilio)
1. Buy a voice number, verify your phone (trial), enable your country in Voice →
   Geographic Permissions.
2. Expose the backend: `ngrok http 8000` → put the HTTPS URL in `PUBLIC_BASE_URL`,
   restart the backend.
3. Place an outbound call (Twilio dials you):
   ```bash
   curl -X POST http://localhost:8000/calls/outbound \
     --data-urlencode "to=+9198XXXXXXXX" --data-urlencode "lang=hi-IN"
   ```
   Or from the dashboard **New Call** page. Inbound also works — point the number's
   "A call comes in" webhook at `https://<tunnel>/twiml/voice`.

---

## API reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Postgres + Redis + Groq-key check |
| GET | `/` | Minimal browser test page |
| GET | `/api/languages` | Supported call languages |
| GET | `/api/stats` | Dashboard metrics |
| GET | `/api/calls` · `/api/calls/{id}` | Call list · detail + transcript |
| GET | `/api/leads` | Lead pipeline |
| WS  | `/ws/call?lang=<code>` | Browser realtime call |
| POST| `/calls/outbound` | Place an outbound phone call (`to`, `lang`) |
| GET/POST | `/twiml/voice` | Twilio webhook (returns Media Streams TwiML) |
| WS  | `/ws/twilio` | Twilio Media Streams audio |

---

## Notable engineering decisions
These were discovered/fixed through real testing (see `docs/ISSUES.md`):

- **Neural VAD over energy VAD.** webrtcvad treated TV/room noise as "100% speech,"
  so noisy turns were never delivered. Silero VAD + an energy floor + debounced
  barge-in fixed it (turns delivered even at 5-10 dB SNR; a 100 ms noise click no
  longer interrupts).
- **Streaming TTS.** Sarvam REST had a ~2.5 s floor; the streaming endpoint
  (`linear16`) drops first-audio to ~0.5 s. Browser plays via Web Audio scheduling;
  phone streams µ-law frames.
- **`reasoning_effort=low`.** gpt-oss is a reasoning model; default reasoning ate the
  token budget → **empty replies / silent stalls** and ~400 ms extra latency. Lowering
  it fixed both, plus a fallback line if a reply is ever empty.
- **Sarvam Saaras `codemix` for Hindi.** Whisper garbles code-mixed Hindi
  ("गुड़गांव" → "गुर्गाओं"); Saaras keeps English words in English and Hindi in
  Devanagari — true Hinglish.
- **STT hallucination guards.** Whisper invents "Thank you." / "झाल" on silence;
  a denylist + repeat guard + half-duplex mic gating (browser echo) stop false turns.
- **Bounded LLM context** (last 12 messages) so latency stays flat on long calls.

---

## Known limitations / production notes
- **No auth** on the API/websockets — fine for local dev; add authentication before
  exposing anything publicly.
- **Secrets** live in `backend/.env` (git-ignored). Rotate any key that has been
  shared. Never commit `.env`.
- **Latency:** English turns ~1-1.5 s; Hindi ~2-3 s (STT + Indic TTS) — in line with
  the industry, further reducible via Sarvam streaming STT.
- **Browser is half-duplex** (echo control without headphones); the phone is
  full-duplex with barge-in.
- **Frontend deps:** `npm audit` flags advisories in Next's transitive deps — pin a
  patched Next before production.
- **GPU:** designed for a 6 GB laptop by keeping big models on APIs; Orpheus local TTS
  is stubbed for a future GPU upgrade.

---

## Further docs
- `docs/EXECUTION_PLAN.md` — the original architecture & sprint plan
- `docs/INSTRUCTIONS.md` — step-by-step setup / phone-call playbook
- `docs/ISSUES.md` — the debugging log: noise robustness, Hinglish, stalls, with
  before/after measurements
```
