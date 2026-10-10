"""M41 AI Models Directory — 15 acceptance test cases.

All network calls are mocked/patched. Tests that require mongomock_motor are
skipped when the package is not installed.

Pattern: def run(coro): loop=asyncio.new_event_loop(); return loop.run_until_complete(coro)
"""

import asyncio
import importlib.util
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_HAS_MONGOMOCK = importlib.util.find_spec("mongomock_motor") is not None

_SKIP_IF_NO_MONGOMOCK = pytest.mark.skipif(
    not _HAS_MONGOMOCK, reason="mongomock_motor not installed"
)


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_platform_user(role: str = "platform_admin"):
    from backend.core.auth import CurrentUser
    return CurrentUser(
        user_id="test-user-001",
        email="admin@test.com",
        role=role,
        org_id=None,
    )


# ---------------------------------------------------------------------------
# Test 1 — catalogue_search_and_capability_filter
# ---------------------------------------------------------------------------

@_SKIP_IF_NO_MONGOMOCK
def test_catalogue_search_and_capability_filter():
    """[mock] Seed 12 entries, verify filtering by capability and text search."""
    import mongomock_motor
    from backend.services.model_catalogue_seed import seed_model_catalogue
    from backend.services.model_directory_service import ModelDirectoryService

    async def scenario():
        db = mongomock_motor.AsyncMongoMockClient()["test"]
        await seed_model_catalogue(db)

        svc = ModelDirectoryService(db)

        # All entries
        all_entries = await svc.list_catalogue()
        assert len(all_entries) == 12, f"Expected 12 entries, got {len(all_entries)}"

        # Filter by capability=tts
        tts_entries = await svc.list_catalogue(capability="tts")
        assert len(tts_entries) == 5, f"Expected 5 TTS entries, got {len(tts_entries)}"
        for e in tts_entries:
            assert e["capability"] == "tts"

        # Filter by capability=llm
        llm_entries = await svc.list_catalogue(capability="llm")
        assert len(llm_entries) == 3, f"Expected 3 LLM entries, got {len(llm_entries)}"

        # Search for groq
        groq_entries = await svc.list_catalogue(search="groq")
        assert len(groq_entries) >= 1
        for e in groq_entries:
            text = (e["provider_name"] + e["model_id"] + (e["notes"] or "")).lower()
            assert "groq" in text

        # Search for ollama — llama3.2 must be present
        ollama_entries = await svc.list_catalogue(search="ollama")
        model_ids = [e["model_id"] for e in ollama_entries]
        assert "llama3.2" in model_ids, f"llama3.2 not found in ollama results: {model_ids}"

    run(scenario())


# ---------------------------------------------------------------------------
# Test 2 — provider_connection_valid_credentials
# ---------------------------------------------------------------------------

@_SKIP_IF_NO_MONGOMOCK
def test_provider_connection_valid_credentials():
    """[mock] Connect groq-whisper with valid credential; verify config stored correctly."""
    import mongomock_motor
    from backend.services.model_catalogue_seed import seed_model_catalogue
    from backend.services.model_directory_service import ModelDirectoryService
    from backend.repositories.model_directory_repo import ProviderCredentialRepo

    async def scenario():
        db = mongomock_motor.AsyncMongoMockClient()["test"]
        await seed_model_catalogue(db)

        svc = ModelDirectoryService(db)
        user = _make_platform_user()

        req = {
            "capability": "stt",
            "provider_name": "groq-whisper",
            "model_id": "whisper-large-v3-turbo",
        }
        result = await svc.connect_provider(req, "test-key-1234", user)

        # is_active must default to False
        assert result["is_active"] is False
        assert result["provider_name"] == "groq-whisper"
        assert result["capability"] == "stt"

        # Credential hint must be last 4 chars of "test-key-1234"
        cred_repo = ProviderCredentialRepo(db)
        creds = await cred_repo.find_by_provider("groq-whisper")
        assert len(creds) == 1
        assert creds[0].key_hint == "1234"

        # encrypted_value must not contain the plaintext
        ev = creds[0].encrypted_value
        assert b"test-key-1234" not in ev
        # plaintext must not be present in stored doc when round-tripped
        raw = await db["provider_credentials"].find_one({"provider_name": "groq-whisper"})
        assert "test-key-1234" not in str(raw)

    run(scenario())


# ---------------------------------------------------------------------------
# Test 3 — provider_connection_invalid_empty_credential
# ---------------------------------------------------------------------------

@_SKIP_IF_NO_MONGOMOCK
def test_provider_connection_invalid_empty_credential():
    """[mock] Empty credential for a provider requiring one raises ValueError."""
    import mongomock_motor
    from backend.services.model_catalogue_seed import seed_model_catalogue
    from backend.services.model_directory_service import ModelDirectoryService

    async def scenario():
        db = mongomock_motor.AsyncMongoMockClient()["test"]
        await seed_model_catalogue(db)

        svc = ModelDirectoryService(db)
        user = _make_platform_user()

        req = {
            "capability": "stt",
            "provider_name": "groq-whisper",
            "model_id": "whisper-large-v3-turbo",
        }
        try:
            await svc.connect_provider(req, "", user)
            assert False, "Expected ValueError for empty credential"
        except ValueError as exc:
            assert "credential" in str(exc).lower() or "required" in str(exc).lower()

    run(scenario())


# ---------------------------------------------------------------------------
# Test 4 — secret_masking
# ---------------------------------------------------------------------------

@_SKIP_IF_NO_MONGOMOCK
def test_secret_masking():
    """[mock] list_credentials returns key_hint only — never encrypted_value or plaintext."""
    import mongomock_motor
    from backend.services.model_catalogue_seed import seed_model_catalogue
    from backend.services.model_directory_service import ModelDirectoryService
    from backend.core.secrets import credential_store

    async def scenario():
        db = mongomock_motor.AsyncMongoMockClient()["test"]
        await seed_model_catalogue(db)

        svc = ModelDirectoryService(db)
        user = _make_platform_user()
        plaintext = "my-secret-api-key-xyz"

        await svc.connect_provider(
            {"capability": "stt", "provider_name": "groq-whisper", "model_id": "whisper-large-v3-turbo"},
            plaintext,
            user,
        )

        creds = await svc.list_credentials("groq-whisper")
        assert len(creds) == 1
        cred_dict = creds[0]

        # Must have key_hint
        assert "key_hint" in cred_dict
        assert cred_dict["key_hint"] == "-xyz"

        # Must NOT expose encrypted_value or plaintext
        assert "encrypted_value" not in cred_dict
        assert plaintext not in str(cred_dict)

        # Round-trip decrypt must work correctly via credential_store
        from backend.repositories.model_directory_repo import ProviderCredentialRepo
        cred_repo = ProviderCredentialRepo(db)
        stored = await cred_repo.find_current("groq-whisper")
        decrypted = credential_store.decrypt(stored.encrypted_value)
        assert decrypted == plaintext

    run(scenario())


# ---------------------------------------------------------------------------
# Test 5 — authorization_enforcement
# ---------------------------------------------------------------------------

@_SKIP_IF_NO_MONGOMOCK
def test_authorization_enforcement():
    """[mock] org-scoped user gets PermissionError from require_platform dependency."""
    import mongomock_motor
    from backend.core.auth import CurrentUser
    from backend.core.rbac import require_platform

    # Test that require_platform raises PermissionError for org-scoped roles
    async def scenario():
        db = mongomock_motor.AsyncMongoMockClient()["test"]

        org_user = CurrentUser(
            user_id="org-user-001",
            email="user@org.com",
            role="organization_admin",
            org_id="org-123",
        )

        # require_platform builds a dependency; we call its inner _check directly
        dep_fn = require_platform("platform_owner", "platform_admin")
        # Get the inner check function (it's an async function returned by the factory)
        # We simulate calling it with our org user
        # The inner function expects a CurrentUser via Depends — inject it manually
        from backend.core.auth import PermissionError as AuthPermissionError

        class FakeDepResolver:
            async def __call__(self):
                return org_user

        try:
            # Invoke the dependency check directly
            check = dep_fn.__wrapped__ if hasattr(dep_fn, "__wrapped__") else None
            # Call the inner _check function directly
            inner = None
            # Access the closure — require_platform returns _check which is an async fn
            # We test it directly
            await dep_fn(user=org_user)
            assert False, "Expected PermissionError"
        except (AuthPermissionError, Exception) as exc:
            # PermissionError from auth is an HTTPException with 403
            from fastapi import HTTPException
            if isinstance(exc, HTTPException):
                assert exc.status_code == 403
            elif isinstance(exc, AssertionError):
                raise
            else:
                # Some other exception — still pass if it's a permission-related error
                assert "permission" in str(exc).lower() or "platform" in str(exc).lower() or "role" in str(exc).lower()

    run(scenario())


# ---------------------------------------------------------------------------
# Test 6 — local_runtime_detection_ollama_unreachable
# ---------------------------------------------------------------------------

def test_local_runtime_detection_ollama_unreachable():
    """[mock] Patched httpx raises ConnectError → test_llm returns status=unavailable."""
    import httpx
    from backend.services.model_test_service import ModelTestService

    async def scenario():
        svc = ModelTestService()

        # Patch OllamaLLMClient.is_runtime_reachable to return False
        with patch(
            "backend.agent.llm.OllamaLLMClient.is_runtime_reachable",
            new_callable=AsyncMock,
            return_value=False,
        ):
            result = await svc.test_llm("ollama", "llama3.2", credential=None)

        assert result["status"] in ("unavailable", "error"), f"Unexpected status: {result}"
        assert "runtime" in result.get("error", "").lower() or "reachable" in result.get("error", "").lower()

    run(scenario())


# ---------------------------------------------------------------------------
# Test 7 — local_runtime_detection_ollama_reachable
# ---------------------------------------------------------------------------

def test_local_runtime_detection_ollama_reachable():
    """[mock] Patched Ollama returns 200 + response → test_llm returns status=ok."""
    from backend.services.model_test_service import ModelTestService

    async def scenario():
        svc = ModelTestService()

        with patch(
            "backend.agent.llm.OllamaLLMClient.is_runtime_reachable",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with patch(
                "backend.agent.llm.OllamaLLMClient.generate",
                new_callable=AsyncMock,
                return_value="Hello! I'm a local LLM.",
            ):
                result = await svc.test_llm("ollama", "llama3.2", credential=None)

        assert result["status"] == "ok", f"Unexpected result: {result}"
        assert result["latency_ms"] >= 0
        assert len(result.get("response", "")) > 0

    run(scenario())


# ---------------------------------------------------------------------------
# Test 8 — actual_tts_sample_groq_sarvam_mock
# ---------------------------------------------------------------------------

def test_actual_tts_sample_mock():
    """[mock] Patched SarvamEngine.synthesize returns PCM bytes → test_tts returns ok."""
    from backend.services.model_test_service import ModelTestService

    async def scenario():
        svc = ModelTestService()

        # Patch _test_sarvam_tts to return fake PCM bytes
        with patch.object(
            svc,
            "_test_sarvam_tts",
            new_callable=AsyncMock,
            return_value=b"pcm_data_placeholder",
        ):
            result = await svc.test_tts(
                "sarvam", "bulbul-v3", credential="test-key", voice="kavya", language="en-IN"
            )

        assert result["status"] == "ok", f"Unexpected result: {result}"
        assert result["latency_ms"] >= 0

    run(scenario())


# ---------------------------------------------------------------------------
# Test 9 — actual_stt_transcription_mock
# ---------------------------------------------------------------------------

def test_actual_stt_transcription_mock():
    """[mock] Patched STTClient.transcribe returns 'hello test' → test_stt returns ok."""
    from backend.services.model_test_service import ModelTestService

    async def scenario():
        svc = ModelTestService()

        # Patch _test_groq_stt to return the expected transcript
        with patch.object(
            svc,
            "_test_groq_stt",
            new_callable=AsyncMock,
            return_value="hello test",
        ):
            result = await svc.test_stt(
                "groq-whisper", "whisper-large-v3-turbo", credential="test-key", language="en"
            )

        assert result["status"] == "ok", f"Unexpected result: {result}"
        assert result["transcript"] == "hello test"
        assert result["latency_ms"] >= 0

    run(scenario())


# ---------------------------------------------------------------------------
# Test 10 — actual_llm_inference_mock
# ---------------------------------------------------------------------------

def test_actual_llm_inference_mock():
    """[mock] Patched LLMClient.complete returns test response → test_llm returns ok."""
    from backend.services.model_test_service import ModelTestService

    async def scenario():
        svc = ModelTestService()

        with patch.object(
            svc,
            "_test_groq_llm",
            new_callable=AsyncMock,
            return_value="This is a test response.",
        ):
            result = await svc.test_llm(
                "groq", "llama-3.3-70b-versatile", credential="test-key"
            )

        assert result["status"] == "ok", f"Unexpected result: {result}"
        assert len(result.get("response", "")) > 0
        assert result["latency_ms"] >= 0

    run(scenario())


# ---------------------------------------------------------------------------
# Test 11 — model_activation_and_audit
# ---------------------------------------------------------------------------

@_SKIP_IF_NO_MONGOMOCK
def test_model_activation_and_audit():
    """[mock] activate_provider sets is_active=True and creates an audit log entry."""
    import mongomock_motor
    from backend.services.model_catalogue_seed import seed_model_catalogue
    from backend.services.model_directory_service import ModelDirectoryService

    async def scenario():
        db = mongomock_motor.AsyncMongoMockClient()["test"]
        await seed_model_catalogue(db)

        svc = ModelDirectoryService(db)
        user = _make_platform_user()

        # Connect a provider
        config_dict = await svc.connect_provider(
            {
                "capability": "llm",
                "provider_name": "groq",
                "model_id": "llama-3.3-70b-versatile",
            },
            "test-groq-key-1234",
            user,
        )
        config_id = config_dict["id"]

        # Simulate a successful test by patching _run_test
        with patch.object(
            svc,
            "_run_test",
            new_callable=AsyncMock,
            return_value={"status": "ok", "latency_ms": 42, "response": "Hello!"},
        ):
            await svc.test_provider(config_id, user)

        # Activate
        activated = await svc.activate_provider(config_id, user)
        assert activated["is_active"] is True

        # Verify DB directly
        raw_config = await db["provider_configurations"].find_one({"_id": config_id})
        assert raw_config["is_active"] is True

        # Verify audit log has a provider.activate entry
        audit_docs = await db["audit_logs"].find({"resource_id": config_id}).to_list(length=100)
        actions = [d.get("action") for d in audit_docs]
        assert any("provider.activate" in a for a in actions), f"Audit actions: {actions}"

    run(scenario())


# ---------------------------------------------------------------------------
# Test 12 — unsupported_language_rejection
# ---------------------------------------------------------------------------

@_SKIP_IF_NO_MONGOMOCK
def test_unsupported_language_rejection():
    """[mock] French (fr) for IndicConformer raises ValueError — unsupported language."""
    import mongomock_motor
    from backend.services.model_catalogue_seed import seed_model_catalogue
    from backend.services.model_directory_service import ModelDirectoryService

    async def scenario():
        db = mongomock_motor.AsyncMongoMockClient()["test"]
        await seed_model_catalogue(db)

        svc = ModelDirectoryService(db)
        user = _make_platform_user()

        try:
            await svc.connect_provider(
                {
                    "capability": "stt",
                    "provider_name": "ai4bharat",
                    "model_id": "indicconformer-multilingual",
                    "language": "fr",  # French — not in supported_languages
                },
                None,  # ai4bharat needs no credential
                user,
            )
            assert False, "Expected ValueError for unsupported language"
        except ValueError as exc:
            msg = str(exc).lower()
            assert "language" in msg or "supported" in msg, f"Unexpected message: {exc}"

    run(scenario())


# ---------------------------------------------------------------------------
# Test 13 — credential_rotation_and_deletion
# ---------------------------------------------------------------------------

@_SKIP_IF_NO_MONGOMOCK
def test_credential_rotation_and_deletion():
    """[mock] rotate_credential creates new cred; delete_credential removes creds + configs."""
    import mongomock_motor
    from backend.services.model_catalogue_seed import seed_model_catalogue
    from backend.services.model_directory_service import ModelDirectoryService
    from backend.repositories.model_directory_repo import (
        ProviderCredentialRepo,
        ProviderConfigurationRepo,
    )

    async def scenario():
        db = mongomock_motor.AsyncMongoMockClient()["test"]
        await seed_model_catalogue(db)

        svc = ModelDirectoryService(db)
        user = _make_platform_user()

        # Connect with old credential
        await svc.connect_provider(
            {"capability": "stt", "provider_name": "groq-whisper", "model_id": "whisper-large-v3-turbo"},
            "old-key-1234",
            user,
        )

        cred_repo = ProviderCredentialRepo(db)
        initial_creds = await cred_repo.find_by_provider("groq-whisper")
        assert len(initial_creds) == 1
        assert initial_creds[0].key_hint == "1234"

        # Rotate to new credential
        await svc.rotate_credential("groq-whisper", "new-key-5678", user)

        all_creds = await cred_repo.find_by_provider("groq-whisper")
        # Old one is rotated, new one is current
        assert len(all_creds) == 2
        current = await cred_repo.find_current("groq-whisper")
        assert current is not None
        assert current.key_hint == "5678"

        # Old credential should be marked as rotated
        rotated = [c for c in all_creds if c.rotated_at is not None]
        assert len(rotated) == 1
        assert rotated[0].key_hint == "1234"

        # Connect groq llm as well for deletion test
        await svc.connect_provider(
            {"capability": "stt", "provider_name": "groq-whisper", "model_id": "whisper-large-v3-turbo"},
            "another-key-abcd",
            user,
        )

        # Delete all credentials + configs for groq-whisper
        await svc.delete_credential("groq-whisper", user)

        remaining_creds = await cred_repo.find_by_provider("groq-whisper")
        assert len(remaining_creds) == 0, "All credentials should be deleted"

        config_repo = ProviderConfigurationRepo(db)
        remaining_configs = await config_repo.find_many({"provider_name": "groq-whisper"})
        assert len(remaining_configs) == 0, "All configs should be deleted"

    run(scenario())


# ---------------------------------------------------------------------------
# Test 14 — free_tier_quota_guard
# ---------------------------------------------------------------------------

@_SKIP_IF_NO_MONGOMOCK
def test_free_tier_quota_guard():
    """[mock] 11th test call within 1 hour for same provider raises RateLimitError."""
    import mongomock_motor
    from backend.services.model_catalogue_seed import seed_model_catalogue
    from backend.services.model_directory_service import ModelDirectoryService, RateLimitError

    async def scenario():
        db = mongomock_motor.AsyncMongoMockClient()["test"]
        await seed_model_catalogue(db)

        svc = ModelDirectoryService(db)
        user = _make_platform_user()

        # Connect a provider to get a config_id
        config_dict = await svc.connect_provider(
            {"capability": "llm", "provider_name": "groq", "model_id": "llama-3.3-70b-versatile"},
            "test-groq-key-1234",
            user,
        )
        config_id = config_dict["id"]

        # Pre-seed 10 test-call records in provider_test_log for "groq" within last hour
        now = datetime.now(timezone.utc)
        records = [
            {"provider_name": "groq", "created_at": now - timedelta(minutes=i)}
            for i in range(10)
        ]
        await db["provider_test_log"].insert_many(records)

        # 11th call should raise RateLimitError
        try:
            await svc.test_provider(config_id, user)
            assert False, "Expected RateLimitError on the 11th call"
        except RateLimitError as exc:
            msg = str(exc).lower()
            assert "quota" in msg or "rate" in msg or "limit" in msg, f"Unexpected message: {exc}"

    run(scenario())


# ---------------------------------------------------------------------------
# Test 15 — customer_tenant_isolation (HTTP level)
# ---------------------------------------------------------------------------

def test_customer_tenant_isolation():
    """[mock] org-level token gets 403 from GET /api/v1/model-directory/catalogue."""
    from fastapi.testclient import TestClient
    from backend.core.auth import create_access_token, CurrentUser
    from backend.core.rbac import require_platform

    # Import app — we don't start lifespan; use lifespan=False
    from backend.main import app

    # Create a JWT for an org-level user
    org_token = create_access_token(
        user_id="org-user-999",
        email="org-user@example.com",
        role="organization_admin",
        org_id="org-999",
    )

    # Use TestClient without lifespan to avoid DB/Redis connection
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(
        "/api/v1/model-directory/catalogue",
        headers={"Authorization": f"Bearer {org_token}"},
    )
    assert resp.status_code == 403, (
        f"Expected 403 for org-level user, got {resp.status_code}: {resp.text}"
    )
