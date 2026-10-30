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

from backend.config import settings
from backend.core.auth import CurrentUser, get_current_user
from backend.core.db import get_db
from backend.services.payment_service import PaymentService

log = logging.getLogger("api.billing")
router = APIRouter(prefix="/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class CreateManualRequestSchema(BaseModel):
    plan_id: str
    billing_cycle: str = "monthly"
    utr_number: str
    payer_note: Optional[str] = None

    @field_validator("billing_cycle")
    @classmethod
    def valid_cycle(cls, v: str) -> str:
        if v not in ("monthly", "yearly"):
            raise ValueError("billing_cycle must be 'monthly' or 'yearly'")
        return v

    @field_validator("utr_number")
    @classmethod
    def valid_utr(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("utr_number cannot be empty")
        return v


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
@router.get("/settings")
async def get_public_billing_settings():
    """Return public billing mode and payment parameters."""
    db = get_db()
    from backend.repositories.billing_repo import PlatformBillingSettingsRepository
    repo = PlatformBillingSettingsRepository(db)
    settings_doc = await repo.get()
    return {
        "payment_mode": settings_doc.payment_mode,
        "admin_upi_id": settings_doc.admin_upi_id,
        "admin_payee_name": settings_doc.admin_payee_name,
        "razorpay_key_id": settings.razorpay_key_id if not settings.demo_mode else "rzp_test_mock",
    }


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
    from backend.repositories.billing_repo import PlatformBillingSettingsRepository
    settings_repo = PlatformBillingSettingsRepository(db)
    settings_doc = await settings_repo.get()
    if settings_doc.payment_mode == "manual":
        raise HTTPException(status_code=400, detail="Manual payment mode is active. Please pay via UPI.")

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
    except Exception as e:
        log.exception("Payment gateway order creation failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Payment gateway error: {str(e)}")
    return result


@router.post("/manual-request")
async def submit_manual_subscription_request(
    body: CreateManualRequestSchema,
    user: CurrentUser = Depends(get_current_user),
):
    """Submit a manual payment (UPI UTR) for admin verification."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    if user.role not in ("organization_owner", "organization_admin") and not user.is_platform:
        raise HTTPException(status_code=403, detail="Only org owners/admins can submit subscription requests")

    db = get_db()
    from backend.repositories.billing_repo import ManualSubscriptionRequestRepository
    from backend.repositories.subscription_repo import SubscriptionPlanRepository
    from backend.repositories.organization_repo import OrganizationRepository

    req_repo = ManualSubscriptionRequestRepository(db)
    plan_repo = SubscriptionPlanRepository(db)
    org_repo = OrganizationRepository(db)

    # Check for active pending request
    existing_pending = await req_repo.find_pending_for_org(user.org_id)
    if existing_pending:
        raise HTTPException(status_code=400, detail="You already have a pending payment request under review")

    # Check for duplicate UTR
    existing_utr = await req_repo.find_by_utr(body.utr_number)
    if existing_utr:
        raise HTTPException(status_code=400, detail="This Transaction ID / UTR has already been submitted")

    # Fetch plan
    plan = await plan_repo.find_by_id(body.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=400, detail="Selected plan is not available")

    # Fetch org
    org = await org_repo.find_by_id(user.org_id)
    org_name = org.name if org else "Unknown Organization"

    amount_paise = plan.price_yearly_paise if body.billing_cycle == "yearly" else plan.price_monthly_paise

    req_doc = await req_repo.create(
        organization_id=user.org_id,
        user_id=user.user_id,
        user_email=user.email,
        org_name=org_name,
        plan_id=plan.id,
        plan_slug=plan.slug,
        plan_name=plan.name,
        amount_paise=amount_paise,
        utr_number=body.utr_number,
        billing_cycle=body.billing_cycle,
        payer_note=body.payer_note,
    )
    return _manual_request_response(req_doc)


@router.get("/my-manual-requests")
async def get_my_manual_requests(
    user: CurrentUser = Depends(get_current_user),
):
    """List manual subscription requests for current user organization."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    from backend.repositories.billing_repo import ManualSubscriptionRequestRepository
    req_repo = ManualSubscriptionRequestRepository(db)
    requests = await req_repo.list_for_org(user.org_id, limit=20)
    return [_manual_request_response(r) for r in requests]


@router.post("/manual-request/{request_id}/cancel")
async def cancel_manual_request(
    request_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Cancel a pending manual subscription request."""
    if not user.org_id:
        raise HTTPException(status_code=400, detail="No organization")
    db = get_db()
    from backend.repositories.billing_repo import ManualSubscriptionRequestRepository
    req_repo = ManualSubscriptionRequestRepository(db)
    req = await req_repo.find_by_id(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.organization_id != user.org_id and not user.is_platform:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this request")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be cancelled")

    await req_repo.set_status(request_id, "cancelled")
    return {"ok": True, "status": "cancelled"}


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
        return []
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
        return []
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
        "paid_at": p.paid_at.isoformat() if hasattr(p.paid_at, "isoformat") else str(p.paid_at) if p.paid_at else None,
        "created_at": p.created_at.isoformat() if hasattr(p.created_at, "isoformat") else str(p.created_at) if p.created_at else None,
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
        "issued_at": i.issued_at.isoformat() if hasattr(i.issued_at, "isoformat") else str(i.issued_at) if i.issued_at else None,
        "created_at": i.created_at.isoformat() if hasattr(i.created_at, "isoformat") else str(i.created_at) if i.created_at else None,
    }


def _manual_request_response(r) -> dict:
    return {
        "id": r.id,
        "organization_id": r.organization_id,
        "org_name": r.org_name,
        "user_email": r.user_email,
        "plan_id": r.plan_id,
        "plan_slug": r.plan_slug,
        "plan_name": r.plan_name,
        "billing_cycle": r.billing_cycle,
        "amount_paise": r.amount_paise,
        "amount_inr": r.amount_paise / 100,
        "currency": r.currency,
        "utr_number": r.utr_number,
        "payer_note": r.payer_note,
        "status": r.status,
        "rejection_reason": r.rejection_reason,
        "reviewed_by": r.reviewed_by,
        "reviewed_at": r.reviewed_at.isoformat() if hasattr(r.reviewed_at, "isoformat") else str(r.reviewed_at) if r.reviewed_at else None,
        "created_at": r.created_at.isoformat() if hasattr(r.created_at, "isoformat") else str(r.created_at) if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if hasattr(r.updated_at, "isoformat") else str(r.updated_at) if r.updated_at else None,
    }

