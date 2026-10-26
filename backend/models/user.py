"""User model.

Users belong to an organization (or are platform users with organization_id=None).

Platform roles:
  platform_owner   — full platform control
  platform_admin   — manage orgs, plans, providers
  support          — read-only + support actions
  billing_admin    — billing/payment management

Organization roles:
  organization_owner — full org control
  organization_admin — manage org settings, team
  manager            — manage campaigns, leads
  agent              — view calls and leads
  viewer             — read-only

Password is bcrypt-hashed; never stored in plain text.
Never include password_hash in API responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field

from backend.models.base import TimestampedModel

PLATFORM_ROLES = {
    "platform_owner",
    "platform_admin",
    "support",
    "billing_admin",
}

ORGANIZATION_ROLES = {
    "organization_owner",
    "organization_admin",
    "manager",
    "agent",
    "viewer",
}

ALL_ROLES = PLATFORM_ROLES | ORGANIZATION_ROLES


class User(TimestampedModel):
    """MongoDB user document."""
    organization_id: Optional[str] = None  # None for platform users
    email: str
    password_hash: str
    role: str                               # see role constants above
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None

    # Status
    is_active: bool = True
    is_email_verified: bool = False
    email_verify_token: Optional[str] = None
    email_verify_expires: Optional[datetime] = None

    # Password reset
    reset_token: Optional[str] = None
    reset_token_expires: Optional[datetime] = None

    # Auth tracking
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

    @property
    def full_name(self) -> str:
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) if parts else self.email.split("@")[0]

    @property
    def is_platform_user(self) -> bool:
        return self.role in PLATFORM_ROLES


class UserPublic(TimestampedModel):
    """Safe user response (no password_hash or tokens)."""
    organization_id: Optional[str] = None
    email: str
    role: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    is_email_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime


class UserCreate(TimestampedModel):
    """Input for creating a user."""
    email: str
    password: str
    role: str = "organization_owner"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class UserLogin(TimestampedModel):
    """Login input."""
    email: str
    password: str


class TokenPair(TimestampedModel):
    """JWT token pair returned on login/signup."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int             # seconds
    user: UserPublic
    organization_id: Optional[str] = None
