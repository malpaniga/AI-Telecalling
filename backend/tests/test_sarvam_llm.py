import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.providers.llm.sarvam import (
    SarvamLLMProvider,
    DEFAULT_MODEL,
    SUPPORTED_MODELS,
)


@pytest.mark.anyio
async def test_sarvam_llm_provider_generate_success():
    """SarvamLLMProvider.generate returns text from OpenAI-compatible response."""
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Namaste! How can I help you today?"}}]
    }
    mock_resp.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    provider = SarvamLLMProvider(api_key="test-sarvam-key", _client=mock_client)
    res = await provider.generate([{"role": "user", "content": "Hello"}])
    assert res == "Namaste! How can I help you today?"

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args.kwargs
    assert call_kwargs["json"]["model"] == DEFAULT_MODEL
    assert call_kwargs["json"]["stream"] is False
    assert call_kwargs["headers"]["api-subscription-key"] == "test-sarvam-key"
    assert call_kwargs["headers"]["Authorization"] == "Bearer test-sarvam-key"


@pytest.mark.anyio
async def test_sarvam_llm_provider_system_prompt_injected():
    """System prompt appears as first message in request."""
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Understood."}}]
    }
    mock_resp.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    provider = SarvamLLMProvider(api_key="test-sarvam-key", _client=mock_client)
    await provider.generate(
        [{"role": "user", "content": "Hello"}],
        system_prompt="You are a helpful banking assistant.",
    )

    call_kwargs = mock_client.post.call_args.kwargs
    messages = call_kwargs["json"]["messages"]
    assert messages[0]["role"] == "system"
    assert "banking assistant" in messages[0]["content"]
    assert messages[1]["role"] == "user"


@pytest.mark.anyio
async def test_sarvam_llm_provider_stream_success():
    """SarvamLLMProvider.stream correctly processes SSE lines."""
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()

    async def mock_aiter_lines():
        lines = [
            ': ping',
            'data: {"choices":[{"delta":{"content":"Namaste"}}]}',
            '',
            'data: {"choices":[{"delta":{"content":" ji!"}}]}',
            'data: [DONE]',
        ]
        for line in lines:
            yield line

    mock_resp.aiter_lines = mock_aiter_lines

    class MockStreamContext:
        async def __aenter__(self):
            return mock_resp

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    mock_client.stream = MagicMock(return_value=MockStreamContext())

    provider = SarvamLLMProvider(api_key="test-sarvam-key", _client=mock_client)
    chunks = []
    async for chunk in provider.stream([{"role": "user", "content": "Hello"}]):
        chunks.append(chunk)

    assert "".join(chunks) == "Namaste ji!"
    assert chunks == ["Namaste", " ji!"]


def test_sarvam_llm_provider_missing_key_raises():
    """Constructing without api_key raises ValueError."""
    with pytest.raises(ValueError, match="SARVAM_API_KEY"):
        SarvamLLMProvider(api_key="")


@pytest.mark.anyio
async def test_sarvam_llm_provider_auth_error_sanitized():
    """401 error does not expose the secret API key in the exception message."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("401 Unauthorized: key secret-key-xyz invalid")
    provider = SarvamLLMProvider(api_key="secret-key-xyz", _client=mock_client)

    with pytest.raises(RuntimeError) as exc_info:
        await provider.generate([{"role": "user", "content": "hi"}])
    assert "secret-key-xyz" not in str(exc_info.value)
    assert "authentication" in str(exc_info.value).lower() or "sarvam" in str(exc_info.value).lower()


@pytest.mark.anyio
async def test_sarvam_llm_provider_rate_limit_sanitized():
    """429 error produces clean rate limit message without secret."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("429 Too Many Requests: secret-key-xyz")
    provider = SarvamLLMProvider(api_key="secret-key-xyz", _client=mock_client)

    with pytest.raises(RuntimeError) as exc_info:
        await provider.generate([{"role": "user", "content": "hi"}])
    assert "secret-key-xyz" not in str(exc_info.value)
    assert "rate limit" in str(exc_info.value).lower()


def test_sarvam_llm_provider_capabilities_and_models():
    """Capabilities and models return expected structure and defaults."""
    provider = SarvamLLMProvider(api_key="test-key", _client=MagicMock())
    caps = provider.get_capabilities()
    assert caps["provider"] == "sarvam"
    assert caps["streaming"] is True
    assert "sarvam-105b-conversations" in caps["model"]


@pytest.mark.anyio
async def test_sarvam_llm_provider_get_models():
    provider = SarvamLLMProvider(api_key="test-key", _client=MagicMock())
    models = await provider.get_models()
    assert "sarvam-105b-conversations" in models


def test_runtime_service_builds_sarvam_llm():
    """CloudProviderRuntime._build_provider instantiates SarvamLLMProvider."""
    from backend.services.provider_runtime import CloudProviderRuntime
    from backend.models.model_directory import ProviderConfiguration

    config = ProviderConfiguration(
        provider_name="sarvam",
        capability="llm",
        model_id="sarvam-105b-conversations",
        is_active=True,
    )
    provider = CloudProviderRuntime._build_provider(config, credential="test-key-123")
    assert isinstance(provider, SarvamLLMProvider)
    assert provider.model == "sarvam-105b-conversations"


@pytest.mark.anyio
async def test_model_test_service_sarvam_llm(monkeypatch):
    """ModelTestService.test_llm routes correctly to Sarvam provider."""
    from backend.services.model_test_service import ModelTestService

    svc = ModelTestService()
    mock_generate = AsyncMock(return_value="Hello from Sarvam!")
    monkeypatch.setattr(SarvamLLMProvider, "generate", mock_generate)

    res = await svc.test_llm("sarvam", "sarvam-105b-conversations", credential="test-key")
    assert res["status"] == "ok"
    assert res["response"] == "Hello from Sarvam!"
    assert "latency_ms" in res


@pytest.mark.anyio
async def test_model_test_service_sarvam_missing_credential():
    """ModelTestService.test_llm for sarvam returns error when credential is missing."""
    from backend.services.model_test_service import ModelTestService

    svc = ModelTestService()
    res = await svc.test_llm("sarvam", "sarvam-105b-conversations", credential=None)
    assert res["status"] == "error"
    assert "SARVAM_API_KEY" in res["error"]


def test_catalogue_seed_contains_sarvam_105b_conversations():
    """Model catalogue seed contains sarvam-105b-conversations with valid specs."""
    from backend.services.model_catalogue_seed import _ENTRIES

    matching = [
        entry for entry in _ENTRIES
        if entry["provider_name"] == "sarvam"
        and entry["model_id"] == "sarvam-105b-conversations"
        and entry["capability"] == "llm"
    ]
    assert len(matching) == 1
    entry = matching[0]
    assert entry["streaming_supported"] is True
    assert "SARVAM_API_KEY" in entry["credential_requirements"]
    assert entry["implementation_status"] == "supported"


@pytest.mark.anyio
async def test_directory_service_lists_sarvam_llm_model():
    """ModelDirectoryService.list_provider_live_models lists sarvam-105b-conversations."""
    from backend.services.model_directory_service import ModelDirectoryService

    mock_db = MagicMock()
    svc = ModelDirectoryService(mock_db)
    svc._catalogue_repo = MagicMock()
    svc._catalogue_repo.find_many = AsyncMock(return_value=[])
    svc._cred_repo = MagicMock()
    svc._cred_repo.find_current = AsyncMock(return_value=None)

    models = await svc.list_provider_live_models("sarvam")
    assert "sarvam-105b-conversations" in models


def test_pricing_sync_contains_sarvam_llm():
    """Pricing sync definitions include sarvam-105b-conversations default rate card."""
    from backend.services.pricing_sync_service import DEFAULT_PROVIDER_DEFINITIONS

    matching = [
        defn for defn in DEFAULT_PROVIDER_DEFINITIONS
        if defn["provider_name"] == "sarvam"
        and defn["model_id"] == "sarvam-105b-conversations"
        and defn["capability"] == "llm"
    ]
    assert len(matching) == 1
    assert matching[0]["base_currency"] == "INR"
    assert matching[0]["billing_unit"] == "turn"
