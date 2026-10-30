"""Unit tests for the Test Agent browser runner & cloud providers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from backend.providers.stt.sarvam import SarvamSTTProvider
from backend.providers.stt.groq import GroqSTTProvider
from backend.services.provider_runtime import CloudProviderRuntime
from backend.models.model_directory import ProviderConfiguration


def run(coro):
    return asyncio.run(coro)


def test_sarvam_stt_provider_transcribe():
    async def scenario():
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"transcript": "नमस्कार, मी बोलतोय"}
        mock_client.post.return_value = mock_resp

        provider = SarvamSTTProvider(
            api_key="test-key",
            model="saaras:v4",
            language="mr-IN",
            _client=mock_client,
        )

        # A real utterance must exceed the provider's short/no-audio guard.
        import io
        import wave
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x01\x00" * 1600)
        transcript = await provider.transcribe(buffer.getvalue(), language="mr-IN")
        assert transcript == "नमस्कार, मी बोलतोय"
        mock_client.post.assert_called_once()

    run(scenario())


def test_groq_stt_provider_transcribe():
    async def scenario():
        mock_client = AsyncMock()
        mock_client.audio = MagicMock()
        mock_client.audio.transcriptions = MagicMock()
        mock_client.audio.transcriptions.create = AsyncMock(return_value="Hello, this is a test.")

        provider = GroqSTTProvider(
            api_key="gsk-test",
            model="whisper-large-v3-turbo",
            _client=mock_client,
        )

        transcript = await provider.transcribe(b"fake-audio-bytes", language="en-IN")
        assert transcript == "Hello, this is a test."

    run(scenario())


def test_cloud_provider_runtime_builds_sarvam_and_groq_stt():
    db = MagicMock()
    runtime = CloudProviderRuntime(db)

    # Sarvam STT config
    sarvam_cfg = ProviderConfiguration(
        provider_name="sarvam",
        model_id="saaras:v4",
        capability="stt",
        is_active=True,
    )
    p1 = runtime._build_provider(sarvam_cfg, "sarvam-secret-key")
    assert isinstance(p1, SarvamSTTProvider)
    assert p1.provider_name == "sarvam"

    # Groq STT config
    groq_cfg = ProviderConfiguration(
        provider_name="groq-whisper",
        model_id="whisper-large-v3-turbo",
        capability="stt",
        is_active=True,
    )
    p2 = runtime._build_provider(groq_cfg, "gsk-secret-key")
    assert isinstance(p2, GroqSTTProvider)
    assert p2.provider_name == "groq-whisper"


def test_interpolate_template_variables():
    from backend.agent.prompts import interpolate_template

    template = "नमस्कार, मी {partnerName} कडून बोलतोय. माझं नाव {{salesRepName}} आहे. तुमचं नाव {userName}?"
    variables = {
        "partnerName": "सोलरशिप एनर्जीज",
        "salesRepName": "प्रिया",
        "userName": "सुधीर",
    }
    interpolated = interpolate_template(template, variables)
    assert interpolated == "नमस्कार, मी सोलरशिप एनर्जीज कडून बोलतोय. माझं नाव प्रिया आहे. तुमचं नाव सुधीर?"

    # Empty / partial variables
    partial = interpolate_template("Hello {partnerName}, call {phone}", {"partnerName": "Acme"})
    assert partial == "Hello Acme, call {phone}"


def test_call_session_interpolates_custom_variables():
    from backend.call_session import CallSession
    from backend.agent.state import OUTPUT_VARIABLE_KEYS

    transport = MagicMock()
    transport.streaming = False
    transport.notify = AsyncMock()
    transport.play = AsyncMock()
    stt = MagicMock()
    engine = MagicMock()
    tts = MagicMock()
    store = MagicMock()

    session = CallSession(
        transport=transport,
        stt=stt,
        engine=engine,
        tts=tts,
        store=store,
        greeting="नमस्कार, मी {partnerName} कडून {salesRepName} बोलतेय.",
        system_prompt="You are {salesRepName} from {partnerName}.",
        variables={"partnerName": "सोलरशिप एनर्जीज", "salesRepName": "प्रिया"},
    )

    assert session.custom_greeting == "नमस्कार, मी सोलरशिप एनर्जीज कडून प्रिया बोलतेय."
    assert session.system_prompt == "You are प्रिया from सोलरशिप एनर्जीज."
    assert "output_variables" in session.state
    for k in OUTPUT_VARIABLE_KEYS:
        assert k in session.state["output_variables"]



def test_call_session_forwards_voice_id_to_tts():
    from backend.call_session import CallSession

    transport = MagicMock()
    transport.streaming = False
    transport.notify = AsyncMock()
    transport.play = AsyncMock()
    stt = MagicMock()
    engine = MagicMock()
    tts = MagicMock()
    tts.synthesize = AsyncMock(return_value=(b"audio-data", 16000))
    store = MagicMock()

    session = CallSession(
        transport=transport,
        stt=stt,
        engine=engine,
        tts=tts,
        store=store,
        agent_name="Chitra",
        voice_id="chaitra_hi_customer",
    )

    assert session.voice_id == "chaitra_hi_customer"

    # Test _say passes voice_id
    run(session._say("नमस्कार! मी चित्रा बोलतेय."))
    tts.synthesize.assert_called_once_with("नमस्कार! मी चित्रा बोलतेय.", session.language, voice_id="chaitra_hi_customer")


def test_sarvam_tts_provider_resolves_chitra_alias_and_keeps_consistent():
    from backend.providers.tts.sarvam import SarvamTTSProvider, SARVAM_SPEAKER_ALIASES

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    # Minimal 16-sample 16kHz mono WAV in base64
    import base64, io, wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 16)
    b64_audio = base64.b64encode(buf.getvalue()).decode()
    mock_resp.json.return_value = {"audios": [b64_audio]}
    mock_client.post.return_value = mock_resp

    provider = SarvamTTSProvider(
        api_key="test-key",
        model="bulbul:v4-flash",
        voice_id="chitra",
        _client=mock_client,
    )

    # Calling synthesize should normalize 'chitra' alias to 'chaitra_hi_customer'
    res = run(provider.synthesize("नमस्कार, मी चित्रा बोलतेय.", language="mr-IN"))
    assert res["sample_rate"] == 16000
    mock_client.post.assert_called_once()
    payload = mock_client.post.call_args[1]["json"]
    assert payload["speaker"] == "chaitra_hi_customer"
    assert payload["target_language_code"] == "mr-IN"

    # Passing explicit alias in kwargs also maps properly
    mock_client.post.reset_mock()
    run(provider.synthesize("Hello!", language="en-IN", voice_id="chitra"))
    payload2 = mock_client.post.call_args[1]["json"]
    assert payload2["speaker"] == "chaitra_hi_customer"


def test_cloud_call_tts_forwards_voice_id():
    from backend.services.cloud_call_components import CloudCallTTS

    provider = MagicMock()
    provider.get_capabilities.return_value = {"sample_rate": 16000}
    provider.synthesize = AsyncMock(return_value={"audio": b"test-pcm", "sample_rate": 16000})

    cloud_tts = CloudCallTTS(provider)
    audio, sr = run(cloud_tts.synthesize("Hello", language="en-IN", voice_id="chaitra_hi_customer"))

    assert audio == b"test-pcm"
    assert sr == 16000
    provider.synthesize.assert_called_once_with("Hello", language="en-IN", voice_id="chaitra_hi_customer")
