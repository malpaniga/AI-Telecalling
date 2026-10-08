"""Knowledge base and document repositories."""

from __future__ import annotations

import logging
from typing import Any, Optional

from pymongo import ASCENDING, DESCENDING

from backend.models.base import new_id, utcnow
from backend.models.knowledge import KnowledgeBase, KnowledgeBaseAgent, KnowledgeDocument
from backend.repositories.base import BaseRepository

log = logging.getLogger("repo.knowledge")


class KnowledgeBaseRepository(BaseRepository):
    collection_name = "knowledge_bases"
    model_class = KnowledgeBase

    async def create(
        self,
        organization_id: str,
        name: str,
        description: str = "",
        tags: Optional[list] = None,
    ) -> KnowledgeBase:
        kb = KnowledgeBase(
            _id=new_id(),
            organization_id=organization_id,
            name=name,
            description=description,
            tags=tags or [],
        )
        await self.insert(kb)
        return kb

    async def get_for_org(self, kb_id: str, organization_id: str) -> Optional[KnowledgeBase]:
        return await self.find_one({"_id": kb_id, "organization_id": organization_id})

    async def list_for_org(self, organization_id: str) -> list[KnowledgeBase]:
        return await self.find_many(
            {"organization_id": organization_id, "is_active": True},
            sort=[("name", ASCENDING)],
        )

    async def increment_document_count(self, kb_id: str, delta: int = 1) -> bool:
        result = await self.col.update_one(
            {"_id": kb_id},
            {"$inc": {"document_count": delta}, "$set": {"updated_at": utcnow()}},
        )
        return result.modified_count > 0


class KnowledgeDocumentRepository(BaseRepository):
    collection_name = "knowledge_documents"
    model_class = KnowledgeDocument

    async def create(
        self,
        organization_id: str,
        knowledge_base_id: str,
        title: str,
        content: str,
        document_type: str = "general",
        keywords: Optional[list] = None,
        tags: Optional[list] = None,
        source: str = "manual",
        created_by: Optional[str] = None,
        custom_fields: Optional[dict] = None,
    ) -> KnowledgeDocument:
        doc = KnowledgeDocument(
            _id=new_id(),
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            title=title,
            content=content,
            document_type=document_type,
            keywords=keywords or _extract_keywords(title, content),
            tags=tags or [],
            source=source,
            last_edited_by=created_by,
            last_edited_at=utcnow(),
            custom_fields=custom_fields or {},
        )
        await self.insert(doc)
        return doc

    async def get_for_org(
        self, doc_id: str, organization_id: str
    ) -> Optional[KnowledgeDocument]:
        return await self.find_one({
            "_id": doc_id,
            "organization_id": organization_id,
            "is_active": True,
        })

    async def list_for_kb(
        self,
        knowledge_base_id: str,
        organization_id: str,
        document_type: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[KnowledgeDocument]:
        query: dict = {
            "knowledge_base_id": knowledge_base_id,
            "organization_id": organization_id,
            "is_active": True,
        }
        if document_type:
            query["document_type"] = document_type
        return await self.find_many(
            query,
            sort=[("title", ASCENDING)],
            limit=limit,
            skip=skip,
        )

    async def search(
        self,
        organization_id: str,
        query_text: str,
        knowledge_base_ids: Optional[list[str]] = None,
        limit: int = 10,
    ) -> list[KnowledgeDocument]:
        """MVP text search: keyword matching on title, content, keywords list.
        No vector embeddings — simple case-insensitive text search.
        """
        import re
        escaped = re.escape(query_text.strip())
        text_filter: dict = {
            "$or": [
                {"title": {"$regex": escaped, "$options": "i"}},
                {"content": {"$regex": escaped, "$options": "i"}},
                {"keywords": {"$elemMatch": {"$regex": escaped, "$options": "i"}}},
            ]
        }
        query: dict = {
            "organization_id": organization_id,
            "is_active": True,
            **text_filter,
        }
        if knowledge_base_ids:
            query["knowledge_base_id"] = {"$in": knowledge_base_ids}
        return await self.find_many(query, sort=[("title", ASCENDING)], limit=limit)

    async def create_version(
        self,
        doc_id: str,
        organization_id: str,
        new_content: str,
        new_title: Optional[str] = None,
        edited_by: Optional[str] = None,
    ) -> Optional[KnowledgeDocument]:
        """Create a new version of a document. Old version is kept but deactivated."""
        old = await self.get_for_org(doc_id, organization_id)
        if old is None:
            return None

        # Deactivate old version
        await self.update_by_id(doc_id, {"is_active": False})

        # Create new version
        new_doc = KnowledgeDocument(
            _id=new_id(),
            organization_id=organization_id,
            knowledge_base_id=old.knowledge_base_id,
            title=new_title or old.title,
            content=new_content,
            document_type=old.document_type,
            keywords=_extract_keywords(new_title or old.title, new_content),
            tags=old.tags,
            source=old.source,
            version=old.version + 1,
            previous_version_id=doc_id,
            last_edited_by=edited_by,
            last_edited_at=utcnow(),
            custom_fields=old.custom_fields,
        )
        await self.insert(new_doc)
        return new_doc

    async def delete_for_org(self, doc_id: str, organization_id: str) -> bool:
        result = await self.col.update_one(
            {"_id": doc_id, "organization_id": organization_id},
            {"$set": {"is_active": False, "updated_at": utcnow()}},
        )
        return result.modified_count > 0


class KnowledgeBaseAgentRepository(BaseRepository):
    collection_name = "knowledge_base_agents"
    model_class = KnowledgeBaseAgent

    async def associate(
        self,
        organization_id: str,
        knowledge_base_id: str,
        agent_id: str,
        priority: int = 0,
    ) -> KnowledgeBaseAgent:
        # Check if already associated
        existing = await self.find_one({
            "organization_id": organization_id,
            "knowledge_base_id": knowledge_base_id,
            "agent_id": agent_id,
        })
        if existing:
            return existing
        assoc = KnowledgeBaseAgent(
            _id=new_id(),
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            agent_id=agent_id,
            priority=priority,
        )
        await self.insert(assoc)
        return assoc

    async def disassociate(
        self,
        organization_id: str,
        knowledge_base_id: str,
        agent_id: str,
    ) -> bool:
        result = await self.col.delete_one({
            "organization_id": organization_id,
            "knowledge_base_id": knowledge_base_id,
            "agent_id": agent_id,
        })
        return result.deleted_count > 0

    async def get_kb_ids_for_agent(
        self, agent_id: str, organization_id: str
    ) -> list[str]:
        docs = await self.find_many(
            {"agent_id": agent_id, "organization_id": organization_id},
            sort=[("priority", ASCENDING)],
        )
        return [d.knowledge_base_id for d in docs]

    async def get_agents_for_kb(
        self, knowledge_base_id: str, organization_id: str
    ) -> list[str]:
        docs = await self.find_many({
            "knowledge_base_id": knowledge_base_id,
            "organization_id": organization_id,
        })
        return [d.agent_id for d in docs]


def _extract_keywords(title: str, content: str, max_words: int = 20) -> list[str]:
    """Extract simple keywords from title and content (MVP: top unique words)."""
    import re
    text = f"{title} {content}".lower()
    words = re.findall(r"\b[a-zA-Z\u0900-\u097F]{3,}\b", text)  # 3+ char, includes Devanagari
    # Remove common stop words
    stop = {"the", "and", "for", "are", "this", "that", "with", "from",
            "have", "will", "your", "our", "can", "not", "but", "what"}
    seen: set[str] = set()
    result = []
    for w in words:
        if w not in stop and w not in seen:
            seen.add(w)
            result.append(w)
        if len(result) >= max_words:
            break
    return result
