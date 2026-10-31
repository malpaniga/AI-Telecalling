"""Tests for campaign worker dialing from campaign_leads and retry lifecycle."""

import asyncio
from datetime import timedelta
import pytest
import mongomock_motor

from backend.models.base import new_id, utcnow
from backend.models.campaign import Campaign
from backend.services.call_service import CallService
from backend.workers.campaign_worker import CampaignWorker


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class FakeRedis:
    def __init__(self):
        self._data = {}

    async def get(self, key):
        return self._data.get(key)

    async def set(self, key, value, ex=None):
        self._data[key] = str(value)
        return True

    async def incr(self, key):
        val = int(self._data.get(key, 0)) + 1
        self._data[key] = str(val)
        return val

    async def decr(self, key):
        val = max(0, int(self._data.get(key, 0)) - 1)
        self._data[key] = str(val)
        return val

    async def delete(self, *keys):
        for k in keys:
            self._data.pop(k, None)
        return True


class TestCampaignMultiLeadWorker:
    def setup_method(self):
        self.client = mongomock_motor.AsyncMongoMockClient()
        self.db = self.client["test_worker_retries"]
        self.redis = FakeRedis()

    def test_worker_respects_pending_retry_without_completing(self):
        async def _test():
            camp_id = "camp_retry_test"
            org_id = "org_1"
            from backend.services.wallet_service import WalletService
            await WalletService(self.db).grant_bonus(org_id, 1000, "test")

            await self.db.campaigns.insert_one({
                "_id": camp_id,
                "organization_id": org_id,
                "name": "Retry Campaign",
                "status": "running",
                "calling_number": "+911234567890",
                "calling_number_id": "pn_1",
                "agent_id": "ag_1",
                "agent_version": 1,
                "voice_profile_id": "vp_1",
                "voice_profile_version": 1,
                "retry_policy": {"max_attempts": 2, "retry_delay_minutes": 30, "retry_on": ["busy"]},
            })
            # Lead has retry scheduled in 30 minutes
            await self.db.campaign_leads.insert_one({
                "_id": "cl_1",
                "campaign_id": camp_id,
                "organization_id": org_id,
                "lead_id": "lead_1",
                "phone": "+919876543210",
                "status": "callback",
                "attempts": 1,
                "max_attempts": 2,
                "next_attempt_at": utcnow() + timedelta(minutes=30),
            })

            worker = CampaignWorker(self.db, redis=self.redis)
            camp_doc = await self.db.campaigns.find_one({"_id": camp_id})
            campaign = Campaign.model_validate(camp_doc)

            await worker._process_campaign(campaign)

            # Campaign must STILL be running because lead is waiting for retry!
            updated = await self.db.campaigns.find_one({"_id": camp_id})
            assert updated["status"] == "running"

        run(_test())

    def test_call_finalization_schedules_retry(self):
        async def _test():
            camp_id = "camp_finalize_test"
            org_id = "org_1"
            await self.db.campaigns.insert_one({
                "_id": camp_id,
                "organization_id": org_id,
                "name": "Finalize Campaign",
                "status": "running",
                "calling_number": "+911234567890",
                "calling_number_id": "pn_1",
                "agent_id": "ag_1",
                "agent_version": 1,
                "voice_profile_id": "vp_1",
                "voice_profile_version": 1,
                "retry_policy": {"max_attempts": 3, "retry_delay_minutes": 15, "retry_on": ["busy", "no_answer"]},
            })
            await self.db.campaign_leads.insert_one({
                "_id": "cl_2",
                "campaign_id": camp_id,
                "organization_id": org_id,
                "lead_id": "lead_2",
                "phone": "+919876543211",
                "status": "scheduled",
                "attempts": 0,
                "max_attempts": 3,
            })
            call_id = "call_retry_test"
            await self.db.calls.insert_one({
                "_id": call_id,
                "organization_id": org_id,
                "campaign_id": camp_id,
                "lead_id": "lead_2",
                "status": "in_progress",
            })

            call_svc = CallService(self.db, redis=self.redis)
            # Finalize call as busy
            await call_svc.finalize_call(
                call_id=call_id,
                organization_id=org_id,
                status="failed",
                outcome="busy",
            )

            # Check campaign lead was transitioned to callback with next_attempt_at
            cl = await self.db.campaign_leads.find_one({"campaign_id": camp_id, "lead_id": "lead_2"})
            assert cl["status"] == "callback"
            assert cl["attempts"] == 1
            assert cl["next_attempt_at"] is not None

        run(_test())
