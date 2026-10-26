"""Sarvam Saaras STT provider adapter."""
import logging
from typing import Any
import httpx
from backend.config import settings
from backend.providers.base import STTProvider

log = logging.getLogger("providers.stt.sarvam")

SUPPORTED_MODELS = {"saaras:v2", "saaras:v3", "saaras:v4", "saaras:v4-turbo"}


class SarvamSTTProvider(STTProvider):
    provider_name = "sarvam"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "saaras:v4",
        language: str = "en-IN",
        mode: str = "codemix",
        timeout: float = 30.0,
        _client: httpx.AsyncClient | None = None,
    ):
        key = api_key or getattr(settings, "sarvam_tts_api_key", None)
        if not key:
            raise ValueError("SARVAM_API_KEY must be provided")

        clean_key = key.strip().strip("'\"")
        if clean_key.startswith("Bearer "):
            clean_key = clean_key[7:].strip()

        target_model = model or "saaras:v4"
        if "v4" in target_model.lower():
            target_model = "saaras:v4"
        elif "v3" in target_model.lower():
            target_model = "saaras:v3"
        elif "v2" in target_model.lower():
            target_model = "saaras:v2"

        self.model = target_model
        self.language = language
        self.mode = mode
        self.timeout = timeout
        self._client = _client or httpx.AsyncClient(
            timeout=timeout,
            headers={"api-subscription-key": clean_key},
        )

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "provider": "sarvam",
            "streaming": False,
            "model": self.model,
            "languages": [
                "bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN", "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN"
            ],
        }

    async def transcribe(
        self,
        audio: bytes,
        filename: str = "audio.wav",
        language: str | None = None,
        **kwargs: Any,
    ) -> str:
        if not audio:
            return ""
        try:
            resp = await self._client.post(
                "https://api.sarvam.ai/speech-to-text",
                files={"file": (filename, audio, "audio/wav")},
                data={
                    "model": kwargs.get("model") or self.model,
                    "mode": kwargs.get("mode") or self.mode,
                    "language_code": language or self.language or "unknown",
                },
            )
            resp.raise_for_status()
            return (resp.json().get("transcript") or "").strip()
        except Exception as exc:
            log.warning("Sarvam STT failed: %s", exc)
            return ""

    async def get_models(self) -> list[str]:
        return sorted(SUPPORTED_MODELS)
