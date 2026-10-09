"""Authentication API endpoints.

POST /api/v1/auth/signup   — create org + owner user in one step
POST /api/v1/auth/login    — email + password → token pair
POST /api/v1/auth/logout   — revoke refresh token
POST /api/v1/auth/refresh  — exchange refresh token for new access token
GET  /api/v1/auth/me       — get current user profile
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator

from backend.core.auth import (
    AuthError,
    CurrentUser,
    create_token_pair,
    decode_refresh_token,
    get_current_user,
    is_refresh_token_revoked,
    revoke_refresh_token,
)
from backend.core.db import get_db
from backend.core.rate_limit import rate_limit_auth
from backend.repositories.audit_log_repo import AuditLogRepository
from backend.repositories.organization_repo import OrganizationRepository
from backend.repositories.user_repo import UserRepository

log = logging.getLogger("api.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class SignupRequest(BaseModel):
    # Organization fields
    org_name: str
    org_email: str
    org_phone: Optional[str] = None

    # User fields
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("email", "org_email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower().strip()


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def lowercase(cls, v: str) -> str:
        return v.lower().strip()


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict
    organization_id: Optional[str]


class MeResponse(BaseModel):
    id: str
    email: str
    role: str
    organization_id: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    is_email_verified: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _token_response(user, org_id: Optional[str]) -> dict:
    tokens = create_token_pair(
        user_id=user.id,
        email=user.email,
        role=user.role,
        org_id=org_id,
    )
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer",
        "expires_in": tokens["expires_in"],
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
        "organization_id": org_id,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, request: Request):
    """
    Create a new organization + organization_owner user in one atomic step.
    Returns a token pair immediately (no email verification required for MVP).
    """
    await rate_limit_auth(request)
    db = get_db()
    user_repo = UserRepository(db)
    org_repo = OrganizationRepository(db)
    audit = AuditLogRepository(db)

    ip = request.client.host if request.client else None

    # Check duplicate user email
    if await user_repo.find_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Check duplicate org email
    if await org_repo.find_by_email(body.org_email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organization with this email already exists",
        )

    # Create organization
    org = await org_repo.create(
        name=body.org_name,
        email=body.org_email,
        phone=body.org_phone,
    )

    # Create owner user
    user = await user_repo.create(
        email=body.email,
        password=body.password,
        role="organization_owner",
        organization_id=org.id,
        first_name=body.first_name,
        last_name=body.last_name,
    )

    await audit.log(
        action="auth.signup",
        organization_id=org.id,
        user_id=user.id,
        user_email=user.email,
        user_role=user.role,
        resource_type="organization",
        resource_id=org.id,
        ip_address=ip,
    )

    log.info("signup org=%s user=%s", org.id, user.id)
    return _token_response(user, org.id)


@router.post("/login")
async def login(body: LoginRequest, request: Request):
    """Authenticate with email + password. Returns token pair."""
    await rate_limit_auth(request)
    db = get_db()
    user_repo = UserRepository(db)
    audit = AuditLogRepository(db)

    ip = request.client.host if request.client else None

    user = await user_repo.authenticate(body.email, body.password)
    if user is None:
        # Log failed attempt (no user_id since we don't know who it was)
        await audit.log(
            action="auth.login",
            status="failure",
            error_message="Invalid credentials or account locked",
            ip_address=ip,
        )
        # Always return the same error to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    await audit.log(
        action="auth.login",
        organization_id=user.organization_id,
        user_id=user.id,
        user_email=user.email,
        user_role=user.role,
        status="success",
        ip_address=ip,
    )

    log.info("login user=%s role=%s org=%s", user.id, user.role, user.organization_id)
    return _token_response(user, user.organization_id)


@router.post("/logout")
async def logout(
    body: RefreshRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Revoke the refresh token. Access token expires naturally."""
    try:
        payload = decode_refresh_token(body.refresh_token)
        jti = payload.get("jti")
        if jti:
            await revoke_refresh_token(jti)
    except AuthError:
        pass  # Token already invalid — logout is idempotent

    return {"status": "logged out"}


@router.post("/refresh")
async def refresh_token(body: RefreshRequest, request: Request):
    """Exchange a valid refresh token for a new access token."""
    db = get_db()
    user_repo = UserRepository(db)

    payload = decode_refresh_token(body.refresh_token)  # raises AuthError if invalid

    jti = payload.get("jti", "")
    if await is_refresh_token_revoked(jti):
        raise AuthError("Refresh token has been revoked")

    # Verify user still exists and is active
    user = await user_repo.find_by_id(payload["sub"])
    if user is None or not user.is_active:
        raise AuthError("User not found or inactive")

    # Revoke old refresh token and issue new pair
    await revoke_refresh_token(jti)

    log.info("token refresh user=%s", user.id)
    return _token_response(user, user.organization_id)


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    db = get_db()
    user_repo = UserRepository(db)

    db_user = await user_repo.find_by_id(user.user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return MeResponse(
        id=db_user.id,
        email=db_user.email,
        role=db_user.role,
        organization_id=db_user.organization_id,
        first_name=db_user.first_name,
        last_name=db_user.last_name,
        is_active=db_user.is_active,
        is_email_verified=db_user.is_email_verified,
    )
