"""M19 tests — Knowledge Base.

Tests:
1.  KnowledgeBase model — tenant-scoped
2.  KnowledgeDocument — version tracking, keyword extraction
3.  KBRepository — CRUD, tenant isolation
4.  DocRepository — CRUD, versioning (old deactivated, new created)
5.  Text search — finds by title, content, keywords
6.  KnowledgeService.create_kb + add_document (validates KB ownership)
7.  Empty title/content raises ValueError
8.  update_document creates new version, old deactivated
9.  delete_document soft-deletes + decrements count
10. associate_agent / disassociate_agent
11. get_kbs_for_agent returns correct KBs in priority order
12. search_for_agent searches only associated KBs
13. get_context_for_agent returns formatted text within char limit
14. Tenant isolation: Org A cannot add doc to Org B's KB
15. HTTP: create KB, add doc, list docs, search, associate agent, context
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _mongomock_available():
    try:
        import mongomock_motor
        return True
    except ImportError:
        return False


SKIP = pytest.mark.skipif(not _mongomock_available(), reason="mongomock_motor not installed")


def _get_mock_db():
    import mongomock_motor
    return mongomock_motor.AsyncMongoMockClient()["test"]


# ---------------------------------------------------------------------------
# Test: Models
# ---------------------------------------------------------------------------
class TestKnowledgeModels:
    def test_kb_model(self):
        from backend.models.knowledge import KnowledgeBase
        from backend.models.base import new_id
        kb = KnowledgeBase(_id=new_id(), organization_id="org-1", name="Product FAQ")
        assert kb.document_count == 0
        assert kb.is_active is True

    def test_document_model_defaults(self):
        from backend.models.knowledge import KnowledgeDocument
        from backend.models.base import new_id
        doc = KnowledgeDocument(
            _id=new_id(), organization_id="org-1",
            knowledge_base_id="kb-1",
            title="What is solar?",
            content="Solar panels convert sunlight to electricity.",
        )
        assert doc.version == 1
        assert doc.is_active is True
        assert doc.document_type == "general"

    def test_keyword_extraction(self):
        from backend.repositories.knowledge_repo import _extract_keywords
        keywords = _extract_keywords("Solar Panel FAQ", "How do solar panels work?")
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "solar" in keywords or "Solar" in [k.lower() for k in keywords]

    def test_keyword_extraction_removes_stop_words(self):
        from backend.repositories.knowledge_repo import _extract_keywords
        kw = _extract_keywords("The Product", "This is the main product for the customer")
        assert "the" not in kw
        assert "this" not in kw
        assert "for" not in kw


# ---------------------------------------------------------------------------
# Test: Repository
# ---------------------------------------------------------------------------
@SKIP
class TestKnowledgeBaseRepository:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_create_and_find(self):
        from backend.repositories.knowledge_repo import KnowledgeBaseRepository
        repo = KnowledgeBaseRepository(self.db)
        async def _t():
            kb = await repo.create("org-1", "FAQ KB", "Frequently asked questions")
            assert kb.id is not None
            found = await repo.get_for_org(kb.id, "org-1")
            assert found.name == "FAQ KB"
        run(_t())

    def test_tenant_isolation(self):
        from backend.repositories.knowledge_repo import KnowledgeBaseRepository
        repo = KnowledgeBaseRepository(self.db)
        async def _t():
            kb = await repo.create("org-A", "KB A")
            assert await repo.get_for_org(kb.id, "org-A") is not None
            assert await repo.get_for_org(kb.id, "org-B") is None
        run(_t())

    def test_list_for_org_scoped(self):
        from backend.repositories.knowledge_repo import KnowledgeBaseRepository
        repo = KnowledgeBaseRepository(self.db)
        async def _t():
            await repo.create("org-X", "KB 1")
            await repo.create("org-X", "KB 2")
            await repo.create("org-Y", "KB 3")
            kbs_x = await repo.list_for_org("org-X")
            kbs_y = await repo.list_for_org("org-Y")
            assert len(kbs_x) == 2
            assert len(kbs_y) == 1
        run(_t())

    def test_increment_document_count(self):
        from backend.repositories.knowledge_repo import KnowledgeBaseRepository
        repo = KnowledgeBaseRepository(self.db)
        async def _t():
            kb = await repo.create("org-1", "Count KB")
            assert kb.document_count == 0
            await repo.increment_document_count(kb.id, 3)
            updated = await repo.find_by_id(kb.id)
            assert updated.document_count == 3
        run(_t())


@SKIP
class TestKnowledgeDocumentRepository:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_create_document(self):
        from backend.repositories.knowledge_repo import KnowledgeDocumentRepository
        repo = KnowledgeDocumentRepository(self.db)
        async def _t():
            doc = await repo.create("org-1", "kb-1", "Solar FAQ",
                                    "Solar panels capture sunlight.")
            assert doc.version == 1
            assert doc.is_active is True
            assert "solar" in doc.keywords or "Solar" in doc.keywords
        run(_t())

    def test_get_for_org_tenant_isolation(self):
        from backend.repositories.knowledge_repo import KnowledgeDocumentRepository
        repo = KnowledgeDocumentRepository(self.db)
        async def _t():
            doc = await repo.create("org-A", "kb-1", "Title", "Content")
            assert await repo.get_for_org(doc.id, "org-A") is not None
            assert await repo.get_for_org(doc.id, "org-B") is None
        run(_t())

    def test_search_by_title(self):
        from backend.repositories.knowledge_repo import KnowledgeDocumentRepository
        repo = KnowledgeDocumentRepository(self.db)
        async def _t():
            await repo.create("org-1", "kb-1", "Solar Installation Process",
                              "Step 1: Survey. Step 2: Install.")
            await repo.create("org-1", "kb-1", "Payment Methods",
                              "We accept UPI and bank transfer.")
            results = await repo.search("org-1", "solar")
            assert len(results) == 1
            assert "solar" in results[0].title.lower()
        run(_t())

    def test_search_by_content(self):
        from backend.repositories.knowledge_repo import KnowledgeDocumentRepository
        repo = KnowledgeDocumentRepository(self.db)
        async def _t():
            await repo.create("org-1", "kb-1", "Process",
                              "The solar installation takes 3 days.")
            results = await repo.search("org-1", "installation")
            assert len(results) >= 1
        run(_t())

    def test_create_version(self):
        from backend.repositories.knowledge_repo import KnowledgeDocumentRepository
        repo = KnowledgeDocumentRepository(self.db)
        async def _t():
            original = await repo.create("org-1", "kb-1", "FAQ",
                                         "Original content")
            new_doc = await repo.create_version(
                original.id, "org-1", "Updated content"
            )
            # New version has higher version number
            assert new_doc.version == 2
            assert new_doc.previous_version_id == original.id
            assert new_doc.content == "Updated content"
            # Old is deactivated
            old = await repo.find_by_id(original.id)
            assert old.is_active is False
        run(_t())

    def test_soft_delete(self):
        from backend.repositories.knowledge_repo import KnowledgeDocumentRepository
        repo = KnowledgeDocumentRepository(self.db)
        async def _t():
            doc = await repo.create("org-1", "kb-1", "Delete Me", "Content")
            await repo.delete_for_org(doc.id, "org-1")
            deleted = await repo.get_for_org(doc.id, "org-1")
            assert deleted is None   # get_for_org filters is_active=True
        run(_t())


# ---------------------------------------------------------------------------
# Test: KnowledgeService
# ---------------------------------------------------------------------------
@SKIP
class TestKnowledgeService:
    def setup_method(self):
        self.db = _get_mock_db()

    def _svc(self):
        from backend.services.knowledge_service import KnowledgeService
        return KnowledgeService(self.db)

    def test_create_kb_and_add_document(self):
        async def _t():
            svc = self._svc()
            kb = await svc.create_kb("org-1", "Product Info")
            doc = await svc.add_document(
                "org-1", kb.id, "How it works",
                "Our product uses advanced AI technology."
            )
            assert doc.id is not None
            assert doc.knowledge_base_id == kb.id
        run(_t())

    def test_add_document_wrong_kb_org_raises(self):
        async def _t():
            svc = self._svc()
            kb = await svc.create_kb("org-A", "KB A")
            with pytest.raises(ValueError, match="[Nn]ot found"):
                await svc.add_document("org-B", kb.id, "Title", "Content")
        run(_t())

    def test_add_document_empty_title_raises(self):
        async def _t():
            svc = self._svc()
            kb = await svc.create_kb("org-1", "KB")
            with pytest.raises(ValueError, match="[Tt]itle"):
                await svc.add_document("org-1", kb.id, "", "Content")
        run(_t())

    def test_add_document_empty_content_raises(self):
        async def _t():
            svc = self._svc()
            kb = await svc.create_kb("org-1", "KB")
            with pytest.raises(ValueError, match="[Cc]ontent"):
                await svc.add_document("org-1", kb.id, "Title", "")
        run(_t())

    def test_update_document_creates_version(self):
        async def _t():
            svc = self._svc()
            kb = await svc.create_kb("org-1", "KB")
            doc = await svc.add_document("org-1", kb.id, "FAQ", "Original")
            new_doc = await svc.update_document(
                doc.id, "org-1", "Updated content", new_title="Updated FAQ"
            )
            assert new_doc.version == 2
            assert new_doc.title == "Updated FAQ"
            # Old doc is gone from active view
            old = await svc.get_document(doc.id, "org-1")
            assert old is None
        run(_t())

    def test_delete_document_decrements_count(self):
        async def _t():
            svc = self._svc()
            kb = await svc.create_kb("org-1", "KB")
            doc = await svc.add_document("org-1", kb.id, "Doc", "Content")
            kb_updated = await svc.get_kb(kb.id, "org-1")
            assert kb_updated.document_count == 1
            await svc.delete_document(doc.id, "org-1")
            kb_final = await svc.get_kb(kb.id, "org-1")
            assert kb_final.document_count == 0
        run(_t())

    def test_associate_and_get_agent(self):
        async def _t():
            svc = self._svc()
            kb1 = await svc.create_kb("org-1", "KB 1")
            kb2 = await svc.create_kb("org-1", "KB 2")
            await svc.associate_agent("org-1", kb1.id, "agent-1", priority=0)
            await svc.associate_agent("org-1", kb2.id, "agent-1", priority=1)
            kbs = await svc.get_kbs_for_agent("agent-1", "org-1")
            assert len(kbs) == 2
            kb_ids = [kb.id for kb in kbs]
            assert kb1.id in kb_ids
            assert kb2.id in kb_ids
        run(_t())

    def test_disassociate_agent(self):
        async def _t():
            svc = self._svc()
            kb = await svc.create_kb("org-1", "KB")
            await svc.associate_agent("org-1", kb.id, "agent-1")
            await svc.disassociate_agent("org-1", kb.id, "agent-1")
            kbs = await svc.get_kbs_for_agent("agent-1", "org-1")
            assert len(kbs) == 0
        run(_t())

    def test_search_for_agent(self):
        async def _t():
            svc = self._svc()
            kb1 = await svc.create_kb("org-1", "Agent KB")
            kb2 = await svc.create_kb("org-1", "Other KB")
            await svc.add_document("org-1", kb1.id, "Solar Benefits", "Solar saves money.")
            await svc.add_document("org-1", kb2.id, "Irrelevant Topic", "Unrelated content.")
            await svc.associate_agent("org-1", kb1.id, "agent-search")
            # NOT associating kb2 with the agent
            results = await svc.search_for_agent("agent-search", "org-1", "solar")
            assert len(results) == 1
            assert "solar" in results[0].title.lower() or "solar" in results[0].content.lower()
        run(_t())

    def test_search_for_agent_no_kbs_returns_empty(self):
        async def _t():
            svc = self._svc()
            results = await svc.search_for_agent("agent-no-kb", "org-1", "anything")
            assert results == []
        run(_t())

    def test_get_context_for_agent(self):
        async def _t():
            svc = self._svc()
            kb = await svc.create_kb("org-1", "Context KB")
            await svc.add_document("org-1", kb.id, "Product Overview",
                                   "Our product helps homeowners save on electricity bills.")
            await svc.associate_agent("org-1", kb.id, "agent-ctx")
            context = await svc.get_context_for_agent("agent-ctx", "org-1")
            assert len(context) > 0
            assert "## " in context   # formatted with markdown heading
        run(_t())

    def test_get_context_char_limit(self):
        async def _t():
            svc = self._svc()
            kb = await svc.create_kb("org-1", "Big KB")
            # Add many large documents
            for i in range(10):
                await svc.add_document("org-1", kb.id, f"Doc {i}",
                                       "X" * 1000)
            await svc.associate_agent("org-1", kb.id, "agent-big")
            context = await svc.get_context_for_agent("agent-big", "org-1",
                                                       max_chars=500)
            assert len(context) <= 600   # some slack for truncation message
        run(_t())

    def test_tenant_isolation_add_doc(self):
        async def _t():
            svc = self._svc()
            kb = await svc.create_kb("org-A", "KB A")
            with pytest.raises(ValueError):
                await svc.add_document("org-B", kb.id, "Title", "Content")
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestKnowledgeHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.knowledge import router as kb_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(kb_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        # Two orgs
        r1 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "KB Org",
            "org_email": "kb@org.com",
            "email": "user@kb.com",
            "password": "KBPass1!",
        })
        self.token_a = r1.json()["access_token"]
        self.org_id_a = r1.json()["organization_id"]

        r2 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Other KB",
            "org_email": "other6@org.com",
            "email": "user@other6.com",
            "password": "Other6Pass1!",
        })
        self.token_b = r2.json()["access_token"]

    def _auth(self, t): return {"Authorization": f"Bearer {t}"}

    def test_create_kb(self):
        resp = self.client.post("/api/v1/knowledge",
                                json={"name": "Product FAQ"},
                                headers=self._auth(self.token_a))
        assert resp.status_code == 201
        assert resp.json()["name"] == "Product FAQ"
        assert resp.json()["organization_id"] == self.org_id_a

    def test_list_kbs(self):
        self.client.post("/api/v1/knowledge", json={"name": "KB 1"},
                         headers=self._auth(self.token_a))
        resp = self.client.get("/api/v1/knowledge",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_kb_tenant_isolation(self):
        r = self.client.post("/api/v1/knowledge", json={"name": "Private KB"},
                             headers=self._auth(self.token_a))
        kb_id = r.json()["id"]
        resp = self.client.get(f"/api/v1/knowledge/{kb_id}",
                               headers=self._auth(self.token_b))
        assert resp.status_code == 404

    def test_add_and_list_documents(self):
        r = self.client.post("/api/v1/knowledge", json={"name": "Doc KB"},
                             headers=self._auth(self.token_a))
        kb_id = r.json()["id"]
        self.client.post(f"/api/v1/knowledge/{kb_id}/documents",
                         json={"title": "FAQ 1", "content": "Answer 1"},
                         headers=self._auth(self.token_a))
        resp = self.client.get(f"/api/v1/knowledge/{kb_id}/documents",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_search_knowledge(self):
        r = self.client.post("/api/v1/knowledge", json={"name": "Search KB"},
                             headers=self._auth(self.token_a))
        kb_id = r.json()["id"]
        self.client.post(f"/api/v1/knowledge/{kb_id}/documents",
                         json={"title": "Solar Savings", "content": "Save with solar"},
                         headers=self._auth(self.token_a))
        resp = self.client.post("/api/v1/knowledge/search",
                                json={"query": "solar"},
                                headers=self._auth(self.token_a))
        assert resp.status_code == 200
        docs = resp.json()
        assert len(docs) >= 1

    def test_associate_agent_and_get_context(self):
        r = self.client.post("/api/v1/knowledge", json={"name": "Agent KB"},
                             headers=self._auth(self.token_a))
        kb_id = r.json()["id"]
        self.client.post(f"/api/v1/knowledge/{kb_id}/documents",
                         json={"title": "Product Info",
                               "content": "Our product saves electricity."},
                         headers=self._auth(self.token_a))
        self.client.post(f"/api/v1/knowledge/{kb_id}/agents/agent-http-1",
                         headers=self._auth(self.token_a))
        resp = self.client.get("/api/v1/knowledge/context/agent-http-1",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert "char_count" in resp.json()

    def test_update_document_creates_new_version(self):
        r = self.client.post("/api/v1/knowledge", json={"name": "Version KB"},
                             headers=self._auth(self.token_a))
        kb_id = r.json()["id"]
        doc_r = self.client.post(f"/api/v1/knowledge/{kb_id}/documents",
                                 json={"title": "Old Title", "content": "Old content"},
                                 headers=self._auth(self.token_a))
        doc_id = doc_r.json()["id"]
        new_doc_r = self.client.put(
            f"/api/v1/knowledge/{kb_id}/documents/{doc_id}",
            json={"content": "New content", "title": "New Title"},
            headers=self._auth(self.token_a),
        )
        assert new_doc_r.status_code == 200
        assert new_doc_r.json()["version"] == 2
        assert new_doc_r.json()["id"] != doc_id

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/v1/knowledge")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
