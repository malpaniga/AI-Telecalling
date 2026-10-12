"""Groq LLM provider adapter.

Uses the official groq Python SDK (OpenAI-compatible API).
Documentation: https://console.groq.com/docs/openai

Supported models (verified 2025-Q3):
  llama-3.3-70b-versatile  — high quality, free tier (30 RPM / 14400 RPD)
  llama-3.1-8b-instant      — fast, free tier (30 RPM / 14400 RPD)
  mixtral-8x7b-32768        — large context

Never logs credentials. api_key passed at construction from credential store.
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from backend.providers.base import LLMProvider

log = logging.getLogger("providers.llm.groq")

DEFAULT_MODEL = "llama-3.3-70b-versatile"

SUPPORTED_MODELS = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-8b-8192",
    "llama3-70b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    # Whisper models are STT-only, not listed here
}


class GroqLLMProvider(LLMProvider):
    """Groq chat-completion adapter.

    api_key is required and must come from the credential store —
    never read from settings here to prevent inadvertent key exposure.
    """

    provider_name = "groq"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
        max_tokens: int = 512,
        temperature: float = 0.6,
        # Inject pre-built AsyncGroq client for testing
        _client: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("GROQ_API_KEY must be provided")
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature

        if _client is not None:
            self._client = _client
        else:
            from groq import AsyncGroq
            self._client = AsyncGroq(api_key=api_key)
        # Do not log api_key

    def get_capabilities(self) -> dict:
        return {
            "streaming": True,
            "languages": ["multilingual"],
            "provider": "groq",
            "model": self.model,
        }

    async def generate(self, messages: list[dict], **kwargs: Any) -> str:
        """Non-streaming chat completion.

        Raises RuntimeError on auth failure, rate limit, model unavailable.
        Never puts the api_key in the exception.
        """
        model = kwargs.get("model", self.model)
        temp = kwargs.get("temperature", self.temperature)
        max_tok = kwargs.get("max_tokens", self.max_tokens)
        system_prompt: str | None = kwargs.get("system_prompt")

        # Build final message list
        final_msgs: list[dict] = []
        if system_prompt:
            final_msgs.append({"role": "system", "content": system_prompt})
        final_msgs.extend(messages)

        try:
            resp = await self._client.chat.completions.create(
                model=model,
                messages=final_msgs,
                temperature=temp,
                max_tokens=max_tok,
                stream=False,
            )
        except Exception as exc:
            sanitized = _sanitize_groq_error(exc, model)
            raise RuntimeError(sanitized) from exc

        content = (resp.choices[0].message.content or "").strip()
        if not content:
            raise ValueError(f"Groq returned empty response for model '{model}'")
        return content

    async def stream(
        self, messages: list[dict], **kwargs: Any
    ) -> AsyncIterator[str]:
        """Streaming chat completion — yields text deltas."""
        model = kwargs.get("model", self.model)
        temp = kwargs.get("temperature", self.temperature)
        max_tok = kwargs.get("max_tokens", self.max_tokens)
        system_prompt: str | None = kwargs.get("system_prompt")

        final_msgs: list[dict] = []
        if system_prompt:
            final_msgs.append({"role": "system", "content": system_prompt})
        final_msgs.extend(messages)

        try:
            stream_resp = await self._client.chat.completions.create(
                model=model,
                messages=final_msgs,
                temperature=temp,
                max_tokens=max_tok,
                stream=True,
            )
            async for chunk in stream_resp:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield delta
        except Exception as exc:
            sanitized = _sanitize_groq_error(exc, model)
            raise RuntimeError(sanitized) from exc

    async def get_models(self) -> list[str]:
        return sorted(SUPPORTED_MODELS)


def _sanitize_groq_error(exc: Exception, model: str) -> str:
    """Return a sanitized error message — never includes the API key."""
    msg = str(exc)
    if "401" in msg or "invalid_api_key" in msg.lower() or "authentication" in msg.lower():
        return f"Groq authentication failed for model '{model}' — check GROQ_API_KEY"
    if "429" in msg or "rate_limit" in msg.lower():
        return f"Groq rate limit exceeded for model '{model}'"
    if "503" in msg or "overloaded" in msg.lower():
        return f"Groq service unavailable for model '{model}'"
    if "404" in msg or "model_not_found" in msg.lower():
        return f"Groq model '{model}' not found"
    return f"Groq request failed ({type(exc).__name__}) for model '{model}'"
