"""Audit log model.

Immutable record of actions in the system. Used for security, compliance, and
support. Never deleted or modified after creation.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from backend.models.base import DocumentModel, utcnow


class AuditLog(DocumentModel):
    """Audit log entry — immutable after creation."""

    # Who
    organization_id: Optional[str] = None  # None for platform actions
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # What
    action: str                             # e.g. "user.login", "campaign.start"
    resource_type: Optional[str] = None    # e.g. "campaign", "call", "payment"
    resource_id: Optional[str] = None
    changes: Optional[dict[str, Any]] = None  # {field: {old, new}}

    # Result
    status: str = "success"                # success | failure
    error_message: Optional[str] = None

    # When
    created_at: datetime = Field(default_factory=utcnow)

    # Request context
    request_id: Optional[str] = None
    duration_ms: Optional[int] = None
