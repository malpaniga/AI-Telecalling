"""Mock payment provider for DEMO_MODE and testing.

Simulates Razorpay behavior without making real API calls.
"""

import hashlib
import hmac
import logging
import uuid
from typing import Optional

from backend.providers.base import PaymentProvider

log = logging.getLogger("provider.mock_payment")

# Fixed test secret used by mock signatures
MOCK_WEBHOOK_SECRET = "mock_webhook_secret_for_testing"


class MockPaymentProvider(PaymentProvider):
    """In-memory mock payment provider. No external calls."""

    # Class-level store for mock payments (shared across instances in tests)
    _orders: dict = {}
    _payments: dict = {}

    def __init__(self, should_fail: bool = False):
        """
        should_fail=True: verify_payment always returns False (simulate failed payment).
        """
        self._should_fail = should_fail
        log.info("MockPaymentProvider initialized (should_fail=%s)", should_fail)

    @property
    def provider_name(self) -> str:
        return "mock"

    async def create_order(
        self,
        amount_paise: int,
        currency: str = "INR",
        receipt: str = "",
        notes: Optional[dict] = None,
    ) -> dict:
        if amount_paise <= 0:
            raise ValueError(f"Amount must be positive; got {amount_paise}")
        order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
        MockPaymentProvider._orders[order_id] = {
            "id": order_id,
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "status": "created",
        }
        log.info("mock order created id=%s amount_paise=%d", order_id, amount_paise)
        return {
            "provider_order_id": order_id,
            "amount_paise": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "status": "created",
        }

    async def verify_payment(
        self,
        provider_order_id: str,
        provider_payment_id: str,
        provider_signature: str,
    ) -> bool:
        if self._should_fail:
            log.info("mock payment verification: FAIL (should_fail=True)")
            return False
        # Accept any signature that starts with "mock_sig_" for easy testing
        valid = provider_signature.startswith("mock_sig_")
        log.info("mock payment verification: %s order=%s", "PASS" if valid else "FAIL",
                 provider_order_id)
        return valid

    async def fetch_payment(self, provider_payment_id: str) -> dict:
        return MockPaymentProvider._payments.get(provider_payment_id, {
            "id": provider_payment_id,
            "status": "captured",
            "amount": 0,
            "currency": "INR",
        })

    async def refund(
        self,
        provider_payment_id: str,
        amount_paise: int,
        reason: str = "",
    ) -> dict:
        refund_id = f"rfnd_mock_{uuid.uuid4().hex[:12]}"
        log.info("mock refund created payment=%s amount=%d", provider_payment_id, amount_paise)
        return {
            "id": refund_id,
            "payment_id": provider_payment_id,
            "amount": amount_paise,
            "status": "processed",
        }

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature: str,
    ) -> bool:
        """Verify against the fixed mock secret."""
        try:
            expected = hmac.new(
                MOCK_WEBHOOK_SECRET.encode(),
                payload_bytes,
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception:  # noqa: BLE001
            return False

    async def handle_webhook(self, event_type: str, payload: dict) -> dict:
        log.info("mock webhook event=%s", event_type)
        return {"provider": "mock", "event": event_type, "handled": True}

    @classmethod
    def reset(cls) -> None:
        """Clear mock state between tests."""
        cls._orders.clear()
        cls._payments.clear()

    @classmethod
    def make_valid_signature(cls, order_id: str, payment_id: str) -> str:
        """Generate a test-valid mock signature for verify_payment."""
        return f"mock_sig_{order_id}_{payment_id}"

    @classmethod
    def make_valid_webhook_signature(cls, payload_bytes: bytes) -> str:
        """Generate a valid webhook signature for testing."""
        return hmac.new(
            MOCK_WEBHOOK_SECRET.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
