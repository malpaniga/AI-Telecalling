"""Tests for dynamic pricing sync, daily FX update, and loss protection."""

import asyncio
from unittest.mock import AsyncMock, patch
from mongomock_motor import AsyncMongoMockClient

from backend.services.pricing_sync_service import PricingSyncService
from backend.repositories.pricing_repo import ProviderRateCardRepository, PricingSettingsRepository


def run(coro):
    return asyncio.run(coro)


def get_mock_db():
    client = AsyncMongoMockClient()
    return client["test_pricing_db"]


def test_pricing_sync_initial_seed():
    db = get_mock_db()
    svc = PricingSyncService(db)

    async def scenario():
        # Mock FX fetch to return exact 85.00
        with patch.object(svc, "fetch_live_fx_rate", new_callable=AsyncMock, return_value=85.00):
            result = await svc.sync_all_rates(force_safety_margin_pct=15.0)

        assert result["status"] == "ok"
        assert result["usd_to_inr_fx_rate"] == 85.00
        assert result["safety_margin_pct"] == 15.0
        assert result["synced_count"] > 10

        # Verify Sarvam STT rate
        rate_repo = ProviderRateCardRepository(db)
        sarvam_stt = await rate_repo.get_by_provider_and_model("stt", "sarvam", "saaras-v3")
        assert sarvam_stt is not None
        assert sarvam_stt.base_unit_rate == 0.45
        assert sarvam_stt.base_currency == "INR"
        assert abs(sarvam_stt.active_cost_per_sec_inr - (0.45 / 60)) < 1e-5
        # 25s user speech in 60s call: 0.0075 * 25 / 60 = 0.003125
        assert abs(sarvam_stt.blended_cost_per_sec_inr - 0.003125) < 1e-5

    run(scenario())


def test_pipeline_cost_calculation():
    db = get_mock_db()
    svc = PricingSyncService(db)

    async def scenario():
        with patch.object(svc, "fetch_live_fx_rate", new_callable=AsyncMock, return_value=85.00):
            await svc.sync_all_rates(force_safety_margin_pct=20.0)

        cost = await svc.calculate_pipeline_cost(
            stt_provider="sarvam",
            stt_model="saaras-v3",
            llm_provider="gemini",
            llm_model="gemini-2.0-flash-lite",
            tts_provider="sarvam",
            tts_model="bulbul:v3",
            telephony_provider="webrtc",
        )

        assert cost["components"]["stt"]["provider"] == "sarvam"
        assert cost["raw_provider_cost_per_sec_inr"] > 0
        # Retail rate must include the 20% safety margin buffer to protect against loss!
        assert cost["retail_billable_rate_per_sec_inr"] > cost["raw_provider_cost_per_sec_inr"]
        margin_diff = cost["retail_billable_rate_per_sec_inr"] - cost["raw_provider_cost_per_sec_inr"]
        assert margin_diff > 0

    run(scenario())


def test_admin_manual_override():
    db = get_mock_db()
    svc = PricingSyncService(db)

    async def scenario():
        with patch.object(svc, "fetch_live_fx_rate", new_callable=AsyncMock, return_value=85.00):
            await svc.sync_all_rates()

        # Admin receives notification that Sarvam hiked prices to ₹0.60/min
        card = await svc.override_provider_rate(
            capability="stt",
            provider_name="sarvam",
            model_id="saaras-v3",
            base_unit_rate=0.60,
            safety_margin_pct=25.0,
            notes="Official price increase effective immediately",
        )

        assert card.base_unit_rate == 0.60
        assert card.sync_source == "admin_override"
        assert card.safety_margin_pct == 25.0
        assert card.active_cost_per_sec_inr == 0.01  # 0.60 / 60 = 0.01

    run(scenario())
