# Design Document: Full Razorpay Integration & Admin Manual Approval Mode for Subscriptions

**Date:** 2026-10-30  
**Status:** In Review  
**Target Areas:** Backend API (`billing`, `admin`, `subscriptions`), Database (`system_settings`, `manual_payment_requests`, `orders`), Frontend (`/billing`, `/admin/subscriptions`)

---

## 1. Intent and Why
Currently, customer subscription attempts fail with HTTP 500 when creating orders because Razorpay credentials on the production server are invalid or unconfigured, and Razorpay exceptions bubble up unhandled. Furthermore, the frontend billing page lacks the Razorpay Checkout popup and payment verification callback.

Additionally, while awaiting merchant account approvals or KYC verification from Razorpay, the platform needs a built-in **Manual Approval Mode**. In this mode, customers can pay directly to the platform owner via UPI QR code, submit their Transaction ID (UTR), and the platform admin can verify the payment in their admin dashboard and manually approve & activate the subscription.

An admin toggle enables seamless switching between **Automated Razorpay Mode** and **Manual Approval Mode**.

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
1. **Full Razorpay Flow:**
   - Handle Razorpay order creation gracefully on backend; return clear errors (e.g. 502/400) if gateway calls fail instead of 500.
   - Frontend dynamically loads Razorpay SDK (`https://checkout.razorpay.com/v1/checkout.js`).
   - Open standard Razorpay popup for payments; upon success, call `/api/v1/billing/verify` to activate the subscription immediately.
2. **Admin Mode Toggle:**
   - Allow platform admins to toggle between `razorpay` and `manual` mode at runtime without restarting the server.
   - Allow platform admins to set their Admin UPI ID (e.g. `nivcall@icici`), Payee Name, and optional bank notes.
3. **Customer Manual UPI Flow:**
   - In manual mode, clicking "Select Plan" displays a modal with plan amount, scannable UPI QR code (standard `upi://pay` URI), UPI ID, and copy button.
   - Customer submits their 12-digit UPI / UTR Transaction ID and optional note.
   - Pending request lives in `manual_subscription_requests` collection.
   - Customer billing page clearly reflects "Pending Admin Verification" with details of their pending request, with an option to cancel their request if they entered incorrect details.
4. **Admin Approval Queue:**
   - Platform admin dashboard displays a table of pending manual subscription requests with customer organization, email, plan, amount, timestamp, and UTR number.
   - Admin can click `Approve & Activate` to immediately activate the organization's subscription, create invoice & payment records, and update request status to `approved`.
   - Admin can click `Reject` with a reason (updating request status to `rejected`).

### Non-Goals
- Automated bank account reconciliation via Netbanking screen scraping (all manual verification is done visually by the admin using their UPI/bank app).
- Complex refund flows for manual UPI (handled offline if rejected).

### Anti-Goals
- Do not break existing API contracts for `POST /api/v1/billing/orders/subscription` or `POST /api/v1/billing/verify`.
- Do not bypass organization permission checks (`organization_owner`/`organization_admin`).

---

## 3. Architecture & Data Model

### A. System Settings (`system_settings` collection)
Stores global platform payment settings:
```typescript
interface PlatformPaymentSettings {
  _id: "billing_settings";
  payment_mode: "razorpay" | "manual"; // Default "manual" if razorpay not fully configured
  admin_upi_id: string;               // e.g. "nivcall@icici"
  admin_payee_name: string;           // e.g. "NivCall Connect"
  updated_at: string;
  updated_by?: string;
}
```

### B. Manual Payment Request (`manual_subscription_requests` collection)
Stores customer manual payment submissions:
```typescript
interface ManualSubscriptionRequest {
  id: string;                         // UUID
  organization_id: string;
  user_id: string;
  user_email: string;
  org_name: string;
  plan_id: string;
  plan_slug: string;
  plan_name: string;
  billing_cycle: "monthly" | "yearly";
  amount_paise: number;
  currency: "INR";
  utr_number: string;                 // Transaction ID submitted by user
  payer_note?: string;
  status: "pending" | "approved" | "rejected" | "cancelled";
  rejection_reason?: string;
  created_at: string;
  updated_at: string;
  reviewed_by?: string;
  reviewed_at?: string;
}
```

---

## 4. API Specification

### Customer / Public Endpoints
1. `GET /api/v1/billing/settings`
   - Returns public payment configuration:
     ```json
     {
       "payment_mode": "manual", // or "razorpay"
       "admin_upi_id": "nivcall@icici",
       "admin_payee_name": "NivCall Connect",
       "razorpay_key_id": "rzp_..." // if in razorpay mode
     }
     ```
2. `POST /api/v1/billing/manual-request`
   - Request body:
     ```json
     {
       "plan_id": "string",
       "billing_cycle": "monthly",
       "utr_number": "string",
       "payer_note": "optional string"
     }
     ```
   - Validates user is org owner/admin.
   - Checks if organization already has an active pending request (rejects with 400 if already pending).
   - Validates that `utr_number` has not already been used in an active/approved request.
   - Creates document in `manual_subscription_requests` with `status: "pending"`.
   - Returns the created request object.

3. `POST /api/v1/billing/manual-request/{request_id}/cancel`
   - Allows customer to cancel their pending request (e.g. if they mistyped UTR or want to pick a different plan).

4. `GET /api/v1/billing/my-manual-requests`
   - Returns recent manual payment requests for the user's organization (latest first).

5. `POST /api/v1/billing/orders/subscription` (Enhanced)
   - *Builder decision:* Backend enforcement: If `payment_mode === "manual"`, reject with 400 Bad Request ("Manual payment mode is active. Please submit payment via UPI.").
   - When in Razorpay mode, wrap `RazorpayProvider.create_order` in `try/except Exception` and return clean `502 Bad Gateway` with description if Razorpay throws an API error, instead of crashing with 500.

### Platform Admin Endpoints (`dependencies=[Depends(require_platform())]`)
1. `GET /api/v1/admin/billing/settings`
   - Returns full billing settings.
2. `PUT /api/v1/admin/billing/settings`
   - Updates `payment_mode`, `admin_upi_id`, `admin_payee_name`.
3. `GET /api/v1/admin/billing/manual-requests`
   - Query params: `status` (optional: `pending`, `approved`, `rejected`), `limit`, `skip`.
   - Returns list of manual requests with pagination.
4. `POST /api/v1/admin/billing/manual-requests/{request_id}/approve`
   - *Builder decision on lifecycle:* Creates `Order` and `Payment` records at approval time marked `paid` via `manual_upi`, generates a paid `Invoice`, and calls `SubscriptionService.activate_plan(org_id, plan_id, billing_cycle)`. Subscription starts from approval date for 30 days (monthly) or 365 days (yearly).
   - Sets request status to `approved`, stamps `reviewed_by` and `reviewed_at`.
   - Returns activated subscription.
5. `POST /api/v1/admin/billing/manual-requests/{request_id}/reject`
   - Body: `{ "reason": "string" }`
   - Marks request as `rejected` with `rejection_reason`.

---

## 5. Frontend Implementation

### 1. Customer Billing Page (`frontend/app/(dashboard)/billing/page.tsx`)
- On load, fetch `api.billing.getSettings()` and `api.billing.getMyManualRequests()`.
- If an active request is `pending`:
  - Display an amber banner: *"You have a pending subscription verification for [Plan Name] (UTR: [UTR]). Our team is verifying your payment."* Includes a *"Cancel Request"* link.
- If the latest request was `rejected`:
  - Display a red alert banner: *"Your payment verification for [Plan Name] was rejected: [Reason]. You can re-submit your payment or contact support."* with a dismiss button.
- When user clicks "Choose a Plan" / "Select Plan":
  - **If `payment_mode === "manual"`:**
    - Open the UPI QR Modal (as previewed in mockup).
    - Render QR code for URI: `upi://pay?pa={admin_upi_id}&pn={encodeURIComponent(payee_name)}&am={amount_inr}&cu=INR&tn={plan_name}%20Subscription`.
    - Provide copy button for UPI ID.
    - User inputs UTR and optional note, submits form.
    - Toast success *"Payment details submitted. Your subscription will be activated upon admin verification."*
  - **If `payment_mode === "razorpay"`:**
    - Dynamically load `https://checkout.razorpay.com/v1/checkout.js`.
    - Create order via `api.billing.createSubscriptionOrder(planId, "monthly")`.
    - Open `new window.Razorpay(options).open()`.
    - In `handler(response)`, call `api.billing.verifyPayment({ order_id, provider_payment_id, provider_order_id, provider_signature })`.
    - On verification, reload billing data and toast success.

### 2. Admin Billing & Subscriptions (`frontend/app/(dashboard)/admin/subscriptions/page.tsx` or new tab)
- Add **Payment Gateway Settings card**:
  - Switch toggle between **Razorpay Auto** and **Manual Approval**.
  - Input fields for **UPI ID** and **Payee Name** with "Save Settings" button.
- Add **Manual Subscription Verification Queue**:
  - Shows table of pending requests with Badge: Organization, Plan, Amount, UTR, Date, Note.
  - Action buttons:
    - `✓ Approve & Activate`: opens confirmation modal or triggers one-click activation.
    - `✕ Reject`: opens prompt for reason, then rejects.

---

## 6. Settled Builder Decisions
1. **Order Record Lifecycle:** `Order` and `Payment` documents are created in the database upon **Admin Approval**, marked as `manual_upi` and `paid`. During submission, the record lives strictly in `manual_subscription_requests` to avoid polluting the orders table with rejected/abandoned attempts.
2. **Subscription Timing:** When an admin approves, the subscription period starts from the date/time of approval for a full 30 days (monthly) or 365 days (yearly).
3. **Resubmission & Concurrency:** Only one `pending` request is permitted per organization at a time. The customer can cancel their pending request if they entered the wrong UTR. UTR numbers must be unique across all active/approved requests to prevent duplicate submissions.
4. **Backend Enforcement:** When `payment_mode` is `"manual"`, automated Razorpay order generation returns 400 Bad Request to prevent inconsistent states.
5. **Rejection UX:** If rejected, a dismissible alert shows the rejection reason so the customer can correct the payment or re-submit cleanly.
