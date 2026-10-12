"""M42 Cloud AI Providers — contract tests with mocked HTTP.

All tests use mock/patched clients. No real API credentials are required.
Tests labelled [LIVE] describe what would happen with real credentials and
are guarded by a SKIP condition when credentials are absent.

Pattern: def run(coro): loop=asyncio.new_event_loop(); return loop.run_until_complete(coro)

Coverage:
  - GeminiLLMProvider (google-genai SDK)
  - GroqLLMProvider (groq SDK)
  - ElevenLabsTTSProviderV2 (elevenlabs SDK)
  - GoogleCloudSTTProvider (google-cloud-speech SDK)
  - ModelTestService additions (gemini, elevenlabs, google-cloud-stt)
  - Credential redaction
  - Local-only rejection (ollama)
  - Missing-credential rejection
  - Error sanitization
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_groq_chat_response(content: str = "Hello from Groq!") -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_gemini_response(text: str = "Hello from Gemini!") -> MagicMock:
    resp = MagicMock()
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# Test 1 — GroqLLMProvider normalizes response
# ---------------------------------------------------------------------------

def test_groq_llm_provider_normalizes_response():
    """[mock] GroqLLMProvider.generate returns plain text from chat completion."""
    from backend.providers.llm.groq import GroqLLMProvider

    async def scenario():
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_groq_chat_response("Hello! I am a Groq LLM.")
        )
        provider = GroqLLMProvider(api_key="test-key", _client=mock_client)
        result = await provider.generate(
            [{"role": "user", "content": "Say hello."}]
        )
        assert isinstance(result, str)
        assert len(result) > 0
        # Verify client was called with correct structure
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs is not None
        msgs = call_kwargs.kwargs.get("messages", [])
        # Should have at least the user message
        assert any(m.get("role") == "user" for m in msgs)

    run(scenario())


def test_groq_llm_provider_system_prompt_injected():
    """[mock] System prompt appears as first message in Groq request."""
    from backend.providers.llm.groq import GroqLLMProvider

    async def scenario():
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_groq_chat_response("Understood.")
        )
        provider = GroqLLMProvider(api_key="test-key", _client=mock_client)
        await provider.generate(
            [{"role": "user", "content": "Hello"}],
            system_prompt="You are a helpful assistant.",
        )
        call_kwargs = mock_client.chat.completions.create.call_args
        msgs = call_kwargs.kwargs.get("messages", [])
        assert msgs[0]["role"] == "system"
        assert "helpful assistant" in msgs[0]["content"]

    run(scenario())


def test_groq_llm_provider_auth_error_sanitized():
    """[mock] 401 error does not expose the API key in the exception message."""
    from backend.providers.llm.groq import GroqLLMProvider
    from groq import AuthenticationError

    async def scenario():
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("401 invalid_api_key sk-real-secret-key-here")
        )
        provider = GroqLLMProvider(api_key="sk-real-secret-key-here", _client=mock_client)
        try:
            await provider.generate([{"role": "user", "content": "hi"}])
            assert False, "Should have raised RuntimeError"
        except RuntimeError as exc:
            assert "sk-real-secret-key-here" not in str(exc)
            assert "groq" in str(exc).lower() or "authentication" in str(exc).lower()

    run(scenario())


def test_groq_llm_provider_rate_limit_sanitized():
    """[mock] 429 rate limit error produces clean message without key."""
    from backend.providers.llm.groq import GroqLLMProvider

    async def scenario():
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("429 rate_limit_exceeded")
        )
        provider = GroqLLMProvider(api_key="gsk-secret", _client=mock_client)
        try:
            await provider.generate([{"role": "user", "content": "hi"}])
            assert False, "Should have raised RuntimeError"
        except RuntimeError as exc:
            assert "gsk-secret" not in str(exc)
            assert "rate" in str(exc).lower() or "limit" in str(exc).lower()

    run(scenario())


def test_groq_llm_provider_missing_key_raises():
    """[mock] Constructing GroqLLMProvider without api_key raises ValueError."""
    from backend.providers.llm.groq import GroqLLMProvider

    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        GroqLLMProvider(api_key="")


# ---------------------------------------------------------------------------
# Test 6 — GeminiLLMProvider normalizes response
# ---------------------------------------------------------------------------

def test_gemini_llm_provider_normalizes_response():
    """[mock] GeminiLLMProvider.generate returns text from Gemini API response."""
    from backend.providers.llm.gemini import GeminiLLMProvider

    async def scenario():
        mock_client = MagicMock()
        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            return_value=_make_gemini_response("Hello from Gemini!")
        )
        provider = GeminiLLMProvider(api_key="AIza-test", _client=mock_client)
        result = await provider.generate(
            [{"role": "user", "content": "Say hello."}]
        )
        assert isinstance(result, str)
        assert "Hello" in result

    run(scenario())


def test_gemini_llm_provider_system_prompt_in_config():
    """[mock] System messages are passed via GenerateContentConfig, not contents."""
    from backend.providers.llm.gemini import GeminiLLMProvider
    from google.genai import types as gtypes

    async def scenario():
        captured = {}

        async def fake_generate_content(model, contents, config):
            captured["contents"] = contents
            captured["config"] = config
            return _make_gemini_response("OK")

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = fake_generate_content
        provider = GeminiLLMProvider(api_key="AIza-test", _client=mock_client)

        await provider.generate(
            [
                {"role": "system", "content": "You are an agent."},
                {"role": "user", "content": "Hello"},
            ]
        )
        # System message must NOT appear in contents list
        roles = [c.role for c in captured.get("contents", [])]
        assert "system" not in roles
        # System instruction must be set in config
        assert captured["config"].system_instruction == "You are an agent."

    run(scenario())


def test_gemini_llm_provider_auth_error_sanitized():
    """[mock] Auth error never exposes API key."""
    from backend.providers.llm.gemini import GeminiLLMProvider

    async def scenario():
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=Exception("INVALID_ARGUMENT API_KEY AIza-my-real-key")
        )
        provider = GeminiLLMProvider(api_key="AIza-my-real-key", _client=mock_client)
        try:
            await provider.generate([{"role": "user", "content": "hi"}])
            assert False, "Should have raised"
        except RuntimeError as exc:
            assert "AIza-my-real-key" not in str(exc)

    run(scenario())


def test_gemini_llm_provider_missing_key_raises():
    """[mock] Constructing GeminiLLMProvider without api_key raises ValueError."""
    from backend.providers.llm.gemini import GeminiLLMProvider

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiLLMProvider(api_key="")


def test_gemini_llm_provider_empty_response_raises():
    """[mock] Empty Gemini response raises ValueError."""
    from backend.providers.llm.gemini import GeminiLLMProvider

    async def scenario():
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            return_value=_make_gemini_response("")
        )
        provider = GeminiLLMProvider(api_key="AIza-test", _client=mock_client)
        try:
            await provider.generate([{"role": "user", "content": "hi"}])
            assert False, "Should have raised ValueError"
        except ValueError as exc:
            assert "empty" in str(exc).lower()

    run(scenario())


# ---------------------------------------------------------------------------
# Test 11 — ElevenLabsTTSProviderV2 normalizes response
# ---------------------------------------------------------------------------

def test_elevenlabs_tts_provider_synthesize_returns_audio():
    """[mock] ElevenLabsTTSProviderV2.synthesize returns audio bytes + sample_rate."""
    from backend.providers.tts.elevenlabs_v2 import ElevenLabsTTSProviderV2

    async def scenario():
        mock_client = MagicMock()
        # elevenlabs SDK returns an iterator of bytes chunks
        mock_client.text_to_speech.convert = MagicMock(
            return_value=iter([b"PCM_CHUNK_1", b"PCM_CHUNK_2"])
        )
        provider = ElevenLabsTTSProviderV2(
            api_key="el-test",
            voice_id="test-voice",
            _client=mock_client,
        )
        result = await provider.synthesize("Hello test.")
        assert isinstance(result, dict)
        assert "audio" in result
        assert "sample_rate" in result
        assert result["audio"] == b"PCM_CHUNK_1PCM_CHUNK_2"
        assert result["sample_rate"] == 16000

    run(scenario())


def test_elevenlabs_tts_provider_missing_key_raises():
    """[mock] Constructing ElevenLabsTTSProviderV2 without api_key raises ValueError."""
    from backend.providers.tts.elevenlabs_v2 import ElevenLabsTTSProviderV2

    with pytest.raises(ValueError, match="ELEVENLABS_API_KEY"):
        ElevenLabsTTSProviderV2(api_key="")


def test_elevenlabs_tts_provider_auth_error_sanitized():
    """[mock] 401 error does not include API key in message."""
    from backend.providers.tts.elevenlabs_v2 import ElevenLabsTTSProviderV2

    async def scenario():
        mock_client = MagicMock()
        mock_client.text_to_speech.convert = MagicMock(
            side_effect=Exception("401 unauthorized el-real-api-key")
        )
        provider = ElevenLabsTTSProviderV2(
            api_key="el-real-api-key",
            _client=mock_client,
        )
        try:
            await provider.synthesize("test")
            assert False, "Should have raised RuntimeError"
        except RuntimeError as exc:
            assert "el-real-api-key" not in str(exc)
            assert "elevenlabs" in str(exc).lower() or "authentication" in str(exc).lower()

    run(scenario())


def test_elevenlabs_tts_provider_empty_text_returns_empty():
    """[mock] Empty text input returns empty audio without calling API."""
    from backend.providers.tts.elevenlabs_v2 import ElevenLabsTTSProviderV2

    async def scenario():
        mock_client = MagicMock()
        mock_client.text_to_speech.convert = MagicMock()
        provider = ElevenLabsTTSProviderV2(api_key="el-test", _client=mock_client)
        result = await provider.synthesize("   ")
        assert result["audio"] == b""
        # API should NOT have been called for empty input
        mock_client.text_to_speech.convert.assert_not_called()

    run(scenario())


# ---------------------------------------------------------------------------
# Test 15 — GoogleCloudSTTProvider normalizes response
# ---------------------------------------------------------------------------

def test_google_cloud_stt_normalizes_response():
    """[mock] GoogleCloudSTTProvider.transcribe returns text from recognition response."""
    from backend.providers.stt.google_cloud import GoogleCloudSTTProvider

    async def scenario():
        mock_client = MagicMock()

        # Mock recognition response
        alt = MagicMock()
        alt.transcript = "नमस्ते यह एक परीक्षण है"
        result_mock = MagicMock()
        result_mock.alternatives = [alt]
        response = MagicMock()
        response.results = [result_mock]
        mock_client.recognize = MagicMock(return_value=response)

        provider = GoogleCloudSTTProvider(
            project_id="test-project",
            _client=mock_client,
        )
        transcript = await provider.transcribe(
            b"\x00\x00" * 100,  # raw PCM
            language="hi-IN",
            sample_rate=16000,
        )
        assert "नमस्ते" in transcript or len(transcript) > 0

    run(scenario())


def test_google_cloud_stt_wav_header_stripped():
    """[mock] WAV-wrapped audio has header stripped before sending to Google API."""
    import wave
    import io as _io
    from backend.providers.stt.google_cloud import GoogleCloudSTTProvider, _detect_encoding

    # Create a minimal WAV file
    buf = _io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 160)
    wav_bytes = buf.getvalue()

    from google.cloud import speech
    encoding, pcm = _detect_encoding(wav_bytes)
    assert encoding == speech.RecognitionConfig.AudioEncoding.LINEAR16
    # WAV header is 44 bytes; stripped result should be shorter
    assert len(pcm) < len(wav_bytes)
    # WAV header stripped — should not start with RIFF
    assert pcm[:4] != b"RIFF"


def test_google_cloud_stt_auth_error_sanitized():
    """[mock] Authentication error message does not expose service account details."""
    from backend.providers.stt.google_cloud import GoogleCloudSTTProvider

    async def scenario():
        mock_client = MagicMock()
        mock_client.recognize = MagicMock(
            side_effect=Exception("UNAUTHENTICATED service_account_key_content_here")
        )
        provider = GoogleCloudSTTProvider(project_id="proj", _client=mock_client)
        try:
            await provider.transcribe(b"\x00\x00" * 100)
            assert False, "Should have raised RuntimeError"
        except RuntimeError as exc:
            assert "service_account_key_content_here" not in str(exc)
            assert "google" in str(exc).lower() or "authentication" in str(exc).lower()

    run(scenario())


def test_google_cloud_stt_missing_project_id_raises():
    """[mock] Constructing GoogleCloudSTTProvider without project_id raises ValueError."""
    from backend.providers.stt.google_cloud import GoogleCloudSTTProvider

    with pytest.raises(ValueError, match="project_id"):
        GoogleCloudSTTProvider(project_id="")


# ---------------------------------------------------------------------------
# Test 19 — ModelTestService additions
# ---------------------------------------------------------------------------

def test_model_test_service_gemini_ok():
    """[mock] ModelTestService.test_llm with provider=gemini returns ok status."""
    from backend.services.model_test_service import ModelTestService

    async def scenario():
        svc = ModelTestService()
        with patch.object(
            svc, "_test_gemini_llm", new_callable=AsyncMock,
            return_value="Hello from Gemini!"
        ):
            result = await svc.test_llm("gemini", "gemini-2.0-flash-lite", credential="AIza-test")
        assert result["status"] == "ok"
        assert result["latency_ms"] >= 0
        assert len(result.get("response", "")) > 0

    run(scenario())


def test_model_test_service_elevenlabs_ok():
    """[mock] ModelTestService.test_tts with provider=elevenlabs returns ok status."""
    from backend.services.model_test_service import ModelTestService

    async def scenario():
        svc = ModelTestService()
        with patch.object(
            svc, "_test_elevenlabs_tts", new_callable=AsyncMock,
            return_value=b"fake_pcm_audio_data"
        ):
            result = await svc.test_tts(
                "elevenlabs", "eleven_multilingual_v2",
                credential="el-test",
                voice="test-voice",
                language="en",
            )
        assert result["status"] == "ok"
        assert result["latency_ms"] >= 0
        assert result.get("sample_output_b64") is not None

    run(scenario())


def test_model_test_service_google_cloud_stt_ok():
    """[mock] ModelTestService.test_stt with provider=google-cloud-stt returns ok."""
    from backend.services.model_test_service import ModelTestService

    async def scenario():
        svc = ModelTestService()
        with patch.object(
            svc, "_test_google_cloud_stt", new_callable=AsyncMock,
            return_value=""  # silent WAV returns empty transcript — still ok
        ):
            result = await svc.test_stt(
                "google-cloud-stt", "chirp_2",
                credential='{"type": "service_account"}',
                language="hi-IN",
            )
        assert result["status"] == "ok"
        assert result["latency_ms"] >= 0

    run(scenario())


def test_model_test_service_ollama_rejected():
    """[mock] ModelTestService.test_llm for ollama returns error (runtime not reachable)
    or unavailable — Ollama cannot be activated in cloud-only mode."""
    from backend.services.model_test_service import ModelTestService

    async def scenario():
        svc = ModelTestService()
        # Don't patch — Ollama runtime won't be running in CI
        result = await svc.test_llm("ollama", "llama3.2", credential=None)
        # Ollama is not running in CI so this will be error or unavailable
        assert result["status"] in ("error", "unavailable"), (
            f"Unexpected status: {result}"
        )
        # Error message must mention local/runtime
        error_msg = result.get("error", "").lower()
        assert any(w in error_msg for w in ("runtime", "local", "reachable", "ollama")), (
            f"Expected error mentioning local/runtime nature, got: {error_msg}"
        )

    run(scenario())


def test_model_test_service_gemini_missing_credential():
    """[mock] test_llm for gemini without credential returns error (not ok)."""
    from backend.services.model_test_service import ModelTestService

    async def scenario():
        svc = ModelTestService()
        # No patching — will call _test_gemini_llm which raises on missing cred
        result = await svc.test_llm("gemini", "gemini-2.0-flash-lite", credential=None)
        assert result["status"] == "error"
        # Key must not appear in error
        assert "AIza" not in result.get("error", "")

    run(scenario())


def test_model_test_service_ai4bharat_tts_unavailable():
    """[mock] Self-hosted providers return unavailable status."""
    from backend.services.model_test_service import ModelTestService

    async def scenario():
        svc = ModelTestService()
        result = await svc.test_tts(
            "ai4bharat-indicf5", "indicf5",
            credential=None, voice=None, language="hi"
        )
        assert result["status"] == "unavailable"
        assert "self-hosted" in result.get("error", "").lower() or \
               "cloud" in result.get("error", "").lower()

    run(scenario())


# ---------------------------------------------------------------------------
# Test 26 — Regression: M41 tests still pass
# ---------------------------------------------------------------------------

def test_m41_catalogue_seed_imports_cleanly():
    """Regression: M41+M42 catalogue seed imports without error."""
    from backend.services.model_catalogue_seed import _ENTRIES, _M42_ENTRIES
    # 12 M41 entries + 1 M42 (Google Cloud STT)
    assert len(_ENTRIES) == 12
    assert len(_M42_ENTRIES) == 1
    # Ollama must be marked unavailable (cloud-only mode)
    ollama = next((e for e in _ENTRIES if e["provider_name"] == "ollama"), None)
    assert ollama is not None
    assert ollama["implementation_status"] == "unavailable", (
        f"Ollama must be unavailable in cloud-only mode, got {ollama['implementation_status']}"
    )
    # ElevenLabs must be supported
    eleven = next((e for e in _ENTRIES if e["provider_name"] == "elevenlabs"), None)
    assert eleven is not None
    assert eleven["implementation_status"] == "supported"
    # Google Cloud STT must be in M42 entries
    gcs = _M42_ENTRIES[0]
    assert gcs["provider_name"] == "google-cloud-stt"
    assert gcs["implementation_status"] == "supported"


def test_gemini_provider_capabilities():
    """GeminiLLMProvider.get_capabilities returns expected keys."""
    from backend.providers.llm.gemini import GeminiLLMProvider

    provider = GeminiLLMProvider(api_key="test", _client=MagicMock())
    caps = provider.get_capabilities()
    assert caps["provider"] == "gemini"
    assert "streaming" in caps
    assert "languages" in caps


def test_groq_provider_capabilities():
    """GroqLLMProvider.get_capabilities returns expected keys."""
    from backend.providers.llm.groq import GroqLLMProvider

    provider = GroqLLMProvider(api_key="test", _client=MagicMock())
    caps = provider.get_capabilities()
    assert caps["provider"] == "groq"
    assert caps["streaming"] is True
