"""Soniox Speech-to-Text provider adapter.

Connects to Soniox's official REST API:
https://api.soniox.com/v1/
using an API key via Bearer token Authorization header.

Supports multilingual transcription with high accuracy across Indian languages and English.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from backend.providers.base import STTProvider

log = logging.getLogger("providers.stt.soniox")

SONIOX_API_BASE = "https://api.soniox.com/v1"

DEFAULT_MODEL = "stt-async-v5"

SUPPORTED_MODELS = {
    "stt-async-v5",
    "stt-rt-v5",
}

SUPPORTED_LANGUAGES = [
    "hi-IN",
    "mr-IN",
    "en-IN",
    "ta-IN",
    "te-IN",
    "kn-IN",
    "gu-IN",
    "bn-IN",
    "pa-IN",
    "ml-IN",
    "multilingual",
]


def _clean_key(key: str | None) -> str:
    """Normalize and strip quotes or redundant Bearer prefix from API key."""
    if not key:
        return ""
    cleaned = key.strip()
    if cleaned.lower().startswith("bearer "):
        cleaned = cleaned[7:].strip()
    return cleaned.strip("'\"").strip()


def _sanitize_soniox_error(exc: Exception, model: str) -> str:
    """Return a sanitized error message — never includes the API key."""
    msg = str(exc)
    if "401" in msg or "403" in msg or "unauthorized" in msg.lower() or "forbidden" in msg.lower():
        return f"Soniox authentication failed for model '{model}' — check SONIOX_API_KEY"
    if "429" in msg or "rate_limit" in msg.lower() or "quota" in msg.lower():
        return f"Soniox rate limit or quota exceeded for model '{model}'"
    if "503" in msg or "unavailable" in msg.lower():
        return f"Soniox service unavailable for model '{model}'"
    return f"Soniox request failed ({type(exc).__name__}) for model '{model}'"


class SonioxSTTProvider(STTProvider):
    """Soniox Speech-to-Text adapter."""

    provider_name = "soniox"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        language: str = "en-IN",
        timeout: float = 30.0,
        _client: httpx.AsyncClient | None = None,
        **kwargs: Any,
    ) -> None:
        cleaned_key = _clean_key(api_key)
        if not cleaned_key:
            raise ValueError("SONIOX_API_KEY must be provided")

        self.api_key = cleaned_key
        self.model = model or DEFAULT_MODEL
        self.language = language or "en-IN"
        self.timeout = timeout
        self.extra_options = kwargs
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        self._client = _client or httpx.AsyncClient(timeout=timeout)

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "provider": "soniox",
            "streaming": True,
            "model": self.model,
            "language": self.language,
            "languages": SUPPORTED_LANGUAGES,
        }

    async def transcribe(
        self,
        audio: bytes,
        filename: str = "audio.wav",
        language: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Transcribe audio bytes to text via Soniox REST API."""
        if not audio or len(audio) < 10:
            return ""

        target_model = kwargs.get("model") or self.model
        file_id: str | None = None

        try:
            # 1. Upload audio file
            upload_resp = await self._client.post(
                f"{SONIOX_API_BASE}/files",
                headers=self._headers,
                files={"file": (filename, audio, "audio/wav")},
            )
            upload_resp.raise_for_status()
            upload_data = upload_resp.json()
            file_id = upload_data.get("id")
            if not file_id:
                raise RuntimeError("Soniox file upload did not return a file_id")

            # 2. Create transcription request
            trans_payload: dict[str, Any] = {
                "model": target_model,
                "file_id": file_id,
            }
            if language or self.language:
                lang_code = (language or self.language).split("-")[0].lower()
                trans_payload["language_hints"] = [lang_code]

            trans_resp = await self._client.post(
                f"{SONIOX_API_BASE}/transcriptions",
                headers={**self._headers, "Content-Type": "application/json"},
                json=trans_payload,
            )
            trans_resp.raise_for_status()
            trans_data = trans_resp.json()
            trans_id = trans_data.get("id")
            status = trans_data.get("status")

            if not trans_id:
                raise RuntimeError("Soniox transcription request did not return an id")

            # 3. Wait for completion if queued/processing
            max_attempts = max(1, int(self.timeout / 0.5))
            attempts = 0
            while status not in ("completed", "done") and attempts < max_attempts:
                if status in ("failed", "error"):
                    error_msg = trans_data.get("error") or "Unknown transcription failure"
                    raise RuntimeError(f"Soniox transcription failed: {error_msg}")
                await asyncio.sleep(0.5)
                attempts += 1
                status_resp = await self._client.get(
                    f"{SONIOX_API_BASE}/transcriptions/{trans_id}",
                    headers=self._headers,
                )
                status_resp.raise_for_status()
                trans_data = status_resp.json()
                status = trans_data.get("status")

            if status not in ("completed", "done"):
                raise TimeoutError(f"Soniox transcription timed out after {self.timeout}s (status: {status})")

            # 4. Fetch transcript text
            transcript_resp = await self._client.get(
                f"{SONIOX_API_BASE}/transcriptions/{trans_id}/transcript",
                headers=self._headers,
            )
            transcript_resp.raise_for_status()
            transcript_data = transcript_resp.json()
            transcript_text = (transcript_data.get("text") or "").strip()

            return transcript_text
        except Exception as exc:
            sanitized = _sanitize_soniox_error(exc, target_model)
            raise RuntimeError(sanitized) from None
        finally:
            # 5. Clean up uploaded file
            if file_id:
                try:
                    await self._client.delete(
                        f"{SONIOX_API_BASE}/files/{file_id}",
                        headers=self._headers,
                    )
                except Exception:
                    pass

    async def get_models(self) -> list[str]:
        return sorted(SUPPORTED_MODELS)
