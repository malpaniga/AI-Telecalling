"""Groq Whisper STT provider adapter."""
import io
import logging
from typing import Any
from groq import AsyncGroq
from backend.config import settings
from backend.providers.base import STTProvider

log = logging.getLogger("providers.stt.groq")

# Prompt priming hints to bias Whisper's tokenizer toward correct Devanagari vocabulary
INDIC_WHISPER_PROMPTS: dict[str, str] = {
    "mr": "हा एक मराठी संवाद आहे: बोला, नमस्कार, हो, नाही, वीज बिल, हजार, रुपये, सबसिडी, सोलर, कंपनी.",
    "hi": "यह एक हिंदी संवाद है: हाँ, नहीं, नमस्कार, बिजली बिल, हजार, रुपये, सबसिडी, सोलर, कंपनी.",
}


class GroqSTTProvider(STTProvider):
    provider_name = "groq-whisper"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "whisper-large-v3-turbo",
        language: str | None = None,
        timeout: float = 30.0,
        _client: Any | None = None,
    ):
        key = api_key or getattr(settings, "groq_api_key", None)
        if not key:
            raise ValueError("GROQ_API_KEY must be provided")

        self.model = model or "whisper-large-v3-turbo"
        self.language = language
        self.client = _client or AsyncGroq(api_key=key, timeout=timeout)

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "provider": "groq-whisper",
            "streaming": False,
            "model": self.model,
            "languages": ["en", "hi", "multilingual"],
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
        lang = (language or self.language or "en").split("-")[0]
        prompt = kwargs.get("prompt") or INDIC_WHISPER_PROMPTS.get(lang)
        create_kwargs: dict[str, Any] = {
            "file": (filename, io.BytesIO(audio)),
            "model": kwargs.get("model") or self.model,
            "language": lang if lang != "unknown" else None,
            "temperature": 0,
            "response_format": "text",
        }
        if prompt:
            create_kwargs["prompt"] = prompt

        try:
            resp = await self.client.audio.transcriptions.create(**create_kwargs)
            return str(resp).strip() if resp else ""
        except Exception as exc:
            log.warning("Groq STT failed: %s", exc)
            return ""
