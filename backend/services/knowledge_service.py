"""Knowledge base service.

MVP scope (per spec): minimal, tenant-safe. No over-engineered RAG.

Key operations:
- Create/manage knowledge bases (org-scoped)
- Add/update/version documents
- Associate KBs with agents
- Simple text search across an agent's configured KBs
- get_context_for_agent() — retrieve relevant docs for AI injection
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.knowledge import KnowledgeBase, KnowledgeDocument
from backend.repositories.knowledge_repo import (
    KnowledgeBaseAgentRepository,
    KnowledgeBaseRepository,
    KnowledgeDocumentRepository,
)

log = logging.getLogger("service.knowledge")

# Max chars of knowledge context to inject per call (keeps LLM context manageable)
MAX_CONTEXT_CHARS = 4000
MAX_DOCS_PER_SEARCH = 5


class KnowledgeService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.kb_repo = KnowledgeBaseRepository(db)
        self.doc_repo = KnowledgeDocumentRepository(db)
        self.assoc_repo = KnowledgeBaseAgentRepository(db)

    # ---- Knowledge Base CRUD ----

    async def create_kb(
        self,
        organization_id: str,
        name: str,
        description: str = "",
        tags: Optional[list] = None,
    ) -> KnowledgeBase:
        return await self.kb_repo.create(
            organization_id, name, description, tags
        )

    async def get_kb(
        self, kb_id: str, organization_id: str
    ) -> Optional[KnowledgeBase]:
        return await self.kb_repo.get_for_org(kb_id, organization_id)

    async def list_kbs(self, organization_id: str) -> list[KnowledgeBase]:
        return await self.kb_repo.list_for_org(organization_id)

    async def delete_kb(self, kb_id: str, organization_id: str) -> bool:
        # Verify ownership
        kb = await self.kb_repo.get_for_org(kb_id, organization_id)
        if kb is None:
            raise ValueError("Knowledge base not found")
        return await self.kb_repo.update_by_id(kb_id, {"is_active": False})

    # ---- Document CRUD ----

    async def add_document(
        self,
        organization_id: str,
        knowledge_base_id: str,
        title: str,
        content: str,
        document_type: str = "general",
        keywords: Optional[list] = None,
        tags: Optional[list] = None,
        created_by: Optional[str] = None,
    ) -> KnowledgeDocument:
        # Verify KB belongs to org
        kb = await self.kb_repo.get_for_org(knowledge_base_id, organization_id)
        if kb is None:
            raise ValueError("Knowledge base not found or not owned by org")
        if not title.strip():
            raise ValueError("Document title cannot be empty")
        if not content.strip():
            raise ValueError("Document content cannot be empty")

        doc = await self.doc_repo.create(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            title=title.strip(),
            content=content.strip(),
            document_type=document_type,
            keywords=keywords,
            tags=tags,
            created_by=created_by,
        )
        await self.kb_repo.increment_document_count(knowledge_base_id, 1)
        return doc

    async def get_document(
        self, doc_id: str, organization_id: str
    ) -> Optional[KnowledgeDocument]:
        return await self.doc_repo.get_for_org(doc_id, organization_id)

    async def list_documents(
        self,
        knowledge_base_id: str,
        organization_id: str,
        document_type: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[KnowledgeDocument]:
        # Verify KB ownership
        kb = await self.kb_repo.get_for_org(knowledge_base_id, organization_id)
        if kb is None:
            raise ValueError("Knowledge base not found")
        return await self.doc_repo.list_for_kb(
            knowledge_base_id, organization_id,
            document_type=document_type,
            limit=limit, skip=skip,
        )

    async def update_document(
        self,
        doc_id: str,
        organization_id: str,
        new_content: str,
        new_title: Optional[str] = None,
        edited_by: Optional[str] = None,
    ) -> Optional[KnowledgeDocument]:
        """Update creates a new version. Old version is preserved but deactivated."""
        return await self.doc_repo.create_version(
            doc_id, organization_id, new_content, new_title, edited_by
        )

    async def delete_document(
        self, doc_id: str, organization_id: str
    ) -> bool:
        doc = await self.doc_repo.get_for_org(doc_id, organization_id)
        if doc is None:
            raise ValueError("Document not found")
        ok = await self.doc_repo.delete_for_org(doc_id, organization_id)
        if ok:
            await self.kb_repo.increment_document_count(doc.knowledge_base_id, -1)
        return ok

    # ---- Agent association ----

    async def associate_agent(
        self,
        organization_id: str,
        knowledge_base_id: str,
        agent_id: str,
        priority: int = 0,
    ) -> bool:
        kb = await self.kb_repo.get_for_org(knowledge_base_id, organization_id)
        if kb is None:
            raise ValueError("Knowledge base not found")
        await self.assoc_repo.associate(
            organization_id, knowledge_base_id, agent_id, priority
        )
        return True

    async def disassociate_agent(
        self,
        organization_id: str,
        knowledge_base_id: str,
        agent_id: str,
    ) -> bool:
        return await self.assoc_repo.disassociate(
            organization_id, knowledge_base_id, agent_id
        )

    async def get_kbs_for_agent(
        self, agent_id: str, organization_id: str
    ) -> list[KnowledgeBase]:
        kb_ids = await self.assoc_repo.get_kb_ids_for_agent(agent_id, organization_id)
        kbs = []
        for kb_id in kb_ids:
            kb = await self.kb_repo.get_for_org(kb_id, organization_id)
            if kb:
                kbs.append(kb)
        return kbs

    # ---- Search (MVP: simple text matching) ----

    async def search(
        self,
        organization_id: str,
        query_text: str,
        knowledge_base_ids: Optional[list[str]] = None,
        limit: int = MAX_DOCS_PER_SEARCH,
    ) -> list[KnowledgeDocument]:
        if not query_text.strip():
            return []
        return await self.doc_repo.search(
            organization_id=organization_id,
            query_text=query_text,
            knowledge_base_ids=knowledge_base_ids,
            limit=limit,
        )

    async def search_for_agent(
        self,
        agent_id: str,
        organization_id: str,
        query_text: str,
        limit: int = MAX_DOCS_PER_SEARCH,
    ) -> list[KnowledgeDocument]:
        """Search across all KBs associated with an agent."""
        kb_ids = await self.assoc_repo.get_kb_ids_for_agent(agent_id, organization_id)
        if not kb_ids:
            return []
        return await self.search(
            organization_id=organization_id,
            query_text=query_text,
            knowledge_base_ids=kb_ids,
            limit=limit,
        )

    # ---- Context injection for AI ----

    async def get_context_for_agent(
        self,
        agent_id: str,
        organization_id: str,
        query_text: Optional[str] = None,
        max_chars: int = MAX_CONTEXT_CHARS,
    ) -> str:
        """
        Retrieve relevant knowledge as plain text for injection into the LLM context.
        MVP: returns top matching documents concatenated (no embeddings/RAG).
        """
        kb_ids = await self.assoc_repo.get_kb_ids_for_agent(agent_id, organization_id)
        if not kb_ids:
            return ""

        if query_text:
            docs = await self.search(
                organization_id, query_text, kb_ids, limit=MAX_DOCS_PER_SEARCH
            )
        else:
            # No query — return first N documents from all associated KBs
            docs = []
            for kb_id in kb_ids:
                kb_docs = await self.doc_repo.list_for_kb(
                    kb_id, organization_id, limit=3
                )
                docs.extend(kb_docs)
            docs = docs[:MAX_DOCS_PER_SEARCH]

        if not docs:
            return ""

        parts = []
        total_chars = 0
        for doc in docs:
            entry = f"## {doc.title}\n{doc.content}\n"
            if total_chars + len(entry) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 100:
                    parts.append(entry[:remaining] + "...")
                break
            parts.append(entry)
            total_chars += len(entry)

        return "\n".join(parts)
