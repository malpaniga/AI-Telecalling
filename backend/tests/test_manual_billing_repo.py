import pytest
import mongomock_motor
from backend.repositories.billing_repo import (
    PlatformBillingSettingsRepository,
    ManualSubscriptionRequestRepository,
)

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def mock_db():
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test_db"]

@pytest.mark.anyio
async def test_billing_settings_repo_defaults_and_update(mock_db):
    repo = PlatformBillingSettingsRepository(mock_db)
    settings = await repo.get()
    assert settings.payment_mode in ("manual", "razorpay")
    assert settings.admin_upi_id != ""

    updated = await repo.update(payment_mode="manual", admin_upi_id="test@upi", admin_payee_name="Test Payee")
    assert updated.payment_mode == "manual"
    assert updated.admin_upi_id == "test@upi"
    assert updated.admin_payee_name == "Test Payee"

@pytest.mark.anyio
async def test_manual_subscription_request_lifecycle(mock_db):
    repo = ManualSubscriptionRequestRepository(mock_db)
    req = await repo.create(
        organization_id="org-1",
        user_id="user-1",
        user_email="user@org.com",
        org_name="Org One",
        plan_id="plan-1",
        plan_slug="starter",
        plan_name="Starter",
        billing_cycle="monthly",
        amount_paise=99900,
        utr_number="UTR1234567890",
        payer_note="Paid via GPay",
    )
    assert req.status == "pending"
    assert req.utr_number == "UTR1234567890"

    # Pending lookup
    pending = await repo.find_pending_for_org("org-1")
    assert pending is not None
    assert pending.id == req.id

    # UTR duplicate lookup
    existing_utr = await repo.find_by_utr("UTR1234567890")
    assert existing_utr is not None
    assert existing_utr.id == req.id

    # Approve
    await repo.set_status(req.id, "approved", reviewed_by="admin-1")
    refreshed = await repo.find_by_id(req.id)
    assert refreshed.status == "approved"
    assert refreshed.reviewed_by == "admin-1"
