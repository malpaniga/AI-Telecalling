"""M29 tests — Separate Knowledge Base Export & Import Across Organizations.

Tests:
1. Export active knowledge base produces valid sarvam_kb_export_v1 package with documents scrubbed of tenant IDs.
2. Tenant isolation on KB export (cannot export another org's KB).
3. Import KB creates a new KnowledgeBase in target org and imports all documents with target org_id.
4. Import handles empty document list gracefully.
5. End-to-end HTTP endpoints GET /api/v1/knowledge/{id}/export and POST /api/v1/knowledge/import.
"""

import asyncio
import os
import sys
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
    return mongomock_motor.AsyncMongoMockClient()["test_m29"]


@SKIP
class TestKnowledgeBaseExportImport:
    def setup_method(self):
        self.db = _get_mock_db()
        from backend.services.knowledge_service import KnowledgeService
        self.kb_svc = KnowledgeService(self.db)

    def test_export_knowledge_base_sanitized(self):
        async def _t():
            # Create KB in Org A
            kb = await self.kb_svc.create_kb(
                organization_id="org-a",
                name="Solar Technical FAQs",
                description="Technical specifications and solar subsidy details",
                tags=["solar", "subsidy"],
            )
            # Add 2 documents
            await self.kb_svc.add_document(
                organization_id="org-a",
                knowledge_base_id=kb.id,
                title="Subsidy Guidelines",
                content="₹78,000 standard subsidy for 2kW systems under PM Surya Ghar.",
                document_type="faq",
                keywords=["subsidy", "price", "pm surya ghar"],
                tags=["pricing"],
            )
            await self.kb_svc.add_document(
                organization_id="org-a",
                knowledge_base_id=kb.id,
                title="Rooftop Area Needed",
                content="Requires at least 200 sq ft shadow-free space.",
                document_type="product_info",
                keywords=["roof", "area"],
            )

            export_pkg = await self.kb_svc.export_knowledge_base(kb.id, "org-a")

            assert export_pkg["format"] == "sarvam_kb_export_v1"
            assert "exported_at" in export_pkg
            kb_data = export_pkg["knowledge_base"]
            assert kb_data["name"] == "Solar Technical FAQs"
            assert kb_data["description"] == "Technical specifications and solar subsidy details"
            assert kb_data["tags"] == ["solar", "subsidy"]

            docs = kb_data["documents"]
            assert len(docs) == 2
            doc_map = {d["title"]: d for d in docs}
            assert "Subsidy Guidelines" in doc_map
            assert "78,000" in doc_map["Subsidy Guidelines"]["content"]
            assert doc_map["Subsidy Guidelines"]["document_type"] == "faq"
            assert "Rooftop Area Needed" in doc_map

            # Check tenant sanitization (no internal IDs leaked)
            assert "organization_id" not in export_pkg
            assert "organization_id" not in kb_data
            assert "id" not in kb_data
            assert "_id" not in kb_data
            for d in docs:
                assert "organization_id" not in d
                assert "knowledge_base_id" not in d
                assert "id" not in d
                assert "_id" not in d

        run(_t())

    def test_export_kb_tenant_isolation(self):
        async def _t():
            kb = await self.kb_svc.create_kb(organization_id="org-a", name="Private KB")
            with pytest.raises(ValueError, match="not found"):
                await self.kb_svc.export_knowledge_base(kb.id, "org-b")
        run(_t())

    def test_import_kb_into_new_organization(self):
        async def _t():
            # Export from Org A
            kb_a = await self.kb_svc.create_kb("org-a", "Product Docs", "Docs description", ["v1"])
            await self.kb_svc.add_document("org-a", kb_a.id, "Doc 1", "Content 1", "policy")
            export_pkg = await self.kb_svc.export_knowledge_base(kb_a.id, "org-a")

            # Import into Org B
            kb_b = await self.kb_svc.import_knowledge_base(
                organization_id="org-b",
                name="Imported Product Docs",
                description=export_pkg["knowledge_base"]["description"],
                tags=export_pkg["knowledge_base"]["tags"],
                documents=export_pkg["knowledge_base"]["documents"],
            )

            assert kb_b.organization_id == "org-b"
            assert kb_b.id != kb_a.id
            assert kb_b.name == "Imported Product Docs"
            assert kb_b.document_count == 1

            # Verify docs in Org B
            docs_b = await self.kb_svc.list_documents(kb_b.id, "org-b")
            assert len(docs_b) == 1
            assert docs_b[0].title == "Doc 1"
            assert docs_b[0].content == "Content 1"
            assert docs_b[0].organization_id == "org-b"
            assert docs_b[0].knowledge_base_id == kb_b.id
        run(_t())

    def test_import_kb_empty_documents(self):
        async def _t():
            kb = await self.kb_svc.import_knowledge_base(
                organization_id="org-b",
                name="Empty KB",
                description="No docs",
                tags=[],
                documents=[],
            )
            assert kb.organization_id == "org-b"
            assert kb.document_count == 0
        run(_t())


@SKIP
class TestKnowledgeBaseExportImportHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from backend.api.v1.knowledge import router as kb_router
        from backend.core import db as db_module
        from backend.core.auth import CurrentUser, get_current_user
        from backend.services.knowledge_service import KnowledgeService

        self.mock_db = mongomock_motor.AsyncMongoMockClient()["test_m29_http"]
        db_module._db = self.mock_db

        self.test_app = FastAPI()
        self.test_app.include_router(kb_router, prefix="/api/v1")

        self.current_user = CurrentUser(
            user_id="user-kb-1",
            email="kb@test.com",
            role="owner",
            org_id="org-kb-1",
        )
        self.test_app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.client = TestClient(self.test_app)
        self.kb_svc = KnowledgeService(self.mock_db)

    def test_http_kb_export_and_import(self):
        # 1. Create KB in org 1
        kb = run(self.kb_svc.create_kb("org-kb-1", "HTTP KB", "Description", ["tag1"]))
        run(self.kb_svc.add_document("org-kb-1", kb.id, "HTTP Doc", "HTTP Content", "general"))

        # 2. Export via HTTP
        res_export = self.client.get(f"/api/v1/knowledge/{kb.id}/export")
        assert res_export.status_code == 200
        pkg = res_export.json()
        assert pkg["format"] == "sarvam_kb_export_v1"
        assert pkg["knowledge_base"]["name"] == "HTTP KB"
        assert len(pkg["knowledge_base"]["documents"]) == 1

        # 3. Import in org 2
        self.current_user.org_id = "org-kb-2"
        res_import = self.client.post("/api/v1/knowledge/import", json={
            "name": "Org2 Imported KB",
            "description": pkg["knowledge_base"]["description"],
            "tags": pkg["knowledge_base"]["tags"],
            "documents": pkg["knowledge_base"]["documents"],
        })
        assert res_import.status_code == 201
        created = res_import.json()
        assert created["name"] == "Org2 Imported KB"
        assert created["organization_id"] == "org-kb-2"
        assert created["document_count"] == 1
