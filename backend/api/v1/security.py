"""Security API — admin only.

GET /api/v1/security/audit    — run security audit checks
GET /api/v1/security/limits   — show configured rate limits
"""

import logging
from fastapi import APIRouter, Depends
from backend.core.rbac import require_platform
from backend.core.db import get_db
from backend.services.security_audit_service import SecurityAuditService
from backend.core.rate_limit import DEFAULT_LIMITS

log = logging.getLogger("api.security")
router = APIRouter(
    prefix="/security",
    tags=["security"],
    dependencies=[Depends(require_platform())],
)


@router.get("/audit")
async def security_audit():
    """Run security audit checks against the codebase."""
    svc = SecurityAuditService(base_path=".")
    return await svc.run_all()


@router.get("/limits")
async def rate_limits():
    """Show configured rate limit settings."""
    return {"limits": DEFAULT_LIMITS}
