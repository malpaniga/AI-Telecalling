"""Transcript repository."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from pymongo import DESCENDING

from backend.models.base import new_id, utcnow
from backend.models.transcript import Transcript, Turn
from backend.repositories.base import BaseRepository

log = logging.getLogger("repo.transcript")


class TranscriptRepository(BaseRepository):
    collection_name = "transcripts"
    model_class = Transcript

    async def create_or_get(
        self,
        organization_id: str,
        call_id: str,
        lead_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        language: str = "en-IN",
    ) -> Transcript:
        """Get existing transcript or create one. Idempotent."""
        existing = await self.find_one({"call_id": call_id,
                                        "organization_id": organization_id})
        if existing:
            return existing
        t = Transcript(
            _id=new_id(),
            organization_id=organization_id,
            call_id=call_id,
            lead_id=lead_id,
            campaign_id=campaign_id,
            language=language,
        )
        await self.insert(t)
        return t

    async def get_for_call(
        self, call_id: str, organization_id: str
    ) -> Optional[Transcript]:
        return await self.find_one({"call_id": call_id,
                                    "organization_id": organization_id})

    async def add_turns(
        self,
        transcript_id: str,
        turns: list[dict],
    ) -> bool:
        """Append turns to transcript and update count."""
        turn_docs = [Turn(**t).to_mongo() for t in turns]
        result = await self.col.update_one(
            {"_id": transcript_id},
            {
                "$push": {"turns": {"$each": turn_docs}},
                "$inc": {"turn_count": len(turn_docs)},
                "$set": {"updated_at": utcnow()},
            },
        )
        return result.modified_count > 0

    async def set_processing_result(
        self,
        transcript_id: str,
        summary: Optional[str],
        qualification: dict,
        score: int,
        outcome: Optional[str],
        status: str = "completed",
        error: Optional[str] = None,
    ) -> bool:
        return await self.update_by_id(transcript_id, {
            "summary": summary,
            "qualification": qualification,
            "score": score,
            "outcome": outcome,
            "processing_status": status,
            "processed_at": utcnow(),
            "processing_error": error,
        })

    async def list_for_org(
        self,
        organization_id: str,
        campaign_id: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list[Transcript]:
        query: dict = {"organization_id": organization_id}
        if campaign_id:
            query["campaign_id"] = campaign_id
        return await self.find_many(
            query,
            sort=[("created_at", DESCENDING)],
            limit=limit,
            skip=skip,
        )
