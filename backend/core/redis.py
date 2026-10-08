"""Redis async client factory.

Single process-wide client. Redis is used for:
- Live call session state (session:{call_id})
- Credit reservation locks (wallet_reserve:{org_id}:{call_id})
- Campaign worker coordination
- Rate limiting counters

NOT used for durable data (MongoDB is source of truth).
"""

import logging
from typing import Optional

import redis.asyncio as aioredis

from backend.config import settings

log = logging.getLogger("redis_client")

_redis: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis


async def init_redis() -> None:
    global _redis
    _redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        max_connections=50,
    )
    # Verify connectivity
    await _redis.ping()
    log.info("Redis connected: %s", settings.redis_url.split("@")[-1])


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        log.info("Redis connection closed")


async def ping_redis() -> bool:
    """Health check — returns True if Redis is reachable."""
    try:
        if _redis is None:
            return False
        return bool(await _redis.ping())
    except Exception as exc:  # noqa: BLE001
        log.warning("Redis ping failed: %s", exc)
        return False
