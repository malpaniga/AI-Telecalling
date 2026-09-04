# Real Estate Voice Agent — Execution Plan

A production-grade AI calling agent that qualifies real estate leads over voice,
handles objections, and books property viewings.

---

## 0. The one thing that matters: latency

A voice agent lives or dies on **response latency** (user stops speaking → agent
starts speaking) and **turn-taking** (knowing when the user is done, and stopping
instantly when interrupted). We design the whole system around these two numbers.

| Metric | Good | Great |
|---|---|---|
| Response latency (silence → first audio) | < 1.2s | < 800ms |
| Barge-in stop (interrupt → agent silent) | < 300ms | < 150ms |
| STT finalize after speech end | < 250ms | < 150ms |
| LLM time-to-first-token | < 400ms | < 250ms |
| TTS time-to-first-audio-chunk | < 250ms | < 150ms |

Rule we never break: **stream everything and overlap stages.** Never wait for a
full STT transcript, a full LLM response, or a full TTS clip before moving.

---

## 1. Hardware reality & the stack decision

**Your machine:** RTX 3050 Laptop, **6GB VRAM**, Docker installed, Python 3.12,
Node 24, Postgres + Redis available via Docker.

6GB VRAM is the binding constraint. It rules out self-hosting a 20B model. So:

| Layer | Choice | Where | Why |
|---|---|---|---|
| STT | Groq Whisper (`whisper-large-v3-turbo`) | Cloud | Fastest hosted Whisper, streaming-friendly |
| LLM | `openai/gpt-oss-20b` on Groq | Cloud | 20B won't fit in 6GB; Groq runs it with very low TTFT |
| TTS | Orpheus (GGUF, quantized) | **Local GPU** | ~3-4GB fits in 6GB; local = no network hop for audio |
| Conversation | LangGraph | Local | Stateful state machine (greeting→…→end) |
| Session state | Redis | Docker | Fast ephemeral per-call state |
| Durable data | Postgres | Docker | Leads, calls, transcripts, bookings |
| Telephony | Twilio Media Streams | Cloud | Real phone calls (added Sprint 5) |
| Frontend | Next.js | Local | Dashboard, live monitor, lead pipeline |

**GPU budget on the 6GB card:** Orpheus-3B at Q4_K_M ≈ 2.3GB weights + KV cache +
audio decode headroom. Fits with room to spare because the LLM lives on Groq.
If Orpheus is too tight, fall back to a lighter local TTS (Piper/Kokoro) — keep
this as a Sprint-4 escape hatch.

---

## 2. System architecture

```
Caller ──audio (20ms PCM frames)──> Ingress
        (local mic / Twilio Media Stream)
                    │  websocket
                    ▼
        ┌─────────────────────────────┐
        │ VAD + endpointing            │──barge-in signal──┐
        │ (detect speech / silence)    │                   │
        └─────────────┬───────────────┘                   ▼
                      │ audio when speaking      TTS playback controller
                      ▼                          (stop instantly on barge-in)
          Groq Whisper (streaming STT)                     ▲
                      │ final transcript                   │ audio chunks
                      ▼                                     │
        ┌─────────────────────────────┐          Orpheus TTS (local, streaming)
        │ LangGraph conversation engine│                    ▲
        │ greeting→qualify→objection→  │────tokens──────────┘
        │ booking→end                  │
        └───────┬─────────────────┬────┘
                │ read/write      │ prompt + stream
                ▼                 ▼
   Redis (session)          Groq gpt-oss-20b
   Postgres (durable)       (OpenAI-compatible)
```

Frontend (Next.js) ↔ FastAPI over REST (leads, calls, transcripts) + websocket
(live call monitor with streaming transcript).

---

## 3. Repository structure

```
voice-agent/
├── docker-compose.yml          # postgres, redis
├── .env.example
├── README.md
├── docs/
│   ├── EXECUTION_PLAN.md        # this file
│   └── INSTRUCTIONS.md          # how to start
├── backend/
│   ├── requirements.txt
│   ├── main.py                  # FastAPI app + websocket entrypoints
│   ├── config.py                # settings from env
│   ├── logging_setup.py         # structured logs + turn/trace IDs
│   ├── audio/
│   │   ├── stt.py               # Groq Whisper (streaming)
│   │   ├── tts.py               # Orpheus local (streaming)
│   │   ├── vad.py               # voice activity detection
│   │   └── player.py            # playback + barge-in control
│   ├── agent/
│   │   ├── llm.py               # Groq gpt-oss client (OpenAI-compatible)
│   │   ├── prompts.py           # per-stage system prompts
│   │   ├── state.py             # conversation state + memory slots
│   │   ├── engine.py            # LangGraph state machine
│   │   └── scoring.py           # lead scoring
│   ├── memory/
│   │   ├── session.py           # Redis session store
│   │   └── repository.py        # Postgres CRUD
│   ├── db/
│   │   ├── models.py            # SQLAlchemy models
│   │   └── migrations/          # alembic
│   ├── telephony/
│   │   └── twilio.py            # Media Streams ws bridge (Sprint 5)
│   └── api/
│       ├── calls.py             # REST: calls, transcripts
│       └── leads.py             # REST: lead pipeline
└── frontend/                    # Next.js (Sprint 6)
    ├── app/
    │   ├── calls/               # live monitor + transcript
    │   ├── leads/               # pipeline / CRM
    │   └── analytics/
    └── lib/api.ts
```

---

## 4. Conversation design (the product)

State machine, implemented as LangGraph nodes over a shared state object.

```
        ┌──────────┐
        │ GREETING │  intro, confirm it's a good time
        └────┬─────┘
             ▼
      ┌──────────────┐   fills 4 slots:
      │ QUALIFICATION│   budget, timeline, city, property_type
      └───┬──────┬───┘
          │      │ objection raised
          │      ▼
          │  ┌───────────┐
          │  │ OBJECTION │ handle price/trust/timing, then return
          │  └─────┬─────┘
          │        │
          ▼        ▼
      ┌──────────────┐   all slots filled + interested
      │   BOOKING     │  propose slots, confirm viewing
      └──────┬────────┘
             ▼
        ┌────────┐
        │  END   │  recap, next steps, polite close
        └────────┘
```

**Memory slots (the qualification payload):**
- `budget` — numeric range or single figure
- `timeline` — when they want to move/buy (e.g. "3 months")
- `city` — target location/area
- `property_type` — apartment / villa / plot / commercial, BHK, etc.

Slot-filling rules: extract from every user turn, never re-ask a filled slot,
confirm ambiguous values, allow correction. Transition to BOOKING only when all
four are filled and the lead signals interest.

---

## 5. Data model (first cut)

```
leads
  id (uuid, pk)
  name, phone (unique), email
  city, budget_min, budget_max, timeline, property_type
  score (int 0-100), status (new|qualifying|qualified|booked|lost)
  created_at, updated_at

calls
  id (uuid, pk)
  lead_id (fk)
  direction (inbound|outbound)
  status (ringing|active|completed|failed)
  started_at, ended_at, duration_s
  outcome (booked|callback|not_interested|no_answer)
  recording_url
  avg_latency_ms

turns
  id (uuid, pk)
  call_id (fk)
  role (user|agent)
  text
  stage (greeting|qualification|objection|booking|end)
  ts, latency_ms

bookings
  id (uuid, pk)
  lead_id (fk), call_id (fk)
  scheduled_for (timestamptz)
  property_ref, status (proposed|confirmed|cancelled)
  created_at
```

Redis holds the live per-call session: `session:{call_id}` → current stage,
filled slots, rolling message window, TTS/barge-in flags. Flushed to Postgres on
turn boundaries and call end.

---

## 6. API surface (backend)

REST:
- `POST /leads` / `GET /leads` / `GET /leads/{id}` — pipeline CRUD
- `GET /calls` / `GET /calls/{id}` — call list + detail with transcript
- `POST /calls/outbound` — trigger an outbound call (Sprint 5)

WebSocket:
- `WS /ws/call/{call_id}` — bidirectional audio stream (browser mic in Sprints
  1-4, Twilio Media Stream in Sprint 5)
- `WS /ws/monitor/{call_id}` — read-only live transcript feed for the dashboard

---

## 7. Sprint plan (walking skeleton first)

Philosophy you asked for: **get one complete, ugly loop working, then upgrade
each layer.** Every sprint after Sprint 1 improves a system that already runs.

### Sprint 0 — Foundations (½ day)
- Repo structure, `docker-compose` (Postgres + Redis), `.env` + `config.py`
- Structured logging with per-turn trace IDs, `/health` endpoint
- **Done when:** `docker compose up` + `uvicorn main:app` boot clean.

### Sprint 1 — Walking skeleton (the first working sprint)
- Browser mic → Groq Whisper → Groq gpt-oss (single prompt, no state machine) →
  Orpheus (local) → speaker, over a websocket.
- Blocking / high-latency / dumb answers are all fine.
- **Done when:** you speak and hear a spoken reply end-to-end.

### Sprint 2 — Conversation engine
- LangGraph state machine: greeting → qualification → objection → booking → end
- Per-stage prompts, transition logic, shared state object
- **Done when:** it runs a coherent qualification call start to finish.

### Sprint 3 — Memory & persistence
- Postgres schema + Alembic migrations, Redis session store
- Slot-filling (budget/timeline/city/property_type), lead scoring
- **Done when:** every call is saved with transcript + extracted slots + score.

### Sprint 4 — Realtime quality (make it feel human)
- Full streaming STT/LLM/TTS pipeline
- VAD, endpointing tuning, **barge-in / interruptions**
- Latency profiling against the budget in section 0
- **Done when:** you can interrupt it and it stops < 300ms; latency < 1.2s.

### Sprint 5 — Telephony
- Twilio Media Streams websocket bridge (μ-law 8kHz ↔ pipeline format)
- Phone number, inbound + outbound flows
- **Done when:** a real phone call runs the full agent.

### Sprint 6 — Frontend & ops
- Next.js: live call monitor (streaming transcript), lead pipeline, analytics
- Observability + a small conversation eval harness
- **Done when:** you can watch/replay calls and manage leads from the dashboard.

---

## 8. Top risks & mitigations

1. **GPU contention / VRAM** — mitigated by moving the LLM to Groq. Keep a lighter
   local TTS (Piper/Kokoro) as fallback if Orpheus is tight on 6GB.
2. **Turn-taking / endpointing** — the hardest UX problem, not the AI. Budget real
   time in Sprint 4; use VAD + adaptive silence threshold + barge-in.
3. **Latency creep** — enforce the section-0 budget from Sprint 1; log `latency_ms`
   per turn from day one so regressions are visible.
4. **Telephony audio format mismatch** — Twilio is μ-law 8kHz mono; resample
   carefully. Isolate in `telephony/twilio.py`.
5. **Prompt/stage drift** — the model skipping stages or re-asking slots. Guard
   with explicit state transitions in LangGraph, not just prompt instructions.

---

## 9. Build order recommendation

Do **Sprint 0 + Sprint 1 back to back.** Once the mic-to-speaker loop talks, every
later sprint is a visible upgrade to a working product instead of a leap of faith.
