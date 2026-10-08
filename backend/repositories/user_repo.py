"""User repository."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from pymongo import ASCENDING, DESCENDING

from backend.models.base import new_id, utcnow
from backend.models.user import User
from backend.repositories.base import BaseRepository


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:  # noqa: BLE001
        return False


class UserRepository(BaseRepository):
    collection_name = "users"
    model_class = User

    async def create(
        self,
        email: str,
        password: str,
        role: str,
        organization_id: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> User:
        user = User(
            _id=new_id(),
            organization_id=organization_id,
            email=email.lower().strip(),
            password_hash=hash_password(password),
            role=role,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
        )
        await self.insert(user)
        return user

    async def find_by_email(self, email: str) -> Optional[User]:
        return await self.find_one({"email": email.lower().strip()})

    async def find_by_org(
        self, organization_id: str, limit: int = 50
    ) -> list[User]:
        return await self.find_many(
            {"organization_id": organization_id, "is_active": True},
            sort=[("created_at", DESCENDING)],
            limit=limit,
        )

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        user = await self.find_by_email(email)
        if user is None:
            return None
        if not user.is_active:
            return None
        # Check lockout
        if user.locked_until and user.locked_until > utcnow():
            return None
        if not verify_password(password, user.password_hash):
            # Increment failed attempts; lock after 5
            attempts = user.failed_login_attempts + 1
            updates: dict = {"failed_login_attempts": attempts}
            if attempts >= 5:
                updates["locked_until"] = utcnow() + timedelta(minutes=15)
            await self.update_by_id(user.id, updates)
            return None
        # Success: reset counters
        await self.update_by_id(user.id, {
            "failed_login_attempts": 0,
            "locked_until": None,
            "last_login_at": utcnow(),
        })
        return user

    async def set_email_verified(self, user_id: str) -> bool:
        return await self.update_by_id(user_id, {
            "is_email_verified": True,
            "email_verify_token": None,
            "email_verify_expires": None,
        })

    async def set_reset_token(self, user_id: str, hours: int = 1) -> str:
        token = secrets.token_urlsafe(32)
        expires = utcnow() + timedelta(hours=hours)
        await self.update_by_id(user_id, {
            "reset_token": token,
            "reset_token_expires": expires,
        })
        return token

    async def find_by_reset_token(self, token: str) -> Optional[User]:
        user = await self.find_one({"reset_token": token})
        if user is None:
            return None
        if user.reset_token_expires and user.reset_token_expires < utcnow():
            return None
        return user

    async def update_password(self, user_id: str, new_password: str) -> bool:
        return await self.update_by_id(user_id, {
            "password_hash": hash_password(new_password),
            "reset_token": None,
            "reset_token_expires": None,
        })

    async def deactivate(self, user_id: str) -> bool:
        return await self.update_by_id(user_id, {"is_active": False})

    async def update_role(self, user_id: str, new_role: str) -> bool:
        return await self.update_by_id(user_id, {"role": new_role})
