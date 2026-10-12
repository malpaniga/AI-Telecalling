"""Build cloud AI providers from active encrypted admin configurations.

This is the single runtime boundary between the model directory and inference.
It deliberately accepts only managed cloud providers: a database edit cannot
re-enable a local model runtime after the Super Admin UI has rejected it.
"""

from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.secrets import credential_store
from backend.models.model_directory import ProviderConfiguration
from backend.repositories.model_directory_repo import (
    ProviderConfigurationRepo,
    ProviderCredentialRepo,
)


LOCAL_OR_SELF_HOSTED_PROVIDERS = frozenset({
    "ollama", "piper", "faster-whisper", "ai4bharat", "ai4bharat-indicf5",
    "ai4bharat-indic-tts", "orpheus",
})


class CloudProviderRuntime:
    """Loads active provider configurations without exposing their credentials."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._config_repo = ProviderConfigurationRepo(db)
        self._credential_repo = ProviderCredentialRepo(db)

    async def load_provider(self, capability: str) -> Any:
        """Return the tested active cloud provider for ``capability``.

        Credentials are decrypted only in-process and passed immediately to the
        official SDK adapter. They are never included in an exception or return
        value. The caller owns the provider object's lifecycle.
        """
        config = await self._config_repo.find_active_for_capability(capability)
        if config is None:
            raise LookupError(f"No active cloud provider configured for {capability}")
        self._ensure_cloud_only(config)
        credential = await self._credential_for(config.provider_name)
        return self._build_provider(config, credential)

    async def load_call_components(self):
        """Build the three configured cloud components used by a live call."""
        from backend.services.cloud_call_components import build_cloud_call_components

        stt, llm, tts = await self.load_provider("stt"), await self.load_provider("llm"), await self.load_provider("tts")
        return build_cloud_call_components(stt=stt, llm=llm, tts=tts)

    async def _credential_for(self, provider_name: str) -> str | None:
        credential = await self._credential_repo.find_current(provider_name)
        if credential is None:
            return None
        try:
            return credential_store.decrypt(credential.encrypted_value)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Credential decryption failed for provider '{provider_name}'"
            ) from exc

    @staticmethod
    def _ensure_cloud_only(config: ProviderConfiguration) -> None:
        if config.provider_name in LOCAL_OR_SELF_HOSTED_PROVIDERS:
            raise ValueError(
                f"Provider '{config.provider_name}' is not allowed in cloud-only mode"
            )

    @staticmethod
    def _build_provider(config: ProviderConfiguration, credential: str | None) -> Any:
        params = config.extra_params or {}
        if config.capability == "llm":
            if config.provider_name == "gemini":
                from backend.providers.llm.gemini import GeminiLLMProvider
                return GeminiLLMProvider(
                    api_key=_required_credential(config, credential),
                    model=config.model_id,
                    **_llm_options(params),
                )
            if config.provider_name == "groq":
                from backend.providers.llm.groq import GroqLLMProvider
                return GroqLLMProvider(
                    api_key=_required_credential(config, credential),
                    model=config.model_id,
                    **_llm_options(params),
                )
        if config.capability == "tts" and config.provider_name == "elevenlabs":
            from backend.providers.tts.elevenlabs_v2 import ElevenLabsTTSProviderV2
            return ElevenLabsTTSProviderV2(
                api_key=_required_credential(config, credential),
                voice_id=config.voice or "",
                model=config.model_id,
                **_tts_options(params),
            )
        if config.capability == "stt" and config.provider_name == "google-cloud-stt":
            from backend.providers.stt.google_cloud import GoogleCloudSTTProvider
            project_id = params.get("project_id")
            if not isinstance(project_id, str) or not project_id.strip():
                raise ValueError("Google Cloud STT configuration requires extra_params.project_id")
            return GoogleCloudSTTProvider(
                project_id=project_id,
                language_code=config.language or "hi-IN",
                model=config.model_id,
                credentials_json=credential,
                timeout=_timeout(params),
            )
        raise ValueError(
            f"No managed-cloud runtime adapter for {config.capability}/{config.provider_name}"
        )


def _required_credential(config: ProviderConfiguration, credential: str | None) -> str:
    if not credential:
        raise ValueError(f"Active provider '{config.provider_name}' has no current credential")
    return credential


def _timeout(params: dict[str, Any]) -> float:
    value = params.get("timeout", 30.0)
    return float(value) if isinstance(value, (int, float)) else 30.0


def _llm_options(params: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"timeout": _timeout(params)}
    for key in ("temperature", "max_tokens", "max_output_tokens"):
        if key in params and isinstance(params[key], (int, float)):
            result[key] = params[key]
    return result


def _tts_options(params: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"timeout": _timeout(params)}
    if isinstance(params.get("output_format"), str):
        result["output_format"] = params["output_format"]
    return result
