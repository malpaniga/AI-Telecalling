"""Knowledge Base API.

GET    /api/v1/knowledge                        — list KBs
POST   /api/v1/knowledge                        — create KB
GET    /api/v1/knowledge/{kb_id}                — get KB
DELETE /api/v1/knowledge/{kb_id}                — delete KB

GET    /api/v1/knowledge/{kb_id}/documents       — list documents
POST   /api/v1/knowledge/{kb_id}/documents       — add document
GET    /api/v1/knowledge/{kb_id}/documents/{id}  — get document
PUT    /api/v1/knowledge/{kb_id}/documents/{id}  — update (creates new version)
DELETE /api/v1/knowledge/{kb_id}/documents/{id}  — delete document

POST   /api/v1/knowledge/{kb_id}/agents/{agent_id}    — associate with agent
DELETE /api/v1/knowledge/{kb_id}/agents/{agent_id}    — disassociate

GET    /api/v1/knowledge/agents/{agent_id}        — KBs for an agent
POST   /api/v1/knowledge/search                   — search across KBs
GET    /api/v1/knowledge/context/{agent_id}       — get context text for AI
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.services.knowledge_service import KnowledgeService

log = logging.getLogger("api.knowledge")
router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class CreateKBRequest(BaseModel):
    name: str
    description: str = ""
    tags: Optional[list[str]] = None


class CreateDocumentRequest(BaseModel):
    title: str
    content: str
    document_type: str = "general"
    keywords: Optional[list[str]] = None
    tags: Optional[list[str]] = None


class UpdateDocumentRequest(BaseModel):
    content: str
    title: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    knowledge_base_ids: Optional[list[str]] = None
    limit: int = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _require_org(user: CurrentUser) -> str:
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    return user.org_id


def _kb_response(kb) -> dict:
    return {
        "id": kb.id,
        "organization_id": kb.organization_id,
        "name": kb.name,
        "description": kb.description,
        "document_count": kb.document_count,
        "is_active": kb.is_active,
        "tags": kb.tags,
        "created_at": kb.created_at.isoformat(),
        "updated_at": kb.updated_at.isoformat(),
    }


def _doc_response(doc) -> dict:
    return {
        "id": doc.id,
        "knowledge_base_id": doc.knowledge_base_id,
        "title": doc.title,
        "content": doc.content,
        "document_type": doc.document_type,
        "version": doc.version,
        "keywords": doc.keywords,
        "tags": doc.tags,
        "is_active": doc.is_active,
        "created_at": doc.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Knowledge Base endpoints
# ---------------------------------------------------------------------------
@router.get("/agents/{agent_id}")
async def get_kbs_for_agent(
    agent_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = KnowledgeService(get_db())
    kbs = await svc.get_kbs_for_agent(agent_id, org_id)
    return [_kb_response(kb) for kb in kbs]


@router.get("/context/{agent_id}")
async def get_agent_context(
    agent_id: str,
    query: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = KnowledgeService(get_db())
    context = await svc.get_context_for_agent(agent_id, org_id, query_text=query)
    return {"agent_id": agent_id, "context": context, "char_count": len(context)}


@router.post("/search")
async def search_knowledge(
    body: SearchRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = KnowledgeService(get_db())
    docs = await svc.search(
        org_id, body.query,
        knowledge_base_ids=body.knowledge_base_ids,
        limit=body.limit,
    )
    return [_doc_response(d) for d in docs]


@router.get("")
async def list_knowledge_bases(user: CurrentUser = Depends(get_current_user)):
    org_id = _require_org(user)
    svc = KnowledgeService(get_db())
    kbs = await svc.list_kbs(org_id)
    return [_kb_response(kb) for kb in kbs]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    body: CreateKBRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = KnowledgeService(get_db())
    kb = await svc.create_kb(org_id, body.name, body.description, body.tags)
    return _kb_response(kb)


@router.get("/{kb_id}")
async def get_knowledge_base(
    kb_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = KnowledgeService(get_db())
    kb = await svc.get_kb(kb_id, org_id)
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return _kb_response(kb)


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = KnowledgeService(get_db())
    try:
        await svc.delete_kb(kb_id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Document endpoints
# ---------------------------------------------------------------------------
@router.get("/{kb_id}/documents")
async def list_documents(
    kb_id: str,
    document_type: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = KnowledgeService(get_db())
    try:
        docs = await svc.list_documents(kb_id, org_id, document_type, limit, skip)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return [_doc_response(d) for d in docs]


@router.post("/{kb_id}/documents", status_code=status.HTTP_201_CREATED)
async def add_document(
    kb_id: str,
    body: CreateDocumentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = KnowledgeService(get_db())
    try:
        doc = await svc.add_document(
            organization_id=org_id,
            knowledge_base_id=kb_id,
            title=body.title,
            content=body.content,
            document_type=body.document_type,
            keywords=body.keywords,
            tags=body.tags,
            created_by=user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _doc_response(doc)


@router.get("/{kb_id}/documents/{doc_id}")
async def get_document(
    kb_id: str,
    doc_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = KnowledgeService(get_db())
    doc = await svc.get_document(doc_id, org_id)
    if doc is None or doc.knowledge_base_id != kb_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_response(doc)


@router.put("/{kb_id}/documents/{doc_id}")
async def update_document(
    kb_id: str,
    doc_id: str,
    body: UpdateDocumentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = KnowledgeService(get_db())
    new_doc = await svc.update_document(
        doc_id, org_id, body.content, body.title, user.user_id
    )
    if new_doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_response(new_doc)


@router.delete("/{kb_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    kb_id: str,
    doc_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = KnowledgeService(get_db())
    try:
        await svc.delete_document(doc_id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Agent association endpoints
# ---------------------------------------------------------------------------
@router.post("/{kb_id}/agents/{agent_id}", status_code=status.HTTP_201_CREATED)
async def associate_agent(
    kb_id: str,
    agent_id: str,
    priority: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = KnowledgeService(get_db())
    try:
        await svc.associate_agent(org_id, kb_id, agent_id, priority)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "associated", "kb_id": kb_id, "agent_id": agent_id}


@router.delete("/{kb_id}/agents/{agent_id}")
async def disassociate_agent(
    kb_id: str,
    agent_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    org_id = _require_org(user)
    svc = KnowledgeService(get_db())
    ok = await svc.disassociate_agent(org_id, kb_id, agent_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Association not found")
    return {"status": "disassociated", "kb_id": kb_id, "agent_id": agent_id}
