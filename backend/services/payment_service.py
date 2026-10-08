"""Payment service — server-authoritative payment flow.

SECURITY RULES (enforced here):
1. Frontend sends ONLY plan_id or calling_pack_id — never the amount.
2. Backend looks up amount from the plan/pack in the database.
3. Backend creates the Razorpay order.
4. Backend verifies the payment signature before granting anything.
5. Webhook events are idempotent via WebhookEvent collection.
6. Credits/subscriptions are NEVER granted based on frontend-reported success.

Flow:
  POST /billing/orders                 → create_subscription_order()
  Frontend: Razorpay checkout          → user completes payment
  POST /billing/verify                 → verify_and_fulfill()
  OR
  POST /billing/webhook                → process_webhook() (server-to-server)
"""

import hashlib
import hmac
import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.config import settings
from backend.models.billing import Order
from backend.providers.base import PaymentProvider
from backend.repositories.billing_repo import (
    InvoiceRepository,
    OrderRepository,
    PaymentRepository,
    WebhookEventRepository,
)
from backend.repositories.organization_repo import OrganizationRepository
from backend.repositories.subscription_repo import SubscriptionPlanRepository
from backend.services.subscription_service import SubscriptionService

log = logging.getLogger("service.payment")


def get_payment_provider(db=None) -> PaymentProvider:
    """Return the appropriate payment provider based on config."""
    if settings.demo_mode:
        from backend.providers.payment.mock import MockPaymentProvider
        return MockPaymentProvider()
    if settings.razorpay_key_id and settings.razorpay_key_secret:
        from backend.providers.payment.razorpay import RazorpayProvider
        return RazorpayProvider()
    # Fall back to mock if no Razorpay keys configured
    from backend.providers.payment.mock import MockPaymentProvider
    log.warning("No Razorpay keys — using mock payment provider")
    return MockPaymentProvider()


class PaymentService:
    def __init__(self, db: AsyncIOMotorDatabase, provider: Optional[PaymentProvider] = None):
        self.db = db
        self.provider = provider or get_payment_provider(db)
        self.order_repo = OrderRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.invoice_repo = InvoiceRepository(db)
        self.webhook_repo = WebhookEventRepository(db)
        self.plan_repo = SubscriptionPlanRepository(db)
        self.sub_service = SubscriptionService(db)
        self.org_repo = OrganizationRepository(db)

    # ---- Order creation ----

    async def create_calling_pack_order(
        self,
        organization_id: str,
        calling_pack_id: str,
        created_by: Optional[str] = None,
    ) -> dict:
        """
        Create a server-side order for a calling pack purchase.
        Amount is looked up from the pack — frontend never determines it.
        """
        pack = await self.db["calling_packs"].find_one({"_id": calling_pack_id})
        if pack is None:
            raise ValueError(f"CallingPack {calling_pack_id} not found")
        if not pack.get("is_active", True):
            raise ValueError("This calling pack is no longer available")

        amount_paise = pack["price_paise"]
        if amount_paise == 0:
            raise ValueError("This pack has no charge — request it via admin grant")

        order = await self.order_repo.create(
            organization_id=organization_id,
            order_type="calling_pack",
            amount_paise=amount_paise,
            description=f"{pack['name']} ({pack['credits'] + pack.get('bonus_credits', 0)} credits)",
            provider=self.provider.provider_name,
            calling_pack_id=calling_pack_id,
            currency="INR",
            created_by=created_by,
        )

        provider_result = await self.provider.create_order(
            amount_paise=amount_paise,
            currency="INR",
            receipt=order.id[:40],
            notes={"pack_slug": pack.get("slug", ""), "org_id": organization_id},
        )

        await self.order_repo.set_provider_order(
            order.id, provider_result["provider_order_id"], metadata=provider_result
        )

        log.info("calling_pack order created org=%s pack=%s amount_paise=%d",
                 organization_id, calling_pack_id, amount_paise)

        return {
            "order_id": order.id,
            "provider_order_id": provider_result["provider_order_id"],
            "amount_paise": amount_paise,
            "amount_inr": amount_paise / 100,
            "currency": "INR",
            "description": order.description,
            "key_id": settings.razorpay_key_id if not settings.demo_mode else "rzp_test_mock",
        }

    async def create_subscription_order(
        self,
        organization_id: str,
        plan_id: str,
        billing_cycle: str = "monthly",
        created_by: Optional[str] = None,
    ) -> dict:
        """
        Step 1: Create a server-side order for a subscription purchase.
        Amount is looked up from the plan — frontend never determines it.
        Returns: {order_id, provider_order_id, amount_paise, currency, key_id}
        """
        plan = await self.plan_repo.find_by_id(plan_id)
        if plan is None:
            raise ValueError(f"Plan {plan_id} not found")
        if not plan.is_active:
            raise ValueError(f"Plan '{plan.name}' is not available")

        # Server determines amount — never from frontend
        if billing_cycle == "yearly":
            amount_paise = plan.price_yearly_paise
        else:
            amount_paise = plan.price_monthly_paise

        if amount_paise == 0:
            raise ValueError("This plan has no charge (use activate directly for free plans)")

        # Create our internal order record
        order = await self.order_repo.create(
            organization_id=organization_id,
            order_type="subscription",
            amount_paise=amount_paise,
            description=f"{plan.name} subscription ({billing_cycle})",
            provider=self.provider.provider_name,
            plan_id=plan_id,
            currency="INR",
            created_by=created_by,
        )

        # Create provider order
        provider_result = await self.provider.create_order(
            amount_paise=amount_paise,
            currency="INR",
            receipt=order.id[:40],
            notes={"plan_slug": plan.slug, "billing_cycle": billing_cycle,
                   "org_id": organization_id},
        )

        # Link provider order to our order
        await self.order_repo.set_provider_order(
            order.id,
            provider_result["provider_order_id"],
            metadata=provider_result,
        )

        log.info("subscription order created org=%s plan=%s amount_paise=%d",
                 organization_id, plan.slug, amount_paise)

        return {
            "order_id": order.id,
            "provider_order_id": provider_result["provider_order_id"],
            "amount_paise": amount_paise,
            "amount_inr": amount_paise / 100,
            "currency": "INR",
            "description": order.description,
            # key_id is safe to return (public key, not secret)
            "key_id": settings.razorpay_key_id if not settings.demo_mode else "rzp_test_mock",
        }

    # ---- Payment verification ----

    async def verify_and_fulfill(
        self,
        order_id: str,
        provider_payment_id: str,
        provider_order_id: str,
        provider_signature: str,
        organization_id: str,
        created_by: Optional[str] = None,
    ) -> dict:
        """
        Step 2: Verify payment signature and fulfill the order.
        NEVER grants credits/subscription without server-side signature verification.
        """
        # Load our order
        order = await self.order_repo.find_by_id(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order.organization_id != organization_id:
            raise PermissionError("Order does not belong to this organization")
        if order.status == "paid":
            log.warning("double payment attempt for order=%s", order_id)
            return {"status": "already_paid", "order_id": order_id}
        if order.status not in ("created", "pending_payment"):
            raise ValueError(f"Order is not payable (status={order.status})")

        # VERIFY SIGNATURE — this is the critical security check
        is_valid = await self.provider.verify_payment(
            provider_order_id=provider_order_id,
            provider_payment_id=provider_payment_id,
            provider_signature=provider_signature,
        )
        if not is_valid:
            await self.order_repo.mark_failed(order_id)
            log.warning("payment signature INVALID order=%s payment=%s",
                        order_id, provider_payment_id)
            raise ValueError("Payment verification failed: invalid signature")

        # Create immutable payment record
        payment = await self.payment_repo.create(
            organization_id=organization_id,
            order_id=order_id,
            amount_paise=order.amount_paise,
            provider=self.provider.provider_name,
            provider_payment_id=provider_payment_id,
            provider_order_id=provider_order_id,
            provider_signature=provider_signature,
            description=order.description,
            created_by=created_by,
        )

        # Generate invoice
        org = await self.org_repo.find_by_id(organization_id)
        invoice = await self.invoice_repo.create(
            organization_id=organization_id,
            order_id=order_id,
            payment_id=payment.id,
            description=order.description,
            subtotal_paise=order.amount_paise,
            tax_paise=order.tax_paise,
            org_name=org.name if org else "",
            org_email=org.email if org else "",
            org_gstin=org.gstin if org else None,
        )

        # Fulfill based on order type
        fulfillment = await self._fulfill_order(order, payment.id)

        # Mark order as paid
        await self.order_repo.mark_paid(order_id, payment.id, invoice.id)

        log.info("payment fulfilled order=%s payment=%s type=%s",
                 order_id, payment.id, order.order_type)

        return {
            "status": "paid",
            "order_id": order_id,
            "payment_id": payment.id,
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "amount_paise": payment.amount_paise,
            "amount_inr": payment.amount_paise / 100,
            **fulfillment,
        }

    async def _fulfill_order(self, order: Order, payment_id: str) -> dict:
        """Dispatch fulfillment based on order type."""
        if order.order_type == "subscription":
            if order.plan_id:
                # Determine billing_cycle from order description
                billing_cycle = "yearly" if "yearly" in order.description.lower() else "monthly"
                sub = await self.sub_service.activate_plan(
                    organization_id=order.organization_id,
                    plan_id=order.plan_id,
                    billing_cycle=billing_cycle,
                    created_by=order.created_by,
                    payment_id=payment_id,
                )
                return {"subscription_id": sub.id, "plan_slug": sub.plan_slug}
        elif order.order_type == "calling_pack":
            if order.calling_pack_id:
                from backend.services.wallet_service import WalletService
                wallet_svc = WalletService(self.db)
                wallet_result = await wallet_svc.purchase_credits(
                    organization_id=order.organization_id,
                    calling_pack_id=order.calling_pack_id,
                    order_id=order.id,
                    idempotency_key=f"purchase:{order.id}",
                )
                return {
                    "credits_granted": wallet_result["credits_granted"],
                    "new_balance": wallet_result["new_balance"],
                }
            return {"credits_granted": 0, "note": "no calling_pack_id on order"}
        return {}

    # ---- Refund ----

    async def refund_payment(
        self,
        payment_id: str,
        amount_paise: Optional[int] = None,
        reason: str = "",
    ) -> dict:
        """Issue a full or partial refund."""
        payment = await self.payment_repo.find_by_id(payment_id)
        if payment is None:
            raise ValueError(f"Payment {payment_id} not found")
        if payment.status in ("refunded",):
            raise ValueError("Payment has already been fully refunded")

        # Default to full refund
        refund_amount = amount_paise or (payment.amount_paise - payment.refunded_paise)
        if refund_amount <= 0:
            raise ValueError("Nothing left to refund")

        result = await self.provider.refund(
            provider_payment_id=payment.provider_payment_id,
            amount_paise=refund_amount,
            reason=reason,
        )
        await self.payment_repo.record_refund(payment_id, refund_amount)

        # Mark order as refunded if fully refunded
        order = await self.order_repo.find_by_id(payment.order_id)
        if order:
            new_refunded = payment.refunded_paise + refund_amount
            if new_refunded >= payment.amount_paise:
                await self.order_repo.mark_refunded(order.id)

        log.info("refund issued payment=%s amount_paise=%d", payment_id, refund_amount)
        return {
            "refund_id": result.get("id"),
            "payment_id": payment_id,
            "amount_refunded_paise": refund_amount,
            "provider_result": result,
        }

    # ---- Webhook processing ----

    async def process_webhook(
        self,
        payload_bytes: bytes,
        signature: str,
        provider: str = "razorpay",
    ) -> dict:
        """
        Process an inbound provider webhook.
        1. Verify signature (synchronous crypto)
        2. Record for idempotency
        3. Process event
        """
        import json

        # 1. Verify webhook signature
        if not self.provider.verify_webhook_signature(payload_bytes, signature):
            log.warning("invalid webhook signature from provider=%s", provider)
            raise ValueError("Invalid webhook signature")

        # 2. Parse payload
        try:
            payload = json.loads(payload_bytes)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e}") from e

        event_type = payload.get("event", "unknown")
        # Razorpay uses payload.entity.id or payload.id as event_id
        event_id = (
            payload.get("payload", {})
            .get("payment", {})
            .get("entity", {})
            .get("id")
            or payload.get("id")
            or f"{provider}_{event_type}_{id(payload)}"
        )

        # 3. Idempotency check
        webhook_event = await self.webhook_repo.record_and_lock(
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            signature=signature,
        )
        if webhook_event is None:
            return {"status": "duplicate", "event_type": event_type}

        # 4. Process
        try:
            result = await self._handle_webhook_event(event_type, payload)
            await self.webhook_repo.mark_processed(webhook_event.id, result=result)
            return {"status": "processed", "event_type": event_type, **result}
        except Exception as exc:  # noqa: BLE001
            await self.webhook_repo.mark_processed(
                webhook_event.id, error=str(exc)
            )
            log.exception("webhook processing error event=%s: %s", event_type, exc)
            return {"status": "error", "event_type": event_type, "error": str(exc)}

    async def _handle_webhook_event(self, event_type: str, payload: dict) -> dict:
        """Handle specific Razorpay webhook events."""
        if event_type == "payment.captured":
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            razorpay_order_id = payment_entity.get("order_id")
            razorpay_payment_id = payment_entity.get("id")
            if razorpay_order_id:
                order = await self.order_repo.find_by_provider_order_id(razorpay_order_id)
                if order and order.status == "pending_payment":
                    log.info("webhook: payment.captured for order=%s", order.id)
                    # Fulfill if not already done via verify_and_fulfill
                    await self._fulfill_order(order, razorpay_payment_id or "")
                    await self.order_repo.mark_paid(order.id, razorpay_payment_id or "")
            return {"handled": True, "event": "payment.captured"}

        elif event_type == "payment.failed":
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            razorpay_order_id = payment_entity.get("order_id")
            if razorpay_order_id:
                order = await self.order_repo.find_by_provider_order_id(razorpay_order_id)
                if order:
                    await self.order_repo.mark_failed(order.id)
            return {"handled": True, "event": "payment.failed"}

        elif event_type == "refund.processed":
            return {"handled": True, "event": "refund.processed"}

        else:
            log.info("unhandled webhook event type: %s", event_type)
            return {"handled": False, "event": event_type}
