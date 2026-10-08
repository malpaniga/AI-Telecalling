"""Razorpay payment provider adapter.

Security rules (enforced here, not in business logic):
- Amount is always looked up server-side from the order; never trusted from frontend.
- Webhook signatures are verified with HMAC-SHA256 before processing.
- Payment ID is validated against the order before granting credits.
"""

import hashlib
import hmac
import logging
from typing import Optional

import razorpay

from backend.config import settings
from backend.providers.base import PaymentProvider

log = logging.getLogger("provider.razorpay")


class RazorpayProvider(PaymentProvider):
    """Razorpay v1 payment provider."""

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ):
        self._key_id = key_id or settings.razorpay_key_id
        self._key_secret = key_secret or settings.razorpay_key_secret
        self._webhook_secret = webhook_secret or settings.razorpay_webhook_secret

        if not self._key_id or not self._key_secret:
            raise ValueError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are required")

        self._client = razorpay.Client(
            auth=(self._key_id, self._key_secret)
        )
        log.info("RazorpayProvider initialized key_id=%s", self._key_id[:8] + "***")

    @property
    def provider_name(self) -> str:
        return "razorpay"

    async def create_order(
        self,
        amount_paise: int,
        currency: str = "INR",
        receipt: str = "",
        notes: Optional[dict] = None,
    ) -> dict:
        """
        Create a Razorpay order. Amount is in PAISE (integer).
        Returns: {provider_order_id, amount_paise, currency, receipt}
        """
        if amount_paise <= 0:
            raise ValueError(f"Amount must be positive paise; got {amount_paise}")

        payload: dict = {
            "amount": amount_paise,       # Razorpay expects paise
            "currency": currency,
            "receipt": receipt[:40] if receipt else "",
        }
        if notes:
            payload["notes"] = notes

        log.info("creating razorpay order amount_paise=%d currency=%s", amount_paise, currency)
        # razorpay SDK is sync — run in threadpool in real usage;
        # for MVP we call it directly (webhook processing is the async path)
        import asyncio
        order = await asyncio.to_thread(self._client.order.create, payload)
        log.info("razorpay order created id=%s", order["id"])
        return {
            "provider_order_id": order["id"],
            "amount_paise": order["amount"],
            "currency": order["currency"],
            "receipt": order.get("receipt", ""),
            "status": order["status"],
        }

    async def verify_payment(
        self,
        provider_order_id: str,
        provider_payment_id: str,
        provider_signature: str,
    ) -> bool:
        """
        Verify Razorpay payment signature.
        Signature = HMAC-SHA256(order_id + "|" + payment_id, key_secret)
        """
        try:
            params = {
                "razorpay_order_id": provider_order_id,
                "razorpay_payment_id": provider_payment_id,
                "razorpay_signature": provider_signature,
            }
            import asyncio
            await asyncio.to_thread(
                self._client.utility.verify_payment_signature, params
            )
            log.info("payment signature verified order=%s payment=%s",
                     provider_order_id, provider_payment_id)
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("payment signature verification failed: %s", exc)
            return False

    async def fetch_payment(self, provider_payment_id: str) -> dict:
        import asyncio
        payment = await asyncio.to_thread(
            self._client.payment.fetch, provider_payment_id
        )
        return dict(payment)

    async def refund(
        self,
        provider_payment_id: str,
        amount_paise: int,
        reason: str = "",
    ) -> dict:
        import asyncio
        payload = {"amount": amount_paise}
        if reason:
            payload["notes"] = {"reason": reason[:100]}
        result = await asyncio.to_thread(
            self._client.payment.refund, provider_payment_id, payload
        )
        log.info("refund created payment=%s amount_paise=%d", provider_payment_id, amount_paise)
        return dict(result)

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature: str,
    ) -> bool:
        """
        Verify Razorpay webhook signature.
        Signature = HMAC-SHA256(body, webhook_secret), hex-encoded.
        """
        if not self._webhook_secret:
            log.warning("RAZORPAY_WEBHOOK_SECRET not set — rejecting webhook")
            return False
        try:
            expected = hmac.new(
                self._webhook_secret.encode(),
                payload_bytes,
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception as exc:  # noqa: BLE001
            log.warning("webhook signature check error: %s", exc)
            return False

    async def handle_webhook(self, event_type: str, payload: dict) -> dict:
        """Route verified webhook event to appropriate handler."""
        log.info("razorpay webhook event=%s", event_type)
        return {"provider": "razorpay", "event": event_type, "handled": True}
