"""M20 tests — Post-Call Processing.

Tests:
1.  Transcript model — turn storage, processing status
2.  TranscriptRepository — create_or_get (idempotent), add_turns, set_processing_result
3.  Tenant isolation — Org A cannot read Org B transcript
4.  _compute_score — slot-based scoring logic
5.  _derive_outcome — outcome from flags/stage/call record
6.  _generate_summary — produces human-readable summary
7.  PostCallService.process — full pipeline runs without error
8.  Pipeline: transcript created and populated
9.  Pipeline: lead status updated after processing
10. Pipeline: campaign counters incremented
11. Pipeline: usage_event written
12. Pipeline: analytics_daily upserted
13. Idempotency — re-running process() does NOT double-count analytics/usage
14. Wallet settlement called (credits deducted once)
15. HTTP: list transcripts, get by call_id, trigger processing
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
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


def _make_redis():
    store: dict = {}
    async def get(key): return store.get(key)
    async def set(key, val, ex=None): store[key] = str(val)
    async def delete(*keys):
        for k in keys: store.pop(k, None)
    async def incr(key):
        store[key] = str(int(store.get(key, 0)) + 1); return int(store[key])
    async def decr(key):
        store[key] = str(max(0, int(store.get(key, 0)) - 1)); return int(store[key])
    async def expire(key, ttl): pass
    r = MagicMock()
    r.get = AsyncMock(side_effect=get)
    r.set = AsyncMock(side_effect=set)
    r.delete = AsyncMock(side_effect=delete)
    r.incr = AsyncMock(side_effect=incr)
    r.decr = AsyncMock(side_effect=decr)
    r.expire = AsyncMock(side_effect=expire)
    r._store = store
    return r


async def _create_call(db, org_id: str, campaign_id=None, lead_id=None,
                       status="completed", outcome=None):
    from backend.repositories.call_repo import CallRepository
    repo = CallRepository(db)
    call = await repo.create(org_id, "+919001000001", "+911800123001",
                              campaign_id=campaign_id, lead_id=lead_id)
    if status != "initiating" or outcome:
        updates = {"status": status}
        if outcome:
            updates["outcome"] = outcome
        await repo.update_by_id(call.id, updates)
    return await repo.find_by_id(call.id)


async def _create_lead(db, org_id: str):
    from backend.repositories.lead_repo import LeadRepository
    return await LeadRepository(db).create(org_id, "+919001000002", name="Test Lead")


async def _create_campaign(db, org_id: str):
    from backend.repositories.campaign_repo import CampaignRepository
    c = await CampaignRepository(db).create(
        organization_id=org_id,
        name="Test Campaign",
        agent_id="agent-1", agent_version=1,
        voice_profile_id="vp-1", voice_profile_version=1,
        calling_number_id="pn-1", calling_number="+911800123001",
    )
    await CampaignRepository(db).transition_status(c.id, org_id, "running")
    return c


# ---------------------------------------------------------------------------
# Test: Models
# ---------------------------------------------------------------------------
class TestTranscriptModel:
    def test_transcript_defaults(self):
        from backend.models.transcript import Transcript
        from backend.models.base import new_id
        t = Transcript(_id=new_id(), organization_id="org-1", call_id="call-1")
        assert t.processing_status == "pending"
        assert t.turn_count == 0
        assert t.score == 0

    def test_turn_model(self):
        from backend.models.transcript import Turn
        from backend.models.base import new_id
        turn = Turn(_id=new_id(), role="user", text="Hello", stage="greeting")
        assert turn.role == "user"
        assert turn.text == "Hello"


# ---------------------------------------------------------------------------
# Test: TranscriptRepository
# ---------------------------------------------------------------------------
@SKIP
class TestTranscriptRepository:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_create_or_get_idempotent(self):
        from backend.repositories.transcript_repo import TranscriptRepository
        repo = TranscriptRepository(self.db)
        async def _t():
            t1 = await repo.create_or_get("org-1", "call-1")
            t2 = await repo.create_or_get("org-1", "call-1")
            # Same document returned both times
            assert t1.id == t2.id
        run(_t())

    def test_add_turns(self):
        from backend.repositories.transcript_repo import TranscriptRepository
        repo = TranscriptRepository(self.db)
        async def _t():
            t = await repo.create_or_get("org-1", "call-turns")
            turns = [
                {"_id": "turn-1", "role": "agent", "text": "Hello", "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00"},
                {"_id": "turn-2", "role": "user", "text": "Hi there", "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00"},
            ]
            await repo.add_turns(t.id, turns)
            updated = await repo.find_by_id(t.id)
            assert updated.turn_count == 2
        run(_t())

    def test_tenant_isolation(self):
        from backend.repositories.transcript_repo import TranscriptRepository
        repo = TranscriptRepository(self.db)
        async def _t():
            await repo.create_or_get("org-A", "call-iso")
            # Org B cannot see org A's transcript
            result = await repo.get_for_call("call-iso", "org-B")
            assert result is None
        run(_t())

    def test_set_processing_result(self):
        from backend.repositories.transcript_repo import TranscriptRepository
        repo = TranscriptRepository(self.db)
        async def _t():
            t = await repo.create_or_get("org-1", "call-result")
            await repo.set_processing_result(
                t.id,
                summary="Short call. Lead interested.",
                qualification={"budget": "50L"},
                score=70,
                outcome="qualified",
            )
            updated = await repo.find_by_id(t.id)
            assert updated.summary == "Short call. Lead interested."
            assert updated.qualification["budget"] == "50L"
            assert updated.score == 70
            assert updated.outcome == "qualified"
            assert updated.processing_status == "completed"
        run(_t())


# ---------------------------------------------------------------------------
# Test: Analysis helpers
# ---------------------------------------------------------------------------
class TestAnalysisHelpers:
    def test_compute_score_all_slots(self):
        from backend.services.post_call_service import _compute_score
        slots = {"budget": "50L", "city": "Mumbai", "timeline": "3 months",
                 "property_type": "3 BHK"}
        score = _compute_score(slots, {"interested": True})
        # 4 slots × 15 = 60 + 10 interest = 70
        assert score == 70

    def test_compute_score_with_booking(self):
        from backend.services.post_call_service import _compute_score
        slots = {"budget": "50L", "city": "Mumbai"}
        score = _compute_score(slots, {"wants_to_book": True, "interested": True})
        # 2 × 15 + 30 booking + 10 interest = 70
        assert score == 70

    def test_compute_score_not_interested_penalty(self):
        from backend.services.post_call_service import _compute_score
        slots = {"budget": "50L"}
        score = _compute_score(slots, {"wants_to_end": True})
        # 15 - 25 = 0 (capped at 0)
        assert score == 0

    def test_compute_score_capped_100(self):
        from backend.services.post_call_service import _compute_score
        slots = {"a": "v", "b": "v", "c": "v", "d": "v", "e": "v", "f": "v"}
        score = _compute_score(slots, {"wants_to_book": True, "interested": True})
        assert score <= 100

    def test_derive_outcome_from_flags(self):
        from backend.services.post_call_service import _derive_outcome
        from backend.models.call import Call
        from backend.models.base import new_id
        call = Call(_id=new_id(), organization_id="o", to_number="+91987")
        assert _derive_outcome({"wants_to_book": True}, "booking", call) == "appointment_set"
        assert _derive_outcome({"wants_to_end": True}, "end", call) == "not_interested"
        assert _derive_outcome({"interested": True}, "qualification", call) == "qualified"

    def test_derive_outcome_uses_call_record(self):
        from backend.services.post_call_service import _derive_outcome
        from backend.models.call import Call
        from backend.models.base import new_id
        call = Call(_id=new_id(), organization_id="o", to_number="+91987",
                    outcome="no_answer", status="no_answer")
        # Call record outcome takes priority
        assert _derive_outcome({}, "greeting", call) == "no_answer"

    def test_generate_summary_with_slots(self):
        from backend.services.post_call_service import _generate_summary
        from backend.models.call import Call
        from backend.models.base import new_id
        turns = [
            {"role": "agent", "text": "Hello"},
            {"role": "user", "text": "Hi"},
        ]
        summary = _generate_summary(turns, {"budget": "50L"}, "qualified", "booking")
        assert summary is not None
        assert "budget" in summary.lower() or "50L" in summary
        assert "qualified" in summary.lower()

    def test_generate_summary_empty_turns(self):
        from backend.services.post_call_service import _generate_summary
        assert _generate_summary([], {}, None, "greeting") is None


# ---------------------------------------------------------------------------
# Test: PostCallService — full pipeline
# ---------------------------------------------------------------------------
@SKIP
class TestPostCallService:
    def setup_method(self):
        self.db = _get_mock_db()
        self.redis = _make_redis()

    def _svc(self):
        from backend.services.post_call_service import PostCallService
        return PostCallService(self.db, redis=self.redis)

    def test_process_creates_transcript(self):
        async def _t():
            call = await _create_call(self.db, "org-1")
            svc = self._svc()
            result = await svc.process(
                call_id=call.id,
                organization_id="org-1",
                turns=[{"_id": "t1", "role": "user", "text": "hi",
                        "created_at": "2026-01-01T00:00:00",
                        "updated_at": "2026-01-01T00:00:00"}],
                call_state={"stage": "greeting", "slots": {}, "flags": {}},
                actual_credits=60,
            )
            assert "error" not in result or result.get("error") is None
            from backend.repositories.transcript_repo import TranscriptRepository
            transcript = await TranscriptRepository(self.db).get_for_call(call.id, "org-1")
            assert transcript is not None
        run(_t())

    def test_process_updates_lead(self):
        async def _t():
            lead = await _create_lead(self.db, "org-2")
            call = await _create_call(self.db, "org-2", lead_id=lead.id)
            svc = self._svc()
            await svc.process(
                call_id=call.id,
                organization_id="org-2",
                call_state={
                    "stage": "booking",
                    "slots": {"budget": "50L"},
                    "flags": {"wants_to_book": True},
                },
                actual_credits=90,
            )
            from backend.repositories.lead_repo import LeadRepository
            updated = await LeadRepository(self.db).find_by_id(lead.id)
            assert updated.status in ("qualified", "not_interested", "contacted",
                                      "callback", "failed")
        run(_t())

    def test_process_creates_usage_event(self):
        async def _t():
            call = await _create_call(self.db, "org-3")
            svc = self._svc()
            await svc.process(
                call_id=call.id,
                organization_id="org-3",
                actual_credits=120,
            )
            usage = await self.db["usage_events"].find_one({
                "call_id": call.id, "event_type": "call_completed"
            })
            assert usage is not None
            assert usage["credits_consumed"] == 120
        run(_t())

    def test_process_updates_analytics(self):
        async def _t():
            call = await _create_call(self.db, "org-4")
            svc = self._svc()
            await svc.process(
                call_id=call.id,
                organization_id="org-4",
                call_state={"stage": "booking", "slots": {}, "flags": {}},
                actual_credits=60,
            )
            from datetime import date
            today = date.today().isoformat()
            analytics = await self.db["analytics_daily"].find_one({
                "organization_id": "org-4", "date": today
            })
            assert analytics is not None
            assert analytics["calls_total"] >= 1
        run(_t())

    def test_process_idempotent_analytics(self):
        """Running process() twice does NOT double-count analytics."""
        async def _t():
            call = await _create_call(self.db, "org-5")
            svc = self._svc()
            await svc.process(call_id=call.id, organization_id="org-5",
                               actual_credits=60)
            await svc.process(call_id=call.id, organization_id="org-5",
                               actual_credits=60)

            from datetime import date
            today = date.today().isoformat()
            analytics = await self.db["analytics_daily"].find_one({
                "organization_id": "org-5", "date": today
            })
            # Should be exactly 1, not 2
            assert analytics["calls_total"] == 1
        run(_t())

    def test_process_idempotent_usage_events(self):
        """Usage event written only once per call."""
        async def _t():
            call = await _create_call(self.db, "org-6")
            svc = self._svc()
            await svc.process(call_id=call.id, organization_id="org-6",
                               actual_credits=60)
            await svc.process(call_id=call.id, organization_id="org-6",
                               actual_credits=60)
            count = await self.db["usage_events"].count_documents({
                "call_id": call.id
            })
            assert count == 1
        run(_t())

    def test_process_campaign_counters(self):
        async def _t():
            campaign = await _create_campaign(self.db, "org-7")
            call = await _create_call(self.db, "org-7", campaign_id=campaign.id)
            svc = self._svc()
            await svc.process(
                call_id=call.id,
                organization_id="org-7",
                call_state={"stage": "booking", "slots": {}, "flags": {"wants_to_book": True}},
                actual_credits=60,
            )
            from backend.repositories.campaign_repo import CampaignRepository
            updated = await CampaignRepository(self.db).find_by_id(campaign.id)
            assert updated.leads_dialed >= 1
        run(_t())

    def test_process_wallet_settlement(self):
        async def _t():
            from backend.services.wallet_service import WalletService
            await WalletService(self.db).grant_bonus("org-8", 500, "test")
            call = await _create_call(self.db, "org-8")
            # Reserve credits first (as would happen at call start)
            from backend.services.credit_service import CreditService
            await CreditService(self.db, redis=self.redis).reserve(
                "org-8", call.id, max_credits=300
            )
            svc = self._svc()
            await svc.process(
                call_id=call.id,
                organization_id="org-8",
                actual_credits=120,
            )
            bal = await WalletService(self.db).get_balance("org-8")
            # 500 - 120 actual = 380 available; reserved should be 0
            assert bal["available_credits"] == 380
            assert bal["reserved_credits"] == 0
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestTranscriptsHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.transcripts import router as transcripts_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(transcripts_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        self.redis = _make_redis()
        redis_module._redis = self.redis

        self.client = TestClient(self.test_app)

        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Transcript Org",
            "org_email": "transcript@org.com",
            "email": "user@transcript.com",
            "password": "TransPass1!",
        })
        self.token = r.json()["access_token"]
        self.org_id = r.json()["organization_id"]

    def _auth(self): return {"Authorization": f"Bearer {self.token}"}

    def test_list_transcripts_empty(self):
        resp = self.client.get("/api/v1/transcripts", headers=self._auth())
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_transcript_not_found(self):
        resp = self.client.get("/api/v1/transcripts/nonexistent-call",
                               headers=self._auth())
        assert resp.status_code == 404

    def test_process_call_creates_transcript(self):
        # Create a call record first
        call = run(_create_call(self.mock_db, self.org_id))
        resp = self.client.post(
            f"/api/v1/transcripts/{call.id}/process",
            json={
                "turns": [],
                "call_state": {"stage": "qualification",
                               "slots": {"budget": "50L"}, "flags": {}},
                "actual_credits": 60,
            },
            headers=self._auth(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "stages" in data
        assert data["call_id"] == call.id

    def test_get_transcript_after_processing(self):
        call = run(_create_call(self.mock_db, self.org_id))
        self.client.post(
            f"/api/v1/transcripts/{call.id}/process",
            json={"turns": [], "call_state": {"stage": "greeting",
                                               "slots": {}, "flags": {}},
                  "actual_credits": 0},
            headers=self._auth(),
        )
        resp = self.client.get(f"/api/v1/transcripts/{call.id}",
                               headers=self._auth())
        assert resp.status_code == 200
        data = resp.json()
        assert data["call_id"] == call.id

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/v1/transcripts")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
