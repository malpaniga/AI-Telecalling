"""Sarvam Bulbul managed-cloud TTS adapter."""
import base64
import io
import wave
from typing import Any
import httpx
from backend.providers.base import TTSProvider

SUPPORTED_MODELS = {"bulbul:v2", "bulbul:v3", "bulbul:v4-flash"}

class SarvamTTSProvider(TTSProvider):
    provider_name = "sarvam"
    def __init__(self, api_key: str, model: str = "bulbul:v4-flash", voice_id: str | None = None,
                 language: str = "en-IN", sample_rate: int = 16000, timeout: float = 30.0,
                 _client: httpx.AsyncClient | None = None):
        if not api_key: raise ValueError("SARVAM_API_KEY must be provided")
        if model not in SUPPORTED_MODELS: raise ValueError(f"Unsupported Sarvam TTS model: {model}")
        self.model, self.voice_id, self.language, self.sample_rate = model, voice_id, language, sample_rate
        self._client = _client or httpx.AsyncClient(timeout=timeout, headers={"api-subscription-key": api_key})
    def get_capabilities(self):
        return {"provider": "sarvam", "streaming": False, "model": self.model, "sample_rate": self.sample_rate,
                "languages": ["bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN", "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN"]}
    async def synthesize(self, text: str, **kwargs: Any):
        if not text.strip(): return {"audio": b"", "sample_rate": self.sample_rate}
        body = {"text": text, "language_code": kwargs.get("language") or self.language,
                "model": kwargs.get("model") or self.model, "speech_sample_rate": self.sample_rate}
        voice_id = kwargs.get("voice_id") or self.voice_id
        if voice_id: body["speaker"] = voice_id
        response = await self._client.post("https://api.sarvam.ai/text-to-speech", json=body)
        response.raise_for_status()
        audio_b64 = (response.json().get("audios") or [None])[0]
        if not audio_b64: raise RuntimeError("Sarvam TTS returned no audio")
        with wave.open(io.BytesIO(base64.b64decode(audio_b64)), "rb") as wav:
            return {"audio": wav.readframes(wav.getnframes()), "sample_rate": wav.getframerate()}
    async def get_models(self): return sorted(SUPPORTED_MODELS)
