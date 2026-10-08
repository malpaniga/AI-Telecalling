"""API v1 router — aggregates all v1 sub-routers."""

from fastapi import APIRouter

from backend.api.v1 import auth, organizations, subscriptions, users

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(users.router)
router.include_router(subscriptions.router)
