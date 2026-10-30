# Full Razorpay Payment Integration & Admin Manual Approval Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement automated Razorpay payment checkout with graceful error handling alongside a runtime-toggleable Admin Manual Approval mode (scannable UPI QR code, customer UTR submission, and admin approval/rejection queue).

**Architecture:** A singleton `system_settings` document manages runtime payment mode (`razorpay` vs `manual`) and Admin UPI credentials. A new `manual_subscription_requests` collection tracks customer UTR submissions. When in manual mode, customers see a scannable UPI QR code and submit their UTR; admins review and one-click activate the subscription from the admin dashboard (generating paid `Order`, `Payment`, and `Invoice` records). When in Razorpay mode, frontend dynamically loads Razorpay Checkout and calls payment verification upon completion.

**Tech Stack:** FastAPI, Motor (Async MongoDB), Pydantic v2, Next.js 14, Tailwind CSS, Lucide Icons, Razorpay JavaScript SDK.

**Spec:** `docs/superpowers/specs/2026-10-30-razorpay-and-manual-billing-design.md`

## Global Constraints
- Target areas: Backend API (`backend/api/v1/billing.py`, `backend/api/v1/admin.py`), Models & Repos (`backend/models/billing.py`, `backend/repositories/billing_repo.py`), Frontend (`frontend/lib/api.ts`, `frontend/lib/razorpay.ts`, `frontend/app/(dashboard)/billing/page.tsx`, `frontend/app/(dashboard)/admin/subscriptions/page.tsx`).
- In manual mode, `POST /api/v1/billing/orders/subscription` must reject automated order creation with HTTP 400.
- When calling Razorpay, any exception from the SDK must be caught and returned as HTTP 502 with a clear message instead of unhandled HTTP 500.
- Only one active `pending` manual request per organization at a time.
- All admin endpoints must be secured with `dependencies=[Depends(require_platform())]`.

## Review Focus
1. Input: Customer enters a UTR that already exists in an active/approved request. Expected: 400 Bad Request ("This Transaction ID / UTR has already been submitted").
2. Input: Organization with an already pending request attempts to submit another manual request. Expected: 400 Bad Request ("You already have a pending payment request under review").
3. Input: Customer submits Razorpay order creation while `payment_mode` is `"manual"`. Expected: 400 Bad Request ("Manual payment mode is active. Please pay via UPI.").
4. Condition: Razorpay SDK throws `BadRequestError` or `AuthenticationError` during order creation. Expected: 502 Bad Gateway with diagnostic error message, not 500.
5. Action: Admin approves manual request. Expected: Organization's subscription is activated for 30 days (or 365 days), and corresponding `Order`, `Payment`, and `Invoice` are recorded with `status: "paid"` and `provider: "manual_upi"`.

---

### Task 1: Backend Data Models and Repositories

**Files:**
- Modify: `backend/models/billing.py`
- Modify: `backend/repositories/billing_repo.py`
- Test: `backend/tests/test_manual_billing_repo.py`

**Interfaces:**
- Consumes: Base models and `BaseRepository` in `backend/repositories/base.py`
- Produces: `PlatformPaymentSettings`, `ManualSubscriptionRequest`, `PlatformBillingSettingsRepository`, `ManualSubscriptionRequestRepository`

- [ ] **Step 1: Write the failing repository unit test**

```python
# backend/tests/test_manual_billing_repo.py
import pytest
from backend.repositories.billing_repo import (
    PlatformBillingSettingsRepository,
    ManualSubscriptionRequestRepository,
)

@pytest.mark.asyncio
async def test_billing_settings_repo_defaults_and_update(mock_db):
    repo = PlatformBillingSettingsRepository(mock_db)
    settings = await repo.get()
    assert settings.payment_mode in ("manual", "razorpay")
    assert settings.admin_upi_id != ""

    updated = await repo.update(payment_mode="manual", admin_upi_id="test@upi", admin_payee_name="Test Payee")
    assert updated.payment_mode == "manual"
    assert updated.admin_upi_id == "test@upi"

@pytest.mark.asyncio
async def test_manual_subscription_request_lifecycle(mock_db):
    repo = ManualSubscriptionRequestRepository(mock_db)
    req = await repo.create(
        organization_id="org-1",
        user_id="user-1",
        user_email="user@org.com",
        org_name="Org One",
        plan_id="plan-1",
        plan_slug="starter",
        plan_name="Starter",
        billing_cycle="monthly",
        amount_paise=99900,
        utr_number="UTR1234567890",
        payer_note="Paid via GPay",
    )
    assert req.status == "pending"
    assert req.utr_number == "UTR1234567890"

    # Pending lookup
    pending = await repo.find_pending_for_org("org-1")
    assert pending is not None
    assert pending.id == req.id

    # UTR duplicate lookup
    existing_utr = await repo.find_by_utr("UTR1234567890")
    assert existing_utr is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest backend/tests/test_manual_billing_repo.py -v`
Expected: FAIL with missing classes/imports

- [ ] **Step 3: Implement models and repositories**

In `backend/models/billing.py`:
- Define `PlatformPaymentSettings(BaseModel)` with fields `_id: str = "billing_settings"`, `payment_mode: str = "manual"`, `admin_upi_id: str = "nivcall@icici"`, `admin_payee_name: str = "NivCall Connect"`, `updated_at: str`, `updated_by: Optional[str] = None`.
- Define `ManualSubscriptionRequest(BaseModel)` with fields `id: str`, `organization_id: str`, `user_id: str`, `user_email: str`, `org_name: str`, `plan_id: str`, `plan_slug: str`, `plan_name: str`, `billing_cycle: str`, `amount_paise: int`, `currency: str = "INR"`, `utr_number: str`, `payer_note: Optional[str] = None`, `status: str = "pending"`, `rejection_reason: Optional[str] = None`, `created_at: str`, `updated_at: str`, `reviewed_by: Optional[str] = None`, `reviewed_at: Optional[str] = None`.

In `backend/repositories/billing_repo.py`:
- Implement `PlatformBillingSettingsRepository`:
  - `get() -> PlatformPaymentSettings`: finds doc with `_id: "billing_settings"`, or seeds default if missing.
  - `update(payment_mode, admin_upi_id, admin_payee_name, updated_by) -> PlatformPaymentSettings`.
- Implement `ManualSubscriptionRequestRepository`:
  - `create(...) -> ManualSubscriptionRequest`
  - `find_by_id(id: str) -> Optional[ManualSubscriptionRequest]`
  - `find_pending_for_org(org_id: str) -> Optional[ManualSubscriptionRequest]`
  - `find_by_utr(utr: str) -> Optional[ManualSubscriptionRequest]`
  - `list_for_org(org_id: str, limit: int = 10) -> list[ManualSubscriptionRequest]`
  - `list_all(status: Optional[str] = None, limit: int = 50, skip: int = 0) -> list[ManualSubscriptionRequest]`
  - `set_status(id: str, status: str, reviewed_by: Optional[str] = None, rejection_reason: Optional[str] = None) -> bool`

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest backend/tests/test_manual_billing_repo.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/models/billing.py backend/repositories/billing_repo.py backend/tests/test_manual_billing_repo.py
git commit -m "feat(billing): add PlatformPaymentSettings and ManualSubscriptionRequest models and repositories"
```

---

### Task 2: Backend API Endpoints (Customer & Admin)

**Files:**
- Modify: `backend/api/v1/billing.py`
- Modify: `backend/api/v1/admin.py`
- Test: `backend/tests/test_manual_billing_api.py`

**Interfaces:**
- Consumes: `PlatformBillingSettingsRepository`, `ManualSubscriptionRequestRepository`, `SubscriptionService`, `OrganizationRepository`
- Produces:
  - `GET /api/v1/billing/settings`
  - `POST /api/v1/billing/manual-request`
  - `GET /api/v1/billing/my-manual-requests`
  - `POST /api/v1/billing/manual-request/{request_id}/cancel`
  - `GET /api/v1/admin/billing/settings`
  - `PUT /api/v1/admin/billing/settings`
  - `GET /api/v1/admin/billing/manual-requests`
  - `POST /api/v1/admin/billing/manual-requests/{id}/approve`
  - `POST /api/v1/admin/billing/manual-requests/{id}/reject`
  - Enhanced error handling on `POST /api/v1/billing/orders/subscription`

- [ ] **Step 1: Write failing API tests**

```python
# backend/tests/test_manual_billing_api.py
import pytest

@pytest.mark.asyncio
async def test_manual_billing_flow(client, user_token, admin_token, sample_plan):
    auth_header = {"Authorization": f"Bearer {user_token}"}
    admin_header = {"Authorization": f"Bearer {admin_token}"}

    # 1. Admin sets mode to manual
    put_res = await client.put("/api/v1/admin/billing/settings", json={
        "payment_mode": "manual",
        "admin_upi_id": "test@upi",
        "admin_payee_name": "NivCall Test"
    }, headers=admin_header)
    assert put_res.status_code == 200

    # 2. Public settings reflects manual
    settings_res = await client.get("/api/v1/billing/settings")
    assert settings_res.status_code == 200
    assert settings_res.json()["payment_mode"] == "manual"

    # 3. Automated razorpay order creation is blocked in manual mode
    order_fail = await client.post("/api/v1/billing/orders/subscription", json={
        "plan_id": sample_plan.id,
        "billing_cycle": "monthly"
    }, headers=auth_header)
    assert order_fail.status_code == 400

    # 4. Customer submits manual request
    req_res = await client.post("/api/v1/billing/manual-request", json={
        "plan_id": sample_plan.id,
        "billing_cycle": "monthly",
        "utr_number": "UTR9988776655",
        "payer_note": "GPay paid"
    }, headers=auth_header)
    assert req_res.status_code == 200
    req_id = req_res.json()["id"]

    # 5. Duplicate submission blocked
    dup_res = await client.post("/api/v1/billing/manual-request", json={
        "plan_id": sample_plan.id,
        "billing_cycle": "monthly",
        "utr_number": "UTR9988776655",
    }, headers=auth_header)
    assert dup_res.status_code == 400

    # 6. Admin approves request
    appr_res = await client.post(f"/api/v1/admin/billing/manual-requests/{req_id}/approve", headers=admin_header)
    assert appr_res.status_code == 200

    # 7. Org now has active subscription
    sub_res = await client.get("/api/v1/subscriptions/my", headers=auth_header)
    assert sub_res.status_code == 200
    assert sub_res.json()["plan_slug"] == sample_plan.slug
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest backend/tests/test_manual_billing_api.py -v`
Expected: FAIL with 404 Not Found on endpoints

- [ ] **Step 3: Implement API endpoints**

In `backend/api/v1/billing.py`:
- Add `GET /billing/settings`: returns public settings.
- Add `POST /billing/manual-request`: validates request body, checks for pending request on org, checks UTR uniqueness, fetches plan & org details, inserts into repository.
- Add `GET /billing/my-manual-requests`: returns recent manual requests for current org.
- Add `POST /billing/manual-request/{request_id}/cancel`: verifies ownership and cancels pending request.
- Update `create_subscription_order`:
  - Check `payment_mode`: if `"manual"`, raise `HTTPException(400, "Manual payment mode is active. Please pay via UPI.")`.
  - Wrap `svc.create_subscription_order` in `try/except Exception as e`:
    ```python
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.exception("Payment gateway order creation failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Payment gateway error: {str(e)}")
    ```

In `backend/api/v1/admin.py`:
- Add `GET /admin/billing/settings` (admin only).
- Add `PUT /admin/billing/settings` (admin only).
- Add `GET /admin/billing/manual-requests` (admin only).
- Add `POST /admin/billing/manual-requests/{id}/approve` (admin only):
  - Fetches manual request. Verifies status is `pending`.
  - Calls `SubscriptionService.activate_plan(req.organization_id, req.plan_id, req.billing_cycle)`.
  - Creates an `Order` and `Payment` marked as `paid`, `manual_upi`.
  - Creates an `Invoice` marked as `paid`.
  - Sets request status to `approved`.
- Add `POST /admin/billing/manual-requests/{id}/reject` (admin only):
  - Sets request status to `rejected` with `rejection_reason`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest backend/tests/test_manual_billing_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/api/v1/billing.py backend/api/v1/admin.py backend/tests/test_manual_billing_api.py
git commit -m "feat(billing): add public & admin manual billing endpoints and enhance Razorpay error handling"
```

---

### Task 3: Frontend API Client and Razorpay Helper

**Files:**
- Create: `frontend/lib/razorpay.ts`
- Modify: `frontend/lib/api.ts`

**Interfaces:**
- Consumes: Backend endpoints from Task 2
- Produces: `api.billing.getSettings`, `api.billing.submitManualRequest`, `api.billing.getMyManualRequests`, `api.billing.cancelManualRequest`, `api.admin.billing.*`, `initiateRazorpayPayment()`

- [ ] **Step 1: Add types and methods in `frontend/lib/api.ts`**

Add TypeScript types:
```typescript
export interface BillingSettings {
  payment_mode: "razorpay" | "manual";
  admin_upi_id: string;
  admin_payee_name: string;
  razorpay_key_id?: string;
}

export interface ManualSubscriptionRequest {
  id: string;
  organization_id: string;
  org_name: string;
  user_email: string;
  plan_id: string;
  plan_slug: string;
  plan_name: string;
  billing_cycle: "monthly" | "yearly";
  amount_paise: number;
  utr_number: string;
  payer_note?: string;
  status: "pending" | "approved" | "rejected" | "cancelled";
  rejection_reason?: string;
  created_at: string;
}
```

Add endpoints under `api.billing`:
- `getSettings: () => apiRequest<BillingSettings>("GET", "/api/v1/billing/settings")`
- `submitManualRequest: (body: { plan_id: string; billing_cycle: string; utr_number: string; payer_note?: string }) => apiRequest<ManualSubscriptionRequest>("POST", "/api/v1/billing/manual-request", body)`
- `getMyManualRequests: () => apiRequest<ManualSubscriptionRequest[]>("GET", "/api/v1/billing/my-manual-requests")`
- `cancelManualRequest: (requestId: string) => apiRequest<{ ok: boolean }>("POST", `/api/v1/billing/manual-request/${requestId}/cancel`)`

Add admin endpoints under `api.admin.billing`:
- `getSettings: () => apiRequest<BillingSettings>("GET", "/api/v1/admin/billing/settings")`
- `updateSettings: (body: Partial<BillingSettings>) => apiRequest<BillingSettings>("PUT", "/api/v1/admin/billing/settings", body)`
- `getManualRequests: (status?: string) => apiRequest<ManualSubscriptionRequest[]>("GET", `/api/v1/admin/billing/manual-requests${status ? `?status=${status}` : ""}`)`
- `approveManualRequest: (id: string) => apiRequest<{ ok: boolean }>("POST", `/api/v1/admin/billing/manual-requests/${id}/approve`)`
- `rejectManualRequest: (id: string, reason: string) => apiRequest<{ ok: boolean }>("POST", `/api/v1/admin/billing/manual-requests/${id}/reject`, { reason })`

- [ ] **Step 2: Create `frontend/lib/razorpay.ts`**

Implement helper to dynamically load script and trigger checkout:
```typescript
export function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (typeof window === "undefined") return resolve(false);
    if ((window as unknown as { Razorpay?: unknown }).Razorpay) return resolve(true);
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export interface RazorpayOptions {
  key: string;
  amount: number;
  currency: string;
  name: string;
  description: string;
  order_id: string;
  prefill?: { email?: string; contact?: string };
  handler: (response: {
    razorpay_payment_id: string;
    razorpay_order_id: string;
    razorpay_signature: string;
  }) => void;
  modal?: { ondismiss?: () => void };
}

export function openRazorpayModal(options: RazorpayOptions): void {
  const RazorpayConstructor = (window as unknown as { Razorpay: new (opts: RazorpayOptions) => { open: () => void } }).Razorpay;
  if (!RazorpayConstructor) {
    throw new Error("Razorpay SDK not loaded");
  }
  const rzp = new RazorpayConstructor(options);
  rzp.open();
}
```

- [ ] **Step 3: Verify build / typecheck**

Run: `cd frontend && npm run build` (or `npx tsc --noEmit`)
Expected: No type errors in `frontend/lib/`

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/razorpay.ts
git commit -m "feat(frontend): add billing API client methods and Razorpay checkout helper"
```

---

### Task 4: Frontend Customer Billing Page Integration

**Files:**
- Modify: `frontend/app/(dashboard)/billing/page.tsx`

**Interfaces:**
- Consumes: `api.billing.*`, `loadRazorpayScript`, `openRazorpayModal`
- Produces: Dynamic subscription handling (Manual UPI QR Modal vs Razorpay Checkout), Pending Request Banner, Rejection Banner.

- [ ] **Step 1: Implement state and banners in `billing/page.tsx`**

- Fetch `api.billing.getSettings()` and `api.billing.getMyManualRequests()` on load.
- If a manual request with `status === "pending"` exists:
  - Display alert banner at the top of Billing page:
    *"Payment Verification Pending for {plan_name} (UTR: {utr_number}). Our team is verifying your payment."*
    Include button to *"Cancel Request"* via `api.billing.cancelManualRequest`.
- If latest request has `status === "rejected"`:
  - Display warning banner: *"Your payment request was rejected: {rejection_reason}. Please try again or contact support."*

- [ ] **Step 2: Implement Plan Selection Handler (Razorpay vs Manual Mode)**

- When user clicks "Select Plan":
  - If `settings.payment_mode === "manual"`:
    - Open `ManualPaymentModal` displaying:
      - Plan name & price
      - Scannable QR code generated for `upi://pay?pa=${admin_upi_id}&pn=${encodeURIComponent(admin_payee_name)}&am=${amount_inr}&cu=INR&tn=${plan_name}%20Subscription`
      - Display Admin UPI ID with a "Copy" button
      - Text input for 12-digit UTR Number (mandatory)
      - Text input for Note / Payer Name (optional)
      - "Submit for Verification" button calling `api.billing.submitManualRequest`
  - If `settings.payment_mode === "razorpay"`:
    - Load Razorpay script via `loadRazorpayScript()`.
    - Create order via `api.billing.createSubscriptionOrder(planId, "monthly")`.
    - Open Razorpay checkout modal via `openRazorpayModal`.
    - In `handler(res)`, call `api.billing.verifyPayment({ order_id: order.order_id, provider_payment_id: res.razorpay_payment_id, provider_order_id: res.razorpay_order_id, provider_signature: res.razorpay_signature })`.
    - On success: toast `"Subscription activated!"`, reload billing data.

- [ ] **Step 3: Test and verify frontend build**

Run: `cd frontend && npm run build`
Expected: Build passes with 0 errors

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(dashboard\)/billing/page.tsx
git commit -m "feat(billing): integrate manual UPI QR payment modal and Razorpay checkout in customer billing page"
```

---

### Task 5: Frontend Admin Dashboard Mode Toggle & Approval Queue

**Files:**
- Modify: `frontend/app/(dashboard)/admin/subscriptions/page.tsx`

**Interfaces:**
- Consumes: `api.admin.billing.*`
- Produces: Platform Payment Settings card (Toggle & UPI configuration) and Manual Payment Requests table (Approve & Reject).

- [ ] **Step 1: Add Payment Gateway Settings Card in Admin Subscriptions**

- Display a settings section with:
  - Mode toggle: **Automated Razorpay** vs **Manual UPI Approval**.
  - Inputs for:
    - Admin UPI ID (e.g. `nivcall@icici`)
    - Admin Payee Name (e.g. `NivCall Connect`)
  - "Save Payment Settings" button calling `api.admin.billing.updateSettings`.

- [ ] **Step 2: Add Manual Payment Requests Table**

- Fetch `api.admin.billing.getManualRequests()` on load.
- Display table of requests with columns:
  - Organization & User Email
  - Plan Requested & Billing Cycle
  - Amount
  - UTR Number & Notes
  - Date Submitted
  - Status Badge (`Pending`, `Approved`, `Rejected`)
  - Actions:
    - `✓ Approve & Activate` button (calls `api.admin.billing.approveManualRequest`, toasts success, refreshes table).
    - `✕ Reject` button (prompts for reason, calls `api.admin.billing.rejectManualRequest`, toasts success, refreshes table).

- [ ] **Step 3: Run full build and lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: Zero build or lint errors

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(dashboard\)/admin/subscriptions/page.tsx
git commit -m "feat(admin): add payment gateway mode toggle and manual subscription approval queue in admin dashboard"
```

---

### Task 6: End-to-End Verification & Graphify Update

**Files:**
- All modified files

- [ ] **Step 1: Run complete backend test suite**

Run: `.venv/Scripts/pytest backend/tests/test_manual_billing_repo.py backend/tests/test_manual_billing_api.py -v`
Expected: All tests PASS

- [ ] **Step 2: Run frontend build verification**

Run: `cd frontend && npm run build`
Expected: Clean build output

- [ ] **Step 3: Update knowledge graph**

Run: `graphify update .`
Expected: Graph updated

- [ ] **Step 4: Final commit**

```bash
git commit -m "chore: complete Razorpay integration and manual admin subscription approval workflow"
```
