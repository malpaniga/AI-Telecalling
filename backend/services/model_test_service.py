"""Test connectivity and inference for each provider/model combination.

Returns a result dict:
  {status: 'ok' | 'unavailable' | 'error', latency_ms: int, ...}

Never propagates raw exceptions to callers — all are caught and returned as
{status: 'error', error: str(exc)}.

Credentials injected here are decrypted by the service layer and passed in
plaintext; they are never logged.

[MOCK] labels indicate that a test uses patched/synthetic data.
[LIVE]  labels indicate tests that make real API calls when credentials present.
"""

import base64
import io
import logging
import time
import wave

log = logging.getLogger("model_test")

# ---------------------------------------------------------------------------
# Minimal silent WAV for STT probing (10 ms of silence at 16 kHz, 16-bit mono)
# ---------------------------------------------------------------------------
def _make_silent_wav(duration_ms: int = 10, sample_rate: int = 16000) -> bytes:
    num_frames = int(sample_rate * duration_ms / 1000)
    pcm = b"\x00\x00" * num_frames  # 16-bit silence
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


_SILENT_WAV = _make_silent_wav()

# Providers whose adapters raise NotImplementedError (self-hosted, no cloud path)
_TTS_UNAVAILABLE = {"ai4bharat-indicf5", "ai4bharat-indic-tts", "ollama"}
_STT_UNAVAILABLE = {"ai4bharat", "faster-whisper"}
# No LLM providers are in _LLM_UNAVAILABLE any more — gemini now implemented
_LLM_UNAVAILABLE: set[str] = set()

# Local-only providers that must not be activated in cloud-only mode
_LOCAL_ONLY_PROVIDERS = {"ollama", "piper", "faster-whisper", "ai4bharat-indicf5",
                          "ai4bharat-indic-tts", "ai4bharat"}


class ModelTestService:
    """Fire-and-forget connectivity and inference tests per capability.

    Methods labelled [LIVE] make real API calls when credentials are present.
    Methods labelled [MOCK] use patched or fixture data.
    """

    # ------------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------------
    async def test_tts(
        self,
        provider_name: str,
        model_id: str,
        credential: str | None,
        voice: str | None,
        language: str | None,
    ) -> dict:
        """[LIVE] Test TTS provider by synthesizing a short phrase.

        Returns {status, latency_ms} on success or {status, error} on failure.
        Never logs credential.
        """
        if provider_name in _TTS_UNAVAILABLE:
            return {
                "status": "unavailable",
                "error": (
                    f"Provider '{provider_name}' requires self-hosted infrastructure "
                    "and cannot be activated in cloud-only mode."
                ),
            }

        started = time.perf_counter()
        try:
            if provider_name == "sarvam":
                audio = await self._test_sarvam_tts(credential, language)
            elif provider_name == "elevenlabs":
                audio = await self._test_elevenlabs_tts(credential, voice, model_id)
            elif provider_name == "piper":
                audio = await self._test_piper_tts()
            else:
                return {
                    "status": "unavailable",
                    "error": f"No test adapter for TTS provider '{provider_name}'.",
                }
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {
                "status": "ok",
                "latency_ms": latency_ms,
                "sample_output_b64": base64.b64encode(audio).decode() if audio else None,
            }
        except Exception as exc:  # noqa: BLE001
            log.warning("TTS test failed for provider=%s: %s", provider_name, type(exc).__name__)
            return {"status": "error", "error": str(exc)}

    async def _test_sarvam_tts(self, credential: str | None, language: str | None) -> bytes:
        """[LIVE] Test Sarvam TTS using an injected API key."""
        import httpx

        if not credential:
            raise ValueError("SARVAM_API_KEY is required for Sarvam TTS")
        async with httpx.AsyncClient(
            timeout=20.0,
            headers={"api-subscription-key": credential},
        ) as client:
            resp = await client.post(
                "https://api.sarvam.ai/text-to-speech",
                json={
                    "text": "Hello, this is a test.",
                    "target_language_code": language or "en-IN",
                    "speaker": "kavya",
                    "model": "bulbul:v3",
                    "speech_sample_rate": 22050,
                },
            )
            resp.raise_for_status()
            audios = resp.json().get("audios") or []
            if not audios:
                raise RuntimeError("Sarvam returned no audio in test response")
            return base64.b64decode(audios[0])

    async def _test_elevenlabs_tts(
        self,
        credential: str | None,
        voice_id: str | None,
        model_id: str,
    ) -> bytes:
        """[LIVE] Test ElevenLabs TTS using an injected API key."""
        if not credential:
            raise ValueError("ELEVENLABS_API_KEY is required for ElevenLabs TTS")
        from backend.providers.tts.elevenlabs_v2 import (
            ElevenLabsTTSProviderV2,
            DEFAULT_VOICE_ID,
        )
        provider = ElevenLabsTTSProviderV2(
            api_key=credential,
            voice_id=voice_id or DEFAULT_VOICE_ID,
            model=model_id or "eleven_multilingual_v2",
        )
        result = await provider.synthesize("Hello, this is a connectivity test.")
        return result.get("audio", b"")

    async def _test_piper_tts(self) -> bytes:
        """[LIVE] Test Piper TTS using the process-wide engine."""
        from backend.audio.tts import get_tts_engine
        engine = get_tts_engine()
        wav = await engine.synthesize_wav("Hello, this is a test.")
        return wav

    # ------------------------------------------------------------------
    # STT
    # ------------------------------------------------------------------
    async def test_stt(
        self,
        provider_name: str,
        model_id: str,
        credential: str | None,
        language: str | None,
    ) -> dict:
        """[LIVE] Test STT provider with a short silent WAV clip.

        Returns {status, latency_ms, transcript} on success.
        """
        if provider_name in _STT_UNAVAILABLE:
            return {
                "status": "unavailable",
                "error": (
                    f"Provider '{provider_name}' requires self-hosted infrastructure "
                    "and cannot be activated in cloud-only mode."
                ),
            }

        started = time.perf_counter()
        try:
            if provider_name == "groq-whisper":
                transcript = await self._test_groq_stt(credential, language)
            elif provider_name == "sarvam":
                transcript = await self._test_sarvam_stt(credential, language)
            elif provider_name == "google-cloud-stt":
                transcript = await self._test_google_cloud_stt(credential, language)
            else:
                return {
                    "status": "unavailable",
                    "error": f"No test adapter for STT provider '{provider_name}'.",
                }
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {"status": "ok", "latency_ms": latency_ms, "transcript": transcript}
        except Exception as exc:  # noqa: BLE001
            log.warning("STT test failed for provider=%s: %s", provider_name, type(exc).__name__)
            return {"status": "error", "error": str(exc)}

    async def _test_groq_stt(self, credential: str | None, language: str | None) -> str:
        """[LIVE] Test Groq Whisper with the injected API key."""
        from groq import AsyncGroq
        import io as _io

        if not credential:
            raise ValueError("GROQ_API_KEY is required for Groq Whisper")
        client = AsyncGroq(api_key=credential)
        resp = await client.audio.transcriptions.create(
            file=("test.wav", _io.BytesIO(_SILENT_WAV)),
            model="whisper-large-v3-turbo",
            language=language.split("-")[0] if language else None,
            temperature=0,
            response_format="text",
        )
        return str(resp).strip() if resp else ""

    async def _test_sarvam_stt(self, credential: str | None, language: str | None) -> str:
        """[LIVE] Test Sarvam STT with the injected API key."""
        import httpx

        if not credential:
            raise ValueError("SARVAM_API_KEY is required for Sarvam STT")
        async with httpx.AsyncClient(
            timeout=20.0,
            headers={"api-subscription-key": credential},
        ) as client:
            resp = await client.post(
                "https://api.sarvam.ai/speech-to-text",
                files={"file": ("test.wav", _SILENT_WAV, "audio/wav")},
                data={
                    "model": "saaras:v3",
                    "mode": "codemix",
                    "language_code": language or "unknown",
                },
            )
            resp.raise_for_status()
            return (resp.json().get("transcript") or "").strip()

    async def _test_google_cloud_stt(
        self,
        credential: str | None,
        language: str | None,
    ) -> str:
        """[LIVE] Test Google Cloud STT with a silent WAV clip.

        credential: service account JSON string (from credential store),
                    or None to use Application Default Credentials.
        """
        from backend.providers.stt.google_cloud import GoogleCloudSTTProvider
        provider = GoogleCloudSTTProvider(
            project_id="test-project",  # only used for resource names, not auth
            language_code=language or "hi-IN",
            credentials_json=credential,
        )
        transcript = await provider.transcribe(_SILENT_WAV, language=language or "hi-IN")
        return transcript

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------
    async def test_llm(
        self,
        provider_name: str,
        model_id: str,
        credential: str | None,
    ) -> dict:
        """[LIVE] Test LLM provider by requesting a one-sentence hello.

        Returns {status, latency_ms, response} on success.
        """
        if provider_name in _LLM_UNAVAILABLE:
            return {
                "status": "unavailable",
                "error": f"Adapter for '{provider_name}' not yet implemented.",
            }

        started = time.perf_counter()
        try:
            if provider_name == "groq":
                response = await self._test_groq_llm(credential, model_id)
            elif provider_name == "gemini":
                response = await self._test_gemini_llm(credential, model_id)
            elif provider_name == "ollama":
                # Ollama is local-only — test connectivity but return unavailable
                # if the runtime is not reachable (cloud-only mode check happens at activation)
                response = await self._test_ollama_llm(model_id)
            else:
                return {
                    "status": "unavailable",
                    "error": f"No test adapter for LLM provider '{provider_name}'.",
                }
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {"status": "ok", "latency_ms": latency_ms, "response": response}
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM test failed for provider=%s: %s", provider_name, type(exc).__name__)
            return {"status": "error", "error": str(exc)}

    async def _test_groq_llm(self, credential: str | None, model_id: str) -> str:
        """[LIVE] Test Groq LLM with the injected API key."""
        if not credential:
            raise ValueError("GROQ_API_KEY is required for Groq LLM")
        from backend.providers.llm.groq import GroqLLMProvider
        provider = GroqLLMProvider(api_key=credential, model=model_id or "llama-3.3-70b-versatile")
        return await provider.generate(
            [{"role": "user", "content": "Say hello in one sentence."}]
        )

    async def _test_gemini_llm(self, credential: str | None, model_id: str) -> str:
        """[LIVE] Test Gemini LLM with the injected API key."""
        if not credential:
            raise ValueError("GEMINI_API_KEY is required for Gemini LLM")
        from backend.providers.llm.gemini import GeminiLLMProvider
        provider = GeminiLLMProvider(
            api_key=credential,
            model=model_id or "gemini-2.0-flash-lite",
        )
        return await provider.generate(
            [{"role": "user", "content": "Say hello in one sentence."}]
        )

    async def _test_ollama_llm(self, model_id: str) -> str:
        """Test Ollama local runtime reachability then generate.

        NOTE: Ollama is a LOCAL-ONLY provider. This method exists to support
        connectivity detection tests (M41). Ollama cannot be activated in
        cloud-only deployment mode — that enforcement lives in activate_provider().
        Raises RuntimeError when the runtime is not reachable.
        """
        from backend.agent.llm import OllamaLLMClient
        client = OllamaLLMClient(model=model_id or "llama3.2")
        if not await client.is_runtime_reachable():
            raise RuntimeError(
                "Ollama runtime not reachable on localhost:11434. "
                "Ollama is a local-only provider; use groq or gemini for cloud inference."
            )
        return await client.generate(
            [{"role": "user", "content": "Say hello in one sentence."}]
        )