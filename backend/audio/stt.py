"""Speech-to-text via Groq Whisper.

Sprint 1 does non-streaming transcription: the browser records an utterance and
sends the whole clip; we transcribe it in one call. Streaming/partial STT comes
in Sprint 4 when we add VAD and endpointing.
"""

import io
import logging
import time

from groq import AsyncGroq

from backend.config import settings

log = logging.getLogger("stt")


def _segment_confidence(resp) -> tuple[float, float]:
    """Return (max no_speech_prob, min avg_logprob) across segments.

    Handles both attribute- and dict-style segments. Defaults are 'confident'
    (0.0, 0.0) so a missing field never causes a false drop.
    """
    segments = getattr(resp, "segments", None) or []
    if not segments:
        return 0.0, 0.0

    def field(seg, name, default):
        if isinstance(seg, dict):
            val = seg.get(name, default)
        else:
            val = getattr(seg, name, default)
        return default if val is None else val

    no_speech = max(field(s, "no_speech_prob", 0.0) for s in segments)
    avg_logprob = min(field(s, "avg_logprob", 0.0) for s in segments)
    return no_speech, avg_logprob


class STTClient:
    def __init__(self, model: str | None = None):
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.model = model or settings.groq_stt_model

    async def transcribe(
        self, audio_bytes: bytes, filename: str = "audio.wav", language: str | None = None
    ) -> str:
        # Groq/Whisper wants ISO-639-1 ("hi"), callers pass BCP-47 ("hi-IN").
        if language:
            language = language.split("-")[0]
        """Transcribe a complete audio clip (wav/webm/mp3) to text.

        `language` is an ISO-639-1 code (e.g. "en", "hi", "ta"). Passing the right
        language sharply reduces Whisper's tendency to hallucinate filler.

        We request verbose_json and drop the result when Whisper's own confidence
        signals say it's probably not speech — `no_speech_prob` high or `avg_logprob`
        very low. This is language-agnostic, so it catches silence/echo
        hallucinations in ANY language (English "Thank you.", Hindi "झाल", etc.)
        without maintaining per-language denylists.
        """
        started = time.perf_counter()
        resp = await self.client.audio.transcriptions.create(
            file=(filename, io.BytesIO(audio_bytes)),
            model=self.model,
            language=language,
            temperature=0,
            response_format="verbose_json",
        )
        text = (resp.text or "").strip()
        no_speech, avg_logprob = _segment_confidence(resp)
        elapsed = (time.perf_counter() - started) * 1000

        if text and (
            no_speech > settings.stt_no_speech_threshold
            or avg_logprob < settings.stt_min_avg_logprob
        ):
            log.info(
                "stt dropped low-confidence %r (no_speech=%.2f avg_logprob=%.2f, %.0f ms)",
                text, no_speech, avg_logprob, elapsed,
            )
            return ""

        log.info("stt %d bytes -> %r (%.0f ms)", len(audio_bytes), text, elapsed)
        return text


class SarvamSTT:
    """Sarvam Saaras v3 speech-to-text — Indic-tuned, code-mixing aware.

    `mode=codemix` returns Hinglish naturally (English words in English, Hindi in
    Devanagari), which is far better than Whisper for real Indian phone calls and
    keeps English keywords intact for downstream extraction.
    """

    _URL = "https://api.sarvam.ai/speech-to-text"

    def __init__(self):
        import httpx

        if not settings.sarvam_tts_api_key:
            raise RuntimeError("SARVAM_TTS_API_KEY is not set")
        self.model = settings.sarvam_stt_model
        self.mode = settings.sarvam_stt_mode
        self._client = httpx.AsyncClient(
            timeout=20.0, headers={"api-subscription-key": settings.sarvam_tts_api_key}
        )

    async def transcribe(
        self, audio_bytes: bytes, filename: str = "audio.wav", language: str | None = None
    ) -> str:
        started = time.perf_counter()
        try:
            resp = await self._client.post(
                self._URL,
                files={"file": (filename, audio_bytes, "audio/wav")},
                data={
                    "model": self.model,
                    "mode": self.mode,
                    "language_code": language or "unknown",
                },
            )
            resp.raise_for_status()
            text = (resp.json().get("transcript") or "").strip()
        except Exception as exc:  # noqa: BLE001
            log.warning("sarvam STT failed: %s", exc)
            return ""
        log.info("stt(sarvam) %d bytes -> %r (%.0f ms)", len(audio_bytes), text,
                 (time.perf_counter() - started) * 1000)
        return text


class STTRouter:
    """Routes each utterance to the best STT: Sarvam Saaras for Indian languages
    (code-mixing), Groq Whisper for English (fast). Falls back to Groq if Sarvam
    is unavailable."""

    def __init__(self, groq: STTClient, sarvam: "SarvamSTT | None"):
        self.groq = groq
        self.sarvam = sarvam

    async def transcribe(
        self, audio_bytes: bytes, filename: str = "audio.wav", language: str | None = None
    ) -> str:
        if self.sarvam is not None and language and language != "en-IN":
            return await self.sarvam.transcribe(audio_bytes, filename, language)
        return await self.groq.transcribe(audio_bytes, filename, language)


async def _smoke_test(path: str) -> None:
    logging.basicConfig(level="INFO")
    with open(path, "rb") as f:
        data = f.read()
    client = STTClient()
    text = await client.transcribe(data, filename=path.split("/")[-1])
    print("TRANSCRIPT:", text)


if __name__ == "__main__":
    import asyncio
    import sys

    if len(sys.argv) < 2:
        print("usage: python -m backend.audio.stt <audio-file>")
        raise SystemExit(1)
    asyncio.run(_smoke_test(sys.argv[1]))
