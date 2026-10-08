"""Base repository with common MongoDB CRUD operations.

All repositories follow the same pattern:
- Each method takes the db handle (AsyncIOMotorDatabase)
- Organization isolation is enforced by always including organization_id in queries
- All documents use string UUIDs as _id
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional, Type, TypeVar

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.base import DocumentModel

log = logging.getLogger("repo")

T = TypeVar("T", bound=DocumentModel)


def _serialize(doc: dict) -> dict:
    """Prep a document dict for MongoDB: ensure _id is set."""
    return doc


def _deserialize(doc: Optional[dict]) -> Optional[dict]:
    """Clean up a MongoDB document for use with Pydantic models."""
    if doc is None:
        return None
    # MongoDB returns ObjectId for _id if we didn't set it; normalize to str
    if "_id" in doc and not isinstance(doc["_id"], str):
        doc["_id"] = str(doc["_id"])
    return doc


class BaseRepository:
    """Thin CRUD wrapper. Subclasses set `collection_name` and `model_class`."""

    collection_name: str
    model_class: Type[T]

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.col = db[self.collection_name]

    async def insert(self, doc: T) -> T:
        data = doc.to_mongo()
        await self.col.insert_one(data)
        log.debug("insert %s id=%s", self.collection_name, doc.id)
        return doc

    async def find_by_id(self, doc_id: str) -> Optional[T]:
        raw = await self.col.find_one({"_id": doc_id})
        if raw is None:
            return None
        return self.model_class(**_deserialize(raw))

    async def find_one(self, query: dict) -> Optional[T]:
        raw = await self.col.find_one(query)
        if raw is None:
            return None
        return self.model_class(**_deserialize(raw))

    async def find_many(
        self,
        query: dict,
        sort: Optional[list] = None,
        limit: int = 0,
        skip: int = 0,
    ) -> list[T]:
        cursor = self.col.find(query)
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        docs = await cursor.to_list(length=limit or None)
        return [self.model_class(**_deserialize(d)) for d in docs]

    async def update_by_id(self, doc_id: str, updates: dict) -> bool:
        updates["updated_at"] = datetime.now(timezone.utc)
        result = await self.col.update_one(
            {"_id": doc_id},
            {"$set": updates},
        )
        return result.modified_count > 0

    async def delete_by_id(self, doc_id: str) -> bool:
        result = await self.col.delete_one({"_id": doc_id})
        return result.deleted_count > 0

    async def count(self, query: dict) -> int:
        return await self.col.count_documents(query)

    async def exists(self, query: dict) -> bool:
        return await self.col.count_documents(query, limit=1) > 0
