"""Audit log repository. Write-only (no updates/deletes)."""

from typing import Any, Optional

from pymongo import DESCENDING

from backend.models.audit_log import AuditLog
from backend.models.base import new_id
from backend.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository):
    collection_name = "audit_logs"
    model_class = AuditLog

    async def log(
        self,
        action: str,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        changes: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> AuditLog:
        entry = AuditLog(
            _id=new_id(),
            organization_id=organization_id,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            error_message=error_message,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            duration_ms=duration_ms,
        )
        await self.insert(entry)
        return entry

    async def list_for_org(
        self,
        organization_id: str,
        limit: int = 100,
        skip: int = 0,
        action_prefix: Optional[str] = None,
    ) -> list[AuditLog]:
        query: dict = {"organization_id": organization_id}
        if action_prefix:
            import re
            query["action"] = {"$regex": f"^{re.escape(action_prefix)}"}
        return await self.find_many(
            query,
            sort=[("created_at", DESCENDING)],
            limit=limit,
            skip=skip,
        )

    async def list_platform(
        self,
        limit: int = 100,
        skip: int = 0,
    ) -> list[AuditLog]:
        return await self.find_many(
            {},
            sort=[("created_at", DESCENDING)],
            limit=limit,
            skip=skip,
        )
