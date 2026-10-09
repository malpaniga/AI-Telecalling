"""Rate limiting via Redis sliding-window counters.

Per-IP and per-user limits to prevent abuse:
  - /api/v1/auth/* : strict (5/min per IP) — brute-force protection
  - /api/v1/billing/* : moderate (30/min per user)
  - general API : lenient (120/min per user)

Uses Redis INCR with TTL — atomic, fast, no DB load.

If Redis is unavailable, rate limiting is skipped (fail-open) so the app
still works in dev/test. Production must have Redis.
"""

import logging
import time
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from backend.core.auth import get_current_user

log = logging.getLogger("rate_limit")

# Default rate limits (requests per window)
DEFAULT_LIMITS = {
    "auth": {"requests": 10, "window_seconds": 60},      # 10/min for auth endpoints
    "billing": {"requests": 30, "window_seconds": 60},   # 30/min for billing
    "api": {"requests": 120, "window_seconds": 60},       # 120/min general
    "import": {"requests": 5, "window_seconds": 300},     # 5/5min for bulk imports
}

_PREFIX = "rate_limit:"


def _client_ip(request: Request) -> str:
    # Honor X-Forwarded-For when behind a trusted proxy (Fly.io)
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _check_rate_limit(
    key: str,
    limit: int,
    window: int,
) -> tuple[bool, int, int]:
    """
    Returns (allowed, current_count, retry_after_seconds).
    Uses Redis INCR + EXPIRE for a sliding window.
    """
    try:
        from backend.core.redis import get_redis
        r = get_redis()
    except Exception:  # noqa: BLE001
        return True, 0, 0  # fail-open if Redis down

    full_key = f"{_PREFIX}{key}"
    try:
        count = await r.incr(full_key)
        if count == 1:
            await r.expire(full_key, window)
        if count > limit:
            ttl = await r.ttl(full_key)
            return False, count, max(1, ttl)
        return True, count, 0
    except Exception as exc:  # noqa: BLE001
        log.warning("rate_limit check failed (fail-open): %s", exc)
        return True, 0, 0


async def rate_limit_auth(request: Request) -> None:
    """Rate limit auth endpoints by IP (brute-force protection)."""
    ip = _client_ip(request)
    allowed, count, retry = await _check_rate_limit(
        f"auth:{ip}",
        DEFAULT_LIMITS["auth"]["requests"],
        DEFAULT_LIMITS["auth"]["window_seconds"],
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many authentication attempts. Retry in {retry}s.",
            headers={"Retry-After": str(retry)},
        )


async def rate_limit_billing(
    request: Request,
    user=Depends(get_current_user),
):
    """Rate limit billing endpoints per user."""
    uid = user.user_id if user else _client_ip(request)
    allowed, count, retry = await _check_rate_limit(
        f"billing:{uid}",
        DEFAULT_LIMITS["billing"]["requests"],
        DEFAULT_LIMITS["billing"]["window_seconds"],
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many billing requests. Please slow down.",
            headers={"Retry-After": str(retry)},
        )
    return user


async def rate_limit_api(
    request: Request,
    user=Depends(get_current_user),
):
    """General API rate limit per user."""
    uid = user.user_id if user else _client_ip(request)
    allowed, count, retry = await _check_rate_limit(
        f"api:{uid}",
        DEFAULT_LIMITS["api"]["requests"],
        DEFAULT_LIMITS["api"]["window_seconds"],
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down.",
            headers={"Retry-After": str(retry)},
        )
    return user


async def rate_limit_import(
    request: Request,
    user=Depends(get_current_user),
):
    """Strict rate limit for bulk import operations."""
    uid = user.user_id if user else _client_ip(request)
    allowed, count, retry = await _check_rate_limit(
        f"import:{uid}",
        DEFAULT_LIMITS["import"]["requests"],
        DEFAULT_LIMITS["import"]["window_seconds"],
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many import requests. Please wait before importing again.",
            headers={"Retry-After": str(retry)},
        )
    return user


# Expose Depends for convenience
