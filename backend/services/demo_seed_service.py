"""Demo Mode seeding service.

When DEMO_MODE=true, seeds a complete demo environment so the full
SaaS workflow can be tested without any paid external providers.

Seeds:
  - Demo organization
  - Demo platform admin user
  - Growth plan subscription (activated)
  - 2000 calling credits
  - Marathi AI Voice profile (version 1, mock provider routes)
  - Demo phone number (+911800DEMO001)
  - Generic agent (Solar template, Marathi AI Voice)
  - 20 demo leads (mix of Indian mobile numbers)
  - Demo campaign (draft, ready to start)

All sensitive fields use mock/demo values — no real provider IDs.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.base import new_id, utcnow

log = logging.getLogger("service.demo_seed")

DEMO_ORG_EMAIL = "demo@telecalling-saas.com"
DEMO_USER_EMAIL = "demo-user@telecalling-saas.com"
DEMO_ADMIN_EMAIL = "demo-admin@telecalling-saas.com"

DEMO_LEADS = [
    {"name": "Priya Sharma",    "phone": "+919876543210", "email": "priya@demo.com",    "city": "Mumbai"},
    {"name": "Rahul Verma",     "phone": "+919865432109", "email": "rahul@demo.com",    "city": "Delhi"},
    {"name": "Anita Patel",     "phone": "+919854321098", "email": "anita@demo.com",    "city": "Ahmedabad"},
    {"name": "Suresh Kumar",    "phone": "+919843210987", "email": "suresh@demo.com",   "city": "Bangalore"},
    {"name": "Meena Joshi",     "phone": "+919832109876", "email": "meena@demo.com",    "city": "Pune"},
    {"name": "Vikram Singh",    "phone": "+919821098765", "email": "vikram@demo.com",   "city": "Jaipur"},
    {"name": "Kavita Nair",     "phone": "+919810987654", "email": "kavita@demo.com",   "city": "Chennai"},
    {"name": "Arun Gupta",      "phone": "+919809876543", "email": "arun@demo.com",     "city": "Hyderabad"},
    {"name": "Sneha Desai",     "phone": "+919798765432", "email": "sneha@demo.com",    "city": "Surat"},
    {"name": "Mohan Rao",       "phone": "+919787654321", "email": "mohan@demo.com",    "city": "Kolkata"},
    {"name": "Deepa Iyer",      "phone": "+919776543210", "email": "deepa@demo.com",    "city": "Coimbatore"},
    {"name": "Rajesh Pillai",   "phone": "+919765432109", "email": "rajesh@demo.com",   "city": "Kochi"},
    {"name": "Sunita Mehta",    "phone": "+919754321098", "email": "sunita@demo.com",   "city": "Lucknow"},
    {"name": "Aditya Bose",     "phone": "+919743210987", "email": "aditya@demo.com",   "city": "Kolkata"},
    {"name": "Pooja Saxena",    "phone": "+919732109876", "email": "pooja@demo.com",    "city": "Agra"},
    {"name": "Ravi Thakur",     "phone": "+919721098765", "email": "ravi@demo.com",     "city": "Bhopal"},
    {"name": "Geeta Mishra",    "phone": "+919710987654", "email": "geeta@demo.com",    "city": "Varanasi"},
    {"name": "Kiran Reddy",     "phone": "+919709876543", "email": "kiran@demo.com",    "city": "Visakhapatnam"},
    {"name": "Sanjay Yadav",    "phone": "+919698765432", "email": "sanjay@demo.com",   "city": "Indore"},
    {"name": "Leela Krishnan",  "phone": "+919687654321", "email": "leela@demo.com",    "city": "Mysore"},
]


class DemoSeedService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def is_seeded(self) -> bool:
        """Check if demo environment is already seeded."""
        return bool(await self.db["organizations"].find_one(
            {"email": DEMO_ORG_EMAIL}
        ))

    async def seed_all(self, force: bool = False) -> dict:
        """Seed the complete demo environment. Idempotent unless force=True."""
        if await self.is_seeded() and not force:
            log.info("Demo environment already seeded — skipping")
            return {"status": "already_seeded", "seeded": False}

        log.info("Seeding demo environment...")
        result: dict = {}

        org = await self._seed_organization(result)
        await self._seed_users(org["id"], result)
        plan = await self._seed_subscription(org["id"], result)
        await self._seed_credits(org["id"], result)
        voice_profile = await self._seed_voice_profile(result)
        phone = await self._seed_phone_number(org["id"], result)
        agent = await self._seed_agent(org["id"], voice_profile["id"], result)
        await self._seed_leads(org["id"], result)
        await self._seed_campaign(org["id"], agent["id"], voice_profile["id"],
                                   phone["id"], phone["number"], result)

        log.info("Demo environment seeded: %s", result)
        return {"status": "seeded", "seeded": True, **result}

    async def _seed_organization(self, result: dict) -> dict:
        # Remove existing demo org if re-seeding
        await self.db["organizations"].delete_many({"email": DEMO_ORG_EMAIL})

        now = utcnow()
        org_id = new_id()
        org = {
            "_id": org_id,
            "name": "Demo Company",
            "slug": "demo-company",
            "email": DEMO_ORG_EMAIL,
            "phone": "+911800123000",
            "status": "active",
            "is_verified": True,
            "max_concurrent_calls": 5,
            "max_campaigns": 10,
            "max_agents": 5,
            "max_leads_per_campaign": 5000,
            "created_at": now, "updated_at": now,
        }
        await self.db["organizations"].insert_one(org)
        result["organization_id"] = org_id
        result["organization_name"] = "Demo Company"
        log.info("Demo org created: %s", org_id)
        return {"id": org_id}

    async def _seed_users(self, org_id: str, result: dict) -> None:
        from backend.repositories.user_repo import hash_password
        now = utcnow()

        # Demo org owner
        user_id = new_id()
        await self.db["users"].insert_one({
            "_id": user_id,
            "organization_id": org_id,
            "email": DEMO_USER_EMAIL,
            "password_hash": hash_password("Demo@1234"),
            "role": "organization_owner",
            "first_name": "Demo",
            "last_name": "User",
            "is_active": True,
            "is_email_verified": True,
            "created_at": now, "updated_at": now,
        })

        # Demo platform admin
        admin_id = new_id()
        await self.db["users"].insert_one({
            "_id": admin_id,
            "organization_id": None,
            "email": DEMO_ADMIN_EMAIL,
            "password_hash": hash_password("DemoAdmin@1234"),
            "role": "platform_admin",
            "first_name": "Demo",
            "last_name": "Admin",
            "is_active": True,
            "is_email_verified": True,
            "created_at": now, "updated_at": now,
        })

        result["demo_user_email"] = DEMO_USER_EMAIL
        result["demo_user_password"] = "Demo@1234"
        result["demo_admin_email"] = DEMO_ADMIN_EMAIL
        result["demo_admin_password"] = "DemoAdmin@1234"
        log.info("Demo users created")

    async def _seed_subscription(self, org_id: str, result: dict) -> dict:
        from backend.repositories.subscription_repo import SubscriptionPlanRepository
        from backend.services.subscription_service import SubscriptionService
        from datetime import timedelta

        # Ensure Growth plan exists
        plan_repo = SubscriptionPlanRepository(self.db)
        growth = await plan_repo.find_by_slug("growth")
        if growth is None:
            from backend.services.subscription_service import seed_default_plans
            await seed_default_plans(self.db)
            growth = await plan_repo.find_by_slug("growth")

        svc = SubscriptionService(self.db)
        sub = await svc.activate_plan(
            organization_id=org_id,
            plan_id=growth.id,
            billing_cycle="monthly",
            payment_id="demo_payment_001",
        )
        result["subscription_plan"] = "growth"
        result["subscription_id"] = sub.id
        log.info("Demo subscription activated: growth plan")
        return {"id": growth.id}

    async def _seed_credits(self, org_id: str, result: dict) -> None:
        from backend.services.wallet_service import WalletService
        svc = WalletService(self.db)
        await svc.grant_bonus(
            org_id, 2000,
            "Welcome bonus — 2000 demo calling credits",
            validity_days=365,
            created_by="demo_seed",
            idempotency_key=f"demo_credits:{org_id}",
        )
        result["calling_credits"] = 2000
        log.info("Demo credits granted: 2000")

    async def _seed_voice_profile(self, result: dict) -> dict:
        now = utcnow()
        profile_id = new_id()
        await self.db["voice_profiles"].insert_one({
            "_id": profile_id,
            "display_name": "Marathi AI Voice",
            "language": "mr-IN",
            "description": "Natural Marathi AI voice for calling campaigns",
            "is_platform": True,
            "is_active": True,
            "active_version": 1,
            "active_version_id": None,
            "created_at": now, "updated_at": now,
        })

        # Version with mock provider routes (hidden from customers)
        version_id = new_id()
        await self.db["voice_profile_versions"].insert_one({
            "_id": version_id,
            "voice_profile_id": profile_id,
            "version": 1,
            "description": "Demo version with mock providers",
            "routes": {
                "telephony": {
                    "provider": "mock",
                    "provider_resource_id": "demo_telephony",
                    "provider_metadata": {},
                },
                "stt": {
                    "provider": "mock",
                    "provider_resource_id": "demo_stt_mr",
                    "provider_language": "mr-IN",
                },
                "llm": {
                    "provider": "mock",
                    "provider_resource_id": "demo_llm",
                },
                "tts": {
                    "provider": "mock",
                    "provider_resource_id": "demo_voice_marathi",
                    "provider_language": "mr-IN",
                },
            },
            "is_published": True,
            "created_at": now, "updated_at": now,
        })

        # Update profile with version reference
        await self.db["voice_profiles"].update_one(
            {"_id": profile_id},
            {"$set": {"active_version_id": version_id}},
        )

        result["voice_profile"] = "Marathi AI Voice"
        result["voice_profile_id"] = profile_id
        log.info("Demo voice profile created: Marathi AI Voice")
        return {"id": profile_id}

    async def _seed_phone_number(self, org_id: str, result: dict) -> dict:
        now = utcnow()
        pn_id = new_id()
        number = "+911800DEMO01"
        await self.db["phone_numbers"].insert_one({
            "_id": pn_id,
            "number": number,
            "display_name": "Demo Calling Number",
            "country_code": "IN",
            "number_type": "local",
            "can_voice": True, "can_sms": False, "can_whatsapp": False,
            "status": "assigned",
            "organization_id": org_id,
            "assigned_at": now,
            "provider": "mock",
            "provider_resource_id": "demo_number_001",
            "provider_metadata": {"demo": True},
            "rental_paise_per_month": 0,
            "created_at": now, "updated_at": now,
        })
        result["demo_phone_number"] = number
        result["phone_number_id"] = pn_id
        log.info("Demo phone number created: %s", number)
        return {"id": pn_id, "number": number}

    async def _seed_agent(
        self, org_id: str, voice_profile_id: str, result: dict
    ) -> dict:
        now = utcnow()

        # Ensure business templates exist
        from backend.services.agent_service import seed_templates
        await seed_templates(self.db)

        agent_id = new_id()
        await self.db["agents"].insert_one({
            "_id": agent_id,
            "organization_id": org_id,
            "name": "Demo Solar Qualifier",
            "description": "Demo AI agent for solar lead qualification",
            "template_slug": "solar",
            "voice_profile_id": voice_profile_id,
            "voice_profile_version": 1,
            "active_version": 1,
            "is_active": True,
            "created_at": now, "updated_at": now,
        })

        version_id = new_id()
        await self.db["agent_versions"].insert_one({
            "_id": version_id,
            "agent_id": agent_id,
            "version": 1,
            "status": "published",
            "description": "Demo configuration",
            "configuration": {
                "goal": "Qualify homeowners interested in solar panels",
                "tone": "warm_consultative",
                "primary_language": "mr-IN",
                "qualification_slots": ["monthly_bill", "roof_type", "home_ownership"],
            },
            "created_at": now, "updated_at": now,
        })

        await self.db["agents"].update_one(
            {"_id": agent_id},
            {"$set": {"active_version_id": version_id}},
        )

        result["agent_id"] = agent_id
        result["agent_name"] = "Demo Solar Qualifier"
        log.info("Demo agent created")
        return {"id": agent_id}

    async def _seed_leads(self, org_id: str, result: dict) -> None:
        now = utcnow()
        docs = []
        for i, lead in enumerate(DEMO_LEADS):
            docs.append({
                "_id": new_id(),
                "organization_id": org_id,
                "phone": lead["phone"],
                "name": lead["name"],
                "email": lead["email"],
                "status": "new",
                "score": 0,
                "qualification": {},
                "custom_fields": {"city": lead["city"]},
                "tags": ["demo"],
                "source": "demo_seed",
                "attempts": 0,
                "import_batch_id": "demo_batch",
                "created_at": now, "updated_at": now,
            })
        if docs:
            await self.db["leads"].insert_many(docs)
        result["leads_count"] = len(docs)
        log.info("Demo leads seeded: %d", len(docs))

    async def _seed_campaign(
        self,
        org_id: str,
        agent_id: str,
        voice_profile_id: str,
        phone_number_id: str,
        phone_number: str,
        result: dict,
    ) -> None:
        now = utcnow()
        campaign_id = new_id()
        await self.db["campaigns"].insert_one({
            "_id": campaign_id,
            "organization_id": org_id,
            "name": "Demo Solar Campaign",
            "description": "Demo campaign for testing the full calling workflow",
            "agent_id": agent_id,
            "agent_version": 1,
            "voice_profile_id": voice_profile_id,
            "voice_profile_version": 1,
            "calling_number_id": phone_number_id,
            "calling_number": phone_number,
            "status": "draft",
            "max_concurrent_calls": 2,
            "timezone": "Asia/Kolkata",
            "calling_hours": {
                "_id": new_id(),
                "start_time": "09:00",
                "end_time": "18:00",
                "days_of_week": [1, 2, 3, 4, 5],
                "created_at": now, "updated_at": now,
            },
            "retry_policy": {
                "_id": new_id(),
                "max_attempts": 3,
                "retry_delay_minutes": 60,
                "retry_on": ["no_answer", "busy"],
                "created_at": now, "updated_at": now,
            },
            "lead_filter": {"tags": "demo"},
            "total_leads": 20,
            "leads_dialed": 0,
            "leads_connected": 0,
            "leads_completed": 0,
            "created_by": "demo_seed",
            "created_at": now, "updated_at": now,
        })
        result["campaign_id"] = campaign_id
        result["campaign_name"] = "Demo Solar Campaign"
        log.info("Demo campaign created: %s", campaign_id)
