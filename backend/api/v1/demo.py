"""Demo Mode API.

GET  /api/v1/demo/status     — check if demo mode is active and seeded
POST /api/v1/demo/seed        — seed demo environment (admin only, or DEMO_MODE=true)
DELETE /api/v1/demo/reset     — reset demo data (admin only)

These endpoints only function when DEMO_MODE=true OR the caller is platform_admin.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from backend.config import settings
from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.services.demo_seed_service import DemoSeedService

log = logging.getLogger("api.demo")
router = APIRouter(prefix="/demo", tags=["demo"])


def _require_demo_or_admin(user: CurrentUser):
    """Allow if DEMO_MODE=true OR caller is platform admin."""
    if settings.demo_mode:
        return
    if user.role not in ("platform_owner", "platform_admin"):
        raise HTTPException(
            status_code=403,
            detail="Demo endpoints require DEMO_MODE=true or platform admin role",
        )


@router.get("/status")
async def demo_status(user: CurrentUser = Depends(get_current_user)):
    """Check demo mode status and seeding state."""
    _require_demo_or_admin(user)
    db = get_db()
    svc = DemoSeedService(db)
    is_seeded = await svc.is_seeded()
    return {
        "demo_mode": settings.demo_mode,
        "is_seeded": is_seeded,
        "demo_user_email": "demo-user@telecalling-saas.com",
        "demo_admin_email": "demo-admin@telecalling-saas.com",
        "note": "Passwords are in the seed response. Use /demo/seed to (re)seed.",
    }


@router.post("/seed")
async def seed_demo(
    force: bool = False,
    user: CurrentUser = Depends(get_current_user),
):
    """Seed the demo environment. Pass force=true to re-seed."""
    _require_demo_or_admin(user)
    db = get_db()
    svc = DemoSeedService(db)
    result = await svc.seed_all(force=force)
    return result


@router.delete("/reset")
async def reset_demo(user: CurrentUser = Depends(get_current_user)):
    """Remove demo data (org, users, leads, etc.). Platform admin only."""
    if user.role not in ("platform_owner", "platform_admin"):
        raise HTTPException(status_code=403, detail="Platform admin required")
    db = get_db()
    from backend.services.demo_seed_service import DEMO_ORG_EMAIL
    org = await db["organizations"].find_one({"email": DEMO_ORG_EMAIL})
    if org is None:
        return {"status": "not_seeded"}
    org_id = str(org["_id"])
    # Remove all demo data
    for coll in ["leads", "campaigns", "calls", "appointments", "agents",
                 "agent_versions", "wallet_transactions", "wallets", "credit_lots",
                 "subscriptions", "usage_events"]:
        await db[coll].delete_many({"organization_id": org_id})
    await db["phone_numbers"].delete_many({"organization_id": org_id})
    await db["users"].delete_many({"organization_id": org_id})
    await db["organizations"].delete_many({"email": DEMO_ORG_EMAIL})
    return {"status": "reset", "org_id": org_id}
