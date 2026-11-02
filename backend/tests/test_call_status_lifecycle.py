import asyncio
import mongomock_motor
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.repositories.call_repo import CallRepository


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_vobiz_ring_webhook_updates_status_to_ringing():
    async def _test():
        db = mongomock_motor.AsyncMongoMockClient()["test_db"]
        call_repo = CallRepository(db)
        call = await call_repo.create(
            organization_id="org_test_ring",
            to_number="+919403220099",
            from_number="+918064262028",
            provider="vobiz",
            credits_reserved=5,
        )
        assert call.status == "initiating"

        with patch("backend.telephony.vobiz.get_db", return_value=db):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"/vobiz/ring?call_id={call.id}",
                    data={"CallStatus": "ringing", "CallUUID": "uuid-123"},
                )
                assert resp.status_code == 200

        updated = await call_repo.find_by_id(call.id)
        assert updated.status == "ringing"

    run(_test())


def test_vobiz_hangup_webhook_unanswered_settles_and_updates_status():
    async def _test():
        db = mongomock_motor.AsyncMongoMockClient()["test_db"]
        call_repo = CallRepository(db)
        call = await call_repo.create(
            organization_id="org_test_hangup",
            to_number="+919403220099",
            from_number="+918064262028",
            provider="vobiz",
            credits_reserved=5,
        )
        await call_repo.mark_ringing(call.id)

        with patch("backend.telephony.vobiz.get_db", return_value=db):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"/vobiz/hangup?call_id={call.id}",
                    data={
                        "CallStatus": "no-answer",
                        "HangupCause": "NO_ANSWER",
                        "Duration": "0",
                        "CallUUID": "uuid-456",
                    },
                )
                assert resp.status_code == 200

        updated = await call_repo.find_by_id(call.id)
        assert updated.status == "no_answer"
        assert updated.outcome == "no_answer"
        assert updated.duration_s == 0
        assert updated.credits_consumed == 0

    run(_test())


def test_vobiz_hangup_busy_updates_status():
    async def _test():
        db = mongomock_motor.AsyncMongoMockClient()["test_db"]
        call_repo = CallRepository(db)
        call = await call_repo.create(
            organization_id="org_test_busy",
            to_number="+919403220099",
            from_number="+918064262028",
            provider="vobiz",
            credits_reserved=5,
        )

        with patch("backend.telephony.vobiz.get_db", return_value=db):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"/vobiz/hangup?call_id={call.id}",
                    data={
                        "CallStatus": "busy",
                        "HangupCause": "USER_BUSY",
                        "Duration": "0",
                        "CallUUID": "uuid-789",
                    },
                )
                assert resp.status_code == 200

        updated = await call_repo.find_by_id(call.id)
        assert updated.status == "busy"
        assert updated.duration_s == 0
        assert updated.credits_consumed == 0

    run(_test())
