import pytest
import mongomock_motor
from backend.repositories.organization_repo import OrganizationRepository
from backend.models.organization import OrganizationSettings
from backend.services.credit_service import CreditService
from backend.repositories.wallet_repo import WalletRepository

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def mock_db():
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test_browser_db"]

@pytest.mark.anyio
async def test_organization_created_with_10_free_tests(mock_db):
    org_repo = OrganizationRepository(mock_db)
    org = await org_repo.create(name="Acme Inc", email="acme@test.com", slug="acme")
    assert org.settings.free_test_sessions_remaining == 10
    assert org.settings.free_test_session_max_minutes == 3
    assert org.settings.max_call_duration_minutes == 7

@pytest.mark.anyio
async def test_admin_grant_free_tests(mock_db):
    org_repo = OrganizationRepository(mock_db)
    org = await org_repo.create(name="Beta Corp", email="beta@test.com", slug="beta")
    assert org.settings.free_test_sessions_remaining == 10

    # Simulate admin granting 5 more tests
    await mock_db.organizations.update_one(
        {"_id": org.id},
        {"$inc": {"settings.free_test_sessions_remaining": 5}}
    )
    updated = await org_repo.find_by_id(org.id)
    assert updated.settings.free_test_sessions_remaining == 15

@pytest.mark.anyio
async def test_free_test_decrement_when_session_starts(mock_db):
    org_repo = OrganizationRepository(mock_db)
    org = await org_repo.create(name="Gamma Inc", email="gamma@test.com", slug="gamma")
    
    # Atomically consume one free test session
    res = await mock_db.organizations.find_one_and_update(
        {"_id": org.id, "settings.free_test_sessions_remaining": {"$gt": 0}},
        {"$inc": {"settings.free_test_sessions_remaining": -1}},
        return_document=True
    )
    assert res is not None
    assert res["settings"]["free_test_sessions_remaining"] == 9
