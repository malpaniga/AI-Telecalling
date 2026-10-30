"""Sarvam AI LLM provider adapter.

Connects to Sarvam's official OpenAI-compatible chat completions API:
https://api.sarvam.ai/v1/chat/completions

Supported models:
  sarvam-105b-conversations  — flagship 105B MoE conversational dialogue model
  sarvam-105b                — base flagship reasoning model

Never logs credentials. api_key passed at construction from credential store.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from backend.providers.base import LLMProvider

log = logging.getLogger("providers.llm.sarvam")

DEFAULT_MODEL = "sarvam-105b-conversations"
SARVAM_API_URL = "https://api.sarvam.ai/v1/chat/completions"

SUPPORTED_MODELS = {
    "sarvam-105b-conversations",
    "sarvam-105b",
}


def _clean_key(key: str | None) -> str:
    """Normalize and strip quotes or redundant Bearer prefix from API key."""
    if not key:
        return ""
    cleaned = key.strip().strip("'\"")
    if cleaned.startswith("Bearer "):
        cleaned = cleaned[7:].strip()
    return cleaned


def _sanitize_sarvam_error(exc: Exception, model: str) -> str:
    """Return a sanitized error message — never includes the API key."""
    msg = str(exc)
    if "401" in msg or "unauthorized" in msg.lower() or "authentication" in msg.lower() or "invalid_api_key" in msg.lower():
        return f"Sarvam authentication failed for model '{model}' — check SARVAM_API_KEY"
    if "429" in msg or "rate_limit" in msg.lower() or "too many requests" in msg.lower():
        return f"Sarvam rate limit exceeded for model '{model}'"
    if "503" in msg or "overloaded" in msg.lower() or "unavailable" in msg.lower():
        return f"Sarvam service unavailable for model '{model}'"
    if "404" in msg or "model_not_found" in msg.lower():
        return f"Sarvam model '{model}' not found"
    return f"Sarvam request failed ({type(exc).__name__}) for model '{model}'"


class SarvamLLMProvider(LLMProvider):
    """Sarvam AI chat-completion adapter.

    api_key is required and must come from the credential store —
    never read from settings here to prevent inadvertent key exposure.
    """

    provider_name = "sarvam"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
        max_tokens: int = 512,
        temperature: float = 0.6,
        _client: httpx.AsyncClient | None = None,
    ) -> None:
        cleaned_key = _clean_key(api_key)
        if not cleaned_key:
            raise ValueError("SARVAM_API_KEY must be provided")

        self.api_key = cleaned_key
        self.model = model or DEFAULT_MODEL
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._headers = {
            "api-subscription-key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        self._client = _client or httpx.AsyncClient(timeout=timeout)

    def get_capabilities(self) -> dict:
        return {
            "streaming": True,
            "languages": [
                "hi",
                "ta",
                "te",
                "kn",
                "mr",
                "bn",
                "gu",
                "ml",
                "pa",
                "en-IN",
                "multilingual",
            ],
            "provider": "sarvam",
            "model": self.model,
        }

    def _build_payload(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        final_msgs: list[dict] = []
        if system_prompt:
            final_msgs.append({"role": "system", "content": system_prompt})
        final_msgs.extend(messages)

        return {
            "model": model,
            "messages": final_msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

    async def generate(self, messages: list[dict], **kwargs: Any) -> str:
        """Non-streaming chat completion."""
        model = kwargs.get("model", self.model)
        temp = kwargs.get("temperature", self.temperature)
        max_tok = kwargs.get("max_tokens", self.max_tokens)
        system_prompt: str | None = kwargs.get("system_prompt")

        payload = self._build_payload(
            messages=messages,
            model=model,
            temperature=temp,
            max_tokens=max_tok,
            stream=False,
            system_prompt=system_prompt,
        )

        try:
            resp = await self._client.post(
                SARVAM_API_URL,
                json=payload,
                headers=self._headers,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            sanitized = _sanitize_sarvam_error(exc, model)
            raise RuntimeError(sanitized) from exc

        choices = data.get("choices", [])
        if not choices:
            raise ValueError(f"Sarvam returned empty response for model '{model}'")

        content = (choices[0].get("message", {}).get("content") or "").strip()
        if not content:
            raise ValueError(f"Sarvam returned empty content for model '{model}'")

        return content

    async def stream(
        self, messages: list[dict], **kwargs: Any
    ) -> AsyncIterator[str]:
        """Streaming chat completion — yields text deltas."""
        model = kwargs.get("model", self.model)
        temp = kwargs.get("temperature", self.temperature)
        max_tok = kwargs.get("max_tokens", self.max_tokens)
        system_prompt: str | None = kwargs.get("system_prompt")

        payload = self._build_payload(
            messages=messages,
            model=model,
            temperature=temp,
            max_tokens=max_tok,
            stream=True,
            system_prompt=system_prompt,
        )

        try:
            async with self._client.stream(
                "POST",
                SARVAM_API_URL,
                json=payload,
                headers=self._headers,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    line_str = line.strip()
                    if line_str.startswith(":"):
                        # SSE comment/keep-alive line
                        continue
                    if line_str.startswith("data: "):
                        raw_data = line_str[6:].strip()
                        if raw_data == "[DONE]":
                            break
                        try:
                            chunk_obj = json.loads(raw_data)
                            choices = chunk_obj.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {}).get("content", "")
                                if delta:
                                    yield delta
                        except Exception:
                            # Skip malformed SSE chunk lines gracefully
                            continue
        except Exception as exc:
            sanitized = _sanitize_sarvam_error(exc, model)
            raise RuntimeError(sanitized) from exc

    async def get_models(self) -> list[str]:
        return sorted(SUPPORTED_MODELS)
