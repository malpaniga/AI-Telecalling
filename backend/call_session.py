"""Transport-agnostic call pipeline.

`CallSession` owns everything that makes a call work — VAD endpointing, the
conversation engine, barge-in, latency tracking, and persistence — and talks to
the outside world only through a `Transport`. The browser and Twilio each provide
a thin Transport, so both share the exact same brain.

Audio contract: the session works in 16-bit mono PCM at `settings.audio_sample_rate`.
Transports feed caller audio in via `feed_pcm16`, and receive agent audio out via
`Transport.play(pcm16, sample_rate)` (sample_rate is whatever the TTS produced;
the transport resamples/encodes as its medium requires).
"""

import asyncio
import logging
import time
from statistics import mean
from typing import Protocol

from backend.agent.engine import ConversationEngine
from backend.agent.state import GREETING as GREETING_STAGE
from backend.agent.state import new_conversation_state
from backend.audio.stt import STTClient
from backend.audio.tts import TTSEngine, pcm_to_wav
from backend.audio.vad import SPEECH_START, UTTERANCE, VADEndpointer
from backend.config import settings
from backend.languages import resolve as resolve_language
from backend.logging_setup import set_trace_id
from backend.memory import repository as repo
from backend.memory.session import SessionStore

log = logging.getLogger("call")

GREETING = "Hello, and thank you so much for calling Rishab Developers! This is Kavya, and I'd be delighted to help you find the perfect place. Are you looking to buy or rent?"

# Phrases Whisper hallucinates on silence / non-speech / echo. If the WHOLE
# transcript is one of these (or junk), we ignore the "turn" instead of acting on it.
# Said if the LLM ever returns nothing, so the call never falls silent.
_EMPTY_FALLBACK = {
    "en-IN": "Sorry, could you say that again?",
    "hi-IN": "माफ़ कीजिए, क्या आप दोबारा बता सकते हैं?",
}

_HALLUCINATION_PHRASES = {
    "thank you", "thanks", "thank you very much", "thank you so much",
    "thanks for watching", "thank you for watching", "please subscribe",
    "you", "the", "bye", ".", "..", "...", "uh", "um", "hmm", "yeah",
}


def _looks_like_noise(text: str) -> bool:
    """True if the transcript is almost certainly a hallucination or noise blip."""
    t = text.strip().lower().rstrip(".!?,")
    if len(t) <= 1:
        return True
    if not any(c.isalpha() for c in t):  # punctuation / numbers-only garble
        return True
    return t in _HALLUCINATION_PHRASES


class Transport(Protocol):
    """A medium (browser websocket, phone line) the session speaks through."""

    async def play(self, pcm16: bytes, sample_rate: int) -> None:
        """Send agent audio to the caller."""

    async def clear(self) -> None:
        """Flush any audio already queued on the caller side (barge-in)."""

    async def notify(self, event: dict) -> None:
        """Deliver a metadata event (transcript, stage, etc.). May be a no-op."""


class CallSession:
    def __init__(
        self,
        transport: Transport,
        stt: STTClient,
        engine: ConversationEngine,
        tts: TTSEngine,
        store: SessionStore,
        direction: str = "inbound",
        language: str = "en-IN",
    ):
        self.t = transport
        self.stt = stt
        self.engine = engine
        self.tts = tts
        self.store = store
        self.direction = direction

        self.language, info = resolve_language(language)
        self.whisper_lang = info["whisper"]
        self.language_name = info["name"]

        self.state = new_conversation_state()
        self.latencies: list[int] = []
        self.call_id = None
        self.lead_id = None
        self.endpointer = VADEndpointer()
        self.responder: asyncio.Task | None = None
        self._last_user_text = ""

    # ---- helpers ----
    async def _say(self, text: str) -> None:
        await self.t.notify({"type": "agent", "text": text})
        # Streaming transports (phone) play progressive chunks for low latency;
        # simple transports (browser) get one clean clip.
        if getattr(self.t, "streaming", False):
            async for chunk, sr in self.tts.synthesize_stream(text, self.language):
                await self.t.play(chunk, sr)
        else:
            pcm, sr = await self.tts.synthesize(text, self.language)
            if pcm:
                await self.t.play(pcm, sr)

    async def _greeting_text(self) -> str:
        """English greeting as-is; otherwise generate one in the call language."""
        if self.language == "en-IN":
            return GREETING
        try:
            prompt = (
                f"You are Kavya, a warm and caring customer-support agent at Rishab "
                f"Developers, a real estate company in India. Write ONE short, warm phone "
                f"greeting in {self.language_name}, OPENING with the culturally natural "
                f"greeting for that language (for example 'Namaste' or 'Namaskar' in Hindi, "
                f"'Vanakkam' in Tamil). Introduce yourself as Kavya from Rishab Developers "
                f"and warmly ask whether they're looking to buy or rent. Write in the "
                f"language's NATIVE SCRIPT (Devanagari for Hindi), never romanized Latin. "
                f"Sound like a friendly human, not a bot. Reply with only the greeting, no quotes."
            )
            text = await self.engine.llm.complete([{"role": "user", "content": prompt}])
            return text.strip() or GREETING
        except Exception as exc:  # noqa: BLE001
            log.warning("greeting generation failed, using English: %s", exc)
            return GREETING

    async def _persist_turn(self, role: str, text: str, stage: str, latency_ms: int | None = None) -> None:
        if self.call_id is None:
            return
        try:
            await repo.add_turn(self.call_id, role, text, stage, latency_ms)
        except Exception as exc:  # noqa: BLE001
            log.warning("failed to persist turn: %s", exc)

    async def _save_session(self) -> None:
        if self.call_id is not None:
            try:
                await self.store.save(str(self.call_id), self.state)
            except Exception as exc:  # noqa: BLE001
                log.warning("failed to save session: %s", exc)

    # ---- lifecycle ----
    async def start(self) -> None:
        try:
            call, lead = await repo.start_call(direction=self.direction)
            self.call_id, self.lead_id = call.id, lead.id
            log.info("call connected call=%s (%s)", self.call_id, self.direction)
        except Exception as exc:  # noqa: BLE001
            log.warning("failed to create call record (continuing unpersisted): %s", exc)

        greeting = await self._greeting_text()
        self.state["messages"].append({"role": "assistant", "content": greeting})
        log.info("call language=%s (%s)", self.language, self.language_name)
        await self._say(greeting)
        await self._persist_turn("agent", greeting, GREETING_STAGE)
        await self._save_session()
        await self.t.notify({"type": "state", "stage": self.state["stage"], "slots": self.state["slots"]})
        await self.t.notify({"type": "ready"})

    async def feed_pcm16(self, pcm: bytes) -> None:
        """Feed a chunk of caller audio; drives VAD, barge-in, and responses."""
        for event, payload in self.endpointer.process(pcm):
            if event == SPEECH_START:
                await self._cancel_responder()
                await self.t.clear()
            elif event == UTTERANCE:
                await self._cancel_responder()
                self.responder = asyncio.create_task(self._handle_utterance(payload))

    async def _handle_utterance(self, audio_pcm: bytes) -> None:
        set_trace_id()
        t0 = time.perf_counter()
        wav = pcm_to_wav(audio_pcm, settings.audio_sample_rate)
        reply_parts: list[str] = []
        try:
            user_text = await self.stt.transcribe(
                wav, filename="utterance.wav", language=self.language
            )
            if not user_text or _looks_like_noise(user_text):
                if user_text:
                    log.info("ignoring likely-noise transcript: %r", user_text)
                await self.t.notify({"type": "info", "text": "(didn't catch that)"})
                return
            # Consecutive identical short transcripts are almost always echo /
            # hallucination looping (e.g. "झाल" repeated), not a real repeat.
            if user_text == self._last_user_text and len(user_text) < 15:
                log.info("ignoring repeated short transcript: %r", user_text)
                await self.t.notify({"type": "info", "text": "(didn't catch that)"})
                return
            self._last_user_text = user_text
            await self.t.notify({"type": "user", "text": user_text})
            await self._persist_turn("user", user_text, self.state["stage"])

            first_audio_ms: int | None = None
            async for sentence in self.engine.run_turn(
                self.state, user_text, self.language_name
            ):
                reply_parts.append(sentence)
                await self._say(sentence)
                if first_audio_ms is None:
                    first_audio_ms = int((time.perf_counter() - t0) * 1000)

            if not reply_parts:
                # LLM returned nothing — never leave the caller in silence.
                fallback = _EMPTY_FALLBACK.get(self.language, _EMPTY_FALLBACK["en-IN"])
                log.warning("empty LLM reply; speaking fallback")
                reply_parts.append(fallback)
                await self._say(fallback)

            total_ms = int((time.perf_counter() - t0) * 1000)
            self.latencies.append(total_ms)
            log.info("turn latency: first_audio=%sms total=%sms", first_audio_ms, total_ms)
            await self._persist_turn("agent", " ".join(reply_parts), self.state["stage"], total_ms)
            await self._save_session()
            await self.t.notify({"type": "state", "stage": self.state["stage"], "slots": self.state["slots"]})
            await self.t.notify({"type": "turn_end"})
        except asyncio.CancelledError:
            partial = " ".join(reply_parts).strip()
            if partial:
                self.state["messages"].append({"role": "assistant", "content": partial})
                await self._persist_turn("agent", partial + " …(interrupted)", self.state["stage"])
            log.info("responder cancelled (barge-in)")
            raise
        except Exception as exc:  # noqa: BLE001
            log.exception("turn failed, recovering: %s", exc)
            await self._say("Sorry, I didn't quite catch that. Could you say it again?")
            await self.t.notify({"type": "turn_end"})

    async def _cancel_responder(self) -> None:
        if self.responder is not None and not self.responder.done():
            self.responder.cancel()
            try:
                await self.responder
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        self.responder = None

    async def finalize(self) -> None:
        await self._cancel_responder()
        if self.call_id is not None and self.lead_id is not None:
            avg_latency = int(mean(self.latencies)) if self.latencies else None
            try:
                score = await repo.finalize_call(
                    self.call_id, self.lead_id, self.state, avg_latency
                )
                await self.store.delete(str(self.call_id))
                log.info("call %s finalized (score=%d)", self.call_id, score)
            except Exception as exc:  # noqa: BLE001
                log.warning("failed to finalize call: %s", exc)
