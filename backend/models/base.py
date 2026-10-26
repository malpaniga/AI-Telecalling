"""Base Pydantic models for MongoDB documents.

MongoDB uses _id (ObjectId) as the primary key. We expose it as `id` (str) in
all API responses. Documents use string UUIDs generated in Python for portability.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


def new_id() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DocumentModel(BaseModel):
    """Base for MongoDB documents. `id` maps to the document's `_id` field."""

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    id: str = Field(default_factory=new_id, alias="_id")

    def to_mongo(self) -> dict[str, Any]:
        """Serialize for MongoDB insertion (use `_id`, not `id`)."""
        data = self.model_dump(by_alias=True)
        return data

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "DocumentModel":
        """Deserialize from a MongoDB document."""
        if doc is None:
            return None
        return cls(**doc)


class TimestampedModel(DocumentModel):
    """DocumentModel with created_at and updated_at."""
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
