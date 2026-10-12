"""Google Cloud Speech-to-Text v2 provider adapter.

Uses google-cloud-speech SDK (batch synchronous transcription).
Documentation: https://cloud.google.com/speech-to-text/v2/docs

Supported languages (verified 2025-Q3 — Chirp 2 model):
  hi-IN  — Hindi
  mr-IN  — Marathi
  te-IN  — Telugu
  ta-IN  — Tamil
  kn-IN  — Kannada
  gu-IN  — Gujarati
  pa-IN  — Punjabi
  bn-IN  — Bengali
  en-IN  — Indian English
  (+ 120+ other BCP-47 codes)

Authentication:
  Service account JSON key — path supplied via GOOGLE_APPLICATION_CREDENTIALS
  env var, or passed as json_str at construction for credential-store management.
  NEVER commit service account JSON to source control.

Streaming note:
  Google Cloud STT v2 supports streaming via gRPC. This adapter implements
  synchronous (batch) recognition only. Batch recognition is suitable for
  complete utterances sent after VAD silence detection. Real-time streaming
  over WebSocket to telephony is a separate integration milestone.

Audio requirements:
  Format: LINEAR16 (16-bit PCM), FLAC, or WEBM_OPUS
  Sample rate: 16000 Hz recommended
  Channel count: 1 (mono)
  Max payload: 10 MB (sync), larger via async/streaming
"""

import asyncio
import logging
from typing import Any

from backend.providers.base import STTProvider

log = logging.getLogger("providers.stt.google_cloud")

DEFAULT_LANGUAGE = "hi-IN"
SUPPORTED_LANGUAGES = [
    "hi-IN", "mr-IN", "te-IN", "ta-IN", "kn-IN",
    "gu-IN", "pa-IN", "bn-IN", "en-IN", "en-US",
    "or-IN", "as-IN", "ur-IN", "ml-IN",
]

# Chirp 2 is Google's latest multilingual model (verified 2025-Q3)
DEFAULT_RECOGNIZER = "chirp_2"


class GoogleCloudSTTProvider(STTProvider):
    """Google Cloud Speech-to-Text batch transcription adapter.

    credentials_json: path to service account JSON, or None to use
      GOOGLE_APPLICATION_CREDENTIALS env var / Application Default Credentials.
    """

    provider_name = "google-cloud-stt"

    def __init__(
        self,
        project_id: str,
        language_code: str = DEFAULT_LANGUAGE,
        model: str = DEFAULT_RECOGNIZER,
        credentials_json: str | None = None,
        timeout: float = 30.0,
        # Inject pre-built client for testing
        _client: Any | None = None,
    ) -> None:
        if not project_id:
            raise ValueError("Google Cloud project_id must be provided")
        self.project_id = project_id
        self.language_code = language_code
        self.model = model
        self.credentials_json = credentials_json
        self.timeout = timeout

        if _client is not None:
            self._client = _client
            self._async_client = _client  # tests inject same object
        else:
            self._client = None  # created lazily

    def _get_client(self):
        """Lazily create the Speech client to defer credential validation."""
        if self._client is not None:
            return self._client
        from google.cloud import speech
        if self.credentials_json:
            import json
            from google.oauth2.service_account import Credentials
            info = json.loads(self.credentials_json)
            creds = Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            self._client = speech.SpeechClient(credentials=creds)
        else:
            # Use Application Default Credentials
            self._client = speech.SpeechClient()
        return self._client

    def get_capabilities(self) -> dict:
        return {
            "streaming": False,  # batch only in this implementation
            "languages": SUPPORTED_LANGUAGES,
            "provider": "google-cloud-stt",
            "model": self.model,
            "max_audio_bytes": 10 * 1024 * 1024,
        }

    async def transcribe(
        self, audio: bytes, **kwargs: Any
    ) -> str:
        """Transcribe audio bytes to text using Cloud Speech-to-Text v1 batch API.

        audio: raw 16-bit mono PCM or WAV bytes at 16 kHz
        Returns the transcript string, or "" if nothing recognized.
        Raises RuntimeError on auth failure or service error.
        """
        language = kwargs.get("language", self.language_code)
        sample_rate = kwargs.get("sample_rate", 16000)

        # Determine encoding from audio header
        encoding, content = _detect_encoding(audio)

        try:
            transcript = await asyncio.to_thread(
                self._transcribe_sync,
                content,
                encoding,
                sample_rate,
                language,
            )
            return transcript
        except Exception as exc:
            raise RuntimeError(_sanitize_google_error(exc)) from exc

    def _transcribe_sync(
        self,
        audio_content: bytes,
        encoding: int,
        sample_rate: int,
        language: str,
    ) -> str:
        """Run synchronous recognition (in a thread pool)."""
        from google.cloud import speech

        client = self._get_client()

        config = speech.RecognitionConfig(
            encoding=encoding,
            sample_rate_hertz=sample_rate,
            language_code=language,
            model="chirp_2" if self.model == DEFAULT_RECOGNIZER else self.model,
            enable_automatic_punctuation=True,
        )
        audio_obj = speech.RecognitionAudio(content=audio_content)

        response = client.recognize(config=config, audio=audio_obj)
        parts = []
        for result in response.results:
            if result.alternatives:
                parts.append(result.alternatives[0].transcript.strip())
        return " ".join(parts).strip()

    async def get_languages(self) -> list[str]:
        return SUPPORTED_LANGUAGES

    async def get_models(self) -> list[str]:
        return ["chirp_2", "latest_long", "latest_short", "telephony"]


def _detect_encoding(audio: bytes) -> tuple[int, bytes]:
    """Detect audio encoding from header bytes.

    Returns (encoding_enum, raw_bytes_for_api).
    For WAV files, strips the header and returns LINEAR16.
    """
    from google.cloud import speech

    # WAV header: 'RIFF....WAVE'
    if audio[:4] == b"RIFF" and audio[8:12] == b"WAVE":
        # Strip 44-byte WAV header to get raw PCM
        import wave
        import io
        with wave.open(io.BytesIO(audio)) as wf:
            pcm = wf.readframes(wf.getnframes())
        return speech.RecognitionConfig.AudioEncoding.LINEAR16, pcm

    # FLAC header
    if audio[:4] == b"fLaC":
        return speech.RecognitionConfig.AudioEncoding.FLAC, audio

    # OGG/WebM
    if audio[:4] == b"OggS":
        return speech.RecognitionConfig.AudioEncoding.OGG_OPUS, audio

    # Assume raw PCM
    return speech.RecognitionConfig.AudioEncoding.LINEAR16, audio


def _sanitize_google_error(exc: Exception) -> str:
    """Return a sanitized error message — never includes credentials."""
    msg = str(exc)
    if "401" in msg or "UNAUTHENTICATED" in msg or "credentials" in msg.lower():
        return "Google Cloud STT authentication failed — check GOOGLE_APPLICATION_CREDENTIALS"
    if "403" in msg or "PERMISSION_DENIED" in msg:
        return "Google Cloud STT permission denied — check service account IAM roles"
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        return "Google Cloud STT quota exceeded or rate limit hit"
    if "404" in msg or "NOT_FOUND" in msg:
        return "Google Cloud STT resource not found — check project_id and recognizer"
    return f"Google Cloud STT failed ({type(exc).__name__})"
