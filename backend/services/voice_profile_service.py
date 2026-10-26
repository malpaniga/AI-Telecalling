from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from backend.repositories.voice_profile_repo import VoiceProfileRepository, VoiceProfileVersionRepository

DEFAULT_PLATFORM_VOICES = [
    {
        "display_name": "Chitra AI Voice",
        "language": "mr-IN",
        "description": "Warm & professional Indian conversational voice (Chitra / Chaitra)",
        "routes": {
            "telephony": {"provider": "mock", "provider_resource_id": "default"},
            "stt": {"provider": "sarvam", "provider_resource_id": "saaras:v4-turbo", "provider_language": "mr-IN"},
            "llm": {"provider": "gemini", "provider_resource_id": "gemini-2.0-flash"},
            "tts": {"provider": "sarvam", "provider_resource_id": "chaitra_hi_customer", "provider_language": "mr-IN"},
        },
    },

    {
        "display_name": "Marathi AI Voice",
        "language": "mr-IN",
        "description": "Natural conversational Marathi AI voice (Priya / Ishita)",
        "routes": {
            "telephony": {"provider": "mock", "provider_resource_id": "default"},
            "stt": {"provider": "sarvam", "provider_resource_id": "saaras:v1", "provider_language": "mr-IN"},
            "llm": {"provider": "gemini", "provider_resource_id": "gemini-2.0-flash"},
            "tts": {"provider": "sarvam", "provider_resource_id": "ishita_mr_conversational", "provider_language": "mr-IN"},
        },
    },
    {
        "display_name": "Hindi AI Voice",
        "language": "hi-IN",
        "description": "Natural conversational Hindi AI voice (Sneha / Shweta)",
        "routes": {
            "telephony": {"provider": "mock", "provider_resource_id": "default"},
            "stt": {"provider": "sarvam", "provider_resource_id": "saaras:v1", "provider_language": "hi-IN"},
            "llm": {"provider": "gemini", "provider_resource_id": "gemini-2.0-flash"},
            "tts": {"provider": "sarvam", "provider_resource_id": "shweta_hi_conversational", "provider_language": "hi-IN"},
        },
    },
    {
        "display_name": "English AI Voice",
        "language": "en-IN",
        "description": "Natural Indian English conversational voice (Rohan / Aarav)",
        "routes": {
            "telephony": {"provider": "mock", "provider_resource_id": "default"},
            "stt": {"provider": "sarvam", "provider_resource_id": "saaras:v1", "provider_language": "en-IN"},
            "llm": {"provider": "gemini", "provider_resource_id": "gemini-2.0-flash"},
            "tts": {"provider": "sarvam", "provider_resource_id": "rohan_en_conversational", "provider_language": "en-IN"},
        },
    },
]


async def seed_default_voice_profiles(db: AsyncIOMotorDatabase) -> list:
    """Seed default platform voice profiles if none exist. Idempotent."""
    svc = VoiceProfileService(db)
    existing = await svc.profiles.list_platform()
    existing_names = {p.display_name for p in existing}
    seeded = []
    for item in DEFAULT_PLATFORM_VOICES:
        if item["display_name"] not in existing_names:
            profile = await svc.create_profile(
                display_name=item["display_name"],
                language=item["language"],
            )
            await svc.create_version(profile.id, item["routes"])
            seeded.append(profile)
    return seeded


def _customer_view(profile):
    return {
        'id': profile.id,
        'display_name': profile.display_name,
        'language': profile.language,
        'active_version': profile.active_version,
        'is_active': profile.is_active,
    }


class VoiceProfileService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.profiles = VoiceProfileRepository(db)
        self.versions = VoiceProfileVersionRepository(db)

    async def create_profile(self, display_name: str, language: str, organization_id: Optional[str] = None):
        return await self.profiles.create(
            display_name=display_name,
            language=language,
            organization_id=organization_id,
            is_platform=organization_id is None,
        )

    async def create_version(self, profile_id: str, routes: dict):
        profile = await self.profiles.find_by_id(profile_id)
        if not profile:
            raise ValueError('Voice profile not found')
        version = await self.versions.create_version(profile_id, routes)
        await self.profiles.set_active_version(profile_id, version.version, version.id)
        return version

    async def update_version_routes(self, version_id: str, routes: dict):
        raise ValueError('Voice profile versions are immutable; create a new version')

    async def get_customer_profile(self, profile_id: str, organization_id: str):
        profile = await self.profiles.find_by_id(profile_id)
        if not profile or not profile.is_active or (not profile.is_platform and profile.organization_id != organization_id):
            return None
        return _customer_view(profile)

    async def list_customer_profiles(self, organization_id: str):
        profiles = await self.profiles.list_for_customer(organization_id)
        if not profiles:
            await seed_default_voice_profiles(self.db)
            profiles = await self.profiles.list_for_customer(organization_id)
        return [_customer_view(p) for p in profiles]
