"""Gemini LLM provider adapter using the official google-genai SDK.

Uses google.genai (v1+), NOT the deprecated google.generativeai package.
Documentation: https://ai.google.dev/gemini-api/docs

Supported models (verified 2025-Q3):
  gemini-2.0-flash-lite  — free tier, fast, efficient
  gemini-2.0-flash       — higher quality
  gemini-1.5-flash-8b    — free tier fallback
  gemini-1.5-pro         — highest quality (paid)

Free-tier limits (as of 2025-Q3, subject to change):
  gemini-2.0-flash-lite: 1500 req/day, 1M TPM
  Check https://ai.google.dev/pricing for current quotas.

Never logs credentials. Credentials are passed at construction time from the
decrypted credential store — not read from settings directly.
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from backend.providers.base import LLMProvider

log = logging.getLogger("providers.llm.gemini")

# Safe default — not preview-only, has free tier
DEFAULT_MODEL = "gemini-2.0-flash-lite"

# Models known to be available on the free tier (verified 2025-Q3)
FREE_TIER_MODELS = {
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash",
}


class GeminiLLMProvider(LLMProvider):
    """Gemini LLM adapter using google-genai SDK.

    Pass api_key at construction time; never read from environment here
    so the credential store controls key access.
    """

    provider_name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
        max_output_tokens: int = 512,
        temperature: float = 0.6,
        # Inject a pre-built client for testing
        _client: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be provided")
        self.model = model
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        # Lazily import to avoid import-time failure when google-genai not installed
        if _client is not None:
            self._client = _client
        else:
            from google import genai
            self._client = genai.Client(api_key=api_key)
        # Do not log api_key

    def get_capabilities(self) -> dict:
        return {
            "streaming": True,
            "structured_output": True,
            "languages": ["multilingual"],
            "provider": "gemini",
            "model": self.model,
            "free_tier": self.model in FREE_TIER_MODELS,
        }

    async def generate(self, messages: list[dict], **kwargs: Any) -> str:
        """Generate a reply for the given conversation messages.

        messages: list of {"role": "user"|"model"|"system", "content": str}
        Returns the text of the first candidate.

        Raises:
            RuntimeError — authentication error, rate limit, model unavailable
            ValueError — empty or malformed response
        """
        from google import genai
        from google.genai import types as gtypes

        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_output_tokens", self.max_output_tokens)
        system_prompt: str | None = kwargs.get("system_prompt")

        # Build contents — Gemini uses "model" not "assistant"
        contents: list[gtypes.Content] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                # Handled via system_instruction below; skip from contents
                if not system_prompt:
                    system_prompt = content
                continue
            gemini_role = "model" if role == "assistant" else "user"
            contents.append(
                gtypes.Content(
                    role=gemini_role,
                    parts=[gtypes.Part(text=content)],
                )
            )

        config = gtypes.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system_prompt:
            config.system_instruction = system_prompt

        try:
            response = await self._client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            # Sanitize: never put the API key in the exception message
            msg_str = str(exc)
            if "API_KEY" in msg_str.upper() or "INVALID_ARGUMENT" in msg_str:
                raise RuntimeError(
                    f"Gemini API error for model '{model}': authentication or request error"
                ) from exc
            if "RESOURCE_EXHAUSTED" in msg_str or "429" in msg_str:
                raise RuntimeError(
                    f"Gemini rate limit or quota exceeded for model '{model}'"
                ) from exc
            if "MODEL_NOT_FOUND" in msg_str or "404" in msg_str:
                raise RuntimeError(
                    f"Gemini model '{model}' not found or unavailable"
                ) from exc
            raise RuntimeError(f"Gemini generate failed: {type(exc).__name__}") from exc

        # Extract text
        try:
            text = response.text or ""
        except Exception:
            # Some responses have no candidates (blocked)
            text = ""

        if not text.strip():
            raise ValueError(f"Gemini returned empty response for model '{model}'")

        return text.strip()

    async def stream(
        self, messages: list[dict], **kwargs: Any
    ) -> AsyncIterator[str]:
        """Stream text deltas from Gemini."""
        from google import genai
        from google.genai import types as gtypes

        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_output_tokens", self.max_output_tokens)
        system_prompt: str | None = kwargs.get("system_prompt")

        contents: list[gtypes.Content] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                if not system_prompt:
                    system_prompt = content
                continue
            gemini_role = "model" if role == "assistant" else "user"
            contents.append(
                gtypes.Content(
                    role=gemini_role,
                    parts=[gtypes.Part(text=content)],
                )
            )

        config = gtypes.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system_prompt:
            config.system_instruction = system_prompt

        try:
            async for chunk in await self._client.aio.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config,
            ):
                delta = chunk.text or ""
                if delta:
                    yield delta
        except Exception as exc:
            raise RuntimeError(f"Gemini stream failed: {type(exc).__name__}") from exc

    async def get_models(self) -> list[str]:
        return list(FREE_TIER_MODELS)
