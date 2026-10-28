import pytest
from datetime import datetime, timezone, timedelta
import mongomock_motor
from unittest.mock import AsyncMock, patch

from backend.models.base import utcnow
from backend.models.call import Call
from backend.repositories.call_repo import CallRepository
from backend.repositories.wallet_repo import WalletRepository
from backend.services.credit_service import CreditService
from backend.services.call_service import CallService
from backend.services.post_call_service import PostCallService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_db():
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test_credit_release_db"]


@pytest.mark.anyio
async def test_naive_datetime_subtraction_handled(mock_db):
    """
    Demonstrates that timezone normalization prevents TypeError and allows duration calculation.
    """
    c = Call(organization_id="org_tz", started_at=datetime(2026, 10, 28, 6, 0, 0))
    started_at = c.started_at
    if started_at and started_at.tzinfo is None:
        from datetime import timezone as _tz
        started_at = started_at.replace(tzinfo=_tz.utc)

    now = started_at + timedelta(seconds=75)
    duration = max(0, int((now - started_at).total_seconds()))
    assert duration == 75


@pytest.mark.anyio
async def test_vobiz_finalize_settles_and_releases_remaining_credits(mock_db):
    """
    Simulates the ws_vobiz finalization logic with naive datetime from MongoDB.
    5 credits reserved. 45 seconds duration -> 1 credit billed, 4 refunded.
    """
    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_vobiz")
    await wallet_repo.atomic_add(w.id, 10, "total_purchased")

    credit_svc = CreditService(mock_db)
    await credit_svc.reserve("org_vobiz", "call_vb_1", max_credits=5)

    call_repo = CallRepository(mock_db)
    call = Call(
        _id="call_vb_1",
        organization_id="org_vobiz",
        status="connected",
        started_at=datetime(2026, 10, 28, 6, 0, 0),  # naive
        connected_at=datetime(2026, 10, 28, 6, 0, 5),  # naive
        credits_reserved=5,
    )
    await call_repo.insert(call)

    c_doc = await call_repo.find_by_id("call_vb_1")
    ref_dt = c_doc.connected_at or c_doc.started_at
    if ref_dt and ref_dt.tzinfo is None:
        from datetime import timezone as _tz
        ref_dt = ref_dt.replace(tzinfo=_tz.utc)

    now = ref_dt + timedelta(seconds=45)
    duration = max(0, int((now - ref_dt).total_seconds()))

    settle_res = await credit_svc.settle_duration(
        organization_id=c_doc.organization_id,
        call_id=c_doc.id,
        duration_seconds=duration,
    )
    assert settle_res["billed_credits"] == 1
    assert settle_res["refunded_credits"] == 4

    wallet_after = await wallet_repo.find_by_id(w.id)
    assert wallet_after.available_credits == 9
    assert wallet_after.reserved_credits == 0


@pytest.mark.anyio
async def test_post_call_service_zero_credits_releases_reservation(mock_db):
    """
    PostCallService._stage_wallet_settle with actual_credits=0
    must settle and release the hold back to wallet.
    """
    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_pc_zero")
    await wallet_repo.atomic_add(w.id, 10, "total_purchased")

    credit_svc = CreditService(mock_db)
    await credit_svc.reserve("org_pc_zero", "call_pc_0", max_credits=5)

    call_repo = CallRepository(mock_db)
    call = Call(
        _id="call_pc_0",
        organization_id="org_pc_zero",
        status="completed",
        credits_reserved=5,
    )
    await call_repo.insert(call)

    post_svc = PostCallService(mock_db)
    result = {"stages": {}}
    await post_svc._stage_wallet_settle(call, actual_credits=0, organization_id="org_pc_zero", result=result)

    assert result["stages"]["wallet_settle"] != "skipped_zero_credits"
    wallet_after = await wallet_repo.find_by_id(w.id)
    assert wallet_after.available_credits == 10
    assert wallet_after.reserved_credits == 0


@pytest.mark.anyio
async def test_initiate_call_dispatch_failure_releases_credits(mock_db):
    """
    When initiate_call fails during provider dispatch,
    credits must be rolled back / released back to the wallet.
    """
    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_dispatch_fail")
    await wallet_repo.atomic_add(w.id, 10, "total_purchased")

    from backend.models.phone_number import PhoneNumber
    from backend.repositories.phone_number_repo import PhoneNumberRepository
    pn_repo = PhoneNumberRepository(mock_db)
    pn = PhoneNumber(
        number="+911122334455",
        organization_id="org_dispatch_fail",
        provider="vobiz",
        status="assigned",
        provider_metadata={"vobiz_auth_id": "test_id", "vobiz_auth_token": "test_token"},
    )
    await pn_repo.insert(pn)

    call_svc = CallService(mock_db)

    with patch("backend.providers.telephony.vobiz.VobizTelephonyProvider.initiate_call", side_effect=RuntimeError("Vobiz API network error")):
        with pytest.raises(RuntimeError, match="Telephony dispatch failed"):
            await call_svc.initiate_call(
                organization_id="org_dispatch_fail",
                to_number="+919876543210",
                from_number="+911122334455",
                provider="vobiz",
            )

    # All 10 credits should be available again; 0 reserved
    wallet_after = await wallet_repo.find_by_id(w.id)
    assert wallet_after.available_credits == 10
    assert wallet_after.reserved_credits == 0


@pytest.mark.anyio
async def test_settle_with_extended_hold_sums_reservations(mock_db):
    """
    When a call exceeds 5 minutes, extend_hold reserves an extra 5 credits (total 10).
    When the call ends at 6 minutes (6 credits billed), 4 credits should be refunded.
    """
    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_ext_settle")
    await wallet_repo.atomic_add(w.id, 20, "total_purchased")

    credit_svc = CreditService(mock_db)
    await credit_svc.reserve("org_ext_settle", "call_ext_1", max_credits=5)
    await credit_svc.extend_hold("org_ext_settle", "call_ext_1", additional_credits=5)

    wallet_held = await wallet_repo.find_by_id(w.id)
    assert wallet_held.reserved_credits == 10
    assert wallet_held.available_credits == 10

    # Settle 6 minutes (360s)
    settle_res = await credit_svc.settle_duration("org_ext_settle", "call_ext_1", duration_seconds=360)
    assert settle_res["billed_credits"] == 6
    assert settle_res["refunded_credits"] == 4
    assert settle_res["new_available_balance"] == 14

    wallet_after = await wallet_repo.find_by_id(w.id)
    assert wallet_after.available_credits == 14
    assert wallet_after.reserved_credits == 0


@pytest.mark.anyio
async def test_api_hangup_endpoint_releases_credits(mock_db):
    """
    Calling the hangup endpoint on an initiating or running call settles duration and releases reserved credits.
    """
    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_hangup_api")
    await wallet_repo.atomic_add(w.id, 10, "total_purchased")

    credit_svc = CreditService(mock_db)
    await credit_svc.reserve("org_hangup_api", "call_api_hang", max_credits=5)

    call_repo = CallRepository(mock_db)
    call = Call(
        _id="call_api_hang",
        organization_id="org_hangup_api",
        status="initiating",
        provider="mock",
        credits_reserved=5,
    )
    await call_repo.insert(call)

    from backend.api.v1.calls import hangup_call
    from backend.core.auth import CurrentUser

    user = CurrentUser(user_id="user_1", org_id="org_hangup_api", role="owner", email="user@test.com")
    
    with patch("backend.api.v1.calls.get_db", return_value=mock_db):
        res = await hangup_call(call_id="call_api_hang", user=user)

    assert res["status"] == "hangup_signaled"
    wallet_after = await wallet_repo.find_by_id(w.id)
    assert wallet_after.available_credits == 10
    assert wallet_after.reserved_credits == 0
