"""Health check logic for all system components."""

import logging

from backend.core.db import ping_db
from backend.core.redis import ping_redis
from backend.config import settings

log = logging.getLogger("health")


async def check_all() -> dict:
    """Run all health checks and return a summary."""
    mongodb_ok = await ping_db()
    redis_ok = await ping_redis()

    # Lightweight provider key presence checks (not actual API calls)
    groq_ok = bool(settings.groq_api_key)
    sarvam_ok = bool(settings.effective_sarvam_key)
    openai_ok = bool(settings.openai_api_key)
    elevenlabs_ok = bool(settings.elevenlabs_api_key)
    razorpay_ok = bool(settings.razorpay_key_id and settings.razorpay_key_secret)
    twilio_ok = bool(settings.twilio_account_sid and settings.twilio_auth_token)
    demo_mode = settings.demo_mode

    # Core services (required for basic operation)
    core_healthy = mongodb_ok and redis_ok

    return {
        "status": "healthy" if core_healthy else "degraded",
        "demo_mode": demo_mode,
        "checks": {
            "mongodb": mongodb_ok,
            "redis": redis_ok,
            "groq_api_key": groq_ok,
            "sarvam_api_key": sarvam_ok,
            "openai_api_key": openai_ok,
            "elevenlabs_api_key": elevenlabs_ok,
            "razorpay": razorpay_ok,
            "twilio": twilio_ok,
        },
    }
