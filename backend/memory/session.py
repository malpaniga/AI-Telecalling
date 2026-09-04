"""Redis-backed live session store.

Holds the in-flight conversation state (stage, slots, flags, messages) for an
active call under `session:{call_id}`. We flush after every turn so the state
survives a process restart and can be inspected live by the dashboard later.
"""

import json
import logging

import redis.asyncio as aioredis

from backend.config import settings
from backend.agent.state import ConversationState

log = logging.getLogger("session")

_SESSION_TTL = 60 * 60  # 1 hour; live calls are short-lived.


class SessionStore:
    def __init__(self, client: aioredis.Redis | None = None):
        self.redis = client or aioredis.from_url(settings.redis_url, decode_responses=True)

    @staticmethod
    def _key(call_id: str) -> str:
        return f"session:{call_id}"

    async def save(self, call_id: str, state: ConversationState) -> None:
        await self.redis.set(self._key(call_id), json.dumps(state), ex=_SESSION_TTL)

    async def load(self, call_id: str) -> ConversationState | None:
        raw = await self.redis.get(self._key(call_id))
        return json.loads(raw) if raw else None

    async def delete(self, call_id: str) -> None:
        await self.redis.delete(self._key(call_id))

    async def ping(self) -> bool:
        return bool(await self.redis.ping())

    async def close(self) -> None:
        await self.redis.aclose()
