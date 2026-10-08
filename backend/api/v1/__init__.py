"""API v1 router — aggregates all v1 sub-routers."""

from fastapi import APIRouter

from backend.api.v1 import agents, auth, billing, credits, leads, organizations, phone_numbers, subscriptions, users, voice_profiles, wallet

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(users.router)
router.include_router(subscriptions.router)
router.include_router(billing.router)
router.include_router(wallet.router)
router.include_router(credits.router)
router.include_router(phone_numbers.router)
router.include_router(voice_profiles.router)
router.include_router(agents.router)
router.include_router(leads.router)
