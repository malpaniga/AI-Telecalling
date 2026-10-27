import pytest
import mongomock_motor
from backend.repositories.organization_repo import OrganizationRepository
from backend.repositories.wallet_repo import WalletRepository
from backend.services.credit_service import CreditService
from backend.services.call_service import CallService, DEFAULT_RESERVE_CREDITS

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def mock_db():
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test_e2e_credit_db"]

@pytest.mark.anyio
async def test_full_minute_credit_and_trial_lifecycle(mock_db):
    org_repo = OrganizationRepository(mock_db)
    wallet_repo = WalletRepository(mock_db)
    credit_svc = CreditService(mock_db)
    call_svc = CallService(mock_db)

    # 1. Organization Creation with Defaults
    org = await org_repo.create(name="Apex Solutions", email="apex@test.com", slug="apex")
    assert org.settings.free_test_sessions_remaining == 10
    assert org.settings.free_test_session_max_minutes == 3
    assert org.settings.max_call_duration_minutes == 7

    # 2. Pre-flight Phone Call Check on 0 Balance
    check = await credit_svc.can_start_call(org.id, required_credits=5)
    assert check["can_start"] is False
    assert check["required_credits"] == 5

    with pytest.raises(ValueError, match="Insufficient credits"):
        await call_svc.initiate_call(
            organization_id=org.id,
            to_number="+919876543210",
            from_number="+911144556677",
            provider="mock"
        )

    # 3. Buy Calling Pack (100 Minutes)
    wallet = await wallet_repo.get_or_create(org.id)
    await wallet_repo.atomic_add(wallet.id, 100, "total_purchased")
    updated_wallet = await wallet_repo.get_or_create(org.id)
    assert updated_wallet.available_credits == 100

    # 4. Initiate Phone Call: 5-Credit Hold
    assert DEFAULT_RESERVE_CREDITS == 5
    reserve_res = await credit_svc.reserve(org.id, "call_test_1", max_credits=5)
    assert reserve_res["reserved_credits"] == 5
    assert reserve_res["new_available_balance"] == 95

    # 5. Call Ends at 45 seconds -> Ceiling round bills 1 credit, refunds 4
    settle_res = await credit_svc.settle_duration(org.id, "call_test_1", duration_seconds=45)
    assert settle_res["billed_credits"] == 1
    assert settle_res["refunded_credits"] == 4
    assert settle_res["new_available_balance"] == 99

    # Verify wallet ledger
    txns = await mock_db.wallet_transactions.find({"organization_id": org.id}).to_list(10)
    assert len(txns) >= 2  # reserve and consume
    consume_txn = next(t for t in txns if t["transaction_type"] == "consume")
    assert consume_txn["credits_delta"] == -1
    assert consume_txn["balance_after"] == 99
    assert "Call billed: 1 min" in consume_txn["description"]

    # 6. In-Browser Free Test Session Consumption
    res = await mock_db.organizations.find_one_and_update(
        {"_id": org.id, "settings.free_test_sessions_remaining": {"$gt": 0}},
        {"$inc": {"settings.free_test_sessions_remaining": -1}},
        return_document=True
    )
    assert res["settings"]["free_test_sessions_remaining"] == 9

    # Calling balance remains untouched at 99
    wallet_after_test = await wallet_repo.get_or_create(org.id)
    assert wallet_after_test.available_credits == 99

    # 7. Admin Grants 5 More Free Test Sessions
    await mock_db.organizations.update_one(
        {"_id": org.id},
        {"$inc": {"settings.free_test_sessions_remaining": 5}}
    )
    reloaded_org = await org_repo.find_by_id(org.id)
    assert reloaded_org.settings.free_test_sessions_remaining == 14

    # 8. Unconnected Call (0 Seconds) Bills 0 Credits
    await credit_svc.reserve(org.id, "call_unconnected", max_credits=5)
    w_held = await wallet_repo.get_or_create(org.id)
    assert w_held.available_credits == 94

    zero_res = await credit_svc.settle_duration(org.id, "call_unconnected", duration_seconds=0)
    assert zero_res["billed_credits"] == 0
    assert zero_res["refunded_credits"] == 5
    assert zero_res["new_available_balance"] == 99

    w_final = await wallet_repo.get_or_create(org.id)
    assert w_final.available_credits == 99
    assert w_final.reserved_credits == 0
