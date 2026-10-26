"""Fernet-based credential encryption for stored provider API keys.

The encryption key is derived from the application's secret_key setting via
SHA-256 so no new environment variable is needed. The key is never logged.
Plaintexts are never logged or returned to the browser.

Usage:
    from backend.core.secrets import credential_store
    encrypted = credential_store.encrypt("sk-...")
    plain = credential_store.decrypt(encrypted)
    hint = credential_store.key_hint("sk-...")  # "sk-."[-4:] → last 4 chars
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet

from backend.config import settings

log = logging.getLogger("secrets")


class CredentialStore:
    """Thin wrapper around Fernet for storing/retrieving provider credentials."""

    def __init__(self) -> None:
        # Derive a 32-byte key from the application secret.
        # SHA-256 of the secret produces 32 bytes; Fernet needs base64url-encoded 32 bytes.
        raw_key = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
        fernet_key = base64.urlsafe_b64encode(raw_key)  # exactly 44 chars, valid Fernet key
        self._fernet = Fernet(fernet_key)
        # Do not log the key.

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt a plaintext credential and return Fernet token bytes.

        Raises ValueError if plaintext is empty.
        Never logs the plaintext or the token.
        """
        if not plaintext:
            raise ValueError("Credential plaintext must not be empty")
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt a Fernet token and return the original plaintext string.

        Raises cryptography.fernet.InvalidToken if the token is invalid or
        the key does not match.
        Never logs the plaintext.
        """
        return self._fernet.decrypt(ciphertext).decode("utf-8")

    @staticmethod
    def key_hint(plaintext: str) -> str:
        """Return the last 4 characters of the plaintext for display purposes,
        or a formatted hint for structured credentials like service accounts.

        Returns '****' if the string is shorter than 4 characters.
        Never logs the full plaintext.
        """
        if not plaintext or len(plaintext) < 4:
            return "****"
        stripped = plaintext.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                import json
                info = json.loads(stripped)
                if isinstance(info, dict):
                    if "client_email" in info:
                        email = info["client_email"]
                        return f"sa:{email.split('@')[0]}"[-14:]
                    if "project_id" in info:
                        return f"proj:{info['project_id']}"[-14:]
            except Exception:
                pass
        return stripped[-4:]


# Module-level singleton — import this in other modules.
credential_store = CredentialStore()
