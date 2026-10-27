import pytest
import math
import mongomock_motor
from backend.services.credit_service import CreditService
from backend.repositories.wallet_repo import WalletRepository

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def mock_db():
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test_db"]

@pytest.mark.anyio
async def test_can_start_call_requires_minimum_5_credits(mock_db):
    svc = CreditService(mock_db)
    wallet_repo = WalletRepository(mock_db)
    
    # 4 credits -> cannot start
    w = await wallet_repo.get_or_create("org_4")
    await wallet_repo.atomic_add(w.id, 4, "total_purchased")
    res = await svc.can_start_call("org_4", required_credits=5)
    assert res["can_start"] is False
    assert res["shortfall"] == 1

    # 5 credits -> can start
    w5 = await wallet_repo.get_or_create("org_5")
    await wallet_repo.atomic_add(w5.id, 5, "total_purchased")
    res5 = await svc.can_start_call("org_5", required_credits=5)
    assert res5["can_start"] is True

@pytest.mark.anyio
async def test_settle_duration_ceiling_rounding(mock_db):
    svc = CreditService(mock_db)
    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_settle")
    await wallet_repo.atomic_add(w.id, 20, "total_purchased")

    # Reserve 5 credits
    await svc.reserve("org_settle", "call_1", max_credits=5)
    
    # 45 seconds -> 1 credit billed, 4 refunded, available after = 20 - 1 = 19
    res = await svc.settle_duration("org_settle", "call_1", duration_seconds=45)
    assert res["billed_credits"] == 1
    assert res["refunded_credits"] == 4
    assert res["new_available_balance"] == 19

@pytest.mark.anyio
async def test_settle_duration_zero_bills_zero_credits(mock_db):
    svc = CreditService(mock_db)
    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_zero")
    await wallet_repo.atomic_add(w.id, 10, "total_purchased")

    await svc.reserve("org_zero", "call_zero", max_credits=5)
    # 0 seconds connected -> 0 credits billed, 5 refunded, balance remains 10
    res = await svc.settle_duration("org_zero", "call_zero", duration_seconds=0)
    assert res["billed_credits"] == 0
    assert res["refunded_credits"] == 5
    assert res["new_available_balance"] == 10

@pytest.mark.anyio
async def test_extend_hold_success(mock_db):
    svc = CreditService(mock_db)
    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_ext")
    await wallet_repo.atomic_add(w.id, 20, "total_purchased")

    await svc.reserve("org_ext", "call_ext", max_credits=5)
    # Available was 20 -> 15 after initial reserve
    ext = await svc.extend_hold("org_ext", "call_ext", additional_credits=5)
    assert ext["extended_credits"] == 5
    assert ext["total_reserved_credits"] == 10
    assert ext["new_available_balance"] == 10
