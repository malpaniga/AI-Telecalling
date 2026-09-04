"""Groq gpt-oss client (OpenAI-compatible), async + streaming.

Streaming matters: we want to start speaking as soon as the first sentence is
ready, not after the whole reply is generated. `stream_reply` yields text chunks;
`stream_sentences` groups those chunks into speakable sentences for the TTS stage.
"""

import logging
import re
from collections.abc import AsyncIterator

from groq import AsyncGroq

from backend.config import settings
from backend.agent.prompts import SKELETON_SYSTEM_PROMPT

log = logging.getLogger("llm")

# Split on sentence-ending punctuation followed by whitespace.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
# First {...} block in a string, for lenient JSON recovery.
_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

Message = dict[str, str]


def _extract_json(raw: str | None) -> dict | None:
    """Best-effort parse of a JSON object from model output. None on failure."""
    import json

    if not raw or not raw.strip():
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        pass
    match = _JSON_BLOCK.search(raw)
    if match:
        try:
            return json.loads(match.group(0))
        except (ValueError, TypeError):
            pass
    return None


class LLMClient:
    def __init__(self, model: str | None = None, system_prompt: str | None = None):
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.model = model or settings.groq_llm_model
        # A small, fast model handles structured slot extraction; the big model
        # is reserved for the actual conversation.
        self.extraction_model = settings.groq_extraction_model
        self.system_prompt = system_prompt or SKELETON_SYSTEM_PROMPT

    def _build_messages(
        self, history: list[Message], system_prompt: str | None = None
    ) -> list[Message]:
        # Keep only the most recent turns so the prompt (and latency) stays bounded
        # on long calls. The system prompt already carries the known slots + stage.
        limit = settings.llm_history_messages
        recent = history[-limit:] if limit and len(history) > limit else history
        return [{"role": "system", "content": system_prompt or self.system_prompt}, *recent]

    async def stream_reply(
        self, history: list[Message], system_prompt: str | None = None
    ) -> AsyncIterator[str]:
        """Yield raw text deltas as the model generates them.

        gpt-oss on Groq intermittently raises "Tool choice is none, but model
        called a tool". If that happens *before* we've spoken anything, we retry
        once. asyncio.CancelledError (barge-in) is a BaseException and is NOT
        caught here, so interruptions still propagate.
        """
        messages = self._build_messages(history, system_prompt)
        for attempt in range(2):
            yielded = False
            try:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    temperature=0.6,
                    max_tokens=400,
                    extra_body={"reasoning_effort": settings.groq_reasoning_effort},
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yielded = True
                        yield delta
                return
            except Exception as exc:  # noqa: BLE001 - Groq APIError; not CancelledError
                if yielded or attempt == 1:
                    log.warning("stream_reply error (giving up): %s", exc)
                    return
                log.warning("stream_reply error, retrying once: %s", exc)

    async def stream_sentences(
        self, history: list[Message], system_prompt: str | None = None
    ) -> AsyncIterator[str]:
        """Yield complete sentences as soon as they're ready, so TTS can start
        speaking sentence-by-sentence instead of waiting for the full reply."""
        buffer = ""
        async for delta in self.stream_reply(history, system_prompt):
            buffer += delta
            parts = _SENTENCE_END.split(buffer)
            # Keep the last (possibly incomplete) fragment in the buffer.
            while len(parts) > 1:
                sentence = parts.pop(0).strip()
                if sentence:
                    yield sentence
                buffer = _SENTENCE_END.split(buffer, maxsplit=1)[1]
                parts = _SENTENCE_END.split(buffer)
        tail = buffer.strip()
        if tail:
            yield tail

    async def complete(self, history: list[Message]) -> str:
        """Non-streaming convenience helper (used by smoke tests)."""
        return "".join([chunk async for chunk in self.stream_reply(history)])

    async def complete_json(self, system_prompt: str, user_content: str) -> dict:
        """Structured extraction. Never raises: returns {} if extraction fails.

        gpt-oss on Groq occasionally fails strict JSON-mode validation (returns a
        400 with empty generation). We first try JSON mode, then fall back to a
        plain completion parsed leniently, and finally give up gracefully so a
        single bad turn never breaks the call.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        # Attempt 1: strict JSON mode on the fast extraction model.
        try:
            resp = await self.client.chat.completions.create(
                model=self.extraction_model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=150,
            )
            parsed = _extract_json(resp.choices[0].message.content)
            if parsed is not None:
                return parsed
        except Exception as exc:  # noqa: BLE001 - includes Groq BadRequestError
            log.warning("json-mode extraction failed (%s); retrying without it", exc)

        # Attempt 2: plain completion, parse the first JSON object we find.
        try:
            resp = await self.client.chat.completions.create(
                model=self.extraction_model,
                messages=messages,
                temperature=0,
                max_tokens=150,
            )
            parsed = _extract_json(resp.choices[0].message.content)
            if parsed is not None:
                return parsed
        except Exception as exc:  # noqa: BLE001
            log.warning("fallback extraction failed: %s", exc)

        log.warning("extraction returned nothing; continuing with no updates")
        return {}


async def _smoke_test() -> None:
    logging.basicConfig(level="INFO")
    client = LLMClient()
    history = [{"role": "user", "content": "Hi, I'm looking for a 2 bedroom flat."}]
    print("\n--- streaming sentences ---")
    async for sentence in client.stream_sentences(history):
        print("SENTENCE:", sentence)


if __name__ == "__main__":
    import asyncio

    asyncio.run(_smoke_test())
