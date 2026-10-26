"""Gemini LLM provider adapter using the official google-genai SDK.

Uses google.genai (v1+), NOT the deprecated google.generativeai package.
Documentation: https://ai.google.dev/gemini-api/docs

Supported models:
  gemini-3.1-flash-lite  — ultra low-latency (~1s), reliable, no thinking overhead
  gemini-3.5-flash-lite  — quality conversational model
  gemini-3.5-flash       — fast general-purpose
  gemini-3.8-flash       — high-capacity model
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from backend.providers.base import LLMProvider

log = logging.getLogger("providers.llm.gemini")

# Safe default — ultra low-latency active model
DEFAULT_MODEL = "gemini-3.1-flash-lite"

FREE_TIER_MODELS = {
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
}

# Automatic aliases from deprecated / legacy model IDs to current active models
MODEL_ALIASES = {
    "gemini-2.0-flash-lite": "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite": "gemini-3.1-flash-lite",
    "gemini-2.0-flash": "gemini-3.5-flash",
    "gemini-2.5-flash": "gemini-3.5-flash",
    "gemini-1.5-flash": "gemini-3.1-flash-lite",
    "gemini-1.5-flash-8b": "gemini-3.1-flash-lite",
    "gemini-flash-latest": "gemini-3.5-flash",
    "gemini-flash-lite-latest": "gemini-3.1-flash-lite",
}


def _get_candidate_models(primary_model: str) -> list[str]:
    """Return ordered list of models to try: primary model first, then compatible fallbacks."""
    primary = MODEL_ALIASES.get(primary_model, primary_model)
    candidates = [primary]
    fallbacks = [
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
    ]
    for m in fallbacks:
        if m not in candidates:
            candidates.append(m)
    return candidates


def _is_transient_error(exc: Exception) -> bool:
    """Return True if the error is temporary (503 high demand, 429 rate limit, network timeout)."""
    msg_str = str(exc)
    return any(
        t in msg_str
        for t in [
            "503",
            "500",
            "502",
            "504",
            "429",
            "high demand",
            "Service Unavailable",
            "UNAVAILABLE",
            "RESOURCE_EXHAUSTED",
            "DEADLINE_EXCEEDED",
            "timed out",
            "timeout",
        ]
    )


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
        _client: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be provided")
        self.model = model
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self._clean_key = api_key.strip().strip("'\"")
        if _client is not None:
            self._client = _client
        else:
            from google import genai
            self._client = genai.Client(api_key=self._clean_key)

    def _sanitize(self, msg: str) -> str:
        if self._clean_key and self._clean_key in msg:
            return msg.replace(self._clean_key, "[REDACTED]")
        return msg

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
        """Generate a reply for the given conversation messages."""
        from google.genai import types as gtypes

        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_output_tokens") or kwargs.get("max_tokens") or self.max_output_tokens
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

        config_kwargs: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt

        config = gtypes.GenerateContentConfig(**config_kwargs)
        candidate_models = _get_candidate_models(model)
        last_exc: Exception | None = None

        for cand_idx, cand_model in enumerate(candidate_models):
            for attempt in range(2):
                try:
                    response = await self._client.aio.models.generate_content(
                        model=cand_model,
                        contents=contents,
                        config=config,
                    )
                    text = ""
                    try:
                        text = response.text or ""
                    except Exception:
                        text = ""

                    if text.strip():
                        return text.strip()
                except Exception as exc:
                    last_exc = exc
                    msg_str = str(exc)
                    if ("API_KEY" in msg_str.upper() or "PERMISSION_DENIED" in msg_str or "UNAUTHENTICATED" in msg_str) and "thinking" not in msg_str.lower():
                        raise RuntimeError(
                            "Gemini authentication failed: Invalid or expired API key. "
                            "Please verify your key at aistudio.google.com"
                        ) from exc

                    if _is_transient_error(exc) or "400" in msg_str:
                        if attempt == 0:
                            await asyncio.sleep(0.35)
                            continue
                        elif cand_idx + 1 < len(candidate_models):
                            next_model = candidate_models[cand_idx + 1]
                            log.warning(
                                "Gemini generate failed on '%s' (%s). Retrying with fallback model '%s'",
                                cand_model,
                                self._sanitize(msg_str[:120]),
                                next_model,
                            )
                            break
                    break

        if last_exc:
            msg_str = self._sanitize(str(last_exc))
            if "RESOURCE_EXHAUSTED" in msg_str or "429" in msg_str:
                raise RuntimeError(
                    f"Gemini rate limit or quota exceeded for model '{model}'"
                ) from last_exc
            if "NOT_FOUND" in msg_str or "404" in msg_str:
                raise RuntimeError(
                    f"Gemini model '{model}' not found or deprecated: {msg_str}"
                ) from last_exc
            raise RuntimeError(f"Gemini generate failed: {msg_str}") from last_exc

        raise ValueError(f"Gemini returned empty response for model '{model}'")

    async def stream(
        self, messages: list[dict], **kwargs: Any
    ) -> AsyncIterator[str]:
        """Stream text deltas from Gemini with automatic retry and model fallback."""
        from google.genai import types as gtypes

        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_output_tokens") or kwargs.get("max_tokens") or self.max_output_tokens
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

        config_kwargs: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt

        config = gtypes.GenerateContentConfig(**config_kwargs)
        candidate_models = _get_candidate_models(model)
        last_exc: Exception | None = None
        yielded_any = False

        for cand_idx, cand_model in enumerate(candidate_models):
            if yielded_any:
                break
            for attempt in range(2):
                if yielded_any:
                    break
                try:
                    stream_res = await self._client.aio.models.generate_content_stream(
                        model=cand_model,
                        contents=contents,
                        config=config,
                    )

                    async for chunk in stream_res:
                        delta = ""
                        try:
                            delta = chunk.text or ""
                        except Exception:
                            delta = ""
                        if delta:
                            yielded_any = True
                            yield delta

                    if yielded_any:
                        return
                except Exception as exc:
                    last_exc = exc
                    msg_str = str(exc)
                    if yielded_any:
                        log.warning("Gemini stream interrupted mid-generation: %s", exc)
                        return

                    if ("API_KEY" in msg_str.upper() or "PERMISSION_DENIED" in msg_str or "UNAUTHENTICATED" in msg_str) and "thinking" not in msg_str.lower():
                        raise RuntimeError(
                            "Gemini authentication failed: Invalid or expired API key. "
                            "Please verify your key at aistudio.google.com"
                        ) from exc

                    if _is_transient_error(exc) or "thinking" in msg_str.lower() or "400" in msg_str:
                        if attempt == 0:
                            await asyncio.sleep(0.35)
                            continue
                        elif cand_idx + 1 < len(candidate_models):
                            next_model = candidate_models[cand_idx + 1]
                            log.warning(
                                "Gemini stream failed on '%s' (%s). Retrying with fallback model '%s'",
                                cand_model,
                                self._sanitize(msg_str[:120]),
                                next_model,
                            )
                            break
                    break

        if not yielded_any and last_exc:
            msg_str = self._sanitize(str(last_exc))
            if "RESOURCE_EXHAUSTED" in msg_str or "429" in msg_str:
                raise RuntimeError(
                    f"Gemini rate limit or quota exceeded for model '{model}'"
                ) from last_exc
            if "NOT_FOUND" in msg_str or "404" in msg_str:
                raise RuntimeError(
                    f"Gemini model '{model}' not found or deprecated: {msg_str}"
                ) from last_exc
            raise RuntimeError(f"Gemini stream failed: {msg_str}") from last_exc

    async def get_models(self) -> list[str]:
        return list(FREE_TIER_MODELS)
