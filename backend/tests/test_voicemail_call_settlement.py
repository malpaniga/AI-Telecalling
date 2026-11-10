import pytest
from datetime import datetime, timezone, timedelta
import mongomock_motor
from backend.models.base import utcnow
from backend.models.call import Call
from backend.models.campaign import Campaign, RetryPolicy
from backend.repositories.call_repo import CallRepository
from backend.repositories.campaign_repo import CampaignRepository
from backend.repositories.wallet_repo import WalletRepository
from backend.services.credit_service import CreditService
from backend.services.call_service import CallService

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def mock_db():
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test_voicemail_settlement_db"]

@pytest.mark.anyio
async def test_voicemail_settles_duration_under_1_min_to_1_credit(mock_db):
    """
    Voicemail disconnected in 18 seconds:
    5 credits reserved -> 1 credit billed (for actual talk time under 1 min), 4 credits refunded.
    """
    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_vm_test")
    await wallet_repo.atomic_add(w.id, 10, "total_purchased")

    credit_svc = CreditService(mock_db)
    await credit_svc.reserve("org_vm_test", "call_vm_1", max_credits=5)

    call_repo = CallRepository(mock_db)
    now = utcnow()
    call = Call(
        _id="call_vm_1",
        organization_id="org_vm_test",
        status="connected",
        started_at=now - timedelta(seconds=20),
        connected_at=now - timedelta(seconds=18),
        credits_reserved=5,
    )
    await call_repo.insert(call)

    call_svc = CallService(mock_db)
    res = await call_svc.finalize_call(
        call_id="call_vm_1",
        organization_id="org_vm_test",
        status="completed",
        outcome="voicemail",
        duration_s=18,
    )

    assert res["outcome"] == "voicemail"
    assert res["duration_s"] == 18
    assert res["credits_consumed"] == 1

    wallet_after = await wallet_repo.find_by_id(w.id)
    # Started with 10 credits -> 1 billed, 9 available, 0 reserved
    assert wallet_after.available_credits == 9
    assert wallet_after.reserved_credits == 0

@pytest.mark.anyio
async def test_voicemail_reschedules_campaign_lead_to_callback(mock_db):
    """
    When a call finishes with outcome='voicemail', the campaign lead
    should be updated to 'callback' and scheduled for retry.
    """
    camp_repo = CampaignRepository(mock_db)
    camp = await camp_repo.create(
        organization_id="org_vm_retry",
        name="Voicemail Retry Campaign",
        agent_id="agent_1",
        agent_version=1,
        voice_profile_id="vp_1",
        voice_profile_version=1,
        calling_number_id="pn_1",
        calling_number="+918064262028",
        retry_policy={"max_attempts": 3, "retry_delay_minutes": 45, "retry_on": ["no_answer", "busy", "failed", "voicemail"]},
    )

    lead_id = "lead_vm_1"
    await mock_db["campaign_leads"].insert_one({
        "_id": "cl_1",
        "campaign_id": camp.id,
        "lead_id": lead_id,
        "phone": "+919403220099",
        "status": "scheduled",
        "attempts": 0,
    })

    call_repo = CallRepository(mock_db)
    call = await call_repo.create(
        call_id="call_camp_vm_1",
        organization_id="org_vm_retry",
        to_number="+919403220099",
        from_number="+918064262028",
        campaign_id=camp.id,
        lead_id=lead_id,
        credits_reserved=5,
    )

    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_vm_retry")
    await wallet_repo.atomic_add(w.id, 10, "total_purchased")
    credit_svc = CreditService(mock_db)
    await credit_svc.reserve("org_vm_retry", call.id, max_credits=5)

    call_svc = CallService(mock_db)
    await call_svc.finalize_call(
        call_id=call.id,
        organization_id="org_vm_retry",
        status="completed",
        outcome="voicemail",
        duration_s=12,
    )

    # Verify CampaignLead status is 'callback'
    cl = await mock_db["campaign_leads"].find_one({"_id": "cl_1"})
    assert cl["status"] == "callback"
    assert cl["attempts"] == 1
    assert cl["next_attempt_at"] is not None
