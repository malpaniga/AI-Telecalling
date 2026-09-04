# Issues Log — post-Sarvam call testing (2026-07)

Catalogued from two real browser test calls (`50c8141d…`, `e005ec63…`). Ordered
by fix priority. Each item: symptom → evidence → root cause → fix.

---

## P0-1 · Whisper hallucinates "Thank you." on silence/noise → false turns
**Symptom:** the agent kept hearing "Thank you." over and over when nobody said it,
and treated it as the caller wanting to end.

**Evidence (logs):** ~15 occurrences of `stt … -> 'Thank you.'`, many followed by
`engine: understand … wants_to_end: True`. Also `stt … -> 'I'` and `-> '.'`.

**Root cause:** Whisper (large-v3 family) hallucinates high-frequency phrases
("Thank you.", "Thanks for watching") when fed near-silence or non-speech. Our VAD
sends very short blips (min_speech_ms = 200 ms) straight to STT, and we accept any
non-empty transcript. Compounded by STT being locked to `language="en"`, so when
the agent's Hindi audio echoes back it gets mistranscribed as English "Thank you."

**Fix:** (a) raise VAD `min_speech_ms` and `aggressiveness`; (b) drop utterances
below a real voiced-duration threshold; (c) filter a denylist of known
hallucination phrases and 1–2 char junk before treating text as a turn.

---

## P0-2 · VAD false triggers / barge-in storm (browser echo)
**Symptom:** endless `responder cancelled (barge-in)` with no real user speech; the
agent talks over itself and never settles.

**Evidence (logs):** ~15 `responder cancelled (barge-in)` lines, clustered after the
agent speaks, with no meaningful transcript between them.

**Root cause:** in the browser without headphones, the agent's (now louder/longer)
Sarvam audio plays through the speakers, the mic picks it up, VAD fires
`speech_start`, which cancels the response and starts a new "utterance" that is the
agent's own audio tail → feeds P0-1. On a real phone line the inbound track is
caller-only, so this is primarily a browser-echo issue, but noise sensitivity
affects phone too.

**Fix:** tune VAD (aggressiveness 2→3, higher min-speech, slightly longer onset),
and gate/ignore junk utterances (shared with P0-1). Headphones remain recommended
for browser testing.

---

## P0-3 · Admin language selection is missing (FEATURE)
**Symptom:** language is hardcoded to `en-IN`; the caller had to ask mid-call
"Can I speak in Hindi?", and even then STT stayed on English.

**Requirement:** as an **admin**, before starting a call, pick the language for
that call (not asked to the customer). Support the popular Indian languages, not
just English/Hindi. Focus on Indian customers.

**Fix:** a per-call `language` threaded through the whole pipeline:
- **STT** — pass the language code to Whisper (stop forcing `en`).
- **LLM** — instruct the agent to reply only in that language.
- **TTS** — set Sarvam `target_language_code` per call.
- **Frontend** — a language dropdown on the New Call page (for both the browser
  test call and the outbound dialer).
Sarvam Bulbul supports: Hindi, English, Bengali, Gujarati, Kannada, Malayalam,
Marathi, Odia, Punjabi, Tamil, Telugu (all `xx-IN`).

---

## P1-1 · Sarvam TTS latency is 2–6 s per turn (PERF regression)
**Symptom:** long pause before the agent speaks, much worse than Piper.

**Evidence (logs):** `first_audio` = 2167–**6274 ms**; individual Sarvam calls
860–**4481 ms** (Hindi sentences are the slowest); greeting synthesis ~3 s.

**Root cause:** Sarvam Bulbul v3 **REST** synthesizes the whole sentence before
returning, and we call it sentence-by-sentence sequentially. The first sentence's
full synthesis time *is* the time-to-first-audio.

**Fix options (in order):** (a) use Sarvam's **streaming** TTS (websocket) so audio
starts flowing before the sentence is done; (b) speak the first, short sentence
first (already do) and pre-split more aggressively; (c) lower sample rate for phone;
(d) keep Piper as a fast fallback for English. Target: first-audio < 1.5 s.

---

## P1-2 · Not India-aware; slot extraction errors (QUALITY)
**Symptom:** misread Indian context.

**Evidence (logs):** `city: 'Vila'` (caller said "villa" — a property *type*, not a
city); `budget: '$20k'` (dollar sign for an Indian caller); "rent a day"
misheard; no awareness of Indian cities/localities.

**Root cause:** prompts are generic/US-centric; extraction has no India grounding
(cities, INR budget formats like lakh/crore, property types vs place names).

**Fix:** ground the persona + extraction prompts in Indian real estate — recognise
Indian cities/localities, budgets in ₹ lakh/crore, and distinguish property types
(flat/apartment/villa/plot/BHK) from city names.

---

## Fix order
1. **P0-1 + P0-2 together** — turn-taking robustness (junk/hallucination filter +
   VAD tuning). Unusable calls until this is fixed; also unblocks testing everything
   else.
2. **P0-3** — admin language selection across STT/LLM/TTS + frontend selector.
3. **P1-2** — India-aware prompts + extraction.
4. **P1-1** — Sarvam streaming to bring latency back down.

---

## Resolution (all fixed)
- **P0-1 / P0-2** ✅ VAD tuned (aggressiveness 3, min-speech 350 ms); STT `language`
  set per call + `temperature=0`; noise/hallucination denylist drops junk turns.
- **P0-3** ✅ Per-call language (11 Indian languages) threaded through STT + LLM +
  TTS; admin selector on the New Call page; localized greeting.
- **P1-2** ✅ India-aware persona + extraction (Indian cities, ₹ lakh/crore, and
  property-type vs city disambiguation — "villa" no longer becomes a city).
- **P1-1** ✅ Sarvam HTTP streaming (linear16). First-audio ~0.3-0.65 s (was
  ~2.5 s). Browser + phone both stream (Web Audio / continuous μ-law). Remaining
  turn latency is now STT + LLM, not TTS.

---

## Follow-up (Hindi call): echo-driven hallucination loop
**Symptom:** in a Hindi browser call, Whisper hallucinated "झाल" repeatedly →
same barge-in storm as the English "Thank you." loop; garbage slots locked in
(city "Diliseria", "2 BHK plot").

**Diagnosis:** Whisper reports these with `no_speech_prob=0` / good `avg_logprob`
— *confident* hallucinations, so confidence filtering can't catch them. Root
cause is acoustic **echo**: streamed TTS from the speakers leaks into the mic and
VAD treats it as ~1 s of speech. Phone calls are immune (separate caller track).

**Fixed:**
- **Half-duplex mic gating (browser)** — don't capture while the agent is
  speaking. Kills the echo loop at the source. Phone stays full-duplex + barge-in.
- **Consecutive-repeat guard** — drops identical short transcripts back-to-back.
- **STT confidence net (conservative)** — safety net for true silence on phone.
- **Outbound number whitespace strip.**

---

## Noise-robustness audit (measured) — why it breaks in a real environment

Tested the VAD + STT pipeline against generated noise/speech. Numbers are from the
harness (16 kHz mono, current settings: webrtcvad aggr=3, silence=450 ms,
min_speech=350 ms).

### VAD false-triggering vs noise
| condition | frames flagged "speech" | speech_start (barge-in) | utterances delivered |
|---|---|---|---|
| digital silence / quiet white noise | 0-3% | 0 | 0 ✓ |
| moderate speech-band noise (-30 dBFS) | 34% | 0 | 0 |
| **loud white noise (-20 dBFS)** | 100% | **1** | **0** |
| **loud speech-band noise (-25 dBFS, TV/babble)** | 100% | **1** | **0** |
| clean speech | 77% | 1 | 1 ✓ |
| speech + noise @ 20 dB SNR | 73% | 1 | 1 ✓ |
| **speech + noise @ 10 dB SNR** | 100% | 1 | **0** |
| **speech + noise @ 5 dB SNR** | 100% | 1 | **0** |
| **speech with 700 ms mid-sentence pause** | 65% | 2 | **2 (split!)** |

### STT on noise (after our filters)
| input | transcript | filtered? |
|---|---|---|
| loud speech-band noise (English) | "." | dropped ✓ |
| **loud speech-band noise (Hindi)** | **"झाल"** | **passes** |
| real speech @ ~2 dB SNR | "Budget is 90 **laps**." | passes (content corrupted) |

### Root-cause bottlenecks (ranked by real-world impact)
1. **CRITICAL — endpointing dies under sustained noise.** When noise keeps
   webrtcvad "speech"-active (10 dB SNR and worse, or loud noise), the 450 ms
   trailing silence never occurs, so **UTTERANCE never fires — the caller's turn is
   never processed.** They talk; nothing happens. On the phone the initial
   speech_start also cut the agent off, so the call freezes. This is the #1 reason
   it fails in a real room.
2. **CRITICAL — naive barge-in.** Any loud sound (door, TV, cough) fires
   speech_start and cancels the agent on the full-duplex phone. No sustained-speech
   confirmation, no energy/confidence gate.
3. **HIGH — premature endpointing.** A 700 ms natural thinking pause splits one
   sentence into two turns; the agent replies to half a thought. silence=450 ms is
   too short for natural speech.
4. **HIGH — webrtcvad can't separate speech from speech-like noise.** It's a 2011
   energy/GMM detector; speech-band noise = "100% speech." Root cause of 1-2.
5. **MEDIUM — no energy/SNR gate.** No loudness floor or adaptive noise-floor.
6. **MEDIUM — STT confident-garbage on noise**, esp. non-English ("झाल" passes).

### Fix plan (addresses 1-5 together)
- **Replace webrtcvad with Silero VAD (neural)** — runs on the onnxruntime we
  already have (no torch), rejects most non-speech. Behind the existing VAD
  interface, so the call loop is untouched.
- **Energy gate + adaptive noise floor** — ignore audio below the running noise
  floor; only real, loud-enough speech counts.
- **Smarter endpointing** — raise silence to ~700-800 ms (fix pause-splitting) and
  add a max-utterance flush so sustained noise can't freeze a turn forever.
- **Barge-in debounce** — require ~300-400 ms of *confirmed* speech before
  cancelling the agent, so a brief noise spike doesn't cut Kavya off.

---

## Noise robustness — FIXED (Silero VAD + energy gate + debounce)

Replaced webrtcvad with **Silero VAD** (neural, via onnxruntime — no torch) plus an
energy floor, a debounced onset, and pause-tolerant endpointing with a max-utterance
flush. webrtcvad kept as `VAD_BACKEND=webrtc` fallback.

Key implementation note: Silero v5 ONNX needs 64 samples of context prepended to
each 512-sample window — without it, even clear speech scores ~0.

### Before → after (same harness)
| condition | before | after |
|---|---|---|
| loud white / TV-babble noise | false barge-in | **0 false triggers** |
| speech @ 10 dB SNR | turn LOST (0 utterances) | **delivered (1)** |
| speech @ 5 dB SNR | turn LOST (0 utterances) | **delivered (1)** |
| 100 ms noise click | would fire barge-in | **ignored (debounce)** |
| natural pause ≤ 700 ms | split into 2 turns | **kept as 1** |
| end-to-end @ 10 dB SNR | nothing happened | **heard + replied correctly** |

Endpoint silence raised 450 → 800 ms (tolerates natural pauses); this adds ~350 ms
end-of-turn latency — an intentional trade for not cutting callers off mid-thought.

---

## Hindi / Hinglish naturalness — issues + fix plan

English is now near-natural. A Hindi (hi-IN) test call exposed language-specific
problems. Research first ([Sarvam ASR](https://www.sarvam.ai/speech-to-text),
[Gnani code-switching](https://www.gnani.ai/resources/blogs/blog-code-switching-speech-recognition-hinglish-asr),
[Deepgram Hinglish](https://deepgram.com/learn/hinglish-voice-ai-speech-recognition),
[Sarvam voice-agent test](https://growwstacks.com/blog/sarvam-ai-tts-stt-voice-agent-test/)):
the consensus is (a) Whisper garbles code-mixed phone audio, (b) most APIs wrongly
treat Hindi and English as separate languages, and (c) Hindi turns run 2.5-4 s vs
~800 ms for English. Our logs match all three. *(Rephrased from sources for
licensing compliance.)*

### Issues observed (call `eefd6019`, hi-IN)
1. **P0 — STT garbles Hindi/Hinglish.** whisper-large-v3-turbo mangles
   conversational Hindi: "लगभग बीस हज़ार" → **"लगब बदस जार के आस पस"**, "गुड़गाँव" →
   **"गुर गाओ"**, plus "लगवक्त", "टूंडाओं", "दन्ने बाद". Garbage in → garbage
   everywhere downstream.
2. **P0 — no real code-switching.** `language="hi"` forces Hindi-only decoding;
   callers naturally mix English ("...so please proceed", "10,000"). The research
   is unanimous that Hindi+English must be handled as one stream.
3. **P1 — Hindi intent misread.** "**कर दो**" (= "go ahead / book it") was extracted
   as `wants_to_end=True` and routed to END — the opposite of intent. The English
   extraction prompt on the small model misreads Hindi cues.
4. **P1 — replies too long/slow in Hindi.** Multi-sentence Hindi replies pushed
   turns to 5-7 s total; the caller even said "हेलो आप सुन रहे" (are you there?)
   thinking the line dropped.
5. **P2 — endpoint latency.** The 800 ms silence window (great for not cutting
   people off) makes English "pause a bit" and compounds Hindi's slower TTS/STT.

### Fix plan
1. **Swap STT to Sarvam Saaras v3 for Indian-language calls** (we already have the
   key). Use `model=saaras:v3, mode=codemix` — it returns Hinglish with English
   words in English and Hindi in Devanagari, and is tuned for Indian accents and
   telephony audio. Route by call language: en-IN → Groq Whisper (fast); hi-IN and
   other Indic → Sarvam Saaras. Fixes #1 and #2 at the root.
2. **Hinglish-aware extraction.** Add Hindi/Hinglish intent cues to the extraction
   prompt: कर दो / हाँ / बुक कर दो / proceed → wants_to_book; नहीं / रहने दो / बाद
   में → end/callback. Cleaner Saaras transcripts also make extraction far more
   reliable. Fixes #3.
3. **Shorter Hindi replies.** Persona: on phone keep replies to ONE short sentence
   (Hindi TTS is slower), so turns stay snappy and the caller never wonders if the
   line dropped. Helps #4.
4. **Latency pass (later).** Consider a slightly shorter, language-adaptive endpoint
   for English, and keep leaning on Sarvam streaming. Addresses #5.

### Hindi/Hinglish — FIXED
- **STT → Sarvam Saaras v3 (`codemix`)** for Indian-language calls via an `STTRouter`
  (English stays on Groq Whisper). Measured on Hinglish audio:
  - "Gurgaon...2 BHK": Whisper "गुर्गाओं...दो भी एज के" → Saaras "गुड़गांव...दो बीएचके" ✓
  - "book कर दो please": Whisper "बुक कर दो प्लीज" → Saaras "book कर दो please" (English kept) ✓
  - "agले month move": Whisper "मंथ मूफ" → Saaras "अगले month move" ✓
- **Hinglish intent cues** in extraction: "कर दो" now → wants_to_book (was wrongly
  wants_to_end→END). Verified: कर दो→book, नहीं रहने दो→end, book कर दो please→book.
- **Shorter Hindi replies** (one warm sentence) to keep turns snappy.
- End-to-end hi-IN call: heard "मुझे गुड़गांव में BHK flat चाहिए, बजट ₹20000" →
  slots {Gurgaon, 20k, BHK flat} → warm one-line Hindi reply. Clean Hinglish throughout.

---

## Conversation stalls (silent agent) — FIXED: gpt-oss reasoning

**Symptom:** call "just stops" — a turn logs `first_audio=None, total=~1.5s` (agent
said nothing), in both Hindi and English. Seen at stage transitions.

**Root cause:** gpt-oss is a *reasoning* model. On Groq its default reasoning
consumed the 300-token budget (measured ~919 chars of hidden reasoning), so ~**2 of
4 turns produced EMPTY content** → the agent spoke nothing → silence. It also added
~400 ms/turn (part of the slow 3-5 s turns).

**Fix:**
- Pass `extra_body={"reasoning_effort": "low"}` to the conversation LLM (Groq SDK
  0.15 doesn't take it as a kwarg), and raise max_tokens 300→400. Measured:
  empties **2/4 → 0/5**, LLM latency **~646 ms → ~250 ms**.
- Defense-in-depth: if a reply is ever empty, speak a short fallback so the call
  never goes silent.
- Verified: 5/5 booking-transition turns now return a warm reply, 0 empties.
