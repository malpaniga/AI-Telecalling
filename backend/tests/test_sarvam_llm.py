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
