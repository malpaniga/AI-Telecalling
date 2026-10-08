"""Abstract provider interfaces for the AI Telecalling SaaS platform.

Core principle: customer-facing business logic MUST NOT contain provider-specific
branches. All provider differences live inside adapters that implement these ABCs.

Provider-specific IDs/keys are stored as:
  provider: str          e.g. "razorpay", "mock"
  provider_resource_id   e.g. Razorpay order_id
  provider_metadata      free-form dict for provider-specific data
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Optional


class Provider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    def get_capabilities(self) -> dict[str, Any]:
        return {}


class TelephonyProvider(Provider):
    @abstractmethod
    async def initiate_call(self, to: str, from_number: str, **kwargs: Any) -> dict: ...
    @abstractmethod
    async def hangup_call(self, provider_resource_id: str) -> None: ...
    @abstractmethod
    async def get_call_status(self, provider_resource_id: str) -> dict: ...
    async def transfer_call(self, provider_resource_id: str, to: str) -> None: raise NotImplementedError
    async def get_recording(self, provider_resource_id: str) -> dict: return {}
    async def stream_audio(self, provider_resource_id: str) -> AsyncIterator[bytes]:
        if False: yield b""
    async def handle_webhook(self, payload: dict) -> dict: return payload


class STTProvider(Provider):
    @abstractmethod
    async def transcribe(self, audio: bytes, **kwargs: Any) -> str: ...
    async def stream_transcribe(self, audio: AsyncIterator[bytes], **kwargs: Any) -> AsyncIterator[str]:
        chunks = [chunk async for chunk in audio]
        yield await self.transcribe(b"".join(chunks), **kwargs)
    async def stop(self) -> None: return None
    async def get_languages(self) -> list[str]: return []
    async def get_models(self) -> list[str]: return []
    async def estimate_cost(self, **kwargs: Any) -> int: return 0


class TTSProvider(Provider):
    @abstractmethod
    async def synthesize(self, text: str, **kwargs: Any) -> dict: ...
    async def stream(self, text: str, **kwargs: Any) -> AsyncIterator[dict]: yield await self.synthesize(text, **kwargs)
    async def stop(self) -> None: return None
    async def get_voices(self) -> list[dict]: return []
    async def get_models(self) -> list[str]: return []
    async def get_languages(self) -> list[str]: return []
    async def estimate_cost(self, **kwargs: Any) -> int: return 0


class LLMProvider(Provider):
    @abstractmethod
    async def generate(self, messages: list[dict], **kwargs: Any) -> str: ...
    async def stream(self, messages: list[dict], **kwargs: Any) -> AsyncIterator[str]: yield await self.generate(messages, **kwargs)
    async def get_models(self) -> list[str]: return []
    async def estimate_cost(self, **kwargs: Any) -> int: return 0


class PhoneNumberProvider(Provider):
    @abstractmethod
    async def provision_number(self, country_code: str, **kwargs: Any) -> dict: ...
    async def search_numbers(self, country_code: str, **kwargs: Any) -> list[dict]: return []
    async def reserve_number(self, provider_resource_id: str) -> dict: return {"provider_resource_id": provider_resource_id}
    async def release_number(self, provider_resource_id: str) -> None: return None
    async def get_number(self, provider_resource_id: str) -> dict: return {"provider_resource_id": provider_resource_id}


class PaymentProvider(Provider):
    """Abstract payment provider. Razorpay, Stripe, etc. implement this."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider identifier string, e.g. 'razorpay'."""

    @abstractmethod
    async def create_order(
        self,
        amount_paise: int,
        currency: str,
        receipt: str,
        notes: Optional[dict] = None,
    ) -> dict:
        """
        Create a payment order.
        Returns dict with at minimum: provider_order_id, amount_paise, currency.
        """

    @abstractmethod
    async def verify_payment(
        self,
        provider_order_id: str,
        provider_payment_id: str,
        provider_signature: str,
    ) -> bool:
        """Verify payment signature. Returns True if valid."""

    @abstractmethod
    async def fetch_payment(self, provider_payment_id: str) -> dict:
        """Fetch payment details from provider. Returns provider payment dict."""

    @abstractmethod
    async def refund(
        self,
        provider_payment_id: str,
        amount_paise: int,
        reason: str = "",
    ) -> dict:
        """Issue a refund. Returns provider refund dict."""

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature: str,
    ) -> bool:
        """
        Verify webhook signature. Called synchronously (crypto only, no I/O).
        Returns True if the webhook is authentic.
        """

    @abstractmethod
    async def handle_webhook(self, event_type: str, payload: dict) -> dict:
        """
        Process a verified webhook event. Returns a summary dict.
        Raises nothing — caller handles errors.
        """
