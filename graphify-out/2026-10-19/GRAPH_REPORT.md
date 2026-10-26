# Graph Report - saas  (2026-10-19)

## Corpus Check
- 305 files · ~226,702 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4925 nodes · 10259 edges · 256 communities (216 shown, 40 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 693 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0e8db58c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AppointmentRepository
- v1/auth.py
- ReconciliationService
- MVP_CHECKPOINTS.md
- SubscriptionService
- card.tsx
- repository.py
- dashboard.py
- test_m42_cloud_providers.py
- v1/model_directory.py
- get_db
- campaigns/page.tsx
- model_directory_service.py
- spinner.tsx
- organizations.py
- dependencies
- CreditService
- PaymentService
- ProviderOpsService
- TestPostCallService
- PricingSyncService
- run
- test_m12_leads.py
- HTTPException
- TTSEngine
- agents.py
- test_m33_e2e_acceptance.py
- auth-context.tsx
- ConversationEngine
- CloudProviderRuntime
- subscriptions.py
- WalletService
- test_m8_provider_abstraction.py
- AgentVersionRepository
- run
- run
- PhoneNumberService
- config.py
- TestSuperAdmin
- leads.py
- ModelDirectoryService
- PreflightService
- run
- TestFlyToml
- UsageService
- _make_mock_redis
- CurrentUser
- models.py
- test_test_agent.py
- test_m17_tools_handoff.py
- TestCustomerBillingPortal
- Backend API Inventory
- CampaignService
- compilerOptions
- TTSProvider
- GoogleCloudSTTProvider
- CampaignRepository
- STTProvider
- TelephonyProvider
- build_demo_registry
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
- get_redis
- test_m14_preflight.py
- Issues Log — post-Sarvam call testing (2026-07)
- VADEndpointer
- CallSession
- LeadRepository
- UserRepository
- run
- TestWalletHTTP
- TestDemoSeedService
- run
- AppointmentService
- SubscriptionRepository
- KnowledgeService
- _to_customer_view
- test_m7_phone_numbers.py
- main.py
- TestCallsHTTP
- GroqLLMProvider
- DNCRepository
- TestHandoffService
- post_call_service.py
- TestAppointmentsHTTP
- Real Estate Voice Agent — Execution Plan
- RateLimitError
- VoiceProfileService
- PaymentProvider
- test_m1_mongodb.py
- DemoSeedService
- LatencyMetrics
- TestLeadsHTTP
- TestAnalyticsService
- run
- LLMClient
- test_m2_auth_rbac.py
- FastAPI
- run
- run
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
- test_m18_appointments.py
- ProviderConfigPanel.tsx
- KnowledgeDocumentRepository
- TestWalletModels
- test_m16_barge_in_latency.py
- PaymentRepository
- run
- OrderRepository
- AI Telecalling SaaS — Developer Guide
- Getting Started — Real Estate Voice Agent
- api.ts
- release_credits
- test_m3_subscriptions.py
- timedelta
- usage_service.py
- ToolRegistry
- TestSecurityAudit
- TestMultiTenancyIsolation
- TestMVPValidation
- AI Telecalling SaaS
- CHECKPOINT HISTORY
- calls.py
- Settings
- test_m15_calls.py
- UsageEventRepository
- TestConcurrencyGate
- AuditLogRepository
- run.py
- TestCampaignModel
- LeadService
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
- BrowserTransport
- TestSecurityHTTP
- seed_default_packs
- test_m31_deployment.py
- TestEnvExampleCompleteness
- test_m19_knowledge.py
- TestAgentHTTP
- TranscriptRepository
- TestPreflightHTTP
- providers/base.py
- CallService
- TwilioProvider
- organization_repo.py
- TestDemoHTTP
- run
- TestModels
- test_m32_documentation.py
- _read
- test_m13_campaigns.py
- _config_to_dict
- TestTransferToHuman
- CallRepository
- TestMVPProgress
- TestReadme
- Provider Configuration
- (auth)/layout.tsx
- 5. PROVIDER ABSTRACTION
- _catalogue_to_dict
- TestEnvExample
- Lead
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
- TestE2EHappyPath
- Adding a New Provider
- Installation
- nav.tsx
- .get_or_create
- NewCampaignPage
- 4. MULTI-TENANCY
- rules/graphify.md
- workflows/graphify.md
- next.config.mjs
- next-env.d.ts
- tailwind.config.ts
- 1. PRODUCT PRINCIPLES
- 35. CHECKPOINTS
- test_m23_customer_billing.py
- LeadsImportPage
- override_rate
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

## Communities (256 total, 40 thin omitted)

### Community 0 - "AppointmentRepository"
Cohesion: 0.15
Nodes (7): AppointmentRepository, datetime, Appointment repository., Upcoming scheduled/confirmed appointments., Mark existing as rescheduled and create a new one., SKIP, TestAppointmentRepository

### Community 1 - "v1/auth.py"
Cohesion: 0.12
Nodes (27): login(), LoginRequest, logout(), MeResponse, BaseModel, field_validator, post, Request (+19 more)

### Community 2 - "ReconciliationService"
Cohesion: 0.05
Nodes (22): AsyncIOMotorDatabase, datetime, Reconciliation service — financial ledger consistency checks. Per spec, runs…, Wallet purchase credits granted but no matching payment., Same webhook event processed more than once., Invoice total != payment amount for the same order., Wallet ledger sum != wallet.balance (available+reserved)., usage_event credits != wallet.total_consumed. (+14 more)

### Community 3 - "MVP_CHECKPOINTS.md"
Cohesion: 0.03
Nodes (67): 10. PHONE NUMBER PRINCIPLES, 11. AI VOICE PROFILE PRINCIPLES, 12. BUSINESS TEMPLATES, 13. AGENTS, 14. LEADS, 15. CAMPAIGNS, 16. CAMPAIGN PREFLIGHT, 17. REAL-TIME CALL PIPELINE (+59 more)

### Community 4 - "SubscriptionService"
Cohesion: 0.17
Nodes (6): Check a boolean feature gate, e.g. 'knowledge_base_enabled'., Activate a plan for an org. Cancels any existing subscription immediately., Upgrade or downgrade. Takes effect immediately., Return a safe summary of what the org is entitled to (for API response)., SubscriptionService, EntitlementCheck

### Community 5 - "card.tsx"
Cohesion: 0.11
Nodes (33): AdminAnalyticsPage(), DailyEntry, MRRData, MRRMovement, PERIOD_OPTIONS, RevenueData, UsageSummary, LANGUAGE_OPTIONS (+25 more)

### Community 6 - "repository.py"
Cohesion: 0.10
Nodes (30): call_outcome(), lead_status(), Lead scoring: a simple, explainable 0-100 heuristic. Each filled qualification…, Map conversation state to a CRM status., score_lead(), call_detail(), CallDetail, CallRow (+22 more)

### Community 7 - "dashboard.py"
Cohesion: 0.06
Nodes (35): dashboard(), dashboard_analytics(), dashboard_appointments(), dashboard_calls(), dashboard_campaigns(), dashboard_credits(), dashboard_leads(), _get_analytics() (+27 more)

### Community 8 - "test_m42_cloud_providers.py"
Cohesion: 0.05
Nodes (55): GeminiLLMProvider, Any, Stream text deltas from Gemini., Gemini LLM adapter using google-genai SDK. Pass api_key at construction time;…, Generate a reply for the given conversation messages. messages: list of…, M42 Cloud AI Providers — contract tests with mocked HTTP. All tests use…, [mock] 401 error does not expose the API key in the exception message., [mock] 429 rate limit error produces clean message without key. (+47 more)

### Community 9 - "v1/model_directory.py"
Cohesion: 0.09
Nodes (40): activate_configuration(), configure_provider(), ConfigureProviderBody, delete_configuration(), delete_credential(), FallbackBody, get_catalogue_entry(), get_configuration() (+32 more)

### Community 10 - "get_db"
Cohesion: 0.06
Nodes (61): admin_adjust_wallet(), admin_costs(), admin_dashboard(), admin_margins(), admin_revenue(), admin_usage(), _date_match(), get_org_wallet() (+53 more)

### Community 11 - "campaigns/page.tsx"
Cohesion: 0.14
Nodes (12): ChatMessage, StudioTab, TestTab, CampaignsPage(), Agent, AgentVersion, Campaign, PhoneNumber (+4 more)

### Community 12 - "model_directory_service.py"
Cohesion: 0.07
Nodes (26): Fernet-based credential encryption for stored provider API keys. The encryption…, AIModelCatalogue, ProviderCredential, TimestampedModel, MongoDB document models for the AI Models Directory. Three collections:…, One entry per (provider_name, model_id) in the catalogue., Fernet-encrypted credential for a provider. Multiple rows per provider_name are…, AIModelCatalogueRepo (+18 more)

### Community 13 - "spinner.tsx"
Cohesion: 0.10
Nodes (46): Tab, Tab, Stats, Tab, LANGUAGE_OPTIONS, STATUS_OPTIONS, STATUS_OPTIONS, STATUS_OPTIONS (+38 more)

### Community 14 - "organizations.py"
Cohesion: 0.17
Nodes (18): create_organization(), get_organization(), list_organizations(), OrgCreateRequest, OrgUpdateRequest, BaseModel, get, patch (+10 more)

### Community 15 - "dependencies"
Cohesion: 0.04
Nodes (48): autoprefixer, clsx, date-fns, eslint, eslint-config-next, dependencies, clsx, date-fns (+40 more)

### Community 16 - "CreditService"
Cohesion: 0.06
Nodes (25): CreditLotRepository, datetime, Wallet, WalletTransaction, CreditLot, and CallingPack repositories. All credit…, Move credits from available → reserved. Returns updated doc or None if…, Move credits from reserved → available (call cancelled, not billed)., Finalize call billing: remove from reserved, add difference back to available.…, Add credits to available_credits and update a lifetime counter., Remove expired credits from available_credits. (+17 more)

### Community 17 - "PaymentService"
Cohesion: 0.07
Nodes (36): create_subscription_order(), CreateSubscriptionOrderRequest, get_invoice(), _invoice_response(), list_invoices(), list_orders(), list_payments(), _order_response() (+28 more)

### Community 18 - "ProviderOpsService"
Cohesion: 0.05
Nodes (24): platform_latency(), provider_health(), provider_metrics(), get, Health summary across all providers., Per-provider metrics: success rate, latency, cost, call count., Platform-wide call latency statistics., Health status of active voice profiles and their provider routes. (+16 more)

### Community 19 - "TestPostCallService"
Cohesion: 0.22
Nodes (5): SKIP, Running process() twice does NOT double-count analytics., Usage event written only once per call., run(), TestPostCallService

### Community 20 - "PricingSyncService"
Cohesion: 0.11
Nodes (20): PricingSettingsRepository, ProviderRateCardRepository, Repositories for ProviderRateCard and PricingSettings., PricingSyncService, Any, AsyncIOMotorDatabase, Daily Provider Pricing and FX Synchronization Service. Ensures real-time…, Orchestrates daily rate card updates, live FX rates, and loss protection. (+12 more)

### Community 21 - "run"
Cohesion: 0.08
Nodes (15): CallingPackRepository, _get_mock_db(), SKIP, M5 tests — Calling Packs + Wallet. Tests: 1. CallingPack model — integer…, Buy 2000 credits → wallet=2000, ledger=+2000, lot=2000, 2000 base + 200 bonus = 2200 total credits granted, Every credit movement requires an immutable WalletTransaction., Same idempotency_key does not double-grant credits. (+7 more)

### Community 22 - "test_m12_leads.py"
Cohesion: 0.10
Nodes (9): _get_mock_db(), SKIP, M12 tests — Lead CRM. Tests: 1. Lead model — status validation, phone required…, Test 4000+ lead import — the M12 mandatory acceptance criterion., Import 4000 leads: all imported, correct count, no errors., 4000 leads, 100 on DNC → 3900 imported, 100 skipped., TestJSONImport, TestLargeImport (+1 more)

### Community 23 - "HTTPException"
Cohesion: 0.12
Nodes (36): delete_agent(), delete, appointment_summary(), _appt_response(), cancel_appointment(), CancelRequest, complete_appointment(), CompleteRequest (+28 more)

### Community 24 - "TTSEngine"
Cohesion: 0.07
Nodes (24): AI4BharatTTSEngine, get_tts_engine(), IndicF5Engine, OllamaTTSEngine, OrpheusEngine, pcm_to_wav(), PiperEngine, ABC (+16 more)

### Community 25 - "agents.py"
Cohesion: 0.09
Nodes (33): _agent_response(), create_agent(), create_version(), CreateAgentRequest, CreateVersionRequest, get_agent(), get_pipeline_status(), improve_instructions() (+25 more)

### Community 26 - "test_m33_e2e_acceptance.py"
Cohesion: 0.10
Nodes (16): _get_mock_db(), _make_redis(), SKIP, M33 tests — Final End-to-End Acceptance. Tests the complete SaaS workflow as…, Change voice profile provider route — campaign unaffected., Active campaign pins a version_id — changing routes creates new version., Org A data completely invisible to Org B end-to-end., run() (+8 more)

### Community 27 - "auth-context.tsx"
Cohesion: 0.07
Nodes (39): AdminGuard(), PLATFORM_ROLES, LoginPage(), handleSubmit(), SignupPage(), handleSubmit(), AuthGuard(), SettingsPage() (+31 more)

### Community 28 - "ConversationEngine"
Cohesion: 0.09
Nodes (23): ConversationEngine, _decide_stage(), TypedDict, The conversation engine: a LangGraph state machine that drives the call. Per…, Advance the conversation by one user turn. Updates `state` in place (stage,…, Ephemeral state passed through the graph for a single turn., Pure transition logic. Order matters: end > objection > booking > qualify., Extract slots + output variables + intent flags from the latest user message. (+15 more)

### Community 29 - "CloudProviderRuntime"
Cohesion: 0.13
Nodes (21): ProviderConfiguration, A configured provider/model for a given capability (tts/stt/llm)., CloudProviderRuntime, _llm_options(), Any, ProviderConfiguration, Build cloud AI providers from active encrypted admin configurations. This is…, Loads active provider configurations without exposing their credentials. (+13 more)

### Community 30 - "subscriptions.py"
Cohesion: 0.09
Nodes (34): admin_activate_subscription(), admin_create_plan(), admin_list_plans(), admin_list_subscriptions(), admin_update_plan(), AdminActivateRequest, cancel_my_subscription(), change_my_plan() (+26 more)

### Community 31 - "WalletService"
Cohesion: 0.07
Nodes (42): billing_overview(), buy_calling_pack(), cancel_subscription(), CancelRequest, _days_remaining(), get_invoice(), get_subscription(), _invoice_response() (+34 more)

### Community 32 - "test_m8_provider_abstraction.py"
Cohesion: 0.11
Nodes (10): MockLLMProvider, OpenAICompatibleLLMProvider, MockSTTProvider, MockTTSProvider, M8 provider contracts and registry tests., run(), test_demo_registry_registers_all_runtime_provider_categories(), test_live_http_adapters_normalize_provider_responses_without_network() (+2 more)

### Community 33 - "AgentVersionRepository"
Cohesion: 0.09
Nodes (12): AgentRepository, AgentVersionRepository, BusinessTemplateRepository, Any, Agent, AgentVersion, BusinessTemplate repositories., Mark a version as published (immutable after this)., Update draft configuration. Raises if already published., Get agent only if it belongs to this org (tenant isolation). (+4 more)

### Community 34 - "run"
Cohesion: 0.09
Nodes (11): _get_mock_db(), SKIP, M11 tests — Agent Builder. Tests: 1. BusinessTemplate — 7 templates seeded,…, Org A cannot see Org B agents., Once published, a version cannot be modified., Solar template is configuration, not code. No if/else in service., run(), _seed() (+3 more)

### Community 35 - "run"
Cohesion: 0.09
Nodes (9): _get_mock_db(), SKIP, run(), TestAddNote, TestBookAppointment, TestMessaging, TestScheduleCallback, TestToolRegistry (+1 more)

### Community 36 - "PhoneNumberService"
Cohesion: 0.13
Nodes (23): add_number_to_inventory(), AddNumberRequest, admin_list_numbers(), assign_number(), AssignRequest, get_my_number(), inventory_stats(), list_available_numbers() (+15 more)

### Community 37 - "config.py"
Cohesion: 0.10
Nodes (12): FasterWhisperSTT, Speech-to-text via Groq Whisper. Sprint 1 does non-streaming transcription: the…, Routes each utterance to the best STT: Sarvam Saaras for Indian languages…, Stub for faster-whisper local runtime. Status: experimental. Raises…, Return (max no_speech_prob, min avg_logprob) across segments. Handles both…, Sarvam Saaras v3 speech-to-text — Indic-tuned, code-mixing aware.…, SarvamSTT, _segment_confidence() (+4 more)

### Community 38 - "TestSuperAdmin"
Cohesion: 0.12
Nodes (3): SKIP, Customer receives 403 on all admin endpoints., TestSuperAdmin

### Community 39 - "leads.py"
Cohesion: 0.18
Nodes (22): add_to_dnc(), create_lead(), CreateLeadRequest, delete_lead(), DNCAddRequest, get_lead(), import_leads(), _lead_response() (+14 more)

### Community 40 - "ModelDirectoryService"
Cohesion: 0.06
Nodes (49): ProviderCredentialRepo, Set rotated_at=now on all non-rotated credentials for the provider. Call before…, Delete ALL credential records for a provider (including history)., ModelDirectoryService, AsyncIOMotorDatabase, Deactivate and delete a configuration., Delete all credentials and all configurations for a provider., ModelTestService (+41 more)

### Community 41 - "PreflightService"
Cohesion: 0.13
Nodes (10): PreflightCheck, PreflightResult, PreflightService, Any, AsyncIOMotorDatabase, Campaign pre-flight validation service. Before a campaign starts, ALL of these…, Run all pre-flight checks for a campaign. Returns PreflightResult with all…, Check if current time is within campaign calling hours. Skipped if campaign has… (+2 more)

### Community 42 - "run"
Cohesion: 0.19
Nodes (4): draft → running → paused → running → completed, Org B cannot start Org A's campaign., run(), TestCampaignStateMachine

### Community 44 - "UsageService"
Cohesion: 0.12
Nodes (23): admin_usage_summary(), list_usage_events(), provider_aggregates(), provider_breakdown(), BaseModel, datetime, get, post (+15 more)

### Community 45 - "_make_mock_redis"
Cohesion: 0.13
Nodes (9): _get_mock_db(), _make_mock_redis(), 10 concurrent calls — no double-spend, no negative credits., 10 concurrent reserves of 60 credits with 600 total: all succeed., 5 calls succeed, 6th fails (300 credits = exactly 5 × 60)., Settling 10 calls concurrently: total consumed = sum of actuals., Hammer reserves beyond balance: wallet always ≥ 0., In-memory dict-based Redis mock for credit reservation keys. (+1 more)

### Community 46 - "CurrentUser"
Cohesion: 0.08
Nodes (42): demo_status(), get, post, Allow if DEMO_MODE=true OR caller is platform admin., Check demo mode status and seeding state., Seed the demo environment. Pass force=true to re-seed., _require_demo_or_admin(), seed_demo() (+34 more)

### Community 47 - "models.py"
Cohesion: 0.14
Nodes (11): Alembic environment. Runs synchronously (psycopg3 sync) using our models'…, Base, Booking, SQLAlchemy models: leads, calls, turns, bookings. Slots…, Turn, _uuid_col(), Append turns to transcript and update count., TestTranscriptModel (+3 more)

### Community 48 - "test_test_agent.py"
Cohesion: 0.13
Nodes (13): GroqSTTProvider, Any, Groq Whisper STT provider adapter., Any, AsyncClient, Sarvam Saaras STT provider adapter., SarvamSTTProvider, Unit tests for the Test Agent browser runner & cloud providers. (+5 more)

### Community 49 - "test_m17_tools_handoff.py"
Cohesion: 0.16
Nodes (24): add_note(), book_appointment(), get_customer_details(), Built-in tool implementations. Every tool: - Receives (inputs: dict, context:…, Transfer the call to a human agent with complete context. Context package…, Update lead qualification data., Create an appointment record for this lead., Add a note to the lead record. (+16 more)

### Community 50 - "TestCustomerBillingPortal"
Cohesion: 0.14
Nodes (5): SKIP, Amount MUST come from server (plan lookup), not frontend., Org A cannot see Org B's invoice., run(), TestCustomerBillingPortal

### Community 51 - "Backend API Inventory"
Cohesion: 0.07
Nodes (26): Admin — `/api/v1/admin/*` (platform roles only), Agents — `/api/v1/agents/*`, Analytics — `/api/v1/analytics/*` (platform roles only), Appointments — `/api/v1/appointments/*`, Auth — `/api/v1/auth/*`, Backend API Inventory, Billing — `/api/v1/billing/*`, Calls — `/api/v1/calls/*` (+18 more)

### Community 52 - "CampaignService"
Cohesion: 0.08
Nodes (30): _campaign_response(), campaign_stats(), cancel_campaign(), create_campaign(), CreateCampaignRequest, get_campaign(), list_campaigns(), pause_campaign() (+22 more)

### Community 53 - "compilerOptions"
Cohesion: 0.07
Nodes (26): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+18 more)

### Community 54 - "TTSProvider"
Cohesion: 0.09
Nodes (8): TTSProvider, ElevenLabsTTSProvider, Any, AsyncClient, Sarvam Bulbul managed-cloud TTS adapter., SarvamTTSProvider, CloudCallTTS, Exposes the established TTSEngine protocol over a cloud TTS provider.

### Community 55 - "GoogleCloudSTTProvider"
Cohesion: 0.09
Nodes (18): _detect_encoding(), GoogleCloudSTTProvider, Any, Exception, Google Cloud Speech-to-Text v2 provider adapter. Uses google-cloud-speech SDK…, Transcribe audio bytes to text using Cloud Speech-to-Text v1 batch API. audio:…, Run synchronous recognition (in a thread pool)., Detect audio encoding from header bytes. Returns (encoding_enum,… (+10 more)

### Community 56 - "CampaignRepository"
Cohesion: 0.15
Nodes (5): CampaignRepository, All running/scheduled campaigns — for worker polling., Atomic status update scoped to org., AsyncIOMotorDatabase, TestCampaignRepository

### Community 57 - "STTProvider"
Cohesion: 0.09
Nodes (12): LLMProvider, Any, STTProvider, Gemini LLM provider adapter using the official google-genai SDK. Uses…, OpenAI-compatible adapter boundary; concrete transport is selected by route., build_cloud_call_components(), CloudCallComponents, CloudCallLLM (+4 more)

### Community 58 - "TelephonyProvider"
Cohesion: 0.09
Nodes (4): TelephonyProvider, ExotelProvider, Exotel REST adapter boundary; credentials stay in platform configuration., MockTelephonyProvider

### Community 59 - "build_demo_registry"
Cohesion: 0.23
Nodes (11): build_demo_registry(), ProviderRouter, Internal provider selection with health, capability, language, and fallback…, Resolve a route and durably retain any failover event for operations review., ResolvedProvider, skipif, run(), test_router_falls_back_and_records_failover() (+3 more)

### Community 60 - "TestBillingHTTP"
Cohesion: 0.19
Nodes (3): Generate a valid webhook signature for testing., Org A cannot see Org B's invoice., TestBillingHTTP

### Community 61 - "test_m4_payment.py"
Cohesion: 0.14
Nodes (6): Idempotent: record a webhook event. Returns the new WebhookEvent if this…, WebhookEventRepository, M4 tests — Razorpay payment integration. Tests: 1. Billing models — integer…, TestBillingModels, TestWebhookIdempotency, WebhookEvent

### Community 62 - "ElevenLabsTTSProviderV2"
Cohesion: 0.10
Nodes (14): ElevenLabsTTSProviderV2, Any, Exception, ElevenLabs TTS provider adapter — proper implementation. Uses the official…, Synchronous synthesis — called in a thread pool., Stream audio chunks from ElevenLabs. Yields {"audio": bytes_chunk,…, Collect streaming chunks synchronously (run in thread)., Return list of available voice dicts from the API. (+6 more)

### Community 63 - "SecurityAuditService"
Cohesion: 0.11
Nodes (15): get, rate_limits(), Run security audit checks against the codebase., Show configured rate limit settings., security_audit(), Security audit service — static checks for known vulnerability patterns. This…, All API endpoint files must use auth dependencies., Check for secret keys in API response builders (not in models/repos). (+7 more)

### Community 64 - "lead_service.py"
Cohesion: 0.19
Nodes (11): _apply_mapping(), _parse_csv(), _parse_json(), _parse_xlsx(), Any, Lead CRM service — import pipeline and CRUD. Import pipeline: 1. Parse file…, Apply column mapping to raw rows → list of dicts with standard field names.…, Full import pipeline. Returns: { imported: int, skipped_dnc: int,… (+3 more)

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
Cohesion: 0.08
Nodes (15): Audit log repository. Write-only (no updates/deletes)., BaseRepository, _deserialize(), AsyncIOMotorDatabase, Base repository with common MongoDB CRUD operations. All repositories follow…, Prep a document dict for MongoDB: ensure _id is set., Clean up a MongoDB document for use with Pydantic models., Thin CRUD wrapper. Subclasses set `collection_name` and `model_class`. (+7 more)

### Community 72 - "SubscriptionPlanRepository"
Cohesion: 0.12
Nodes (7): Subscription plan and subscription repositories., Platform-managed subscription plans., Active public plans, sorted by sort_order., SubscriptionPlanRepository, Subscription service — business logic layer. Responsibilities: - Entitlement…, Changing plan price in DB must not change an existing subscription snapshot., TestSubscriptionPlanRepository

### Community 73 - "get_redis"
Cohesion: 0.13
Nodes (18): _check_rate_limit(), _client_ip(), Request, rate_limit_api(), rate_limit_auth(), rate_limit_billing(), rate_limit_import(), Rate limiting via Redis sliding-window counters. Per-IP and per-user limits to… (+10 more)

### Community 74 - "test_m14_preflight.py"
Cohesion: 0.06
Nodes (22): _get_mock_db(), _make_redis(), SKIP, M14 tests — Campaign Pre-flight. Tests: 1. All checks pass → campaign can start…, Create a published agent version., Create a phone number assigned to the org., Create leads for the org., Calling hours check fails when current time is outside window. (+14 more)

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
Cohesion: 0.13
Nodes (5): LeadRepository, Lead, Return the subset of phones that already exist in this org., Insert multiple lead documents. Skips duplicates (same org + phone). Returns…, TestLeadRepository

### Community 79 - "UserRepository"
Cohesion: 0.14
Nodes (5): UserRepository, SKIP_IF_NO_MONGOMOCK, Organization A should not see Organization B's users., TestTenantIsolation, TestUserRepository

### Community 80 - "run"
Cohesion: 0.18
Nodes (6): SKIP_IF_NO_MONGOMOCK, Changing plan config in DB changes entitlements without code changes., Activating a new plan cancels the previous one., run(), TestSeedDefaultPlans, TestSubscriptionServiceEntitlements

### Community 82 - "TestDemoSeedService"
Cohesion: 0.20
Nodes (4): SKIP, Provider routes in voice_profile_versions are internal only., run(), TestDemoSeedService

### Community 83 - "run"
Cohesion: 0.17
Nodes (3): run(), TestMockPaymentProvider, TestPaymentService

### Community 84 - "AppointmentService"
Cohesion: 0.15
Nodes (5): AppointmentService, _appt_brief(), AsyncIOMotorDatabase, datetime, Appointment service. Handles: - Creating appointments (standalone or from a…

### Community 85 - "SubscriptionRepository"
Cohesion: 0.15
Nodes (6): Organization subscriptions — one active subscription per org., Get the current active/trialing/past_due subscription for an org., Get the most recent subscription (any status)., How many active orgs are on this plan., SubscriptionRepository, TestSubscriptionRepository

### Community 86 - "KnowledgeService"
Cohesion: 0.11
Nodes (4): KnowledgeService, Update creates a new version. Old version is preserved but deactivated., Search across all KBs associated with an agent., Retrieve relevant knowledge as plain text for injection into the LLM context.…

### Community 87 - "_to_customer_view"
Cohesion: 0.10
Nodes (11): Get a specific number only if it belongs to this org., Atomically assign an available number to an organization. Returns customer-safe…, Available numbers — customer-safe view (no provider details)., Full inventory view for platform admin — includes provider details., Strip all provider details for customer-facing responses., Full view including provider details — admin only., Numbers assigned to an org — no provider details., _to_admin_view() (+3 more)

### Community 88 - "test_m7_phone_numbers.py"
Cohesion: 0.12
Nodes (9): _get_mock_db(), SKIP, M7 tests — Phone Number Inventory. Tests: 1. PhoneNumber model — status…, Only one org can claim the same number — concurrent request safety., 5 concurrent assign attempts for the same number: exactly 1 wins., 5 concurrent assigns for 5 different numbers: all succeed., Even seed numbers: customer view must not expose provider., TestConcurrentAssignment (+1 more)

### Community 89 - "main.py"
Cohesion: 0.11
Nodes (26): close_db(), _ensure_indexes(), init_db(), ping_db(), AsyncIOMotorDatabase, Connect to MongoDB and create all indexes., Health check — returns True if MongoDB is reachable., Create all collection indexes. Idempotent. (+18 more)

### Community 91 - "GroqLLMProvider"
Cohesion: 0.06
Nodes (22): OllamaLLMClient, Async client for a locally-running Ollama server. Ollama must be started…, Return True if the Ollama server is responding on /api/tags., Call /api/chat with the configured model and messages. Raises RuntimeError if…, GroqLLMProvider, Any, Exception, Groq LLM provider adapter. Uses the official groq Python SDK (OpenAI-compatible… (+14 more)

### Community 92 - "DNCRepository"
Cohesion: 0.18
Nodes (5): DNCRepository, Add phone to DNC. Returns None if already on DNC., Return the subset of phones that are on DNC for this org., TestDNCRepository, DNCEntry

### Community 93 - "TestHandoffService"
Cohesion: 0.12
Nodes (8): HandoffService, AsyncIOMotorDatabase, Human handoff service. Packages complete call context for transfer to a human…, Generate a recommended action string based on transfer trigger., Package call context and record a human transfer request. Returns the complete…, _recommended_action(), Tool implementations must not contain business-specific branches (if/else on…, TestHandoffService

### Community 94 - "post_call_service.py"
Cohesion: 0.13
Nodes (12): Call, _analyze_call(), _compute_score(), _derive_outcome(), _generate_summary(), Post-call processing service. Runs AFTER a call completes. Must be: -…, Derive qualification, score, outcome, and summary from call state., Simple slot-based scoring. 15 pts per filled slot, bonuses for intent. (+4 more)

### Community 96 - "Real Estate Voice Agent — Execution Plan"
Cohesion: 0.11
Nodes (18): 0. The one thing that matters: latency, 1. Hardware reality & the stack decision, 2. System architecture, 3. Repository structure, 4. Conversation design (the product), 5. Data model (first cut), 6. API surface (backend), 7. Sprint plan (walking skeleton first) (+10 more)

### Community 97 - "RateLimitError"
Cohesion: 0.18
Nodes (7): Exception, RateLimitError, Run an inference test for the given configuration. Raises: LookupError — config…, Raised when the test-call rate limit is exceeded., Fetch and decrypt the current credential. Returns None if not set., Raise RateLimitError if too many test calls in the last hour., Insert a record into provider_test_log for rate-limiting.

### Community 98 - "VoiceProfileService"
Cohesion: 0.07
Nodes (28): ProviderRoute, TimestampedModel, Voice profile models. CORE ABSTRACTION — the most important thing in the whole…, Internal provider route for one layer of a voice profile version. NEVER…, Immutable snapshot of a voice profile's provider configuration. Once published,…, Customer-facing voice profile object. The customer sees only: id, display_name,…, VoiceProfile, VoiceProfileVersion (+20 more)

### Community 99 - "PaymentProvider"
Cohesion: 0.06
Nodes (17): PaymentProvider, Verify payment signature. Returns True if valid., Fetch payment details from provider. Returns provider payment dict., Issue a refund. Returns provider refund dict., Verify webhook signature. Called synchronously (crypto only, no I/O). Returns…, Process a verified webhook event. Returns a summary dict. Raises nothing —…, Abstract payment provider. Razorpay, Stripe, etc. implement this., Unique provider identifier string, e.g. 'razorpay'. (+9 more)

### Community 100 - "test_m1_mongodb.py"
Cohesion: 0.15
Nodes (8): hash_password(), verify_password(), get_mock_db(), M1 tests — MongoDB foundation. Tests run against mongomock (in-memory MongoDB…, Return a mongomock-backed async Motor database substitute., health.check_all should return the correct structure (mocked)., TestHealthCheck, TestPasswordHashing

### Community 101 - "DemoSeedService"
Cohesion: 0.21
Nodes (4): DemoSeedService, AsyncIOMotorDatabase, Check if demo environment is already seeded., Seed the complete demo environment. Idempotent unless force=True.

### Community 102 - "LatencyMetrics"
Cohesion: 0.16
Nodes (5): _grade_latency(), LatencyMetrics, Latency metrics service. Records per-turn latency observations and provides…, In-memory latency accumulator for a single call., TestLatencyMetrics

### Community 103 - "TestLeadsHTTP"
Cohesion: 0.18
Nodes (4): _make_csv(), Build a CSV bytes payload from a list of dicts., Org A DNC does not affect Org B., TestLeadsHTTP

### Community 104 - "TestAnalyticsService"
Cohesion: 0.20
Nodes (4): charge=1000, cost=300 → margin=70%, total_revenue = subscription + calling, run(), TestAnalyticsService

### Community 105 - "run"
Cohesion: 0.18
Nodes (5): Org A cannot see Org B numbers., get_number_for_org returns None if number belongs to a different org., Provider details must not leak into any customer-facing response., run(), TestPhoneNumberService

### Community 106 - "LLMClient"
Cohesion: 0.19
Nodes (9): _extract_json(), LLMClient, Yield complete sentences as soon as they're ready, so TTS can start speaking…, Non-streaming convenience helper (used by smoke tests)., Structured extraction. Never raises: returns {} if extraction fails. gpt-oss on…, Best-effort parse of a JSON object from model output. None on failure., Yield raw text deltas as the model generates them. gpt-oss on Groq…, _smoke_test() (+1 more)

### Community 107 - "test_m2_auth_rbac.py"
Cohesion: 0.13
Nodes (12): create_access_token(), create_refresh_token(), decode_access_token(), _make_token(), Return (encoded_jwt, jti)., Returns (token, jti). Caller stores jti in Redis for revocation., _get_test_app(), M2 tests — Auth + Multi-Tenancy + RBAC. Tests: 1. JWT token creation / decoding… (+4 more)

### Community 108 - "FastAPI"
Cohesion: 0.20
Nodes (4): create_token_pair(), _fund_org(), Helper: give an org N credits via bonus., FastAPI

### Community 109 - "run"
Cohesion: 0.18
Nodes (4): Auto-mapping handles common aliases (mobile → phone, etc.)., run(), TestCSVImport, TestLeadService

### Community 111 - "OrganizationRepository"
Cohesion: 0.21
Nodes (3): OrganizationRepository, run(), TestOrganizationRepository

### Community 112 - "seed_default_plans"
Cohesion: 0.21
Nodes (4): AsyncIOMotorDatabase, Create default plans if they don't exist. Safe to call on every startup., seed_default_plans(), TestSubscriptionHTTP

### Community 113 - "TestPhoneNumberHTTP"
Cohesion: 0.21
Nodes (3): CRITICAL: provider details must never appear in customer API response., Org A cannot see Org B's assigned numbers via /my endpoint., TestPhoneNumberHTTP

### Community 114 - "CampaignWorker"
Cohesion: 0.20
Nodes (5): TestWorkerShutdown, CampaignWorker, Initiate the actual call and handle completion., Find running campaigns and dispatch calls., Try to start a new call for this campaign.

### Community 115 - "TestCallPipelinePreserved"
Cohesion: 0.18
Nodes (5): Verify the original call_session.py pipeline is intact., CallSession must import without errors., Silero VAD endpointer must import without errors., Transport protocol (play/clear/notify) is still intact., TestCallPipelinePreserved

### Community 116 - "analytics.py"
Cohesion: 0.16
Nodes (19): get_arpu(), get_costs(), get_daily_analytics(), get_full_report(), get_margins(), get_mrr(), get_mrr_movement(), get_revenue() (+11 more)

### Community 117 - "phone_number_service.py"
Cohesion: 0.19
Nodes (8): PhoneNumberAssignmentRepository, Phone number inventory and assignment repositories. Concurrent reservation…, AsyncIOMotorDatabase, Phone number service — inventory management. All operations record an immutable…, Seed demo phone numbers for DEMO_MODE. Idempotent., # NOTE: provider, provider_resource_id, provider_metadata,…, seed_demo_numbers(), PhoneNumberAssignment

### Community 118 - "normalize_phone"
Cohesion: 0.36
Nodes (3): normalize_phone(), Normalize a phone number to E.164 (best-effort for Indian numbers)., TestPhoneNormalization

### Community 120 - "test_m20_post_call.py"
Cohesion: 0.16
Nodes (7): _create_call(), _create_campaign(), _create_lead(), _get_mock_db(), _make_redis(), M20 tests — Post-Call Processing. Tests: 1. Transcript model — turn storage,…, TestTranscriptsHTTP

### Community 121 - "call_session.py"
Cohesion: 0.11
Nodes (15): interpolate_template(), Any, Interpolate variables into template string supporting both {var} and {{var}}…, _looks_like_noise(), Transport-agnostic call pipeline. `CallSession` owns everything that makes a…, True if the transcript is almost certainly a hallucination or noise blip., Supported call languages (Indian-focused, backed by Sarvam Bulbul). Each entry…, Return (canonical_code, info). Falls back to the default if unknown. (+7 more)

### Community 122 - "AnalyticsService"
Cohesion: 0.19
Nodes (8): AnalyticsService, AsyncIOMotorDatabase, datetime, Revenue and margin analytics service — MVP simple approach. Per spec: "Keep MVP…, Total revenue: subscription + calling., Complete analytics report for the admin dashboard., Current MRR from active subscriptions. MRR = sum of monthly price of all…, MRR movement for a period: new_mrr — from new subscriptions started in period…

### Community 123 - "TestAnalyticsHTTP"
Cohesion: 0.23
Nodes (3): SKIP, All paise values must be integers in responses., TestAnalyticsHTTP

### Community 124 - "API-to-UI Mapping — Super Admin Dashboard"
Cohesion: 0.13
Nodes (14): API-to-UI Mapping — Super Admin Dashboard, Audit Logs, Calling Packs & Credits, Customer Dashboard Pages (for completeness), Dashboard, Organizations, Payments & Invoices, Phone Numbers (+6 more)

### Community 125 - "InvoiceRepository"
Cohesion: 0.18
Nodes (4): InvoiceRepository, _get_mock_db(), SKIP, TestInvoiceRepository

### Community 127 - "test_m18_appointments.py"
Cohesion: 0.21
Nodes (5): _future_dt(), _get_mock_db(), datetime, M18 tests — Appointments. Tests: 1. Appointment model — valid statuses,…, TestAppointmentModel

### Community 128 - "ProviderConfigPanel.tsx"
Cohesion: 0.23
Nodes (6): configStatus(), formatDate(), ProviderConfigPanel(), ProviderConfigPanelProps, truncate(), ProviderCredentialMeta

### Community 129 - "KnowledgeDocumentRepository"
Cohesion: 0.20
Nodes (4): KnowledgeDocumentRepository, MVP text search: keyword matching on title, content, keywords list. No vector…, Create a new version of a document. Old version is kept but deactivated., TestKnowledgeDocumentRepository

### Community 130 - "TestWalletModels"
Cohesion: 0.14
Nodes (3): Record an immutable ledger entry. Returns None if idempotency_key already…, TestWalletModels, WalletTransaction

### Community 131 - "test_m16_barge_in_latency.py"
Cohesion: 0.11
Nodes (14): LatencyService, Redis-backed latency tracker for active calls., M16 tests — Barge-In + Latency. Tests: 1. VAD SPEECH_START event fires when…, Test the barge-in flow in CallSession using mock components., SPEECH_START → _cancel_responder() + transport.clear()., During TTS playback, barge-in cancels the task., SPEECH_START with no active responder still calls transport.clear()., UTTERANCE event → new responder task created. (+6 more)

### Community 132 - "PaymentRepository"
Cohesion: 0.22
Nodes (3): PaymentRepository, Billing repositories: Order, Payment, Invoice, WebhookEvent., AsyncIOMotorDatabase

### Community 134 - "OrderRepository"
Cohesion: 0.19
Nodes (3): OrderRepository, TestOrderRepository, Order

### Community 135 - "AI Telecalling SaaS — Developer Guide"
Cohesion: 0.13
Nodes (15): AI Telecalling SaaS — Developer Guide, AI Voice Profiles, Architecture Overview, Business Templates & Agents, Campaign Engine, Creating a voice profile (admin), Creating a Voice Profile (Step-by-Step), Demo Mode (+7 more)

### Community 136 - "Getting Started — Real Estate Voice Agent"
Cohesion: 0.13
Nodes (14): 0. Prerequisites (already on this machine), 1. Why this stack (read once), 2.1 Environment file, 2.2 Start Postgres + Redis, 2.3 Python environment, 2.4 Download the TTS voice, 2. One-time setup, 3. Smoke test each piece independently (+6 more)

### Community 137 - "api.ts"
Cohesion: 0.05
Nodes (55): AdminModelsPage(), Capability, capabilityVariant(), formatFreeTierInfo(), freeTierDetails(), hostingIcon(), hostingLabel(), isStale() (+47 more)

### Community 138 - "release_credits"
Cohesion: 0.18
Nodes (12): BaseModel, field_validator, post, Settle exact credits after call completes. Idempotent., Reserve credits for an outbound call. Fails if insufficient credits., Release reserved credits (call cancelled/failed before billing)., release_credits(), ReleaseRequest (+4 more)

### Community 139 - "test_m3_subscriptions.py"
Cohesion: 0.12
Nodes (3): _get_mock_db(), M3 tests — Plans + Subscriptions. Tests: 1. SubscriptionPlan model — price…, TestSubscriptionPlanModel

### Community 140 - "timedelta"
Cohesion: 0.14
Nodes (7): Create a new subscription. Cancels any existing active subscription first., Upgrade/downgrade to a new plan. Updates snapshot immediately., Per-day call/credit analytics for the last N days., Platform-wide latency stats from recent calls., _seed_appointment(), CreditLot, timedelta

### Community 141 - "usage_service.py"
Cohesion: 0.08
Nodes (16): ProviderUsageRepository, datetime, Usage event and provider usage repositories., Admin aggregation including provider costs and margins., Admin: cost breakdown by provider layer., Aggregate customer-facing usage stats (no provider costs)., _customer_event(), AsyncIOMotorDatabase (+8 more)

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

### Community 148 - "calls.py"
Cohesion: 0.29
Nodes (12): _call_response(), finalize_call(), FinalizeCallRequest, get_call(), initiate_call(), InitiateCallRequest, list_calls(), BaseModel (+4 more)

### Community 149 - "Settings"
Cohesion: 0.19
Nodes (5): Return whichever Sarvam key is set., Legacy compat for existing session.py., Settings, TestConfig, BaseSettings

### Community 150 - "test_m15_calls.py"
Cohesion: 0.18
Nodes (6): _fund_org(), _get_mock_db(), _make_redis(), M15 tests — Real-Time AI Calling infrastructure. Tests: 1. Call model — valid…, run(), TestCallService

### Community 151 - "UsageEventRepository"
Cohesion: 0.14
Nodes (9): UsageEventRepository, _get_mock_db(), SKIP, M21 tests — Usage + Cost. Tests: 1. UsageEvent model — integer paise,…, CRITICAL: provider_cost_paise must NEVER appear in customer event list., Each usage event has call_id + idempotency_key for billing reconstruction., run(), TestUsageEventRepository (+1 more)

### Community 152 - "TestConcurrencyGate"
Cohesion: 0.17
Nodes (4): SKIP, Never exceed max_concurrent_calls., 10 concurrent acquire attempts with max=5: exactly 5 succeed., TestConcurrencyGate

### Community 153 - "AuditLogRepository"
Cohesion: 0.24
Nodes (4): AuditLogRepository, Any, TestAuditLogRepository, AuditLog

### Community 154 - "run.py"
Cohesion: 0.22
Nodes (13): is_port_in_use(), kill_process_tree(), main(), preflight_checks(), Launch backend and frontend in separate console windows (Windows)., Run both services unified in the current console with log prefixing., Check if a TCP port is in use., Stream stdout/stderr line by line with a colored prefix. (+5 more)

### Community 156 - "LeadService"
Cohesion: 0.23
Nodes (3): LeadService, AsyncIOMotorDatabase, Lead

### Community 157 - "AI Telecalling SaaS — Development Progress"
Cohesion: 0.15
Nodes (13): AI Telecalling SaaS — Development Progress, Build, CHECKPOINT HISTORY, CHECKPOINT ROADMAP, EXISTING CODEBASE SUMMARY, FEAT-001 — Design Foundations (COMPLETE — commit e04ec2d), FEAT-002 — Customer Application (COMPLETE — see commit after M40), FEAT-003/004 — Admin Application (COMPLETE) (+5 more)

### Community 158 - "Admin UI Implementation Plan — M40 FEAT-005A"
Cohesion: 0.17
Nodes (11): 1. Current State (post FEAT-005A), 2. File Structure, 3. Shared Component Reuse, 4. Auth/Permission Guard Strategy, 5. Design System, 6. API Client Namespaces (lib/api.ts), 7. Verification Commands, 8. Known Gaps / Future Work (+3 more)

### Community 159 - "db.py"
Cohesion: 0.04
Nodes (75): Credit reservation/settlement API — internal call billing endpoints. These are…, Demo Mode API. GET /api/v1/demo/status — check if demo mode is active and…, API v1 router — aggregates all v1 sub-routers., REST API for dynamic provider rate cards, daily FX updates, and loss…, Provider Operations API — admin only. GET /api/v1/provider-ops/health — overall…, Reconciliation API — admin only. GET /api/v1/reconciliation/run — run all…, Security API — admin only. GET /api/v1/security/audit — run security audit…, deactivate_user() (+67 more)

### Community 160 - "KnowledgeBaseAgentRepository"
Cohesion: 0.18
Nodes (5): KnowledgeBaseAgentRepository, Knowledge base and document repositories., AsyncIOMotorDatabase, Knowledge base service. MVP scope (per spec): minimal, tenant-safe. No over-…, KnowledgeBaseAgent

### Community 161 - "PostCallService"
Cohesion: 0.29
Nodes (3): PostCallService, AsyncIOMotorDatabase, Run the full post-call pipeline. Returns a summary dict of what was processed.…

### Community 162 - "TestRBACHTTP"
Cohesion: 0.26
Nodes (3): Role-based access control enforced at the HTTP layer., Viewer does not have organization_admin role., TestRBACHTTP

### Community 163 - "Transport"
Cohesion: 0.22
Nodes (6): A medium (browser websocket, phone line) the session speaks through., Send agent audio to the caller., Flush any audio already queued on the caller side (barge-in)., Deliver a metadata event (transcript, stage, etc.). May be a no-op., Transport, Protocol

### Community 164 - "MockPaymentProvider"
Cohesion: 0.07
Nodes (12): MockPaymentProvider, Verify against the fixed mock secret., Clear mock state between tests., Generate a test-valid mock signature for verify_payment., In-memory mock payment provider. No external calls., should_fail=True: verify_payment always returns False (simulate failed payment)., get_payment_provider(), Return the appropriate payment provider based on config. (+4 more)

### Community 165 - "CredentialStore"
Cohesion: 0.22
Nodes (5): CredentialStore, Thin wrapper around Fernet for storing/retrieving provider credentials., Encrypt a plaintext credential and return Fernet token bytes. Raises ValueError…, Decrypt a Fernet token and return the original plaintext string. Raises…, Return the last 4 characters of the plaintext for display purposes, or a…

### Community 166 - "transcripts.py"
Cohesion: 0.27
Nodes (11): get_transcript(), list_transcripts(), process_call(), ProcessCallRequest, BaseModel, get, post, Transcripts API. GET /api/v1/transcripts — list transcripts for org GET… (+3 more)

### Community 167 - "KnowledgeBaseRepository"
Cohesion: 0.25
Nodes (3): KnowledgeBaseRepository, SKIP, TestKnowledgeBaseRepository

### Community 168 - "TestAuthEndpoints"
Cohesion: 0.11
Nodes (4): SKIP_IF_NO_MONGOMOCK, Test auth endpoints using TestClient + mongomock., TestAuthEndpoints, TestTokenRefresh

### Community 169 - "ProviderConfigurationRepo"
Cohesion: 0.24
Nodes (5): ProviderConfigurationRepo, ProviderConfiguration, Return the single active config for a capability, or None., Set is_active=False on all configs for the given capability. Returns the number…, AsyncIOMotorDatabase

### Community 173 - "SarvamAgentStudioPage"
Cohesion: 0.23
Nodes (7): SarvamAgentStudioPage(), downsampleTo16k(), handleEndCall(), handleStartCall(), playPcmChunk(), scheduleAutoHangup(), stopPlayback()

### Community 174 - "TestUsageModels"
Cohesion: 0.25
Nodes (4): Record a usage event. Returns None if idempotency_key already exists., charge=100 paise, cost=30 paise → margin=70%, TestUsageModels, UsageEvent

### Community 175 - "BrowserTransport"
Cohesion: 0.25
Nodes (4): BrowserTransport, WebSocket, Speaks to the browser. Streams PCM chunks (4-byte sample-rate header + PCM)., ws_call()

### Community 177 - "seed_default_packs"
Cohesion: 0.22
Nodes (5): AsyncIOMotorDatabase, Seed default calling packs. Idempotent., seed_default_packs(), M24 tests — Super Admin. Tests: 1. All admin endpoints require platform role…, run()

### Community 178 - "test_m31_deployment.py"
Cohesion: 0.29
Nodes (3): _exists(), M31 tests — Production Deployment Configuration. Tests: 1. Dockerfile exists…, TestDeploymentFilesExist

### Community 180 - "test_m19_knowledge.py"
Cohesion: 0.15
Nodes (5): _extract_keywords(), Extract simple keywords from title and content (MVP: top unique words)., _get_mock_db(), M19 tests — Knowledge Base. Tests: 1. KnowledgeBase model — tenant-scoped 2.…, TestKnowledgeModels

### Community 182 - "TranscriptRepository"
Cohesion: 0.26
Nodes (4): Get existing transcript or create one. Idempotent., TranscriptRepository, TestTranscriptRepository, Transcript

### Community 184 - "providers/base.py"
Cohesion: 0.12
Nodes (8): PhoneNumberProvider, Provider, ABC, Abstract provider interfaces for the AI Telecalling SaaS platform. Core…, MockPhoneNumberProvider, ProviderRegistry, Typed provider registry; business services resolve providers by capability., test_registry_rejects_unknown_provider_and_duplicate_registration()

### Community 185 - "CallService"
Cohesion: 0.22
Nodes (4): CallService, AsyncIOMotorDatabase, Finalize a call after it ends. 1. Settle credits 2. Finalize call record 3.…, Initiate an outbound call. 1. Reserve credits 2. Create call record 3.…

### Community 186 - "TwilioProvider"
Cohesion: 0.27
Nodes (4): AsyncIOMotorClient, get_client(), Twilio adapter; the Media Streams transport remains in backend.telephony.twilio., TwilioProvider

### Community 187 - "organization_repo.py"
Cohesion: 0.27
Nodes (4): Organization repository., Simple slugifier: lowercase, alphanumeric + hyphens., _slugify(), TestSlugGeneration

### Community 189 - "run"
Cohesion: 0.07
Nodes (18): SKIP, M6 tests — Credit Reservation + Settlement. Tests: 1. reserve() moves credits…, Same call_id reserve twice: no double-deduction., Can't release a call that was already settled., Settle bills exactly; over-reserved credits returned to available., Settle using all reserved credits., actual_credits > reserved is capped at reserved (safety guard)., Double-settle same call_id is a no-op. (+10 more)

### Community 191 - "test_m32_documentation.py"
Cohesion: 0.39
Nodes (3): _exists(), M32 tests — Documentation Completeness. Tests: 1. DEVELOPER_GUIDE.md exists and…, TestDocumentationFilesExist

### Community 192 - "_read"
Cohesion: 0.25
Nodes (3): Should have substantial number of routes registered., _read(), TestAPICoverage

### Community 193 - "test_m13_campaigns.py"
Cohesion: 0.24
Nodes (4): _get_mock_db(), _make_redis(), M13 tests — Campaign Engine. Tests: 1. Campaign model — status validation, FSM…, In-memory Redis mock.

### Community 194 - "_config_to_dict"
Cohesion: 0.12
Nodes (10): _config_to_dict(), ProviderConfiguration, Validate, encrypt credential, and persist a new ProviderConfiguration. Raises:…, Activate a tested configuration. Raises: LookupError — config not found…, Return the active ProviderConfiguration for a capability, or None., List all ProviderConfiguration records (credentials stripped)., Return a single config or raise LookupError., Mark fallback_config_id as the fallback for config_id's capability. (+2 more)

### Community 196 - "CallRepository"
Cohesion: 0.15
Nodes (5): CallRepository, Finalize a call. Tenant-safe (org check on update)., SKIP, TestCallRepository, Call

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

### Community 217 - "TestE2EHappyPath"
Cohesion: 0.33
Nodes (4): Complete E2E: signup → org → plan → credits → voice profile → agent → phone →…, Complete workflow: signup → call → settlement → analytics., Seed plans, packs, and voice profile., TestE2EHappyPath

### Community 218 - "Adding a New Provider"
Cohesion: 0.50
Nodes (4): 1. Create the adapter, 2. Register in the provider registry, 3. Create a voice profile version using the new provider, Adding a New Provider

### Community 219 - "Installation"
Cohesion: 0.50
Nodes (4): Backend, Frontend, Installation, Prerequisites

### Community 224 - "4. MULTI-TENANCY"
Cohesion: 0.67
Nodes (3): 4. MULTI-TENANCY, Organization, Platform

### Community 253 - "override_rate"
Cohesion: 0.29
Nodes (8): override_rate(), OverrideRateRequest, BaseModel, post, Trigger an on-demand sync of USD/INR foreign exchange and provider rate cards., Immediately override a provider's rate to guard against sudden price hikes., SyncRatesRequest, trigger_daily_sync()

### Community 255 - "formatDateTime"
Cohesion: 0.04
Nodes (27): AdminAuditLogsPage(), AdminCallingPacksPage(), AdminDashboardPage(), AdminOrgDetailPage(), AdminOrgsPage(), AdminPaymentsPage(), AdminPhoneNumbersPage(), AdminSubscriptionsPage() (+19 more)

## Knowledge Gaps
- **437 isolated node(s):** `MRRData`, `MRRMovement`, `RevenueData`, `DailyEntry`, `PERIOD_OPTIONS` (+432 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **40 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_db()` connect `get_db` to `v1/auth.py`, `repository.py`, `dashboard.py`, `v1/model_directory.py`, `release_credits`, `organizations.py`, `PaymentService`, `ProviderOpsService`, `calls.py`, `HTTPException`, `agents.py`, `subscriptions.py`, `db.py`, `WalletService`, `PhoneNumberService`, `transcripts.py`, `leads.py`, `UsageService`, `CurrentUser`, `BrowserTransport`, `CampaignService`, `main.py`, `CampaignWorker`, `analytics.py`, `override_rate`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Why does `CurrentUser` connect `CurrentUser` to `v1/auth.py`, `dashboard.py`, `v1/model_directory.py`, `get_db`, `release_credits`, `model_directory_service.py`, `organizations.py`, `PaymentService`, `calls.py`, `HTTPException`, `agents.py`, `CloudProviderRuntime`, `subscriptions.py`, `db.py`, `WalletService`, `PhoneNumberService`, `transcripts.py`, `leads.py`, `ModelDirectoryService`, `UsageService`, `CampaignService`, `_config_to_dict`, `RateLimitError`, `test_m2_auth_rbac.py`, `override_rate`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `BaseRepository` connect `BaseRepository` to `AppointmentRepository`, `KnowledgeDocumentRepository`, `PaymentRepository`, `OrderRepository`, `model_directory_service.py`, `usage_service.py`, `CreditService`, `PricingSyncService`, `run`, `UsageEventRepository`, `AuditLogRepository`, `KnowledgeBaseAgentRepository`, `AgentVersionRepository`, `KnowledgeBaseRepository`, `ModelDirectoryService`, `ProviderConfigurationRepo`, `TranscriptRepository`, `CampaignRepository`, `organization_repo.py`, `test_m4_payment.py`, `PhoneNumberRepository`, `CallRepository`, `SubscriptionPlanRepository`, `LeadRepository`, `UserRepository`, `SubscriptionRepository`, `DNCRepository`, `VoiceProfileService`, `test_m1_mongodb.py`, `OrganizationRepository`, `phone_number_service.py`, `InvoiceRepository`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 130 inferred relationships involving `HTTPException` (e.g. with `call_detail()` and `admin_adjust_wallet()`) actually correct?**
  _`HTTPException` has 130 INFERRED edges - model-reasoned connections that need verification._
- **Are the 35 inferred relationships involving `WalletService` (e.g. with `admin_adjust_wallet()` and `get_org_wallet()`) actually correct?**
  _`WalletService` has 35 INFERRED edges - model-reasoned connections that need verification._
- **What connects `MRRData`, `MRRMovement`, `RevenueData` to the rest of the system?**
  _437 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `v1/auth.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12043010752688173 - nodes in this community are weakly interconnected._