# Graph Report - saas  (2026-10-26)

## Corpus Check
- 340 files · ~254,596 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5327 nodes · 11584 edges · 251 communities (215 shown, 36 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 751 edges (avg confidence: 0.58)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bc3ac443`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AppointmentRepository
- WalletRepository
- v1/wallet.py
- MVP_CHECKPOINTS.md
- knowledge_repo.py
- card.tsx
- routes.py
- dashboard.py
- test_m42_cloud_providers.py
- v1/model_directory.py
- get_db
- model_directory_repo.py
- CreditService
- spinner.tsx
- db.py
- devDependencies
- wallet_repo.py
- PaymentService
- test_m26_provider_ops.py
- SubscriptionPlan
- LLMProvider
- test_m5_wallet.py
- _config_to_dict
- HTTPException
- TTSEngine
- AgentService
- test_m33_e2e_acceptance.py
- auth-context.tsx
- ConversationEngine
- subscriptions.py
- v1/auth.py
- billing_portal.py
- repository.py
- organizations.py
- run
- run
- LatencyMetrics
- call_session.py
- TestSuperAdmin
- leads.py
- cloud_call_components.py
- PreflightService
- run
- TestFlyToml
- UsageService
- CampaignService
- CurrentUser
- dependencies
- TestWalletHTTP
- test_m17_tools_handoff.py
- TestCustomerBillingPortal
- Backend API Inventory
- campaigns.py
- compilerOptions
- ReconciliationService
- GoogleCloudSTTProvider
- FastAPI
- ModelDirectoryService
- TelephonyProvider
- v1/pricing.py
- TestMVPValidation
- SarvamTTSProvider
- ElevenLabsTTSProviderV2
- WalletService
- backend/telephony/vobiz.py
- AI Telecalling SaaS — Architecture Reference
- PhoneNumberRepository
- TestDeveloperGuide
- AI Telecalling SaaS — Technical Decisions Log
- AI Telecalling SaaS — Test Status
- backend/telephony/twilio.py
- model_test_service.py
- SubscriptionPlanRepository
- TTSProvider
- TestPreflightChecks
- Issues Log — post-Sarvam call testing (2026-07)
- VADEndpointer
- CallSession
- LeadRepository
- UserRepository
- StructuredInstructionEditor
- .create_version
- TestDemoSeedService
- run
- build_demo_registry
- SubscriptionRepository
- BaseRepository
- PhoneNumberService
- SecurityAuditService
- AppointmentService
- phone_numbers.py
- VobizTelephonyProvider
- DNCRepository
- OrderRepository
- TestAnalysisHelpers
- TestAuditLogRepository
- Real Estate Voice Agent — Execution Plan
- _sanitize_groq_error
- VoiceProfileVersionRepository
- providers/base.py
- run
- utcnow
- CallingPackRepository
- TestLeadsHTTP
- TestAnalyticsService
- run
- LLMClient
- GeminiLLMProvider
- VoiceProfileService
- TestAppointmentsHTTP
- CallEventBroadcaster
- OrganizationRepository
- seed_default_plans
- TestPhoneNumberHTTP
- test_m31_deployment.py
- TestCallPipelinePreserved
- analytics.py
- .test_stt
- TestTranscriptsHTTP
- TestCampaignHTTP
- TranscriptRepository
- AnalyticsService
- PricingSyncService
- run
- API-to-UI Mapping — Super Admin Dashboard
- PostCallService
- datetime
- package.json
- _get_mock_db
- CloudProviderRuntime
- Detailed Data Model & API Changes
- LatencyService
- run
- TestCreditReserve
- TestProviderSwitching
- AI Telecalling SaaS — Developer Guide
- Getting Started — Real Estate Voice Agent
- api.ts
- test_agent_kb_integration.py
- TestBillingHTTP
- test_test_agent.py
- SKIP
- test_m6_credit_reservation.py
- DocumentModel
- AI Telecalling SaaS
- CHECKPOINT HISTORY
- Review Focus
- Settings
- CallRepository
- UsageEventRepository
- run.py
- Campaign
- SubscriptionService
- AI Telecalling SaaS — Development Progress
- Admin UI Implementation Plan — M40 FEAT-005A
- ProviderConfigPanel.tsx
- main.py
- redis.py
- test_m3_subscriptions.py
- MockPaymentProvider
- model_directory_service.py
- transcripts.py
- seed_default_packs
- TestAuthEndpoints
- TestVobizCallDispatch
- AgentVersionRepository
- TestCreditHTTP
- SarvamAgentStudioPage
- AdminPhoneNumbersPage
- TestConcurrentReservations
- _exists
- TestEnvExampleCompleteness
- TestGitignore
- Appointment
- LeadService
- TestPreflightHTTP
- test_m14_preflight.py
- CampaignRepository
- new_id
- test_m12_leads.py
- run
- TimestampedModel
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
- TestPostCallService
- ui.tsx
- 29. AUTONOMOUS CHECKPOINT EXECUTION CONTRACT
- M41 Implementation Plan — AI Models Directory and One-Click Provider Setup
- Transport
- Deployment (Fly.io)
- Local Development
- Testing
- 36. DOCUMENTATION FILES MAINTAINED DURING EXECUTION
- _slugify
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
- CallService
- formatDateTime
- Review Focus
- _get_mock_db
- test_m20_post_call.py
- Design: Agent Multi-KB Selector and Grounded Response Injection
- TestDockerfile
- progress.md
- _read

## God Nodes (most connected - your core abstractions)
1. `get_db()` - 249 edges
2. `CurrentUser` - 213 edges
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
- `CallSession` --uses--> `ConversationEngine`  [INFERRED]
  backend/call_session.py → backend/agent/engine.py
- `lifespan()` --uses--> `ConversationEngine`  [INFERRED]
  backend/main.py → backend/agent/engine.py
- `ws_call()` --uses--> `ConversationEngine`  [INFERRED]
  backend/main.py → backend/agent/engine.py
- `ws_vobiz()` --uses--> `ConversationEngine`  [INFERRED]
  backend/telephony/vobiz.py → backend/agent/engine.py

## Import Cycles
- None detected.

## Communities (251 total, 36 thin omitted)

### Community 0 - "AppointmentRepository"
Cohesion: 0.19
Nodes (6): AppointmentRepository, Appointment, datetime, Upcoming scheduled/confirmed appointments., Mark existing as rescheduled and create a new one., TestAppointmentRepository

### Community 1 - "WalletRepository"
Cohesion: 0.08
Nodes (17): CreditLotRepository, datetime, Move credits from available → reserved. Returns updated doc or None if…, Move credits from reserved → available (call cancelled, not billed)., Finalize call billing: remove from reserved, add difference back to available.…, Add credits to available_credits and update a lifetime counter., Remove expired credits from available_credits., Active lots, sorted FIFO (oldest first for consumption). (+9 more)

### Community 2 - "v1/wallet.py"
Cohesion: 0.12
Nodes (26): AdjustRequest, admin_adjust_credits(), admin_create_pack(), admin_get_wallet(), admin_grant_bonus(), admin_run_expiry(), admin_update_pack(), BonusRequest (+18 more)

### Community 3 - "MVP_CHECKPOINTS.md"
Cohesion: 0.03
Nodes (67): 10. PHONE NUMBER PRINCIPLES, 11. AI VOICE PROFILE PRINCIPLES, 12. BUSINESS TEMPLATES, 13. AGENTS, 14. LEADS, 15. CAMPAIGNS, 16. CAMPAIGN PREFLIGHT, 17. REAL-TIME CALL PIPELINE (+59 more)

### Community 4 - "knowledge_repo.py"
Cohesion: 0.15
Nodes (10): KnowledgeBase, KnowledgeBaseAgent, KnowledgeDocument, Knowledge base models — minimal, tenant-safe. Per spec: "Do NOT over-engineer…, A named collection of knowledge documents., A single knowledge document with versioning., Association between a KnowledgeBase and an Agent., KnowledgeBaseAgentRepository (+2 more)

### Community 5 - "card.tsx"
Cohesion: 0.08
Nodes (35): AdminAnalyticsPage(), DailyEntry, MRRData, MRRMovement, PERIOD_OPTIONS, RevenueData, AdminCallingPacksPage(), AdminDashboardPage() (+27 more)

### Community 6 - "routes.py"
Cohesion: 0.11
Nodes (25): call_detail(), CallDetail, CallRow, calls(), languages(), LeadOut, leads(), BaseModel (+17 more)

### Community 7 - "dashboard.py"
Cohesion: 0.06
Nodes (34): dashboard(), dashboard_analytics(), dashboard_appointments(), dashboard_calls(), dashboard_campaigns(), dashboard_credits(), dashboard_leads(), _get_analytics() (+26 more)

### Community 8 - "test_m42_cloud_providers.py"
Cohesion: 0.05
Nodes (52): GroqLLMProvider, Groq chat-completion adapter. api_key is required and must come from the…, M42 Cloud AI Providers — contract tests with mocked HTTP. All tests use…, [mock] 401 error does not expose the API key in the exception message., [mock] 429 rate limit error produces clean message without key., [mock] Constructing GroqLLMProvider without api_key raises ValueError., [mock] GeminiLLMProvider.generate returns text from Gemini API response., [mock] System messages are passed via GenerateContentConfig, not contents. (+44 more)

### Community 9 - "v1/model_directory.py"
Cohesion: 0.09
Nodes (40): activate_configuration(), configure_provider(), ConfigureProviderBody, delete_configuration(), delete_credential(), FallbackBody, get_catalogue_entry(), get_configuration() (+32 more)

### Community 10 - "get_db"
Cohesion: 0.07
Nodes (52): admin_adjust_wallet(), admin_costs(), admin_dashboard(), admin_margins(), admin_revenue(), admin_usage(), _date_match(), get_org_wallet() (+44 more)

### Community 11 - "model_directory_repo.py"
Cohesion: 0.10
Nodes (20): AIModelCatalogue, ProviderConfiguration, ProviderCredential, MongoDB document models for the AI Models Directory. Three collections:…, One entry per (provider_name, model_id) in the catalogue., A configured provider/model for a given capability (tts/stt/llm)., Fernet-encrypted credential for a provider. Multiple rows per provider_name are…, AIModelCatalogueRepo (+12 more)

### Community 12 - "CreditService"
Cohesion: 0.14
Nodes (9): Finalize a call after it ends. 1. Settle credits 2. Finalize call record 3.…, Initiate an outbound call. 1. Reserve credits 2. Create call record 3.…, CreditService, Return all reserved credits for call_id back to available. Idempotent: if no…, Finalize billing for a completed call. actual_credits ≤ reserved_credits.…, Quick check before reserving — no state change., Return all outstanding reserve transactions for the org., Reserve up to max_credits for an active call. Raises ValueError if insufficient… (+1 more)

### Community 13 - "spinner.tsx"
Cohesion: 0.10
Nodes (50): AuditLog, Tab, Tab, AgentItem, OrgItem, Stats, Tab, LANGUAGE_OPTIONS (+42 more)

### Community 14 - "db.py"
Cohesion: 0.04
Nodes (66): active_reservations(), admin_active_reservations(), check_credits(), BaseModel, field_validator, get, post, Credit reservation/settlement API — internal call billing endpoints. These are… (+58 more)

### Community 15 - "devDependencies"
Cohesion: 0.12
Nodes (17): autoprefixer, eslint, eslint-config-next, devDependencies, autoprefixer, eslint, eslint-config-next, postcss (+9 more)

### Community 16 - "wallet_repo.py"
Cohesion: 0.06
Nodes (17): CallingPack, CreditLot, field_validator, Wallet, credit ledger, credit lots, and calling pack models. KEY RULES: - 1…, Immutable ledger record. Never updated after creation., A batch of credits from a single purchase or grant. Consumed FIFO by billing.…, A calling credit pack offered for purchase., Base + bonus credits. (+9 more)

### Community 17 - "PaymentService"
Cohesion: 0.07
Nodes (36): create_subscription_order(), CreateSubscriptionOrderRequest, get_invoice(), _invoice_response(), list_invoices(), list_orders(), list_payments(), _order_response() (+28 more)

### Community 18 - "test_m26_provider_ops.py"
Cohesion: 0.05
Nodes (25): platform_latency(), provider_health(), provider_metrics(), get, Health summary across all providers., Per-provider metrics: success rate, latency, cost, call count., Platform-wide call latency statistics., Health status of active voice profiles and their provider routes. (+17 more)

### Community 19 - "SubscriptionPlan"
Cohesion: 0.14
Nodes (7): field_validator, A plan offered on the platform. Managed by platform admins only., Convenience for display — never use for billing calculations., An organization's active subscription to a plan., Subscription, SubscriptionPlan, TestSubscriptionPlanModel

### Community 20 - "LLMProvider"
Cohesion: 0.10
Nodes (5): LLMProvider, PhoneNumberProvider, Any, Groq LLM provider adapter. Uses the official groq Python SDK (OpenAI-compatible…, MockPhoneNumberProvider

### Community 21 - "test_m5_wallet.py"
Cohesion: 0.12
Nodes (9): _get_mock_db(), SKIP, M5 tests — Calling Packs + Wallet. Tests: 1. CallingPack model — integer…, Wallet must never go negative., run(), TestSeedCallingPacks, TestWalletExpiry, TestWalletServiceAdminAdjustment (+1 more)

### Community 22 - "_config_to_dict"
Cohesion: 0.08
Nodes (16): _config_to_dict(), Exception, ProviderConfiguration, RateLimitError, Run an inference test for the given configuration. Raises: LookupError — config…, Activate a tested configuration. Raises: LookupError — config not found…, Return the active ProviderConfiguration for a capability, or None., List all ProviderConfiguration records (credentials stripped). (+8 more)

### Community 23 - "HTTPException"
Cohesion: 0.14
Nodes (33): appointment_summary(), _appt_response(), cancel_appointment(), CancelRequest, complete_appointment(), CompleteRequest, confirm_appointment(), create_appointment() (+25 more)

### Community 24 - "TTSEngine"
Cohesion: 0.07
Nodes (25): AI4BharatTTSEngine, get_tts_engine(), IndicF5Engine, OllamaTTSEngine, OrpheusEngine, pcm_to_wav(), PiperEngine, ABC (+17 more)

### Community 25 - "AgentService"
Cohesion: 0.09
Nodes (43): _agent_response(), create_agent(), create_version(), CreateAgentRequest, CreateVersionRequest, delete_agent(), get_agent(), get_pipeline_status() (+35 more)

### Community 26 - "test_m33_e2e_acceptance.py"
Cohesion: 0.11
Nodes (16): _get_mock_db(), _make_redis(), SKIP, M33 tests — Final End-to-End Acceptance. Tests the complete SaaS workflow as…, Complete E2E: signup → org → plan → credits → voice profile → agent → phone →…, Org A data completely invisible to Org B end-to-end., Complete workflow: signup → call → settlement → analytics., run() (+8 more)

### Community 27 - "auth-context.tsx"
Cohesion: 0.08
Nodes (33): AdminGuard(), PLATFORM_ROLES, LoginPage(), handleSubmit(), SignupPage(), handleSubmit(), AuthGuard(), SettingsPage() (+25 more)

### Community 28 - "ConversationEngine"
Cohesion: 0.08
Nodes (26): ConversationEngine, _decide_stage(), TypedDict, The conversation engine: a LangGraph state machine that drives the call. Per…, Advance the conversation by one user turn. Updates `state` in place (stage,…, Ephemeral state passed through the graph for a single turn., Pure transition logic. Order matters: end > objection > booking > qualify., Extract slots + output variables + intent flags from the latest user message. (+18 more)

### Community 29 - "subscriptions.py"
Cohesion: 0.09
Nodes (34): admin_activate_subscription(), admin_create_plan(), admin_list_plans(), admin_list_subscriptions(), admin_update_plan(), AdminActivateRequest, cancel_my_subscription(), change_my_plan() (+26 more)

### Community 30 - "v1/auth.py"
Cohesion: 0.06
Nodes (48): AuditLog, login(), LoginRequest, logout(), me(), MeResponse, BaseModel, field_validator (+40 more)

### Community 31 - "billing_portal.py"
Cohesion: 0.09
Nodes (37): billing_overview(), buy_calling_pack(), cancel_subscription(), CancelRequest, _days_remaining(), get_invoice(), get_subscription(), _invoice_response() (+29 more)

### Community 32 - "repository.py"
Cohesion: 0.14
Nodes (16): call_outcome(), lead_status(), Lead scoring: a simple, explainable 0-100 heuristic. Each filled qualification…, Map conversation state to a CRM status., score_lead(), add_turn(), _Call, finalize_call() (+8 more)

### Community 33 - "organizations.py"
Cohesion: 0.18
Nodes (17): create_organization(), get_organization(), list_organizations(), OrgCreateRequest, OrgUpdateRequest, BaseModel, get, Organization (+9 more)

### Community 34 - "run"
Cohesion: 0.05
Nodes (19): BusinessTemplateRepository, BusinessTemplate, AsyncIOMotorDatabase, BusinessTemplate, Seed default business templates. Idempotent., seed_templates(), _get_mock_db(), SKIP (+11 more)

### Community 35 - "run"
Cohesion: 0.06
Nodes (13): _get_mock_db(), SKIP, transfer_to_human must not contain business-specific logic., Tool implementations must not contain business-specific branches (if/else on…, run(), TestAddNote, TestBookAppointment, TestHandoffService (+5 more)

### Community 36 - "LatencyMetrics"
Cohesion: 0.10
Nodes (8): BrowserTransport, Speaks to the browser. Streams PCM chunks (4-byte sample-rate header + PCM)., _grade_latency(), LatencyMetrics, Latency metrics service. Records per-turn latency observations and provides…, In-memory latency accumulator for a single call., M16 tests — Barge-In + Latency. Tests: 1. VAD SPEECH_START event fires when…, TestLatencyMetrics

### Community 37 - "call_session.py"
Cohesion: 0.07
Nodes (20): FasterWhisperSTT, Speech-to-text via Groq Whisper. Sprint 1 does non-streaming transcription: the…, Routes each utterance to the best STT: Sarvam Saaras for Indian languages…, Stub for faster-whisper local runtime. Status: experimental. Raises…, Return (max no_speech_prob, min avg_logprob) across segments. Handles both…, Sarvam Saaras v3 speech-to-text — Indic-tuned, code-mixing aware.…, SarvamSTT, _segment_confidence() (+12 more)

### Community 38 - "TestSuperAdmin"
Cohesion: 0.12
Nodes (3): SKIP, Customer receives 403 on all admin endpoints., TestSuperAdmin

### Community 39 - "leads.py"
Cohesion: 0.18
Nodes (22): add_to_dnc(), create_lead(), CreateLeadRequest, delete_lead(), DNCAddRequest, get_lead(), import_leads(), _lead_response() (+14 more)

### Community 40 - "cloud_call_components.py"
Cohesion: 0.14
Nodes (10): build_cloud_call_components(), CloudCallComponents, CloudCallLLM, CloudCallTTS, _parse_json(), Any, Compatibility adapters from cloud provider interfaces to the call pipeline., Exposes the legacy conversation-engine protocol over an LLMProvider. (+2 more)

### Community 41 - "PreflightService"
Cohesion: 0.14
Nodes (11): PreflightCheck, PreflightResult, PreflightService, Any, AsyncIOMotorDatabase, Campaign, Campaign pre-flight validation service. Before a campaign starts, ALL of these…, Run all pre-flight checks for a campaign. Returns PreflightResult with all… (+3 more)

### Community 42 - "run"
Cohesion: 0.11
Nodes (8): SKIP, draft → running → paused → running → completed, Org B cannot start Org A's campaign., Never exceed max_concurrent_calls., 10 concurrent acquire attempts with max=5: exactly 5 succeed., run(), TestCampaignStateMachine, TestConcurrencyGate

### Community 44 - "UsageService"
Cohesion: 0.13
Nodes (22): admin_usage_summary(), list_usage_events(), provider_aggregates(), provider_breakdown(), BaseModel, datetime, get, post (+14 more)

### Community 45 - "CampaignService"
Cohesion: 0.13
Nodes (9): CampaignService, Campaign, datetime, Transition draft/scheduled → running. Runs pre-flight validation first., Mark campaign as completed (all leads processed)., Mark campaign as failed (unrecoverable error)., Check whether a new call can start for this campaign. Returns {allowed, reason,…, Atomically increment active call count. Returns True if slot acquired (count ≤… (+1 more)

### Community 46 - "CurrentUser"
Cohesion: 0.07
Nodes (40): add_document(), associate_agent(), create_knowledge_base(), CreateDocumentRequest, CreateKBRequest, delete_document(), delete_knowledge_base(), disassociate_agent() (+32 more)

### Community 47 - "dependencies"
Cohesion: 0.12
Nodes (17): clsx, dependencies, clsx, lucide-react, marked, next, react-dom, react-hot-toast (+9 more)

### Community 49 - "test_m17_tools_handoff.py"
Cohesion: 0.09
Nodes (34): Tool models — generic callable actions the AI agent can invoke during a call.…, Immutable record of a single tool invocation during a call., ToolCall, add_note(), book_appointment(), get_customer_details(), Built-in tool implementations. Every tool: - Receives (inputs: dict, context:…, Transfer the call to a human agent with complete context. Context package… (+26 more)

### Community 50 - "TestCustomerBillingPortal"
Cohesion: 0.13
Nodes (5): SKIP, Amount MUST come from server (plan lookup), not frontend., Org A cannot see Org B's invoice., run(), TestCustomerBillingPortal

### Community 51 - "Backend API Inventory"
Cohesion: 0.07
Nodes (26): Admin — `/api/v1/admin/*` (platform roles only), Agents — `/api/v1/agents/*`, Analytics — `/api/v1/analytics/*` (platform roles only), Appointments — `/api/v1/appointments/*`, Auth — `/api/v1/auth/*`, Backend API Inventory, Billing — `/api/v1/billing/*`, Calls — `/api/v1/calls/*` (+18 more)

### Community 52 - "campaigns.py"
Cohesion: 0.20
Nodes (21): _campaign_response(), campaign_stats(), cancel_campaign(), create_campaign(), CreateCampaignRequest, get_campaign(), list_campaigns(), pause_campaign() (+13 more)

### Community 53 - "compilerOptions"
Cohesion: 0.07
Nodes (26): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+18 more)

### Community 54 - "ReconciliationService"
Cohesion: 0.05
Nodes (22): AsyncIOMotorDatabase, datetime, Reconciliation service — financial ledger consistency checks. Per spec, runs…, Wallet purchase credits granted but no matching payment., Same webhook event processed more than once., Invoice total != payment amount for the same order., Wallet ledger sum != wallet.balance (available+reserved)., usage_event credits != wallet.total_consumed. (+14 more)

### Community 55 - "GoogleCloudSTTProvider"
Cohesion: 0.09
Nodes (18): _detect_encoding(), GoogleCloudSTTProvider, Any, Exception, Google Cloud Speech-to-Text v2 provider adapter. Uses google-cloud-speech SDK…, Transcribe audio bytes to text using Cloud Speech-to-Text v1 batch API. audio:…, Run synchronous recognition (in a thread pool)., Detect audio encoding from header bytes. Returns (encoding_enum,… (+10 more)

### Community 56 - "FastAPI"
Cohesion: 0.05
Nodes (34): demo_status(), get, post, Demo Mode API. GET /api/v1/demo/status — check if demo mode is active and…, Allow if DEMO_MODE=true OR caller is platform admin., Check demo mode status and seeding state., Seed the demo environment. Pass force=true to re-seed., _require_demo_or_admin() (+26 more)

### Community 57 - "ModelDirectoryService"
Cohesion: 0.05
Nodes (50): ProviderCredentialRepo, Return all credential records for a provider (including rotated history)., Return the current (non-rotated) credential for a provider, or None., Persist a new ProviderCredential document. Returns the saved document., Set rotated_at=now on all non-rotated credentials for the provider. Call before…, Delete ALL credential records for a provider (including history)., ModelDirectoryService, AsyncIOMotorDatabase (+42 more)

### Community 58 - "TelephonyProvider"
Cohesion: 0.09
Nodes (7): AsyncIOMotorClient, get_client(), TelephonyProvider, Exotel REST adapter boundary; credentials stay in platform configuration., MockTelephonyProvider, Twilio adapter; the Media Streams transport remains in backend.telephony.twilio., TwilioProvider

### Community 59 - "v1/pricing.py"
Cohesion: 0.18
Nodes (14): get_all_rates(), get_pipeline_cost(), override_rate(), OverrideRateRequest, BaseModel, get, post, REST API for dynamic provider rate cards, daily FX updates, and loss… (+6 more)

### Community 60 - "TestMVPValidation"
Cohesion: 0.17
Nodes (7): Validate the overall MVP state., All 26+ API routers are wired., Every checkpoint M1-M32 has a test file (M29 used existing suite)., Core services never import provider-specific modules directly., All repositories include organization_id in their queries., Demo mode seed can be imported and creates the right data., TestMVPValidation

### Community 61 - "SarvamTTSProvider"
Cohesion: 0.22
Nodes (5): Any, AsyncClient, Sarvam Bulbul managed-cloud TTS adapter., Progressive low-latency streaming TTS using Sarvam /stream endpoint., SarvamTTSProvider

### Community 62 - "ElevenLabsTTSProviderV2"
Cohesion: 0.10
Nodes (13): ElevenLabsTTSProviderV2, Any, Exception, Synchronous synthesis — called in a thread pool., Stream audio chunks from ElevenLabs. Yields {"audio": bytes_chunk,…, Collect streaming chunks synchronously (run in thread)., Return list of available voice dicts from the API., Return a sanitized error message — never includes the API key. (+5 more)

### Community 63 - "WalletService"
Cohesion: 0.20
Nodes (5): Grant credits from a calling pack purchase. Idempotent: same idempotency_key is…, Grant free bonus credits. Admin action., Manual credit adjustment by platform admin. credits_delta positive = add,…, Expire lots past their expiry date and remove those credits from wallet.…, WalletService

### Community 64 - "backend/telephony/vobiz.py"
Cohesion: 0.10
Nodes (16): get_active_transport(), api_route, Request, Response, WebSocket, Vobiz.ai Telephony webhook and Media Streams over WebSocket. Vobiz speaks a…, Vobiz calls this when an outbound or inbound call connects., Speaks the Vobiz Media Streams protocol over the websocket. (+8 more)

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

### Community 71 - "model_test_service.py"
Cohesion: 0.12
Nodes (9): OllamaLLMClient, Async client for a locally-running Ollama server. Ollama must be started…, Return True if the Ollama server is responding on /api/tags., Call /api/chat with the configured model and messages. Raises RuntimeError if…, Test connectivity and inference for each provider/model combination. Returns a…, [LIVE] Test LLM provider by requesting a one-sentence hello. Returns {status,…, [LIVE] Test Groq LLM with the injected API key., [LIVE] Test Gemini LLM with the injected API key. (+1 more)

### Community 72 - "SubscriptionPlanRepository"
Cohesion: 0.14
Nodes (7): SubscriptionPlan, Platform-managed subscription plans., Upgrade/downgrade to a new plan. Updates snapshot immediately., Active public plans, sorted by sort_order., SubscriptionPlanRepository, Changing plan price in DB must not change an existing subscription snapshot., TestSubscriptionPlanRepository

### Community 73 - "TTSProvider"
Cohesion: 0.08
Nodes (12): TTSProvider, OpenAICompatibleLLMProvider, OpenAI-compatible adapter boundary; concrete transport is selected by route., ExotelProvider, ElevenLabsTTSProvider, ElevenLabs TTS provider adapter — proper implementation. Uses the official…, MockTTSProvider, M8 provider contracts and registry tests. (+4 more)

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
Cohesion: 0.11
Nodes (12): CallSession, _looks_like_noise(), Return custom greeting, or generate one in the call language., Handle explicit caller interrupt event (barge-in)., Feed a chunk of caller audio; drives VAD, barge-in, and responses., True if the transcript is almost certainly a hallucination or noise blip., Build a CallSession with mocked dependencies., BrowserTransport implements the Transport protocol. (+4 more)

### Community 78 - "LeadRepository"
Cohesion: 0.15
Nodes (4): LeadRepository, Lead, Return the subset of phones that already exist in this org., TestLeadRepository

### Community 79 - "UserRepository"
Cohesion: 0.18
Nodes (3): UserRepository, TestUserRepository, User

### Community 80 - "StructuredInstructionEditor"
Cohesion: 0.16
Nodes (14): ConversationPhase, ObjectionItem, StructuredInstructionEditor(), compileStructuredToMarkdown(), handleLoadTemplate(), insertPrefix(), insertSnippet(), insertVariable() (+6 more)

### Community 81 - ".create_version"
Cohesion: 0.27
Nodes (5): AgentVersion, Any, Create a new draft version. Optionally publish and activate it., Publish a draft version and set it as active. Immutable after this., Update a draft version's configuration. Fails if already published.

### Community 82 - "TestDemoSeedService"
Cohesion: 0.11
Nodes (7): _get_mock_db(), SKIP, M30 tests — Demo Mode. Tests: 1. DemoSeedService.seed_all creates all required…, Provider routes in voice_profile_versions are internal only., run(), TestDemoHTTP, TestDemoSeedService

### Community 83 - "run"
Cohesion: 0.08
Nodes (10): Clear mock state between tests., WebhookEventRepository, _get_mock_db(), SKIP, M4 tests — Razorpay payment integration. Tests: 1. Billing models — integer…, run(), TestInvoiceRepository, TestMockPaymentProvider (+2 more)

### Community 84 - "build_demo_registry"
Cohesion: 0.09
Nodes (16): MockLLMProvider, build_demo_registry(), ProviderRegistry, Typed provider registry; business services resolve providers by capability., ProviderRouter, Internal provider selection with health, capability, language, and fallback…, ResolvedProvider, MockSTTProvider (+8 more)

### Community 85 - "SubscriptionRepository"
Cohesion: 0.16
Nodes (7): Subscription, Organization subscriptions — one active subscription per org., Get the current active/trialing/past_due subscription for an org., Get the most recent subscription (any status)., How many active orgs are on this plan., SubscriptionRepository, TestSubscriptionRepository

### Community 86 - "BaseRepository"
Cohesion: 0.04
Nodes (43): Appointment model — generic scheduling. Appointments are generic. Solar uses…, Base Pydantic models for MongoDB documents. MongoDB uses _id (ObjectId) as the…, Call model — an outbound AI call record. Each call is scoped to an…, CallingHours, Campaign model. A campaign is a scheduled outbound calling operation that dials…, Time window during which calls are allowed., How to retry leads that didn't connect., RetryPolicy (+35 more)

### Community 87 - "PhoneNumberService"
Cohesion: 0.06
Nodes (34): PhoneNumber, PhoneNumberAssignment, Phone number inventory models. IMPORTANT ABSTRACTION: - Customers see: number…, A phone number in the platform inventory., Immutable record of a number assignment to an org. History tracking., PhoneNumberAssignmentRepository, Phone number inventory and assignment repositories. Concurrent reservation…, PhoneNumberService (+26 more)

### Community 88 - "SecurityAuditService"
Cohesion: 0.06
Nodes (19): get, rate_limits(), Run security audit checks against the codebase., Show configured rate limit settings., security_audit(), Security audit service — static checks for known vulnerability patterns. This…, All API endpoint files must use auth dependencies., Check for secret keys in API response builders (not in models/repos). (+11 more)

### Community 89 - "AppointmentService"
Cohesion: 0.21
Nodes (6): AppointmentService, _appt_brief(), Appointment, AsyncIOMotorDatabase, datetime, Appointment service. Handles: - Creating appointments (standalone or from a…

### Community 90 - "phone_numbers.py"
Cohesion: 0.17
Nodes (20): add_number_to_inventory(), AddNumberRequest, admin_list_numbers(), assign_number(), AssignRequest, get_my_number(), inventory_stats(), list_available_numbers() (+12 more)

### Community 91 - "VobizTelephonyProvider"
Cohesion: 0.17
Nodes (10): Any, AsyncClient, Vobiz.ai Telephony adapter. Initiates outbound PSTN calls and manages call…, Fetch status of a call., Initiate an outbound call via Vobiz REST API. kwargs must contain: - auth_id:…, VobizTelephonyProvider, patch, Unit tests for VobizTelephonyProvider adapter. (+2 more)

### Community 92 - "DNCRepository"
Cohesion: 0.16
Nodes (6): DNCRepository, Add phone to DNC. Returns None if already on DNC., Return the subset of phones that are on DNC for this org., AsyncIOMotorDatabase, TestDNCRepository, DNCEntry

### Community 93 - "OrderRepository"
Cohesion: 0.21
Nodes (3): OrderRepository, Order, TestOrderRepository

### Community 94 - "TestAnalysisHelpers"
Cohesion: 0.22
Nodes (7): _analyze_call(), _compute_score(), _generate_summary(), Derive qualification, score, outcome, and summary from call state., Simple slot-based scoring. 15 pts per filled slot, bonuses for intent., Generate a brief text summary (no LLM in post-call for MVP)., TestAnalysisHelpers

### Community 95 - "TestAuditLogRepository"
Cohesion: 0.20
Nodes (4): SKIP_IF_NO_MONGOMOCK, Organization A should not see Organization B's users., TestAuditLogRepository, TestTenantIsolation

### Community 96 - "Real Estate Voice Agent — Execution Plan"
Cohesion: 0.11
Nodes (18): 0. The one thing that matters: latency, 1. Hardware reality & the stack decision, 2. System architecture, 3. Repository structure, 4. Conversation design (the product), 5. Data model (first cut), 6. API surface (backend), 7. Sprint plan (walking skeleton first) (+10 more)

### Community 97 - "_sanitize_groq_error"
Cohesion: 0.25
Nodes (6): Any, Exception, Streaming chat completion — yields text deltas., Return a sanitized error message — never includes the API key., Non-streaming chat completion. Raises RuntimeError on auth failure, rate limit,…, _sanitize_groq_error()

### Community 98 - "VoiceProfileVersionRepository"
Cohesion: 0.14
Nodes (13): ProviderRoute, Voice profile models. CORE ABSTRACTION — the most important thing in the whole…, Internal provider route for one layer of a voice profile version. NEVER…, Immutable snapshot of a voice profile's provider configuration. Once published,…, Customer-facing voice profile object. The customer sees only: id, display_name,…, VoiceProfile, VoiceProfileVersion, Any (+5 more)

### Community 99 - "providers/base.py"
Cohesion: 0.06
Nodes (23): PaymentProvider, Provider, ABC, Abstract provider interfaces for the AI Telecalling SaaS platform. Core…, Verify payment signature. Returns True if valid., Fetch payment details from provider. Returns provider payment dict., Issue a refund. Returns provider refund dict., Verify webhook signature. Called synchronously (crypto only, no I/O). Returns… (+15 more)

### Community 100 - "run"
Cohesion: 0.20
Nodes (3): SKIP, run(), TestAppointmentService

### Community 101 - "utcnow"
Cohesion: 0.06
Nodes (23): datetime, utcnow(), Resolve a route and durably retain any failover event for operations review., Insert multiple lead documents. Skips duplicates (same org + phone). Returns…, Create a new subscription. Cancels any existing active subscription first., DemoSeedService, AsyncIOMotorDatabase, Demo Mode seeding service. When DEMO_MODE=true, seeds a complete demo… (+15 more)

### Community 102 - "CallingPackRepository"
Cohesion: 0.15
Nodes (7): CallingPackRepository, CallingPack, Buy 2000 credits → wallet=2000, ledger=+2000, lot=2000, 2000 base + 200 bonus = 2200 total credits granted, Every credit movement requires an immutable WalletTransaction., Same idempotency_key does not double-grant credits., TestWalletServicePurchase

### Community 104 - "TestAnalyticsService"
Cohesion: 0.17
Nodes (5): _get_mock_db(), charge=1000, cost=300 → margin=70%, total_revenue = subscription + calling, run(), TestAnalyticsService

### Community 105 - "run"
Cohesion: 0.09
Nodes (13): _get_mock_db(), SKIP, Org A cannot see Org B numbers., get_number_for_org returns None if number belongs to a different org., Provider details must not leak into any customer-facing response., Only one org can claim the same number — concurrent request safety., 5 concurrent assign attempts for the same number: exactly 1 wins., 5 concurrent assigns for 5 different numbers: all succeed. (+5 more)

### Community 106 - "LLMClient"
Cohesion: 0.18
Nodes (10): _extract_json(), LLMClient, Groq gpt-oss client (OpenAI-compatible), async + streaming. Streaming matters:…, Yield complete sentences as soon as they're ready, so TTS can start speaking…, Non-streaming convenience helper (used by smoke tests)., Structured extraction. Never raises: returns {} if extraction fails. gpt-oss on…, Best-effort parse of a JSON object from model output. None on failure., Yield raw text deltas as the model generates them. gpt-oss on Groq… (+2 more)

### Community 107 - "GeminiLLMProvider"
Cohesion: 0.13
Nodes (15): GeminiLLMProvider, _get_candidate_models(), _is_transient_error(), Any, Exception, Gemini LLM provider adapter using the official google-genai SDK. Uses…, Generate a reply for the given conversation messages., Stream text deltas from Gemini with automatic retry and model fallback. (+7 more)

### Community 108 - "VoiceProfileService"
Cohesion: 0.12
Nodes (14): Return platform profiles + org's own profiles. Active only., VoiceProfileRepository, _customer_view(), AsyncIOMotorDatabase, Seed default platform voice profiles if none exist. Idempotent., seed_default_voice_profiles(), VoiceProfileService, skipif (+6 more)

### Community 110 - "CallEventBroadcaster"
Cohesion: 0.17
Nodes (9): CallEventBroadcaster, Any, In-memory real-time event broadcaster for live phone calls., Pub/sub broadcaster delivering real-time call events (turns, status,…, Tests for CallEventBroadcaster and live call transcript monitoring., run(), test_broadcaster_empty_and_cleanup(), test_broadcaster_pubsub() (+1 more)

### Community 111 - "OrganizationRepository"
Cohesion: 0.21
Nodes (4): OrganizationRepository, Organization, run(), TestOrganizationRepository

### Community 112 - "seed_default_plans"
Cohesion: 0.16
Nodes (5): AsyncIOMotorDatabase, SubscriptionPlan, Create default plans if they don't exist. Safe to call on every startup., seed_default_plans(), TestSubscriptionHTTP

### Community 113 - "TestPhoneNumberHTTP"
Cohesion: 0.21
Nodes (3): CRITICAL: provider details must never appear in customer API response., Org A cannot see Org B's assigned numbers via /my endpoint., TestPhoneNumberHTTP

### Community 115 - "TestCallPipelinePreserved"
Cohesion: 0.18
Nodes (5): Verify the original call_session.py pipeline is intact., CallSession must import without errors., Silero VAD endpointer must import without errors., Transport protocol (play/clear/notify) is still intact., TestCallPipelinePreserved

### Community 116 - "analytics.py"
Cohesion: 0.16
Nodes (19): get_arpu(), get_costs(), get_daily_analytics(), get_full_report(), get_margins(), get_mrr(), get_mrr_movement(), get_revenue() (+11 more)

### Community 117 - ".test_stt"
Cohesion: 0.25
Nodes (4): [LIVE] Test STT provider with a short silent WAV clip. Returns {status,…, [LIVE] Test Groq Whisper with the injected API key., [LIVE] Test Sarvam STT with the injected API key., [LIVE] Test Google Cloud STT with a silent WAV clip. credential: service…

### Community 120 - "TranscriptRepository"
Cohesion: 0.16
Nodes (9): A single turn (user or agent utterance) in the call transcript., Full transcript for a single call. Unique per call_id., Transcript, Turn, Get existing transcript or create one. Idempotent., Append turns to transcript and update count., TranscriptRepository, TestTranscriptModel (+1 more)

### Community 121 - "AnalyticsService"
Cohesion: 0.16
Nodes (9): AnalyticsService, AsyncIOMotorDatabase, datetime, Revenue and margin analytics service — MVP simple approach. Per spec: "Keep MVP…, Total revenue: subscription + calling., Per-day call/credit analytics for the last N days., Complete analytics report for the admin dashboard., Current MRR from active subscriptions. MRR = sum of monthly price of all… (+1 more)

### Community 122 - "PricingSyncService"
Cohesion: 0.08
Nodes (30): PricingSettings, ProviderRateCard, MongoDB document models for provider pricing, FX rates, and rate cards. Tracks…, Stores the effective cost and billable rate for a provider/model., Global platform pricing and loss-protection settings., _deserialize(), Clean up a MongoDB document for use with Pydantic models., PricingSettingsRepository (+22 more)

### Community 123 - "run"
Cohesion: 0.18
Nodes (4): Auto-mapping handles common aliases (mobile → phone, etc.)., run(), TestCSVImport, TestLeadService

### Community 124 - "API-to-UI Mapping — Super Admin Dashboard"
Cohesion: 0.13
Nodes (14): API-to-UI Mapping — Super Admin Dashboard, Audit Logs, Calling Packs & Credits, Customer Dashboard Pages (for completeness), Dashboard, Organizations, Payments & Invoices, Phone Numbers (+6 more)

### Community 125 - "PostCallService"
Cohesion: 0.29
Nodes (3): PostCallService, AsyncIOMotorDatabase, Run the full post-call pipeline. Returns a summary dict of what was processed.…

### Community 126 - "datetime"
Cohesion: 0.22
Nodes (6): _customer_event(), datetime, Usage summary safe to return to customer (no provider costs)., Customer-safe usage event list (strips provider cost)., Full admin summary with provider costs and margin., Strip provider cost from event before sending to customer.

### Community 127 - "package.json"
Cohesion: 0.22
Nodes (8): name, private, scripts, build, dev, lint, start, version

### Community 128 - "_get_mock_db"
Cohesion: 0.11
Nodes (8): _get_mock_db(), SKIP, Test 4000+ lead import — the M12 mandatory acceptance criterion., Import 4000 leads: all imported, correct count, no errors., 4000 leads, 100 on DNC → 3900 imported, 100 skipped., TestJSONImport, TestLargeImport, TestXLSXImport

### Community 129 - "CloudProviderRuntime"
Cohesion: 0.10
Nodes (24): ProviderConfigurationRepo, ProviderConfiguration, Return the single active config for a capability, or None., Set is_active=False on all configs for the given capability. Returns the number…, CloudProviderRuntime, _llm_options(), Any, AsyncIOMotorDatabase (+16 more)

### Community 130 - "Detailed Data Model & API Changes"
Cohesion: 0.15
Nodes (12): 1. Model Updates (`backend/models/phone_number.py`), 2. Service & Repository Updates, 3. Vobiz Telephony Provider Adapter (`backend/providers/telephony/vobiz.py`), 4. Vobiz Webhook & WebSocket Streaming (`backend/telephony/vobiz.py`), 5. Frontend Admin Dashboard Updates (`frontend/app/(admin)/admin/phone-numbers/page.tsx`), 6. Frontend AI Agent Studio Updates (`frontend/app/(dashboard)/agents/[id]/page.tsx`), Architecture & Data Flow, Design: Vobiz.ai Phone Number Provider & Multi-Organization Assignment (+4 more)

### Community 131 - "LatencyService"
Cohesion: 0.12
Nodes (13): LatencyService, Redis-backed latency tracker for active calls., Test the barge-in flow in CallSession using mock components., SPEECH_START → _cancel_responder() + transport.clear()., During TTS playback, barge-in cancels the task., SPEECH_START with no active responder still calls transport.clear()., UTTERANCE event → new responder task created., Each processed utterance appends to self.latencies. (+5 more)

### Community 132 - "run"
Cohesion: 0.05
Nodes (18): _extract_keywords(), KnowledgeBaseRepository, KnowledgeDocumentRepository, KnowledgeBase, KnowledgeDocument, MVP text search: keyword matching on title, content, keywords list. No vector…, Create a new version of a document. Old version is kept but deactivated., Extract simple keywords from title and content (MVP: top unique words). (+10 more)

### Community 133 - "TestCreditReserve"
Cohesion: 0.25
Nodes (3): Same call_id reserve twice: no double-deduction., reserve() moves available → reserved; total unchanged., TestCreditReserve

### Community 134 - "TestProviderSwitching"
Cohesion: 0.40
Nodes (3): Change voice profile provider route — campaign unaffected., Active campaign pins a version_id — changing routes creates new version., TestProviderSwitching

### Community 135 - "AI Telecalling SaaS — Developer Guide"
Cohesion: 0.13
Nodes (15): AI Telecalling SaaS — Developer Guide, AI Voice Profiles, Architecture Overview, Business Templates & Agents, Campaign Engine, Creating a voice profile (admin), Creating a Voice Profile (Step-by-Step), Demo Mode (+7 more)

### Community 136 - "Getting Started — Real Estate Voice Agent"
Cohesion: 0.13
Nodes (14): 0. Prerequisites (already on this machine), 1. Why this stack (read once), 2.1 Environment file, 2.2 Start Postgres + Redis, 2.3 Python environment, 2.4 Download the TTS voice, 2. One-time setup, 3. Smoke test each piece independently (+6 more)

### Community 137 - "api.ts"
Cohesion: 0.04
Nodes (64): AdminModelsPage(), Capability, capabilityVariant(), formatFreeTierInfo(), freeTierDetails(), hostingIcon(), hostingLabel(), isStale() (+56 more)

### Community 138 - "test_agent_kb_integration.py"
Cohesion: 0.29
Nodes (4): SKIP, End-to-End integration test for Agent Multi-KB association and Prompt Grounding., run(), TestAgentKBIntegration

### Community 139 - "TestBillingHTTP"
Cohesion: 0.19
Nodes (3): Generate a valid webhook signature for testing., Org A cannot see Org B's invoice., TestBillingHTTP

### Community 140 - "test_test_agent.py"
Cohesion: 0.10
Nodes (17): STTProvider, GroqSTTProvider, Any, Groq Whisper STT provider adapter., Any, AsyncClient, Sarvam Saaras STT provider adapter., SarvamSTTProvider (+9 more)

### Community 142 - "test_m6_credit_reservation.py"
Cohesion: 0.22
Nodes (6): _fund_org(), _get_mock_db(), _make_mock_redis(), M6 tests — Credit Reservation + Settlement. Tests: 1. reserve() moves credits…, In-memory dict-based Redis mock for credit reservation keys., Helper: give an org N credits via bonus.

### Community 145 - "DocumentModel"
Cohesion: 0.06
Nodes (22): Audit log model. Immutable record of actions in the system. Used for security,…, DocumentModel, Any, BaseModel, Base for MongoDB documents. `id` maps to the document's `_id` field., Serialize for MongoDB insertion (use `_id`, not `id`)., Deserialize from a MongoDB document., Invoice (+14 more)

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

### Community 150 - "CallRepository"
Cohesion: 0.07
Nodes (13): CallRepository, Finalize a call. Tenant-safe (org check on update)., AsyncIOMotorDatabase, _fund_org(), _get_mock_db(), _make_redis(), SKIP, M15 tests — Real-Time AI Calling infrastructure. Tests: 1. Call model — valid… (+5 more)

### Community 151 - "UsageEventRepository"
Cohesion: 0.08
Nodes (15): datetime, Admin aggregation including provider costs and margins., Admin: cost breakdown by provider layer., Aggregate customer-facing usage stats (no provider costs)., UsageEventRepository, AsyncIOMotorDatabase, _get_mock_db(), SKIP (+7 more)

### Community 154 - "run.py"
Cohesion: 0.22
Nodes (13): is_port_in_use(), kill_process_tree(), main(), preflight_checks(), Launch backend and frontend in separate console windows (Windows)., Run both services unified in the current console with log prefixing., Check if a TCP port is in use., Stream stdout/stderr line by line with a colored prefix. (+5 more)

### Community 155 - "Campaign"
Cohesion: 0.13
Nodes (5): Campaign, field_validator, An outbound calling campaign., TestCampaignModel, _make_campaign()

### Community 156 - "SubscriptionService"
Cohesion: 0.11
Nodes (12): EntitlementCheck, Result of an entitlement check. Not stored in DB., Subscription, Check a boolean feature gate, e.g. 'knowledge_base_enabled'., Activate a plan for an org. Cancels any existing subscription immediately., Upgrade or downgrade. Takes effect immediately., Return a safe summary of what the org is entitled to (for API response)., SubscriptionService (+4 more)

### Community 157 - "AI Telecalling SaaS — Development Progress"
Cohesion: 0.15
Nodes (13): AI Telecalling SaaS — Development Progress, Build, CHECKPOINT HISTORY, CHECKPOINT ROADMAP, EXISTING CODEBASE SUMMARY, FEAT-001 — Design Foundations (COMPLETE — commit e04ec2d), FEAT-002 — Customer Application (COMPLETE — see commit after M40), FEAT-003/004 — Admin Application (COMPLETE) (+5 more)

### Community 158 - "Admin UI Implementation Plan — M40 FEAT-005A"
Cohesion: 0.17
Nodes (11): 1. Current State (post FEAT-005A), 2. File Structure, 3. Shared Component Reuse, 4. Auth/Permission Guard Strategy, 5. Design System, 6. API Client Namespaces (lib/api.ts), 7. Verification Commands, 8. Known Gaps / Future Work (+3 more)

### Community 159 - "ProviderConfigPanel.tsx"
Cohesion: 0.23
Nodes (6): configStatus(), formatDate(), ProviderConfigPanel(), ProviderConfigPanelProps, truncate(), ProviderCredentialMeta

### Community 161 - "main.py"
Cohesion: 0.16
Nodes (16): close_db(), _ensure_indexes(), init_db(), ping_db(), AsyncIOMotorDatabase, Connect to MongoDB and create all indexes., Health check — returns True if MongoDB is reachable., Create all collection indexes. Idempotent. (+8 more)

### Community 162 - "redis.py"
Cohesion: 0.14
Nodes (10): close_redis(), init_redis(), Redis async client factory. Single process-wide client. Redis is used for: -…, TestWorkerShutdown, CampaignWorker, main(), Campaign worker — polls Redis for pending campaigns and initiates calls. This…, Initiate the actual call and handle completion. (+2 more)

### Community 163 - "test_m3_subscriptions.py"
Cohesion: 0.17
Nodes (4): _get_mock_db(), SKIP_IF_NO_MONGOMOCK, M3 tests — Plans + Subscriptions. Tests: 1. SubscriptionPlan model — price…, TestSeedDefaultPlans

### Community 164 - "MockPaymentProvider"
Cohesion: 0.09
Nodes (7): MockPaymentProvider, Verify against the fixed mock secret., Generate a test-valid mock signature for verify_payment., In-memory mock payment provider. No external calls., should_fail=True: verify_payment always returns False (simulate failed payment)., In DEMO_MODE, payment_service uses MockPaymentProvider., TestDemoModeProviders

### Community 165 - "model_directory_service.py"
Cohesion: 0.08
Nodes (15): CredentialStore, Fernet-based credential encryption for stored provider API keys. The encryption…, Thin wrapper around Fernet for storing/retrieving provider credentials., Encrypt a plaintext credential and return Fernet token bytes. Raises ValueError…, Decrypt a Fernet token and return the original plaintext string. Raises…, Return the last 4 characters of the plaintext for display purposes, or a…, _catalogue_to_dict(), _cred_to_safe_dict() (+7 more)

### Community 166 - "transcripts.py"
Cohesion: 0.27
Nodes (11): get_transcript(), list_transcripts(), process_call(), ProcessCallRequest, BaseModel, get, post, Transcripts API. GET /api/v1/transcripts — list transcripts for org GET… (+3 more)

### Community 167 - "seed_default_packs"
Cohesion: 0.25
Nodes (5): AsyncIOMotorDatabase, CallingPack, Seed default calling packs. Idempotent., seed_default_packs(), M23 tests — Customer Billing Portal. Tests: 1. /billing-portal/overview —…

### Community 168 - "TestAuthEndpoints"
Cohesion: 0.06
Nodes (12): SKIP_IF_NO_MONGOMOCK, Test auth endpoints using TestClient + mongomock., Critical: Org A must NOT be able to access Org B data., CRITICAL: Org A must receive 403 when accessing Org B., CRITICAL: Org B must receive 403 when accessing Org A., Org A cannot list users of Org B., Role-based access control enforced at the HTTP layer., Viewer does not have organization_admin role. (+4 more)

### Community 170 - "TestVobizCallDispatch"
Cohesion: 0.47
Nodes (3): patch, run(), TestVobizCallDispatch

### Community 171 - "AgentVersionRepository"
Cohesion: 0.27
Nodes (5): AgentVersionRepository, AgentVersion, Any, Mark a version as published (immutable after this)., Update draft configuration. Raises if already published.

### Community 173 - "SarvamAgentStudioPage"
Cohesion: 0.17
Nodes (9): SarvamAgentStudioPage(), connectPhoneCallStream(), downsampleTo16k(), handleDialPhone(), handleEndCall(), handleStartCall(), playPcmChunk(), scheduleAutoHangup() (+1 more)

### Community 177 - "TestConcurrentReservations"
Cohesion: 0.17
Nodes (6): 10 concurrent calls — no double-spend, no negative credits., 10 concurrent reserves of 60 credits with 600 total: all succeed., 5 calls succeed, 6th fails (300 credits = exactly 5 × 60)., Settling 10 calls concurrently: total consumed = sum of actuals., Hammer reserves beyond balance: wallet always ≥ 0., TestConcurrentReservations

### Community 181 - "Appointment"
Cohesion: 0.23
Nodes (7): Appointment, field_validator, A generic appointment record., _future_dt(), datetime, M18 tests — Appointments. Tests: 1. Appointment model — valid statuses,…, TestAppointmentModel

### Community 184 - "test_m14_preflight.py"
Cohesion: 0.13
Nodes (13): AgentRepository, Agent, Get agent only if it belongs to this org (tenant isolation)., M14 tests — Campaign Pre-flight. Tests: 1. All checks pass → campaign can start…, Create a published agent version., Create a phone number assigned to the org., Create leads for the org., Create an active subscription for the org. (+5 more)

### Community 185 - "CampaignRepository"
Cohesion: 0.10
Nodes (11): CampaignRepository, Campaign, All running/scheduled campaigns — for worker polling., Atomic status update scoped to org., AsyncIOMotorDatabase, _get_mock_db(), _make_redis(), M13 tests — Campaign Engine. Tests: 1. Campaign model — status validation, FSM… (+3 more)

### Community 186 - "new_id"
Cohesion: 0.07
Nodes (24): new_id(), Generate a new UUID4 string., Call, An outbound AI call record., Lead, field_validator, A single lead record owned by an organization., ProviderUsage (+16 more)

### Community 187 - "test_m12_leads.py"
Cohesion: 0.19
Nodes (6): normalize_phone(), Normalize a phone number to E.164 (best-effort for Indian numbers)., _make_csv(), M12 tests — Lead CRM. Tests: 1. Lead model — status validation, phone required…, Build a CSV bytes payload from a list of dicts., TestPhoneNormalization

### Community 189 - "run"
Cohesion: 0.14
Nodes (9): Can't release a call that was already settled., Settle bills exactly; over-reserved credits returned to available., Settle using all reserved credits., actual_credits > reserved is capped at reserved (safety guard)., Double-settle same call_id is a no-op., 0-second call: no consume ledger entry, reservation cleared., run(), TestCreditRelease (+1 more)

### Community 190 - "TimestampedModel"
Cohesion: 0.06
Nodes (34): AuditLog, Audit log entry — immutable after creation., DocumentModel with created_at and updated_at., TimestampedModel, Organization, OrganizationCreate, OrganizationPublic, OrganizationSettings (+26 more)

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

### Community 207 - "TestPostCallService"
Cohesion: 0.22
Nodes (5): SKIP, Running process() twice does NOT double-count analytics., Usage event written only once per call., run(), TestPostCallService

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

### Community 216 - "_slugify"
Cohesion: 0.36
Nodes (3): Simple slugifier: lowercase, alphanumeric + hyphens., _slugify(), TestSlugGeneration

### Community 217 - "button.tsx"
Cohesion: 0.07
Nodes (25): ChatMessage, StudioTab, TestTab, LANGUAGE_OPTIONS, NewAgentPage(), Step, TONE_OPTIONS, AgentsPage() (+17 more)

### Community 218 - "Adding a New Provider"
Cohesion: 0.50
Nodes (4): 1. Create the adapter, 2. Register in the provider registry, 3. Create a voice profile version using the new provider, Adding a New Provider

### Community 219 - "Installation"
Cohesion: 0.50
Nodes (4): Backend, Frontend, Installation, Prerequisites

### Community 222 - "PaymentRepository"
Cohesion: 0.32
Nodes (3): PaymentRepository, AsyncIOMotorDatabase, Payment

### Community 223 - "TestCreditConservation"
Cohesion: 0.29
Nodes (3): Credits are conserved: available + reserved = constant (except consume)., After settle, total = initial - billed., TestCreditConservation

### Community 224 - "4. MULTI-TENANCY"
Cohesion: 0.67
Nodes (3): 4. MULTI-TENANCY, Organization, Platform

### Community 251 - "CallService"
Cohesion: 0.21
Nodes (17): _call_response(), finalize_call(), FinalizeCallRequest, get_call(), get_call_transcript(), hangup_call(), initiate_call(), InitiateCallRequest (+9 more)

### Community 255 - "formatDateTime"
Cohesion: 0.05
Nodes (21): AdminAuditLogsPage(), AdminOrgDetailPage(), AdminOrgsPage(), AdminSubscriptionsPage(), AdminVoiceProfilesPage(), AppointmentsPage(), BillingPage(), CallDetailPage() (+13 more)

### Community 256 - "Review Focus"
Cohesion: 0.22
Nodes (8): Agent Multi-KB Selector and Response Grounding Implementation Plan, Global Constraints, Review Focus, Task 1: Frontend API Client KB Association Methods, Task 2: Backend Prompt Grounding & Strictness Mode Enhancement, Task 3: Backend Unit Tests, Task 4: Frontend Agent Knowledge Base Selector UI, Task 5: Verification & Demo

### Community 258 - "test_m20_post_call.py"
Cohesion: 0.22
Nodes (5): _create_campaign(), _create_lead(), _get_mock_db(), _make_redis(), M20 tests — Post-Call Processing. Tests: 1. Transcript model — turn storage,…

### Community 263 - "Design: Agent Multi-KB Selector and Grounded Response Injection"
Cohesion: 0.29
Nodes (6): Architecture & Data Flow, Design: Agent Multi-KB Selector and Grounded Response Injection, Detailed Decisions, Goals, Intent and Context, Non-Goals & Anti-Goals

## Knowledge Gaps
- **481 isolated node(s):** `MRRData`, `MRRMovement`, `RevenueData`, `DailyEntry`, `PERIOD_OPTIONS` (+476 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `new_id()` connect `new_id` to `AppointmentRepository`, `WalletRepository`, `test_m20_post_call.py`, `knowledge_repo.py`, `run`, `model_directory_repo.py`, `wallet_repo.py`, `DocumentModel`, `test_m26_provider_ops.py`, `SubscriptionPlan`, `test_m5_wallet.py`, `CallRepository`, `UsageEventRepository`, `test_m33_e2e_acceptance.py`, `Campaign`, `v1/auth.py`, `billing_portal.py`, `repository.py`, `run`, `test_m3_subscriptions.py`, `model_directory_service.py`, `seed_default_packs`, `AgentVersionRepository`, `test_m17_tools_handoff.py`, `TestCustomerBillingPortal`, `Appointment`, `ReconciliationService`, `test_m14_preflight.py`, `CampaignRepository`, `test_m12_leads.py`, `TimestampedModel`, `PhoneNumberRepository`, `SubscriptionPlanRepository`, `LeadRepository`, `UserRepository`, `run`, `build_demo_registry`, `SubscriptionRepository`, `BaseRepository`, `PhoneNumberService`, `_slugify`, `DNCRepository`, `OrderRepository`, `PaymentRepository`, `VoiceProfileVersionRepository`, `utcnow`, `CallingPackRepository`, `VoiceProfileService`, `TranscriptRepository`, `PricingSyncService`, `PostCallService`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `get_db()` connect `get_db` to `v1/wallet.py`, `routes.py`, `dashboard.py`, `v1/model_directory.py`, `db.py`, `PaymentService`, `test_m26_provider_ops.py`, `HTTPException`, `AgentService`, `subscriptions.py`, `v1/auth.py`, `billing_portal.py`, `repository.py`, `organizations.py`, `main.py`, `redis.py`, `transcripts.py`, `leads.py`, `UsageService`, `CurrentUser`, `campaigns.py`, `FastAPI`, `v1/pricing.py`, `backend/telephony/vobiz.py`, `backend/telephony/twilio.py`, `phone_numbers.py`, `analytics.py`, `CallService`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `AppointmentRepository`, `WalletRepository`, `knowledge_repo.py`, `run`, `get_db`, `CreditService`, `wallet_repo.py`, `DocumentModel`, `test_m26_provider_ops.py`, `CallRepository`, `_config_to_dict`, `test_m33_e2e_acceptance.py`, `repository.py`, `model_directory_service.py`, `PreflightService`, `CampaignService`, `test_m17_tools_handoff.py`, `test_m14_preflight.py`, `CampaignRepository`, `new_id`, `TimestampedModel`, `WalletService`, `backend/telephony/vobiz.py`, `PhoneNumberRepository`, `SubscriptionPlanRepository`, `LeadRepository`, `UserRepository`, `run`, `build_demo_registry`, `SubscriptionRepository`, `BaseRepository`, `PhoneNumberService`, `VoiceProfileVersionRepository`, `OrganizationRepository`, `TranscriptRepository`, `PricingSyncService`, `CallService`, `PostCallService`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 134 inferred relationships involving `HTTPException` (e.g. with `call_detail()` and `admin_adjust_wallet()`) actually correct?**
  _`HTTPException` has 134 INFERRED edges - model-reasoned connections that need verification._
- **What connects `MRRData`, `MRRMovement`, `RevenueData` to the rest of the system?**
  _481 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `WalletRepository` be split into smaller, more focused modules?**
  _Cohesion score 0.08045977011494253 - nodes in this community are weakly interconnected._
- **Should `v1/wallet.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11612903225806452 - nodes in this community are weakly interconnected._