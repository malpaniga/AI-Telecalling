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
import inspect
import logging
import random
import time
from collections.abc import Callable
from statistics import mean
from typing import Protocol

from backend.agent.engine import ConversationEngine
from backend.agent.prompts import interpolate_template
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
    "mr-IN": "माफ करा, मला नीट ऐकू आलं नाही. तुम्ही पुन्हा सांगाल का?",
    "gu-IN": "માફ કરશો, મને બરાબર સંભળાયું નહીં. શું તમે ફરીથી કહી શકશો?",
    "ta-IN": "மன்னிக்கவும், எனக்கு சரியாக கேட்கவில்லை. மீண்டும் சொல்ல முடியுமா?",
    "te-IN": "క్షమించండి, నాకు సరిగ్గా వినపడలేదు. మళ్ళీ చెప్పగలరా?",
    "kn-IN": "ಕ್ಷಮಿಸಿ, ನನಗೆ ಸರಿಯಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೊಮ್ಮೆ ಹೇಳುತ್ತೀರಾ?",
    "bn-IN": "দুঃখিত, আমি ঠিক শুনতে পাইনি। আপনি কি আবার বলবেন?",
    "pa-IN": "ਮਾਫ਼ ਕਰਨਾ, ਮੈਨੂੰ ਠੀਕ ਤਰ੍ਹਾਂ ਸੁਣਿਆ ਨਹੀਂ। ਕੀ ਤੁਸੀਂ ਦੁਬਾਰਾ ਕਹਿ ਸਕਦੇ ਹੋ?",
}

_SERVER_ERROR_FALLBACK = {
    "en-IN": "One moment please, let me check that information.",
    "hi-IN": "एक क्षण रुकिए, मैं जानकारी देख कर बताती हूँ।",
    "mr-IN": "एक सेकंद, मी माहिती तपासून सांगते.",
    "gu-IN": "એક ક્ષણ, હું વિગતો તપાસીને કહું છું.",
    "ta-IN": "ஒரு நிமிடம், நான் விவரங்களை சரிபார்க்கிறேன்.",
    "te-IN": "ఒక్క క్షణం, నేను వివరాలను పరిశీలిస్తాను.",
    "kn-IN": "ಒಂದು ಕ್ಷಣ, ನಾನು ವಿವರಗಳನ್ನು ಪರಿಶೀಲಿಸುತ್ತೇನೆ.",
    "bn-IN": "এক মুহূর্ত, আমি তথ্যটি দেখে নিচ্ছি।",
    "pa-IN": "ਇੱਕ ਪਲ ਰੁਕੋ, ਮੈਂ ਜਾਣਕਾਰੀ ਚੈੱਕ ਕਰਦੀ ਹਾਂ।",
}

_HALLUCINATION_PHRASES = {
    "thanks for watching", "thank you for watching", "please subscribe",
    "you", "the", ".", "..", "...", "uh", "um", "hmm",
}

# Conversational fillers played concurrently with LLM to mask response latency
_FILLERS: dict[str, list[str]] = {
    "mr-IN": ["हं...", "बरोबर...", "अच्छा..."],
    "hi-IN": ["हम्म...", "अच्छा...", "जी..."],
    "en-IN": ["Sure...", "Right...", "I see..."],
}


def _looks_like_noise(text: str) -> bool:
    """True if the transcript is almost certainly a hallucination or noise blip."""
    t = text.strip().lower().rstrip(".!?,")
    if not any(c.isalnum() for c in t):
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
        agent_name: str | None = None,
        custom_greeting: str | None = None,
        system_prompt: str | None = None,
        variables: dict[str, str] | None = None,
        greeting: str | None = None,
        barge_in_sensitivity: int | None = None,
        voice_id: str | None = None,
        call_id: str | None = None,
    ):
        self.t = transport
        self.voice_id = voice_id
        self.stt = stt
        self.engine = engine
        self.tts = tts
        self.store = store
        self.direction = direction
        self.agent_name = agent_name
        self.variables = variables or {}
        raw_greeting = custom_greeting or greeting
        self.custom_greeting = interpolate_template(raw_greeting, self.variables) if raw_greeting else None
        self.system_prompt = interpolate_template(system_prompt, self.variables) if system_prompt else None

        self.language, info = resolve_language(language)
        self.whisper_lang = info["whisper"]
        self.language_name = info["name"]

        self.state = new_conversation_state()
        self.latencies: list[int] = []
        self.call_id = call_id
        self.lead_id = None

        self.barge_in_sensitivity = 70 if barge_in_sensitivity is None else barge_in_sensitivity
        # Dynamic VAD tuning to reject fan noise, breathing, and acoustic bleed:
        speech_prob = max(0.45, min(0.75, 0.80 - (self.barge_in_sensitivity / 100.0) * 0.30))
        energy_floor = max(-52.0, min(-36.0, -42.0 - (self.barge_in_sensitivity / 100.0) * 8.0))
        # WebRTC returns binary probabilities, so probability thresholds alone
        # cannot make its interruption onset more or less responsive.
        confirm_ms = max(40, round(settings.vad_speech_confirm_ms * (
            2.0 - 1.5 * self.barge_in_sensitivity / 100.0
        )))
        self.endpointer = VADEndpointer(
            speech_prob=speech_prob,
            energy_floor_dbfs=energy_floor,
            confirm_ms=confirm_ms,
        )

        self.responder: asyncio.Task | None = None
        self._filler_task: asyncio.Task | None = None
        self._last_user_text = ""
        self._in_greeting = False
        self._is_speaking = False
        self._call_ending = False

        # Cache run_turn signature once — avoid inspect overhead on every utterance
        _sig = inspect.signature(self.engine.run_turn)
        self._can_pass_prompt = "system_prompt" in _sig.parameters or any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in _sig.parameters.values()
        )

    # ---- helpers ----
    async def _say(self, text: str, on_audio: Callable[[], None] | None = None) -> float:
        self._is_speaking = True
        await self.t.notify({"type": "agent", "text": text})
        if self.call_id:
            try:
                from backend.telephony.broadcaster import call_broadcaster
                await call_broadcaster.broadcast(str(self.call_id), {"type": "agent", "text": text})
            except Exception:
                pass
        total_duration = 0.0
        try:
            # Streaming transports (phone) play progressive chunks for low latency;
            # simple transports (browser) get one clean clip.
            synth_kwargs = {"voice_id": self.voice_id} if self.voice_id else {}
            if getattr(self.t, "streaming", False):
                async for chunk, sr in self.tts.synthesize_stream(text, self.language, **synth_kwargs):
                    if chunk:
                        duration = len(chunk) / (2.0 * max(sr, 8000))
                        total_duration += duration
                        await self.t.play(chunk, sr)
                        if on_audio is not None:
                            on_audio()
            else:
                pcm, sr = await self.tts.synthesize(text, self.language, **synth_kwargs)
                if pcm:
                    total_duration = len(pcm) / (2.0 * max(sr, 8000))
                    await self.t.play(pcm, sr)
                    if on_audio is not None:
                        on_audio()
        except Exception as exc:
            log.warning("TTS synthesis failed for text %r: %s", text[:30], exc)
            await self.t.notify({
                "type": "error",
                "message": f"TTS playback error: {exc}. Please verify your TTS provider in Admin.",
            })
        finally:
            self._is_speaking = False
        return total_duration

    async def _greeting_text(self) -> str:
        """Return custom greeting, or generate one in the call language."""
        if self.custom_greeting and self.custom_greeting.strip():
            return self.custom_greeting.strip()

        name = self.agent_name or "Kavya"
        if self.language == "en-IN":
            return GREETING if not self.agent_name else GREETING.replace("Kavya", self.agent_name)

        try:
            prompt = (
                f"You are {name}, a warm and helpful phone assistant in India. "
                f"Write ONE short, warm phone greeting in {self.language_name}, "
                f"OPENING with the culturally natural greeting for that language (for example 'Namaste' or 'Namaskar' in Hindi/Marathi, 'Vanakkam' in Tamil). "
                f"Introduce yourself as {name} and ask how you can help them today. "
                f"Write in the language's NATIVE SCRIPT (Devanagari for Hindi/Marathi), never romanized Latin. "
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
        if self.call_id is None:
            try:
                call, lead = await repo.start_call(direction=self.direction)
                self.call_id, self.lead_id = call.id, lead.id
                log.info("call connected call=%s (%s)", self.call_id, self.direction)
            except Exception as exc:  # noqa: BLE001
                log.warning("failed to create call record (continuing unpersisted): %s", exc)
        else:
            log.info("call connected with existing call=%s (%s)", self.call_id, self.direction)

        if self.call_id:
            try:
                from backend.telephony.broadcaster import call_broadcaster
                await call_broadcaster.broadcast(str(self.call_id), {"type": "ready", "status": "connected"})
            except Exception:
                pass

        # Transports await start() before reading microphone frames. Own the
        # greeting as a responder so synthesis cannot block input or barge-in.
        self._in_greeting = True
        self.responder = asyncio.create_task(self._run_greeting())
        await self.t.notify({"type": "ready"})

    async def _run_greeting(self) -> None:
        greeting = await self._greeting_text()
        self.state["messages"].append({"role": "assistant", "content": greeting})
        log.info("call language=%s (%s)", self.language, self.language_name)
        self._in_greeting = True
        greeting_start = time.monotonic()
        greeting_duration = await self._say(greeting)
        elapsed = time.monotonic() - greeting_start
        remaining = max(0.0, greeting_duration - elapsed)
        self._greeting_end_time = time.monotonic() + remaining + 0.3

        await self._persist_turn("agent", greeting, GREETING_STAGE)
        await self._save_session()
        await self.t.notify({
            "type": "state",
            "stage": self.state["stage"],
            "slots": self.state["slots"],
            "output_variables": self.state.get("output_variables", {}),
        })
        await self.t.notify({"type": "ready"})

    async def handle_interrupt(self) -> None:
        """Handle explicit caller interrupt event (barge-in)."""
        self._in_greeting = False
        # Stop producers before clearing queued audio, without waiting for DB
        # persistence in responder cancellation cleanup before flushing playback.
        if self.responder is not None:
            self.responder.cancel()
        if self._filler_task is not None:
            self._filler_task.cancel()
        try:
            await self.t.clear()
        finally:
            await self._cancel_responder()

    async def feed_pcm16(self, pcm: bytes) -> None:
        """Feed a chunk of caller audio; drives VAD, barge-in, and responses."""
        if self._call_ending:
            return
        for event, payload in self.endpointer.process(pcm):
            if event == SPEECH_START:
                await self.handle_interrupt()
            elif event == UTTERANCE:
                log.info("VAD detected UTTERANCE: %d bytes (%.2f s)", len(payload) if payload else 0, (len(payload) / 32000.0) if payload else 0)
                if not self._call_ending and payload:
                    self._in_greeting = False
                    await self._cancel_responder()
                    self.responder = asyncio.create_task(self._handle_utterance(payload))

    async def _handle_utterance(self, audio_pcm: bytes) -> None:
        if self._call_ending:
            return
        set_trace_id()
        t0 = time.perf_counter()
        wav = pcm_to_wav(audio_pcm, settings.audio_sample_rate)
        reply_parts: list[str] = []
        try:
            user_text = await self.stt.transcribe(
                wav, filename="utterance.wav", language=self.language
            )
            log.info("STT transcribed: %r (%.0f ms)", user_text, (time.perf_counter() - t0) * 1000)
            if not user_text or _looks_like_noise(user_text):
                if user_text:
                    log.info("ignoring likely-noise transcript: %r", user_text)
                await self.t.notify({"type": "info", "text": "(didn't catch that)"})
                await self.t.notify({"type": "ready"})
                return

            if self._is_speaking and user_text == self._last_user_text and len(user_text) < 15:
                log.info("ignoring echo transcript during agent speech: %r", user_text)
                await self.t.notify({"type": "ready"})
                return

            self._last_user_text = user_text
            await self.t.notify({"type": "user", "text": user_text})
            await self._persist_turn("user", user_text, self.state["stage"])
            if self.call_id:
                try:
                    from backend.telephony.broadcaster import call_broadcaster
                    await call_broadcaster.broadcast(str(self.call_id), {"type": "user", "text": user_text})
                except Exception:
                    pass

            first_audio_ms: int | None = None

            def record_first_audio() -> None:
                nonlocal first_audio_ms
                if first_audio_ms is None:
                    first_audio_ms = int((time.perf_counter() - t0) * 1000)

            should_hangup = False

            # Use cached signature check (computed once at __init__)
            if self._can_pass_prompt and self.system_prompt:
                turn_generator = self.engine.run_turn(
                    self.state, user_text, self.language_name, system_prompt=self.system_prompt
                )
            else:
                turn_generator = self.engine.run_turn(self.state, user_text, self.language_name)

            # Fill long LLM waits, but never delay an answer for filler synthesis.
            # Only for utterances >= 4 words (complex enough to warrant thinking time).
            filler_task: asyncio.Task | None = None
            filler_list = _FILLERS.get(self.language, [])
            if filler_list and len(user_text.split()) >= 4 and not self._in_greeting:
                filler_task = asyncio.create_task(self._say(random.choice(filler_list), record_first_audio))
                self._filler_task = filler_task

            async for sentence in turn_generator:
                if filler_task is not None:
                    await self._cancel_filler()
                    filler_task = None
                clean_sentence = sentence.replace("[HANGUP]", "").replace("[hangup]", "").strip()
                if "[HANGUP]" in sentence.upper():
                    should_hangup = True
                if clean_sentence:
                    reply_parts.append(clean_sentence)
                    await self._say(clean_sentence, record_first_audio)

            await self._cancel_filler()

            if not reply_parts:
                # LLM returned nothing — never leave the caller in silence.
                fallback = _EMPTY_FALLBACK.get(self.language, _EMPTY_FALLBACK["en-IN"])
                log.warning("empty LLM reply; speaking fallback")
                reply_parts.append(fallback)
                await self._say(fallback, record_first_audio)

            total_ms = int((time.perf_counter() - t0) * 1000)
            self.latencies.append(total_ms)
            log.info("turn latency: first_audio=%sms total=%sms", first_audio_ms, total_ms)
            await self._persist_turn("agent", " ".join(reply_parts), self.state["stage"], total_ms)
            await self._save_session()
            await self.t.notify({
                "type": "state",
                "stage": self.state["stage"],
                "slots": self.state["slots"],
                "output_variables": self.state.get("output_variables", {}),
            })
            await self.t.notify({
                "type": "variables_update",
                "variables": self.state.get("output_variables", {}),
                "slots": self.state["slots"],
            })
            await self.t.notify({"type": "turn_end", "first_audio_ms": first_audio_ms, "total_ms": total_ms})
            if self.call_id:
                try:
                    from backend.telephony.broadcaster import call_broadcaster
                    await call_broadcaster.broadcast(str(self.call_id), {
                        "type": "state",
                        "stage": self.state["stage"],
                        "slots": self.state["slots"],
                        "output_variables": self.state.get("output_variables", {}),
                    })
                except Exception:
                    pass

            # Automated Call Hangup Check
            full_reply = " ".join(reply_parts).lower()
            wrap_phrases = [
                # Marathi phrases
                "दिवस शुभ जावो", "दिवस चांगला जावो", "बोलल्याबद्दल धन्यवाद",
                "शुभ दिवस", "तुमचा दिवस", "आपला दिवस", "दिवस आनंदाचा जावो",
                "काळजी घ्या", "पुन्हा संपर्क", "वेळ दिल्याबद्दल धन्यवाद",
                # Hindi phrases
                "दिन शुभ", "अच्छा रहे", "बात करने के लिए धन्यवाद",
                "धन्यवाद, बाय", "अलविदा", "ख्याल रखें",
                # English phrases
                "have a nice day", "have a great day", "have a good day",
                "goodbye", "bye bye", "take care", "thank you for your time",
                "thank you, bye", "call completed",
            ]
            disposition = (self.state.get("output_variables") or {}).get("disposition")
            # Do NOT prematurely hang up if caller merely declined a booking and call is still active
            has_wrap_phrase = any(p in full_reply for p in wrap_phrases) and disposition != "declined_booking"
            if should_hangup or self.state.get("stage") == "end" or has_wrap_phrase:
                self._call_ending = True
                log.info("Call wrap-up detected, notifying transport to hang up")
                await self.t.notify({"type": "hangup", "reason": "call_completed"})
                if self.call_id:
                    try:
                        from backend.telephony.broadcaster import call_broadcaster
                        await call_broadcaster.broadcast(str(self.call_id), {"type": "hangup", "reason": "call_completed"})
                    except Exception:
                        pass

                async def _delayed_close() -> None:
                    await asyncio.sleep(3.5)
                    if hasattr(self.t, "close"):
                        try:
                            await self.t.close()
                        except Exception:
                            pass

                asyncio.create_task(_delayed_close())
        except asyncio.CancelledError:
            partial = " ".join(reply_parts).strip()
            if partial:
                self.state["messages"].append({"role": "assistant", "content": partial})
                await self._persist_turn("agent", partial + " …(interrupted)", self.state["stage"])
            log.info("responder cancelled (barge-in)")
            raise
        except Exception as exc:  # noqa: BLE001
            await self._cancel_filler()
            log.exception("turn failed, recovering: %s", exc)
            fallback = _SERVER_ERROR_FALLBACK.get(self.language, _SERVER_ERROR_FALLBACK["en-IN"])
            await self._say(fallback)
            self.state["messages"].append({"role": "assistant", "content": fallback})
            await self._persist_turn("agent", fallback, self.state["stage"])
            await self.t.notify({"type": "turn_end"})
        finally:
            await self._cancel_filler()

    async def _cancel_filler(self) -> None:
        task = self._filler_task
        self._filler_task = None
        if task is not None:
            if not task.done():
                task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    async def _cancel_responder(self) -> None:
        if self._filler_task is not None:
            self._filler_task.cancel()
        if self.responder is not None:
            if not self.responder.done() and not self.responder.cancelling():
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
