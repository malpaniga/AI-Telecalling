"""M42 runtime wiring tests.

The production change these tests protect: active encrypted cloud-provider
configurations must construct the same provider interfaces consumed by a call,
and local/self-hosted providers must never become active in cloud-only mode.
"""

import asyncio
from datetime import datetime, timezone

import mongomock_motor
import pytest


def run(coro):
    return asyncio.run(coro)


def test_runtime_loads_active_gemini_from_encrypted_configuration():
    """A rotated credential must not be selected over the current active one."""
    from backend.core.secrets import credential_store
    from backend.services.provider_runtime import CloudProviderRuntime

    async def scenario():
        db = mongomock_motor.AsyncMongoMockClient().m42_runtime
        await db["provider_configurations"].insert_one({
            "_id": "gemini-config", "capability": "llm", "provider_name": "gemini",
            "model_id": "gemini-2.0-flash-lite", "is_active": True,
            "is_fallback": False, "extra_params": {},
        })
        await db["provider_credentials"].insert_many([
            {"_id": "old", "provider_name": "gemini", "rotated_at": datetime.now(timezone.utc),
             "encrypted_value": credential_store.encrypt("old-key"), "key_hint": "-key", "created_by": "admin"},
            {"_id": "current", "provider_name": "gemini", "rotated_at": None,
             "encrypted_value": credential_store.encrypt("current-key"), "key_hint": "-key", "created_by": "admin"},
        ])

        runtime = CloudProviderRuntime(db)
        provider = await runtime.load_provider("llm")

        assert provider.provider_name == "gemini"
        assert provider.model == "gemini-2.0-flash-lite"

    run(scenario())


def test_runtime_rejects_local_provider_even_if_database_marks_it_active():
    """A corrupt/manual DB edit cannot route inference to Ollama or another local engine."""
    from backend.services.provider_runtime import CloudProviderRuntime

    async def scenario():
        db = mongomock_motor.AsyncMongoMockClient().m42_runtime
        await db["provider_configurations"].insert_one({
            "_id": "ollama-config", "capability": "llm", "provider_name": "ollama",
            "model_id": "llama3.2", "is_active": True, "is_fallback": False,
            "extra_params": {},
        })
        with pytest.raises(ValueError, match="cloud-only"):
            await CloudProviderRuntime(db).load_provider("llm")

    run(scenario())


def test_activation_rejects_local_provider_after_successful_test_record():
    """Successful historical testing must not bypass cloud-only activation policy."""
    from backend.core.auth import CurrentUser
    from backend.models.model_directory import ProviderConfiguration
    from backend.services.model_directory_service import ModelDirectoryService

    async def scenario():
        db = mongomock_motor.AsyncMongoMockClient().m42_runtime
        await db["provider_configurations"].insert_one(
            ProviderConfiguration(
                _id="piper-config", capability="tts", provider_name="piper",
                model_id="en-us-lessac-medium", last_test_result="ok",
            ).to_mongo()
        )
        user = CurrentUser(
            user_id="admin", email="admin@example.com", role="platform_admin", org_id=None
        )
        with pytest.raises(ValueError, match="cloud-only"):
            await ModelDirectoryService(db).activate_provider("piper-config", user)

    run(scenario())
