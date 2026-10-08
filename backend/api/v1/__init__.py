"""API v1 router — aggregates all v1 sub-routers."""

from fastapi import APIRouter

from backend.api.v1 import organizations, users

router = APIRouter(prefix="/api/v1")

router.include_router(organizations.router)
router.include_router(users.router)
