"""Seed the AI model catalogue with the 12 verified entries for M41.

Run on every startup — idempotent (upserts by provider_name + model_id).
Pricing data is timestamped so staleness warnings can be shown in the UI.
"""

import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.model_directory import AIModelCatalogue
from backend.repositories.model_directory_repo import AIModelCatalogueRepo

log = logging.getLogger("seed.catalogue")


# ---------------------------------------------------------------------------
# Catalogue definitions
# ---------------------------------------------------------------------------

_ENTRIES: list[dict] = [
    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------
    {
        "provider_name": "gemini",
        "model_id": "gemini-2.0-flash-lite",
        "capability": "llm",
        "hosting_mode": "managed_api",
        "supported_languages": ["multilingual"],
        "streaming_supported": True,
        "credential_requirements": ["GEMINI_API_KEY"],
        "setup_requirements": "Create API key at aistudio.google.com",
        "license_spdx": "Proprietary",
        "commercial_use_allowed": True,
        "free_tier_info": {
            "requests_per_day": 1500,
            "tokens_per_minute": 1000000,
            "note": "Verified 2025-Q2; subject to change",
        },
        "free_tier_verified_date": "2025-06-01",
        "pricing_per_minute_usd": None,
        "doc_url": "https://ai.google.dev/gemini-api/docs",
        "model_card_url": None,
        "implementation_status": "supported",
        "notes": (
            "Free tier requires Google account. "
            "Data used for training unless opted out via API settings."
        ),
    },
    {
        "provider_name": "ollama",
        "model_id": "llama3.2",
        "capability": "llm",
        "hosting_mode": "local_runtime",
        "supported_languages": ["multilingual"],
        "streaming_supported": True,
        "credential_requirements": [],
        "setup_requirements": "Install Ollama from ollama.com; run: ollama pull llama3.2",
        "license_spdx": "Meta-Llama-3.2-License",
        "commercial_use_allowed": True,
        "free_tier_info": {
            "note": "Fully local; no API costs. Requires local hardware."
        },
        "free_tier_verified_date": "2025-06-01",
        "pricing_per_minute_usd": 0.0,
        "doc_url": "https://ollama.com",
        "model_card_url": "https://huggingface.co/meta-llama/Llama-3.2-3B",
        "implementation_status": "supported",
        "notes": (
            "Requires Ollama runtime on port 11434. "
            "Min 4 GB RAM for 3B model; 8 GB for 8B model."
        ),
    },
    {
        "provider_name": "groq",
        "model_id": "llama-3.3-70b-versatile",
        "capability": "llm",
        "hosting_mode": "managed_api",
        "supported_languages": ["multilingual"],
        "streaming_supported": True,
        "credential_requirements": ["GROQ_API_KEY"],
        "setup_requirements": "Create API key at console.groq.com",
        "license_spdx": "Meta-Llama-3.3-License",
        "commercial_use_allowed": True,
        "free_tier_info": {
            "requests_per_minute": 30,
            "requests_per_day": 14400,
            "tokens_per_minute": 6000,
            "note": "Verified 2025-Q2; subject to change",
        },
        "free_tier_verified_date": "2025-06-01",
        "pricing_per_minute_usd": None,
        "doc_url": "https://console.groq.com/docs/openai",
        "model_card_url": None,
        "implementation_status": "supported",
        "notes": "Already wired in existing LLMClient. Rate limits apply on free tier.",
    },
    # ------------------------------------------------------------------
    # STT
    # ------------------------------------------------------------------
    {
        "provider_name": "ai4bharat",
        "model_id": "indicconformer-multilingual",
        "capability": "stt",
        "hosting_mode": "self_hosted",
        "supported_languages": ["hi", "ta", "te", "kn", "mr", "bn", "gu", "ml", "pa", "or", "as", "ur"],
        "streaming_supported": False,
        "credential_requirements": [],
        "setup_requirements": (
            "Deploy AI4Bharat IndicConformer server; "
            "see https://github.com/AI4Bharat/NeMo. "
            "Requires GPU (A100 recommended)."
        ),
        "license_spdx": "MIT",
        "commercial_use_allowed": True,
        "free_tier_info": {
            "note": "Self-hosted; no per-call cost. Infrastructure cost applies."
        },
        "free_tier_verified_date": "2025-06-01",
        "pricing_per_minute_usd": 0.0,
        "doc_url": "https://github.com/AI4Bharat/NeMo",
        "model_card_url": "https://huggingface.co/ai4bharat/indicconformer",
        "implementation_status": "experimental",
        "notes": (
            "Adapter not yet implemented. "
            "Self-hosting requires significant infrastructure. MIT licensed."
        ),
    },
    {
        "provider_name": "groq-whisper",
        "model_id": "whisper-large-v3-turbo",
        "capability": "stt",
        "hosting_mode": "managed_api",
        "supported_languages": ["multilingual"],
        "streaming_supported": False,
        "credential_requirements": ["GROQ_API_KEY"],
        "setup_requirements": "Use existing GROQ_API_KEY",
        "license_spdx": "Apache-2.0",
        "commercial_use_allowed": True,
        "free_tier_info": {
            "audio_seconds_per_hour": 7200,
            "note": "Verified 2025-Q2; subject to change",
        },
        "free_tier_verified_date": "2025-06-01",
        "pricing_per_minute_usd": None,
        "doc_url": "https://console.groq.com/docs/speech-text",
        "model_card_url": "https://huggingface.co/openai/whisper-large-v3-turbo",
        "implementation_status": "supported",
        "notes": "Already wired in existing STTClient.",
    },
    {
        "provider_name": "sarvam",
        "model_id": "saaras-v3",
        "capability": "stt",
        "hosting_mode": "managed_api",
        "supported_languages": ["hi", "ta", "te", "kn", "mr", "bn", "gu", "ml", "pa", "en-IN"],
        "streaming_supported": False,
        "credential_requirements": ["SARVAM_API_KEY"],
        "setup_requirements": "Create API key at dashboard.sarvam.ai",
        "license_spdx": "Proprietary",
        "commercial_use_allowed": True,
        "free_tier_info": {
            "note": "Free tier available; contact Sarvam for current quota. Verified 2025-Q2."
        },
        "free_tier_verified_date": "2025-06-01",
        "pricing_per_minute_usd": None,
        "doc_url": "https://docs.sarvam.ai",
        "model_card_url": None,
        "implementation_status": "supported",
        "notes": "Already wired in existing SarvamSTT. Code-mixing (Hinglish) supported.",
    },
    {
        "provider_name": "faster-whisper",
        "model_id": "faster-whisper-large-v3",
        "capability": "stt",
        "hosting_mode": "local_runtime",
        "supported_languages": ["multilingual"],
        "streaming_supported": False,
        "credential_requirements": [],
        "setup_requirements": (
            "pip install faster-whisper; "
            "requires ffmpeg on PATH. CUDA optional for GPU acceleration."
        ),
        "license_spdx": "MIT",
        "commercial_use_allowed": True,
        "free_tier_info": {"note": "Fully local; no API costs."},
        "free_tier_verified_date": "2025-06-01",
        "pricing_per_minute_usd": 0.0,
        "doc_url": "https://github.com/SYSTRAN/faster-whisper",
        "model_card_url": "https://huggingface.co/Systran/faster-whisper-large-v3",
        "implementation_status": "experimental",
        "notes": "Adapter stub created; not yet integrated into call pipeline.",
    },
    # ------------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------------
    {
        "provider_name": "ai4bharat-indicf5",
        "model_id": "indicf5",
        "capability": "tts",
        "hosting_mode": "self_hosted",
        "supported_languages": ["hi", "ta", "te", "kn", "mr", "bn", "gu", "ml", "pa"],
        "streaming_supported": False,
        "credential_requirements": [],
        "setup_requirements": (
            "Deploy AI4Bharat IndicF5 server; "
            "see https://github.com/AI4Bharat/IndicF5. Requires GPU."
        ),
        "license_spdx": "MIT",
        "commercial_use_allowed": True,
        "free_tier_info": {"note": "Self-hosted; no per-call cost."},
        "free_tier_verified_date": "2025-06-01",
        "pricing_per_minute_usd": 0.0,
        "doc_url": "https://github.com/AI4Bharat/IndicF5",
        "model_card_url": "https://huggingface.co/ai4bharat/indicF5",
        "implementation_status": "experimental",
        "notes": (
            "Adapter stub created (NotImplementedError). "
            "Streaming not supported by current architecture."
        ),
    },
    {
        "provider_name": "ai4bharat-indic-tts",
        "model_id": "indic-tts",
        "capability": "tts",
        "hosting_mode": "self_hosted",
        "supported_languages": ["hi", "ta", "te", "kn", "mr", "bn", "gu", "ml", "pa"],
        "streaming_supported": False,
        "credential_requirements": [],
        "setup_requirements": (
            "Deploy Indic TTS server; "
            "see https://github.com/AI4Bharat/Indic-TTS. Requires CPU or GPU."
        ),
        "license_spdx": "MIT",
        "commercial_use_allowed": True,
        "free_tier_info": {"note": "Self-hosted; no per-call cost."},
        "free_tier_verified_date": "2025-06-01",
        "pricing_per_minute_usd": 0.0,
        "doc_url": "https://github.com/AI4Bharat/Indic-TTS",
        "model_card_url": None,
        "implementation_status": "experimental",
        "notes": "Adapter stub created (NotImplementedError).",
    },
    {
        "provider_name": "piper",
        "model_id": "en-us-lessac-medium",
        "capability": "tts",
        "hosting_mode": "local_runtime",
        "supported_languages": ["en"],
        "streaming_supported": False,
        "credential_requirements": [],
        "setup_requirements": (
            "Download model from huggingface.co/rhasspy/piper-voices; "
            "set PIPER_MODEL_PATH in .env"
        ),
        "license_spdx": "MIT",
        "commercial_use_allowed": True,
        "free_tier_info": {"note": "Fully local; no API costs."},
        "free_tier_verified_date": "2025-06-01",
        "pricing_per_minute_usd": 0.0,
        "doc_url": "https://github.com/rhasspy/piper",
        "model_card_url": "https://huggingface.co/rhasspy/piper-voices",
        "implementation_status": "supported",
        "notes": "Already wired in existing PiperEngine. English only.",
    },
    {
        "provider_name": "sarvam",
        "model_id": "bulbul-v3",
        "capability": "tts",
        "hosting_mode": "managed_api",
        "supported_languages": ["hi", "ta", "te", "kn", "mr", "bn", "gu", "ml", "pa", "en-IN"],
        "streaming_supported": True,
        "credential_requirements": ["SARVAM_API_KEY"],
        "setup_requirements": "Create API key at dashboard.sarvam.ai",
        "license_spdx": "Proprietary",
        "commercial_use_allowed": True,
        "free_tier_info": {
            "note": "Free tier available; contact Sarvam for current quota. Verified 2025-Q2."
        },
        "free_tier_verified_date": "2025-06-01",
        "pricing_per_minute_usd": None,
        "doc_url": "https://docs.sarvam.ai",
        "model_card_url": None,
        "implementation_status": "supported",
        "notes": (
            "Already wired in existing SarvamEngine. "
            "Streaming supported via synthesize_stream."
        ),
    },
    {
        "provider_name": "elevenlabs",
        "model_id": "multilingual-v2",
        "capability": "tts",
        "hosting_mode": "managed_api",
        "supported_languages": ["multilingual"],
        "streaming_supported": True,
        "credential_requirements": ["ELEVENLABS_API_KEY"],
        "setup_requirements": "Create API key at elevenlabs.io",
        "license_spdx": "Proprietary",
        "commercial_use_allowed": True,
        "free_tier_info": {
            "credits_per_month": 10000,
            "note": (
                "Verified 2025-Q2; subject to change. "
                "~10 min audio at standard quality."
            ),
        },
        "free_tier_verified_date": "2025-06-01",
        "pricing_per_minute_usd": None,
        "doc_url": "https://elevenlabs.io/docs",
        "model_card_url": None,
        "implementation_status": "experimental",
        "notes": (
            "ElevenLabsTTSProvider exists in backend/providers/tts/elevenlabs.py (M8) "
            "but not wired into call pipeline TTS routing."
        ),
    },
]


async def seed_model_catalogue(db: AsyncIOMotorDatabase) -> None:
    """Upsert all 12 catalogue entries. Safe to call on every startup."""
    repo = AIModelCatalogueRepo(db)
    seeded = 0
    skipped = 0

    for entry_data in _ENTRIES:
        doc = AIModelCatalogue(**entry_data)
        existing = await repo.find_one(
            {"provider_name": doc.provider_name, "model_id": doc.model_id}
        )
        if existing is None:
            await repo.upsert_by_provider_model(doc)
            seeded += 1
        else:
            # Still upsert to keep metadata current
            await repo.upsert_by_provider_model(doc)
            skipped += 1

    log.info(
        "model catalogue seed complete: %d upserted, %d already existed",
        seeded,
        skipped,
    )
