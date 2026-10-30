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
        "implementation_status": "unavailable",
        "notes": (
            "LOCAL-ONLY: Requires Ollama runtime on port 11434. "
            "Cannot be activated in cloud-only deployment mode. "
            "Use groq or gemini for managed cloud LLM inference."
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
        "notes": "Deprecated on free tier by Groq. Requires enterprise or paid tier. Use openai/gpt-oss-20b for free tier.",
    },
    {
        "provider_name": "sarvam",
        "model_id": "sarvam-105b-conversations",
        "capability": "llm",
        "hosting_mode": "managed_api",
        "supported_languages": ["hi-IN", "ta-IN", "te-IN", "kn-IN", "mr-IN", "bn-IN", "gu-IN", "ml-IN", "pa-IN", "en-IN", "multilingual"],
        "streaming_supported": True,
        "credential_requirements": ["SARVAM_API_KEY"],
        "setup_requirements": "Create API key at dashboard.sarvam.ai",
        "license_spdx": "Proprietary",
        "commercial_use_allowed": True,
        "free_tier_info": {
            "note": "Free tier available; contact Sarvam for current quota. Verified 2026-Q1."
        },
        "free_tier_verified_date": "2026-01-01",
        "pricing_per_minute_usd": None,
        "doc_url": "https://docs.sarvam.ai",
        "model_card_url": None,
        "implementation_status": "supported",
        "notes": (
            "Sarvam 105B conversational dialogue model (MoE) fine-tuned specifically "
            "for voice agents, chatbots, and low-latency multi-turn conversations across Indian languages."
        ),
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
        "supported_languages": ["mr-IN", "hi-IN", "en-IN", "gu-IN", "ta-IN", "te-IN", "kn-IN", "ml-IN", "pa-IN", "bn-IN", "od-IN"],
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
        "model_id": "bulbul:v3",
        "capability": "tts",
        "hosting_mode": "managed_api",
        "supported_languages": ["mr-IN", "hi-IN", "en-IN", "gu-IN", "ta-IN", "te-IN", "kn-IN", "ml-IN", "pa-IN", "bn-IN", "od-IN"],
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
        "model_id": "eleven_multilingual_v2",
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
        "implementation_status": "supported",
        "notes": (
            "ElevenLabsTTSProviderV2 implemented in M42 using official elevenlabs SDK. "
            "Configure voice_id via admin provider config. "
            "Admin must set a valid voice_id from their ElevenLabs account. "
            "ELEVENLABS_API_KEY required."
        ),
    },
]

# Additional verified managed TTS models. The provider-facing identifiers are
# deliberately kept identical to the official API model IDs.
_TTS_MODEL_ADDITIONS = [
    ("sarvam", "bulbul:v4-flash", "Sarvam Bulbul v4 Flash — latest managed model with persona voices."),
    ("elevenlabs", "eleven_v4", "ElevenLabs v4 TTS."),
    ("elevenlabs", "eleven_v4_turbo", "ElevenLabs v4 Turbo TTS."),
    ("elevenlabs", "eleven_v3", "ElevenLabs v3 TTS."),
    ("elevenlabs", "eleven_multilingual_v1", "ElevenLabs Multilingual v1 TTS."),
    ("elevenlabs", "eleven_monolingual_v1", "ElevenLabs English v1 TTS."),
    ("elevenlabs", "eleven_flash_v2_5", "ElevenLabs Flash v2.5 TTS."),
    ("elevenlabs", "eleven_flash_v2", "ElevenLabs Flash v2 TTS."),
    ("elevenlabs", "eleven_turbo_v2_5", "ElevenLabs Turbo v2.5 TTS."),
    ("elevenlabs", "eleven_turbo_v2", "ElevenLabs Turbo v2 TTS."),
]

for _provider, _model, _note in _TTS_MODEL_ADDITIONS:
    _ENTRIES.append({
        "provider_name": _provider, "model_id": _model, "capability": "tts",
        "hosting_mode": "managed_api", "supported_languages": ["multilingual"] if _provider == "elevenlabs" else ["bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN", "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN"],
        "streaming_supported": True, "credential_requirements": ["ELEVENLABS_API_KEY"] if _provider == "elevenlabs" else ["SARVAM_API_KEY"],
        "setup_requirements": "Configure an API key and compatible voice in Super Admin.", "license_spdx": "Proprietary",
        "commercial_use_allowed": True, "free_tier_info": None, "free_tier_verified_date": None,
        "pricing_per_minute_usd": None, "doc_url": "https://elevenlabs.io/docs/models" if _provider == "elevenlabs" else "https://docs.sarvam.ai/api-reference/text-to-speech/convert",
        "model_card_url": None, "implementation_status": "supported", "notes": _note,
    })

# ---------------------------------------------------------------------------
# Additional verified LLM and STT models
# ---------------------------------------------------------------------------
_LLM_MODEL_ADDITIONS = [
    (
        "groq",
        "openai/gpt-oss-20b",
        "Recommended Groq reasoning model (~270ms latency) on Groq LPU inference.",
        "https://console.groq.com/docs/models",
        ["GROQ_API_KEY"],
        "Apache-2.0",
    ),
    (
        "groq",
        "openai/gpt-oss-120b",
        "Large high-capacity reasoning model on Groq LPU inference.",
        "https://console.groq.com/docs/models",
        ["GROQ_API_KEY"],
        "Apache-2.0",
    ),
    (
        "groq",
        "qwen/qwen3.8-27b",
        "Ultra-fast low-latency (~65ms) reasoning model on Groq LPU inference.",
        "https://console.groq.com/docs/models",
        ["GROQ_API_KEY"],
        "Apache-2.0",
    ),
    (
        "groq",
        "llama-3.1-8b-instant",
        "Fast 8B instant model on Groq.",
        "https://console.groq.com/docs/openai",
        ["GROQ_API_KEY"],
        "Meta-Llama-3.1-License",
    ),
    (
        "gemini",
        "gemini-3.1-flash-lite",
        "Google Gemini 3.1 Flash Lite model.",
        "https://ai.google.dev/gemini-api/docs",
        ["GEMINI_API_KEY"],
        "Proprietary",
    ),
    (
        "gemini",
        "gemini-3.5-flash-lite",
        "Google Gemini 3.5 Flash Lite model.",
        "https://ai.google.dev/gemini-api/docs",
        ["GEMINI_API_KEY"],
        "Proprietary",
    ),
    (
        "gemini",
        "gemini-3.5-flash",
        "Google Gemini 3.5 Flash model — high-intelligence, fast general-purpose.",
        "https://ai.google.dev/gemini-api/docs",
        ["GEMINI_API_KEY"],
        "Proprietary",
    ),
    (
        "gemini",
        "gemini-3.8-flash",
        "Google Gemini 3.8 Flash model.",
        "https://ai.google.dev/gemini-api/docs",
        ["GEMINI_API_KEY"],
        "Proprietary",
    ),
]

for _provider, _model, _note, _doc, _creds, _license in _LLM_MODEL_ADDITIONS:
    _ENTRIES.append({
        "provider_name": _provider,
        "model_id": _model,
        "capability": "llm",
        "hosting_mode": "managed_api",
        "supported_languages": ["multilingual"],
        "streaming_supported": True,
        "credential_requirements": _creds,
        "setup_requirements": f"Configure API key for {_provider} in Super Admin.",
        "license_spdx": _license,
        "commercial_use_allowed": True,
        "free_tier_info": {"note": "Active production model tier."},
        "free_tier_verified_date": "2026-01-01",
        "pricing_per_minute_usd": None,
        "doc_url": _doc,
        "model_card_url": None,
        "implementation_status": "supported",
        "notes": _note,
    })

_STT_MODEL_ADDITIONS = [
    ("sarvam", "saaras:v4", "Sarvam Saaras v4 STT model. High accuracy Indian language transcription."),
    ("sarvam", "saaras:v4-turbo", "Sarvam Saaras v4 Turbo STT model. Optimized for low-latency voice pipeline."),
]

for _provider, _model, _note in _STT_MODEL_ADDITIONS:
    _ENTRIES.append({
        "provider_name": _provider,
        "model_id": _model,
        "capability": "stt",
        "hosting_mode": "managed_api",
        "supported_languages": ["mr-IN", "hi-IN", "en-IN", "gu-IN", "ta-IN", "te-IN", "kn-IN", "ml-IN", "pa-IN", "bn-IN", "od-IN"],
        "streaming_supported": False,
        "credential_requirements": ["SARVAM_API_KEY"],
        "setup_requirements": "Configure SARVAM_API_KEY in Super Admin.",
        "license_spdx": "Proprietary",
        "commercial_use_allowed": True,
        "free_tier_info": {"note": "Free tier available; contact Sarvam for current quota."},
        "free_tier_verified_date": "2026-01-01",
        "pricing_per_minute_usd": None,
        "doc_url": "https://docs.sarvam.ai",
        "model_card_url": None,
        "implementation_status": "supported",
        "notes": _note,
    })

# ---------------------------------------------------------------------------
# M42 additions — appended to keep seed idempotent with M41 data
# ---------------------------------------------------------------------------
_M42_ENTRIES: list[dict] = [
    {
        "provider_name": "google-cloud-stt",
        "model_id": "chirp_2",
        "capability": "stt",
        "hosting_mode": "managed_api",
        "supported_languages": [
            "hi-IN", "mr-IN", "te-IN", "ta-IN", "kn-IN",
            "gu-IN", "pa-IN", "bn-IN", "en-IN", "en-US",
            "or-IN", "as-IN", "ur-IN", "ml-IN",
        ],
        "streaming_supported": False,
        "credential_requirements": ["GOOGLE_APPLICATION_CREDENTIALS_JSON"],
        "setup_requirements": (
            "Create a Google Cloud service account with roles/speech.client. "
            "Download JSON key, paste contents into admin credential store. "
            "Enable Speech-to-Text API at console.cloud.google.com."
        ),
        "license_spdx": "Proprietary",
        "commercial_use_allowed": True,
        "free_tier_info": {
            "hours_per_month": 1,
            "note": (
                "First 60 minutes/month free for Chirp 2 (verified 2025-Q3). "
                "Subject to Google Cloud pricing changes."
            ),
        },
        "free_tier_verified_date": "2025-09-01",
        "pricing_per_minute_usd": 0.016,
        "doc_url": "https://cloud.google.com/speech-to-text/v2/docs",
        "model_card_url": None,
        "implementation_status": "supported",
        "notes": (
            "M42: GoogleCloudSTTProvider implemented using google-cloud-speech SDK. "
            "Batch transcription only; streaming STT over gRPC is a separate milestone. "
            "Hindi (hi-IN) and Marathi (mr-IN) verified supported by Chirp 2. "
            "Service account JSON stored encrypted via credential store."
        ),
    },
]


async def seed_model_catalogue(db: AsyncIOMotorDatabase) -> None:
    """Upsert the 12 M41 catalogue entries. Safe to call on every startup."""
    repo = AIModelCatalogueRepo(db)
    seeded = 0

    for entry_data in _ENTRIES:
        doc = AIModelCatalogue(**entry_data)
        await repo.upsert_by_provider_model(doc)
        seeded += 1

    log.info("M41 model catalogue seed complete: %d upserted", seeded)


async def seed_m42_catalogue(db: AsyncIOMotorDatabase) -> None:
    """Upsert M42 additional catalogue entries (Google Cloud STT etc.)."""
    repo = AIModelCatalogueRepo(db)
    seeded = 0

    for entry_data in _M42_ENTRIES:
        doc = AIModelCatalogue(**entry_data)
        await repo.upsert_by_provider_model(doc)
        seeded += 1

    log.info("M42 model catalogue seed complete: %d upserted", seeded)
