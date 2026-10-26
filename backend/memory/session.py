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
        self._local: dict[str, str] = {}
        self._disabled = False
        if client is not None:
            self.redis = client
        else:
            try:
                import redis.asyncio as aioredis
                self.redis = aioredis.from_url(
                    settings.redis_url, decode_responses=True
                )
            except Exception:
                self.redis = None
                self._disabled = True

    @staticmethod
    def _key(call_id: str) -> str:
        return f"session:{call_id}"

    async def save(self, call_id: str, state: ConversationState) -> None:
        if self._disabled or self.redis is None:
            self._local[self._key(call_id)] = json.dumps(state)
            return
        try:
            await self.redis.set(self._key(call_id), json.dumps(state), ex=_SESSION_TTL)
        except Exception as exc:
            self._disabled = True
            log.info("Redis unavailable; using in-memory session store: %s", exc)
            self._local[self._key(call_id)] = json.dumps(state)

    async def load(self, call_id: str) -> Optional[ConversationState]:
        if self._disabled or self.redis is None:
            raw = self._local.get(self._key(call_id))
            return json.loads(raw) if raw else None
        try:
            raw = await self.redis.get(self._key(call_id))
            return json.loads(raw) if raw else None
        except Exception:
            self._disabled = True
            raw = self._local.get(self._key(call_id))
            return json.loads(raw) if raw else None

    async def delete(self, call_id: str) -> None:
        if self._disabled or self.redis is None:
            self._local.pop(self._key(call_id), None)
            return
        try:
            await self.redis.delete(self._key(call_id))
        except Exception:
            self._disabled = True
            self._local.pop(self._key(call_id), None)

    async def ping(self) -> bool:
        if self._disabled or self.redis is None:
            return True
        try:
            return bool(await self.redis.ping())
        except Exception:
            self._disabled = True
            return True

    async def close(self) -> None:
        if self.redis is not None and not self._disabled:
            try:
                await self.redis.aclose()
            except Exception:
                pass
