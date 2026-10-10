"""Repository classes for the AI Models Directory.

Three repositories:
  AIModelCatalogueRepo     — ai_model_catalogue collection
  ProviderConfigurationRepo — provider_configurations collection
  ProviderCredentialRepo   — provider_credentials collection

IMPORTANT: ProviderCredentialRepo never decrypts credentials.
Callers must strip encrypted_value before returning data to the browser.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from pymongo import ASCENDING

from backend.models.base import new_id
from backend.models.model_directory import (
    AIModelCatalogue,
    ProviderConfiguration,
    ProviderCredential,
)
from backend.repositories.base import BaseRepository, _deserialize

log = logging.getLogger("repo.model_directory")


class AIModelCatalogueRepo(BaseRepository):
    collection_name = "ai_model_catalogue"
    model_class = AIModelCatalogue

    async def find_by_capability(self, capability: str) -> list[AIModelCatalogue]:
        return await self.find_many({"capability": capability})

    async def find_by_status(self, status: str) -> list[AIModelCatalogue]:
        return await self.find_many({"implementation_status": status})

    async def search(self, query: str) -> list[AIModelCatalogue]:
        """Case-insensitive regex search across provider_name, model_id, and notes."""
        regex = {"$regex": query, "$options": "i"}
        return await self.find_many({
            "$or": [
                {"provider_name": regex},
                {"model_id": regex},
                {"notes": regex},
            ]
        })

    async def upsert_by_provider_model(self, doc: AIModelCatalogue) -> AIModelCatalogue:
        """Insert or update by (provider_name, model_id). Idempotent."""
        from datetime import datetime, timezone
        data = doc.to_mongo()
        # On update, always refresh updated_at; never overwrite created_at if already set
        update_fields = {k: v for k, v in data.items() if k not in ("_id", "created_at")}
        update_fields["updated_at"] = datetime.now(timezone.utc)
        result = await self.col.update_one(
            {"provider_name": doc.provider_name, "model_id": doc.model_id},
            {
                "$set": update_fields,
                "$setOnInsert": {"_id": doc.id, "created_at": doc.created_at},
            },
            upsert=True,
        )
        # Reload to return the persisted document
        raw = await self.col.find_one(
            {"provider_name": doc.provider_name, "model_id": doc.model_id}
        )
        return AIModelCatalogue(**_deserialize(raw))


class ProviderConfigurationRepo(BaseRepository):
    collection_name = "provider_configurations"
    model_class = ProviderConfiguration

    async def find_active_for_capability(
        self, capability: str
    ) -> Optional[ProviderConfiguration]:
        """Return the single active config for a capability, or None."""
        return await self.find_one({"capability": capability, "is_active": True})

    async def find_all_for_capability(
        self, capability: str
    ) -> list[ProviderConfiguration]:
        return await self.find_many({"capability": capability})

    async def deactivate_all_for_capability(self, capability: str) -> int:
        """Set is_active=False on all configs for the given capability.
        Returns the number of modified documents."""
        result = await self.col.update_many(
            {"capability": capability, "is_active": True},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count

    async def find_by_id(self, config_id: str) -> Optional[ProviderConfiguration]:
        return await self.find_one({"_id": config_id})


class ProviderCredentialRepo(BaseRepository):
    collection_name = "provider_credentials"
    model_class = ProviderCredential

    async def find_by_provider(self, provider_name: str) -> list[ProviderCredential]:
        """Return all credential records for a provider (including rotated history)."""
        return await self.find_many({"provider_name": provider_name})

    async def find_current(self, provider_name: str) -> Optional[ProviderCredential]:
        """Return the current (non-rotated) credential for a provider, or None."""
        return await self.find_one(
            {"provider_name": provider_name, "rotated_at": None}
        )

    async def store_credential(self, cred: ProviderCredential) -> ProviderCredential:
        """Persist a new ProviderCredential document. Returns the saved document."""
        return await self.insert(cred)

    async def mark_rotated(self, provider_name: str) -> int:
        """Set rotated_at=now on all non-rotated credentials for the provider.
        Call before storing a new credential to make the rotation atomic."""
        result = await self.col.update_many(
            {"provider_name": provider_name, "rotated_at": None},
            {"$set": {
                "rotated_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }},
        )
        return result.modified_count

    async def delete_by_provider(self, provider_name: str) -> int:
        """Delete ALL credential records for a provider (including history)."""
        result = await self.col.delete_many({"provider_name": provider_name})
        return result.deleted_count
