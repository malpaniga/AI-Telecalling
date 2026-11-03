"""Tests for Lead Filtering (City, Tags, Search) and Filter Options Metadata."""

import sys
import os
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.api.v1.auth import router as auth_router
from backend.api.v1.leads import router as leads_router
from backend.core import db as db_module, redis as redis_module
from backend.repositories.lead_repo import LeadRepository


def _mongomock_available():
    try:
        import mongomock_motor
        return True
    except ImportError:
        return False


SKIP = pytest.mark.skipif(not _mongomock_available(), reason="mongomock_motor not installed")


@SKIP
class TestLeadFilters:
    @pytest.fixture(autouse=True)
    def setup(self):
        import mongomock_motor

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(leads_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test_lead_filters"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        # Create user & auth token
        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Filter Test Org",
            "org_email": "filter@org.com",
            "email": "user@filter.com",
            "password": "FilterPass1!",
        })
        self.token = r.json()["access_token"]
        self.org_id = r.json()["organization_id"]

    def _auth(self):
        return {"Authorization": f"Bearer {self.token}"}

    def test_repo_filtering_and_filter_options(self):
        import asyncio
        loop = asyncio.new_event_loop()
        repo = LeadRepository(self.mock_db)

        async def run_test():
            # Seed 3 leads with different cities, tags, names
            await repo.create(
                organization_id=self.org_id,
                phone="+919800000001",
                name="Rahul Sharma",
                email="rahul@example.com",
                custom_fields={"city": "Mumbai"},
                tags=["vip", "q4_sale"],
            )
            await repo.create(
                organization_id=self.org_id,
                phone="+919800000002",
                name="Priya Patel",
                email="priya@example.com",
                custom_fields={"city": "Pune"},
                tags=["lead_inbound"],
            )
            await repo.create(
                organization_id=self.org_id,
                phone="+919800000003",
                name="Amit Kumar",
                email="amit@example.com",
                custom_fields={"city": "Mumbai"},
                tags=["vip"],
            )

            # Test filter options
            options = await repo.get_filter_options(self.org_id)
            assert "Mumbai" in options["cities"]
            assert "Pune" in options["cities"]
            assert "vip" in options["tags"]
            assert "q4_sale" in options["tags"]

            # Filter by city
            mumbai_leads = await repo.list_for_org(self.org_id, city="Mumbai")
            assert len(mumbai_leads) == 2
            mumbai_count = await repo.count_for_org(self.org_id, city="Mumbai")
            assert mumbai_count == 2

            # Filter by tag
            vip_leads = await repo.list_for_org(self.org_id, tags=["vip"])
            assert len(vip_leads) == 2

            # Filter by search
            search_leads = await repo.list_for_org(self.org_id, search="Priya")
            assert len(search_leads) == 1
            assert search_leads[0].name == "Priya Patel"

        try:
            loop.run_until_complete(run_test())
        finally:
            loop.close()

    def test_http_filter_options_and_listing(self):
        # Create lead via HTTP
        self.client.post("/api/v1/leads", json={
            "phone": "+919999900001",
            "name": "Sunil Verma",
            "custom_fields": {"city": "Bangalore"},
            "tags": ["enterprise"],
        }, headers=self._auth())

        # Test GET /api/v1/leads/filters
        resp = self.client.get("/api/v1/leads/filters", headers=self._auth())
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "cities" in data
        assert "tags" in data
        assert "Bangalore" in data["cities"]
        assert "enterprise" in data["tags"]

        # Test GET /api/v1/leads with city filter
        resp = self.client.get("/api/v1/leads?city=Bangalore", headers=self._auth())
        assert resp.status_code == 200
        leads = resp.json()["leads"]
        assert len(leads) >= 1
        assert leads[0]["custom_fields"].get("city") == "Bangalore"

    def test_search_with_regex_metacharacters(self):
        self.client.post("/api/v1/leads", json={
            "phone": "+919999900001",
            "name": "Sunil Verma",
            "custom_fields": {"city": "Bangalore"},
            "tags": ["enterprise"],
        }, headers=self._auth())

        # Searching phone with '+' or regex brackets should not crash with 500
        resp = self.client.get("/api/v1/leads?search=%2B9199", headers=self._auth())
        assert resp.status_code == 200, resp.text
        assert resp.json()["total"] >= 1

        resp2 = self.client.get("/api/v1/leads?search=[unclosed_bracket", headers=self._auth())
        assert resp2.status_code == 200, resp2.text
        assert resp2.json()["total"] == 0
