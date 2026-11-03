"""Test campaign call lifecycle, finalization, slot release, and auto-completion."""

import asyncio
from unittest.mock import MagicMock
import pytest

from backend.models.base import new_id
from backend.repositories.campaign_repo import CampaignRepository
from backend.repositories.lead_repo import LeadRepository
from backend.repositories.call_repo import CallRepository
from backend.services.campaign_service import CampaignService
from backend.services.call_service import CallService


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

    async def expire(self, key, seconds):
        return True

    async def decr(self, key):
        val = max(0, int(self._data.get(key, 0)) - 1)
        self._data[key] = str(val)
        return val

    async def delete(self, *keys):
        for k in keys:
            self._data.pop(k, None)
        return True


@SKIP
class TestCampaignCallCompletion:
    def setup_method(self):
        import mongomock_motor
        self.client = mongomock_motor.AsyncMongoMockClient()
        self.db = self.client["test_campaign_completion"]
        self.redis = FakeRedis()
        self.camp_repo = CampaignRepository(self.db)
        self.lead_repo = LeadRepository(self.db)
        self.call_repo = CallRepository(self.db)
        self.camp_svc = CampaignService(self.db, redis=self.redis)
        self.call_svc = CallService(self.db, redis=self.redis)

    async def _setup_data(self, org_id="org-test", num_leads=1):
        # Seed wallet credits via WalletService
        from backend.services.wallet_service import WalletService
        await WalletService(self.db).grant_bonus(org_id, 1000, "test")
        # Seed phone number
        pn_id = new_id()
        await self.db.phone_numbers.insert_one({
            "_id": pn_id,
            "organization_id": org_id,
            "number": "+911800123456",
            "status": "assigned",
            "provider": "mock",
        })
        # Seed leads
        leads = []
        for i in range(num_leads):
            lead = await self.lead_repo.create(org_id, f"+91987654321{i}", name=f"Lead {i}")
            leads.append(lead)

        # Create campaign
        campaign = await self.camp_svc.create_campaign(
            organization_id=org_id,
            name="Single Lead Campaign",
            agent_id="agent-1",
            agent_version=1,
            voice_profile_id="vp-1",
            voice_profile_version=1,
            calling_number_id=pn_id,
            calling_number="+911800123456",
            max_concurrent_calls=1,
        )
        return campaign, leads

    def test_campaign_call_finalization_updates_counters_and_completes(self):
        """When the only lead in a campaign is called and finished:
        1. Concurrency slot is released.
        2. Campaign counters (dialed, completed) increment.
        3. Campaign status transitions to 'completed'.
        """
        async def _t():
            campaign, leads = await self._setup_data(org_id="org-c1", num_leads=1)

            # Start campaign
            started = await self.camp_svc.start_campaign(campaign.id, "org-c1", skip_preflight=True)
            assert started.status == "running"
            assert started.total_leads == 1

            # Simulate acquiring slot & initiating call
            slot_ok = await self.camp_svc.acquire_call_slot(campaign.id)
            assert slot_ok is True
            active = await self.camp_svc.get_active_call_count(campaign.id)
            assert active == 1

            # Initiate call
            res = await self.call_svc.initiate_call(
                organization_id="org-c1",
                to_number=leads[0].phone,
                from_number=campaign.calling_number,
                campaign_id=campaign.id,
                lead_id=leads[0].id,
                slot_already_acquired=True,
            )
            call_id = res["call_id"]

            # Active calls should still be 1 (not double-incremented)
            active = await self.camp_svc.get_active_call_count(campaign.id)
            assert active == 1

            # Finalize call (simulating hangup)
            fin = await self.call_svc.finalize_call(
                call_id=call_id,
                organization_id="org-c1",
                status="completed",
                outcome="qualified",
                turn_count=4,
                score=80,
            )
            assert fin["status"] == "completed"

            # Check campaign state
            updated_camp = await self.camp_svc.get_campaign(campaign.id, "org-c1")
            assert updated_camp.leads_dialed == 1
            assert updated_camp.leads_completed == 1
            assert updated_camp.leads_connected == 1
            # Active calls should be 0
            active_after = await self.camp_svc.get_active_call_count(campaign.id)
            assert active_after == 0
            # Campaign should be completed!
            assert updated_camp.status == "completed"

        run(_t())

    def test_finalize_call_is_idempotent(self):
        """Calling finalize_call twice does not double-increment counters or release slots twice."""
        async def _t():
            campaign, leads = await self._setup_data(org_id="org-c2", num_leads=2)
            await self.camp_svc.start_campaign(campaign.id, "org-c2", skip_preflight=True)

            await self.camp_svc.acquire_call_slot(campaign.id)
            res = await self.call_svc.initiate_call(
                organization_id="org-c2",
                to_number=leads[0].phone,
                from_number=campaign.calling_number,
                campaign_id=campaign.id,
                lead_id=leads[0].id,
                slot_already_acquired=True,
            )
            call_id = res["call_id"]

            # Finalize once
            await self.call_svc.finalize_call(call_id, "org-c2", status="completed", outcome="qualified")
            camp1 = await self.camp_svc.get_campaign(campaign.id, "org-c2")
            assert camp1.leads_dialed == 1
            assert camp1.leads_completed == 1

            # Finalize again (duplicate webhook / duplicate event)
            await self.call_svc.finalize_call(call_id, "org-c2", status="completed", outcome="qualified")
            camp2 = await self.camp_svc.get_campaign(campaign.id, "org-c2")
            assert camp2.leads_dialed == 1
            assert camp2.leads_completed == 1

        run(_t())

    def test_finalize_call_enriches_already_finalized_call_with_post_call_evaluation(self):
        """When carrier hangup webhook finalizes first (outcome=contacted, score=0, summary=None),
        a subsequent CallSession.finalize call properly enriches the call and lead with score,
        summary, qualification, and updated outcome without double-incrementing campaign counters."""
        async def _t():
            campaign, leads = await self._setup_data(org_id="org-c2b", num_leads=2)
            await self.camp_svc.start_campaign(campaign.id, "org-c2b", skip_preflight=True)

            await self.camp_svc.acquire_call_slot(campaign.id)
            res = await self.call_svc.initiate_call(
                organization_id="org-c2b",
                to_number=leads[0].phone,
                from_number=campaign.calling_number,
                campaign_id=campaign.id,
                lead_id=leads[0].id,
                slot_already_acquired=True,
            )
            call_id = res["call_id"]

            # 1. Carrier hangup webhook arrives first
            await self.call_svc.finalize_call(
                call_id, "org-c2b",
                status="completed",
                outcome="contacted",
                duration_s=47,
                score=0,
                summary=None,
            )
            call1 = await self.call_repo.get_for_org(call_id, "org-c2b")
            assert call1.status == "completed"
            assert call1.outcome == "contacted"
            assert call1.score == 0
            assert call1.summary is None
            camp1 = await self.camp_svc.get_campaign(campaign.id, "org-c2b")
            assert camp1.leads_dialed == 1
            assert camp1.leads_completed == 1

            # 2. CallSession.finalize finishes 1s later with post-call evaluation
            await self.call_svc.finalize_call(
                call_id, "org-c2b",
                status="completed",
                outcome="qualified",
                score=55,
                summary="Customer stated electricity bill is ~₹1000-2000.",
                qualification={"monthly_bill": "₹1000-2000"},
            )
            call2 = await self.call_repo.get_for_org(call_id, "org-c2b")
            assert call2.status == "completed"
            assert call2.outcome == "qualified"
            assert call2.score == 55
            assert call2.summary == "Customer stated electricity bill is ~₹1000-2000."
            assert call2.qualification == {"monthly_bill": "₹1000-2000"}

            # Campaign counters must not double-increment
            camp2 = await self.camp_svc.get_campaign(campaign.id, "org-c2b")
            assert camp2.leads_dialed == 1
            assert camp2.leads_completed == 1

            # Lead record must be updated with qualified status and score
            lead_repo = self.call_svc.lead_repo
            updated_lead = await lead_repo.find_by_id(leads[0].id)
            assert updated_lead.status == "qualified"
            assert updated_lead.score == 55
            assert updated_lead.qualification == {"monthly_bill": "₹1000-2000"}

        run(_t())

    def test_call_session_finalize_integrates_with_campaign(self, monkeypatch):
        """CallSession.finalize() directly finalizes the SaaS call without hitting legacy repo,
        updating campaign counters, releasing slots, and completing the campaign.
        """
        async def _t():
            campaign, leads = await self._setup_data(org_id="org-c3", num_leads=1)
            await self.camp_svc.start_campaign(campaign.id, "org-c3", skip_preflight=True)

            await self.camp_svc.acquire_call_slot(campaign.id)
            res = await self.call_svc.initiate_call(
                organization_id="org-c3",
                to_number=leads[0].phone,
                from_number=campaign.calling_number,
                campaign_id=campaign.id,
                lead_id=leads[0].id,
                slot_already_acquired=True,
            )
            call_id = res["call_id"]

            from backend.memory import repository as mem_repo
            monkeypatch.setattr(mem_repo, "get_db", lambda: self.db)

            from backend.core import redis as core_redis
            monkeypatch.setattr(core_redis, "get_redis", lambda: self.redis)

            import sys
            if "groq" not in sys.modules:
                sys.modules["groq"] = MagicMock()
            if "onnxruntime" not in sys.modules:
                sys.modules["onnxruntime"] = MagicMock()

            # Mock transport, stt, engine, tts, store
            transport = MagicMock()
            stt = MagicMock()
            engine = MagicMock()
            tts = MagicMock()
            store = MagicMock()
            async def _dummy_del(k): return None
            store.delete = _dummy_del

            from backend.call_session import CallSession
            session = CallSession(
                transport=transport,
                stt=stt,
                engine=engine,
                tts=tts,
                store=store,
                call_id=call_id,
            )
            session.latencies = [150, 200]
            session.state = {"slots": {"budget": "50L"}, "flags": {"interested": True}, "stage": "pitch"}

            # Finalize via CallSession
            await session.finalize()

            camp = await self.camp_svc.get_campaign(campaign.id, "org-c3")
            assert camp.leads_dialed == 1
            assert camp.leads_connected == 1
            assert camp.leads_completed == 1
            assert camp.status == "completed"

            active = await self.camp_svc.get_active_call_count(campaign.id)
            assert active == 0

        run(_t())
