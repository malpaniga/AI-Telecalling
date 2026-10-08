"""API v1 router — aggregates all v1 sub-routers."""

from fastapi import APIRouter

from backend.api.v1 import auth, billing, credits, organizations, phone_numbers, subscriptions, users, wallet

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(users.router)
router.include_router(subscriptions.router)
router.include_router(billing.router)
router.include_router(wallet.router)
router.include_router(credits.router)
router.include_router(phone_numbers.router)
