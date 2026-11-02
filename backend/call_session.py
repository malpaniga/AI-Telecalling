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
from typing import Any, Protocol

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
from backend.telephony.recording import CallAudioRecorder

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
        qualification_schema: list[dict[str, Any]] | None = None,
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
        self.qualification_schema = qualification_schema or []
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
        self.recorder = None
        if call_id:
            try:
                self.recorder = CallAudioRecorder(call_id=str(call_id))
            except Exception as e:
                log.warning("failed to init CallAudioRecorder for call %s: %s", call_id, e)

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
                        if self.recorder and chunk:
                            try:
                                self.recorder.record_agent_pcm(chunk, sample_rate=sr)
                            except Exception:
                                pass
                        await self.t.play(chunk, sr)
                        if on_audio is not None:
                            on_audio()
            else:
                pcm, sr = await self.tts.synthesize(text, self.language, **synth_kwargs)
                if pcm:
                    total_duration = len(pcm) / (2.0 * max(sr, 8000))
                    if self.recorder and pcm:
                        try:
                            self.recorder.record_agent_pcm(pcm, sample_rate=sr)
                        except Exception:
                            pass
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
            try:
                db = repo.get_db()
            except Exception:
                db = None
            if db is not None and self.lead_id is None:
                try:
                    call_doc = await db["calls"].find_one({"_id": str(self.call_id)})
                    if call_doc and call_doc.get("lead_id"):
                        self.lead_id = str(call_doc["lead_id"])
                except Exception as exc:  # noqa: BLE001
                    log.warning("failed to resolve lead_id for call %s: %s", self.call_id, exc)
            log.info("call connected with existing call=%s lead=%s (%s)", self.call_id, self.lead_id, self.direction)

        if self.call_id:
            try:
                from backend.telephony.broadcaster import call_broadcaster
                await call_broadcaster.broadcast(str(self.call_id), {"type": "ready", "status": "connected"})
            except Exception:
                pass

        # Transports await start() before reading microphone frames. Own the
        # greeting as a responder so synthesis cannot block input or barge-in.
        if self.recorder is None and self.call_id:
            try:
                self.recorder = CallAudioRecorder(call_id=str(self.call_id))
            except Exception:
                pass
        if self.recorder:
            try:
                self.recorder.start()
            except Exception as e:
                log.warning("failed starting CallAudioRecorder: %s", e)
        self._in_greeting = True
        self.responder = asyncio.create_task(self._run_greeting())
        await self.t.notify({"type": "ready"})

    async def _run_greeting(self) -> None:
        greeting = await self._greeting_text()
        self.state["messages"].append({"role": "assistant", "content": greeting})
        log.info("call language=%s (%s)", self.language, self.language_name)
        self._in_greeting = True
        greeting_start = time.monotonic()
        try:
            greeting_duration = await self._say(greeting)
            elapsed = time.monotonic() - greeting_start
            remaining = max(0.0, greeting_duration - elapsed)
            self._greeting_end_time = time.monotonic() + remaining + 0.3
            if remaining > 0:
                await asyncio.sleep(remaining)
            await self._persist_turn("agent", greeting, GREETING_STAGE)
        except asyncio.CancelledError:
            log.info("greeting cancelled (barge-in)")
            if self.recorder:
                try:
                    self.recorder.handle_interrupt()
                except Exception:
                    pass
            await self._persist_turn("agent", greeting + " …(interrupted)", GREETING_STAGE)
            raise
        finally:
            self._in_greeting = False
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
        if self.recorder:
            try:
                self.recorder.handle_interrupt()
            except Exception:
                pass
        try:
            await self.t.clear()
        finally:
            await self._cancel_responder()

    async def feed_pcm16(self, pcm: bytes) -> None:
        """Feed a chunk of caller audio; drives VAD, barge-in, and responses."""
        if self._call_ending:
            return
        if self.recorder and pcm:
            try:
                self.recorder.record_caller_pcm(pcm, sample_rate=16000)
            except Exception:
                pass
        for event, payload in self.endpointer.process(pcm):
            if event == SPEECH_START:
                await self.handle_interrupt()
            elif event == UTTERANCE:
                log.info("VAD detected UTTERANCE: %d bytes (%.2f s)", len(payload) if payload else 0, (len(payload) / 32000.0) if payload else 0)
                if not self._call_ending and payload:
                    self._in_greeting = False
                    if self.recorder:
                        try:
                            self.recorder.handle_interrupt()
                        except Exception:
                            pass
                    await self._cancel_responder()
                    self.responder = asyncio.create_task(self._handle_utterance(payload))

    async def push_audio(self, pcm: bytes) -> None:
        """Compatibility alias for Plivo / WebSocket audio push."""
        await self.feed_pcm16(pcm)

    async def handle_barge_in(self) -> None:
        """Compatibility alias for Plivo clearAudio / barge-in."""
        await self.handle_interrupt()

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

    async def _evaluate_call_transcript(self, messages: list[dict]) -> dict:
        """Run post-call LLM evaluation to generate summary, outcome, and qualification."""
        if not messages or not getattr(self, "engine", None) or not getattr(self.engine, "llm", None):
            return {}

        lines = []
        for m in messages:
            role = "AGENT" if m.get("role") == "assistant" else "CALLER"
            content = (m.get("content") or "").strip()
            if content:
                lines.append(f"{role}: {content}")

        if not lines:
            return {}
        transcript = "\n".join(lines[-20:])

        schema_guide = ""
        if self.qualification_schema:
            lines_schema = []
            for s in self.qualification_schema:
                if isinstance(s, dict) and s.get("key"):
                    k = s["key"]
                    lbl = s.get("label") or k
                    req = "required" if s.get("required", True) else "optional"
                    lines_schema.append(f"  * \"{k}\": {lbl} ({req})")
            if lines_schema:
                schema_guide = (
                    "Target Campaign Qualification Schema:\n"
                    + "\n".join(lines_schema)
                    + "\n\n"
                )

        target_example_keys = (
            ", ".join(s["key"] for s in self.qualification_schema if isinstance(s, dict) and "key" in s)
            if self.qualification_schema
            else "monthly_bill, requirement, appointment_time, preference"
        )

        prompt = (
            "You are an expert sales analyst reviewing an AI phone call conversation in India.\n"
            "Analyze this call transcript and produce a valid JSON evaluation.\n\n"
            f"{schema_guide}"
            f"Transcript:\n{transcript}\n\n"
            "Return ONLY a single valid JSON object with:\n"
            "- \"summary\": A concise 2-3 sentence summary in the language of the call (or English) capturing caller intent, key details mentioned, and agreed next steps.\n"
            "- \"outcome\": One of [\"qualified\", \"appointment_set\", \"callback\", \"not_interested\", \"contacted\"].\n"
            "  * Use \"qualified\" or \"appointment_set\" if caller expressed interest, shared requirements, agreed to appointment/visit, or requested details.\n"
            "  * Use \"callback\" if caller asked to call back later.\n"
            "  * Use \"not_interested\" if caller refused or hung up.\n"
            "- \"score\": Integer from 0 to 100 representing lead quality (80-100 for appointment/highly interested, 50-70 for exploratory, 0-30 for cold/rejection).\n"
            f"- \"qualification\": A dictionary containing the target qualification keys ({target_example_keys}) with actual values stated by the caller. Only include keys with actual values.\n"
            "- \"disposition\": One of [\"qualified\", \"appointment_set\", \"callback\", \"not_interested\"].\n"
        )

        try:
            eval_data = await self.engine.llm.complete_json(
                "You are a sales evaluation AI that returns only valid JSON.",
                prompt,
            )
            return eval_data or {}
        except Exception as e:
            log.warning("call evaluation exception: %s", e)
            return {}

    async def finalize(self) -> None:
        await self._cancel_responder()
        saved_recording_url = None
        if self.recorder:
            try:
                saved_recording_url = self.recorder.save_wav()
            except Exception as e:
                log.warning("failed saving call audio recording: %s", e)
        if self.call_id is not None:
            avg_latency = int(mean(self.latencies)) if self.latencies else None
            try:
                db = repo.get_db()
                call_doc = None
                if db is not None:
                    call_doc = await db["calls"].find_one({"_id": str(self.call_id)})
                    if call_doc and not self.lead_id and call_doc.get("lead_id"):
                        self.lead_id = str(call_doc["lead_id"])

                score = 0
                if db is not None and call_doc:
                    org_id = call_doc.get("organization_id", "demo")
                    if not self.qualification_schema and call_doc.get("qualification_schema"):
                        self.qualification_schema = call_doc["qualification_schema"]
                    if not self.qualification_schema and call_doc.get("campaign_id"):
                        try:
                            camp_doc = await db["campaigns"].find_one({"_id": str(call_doc["campaign_id"])})
                            if camp_doc and camp_doc.get("qualification_schema"):
                                self.qualification_schema = camp_doc["qualification_schema"]
                        except Exception:
                            pass

                    from backend.agent.scoring import call_outcome, score_lead
                    slots = self.state.get("slots", {})
                    output_vars = self.state.get("output_variables", {})
                    flags = self.state.get("flags", {})
                    stage = self.state.get("stage", "")

                    lead_score = score_lead(
                        slots, flags, output_variables=output_vars, qualification_schema=self.qualification_schema
                    )
                    outcome = call_outcome(flags, stage, output_variables=output_vars)
                    summary = None

                    # Merge meaningful output variables into qualification
                    qualification = {k: v for k, v in slots.items() if v is not None}
                    for k, v in output_vars.items():
                        if v is not None and k != "disposition":
                            qualification[k] = v

                    # Run post-call evaluation on the transcript if turns took place
                    messages = self.state.get("messages", [])
                    user_turns = [m for m in messages if m.get("role") == "user"]
                    if user_turns:
                        try:
                            eval_res = await self._evaluate_call_transcript(messages)
                            if eval_res:
                                if eval_res.get("summary"):
                                    summary = eval_res["summary"]
                                if eval_res.get("outcome"):
                                    outcome = eval_res["outcome"]
                                if eval_res.get("score") is not None:
                                    lead_score = int(eval_res["score"])
                                if eval_res.get("qualification") and isinstance(eval_res["qualification"], dict):
                                    eval_qual = {k: v for k, v in eval_res["qualification"].items() if v is not None}
                                    if eval_qual:
                                        qualification = eval_qual
                        except Exception as eval_exc:
                            log.warning("post-call evaluation error: %s", eval_exc)

                    from backend.core.redis import get_redis
                    try:
                        r = get_redis()
                    except Exception:
                        r = None
                    from backend.services.call_service import CallService
                    call_svc = CallService(db, redis=r)
                    await call_svc.finalize_call(
                        call_id=str(self.call_id),
                        organization_id=org_id,
                        status="completed",
                        outcome=outcome,
                        avg_latency_ms=avg_latency,
                        turn_count=len(self.latencies),
                        score=lead_score,
                        qualification=qualification,
                        summary=summary,
                        recording_url=saved_recording_url,
                    )
                    if saved_recording_url:
                        await db["calls"].update_one(
                            {"_id": str(self.call_id)},
                            {"$set": {"recording_url": saved_recording_url}},
                        )
                    score = lead_score
                elif self.lead_id is not None:
                    # Legacy fallback only for demo calls without a db call document
                    score = await repo.finalize_call(
                        self.call_id, self.lead_id, self.state, avg_latency
                    )

                await self.store.delete(str(self.call_id))
                log.info("call %s finalized (score=%d outcome=%s)", self.call_id, score, outcome if 'outcome' in locals() else 'unknown')
            except Exception as exc:  # noqa: BLE001
                log.warning("failed to finalize call: %s", exc)
