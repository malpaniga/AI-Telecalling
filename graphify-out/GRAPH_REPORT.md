# Graph Report - saas  (2026-10-26)

## Corpus Check
- 343 files · ~257,258 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5351 nodes · 11626 edges · 263 communities (224 shown, 39 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 752 edges (avg confidence: 0.58)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `335de7f1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AppointmentRepository
- CloudProviderRuntime
- WalletService
- MVP_CHECKPOINTS.md
- Call
- card.tsx
- repository.py
- dashboard.py
- test_m42_cloud_providers.py
- CurrentUser
- get_db
- FastAPI
- test_m15_calls.py
- spinner.tsx
- v1/__init__.py
- devDependencies
- CreditService
- PaymentService
- test_m26_provider_ops.py
- api.ts
- PhoneNumberProvider
- test_m5_wallet.py
- test_m42_runtime_providers.py
- appointments.py
- TTSEngine
- agents.py
- test_m33_e2e_acceptance.py
- TestAgentModal.tsx
- SessionStore
- subscriptions.py
- get_redis
- billing_portal.py
- test_m2_auth_rbac.py
- organizations.py
- run
- run
- LatencyMetrics
- TestCallPipelinePreserved
- TestSuperAdmin
- LeadService
- RazorpayProvider
- PreflightService
- run
- TestFlyToml
- UsageService
- CampaignService
- KnowledgeService
- dependencies
- TestPostCallService
- test_m17_tools_handoff.py
- TestCustomerBillingPortal
- Backend API Inventory
- HTTPException
- compilerOptions
- ReconciliationService
- GoogleCloudSTTProvider
- core/auth.py
- ModelDirectoryService
- TelephonyProvider
- seed_demo_numbers
- TestAnalyticsService
- LLMProvider
- ElevenLabsTTSProviderV2
- payment_service.py
- backend/telephony/vobiz.py
- AI Telecalling SaaS — Architecture Reference
- PhoneNumberRepository
- TestDeveloperGuide
- AI Telecalling SaaS — Technical Decisions Log
- AI Telecalling SaaS — Test Status
- backend/telephony/twilio.py
- AnalyticsService
- SubscriptionPlanRepository
- test_m8_provider_abstraction.py
- TestPreflightChecks
- Issues Log — post-Sarvam call testing (2026-07)
- VADEndpointer
- CallSession
- LeadRepository
- UserRepository
- StructuredInstructionEditor
- test_m4_payment.py
- TestDemoSeedService
- run
- build_demo_registry
- SubscriptionRepository
- BaseRepository
- phone_number_repo.py
- SecurityAuditService
- AppointmentService
- PhoneNumberService
- VobizTelephonyProvider
- DNCRepository
- OrderRepository
- run
- CallRepository
- Real Estate Voice Agent — Execution Plan
- GroqLLMProvider
- VoiceProfileVersionRepository
- providers/base.py
- run
- new_id
- .test_llm
- TestLeadsHTTP
- analytics.py
- run
- LLMClient
- GeminiLLMProvider
- VoiceProfileService
- TestAppointmentsHTTP
- CallEventBroadcaster
- OrganizationRepository
- seed_default_plans
- TestPhoneNumberHTTP
- TestDeploymentModulesImportable
- call_session.py
- BrowserTransport
- UsageEvent
- UUID
- TestCampaignHTTP
- TranscriptRepository
- TTSProvider
- PricingSyncService
- run
- API-to-UI Mapping — Super Admin Dashboard
- PostCallService
- TestReconciliationChecks
- package.json
- test_m12_leads.py
- TestAgentHTTP
- Detailed Data Model & API Changes
- test_m16_barge_in_latency.py
- run
- TestCreditReserve
- test_m27_reconciliation.py
- AI Telecalling SaaS — Developer Guide
- Getting Started — Real Estate Voice Agent
- ModelSetupWizard.tsx
- PhoneNumber
- TestBillingHTTP
- test_test_agent.py
- SKIP
- _make_mock_redis
- TestCallsHTTP
- MockPaymentProvider
- Order
- AI Telecalling SaaS
- CHECKPOINT HISTORY
- Review Focus
- Settings
- AgentRepository
- UsageEventRepository
- AuditLogRepository
- ReconciliationResult
- run.py
- Campaign
- SubscriptionService
- AI Telecalling SaaS — Development Progress
- Admin UI Implementation Plan — M40 FEAT-005A
- TwilioProvider
- TestReconciliationHTTP
- db.py
- CampaignWorker
- _catalogue_to_dict
- AgentService
- CredentialStore
- TestE2EHappyPath
- TestMVPValidation
- TestAuthEndpoints
- AgentVersionRepository
- CallService
- test_m20_post_call.py
- TestCreditHTTP
- SarvamAgentStudioPage
- reconciliation_report
- AdminPhoneNumbersPage
- test_m6_credit_reservation.py
- TestConcurrentReservations
- _exists
- TestEnvExampleCompleteness
- TestGitignore
- Appointment
- SarvamTTSProvider
- TestPreflightHTTP
- test_m14_preflight.py
- CampaignRepository
- _get_mock_db
- normalize_phone
- TestVobizPhoneNumbers
- run
- TestModels
- test_m32_documentation.py
- _read
- date-fns
- react
- 2026-10-23-vobiz-phone-provider/progress.md
- tailwind-merge
- TestMVPProgress
- TestReadme
- Provider Configuration
- (auth)/layout.tsx
- 5. PROVIDER ABSTRACTION
- TestAnalyticsHTTP
- TestEnvExample
- @types/react-dom
- test_m13_campaigns.py
- ui.tsx
- 29. AUTONOMOUS CHECKPOINT EXECUTION CONTRACT
- M41 Implementation Plan — AI Models Directory and One-Click Provider Setup
- Transport
- Deployment (Fly.io)
- Local Development
- Testing
- 36. DOCUMENTATION FILES MAINTAINED DURING EXECUTION
- test_m1_mongodb.py
- button.tsx
- Adding a New Provider
- Installation
- nav.tsx
- PaymentRepository
- TestCreditConservation
- 4. MULTI-TENANCY
- rules/graphify.md
- workflows/graphify.md
- next.config.mjs
- next-env.d.ts
- tailwind.config.ts
- 1. PRODUCT PRINCIPLES
- 35. CHECKPOINTS
- calls.py
- TestDemoHTTP
- Global Constraints
- _slugify
- formatDateTime
- Review Focus
- TestLargeImport
- Design: Agent Multi-KB Selector and Grounded Response Injection
- .from_mongo
- TestDockerfile
- progress.md

## God Nodes (most connected - your core abstractions)
1. `get_db()` - 249 edges
2. `CurrentUser` - 215 edges
3. `new_id()` - 185 edges
4. `utcnow()` - 135 edges
5. `WalletService` - 68 edges
6. `SubscriptionService` - 67 edges
7. `BaseRepository` - 65 edges
8. `TimestampedModel` - 64 edges
9. `CampaignService` - 56 edges
10. `LeadRepository` - 53 edges

## Surprising Connections (you probably didn't know these)
- `ConversationEngine` --uses--> `LLMClient`  [INFERRED]
  backend/agent/engine.py → backend/agent/llm.py
- `ConversationEngine` --uses--> `ConversationState`  [INFERRED]
  backend/agent/engine.py → backend/agent/state.py
- `CallSession` --uses--> `ConversationEngine`  [INFERRED]
  backend/call_session.py → backend/agent/engine.py
- `lifespan()` --uses--> `ConversationEngine`  [INFERRED]
  backend/main.py → backend/agent/engine.py
- `ws_call()` --uses--> `ConversationEngine`  [INFERRED]
  backend/main.py → backend/agent/engine.py

## Import Cycles
- None detected.

## Communities (263 total, 39 thin omitted)

### Community 0 - "AppointmentRepository"
Cohesion: 0.19
Nodes (6): AppointmentRepository, Appointment, datetime, Upcoming scheduled/confirmed appointments., Mark existing as rescheduled and create a new one., TestAppointmentRepository

### Community 1 - "CloudProviderRuntime"
Cohesion: 0.22
Nodes (12): CloudProviderRuntime, _llm_options(), Any, ProviderConfiguration, Build cloud AI providers from active encrypted admin configurations. This is…, Loads active provider configurations without exposing their credentials., Return the tested active cloud provider for ``capability``. Credentials are…, Build the three configured cloud components used by a live call. (+4 more)

### Community 2 - "WalletService"
Cohesion: 0.09
Nodes (32): AdjustRequest, admin_adjust_credits(), admin_create_pack(), admin_get_wallet(), admin_grant_bonus(), admin_run_expiry(), admin_update_pack(), BonusRequest (+24 more)

### Community 3 - "MVP_CHECKPOINTS.md"
Cohesion: 0.03
Nodes (67): 10. PHONE NUMBER PRINCIPLES, 11. AI VOICE PROFILE PRINCIPLES, 12. BUSINESS TEMPLATES, 13. AGENTS, 14. LEADS, 15. CAMPAIGNS, 16. CAMPAIGN PREFLIGHT, 17. REAL-TIME CALL PIPELINE (+59 more)

### Community 4 - "Call"
Cohesion: 0.13
Nodes (12): Call, An outbound AI call record., _analyze_call(), _compute_score(), _derive_outcome(), _generate_summary(), Derive qualification, score, outcome, and summary from call state., Simple slot-based scoring. 15 pts per filled slot, bonuses for intent. (+4 more)

### Community 5 - "card.tsx"
Cohesion: 0.08
Nodes (35): AdminAnalyticsPage(), DailyEntry, MRRData, MRRMovement, PERIOD_OPTIONS, RevenueData, AdminCallingPacksPage(), AdminDashboardPage() (+27 more)

### Community 6 - "repository.py"
Cohesion: 0.10
Nodes (27): call_outcome(), lead_status(), Lead scoring: a simple, explainable 0-100 heuristic. Each filled qualification…, Map conversation state to a CRM status., score_lead(), call_detail(), CallDetail, CallRow (+19 more)

### Community 7 - "dashboard.py"
Cohesion: 0.06
Nodes (34): dashboard(), dashboard_analytics(), dashboard_appointments(), dashboard_calls(), dashboard_campaigns(), dashboard_credits(), dashboard_leads(), _get_analytics() (+26 more)

### Community 8 - "test_m42_cloud_providers.py"
Cohesion: 0.05
Nodes (48): M42 Cloud AI Providers — contract tests with mocked HTTP. All tests use…, [mock] 401 error does not expose the API key in the exception message., [mock] 429 rate limit error produces clean message without key., [mock] Dynamic list_available_models returns models and includes supported ones., [mock] GeminiLLMProvider.generate returns text from Gemini API response., [mock] System messages are passed via GenerateContentConfig, not contents., [mock] Auth error never exposes API key., [mock] Empty Gemini response raises ValueError. (+40 more)

### Community 9 - "CurrentUser"
Cohesion: 0.06
Nodes (62): demo_status(), get, post, Allow if DEMO_MODE=true OR caller is platform admin., Check demo mode status and seeding state., Seed the demo environment. Pass force=true to re-seed., _require_demo_or_admin(), seed_demo() (+54 more)

### Community 10 - "get_db"
Cohesion: 0.06
Nodes (60): admin_adjust_wallet(), admin_costs(), admin_dashboard(), admin_margins(), admin_revenue(), admin_usage(), _date_match(), get_org_wallet() (+52 more)

### Community 11 - "FastAPI"
Cohesion: 0.16
Nodes (4): create_token_pair(), M24 tests — Super Admin. Tests: 1. All admin endpoints require platform role…, run(), FastAPI

### Community 12 - "test_m15_calls.py"
Cohesion: 0.16
Nodes (6): _fund_org(), _get_mock_db(), _make_redis(), M15 tests — Real-Time AI Calling infrastructure. Tests: 1. Call model — valid…, run(), TestCallService

### Community 13 - "spinner.tsx"
Cohesion: 0.10
Nodes (49): AuditLog, Tab, Tab, AgentItem, OrgItem, Stats, Tab, LANGUAGE_OPTIONS (+41 more)

### Community 14 - "v1/__init__.py"
Cohesion: 0.05
Nodes (46): BaseModel, field_validator, Credit reservation/settlement API — internal call billing endpoints. These are…, ReleaseRequest, ReserveRequest, SettleRequest, API v1 router — aggregates all v1 sub-routers., OverrideRateRequest (+38 more)

### Community 15 - "devDependencies"
Cohesion: 0.12
Nodes (17): autoprefixer, eslint, eslint-config-next, devDependencies, autoprefixer, eslint, eslint-config-next, postcss (+9 more)

### Community 16 - "CreditService"
Cohesion: 0.03
Nodes (42): CallingPack, CreditLot, field_validator, Wallet, credit ledger, credit lots, and calling pack models. KEY RULES: - 1…, Immutable ledger record. Never updated after creation., A batch of credits from a single purchase or grant. Consumed FIFO by billing.…, A calling credit pack offered for purchase., Base + bonus credits. (+34 more)

### Community 17 - "PaymentService"
Cohesion: 0.07
Nodes (36): create_subscription_order(), CreateSubscriptionOrderRequest, get_invoice(), _invoice_response(), list_invoices(), list_orders(), list_payments(), _order_response() (+28 more)

### Community 18 - "test_m26_provider_ops.py"
Cohesion: 0.05
Nodes (25): platform_latency(), provider_health(), provider_metrics(), get, Health summary across all providers., Per-provider metrics: success rate, latency, cost, call count., Platform-wide call latency statistics., Health status of active voice profiles and their provider routes. (+17 more)

### Community 19 - "api.ts"
Cohesion: 0.08
Nodes (37): SignupPage(), handleSubmit(), AuthAction, AuthContext, AuthContextValue, AuthProvider(), authReducer(), AuthState (+29 more)

### Community 21 - "test_m5_wallet.py"
Cohesion: 0.06
Nodes (18): CallingPackRepository, CallingPack, _get_mock_db(), SKIP, M5 tests — Calling Packs + Wallet. Tests: 1. CallingPack model — integer…, Buy 2000 credits → wallet=2000, ledger=+2000, lot=2000, 2000 base + 200 bonus = 2200 total credits granted, Every credit movement requires an immutable WalletTransaction. (+10 more)

### Community 22 - "test_m42_runtime_providers.py"
Cohesion: 0.31
Nodes (8): M42 runtime wiring tests. The production change these tests protect: active…, A rotated credential must not be selected over the current active one., A corrupt/manual DB edit cannot route inference to Ollama or another local…, Successful historical testing must not bypass cloud-only activation policy., run(), test_activation_rejects_local_provider_after_successful_test_record(), test_runtime_loads_active_gemini_from_encrypted_configuration(), test_runtime_rejects_local_provider_even_if_database_marks_it_active()

### Community 23 - "appointments.py"
Cohesion: 0.19
Nodes (24): appointment_summary(), _appt_response(), cancel_appointment(), CancelRequest, complete_appointment(), CompleteRequest, confirm_appointment(), create_appointment() (+16 more)

### Community 24 - "TTSEngine"
Cohesion: 0.07
Nodes (25): AI4BharatTTSEngine, get_tts_engine(), IndicF5Engine, OllamaTTSEngine, OrpheusEngine, pcm_to_wav(), PiperEngine, ABC (+17 more)

### Community 25 - "agents.py"
Cohesion: 0.14
Nodes (30): _agent_response(), create_agent(), create_version(), CreateAgentRequest, CreateVersionRequest, delete_agent(), get_agent(), get_pipeline_status() (+22 more)

### Community 26 - "test_m33_e2e_acceptance.py"
Cohesion: 0.10
Nodes (16): _get_mock_db(), _make_redis(), SKIP, M33 tests — Final End-to-End Acceptance. Tests the complete SaaS workflow as…, Change voice profile provider route — campaign unaffected., Active campaign pins a version_id — changing routes creates new version., Org A data completely invisible to Org B end-to-end., run() (+8 more)

### Community 27 - "TestAgentModal.tsx"
Cohesion: 0.07
Nodes (28): AdminModelsPage(), AdminGuard(), PLATFORM_ROLES, LoginPage(), handleSubmit(), AuthGuard(), SettingsPage(), ADMIN_LINKS (+20 more)

### Community 28 - "SessionStore"
Cohesion: 0.08
Nodes (25): _decide_stage(), TypedDict, The conversation engine: a LangGraph state machine that drives the call. Per…, Advance the conversation by one user turn. Updates `state` in place (stage,…, Ephemeral state passed through the graph for a single turn., Pure transition logic. Order matters: end > objection > booking > qualify., Extract slots + output variables + intent flags from the latest user message., _smoke_test() (+17 more)

### Community 29 - "subscriptions.py"
Cohesion: 0.09
Nodes (34): admin_activate_subscription(), admin_create_plan(), admin_list_plans(), admin_list_subscriptions(), admin_update_plan(), AdminActivateRequest, cancel_my_subscription(), change_my_plan() (+26 more)

### Community 30 - "get_redis"
Cohesion: 0.13
Nodes (18): _check_rate_limit(), _client_ip(), Request, rate_limit_api(), rate_limit_auth(), rate_limit_billing(), rate_limit_import(), Rate limiting via Redis sliding-window counters. Per-IP and per-user limits to… (+10 more)

### Community 31 - "billing_portal.py"
Cohesion: 0.09
Nodes (37): billing_overview(), buy_calling_pack(), cancel_subscription(), CancelRequest, _days_remaining(), get_invoice(), get_subscription(), _invoice_response() (+29 more)

### Community 32 - "test_m2_auth_rbac.py"
Cohesion: 0.17
Nodes (7): assert_org_access(), _org_level(), Raise 403 if `user` does not belong to `document_org_id`. Platform users with…, _get_test_app(), M2 tests — Auth + Multi-Tenancy + RBAC. Tests: 1. JWT token creation / decoding…, Build a test FastAPI app with in-memory MongoDB., TestRBACPermissions

### Community 33 - "organizations.py"
Cohesion: 0.23
Nodes (12): get_organization(), list_organizations(), OrgCreateRequest, OrgUpdateRequest, BaseModel, get, Organization, patch (+4 more)

### Community 34 - "run"
Cohesion: 0.09
Nodes (11): _get_mock_db(), SKIP, M11 tests — Agent Builder. Tests: 1. BusinessTemplate — 7 templates seeded,…, Org A cannot see Org B agents., Once published, a version cannot be modified., Solar template is configuration, not code. No if/else in service., run(), _seed() (+3 more)

### Community 35 - "run"
Cohesion: 0.06
Nodes (13): _get_mock_db(), SKIP, transfer_to_human must not contain business-specific logic., Tool implementations must not contain business-specific branches (if/else on…, run(), TestAddNote, TestBookAppointment, TestHandoffService (+5 more)

### Community 36 - "LatencyMetrics"
Cohesion: 0.16
Nodes (5): _grade_latency(), LatencyMetrics, Latency metrics service. Records per-turn latency observations and provides…, In-memory latency accumulator for a single call., TestLatencyMetrics

### Community 37 - "TestCallPipelinePreserved"
Cohesion: 0.07
Nodes (16): FasterWhisperSTT, Speech-to-text via Groq Whisper. Sprint 1 does non-streaming transcription: the…, Routes each utterance to the best STT: Sarvam Saaras for Indian languages…, Stub for faster-whisper local runtime. Status: experimental. Raises…, Return (max no_speech_prob, min avg_logprob) across segments. Handles both…, Sarvam Saaras v3 speech-to-text — Indic-tuned, code-mixing aware.…, SarvamSTT, _segment_confidence() (+8 more)

### Community 38 - "TestSuperAdmin"
Cohesion: 0.12
Nodes (3): SKIP, Customer receives 403 on all admin endpoints., TestSuperAdmin

### Community 39 - "LeadService"
Cohesion: 0.15
Nodes (24): add_to_dnc(), create_lead(), CreateLeadRequest, delete_lead(), DNCAddRequest, get_lead(), import_leads(), _lead_response() (+16 more)

### Community 40 - "RazorpayProvider"
Cohesion: 0.14
Nodes (6): Verify Razorpay webhook signature. Signature = HMAC-SHA256(body,…, Route verified webhook event to appropriate handler., Razorpay v1 payment provider., Create a Razorpay order. Amount is in PAISE (integer). Returns:…, Verify Razorpay payment signature. Signature = HMAC-SHA256(order_id + "|" +…, RazorpayProvider

### Community 41 - "PreflightService"
Cohesion: 0.14
Nodes (11): PreflightCheck, PreflightResult, PreflightService, Any, AsyncIOMotorDatabase, Campaign, Campaign pre-flight validation service. Before a campaign starts, ALL of these…, Run all pre-flight checks for a campaign. Returns PreflightResult with all… (+3 more)

### Community 42 - "run"
Cohesion: 0.11
Nodes (8): SKIP, draft → running → paused → running → completed, Org B cannot start Org A's campaign., Never exceed max_concurrent_calls., 10 concurrent acquire attempts with max=5: exactly 5 succeed., run(), TestCampaignStateMachine, TestConcurrencyGate

### Community 44 - "UsageService"
Cohesion: 0.09
Nodes (28): admin_usage_summary(), list_usage_events(), provider_aggregates(), provider_breakdown(), BaseModel, datetime, get, post (+20 more)

### Community 45 - "CampaignService"
Cohesion: 0.13
Nodes (9): CampaignService, Campaign, datetime, Transition draft/scheduled → running. Runs pre-flight validation first., Mark campaign as completed (all leads processed)., Mark campaign as failed (unrecoverable error)., Check whether a new call can start for this campaign. Returns {allowed, reason,…, Atomically increment active call count. Returns True if slot acquired (count ≤… (+1 more)

### Community 46 - "KnowledgeService"
Cohesion: 0.08
Nodes (37): add_document(), associate_agent(), create_knowledge_base(), CreateDocumentRequest, CreateKBRequest, delete_document(), delete_knowledge_base(), disassociate_agent() (+29 more)

### Community 47 - "dependencies"
Cohesion: 0.12
Nodes (17): clsx, dependencies, clsx, lucide-react, marked, next, react-dom, react-hot-toast (+9 more)

### Community 48 - "TestPostCallService"
Cohesion: 0.27
Nodes (4): Running process() twice does NOT double-count analytics., Usage event written only once per call., run(), TestPostCallService

### Community 49 - "test_m17_tools_handoff.py"
Cohesion: 0.09
Nodes (33): Immutable record of a single tool invocation during a call., ToolCall, add_note(), book_appointment(), get_customer_details(), Built-in tool implementations. Every tool: - Receives (inputs: dict, context:…, Transfer the call to a human agent with complete context. Context package…, Update lead qualification data. (+25 more)

### Community 50 - "TestCustomerBillingPortal"
Cohesion: 0.14
Nodes (5): SKIP, Amount MUST come from server (plan lookup), not frontend., Org A cannot see Org B's invoice., run(), TestCustomerBillingPortal

### Community 51 - "Backend API Inventory"
Cohesion: 0.07
Nodes (26): Admin — `/api/v1/admin/*` (platform roles only), Agents — `/api/v1/agents/*`, Analytics — `/api/v1/analytics/*` (platform roles only), Appointments — `/api/v1/appointments/*`, Auth — `/api/v1/auth/*`, Backend API Inventory, Billing — `/api/v1/billing/*`, Calls — `/api/v1/calls/*` (+18 more)

### Community 52 - "HTTPException"
Cohesion: 0.08
Nodes (44): Use active LLM to translate the greeting text into the target language.…, translate_greeting(), me(), get, Get the current authenticated user's profile., _campaign_response(), campaign_stats(), cancel_campaign() (+36 more)

### Community 53 - "compilerOptions"
Cohesion: 0.07
Nodes (26): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+18 more)

### Community 54 - "ReconciliationService"
Cohesion: 0.14
Nodes (12): AsyncIOMotorDatabase, datetime, Reconciliation service — financial ledger consistency checks. Per spec, runs…, Wallet purchase credits granted but no matching payment., Same webhook event processed more than once., Invoice total != payment amount for the same order., Wallet ledger sum != wallet.balance (available+reserved)., usage_event credits != wallet.total_consumed. (+4 more)

### Community 55 - "GoogleCloudSTTProvider"
Cohesion: 0.08
Nodes (19): _detect_encoding(), GoogleCloudSTTProvider, Any, Exception, Google Cloud Speech-to-Text v2 provider adapter. Uses google-cloud-speech SDK…, Transcribe audio bytes to text using Cloud Speech-to-Text v1 batch API. audio:…, Run synchronous recognition (in a thread pool)., Detect audio encoding from header bytes. Returns (encoding_enum,… (+11 more)

### Community 56 - "core/auth.py"
Cohesion: 0.06
Nodes (46): login(), LoginRequest, logout(), MeResponse, BaseModel, field_validator, post, Request (+38 more)

### Community 57 - "ModelDirectoryService"
Cohesion: 0.02
Nodes (103): Fernet-based credential encryption for stored provider API keys. The encryption…, AIModelCatalogue, ProviderConfiguration, ProviderCredential, MongoDB document models for the AI Models Directory. Three collections:…, One entry per (provider_name, model_id) in the catalogue., A configured provider/model for a given capability (tts/stt/llm)., Fernet-encrypted credential for a provider. Multiple rows per provider_name are… (+95 more)

### Community 58 - "TelephonyProvider"
Cohesion: 0.09
Nodes (4): TelephonyProvider, ExotelProvider, Exotel REST adapter boundary; credentials stay in platform configuration., MockTelephonyProvider

### Community 59 - "seed_demo_numbers"
Cohesion: 0.29
Nodes (5): AsyncIOMotorDatabase, PhoneNumber, Add a new number to the platform inventory., Seed demo phone numbers for DEMO_MODE. Idempotent., seed_demo_numbers()

### Community 60 - "TestAnalyticsService"
Cohesion: 0.17
Nodes (5): _get_mock_db(), charge=1000, cost=300 → margin=70%, total_revenue = subscription + calling, run(), TestAnalyticsService

### Community 61 - "LLMProvider"
Cohesion: 0.09
Nodes (14): LLMProvider, Groq LLM provider adapter. Uses the official groq Python SDK (OpenAI-compatible…, OpenAICompatibleLLMProvider, OpenAI-compatible adapter boundary; concrete transport is selected by route., build_cloud_call_components(), CloudCallComponents, CloudCallLLM, CloudCallTTS (+6 more)

### Community 62 - "ElevenLabsTTSProviderV2"
Cohesion: 0.10
Nodes (13): ElevenLabsTTSProviderV2, Any, Exception, Synchronous synthesis — called in a thread pool., Stream audio chunks from ElevenLabs. Yields {"audio": bytes_chunk,…, Collect streaming chunks synchronously (run in thread)., Return list of available voice dicts from the API., Return a sanitized error message — never includes the API key. (+5 more)

### Community 63 - "payment_service.py"
Cohesion: 0.11
Nodes (11): field_validator, Subscription plan and subscription models. KEY RULES: - All prices stored as…, A plan offered on the platform. Managed by platform admins only., Convenience for display — never use for billing calculations., An organization's active subscription to a plan., Subscription, SubscriptionPlan, Subscription plan and subscription repositories. (+3 more)

### Community 64 - "backend/telephony/vobiz.py"
Cohesion: 0.09
Nodes (18): ConversationEngine, get_active_transport(), api_route, Request, Response, WebSocket, Vobiz.ai Telephony webhook and Media Streams over WebSocket. Vobiz speaks a…, Vobiz calls this when an outbound or inbound call connects. (+10 more)

### Community 65 - "AI Telecalling SaaS — Architecture Reference"
Cohesion: 0.08
Nodes (22): 10. Reuse vs. Replace Decision Table, 1. Repository Origin, 2.1 Backend — Python / FastAPI, 2.2 Frontend — Next.js 14 / TypeScript / Tailwind, 2.3 Database (Current) — PostgreSQL, 2.4 Runtime (Current) — Redis, 2. Existing Architecture (AS-IS), 3.1 Core Changes (+14 more)

### Community 66 - "PhoneNumberRepository"
Cohesion: 0.11
Nodes (8): PhoneNumberRepository, PhoneNumber, Atomically mark a number as 'reserved' only if it is currently 'available'.…, Finalize assignment: reserved → assigned., Finalize assignment to multiple orgs., Return number to available pool., Two concurrent atomic_reserve calls on same number: only ONE wins., TestPhoneNumberRepository

### Community 67 - "TestDeveloperGuide"
Cohesion: 0.09
Nodes (3): Must explain that customer never sees provider details., Guide must be substantial., TestDeveloperGuide

### Community 68 - "AI Telecalling SaaS — Technical Decisions Log"
Cohesion: 0.09
Nodes (21): AI Telecalling SaaS — Technical Decisions Log, D001 — MongoDB Atlas as primary database (not PostgreSQL), D002 — Redis for runtime coordination only, D003 — Provider abstractions (no core provider branching), D004 — Existing VAD + call pipeline preserved, D005 — Money in integer paise; credits in integer seconds, D006 — Subscription + calling packs are separate, D007 — Razorpay is server-authoritative (+13 more)

### Community 69 - "AI Telecalling SaaS — Test Status"
Cohesion: 0.09
Nodes (21): AI Telecalling SaaS — Test Status, Frontend Coverage (TypeScript + ESLint), Known Gaps (not test failures — require external setup), Known Issues at M0, Known Issues at M1, Known Issues at M7, Known Issues at M8, M0 — Repository Audit (+13 more)

### Community 70 - "backend/telephony/twilio.py"
Cohesion: 0.11
Nodes (17): _mulaw8k_to_pcm16k(), place_outbound_call(), api_route, post, Request, Response, WebSocket, Twilio telephony via Media Streams. Twilio speaks a websocket protocol carrying… (+9 more)

### Community 71 - "AnalyticsService"
Cohesion: 0.16
Nodes (9): AnalyticsService, AsyncIOMotorDatabase, datetime, Revenue and margin analytics service — MVP simple approach. Per spec: "Keep MVP…, Total revenue: subscription + calling., Per-day call/credit analytics for the last N days., Complete analytics report for the admin dashboard., Current MRR from active subscriptions. MRR = sum of monthly price of all… (+1 more)

### Community 72 - "SubscriptionPlanRepository"
Cohesion: 0.11
Nodes (8): SubscriptionPlan, Platform-managed subscription plans., Active public plans, sorted by sort_order., SubscriptionPlanRepository, _get_mock_db(), M3 tests — Plans + Subscriptions. Tests: 1. SubscriptionPlan model — price…, Changing plan price in DB must not change an existing subscription snapshot., TestSubscriptionPlanRepository

### Community 73 - "test_m8_provider_abstraction.py"
Cohesion: 0.12
Nodes (9): MockLLMProvider, MockSTTProvider, MockTTSProvider, M8 provider contracts and registry tests., run(), test_demo_registry_registers_all_runtime_provider_categories(), test_live_http_adapters_normalize_provider_responses_without_network(), test_mock_providers_implement_offline_calling_media_and_llm_flow() (+1 more)

### Community 74 - "TestPreflightChecks"
Cohesion: 0.10
Nodes (11): _get_mock_db(), SKIP, Calling hours check fails when current time is outside window., Low credits (above minimum) generate a warning, not a failure., All failing checks are reported — not just the first., Campaign with no subscription/credits/etc must not start., Campaign with all pre-flight checks passing can start., skip_preflight=True starts even if checks would fail. (+3 more)

### Community 75 - "Issues Log — post-Sarvam call testing (2026-07)"
Cohesion: 0.09
Nodes (21): Before → after (same harness), Conversation stalls (silent agent) — FIXED: gpt-oss reasoning, Fix order, Fix plan, Fix plan (addresses 1-5 together), Follow-up (Hindi call): echo-driven hallucination loop, Hindi/Hinglish — FIXED, Hindi / Hinglish naturalness — issues + fix plan (+13 more)

### Community 76 - "VADEndpointer"
Cohesion: 0.09
Nodes (18): Streaming voice-activity detection + endpointing. Fed continuous 16-bit mono…, Silero VAD v5 over onnxruntime. Returns P(speech) for a 512-sample window., Fallback: webrtcvad on 20 ms frames -> boolean speech., _rms_dbfs(), SileroVAD, VADEndpointer, _WebRTCVAD, reset() should clear accumulated state. (+10 more)

### Community 77 - "CallSession"
Cohesion: 0.12
Nodes (10): CallSession, Return custom greeting, or generate one in the call language., Handle explicit caller interrupt event (barge-in)., Feed a chunk of caller audio; drives VAD, barge-in, and responses., Build a CallSession with mocked dependencies., BrowserTransport implements the Transport protocol., CallSession.Transport protocol has play/clear/notify., CallSession starts with empty latency list. (+2 more)

### Community 78 - "LeadRepository"
Cohesion: 0.15
Nodes (4): LeadRepository, Lead, Return the subset of phones that already exist in this org., TestLeadRepository

### Community 79 - "UserRepository"
Cohesion: 0.14
Nodes (6): UserRepository, SKIP_IF_NO_MONGOMOCK, Organization A should not see Organization B's users., TestTenantIsolation, TestUserRepository, User

### Community 80 - "StructuredInstructionEditor"
Cohesion: 0.16
Nodes (14): ConversationPhase, ObjectionItem, StructuredInstructionEditor(), compileStructuredToMarkdown(), handleLoadTemplate(), insertPrefix(), insertSnippet(), insertVariable() (+6 more)

### Community 81 - "test_m4_payment.py"
Cohesion: 0.15
Nodes (6): WebhookEventRepository, _get_mock_db(), SKIP, M4 tests — Razorpay payment integration. Tests: 1. Billing models — integer…, TestInvoiceRepository, TestWebhookIdempotency

### Community 82 - "TestDemoSeedService"
Cohesion: 0.16
Nodes (5): _get_mock_db(), M30 tests — Demo Mode. Tests: 1. DemoSeedService.seed_all creates all required…, Provider routes in voice_profile_versions are internal only., run(), TestDemoSeedService

### Community 83 - "run"
Cohesion: 0.17
Nodes (3): run(), TestMockPaymentProvider, TestPaymentService

### Community 84 - "build_demo_registry"
Cohesion: 0.16
Nodes (13): build_demo_registry(), ProviderRegistry, Typed provider registry; business services resolve providers by capability., ProviderRouter, Internal provider selection with health, capability, language, and fallback…, ResolvedProvider, skipif, run() (+5 more)

### Community 85 - "SubscriptionRepository"
Cohesion: 0.14
Nodes (8): Subscription, Organization subscriptions — one active subscription per org., Get the current active/trialing/past_due subscription for an org., Get the most recent subscription (any status)., Upgrade/downgrade to a new plan. Updates snapshot immediately., How many active orgs are on this plan., SubscriptionRepository, TestSubscriptionRepository

### Community 86 - "BaseRepository"
Cohesion: 0.03
Nodes (68): Appointment model — generic scheduling. Appointments are generic. Solar uses…, AuditLog, Audit log model. Immutable record of actions in the system. Used for security,…, Audit log entry — immutable after creation., DocumentModel, BaseModel, Base Pydantic models for MongoDB documents. MongoDB uses _id (ObjectId) as the…, Base for MongoDB documents. `id` maps to the document's `_id` field. (+60 more)

### Community 87 - "phone_number_repo.py"
Cohesion: 0.23
Nodes (8): PhoneNumberAssignment, Phone number inventory models. IMPORTANT ABSTRACTION: - Customers see: number…, Immutable record of a number assignment to an org. History tracking., PhoneNumberAssignmentRepository, Phone number inventory and assignment repositories. Concurrent reservation…, Phone number service — inventory management. All operations record an immutable…, # NOTE: provider, provider_resource_id, provider_metadata,…, Tests for Vobiz.ai Phone Number provider and multi-organization assignment.

### Community 88 - "SecurityAuditService"
Cohesion: 0.07
Nodes (14): Security audit service — static checks for known vulnerability patterns. This…, All API endpoint files must use auth dependencies., Check for secret keys in API response builders (not in models/repos)., Webhook endpoints must verify signatures., Rate limiting module must exist and auth endpoints use it., Check that repos filter by organization_id (heuristic)., File upload endpoints must validate file type/size., Runs targeted security checks against the codebase. (+6 more)

### Community 89 - "AppointmentService"
Cohesion: 0.21
Nodes (6): AppointmentService, _appt_brief(), Appointment, AsyncIOMotorDatabase, datetime, Appointment service. Handles: - Creating appointments (standalone or from a…

### Community 90 - "PhoneNumberService"
Cohesion: 0.15
Nodes (22): add_number_to_inventory(), AddNumberRequest, admin_list_numbers(), assign_number(), AssignRequest, get_my_number(), inventory_stats(), list_available_numbers() (+14 more)

### Community 91 - "VobizTelephonyProvider"
Cohesion: 0.17
Nodes (10): Any, AsyncClient, Vobiz.ai Telephony adapter. Initiates outbound PSTN calls and manages call…, Fetch status of a call., Initiate an outbound call via Vobiz REST API. kwargs must contain: - auth_id:…, VobizTelephonyProvider, patch, Unit tests for VobizTelephonyProvider adapter. (+2 more)

### Community 92 - "DNCRepository"
Cohesion: 0.16
Nodes (6): DNCRepository, Add phone to DNC. Returns None if already on DNC., Return the subset of phones that are on DNC for this org., AsyncIOMotorDatabase, TestDNCRepository, DNCEntry

### Community 93 - "OrderRepository"
Cohesion: 0.21
Nodes (3): OrderRepository, Order, TestOrderRepository

### Community 94 - "run"
Cohesion: 0.16
Nodes (6): SKIP_IF_NO_MONGOMOCK, Changing plan config in DB changes entitlements without code changes., Activating a new plan cancels the previous one., run(), TestSeedDefaultPlans, TestSubscriptionServiceEntitlements

### Community 95 - "CallRepository"
Cohesion: 0.14
Nodes (5): CallRepository, Finalize a call. Tenant-safe (org check on update)., AsyncIOMotorDatabase, TestCallRepository, Call

### Community 96 - "Real Estate Voice Agent — Execution Plan"
Cohesion: 0.11
Nodes (18): 0. The one thing that matters: latency, 1. Hardware reality & the stack decision, 2. System architecture, 3. Repository structure, 4. Conversation design (the product), 5. Data model (first cut), 6. API surface (backend), 7. Sprint plan (walking skeleton first) (+10 more)

### Community 97 - "GroqLLMProvider"
Cohesion: 0.11
Nodes (14): GroqLLMProvider, Any, Exception, Streaming chat completion — yields text deltas., Fetch models dynamically from the official Groq API using this client., Return a sanitized error message — never includes the API key., Groq chat-completion adapter. api_key is required and must come from the…, Non-streaming chat completion. Raises RuntimeError on auth failure, rate limit,… (+6 more)

### Community 98 - "VoiceProfileVersionRepository"
Cohesion: 0.29
Nodes (5): Immutable snapshot of a voice profile's provider configuration. Once published,…, VoiceProfileVersion, Any, Create a new immutable version. Routes contain internal provider config., VoiceProfileVersionRepository

### Community 99 - "providers/base.py"
Cohesion: 0.09
Nodes (14): PaymentProvider, Provider, ABC, Abstract provider interfaces for the AI Telecalling SaaS platform. Core…, Verify payment signature. Returns True if valid., Fetch payment details from provider. Returns provider payment dict., Issue a refund. Returns provider refund dict., Verify webhook signature. Called synchronously (crypto only, no I/O). Returns… (+6 more)

### Community 100 - "run"
Cohesion: 0.20
Nodes (3): SKIP, run(), TestAppointmentService

### Community 101 - "new_id"
Cohesion: 0.04
Nodes (48): add_turn(), Create a fresh lead + active call at the start of a conversation., start_call(), new_id(), datetime, Generate a new UUID4 string., utcnow(), DNCEntry (+40 more)

### Community 102 - ".test_llm"
Cohesion: 0.25
Nodes (4): [LIVE] Test LLM provider by requesting a one-sentence hello. Returns {status,…, [LIVE] Test Groq LLM with the injected API key., [LIVE] Test Gemini LLM with the injected API key., Test Ollama local runtime reachability then generate. NOTE: Ollama is a LOCAL-…

### Community 104 - "analytics.py"
Cohesion: 0.16
Nodes (19): get_arpu(), get_costs(), get_daily_analytics(), get_full_report(), get_margins(), get_mrr(), get_mrr_movement(), get_revenue() (+11 more)

### Community 105 - "run"
Cohesion: 0.09
Nodes (13): _get_mock_db(), SKIP, Org A cannot see Org B numbers., get_number_for_org returns None if number belongs to a different org., Provider details must not leak into any customer-facing response., Only one org can claim the same number — concurrent request safety., 5 concurrent assign attempts for the same number: exactly 1 wins., 5 concurrent assigns for 5 different numbers: all succeed. (+5 more)

### Community 106 - "LLMClient"
Cohesion: 0.12
Nodes (14): _extract_json(), LLMClient, OllamaLLMClient, Groq gpt-oss client (OpenAI-compatible), async + streaming. Streaming matters:…, Yield complete sentences as soon as they're ready, so TTS can start speaking…, Non-streaming convenience helper (used by smoke tests)., Structured extraction. Never raises: returns {} if extraction fails. gpt-oss on…, Async client for a locally-running Ollama server. Ollama must be started… (+6 more)

### Community 107 - "GeminiLLMProvider"
Cohesion: 0.13
Nodes (15): GeminiLLMProvider, _get_candidate_models(), _is_transient_error(), Any, Exception, Gemini LLM provider adapter using the official google-genai SDK. Uses…, Generate a reply for the given conversation messages., Stream text deltas from Gemini with automatic retry and model fallback. (+7 more)

### Community 108 - "VoiceProfileService"
Cohesion: 0.13
Nodes (20): create_profile(), create_version(), CreateProfile, CreateVersion, get_profile(), list_profiles(), BaseModel, get (+12 more)

### Community 110 - "CallEventBroadcaster"
Cohesion: 0.17
Nodes (9): CallEventBroadcaster, Any, In-memory real-time event broadcaster for live phone calls., Pub/sub broadcaster delivering real-time call events (turns, status,…, Tests for CallEventBroadcaster and live call transcript monitoring., run(), test_broadcaster_empty_and_cleanup(), test_broadcaster_pubsub() (+1 more)

### Community 111 - "OrganizationRepository"
Cohesion: 0.21
Nodes (4): OrganizationRepository, Organization, run(), TestOrganizationRepository

### Community 112 - "seed_default_plans"
Cohesion: 0.19
Nodes (4): AsyncIOMotorDatabase, Create default plans if they don't exist. Safe to call on every startup., seed_default_plans(), TestSubscriptionHTTP

### Community 113 - "TestPhoneNumberHTTP"
Cohesion: 0.21
Nodes (3): CRITICAL: provider details must never appear in customer API response., Org A cannot see Org B's assigned numbers via /my endpoint., TestPhoneNumberHTTP

### Community 115 - "call_session.py"
Cohesion: 0.14
Nodes (11): _looks_like_noise(), Transport-agnostic call pipeline. `CallSession` owns everything that makes a…, True if the transcript is almost certainly a hallucination or noise blip., Supported call languages (Indian-focused, backed by Sarvam Bulbul). Each entry…, Return (canonical_code, info). Falls back to the default if unknown., resolve(), configure_logging(), Structured logging with a per-turn/trace correlation id. Every log line carries… (+3 more)

### Community 116 - "BrowserTransport"
Cohesion: 0.22
Nodes (5): BrowserTransport, WebSocket, Speaks to the browser. Streams PCM chunks (4-byte sample-rate header + PCM)., ws_call(), ws_call_monitor()

### Community 117 - "UsageEvent"
Cohesion: 0.10
Nodes (11): ProviderUsage, field_validator, One billable usage event. Immutable after creation., Per-call provider cost breakdown. ADMIN ONLY., UsageEvent, ProviderUsageRepository, Record a usage event. Returns None if idempotency_key already exists., Usage and cost accounting service. KEY SEPARATION (enforced here): -… (+3 more)

### Community 118 - "UUID"
Cohesion: 0.19
Nodes (11): Alembic environment. Runs synchronously (psycopg3 sync) using our models'…, Base, Booking, Call, Lead, SQLAlchemy models: leads, calls, turns, bookings. Slots…, Turn, _uuid_col() (+3 more)

### Community 120 - "TranscriptRepository"
Cohesion: 0.16
Nodes (9): A single turn (user or agent utterance) in the call transcript., Full transcript for a single call. Unique per call_id., Transcript, Turn, Get existing transcript or create one. Idempotent., Append turns to transcript and update count., TranscriptRepository, TestTranscriptModel (+1 more)

### Community 121 - "TTSProvider"
Cohesion: 0.09
Nodes (6): Any, STTProvider, TTSProvider, ElevenLabsTTSProvider, ElevenLabs TTS provider adapter — proper implementation. Uses the official…, Sarvam Bulbul managed-cloud TTS adapter.

### Community 122 - "PricingSyncService"
Cohesion: 0.07
Nodes (31): PricingSettings, ProviderRateCard, MongoDB document models for provider pricing, FX rates, and rate cards. Tracks…, Stores the effective cost and billable rate for a provider/model., Global platform pricing and loss-protection settings., _deserialize(), Clean up a MongoDB document for use with Pydantic models., PricingSettingsRepository (+23 more)

### Community 123 - "run"
Cohesion: 0.17
Nodes (4): Auto-mapping handles common aliases (mobile → phone, etc.)., run(), TestCSVImport, TestLeadService

### Community 124 - "API-to-UI Mapping — Super Admin Dashboard"
Cohesion: 0.13
Nodes (14): API-to-UI Mapping — Super Admin Dashboard, Audit Logs, Calling Packs & Credits, Customer Dashboard Pages (for completeness), Dashboard, Organizations, Payments & Invoices, Phone Numbers (+6 more)

### Community 125 - "PostCallService"
Cohesion: 0.26
Nodes (3): PostCallService, AsyncIOMotorDatabase, Run the full post-call pipeline. Returns a summary dict of what was processed.…

### Community 127 - "package.json"
Cohesion: 0.22
Nodes (8): name, private, scripts, build, dev, lint, start, version

### Community 128 - "test_m12_leads.py"
Cohesion: 0.12
Nodes (7): _get_mock_db(), _make_csv(), SKIP, M12 tests — Lead CRM. Tests: 1. Lead model — status validation, phone required…, Build a CSV bytes payload from a list of dicts., TestJSONImport, TestXLSXImport

### Community 130 - "Detailed Data Model & API Changes"
Cohesion: 0.15
Nodes (12): 1. Model Updates (`backend/models/phone_number.py`), 2. Service & Repository Updates, 3. Vobiz Telephony Provider Adapter (`backend/providers/telephony/vobiz.py`), 4. Vobiz Webhook & WebSocket Streaming (`backend/telephony/vobiz.py`), 5. Frontend Admin Dashboard Updates (`frontend/app/(admin)/admin/phone-numbers/page.tsx`), 6. Frontend AI Agent Studio Updates (`frontend/app/(dashboard)/agents/[id]/page.tsx`), Architecture & Data Flow, Design: Vobiz.ai Phone Number Provider & Multi-Organization Assignment (+4 more)

### Community 131 - "test_m16_barge_in_latency.py"
Cohesion: 0.11
Nodes (14): LatencyService, Redis-backed latency tracker for active calls., M16 tests — Barge-In + Latency. Tests: 1. VAD SPEECH_START event fires when…, Test the barge-in flow in CallSession using mock components., SPEECH_START → _cancel_responder() + transport.clear()., During TTS playback, barge-in cancels the task., SPEECH_START with no active responder still calls transport.clear()., UTTERANCE event → new responder task created. (+6 more)

### Community 132 - "run"
Cohesion: 0.05
Nodes (18): _extract_keywords(), KnowledgeBaseRepository, KnowledgeDocumentRepository, KnowledgeBase, KnowledgeDocument, MVP text search: keyword matching on title, content, keywords list. No vector…, Create a new version of a document. Old version is kept but deactivated., Extract simple keywords from title and content (MVP: top unique words). (+10 more)

### Community 133 - "TestCreditReserve"
Cohesion: 0.22
Nodes (3): Same call_id reserve twice: no double-deduction., reserve() moves available → reserved; total unchanged., TestCreditReserve

### Community 134 - "test_m27_reconciliation.py"
Cohesion: 0.17
Nodes (4): _get_mock_db(), SKIP, M27 tests — Reconciliation. Tests: 1. ReconciliationResult.add_failure sets…, TestRunAll

### Community 135 - "AI Telecalling SaaS — Developer Guide"
Cohesion: 0.13
Nodes (15): AI Telecalling SaaS — Developer Guide, AI Voice Profiles, Architecture Overview, Business Templates & Agents, Campaign Engine, Creating a voice profile (admin), Creating a Voice Profile (Step-by-Step), Demo Mode (+7 more)

### Community 136 - "Getting Started — Real Estate Voice Agent"
Cohesion: 0.13
Nodes (14): 0. Prerequisites (already on this machine), 1. Why this stack (read once), 2.1 Environment file, 2.2 Start Postgres + Redis, 2.3 Python environment, 2.4 Download the TTS voice, 2. One-time setup, 3. Smoke test each piece independently (+6 more)

### Community 137 - "ModelSetupWizard.tsx"
Cohesion: 0.07
Nodes (38): Capability, capabilityVariant(), formatFreeTierInfo(), freeTierDetails(), hostingIcon(), hostingLabel(), isStale(), ModelCard() (+30 more)

### Community 138 - "PhoneNumber"
Cohesion: 0.09
Nodes (17): PhoneNumber, A phone number in the platform inventory., Get a specific number only if it belongs to this org., Atomically assign an available number to an organization. Returns customer-safe…, Assign an available or assigned number to multiple organizations., Available numbers — customer-safe view (no provider details)., Full inventory view for platform admin — includes provider details., Strip all provider details for customer-facing responses. (+9 more)

### Community 139 - "TestBillingHTTP"
Cohesion: 0.19
Nodes (3): Generate a valid webhook signature for testing., Org A cannot see Org B's invoice., TestBillingHTTP

### Community 140 - "test_test_agent.py"
Cohesion: 0.12
Nodes (15): GroqSTTProvider, Any, Groq Whisper STT provider adapter., Any, AsyncClient, Sarvam Saaras STT provider adapter., SarvamSTTProvider, Unit tests for the Test Agent browser runner & cloud providers. (+7 more)

### Community 142 - "_make_mock_redis"
Cohesion: 0.43
Nodes (3): _get_mock_db(), _make_mock_redis(), In-memory dict-based Redis mock for credit reservation keys.

### Community 144 - "MockPaymentProvider"
Cohesion: 0.09
Nodes (7): MockPaymentProvider, Verify against the fixed mock secret., Clear mock state between tests., Generate a test-valid mock signature for verify_payment., In-memory mock payment provider. No external calls., should_fail=True: verify_payment always returns False (simulate failed payment)., TestDemoModeProviders

### Community 145 - "Order"
Cohesion: 0.08
Nodes (13): Invoice, Order, Payment, field_validator, Invoice generated after a successful payment., Every inbound provider webhook is recorded for idempotency. Unique index:…, An order created before payment. Tracks what the customer is buying., Display only — never use for billing calculations. (+5 more)

### Community 146 - "AI Telecalling SaaS"
Cohesion: 0.14
Nodes (10): AI Telecalling SaaS, Architecture, Checkpoints completed, Deployment, License, Project structure, Quick start (Demo Mode), Running tests (+2 more)

### Community 147 - "CHECKPOINT HISTORY"
Cohesion: 0.14
Nodes (14): CHECKPOINT HISTORY, M0 — REPOSITORY AUDIT, M10 — PROVIDER ROUTER, M11 — AGENT BUILDER, M1 — MONGODB FOUNDATION, M2 — AUTH + MULTI-TENANCY + RBAC, M3 — PLANS + SUBSCRIPTIONS, M40 — COMPLETE FRONTEND REDESIGN (+6 more)

### Community 148 - "Review Focus"
Cohesion: 0.18
Nodes (10): Global Constraints, Review Focus, Task 1: Phone Number Multi-Organization Data Model & Service Layer, Task 2: Vobiz Telephony Provider Adapter & Registry Integration, Task 3: Vobiz Real-Time Media Stream WebSocket & Webhook, Task 4: Outbound Calling Integration in `CallService` & Campaign Worker, Task 5: Frontend Admin Dashboard - Phone Number Inventory & Multi-Org UI, Task 6: Frontend AI Agent Studio - Calling Number Selection (+2 more)

### Community 149 - "Settings"
Cohesion: 0.19
Nodes (5): Return whichever Sarvam key is set., Legacy compat for existing session.py., Settings, TestConfig, BaseSettings

### Community 150 - "AgentRepository"
Cohesion: 0.11
Nodes (18): Agent, AgentVersion, BusinessTemplate, Agent builder models. An Agent is an AI calling agent configuration tied to a…, A generic business template (Solar, Real Estate, Collections, etc.).…, Customer-owned AI calling agent., Immutable-once-published snapshot of an agent's configuration., AgentRepository (+10 more)

### Community 151 - "UsageEventRepository"
Cohesion: 0.08
Nodes (15): datetime, Admin aggregation including provider costs and margins., Admin: cost breakdown by provider layer., Aggregate customer-facing usage stats (no provider costs)., UsageEventRepository, AsyncIOMotorDatabase, _get_mock_db(), SKIP (+7 more)

### Community 152 - "AuditLogRepository"
Cohesion: 0.27
Nodes (4): AuditLog, AuditLogRepository, Any, TestAuditLogRepository

### Community 153 - "ReconciliationResult"
Cohesion: 0.31
Nodes (3): Result of one reconciliation check., ReconciliationResult, TestReconciliationResult

### Community 154 - "run.py"
Cohesion: 0.22
Nodes (13): is_port_in_use(), kill_process_tree(), main(), preflight_checks(), Launch backend and frontend in separate console windows (Windows)., Run both services unified in the current console with log prefixing., Check if a TCP port is in use., Stream stdout/stderr line by line with a colored prefix. (+5 more)

### Community 155 - "Campaign"
Cohesion: 0.13
Nodes (5): Campaign, field_validator, An outbound calling campaign., TestCampaignModel, _make_campaign()

### Community 156 - "SubscriptionService"
Cohesion: 0.15
Nodes (9): EntitlementCheck, Result of an entitlement check. Not stored in DB., Subscription, SubscriptionPlan, Check a boolean feature gate, e.g. 'knowledge_base_enabled'., Activate a plan for an org. Cancels any existing subscription immediately., Upgrade or downgrade. Takes effect immediately., Return a safe summary of what the org is entitled to (for API response). (+1 more)

### Community 157 - "AI Telecalling SaaS — Development Progress"
Cohesion: 0.15
Nodes (13): AI Telecalling SaaS — Development Progress, Build, CHECKPOINT HISTORY, CHECKPOINT ROADMAP, EXISTING CODEBASE SUMMARY, FEAT-001 — Design Foundations (COMPLETE — commit e04ec2d), FEAT-002 — Customer Application (COMPLETE — see commit after M40), FEAT-003/004 — Admin Application (COMPLETE) (+5 more)

### Community 158 - "Admin UI Implementation Plan — M40 FEAT-005A"
Cohesion: 0.17
Nodes (11): 1. Current State (post FEAT-005A), 2. File Structure, 3. Shared Component Reuse, 4. Auth/Permission Guard Strategy, 5. Design System, 6. API Client Namespaces (lib/api.ts), 7. Verification Commands, 8. Known Gaps / Future Work (+3 more)

### Community 161 - "db.py"
Cohesion: 0.08
Nodes (34): AsyncIOMotorClient, Central configuration for the AI Telecalling SaaS platform. Loads backend/.env…, close_db(), _ensure_indexes(), get_client(), init_db(), ping_db(), AsyncIOMotorDatabase (+26 more)

### Community 162 - "CampaignWorker"
Cohesion: 0.18
Nodes (7): M31 tests — Production Deployment Configuration. Tests: 1. Dockerfile exists…, TestWorkerShutdown, CampaignWorker, main(), Initiate the actual call and handle completion., Find running campaigns and dispatch calls., Try to start a new call for this campaign.

### Community 163 - "_catalogue_to_dict"
Cohesion: 0.29
Nodes (5): _catalogue_to_dict(), AIModelCatalogue, Return a single catalogue entry or raise LookupError., Serialize catalogue entry. No credentials present in this model., Return catalogue entries with a pricing_stale flag. Entries whose…

### Community 164 - "AgentService"
Cohesion: 0.18
Nodes (8): AgentService, Agent, AgentVersion, Any, Returns agent only if it belongs to this org (tenant isolation)., Create a new draft version. Optionally publish and activate it., Publish a draft version and set it as active. Immutable after this., Update a draft version's configuration. Fails if already published.

### Community 165 - "CredentialStore"
Cohesion: 0.22
Nodes (5): CredentialStore, Thin wrapper around Fernet for storing/retrieving provider credentials., Encrypt a plaintext credential and return Fernet token bytes. Raises ValueError…, Decrypt a Fernet token and return the original plaintext string. Raises…, Return the last 4 characters of the plaintext for display purposes, or a…

### Community 166 - "TestE2EHappyPath"
Cohesion: 0.33
Nodes (4): Complete E2E: signup → org → plan → credits → voice profile → agent → phone →…, Complete workflow: signup → call → settlement → analytics., Seed plans, packs, and voice profile., TestE2EHappyPath

### Community 167 - "TestMVPValidation"
Cohesion: 0.17
Nodes (7): Validate the overall MVP state., All 26+ API routers are wired., Every checkpoint M1-M32 has a test file (M29 used existing suite)., Core services never import provider-specific modules directly., All repositories include organization_id in their queries., Demo mode seed can be imported and creates the right data., TestMVPValidation

### Community 168 - "TestAuthEndpoints"
Cohesion: 0.06
Nodes (12): SKIP_IF_NO_MONGOMOCK, Test auth endpoints using TestClient + mongomock., Critical: Org A must NOT be able to access Org B data., CRITICAL: Org A must receive 403 when accessing Org B., CRITICAL: Org B must receive 403 when accessing Org A., Org A cannot list users of Org B., Role-based access control enforced at the HTTP layer., Viewer does not have organization_admin role. (+4 more)

### Community 169 - "AgentVersionRepository"
Cohesion: 0.27
Nodes (5): AgentVersionRepository, AgentVersion, Any, Mark a version as published (immutable after this)., Update draft configuration. Raises if already published.

### Community 170 - "CallService"
Cohesion: 0.18
Nodes (7): CallService, Finalize a call after it ends. 1. Settle credits 2. Finalize call record 3.…, Initiate an outbound call. 1. Reserve credits 2. Create call record 3.…, patch, Tests for CallService Vobiz outbound dispatch and failure handling., run(), TestVobizCallDispatch

### Community 171 - "test_m20_post_call.py"
Cohesion: 0.15
Nodes (8): _create_call(), _create_campaign(), _create_lead(), _get_mock_db(), _make_redis(), SKIP, M20 tests — Post-Call Processing. Tests: 1. Transcript model — turn storage,…, TestTranscriptsHTTP

### Community 173 - "SarvamAgentStudioPage"
Cohesion: 0.17
Nodes (9): SarvamAgentStudioPage(), connectPhoneCallStream(), downsampleTo16k(), handleDialPhone(), handleEndCall(), handleStartCall(), playPcmChunk(), scheduleAutoHangup() (+1 more)

### Community 174 - "reconciliation_report"
Cohesion: 0.40
Nodes (5): get, Run all financial ledger consistency checks., Alias for /run — returns the full reconciliation report., reconciliation_report(), run_reconciliation()

### Community 176 - "test_m6_credit_reservation.py"
Cohesion: 0.40
Nodes (3): _fund_org(), M6 tests — Credit Reservation + Settlement. Tests: 1. reserve() moves credits…, Helper: give an org N credits via bonus.

### Community 177 - "TestConcurrentReservations"
Cohesion: 0.17
Nodes (6): 10 concurrent calls — no double-spend, no negative credits., 10 concurrent reserves of 60 credits with 600 total: all succeed., 5 calls succeed, 6th fails (300 credits = exactly 5 × 60)., Settling 10 calls concurrently: total consumed = sum of actuals., Hammer reserves beyond balance: wallet always ≥ 0., TestConcurrentReservations

### Community 181 - "Appointment"
Cohesion: 0.23
Nodes (7): Appointment, field_validator, A generic appointment record., _future_dt(), datetime, M18 tests — Appointments. Tests: 1. Appointment model — valid statuses,…, TestAppointmentModel

### Community 182 - "SarvamTTSProvider"
Cohesion: 0.28
Nodes (4): Any, AsyncClient, Progressive low-latency streaming TTS using Sarvam /stream endpoint., SarvamTTSProvider

### Community 184 - "test_m14_preflight.py"
Cohesion: 0.13
Nodes (13): Return platform profiles + org's own profiles. Active only., VoiceProfileRepository, M14 tests — Campaign Pre-flight. Tests: 1. All checks pass → campaign can start…, Create a published agent version., Create an active platform voice profile with a version., Create leads for the org., Create an active subscription for the org., _seed_agent() (+5 more)

### Community 185 - "CampaignRepository"
Cohesion: 0.15
Nodes (7): CampaignRepository, Campaign, All running/scheduled campaigns — for worker polling., Atomic status update scoped to org., AsyncIOMotorDatabase, TestCampaignRepository, _seed_campaign()

### Community 187 - "normalize_phone"
Cohesion: 0.27
Nodes (3): normalize_phone(), Normalize a phone number to E.164 (best-effort for Indian numbers)., TestPhoneNormalization

### Community 188 - "TestVobizPhoneNumbers"
Cohesion: 0.33
Nodes (3): Vobiz credentials must be stored in provider_metadata and NEVER exposed in…, run(), TestVobizPhoneNumbers

### Community 189 - "run"
Cohesion: 0.13
Nodes (9): Can't release a call that was already settled., Settle bills exactly; over-reserved credits returned to available., Settle using all reserved credits., actual_credits > reserved is capped at reserved (safety guard)., Double-settle same call_id is a no-op., 0-second call: no consume ledger entry, reservation cleared., run(), TestCreditRelease (+1 more)

### Community 190 - "TestModels"
Cohesion: 0.15
Nodes (7): Organization, OrganizationSettings, Mutable settings nested inside an organization., Represents a customer organization (tenant)., MongoDB user document., User, TestModels

### Community 191 - "test_m32_documentation.py"
Cohesion: 0.39
Nodes (3): _exists(), M32 tests — Documentation Completeness. Tests: 1. DEVELOPER_GUIDE.md exists and…, TestDocumentationFilesExist

### Community 192 - "_read"
Cohesion: 0.25
Nodes (3): Should have substantial number of routes registered., _read(), TestAPICoverage

### Community 199 - "Provider Configuration"
Cohesion: 0.29
Nodes (7): ElevenLabs (TTS), Exotel (Telephony), OpenAI / Groq (LLM), Provider Configuration, Razorpay (Payments), Sarvam (STT + TTS), Twilio (Telephony)

### Community 200 - "(auth)/layout.tsx"
Cohesion: 0.18
Nodes (6): AuthClientLayout(), metadata, inter, metadata, extends, next

### Community 201 - "5. PROVIDER ABSTRACTION"
Cohesion: 0.29
Nodes (7): 5. PROVIDER ABSTRACTION, LLMProvider, PaymentProvider, PhoneNumberProvider, STTProvider, TelephonyProvider, TTSProvider

### Community 202 - "TestAnalyticsHTTP"
Cohesion: 0.23
Nodes (3): SKIP, All paise values must be integers in responses., TestAnalyticsHTTP

### Community 207 - "test_m13_campaigns.py"
Cohesion: 0.24
Nodes (4): _get_mock_db(), _make_redis(), M13 tests — Campaign Engine. Tests: 1. Campaign model — status validation, FSM…, In-memory Redis mock.

### Community 209 - "29. AUTONOMOUS CHECKPOINT EXECUTION CONTRACT"
Cohesion: 0.33
Nodes (6): 29.1 `BEGIN MXX` means COMPLETE THE WHOLE CHECKPOINT, 29.2 NEVER STOP BECAUSE A TEST IS RED, 29.3 DO NOT ASK WHETHER TO CONTINUE, 29.4 FINAL RESPONSE RULE, 29.5 GENUINE BLOCKED STATE, 29. AUTONOMOUS CHECKPOINT EXECUTION CONTRACT

### Community 210 - "M41 Implementation Plan — AI Models Directory and One-Click Provider Setup"
Cohesion: 0.40
Nodes (4): Architecture decisions, Implementation Plan, Known gaps and non-blockers, M41 Implementation Plan — AI Models Directory and One-Click Provider Setup

### Community 211 - "Transport"
Cohesion: 0.22
Nodes (6): Deliver a metadata event (transcript, stage, etc.). May be a no-op., A medium (browser websocket, phone line) the session speaks through., Send agent audio to the caller., Flush any audio already queued on the caller side (barge-in)., Transport, Protocol

### Community 212 - "Deployment (Fly.io)"
Cohesion: 0.40
Nodes (5): Deploy campaign worker, Deployment (Fly.io), First deploy, Health check, Logs

### Community 213 - "Local Development"
Cohesion: 0.40
Nodes (5): Local Development, Run the API server, Run the campaign worker, Seed demo data, Start infrastructure

### Community 214 - "Testing"
Cohesion: 0.40
Nodes (5): Run all tests, Run specific checkpoint, Run with coverage, Test without external providers, Testing

### Community 215 - "36. DOCUMENTATION FILES MAINTAINED DURING EXECUTION"
Cohesion: 0.40
Nodes (5): 36. DOCUMENTATION FILES MAINTAINED DURING EXECUTION, MVP_ARCHITECTURE.md, MVP_DECISIONS.md, MVP_PROGRESS.md, MVP_TEST_STATUS.md

### Community 216 - "test_m1_mongodb.py"
Cohesion: 0.17
Nodes (8): hash_password(), verify_password(), get_mock_db(), M1 tests — MongoDB foundation. Tests run against mongomock (in-memory MongoDB…, Return a mongomock-backed async Motor database substitute., health.check_all should return the correct structure (mocked)., TestHealthCheck, TestPasswordHashing

### Community 217 - "button.tsx"
Cohesion: 0.07
Nodes (27): ChatMessage, StudioTab, TestTab, LANGUAGE_OPTIONS, NewAgentPage(), Step, TONE_OPTIONS, AgentsPage() (+19 more)

### Community 218 - "Adding a New Provider"
Cohesion: 0.50
Nodes (4): 1. Create the adapter, 2. Register in the provider registry, 3. Create a voice profile version using the new provider, Adding a New Provider

### Community 219 - "Installation"
Cohesion: 0.50
Nodes (4): Backend, Frontend, Installation, Prerequisites

### Community 222 - "PaymentRepository"
Cohesion: 0.20
Nodes (6): PaymentRepository, get_payment_provider(), AsyncIOMotorDatabase, Return the appropriate payment provider based on config., In DEMO_MODE, payment_service uses MockPaymentProvider., Payment

### Community 223 - "TestCreditConservation"
Cohesion: 0.29
Nodes (3): Credits are conserved: available + reserved = constant (except consume)., After settle, total = initial - billed., TestCreditConservation

### Community 224 - "4. MULTI-TENANCY"
Cohesion: 0.67
Nodes (3): 4. MULTI-TENANCY, Organization, Platform

### Community 251 - "calls.py"
Cohesion: 0.24
Nodes (16): _call_response(), finalize_call(), FinalizeCallRequest, get_call(), get_call_transcript(), hangup_call(), initiate_call(), InitiateCallRequest (+8 more)

### Community 253 - "Global Constraints"
Cohesion: 0.29
Nodes (6): Global Constraints, Model Directory Catalogue & Auto-Loading Models Implementation Plan, Task 1: Update Groq LLM Provider Adapter, Task 2: Catalogue Seeding, Credential Reuse & Live Models Endpoint, Task 3: Frontend API & Dropdown Auto-Loading, Task 4: Verification & Graphify Update

### Community 254 - "_slugify"
Cohesion: 0.43
Nodes (3): Simple slugifier: lowercase, alphanumeric + hyphens., _slugify(), TestSlugGeneration

### Community 255 - "formatDateTime"
Cohesion: 0.05
Nodes (21): AdminAuditLogsPage(), AdminOrgDetailPage(), AdminOrgsPage(), AdminSubscriptionsPage(), AdminVoiceProfilesPage(), AppointmentsPage(), BillingPage(), CallDetailPage() (+13 more)

### Community 256 - "Review Focus"
Cohesion: 0.22
Nodes (8): Agent Multi-KB Selector and Response Grounding Implementation Plan, Global Constraints, Review Focus, Task 1: Frontend API Client KB Association Methods, Task 2: Backend Prompt Grounding & Strictness Mode Enhancement, Task 3: Backend Unit Tests, Task 4: Frontend Agent Knowledge Base Selector UI, Task 5: Verification & Demo

### Community 258 - "TestLargeImport"
Cohesion: 0.29
Nodes (4): Test 4000+ lead import — the M12 mandatory acceptance criterion., Import 4000 leads: all imported, correct count, no errors., 4000 leads, 100 on DNC → 3900 imported, 100 skipped., TestLargeImport

### Community 263 - "Design: Agent Multi-KB Selector and Grounded Response Injection"
Cohesion: 0.29
Nodes (6): Architecture & Data Flow, Design: Agent Multi-KB Selector and Grounded Response Injection, Detailed Decisions, Goals, Intent and Context, Non-Goals & Anti-Goals

### Community 264 - ".from_mongo"
Cohesion: 0.40
Nodes (3): Any, Serialize for MongoDB insertion (use `_id`, not `id`)., Deserialize from a MongoDB document.

## Knowledge Gaps
- **485 isolated node(s):** `MRRData`, `MRRMovement`, `RevenueData`, `DailyEntry`, `PERIOD_OPTIONS` (+480 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `new_id()` connect `new_id` to `AppointmentRepository`, `test_m12_leads.py`, `run`, `Call`, `repository.py`, `test_m27_reconciliation.py`, `PhoneNumber`, `FastAPI`, `test_m15_calls.py`, `CreditService`, `Order`, `test_m26_provider_ops.py`, `test_m5_wallet.py`, `AgentRepository`, `UsageEventRepository`, `AuditLogRepository`, `test_m33_e2e_acceptance.py`, `Campaign`, `billing_portal.py`, `db.py`, `AgentVersionRepository`, `test_m20_post_call.py`, `test_m17_tools_handoff.py`, `Appointment`, `test_m14_preflight.py`, `ModelDirectoryService`, `TestModels`, `payment_service.py`, `PhoneNumberRepository`, `SubscriptionPlanRepository`, `LeadRepository`, `UserRepository`, `test_m13_campaigns.py`, `test_m4_payment.py`, `build_demo_registry`, `SubscriptionRepository`, `BaseRepository`, `phone_number_repo.py`, `test_m1_mongodb.py`, `DNCRepository`, `OrderRepository`, `PaymentRepository`, `CallRepository`, `VoiceProfileVersionRepository`, `UsageEvent`, `TranscriptRepository`, `PricingSyncService`, `PostCallService`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `get_db()` connect `get_db` to `WalletService`, `repository.py`, `dashboard.py`, `CurrentUser`, `v1/__init__.py`, `PaymentService`, `test_m26_provider_ops.py`, `appointments.py`, `agents.py`, `subscriptions.py`, `billing_portal.py`, `organizations.py`, `db.py`, `LeadService`, `UsageService`, `KnowledgeService`, `reconciliation_report`, `HTTPException`, `core/auth.py`, `backend/telephony/vobiz.py`, `backend/telephony/twilio.py`, `PhoneNumberService`, `new_id`, `analytics.py`, `VoiceProfileService`, `BrowserTransport`, `calls.py`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `new_id` to `AppointmentRepository`, `run`, `repository.py`, `PhoneNumber`, `CreditService`, `test_m26_provider_ops.py`, `AgentRepository`, `test_m33_e2e_acceptance.py`, `PreflightService`, `CallService`, `CampaignService`, `test_m17_tools_handoff.py`, `test_m14_preflight.py`, `CampaignRepository`, `ModelDirectoryService`, `payment_service.py`, `backend/telephony/vobiz.py`, `PhoneNumberRepository`, `LeadRepository`, `UserRepository`, `test_m4_payment.py`, `build_demo_registry`, `SubscriptionRepository`, `BaseRepository`, `phone_number_repo.py`, `CallRepository`, `VoiceProfileVersionRepository`, `OrganizationRepository`, `UsageEvent`, `TranscriptRepository`, `PricingSyncService`, `calls.py`, `PostCallService`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 134 inferred relationships involving `HTTPException` (e.g. with `call_detail()` and `admin_adjust_wallet()`) actually correct?**
  _`HTTPException` has 134 INFERRED edges - model-reasoned connections that need verification._
- **What connects `MRRData`, `MRRMovement`, `RevenueData` to the rest of the system?**
  _485 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `WalletService` be split into smaller, more focused modules?**
  _Cohesion score 0.09059233449477352 - nodes in this community are weakly interconnected._
- **Should `MVP_CHECKPOINTS.md` be split into smaller, more focused modules?**
  _Cohesion score 0.028985507246376812 - nodes in this community are weakly interconnected._