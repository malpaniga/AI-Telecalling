import base64
from unittest.mock import AsyncMock, MagicMock
import pytest

from backend.providers.tts.google_wavenet import (
    DEFAULT_MODEL,
    GoogleWaveNetTTSProvider,
)


@pytest.mark.anyio
async def test_google_wavenet_synthesize_success():
    """GoogleWaveNetTTSProvider.synthesize decodes base64 and strips 44-byte WAV header."""
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    # Build 44-byte dummy WAV header + PCM audio payload
    wav_header = b"RIFF" + b"\x00" * 36 + b"WAVE"
    raw_audio = b"AUDIO_PCM_FRAME_DATA_12345"
    full_wav = wav_header + raw_audio
    b64_audio = base64.b64encode(full_wav).decode("ascii")

    mock_resp.json.return_value = {"audioContent": b64_audio}
    mock_resp.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    provider = GoogleWaveNetTTSProvider(
        api_key="AIzaSyTestKey123",
        voice_id="hi-IN-Wavenet-A",
        language="hi-IN",
        _client=mock_client,
    )

    res = await provider.synthesize("Namaste")
    assert res["audio"] == raw_audio
    assert res["sample_rate"] == 16000

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args.kwargs
    assert call_kwargs["headers"]["X-Goog-Api-Key"] == "AIzaSyTestKey123"
    assert call_kwargs["json"]["input"]["text"] == "Namaste"
    assert call_kwargs["json"]["voice"]["name"] == "hi-IN-Wavenet-A"
    assert call_kwargs["json"]["voice"]["languageCode"] == "hi-IN"
    assert call_kwargs["json"]["audioConfig"]["audioEncoding"] == "LINEAR16"


@pytest.mark.anyio
async def test_google_wavenet_stream_success():
    """GoogleWaveNetTTSProvider.stream yields audio chunk dictionary."""
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    wav_header = b"RIFF" + b"\x00" * 36 + b"WAVE"
    raw_audio = b"STREAMED_CHUNK_AUDIO"
    b64_audio = base64.b64encode(wav_header + raw_audio).decode("ascii")

    mock_resp.json.return_value = {"audioContent": b64_audio}
    mock_resp.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    provider = GoogleWaveNetTTSProvider(api_key="AIzaSyTestKey", _client=mock_client)
    chunks = []
    async for chunk in provider.stream("Hello"):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0]["audio"] == raw_audio
    assert chunks[0]["sample_rate"] == 16000


def test_google_wavenet_missing_key_raises():
    """Constructing GoogleWaveNetTTSProvider without key raises ValueError."""
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        GoogleWaveNetTTSProvider(api_key="")


@pytest.mark.anyio
async def test_google_wavenet_auth_error_sanitized():
    """Authentication errors never expose API key and suppress cause."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("403 Forbidden: API key AIzaSyRealSecretKey invalid")
    provider = GoogleWaveNetTTSProvider(api_key="AIzaSyRealSecretKey", _client=mock_client)

    with pytest.raises(RuntimeError) as exc_info:
        await provider.synthesize("Hello")

    assert "AIzaSyRealSecretKey" not in str(exc_info.value)
    assert "Google WaveNet" in str(exc_info.value)
    assert exc_info.value.__cause__ is None


def test_google_wavenet_capabilities_and_models():
    """Capabilities and models return expected structure."""
    provider = GoogleWaveNetTTSProvider(api_key="test-key", _client=MagicMock())
    caps = provider.get_capabilities()
    assert caps["provider"] == "google-wavenet"
    assert caps["streaming"] is True
    assert caps["sample_rate"] == 16000
    assert "hi-IN" in caps["languages"]



# ---------------------------------------------------------------------------
# Task 2: Soniox STT Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_soniox_stt_transcribe_success():
    """SonioxSTTProvider.transcribe uploads audio and retrieves transcript."""
    from backend.providers.stt.soniox import SonioxSTTProvider, DEFAULT_MODEL

    mock_client = AsyncMock()

    # 1. Upload file response
    mock_upload_resp = MagicMock()
    mock_upload_resp.status_code = 200
    mock_upload_resp.json.return_value = {"id": "file_abc123"}
    mock_upload_resp.raise_for_status = MagicMock()

    # 2. Create transcription response
    mock_trans_resp = MagicMock()
    mock_trans_resp.status_code = 200
    mock_trans_resp.json.return_value = {"id": "tr_xyz789", "status": "completed"}
    mock_trans_resp.raise_for_status = MagicMock()

    # 3. Get transcript response
    mock_transcript_resp = MagicMock()
    mock_transcript_resp.status_code = 200
    mock_transcript_resp.json.return_value = {"text": "Hello world from Soniox"}
    mock_transcript_resp.raise_for_status = MagicMock()

    # 4. Delete file response
    mock_delete_resp = MagicMock()
    mock_delete_resp.status_code = 200
    mock_delete_resp.raise_for_status = MagicMock()

    def mock_post(url, *args, **kwargs):
        if "/v1/files" in url:
            return mock_upload_resp
        if "/v1/transcriptions" in url:
            return mock_trans_resp
        raise ValueError(f"Unexpected POST url {url}")

    def mock_get(url, *args, **kwargs):
        if "/transcript" in url:
            return mock_transcript_resp
        if "/v1/transcriptions/" in url:
            return mock_trans_resp
        raise ValueError(f"Unexpected GET url {url}")

    mock_client.post = AsyncMock(side_effect=mock_post)
    mock_client.get = AsyncMock(side_effect=mock_get)
    mock_client.delete = AsyncMock(return_value=mock_delete_resp)

    provider = SonioxSTTProvider(api_key="soniox_secret_key_123", _client=mock_client)
    transcript = await provider.transcribe(b"WAV_AUDIO_BYTES_TEST_SAMPLE")
    assert transcript == "Hello world from Soniox"

    # Verify authorization header was sent
    post_calls = mock_client.post.call_args_list
    assert any("Bearer soniox_secret_key_123" in str(call) for call in post_calls)


def test_soniox_stt_missing_key_raises():
    """Constructing SonioxSTTProvider without key raises ValueError."""
    from backend.providers.stt.soniox import SonioxSTTProvider

    with pytest.raises(ValueError, match="SONIOX_API_KEY"):
        SonioxSTTProvider(api_key="")


@pytest.mark.anyio
async def test_soniox_stt_auth_error_sanitized():
    """Authentication errors never expose API key and suppress cause."""
    from backend.providers.stt.soniox import SonioxSTTProvider

    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("401 Unauthorized: key soniox_super_secret invalid")
    provider = SonioxSTTProvider(api_key="soniox_super_secret", _client=mock_client)

    with pytest.raises(RuntimeError) as exc_info:
        await provider.transcribe(b"audio-bytes-sample")

    assert "soniox_super_secret" not in str(exc_info.value)
    assert "Soniox" in str(exc_info.value)
    assert exc_info.value.__cause__ is None


def test_soniox_stt_capabilities_and_models():
    """Soniox capabilities and models return expected structure."""
    from backend.providers.stt.soniox import SonioxSTTProvider

    provider = SonioxSTTProvider(api_key="test-key", _client=MagicMock())
    caps = provider.get_capabilities()
    assert caps["provider"] == "soniox"
    assert "hi-IN" in caps["languages"]
    assert "mr-IN" in caps["languages"]



# ---------------------------------------------------------------------------
# Task 3: Runtime & ModelTestService Integration Tests
# ---------------------------------------------------------------------------

def test_runtime_builds_google_wavenet_tts():
    """CloudProviderRuntime._build_provider builds GoogleWaveNetTTSProvider."""
    from backend.models.model_directory import ProviderConfiguration
    from backend.services.provider_runtime import CloudProviderRuntime

    config = ProviderConfiguration(
        provider_name="google-wavenet",
        capability="tts",
        model_id="wavenet",
        voice="hi-IN-Wavenet-A",
        language="hi-IN",
        is_active=True,
    )
    provider = CloudProviderRuntime._build_provider(config, credential="test-google-key")
    assert isinstance(provider, GoogleWaveNetTTSProvider)
    assert provider.voice_id == "hi-IN-Wavenet-A"


def test_runtime_builds_soniox_stt():
    """CloudProviderRuntime._build_provider builds SonioxSTTProvider."""
    from backend.models.model_directory import ProviderConfiguration
    from backend.services.provider_runtime import CloudProviderRuntime
    from backend.providers.stt.soniox import SonioxSTTProvider

    config = ProviderConfiguration(
        provider_name="soniox",
        capability="stt",
        model_id="stt-async-v5",
        language="en-IN",
        is_active=True,
    )
    provider = CloudProviderRuntime._build_provider(config, credential="test-soniox-key")
    assert isinstance(provider, SonioxSTTProvider)
    assert provider.model == "stt-async-v5"


@pytest.mark.anyio
async def test_model_test_service_google_wavenet(monkeypatch):
    """ModelTestService.test_tts routes to Google WaveNet."""
    from backend.services.model_test_service import ModelTestService

    svc = ModelTestService()
    mock_synth = AsyncMock(return_value={"audio": b"DUMMY_AUDIO", "sample_rate": 16000})
    monkeypatch.setattr(GoogleWaveNetTTSProvider, "synthesize", mock_synth)

    res = await svc.test_tts("google-wavenet", "wavenet", credential="test-key", voice="hi-IN-Wavenet-A", language="hi-IN")
    assert res["status"] == "ok"
    assert "sample_output_b64" in res


@pytest.mark.anyio
async def test_model_test_service_soniox(monkeypatch):
    """ModelTestService.test_stt routes to Soniox."""
    from backend.services.model_test_service import ModelTestService
    from backend.providers.stt.soniox import SonioxSTTProvider

    svc = ModelTestService()
    mock_transcribe = AsyncMock(return_value="Test Hello")
    monkeypatch.setattr(SonioxSTTProvider, "transcribe", mock_transcribe)

    res = await svc.test_stt("soniox", "stt-async-v5", credential="test-key", language="en-IN")
    assert res["status"] == "ok"
    assert res["transcript"] == "Test Hello"



# ---------------------------------------------------------------------------
# Task 4: Catalogue, Directory, and Pricing Tests
# ---------------------------------------------------------------------------

def test_catalogue_contains_soniox_and_google_wavenet():
    """Model catalogue seed contains entries for Soniox STT and Google WaveNet TTS."""
    from backend.services.model_catalogue_seed import _ENTRIES

    soniox_entries = [
        e for e in _ENTRIES
        if e["provider_name"] == "soniox" and e["capability"] == "stt"
    ]
    assert len(soniox_entries) >= 1
    assert "SONIOX_API_KEY" in soniox_entries[0]["credential_requirements"]

    wavenet_entries = [
        e for e in _ENTRIES
        if e["provider_name"] == "google-wavenet" and e["capability"] == "tts"
    ]
    assert len(wavenet_entries) >= 1
    assert "GOOGLE_API_KEY" in wavenet_entries[0]["credential_requirements"]


@pytest.mark.anyio
async def test_directory_service_lists_soniox_and_wavenet():
    """ModelDirectoryService lists live models for Soniox and Google WaveNet."""
    from backend.services.model_directory_service import ModelDirectoryService

    mock_db = MagicMock()
    svc = ModelDirectoryService(mock_db)
    svc._catalogue_repo = MagicMock()
    svc._catalogue_repo.find_many = AsyncMock(return_value=[])
    svc._cred_repo = MagicMock()
    svc._cred_repo.find_current = AsyncMock(return_value=None)

    soniox_models = await svc.list_provider_live_models("soniox")
    assert "stt-async-v5" in soniox_models

    wavenet_models = await svc.list_provider_live_models("google-wavenet")
    assert "wavenet" in wavenet_models


def test_pricing_sync_contains_soniox_and_wavenet():
    """Pricing sync definitions include Soniox and Google WaveNet rate cards."""
    from backend.services.pricing_sync_service import DEFAULT_PROVIDER_DEFINITIONS

    soniox_defs = [
        d for d in DEFAULT_PROVIDER_DEFINITIONS
        if d["provider_name"] == "soniox" and d["capability"] == "stt"
    ]
    assert len(soniox_defs) == 1

    wavenet_defs = [
        d for d in DEFAULT_PROVIDER_DEFINITIONS
        if d["provider_name"] == "google-wavenet" and d["capability"] == "tts"
    ]
    assert len(wavenet_defs) == 1
