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
