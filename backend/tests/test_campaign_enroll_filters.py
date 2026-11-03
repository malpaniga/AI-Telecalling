"""Tests for Campaign Lead Enrollment by City, Tags, and Status filters."""

import sys
import os
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.api.v1.auth import router as auth_router
from backend.api.v1.campaigns import router as campaigns_router, EnrollCampaignLeadsRequest
from backend.api.v1.leads import router as leads_router
from backend.core import db as db_module, redis as redis_module
from backend.models.base import new_id, utcnow


def _mongomock_available():
    try:
        import mongomock_motor
        return True
    except ImportError:
        return False


SKIP = pytest.mark.skipif(not _mongomock_available(), reason="mongomock_motor not installed")


@SKIP
class TestCampaignEnrollFilters:
    @pytest.fixture(autouse=True)
    def setup(self):
        import mongomock_motor

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(campaigns_router, prefix="/api/v1")
        self.test_app.include_router(leads_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test_campaign_enroll"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        # Signup
        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Enroll Filter Org",
            "org_email": "enroll@org.com",
            "email": "user@enroll.com",
            "password": "EnrollPass1!",
        })
        self.token = r.json()["access_token"]
        self.org_id = r.json()["organization_id"]

    def _auth(self):
        return {"Authorization": f"Bearer {self.token}"}

    def test_enroll_request_schema(self):
        req = EnrollCampaignLeadsRequest(city="Delhi", status="new", tags=["promo"])
        assert req.city == "Delhi"
        assert req.status == "new"
        assert req.tags == ["promo"]

    def test_enroll_campaign_leads_by_city(self):
        import asyncio
        loop = asyncio.new_event_loop()

        async def run_test():
            # Create a mock campaign directly in DB
            camp_id = new_id()
            await self.mock_db["campaigns"].insert_one({
                "_id": camp_id,
                "organization_id": self.org_id,
                "name": "Delhi Outreach",
                "status": "draft",
                "agent_id": "ag_1",
                "agent_version": 1,
                "voice_profile_id": "vp_1",
                "voice_profile_version": 1,
                "calling_number_id": "ph_1",
                "calling_number": "+919876543210",
                "created_at": utcnow(),
                "updated_at": utcnow(),
            })

            # Create 2 leads in Delhi and 1 in Mumbai
            await self.mock_db["leads"].insert_many([
                {
                    "_id": "lead_d1",
                    "organization_id": self.org_id,
                    "phone": "+919111111111",
                    "status": "new",
                    "custom_fields": {"city": "Delhi"},
                    "tags": ["retail"],
                },
                {
                    "_id": "lead_d2",
                    "organization_id": self.org_id,
                    "phone": "+919111111112",
                    "status": "new",
                    "custom_fields": {"city": "Delhi"},
                    "tags": ["wholesale"],
                },
                {
                    "_id": "lead_m1",
                    "organization_id": self.org_id,
                    "phone": "+919111111113",
                    "status": "new",
                    "custom_fields": {"city": "Mumbai"},
                    "tags": ["retail"],
                },
            ])

            # Call enroll endpoint with city=Delhi
            resp = self.client.post(
                f"/api/v1/campaigns/{camp_id}/leads",
                json={"city": "Delhi"},
                headers=self._auth(),
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["enrolled"] == 2

            # Verify campaign_leads has 2 enrolled leads
            enrolled_cursor = self.mock_db["campaign_leads"].find({"campaign_id": camp_id})
            docs = await enrolled_cursor.to_list(10)
            assert len(docs) == 2
            phones = {d["phone"] for d in docs}
            assert "+919111111111" in phones
            assert "+919111111112" in phones
            assert "+919111111113" not in phones

        try:
            loop.run_until_complete(run_test())
        finally:
            loop.close()
