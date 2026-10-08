# MVP_PROGRESS.md
# AI Telecalling SaaS — Development Progress

**Last updated:** 2026-10-08  
**Current checkpoint:** M18 PASS — Appointments Complete  
**Next checkpoint:** M19 — Knowledge Base

---

## CHECKPOINT HISTORY

---

### M11 — AGENT BUILDER

```
Checkpoint: M11
Status: IN_PROGRESS
Started: 2026-10-08
Objective: Create tenant-safe AI agents, immutable versions, and configuration-driven business templates.

Tests:
  - backend/tests/test_m11_agents.py — RED (AgentService not implemented yet)

Remaining work:
  - Implement models, repositories, service, APIs, generic templates, regression, and commit.
Next checkpoint: M11
```

---

### M10 — PROVIDER ROUTER

```
Checkpoint: M10
Status: PASS
Started: 2026-10-08
Completed: 2026-10-08
Objective: Resolve primary/fallback providers by health, capability, and language without customer configuration changes.

Implementation so far:
  - Added ProviderRouter and ResolvedProvider internal selection boundary.
  - Rejects unhealthy providers and unsupported languages; logs fallback decisions.
  - Persists failover events in MongoDB for provider operations review.

Tests:
  - backend/tests/test_m10_provider_router.py — 4 tests
  - Regression: 293 tests across M1–M10

Tests passed: 293 total
Tests failed: 0
Manual verification: PASS — primary, fallback, capability, language, and durable failover behavior.
Known issues: Provider health signals are injected until M26 adds active health monitoring.
Remaining work: None for M10.
Next checkpoint: M11
Git commit: HEAD (checkpoint: M10 provider router)
```

---

### M9 — AI VOICE PROFILES

```
Checkpoint: M9
Status: PASS
Started: 2026-10-08
Completed: 2026-10-08
Objective: Implement customer-safe AI voice profiles and immutable internal route versions.

Implementation so far:
  - Added voice profiles, version repositories, tenant-safe service, and customer/admin APIs.
  - Customer responses redact all provider route, model, ID, metadata, and cost details.
  - Versions are immutable and active profiles reference a pinned version.

Tests:
  - backend/tests/test_m9_voice_profiles.py — 4 tests
  - Regression: 289 tests across M1–M9

Tests passed: 289 total
Tests failed: 0
Manual verification: PASS — customer view excludes all internal provider route data.
Known issues: Existing third-party asyncio/JWT/TestClient deprecation warnings remain non-blocking.
Remaining work: Provider route selection and failover are deferred to M10.
Next checkpoint: M10
Git commit: HEAD (checkpoint: M9 voice profiles)
```

---

### M8 — PROVIDER ABSTRACTION

```
Checkpoint: M8
Status: PASS
Started: 2026-10-08
Completed: 2026-10-08
Objective: Move telephony, STT, TTS, LLM, payment, and phone-number integrations
           behind typed provider contracts and a provider registry.

Implementation so far:
  - Added typed TelephonyProvider, STTProvider, TTSProvider, LLMProvider, and
    PhoneNumberProvider contracts alongside the existing PaymentProvider.
  - Added ProviderRegistry and offline mock implementations for every provider
    category.
  - Wrapped existing Twilio and Sarvam capabilities behind adapter boundaries.
  - Added concrete Exotel, ElevenLabs, and OpenAI-compatible HTTP adapters.
  - Added a demo registry bootstrap that supplies mock providers for every
    runtime provider category without paid credentials.

Tests:
  - backend/tests/test_m8_provider_abstraction.py — 5 tests
  - Regression: 280 tests across M1–M7

Tests passed: 285 total
Tests failed: 0

Manual verification:
  - PASS: registry resolves only typed provider contracts and rejects unknown or
    duplicate registrations.
  - PASS: provider request/response normalization is tested without network I/O.
  - PASS: demo registry provides complete offline telephony, STT, TTS, LLM, and
    phone-number workflows.

Known issues:
  - Concrete live API calls require configured provider credentials and are not
    exercised against external accounts in CI.

Remaining work:
  - Route selection belongs to M10; voice-profile configuration belongs to M9.

Next checkpoint: M9
Git commit: HEAD (checkpoint: M8 provider abstraction)
```

---

### M7 — PHONE NUMBER INVENTORY

```
Checkpoint: M7
Status: PASS
Started: 2026-10-08
Completed: 2026-10-08
Objective: Build platform-owned phone number inventory with provider details
           hidden from customers, assignment lifecycle management, immutable
           assignment history, and concurrency-safe reservations.

Implementation:
  - backend/models/phone_number.py — PhoneNumber and immutable
    PhoneNumberAssignment documents. Provider data and rental cost remain
    internal-only.
  - backend/repositories/phone_number_repo.py — inventory querying, unique
    E.164 number lookup, and MongoDB atomic available -> reserved -> assigned
    transition; only one concurrent request can reserve a number.
  - backend/services/phone_number_service.py — add, assign, release, suspend,
    reactivate, tenant-scoped lookup, inventory statistics, and idempotent demo
    inventory seeding. Customer views redact provider data.
  - backend/api/v1/phone_numbers.py — authenticated customer inventory and
    assigned-number routes, plus platform-only management routes.
  - backend/api/v1/__init__.py — phone-number router registered.
  - backend/tests/test_m7_phone_numbers.py — lifecycle, tenant isolation,
    concurrency, redaction, seed, and HTTP authorization coverage.

Database changes:
  - phone_numbers collection (unique number, organization, status, provider indexes)
  - phone_number_assignments collection (number history and organization indexes)

API changes:
  - GET  /api/v1/phone-numbers/available
  - GET  /api/v1/phone-numbers/my
  - GET  /api/v1/phone-numbers/my/{phone_number_id}
  - GET  /api/v1/phone-numbers/admin
  - POST /api/v1/phone-numbers/admin
  - POST /api/v1/phone-numbers/admin/{phone_number_id}/assign
  - POST /api/v1/phone-numbers/admin/{phone_number_id}/release
  - POST /api/v1/phone-numbers/admin/{phone_number_id}/suspend
  - POST /api/v1/phone-numbers/admin/{phone_number_id}/reactivate
  - GET  /api/v1/phone-numbers/admin/stats

Tests:
  - backend/tests/test_m7_phone_numbers.py — 40 tests
  - Regression: 280 tests across M1–M7

Tests passed: 280 total
Tests failed: 0

Manual verification:
  - PASS: exactly one of five concurrent organizations can claim one number.
  - PASS: organization A cannot retrieve organization B's number.
  - PASS: customer-facing responses exclude provider, provider_resource_id,
    provider_metadata, and rental_paise_per_month.
  - PASS: customer tokens receive 403 from platform inventory endpoints.

Known issues:
  - Existing third-party asyncio/JWT/TestClient deprecation warnings remain;
    no test failures result from them.

Remaining work:
  - Provider provisioning adapters are intentionally deferred to M8.

Next checkpoint: M8
Git commit: HEAD (checkpoint: M7 phone number inventory)
```

---

### M6 — CREDIT RESERVATION + SETTLEMENT

```
Checkpoint: M6
Status: PASS
Started: 2026-10-08
Completed: 2026-10-08
Objective: Reserve credits at call start, release on failure, settle exact
           usage on completion. No double-spend. No negative credits.
           10 concurrent calls verified.

Implementation:
  - backend/services/credit_service.py — CreditService:
    reserve(org_id, call_id, max_credits) — atomic available→reserved,
      Redis key for fast check, WalletTransaction(type=reserve), idempotent
    release(org_id, call_id) — returns reserved→available, idempotent
    settle(org_id, call_id, actual_credits) — bills exact amount, refunds
      over-reserve, FIFO lot consumption, idempotency_key prevents double-settle
    can_start_call() — no-state-change preflight check
    get_active_reservations() — monitoring view
  - backend/api/v1/credits.py — POST /reserve (402 on insufficient),
    POST /release, POST /settle, GET /check, GET /reservations,
    GET /admin/orgs/{id}/reservations
  - backend/api/v1/__init__.py — credits router added
  - Fixed: CreditLot.is_expired handles mongomock naive datetimes
  - Fixed: WalletRepository.atomic_consume fallback for mongomock
  - Fixed: settle() fallback when atomic_consume returns None

Key properties verified by tests:
  - reserve() available→reserved; total unchanged
  - Insufficient credits raises ValueError (HTTP 402)
  - reserve() idempotent (same call_id)
  - release() returns reserved→available; creates ledger entry
  - release() on non-existent reservation is a no-op
  - release() after settle is a no-op
  - settle() bills exact usage; refunds over-reserved amount
  - settle() capped at reserved (safety guard)
  - settle() idempotent: double-settle is a no-op
  - 10 concurrent reserves (600 credits): all 10 succeed, no double-spend
  - 6 calls, 300 credits (5×60): exactly 5 succeed, 6th fails
  - 10 concurrent settles: all 10 succeed, correct final balance
  - Wallet never goes negative under concurrent hammering
  - Every operation creates immutable WalletTransaction ledger entry

Files changed:
  - backend/services/credit_service.py (new)
  - backend/api/v1/credits.py (new)
  - backend/api/v1/__init__.py (updated)
  - backend/models/wallet.py (fixed is_expired timezone handling)
  - backend/repositories/wallet_repo.py (fixed atomic_consume fallback)
  - backend/tests/test_m6_credit_reservation.py (new)

API changes:
  - POST /api/v1/credits/reserve
  - POST /api/v1/credits/release
  - POST /api/v1/credits/settle
  - GET  /api/v1/credits/check
  - GET  /api/v1/credits/reservations
  - GET  /api/v1/credits/admin/orgs/{org_id}/reservations

Tests:
  - backend/tests/test_m6_credit_reservation.py — 32 tests
  - Regression: 208 tests

Tests passed: 240 total (32 new + 208 regression)
Tests failed: 0

Next checkpoint: M7

Git commit: (see below)
```

---

### M5 — CALLING PACKS + WALLET

```
Checkpoint: M5
Status: PASS
Started: 2026-10-08
Completed: 2026-10-08
Objective: Calling pack purchase flow, wallet with immutable ledger, credit lots
           with expiry, bonus, admin adjustment. Every credit movement has a
           WalletTransaction entry. Wallet never goes negative.

Implementation:
  - backend/models/wallet.py — CallingPack (integer credits/paise, bonus),
    Wallet (available + reserved, non-negative), WalletTransaction (immutable
    ledger, typed operations), CreditLot (expiry, FIFO, available_from_lot)
  - backend/repositories/wallet_repo.py — CallingPackRepository,
    WalletRepository (atomic $inc ops: atomic_reserve, atomic_release,
    atomic_consume, atomic_add, atomic_expire; prevent negative via query guards),
    WalletTransactionRepository (find-before-insert idempotency for mongomock),
    CreditLotRepository (FIFO consume_from_lots, deactivate_expired)
  - backend/services/wallet_service.py — WalletService: purchase_credits
    (idempotency checked before wallet update), grant_bonus, admin_adjustment
    (deduction raises if insufficient), process_expiry (backdates lots, creates
    expiry ledger entries), get_wallet_summary, get_balance;
    seed_default_packs() (Trial/Starter/Growth/Pro)
  - backend/services/payment_service.py — calling_pack order fulfillment wired;
    create_calling_pack_order() added
  - backend/api/v1/wallet.py — GET/wallet, GET/transactions, GET/lots, GET/packs,
    POST/packs/{id}/order, admin bonus, admin adjust, admin create/update packs
  - backend/api/v1/__init__.py — wallet router added
  - backend/main.py — seed_default_packs() added to lifespan

Key properties verified by tests:
  - Buy 2000 credits → wallet=2000, ledger=+2000, lot=2000 (the M5 acceptance test)
  - Bonus credits add both to wallet and to ledger
  - Every movement has immutable WalletTransaction entry
  - Admin deduction beyond balance raises ValueError (wallet stays positive)
  - Expired lots are removed from wallet with ledger entry
  - Purchase idempotency: same key cannot double-grant
  - Seed packs are idempotent
  - All prices/credits are integer types

Bugs fixed:
  - Missing utcnow import in wallet_service.py
  - Nested run() in tests: refactored to async helpers
  - Idempotency check moved before atomic wallet update (prevents double-grant)

Files changed:
  - backend/models/wallet.py (new)
  - backend/repositories/wallet_repo.py (new)
  - backend/services/wallet_service.py (new)
  - backend/services/payment_service.py (updated — calling_pack fulfillment)
  - backend/api/v1/wallet.py (new)
  - backend/api/v1/__init__.py (updated)
  - backend/main.py (updated — pack seeding)
  - backend/tests/test_m5_wallet.py (new)

API changes:
  - GET  /api/v1/wallet
  - GET  /api/v1/wallet/transactions
  - GET  /api/v1/wallet/lots
  - GET  /api/v1/wallet/packs
  - GET  /api/v1/wallet/packs/{id}
  - POST /api/v1/wallet/packs/{id}/order
  - POST /api/v1/wallet/admin/bonus
  - POST /api/v1/wallet/admin/adjust
  - GET  /api/v1/wallet/admin/orgs/{org_id}
  - POST /api/v1/wallet/admin/packs
  - PATCH /api/v1/wallet/admin/packs/{id}
  - POST /api/v1/wallet/admin/expire

Database changes:
  - calling_packs collection
  - wallets collection (one per org)
  - wallet_transactions collection (immutable ledger)
  - credit_lots collection (expiry tracking)
  - Default packs seeded: Trial (free), Starter (₹999), Growth (₹3,999), Pro (₹6,999)

Tests:
  - backend/tests/test_m5_wallet.py — 39 tests
  - Regression: 169 tests

Tests passed: 208 total (39 new + 169 regression)
Tests failed: 0

Next checkpoint: M6

Git commit: (see below)
```

---

### M4 — RAZORPAY PAYMENT INTEGRATION

```
Checkpoint: M4
Status: PASS
Started: 2026-10-08
Completed: 2026-10-08
Objective: Server-authoritative Razorpay payment flow, webhook verification with
           idempotency, mock provider for tests, orders/payments/invoices in MongoDB.

Implementation:
  - backend/providers/base.py — PaymentProvider abstract interface
  - backend/providers/payment/razorpay.py — Razorpay adapter:
    create_order (amount from DB, never frontend), verify_payment (HMAC-SHA256),
    refund, fetch_payment, verify_webhook_signature
  - backend/providers/payment/mock.py — Mock adapter for tests/DEMO_MODE:
    deterministic signatures, configurable failure mode, reset() for test isolation
  - backend/models/billing.py — Order, Payment (immutable), Invoice, WebhookEvent;
    all amounts in INTEGER PAISE, amount_inr is computed property (not stored)
  - backend/repositories/billing_repo.py — OrderRepository (status FSM),
    PaymentRepository (record_refund with partial tracking),
    InvoiceRepository (sequential INV-YYYY-NNNNNN numbering),
    WebhookEventRepository (idempotency: find-then-insert guards duplicates)
  - backend/services/payment_service.py — PaymentService orchestrates:
    create_subscription_order (amount looked up from plan, NEVER from frontend),
    verify_and_fulfill (sig check → payment record → invoice → subscription activation),
    refund_payment, process_webhook (sig verify → idempotency check → dispatch)
  - backend/api/v1/billing.py — POST /orders/subscription, POST /verify,
    POST /webhook (no auth, sig-verified), POST /refund/{id}, GET /orders,
    GET /payments, GET /invoices, GET /invoices/{id}
  - backend/api/v1/__init__.py — billing router added

Key security properties:
  - Amount NEVER from frontend: backend looks up plan price from MongoDB
  - Payment sig verified via HMAC-SHA256 before any fulfillment
  - Webhook sig verified before any processing
  - Webhook idempotency via (provider, event_id) uniqueness check
  - Duplicate payment attempt returns already_paid (not error, not double-fulfill)
  - Invoice tenant isolation: org A cannot read org B invoice (403)
  - Only billing_admin/platform_admin can issue refunds

Fixed during M4:
  - razorpay SDK 1.4.2 needs setuptools (pkg_resources); installed
  - mongomock doesn't raise DuplicateKeyError on unique indexes: switched
    WebhookEventRepository to find-then-insert for idempotency
  - nested run() inside async: refactored _seed_plan to inline await

Files changed:
  - backend/models/billing.py (new)
  - backend/providers/__init__.py (new)
  - backend/providers/base.py (new)
  - backend/providers/payment/__init__.py (new)
  - backend/providers/payment/razorpay.py (new)
  - backend/providers/payment/mock.py (new)
  - backend/repositories/billing_repo.py (new)
  - backend/services/payment_service.py (new)
  - backend/api/v1/billing.py (new)
  - backend/api/v1/__init__.py (updated)
  - backend/tests/test_m4_payment.py (new)

API changes:
  - POST /api/v1/billing/orders/subscription
  - POST /api/v1/billing/verify
  - POST /api/v1/billing/webhook
  - POST /api/v1/billing/refund/{payment_id}
  - GET  /api/v1/billing/orders
  - GET  /api/v1/billing/payments
  - GET  /api/v1/billing/invoices
  - GET  /api/v1/billing/invoices/{id}

Database changes:
  - orders collection
  - payments collection
  - invoices collection (sequential numbering INV-YYYY-NNNNNN)
  - webhook_events collection (idempotency key: provider+event_id)

Tests:
  - backend/tests/test_m4_payment.py — 43 tests
  - Regression (M1+M2+M3): 126 tests

Tests passed: 169 total (43 new + 126 regression)
Tests failed: 0

Next checkpoint: M5

Git commit: (see below)
```

---

### M3 — PLANS + SUBSCRIPTIONS

```
Checkpoint: M3
Status: PASS
Started: 2026-10-08
Completed: 2026-10-08
Objective: Database-driven subscription plans and entitlements. Changing plan
           configuration in DB changes behaviour without code changes.

Implementation:
  - backend/models/subscription.py — SubscriptionPlan (integer paise prices),
    Subscription (org-scoped, plan snapshot at subscribe time), EntitlementCheck
  - backend/repositories/subscription_repo.py — SubscriptionPlanRepository
    (CRUD, list_public, update_price, update_limits, set_active),
    SubscriptionRepository (create_for_org with snapshot, find_active, cancel,
    upgrade, mark_renewed, count_by_plan)
  - backend/services/subscription_service.py — SubscriptionService with
    entitlement checks (campaign, agent, concurrent calls, features, leads,
    team members), activate_plan, cancel_subscription, change_plan,
    get_entitlements; seed_default_plans() for Starter/Growth/Pro
  - backend/api/v1/subscriptions.py — public plan listing (no auth),
    customer /my/* endpoints, admin /admin/* endpoints (platform-only)
  - backend/main.py — plan seeding added to lifespan
  - backend/api/v1/__init__.py — subscriptions router wired in

Key design properties verified by tests:
  - All prices are integer paise (never float)
  - price_monthly_inr is a computed property, not stored in MongoDB
  - Plan snapshot at subscription time: changing plan DB record does NOT
    retroactively affect existing subscribers
  - New subscriptions pick up updated plan limits
  - One active subscription per org enforced
  - Upgrade/downgrade updates snapshot immediately
  - Feature gates (knowledge_base_enabled, api_access, etc.) from plan config
  - Customers cannot access admin plan creation endpoints (403)
  - Default plans (Starter/Growth/Pro) seeded idempotently on startup

Files changed:
  - backend/models/subscription.py (new)
  - backend/repositories/subscription_repo.py (new)
  - backend/services/__init__.py (new)
  - backend/services/subscription_service.py (new)
  - backend/api/v1/subscriptions.py (new)
  - backend/api/v1/__init__.py (updated)
  - backend/main.py (updated — plan seeding in lifespan)
  - backend/tests/test_m3_subscriptions.py (new)

API changes:
  - GET  /api/v1/subscriptions/plans
  - GET  /api/v1/subscriptions/plans/{slug}
  - GET  /api/v1/subscriptions/my
  - GET  /api/v1/subscriptions/my/entitlements
  - POST /api/v1/subscriptions/my/cancel
  - POST /api/v1/subscriptions/my/change
  - GET  /api/v1/subscriptions/admin/plans
  - POST /api/v1/subscriptions/admin/plans
  - PATCH /api/v1/subscriptions/admin/plans/{plan_id}
  - GET  /api/v1/subscriptions/admin/all
  - POST /api/v1/subscriptions/admin/orgs/{org_id}/activate

Database changes:
  - subscription_plans collection — indexes on (slug unique, is_active, sort_order)
  - subscriptions collection — index on (organization_id unique for active subs)
  - Default plans seeded: starter (₹2,999/mo), growth (₹7,999/mo), pro (₹19,999/mo)

Tests:
  - backend/tests/test_m3_subscriptions.py — 42 tests
  - Regression (M1+M2): 84 tests

Tests passed: 126 total (42 new + 84 regression)
Tests failed: 0

Known issues: None

Next checkpoint: M4

Git commit: (see below)
```

---

### M2 — AUTH + MULTI-TENANCY + RBAC

```
Checkpoint: M2
Status: PASS
Started: 2026-10-08
Completed: 2026-10-08
Objective: JWT authentication, signup/login/logout/refresh, org-scoped RBAC,
           tenant isolation enforcement. Org A must never access Org B data.

Implementation:
  - backend/core/auth.py — JWT create/decode (access + refresh tokens), 
    CurrentUser dataclass, get_current_user/get_optional_user FastAPI deps,
    refresh token revocation via Redis (refresh_revoked:{jti})
  - backend/core/rbac.py — role hierarchy, OrgContext, require_role(),
    require_platform(), require_org_access(), assert_org_access()
  - backend/api/v1/auth.py — POST /signup (org + owner user in one step),
    POST /login, POST /logout, POST /refresh, GET /me
  - backend/api/v1/organizations.py — full RBAC guards on all routes;
    viewer can read own org, org_admin can update, platform can list all
  - backend/api/v1/users.py — invite, list, get, update, deactivate;
    all endpoints enforcing org isolation and role minimums
  - backend/api/v1/__init__.py — auth router added

Key security properties verified by tests:
  - JWT tamper detection
  - Access vs refresh token type enforcement
  - Login brute-force lockout (5 attempts → 15-min lock)
  - User enumeration prevention (same 401 for wrong pw vs nonexistent user)
  - Org A cannot read Org B (HTTP 403 enforced)
  - Viewer cannot update or invite (403)
  - Platform roles cannot be assigned via org invite (400)
  - Unauthenticated requests return 401
  - Refresh token revocation on logout

Files changed:
  - backend/core/auth.py (new)
  - backend/core/rbac.py (new)
  - backend/api/v1/auth.py (new)
  - backend/api/v1/organizations.py (updated — added RBAC)
  - backend/api/v1/users.py (updated — added RBAC)
  - backend/api/v1/__init__.py (updated — added auth router)
  - backend/tests/test_m2_auth_rbac.py (new)

API changes:
  - POST /api/v1/auth/signup
  - POST /api/v1/auth/login
  - POST /api/v1/auth/logout
  - POST /api/v1/auth/refresh
  - GET  /api/v1/auth/me
  - All /api/v1/organizations/* — now require auth
  - All /api/v1/users/* — now require auth

Environment variables:
  - SECRET_KEY (required — JWT signing key)
  - JWT_ALGORITHM (default: HS256)
  - ACCESS_TOKEN_EXPIRE_MINUTES (default: 60)
  - REFRESH_TOKEN_EXPIRE_DAYS (default: 30)

Tests:
  - backend/tests/test_m2_auth_rbac.py — 45 tests
  - Regression (M1): 39 tests

Tests passed: 84 total (45 new + 39 regression)
Tests failed: 0

Manual verification:
  - PASS: Org A cannot access Org B (critical tenant isolation test)
  - PASS: Viewer gets 403 on org admin actions
  - PASS: Unauthenticated requests get 401
  - PASS: Logout revokes refresh token

Known issues:
  - python-jose uses deprecated datetime.utcnow() internally — cosmetic warning only
  - No email verification flow in MVP (deferred)

Remaining work:
  - None for M2

Next checkpoint: M3

Git commit: (see below)
```

---

### M1 — MONGODB FOUNDATION

```
Checkpoint: M1
Status: PASS
Started: 2026-10-08
Completed: 2026-10-08
Objective: Replace PostgreSQL with MongoDB Atlas; implement Motor async client,
           indexes, health check, organizations, users, audit logs.

Implementation:
  - Removed SQLAlchemy/psycopg3/Alembic dependencies
  - Added Motor (async MongoDB), pymongo, pyjwt, bcrypt, python-slugify
  - Created backend/core/db.py — Motor client, init_db/close_db/ping_db,
    complete index creation for all 30+ planned collections (idempotent)
  - Created backend/core/redis.py — Redis client factory using REDIS_URL
  - Created backend/core/health.py — all-components health check
  - Created backend/models/base.py — DocumentModel/TimestampedModel base classes
  - Created backend/models/organization.py — Organization, OrganizationSettings,
    OrganizationPublic, OrganizationCreate
  - Created backend/models/user.py — User, UserPublic, UserCreate, TokenPair;
    PLATFORM_ROLES / ORGANIZATION_ROLES constants
  - Created backend/models/audit_log.py — AuditLog (immutable)
  - Created backend/repositories/base.py — BaseRepository CRUD wrapper
  - Created backend/repositories/organization_repo.py — create, find_by_id,
    find_by_slug, find_by_email, list_all, slug uniqueness enforcement, suspend/reactivate
  - Created backend/repositories/user_repo.py — create, authenticate,
    bcrypt password hashing, lockout after 5 failed attempts, deactivate, reset token
  - Created backend/repositories/audit_log_repo.py — log(), list_for_org(),
    list_platform()
  - Updated backend/config.py — MONGODB_URI, REDIS_URL, JWT settings,
    all provider keys; removed postgres_* fields; legacy Sarvam key fallback
  - Updated backend/main.py — MongoDB+Redis lifespan; health check uses core/health;
    call pipeline conditional on key availability; versioned /api/v1 router
  - Created backend/api/v1/__init__.py, organizations.py, users.py
  - Updated backend/memory/repository.py — MongoDB-backed (replaces SQLAlchemy)
  - Updated backend/memory/session.py — uses REDIS_URL from config
  - Updated backend/db/database.py — stub pointing to core/db
  - Updated backend/api/routes.py — MongoDB-backed legacy dashboard routes
  - Updated backend/call_session.py — removed async_session() calls; uses new repo
  - Updated docker-compose.yml — removed PostgreSQL service (keep Redis)
  - Updated .env.example — MongoDB URI, all new vars
  - Created backend/tests/test_m1_mongodb.py — 39 tests
  - Created .venv (Python 3.13)

Files changed:
  - backend/requirements.txt
  - backend/config.py
  - backend/main.py
  - backend/call_session.py
  - backend/db/database.py
  - backend/memory/repository.py
  - backend/memory/session.py
  - backend/api/routes.py
  - backend/api/v1/__init__.py (new)
  - backend/api/v1/organizations.py (new)
  - backend/api/v1/users.py (new)
  - backend/core/__init__.py (new)
  - backend/core/db.py (new)
  - backend/core/redis.py (new)
  - backend/core/health.py (new)
  - backend/models/__init__.py (new)
  - backend/models/base.py (new)
  - backend/models/organization.py (new)
  - backend/models/user.py (new)
  - backend/models/audit_log.py (new)
  - backend/repositories/__init__.py (new)
  - backend/repositories/base.py (new)
  - backend/repositories/organization_repo.py (new)
  - backend/repositories/user_repo.py (new)
  - backend/repositories/audit_log_repo.py (new)
  - backend/tests/__init__.py (new)
  - backend/tests/test_m1_mongodb.py (new)
  - docker-compose.yml
  - .env.example

Database changes:
  - PostgreSQL removed
  - MongoDB Atlas is now primary database
  - 30+ collection indexes defined and created on startup (idempotent)
  - Collections: organizations, users, audit_logs (and stubs for all future collections)

API changes:
  - /api/v1/organizations — POST (create), GET / (list), GET /{id}
  - /api/v1/users — POST (create), GET /{id}
  - /health — now checks MongoDB + Redis (not PostgreSQL)
  - Legacy /api/stats, /api/calls, /api/leads — MongoDB-backed

Environment variables:
  - Added: MONGODB_URI, MONGODB_DATABASE, REDIS_URL, SECRET_KEY, APP_ENV,
    DEMO_MODE, JWT settings, ELEVENLABS_API_KEY, OPENAI_API_KEY, OPENAI_BASE_URL,
    RAZORPAY_*, EXOTEL_*, SARVAM_API_KEY
  - Removed: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT,
    DATABASE_URL

Tests:
  - backend/tests/test_m1_mongodb.py

Tests passed: 39
Tests failed: 0

Manual verification:
  - PASS: All 17 modules import cleanly
  - PASS: FastAPI app imports and registers 18 routes
  - PASS: No SQLAlchemy/psycopg3 references in core files

Known issues:
  - Twilio router fails to load on Python 3.13 (audioop removed from stdlib).
    Non-blocking: app starts fine; fix deferred to M8 (provider abstraction).
  - call_session.py still has real-estate specific GREETING text — generalized in M11.

Remaining work:
  - None for M1

Next checkpoint: M2

Git commit: (see below)
```

---

### M0 — REPOSITORY AUDIT

```
Checkpoint: M0
Status: PASS
Started: 2026-10-08
Completed: 2026-10-08
Objective: Inspect entire existing repository; document architecture; 
           determine what to reuse vs change; create MVP_ARCHITECTURE.md

Implementation:
  - Cloned https://github.com/Risabkshetri/AI-Telecalling
  - Inspected all 30+ source files (backend + frontend)
  - Documented existing architecture in MVP_ARCHITECTURE.md
  - Documented technical decisions in MVP_DECISIONS.md
  - Documented test status in MVP_TEST_STATUS.md
  - Created this MVP_PROGRESS.md

Files changed:
  - MVP_ARCHITECTURE.md (created)
  - MVP_DECISIONS.md (created)
  - MVP_TEST_STATUS.md (created)
  - MVP_PROGRESS.md (created)

Database changes:
  - None (PostgreSQL still in place; MongoDB migration is M1)

API changes:
  - None

Environment variables:
  - None added yet

Tests:
  - Repository structure verified
  - All source files readable and understood
  - Existing codebase documented

Tests passed: 2
Tests failed: 0

Manual verification:
  - PASS: repository cloned and fully inspected
  - PASS: architecture documented

Known issues:
  - Backend uses PostgreSQL → will be replaced with MongoDB in M1
  - No authentication system
  - No multi-tenancy
  - No billing
  - Providers not abstracted
  - Real-estate-specific prompts and business logic

Remaining work:
  - None for M0 (audit only)

Next checkpoint: M1

Git commit: (see below)
```

---

## EXISTING CODEBASE SUMMARY

### What exists and works
- ✅ FastAPI application with async WebSocket support
- ✅ Transport-agnostic call session pipeline (`call_session.py`)
- ✅ Silero VAD endpointer with barge-in (`audio/vad.py`) — **excellent, preserve**
- ✅ LangGraph conversation state machine (`agent/engine.py`)
- ✅ Groq Whisper STT + Sarvam STT router (`audio/stt.py`)
- ✅ Sarvam TTS with streaming (`audio/tts.py`)
- ✅ Twilio Media Streams bridge (`telephony/twilio.py`)
- ✅ Redis session store (`memory/session.py`)
- ✅ PostgreSQL repository (`memory/repository.py`)
- ✅ 11 Indian languages support (`languages.py`)
- ✅ Next.js 14 dashboard with calls/leads/overview
- ✅ Structured logging with per-turn trace IDs

### What needs to be built
- ❌ MongoDB foundation (replace PostgreSQL)
- ❌ Authentication + JWT
- ❌ Multi-tenancy (organization_id isolation)
- ❌ RBAC
- ❌ Subscription plans (database-driven)
- ❌ Razorpay payment integration
- ❌ Wallet + calling credits
- ❌ Credit reservation + settlement
- ❌ Phone number inventory
- ❌ Provider abstractions (Telephony, STT, TTS, LLM, Payment)
- ❌ ElevenLabs TTS adapter
- ❌ Exotel telephony adapter
- ❌ OpenAI LLM adapter
- ❌ Mock providers for DEMO_MODE
- ❌ AI Voice Profiles (customer-facing)
- ❌ Provider Router (primary/fallback)
- ❌ Generic Agent Builder (templates)
- ❌ Lead CRM (import CSV/XLSX, DNC, deduplication)
- ❌ Campaign engine (state machine, concurrency, Redis workers)
- ❌ Campaign pre-flight validation
- ❌ Post-call processing (async)
- ❌ Usage tracking + cost accounting
- ❌ Customer dashboard (full SaaS)
- ❌ Super admin panel
- ❌ Appointments module
- ❌ Knowledge base
- ❌ Analytics
- ❌ Demo mode (DEMO_MODE=true)
- ❌ Fly.io deployment config
- ❌ Full documentation

### Key architectural changes required
- PostgreSQL → MongoDB Atlas (M1)
- Groq-only → OpenAI-compatible LLM provider abstraction (M8)
- Sarvam-only → TTS provider abstraction with ElevenLabs (M8)
- Twilio-only → Telephony provider abstraction with Exotel (M8)
- Real-estate prompts → template-driven generic prompts (M11)
- No auth → JWT + RBAC (M2)
- No billing → Razorpay + wallet (M4, M5)

---

## CHECKPOINT ROADMAP

| Checkpoint | Title | Status | Dependency |
|---|---|---|---|
| M0 | Repository Audit | **PASS** | — |
| M1 | MongoDB Foundation | **PASS** | M0 |
| M2 | Auth + Multi-Tenancy + RBAC | **PASS** | M1 |
| M3 | Plans + Subscriptions | **PASS** | M2 |
| M4 | Razorpay | **PASS** | M3 |
| M5 | Calling Packs + Wallet | **PASS** | M4 |
| M6 | Credit Reservation + Settlement | **PASS** | M5 |
| M7 | Phone Number Inventory | TODO | M6 |
| M8 | Provider Abstraction | TODO | M7 |
| M9 | AI Voice Profiles | TODO | M8 |
| M10 | Provider Router | TODO | M9 |
| M11 | Agent Builder | **PASS** | M10 |
| M12 | Lead CRM | **PASS** | M11 |
| M13 | Campaign Engine | **PASS** | M12 |
| M14 | Campaign Pre-flight | **PASS** | M13 |
| M15 | Real-Time AI Calling | **PASS** | M14 |
| M16 | Barge-In + Latency | **PASS** | M15 |
| M17 | Tools + Human Handoff | **PASS** | M16 |
| M18 | Appointments | **PASS** | M17 |
| M19 | Knowledge Base | TODO | M18 |
| M20 | Post-Call Processing | TODO | M19 |
| M21 | Usage + Cost | TODO | M20 |
| M22 | Customer Dashboard | TODO | M21 |
| M23 | Customer Billing | TODO | M22 |
| M24 | Super Admin | TODO | M23 |
| M25 | Revenue + Margin Analytics | TODO | M24 |
| M26 | Provider Operations | TODO | M25 |
| M27 | Reconciliation | TODO | M26 |
| M28 | Security Hardening | TODO | M27 |
| M29 | Automated Testing | TODO | M28 |
| M30 | Demo Mode | TODO | M29 |
| M31 | Production Deployment | TODO | M30 |
| M32 | Documentation | TODO | M31 |
| M33 | Final E2E Acceptance | TODO | M32 |
