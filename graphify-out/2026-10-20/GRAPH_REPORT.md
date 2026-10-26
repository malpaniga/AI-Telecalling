# Graph Report - saas  (2026-10-20)

## Corpus Check
- 306 files · ~231,884 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4943 nodes · 10282 edges · 252 communities (206 shown, 46 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 693 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0e8db58c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AppointmentRepository
- release_credits
- ReconciliationResult
- MVP_CHECKPOINTS.md
- SubscriptionService
- card.tsx
- repository.py
- dashboard.py
- test_m42_cloud_providers.py
- v1/model_directory.py
- get_db
- api.ts
- CloudProviderRuntime
- spinner.tsx
- WalletService
- devDependencies
- CreditService
- PaymentService
- ProviderOpsService
- TranscriptRepository
- PricingSyncService
- run
- run
- AppointmentService
- TTSEngine
- agents.py
- test_m33_e2e_acceptance.py
- auth-context.tsx
- ConversationEngine
- test_m14_preflight.py
- subscriptions.py
- CurrentUser
- providers/base.py
- AgentRepository
- run
- run
- PhoneNumberService
- stt.py
- TestSuperAdmin
- LeadService
- ModelDirectoryService
- PreflightService
- run
- TestFlyToml
- UsageService
- test_m2_auth_rbac.py
- HTTPException
- dependencies
- AgentService
- test_m17_tools_handoff.py
- TestCustomerBillingPortal
- Backend API Inventory
- CampaignService
- compilerOptions
- ReconciliationService
- GoogleCloudSTTProvider
- CampaignRepository
- TTSProvider
- TelephonyProvider
- TestReconciliationChecks
- TestBillingHTTP
- test_m4_payment.py
- ElevenLabsTTSProviderV2
- SecurityAuditService
- lead_service.py
- AI Telecalling SaaS — Architecture Reference
- PhoneNumberRepository
- TestDeveloperGuide
- AI Telecalling SaaS — Technical Decisions Log
- AI Telecalling SaaS — Test Status
- backend/telephony/twilio.py
- BaseRepository
- SubscriptionPlanRepository
- test_m28_security.py
- TestPreflightChecks
- Issues Log — post-Sarvam call testing (2026-07)
- VADEndpointer
- CallSession
- LeadRepository
- UserRepository
- StructuredInstructionEditor
- TestWalletHTTP
- TestDemoSeedService
- run
- campaign_worker.py
- SubscriptionRepository
- RazorpayProvider
- _to_customer_view
- test_m7_phone_numbers.py
- main.py
- VoiceProfileRepository
- model_test_service.py
- DNCRepository
- TestHandoffService
- post_call_service.py
- AgentVersionRepository
- Real Estate Voice Agent — Execution Plan
- TestReconciliationHTTP
- VoiceProfileVersionRepository
- PaymentProvider
- hash_password
- DemoSeedService
- LatencyMetrics
- TestLeadsHTTP
- TestAnalyticsService
- run
- LLMClient
- decode_access_token
- create_token_pair
- .sync_all_rates
- datetime
- OrganizationRepository
- seed_default_plans
- TestPhoneNumberHTTP
- CampaignWorker
- TestCallPipelinePreserved
- analytics.py
- phone_number_service.py
- normalize_phone
- TestCampaignHTTP
- test_m20_post_call.py
- call_session.py
- AnalyticsService
- TestAnalyticsHTTP
- API-to-UI Mapping — Super Admin Dashboard
- InvoiceRepository
- TestDeploymentModulesImportable
- package.json
- _get_mock_db
- KnowledgeDocumentRepository
- TestWalletModels
- LatencyService
- PaymentRepository
- run
- OrderRepository
- AI Telecalling SaaS — Developer Guide
- Getting Started — Real Estate Voice Agent
- ModelSetupWizard.tsx
- datetime
- test_m3_subscriptions.py
- timedelta
- usage_service.py
- ToolRegistry
- TestSecurityAudit
- TestMultiTenancyIsolation
- TestMVPValidation
- AI Telecalling SaaS
- CHECKPOINT HISTORY
- CallService
- Settings
- CallRepository
- UsageEventRepository
- TestSubscriptionPlanModel
- AuditLogRepository
- run.py
- TestCampaignModel
- test_m27_reconciliation.py
- AI Telecalling SaaS — Development Progress
- Admin UI Implementation Plan — M40 FEAT-005A
- db.py
- KnowledgeBaseAgentRepository
- PostCallService
- TestRBACHTTP
- Transport
- MockPaymentProvider
- CredentialStore
- transcripts.py
- KnowledgeBaseRepository
- TestAuthEndpoints
- ProviderConfigurationRepo
- TestKnowledgeHTTP
- TestUsageHTTP
- TestCreditHTTP
- SarvamAgentStudioPage
- TestUsageModels
- TestTokenRefresh
- TestSecurityHTTP
- seed_default_packs
- _exists
- TestEnvExampleCompleteness
- test_m19_knowledge.py
- TestAgentHTTP
- reconciliation_report
- TestPreflightHTTP
- security_audit
- .activate_plan
- TwilioProvider
- test_m1_mongodb.py
- TestDemoHTTP
- run
- TestModels
- test_m32_documentation.py
- _read
- date-fns
- react
- TestTransferToHuman
- tailwind-merge
- TestMVPProgress
- TestReadme
- Provider Configuration
- (auth)/layout.tsx
- 5. PROVIDER ABSTRACTION
- _catalogue_to_dict
- TestEnvExample
- @types/react-dom
- test_m25_analytics.py
- TestDockerfile
- ui.tsx
- 29. AUTONOMOUS CHECKPOINT EXECUTION CONTRACT
- M41 Implementation Plan — AI Models Directory and One-Click Provider Setup
- TestGitignore
- Deployment (Fly.io)
- Local Development
- Testing
- 36. DOCUMENTATION FILES MAINTAINED DURING EXECUTION
- providers/page.tsx
- Adding a New Provider
- Installation
- nav.tsx
- NewCampaignPage
- 4. MULTI-TENANCY
- rules/graphify.md
- workflows/graphify.md
- next.config.mjs
- next-env.d.ts
- tailwind.config.ts
- 1. PRODUCT PRINCIPLES
- 35. CHECKPOINTS
- LeadsImportPage
- formatDateTime
- AgentsPage

## God Nodes (most connected - your core abstractions)
1. `get_db()` - 240 edges
2. `CurrentUser` - 210 edges
3. `WalletService` - 68 edges
4. `BaseRepository` - 65 edges
5. `SubscriptionService` - 64 edges
6. `CampaignService` - 55 edges
7. `LeadRepository` - 50 edges
8. `CreditService` - 46 edges
9. `OrganizationRepository` - 45 edges
10. `formatDateTime()` - 41 edges

## Surprising Connections (you probably didn't know these)
- `ConversationEngine` --uses--> `LLMClient`  [INFERRED]
  backend/agent/engine.py → backend/agent/llm.py
- `CallSession` --uses--> `ConversationEngine`  [INFERRED]
  backend/call_session.py → backend/agent/engine.py
- `lifespan()` --uses--> `ConversationEngine`  [INFERRED]
  backend/main.py → backend/agent/engine.py
- `ws_call()` --uses--> `ConversationEngine`  [INFERRED]
  backend/main.py → backend/agent/engine.py
- `TestCallPipelinePreserved` --uses--> `ConversationEngine`  [INFERRED]
  backend/tests/test_m15_calls.py → backend/agent/engine.py

## Import Cycles
- None detected.

## Communities (252 total, 46 thin omitted)

### Community 0 - "AppointmentRepository"
Cohesion: 0.06
Nodes (16): AppointmentRepository, datetime, Appointment repository., Upcoming scheduled/confirmed appointments., Mark existing as rescheduled and create a new one., AsyncIOMotorDatabase, _future_dt(), _get_mock_db() (+8 more)

### Community 1 - "release_credits"
Cohesion: 0.18
Nodes (12): BaseModel, field_validator, post, Settle exact credits after call completes. Idempotent., Reserve credits for an outbound call. Fails if insufficient credits., Release reserved credits (call cancelled/failed before billing)., release_credits(), ReleaseRequest (+4 more)

### Community 2 - "ReconciliationResult"
Cohesion: 0.31
Nodes (3): Result of one reconciliation check., ReconciliationResult, TestReconciliationResult

### Community 3 - "MVP_CHECKPOINTS.md"
Cohesion: 0.03
Nodes (67): 10. PHONE NUMBER PRINCIPLES, 11. AI VOICE PROFILE PRINCIPLES, 12. BUSINESS TEMPLATES, 13. AGENTS, 14. LEADS, 15. CAMPAIGNS, 16. CAMPAIGN PREFLIGHT, 17. REAL-TIME CALL PIPELINE (+59 more)

### Community 4 - "SubscriptionService"
Cohesion: 0.14
Nodes (8): Check a boolean feature gate, e.g. 'knowledge_base_enabled'., Return a safe summary of what the org is entitled to (for API response)., SubscriptionService, Changing plan config in DB changes entitlements without code changes., Activating a new plan cancels the previous one., run(), TestSubscriptionServiceEntitlements, EntitlementCheck

### Community 5 - "card.tsx"
Cohesion: 0.11
Nodes (33): AdminAnalyticsPage(), DailyEntry, MRRData, MRRMovement, PERIOD_OPTIONS, RevenueData, UsageSummary, LANGUAGE_OPTIONS (+25 more)

### Community 6 - "repository.py"
Cohesion: 0.05
Nodes (44): call_outcome(), lead_status(), Lead scoring: a simple, explainable 0-100 heuristic. Each filled qualification…, Map conversation state to a CRM status., score_lead(), call_detail(), CallDetail, CallRow (+36 more)

### Community 7 - "dashboard.py"
Cohesion: 0.06
Nodes (34): dashboard(), dashboard_analytics(), dashboard_appointments(), dashboard_calls(), dashboard_campaigns(), dashboard_credits(), dashboard_leads(), _get_analytics() (+26 more)

### Community 8 - "test_m42_cloud_providers.py"
Cohesion: 0.03
Nodes (69): GeminiLLMProvider, Any, Gemini LLM provider adapter using the official google-genai SDK. Uses…, Stream text deltas from Gemini., Gemini LLM adapter using google-genai SDK. Pass api_key at construction time;…, Generate a reply for the given conversation messages. messages: list of…, GroqLLMProvider, Any (+61 more)

### Community 9 - "v1/model_directory.py"
Cohesion: 0.09
Nodes (40): activate_configuration(), configure_provider(), ConfigureProviderBody, delete_configuration(), delete_credential(), FallbackBody, get_catalogue_entry(), get_configuration() (+32 more)

### Community 10 - "get_db"
Cohesion: 0.07
Nodes (56): admin_adjust_wallet(), admin_costs(), admin_dashboard(), admin_margins(), admin_revenue(), admin_usage(), _date_match(), get_org_wallet() (+48 more)

### Community 11 - "api.ts"
Cohesion: 0.07
Nodes (30): ChatMessage, StudioTab, TestTab, CampaignsPage(), AdminDashboard, Agent, AgentVersion, API_BASE_URL (+22 more)

### Community 12 - "CloudProviderRuntime"
Cohesion: 0.05
Nodes (54): Fernet-based credential encryption for stored provider API keys. The encryption…, AIModelCatalogue, ProviderConfiguration, ProviderCredential, TimestampedModel, MongoDB document models for the AI Models Directory. Three collections:…, One entry per (provider_name, model_id) in the catalogue., A configured provider/model for a given capability (tts/stt/llm). (+46 more)

### Community 13 - "spinner.tsx"
Cohesion: 0.10
Nodes (46): Tab, Tab, Stats, Tab, LANGUAGE_OPTIONS, STATUS_OPTIONS, STATUS_OPTIONS, STATUS_OPTIONS (+38 more)

### Community 14 - "WalletService"
Cohesion: 0.17
Nodes (6): Wallet, Grant credits from a calling pack purchase. Idempotent: same idempotency_key is…, Grant free bonus credits. Admin action., Manual credit adjustment by platform admin. credits_delta positive = add,…, Expire lots past their expiry date and remove those credits from wallet.…, WalletService

### Community 15 - "devDependencies"
Cohesion: 0.12
Nodes (17): autoprefixer, eslint, eslint-config-next, devDependencies, autoprefixer, eslint, eslint-config-next, postcss (+9 more)

### Community 16 - "CreditService"
Cohesion: 0.06
Nodes (27): CreditLotRepository, datetime, Wallet, Wallet, WalletTransaction, CreditLot, and CallingPack repositories. All credit…, Move credits from available → reserved. Returns updated doc or None if…, Move credits from reserved → available (call cancelled, not billed)., Finalize call billing: remove from reserved, add difference back to available.…, Add credits to available_credits and update a lifetime counter. (+19 more)

### Community 17 - "PaymentService"
Cohesion: 0.07
Nodes (36): create_subscription_order(), CreateSubscriptionOrderRequest, get_invoice(), _invoice_response(), list_invoices(), list_orders(), list_payments(), _order_response() (+28 more)

### Community 18 - "ProviderOpsService"
Cohesion: 0.05
Nodes (24): platform_latency(), provider_health(), provider_metrics(), get, Health summary across all providers., Per-provider metrics: success rate, latency, cost, call count., Platform-wide call latency statistics., Health status of active voice profiles and their provider routes. (+16 more)

### Community 19 - "TranscriptRepository"
Cohesion: 0.12
Nodes (9): Get existing transcript or create one. Idempotent., TranscriptRepository, Running process() twice does NOT double-count analytics., Usage event written only once per call., run(), TestPostCallService, TestTranscriptModel, TestTranscriptRepository (+1 more)

### Community 20 - "PricingSyncService"
Cohesion: 0.17
Nodes (15): PricingSettingsRepository, ProviderRateCardRepository, Repositories for ProviderRateCard and PricingSettings., PricingSyncService, AsyncIOMotorDatabase, Daily Provider Pricing and FX Synchronization Service. Ensures real-time…, Orchestrates daily rate card updates, live FX rates, and loss protection., Allow admin to instantly override a provider's rate to guard against sudden… (+7 more)

### Community 21 - "run"
Cohesion: 0.08
Nodes (15): CallingPackRepository, _get_mock_db(), SKIP, M5 tests — Calling Packs + Wallet. Tests: 1. CallingPack model — integer…, Buy 2000 credits → wallet=2000, ledger=+2000, lot=2000, 2000 base + 200 bonus = 2200 total credits granted, Every credit movement requires an immutable WalletTransaction., Same idempotency_key does not double-grant credits. (+7 more)

### Community 22 - "run"
Cohesion: 0.08
Nodes (13): _get_mock_db(), SKIP, M12 tests — Lead CRM. Tests: 1. Lead model — status validation, phone required…, Auto-mapping handles common aliases (mobile → phone, etc.)., Test 4000+ lead import — the M12 mandatory acceptance criterion., Import 4000 leads: all imported, correct count, no errors., 4000 leads, 100 on DNC → 3900 imported, 100 skipped., run() (+5 more)

### Community 23 - "AppointmentService"
Cohesion: 0.11
Nodes (28): appointment_summary(), _appt_response(), cancel_appointment(), CancelRequest, complete_appointment(), CompleteRequest, confirm_appointment(), create_appointment() (+20 more)

### Community 24 - "TTSEngine"
Cohesion: 0.07
Nodes (24): AI4BharatTTSEngine, get_tts_engine(), IndicF5Engine, OllamaTTSEngine, OrpheusEngine, pcm_to_wav(), PiperEngine, ABC (+16 more)

### Community 25 - "agents.py"
Cohesion: 0.15
Nodes (29): _agent_response(), create_agent(), create_version(), CreateAgentRequest, CreateVersionRequest, delete_agent(), get_agent(), get_pipeline_status() (+21 more)

### Community 26 - "test_m33_e2e_acceptance.py"
Cohesion: 0.09
Nodes (19): _get_mock_db(), _make_redis(), SKIP, M33 tests — Final End-to-End Acceptance. Tests the complete SaaS workflow as…, Complete E2E: signup → org → plan → credits → voice profile → agent → phone →…, Change voice profile provider route — campaign unaffected., Active campaign pins a version_id — changing routes creates new version., Org A data completely invisible to Org B end-to-end. (+11 more)

### Community 27 - "auth-context.tsx"
Cohesion: 0.06
Nodes (44): AdminGuard(), PLATFORM_ROLES, LoginPage(), handleSubmit(), SignupPage(), handleSubmit(), AuthGuard(), SettingsPage() (+36 more)

### Community 28 - "ConversationEngine"
Cohesion: 0.09
Nodes (23): ConversationEngine, _decide_stage(), TypedDict, The conversation engine: a LangGraph state machine that drives the call. Per…, Advance the conversation by one user turn. Updates `state` in place (stage,…, Ephemeral state passed through the graph for a single turn., Pure transition logic. Order matters: end > objection > booking > qualify., Extract slots + output variables + intent flags from the latest user message. (+15 more)

### Community 29 - "test_m14_preflight.py"
Cohesion: 0.13
Nodes (12): _get_mock_db(), _make_redis(), M14 tests — Campaign Pre-flight. Tests: 1. All checks pass → campaign can start…, Create an active platform voice profile with a version., Create a phone number assigned to the org., Create leads for the org., Create an active subscription for the org., _seed_credits() (+4 more)

### Community 30 - "subscriptions.py"
Cohesion: 0.09
Nodes (34): admin_activate_subscription(), admin_create_plan(), admin_list_plans(), admin_list_subscriptions(), admin_update_plan(), AdminActivateRequest, cancel_my_subscription(), change_my_plan() (+26 more)

### Community 31 - "CurrentUser"
Cohesion: 0.06
Nodes (53): billing_overview(), buy_calling_pack(), cancel_subscription(), CancelRequest, _days_remaining(), get_invoice(), get_subscription(), _invoice_response() (+45 more)

### Community 32 - "providers/base.py"
Cohesion: 0.05
Nodes (31): PhoneNumberProvider, Provider, ABC, Abstract provider interfaces for the AI Telecalling SaaS platform. Core…, MockLLMProvider, OpenAICompatibleLLMProvider, OpenAI-compatible adapter boundary; concrete transport is selected by route., MockPhoneNumberProvider (+23 more)

### Community 33 - "AgentRepository"
Cohesion: 0.10
Nodes (12): AgentRepository, BusinessTemplateRepository, Agent, AgentVersion, BusinessTemplate repositories., Get agent only if it belongs to this org (tenant isolation)., AsyncIOMotorDatabase, Agent builder service. Handles creation and management of AI calling agents and…, Seed default business templates. Idempotent., seed_templates() (+4 more)

### Community 34 - "run"
Cohesion: 0.10
Nodes (9): _get_mock_db(), SKIP, Org A cannot see Org B agents., Once published, a version cannot be modified., Solar template is configuration, not code. No if/else in service., run(), TestAgentCreation, TestAgentVersions (+1 more)

### Community 35 - "run"
Cohesion: 0.09
Nodes (9): _get_mock_db(), SKIP, run(), TestAddNote, TestBookAppointment, TestMessaging, TestScheduleCallback, TestToolRegistry (+1 more)

### Community 36 - "PhoneNumberService"
Cohesion: 0.10
Nodes (26): add_number_to_inventory(), AddNumberRequest, admin_list_numbers(), assign_number(), AssignRequest, get_my_number(), inventory_stats(), list_available_numbers() (+18 more)

### Community 37 - "stt.py"
Cohesion: 0.11
Nodes (11): FasterWhisperSTT, Speech-to-text via Groq Whisper. Sprint 1 does non-streaming transcription: the…, Routes each utterance to the best STT: Sarvam Saaras for Indian languages…, Stub for faster-whisper local runtime. Status: experimental. Raises…, Return (max no_speech_prob, min avg_logprob) across segments. Handles both…, Sarvam Saaras v3 speech-to-text — Indic-tuned, code-mixing aware.…, SarvamSTT, _segment_confidence() (+3 more)

### Community 38 - "TestSuperAdmin"
Cohesion: 0.09
Nodes (5): SKIP, M24 tests — Super Admin. Tests: 1. All admin endpoints require platform role…, Customer receives 403 on all admin endpoints., run(), TestSuperAdmin

### Community 39 - "LeadService"
Cohesion: 0.15
Nodes (24): add_to_dnc(), create_lead(), CreateLeadRequest, delete_lead(), DNCAddRequest, get_lead(), import_leads(), _lead_response() (+16 more)

### Community 40 - "ModelDirectoryService"
Cohesion: 0.03
Nodes (70): ProviderCredentialRepo, Return all credential records for a provider (including rotated history)., Return the current (non-rotated) credential for a provider, or None., Persist a new ProviderCredential document. Returns the saved document., Set rotated_at=now on all non-rotated credentials for the provider. Call before…, Delete ALL credential records for a provider (including history)., _config_to_dict(), ModelDirectoryService (+62 more)

### Community 41 - "PreflightService"
Cohesion: 0.14
Nodes (10): PreflightCheck, PreflightResult, PreflightService, Any, AsyncIOMotorDatabase, Campaign pre-flight validation service. Before a campaign starts, ALL of these…, Run all pre-flight checks for a campaign. Returns PreflightResult with all…, Check if current time is within campaign calling hours. Skipped if campaign has… (+2 more)

### Community 42 - "run"
Cohesion: 0.11
Nodes (8): SKIP, draft → running → paused → running → completed, Org B cannot start Org A's campaign., Never exceed max_concurrent_calls., 10 concurrent acquire attempts with max=5: exactly 5 succeed., run(), TestCampaignStateMachine, TestConcurrencyGate

### Community 44 - "UsageService"
Cohesion: 0.12
Nodes (23): admin_usage_summary(), list_usage_events(), provider_aggregates(), provider_breakdown(), BaseModel, datetime, get, post (+15 more)

### Community 45 - "test_m2_auth_rbac.py"
Cohesion: 0.17
Nodes (7): assert_org_access(), _org_level(), Raise 403 if `user` does not belong to `document_org_id`. Platform users with…, _get_test_app(), M2 tests — Auth + Multi-Tenancy + RBAC. Tests: 1. JWT token creation / decoding…, Build a test FastAPI app with in-memory MongoDB., TestRBACPermissions

### Community 46 - "HTTPException"
Cohesion: 0.10
Nodes (32): add_document(), associate_agent(), create_knowledge_base(), CreateDocumentRequest, CreateKBRequest, delete_document(), delete_knowledge_base(), disassociate_agent() (+24 more)

### Community 47 - "dependencies"
Cohesion: 0.12
Nodes (17): clsx, dependencies, clsx, lucide-react, marked, next, react-dom, react-hot-toast (+9 more)

### Community 48 - "AgentService"
Cohesion: 0.15
Nodes (6): AgentService, Any, Returns agent only if it belongs to this org (tenant isolation)., Create a new draft version. Optionally publish and activate it., Publish a draft version and set it as active. Immutable after this., Update a draft version's configuration. Fails if already published.

### Community 49 - "test_m17_tools_handoff.py"
Cohesion: 0.16
Nodes (24): add_note(), book_appointment(), get_customer_details(), Built-in tool implementations. Every tool: - Receives (inputs: dict, context:…, Transfer the call to a human agent with complete context. Context package…, Update lead qualification data., Create an appointment record for this lead., Add a note to the lead record. (+16 more)

### Community 50 - "TestCustomerBillingPortal"
Cohesion: 0.11
Nodes (6): SKIP, M23 tests — Customer Billing Portal. Tests: 1. /billing-portal/overview —…, Amount MUST come from server (plan lookup), not frontend., Org A cannot see Org B's invoice., run(), TestCustomerBillingPortal

### Community 51 - "Backend API Inventory"
Cohesion: 0.07
Nodes (26): Admin — `/api/v1/admin/*` (platform roles only), Agents — `/api/v1/agents/*`, Analytics — `/api/v1/analytics/*` (platform roles only), Appointments — `/api/v1/appointments/*`, Auth — `/api/v1/auth/*`, Backend API Inventory, Billing — `/api/v1/billing/*`, Calls — `/api/v1/calls/*` (+18 more)

### Community 52 - "CampaignService"
Cohesion: 0.08
Nodes (30): _campaign_response(), campaign_stats(), cancel_campaign(), create_campaign(), CreateCampaignRequest, get_campaign(), list_campaigns(), pause_campaign() (+22 more)

### Community 53 - "compilerOptions"
Cohesion: 0.07
Nodes (26): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+18 more)

### Community 54 - "ReconciliationService"
Cohesion: 0.14
Nodes (12): AsyncIOMotorDatabase, datetime, Reconciliation service — financial ledger consistency checks. Per spec, runs…, Wallet purchase credits granted but no matching payment., Same webhook event processed more than once., Invoice total != payment amount for the same order., Wallet ledger sum != wallet.balance (available+reserved)., usage_event credits != wallet.total_consumed. (+4 more)

### Community 55 - "GoogleCloudSTTProvider"
Cohesion: 0.09
Nodes (18): _detect_encoding(), GoogleCloudSTTProvider, Any, Exception, Google Cloud Speech-to-Text v2 provider adapter. Uses google-cloud-speech SDK…, Transcribe audio bytes to text using Cloud Speech-to-Text v1 batch API. audio:…, Run synchronous recognition (in a thread pool)., Detect audio encoding from header bytes. Returns (encoding_enum,… (+10 more)

### Community 56 - "CampaignRepository"
Cohesion: 0.09
Nodes (11): CampaignRepository, datetime, All running/scheduled campaigns — for worker polling., Atomic status update scoped to org., AsyncIOMotorDatabase, _get_mock_db(), _make_redis(), M13 tests — Campaign Engine. Tests: 1. Campaign model — status validation, FSM… (+3 more)

### Community 57 - "TTSProvider"
Cohesion: 0.06
Nodes (18): LLMProvider, Any, STTProvider, TTSProvider, ElevenLabsTTSProvider, Any, AsyncClient, Sarvam Bulbul managed-cloud TTS adapter. (+10 more)

### Community 58 - "TelephonyProvider"
Cohesion: 0.12
Nodes (3): TelephonyProvider, ExotelProvider, Exotel REST adapter boundary; credentials stay in platform configuration.

### Community 60 - "TestBillingHTTP"
Cohesion: 0.19
Nodes (3): Generate a valid webhook signature for testing., Org A cannot see Org B's invoice., TestBillingHTTP

### Community 61 - "test_m4_payment.py"
Cohesion: 0.11
Nodes (7): Idempotent: record a webhook event. Returns the new WebhookEvent if this…, WebhookEventRepository, _get_mock_db(), M4 tests — Razorpay payment integration. Tests: 1. Billing models — integer…, TestBillingModels, TestWebhookIdempotency, WebhookEvent

### Community 62 - "ElevenLabsTTSProviderV2"
Cohesion: 0.10
Nodes (14): ElevenLabsTTSProviderV2, Any, Exception, ElevenLabs TTS provider adapter — proper implementation. Uses the official…, Synchronous synthesis — called in a thread pool., Stream audio chunks from ElevenLabs. Yields {"audio": bytes_chunk,…, Collect streaming chunks synchronously (run in thread)., Return list of available voice dicts from the API. (+6 more)

### Community 63 - "SecurityAuditService"
Cohesion: 0.14
Nodes (10): Security audit service — static checks for known vulnerability patterns. This…, All API endpoint files must use auth dependencies., Check for secret keys in API response builders (not in models/repos)., Webhook endpoints must verify signatures., Rate limiting module must exist and auth endpoints use it., Check that repos filter by organization_id (heuristic)., File upload endpoints must validate file type/size., Runs targeted security checks against the codebase. (+2 more)

### Community 64 - "lead_service.py"
Cohesion: 0.16
Nodes (12): Lead and DNC repositories. Key design: - All queries include organization_id…, _apply_mapping(), _parse_csv(), _parse_json(), _parse_xlsx(), Any, Lead CRM service — import pipeline and CRUD. Import pipeline: 1. Parse file…, Apply column mapping to raw rows → list of dicts with standard field names.… (+4 more)

### Community 65 - "AI Telecalling SaaS — Architecture Reference"
Cohesion: 0.08
Nodes (22): 10. Reuse vs. Replace Decision Table, 1. Repository Origin, 2.1 Backend — Python / FastAPI, 2.2 Frontend — Next.js 14 / TypeScript / Tailwind, 2.3 Database (Current) — PostgreSQL, 2.4 Runtime (Current) — Redis, 2. Existing Architecture (AS-IS), 3.1 Core Changes (+14 more)

### Community 66 - "PhoneNumberRepository"
Cohesion: 0.11
Nodes (6): PhoneNumberRepository, Atomically mark a number as 'reserved' only if it is currently 'available'.…, Finalize assignment: reserved → assigned., Return number to available pool., Two concurrent atomic_reserve calls on same number: only ONE wins., TestPhoneNumberRepository

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
Cohesion: 0.12
Nodes (17): api_route, _mulaw8k_to_pcm16k(), place_outbound_call(), post, Request, WebSocket, Twilio telephony via Media Streams. Twilio speaks a websocket protocol carrying…, Twilio fetches this when a call connects; we hand it a media stream. (+9 more)

### Community 71 - "BaseRepository"
Cohesion: 0.15
Nodes (6): BaseRepository, _deserialize(), AsyncIOMotorDatabase, Clean up a MongoDB document for use with Pydantic models., Thin CRUD wrapper. Subclasses set `collection_name` and `model_class`., T

### Community 72 - "SubscriptionPlanRepository"
Cohesion: 0.12
Nodes (7): Subscription plan and subscription repositories., Platform-managed subscription plans., Active public plans, sorted by sort_order., SubscriptionPlanRepository, Subscription service — business logic layer. Responsibilities: - Entitlement…, Changing plan price in DB must not change an existing subscription snapshot., TestSubscriptionPlanRepository

### Community 73 - "test_m28_security.py"
Cohesion: 0.15
Nodes (12): _check_rate_limit(), _client_ip(), Request, rate_limit_api(), rate_limit_billing(), rate_limit_import(), General API rate limit per user., Strict rate limit for bulk import operations. (+4 more)

### Community 74 - "TestPreflightChecks"
Cohesion: 0.11
Nodes (10): SKIP, Calling hours check fails when current time is outside window., Low credits (above minimum) generate a warning, not a failure., All failing checks are reported — not just the first., Campaign with no subscription/credits/etc must not start., Campaign with all pre-flight checks passing can start., skip_preflight=True starts even if checks would fail., run() (+2 more)

### Community 75 - "Issues Log — post-Sarvam call testing (2026-07)"
Cohesion: 0.09
Nodes (21): Before → after (same harness), Conversation stalls (silent agent) — FIXED: gpt-oss reasoning, Fix order, Fix plan, Fix plan (addresses 1-5 together), Follow-up (Hindi call): echo-driven hallucination loop, Hindi/Hinglish — FIXED, Hindi / Hinglish naturalness — issues + fix plan (+13 more)

### Community 76 - "VADEndpointer"
Cohesion: 0.09
Nodes (18): Streaming voice-activity detection + endpointing. Fed continuous 16-bit mono…, Silero VAD v5 over onnxruntime. Returns P(speech) for a 512-sample window., Fallback: webrtcvad on 20 ms frames -> boolean speech., _rms_dbfs(), SileroVAD, VADEndpointer, _WebRTCVAD, reset() should clear accumulated state. (+10 more)

### Community 77 - "CallSession"
Cohesion: 0.08
Nodes (15): CallSession, Return custom greeting, or generate one in the call language., Handle explicit caller interrupt event (barge-in)., Feed a chunk of caller audio; drives VAD, barge-in, and responses., BrowserTransport, WebSocket, Speaks to the browser. Streams PCM chunks (4-byte sample-rate header + PCM)., ws_call() (+7 more)

### Community 78 - "LeadRepository"
Cohesion: 0.13
Nodes (5): LeadRepository, Lead, Return the subset of phones that already exist in this org., Insert multiple lead documents. Skips duplicates (same org + phone). Returns…, TestLeadRepository

### Community 79 - "UserRepository"
Cohesion: 0.14
Nodes (5): UserRepository, SKIP_IF_NO_MONGOMOCK, Organization A should not see Organization B's users., TestTenantIsolation, TestUserRepository

### Community 80 - "StructuredInstructionEditor"
Cohesion: 0.16
Nodes (14): ConversationPhase, ObjectionItem, StructuredInstructionEditor(), compileStructuredToMarkdown(), handleLoadTemplate(), insertPrefix(), insertSnippet(), insertVariable() (+6 more)

### Community 82 - "TestDemoSeedService"
Cohesion: 0.16
Nodes (5): _get_mock_db(), M30 tests — Demo Mode. Tests: 1. DemoSeedService.seed_all creates all required…, Provider routes in voice_profile_versions are internal only., run(), TestDemoSeedService

### Community 83 - "run"
Cohesion: 0.17
Nodes (3): run(), TestMockPaymentProvider, TestPaymentService

### Community 84 - "campaign_worker.py"
Cohesion: 0.19
Nodes (12): close_db(), _ensure_indexes(), init_db(), ping_db(), AsyncIOMotorDatabase, Connect to MongoDB and create all indexes., Health check — returns True if MongoDB is reachable., Create all collection indexes. Idempotent. (+4 more)

### Community 85 - "SubscriptionRepository"
Cohesion: 0.15
Nodes (6): Organization subscriptions — one active subscription per org., Get the current active/trialing/past_due subscription for an org., Get the most recent subscription (any status)., How many active orgs are on this plan., SubscriptionRepository, TestSubscriptionRepository

### Community 86 - "RazorpayProvider"
Cohesion: 0.14
Nodes (6): Verify Razorpay webhook signature. Signature = HMAC-SHA256(body,…, Route verified webhook event to appropriate handler., Razorpay v1 payment provider., Create a Razorpay order. Amount is in PAISE (integer). Returns:…, Verify Razorpay payment signature. Signature = HMAC-SHA256(order_id + "|" +…, RazorpayProvider

### Community 87 - "_to_customer_view"
Cohesion: 0.14
Nodes (8): Get a specific number only if it belongs to this org., Atomically assign an available number to an organization. Returns customer-safe…, Available numbers — customer-safe view (no provider details)., Strip all provider details for customer-facing responses., Numbers assigned to an org — no provider details., _to_customer_view(), Provider details must NEVER appear in customer-facing responses., TestPhoneNumberModel

### Community 88 - "test_m7_phone_numbers.py"
Cohesion: 0.12
Nodes (9): _get_mock_db(), SKIP, M7 tests — Phone Number Inventory. Tests: 1. PhoneNumber model — status…, Only one org can claim the same number — concurrent request safety., 5 concurrent assign attempts for the same number: exactly 1 wins., 5 concurrent assigns for 5 different numbers: all succeed., Even seed numbers: customer view must not expose provider., TestConcurrentAssignment (+1 more)

### Community 89 - "main.py"
Cohesion: 0.18
Nodes (16): check_all(), Health check logic for all system components., Run all health checks and return a summary., close_redis(), init_redis(), ping_redis(), Redis async client factory. Single process-wide client. Redis is used for: -…, Health check — returns True if Redis is reachable. (+8 more)

### Community 90 - "VoiceProfileRepository"
Cohesion: 0.24
Nodes (4): Return platform profiles + org's own profiles. Active only., VoiceProfileRepository, AsyncIOMotorDatabase, VoiceProfile

### Community 91 - "model_test_service.py"
Cohesion: 0.12
Nodes (9): OllamaLLMClient, Async client for a locally-running Ollama server. Ollama must be started…, Return True if the Ollama server is responding on /api/tags., Call /api/chat with the configured model and messages. Raises RuntimeError if…, Test connectivity and inference for each provider/model combination. Returns a…, [LIVE] Test LLM provider by requesting a one-sentence hello. Returns {status,…, [LIVE] Test Groq LLM with the injected API key., [LIVE] Test Gemini LLM with the injected API key. (+1 more)

### Community 92 - "DNCRepository"
Cohesion: 0.15
Nodes (6): DNCRepository, Add phone to DNC. Returns None if already on DNC., Return the subset of phones that are on DNC for this org., AsyncIOMotorDatabase, TestDNCRepository, DNCEntry

### Community 93 - "TestHandoffService"
Cohesion: 0.12
Nodes (8): HandoffService, AsyncIOMotorDatabase, Human handoff service. Packages complete call context for transfer to a human…, Generate a recommended action string based on transfer trigger., Package call context and record a human transfer request. Returns the complete…, _recommended_action(), Tool implementations must not contain business-specific branches (if/else on…, TestHandoffService

### Community 94 - "post_call_service.py"
Cohesion: 0.13
Nodes (12): Call repository — org-scoped call records., Transcript repository., _analyze_call(), _compute_score(), _derive_outcome(), _generate_summary(), Post-call processing service. Runs AFTER a call completes. Must be: -…, Derive qualification, score, outcome, and summary from call state. (+4 more)

### Community 95 - "AgentVersionRepository"
Cohesion: 0.24
Nodes (4): AgentVersionRepository, Any, Mark a version as published (immutable after this)., Update draft configuration. Raises if already published.

### Community 96 - "Real Estate Voice Agent — Execution Plan"
Cohesion: 0.11
Nodes (18): 0. The one thing that matters: latency, 1. Hardware reality & the stack decision, 2. System architecture, 3. Repository structure, 4. Conversation design (the product), 5. Data model (first cut), 6. API surface (backend), 7. Sprint plan (walking skeleton first) (+10 more)

### Community 98 - "VoiceProfileVersionRepository"
Cohesion: 0.15
Nodes (12): ProviderRoute, TimestampedModel, Voice profile models. CORE ABSTRACTION — the most important thing in the whole…, Internal provider route for one layer of a voice profile version. NEVER…, Immutable snapshot of a voice profile's provider configuration. Once published,…, Customer-facing voice profile object. The customer sees only: id, display_name,…, VoiceProfile, VoiceProfileVersion (+4 more)

### Community 99 - "PaymentProvider"
Cohesion: 0.10
Nodes (11): PaymentProvider, Verify payment signature. Returns True if valid., Fetch payment details from provider. Returns provider payment dict., Issue a refund. Returns provider refund dict., Verify webhook signature. Called synchronously (crypto only, no I/O). Returns…, Process a verified webhook event. Returns a summary dict. Raises nothing —…, Abstract payment provider. Razorpay, Stripe, etc. implement this., Unique provider identifier string, e.g. 'razorpay'. (+3 more)

### Community 100 - "hash_password"
Cohesion: 0.33
Nodes (3): hash_password(), verify_password(), TestPasswordHashing

### Community 101 - "DemoSeedService"
Cohesion: 0.18
Nodes (5): DemoSeedService, AsyncIOMotorDatabase, Demo Mode seeding service. When DEMO_MODE=true, seeds a complete demo…, Check if demo environment is already seeded., Seed the complete demo environment. Idempotent unless force=True.

### Community 102 - "LatencyMetrics"
Cohesion: 0.15
Nodes (6): _grade_latency(), LatencyMetrics, Latency metrics service. Records per-turn latency observations and provides…, In-memory latency accumulator for a single call., M16 tests — Barge-In + Latency. Tests: 1. VAD SPEECH_START event fires when…, TestLatencyMetrics

### Community 103 - "TestLeadsHTTP"
Cohesion: 0.18
Nodes (4): _make_csv(), Build a CSV bytes payload from a list of dicts., Org A DNC does not affect Org B., TestLeadsHTTP

### Community 104 - "TestAnalyticsService"
Cohesion: 0.20
Nodes (4): charge=1000, cost=300 → margin=70%, total_revenue = subscription + calling, run(), TestAnalyticsService

### Community 105 - "run"
Cohesion: 0.20
Nodes (5): Org A cannot see Org B numbers., get_number_for_org returns None if number belongs to a different org., Provider details must not leak into any customer-facing response., run(), TestPhoneNumberService

### Community 106 - "LLMClient"
Cohesion: 0.19
Nodes (9): _extract_json(), LLMClient, Yield complete sentences as soon as they're ready, so TTS can start speaking…, Non-streaming convenience helper (used by smoke tests)., Structured extraction. Never raises: returns {} if extraction fails. gpt-oss on…, Best-effort parse of a JSON object from model output. None on failure., Yield raw text deltas as the model generates them. gpt-oss on Groq…, _smoke_test() (+1 more)

### Community 107 - "decode_access_token"
Cohesion: 0.18
Nodes (9): create_access_token(), create_refresh_token(), decode_access_token(), _make_token(), Return (encoded_jwt, jti)., Returns (token, jti). Caller stores jti in Redis for revocation., TestJWTTokens, [mock] org-level token gets 403 from GET /api/v1/model-directory/catalogue. (+1 more)

### Community 108 - "create_token_pair"
Cohesion: 0.25
Nodes (9): create_token_pair(), _customer_view(), VoiceProfileService, skipif, run(), test_customer_view_has_no_internal_route_fields(), test_customer_voice_profile_hides_provider_route_and_versions_are_immutable(), test_org_voice_profile_is_tenant_isolated() (+1 more)

### Community 109 - ".sync_all_rates"
Cohesion: 0.25
Nodes (5): Any, Fetch current USD to INR exchange rate from live open FX APIs., Run daily sync of all provider rate cards and update effective rates., Return all active provider rate cards, settings, and conversion factors., Compute exact composite pipeline costs per second, minute, and volume tiers.

### Community 110 - "datetime"
Cohesion: 0.22
Nodes (6): _customer_event(), datetime, Usage summary safe to return to customer (no provider costs)., Customer-safe usage event list (strips provider cost)., Full admin summary with provider costs and margin., Strip provider cost from event before sending to customer.

### Community 111 - "OrganizationRepository"
Cohesion: 0.21
Nodes (3): OrganizationRepository, run(), TestOrganizationRepository

### Community 112 - "seed_default_plans"
Cohesion: 0.18
Nodes (4): AsyncIOMotorDatabase, Create default plans if they don't exist. Safe to call on every startup., seed_default_plans(), TestSubscriptionHTTP

### Community 113 - "TestPhoneNumberHTTP"
Cohesion: 0.21
Nodes (3): CRITICAL: provider details must never appear in customer API response., Org A cannot see Org B's assigned numbers via /my endpoint., TestPhoneNumberHTTP

### Community 114 - "CampaignWorker"
Cohesion: 0.18
Nodes (6): M31 tests — Production Deployment Configuration. Tests: 1. Dockerfile exists…, TestWorkerShutdown, CampaignWorker, Initiate the actual call and handle completion., Find running campaigns and dispatch calls., Try to start a new call for this campaign.

### Community 115 - "TestCallPipelinePreserved"
Cohesion: 0.18
Nodes (5): Verify the original call_session.py pipeline is intact., CallSession must import without errors., Silero VAD endpointer must import without errors., Transport protocol (play/clear/notify) is still intact., TestCallPipelinePreserved

### Community 116 - "analytics.py"
Cohesion: 0.16
Nodes (19): get_arpu(), get_costs(), get_daily_analytics(), get_full_report(), get_margins(), get_mrr(), get_mrr_movement(), get_revenue() (+11 more)

### Community 117 - "phone_number_service.py"
Cohesion: 0.16
Nodes (8): PhoneNumberAssignmentRepository, Phone number inventory and assignment repositories. Concurrent reservation…, AsyncIOMotorDatabase, Phone number service — inventory management. All operations record an immutable…, Seed demo phone numbers for DEMO_MODE. Idempotent., # NOTE: provider, provider_resource_id, provider_metadata,…, seed_demo_numbers(), PhoneNumberAssignment

### Community 118 - "normalize_phone"
Cohesion: 0.27
Nodes (3): normalize_phone(), Normalize a phone number to E.164 (best-effort for Indian numbers)., TestPhoneNormalization

### Community 120 - "test_m20_post_call.py"
Cohesion: 0.15
Nodes (8): _create_call(), _create_campaign(), _create_lead(), _get_mock_db(), _make_redis(), SKIP, M20 tests — Post-Call Processing. Tests: 1. Transcript model — turn storage,…, TestTranscriptsHTTP

### Community 121 - "call_session.py"
Cohesion: 0.11
Nodes (15): interpolate_template(), Any, Interpolate variables into template string supporting both {var} and {{var}}…, _looks_like_noise(), Transport-agnostic call pipeline. `CallSession` owns everything that makes a…, True if the transcript is almost certainly a hallucination or noise blip., Supported call languages (Indian-focused, backed by Sarvam Bulbul). Each entry…, Return (canonical_code, info). Falls back to the default if unknown. (+7 more)

### Community 122 - "AnalyticsService"
Cohesion: 0.19
Nodes (8): AnalyticsService, AsyncIOMotorDatabase, datetime, Revenue and margin analytics service — MVP simple approach. Per spec: "Keep MVP…, Total revenue: subscription + calling., Complete analytics report for the admin dashboard., Current MRR from active subscriptions. MRR = sum of monthly price of all…, MRR movement for a period: new_mrr — from new subscriptions started in period…

### Community 123 - "TestAnalyticsHTTP"
Cohesion: 0.21
Nodes (3): SKIP, All paise values must be integers in responses., TestAnalyticsHTTP

### Community 124 - "API-to-UI Mapping — Super Admin Dashboard"
Cohesion: 0.13
Nodes (14): API-to-UI Mapping — Super Admin Dashboard, Audit Logs, Calling Packs & Credits, Customer Dashboard Pages (for completeness), Dashboard, Organizations, Payments & Invoices, Phone Numbers (+6 more)

### Community 125 - "InvoiceRepository"
Cohesion: 0.31
Nodes (3): InvoiceRepository, SKIP, TestInvoiceRepository

### Community 127 - "package.json"
Cohesion: 0.22
Nodes (8): name, private, scripts, build, dev, lint, start, version

### Community 129 - "KnowledgeDocumentRepository"
Cohesion: 0.20
Nodes (4): KnowledgeDocumentRepository, MVP text search: keyword matching on title, content, keywords list. No vector…, Create a new version of a document. Old version is kept but deactivated., TestKnowledgeDocumentRepository

### Community 130 - "TestWalletModels"
Cohesion: 0.14
Nodes (3): Record an immutable ledger entry. Returns None if idempotency_key already…, TestWalletModels, WalletTransaction

### Community 131 - "LatencyService"
Cohesion: 0.12
Nodes (13): LatencyService, Redis-backed latency tracker for active calls., Test the barge-in flow in CallSession using mock components., SPEECH_START → _cancel_responder() + transport.clear()., During TTS playback, barge-in cancels the task., SPEECH_START with no active responder still calls transport.clear()., UTTERANCE event → new responder task created., Each processed utterance appends to self.latencies. (+5 more)

### Community 132 - "PaymentRepository"
Cohesion: 0.15
Nodes (6): PaymentRepository, Billing repositories: Order, Payment, Invoice, WebhookEvent., get_payment_provider(), AsyncIOMotorDatabase, Return the appropriate payment provider based on config., In DEMO_MODE, payment_service uses MockPaymentProvider.

### Community 134 - "OrderRepository"
Cohesion: 0.19
Nodes (3): OrderRepository, TestOrderRepository, Order

### Community 135 - "AI Telecalling SaaS — Developer Guide"
Cohesion: 0.13
Nodes (15): AI Telecalling SaaS — Developer Guide, AI Voice Profiles, Architecture Overview, Business Templates & Agents, Campaign Engine, Creating a voice profile (admin), Creating a Voice Profile (Step-by-Step), Demo Mode (+7 more)

### Community 136 - "Getting Started — Real Estate Voice Agent"
Cohesion: 0.13
Nodes (14): 0. Prerequisites (already on this machine), 1. Why this stack (read once), 2.1 Environment file, 2.2 Start Postgres + Redis, 2.3 Python environment, 2.4 Download the TTS voice, 2. One-time setup, 3. Smoke test each piece independently (+6 more)

### Community 137 - "ModelSetupWizard.tsx"
Cohesion: 0.06
Nodes (38): AdminModelsPage(), Capability, capabilityVariant(), formatFreeTierInfo(), freeTierDetails(), hostingIcon(), hostingLabel(), isStale() (+30 more)

### Community 138 - "datetime"
Cohesion: 0.25
Nodes (4): datetime, Admin aggregation including provider costs and margins., Admin: cost breakdown by provider layer., Aggregate customer-facing usage stats (no provider costs).

### Community 139 - "test_m3_subscriptions.py"
Cohesion: 0.17
Nodes (4): _get_mock_db(), SKIP_IF_NO_MONGOMOCK, M3 tests — Plans + Subscriptions. Tests: 1. SubscriptionPlan model — price…, TestSeedDefaultPlans

### Community 140 - "timedelta"
Cohesion: 0.14
Nodes (7): Create a new subscription. Cancels any existing active subscription first., Upgrade/downgrade to a new plan. Updates snapshot immediately., Per-day call/credit analytics for the last N days., Platform-wide latency stats from recent calls., _seed_appointment(), CreditLot, timedelta

### Community 141 - "usage_service.py"
Cohesion: 0.22
Nodes (6): ProviderUsageRepository, Usage event and provider usage repositories., AsyncIOMotorDatabase, Usage and cost accounting service. KEY SEPARATION (enforced here): -…, # NOTE: customer_charge_paise intentionally omitted for MVP, ProviderUsage

### Community 142 - "ToolRegistry"
Cohesion: 0.16
Nodes (7): AsyncIOMotorDatabase, Invoke a tool. Creates an immutable ToolCall audit record. Returns the tool's…, Central tool registry. Singleton-friendly; no global state., Register a tool callable., Check if tool is enabled for this org. Default: all built-ins enabled., ToolRegistry, ToolFn

### Community 144 - "TestMultiTenancyIsolation"
Cohesion: 0.21
Nodes (5): Critical: Org A must NOT be able to access Org B data., CRITICAL: Org A must receive 403 when accessing Org B., CRITICAL: Org B must receive 403 when accessing Org A., Org A cannot list users of Org B., TestMultiTenancyIsolation

### Community 145 - "TestMVPValidation"
Cohesion: 0.14
Nodes (8): Validate the overall MVP state., All 26+ API routers are wired., Every checkpoint M1-M32 has a test file (M29 used existing suite)., Core services never import provider-specific modules directly., All monetary model fields use int (paise), not float., All repositories include organization_id in their queries., Demo mode seed can be imported and creates the right data., TestMVPValidation

### Community 146 - "AI Telecalling SaaS"
Cohesion: 0.14
Nodes (10): AI Telecalling SaaS, Architecture, Checkpoints completed, Deployment, License, Project structure, Quick start (Demo Mode), Running tests (+2 more)

### Community 147 - "CHECKPOINT HISTORY"
Cohesion: 0.14
Nodes (14): CHECKPOINT HISTORY, M0 — REPOSITORY AUDIT, M10 — PROVIDER ROUTER, M11 — AGENT BUILDER, M1 — MONGODB FOUNDATION, M2 — AUTH + MULTI-TENANCY + RBAC, M3 — PLANS + SUBSCRIPTIONS, M40 — COMPLETE FRONTEND REDESIGN (+6 more)

### Community 148 - "CallService"
Cohesion: 0.16
Nodes (16): _call_response(), finalize_call(), FinalizeCallRequest, get_call(), initiate_call(), InitiateCallRequest, list_calls(), BaseModel (+8 more)

### Community 149 - "Settings"
Cohesion: 0.19
Nodes (5): Return whichever Sarvam key is set., Legacy compat for existing session.py., Settings, TestConfig, BaseSettings

### Community 150 - "CallRepository"
Cohesion: 0.07
Nodes (13): CallRepository, Finalize a call. Tenant-safe (org check on update)., AsyncIOMotorDatabase, _fund_org(), _get_mock_db(), _make_redis(), SKIP, M15 tests — Real-Time AI Calling infrastructure. Tests: 1. Call model — valid… (+5 more)

### Community 151 - "UsageEventRepository"
Cohesion: 0.15
Nodes (8): UsageEventRepository, _get_mock_db(), M21 tests — Usage + Cost. Tests: 1. UsageEvent model — integer paise,…, CRITICAL: provider_cost_paise must NEVER appear in customer event list., Each usage event has call_id + idempotency_key for billing reconstruction., run(), TestUsageEventRepository, TestUsageService

### Community 153 - "AuditLogRepository"
Cohesion: 0.05
Nodes (49): create_organization(), get_organization(), list_organizations(), OrgCreateRequest, OrgUpdateRequest, BaseModel, get, patch (+41 more)

### Community 154 - "run.py"
Cohesion: 0.22
Nodes (13): is_port_in_use(), kill_process_tree(), main(), preflight_checks(), Launch backend and frontend in separate console windows (Windows)., Run both services unified in the current console with log prefixing., Check if a TCP port is in use., Stream stdout/stderr line by line with a colored prefix. (+5 more)

### Community 156 - "test_m27_reconciliation.py"
Cohesion: 0.17
Nodes (4): _get_mock_db(), SKIP, M27 tests — Reconciliation. Tests: 1. ReconciliationResult.add_failure sets…, TestRunAll

### Community 157 - "AI Telecalling SaaS — Development Progress"
Cohesion: 0.15
Nodes (13): AI Telecalling SaaS — Development Progress, Build, CHECKPOINT HISTORY, CHECKPOINT ROADMAP, EXISTING CODEBASE SUMMARY, FEAT-001 — Design Foundations (COMPLETE — commit e04ec2d), FEAT-002 — Customer Application (COMPLETE — see commit after M40), FEAT-003/004 — Admin Application (COMPLETE) (+5 more)

### Community 158 - "Admin UI Implementation Plan — M40 FEAT-005A"
Cohesion: 0.17
Nodes (11): 1. Current State (post FEAT-005A), 2. File Structure, 3. Shared Component Reuse, 4. Auth/Permission Guard Strategy, 5. Design System, 6. API Client Namespaces (lib/api.ts), 7. Verification Commands, 8. Known Gaps / Future Work (+3 more)

### Community 159 - "db.py"
Cohesion: 0.03
Nodes (99): login(), LoginRequest, logout(), me(), MeResponse, BaseModel, field_validator, get (+91 more)

### Community 160 - "KnowledgeBaseAgentRepository"
Cohesion: 0.25
Nodes (3): KnowledgeBaseAgentRepository, AsyncIOMotorDatabase, KnowledgeBaseAgent

### Community 161 - "PostCallService"
Cohesion: 0.26
Nodes (3): PostCallService, AsyncIOMotorDatabase, Run the full post-call pipeline. Returns a summary dict of what was processed.…

### Community 162 - "TestRBACHTTP"
Cohesion: 0.26
Nodes (3): Role-based access control enforced at the HTTP layer., Viewer does not have organization_admin role., TestRBACHTTP

### Community 163 - "Transport"
Cohesion: 0.22
Nodes (6): A medium (browser websocket, phone line) the session speaks through., Send agent audio to the caller., Flush any audio already queued on the caller side (barge-in)., Deliver a metadata event (transcript, stage, etc.). May be a no-op., Transport, Protocol

### Community 164 - "MockPaymentProvider"
Cohesion: 0.09
Nodes (7): MockPaymentProvider, Verify against the fixed mock secret., Clear mock state between tests., Generate a test-valid mock signature for verify_payment., In-memory mock payment provider. No external calls., should_fail=True: verify_payment always returns False (simulate failed payment)., TestDemoModeProviders

### Community 165 - "CredentialStore"
Cohesion: 0.22
Nodes (5): CredentialStore, Thin wrapper around Fernet for storing/retrieving provider credentials., Encrypt a plaintext credential and return Fernet token bytes. Raises ValueError…, Decrypt a Fernet token and return the original plaintext string. Raises…, Return the last 4 characters of the plaintext for display purposes, or a…

### Community 166 - "transcripts.py"
Cohesion: 0.27
Nodes (11): get_transcript(), list_transcripts(), process_call(), ProcessCallRequest, BaseModel, get, post, Transcripts API. GET /api/v1/transcripts — list transcripts for org GET… (+3 more)

### Community 167 - "KnowledgeBaseRepository"
Cohesion: 0.20
Nodes (4): KnowledgeBaseRepository, Knowledge base and document repositories., Knowledge base service. MVP scope (per spec): minimal, tenant-safe. No over-…, TestKnowledgeBaseRepository

### Community 169 - "ProviderConfigurationRepo"
Cohesion: 0.24
Nodes (5): ProviderConfigurationRepo, ProviderConfiguration, Return the single active config for a capability, or None., Set is_active=False on all configs for the given capability. Returns the number…, AsyncIOMotorDatabase

### Community 173 - "SarvamAgentStudioPage"
Cohesion: 0.23
Nodes (7): SarvamAgentStudioPage(), downsampleTo16k(), handleEndCall(), handleStartCall(), playPcmChunk(), scheduleAutoHangup(), stopPlayback()

### Community 174 - "TestUsageModels"
Cohesion: 0.25
Nodes (4): Record a usage event. Returns None if idempotency_key already exists., charge=100 paise, cost=30 paise → margin=70%, TestUsageModels, UsageEvent

### Community 177 - "seed_default_packs"
Cohesion: 0.33
Nodes (4): AsyncIOMotorDatabase, Seed default calling packs. Idempotent., seed_default_packs(), Seed plans, packs, and voice profile.

### Community 180 - "test_m19_knowledge.py"
Cohesion: 0.22
Nodes (4): _extract_keywords(), Extract simple keywords from title and content (MVP: top unique words)., M19 tests — Knowledge Base. Tests: 1. KnowledgeBase model — tenant-scoped 2.…, TestKnowledgeModels

### Community 182 - "reconciliation_report"
Cohesion: 0.40
Nodes (5): get, Run all financial ledger consistency checks., Alias for /run — returns the full reconciliation report., reconciliation_report(), run_reconciliation()

### Community 184 - "security_audit"
Cohesion: 0.40
Nodes (5): get, rate_limits(), Run security audit checks against the codebase., Show configured rate limit settings., security_audit()

### Community 186 - "TwilioProvider"
Cohesion: 0.27
Nodes (4): AsyncIOMotorClient, get_client(), Twilio adapter; the Media Streams transport remains in backend.telephony.twilio., TwilioProvider

### Community 187 - "test_m1_mongodb.py"
Cohesion: 0.15
Nodes (8): Simple slugifier: lowercase, alphanumeric + hyphens., _slugify(), get_mock_db(), M1 tests — MongoDB foundation. Tests run against mongomock (in-memory MongoDB…, Return a mongomock-backed async Motor database substitute., health.check_all should return the correct structure (mocked)., TestHealthCheck, TestSlugGeneration

### Community 189 - "run"
Cohesion: 0.05
Nodes (29): _fund_org(), _get_mock_db(), _make_mock_redis(), SKIP, M6 tests — Credit Reservation + Settlement. Tests: 1. reserve() moves credits…, Same call_id reserve twice: no double-deduction., Can't release a call that was already settled., Settle bills exactly; over-reserved credits returned to available. (+21 more)

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

### Community 202 - "_catalogue_to_dict"
Cohesion: 0.29
Nodes (5): _catalogue_to_dict(), AIModelCatalogue, Return a single catalogue entry or raise LookupError., Serialize catalogue entry. No credentials present in this model., Return catalogue entries with a pricing_stale flag. Entries whose…

### Community 206 - "test_m25_analytics.py"
Cohesion: 0.22
Nodes (3): _get_mock_db(), M25 tests — Basic Revenue + Margin Analytics. Tests: 1. compute_mrr — zero when…, _seed_subscription()

### Community 209 - "29. AUTONOMOUS CHECKPOINT EXECUTION CONTRACT"
Cohesion: 0.33
Nodes (6): 29.1 `BEGIN MXX` means COMPLETE THE WHOLE CHECKPOINT, 29.2 NEVER STOP BECAUSE A TEST IS RED, 29.3 DO NOT ASK WHETHER TO CONTINUE, 29.4 FINAL RESPONSE RULE, 29.5 GENUINE BLOCKED STATE, 29. AUTONOMOUS CHECKPOINT EXECUTION CONTRACT

### Community 210 - "M41 Implementation Plan — AI Models Directory and One-Click Provider Setup"
Cohesion: 0.40
Nodes (4): Architecture decisions, Implementation Plan, Known gaps and non-blockers, M41 Implementation Plan — AI Models Directory and One-Click Provider Setup

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

### Community 216 - "providers/page.tsx"
Cohesion: 0.29
Nodes (7): AdminProvidersPage(), HealthSummary, LatencyStats, ProviderHealth, ProviderMetric, statusIcon(), VoiceProfileHealth

### Community 218 - "Adding a New Provider"
Cohesion: 0.50
Nodes (4): 1. Create the adapter, 2. Register in the provider registry, 3. Create a voice profile version using the new provider, Adding a New Provider

### Community 219 - "Installation"
Cohesion: 0.50
Nodes (4): Backend, Frontend, Installation, Prerequisites

### Community 224 - "4. MULTI-TENANCY"
Cohesion: 0.67
Nodes (3): 4. MULTI-TENANCY, Organization, Platform

### Community 255 - "formatDateTime"
Cohesion: 0.04
Nodes (27): AdminAuditLogsPage(), AdminCallingPacksPage(), AdminDashboardPage(), AdminOrgDetailPage(), AdminOrgsPage(), AdminPaymentsPage(), AdminPhoneNumbersPage(), AdminSubscriptionsPage() (+19 more)

## Knowledge Gaps
- **443 isolated node(s):** `MRRData`, `MRRMovement`, `RevenueData`, `DailyEntry`, `PERIOD_OPTIONS` (+438 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **46 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_db()` connect `get_db` to `release_credits`, `repository.py`, `dashboard.py`, `v1/model_directory.py`, `PaymentService`, `ProviderOpsService`, `CallService`, `AppointmentService`, `AuditLogRepository`, `agents.py`, `subscriptions.py`, `CurrentUser`, `db.py`, `PhoneNumberService`, `transcripts.py`, `LeadService`, `UsageService`, `HTTPException`, `CampaignService`, `reconciliation_report`, `CallSession`, `campaign_worker.py`, `main.py`, `CampaignWorker`, `analytics.py`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Why does `CurrentUser` connect `CurrentUser` to `release_credits`, `dashboard.py`, `v1/model_directory.py`, `get_db`, `CloudProviderRuntime`, `PaymentService`, `CallService`, `AppointmentService`, `AuditLogRepository`, `agents.py`, `subscriptions.py`, `db.py`, `PhoneNumberService`, `transcripts.py`, `LeadService`, `ModelDirectoryService`, `UsageService`, `test_m2_auth_rbac.py`, `HTTPException`, `CampaignService`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `BaseRepository` connect `BaseRepository` to `AppointmentRepository`, `KnowledgeDocumentRepository`, `PaymentRepository`, `OrderRepository`, `CloudProviderRuntime`, `usage_service.py`, `CreditService`, `TranscriptRepository`, `PricingSyncService`, `run`, `CallRepository`, `UsageEventRepository`, `AuditLogRepository`, `KnowledgeBaseAgentRepository`, `AgentRepository`, `KnowledgeBaseRepository`, `ModelDirectoryService`, `ProviderConfigurationRepo`, `CampaignRepository`, `test_m4_payment.py`, `lead_service.py`, `PhoneNumberRepository`, `SubscriptionPlanRepository`, `LeadRepository`, `UserRepository`, `SubscriptionRepository`, `VoiceProfileRepository`, `DNCRepository`, `post_call_service.py`, `AgentVersionRepository`, `VoiceProfileVersionRepository`, `hash_password`, `OrganizationRepository`, `phone_number_service.py`, `InvoiceRepository`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 130 inferred relationships involving `HTTPException` (e.g. with `call_detail()` and `admin_adjust_wallet()`) actually correct?**
  _`HTTPException` has 130 INFERRED edges - model-reasoned connections that need verification._
- **Are the 35 inferred relationships involving `WalletService` (e.g. with `admin_adjust_wallet()` and `get_org_wallet()`) actually correct?**
  _`WalletService` has 35 INFERRED edges - model-reasoned connections that need verification._
- **What connects `MRRData`, `MRRMovement`, `RevenueData` to the rest of the system?**
  _443 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `AppointmentRepository` be split into smaller, more focused modules?**
  _Cohesion score 0.05555555555555555 - nodes in this community are weakly interconnected._