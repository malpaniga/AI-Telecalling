"""JWT authentication utilities and FastAPI dependencies.

Tokens:
  access_token  — short-lived (60 min default), carries user identity + role
  refresh_token — long-lived (30 days), stored in Redis for revocation

Payload shape:
  {
    "sub": "<user_id>",
    "email": "<email>",
    "role": "<role>",
    "org": "<organization_id | None>",
    "type": "access" | "refresh",
    "jti": "<unique token id>",   # for refresh revocation
    "exp": <unix timestamp>,
    "iat": <unix timestamp>,
  }
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from backend.config import settings

log = logging.getLogger("auth")

# FastAPI security scheme — reads Bearer token from Authorization header
_bearer = HTTPBearer(auto_error=False)

# Redis key for refresh token revocation list: refresh_revoked:{jti}
_REVOKED_PREFIX = "refresh_revoked:"
_REFRESH_TTL = settings.refresh_token_expire_days * 86400


class AuthError(HTTPException):
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------
def _make_token(
    user_id: str,
    email: str,
    role: str,
    org_id: Optional[str],
    token_type: str,
    expire_delta: timedelta,
) -> tuple[str, str]:
    """Return (encoded_jwt, jti)."""
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "org": org_id,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": now + expire_delta,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, jti


def create_access_token(
    user_id: str, email: str, role: str, org_id: Optional[str]
) -> str:
    token, _ = _make_token(
        user_id, email, role, org_id,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    return token


def create_refresh_token(
    user_id: str, email: str, role: str, org_id: Optional[str]
) -> tuple[str, str]:
    """Returns (token, jti). Caller stores jti in Redis for revocation."""
    return _make_token(
        user_id, email, role, org_id,
        "refresh",
        timedelta(days=settings.refresh_token_expire_days),
    )


def create_token_pair(
    user_id: str, email: str, role: str, org_id: Optional[str]
) -> dict:
    access = create_access_token(user_id, email, role, org_id)
    refresh, jti = create_refresh_token(user_id, email, role, org_id)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "jti": jti,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------
def _decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises AuthError on failure."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as exc:
        raise AuthError(f"Invalid token: {exc}") from exc


def decode_access_token(token: str) -> dict:
    payload = _decode_token(token)
    if payload.get("type") != "access":
        raise AuthError("Expected access token")
    return payload


def decode_refresh_token(token: str) -> dict:
    payload = _decode_token(token)
    if payload.get("type") != "refresh":
        raise AuthError("Expected refresh token")
    return payload


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------
class CurrentUser:
    """Authenticated user context — attached to every protected request."""
    __slots__ = ("user_id", "email", "role", "org_id")

    def __init__(self, user_id: str, email: str, role: str, org_id: Optional[str]):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.org_id = org_id

    @property
    def is_platform(self) -> bool:
        from backend.models.user import PLATFORM_ROLES
        return self.role in PLATFORM_ROLES


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> CurrentUser:
    """Dependency: extract + validate access token. Raises 401 if missing/invalid."""
    if not credentials:
        raise AuthError()
    payload = decode_access_token(credentials.credentials)
    return CurrentUser(
        user_id=payload["sub"],
        email=payload["email"],
        role=payload["role"],
        org_id=payload.get("org"),
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[CurrentUser]:
    """Dependency: returns CurrentUser or None (for public endpoints with optional auth)."""
    if not credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        return CurrentUser(
            user_id=payload["sub"],
            email=payload["email"],
            role=payload["role"],
            org_id=payload.get("org"),
        )
    except AuthError:
        return None


# ---------------------------------------------------------------------------
# Refresh token revocation (Redis)
# ---------------------------------------------------------------------------
async def revoke_refresh_token(jti: str) -> None:
    """Mark a refresh token as revoked. Called on logout."""
    try:
        from backend.core.redis import get_redis
        r = get_redis()
        await r.set(f"{_REVOKED_PREFIX}{jti}", "1", ex=_REFRESH_TTL)
    except Exception as exc:  # noqa: BLE001
        log.warning("failed to revoke refresh token: %s", exc)


async def is_refresh_token_revoked(jti: str) -> bool:
    """Returns True if the refresh token has been revoked."""
    try:
        from backend.core.redis import get_redis
        r = get_redis()
        return bool(await r.exists(f"{_REVOKED_PREFIX}{jti}"))
    except Exception as exc:  # noqa: BLE001
        log.warning("failed to check refresh token revocation: %s", exc)
        return False  # fail open (token expiry is the backstop)
