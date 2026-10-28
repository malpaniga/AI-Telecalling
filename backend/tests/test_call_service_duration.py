import pytest
import mongomock_motor
from backend.services.call_service import CallService, DEFAULT_RESERVE_CREDITS
from backend.services.credit_service import CreditService
from backend.repositories.wallet_repo import WalletRepository
from backend.api.v1.calls import InitiateCallRequest

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def mock_db():
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test_call_db"]

@pytest.mark.anyio
async def test_call_service_uses_5_credit_default():
    assert DEFAULT_RESERVE_CREDITS == 5
    req = InitiateCallRequest(to_number="+919876543210", from_number="+911144556677")
    assert req.reserve_credits == 5

@pytest.mark.anyio
async def test_initiate_call_fails_if_under_5_credits(mock_db):
    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_low")
    await wallet_repo.atomic_add(w.id, 4, "total_purchased")

    call_svc = CallService(mock_db)
    with pytest.raises(ValueError, match="Insufficient credits"):
        await call_svc.initiate_call(
            organization_id="org_low",
            to_number="+919876543210",
            from_number="+911144556677",
            provider="mock"
        )
