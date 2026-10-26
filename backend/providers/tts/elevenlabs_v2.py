"""ElevenLabs TTS provider adapter — proper implementation.

Uses the official elevenlabs Python SDK (v2+).
Documentation: https://elevenlabs.io/docs/api-reference/text-to-speech

Supported output formats:
  pcm_16000 — 16-bit PCM at 16 kHz (compatible with telephony pipeline)
  pcm_22050 — 16-bit PCM at 22 kHz

The existing ElevenLabsTTSProvider in elevenlabs.py is a one-liner that uses
an undocumented kwarg interface. This adapter uses the official SDK and
returns audio as bytes + sample_rate in the existing TTSProvider contract.

Never logs api_key or voice_id from user data.
Credentials passed at construction from the credential store.
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from backend.providers.base import TTSProvider

log = logging.getLogger("providers.tts.elevenlabs")

# Default to a public voice to avoid None errors; admins set real voice IDs via config
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # ElevenLabs "George" — public

SUPPORTED_MODELS = {
    "eleven_v4", "eleven_v4_turbo", "eleven_v3",
    "eleven_multilingual_v2",
    "eleven_multilingual_v1", "eleven_monolingual_v1",
    "eleven_flash_v2_5", "eleven_flash_v2",
    "eleven_turbo_v2_5", "eleven_turbo_v2",
}

DEFAULT_MODEL = "eleven_multilingual_v2"


class ElevenLabsTTSProviderV2(TTSProvider):
    """ElevenLabs TTS adapter using the official elevenlabs SDK.

    api_key and voice_id come from the credential store / admin configuration —
    never from settings at import time.
    """

    provider_name = "elevenlabs"

    def __init__(
        self,
        api_key: str,
        voice_id: str = DEFAULT_VOICE_ID,
        model: str = DEFAULT_MODEL,
        output_format: str = "pcm_16000",
        timeout: float = 30.0,
        # Inject a pre-built client for testing
        _client: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY must be provided")
        self.voice_id = voice_id or DEFAULT_VOICE_ID
        self.model = model
        self.output_format = output_format
        self.timeout = timeout
        self.sample_rate = 16000 if "16000" in output_format else 22050

        if _client is not None:
            self._client = _client
        else:
            from elevenlabs import ElevenLabs as _ElevenLabs
            self._client = _ElevenLabs(api_key=api_key, timeout=timeout)

    def get_capabilities(self) -> dict:
        return {
            "streaming": True,
            "languages": ["multilingual"],
            "provider": "elevenlabs",
            "model": self.model,
            "sample_rate": self.sample_rate,
        }

    async def synthesize(self, text: str, **kwargs: Any) -> dict:
        """Synthesize text to PCM16 audio bytes.

        Returns {"audio": bytes, "sample_rate": int}.
        Raises RuntimeError on auth failure, quota exhaustion, or timeout.
        """
        import asyncio

        voice_id = kwargs.get("voice_id") or self.voice_id or DEFAULT_VOICE_ID
        model = kwargs.get("model", self.model)
        text = text.strip()
        if not text:
            return {"audio": b"", "sample_rate": self.sample_rate}

        try:
            # elevenlabs SDK is sync — run in thread to avoid blocking the event loop
            audio_bytes = await asyncio.to_thread(
                self._synthesize_sync, text, voice_id, model
            )
        except Exception as exc:
            raise RuntimeError(_sanitize_elevenlabs_error(exc)) from exc

        return {"audio": audio_bytes, "sample_rate": self.sample_rate}

    def _synthesize_sync(self, text: str, voice_id: str, model: str) -> bytes:
        """Synchronous synthesis — called in a thread pool."""
        audio_iter = self._client.text_to_speech.convert(
            voice_id=voice_id or DEFAULT_VOICE_ID,
            text=text,
            model_id=model,
            output_format=self.output_format,
        )
        # SDK returns a generator of bytes chunks
        chunks = list(audio_iter)
        return b"".join(c for c in chunks if c)

    async def stream(
        self, text: str, **kwargs: Any
    ) -> AsyncIterator[dict]:
        """Stream audio chunks from ElevenLabs.

        Yields {"audio": bytes_chunk, "sample_rate": int} per chunk.
        """
        import asyncio

        voice_id = kwargs.get("voice_id") or self.voice_id or DEFAULT_VOICE_ID
        model = kwargs.get("model", self.model)
        text = text.strip()
        if not text:
            return

        try:
            audio_stream = await asyncio.to_thread(
                self._stream_sync_collect, text, voice_id, model
            )
            for chunk in audio_stream:
                if chunk:
                    yield {"audio": chunk, "sample_rate": self.sample_rate}
        except Exception as exc:
            raise RuntimeError(_sanitize_elevenlabs_error(exc)) from exc

    def _stream_sync_collect(
        self, text: str, voice_id: str, model: str
    ) -> list[bytes]:
        """Collect streaming chunks synchronously (run in thread)."""
        chunks = []
        for chunk in self._client.text_to_speech.convert(
            voice_id=voice_id or DEFAULT_VOICE_ID,
            text=text,
            model_id=model,
            output_format=self.output_format,
        ):
            if chunk:
                chunks.append(chunk)
        return chunks

    async def get_voices(self) -> list[dict]:
        """Return list of available voice dicts from the API."""
        import asyncio
        try:
            voices = await asyncio.to_thread(self._get_voices_sync)
            return voices
        except Exception as exc:
            log.warning("ElevenLabs get_voices failed: %s", type(exc).__name__)
            return []

    def _get_voices_sync(self) -> list[dict]:
        resp = self._client.voices.get_all()
        return [
            {"voice_id": v.voice_id, "name": v.name, "category": getattr(v, "category", "")}
            for v in (resp.voices or [])
        ]

    async def get_models(self) -> list[str]:
        return sorted(SUPPORTED_MODELS)


def _sanitize_elevenlabs_error(exc: Exception) -> str:
    """Return a sanitized error message — never includes the API key."""
    msg = str(exc)
    if "401" in msg or "unauthorized" in msg.lower():
        return "ElevenLabs authentication failed — check ELEVENLABS_API_KEY"
    if "429" in msg or "quota" in msg.lower():
        return "ElevenLabs quota exceeded or rate limit hit"
    if "404" in msg or "voice" in msg.lower() and "not found" in msg.lower():
        return "ElevenLabs voice ID not found"
    return f"ElevenLabs TTS failed ({type(exc).__name__})"
