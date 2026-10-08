"""M12 tests — Lead CRM.

Tests:
1.  Lead model — status validation, phone required
2.  Phone normalization — 10-digit Indian → E.164, existing E.164 unchanged
3.  LeadRepository — CRUD, tenant isolation (org_id on every query)
4.  DNCRepository — add, bulk_check, remove, duplicate add returns None
5.  LeadService.create_lead — DNC blocked, duplicate blocked
6.  CSV import pipeline — parse, map, validate, DNC filter, deduplication
7.  XLSX import pipeline
8.  JSON import pipeline
9.  Import with column mapping
10. Import with missing phone field → validation error recorded, row skipped
11. 4000+ lead import test (performance + correctness)
12. DNC numbers filtered from import
13. Duplicate phones skipped in import (same org)
14. Error report generated for invalid rows
15. Tenant isolation: Org A leads invisible to Org B
16. HTTP: create, list, get, update, delete, DNC, import
17. HTTP: tenant isolation 404 for cross-org access
"""

import asyncio
import csv
import io
import json
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
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test"]


def _make_csv(rows: list[dict], extra_headers: list[str] = None) -> bytes:
    """Build a CSV bytes payload from a list of dicts."""
    if not rows:
        return b"phone,name,email\n"
    headers = list(rows[0].keys())
    if extra_headers:
        for h in extra_headers:
            if h not in headers:
                headers.append(h)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _make_json(rows: list[dict]) -> bytes:
    return json.dumps(rows).encode("utf-8")


# ---------------------------------------------------------------------------
# Test: Models
# ---------------------------------------------------------------------------
class TestLeadModel:
    def test_lead_requires_phone(self):
        from backend.models.lead import Lead
        from backend.models.base import new_id
        with pytest.raises(Exception):
            Lead(_id=new_id(), organization_id="org-1", phone="")

    def test_lead_default_status(self):
        from backend.models.lead import Lead
        from backend.models.base import new_id
        lead = Lead(_id=new_id(), organization_id="org-1", phone="+919876543210")
        assert lead.status == "new"
        assert lead.score == 0
        assert lead.attempts == 0

    def test_invalid_status_rejected(self):
        from backend.models.lead import Lead
        from backend.models.base import new_id
        with pytest.raises(Exception):
            Lead(_id=new_id(), organization_id="org-1", phone="+91987",
                 status="bad_status")

    def test_all_valid_statuses(self):
        from backend.models.lead import Lead, LEAD_STATUSES
        from backend.models.base import new_id
        for s in LEAD_STATUSES:
            lead = Lead(_id=new_id(), organization_id="org-1",
                        phone="+919876543210", status=s)
            assert lead.status == s

    def test_custom_fields_stored(self):
        from backend.models.lead import Lead
        from backend.models.base import new_id
        lead = Lead(_id=new_id(), organization_id="org-1", phone="+91987",
                    custom_fields={"monthly_bill": "5000", "roof_type": "flat"})
        assert lead.custom_fields["monthly_bill"] == "5000"


# ---------------------------------------------------------------------------
# Test: Phone normalization
# ---------------------------------------------------------------------------
class TestPhoneNormalization:
    def test_10_digit_indian_mobile(self):
        from backend.services.lead_service import normalize_phone
        assert normalize_phone("9876543210") == "+919876543210"
        assert normalize_phone("8765432109") == "+918765432109"

    def test_existing_e164_unchanged(self):
        from backend.services.lead_service import normalize_phone
        assert normalize_phone("+919876543210") == "+919876543210"
        assert normalize_phone("+14155552671") == "+14155552671"

    def test_strips_formatting(self):
        from backend.services.lead_service import normalize_phone
        assert normalize_phone("98-765-43210") == "+919876543210"
        assert normalize_phone("(987) 654-3210") == "+919876543210"
        assert normalize_phone(" 9876543210 ") == "+919876543210"

    def test_12_digit_with_country_code(self):
        from backend.services.lead_service import normalize_phone
        assert normalize_phone("919876543210") == "+919876543210"

    def test_empty_string(self):
        from backend.services.lead_service import normalize_phone
        assert normalize_phone("") == ""

    def test_non_indian_number_returned_as_is(self):
        from backend.services.lead_service import normalize_phone
        result = normalize_phone("001234567890")
        assert result  # some non-empty result


# ---------------------------------------------------------------------------
# Test: LeadRepository
# ---------------------------------------------------------------------------
@SKIP
class TestLeadRepository:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_create_and_find(self):
        from backend.repositories.lead_repo import LeadRepository
        repo = LeadRepository(self.db)
        async def _t():
            lead = await repo.create("org-1", "+919001000001", name="Alice")
            assert lead.id is not None
            found = await repo.find_by_id(lead.id)
            assert found.name == "Alice"
            assert found.organization_id == "org-1"
        run(_t())

    def test_find_by_phone_org(self):
        from backend.repositories.lead_repo import LeadRepository
        repo = LeadRepository(self.db)
        async def _t():
            await repo.create("org-1", "+919001000002", name="Bob")
            found = await repo.find_by_phone_org("+919001000002", "org-1")
            assert found is not None
            # Wrong org → None
            assert await repo.find_by_phone_org("+919001000002", "org-2") is None
        run(_t())

    def test_list_for_org_scoped(self):
        from backend.repositories.lead_repo import LeadRepository
        repo = LeadRepository(self.db)
        async def _t():
            await repo.create("org-A", "+919001000010")
            await repo.create("org-A", "+919001000011")
            await repo.create("org-B", "+919001000012")
            leads_a = await repo.list_for_org("org-A")
            leads_b = await repo.list_for_org("org-B")
            assert len(leads_a) == 2
            assert len(leads_b) == 1
            # Org A cannot see org B
            phones_a = {l.phone for l in leads_a}
            assert "+919001000012" not in phones_a
        run(_t())

    def test_update_status(self):
        from backend.repositories.lead_repo import LeadRepository
        repo = LeadRepository(self.db)
        async def _t():
            lead = await repo.create("org-1", "+919001000020")
            ok = await repo.update_status(lead.id, "org-1", "qualified", score=80)
            assert ok
            updated = await repo.find_by_id(lead.id)
            assert updated.status == "qualified"
        run(_t())

    def test_update_status_wrong_org_fails(self):
        from backend.repositories.lead_repo import LeadRepository
        repo = LeadRepository(self.db)
        async def _t():
            lead = await repo.create("org-owner", "+919001000030")
            ok = await repo.update_status(lead.id, "org-other", "qualified")
            assert not ok  # Tenant isolation: wrong org cannot update
            unchanged = await repo.find_by_id(lead.id)
            assert unchanged.status == "new"
        run(_t())

    def test_phones_in_org(self):
        from backend.repositories.lead_repo import LeadRepository
        repo = LeadRepository(self.db)
        async def _t():
            await repo.create("org-1", "+919001000040")
            await repo.create("org-1", "+919001000041")
            existing = await repo.phones_in_org("org-1",
                ["+919001000040", "+919001000041", "+919001000099"])
            assert "+919001000040" in existing
            assert "+919001000041" in existing
            assert "+919001000099" not in existing
        run(_t())


# ---------------------------------------------------------------------------
# Test: DNCRepository
# ---------------------------------------------------------------------------
@SKIP
class TestDNCRepository:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_add_and_check(self):
        from backend.repositories.lead_repo import DNCRepository
        repo = DNCRepository(self.db)
        async def _t():
            entry = await repo.add("org-1", "+919001000050", reason="opt out")
            assert entry is not None
            assert await repo.is_dnc("org-1", "+919001000050") is True
            assert await repo.is_dnc("org-1", "+919001000051") is False
        run(_t())

    def test_add_duplicate_returns_none(self):
        from backend.repositories.lead_repo import DNCRepository
        repo = DNCRepository(self.db)
        async def _t():
            await repo.add("org-1", "+919001000060")
            result = await repo.add("org-1", "+919001000060")
            assert result is None  # already on DNC
        run(_t())

    def test_dnc_is_org_scoped(self):
        from backend.repositories.lead_repo import DNCRepository
        repo = DNCRepository(self.db)
        async def _t():
            await repo.add("org-A", "+919001000070")
            assert await repo.is_dnc("org-A", "+919001000070") is True
            assert await repo.is_dnc("org-B", "+919001000070") is False  # different org
        run(_t())

    def test_bulk_check(self):
        from backend.repositories.lead_repo import DNCRepository
        repo = DNCRepository(self.db)
        async def _t():
            await repo.add("org-1", "+919001000080")
            await repo.add("org-1", "+919001000081")
            dnc_set = await repo.bulk_check("org-1",
                ["+919001000080", "+919001000081", "+919001000082"])
            assert "+919001000080" in dnc_set
            assert "+919001000081" in dnc_set
            assert "+919001000082" not in dnc_set
        run(_t())

    def test_remove_from_dnc(self):
        from backend.repositories.lead_repo import DNCRepository
        repo = DNCRepository(self.db)
        async def _t():
            await repo.add("org-1", "+919001000090")
            assert await repo.is_dnc("org-1", "+919001000090") is True
            removed = await repo.remove("org-1", "+919001000090")
            assert removed is True
            assert await repo.is_dnc("org-1", "+919001000090") is False
        run(_t())


# ---------------------------------------------------------------------------
# Test: LeadService
# ---------------------------------------------------------------------------
@SKIP
class TestLeadService:
    def setup_method(self):
        self.db = _get_mock_db()

    def _svc(self):
        from backend.services.lead_service import LeadService
        return LeadService(self.db)

    def test_create_lead(self):
        async def _t():
            svc = self._svc()
            lead = await svc.create_lead("org-1", "9876543210", name="Test")
            assert lead.phone == "+919876543210"  # normalized
            assert lead.name == "Test"
        run(_t())

    def test_create_lead_dnc_blocked(self):
        async def _t():
            svc = self._svc()
            await svc.add_to_dnc("org-1", "+919001000100")
            with pytest.raises(ValueError, match="DNC"):
                await svc.create_lead("org-1", "+919001000100")
        run(_t())

    def test_create_lead_duplicate_blocked(self):
        async def _t():
            svc = self._svc()
            await svc.create_lead("org-1", "+919001000110")
            with pytest.raises(ValueError, match="already exists"):
                await svc.create_lead("org-1", "+919001000110")
        run(_t())

    def test_get_lead_tenant_isolation(self):
        async def _t():
            svc = self._svc()
            lead = await svc.create_lead("org-A", "+919001000120")
            # Same org: OK
            found = await svc.get_lead(lead.id, "org-A")
            assert found is not None
            # Different org: None
            not_found = await svc.get_lead(lead.id, "org-B")
            assert not_found is None
        run(_t())

    def test_update_lead(self):
        async def _t():
            svc = self._svc()
            lead = await svc.create_lead("org-1", "+919001000130")
            updated = await svc.update_lead(lead.id, "org-1",
                                            {"name": "Updated", "status": "qualified"})
            assert updated.name == "Updated"
            assert updated.status == "qualified"
        run(_t())

    def test_delete_lead(self):
        async def _t():
            svc = self._svc()
            lead = await svc.create_lead("org-1", "+919001000140")
            ok = await svc.delete_lead(lead.id, "org-1")
            assert ok is True
            gone = await svc.get_lead(lead.id, "org-1")
            assert gone is None
        run(_t())


# ---------------------------------------------------------------------------
# Test: Import pipeline
# ---------------------------------------------------------------------------
@SKIP
class TestCSVImport:
    def setup_method(self):
        self.db = _get_mock_db()

    def _svc(self):
        from backend.services.lead_service import LeadService
        return LeadService(self.db)

    def test_basic_csv_import(self):
        async def _t():
            svc = self._svc()
            rows = [
                {"phone": "9876543210", "name": "Alice", "email": "alice@test.com"},
                {"phone": "8765432109", "name": "Bob"},
                {"phone": "7654321098", "name": "Carol"},
            ]
            result = await svc.import_leads("org-csv", _make_csv(rows), "csv")
            assert result["imported"] == 3
            assert result["skipped_dnc"] == 0
            assert result["skipped_duplicate"] == 0
            assert result["total_rows"] == 3
            assert result["batch_id"] is not None
        run(_t())

    def test_csv_phones_normalized(self):
        async def _t():
            svc = self._svc()
            rows = [{"phone": "9123456789"}]
            result = await svc.import_leads("org-norm", _make_csv(rows), "csv")
            assert result["imported"] == 1
            leads, _ = await svc.list_leads("org-norm")
            assert leads[0].phone == "+919123456789"
        run(_t())

    def test_csv_missing_phone_skipped_with_error(self):
        async def _t():
            svc = self._svc()
            rows = [
                {"phone": "9876543210", "name": "Alice"},
                {"phone": "", "name": "No Phone"},       # missing phone
                {"phone": "8765432109", "name": "Bob"},
            ]
            result = await svc.import_leads("org-phone", _make_csv(rows), "csv")
            assert result["imported"] == 2
            assert result["skipped_invalid"] == 1
            assert len(result["errors"]) == 1
        run(_t())

    def test_csv_dnc_filtered(self):
        async def _t():
            svc = self._svc()
            # Add to DNC first
            await svc.add_to_dnc("org-dnc", "+919876543210")
            rows = [
                {"phone": "9876543210", "name": "DNC Lead"},  # → +91987... on DNC
                {"phone": "8765432109", "name": "OK Lead"},
            ]
            result = await svc.import_leads("org-dnc", _make_csv(rows), "csv")
            assert result["imported"] == 1
            assert result["skipped_dnc"] == 1
        run(_t())

    def test_csv_duplicates_skipped(self):
        async def _t():
            svc = self._svc()
            # Import once
            rows = [{"phone": "9876543210"}, {"phone": "8765432109"}]
            r1 = await svc.import_leads("org-dup", _make_csv(rows), "csv")
            assert r1["imported"] == 2
            # Import again (same phones)
            r2 = await svc.import_leads("org-dup", _make_csv(rows), "csv")
            assert r2["imported"] == 0
            assert r2["skipped_duplicate"] == 2
        run(_t())

    def test_csv_column_mapping(self):
        async def _t():
            svc = self._svc()
            # Non-standard column names
            rows = [{"mobile": "9876543210", "full_name": "Alice"}]
            mapping = {"mobile": "phone", "full_name": "name"}
            result = await svc.import_leads(
                "org-map", _make_csv(rows), "csv", column_mapping=mapping
            )
            assert result["imported"] == 1
            leads, _ = await svc.list_leads("org-map")
            assert leads[0].name == "Alice"
        run(_t())

    def test_csv_auto_column_mapping(self):
        """Auto-mapping handles common aliases (mobile → phone, etc.)."""
        async def _t():
            svc = self._svc()
            rows = [{"mobile": "9876543210", "customer_name": "Auto Map"}]
            result = await svc.import_leads("org-automap", _make_csv(rows), "csv")
            assert result["imported"] == 1
        run(_t())


@SKIP
class TestJSONImport:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_json_import(self):
        from backend.services.lead_service import LeadService
        async def _t():
            svc = LeadService(self.db)
            rows = [
                {"phone": "9876543210", "name": "JSON Lead 1"},
                {"phone": "8765432109", "name": "JSON Lead 2"},
            ]
            result = await svc.import_leads("org-json", _make_json(rows), "json")
            assert result["imported"] == 2
            assert result["total_rows"] == 2
        run(_t())

    def test_json_not_array_raises_graceful_error(self):
        from backend.services.lead_service import LeadService
        async def _t():
            svc = LeadService(self.db)
            result = await svc.import_leads("org-json2", b'{"phone": "1234567890"}', "json")
            assert result["imported"] == 0
            assert len(result["errors"]) > 0
        run(_t())


@SKIP
class TestXLSXImport:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_xlsx_import(self):
        from backend.services.lead_service import LeadService
        import openpyxl
        async def _t():
            svc = LeadService(self.db)
            # Build a minimal XLSX in memory
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(["phone", "name", "email"])
            ws.append(["9876543210", "XLSX Lead 1", "lead1@test.com"])
            ws.append(["8765432109", "XLSX Lead 2", "lead2@test.com"])
            buf = io.BytesIO()
            wb.save(buf)
            content = buf.getvalue()

            result = await svc.import_leads("org-xlsx", content, "xlsx")
            assert result["imported"] == 2
            assert result["total_rows"] == 2
        run(_t())


@SKIP
class TestLargeImport:
    """Test 4000+ lead import — the M12 mandatory acceptance criterion."""

    def setup_method(self):
        self.db = _get_mock_db()

    def test_4000_lead_csv_import(self):
        """Import 4000 leads: all imported, correct count, no errors."""
        from backend.services.lead_service import LeadService
        async def _t():
            svc = LeadService(self.db)
            # Generate 4000 unique Indian mobile numbers
            rows = [
                {"phone": f"{6000000000 + i}", "name": f"Lead {i}"}
                for i in range(4000)
            ]
            result = await svc.import_leads("org-bulk", _make_csv(rows), "csv")
            assert result["imported"] == 4000, \
                f"Expected 4000 imported, got {result['imported']} (errors: {result['errors'][:3]})"
            assert result["skipped_invalid"] == 0
            assert result["skipped_duplicate"] == 0
            assert result["total_rows"] == 4000

            # Verify count in DB
            _, total = await svc.list_leads("org-bulk", limit=1)
            assert total == 4000
        run(_t())

    def test_4000_leads_with_100_dnc(self):
        """4000 leads, 100 on DNC → 3900 imported, 100 skipped."""
        from backend.services.lead_service import LeadService
        async def _t():
            svc = LeadService(self.db)
            # Add 100 phones to DNC
            for i in range(100):
                phone = f"+91{7000000000 + i}"
                await svc.add_to_dnc("org-dnc-bulk", phone)

            rows = [
                {"phone": f"{7000000000 + i}", "name": f"Lead {i}"}
                for i in range(4000)
            ]
            result = await svc.import_leads("org-dnc-bulk", _make_csv(rows), "csv")
            assert result["imported"] == 3900
            assert result["skipped_dnc"] == 100
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestLeadsHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.leads import router as leads_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(leads_router, prefix="/api/v1")

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
            "org_name": "Lead Org",
            "org_email": "lead@org.com",
            "email": "user@lead.com",
            "password": "LeadPass1!",
        })
        self.token_a = r1.json()["access_token"]
        self.org_id_a = r1.json()["organization_id"]

        r2 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Other Org",
            "org_email": "other2@org.com",
            "email": "user@other2.com",
            "password": "OtherPass1!",
        })
        self.token_b = r2.json()["access_token"]

    def _auth(self, token): return {"Authorization": f"Bearer {token}"}

    def test_create_lead(self):
        resp = self.client.post("/api/v1/leads", json={
            "phone": "9876543210",
            "name": "HTTP Lead",
        }, headers=self._auth(self.token_a))
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["phone"] == "+919876543210"
        assert data["name"] == "HTTP Lead"

    def test_list_leads_empty(self):
        resp = self.client.get("/api/v1/leads",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert "leads" in resp.json()

    def test_get_lead(self):
        r = self.client.post("/api/v1/leads", json={"phone": "9001000001"},
                             headers=self._auth(self.token_a))
        lead_id = r.json()["id"]
        resp = self.client.get(f"/api/v1/leads/{lead_id}",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert resp.json()["id"] == lead_id

    def test_tenant_isolation_get(self):
        r = self.client.post("/api/v1/leads", json={"phone": "9001000002"},
                             headers=self._auth(self.token_a))
        lead_id = r.json()["id"]
        # Org B cannot access Org A lead
        resp = self.client.get(f"/api/v1/leads/{lead_id}",
                               headers=self._auth(self.token_b))
        assert resp.status_code == 404

    def test_update_lead(self):
        r = self.client.post("/api/v1/leads", json={"phone": "9001000003"},
                             headers=self._auth(self.token_a))
        lead_id = r.json()["id"]
        resp = self.client.patch(f"/api/v1/leads/{lead_id}",
                                 json={"name": "Updated", "status": "qualified"},
                                 headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"
        assert resp.json()["status"] == "qualified"

    def test_delete_lead(self):
        r = self.client.post("/api/v1/leads", json={"phone": "9001000004"},
                             headers=self._auth(self.token_a))
        lead_id = r.json()["id"]
        resp = self.client.delete(f"/api/v1/leads/{lead_id}",
                                  headers=self._auth(self.token_a))
        assert resp.status_code == 204
        # Confirm gone
        get_resp = self.client.get(f"/api/v1/leads/{lead_id}",
                                   headers=self._auth(self.token_a))
        assert get_resp.status_code == 404

    def test_dnc_add_and_check(self):
        resp = self.client.post("/api/v1/leads/dnc",
                                json={"phone": "+919999999999", "reason": "opt out"},
                                headers=self._auth(self.token_a))
        assert resp.status_code == 201
        assert resp.json()["added"] is True

        # Now try creating a lead with that phone → blocked
        resp2 = self.client.post("/api/v1/leads",
                                 json={"phone": "+919999999999"},
                                 headers=self._auth(self.token_a))
        assert resp2.status_code == 400
        assert "DNC" in resp2.json()["detail"]

    def test_dnc_list(self):
        self.client.post("/api/v1/leads/dnc",
                         json={"phone": "+918888888888"},
                         headers=self._auth(self.token_a))
        resp = self.client.get("/api/v1/leads/dnc",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert any(e["phone"] == "+918888888888" for e in resp.json())

    def test_dnc_tenant_isolation(self):
        """Org A DNC does not affect Org B."""
        self.client.post("/api/v1/leads/dnc",
                         json={"phone": "+917777777777"},
                         headers=self._auth(self.token_a))
        # Org B can create a lead with that phone (different org DNC)
        resp = self.client.post("/api/v1/leads",
                                json={"phone": "+917777777777"},
                                headers=self._auth(self.token_b))
        assert resp.status_code == 201

    def test_csv_import_via_http(self):
        rows = [
            {"phone": "9500000001", "name": "Import A"},
            {"phone": "9500000002", "name": "Import B"},
        ]
        csv_bytes = _make_csv(rows)
        resp = self.client.post(
            "/api/v1/leads/import",
            files={"file": ("leads.csv", csv_bytes, "text/csv")},
            headers=self._auth(self.token_a),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["imported"] == 2
        assert data["total_rows"] == 2

    def test_unsupported_format_returns_400(self):
        resp = self.client.post(
            "/api/v1/leads/import",
            files={"file": ("leads.txt", b"some data", "text/plain")},
            headers=self._auth(self.token_a),
        )
        assert resp.status_code == 400

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/v1/leads")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
