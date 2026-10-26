"""Compatibility adapters from cloud provider interfaces to the call pipeline."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Any
from dataclasses import dataclass

from backend.providers.base import LLMProvider, STTProvider, TTSProvider

_SENTENCE_END = re.compile(r"(?<=[.!?।॥\n])\s+")
_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


class CloudCallLLM:
    """Exposes the legacy conversation-engine protocol over an LLMProvider."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def complete(self, history: list[dict]) -> str:
        return await self._provider.generate(history)

    async def stream_sentences(
        self, history: list[dict], system_prompt: str | None = None
    ) -> AsyncIterator[str]:
        # Keep only the most recent 6 messages to prevent prompt bloat and keep generation under 1 second
        bounded_history = history[-6:] if len(history) > 6 else history
        buffer = ""
        async for delta in self._provider.stream(bounded_history, system_prompt=system_prompt):
            buffer += delta
            parts = _SENTENCE_END.split(buffer)
            if len(parts) > 1:
                for sentence in parts[:-1]:
                    s = sentence.strip()
                    if s:
                        yield s
                buffer = parts[-1]
        tail = buffer.strip()
        if tail:
            yield tail

    async def complete_json(self, system_prompt: str, user_content: str) -> dict:
        """Best-effort extraction; a malformed model answer cannot end a call."""
        try:
            raw = await self._provider.generate(
                [{"role": "user", "content": user_content}],
                system_prompt=system_prompt,
                temperature=0,
                max_tokens=150,
                max_output_tokens=150,
            )
            return _parse_json(raw)
        except Exception:  # call engine treats extraction as non-critical
            return {}


class CloudCallTTS:
    """Exposes the established TTSEngine protocol over a cloud TTS provider."""

    def __init__(self, provider: TTSProvider) -> None:
        self._provider = provider
        self.sample_rate = int(provider.get_capabilities().get("sample_rate", 16000))

    async def synthesize(self, text: str, language: str | None = None, **kwargs: Any) -> tuple[bytes, int]:
        result = await self._provider.synthesize(text, language=language, **kwargs)
        return result.get("audio", b""), int(result.get("sample_rate", self.sample_rate))

    async def synthesize_stream(
        self, text: str, language: str | None = None, **kwargs: Any
    ) -> AsyncIterator[tuple[bytes, int]]:
        async for result in self._provider.stream(text, language=language, **kwargs):
            audio = result.get("audio", b"")
            if audio:
                yield audio, int(result.get("sample_rate", self.sample_rate))


@dataclass(frozen=True)
class CloudCallComponents:
    stt: STTProvider
    llm: CloudCallLLM
    tts: CloudCallTTS


def build_cloud_call_components(
    stt: STTProvider, llm: LLMProvider, tts: TTSProvider
) -> CloudCallComponents:
    return CloudCallComponents(stt=stt, llm=CloudCallLLM(llm), tts=CloudCallTTS(tts))


def _parse_json(raw: str) -> dict:
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        match = _JSON_BLOCK.search(raw or "")
        if not match:
            return {}
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else {}
        except ValueError:
            return {}
