# Getting Started — Real Estate Voice Agent

This is the "start here" guide. It takes you from an empty machine to a running
**Sprint 1 walking skeleton** (mic → STT → LLM → TTS → speaker). Follow the steps
in order. See `EXECUTION_PLAN.md` for the full architecture and sprint roadmap.

---

## 0. Prerequisites (already on this machine)

- Docker 29+ (`docker --version`)
- Python 3.12 (`python3 --version`)
- Node 24 (`node --version`)
- NVIDIA RTX 3050, 6GB VRAM (`nvidia-smi`)

You still need:
- A **Groq API key** — used for both Whisper (STT) and gpt-oss (LLM).
  Get one at https://console.groq.com → API Keys.
- (Sprint 5 only) A **Twilio account** with a phone number.

---

## 1. Why this stack (read once)

The 6GB GPU cannot host a 20B LLM, so:

- **STT + LLM run on Groq** (fast cloud). One API key covers both.
- **Orpheus TTS runs locally** on the GPU (quantized, ~3-4GB). Keeps audio
  generation off the network for low latency.

If Orpheus is too heavy for 6GB later, swap to Piper/Kokoro (see plan §8).

---

## 2. One-time setup

### 2.1 Environment file

Copy the template and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env`:

```
GROQ_API_KEY=gsk_...
GROQ_STT_MODEL=whisper-large-v3-turbo
GROQ_LLM_MODEL=openai/gpt-oss-20b

POSTGRES_USER=voice
POSTGRES_PASSWORD=voice
POSTGRES_DB=voiceagent
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

REDIS_HOST=localhost
REDIS_PORT=6379

# Orpheus (local TTS)
ORPHEUS_MODEL_PATH=./models/orpheus-3b-Q4_K_M.gguf
TTS_SAMPLE_RATE=24000
```

### 2.2 Start Postgres + Redis

```bash
docker compose up -d
docker compose ps          # both should show "healthy"
```

### 2.3 Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2.4 Download the TTS voice

Sprint 1 uses **Piper** (CPU, reliable) so the loop talks today. Orpheus is the
Sprint 4 upgrade — it drops in behind the same `TTSEngine` interface via
`TTS_ENGINE=orpheus`, no loop changes.

```bash
mkdir -p models/piper
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
curl -sL -o models/piper/en_US-lessac-medium.onnx      "$BASE/en_US-lessac-medium.onnx"
curl -sL -o models/piper/en_US-lessac-medium.onnx.json "$BASE/en_US-lessac-medium.onnx.json"
```

---

## 3. Smoke test each piece independently

Before wiring the loop, verify each dependency in isolation. This is the fastest
way to localize failures.

1. **Groq LLM reachable**
   ```bash
   curl https://api.groq.com/openai/v1/chat/completions \
     -H "Authorization: Bearer $GROQ_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"openai/gpt-oss-20b","messages":[{"role":"user","content":"say hi"}]}'
   ```
2. **Groq Whisper reachable** — POST a short wav to the transcriptions endpoint.
3. **Orpheus loads on GPU** — run `backend/audio/tts.py` directly to synthesize a
   test phrase to a wav file, and watch VRAM in `nvidia-smi`.
4. **Postgres + Redis** — `docker compose ps` shows healthy; connect with `psql`
   and `redis-cli ping`.

Only proceed to the full loop once all four pass.

---

## 4. Run the walking skeleton (Sprint 1)

```bash
# Terminal 1: backend
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Health check
curl http://localhost:8000/health
```

Open the test page (served by FastAPI) at `http://localhost:8000`, click
**Start call**, and allow the mic. Ava greets you and then just listens — talk
naturally, pause, and she replies. You can **interrupt her mid-sentence** (barge-in)
and she stops instantly. Use headphones for the best experience (avoids the mic
picking up her voice). Click **End call** to hang up.

**Definition of done for Sprint 1:** you talk, the agent answers out loud,
end-to-end, through the websocket. Latency and answer quality do not matter yet.
(Sprints 2-4 add the qualification flow, persistence, and realtime turn-taking.)

---

## 5. Daily build order

Work the sprints in `EXECUTION_PLAN.md` §7 in order:

1. **Sprint 0** — foundations (compose, config, logging, /health)
2. **Sprint 1** — walking skeleton (this guide)
3. **Sprint 2** — LangGraph conversation engine (5 stages)
4. **Sprint 3** — Postgres/Redis persistence + slot-filling + scoring
5. **Sprint 4** — streaming, VAD, barge-in, latency tuning
6. **Sprint 5** — Twilio telephony
7. **Sprint 6** — Next.js dashboard + observability

Do not jump ahead. Each sprint upgrades a system that already runs.

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `CUDA out of memory` on TTS | Orpheus + KV cache > 6GB | Use a smaller quant (Q4) or fall back to Piper/Kokoro |
| High response latency | Waiting for full STT/LLM/TTS | Ensure streaming is enabled at every stage (Sprint 4) |
| Agent talks over you | No barge-in | Sprint 4: wire VAD → stop TTS playback |
| Groq 401 | Bad/missing key | Check `GROQ_API_KEY` in `.env` |
| DB connection refused | Containers not up | `docker compose up -d` and check `docker compose ps` |

---

## 7. Conventions

- Config only via `.env` → `config.py`. No hardcoded secrets or URLs.
- Log a `latency_ms` on every turn from Sprint 1 — you cannot optimize what you
  don't measure.
- Keep each integration (STT/LLM/TTS/telephony) behind a single module so it can
  be swapped without touching the engine.

---

## 8. Sprint 5 — make a real phone call (Twilio)

Twilio reaches your backend over the public internet, so you need a tunnel.

**One-time Twilio setup (free trial):**
1. Rotate your Auth Token if it was ever shared, then buy a voice-capable number
   (Console → Phone Numbers).
2. Verify the phone you'll call (Console → Phone Numbers → Verified Caller IDs).
   Trial accounts can only call verified numbers.
3. Enable your destination country under Voice → Settings → Geographic Permissions
   (e.g. India for a +91 number).

**Each dev session:**
```bash
# 1. Start the backend
./.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 2. Expose it publicly
ngrok http 8000        # copy the https://....ngrok-free.app URL
```

Put the values in `backend/.env` (never in chat):
```
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...            # the rotated token
TWILIO_PHONE_NUMBER=+1...        # your Twilio number
PUBLIC_BASE_URL=https://....ngrok-free.app
```
Restart the backend after editing `.env`.

**Place an outbound call (Twilio dials you, you talk to Ava):**
```bash
curl -X POST http://localhost:8000/calls/outbound \
  -d "to=+918130243850"          # your verified number, E.164
```

Twilio calls the number, fetches `/twiml/voice`, and connects the audio to
`/ws/twilio`. Pick up and talk — the same VAD/engine/barge-in/persistence path as
the browser runs the call. Hang up and the call is finalized in Postgres.

**Inbound instead:** point your Twilio number's "A call comes in" webhook at
`https://....ngrok-free.app/twiml/voice` (HTTP POST), then call the number.

**Telephony notes:**
- Audio is 8 kHz mu-law both ways; the bridge resamples to/from our 16 kHz pipeline.
- On a phone line the inbound track is the caller only, so there's no echo — barge-in
  is cleaner than in the browser.
- Trial calls are capped at 10 minutes and play a trial notice first.
