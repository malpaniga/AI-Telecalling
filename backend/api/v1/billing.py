"""Billing API endpoints.

POST /api/v1/billing/orders/subscription  — create subscription order (server-side amount)
POST /api/v1/billing/verify               — verify payment + fulfill
POST /api/v1/billing/webhook              — Razorpay webhook (no auth, sig-verified)
POST /api/v1/billing/refund/{payment_id}  — admin refund
GET  /api/v1/billing/orders               — list org orders
GET  /api/v1/billing/payments             — list org payments
GET  /api/v1/billing/invoices             — list org invoices
GET  /api/v1/billing/invoices/{id}        — get invoice
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator

from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.services.payment_service import PaymentService

log = logging.getLogger("api.billing")
router = APIRouter(prefix="/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class CreateSubscriptionOrderRequest(BaseModel):
    plan_id: str
    billing_cycle: str = "monthly"

    @field_validator("billing_cycle")
    @classmethod
    def valid_cycle(cls, v: str) -> str:
        if v not in ("monthly", "yearly"):
            raise ValueError("billing_cycle must be 'monthly' or 'yearly'")
        return v


class VerifyPaymentRequest(BaseModel):
    order_id: str
    provider_payment_id: str
    provider_order_id: str
    provider_signature: str


class RefundRequest(BaseModel):
    amount_paise: Optional[int] = None
    reason: str = ""

    @field_validator("amount_paise")
    @classmethod
    def non_negative(cls, v):
        if v is not None and v <= 0:
            raise ValueError("amount_paise must be positive")
        return v


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/orders/subscription")
async def create_subscription_order(
    body: CreateSubscriptionOrderRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Create a payment order for a subscription.
    Frontend sends plan_id — backend determines amount. Never trust frontend amount.
    """
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    if user.role not in ("organization_owner", "organization_admin") and not user.is_platform:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    db = get_db()
    svc = PaymentService(db)
    try:
        result = await svc.create_subscription_order(
            organization_id=user.org_id,
            plan_id=body.plan_id,
            billing_cycle=body.billing_cycle,
            created_by=user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.post("/verify")
async def verify_payment(
    body: VerifyPaymentRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Verify payment signature and fulfill the order.
    Returns 400 if signature is invalid.
    """
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")

    db = get_db()
    svc = PaymentService(db)
    try:
        result = await svc.verify_and_fulfill(
            order_id=body.order_id,
            provider_payment_id=body.provider_payment_id,
            provider_order_id=body.provider_order_id,
            provider_signature=body.provider_signature,
            organization_id=user.org_id,
            created_by=user.user_id,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.post("/webhook", include_in_schema=False)
async def razorpay_webhook(request: Request):
    """
    Razorpay webhook endpoint.
    No auth header — verified via HMAC-SHA256 signature.
    Always returns 200 to prevent Razorpay retries on our processing errors.
    """
    payload_bytes = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    db = get_db()
    svc = PaymentService(db)
    try:
        result = await svc.process_webhook(
            payload_bytes=payload_bytes,
            signature=signature,
            provider="razorpay",
        )
        return {"status": "ok", **result}
    except ValueError as e:
        # Invalid signature — return 400 (Razorpay will retry)
        log.warning("webhook rejected: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:  # noqa: BLE001
        log.exception("webhook processing error: %s", exc)
        return {"status": "error", "detail": "Internal error during webhook processing"}


@router.post("/refund/{payment_id}")
async def refund_payment(
    payment_id: str,
    body: RefundRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Issue a refund (platform admin or billing_admin only)."""
    if user.role not in ("platform_owner", "platform_admin", "billing_admin"):
        raise HTTPException(status_code=403, detail="Refunds require platform admin access")

    db = get_db()
    svc = PaymentService(db)
    try:
        result = await svc.refund_payment(
            payment_id=payment_id,
            amount_paise=body.amount_paise,
            reason=body.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/orders")
async def list_orders(
    limit: int = 50,
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    """List orders for the current org."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = PaymentService(db)
    orders = await svc.order_repo.list_for_org(user.org_id, limit=limit, skip=skip)
    return [_order_response(o) for o in orders]


@router.get("/payments")
async def list_payments(
    limit: int = 50,
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    """List payments for the current org."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = PaymentService(db)
    payments = await svc.payment_repo.list_for_org(user.org_id, limit=limit, skip=skip)
    return [_payment_response(p) for p in payments]


@router.get("/invoices")
async def list_invoices(
    limit: int = 50,
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
):
    """List invoices for the current org."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = PaymentService(db)
    invoices = await svc.invoice_repo.list_for_org(user.org_id, limit=limit, skip=skip)
    return [_invoice_response(i) for i in invoices]


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, user: CurrentUser = Depends(get_current_user)):
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    svc = PaymentService(db)
    invoice = await svc.invoice_repo.find_by_id(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    # Tenant isolation check
    if invoice.organization_id != user.org_id and not user.is_platform:
        raise HTTPException(status_code=403, detail="Access denied")
    return _invoice_response(invoice)


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------
def _order_response(o) -> dict:
    return {
        "id": o.id,
        "order_type": o.order_type,
        "description": o.description,
        "amount_paise": o.amount_paise,
        "amount_inr": o.amount_paise / 100,
        "status": o.status,
        "provider": o.provider,
        "provider_order_id": o.provider_order_id,
        "created_at": o.created_at.isoformat(),
    }


def _payment_response(p) -> dict:
    return {
        "id": p.id,
        "order_id": p.order_id,
        "amount_paise": p.amount_paise,
        "amount_inr": p.amount_paise / 100,
        "refunded_paise": p.refunded_paise,
        "status": p.status,
        "provider": p.provider,
        "provider_payment_id": p.provider_payment_id,
        "paid_at": p.paid_at.isoformat(),
        "created_at": p.created_at.isoformat(),
    }


def _invoice_response(i) -> dict:
    return {
        "id": i.id,
        "invoice_number": i.invoice_number,
        "description": i.description,
        "subtotal_paise": i.subtotal_paise,
        "tax_paise": i.tax_paise,
        "total_paise": i.total_paise,
        "total_inr": i.total_paise / 100,
        "currency": i.currency,
        "status": i.status,
        "org_name": i.org_name,
        "issued_at": i.issued_at.isoformat(),
        "created_at": i.created_at.isoformat(),
    }
