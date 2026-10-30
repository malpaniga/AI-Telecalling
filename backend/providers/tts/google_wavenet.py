"""Google Cloud WaveNet Text-to-Speech provider adapter.

Connects to Google Cloud Text-to-Speech REST API:
https://texttospeech.googleapis.com/v1/text:synthesize
using an API key via X-Goog-Api-Key header.

Provides low-latency synthesis with WaveNet voices across Indian languages & English.
Returns raw 16kHz PCM audio bytes compatible with the telephony call pipeline.
"""

from __future__ import annotations

import base64
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from backend.providers.base import TTSProvider

log = logging.getLogger("providers.tts.google_wavenet")

GOOGLE_TTS_API_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"

DEFAULT_MODEL = "wavenet"

SUPPORTED_MODELS = {
    "wavenet",
    "neural2",
    "standard",
}

DEFAULT_VOICES = {
    "hi-IN": "hi-IN-Wavenet-A",
    "mr-IN": "mr-IN-Wavenet-A",
    "en-IN": "en-IN-Wavenet-A",
    "en-US": "en-US-Wavenet-D",
    "ta-IN": "ta-IN-Wavenet-A",
    "te-IN": "te-IN-Standard-A",
    "kn-IN": "kn-IN-Wavenet-A",
    "ml-IN": "ml-IN-Wavenet-A",
    "bn-IN": "bn-IN-Wavenet-A",
    "gu-IN": "gu-IN-Wavenet-A",
    "pa-IN": "pa-IN-Wavenet-A",
}


def _clean_key(key: str | None) -> str:
    """Normalize and strip quotes or redundant Bearer prefix from API key."""
    if not key:
        return ""
    cleaned = key.strip()
    if cleaned.lower().startswith("bearer "):
        cleaned = cleaned[7:].strip()
    return cleaned.strip("'\"").strip()


def _sanitize_google_tts_error(exc: Exception, voice: str) -> str:
    """Return a sanitized error message — never includes the API key."""
    msg = str(exc)
    if "401" in msg or "403" in msg or "unauthorized" in msg.lower() or "forbidden" in msg.lower() or "api_key" in msg.lower():
        return f"Google WaveNet authentication failed for voice '{voice}' — check GOOGLE_API_KEY"
    if "429" in msg or "rate_limit" in msg.lower() or "quota" in msg.lower():
        return f"Google WaveNet rate limit or quota exceeded for voice '{voice}'"
    if "503" in msg or "unavailable" in msg.lower():
        return f"Google WaveNet service unavailable for voice '{voice}'"
    return f"Google WaveNet request failed ({type(exc).__name__}) for voice '{voice}'"


class GoogleWaveNetTTSProvider(TTSProvider):
    """Google Cloud WaveNet TTS adapter using direct REST API authentication."""

    provider_name = "google-wavenet"

    def __init__(
        self,
        api_key: str,
        voice_id: str | None = None,
        language: str = "hi-IN",
        model: str = DEFAULT_MODEL,
        sample_rate: int = 16000,
        timeout: float = 30.0,
        _client: httpx.AsyncClient | None = None,
        **kwargs: Any,
    ) -> None:
        cleaned_key = _clean_key(api_key)
        if not cleaned_key:
            raise ValueError("GOOGLE_API_KEY must be provided")

        self.api_key = cleaned_key
        self.language = language or "hi-IN"
        self.voice_id = voice_id or DEFAULT_VOICES.get(self.language, "hi-IN-Wavenet-A")
        self.model = model or DEFAULT_MODEL
        self.sample_rate = sample_rate
        self.timeout = timeout
        self.extra_options = kwargs
        self._headers = {
            "X-Goog-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        self._client = _client or httpx.AsyncClient(timeout=timeout)

    def get_capabilities(self) -> dict:
        return {
            "streaming": True,
            "provider": "google-wavenet",
            "model": self.model,
            "voice": self.voice_id,
            "sample_rate": self.sample_rate,
            "languages": list(DEFAULT_VOICES.keys()),
        }

    def _resolve_voice_and_lang(self, kwargs: dict[str, Any]) -> tuple[str, str]:
        voice = kwargs.get("voice_id") or self.voice_id or DEFAULT_VOICES.get(self.language, "hi-IN-Wavenet-A")
        lang = kwargs.get("language") or self.language or "hi-IN"

        # If voice name has BCP-47 prefix (e.g. "hi-IN-Wavenet-A"), synchronize language
        parts = voice.split("-")
        if len(parts) >= 3:
            inferred_lang = f"{parts[0]}-{parts[1]}"
            if not kwargs.get("language"):
                lang = inferred_lang
        return voice, lang

    async def synthesize(self, text: str, **kwargs: Any) -> dict:
        """Synthesize text into raw PCM16 audio frames."""
        clean_text = text.strip() if text else ""
        if not clean_text:
            return {"audio": b"", "sample_rate": self.sample_rate}

        voice_name, language_code = self._resolve_voice_and_lang(kwargs)

        payload = {
            "input": {"text": clean_text},
            "voice": {
                "languageCode": language_code,
                "name": voice_name,
            },
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "sampleRateHertz": self.sample_rate,
            },
        }

        try:
            resp = await self._client.post(
                GOOGLE_TTS_API_URL,
                json=payload,
                headers=self._headers,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            sanitized = _sanitize_google_tts_error(exc, voice_name)
            raise RuntimeError(sanitized) from None

        audio_b64 = data.get("audioContent")
        if not audio_b64:
            raise ValueError(f"Google WaveNet returned no audioContent for voice '{voice_name}'")

        try:
            raw_audio = base64.b64decode(audio_b64)
        except Exception as exc:
            raise ValueError(f"Invalid base64 audio returned by Google WaveNet: {exc}") from None

        # Google Cloud LINEAR16 includes a standard 44-byte WAV header (RIFF...)
        if raw_audio.startswith(b"RIFF") and len(raw_audio) > 44:
            pcm_audio = raw_audio[44:]
        else:
            pcm_audio = raw_audio

        return {"audio": pcm_audio, "sample_rate": self.sample_rate}

    async def stream(self, text: str, **kwargs: Any) -> AsyncIterator[dict]:
        """Stream synthesized audio chunk."""
        result = await self.synthesize(text, **kwargs)
        if result.get("audio"):
            yield result

    async def get_models(self) -> list[str]:
        return sorted(SUPPORTED_MODELS)

    async def get_voices(self) -> list[dict]:
        return [
            {"voice_id": vid, "language": lang, "provider": "google-wavenet"}
            for lang, vid in DEFAULT_VOICES.items()
        ]
