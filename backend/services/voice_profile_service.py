from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from backend.repositories.voice_profile_repo import VoiceProfileRepository, VoiceProfileVersionRepository

def _customer_view(profile):
    return {'id':profile.id,'display_name':profile.display_name,'language':profile.language,'active_version':profile.active_version,'is_active':profile.is_active}

class VoiceProfileService:
    def __init__(self, db: AsyncIOMotorDatabase): self.profiles=VoiceProfileRepository(db); self.versions=VoiceProfileVersionRepository(db)
    async def create_profile(self, display_name: str, language: str, organization_id: Optional[str]=None):
        return await self.profiles.create(display_name=display_name, language=language, organization_id=organization_id, is_platform=organization_id is None)
    async def create_version(self, profile_id: str, routes: dict):
        profile=await self.profiles.find_by_id(profile_id)
        if not profile: raise ValueError('Voice profile not found')
        version=await self.versions.create_version(profile_id, routes)
        await self.profiles.set_active_version(profile_id, version.version, version.id)
        return version
    async def update_version_routes(self, version_id: str, routes: dict):
        raise ValueError('Voice profile versions are immutable; create a new version')
    async def get_customer_profile(self, profile_id: str, organization_id: str):
        profile=await self.profiles.find_by_id(profile_id)
        if not profile or not profile.is_active or (not profile.is_platform and profile.organization_id != organization_id): return None
        return _customer_view(profile)
    async def list_customer_profiles(self, organization_id: str): return [_customer_view(p) for p in await self.profiles.list_for_customer(organization_id)]
