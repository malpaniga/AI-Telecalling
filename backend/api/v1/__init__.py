"""API v1 router — aggregates all v1 sub-routers."""

from fastapi import APIRouter

from backend.api.v1 import admin, agents, analytics, appointments, auth, billing, billing_portal, calls, campaigns, credits, dashboard, knowledge, leads, organizations, phone_numbers, provider_ops, reconciliation, security, subscriptions, transcripts, usage, users, voice_profiles, wallet

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(users.router)
router.include_router(subscriptions.router)
router.include_router(billing.router)
router.include_router(billing_portal.router)
router.include_router(wallet.router)
router.include_router(credits.router)
router.include_router(phone_numbers.router)
router.include_router(voice_profiles.router)
router.include_router(agents.router)
router.include_router(leads.router)
router.include_router(campaigns.router)
router.include_router(calls.router)
router.include_router(appointments.router)
router.include_router(knowledge.router)
router.include_router(transcripts.router)
router.include_router(usage.router)
router.include_router(dashboard.router)
router.include_router(admin.router)
router.include_router(analytics.router)
router.include_router(provider_ops.router)
router.include_router(reconciliation.router)
router.include_router(security.router)
