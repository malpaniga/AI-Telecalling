"""Daily Provider Pricing and FX Synchronization Service.

Ensures real-time pricing accuracy and loss protection for AI telecalling.
Synchronizes daily USD/INR foreign exchange rates and recalculates effective
rates across STT, LLM, TTS, and Telephony providers with configurable safety margins.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.base import utcnow
from backend.models.pricing import ProviderRateCard, PricingSettings
from backend.repositories.pricing_repo import (
    ProviderRateCardRepository,
    PricingSettingsRepository,
)

log = logging.getLogger("service.pricing_sync")

# ---------------------------------------------------------------------------
# Default Official Vendor Base Rate Cards
# ---------------------------------------------------------------------------
DEFAULT_PROVIDER_DEFINITIONS: List[Dict[str, Any]] = [
    # ── STT (Speech-to-Text) ──
    {
        "provider_name": "sarvam",
        "model_id": "saaras-v3",
        "capability": "stt",
        "display_name": "Sarvam Saaras v3",
        "base_currency": "INR",
        "billing_unit": "audio_minute",
        "base_unit_rate": 0.45,  # ₹0.45 per audio minute
        "notes": "Official Sarvam published pricing: ₹0.45/min for Indic speech.",
    },
    {
        "provider_name": "groq-whisper",
        "model_id": "whisper-large-v3-turbo",
        "capability": "stt",
        "display_name": "Groq Whisper Large v3 Turbo",
        "base_currency": "USD",
        "billing_unit": "audio_minute",
        "base_unit_rate": 0.00185,  # $0.00185 per audio minute
        "notes": "Official Groq pricing: $0.00185/min ultra-low latency whisper.",
    },
    {
        "provider_name": "google-cloud-stt",
        "model_id": "chirp-2",
        "capability": "stt",
        "display_name": "Google Cloud Chirp 2",
        "base_currency": "USD",
        "billing_unit": "audio_minute",
        "base_unit_rate": 0.016,  # $0.016 per audio minute
        "notes": "Google Cloud Speech-to-Text Chirp 2 model.",
    },
    {
        "provider_name": "deepgram",
        "model_id": "nova-2",
        "capability": "stt",
        "display_name": "Deepgram Nova-2",
        "base_currency": "USD",
        "billing_unit": "audio_minute",
        "base_unit_rate": 0.0043,  # $0.0043 per audio minute
        "notes": "Deepgram Nova-2 pay-as-you-go pricing.",
    },
    {
        "provider_name": "faster-whisper",
        "model_id": "faster-whisper-large-v3",
        "capability": "stt",
        "display_name": "Faster-Whisper (Local Runtime)",
        "base_currency": "INR",
        "billing_unit": "audio_minute",
        "base_unit_rate": 0.0,
        "notes": "Self-hosted local model on customer/dedicated server.",
    },
    {
        "provider_name": "ai4bharat-indicconformer",
        "model_id": "indicconformer",
        "capability": "stt",
        "display_name": "AI4Bharat IndicConformer",
        "base_currency": "INR",
        "billing_unit": "audio_minute",
        "base_unit_rate": 0.0,
        "notes": "Open-source self-hosted model.",
    },
    {
        "provider_name": "soniox",
        "model_id": "stt-async-v5",
        "capability": "stt",
        "display_name": "Soniox Speech-to-Text",
        "base_currency": "INR",
        "billing_unit": "audio_minute",
        "base_unit_rate": 0.10,
        "notes": "Official Soniox low-latency speech recognition.",
    },

    # ── LLM (Language Model) ──
    {
        "provider_name": "gemini",
        "model_id": "gemini-2.0-flash-lite",
        "capability": "llm",
        "display_name": "Google Gemini 2.0 Flash Lite",
        "base_currency": "USD",
        "billing_unit": "turn",
        "base_unit_rate": 0.00004,  # ~$0.075/1M in, $0.30/1M out -> ~$0.00004/turn (~₹0.0034)
        "notes": "Gemini 2.0 Flash Lite ultra-low latency & cost token pricing.",
    },
    {
        "provider_name": "groq",
        "model_id": "llama-3.3-70b-versatile",
        "capability": "llm",
        "display_name": "Groq Llama 3.3 70B",
        "base_currency": "USD",
        "billing_unit": "turn",
        "base_unit_rate": 0.00005,  # $0.59/1M in, $0.79/1M out -> ~$0.00005/turn
        "notes": "Groq LPUs hardware accelerated inference.",
    },
    {
        "provider_name": "ollama",
        "model_id": "llama3.2",
        "capability": "llm",
        "display_name": "Ollama (Local Runtime)",
        "base_currency": "INR",
        "billing_unit": "turn",
        "base_unit_rate": 0.0,
        "notes": "Self-hosted Ollama runtime.",
    },
    {
        "provider_name": "sarvam",
        "model_id": "sarvam-105b-conversations",
        "capability": "llm",
        "display_name": "Sarvam 105B Conversations",
        "base_currency": "INR",
        "billing_unit": "turn",
        "base_unit_rate": 0.05,
        "notes": "Official Sarvam conversational 105B model estimated per-turn rate.",
    },

    # ── TTS (Text-to-Speech) ──
    {
        "provider_name": "sarvam",
        "model_id": "bulbul:v3",
        "capability": "tts",
        "display_name": "Sarvam Bulbul v2/v3",
        "base_currency": "INR",
        "billing_unit": "1k_characters",
        "base_unit_rate": 0.18,  # ₹0.18 per 1,000 characters
        "notes": "Official Sarvam published pricing: ₹0.18 per 1k characters.",
    },
    {
        "provider_name": "elevenlabs",
        "model_id": "eleven_multilingual_v2",
        "capability": "tts",
        "display_name": "ElevenLabs Flash v2.5",
        "base_currency": "USD",
        "billing_unit": "1k_characters",
        "base_unit_rate": 0.015,  # $0.015 per 1,000 characters
        "notes": "ElevenLabs Flash v2.5 fast real-time model pricing.",
    },
    {
        "provider_name": "cartesia",
        "model_id": "sonic-english",
        "capability": "tts",
        "display_name": "Cartesia Sonic",
        "base_currency": "USD",
        "billing_unit": "1k_characters",
        "base_unit_rate": 0.075,  # $0.075 per 1,000 characters
        "notes": "Cartesia Sonic high-speed conversational TTS.",
    },
    {
        "provider_name": "google-cloud-tts",
        "model_id": "neural2",
        "capability": "tts",
        "display_name": "Google Cloud Neural2",
        "base_currency": "USD",
        "billing_unit": "1k_characters",
        "base_unit_rate": 0.016,  # $0.016 per 1,000 characters
        "notes": "Google Cloud TTS Neural2 voices.",
    },
    {
        "provider_name": "google-wavenet",
        "model_id": "wavenet",
        "capability": "tts",
        "display_name": "Google Cloud WaveNet",
        "base_currency": "INR",
        "billing_unit": "1k_characters",
        "base_unit_rate": 0.13,
        "notes": "Google Cloud WaveNet neural voices (~$16/1M chars).",
    },
    {
        "provider_name": "piper",
        "model_id": "en-us-lessac-medium",
        "capability": "tts",
        "display_name": "Piper (Local Runtime)",
        "base_currency": "INR",
        "billing_unit": "1k_characters",
        "base_unit_rate": 0.0,
        "notes": "Local lightweight Piper neural TTS.",
    },
    {
        "provider_name": "ai4bharat-indic-tts",
        "model_id": "indic-tts",
        "capability": "tts",
        "display_name": "AI4Bharat Indic-TTS",
        "base_currency": "INR",
        "billing_unit": "1k_characters",
        "base_unit_rate": 0.0,
        "notes": "Open-source self-hosted Indic-TTS.",
    },

    # ── Telephony / Carrier PSTN ──
    {
        "provider_name": "tata-sip",
        "model_id": "airtel-tata-pstn",
        "capability": "telephony",
        "display_name": "Tata / Airtel SIP Trunk",
        "base_currency": "INR",
        "billing_unit": "pstn_minute",
        "base_unit_rate": 0.40,  # ₹0.40 per minute PSTN
        "notes": "Standard Indian cellular & landline interconnect rate.",
    },
    {
        "provider_name": "webrtc",
        "model_id": "browser-audio",
        "capability": "telephony",
        "display_name": "Browser WebRTC",
        "base_currency": "INR",
        "billing_unit": "pstn_minute",
        "base_unit_rate": 0.0,
        "notes": "Free zero-cost browser mic/speaker channel.",
    },
]


class PricingSyncService:
    """Orchestrates daily rate card updates, live FX rates, and loss protection."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.rate_repo = ProviderRateCardRepository(db)
        self.settings_repo = PricingSettingsRepository(db)

    async def fetch_live_fx_rate(self) -> float:
        """Fetch current USD to INR exchange rate from live open FX APIs."""
        # Primary API: open.er-api.com (open, fast, daily update)
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get("https://open.er-api.com/v6/latest/USD")
                if res.status_code == 200:
                    data = res.json()
                    inr = data.get("rates", {}).get("INR")
                    if inr and isinstance(inr, (int, float)) and inr > 50:
                        log.info("fetched live USD/INR FX from open.er-api: %.4f", inr)
                        return float(inr)
        except Exception as exc:
            log.warning("primary FX fetch failed: %s, trying fallback", exc)

        # Fallback API: Frankfurter
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get("https://api.frankfurter.app/latest?from=USD&to=INR")
                if res.status_code == 200:
                    data = res.json()
                    inr = data.get("rates", {}).get("INR")
                    if inr and isinstance(inr, (int, float)) and inr > 50:
                        log.info("fetched live USD/INR FX from Frankfurter: %.4f", inr)
                        return float(inr)
        except Exception as exc:
            log.warning("fallback FX fetch failed: %s", exc)

        # Retain last stored rate or safe conservative default
        settings = await self.settings_repo.get_settings()
        return settings.usd_to_inr_fx_rate or 84.85

    async def sync_all_rates(
        self,
        force_fx_rate: Optional[float] = None,
        force_safety_margin_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Run daily sync of all provider rate cards and update effective rates."""
        settings = await self.settings_repo.get_settings()
        fx_rate = force_fx_rate or await self.fetch_live_fx_rate()
        margin_pct = force_safety_margin_pct or settings.default_safety_margin_pct

        # Update global settings
        await self.settings_repo.update_settings({
            "usd_to_inr_fx_rate": fx_rate,
            "fx_last_updated_at": utcnow(),
            "default_safety_margin_pct": margin_pct,
            "last_daily_sync_at": utcnow(),
        })

        synced_count = 0
        now = utcnow()

        for defn in DEFAULT_PROVIDER_DEFINITIONS:
            # Check if admin had placed an override
            existing = await self.rate_repo.get_by_provider_and_model(
                capability=defn["capability"],
                provider_name=defn["provider_name"],
                model_id=defn["model_id"],
            )

            # Preserve admin override base_unit_rate if set manually
            base_rate = existing.base_unit_rate if (existing and existing.sync_source == "admin_override") else defn["base_unit_rate"]
            card_margin = existing.safety_margin_pct if existing else margin_pct

            # Calculate effective INR rate
            if defn["base_currency"] == "USD":
                effective_inr = base_rate * fx_rate
            else:
                effective_inr = base_rate

            # Derive active cost per second
            # STT: audio_minute -> cost per second of user speech
            # TTS: 1k_chars -> average speaking speed: ~15 chars/sec -> cost per second of speech
            # LLM: per turn -> ~3.5 turns in 60s
            # Telephony: pstn_minute -> cost per connected second
            if defn["capability"] == "stt":
                active_cost_sec = effective_inr / 60.0
                blended_cost_sec = active_cost_sec * (25.0 / 60.0)  # User speaks ~25s in 60s call
            elif defn["capability"] == "tts":
                # 1000 chars = ~66 seconds of speech (~15 chars/sec)
                cost_per_char = effective_inr / 1000.0
                active_cost_sec = cost_per_char * 15.0
                blended_cost_sec = active_cost_sec * (25.0 / 60.0)  # Agent speaks ~25s in 60s call
            elif defn["capability"] == "llm":
                cost_per_turn = effective_inr
                active_cost_sec = cost_per_turn
                blended_cost_sec = (cost_per_turn * 3.5) / 60.0  # 3.5 turns per 60s call
            elif defn["capability"] == "telephony":
                active_cost_sec = effective_inr / 60.0
                blended_cost_sec = active_cost_sec  # Full call connected duration
            else:
                active_cost_sec = 0.0
                blended_cost_sec = 0.0

            # Loss-prevention retail billed rate
            retail_rate_sec = blended_cost_sec * (1.0 + (card_margin / 100.0))

            card = ProviderRateCard(
                provider_name=defn["provider_name"],
                model_id=defn["model_id"],
                capability=defn["capability"],
                display_name=defn["display_name"],
                base_currency=defn["base_currency"],
                billing_unit=defn["billing_unit"],
                base_unit_rate=base_rate,
                fx_rate_usd_inr=fx_rate,
                effective_unit_rate_inr=effective_inr,
                active_cost_per_sec_inr=active_cost_sec,
                blended_cost_per_sec_inr=blended_cost_sec,
                safety_margin_pct=card_margin,
                retail_rate_per_sec_inr=retail_rate_sec,
                last_synced_at=now,
                sync_source=existing.sync_source if existing else "daily_auto_sync",
                notes=defn.get("notes"),
            )
            await self.rate_repo.upsert_rate_card(card)
            synced_count += 1

        log.info("completed daily pricing sync for %d providers with USD/INR=%.4f", synced_count, fx_rate)
        return {
            "status": "ok",
            "synced_count": synced_count,
            "usd_to_inr_fx_rate": fx_rate,
            "safety_margin_pct": margin_pct,
            "synced_at": now.isoformat(),
        }

    async def get_all_rates(self) -> Dict[str, Any]:
        """Return all active provider rate cards, settings, and conversion factors."""
        settings = await self.settings_repo.get_settings()
        cards = await self.rate_repo.list_all()

        # If empty (first boot before sync), trigger a sync immediately
        if not cards:
            await self.sync_all_rates()
            cards = await self.rate_repo.list_all()

        by_capability: Dict[str, List[Dict[str, Any]]] = {
            "stt": [],
            "llm": [],
            "tts": [],
            "telephony": [],
        }

        for c in cards:
            if c.capability in by_capability:
                by_capability[c.capability].append(c.model_dump())

        return {
            "settings": settings.model_dump(),
            "rates_by_capability": by_capability,
            "total_providers_tracked": len(cards),
            "last_synced_at": settings.last_daily_sync_at.isoformat() if settings.last_daily_sync_at else None,
        }

    async def calculate_pipeline_cost(
        self,
        stt_provider: str = "sarvam",
        stt_model: str = "saaras-v3",
        llm_provider: str = "gemini",
        llm_model: str = "gemini-2.0-flash-lite",
        tts_provider: str = "sarvam",
        tts_model: str = "bulbul:v3",
        telephony_provider: str = "webrtc",
        custom_safety_margin_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Compute exact composite pipeline costs per second, minute, and volume tiers."""
        stt_card = await self.rate_repo.get_by_provider_and_model("stt", stt_provider, stt_model)
        llm_card = await self.rate_repo.get_by_provider_and_model("llm", llm_provider, llm_model)
        tts_card = await self.rate_repo.get_by_provider_and_model("tts", tts_provider, tts_model)
        tel_card = await self.rate_repo.get_by_provider_and_model("telephony", telephony_provider, "default")

        settings = await self.settings_repo.get_settings()
        margin_pct = custom_safety_margin_pct if custom_safety_margin_pct is not None else settings.default_safety_margin_pct

        stt_blended = stt_card.blended_cost_per_sec_inr if stt_card else 0.0031
        llm_blended = llm_card.blended_cost_per_sec_inr if llm_card else 0.0002
        tts_blended = tts_card.blended_cost_per_sec_inr if tts_card else 0.0033
        tel_blended = tel_card.blended_cost_per_sec_inr if tel_card else 0.0

        ai_cost_sec = stt_blended + llm_blended + tts_blended
        total_cost_sec = ai_cost_sec + tel_blended

        # Loss-protected retail rate
        loss_protected_rate_sec = total_cost_sec * (1.0 + (margin_pct / 100.0))

        # Guarantee minimum price floor to prevent loss
        final_billable_rate_sec = max(loss_protected_rate_sec, (settings.min_retail_paise_per_sec / 100.0))

        return {
            "components": {
                "stt": {
                    "provider": stt_provider,
                    "model": stt_model,
                    "blended_cost_per_sec_inr": stt_blended,
                    "paise_per_sec": stt_blended * 100,
                },
                "llm": {
                    "provider": llm_provider,
                    "model": llm_model,
                    "blended_cost_per_sec_inr": llm_blended,
                    "paise_per_sec": llm_blended * 100,
                },
                "tts": {
                    "provider": tts_provider,
                    "model": tts_model,
                    "blended_cost_per_sec_inr": tts_blended,
                    "paise_per_sec": tts_blended * 100,
                },
                "telephony": {
                    "provider": telephony_provider,
                    "blended_cost_per_sec_inr": tel_blended,
                    "paise_per_sec": tel_blended * 100,
                },
            },
            "raw_provider_cost_per_sec_inr": total_cost_sec,
            "raw_provider_cost_per_min_inr": total_cost_sec * 60,
            "raw_provider_paise_per_sec": total_cost_sec * 100,
            "safety_margin_pct": margin_pct,
            "safety_buffer_paise_per_sec": (loss_protected_rate_sec - total_cost_sec) * 100,
            "retail_billable_rate_per_sec_inr": final_billable_rate_sec,
            "retail_billable_rate_per_min_inr": final_billable_rate_sec * 60,
            "retail_billable_paise_per_sec": final_billable_rate_sec * 100,
            "projections": {
                "one_minute_call_inr": final_billable_rate_sec * 60,
                "three_minute_call_inr": final_billable_rate_sec * 180,
                "thousand_calls_one_min_inr": final_billable_rate_sec * 60 * 1000,
            },
            "fx_usd_to_inr": settings.usd_to_inr_fx_rate,
            "last_synced_at": settings.last_daily_sync_at.isoformat() if settings.last_daily_sync_at else None,
        }

    async def override_provider_rate(
        self,
        capability: str,
        provider_name: str,
        model_id: str,
        base_unit_rate: float,
        safety_margin_pct: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> ProviderRateCard:
        """Allow admin to instantly override a provider's rate to guard against sudden price hikes."""
        settings = await self.settings_repo.get_settings()
        card = await self.rate_repo.get_by_provider_and_model(capability, provider_name, model_id)
        margin = safety_margin_pct if safety_margin_pct is not None else (card.safety_margin_pct if card else settings.default_safety_margin_pct)
        fx_rate = settings.usd_to_inr_fx_rate

        currency = card.base_currency if card else "INR"
        effective_inr = base_unit_rate * fx_rate if currency == "USD" else base_unit_rate

        if capability == "stt":
            active_sec = effective_inr / 60.0
            blended_sec = active_sec * (25.0 / 60.0)
        elif capability == "tts":
            cost_per_char = effective_inr / 1000.0
            active_sec = cost_per_char * 15.0
            blended_sec = active_sec * (25.0 / 60.0)
        elif capability == "llm":
            active_sec = effective_inr
            blended_sec = (effective_inr * 3.5) / 60.0
        else:
            active_sec = effective_inr / 60.0
            blended_sec = active_sec

        retail_sec = blended_sec * (1.0 + (margin / 100.0))

        updated_card = ProviderRateCard(
            provider_name=provider_name.lower(),
            model_id=model_id.lower(),
            capability=capability.lower(),
            display_name=card.display_name if card else f"{provider_name} {model_id}",
            base_currency=currency,
            billing_unit=card.billing_unit if card else "unit",
            base_unit_rate=base_unit_rate,
            fx_rate_usd_inr=fx_rate,
            effective_unit_rate_inr=effective_inr,
            active_cost_per_sec_inr=active_sec,
            blended_cost_per_sec_inr=blended_sec,
            safety_margin_pct=margin,
            retail_rate_per_sec_inr=retail_sec,
            last_synced_at=utcnow(),
            sync_source="admin_override",
            notes=notes or f"Manual override applied at {utcnow().isoformat()}",
        )
        return await self.rate_repo.upsert_rate_card(updated_card)
