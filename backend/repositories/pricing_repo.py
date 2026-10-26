"""Repositories for ProviderRateCard and PricingSettings."""

from datetime import datetime
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReplaceOne

from backend.models.base import utcnow
from backend.models.pricing import ProviderRateCard, PricingSettings
from backend.repositories.base import BaseRepository, _deserialize


class ProviderRateCardRepository(BaseRepository):
    collection_name = "provider_rate_cards"
    model_class = ProviderRateCard

    async def get_by_provider_and_model(
        self, capability: str, provider_name: str, model_id: str
    ) -> Optional[ProviderRateCard]:
        raw = await self.col.find_one({
            "capability": capability,
            "provider_name": provider_name.lower(),
            "model_id": model_id.lower(),
        })
        if not raw:
            # Fallback by provider_name and capability
            raw = await self.col.find_one({
                "capability": capability,
                "provider_name": provider_name.lower(),
            })
        return self.model_class(**_deserialize(raw)) if raw else None

    async def list_all(self, capability: Optional[str] = None) -> List[ProviderRateCard]:
        query = {"capability": capability} if capability else {}
        cursor = self.col.find(query).sort("provider_name", 1)
        results = []
        async for doc in cursor:
            results.append(self.model_class(**_deserialize(doc)))
        return results

    async def upsert_rate_card(self, card: ProviderRateCard) -> ProviderRateCard:
        data = card.to_mongo()
        doc_id = data.pop("_id", card.id)
        data.pop("created_at", None)
        data["updated_at"] = utcnow()
        await self.col.update_one(
            {
                "capability": card.capability,
                "provider_name": card.provider_name.lower(),
                "model_id": card.model_id.lower(),
            },
            {
                "$set": data,
                "$setOnInsert": {
                    "_id": doc_id,
                    "created_at": card.created_at or utcnow(),
                },
            },
            upsert=True,
        )
        return card


class PricingSettingsRepository(BaseRepository):
    collection_name = "pricing_settings"
    model_class = PricingSettings

    async def get_settings(self) -> PricingSettings:
        raw = await self.col.find_one({"_id": "global_pricing_settings"})
        if not raw:
            settings = PricingSettings()
            await self.col.insert_one(settings.to_mongo())
            return settings
        return self.model_class(**_deserialize(raw))

    async def update_settings(self, updates: dict) -> PricingSettings:
        updates["updated_at"] = utcnow()
        await self.col.update_one(
            {"_id": "global_pricing_settings"},
            {"$set": updates},
            upsert=True,
        )
        return await self.get_settings()
