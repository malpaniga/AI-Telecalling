"""Central configuration for the AI Telecalling SaaS platform.

Loads backend/.env regardless of the working directory.
All settings have sensible defaults; only secrets have empty defaults.
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- App ----
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"
    public_base_url: str = ""

    # ---- Demo mode ----
    demo_mode: bool = False

    # ---- MongoDB ----
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "telecalling_saas"

    # ---- Redis ----
    redis_url: str = "redis://localhost:6379/0"

    # ---- Auth (JWT) ----
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # ---- Groq (STT + LLM — legacy, still used by existing audio pipeline) ----
    groq_api_key: str = ""
    groq_stt_model: str = "whisper-large-v3-turbo"
    groq_llm_model: str = "openai/gpt-oss-20b"
    groq_extraction_model: str = "openai/gpt-oss-20b"
    groq_reasoning_effort: str = "low"
    stt_no_speech_threshold: float = 0.8
    stt_min_avg_logprob: float = -1.5
    llm_history_messages: int = 12

    # ---- Sarvam (STT + TTS) ----
    sarvam_api_key: str = ""
    # Legacy alias still accepted
    sarvam_tts_api_key: str = ""
    sarvam_stt_model: str = "saaras:v3"
    sarvam_stt_mode: str = "codemix"
    sarvam_model: str = "bulbul:v3"
    sarvam_speaker: str = "kavya"
    sarvam_language: str = "en-IN"

    # ---- ElevenLabs ----
    elevenlabs_api_key: str = ""

    # ---- OpenAI / OpenAI-compatible ----
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # ---- Razorpay ----
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # ---- Twilio ----
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # ---- Exotel ----
    exotel_api_key: str = ""
    exotel_api_token: str = ""
    exotel_sid: str = ""
    exotel_subdomain: str = "api.exotel.com"

    # ---- TTS ----
    tts_engine: str = "sarvam"
    tts_sample_rate: int = 24000
    piper_model_path: str = "./models/piper/en_US-lessac-medium.onnx"
    piper_use_cuda: bool = False

    # ---- VAD / audio ----
    audio_sample_rate: int = 16000
    vad_backend: str = "silero"
    silero_model_path: str = "./models/silero/silero_vad.onnx"
    vad_speech_prob: float = 0.5
    vad_energy_floor_dbfs: float = -50.0
    vad_frame_ms: int = 20
    vad_aggressiveness: int = 3
    vad_silence_ms: int = 800
    vad_min_speech_ms: int = 250
    vad_speech_confirm_ms: int = 200
    vad_max_utterance_ms: int = 20000

    @property
    def effective_sarvam_key(self) -> str:
        """Return whichever Sarvam key is set."""
        return self.sarvam_api_key or self.sarvam_tts_api_key

    @property
    def redis_host(self) -> str:
        """Legacy compat for existing session.py."""
        import urllib.parse
        parsed = urllib.parse.urlparse(self.redis_url)
        return parsed.hostname or "localhost"

    @property
    def redis_port(self) -> int:
        import urllib.parse
        parsed = urllib.parse.urlparse(self.redis_url)
        return parsed.port or 6379


settings = Settings()
