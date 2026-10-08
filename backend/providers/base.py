"""Abstract provider interfaces for the AI Telecalling SaaS platform.

Core principle: customer-facing business logic MUST NOT contain provider-specific
branches. All provider differences live inside adapters that implement these ABCs.

Provider-specific IDs/keys are stored as:
  provider: str          e.g. "razorpay", "mock"
  provider_resource_id   e.g. Razorpay order_id
  provider_metadata      free-form dict for provider-specific data
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class PaymentProvider(ABC):
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
