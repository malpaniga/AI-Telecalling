# Simplified Credit System & In-Browser Test Free Trial Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the credit system from confusing per-second accounting to an intuitive minute-based model (1 credit = 1 minute) with strict 5-credit holds, a 7-minute call duration cap, 10 free 3-minute in-browser test sessions, and transparent receipts.

**Architecture:** Update MongoDB schemas and atomic wallet operations in `CreditService` to enforce 1 credit = 1 minute with ceil rounding and rolling 5-minute hold extensions. Connect in-browser WebSocket call handling to a 10-session trial quota with a server-side 180s hard disconnect, while keeping text chat unmetered. Expose minute-based balances, active holds, trial counters, and human-readable ledger entries across the customer credits page and test agent modal.

**Tech Stack:** Python 3.14 / FastAPI, Motor (Async MongoDB), Redis, Pydantic v2, Next.js 14 / TypeScript, Tailwind CSS.

**Spec:** [docs/superpowers/specs/2026-10-27-simplified-credit-system-design.md](file:///c:/Programs/saas/docs/superpowers/specs/2026-10-27-simplified-credit-system-design.md)

## Global Constraints

- 1 Credit = 1 Minute of Call Time (60 billable seconds, integer values only).
- Billed credits ceiling formula: `math.ceil(duration_seconds / 60) if duration_seconds > 0 else 0`.
- 0 credits billed for failed, busy, or 0-second connected calls, with immediate full hold release.
- Minimum 5 available credits strictly required to initiate any phone call (`available_credits >= 5`).
- Initial hold for phone calls: exactly 5 credits.
- Live call rolling hold check at 4:45: auto-extends hold by 5 credits if `available_credits >= 5`; wraps up at 5:00 if balance is 0.
- Organization default maximum call duration: 7 minutes (`max_call_duration_minutes = 7`).
- In-browser voice test free quota: 10 sessions per organization (`free_test_sessions_remaining = 10`).
- In-browser voice test session cap: exactly 180 seconds (3 minutes) with speech cutoff notice: *"3-minute testing session ending now."*
- In-browser text Chat tab: 100% free and unmetered (no trial session deduction, no credit holds).
- Phone tab test calls: draw from standard credits at 1 credit/min with the standard 5-credit hold.
- Calling pack denominations: Starter (100 mins for ₹999), Growth (500 mins for ₹3,999), Pro (1,000 mins for ₹6,999).

## Review Focus

1. **Zero-second call completion (busy / rejected / network drop):** When duration is 0 seconds, system must bill exactly 0 credits and release the full 5-credit hold back to available balance without leaving negative deltas.
2. **Concurrent call reservation gate:** When an organization with 7 credits initiates 2 simultaneous calls, the first call successfully reserves 5 credits (leaving 2), and the second call is rejected immediately with "Insufficient credits. Minimum 5 credits required to initiate a call."
3. **Mid-call exhaustion at 4:45 check:** When a call reaches 4:45 and the organization has 0 available credits, the system must not allow the call to run past 5:00, terminating at 5:00 sharp to prevent negative wallet balance.
4. **Free trial exhaustion boundary (session 10 to 11 transition):** During session 10, the call is completely free. Starting session 11 requires at least 5 standard wallet credits and transitions to paid minute billing.
5. **Exact 180-second hard stop on browser voice tests:** At second 180, the server-side WebSocket handler must close the stream cleanly even if the frontend tab fails or network delays, preventing runaway LLM/TTS generation.

---

### Task 1: Model & Schema Updates (Wallet, OrganizationSettings & CallingPacks)

**Files:**
- Modify: `backend/models/organization.py:14-55`
- Modify: `backend/models/wallet.py:1-100`
- Modify: `backend/services/wallet_service.py:30-80`
- Create: `backend/tests/test_simplified_models.py`

**Interfaces:**
- Consumes: `TimestampedModel` from `backend.models.base`
- Produces: `OrganizationSettings.max_call_duration_minutes` (`int = 7`), `OrganizationSettings.free_test_sessions_remaining` (`int = 10`), `OrganizationSettings.free_test_session_max_minutes` (`int = 3`), updated `DEFAULT_CALLING_PACKS`

- [ ] **Step 1: Write the failing test for new OrganizationSettings fields and CallingPack definitions**

```python
# backend/tests/test_simplified_models.py
import pytest
from backend.models.organization import OrganizationSettings
from backend.services.wallet_service import DEFAULT_CALLING_PACKS

def test_organization_settings_defaults():
    settings = OrganizationSettings()
    assert settings.max_call_duration_minutes == 7
    assert settings.free_test_sessions_remaining == 10
    assert settings.free_test_session_max_minutes == 3

def test_calling_packs_minute_denominations():
    starter = next(p for p in DEFAULT_CALLING_PACKS if p["slug"] == "starter-pack")
    assert starter["credits"] == 100
    assert starter["price_paise"] == 99900

    growth = next(p for p in DEFAULT_CALLING_PACKS if p["slug"] == "growth-pack")
    assert growth["credits"] == 500
    assert growth["bonus_credits"] == 50
    assert growth["price_paise"] == 399900

    pro = next(p for p in DEFAULT_CALLING_PACKS if p["slug"] == "pro-pack")
    assert pro["credits"] == 1000
    assert pro["bonus_credits"] == 150
    assert pro["price_paise"] == 699900
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_simplified_models.py -v`  
Expected: FAIL with AttributeError or AssertionError on default values.

- [ ] **Step 3: Implement new settings fields and pack definitions**

In `backend/models/organization.py`, add `max_call_duration_minutes: int = 7`, `free_test_sessions_remaining: int = 10`, `free_test_session_max_minutes: int = 3` to `OrganizationSettings`.  
In `backend/models/wallet.py`, update module docstrings to reflect 1 credit = 1 billable minute.  
In `backend/services/wallet_service.py`, update `DEFAULT_CALLING_PACKS` to:
- Starter Pack: 100 credits, ₹999 (99900 paise)
- Growth Pack: 500 credits + 50 bonus, ₹3,999 (399900 paise)
- Pro Pack: 1000 credits + 150 bonus, ₹6,999 (699900 paise)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_simplified_models.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/models/organization.py backend/models/wallet.py backend/services/wallet_service.py backend/tests/test_simplified_models.py
git commit -m "feat(billing): update OrganizationSettings and CallingPack minute denominations"
```

---

### Task 2: CreditService 1-Credit=1-Minute Billing, 5-Credit Hold & Auto-Extension

**Files:**
- Modify: `backend/services/credit_service.py:75-340`
- Create: `backend/tests/test_minute_credit_service.py`

**Interfaces:**
- Consumes: `WalletRepository`, `WalletTransactionRepository`, `CreditLotRepository`
- Produces:
  - `CreditService.can_start_call(organization_id: str, required_credits: int = 5) -> dict`
  - `CreditService.reserve(organization_id: str, call_id: str, max_credits: int = 5) -> dict`
  - `CreditService.settle(organization_id: str, call_id: str, duration_seconds: int, idempotency_key: Optional[str] = None) -> dict`
  - `CreditService.extend_hold(organization_id: str, call_id: str, additional_credits: int = 5) -> dict`

- [ ] **Step 1: Write failing tests for minute calculation, 5-credit minimum, and hold extension**

```python
# backend/tests/test_minute_credit_service.py
import pytest
import math
import mongomock_motor
from backend.services.credit_service import CreditService
from backend.repositories.wallet_repo import WalletRepository

@pytest.fixture
def mock_db():
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test_db"]

@pytest.mark.anyio
async def test_can_start_call_requires_minimum_5_credits(mock_db):
    svc = CreditService(mock_db)
    wallet_repo = WalletRepository(mock_db)
    
    # 4 credits -> cannot start
    w = await wallet_repo.get_or_create("org_4")
    await wallet_repo.atomic_add(w.id, 4, "total_purchased")
    res = await svc.can_start_call("org_4", required_credits=5)
    assert res["can_start"] is False
    assert res["shortfall"] == 1

    # 5 credits -> can start
    w5 = await wallet_repo.get_or_create("org_5")
    await wallet_repo.atomic_add(w5.id, 5, "total_purchased")
    res5 = await svc.can_start_call("org_5", required_credits=5)
    assert res5["can_start"] is True

@pytest.mark.anyio
async def test_settle_ceiling_rounding(mock_db):
    svc = CreditService(mock_db)
    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_settle")
    await wallet_repo.atomic_add(w.id, 20, "total_purchased")

    # Reserve 5 credits
    await svc.reserve("org_settle", "call_1", max_credits=5)
    
    # 45 seconds -> 1 credit billed, 4 refunded, available after = 20 - 1 = 19
    res = await svc.settle_duration("org_settle", "call_1", duration_seconds=45)
    assert res["billed_credits"] == 1
    assert res["refunded_credits"] == 4
    assert res["new_available_balance"] == 19

@pytest.mark.anyio
async def test_settle_zero_duration_bills_zero_credits(mock_db):
    svc = CreditService(mock_db)
    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_zero")
    await wallet_repo.atomic_add(w.id, 10, "total_purchased")

    await svc.reserve("org_zero", "call_zero", max_credits=5)
    # 0 seconds connected -> 0 credits billed, 5 refunded, balance remains 10
    res = await svc.settle_duration("org_zero", "call_zero", duration_seconds=0)
    assert res["billed_credits"] == 0
    assert res["refunded_credits"] == 5
    assert res["new_available_balance"] == 10

@pytest.mark.anyio
async def test_extend_hold_success(mock_db):
    svc = CreditService(mock_db)
    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_ext")
    await wallet_repo.atomic_add(w.id, 20, "total_purchased")

    await svc.reserve("org_ext", "call_ext", max_credits=5)
    # Available was 20 -> 15 after initial reserve
    ext = await svc.extend_hold("org_ext", "call_ext", additional_credits=5)
    assert ext["extended_credits"] == 5
    assert ext["total_reserved_credits"] == 10
    assert ext["new_available_balance"] == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_minute_credit_service.py -v`  
Expected: FAIL (`AttributeError: 'CreditService' object has no attribute 'settle_duration'` or `extend_hold`).

- [ ] **Step 3: Implement minute calculation, 5-credit hold, and `extend_hold` in `CreditService`**

1. In `backend/services/credit_service.py`:
   - Update default `required_credits` in `can_start_call` to `5`.
   - Update `reserve()` to validate `max_credits >= 1` (defaulting to 5 for standard calls).
   - Add `settle_duration(organization_id, call_id, duration_seconds: int, idempotency_key=None)`:
     ```python
     billed_credits = math.ceil(duration_seconds / 60) if duration_seconds > 0 else 0
     ```
     Deducts `billed_credits` from reserved, refunds `(reserved_credits - billed_credits)` to available, records descriptive ledger entry:
     `"Call billed: {billed_credits} min ({duration_seconds}s), {refunded} credits returned"`.
   - Add `extend_hold(organization_id, call_id, additional_credits: int = 5)`:
     Atomically reserves `min(additional_credits, wallet.available_credits)` and updates Redis/ledger with the new total reserved credits.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_minute_credit_service.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/credit_service.py backend/tests/test_minute_credit_service.py
git commit -m "feat(billing): implement 1-credit-per-minute billing, 5-credit hold and hold extensions"
```

---

### Task 3: CallService & Telephony Integration (5-Credit Hold, Extension at 4:45 & 7-Min Cap)

**Files:**
- Modify: `backend/services/call_service.py:30-280`
- Modify: `backend/telephony/vobiz.py:250-310, 520-545`
- Modify: `backend/services/post_call_service.py:280-300`
- Create: `backend/tests/test_call_service_duration.py`

**Interfaces:**
- Consumes: `CreditService.reserve`, `CreditService.settle_duration`, `CreditService.extend_hold`
- Produces: `CallService.initiate_call` with `DEFAULT_RESERVE_CREDITS = 5`, automatic 7-minute organization cap in telephony sessions

- [ ] **Step 1: Write failing test for CallService 5-credit reservation and duration settlement**

```python
# backend/tests/test_call_service_duration.py
import pytest
import mongomock_motor
from backend.services.call_service import CallService, DEFAULT_RESERVE_CREDITS
from backend.services.credit_service import CreditService
from backend.repositories.wallet_repo import WalletRepository

@pytest.fixture
def mock_db():
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test_call_db"]

@pytest.mark.anyio
async def test_call_service_uses_5_credit_default(mock_db):
    assert DEFAULT_RESERVE_CREDITS == 5

@pytest.mark.anyio
async def test_initiate_call_fails_if_under_5_credits(mock_db):
    wallet_repo = WalletRepository(mock_db)
    w = await wallet_repo.get_or_create("org_low")
    await wallet_repo.atomic_add(w.id, 4, "total_purchased")

    call_svc = CallService(mock_db)
    with pytest.raises(ValueError, match="Insufficient credits"):
        await call_svc.initiate_call(
            organization_id="org_low",
            to_number="+919876543210",
            from_number="+911144556677",
            provider="mock"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_call_service_duration.py -v`  
Expected: FAIL (`DEFAULT_RESERVE_CREDITS != 5` or ValueError not matching).

- [ ] **Step 3: Implement CallService and telephony changes**

1. In `backend/services/call_service.py`:
   - Change `DEFAULT_RESERVE_CREDITS = 5` (was 300).
   - In `initiate_call`: Pre-flight check with `credit_svc.can_start_call(organization_id, required_credits=reserve_credits)`. If False, raise `ValueError("Insufficient credits. Minimum 5 credits required to initiate a call.")`.
   - In `finalize_call`: Call `credit_svc.settle_duration(organization_id, call_id, duration_seconds=duration_s)`.
2. In `backend/telephony/vobiz.py`:
   - In inbound handler: change `required_credits=5`, `max_credits=5` (was 60/300).
   - In `ws_vobiz` stream:
     - Check organization's `max_call_duration_minutes` (default 7).
     - At 4:45 into the call: trigger `credit_svc.extend_hold(org_id, call_id, 5)`. If wallet has 0 credits, set cutoff at 5:00.
     - Enforce disconnect at `max_call_duration_minutes * 60` seconds with `hangup_vobiz_call`.
     - In disconnection/settle: use `settle_duration(c_doc.organization_id, call_id, duration_seconds=duration)` instead of the ad-hoc formula.
3. In `backend/services/post_call_service.py`:
   - In `_stage_wallet_settle`: call `settle_duration` with `call.duration_s`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_call_service_duration.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/call_service.py backend/telephony/vobiz.py backend/services/post_call_service.py backend/tests/test_call_service_duration.py
git commit -m "feat(telephony): enforce 5-credit hold, rolling extension, and 7-min duration cap"
```

---

### Task 4: In-Browser Voice Testing (10 Free Sessions, 3-Min Hard Cutoff & Free Chat)

**Files:**
- Modify: `backend/main.py:225-300`
- Modify: `backend/api/v1/wallet.py:15-180`
- Create: `backend/tests/test_browser_test_session.py`

**Interfaces:**
- Consumes: `OrganizationSettings.free_test_sessions_remaining`, `CreditService`
- Produces:
  - GET `/api/v1/wallet/free-tests`: returns `{free_tests_remaining, max_minutes_per_test: 3}`
  - POST `/api/v1/wallet/admin/grant-free-tests`: admin grants `count` free test sessions to org
  - WebSocket `/ws/call`: enforces 180s timeout when on free trial, speaks cutoff notice, transitions to 5-credit hold if free trial is 0

- [ ] **Step 1: Write failing test for free trial quota and admin grant endpoints**

```python
# backend/tests/test_browser_test_session.py
import pytest
import mongomock_motor
from backend.repositories.organization_repo import OrganizationRepository
from backend.models.organization import OrganizationSettings

@pytest.fixture
def mock_db():
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test_browser_db"]

@pytest.mark.anyio
async def test_organization_created_with_10_free_tests(mock_db):
    org_repo = OrganizationRepository(mock_db)
    org = await org_repo.create(name="Acme Inc", email="acme@test.com", slug="acme")
    assert org.settings.free_test_sessions_remaining == 10
    assert org.settings.free_test_session_max_minutes == 3
```

- [ ] **Step 2: Run test to verify it passes or fails**

Run: `pytest backend/tests/test_browser_test_session.py -v`  
Expected: PASS or verify OrganizationRepository saves the new settings defaults.

- [ ] **Step 3: Implement 3-minute cutoff in `/ws/call` and admin grant endpoint**

1. In `backend/api/v1/wallet.py`:
   - Add endpoint `GET /api/v1/wallet/trial-status`:
     ```python
     @router.get("/trial-status")
     async def get_trial_status(user: CurrentUser = Depends(get_current_user)):
         org = await OrganizationRepository(get_db()).find_by_id(user.org_id)
         return {
             "free_tests_remaining": org.settings.free_test_sessions_remaining,
             "free_test_session_max_minutes": org.settings.free_test_session_max_minutes,
         }
     ```
   - Add endpoint `POST /api/v1/wallet/admin/grant-free-tests` (require platform admin):
     Increments `settings.free_test_sessions_remaining` by `body.count`.
2. In `backend/main.py` (`/ws/call`):
   - Resolve `org_id` from query parameter or agent document.
   - If `org.settings.free_test_sessions_remaining > 0`:
     - Decrement `free_test_sessions_remaining` atomically by 1.
     - Set session timeout timer: `180.0` seconds (3 minutes).
     - At 180s: send audio/json alert `{"type": "info", "text": "3-minute testing session ending now."}` and close with code 1000.
   - If `org.settings.free_test_sessions_remaining == 0`:
     - Require `wallet.available_credits >= 5`. If insufficient, reject with 4002 error: `"Minimum 5 credits required to run a test call."`.
     - Reserve 5 credits at start; on websocket disconnect, call `credit_svc.settle_duration(org_id, call_id, duration_seconds)`.

- [ ] **Step 4: Verify `/test-chat` remains untouched and unmetered**

Inspect `backend/api/v1/model_directory.py:392` to confirm `/test-chat` performs pure LLM inference without deducting trial sessions or wallet credits.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/api/v1/wallet.py backend/tests/test_browser_test_session.py
git commit -m "feat(test-agent): enforce 10 free 3-minute test sessions with server-side cutoff"
```

---

### Task 5: Frontend Customer Credits & Activity Ledger Redesign

**Files:**
- Modify: `frontend/lib/api.ts:250-320`
- Modify: `frontend/app/(dashboard)/credits/page.tsx:1-172`

**Interfaces:**
- Consumes: `/api/v1/wallet`, `/api/v1/wallet/transactions`, `/api/v1/wallet/trial-status`
- Produces: Redesigned Credits page showing Available Minutes, Active Holds, Free Browser Tests, and itemized ledger

- [ ] **Step 1: Update API client in `frontend/lib/api.ts`**

Add `trialStatus: () => apiRequest<{ free_tests_remaining: number; free_test_session_max_minutes: number }>("GET", "/api/v1/wallet/trial-status")` to `api.wallet`.

- [ ] **Step 2: Update Metric Cards in `frontend/app/(dashboard)/credits/page.tsx`**

Replace old metrics with:
1. **Available Balance:** `formatCredits(wallet.available_credits)} Mins ({wallet.available_credits} Credits)`
2. **Active Call Holds:** `formatCredits(wallet.reserved_credits)} Mins ({wallet.reserved_credits} Credits)`
3. **Free Browser Tests:** `{trialStatus.free_tests_remaining} Left of 10 (Max 3 mins each)`

- [ ] **Step 3: Redesign the Transaction History Table**

Replace the table columns with:
`["Activity / Call", "Duration", "Cost", "Hold Lifecycle", "Date", "Balance After"]`
Format each row clearly:
- If `credits_delta < 0`:
  - Show call target/name (e.g. `Call to {t.call_id}`)
  - Cost: `{t.credits_delta} Credits`
  - Lifecycle: `t.description` (e.g. `Billed 1 min (45s), 4 credits returned`)
- If `transaction_type === "bonus"` or `"purchase"`:
  - Cost: `+{t.credits_delta} Credits` (e.g. `Purchased 100 calling minutes`)
- Balance After: `{t.balance_after} Credits`

- [ ] **Step 4: Verify build with type-check**

Run: `npm --prefix frontend run build` or `npx --prefix frontend tsc --noEmit`  
Expected: PASS with 0 errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/api.ts frontend/app/\(dashboard\)/credits/page.tsx
git commit -m "feat(frontend): redesign customer credits page with minute metrics and itemized ledger"
```

---

### Task 6: Frontend Test Agent Modal & Admin Controls

**Files:**
- Modify: `frontend/components/test-agent/TestAgentModal.tsx:50-250, 750-850`
- Modify: `frontend/app/(dashboard)/agents/[id]/page.tsx:2300-2350`
- Modify: `frontend/app/(admin)/admin/calling-packs/page.tsx:1-150`
- Modify: `frontend/app/(admin)/admin/organizations/[id]/page.tsx:1-200`

**Interfaces:**
- Consumes: `api.wallet.trialStatus()`, `api.wallet.admin.grantFreeTests()`
- Produces: Test Agent Modal trial countdown pill, 3-minute cutoff toast, Phone tab 5-credit warning, Admin grant actions

- [ ] **Step 1: Add Free Trial Badge & 3-Minute Countdown to `TestAgentModal.tsx`**

1. In header of `TestAgentModal`:
   - If `free_tests_remaining > 0`: Display green pill: `Free Trial: {free_tests_remaining} of 10 remaining (Max 3 mins)`.
   - If `free_tests_remaining === 0`: Display neutral pill: `Standard Rate: 1 credit / min (5 credits min balance)`.
2. When Voice test is active:
   - Render countdown timer: `⏱️ {formatMMSS(180 - callDuration)} / 03:00`.
   - When timer reaches 0: Stop call, play sound / show toast: `"3-minute testing session ending now. Call disconnected."`.
3. In Phone Tab:
   - Add clear warning text: `"Real phone calls use standard credits at 1 credit/minute (requires at least 5 available credits in your wallet)."`

- [ ] **Step 2: Add Admin Actions in `calling-packs` and `organizations/[id]`**

1. In `frontend/app/(admin)/admin/calling-packs/page.tsx`:
   - Add button `"Grant Free Test Sessions"` opening modal to grant `N` test sessions to an organization.
2. In `frontend/app/(admin)/admin/organizations/[id]/page.tsx`:
   - Display `Free Test Sessions Remaining: {org.settings.free_test_sessions_remaining}`.
   - Display `Max Call Duration: {org.settings.max_call_duration_minutes} minutes`.
   - Add inline input to edit max call duration (default 7).

- [ ] **Step 3: Verify frontend type-check**

Run: `npx --prefix frontend tsc --noEmit`  
Expected: PASS with 0 errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/test-agent/TestAgentModal.tsx frontend/app/\(dashboard\)/agents/\[id\]/page.tsx frontend/app/\(admin\)/admin/calling-packs/page.tsx frontend/app/\(admin\)/admin/organizations/\[id\]/page.tsx
git commit -m "feat(ui): add test agent 3-min countdown, trial badge, and admin free trial grant controls"
```

---

### Task 7: Data Migration Script & End-to-End Verification

**Files:**
- Create: `backend/scripts/migrate_credits_to_minutes.py`
- Create: `backend/tests/test_e2e_minute_credit_flow.py`

**Interfaces:**
- Consumes: MongoDB `wallets`, `calling_packs`, `organizations` collections
- Produces: Clean migration converting second credits to minute credits (`round(credits / 60)`) and seeded packs

- [ ] **Step 1: Write the migration script**

```python
# backend/scripts/migrate_credits_to_minutes.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import settings

async def migrate():
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]

    # 1. Migrate Wallets
    async for w in db.wallets.find():
        old_avail = w.get("available_credits", 0)
        old_res = w.get("reserved_credits", 0)
        new_avail = max(0, round(old_avail / 60))
        new_res = max(0, round(old_res / 60))
        await db.wallets.update_one(
            {"_id": w["_id"]},
            {"$set": {"available_credits": new_avail, "reserved_credits": new_res}}
        )

    # 2. Update Organizations settings
    await db.organizations.update_many(
        {"settings.free_test_sessions_remaining": {"$exists": False}},
        {"$set": {
            "settings.free_test_sessions_remaining": 10,
            "settings.free_test_session_max_minutes": 3,
            "settings.max_call_duration_minutes": 7,
        }}
    )
    print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
```

- [ ] **Step 2: Write end-to-end integration test proving the entire lifecycle**

```python
# backend/tests/test_e2e_minute_credit_flow.py
import pytest
import mongomock_motor
from backend.services.credit_service import CreditService
from backend.repositories.wallet_repo import WalletRepository
from backend.repositories.organization_repo import OrganizationRepository

@pytest.mark.anyio
async def test_full_credit_lifecycle_e2e():
    client = mongomock_motor.AsyncMongoMockClient()
    db = client["test_e2e"]
    
    # 1. Org created with 10 free tests
    org_repo = OrganizationRepository(db)
    org = await org_repo.create(name="Beta Corp", email="beta@test.com", slug="beta")
    assert org.settings.free_test_sessions_remaining == 10

    # 2. Fund org with 20 minutes (20 credits)
    wallet_repo = WalletRepository(db)
    w = await wallet_repo.get_or_create(org.id)
    await wallet_repo.atomic_add(w.id, 20, "total_purchased")

    # 3. Start call: reserves 5 credits (available = 15, reserved = 5)
    credit_svc = CreditService(db)
    res = await credit_svc.reserve(org.id, "call_e2e_1", max_credits=5)
    assert res["reserved_credits"] == 5
    assert res["new_available_balance"] == 15

    # 4. Call ends at 75 seconds (1m 15s) -> 2 credits billed, 3 credits refunded
    settle = await credit_svc.settle_duration(org.id, "call_e2e_1", duration_seconds=75)
    assert settle["billed_credits"] == 2
    assert settle["refunded_credits"] == 3
    assert settle["new_available_balance"] == 18

    # 5. Ledger has descriptive entry
    txns = await credit_svc.txn_repo.find_many({"organization_id": org.id})
    consume_txn = next(t for t in txns if t.transaction_type == "consume")
    assert "2 min (75s)" in consume_txn.description
```

- [ ] **Step 3: Run end-to-end test**

Run: `pytest backend/tests/test_e2e_minute_credit_flow.py -v`  
Expected: PASS

- [ ] **Step 4: Update Graphify Knowledge Graph**

Run: `graphify update .`

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/migrate_credits_to_minutes.py backend/tests/test_e2e_minute_credit_flow.py
git commit -m "feat(billing): add migration script and end-to-end credit verification suite"
```
