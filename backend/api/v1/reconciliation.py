"""Reconciliation API — admin only.

GET /api/v1/reconciliation/run       — run all reconciliation checks
GET /api/v1/reconciliation/report      — alias for /run (returns latest report)
"""

import logging
from fastapi import APIRouter, Depends, Query
from backend.core.rbac import require_platform
from backend.core.db import get_db
from backend.services.reconciliation_service import ReconciliationService

log = logging.getLogger("api.reconciliation")
router = APIRouter(
    prefix="/reconciliation",
    tags=["reconciliation"],
    dependencies=[Depends(require_platform())],
)


@router.get("/run")
async def run_reconciliation(hours: int = Query(default=24, ge=1, le=168)):
    """Run all financial ledger consistency checks."""
    svc = ReconciliationService(get_db())
    return await svc.run_all(hours=hours)


@router.get("/report")
async def reconciliation_report(hours: int = Query(default=24, ge=1, le=168)):
    """Alias for /run — returns the full reconciliation report."""
    svc = ReconciliationService(get_db())
    return await svc.run_all(hours=hours)
