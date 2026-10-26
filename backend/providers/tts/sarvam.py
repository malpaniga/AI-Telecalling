"""Sarvam Bulbul managed-cloud TTS adapter."""
import base64
import io
import wave
from typing import Any
import httpx
from backend.providers.base import TTSProvider

SUPPORTED_MODELS = {"bulbul:v2", "bulbul:v3", "bulbul:v4", "bulbul:v4-flash", "bulbul:v4-turbo"}

SARVAM_SPEAKER_ALIASES = {
    "chitra": "chaitra_hi_customer",
    "chaitra": "chaitra_hi_customer",
    "chitra_hi": "chaitra_hi_customer",
    "chitra_mr": "chaitra_hi_customer",
    "chaitra_kn": "chaitra_kn_conversation",
    "ishita": "ishita_mr_conversational",
    "kavya": "kavya_hi_conversational",
    "aditi": "aditi_en_stories",
    "pooja": "pooja_gu_conversational",
    "priya": "ishita_mr_conversational",
    "priya_mr_conversational": "ishita_mr_conversational",
    "demo_voice_marathi": "ishita_mr_conversational",
    "demo_voice_hindi": "kavya_hi_conversational",
    "demo_voice_english": "aditi_en_stories",
    "shweta_hi_conversational": "kavya_hi_conversational",
    "rohan_en_conversational": "aditi_en_stories",
}

DEFAULT_V4_SPEAKERS = {
    "mr-IN": "ishita_mr_conversational",
    "hi-IN": "kavya_hi_conversational",
    "en-IN": "aditi_en_stories",
    "gu-IN": "pooja_gu_conversational",
    "ta-IN": "vijay_ta_narration",
    "te-IN": "kavitha_te_conversation",
    "kn-IN": "chaitra_kn_conversation",
    "bn-IN": "arnab_bn_conversation",
    "pa-IN": "anand_pa_conversation",
}


class SarvamTTSProvider(TTSProvider):
    provider_name = "sarvam"

    def __init__(
        self,
        api_key: str,
        model: str = "bulbul:v4-flash",
        voice_id: str | None = None,
        language: str = "en-IN",
        sample_rate: int = 16000,
        timeout: float = 30.0,
        _client: httpx.AsyncClient | None = None,
    ):
        if not api_key:
            raise ValueError("SARVAM_API_KEY must be provided")
        if model not in SUPPORTED_MODELS:
            raise ValueError(f"Unsupported Sarvam TTS model: {model}")
        self.model = model
        self.voice_id = voice_id
        self.language = language
        self.sample_rate = sample_rate
        self._client = _client or httpx.AsyncClient(
            timeout=timeout,
            headers={"api-subscription-key": api_key.strip().strip("'\"")},
        )

    def get_capabilities(self):
        return {
            "provider": "sarvam",
            "streaming": True,
            "model": self.model,
            "sample_rate": self.sample_rate,
            "languages": [
                "bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN",
                "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN",
            ],
        }

    async def stream(self, text: str, **kwargs: Any):
        """Progressive low-latency streaming TTS using Sarvam /stream endpoint."""
        text = text.strip()
        if not text:
            return

        lang = kwargs.get("language") or self.language or "en-IN"
        target_model = kwargs.get("model") or self.model
        voice_id = kwargs.get("voice_id") or self.voice_id

        # Normalize speaker alias
        if voice_id and isinstance(voice_id, str):
            clean_vid = voice_id.strip().lower()
            voice_id = SARVAM_SPEAKER_ALIASES.get(clean_vid, voice_id)

        # Map compatible speaker based on model version
        if "v4" in target_model.lower():
            if not voice_id:
                voice_id = DEFAULT_V4_SPEAKERS.get(lang, "kavya_hi_conversational" if "hi" in lang else "aditi_en_stories")
        else:
            if not voice_id:
                voice_id = "kavya"

        body = {
            "text": text,
            "target_language_code": lang,
            "model": target_model,
            "speaker": voice_id,
            "speech_sample_rate": self.sample_rate,
            "output_audio_codec": "linear16",
        }

        carry = b""
        try:
            async with self._client.stream("POST", "https://api.sarvam.ai/text-to-speech/stream", json=body) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes():
                    if not chunk:
                        continue
                    data = carry + chunk
                    if len(data) % 2:
                        carry, data = data[-1:], data[:-1]
                    else:
                        carry = b""
                    if data:
                        yield {
                            "audio": data,
                            "sample_rate": self.sample_rate,
                        }
        except Exception:
            # Fall back to single-shot synthesis if stream endpoint is unavailable
            synth_res = await self.synthesize(text, **kwargs)
            yield synth_res

    async def synthesize(self, text: str, **kwargs: Any):
        if not text.strip():
            return {"audio": b"", "sample_rate": self.sample_rate}

        lang = kwargs.get("language") or self.language or "en-IN"
        target_model = kwargs.get("model") or self.model
        voice_id = kwargs.get("voice_id") or self.voice_id

        # Normalize speaker alias
        if voice_id and isinstance(voice_id, str):
            clean_vid = voice_id.strip().lower()
            voice_id = SARVAM_SPEAKER_ALIASES.get(clean_vid, voice_id)

        # Map compatible speaker based on model version
        if "v4" in target_model.lower():
            if not voice_id:
                voice_id = DEFAULT_V4_SPEAKERS.get(lang, "kavya_hi_conversational" if "hi" in lang else "aditi_en_stories")
        else:
            if not voice_id:
                voice_id = "kavya"

        body = {
            "text": text,
            "target_language_code": lang,
            "model": target_model,
            "speaker": voice_id,
            "speech_sample_rate": self.sample_rate,
        }

        response = await self._client.post("https://api.sarvam.ai/text-to-speech", json=body)
        response.raise_for_status()
        audio_b64 = (response.json().get("audios") or [None])[0]
        if not audio_b64:
            raise RuntimeError("Sarvam TTS returned no audio")

        with wave.open(io.BytesIO(base64.b64decode(audio_b64)), "rb") as wav:
            return {
                "audio": wav.readframes(wav.getnframes()),
                "sample_rate": wav.getframerate(),
            }

    async def get_models(self):
        return sorted(SUPPORTED_MODELS)
