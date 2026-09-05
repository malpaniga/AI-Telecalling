"""Central configuration. Loads backend/.env regardless of the current working
directory, so `uvicorn backend.main:app` (from repo root) and `uvicorn main:app`
(from backend/) both work."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env sits next to this file.
ENV_FILE = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Groq (STT + LLM) ----
    groq_api_key: str = ""
    groq_stt_model: str = "whisper-large-v3-turbo"
    # Drop transcripts Whisper isn't confident are speech (kills silence/echo
    # hallucinations like "Thank you." / "झाल" in any language).
    # Conservative: a safety net for true silence/noise on the phone channel
    # (browser echo is handled at the source by half-duplex mic gating). Kept
    # loose so real accented speech is never wrongly dropped.
    stt_no_speech_threshold: float = 0.8  # drop if no_speech_prob above this
    stt_min_avg_logprob: float = -1.5  # drop if avg_logprob below this
    groq_llm_model: str = "openai/gpt-oss-20b"  # conversation (quality)
    groq_extraction_model: str = "openai/gpt-oss-20b"  # slot extraction (speed)
    # STT routing: English uses Groq Whisper (fast); Indian languages use Sarvam
    # Saaras (Indic-tuned, code-mixing aware). "codemix" keeps English words in
    # English and Hindi in Devanagari — ideal for Hinglish.
    sarvam_stt_model: str = "saaras:v3"
    sarvam_stt_mode: str = "codemix"
    # Only the most recent N messages are sent to the LLM, so time-to-first-token
    # (and thus the pause before Ava speaks) stays flat no matter how long the call runs.
    llm_history_messages: int = 12
    # gpt-oss is a reasoning model; default "medium" reasoning burns the token
    # budget (causing EMPTY replies -> silent stalls) and adds ~400ms/turn. A
    # conversational agent needs almost none, so keep it low.
    groq_reasoning_effort: str = "low"

    # ---- Postgres ----
    postgres_user: str = "voice"
    postgres_password: str = "voice"
    postgres_db: str = "voiceagent"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # ---- Redis ----
    redis_host: str = "localhost"
    redis_port: int = 6379

    # ---- TTS ----
    # "piper" (CPU, local), "sarvam" (Indic-native API), or "orpheus" (local GPU).
    tts_engine: str = "piper"
    # Sarvam Bulbul (native Indian voices, handles Hinglish code-mixing).
    sarvam_tts_api_key: str = ""
    sarvam_model: str = "bulbul:v3"
    sarvam_speaker: str = "kavya"
    sarvam_language: str = "en-IN"  # BCP-47; set hi-IN for native Hindi replies
    piper_model_path: str = "./models/piper/en_US-lessac-medium.onnx"
    piper_use_cuda: bool = False
    # Orpheus TTS (local GPU) — planned upgrade.
    orpheus_model_path: str = "./models/orpheus-3b-Q4_K_M.gguf"
    tts_sample_rate: int = 24000

    # ---- Realtime audio / VAD ----
    # Browser/phone stream 16 kHz mono PCM; the endpointer decides turn boundaries.
    audio_sample_rate: int = 16000
    vad_backend: str = "silero"  # "silero" (neural, noise-robust) or "webrtc" (fallback)
    silero_model_path: str = "./models/silero/silero_vad.onnx"
    vad_speech_prob: float = 0.5  # Silero: window is speech if prob >= this
    vad_energy_floor_dbfs: float = -50.0  # below this loudness never counts as speech
    # webrtc fallback only:
    vad_frame_ms: int = 20
    vad_aggressiveness: int = 3
    # Endpointing / turn-taking (both backends):
    vad_silence_ms: int = 800  # trailing silence that ends a turn (tolerates natural pauses)
    vad_min_speech_ms: int = 250  # ignore utterances with less real speech than this
    vad_speech_confirm_ms: int = 200  # sustained speech before barge-in fires (debounce)
    vad_max_utterance_ms: int = 20000  # force-flush cap so steady noise can't freeze a turn

    # ---- Twilio (Sprint 5) ----
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""  # your Twilio voice number, E.164 e.g. +15551234567
    # Public HTTPS base URL that Twilio can reach (e.g. your ngrok tunnel):
    # https://<subdomain>.ngrok-free.app  — used to build the Media Streams wss URL.
    public_base_url: str = ""

    # ---- App ----
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


settings = Settings()
