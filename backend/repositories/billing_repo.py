"""Billing repositories: Order, Payment, Invoice, WebhookEvent."""

import logging
from datetime import datetime, timezone
from typing import Optional

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from backend.models.base import new_id, utcnow
from backend.models.billing import Invoice, Order, Payment, WebhookEvent
from backend.repositories.base import BaseRepository

log = logging.getLogger("repo.billing")


class OrderRepository(BaseRepository):
    collection_name = "orders"
    model_class = Order

    async def create(
        self,
        organization_id: str,
        order_type: str,
        amount_paise: int,
        description: str = "",
        provider: str = "razorpay",
        plan_id: Optional[str] = None,
        calling_pack_id: Optional[str] = None,
        currency: str = "INR",
        tax_paise: int = 0,
        created_by: Optional[str] = None,
    ) -> Order:
        order = Order(
            _id=new_id(),
            organization_id=organization_id,
            order_type=order_type,
            amount_paise=amount_paise,
            description=description,
            provider=provider,
            plan_id=plan_id,
            calling_pack_id=calling_pack_id,
            currency=currency,
            tax_paise=tax_paise,
            created_by=created_by,
            status="created",
        )
        await self.insert(order)
        log.info("order created id=%s org=%s amount_paise=%d",
                 order.id, organization_id, amount_paise)
        return order

    async def set_provider_order(
        self, order_id: str, provider_order_id: str, metadata: Optional[dict] = None
    ) -> bool:
        updates: dict = {
            "provider_order_id": provider_order_id,
            "status": "pending_payment",
        }
        if metadata:
            updates["provider_metadata"] = metadata
        return await self.update_by_id(order_id, updates)

    async def mark_paid(
        self, order_id: str, payment_id: str, invoice_id: Optional[str] = None
    ) -> bool:
        updates: dict = {"status": "paid", "payment_id": payment_id}
        if invoice_id:
            updates["invoice_id"] = invoice_id
        return await self.update_by_id(order_id, updates)

    async def mark_failed(self, order_id: str) -> bool:
        return await self.update_by_id(order_id, {"status": "failed"})

    async def mark_refunded(self, order_id: str) -> bool:
        return await self.update_by_id(order_id, {"status": "refunded"})

    async def find_by_provider_order_id(self, provider_order_id: str) -> Optional[Order]:
        return await self.find_one({"provider_order_id": provider_order_id})

    async def list_for_org(
        self, organization_id: str, limit: int = 50, skip: int = 0
    ) -> list[Order]:
        return await self.find_many(
            {"organization_id": organization_id},
            sort=[("created_at", DESCENDING)],
            limit=limit,
            skip=skip,
        )


class PaymentRepository(BaseRepository):
    collection_name = "payments"
    model_class = Payment

    async def create(
        self,
        organization_id: str,
        order_id: str,
        amount_paise: int,
        provider: str,
        provider_payment_id: str,
        provider_order_id: str,
        provider_signature: Optional[str] = None,
        provider_metadata: Optional[dict] = None,
        currency: str = "INR",
        description: str = "",
        created_by: Optional[str] = None,
    ) -> Payment:
        payment = Payment(
            _id=new_id(),
            organization_id=organization_id,
            order_id=order_id,
            amount_paise=amount_paise,
            currency=currency,
            provider=provider,
            provider_payment_id=provider_payment_id,
            provider_order_id=provider_order_id,
            provider_signature=provider_signature,
            provider_metadata=provider_metadata or {},
            status="captured",
            description=description,
            created_by=created_by,
        )
        await self.insert(payment)
        log.info("payment created id=%s org=%s amount_paise=%d",
                 payment.id, organization_id, amount_paise)
        return payment

    async def record_refund(
        self, payment_id: str, refund_amount_paise: int
    ) -> bool:
        payment = await self.find_by_id(payment_id)
        if payment is None:
            return False
        new_refunded = payment.refunded_paise + refund_amount_paise
        new_status = (
            "refunded" if new_refunded >= payment.amount_paise
            else "partially_refunded"
        )
        return await self.update_by_id(payment_id, {
            "refunded_paise": new_refunded,
            "status": new_status,
        })

    async def find_by_provider_payment_id(
        self, provider_payment_id: str
    ) -> Optional[Payment]:
        return await self.find_one({"provider_payment_id": provider_payment_id})

    async def list_for_org(
        self, organization_id: str, limit: int = 50, skip: int = 0
    ) -> list[Payment]:
        return await self.find_many(
            {"organization_id": organization_id},
            sort=[("created_at", DESCENDING)],
            limit=limit,
            skip=skip,
        )


class InvoiceRepository(BaseRepository):
    collection_name = "invoices"
    model_class = Invoice

    async def create(
        self,
        organization_id: str,
        order_id: str,
        payment_id: str,
        description: str,
        subtotal_paise: int,
        tax_paise: int,
        currency: str = "INR",
        org_name: str = "",
        org_email: str = "",
        org_gstin: Optional[str] = None,
    ) -> Invoice:
        invoice_number = await self._next_invoice_number()
        total_paise = subtotal_paise + tax_paise
        invoice = Invoice(
            _id=new_id(),
            organization_id=organization_id,
            order_id=order_id,
            payment_id=payment_id,
            invoice_number=invoice_number,
            description=description,
            subtotal_paise=subtotal_paise,
            tax_paise=tax_paise,
            total_paise=total_paise,
            currency=currency,
            org_name=org_name,
            org_email=org_email,
            org_gstin=org_gstin,
        )
        await self.insert(invoice)
        log.info("invoice created id=%s number=%s total_paise=%d",
                 invoice.id, invoice_number, total_paise)
        return invoice

    async def _next_invoice_number(self) -> str:
        from datetime import datetime, timezone
        year = datetime.now(timezone.utc).year
        count = await self.count({"invoice_number": {"$regex": f"^INV-{year}-"}})
        return f"INV-{year}-{count + 1:06d}"

    async def find_by_number(self, invoice_number: str) -> Optional[Invoice]:
        return await self.find_one({"invoice_number": invoice_number})

    async def list_for_org(
        self, organization_id: str, limit: int = 50, skip: int = 0
    ) -> list[Invoice]:
        return await self.find_many(
            {"organization_id": organization_id},
            sort=[("created_at", DESCENDING)],
            limit=limit,
            skip=skip,
        )


class WebhookEventRepository(BaseRepository):
    collection_name = "webhook_events"
    model_class = WebhookEvent

    async def record_and_lock(
        self,
        provider: str,
        event_id: str,
        event_type: str,
        payload: dict,
        signature: Optional[str] = None,
    ) -> Optional[WebhookEvent]:
        """
        Idempotent: record a webhook event.
        Returns the new WebhookEvent if this event_id has NOT been seen before.
        Returns None if it's a duplicate (already processed or being processed).

        Uses find-then-insert with the unique compound key (provider, event_id).
        In production MongoDB the unique index is the final backstop; the
        pre-check is the fast path that avoids a write attempt for duplicates.
        """
        # Pre-check existence — covers both real MongoDB and mongomock (which
        # doesn't raise DuplicateKeyError on unique index violations).
        existing = await self.find_one({"provider": provider, "event_id": event_id})
        if existing is not None:
            log.info("duplicate webhook ignored provider=%s event_id=%s", provider, event_id)
            return None

        event = WebhookEvent(
            _id=new_id(),
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            signature=signature,
            processed=False,
        )
        try:
            await self.insert(event)
            return event
        except DuplicateKeyError:
            # Race condition: another process inserted between our check and insert
            log.info("duplicate webhook (race) ignored provider=%s event_id=%s", provider, event_id)
            return None

    async def mark_processed(
        self,
        webhook_id: str,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> bool:
        return await self.update_by_id(webhook_id, {
            "processed": True,
            "processed_at": utcnow(),
            "processing_result": result,
            "error_message": error,
        })

    async def list_recent(self, limit: int = 100) -> list[WebhookEvent]:
        return await self.find_many(
            {},
            sort=[("received_at", DESCENDING)],
            limit=limit,
        )
