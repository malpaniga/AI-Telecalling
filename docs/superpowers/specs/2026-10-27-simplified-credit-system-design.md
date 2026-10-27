# Simplified Credit System & In-Browser Test Free Trial Design

**Date:** 2026-10-27  
**Status:** Approved Specification  
**Target Platform:** SaaS Core (Backend FastAPI/MongoDB/Redis + Frontend Next.js/Tailwind)

---

## 1. Intent & Problem Statement

### 1.1 The Problem
The existing credit system is difficult for both customers and administrators to understand:
1. **Opaque unit:** Under the hood, `1 credit = 1 billable second`, but this is never made explicit in the UI. Customers purchasing a "1,000 credit pack" do not easily understand how much talk time that buys (~16.6 minutes), nor why a 45-second call deducted 45 credits.
2. **Excessive holds:** Every call currently places a `300-credit` (5-minute) security hold. If an organization has 250 credits remaining, calls are blocked with an "insufficient credits" error, even if the user only wanted to make a quick test call.
3. **Confusing ledger:** Because reservation and release operations do not change the total sum of the wallet, they are logged in the transaction table with `credits_delta: 0`. Customers see rows showing `reserve: 0 credits` and `release: 0 credits`, giving the appearance of a broken or deceptive system.
4. **Unclear test costs:** In-browser agent testing and real phone testing lacked distinct, transparent billing boundaries.

### 1.2 The Solution
Transition the entire platform to a **minute-based credit currency**:
- **1 Credit = 1 Minute of Call Time** (ceiling rounded: any call from 1s to 60s is 1 credit; 61s to 120s is 2 credits; 0s / unanswered is 0 credits).
- **Minimum 5 Credits to Initiate Calls:** All phone calls (campaigns or real phone tests) strictly require at least 5 available credits to start, placing a 5-credit (5-minute) initial security hold.
- **Auto-Extension:** At 4:45 into a live phone call, if the call will exceed 5 minutes and the organization has available credits, the hold is seamlessly extended by another 5 credits. If available balance is 0, the call gracefully wraps up at 5:00.
- **Configurable Maximum Call Duration:** Default 7 minutes per call, configurable by organizations in organization settings.
- **10 Free In-Browser Voice Test Sessions:** Each organization receives 10 free browser voice test calls capped at exactly 3 minutes each with an automatic wrap-up and notification. Once 10 free tests are used, browser voice tests transition to standard billing.
- **Text Chat Testing is Free & Unmetered:** The in-browser text Chat tab in the test agent remains completely free and unmetered for prompt tuning.
- **Phone Tab Testing Uses Standard Credits:** Placing test calls to real phone numbers draws from the organization's standard credit balance at 1 credit/minute with the standard 5-credit hold.
- **Admin Management:** Platform admins can grant credits (minutes) and grant additional free browser test sessions.
- **Human-Readable Ledger:** Itemized history with duration, hold lifecycle, cost, and balance after.

---

## 2. Goals, Non-Goals, and Anti-Goals

### 2.1 Goals
- Establish `1 Credit = 1 Minute` as the single universal currency across backend schemas, pricing cards, and frontend UI.
- Implement standard telecom ceiling-rounding (`math.ceil(duration_seconds / 60)`).
- Ensure failed or unconnected calls (0 seconds connected) cost 0 credits and immediately release any hold.
- Enforce strict 5-credit minimum requirement to initiate any phone call.
- Provide a seamless 5-minute rolling hold extension mechanism for calls that run longer than 5 minutes.
- Enforce organization-level maximum call duration (default 7 minutes, customizable in organization settings).
- Implement a 10-session free trial quota for in-browser voice agent tests, with a strict 3-minute hard session limit and audible/visual cutoff alert.
- Keep in-browser text Chat testing completely free and unmetered.
- Redesign the customer wallet and transaction UI to display time-based metrics and itemized receipt entries.
- Provide admin actions to grant credits (minutes) and grant free browser test sessions.

### 2.2 Non-Goals
- Changing the underlying low-level audio streaming, VAD, STT, or TTS pipelines.
- Replacing external telephony providers (Vobiz/Twilio) or payment gateways (Razorpay).
- Adding complex sub-minute fractional billing tiers (e.g. 15-second blocks).

### 2.3 Anti-Goals
- Never allow a customer wallet to drop below zero available credits.
- Never abruptly terminate an active customer conversation mid-sentence if the organization has available credits to cover the extension.
- Never show cryptic `+0` or `0 Credits` entries in customer transaction ledgers without human-readable lifecycle context.

---

## 3. Detailed Architecture & Specifications

### 3.1 Currency & Accounting Rules
1. **Conversion:** `1 Credit = 1 Billable Minute` (60 seconds).
2. **Rounding:**
   - `duration_seconds == 0`: 0 credits billed (call failed, busy, or uncompleted).
   - `1 <= duration_seconds <= 60`: 1 credit.
   - `61 <= duration_seconds <= 120`: 2 credits.
   - Formula: `billed_credits = math.ceil(duration_seconds / 60) if duration_seconds > 0 else 0`.
3. **Packs & Pricing Alignment:**
   - **Trial Pack:** 10 credits (10 minutes free on signup / admin grant).
   - **Starter Pack:** 100 credits (100 mins) — ₹999.
   - **Growth Pack:** 500 credits (500 mins) + 50 bonus — ₹3,999.
   - **Pro Pack:** 1,000 credits (1,000 mins) + 150 bonus — ₹6,999.

### 3.2 Live Call Hold & Rolling Extension Lifecycle (Telephony & Phone Tests)
```
[Call Initiated (Campaign or Phone Tab Test)]
       │
       ▼
Check Wallet Balance
   ├── Available Credits < 5:
   │     └── REJECT: "Insufficient credits. Minimum 5 credits required to initiate a call."
   │
   └── Available Credits >= 5:
         └── Place temporary hold of 5 Credits (5 minutes). Call connects.
       │
       ▼
[Call In Progress]
   ├── Call ends at t <= 5:00:
   │     Bill: ceil(t / 60) credits.
   │     Release: (5 - billed) credits back to Available balance.
   │
   ├── Call reaches t = 4:45 (Extension Check):
   │     ├── Org Available Credits >= 5?
   │     │     └── Reserve additional 5 credits (Total hold = 10 mins).
   │     │         Call continues seamlessly.
   │     ├── 1 <= Org Available Credits < 5?
   │     │     └── Reserve remaining balance (e.g. 2 credits for 2 mins).
   │     │         Call extends until t = 7:00.
   │     └── Org Available Credits == 0?
   │           └── Schedule graceful disconnect at 5:00 sharp.
   │
   └── Call reaches Max Duration Cap (Default 7:00, or Org Setting):
         Wrap up and disconnect. Settle exact rounded minutes. Release remaining hold.
```

### 3.3 Free In-Browser Voice Test Sessions
1. **Quota:**
   - Stored on Organization: `free_test_sessions_remaining: int` (default `10` on org creation).
   - `free_test_session_max_seconds: int = 180` (3 minutes).
2. **In-Session Behavior:**
   - When user starts in-browser voice test and `free_test_sessions_remaining > 0`:
     - Decrements `free_test_sessions_remaining` by 1 upon session start.
     - 0 wallet credits held; 0 wallet credits deducted.
     - Displays live countdown: `02:45 / 03:00`.
   - At `02:45` (15s warning): Subtle warning badge: *"Session ending in 15 seconds"*.
   - At `03:00` (Cutoff):
     - Agent voice speaks: *"3-minute testing session ending now."*
     - WebSocket stream closes gracefully.
     - UI modal displays: *"3-minute testing session ending now. Call disconnected."*
3. **Transition to Standard Billing:**
   - When `free_test_sessions_remaining == 0`:
     - In-browser voice test modal displays: *"Free test sessions exhausted. Testing at standard rate: 1 credit / minute."*
     - Starting a paid in-browser test requires at least 5 available credits in wallet.
     - Follows standard rolling 5-minute hold and deduction up to organization max call duration.
     - If wallet has < 5 credits: Disables Start Call button with prompt: *"Minimum 5 credits required. Buy Calling Credits to continue testing"*.

### 3.4 In-Browser Text Chat Testing (Chat Tab)
- The **Chat** tab in Test Agent Modal is used for quick prompt and LLM tuning.
- **100% Free and Unmetered:** Does not decrement `free_test_sessions_remaining` and does not deduct wallet credits.
- Operates via the existing `/api/v1/model-directory/test-chat` REST endpoint without time limits or audio hangups.

### 3.5 Organization Settings Updates
In `backend/models/organization.py`:
- `max_call_duration_minutes: int = 7` (Allowed range: 1 to 60 minutes).
- `free_test_sessions_remaining: int = 10`.
- `free_test_session_max_minutes: int = 3`.

### 3.6 Admin Portal Enhancements
1. **Organization Details & Calling Packs View:**
   - Action 1: **"Assign Calling Credits"**: Adds `N` credits (minutes) to organization wallet.
   - Action 2: **"Grant Free Test Sessions"**: Adds `N` free 3-minute browser voice test sessions (e.g. +10 tests).
   - Action 3: **"Configure Max Call Duration"**: Sets max call minutes (default 7).
2. **Ledger Auditing:**
   - Admin can view itemized history with complete hold/settle traces.

### 3.7 Frontend Customer View Redesign
1. **Metrics Bar (`/credits`):**
   - **Available Balance:** e.g. `150 Mins (150 Credits)`
   - **Active Call Holds:** e.g. `5 Mins (5 Credits held)`
   - **Free Browser Tests:** e.g. `7 of 10 remaining`
2. **Transaction History Table:**
   - Columns: `Activity / Call`, `Duration`, `Cost`, `Hold & Refund Lifecycle`, `Date`, `Balance After`.
   - Replaces vague delta entries with clear explanations:
     - *"Outbound Call (+91 98200 12345) • 45s duration • -1 Credit • Held 5, refunded 4"*
     - *"In-Browser Voice Test • 2m 10s • 0 Credits (Free trial session used: 7 remaining)"*
     - *"Admin Credit Top-up • +100 Credits (100 calling minutes)"*
3. **Test Agent Modal:**
   - Trial Badge header: *"Free Trial: 7 of 10 Tests Remaining"*
   - Live Countdown Pill: *"⏱️ 02:45 / 03:00"*
   - Banner notification on expiration: *"3-minute testing session ending now."*
   - Phone Tab Warning: *"Real phone calls use standard credits at 1 credit/min (5 credits min balance required)."*

---

## 4. Implementation Calls Made by Builder

1. **Legacy Credit Migration:** Existing wallets in database will have their `available_credits` and `reserved_credits` converted from seconds to minutes using `max(0, round(credits / 60))`.
2. **Paid Browser Test Rules:** Once the 10 free tests are used up, paid in-browser voice tests follow the standard 5-credit hold with the organization's max call duration cap (7 minutes default).
3. **Packs Update:** Default calling packs in `backend/services/wallet_service.py` will be seeded with clean minute denominations: Starter (100 mins/credits for ₹999), Growth (500 mins/credits for ₹3,999), Pro (1,000 mins/credits for ₹6,999).

---

## 5. Review & Approval Gate
This specification incorporates all requirements agreed upon during brainstorming. Upon your approval, this document will be passed to `superpowers:writing-plans` to create the step-by-step implementation plan.
