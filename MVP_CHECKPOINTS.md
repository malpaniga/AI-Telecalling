# MVP_CHECKPOINTS.md

# AI Telecalling SaaS — MVP Checkpoints & Autonomous Execution Contract

This file is the persistent source of truth for implementing the MVP checkpoint-by-checkpoint.

The repository must be completed by executing checkpoints in order:

M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 → M9 → M10 → M11 → M12 → M13 → M14 → M15 → M16 → M17 → M18 → M19 → M20 → M21 → M22 → M23 → M24 → M25 → M26 → M27 → M28 → M29 → M30 → M31 → M32 → M33

---

# 1. PRODUCT PRINCIPLES

## 1.1 Product

Commercial multi-tenant AI Voice Telecalling SaaS.

Customers can:

- Sign up
- Create an organization
- Choose a subscription
- Pay using Razorpay
- Buy calling-credit packs
- Use platform-managed phone numbers
- Create AI agents
- Select customer-facing AI Voice Profiles
- Upload/manage leads
- Create and launch campaigns
- Make AI calls
- Consume calling credits based on actual billable usage
- View calls, outcomes, analytics and billing
- Buy additional credits
- View invoices

Platform owners can:

- Manage organizations
- Manage subscription plans
- Manage calling packs
- Manage subscriptions
- Manage payments
- Manage invoices
- Manage wallets and credits
- Manage phone-number inventory
- Manage AI Voice Profiles
- Manage internal telephony/STT/LLM/TTS providers
- Configure routing and fallback
- Monitor provider health
- Monitor usage
- Monitor provider cost
- Monitor revenue
- Monitor gross profit and margins
- Manage support and audit logs

---

# 2. CUSTOMER VS PLATFORM ABSTRACTION

Customers buy outcomes, not infrastructure.

Customers must see:

- AI Voice Profiles
- AI Agents
- Campaigns
- Leads
- Calling Credits
- Phone Numbers
- Calls
- Analytics
- Billing

Customers must NOT be exposed to:

- Exotel
- Twilio
- Sarvam
- ElevenLabs
- OpenAI
- Gemini
- Deepgram
- Provider API keys
- Provider costs
- Internal provider routes
- Internal fallback configuration

Example customer-facing voice profiles:

- Marathi AI Voice
- Hindi AI Voice
- English AI Voice
- Gujarati AI Voice

The platform internally maps these to provider routes.

---

# 3. TECHNOLOGY RULES

Primary stack:

- Python
- Flask
- MongoDB Atlas
- Redis
- Existing repository architecture
- Existing LangGraph/call engine where useful
- Existing WebSocket/media streaming where useful
- Existing STT/TTS/LLM integrations where useful
- Existing frontend where useful

MongoDB is the persistent source of truth.

Redis is only for:

- Queues
- Locks
- Active call state
- Rate limiting
- Worker coordination
- Short-lived conversation state
- Provider throttling
- Retry scheduling
- Temporary cache

Financial/business records MUST NOT depend on Redis persistence.

---

# 4. MULTI-TENANCY

Every tenant-owned record must have:

`organization_id`

Tenant isolation must be enforced server-side.

Never rely only on frontend filtering.

Roles:

## Platform

- platform_owner
- platform_admin
- support
- billing_admin

## Organization

- organization_owner
- organization_admin
- manager
- agent
- viewer

Cross-organization access must be denied.

---

# 5. PROVIDER ABSTRACTION

Core business logic MUST NOT depend directly on provider names.

Use provider interfaces.

## TelephonyProvider

```python
class TelephonyProvider:
    async def initiate_call(...)
    async def hangup_call(...)
    async def transfer_call(...)
    async def get_call_status(...)
    async def get_recording(...)
    async def stream_audio(...)
    async def handle_webhook(...)
    def get_capabilities(...)
```

Implement:

- Exotel
- Twilio
- Mock

## STTProvider

```python
class STTProvider:
    async def transcribe(...)
    async def stream_transcribe(...)
    async def stop(...)
    async def get_languages(...)
    async def get_models(...)
    async def get_capabilities(...)
    async def estimate_cost(...)
```

Implement:

- Sarvam
- Another replaceable provider
- Mock

## TTSProvider

```python
class TTSProvider:
    async def synthesize(...)
    async def stream(...)
    async def stop(...)
    async def get_voices(...)
    async def get_models(...)
    async def get_languages(...)
    async def estimate_cost(...)
```

Implement:

- ElevenLabs
- Sarvam
- Mock

## LLMProvider

```python
class LLMProvider:
    async def generate(...)
    async def stream(...)
    async def get_models(...)
    async def get_capabilities(...)
    async def estimate_cost(...)
```

Support where practical:

- OpenAI
- OpenAI-compatible providers
- Gemini
- Local/self-hosted
- Mock

## PaymentProvider

```python
class PaymentProvider:
    async def create_order(...)
    async def verify_payment(...)
    async def create_subscription(...)
    async def cancel_subscription(...)
    async def fetch_payment(...)
    async def create_invoice(...)
    async def refund(...)
    async def handle_webhook(...)
```

Implement:

- Razorpay
- Mock

## PhoneNumberProvider

```python
class PhoneNumberProvider:
    async def search_numbers(...)
    async def reserve_number(...)
    async def provision_number(...)
    async def release_number(...)
    async def get_number(...)
```

Implement:

- Exotel
- Twilio
- Mock

Also use abstractions for:

- WhatsApp
- SMS
- Messaging

Avoid core fields such as:

- elevenlabs_voice_id
- exotel_call_sid

Prefer generic fields:

- provider
- provider_resource_id
- provider_metadata

---

# 6. DATABASE COLLECTIONS

Recommended collections:

- organizations
- users
- subscription_plans
- subscriptions
- products
- prices
- calling_packs
- add_ons
- orders
- order_items
- payments
- invoices
- wallets
- wallet_transactions
- credit_lots
- usage_events
- phone_numbers
- phone_number_assignments
- voice_profiles
- voice_profile_versions
- provider_routes
- agents
- agent_versions
- business_templates
- knowledge_bases
- knowledge_documents
- leads
- campaigns
- calls
- transcripts
- appointments
- dnc_entries
- tool_configs
- activities
- provider_configs
- provider_usage
- webhook_events
- analytics_daily
- notifications
- audit_logs

Create appropriate indexes.

Important unique indexes include:

- user email/mobile
- organization wallet
- phone number
- organization + DNC phone
- provider payment ID
- webhook event ID

---

# 7. BILLING PRINCIPLES

Subscription and calling usage are separate.

Subscription controls:

- feature access
- user limits
- agent limits
- campaign limits
- phone-number limits
- concurrency limits
- other configurable entitlements

Calling packs control usage.

Never hard-code pricing.

All prices must be configurable by platform administrators.

Money must use:

- integer paise
- or Decimal

Never use floating-point money calculations.

Invoice numbers must be concurrency-safe.

Example:

`INV-2026-000001`

---

# 8. CALLING CREDIT PRINCIPLES

Recommended internal unit:

`1 credit = 1 billable second`

UI may display approximate minutes.

Credits must use integer arithmetic.

Wallet structure:

```text
available_credits
reserved_credits
```

Ledger is authoritative.

Use credit lots for:

- expiry
- bonuses
- refunds
- promotional credits

If expiry ordering is configured, use earliest-expiry-first.

Every credit movement must have an immutable ledger record.

---

# 9. PAYMENT PRINCIPLES

Backend determines the price from the product/plan/pack ID.

Frontend must NEVER be authoritative for payment amount.

Flow:

```text
Frontend
→ Backend creates order
→ Razorpay Checkout
→ Payment
→ Backend verification
→ Verified webhook
→ Idempotent fulfillment
```

Webhook signatures must be verified.

Webhook events must be stored.

Duplicate webhook delivery must be safe.

Payment success must never grant credits twice.

Reconciliation must detect:

- payment succeeded but credits missing
- credits granted without payment
- duplicate webhook
- invoice mismatch
- wallet mismatch

---

# 10. PHONE NUMBER PRINCIPLES

Platform-managed phone inventory states:

- available
- reserved
- assigned
- suspended
- maintenance
- released

Customers see:

- number
- status
- assigned agent
- rental price

Customers do NOT see provider details.

Assignment must be atomic.

Phone pricing must be configurable:

- monthly rental
- setup fee
- usage
- deposit

---

# 11. AI VOICE PROFILE PRINCIPLES

AI Voice Profile is a customer-facing abstraction.

Example:

```text
Marathi AI Voice
```

Internally it can map to:

```text
Telephony: Exotel
STT: Sarvam
LLM: Provider A
TTS: ElevenLabs
```

Customers never see the internal route.

Agent stores:

```text
voice_profile_id
voice_profile_version
```

It must NOT store provider-specific configuration as the primary business reference.

Voice profiles support:

- draft
- testing
- active
- degraded
- disabled
- retired

Every profile has versions.

Active campaigns pin a specific voice-profile version.

Changing the provider behind a profile must NOT require customer reconfiguration.

---

# 12. BUSINESS TEMPLATES

The engine must remain generic.

Initial templates:

- Generic
- Solar
- Real Estate
- Insurance
- Education
- Home Services
- Automotive

Solar must NOT be hard-coded into the core calling engine.

Business-specific behavior belongs in templates/configuration.

---

# 13. AGENTS

Agent configuration should support:

- business template
- goal
- tone
- knowledge
- qualification schema
- objections
- tools
- transfer rules
- calling rules
- voice profile
- voice profile version
- primary language
- fallback languages

Agent versions must be immutable after publication.

Draft versions may be edited.

Published versions must remain reproducible.

---

# 14. LEADS

Lead fields should support:

- organization_id
- campaign_id
- name
- phone
- email
- status
- custom_fields
- qualification
- score
- language_preference
- attempts
- last_contact
- next_contact
- source
- tags
- timestamps

Import formats:

- CSV
- XLSX
- JSON

Import must support:

- column mapping
- validation
- duplicate detection
- DNC filtering
- error report
- large imports

Target acceptance:

`4000+ leads`

---

# 15. CAMPAIGNS

Campaign configuration:

- agent/version
- voice profile/version
- phone number
- concurrency
- max attempts
- calling hours
- timezone
- retry policy
- lead filter
- status

States:

- draft
- scheduled
- running
- paused
- paused_insufficient_credits
- completed
- cancelled
- failed

Campaign execution uses Redis workers/queues.

Persistent campaign state remains in MongoDB.

Pause/resume/stop must work.

No over-concurrency.

---

# 16. CAMPAIGN PREFLIGHT

Before starting a campaign verify:

- subscription
- entitlements
- credits
- agent
- agent version
- voice profile
- voice profile version
- phone number
- providers/routes
- language support
- calling hours
- DNC
- concurrency

Invalid campaigns MUST NOT start.

---

# 17. REAL-TIME CALL PIPELINE

Target architecture:

```text
Telephony
↓
Audio Stream
↓
VAD
↓
STT
↓
Conversation Engine / LangGraph
↓
LLM
↓
Streaming TTS
↓
Telephony
```

Support barge-in:

```text
Customer speaks
→ detect speech
→ stop TTS
→ clear queued audio
→ process customer speech
```

Conversation states:

- call started
- greeting
- intent
- conversation
- qualification
- objection handling
- action
- appointment
- callback
- transfer
- end

---

# 18. TOOLS

Generic tools include:

- book_appointment
- schedule_callback
- send_whatsapp
- send_sms
- transfer_to_human
- update_lead
- add_note
- get_customer_details
- check_availability

Tool permissions and audit logs are required.

Human handoff should pass:

- lead
- summary
- qualification
- transcript
- recommended action

---

# 19. APPOINTMENTS

Appointments must be generic.

Fields include:

- organization_id
- date
- time
- timezone
- duration
- type
- assigned user
- location
- status
- notes

Solar-specific "site survey" is a template appointment type, not core logic.

---

# 20. DNC / COMPLIANCE

DNC must be organization-scoped.

Opt-out must:

- add the lead/number to DNC
- stop future retries
- be auditable

Calling hours must be configurable.

Store timestamps in UTC.

Apply organization/campaign timezone when enforcing calling windows.

Do not implement:

- caller-ID spoofing
- DND bypass
- filtering bypass

---

# 21. POST-CALL PROCESSING

After a call:

```text
Call ends
↓
Finalize transcript
↓
Generate summary
↓
Qualification
↓
Score
↓
Outcome
↓
Update lead
↓
Update campaign
↓
Usage event
↓
Wallet settlement
↓
Provider cost
↓
Margin
↓
Analytics
```

Post-call processing should be asynchronous where appropriate.

Must be retryable and idempotent.

Usage settlement idempotency key:

`call_id + usage_finalization`

---

# 22. USAGE / COST ACCOUNTING

Track usage for:

- call duration
- STT
- LLM
- TTS
- messaging
- phone number rental

Separate:

- customer charge
- provider cost

Customers never see provider cost.

Platform administrators can see:

- revenue
- provider cost
- gross profit
- gross margin

---

# 23. CUSTOMER DASHBOARD

Customer navigation:

- Dashboard
- AI Agents
- Campaigns
- Leads
- Calls
- Appointments
- Phone Numbers
- Calling Credits
- Analytics
- Knowledge Base
- Team
- Billing
- Settings

Customer must never see internal provider information.

---

# 24. SUPER ADMIN DASHBOARD

Super Admin navigation:

- Dashboard
- Organizations
- Subscriptions
- Calling Packs
- Payments
- Invoices
- Wallets
- Phone Numbers
- Voice Profiles
- Providers
- Usage
- Revenue
- Costs
- Margins
- Support
- Audit Logs
- System Health
- Settings

---

# 25. SECURITY

Required:

- authentication
- RBAC
- tenant isolation
- secret protection
- rate limiting
- webhook verification
- file validation
- audit logs
- no secrets in logs
- no provider secrets in frontend
- safe error messages
- API authorization
- session security

Rate-limit:

- signup
- login
- OTP
- password reset
- payments
- API
- campaign creation
- call initiation
- webhooks where appropriate

---

# 26. DEMO MODE

`DEMO_MODE=true` must allow the application to run without paid external APIs.

Use mock:

- telephony
- STT
- TTS
- LLM
- payments
- phone numbers

Seed:

- Demo organization
- Growth plan
- 2,000 credits
- Marathi AI Voice
- Demo number
- 20 leads
- Demo campaign

---

# 27. ENVIRONMENT

Use `.env.example`.

Potential variables:

```text
APP_ENV
SECRET_KEY
MONGODB_URI
MONGODB_DATABASE
REDIS_URL

RAZORPAY_KEY_ID
RAZORPAY_SECRET
RAZORPAY_WEBHOOK_SECRET

EXOTEL credentials
TWILIO credentials
SARVAM_API_KEY
ELEVENLABS_API_KEY
OPENAI_API_KEY
```

Only configured providers should be required.

---

# 28. DEPLOYMENT

Target:

- Fly.io API/web
- Fly.io worker
- Fly.io Redis
- MongoDB Atlas
- external AI/voice providers
- WebSocket/media streaming
- HTTPS
- provider webhooks

Do NOT deploy MongoDB on Fly.io.

Health checks should cover:

- application
- MongoDB
- Redis
- worker
- providers
- Razorpay

Use structured logs with:

- organization_id
- user_id
- agent_id
- campaign_id
- lead_id
- call_id
- provider
- event
- latency
- error

Never log secrets.

---

# 29. AUTONOMOUS CHECKPOINT EXECUTION CONTRACT

This section is mandatory.

## 29.1 `BEGIN MXX` means COMPLETE THE WHOLE CHECKPOINT

When the user sends:

```text
BEGIN M11
```

the agent has permission to perform ALL work required by M11.

Do NOT interpret it as permission to perform only:

- one file change
- one test
- one component
- one implementation step

The unit of execution is the entire checkpoint.

---

## 29.2 NEVER STOP BECAUSE A TEST IS RED

A failing test is NEVER a reason to return control to the user.

A failing test creates a DEBUG/FIX work item.

Correct loop:

```text
Implement
↓
Run test
↓
Failure
↓
Inspect failure
↓
Identify cause
↓
Implement fix
↓
Run test again
↓
Repeat
↓
Pass
↓
Continue checkpoint
```

Do not stop after reporting:

- "test is red"
- "component is missing"
- "implementation is pending"
- "remaining work exists"

Those are internal work states, not completion states.

---

## 29.3 DO NOT ASK WHETHER TO CONTINUE

During an active checkpoint:

- Do not ask "Should I continue?"
- Do not ask "Do you want me to implement the remaining items?"
- Do not wait for another user message.
- Do not return a partial checkpoint merely because the first implementation step is complete.

Continue autonomously.

---

## 29.4 FINAL RESPONSE RULE

For a successfully completed checkpoint, the final response MUST be:

```text
CHECKPOINT: MXX
STATUS: PASS
```

followed by a concise verification summary.

Do NOT report:

- "MXX is in progress"
- "MXX is partially complete"
- "Remaining:"
- "Next I will..."
- "I implemented the first part..."

if the checkpoint has not actually been completed.

---

## 29.5 GENUINE BLOCKED STATE

Only use:

```text
STATUS: BLOCKED
```

when a genuine external/tool limitation makes further execution impossible.

Examples:

- unavailable external service
- unavailable credentials required for real verification
- environment/tool hard limit
- corrupted repository that cannot be recovered safely
- required user-owned secret/access that cannot be obtained autonomously

Before reporting BLOCKED:

1. Save all valid progress.
2. Update `MVP_PROGRESS.md`.
3. Document the exact blocker.
4. Document the exact unfinished work.
5. Ensure the repository remains in a recoverable state.
6. Do not falsely report PASS.

---

# 30. INTERRUPTION / RESUME CONTRACT

If execution is interrupted because of:

- network failure
- token exhaustion
- tool timeout
- IDE interruption
- process termination
- session interruption

the next command may be:

```text
RESUME
```

or:

```text
RESUME M11
```

The agent must recover state from:

1. `MVP_CHECKPOINTS.md`
2. `MVP_PROGRESS.md`
3. `MVP_TEST_STATUS.md`
4. `MVP_ARCHITECTURE.md`
5. `MVP_DECISIONS.md`
6. `git status`
7. latest git commit
8. existing tests
9. existing implementation

Then:

```text
inspect current state
↓
identify first incomplete requirement
↓
continue implementation
↓
run tests
↓
fix failures
↓
continue
↓
complete checkpoint
↓
commit
↓
verify
```

Do NOT restart completed work unnecessarily.

---

# 31. STANDARD TEST / VERIFICATION / COMMIT PROCESS

Before modifying:

```bash
git status --short
git branch --show-current
git log -1 --oneline
```

Inspect existing project configuration:

```text
pyproject.toml
requirements.txt
requirements-dev.txt
pytest.ini
setup.cfg
tox.ini
Makefile
package.json
```

Use the repository's existing environment.

Typical Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Typical Linux/macOS:

```bash
source .venv/bin/activate
```

Primary test:

```bash
python -m pytest -q
```

If the repository has an official test command, use it instead.

Checkpoint-specific tests MUST be run first.

Create missing tests when required.

Full regression:

```bash
python -m pytest -q
```

Compile/syntax:

```bash
python -m compileall -q .
```

Diff validation:

```bash
git diff --check
```

Inspect:

```bash
git status --short
git diff --stat
git diff
```

If configured:

```bash
ruff check .
black --check .
mypy .
```

Frontend tests/build must also be run when applicable.

Application smoke test must use the repository's actual startup command.

Verify:

- app starts
- MongoDB connection
- Redis connection
- health endpoint
- relevant worker
- relevant WebSocket/media flow where applicable

---

# 32. VERIFICATION ORDER

Always use:

```text
IMPLEMENT
↓
CHECKPOINT TESTS
↓
FIX FAILURES
↓
COMPILE
↓
FULL REGRESSION
↓
FIX REGRESSIONS
↓
FRONTEND TEST/BUILD
↓
SMOKE TEST
↓
git diff --check
↓
REVIEW DIFF
↓
UPDATE DOCUMENTATION
↓
VERIFY EXIT CRITERIA
↓
COMMIT
↓
VERIFY COMMIT
↓
REPORT PASS
```

A checkpoint is NOT PASS until this sequence is completed as applicable.

---

# 33. COMMIT RULE

Each completed checkpoint gets a checkpoint commit.

Format:

```bash
git add <relevant-files>
git commit -m "checkpoint: MXX <short description>"
```

Examples:

```bash
git commit -m "checkpoint: M10 provider routing and failover"
```

```bash
git commit -m "checkpoint: M11 agent builder and business templates"
```

After commit:

```bash
git log -1 --oneline
git status --short
git show --stat --oneline HEAD
git show --name-status HEAD
```

Working tree should be clean unless a documented reason exists.

---

# 34. CHECKPOINT REPORT FORMAT

Every completed checkpoint must report:

```text
CHECKPOINT: MXX
STATUS: PASS

Implementation:
...

Automated Tests:
...

Manual Acceptance:
...

Regression:
...

Compile:
...

Smoke Test:
...

Exit Criteria:
...

Documentation:
...

Git:
...

Working Tree:
CLEAN

Ready for Next Checkpoint:
YES
```

For BLOCKED:

```text
CHECKPOINT: MXX
STATUS: BLOCKED

Blocker:
...

Progress Saved:
YES

Exact Unfinished Work:
...

Recovery Command:
RESUME MXX
```

---

# 35. CHECKPOINTS

## M0 — Repository Audit

Requirements:

- Inspect entire repository.
- Understand current architecture.
- Identify backend/frontend.
- Identify MongoDB usage.
- Identify authentication.
- Identify call engine.
- Identify WebSocket/media streaming.
- Identify STT/TTS/LLM.
- Identify Redis.
- Identify workers.
- Identify leads/campaigns.
- Identify deployment.
- Identify tests.
- Identify environment configuration.
- Document architecture.

Exit criteria:

- Entire repo inspected.
- Current architecture documented.
- Current database documented.
- Current auth documented.
- Current calling flow documented.
- Existing provider integrations documented.
- Redis/workers documented.
- Deployment documented.
- App still starts.
- Existing core functionality remains working.

---

# M1 — MongoDB Foundation

Implement:

- MongoDB configuration
- connection lifecycle
- repository/data-access layer
- indexes
- organizations
- users
- audit logs
- health checks

Acceptance:

- MongoDB connects.
- App starts.
- CRUD works.
- Indexes exist.
- Tests pass.

---

# M2 — Auth + Multi-tenancy + RBAC

Implement:

- signup
- login
- logout
- password reset architecture
- verification architecture
- organization creation
- tenant middleware
- RBAC

Acceptance:

- authentication works
- organization creation works
- tenant isolation works
- cross-organization access is denied
- role restrictions work

---

# M3 — Plans + Entitlements

Implement:

- subscription plans
- subscriptions
- configurable limits
- feature entitlements

Plans must be database-driven.

Changing plan configuration must change behavior without code modification.

---

# M4 — Razorpay + Billing

Implement:

- PaymentProvider
- Razorpay adapter
- Mock payment adapter
- orders
- order items
- payments
- subscriptions
- invoices
- webhook handling
- refunds

Acceptance:

- server-side pricing
- payment verification
- webhook HMAC
- webhook idempotency
- duplicate webhook safety
- refund support
- payment failure handling

Tests:

- success
- failure
- invalid signature
- duplicate webhook
- refund

---

# M5 — Calling Packs + Wallet

Implement:

- calling packs
- wallet
- immutable wallet ledger
- credit lots
- expiry
- bonus credits
- admin adjustment
- purchase fulfillment

Acceptance:

Purchasing a 2,000-credit pack results in:

```text
wallet available = 2000
ledger = +2000
credit lot = 2000
```

Every credit movement has an immutable ledger record.

---

# M6 — Credit Reservation + Settlement

Implement:

- reserve
- release
- settle
- refunds
- insufficient balance handling
- concurrency safety
- idempotency

Acceptance:

10 concurrent calls cannot:

- double-spend
- create negative balance
- lose credits

Settlement must be idempotent.

---

# M7 — Phone Number Inventory

Implement:

- phone number inventory
- provider abstraction
- reservation
- assignment
- release
- suspension
- maintenance

Acceptance:

Two concurrent reservations for the same number cannot both succeed.

---

# M8 — Provider Abstraction

Implement:

- TelephonyProvider
- STTProvider
- TTSProvider
- LLMProvider
- PaymentProvider
- PhoneNumberProvider
- Messaging provider
- provider registry
- capability discovery
- mock providers

Acceptance:

The same workflow works with mocks.

Core logic must not branch on provider names.

---

# M9 — AI Voice Profiles

Implement:

- voice profiles
- voice profile versions
- customer-safe API
- internal route configuration
- languages
- statuses
- versioning

Customer API must return only appropriate product-level information.

It must NOT reveal:

- provider
- model
- API key
- provider cost
- route

Acceptance:

Customer sees:

```text
Marathi AI Voice
```

not:

```text
Sarvam STT + ElevenLabs TTS + Provider X
```

---

# M10 — Provider Router + Failover

Implement:

- ProviderRouter
- primary routes
- fallback routes
- capability validation
- language validation
- provider health validation
- failover
- failover logs
- route management

Acceptance:

Changing the internal provider for a voice profile requires no customer reconfiguration.

Provider failure must trigger valid fallback when configured.

---

# M11 — Agent Builder + Business Templates

Implement:

- agents
- agent versions
- immutable published versions
- business templates
- Generic
- Solar
- Real Estate
- Insurance
- Education
- Home Services
- Automotive
- goals
- tone
- knowledge configuration
- qualification schema
- objections
- tools
- transfer rules
- calling rules
- voice profile/version
- language configuration

Acceptance:

- All seven templates exist.
- Agent creation works.
- Agent versions are immutable after publication.
- Tenant isolation works.
- Generic engine supports all templates.
- Solar is not hard-coded into core calling logic.
- Customer sees voice profile, not provider configuration.

Required acceptance tests include:

- all template availability
- agent CRUD
- versioning
- immutable published versions
- tenant isolation
- RBAC
- voice profile linkage
- template-driven behavior
- invalid configuration handling

---

# M12 — Lead CRM + Import

Implement:

- lead CRUD
- CSV import
- XLSX import
- JSON import
- column mapping
- validation
- duplicates
- DNC filtering
- import error report
- bulk processing

Acceptance:

- 4,000+ leads can be imported.
- Duplicate detection works.
- Invalid records are reported.
- DNC records are skipped.
- Tenant isolation works.

---

# M13 — Campaign Engine

Implement:

- campaigns
- states
- agent/version
- voice profile/version
- phone number
- lead filters
- concurrency
- retry policy
- max attempts
- calling hours
- timezone
- worker queue
- pause
- resume
- stop

Acceptance:

- campaigns execute
- concurrency is enforced
- retry rules work
- pause works
- resume works
- stop works
- persistent state survives worker restart

---

# M14 — Campaign Preflight + Compliance

Before campaign launch verify:

- subscription
- entitlements
- credits
- agent
- voice profile
- phone number
- providers
- language
- calling hours
- DNC
- concurrency

Acceptance:

Invalid campaigns cannot start.

---

# M15 — Real-Time AI Calling

Implement end-to-end:

```text
Telephony
→ audio
→ VAD
→ STT
→ conversation engine
→ LLM
→ TTS
→ audio
→ telephony
```

Acceptance:

- call initiation
- audio streaming
- speech recognition
- LLM response
- TTS playback
- call completion
- call record
- error handling

Mock provider tests must exist.

---

# M16 — Barge-in + Latency

Implement:

- speech interruption
- TTS stop
- audio queue clear
- streaming
- latency metrics

Acceptance:

When the customer interrupts:

- TTS stops
- queued audio is cleared
- speech is processed
- next response is generated

---

# M17 — Tools + Human Handoff

Implement:

- appointment booking
- callback scheduling
- WhatsApp
- SMS
- transfer
- lead update
- notes
- customer details
- availability

Implement:

- tool registry
- tool permissions
- tool audit logs

Human handoff must pass context.

---

# M18 — Appointments + Follow-up

Implement:

- appointments
- callbacks
- timezone handling
- create/update/cancel
- dashboard

Acceptance:

AI can schedule a generic appointment and it appears in the dashboard.

---

# M19 — Knowledge Base

Implement:

- knowledge bases
- documents
- versions
- tenant isolation
- agent knowledge configuration

Acceptance:

AI uses configured knowledge.

---

# M20 — Post-call Processing

Implement:

- transcript
- summary
- qualification
- score
- outcome
- lead update
- campaign update
- analytics update
- usage event
- wallet settlement
- provider cost

Must be:

- asynchronous where appropriate
- retryable
- idempotent

---

# M21 — Usage + Cost Accounting

Implement:

- usage events
- customer charge
- provider cost
- margin

Track:

- telephony
- STT
- LLM
- TTS
- messaging
- phone rental

Acceptance:

Historical financial state can be reconstructed from records.

---

# M22 — Customer Dashboard

Complete customer UI:

- Dashboard
- AI Agents
- Campaigns
- Leads
- Calls
- Appointments
- Phone Numbers
- Calling Credits
- Analytics
- Knowledge Base
- Team
- Billing
- Settings

Tenant-safe.

---

# M23 — Customer Billing UI

Implement:

- current plan
- renewal
- payment history
- invoices
- calling packs
- upgrade
- downgrade
- cancellation
- auto-top-up if supported

Customers must not see provider costs.

---

# M24 — Super Admin

Implement complete platform administration:

- organizations
- plans
- packs
- subscriptions
- payments
- invoices
- credits
- phone numbers
- voice profiles
- providers
- routes
- calls
- usage
- costs
- margins
- audit logs

---

# M25 — Revenue + Margin Analytics

Implement:

- MRR
- ARR estimate
- new MRR
- expansion MRR
- churn MRR
- ARPU
- subscription revenue
- calling revenue
- phone revenue
- add-on revenue
- provider costs
- gross profit
- gross margin
- customer profitability
- plan profitability
- voice profile profitability
- provider profitability

Reconcile with billing and usage.

---

# M26 — Provider Operations

Implement:

- provider health
- latency
- error rate
- success rate
- usage
- provider cost
- voice profile health
- customer-neutral errors
- route switching

Provider changes must not require customer reconfiguration.

---

# M27 — Reconciliation

Implement reconciliation for:

- payment vs credits
- credits vs payment
- duplicate webhook
- invoice
- wallet
- usage
- provider cost

Acceptance:

Known mismatches are detected.

---

# M28 — Security Hardening

Perform security review.

Check:

- authentication
- authorization
- tenant isolation
- secret handling
- injection
- file uploads
- webhooks
- rate limiting
- API access
- session security
- audit logs
- sensitive logging

Exit:

No known critical/high severity issues.

---

# M29 — Automated Testing

Complete automated tests across:

- auth
- tenancy
- RBAC
- plans
- subscriptions
- payments
- Razorpay
- wallet
- credit lots
- reservation
- settlement
- phone numbers
- provider registry
- voice profiles
- routing
- agents
- templates
- leads
- campaigns
- compliance
- conversation engine
- tools
- handoff
- appointments
- knowledge
- post-call processing
- usage
- billing
- admin
- analytics
- reconciliation

No known critical regression.

---

# M30 — Demo Mode

Verify:

```text
DEMO_MODE=true
```

works without paid external APIs.

Verify seeded demo data.

Verify complete demo customer workflow.

Verify complete demo admin workflow.

---

# M31 — Production Deployment

Deploy:

- API/frontend
- workers
- Redis
- MongoDB Atlas
- WebSocket/media
- webhooks
- HTTPS

Verify:

- health checks
- logs
- secrets
- graceful shutdown
- worker recovery
- Redis recovery
- MongoDB connectivity

---

# M32 — Documentation

Complete documentation for:

- architecture
- local setup
- environment variables
- database
- Redis
- providers
- provider adapters
- voice profiles
- agent builder
- templates
- leads
- campaigns
- billing
- wallet
- usage
- deployment
- troubleshooting
- testing
- demo mode

A fresh developer must be able to:

1. Clone.
2. Configure.
3. Run.
4. Test.
5. Seed.
6. Add a provider.
7. Create a voice profile.

---

# M33 — Final E2E Acceptance

Run complete end-to-end tests.

Customer:

```text
Signup
→ Organization
→ Plan
→ Payment
→ Calling Pack
→ Credits
→ Voice Profile
→ Agent
→ Phone Number
→ Leads
→ Campaign
→ Calls
→ AI conversation
→ Outcome
→ Usage
→ Wallet settlement
→ Analytics
→ Invoice
```

Admin:

```text
Login
→ Organization
→ Plans
→ Packs
→ Payments
→ Wallets
→ Numbers
→ Voice Profiles
→ Providers
→ Usage
→ Costs
→ Revenue
→ Margin
→ Audit
```

Also verify:

- provider switching
- failover
- tenant isolation
- DNC
- insufficient credits
- duplicate webhooks
- idempotency
- privacy
- security

Final result:

```text
CHECKPOINT: M33
STATUS: PASS
```

---

# 36. DOCUMENTATION FILES MAINTAINED DURING EXECUTION

The implementation agent must maintain:

## MVP_PROGRESS.md

Track:

- current checkpoint
- status
- completed work
- current task
- test status
- blockers
- last verified state
- commit

## MVP_TEST_STATUS.md

Track:

- test suites
- tests added
- tests passed
- tests failed
- regressions
- smoke tests
- verification date/state

## MVP_ARCHITECTURE.md

Update whenever architecture changes.

## MVP_DECISIONS.md

Record significant architectural/product decisions.

---

# 37. MANDATORY EXIT RULE

A checkpoint is complete only when:

```text
IMPLEMENTATION
+
AUTOMATED TESTS
+
MANUAL ACCEPTANCE
+
REGRESSION
+
COMPILE/SYNTAX
+
SMOKE TEST
+
DOCUMENTATION
+
EXIT CRITERIA
+
COMMIT
+
COMMIT VERIFICATION
=
PASS
```

If any mandatory item fails:

```text
STATUS = FAIL
```

or, if execution cannot continue because of a genuine external limitation:

```text
STATUS = BLOCKED
```

Never falsely report PASS.

---

# 38. MOST IMPORTANT EXECUTION RULE

The checkpoint is the unit of work.

NOT:

```text
one test
one file
one class
one endpoint
one component
```

Instead:

```text
BEGIN MXX
=
complete the entire MXX checkpoint
```

The agent must continue autonomously until:

```text
PASS
```

or a genuine:

```text
BLOCKED
```

state is reached.

A failing test means:

```text
FIX IT
```

not:

```text
STOP
```

A missing implementation means:

```text
IMPLEMENT IT
```

not:

```text
REPORT IT
```

A partial result means:

```text
CONTINUE
```

not:

```text
RETURN CONTROL
```

---

# 39. STANDARD COMMANDS

Start a checkpoint:

```text
BEGIN M0
```

Continue:

```text
BEGIN M11
```

Resume after interruption:

```text
RESUME
```

Resume a specific checkpoint:

```text
RESUME M11
```

The agent must read this file and the persistent progress files before acting.
