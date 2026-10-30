"""Orchestration service for the AI Models Directory.

Responsibilities:
  - List and search the catalogue
  - Connect (configure) providers with encrypted credentials
  - Test and activate providers
  - Manage credential rotation and deletion
  - Enforce rate limits on test calls
  - Audit every configuration-changing action

Credentials are never returned to callers (only key_hint + metadata).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.auth import CurrentUser
from backend.core.secrets import credential_store
from backend.models.base import new_id, utcnow
from backend.models.model_directory import (
    AIModelCatalogue,
    ProviderConfiguration,
    ProviderCredential,
)
from backend.repositories.audit_log_repo import AuditLogRepository
from backend.repositories.model_directory_repo import (
    AIModelCatalogueRepo,
    ProviderConfigurationRepo,
    ProviderCredentialRepo,
)
from backend.services.model_test_service import ModelTestService
from backend.languages import is_language_supported, normalize_sarvam_language

log = logging.getLogger("model_directory")

# Max test calls per provider per hour
_TEST_RATE_LIMIT = 10


class RateLimitError(Exception):
    """Raised when the test-call rate limit is exceeded."""


class ModelDirectoryService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._catalogue_repo = AIModelCatalogueRepo(db)
        self._config_repo = ProviderConfigurationRepo(db)
        self._cred_repo = ProviderCredentialRepo(db)
        self._audit_repo = AuditLogRepository(db)
        self._test_svc = ModelTestService()

    # ------------------------------------------------------------------
    # Catalogue
    # ------------------------------------------------------------------
    async def list_catalogue(
        self,
        capability: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[dict]:
        """Return catalogue entries with a pricing_stale flag.

        Entries whose free_tier_verified_date is older than 90 days get
        pricing_stale=True to prompt an admin review.
        """
        if search:
            docs = await self._catalogue_repo.search(search)
            if capability:
                docs = [d for d in docs if d.capability == capability]
            if status:
                docs = [d for d in docs if d.implementation_status == status]
        elif capability and status:
            docs = await self._catalogue_repo.find_many(
                {"capability": capability, "implementation_status": status}
            )
        elif capability:
            docs = await self._catalogue_repo.find_by_capability(capability)
        elif status:
            docs = await self._catalogue_repo.find_by_status(status)
        else:
            docs = await self._catalogue_repo.find_many({})

        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        result = []
        for doc in docs:
            entry = _catalogue_to_dict(doc)
            if doc.free_tier_verified_date:
                try:
                    verified = datetime.fromisoformat(doc.free_tier_verified_date)
                    if verified.tzinfo is None:
                        verified = verified.replace(tzinfo=timezone.utc)
                    entry["pricing_stale"] = verified < cutoff
                except (ValueError, TypeError):
                    entry["pricing_stale"] = True
            else:
                entry["pricing_stale"] = False
            result.append(entry)
        return result

    async def get_model(self, provider_name: str, model_id: str) -> dict:
        """Return a single catalogue entry or raise LookupError."""
        doc = await self._catalogue_repo.find_one(
            {"provider_name": provider_name, "model_id": model_id}
        )
        if doc is None:
            raise LookupError(
                f"Catalogue entry not found: provider={provider_name!r} model={model_id!r}"
            )
        return _catalogue_to_dict(doc)

    # ------------------------------------------------------------------
    # Provider configuration
    # ------------------------------------------------------------------
    async def connect_provider(
        self,
        req: dict,
        credential_plaintext: str | None,
        user: CurrentUser,
    ) -> dict:
        """Validate, encrypt credential, and persist a new ProviderConfiguration.

        Raises:
            ValueError — invalid capability, incompatible language, missing credential
        """
        capability = req.get("capability", "")
        if capability not in {"tts", "stt", "llm"}:
            raise ValueError(f"Invalid capability: {capability!r}. Must be tts, stt, or llm.")

        provider_name = req.get("provider_name", "")
        model_id = req.get("model_id", "")

        # Validate language against catalogue
        language = req.get("language")
        if language and provider_name == "sarvam":
            language = normalize_sarvam_language(language, default=language)

        if language:
            catalogue_entry = await self._catalogue_repo.find_one(
                {"provider_name": provider_name, "model_id": model_id}
            )
            if catalogue_entry:
                supported = catalogue_entry.supported_languages
                if supported and not is_language_supported(language, supported):
                    raise ValueError(
                        f"Language '{language}' is not supported by "
                        f"{provider_name}/{model_id}. "
                        f"Supported: {supported}"
                    )

        # Check credential requirements
        catalogue_entry = await self._catalogue_repo.find_one(
            {"provider_name": provider_name, "model_id": model_id}
        )
        existing_cred = await self._cred_repo.find_current(provider_name)
        if catalogue_entry and catalogue_entry.credential_requirements:
            if not credential_plaintext and not existing_cred:
                raise ValueError(
                    f"A credential is required for {provider_name}. "
                    f"Required: {catalogue_entry.credential_requirements}"
                )

        # Validate Google Cloud STT service account JSON
        if provider_name == "google-cloud-stt" and credential_plaintext:
            import json
            try:
                parsed = json.loads(credential_plaintext.strip())
                if not isinstance(parsed, dict):
                    raise ValueError("Not a JSON object")
                if "type" in parsed and parsed.get("type") != "service_account":
                    raise ValueError("Not a service_account JSON")
            except Exception as err:
                raise ValueError(
                    "Google Cloud STT requires a valid Service Account JSON key (must contain '\"type\": \"service_account\"'). "
                    "API keys are not supported by the Google Cloud Speech API."
                ) from err
            extra = req.get("extra_params") or {}
            if not extra.get("project_id") and parsed.get("project_id"):
                extra["project_id"] = parsed["project_id"]
                req["extra_params"] = extra

        # Encrypt and store credential
        if credential_plaintext:
            clean_cred = credential_plaintext.strip().strip("'\"")
            hint = credential_store.key_hint(clean_cred)
            encrypted = credential_store.encrypt(clean_cred)
            cred = ProviderCredential(
                _id=new_id(),
                provider_name=provider_name,
                encrypted_value=encrypted,
                key_hint=hint,
                created_by=user.user_id,
            )
            # Mark any existing current credential as rotated before storing new one
            await self._cred_repo.mark_rotated(provider_name)
            await self._cred_repo.store_credential(cred)

        # Store configuration
        config = ProviderConfiguration(
            _id=new_id(),
            capability=capability,
            provider_name=provider_name,
            model_id=model_id,
            is_active=False,
            is_fallback=req.get("is_fallback", False),
            voice=req.get("voice"),
            language=language,
            extra_params=req.get("extra_params") or {},
        )
        await self._config_repo.insert(config)

        await self._audit_repo.log(
            action="provider.configure",
            user_id=user.user_id,
            user_email=user.email,
            user_role=user.role,
            resource_type="provider_configuration",
            resource_id=config.id,
            changes={
                "capability": capability,
                "provider_name": provider_name,
                "model_id": model_id,
            },
        )

        return _config_to_dict(config)

    async def test_provider(self, config_id: str, user: CurrentUser) -> dict:
        """Run an inference test for the given configuration.

        Raises:
            LookupError — config not found
            RateLimitError — too many test calls in the last hour
        """
        config = await self._config_repo.find_by_id(config_id)
        if config is None:
            raise LookupError(f"Configuration not found: {config_id}")

        # Rate limit: max 10 test calls per provider per hour
        await self._enforce_rate_limit(config.provider_name)

        # Decrypt credential
        credential = await self._get_decrypted_credential(config.provider_name)

        # Record test call
        await self._record_test_call(config.provider_name)

        # Run test
        result = await self._run_test(config, credential)

        # Update config record
        test_result = result.get("status", "error")
        latency = result.get("latency_ms")
        await self._config_repo.update_by_id(
            config_id,
            {
                "last_tested_at": utcnow(),
                "last_test_result": test_result,
                "last_test_latency_ms": latency,
            },
        )

        await self._audit_repo.log(
            action="provider.test",
            user_id=user.user_id,
            user_email=user.email,
            user_role=user.role,
            resource_type="provider_configuration",
            resource_id=config_id,
            changes={"result": test_result, "latency_ms": latency},
        )

        return result

    async def activate_provider(self, config_id: str, user: CurrentUser) -> dict:
        """Activate a tested configuration.

        Raises:
            LookupError — config not found
            ValueError — config not tested or last test failed
        """
        config = await self._config_repo.find_by_id(config_id)
        if config is None:
            raise LookupError(f"Configuration not found: {config_id}")

        if config.last_test_result != "ok":
            raise ValueError(
                "Cannot activate an untested or failed configuration. "
                "Run a successful test first."
            )

        from backend.services.provider_runtime import LOCAL_OR_SELF_HOSTED_PROVIDERS
        if config.provider_name in LOCAL_OR_SELF_HOSTED_PROVIDERS:
            raise ValueError(
                f"Provider '{config.provider_name}' cannot be activated in cloud-only mode."
            )

        # Deactivate any currently active config for this capability
        await self._config_repo.deactivate_all_for_capability(config.capability)

        # Activate this one
        await self._config_repo.update_by_id(
            config_id,
            {"is_active": True, "activated_at": utcnow()},
        )

        await self._audit_repo.log(
            action="provider.activate",
            user_id=user.user_id,
            user_email=user.email,
            user_role=user.role,
            resource_type="provider_configuration",
            resource_id=config_id,
            changes={
                "capability": config.capability,
                "provider_name": config.provider_name,
                "model_id": config.model_id,
            },
        )

        # Re-fetch to return updated state
        updated = await self._config_repo.find_by_id(config_id)
        return _config_to_dict(updated)

    async def get_active_config(self, capability: str) -> dict | None:
        """Return the active ProviderConfiguration for a capability, or None."""
        config = await self._config_repo.find_active_for_capability(capability)
        if config is None:
            return None
        return _config_to_dict(config)

    async def list_configs(self, capability: str | None = None) -> list[dict]:
        """List all ProviderConfiguration records (credentials stripped)."""
        if capability:
            docs = await self._config_repo.find_all_for_capability(capability)
        else:
            docs = await self._config_repo.find_many({})
        return [_config_to_dict(d) for d in docs]

    async def get_config(self, config_id: str) -> dict:
        """Return a single config or raise LookupError."""
        config = await self._config_repo.find_by_id(config_id)
        if config is None:
            raise LookupError(f"Configuration not found: {config_id}")
        return _config_to_dict(config)

    async def delete_config(self, config_id: str, user: CurrentUser) -> None:
        """Deactivate and delete a configuration."""
        config = await self._config_repo.find_by_id(config_id)
        if config is None:
            raise LookupError(f"Configuration not found: {config_id}")

        await self._config_repo.delete_by_id(config_id)

        await self._audit_repo.log(
            action="provider.config.delete",
            user_id=user.user_id,
            user_email=user.email,
            user_role=user.role,
            resource_type="provider_configuration",
            resource_id=config_id,
            changes={"provider_name": config.provider_name},
        )

    async def update_fallback(
        self,
        config_id: str,
        fallback_config_id: str,
        user: CurrentUser,
    ) -> dict:
        """Mark fallback_config_id as the fallback for config_id's capability."""
        config = await self._config_repo.find_by_id(config_id)
        if config is None:
            raise LookupError(f"Configuration not found: {config_id}")

        fallback = await self._config_repo.find_by_id(fallback_config_id)
        if fallback is None:
            raise LookupError(f"Fallback configuration not found: {fallback_config_id}")

        if fallback.capability != config.capability:
            raise ValueError(
                f"Fallback capability '{fallback.capability}' does not match "
                f"primary capability '{config.capability}'"
            )

        await self._config_repo.update_by_id(fallback_config_id, {"is_fallback": True})

        await self._audit_repo.log(
            action="provider.fallback.set",
            user_id=user.user_id,
            user_email=user.email,
            user_role=user.role,
            resource_type="provider_configuration",
            resource_id=config_id,
            changes={"fallback_config_id": fallback_config_id},
        )

        updated = await self._config_repo.find_by_id(fallback_config_id)
        return _config_to_dict(updated)

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------
    async def list_credentials(self, provider_name: str) -> list[dict]:
        """Return credential metadata only — never encrypted bytes."""
        creds = await self._cred_repo.find_by_provider(provider_name)
        return [_cred_to_safe_dict(c) for c in creds]

    async def rotate_credential(
        self,
        provider_name: str,
        new_plaintext: str,
        user: CurrentUser,
    ) -> None:
        """Encrypt and store a new credential, marking the old one as rotated."""
        if not new_plaintext:
            raise ValueError("New credential must not be empty")

        if provider_name == "google-cloud-stt":
            import json
            try:
                parsed = json.loads(new_plaintext.strip())
                if not isinstance(parsed, dict):
                    raise ValueError("Not a JSON object")
                if "type" in parsed and parsed.get("type") != "service_account":
                    raise ValueError("Not a service_account JSON")
            except Exception as err:
                raise ValueError(
                    "Google Cloud STT requires a valid Service Account JSON key (must contain '\"type\": \"service_account\"'). "
                    "API keys are not supported by the Google Cloud Speech API."
                ) from err

        hint = credential_store.key_hint(new_plaintext)
        encrypted = credential_store.encrypt(new_plaintext)
        await self._cred_repo.mark_rotated(provider_name)
        new_cred = ProviderCredential(
            _id=new_id(),
            provider_name=provider_name,
            encrypted_value=encrypted,
            key_hint=hint,
            created_by=user.user_id,
        )
        await self._cred_repo.store_credential(new_cred)

        await self._audit_repo.log(
            action="provider.credential.rotate",
            user_id=user.user_id,
            user_email=user.email,
            user_role=user.role,
            resource_type="provider_credential",
            resource_id=provider_name,
        )

    async def delete_credential(self, provider_name: str, user: CurrentUser) -> None:
        """Delete all credentials and all configurations for a provider."""
        await self._cred_repo.delete_by_provider(provider_name)
        # Remove all configs that reference this provider
        configs = await self._config_repo.find_many({"provider_name": provider_name})
        for cfg in configs:
            await self._config_repo.delete_by_id(cfg.id)

        await self._audit_repo.log(
            action="provider.credential.delete",
            user_id=user.user_id,
            user_email=user.email,
            user_role=user.role,
            resource_type="provider_credential",
            resource_id=provider_name,
            changes={"configs_deleted": len(configs)},
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _get_decrypted_credential(self, provider_name: str) -> str | None:
        """Fetch and decrypt the current credential. Returns None if not set."""
        cred = await self._cred_repo.find_current(provider_name)
        if cred is None:
            return None
        try:
            return credential_store.decrypt(cred.encrypted_value)
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to decrypt credential for provider=%s", provider_name)
            raise RuntimeError(
                f"Credential decryption failed for provider '{provider_name}'"
            ) from exc

    async def _run_test(self, config: ProviderConfiguration, credential: str | None) -> dict:
        """Dispatch to ModelTestService based on capability."""
        cap = config.capability
        if cap == "tts":
            return await self._test_svc.test_tts(
                config.provider_name,
                config.model_id,
                credential,
                config.voice,
                config.language,
            )
        if cap == "stt":
            return await self._test_svc.test_stt(
                config.provider_name,
                config.model_id,
                credential,
                config.language,
            )
        if cap == "llm":
            return await self._test_svc.test_llm(
                config.provider_name,
                config.model_id,
                credential,
                config.extra_params,
            )
        return {"status": "error", "error": f"Unknown capability: {cap}"}

    async def list_provider_live_models(self, provider_name: str) -> list[str]:
        """Return available models for a provider, querying provider API if credentials exist."""
        provider_name = provider_name.strip().lower()

        # Catalogue models for this provider
        cat_docs = await self._catalogue_repo.find_many({"provider_name": provider_name})
        cat_models = {d.model_id for d in cat_docs}

        # Check if we have credentials to do live querying
        cred_doc = await self._cred_repo.find_current(provider_name)
        plaintext_key = None
        if cred_doc and cred_doc.encrypted_value:
            try:
                plaintext_key = credential_store.decrypt(cred_doc.encrypted_value)
            except Exception as e:
                log.warning("Could not decrypt credential for live models lookup: %s", e)

        if provider_name in ("groq", "groq-whisper"):
            from backend.providers.llm.groq import GroqLLMProvider, SUPPORTED_MODELS
            cat_models.update(SUPPORTED_MODELS)
            if plaintext_key:
                try:
                    prov = GroqLLMProvider(api_key=plaintext_key)
                    live = await prov.list_available_models()
                    cat_models.update(live)
                except Exception as e:
                    log.warning("Failed live Groq model lookup: %s", e)
        elif provider_name == "gemini":
            cat_models.update([
                "gemini-2.0-flash-lite",
                "gemini-3.1-flash-lite",
                "gemini-3.5-flash-lite",
                "gemini-3.8-flash",
            ])
        elif provider_name == "sarvam":
            cat_models.update([
                "sarvam-105b-conversations",
                "sarvam-105b",
                "saaras:v4",
                "saaras:v4-turbo",
                "saaras-v3",
                "bulbul:v4-flash",
                "bulbul:v4",
                "bulbul:v3",
            ])
        elif provider_name == "elevenlabs":
            cat_models.update([
                "eleven_multilingual_v2",
                "eleven_flash_v2_5",
                "eleven_turbo_v2_5",
                "eleven_v4",
                "eleven_v4_turbo",
            ])

        return sorted(cat_models)

    async def _enforce_rate_limit(self, provider_name: str) -> None:
        """Raise RateLimitError if too many test calls in the last hour."""
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        count = await self._db["provider_test_log"].count_documents(
            {"provider_name": provider_name, "created_at": {"$gte": since}}
        )
        if count >= _TEST_RATE_LIMIT:
            raise RateLimitError(
                f"Rate limit exceeded for provider '{provider_name}': "
                f"max {_TEST_RATE_LIMIT} test calls per hour."
            )

    async def _record_test_call(self, provider_name: str) -> None:
        """Insert a record into provider_test_log for rate-limiting."""
        await self._db["provider_test_log"].insert_one(
            {"provider_name": provider_name, "created_at": datetime.now(timezone.utc)}
        )


# ------------------------------------------------------------------
# Serialization helpers
# ------------------------------------------------------------------
def _catalogue_to_dict(doc: AIModelCatalogue) -> dict:
    """Serialize catalogue entry. No credentials present in this model."""
    return {
        "id": doc.id,
        "provider_name": doc.provider_name,
        "model_id": doc.model_id,
        "capability": doc.capability,
        "hosting_mode": doc.hosting_mode,
        "supported_languages": doc.supported_languages,
        "streaming_supported": doc.streaming_supported,
        "credential_requirements": doc.credential_requirements,
        "setup_requirements": doc.setup_requirements,
        "license_spdx": doc.license_spdx,
        "commercial_use_allowed": doc.commercial_use_allowed,
        "free_tier_info": doc.free_tier_info,
        "free_tier_verified_date": doc.free_tier_verified_date,
        "pricing_per_minute_usd": doc.pricing_per_minute_usd,
        "doc_url": doc.doc_url,
        "model_card_url": doc.model_card_url,
        "implementation_status": doc.implementation_status,
        "notes": doc.notes,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


def _config_to_dict(doc: ProviderConfiguration) -> dict:
    """Serialize config. Never include encrypted credentials."""
    return {
        "id": doc.id,
        "org_id": doc.org_id,
        "capability": doc.capability,
        "provider_name": doc.provider_name,
        "model_id": doc.model_id,
        "is_active": doc.is_active,
        "is_fallback": doc.is_fallback,
        "voice": doc.voice,
        "language": doc.language,
        "extra_params": doc.extra_params,
        "last_tested_at": doc.last_tested_at.isoformat() if doc.last_tested_at else None,
        "last_test_result": doc.last_test_result,
        "last_test_latency_ms": doc.last_test_latency_ms,
        "activated_at": doc.activated_at.isoformat() if doc.activated_at else None,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


def _cred_to_safe_dict(doc: ProviderCredential) -> dict:
    """Return credential metadata ONLY — never encrypted_value."""
    return {
        "provider_name": doc.provider_name,
        "key_hint": doc.key_hint,
        "created_by": doc.created_by,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "rotated_at": doc.rotated_at.isoformat() if doc.rotated_at else None,
    }
