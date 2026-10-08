"""Voice profile and version repositories."""

import logging
from typing import Any, Optional

from pymongo import ASCENDING, DESCENDING

from backend.models.base import new_id, utcnow
from backend.models.voice_profile import VoiceProfile, VoiceProfileVersion
from backend.repositories.base import BaseRepository

log = logging.getLogger("repo.voice_profile")


class VoiceProfileRepository(BaseRepository):
    collection_name = "voice_profiles"
    model_class = VoiceProfile

    async def create(
        self,
        display_name: str,
        language: str,
        description: str = "",
        organization_id: Optional[str] = None,
        is_platform: bool = True,
    ) -> VoiceProfile:
        profile = VoiceProfile(
            _id=new_id(),
            display_name=display_name,
            language=language,
            description=description,
            organization_id=organization_id,
            is_platform=is_platform,
            is_active=True,
        )
        await self.insert(profile)
        log.info("voice profile created id=%s name=%s lang=%s", profile.id, display_name, language)
        return profile

    async def list_for_customer(self, organization_id: str) -> list[VoiceProfile]:
        """Return platform profiles + org's own profiles. Active only."""
        return await self.find_many(
            {
                "is_active": True,
                "$or": [
                    {"is_platform": True},
                    {"organization_id": organization_id},
                ],
            },
            sort=[("display_name", ASCENDING)],
        )

    async def list_platform(self) -> list[VoiceProfile]:
        return await self.find_many(
            {"is_platform": True, "is_active": True},
            sort=[("display_name", ASCENDING)],
        )

    async def list_all_admin(
        self,
        include_inactive: bool = False,
        language: Optional[str] = None,
    ) -> list[VoiceProfile]:
        query: dict = {} if include_inactive else {"is_active": True}
        if language:
            query["language"] = language
        return await self.find_many(query, sort=[("display_name", ASCENDING)])

    async def set_active_version(
        self, profile_id: str, version: int, version_id: str
    ) -> bool:
        return await self.update_by_id(profile_id, {
            "active_version": version,
            "active_version_id": version_id,
        })

    async def deactivate(self, profile_id: str) -> bool:
        return await self.update_by_id(profile_id, {"is_active": False})


class VoiceProfileVersionRepository(BaseRepository):
    collection_name = "voice_profile_versions"
    model_class = VoiceProfileVersion

    async def next_version_number(self, profile_id: str) -> int:
        existing = await self.find_many(
            {"voice_profile_id": profile_id},
            sort=[("version", DESCENDING)],
            limit=1,
        )
        return (existing[0].version if existing else 0) + 1

    async def create_version(
        self,
        profile_id: str,
        routes: dict[str, Any],
        description: str = "",
    ) -> VoiceProfileVersion:
        """Create a new immutable version. Routes contain internal provider config."""
        version_number = await self.next_version_number(profile_id)
        version = VoiceProfileVersion(
            _id=new_id(),
            voice_profile_id=profile_id,
            version=version_number,
            routes=routes,
            description=description,
            is_published=True,
        )
        await self.insert(version)
        log.info("voice profile version created profile=%s version=%d", profile_id, version_number)
        return version

    async def list_for_profile(self, profile_id: str) -> list[VoiceProfileVersion]:
        return await self.find_many(
            {"voice_profile_id": profile_id},
            sort=[("version", DESCENDING)],
        )

    async def get_version(
        self, profile_id: str, version_number: int
    ) -> Optional[VoiceProfileVersion]:
        return await self.find_one({
            "voice_profile_id": profile_id,
            "version": version_number,
        })

    async def deprecate(self, version_id: str) -> bool:
        return await self.update_by_id(version_id, {
            "deprecated_at": utcnow(),
        })
