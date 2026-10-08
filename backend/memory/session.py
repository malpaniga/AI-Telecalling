"""Redis-backed live session store.

Holds in-flight conversation state (stage, slots, flags, messages) for an
active call under `session:{call_id}`. Flushed after every turn; survives
process restarts. Loaded and deleted on call finalization.
"""

import json
import logging
from typing import Optional

from backend.config import settings
from backend.agent.state import ConversationState

log = logging.getLogger("session")

_SESSION_TTL = 60 * 60  # 1 hour


class SessionStore:
    def __init__(self, client=None):
        if client is not None:
            self.redis = client
        else:
            import redis.asyncio as aioredis
            self.redis = aioredis.from_url(
                settings.redis_url, decode_responses=True
            )

    @staticmethod
    def _key(call_id: str) -> str:
        return f"session:{call_id}"

    async def save(self, call_id: str, state: ConversationState) -> None:
        await self.redis.set(self._key(call_id), json.dumps(state), ex=_SESSION_TTL)

    async def load(self, call_id: str) -> Optional[ConversationState]:
        raw = await self.redis.get(self._key(call_id))
        return json.loads(raw) if raw else None

    async def delete(self, call_id: str) -> None:
        await self.redis.delete(self._key(call_id))

    async def ping(self) -> bool:
        return bool(await self.redis.ping())

    async def close(self) -> None:
        await self.redis.aclose()
