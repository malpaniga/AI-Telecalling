import pytest
from backend.models.organization import OrganizationSettings
from backend.services.wallet_service import DEFAULT_CALLING_PACKS

def test_organization_settings_defaults():
    settings = OrganizationSettings()
    assert settings.max_call_duration_minutes == 7
    assert settings.free_test_sessions_remaining == 10
    assert settings.free_test_session_max_minutes == 3

def test_calling_packs_minute_denominations():
    starter = next(p for p in DEFAULT_CALLING_PACKS if p["slug"] == "starter-pack")
    assert starter["credits"] == 100
    assert starter["price_paise"] == 99900

    growth = next(p for p in DEFAULT_CALLING_PACKS if p["slug"] == "growth-pack")
    assert growth["credits"] == 500
    assert growth["bonus_credits"] == 50
    assert growth["price_paise"] == 399900

    pro = next(p for p in DEFAULT_CALLING_PACKS if p["slug"] == "pro-pack")
    assert pro["credits"] == 1000
    assert pro["bonus_credits"] == 150
    assert pro["price_paise"] == 699900
