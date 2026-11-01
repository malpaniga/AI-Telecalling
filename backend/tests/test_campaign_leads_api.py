"""Tests for Campaign Leads API endpoints."""

from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
import mongomock_motor
import pytest

from backend.api.v1.campaigns import router as campaigns_router
from backend.core import db as db_module, redis as redis_module
from backend.core.auth import create_token_pair
from backend.models.base import new_id, utcnow


class TestCampaignLeadsAPI:
    def setup_method(self):
        self.test_app = FastAPI()
        self.test_app.include_router(campaigns_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test_campaign_leads_api"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.delete = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        user_tokens = create_token_pair("user-1", "user@org.com", "customer_admin", "org-1")
        self.token = user_tokens["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_campaign_leads_enroll_and_list(self):
        # 1. Seed campaign & leads in DB
        camp_id = "camp-123"
        lead_id = "lead-456"
        now = utcnow()
        
        # Async setup via run_until_complete
        import asyncio
        loop = asyncio.new_event_loop()
        
        async def _seed():
            await self.mock_db.campaigns.insert_one({
                "_id": camp_id,
                "organization_id": "org-1",
                "name": "Outbound Test",
                "status": "draft",
                "agent_id": "ag_1",
                "agent_version": 1,
                "voice_profile_id": "vp_1",
                "voice_profile_version": 1,
                "calling_number_id": "pn_1",
                "calling_number": "+911800123456",
                "created_at": now,
                "updated_at": now,
            })
            await self.mock_db.leads.insert_one({
                "_id": lead_id,
                "organization_id": "org-1",
                "phone": "+919876543210",
                "name": "Deepak Verma",
                "status": "new",
                "custom_fields": {"city": "Pune"},
                "tags": ["vip"],
                "created_at": now,
                "updated_at": now,
            })
        loop.run_until_complete(_seed())

        # 2. Enroll lead via POST /api/v1/campaigns/{id}/leads
        res = self.client.post(
            f"/api/v1/campaigns/{camp_id}/leads",
            json={"lead_ids": [lead_id]},
            headers=self.headers,
        )
        assert res.status_code == 200
        assert res.json()["enrolled"] == 1

        # 3. List leads via GET /api/v1/campaigns/{id}/leads
        res_list = self.client.get(
            f"/api/v1/campaigns/{camp_id}/leads",
            headers=self.headers,
        )
        assert res_list.status_code == 200
        data = res_list.json()
        assert data["total"] == 1
        assert data["items"][0]["lead_id"] == lead_id
        assert data["items"][0]["name"] == "Deepak Verma"
        assert data["items"][0]["phone"] == "+919876543210"
        assert data["items"][0]["status"] == "new"

        # 4. Remove lead via DELETE /api/v1/campaigns/{id}/leads/{lead_id}
        res_del = self.client.delete(
            f"/api/v1/campaigns/{camp_id}/leads/{lead_id}",
            headers=self.headers,
        )
        assert res_del.status_code == 200
        assert res_del.json()["removed"] is True

        # Verify list is empty
        res_list2 = self.client.get(
            f"/api/v1/campaigns/{camp_id}/leads",
            headers=self.headers,
        )
        assert res_list2.json()["total"] == 0


    def test_campaign_update_and_delete_api(self):
        camp_id = "camp-crud-1"
        now = utcnow()
        import asyncio
        loop = asyncio.new_event_loop()

        async def _seed():
            await self.mock_db.campaigns.insert_one({
                "_id": camp_id,
                "organization_id": "org-1",
                "name": "Draft Campaign",
                "agent_id": "ag-1",
                "agent_version": 1,
                "voice_profile_id": "vp-1",
                "voice_profile_version": 1,
                "calling_number_id": "pn-1",
                "calling_number": "+918000000000",
                "status": "draft",
                "max_concurrent_calls": 1,
                "created_at": now,
                "updated_at": now,
            })
            await self.mock_db.campaign_leads.insert_one({
                "campaign_id": camp_id,
                "lead_id": "lead-crud-1",
                "organization_id": "org-1",
                "phone": "+919876543210",
                "status": "new",
            })
        loop.run_until_complete(_seed())

        # 1. Update Campaign via PATCH /api/v1/campaigns/{id}
        res_patch = self.client.patch(
            f"/api/v1/campaigns/{camp_id}",
            headers=self.headers,
            json={"name": "Renamed Campaign", "max_concurrent_calls": 3},
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["name"] == "Renamed Campaign"
        assert res_patch.json()["max_concurrent_calls"] == 3

        # 2. Delete Campaign via DELETE /api/v1/campaigns/{id}
        res_del = self.client.delete(
            f"/api/v1/campaigns/{camp_id}",
            headers=self.headers,
        )
        assert res_del.status_code == 200
        assert res_del.json()["deleted"] is True

        # 3. Verify GET returns 404
        res_get = self.client.get(
            f"/api/v1/campaigns/{camp_id}",
            headers=self.headers,
        )
        assert res_get.status_code == 404
