# M41 Implementation Plan — AI Models Directory and One-Click Provider Setup

## Architecture decisions

**MongoDB not PostgreSQL.** The project migrated to MongoDB + Motor in M1. The `backend/db/models.py` SQLAlchemy file still exists but is dead code; ignore it. All new models extend `backend.models.base.TimestampedModel` (Pydantic + Motor pattern established in M3–M9).

**No new pip package for encryption.** `cryptography` is already installed transitively via `python-jose[cryptography]`. `Fernet` encryption in `backend/core/secrets.py` uses it directly — no `cryptography` line needed in `requirements.txt`.

**Adapter stubs, not fake success.** AI4Bharat and faster-whisper adapters raise `NotImplementedError` and catalogue entries set `implementation_status='experimental'`. `ModelTestService` returns `{status:'unavailable'}` for these — it never reports success for unimplemented adapters.

**No Alembic.** There is no migration system; MongoDB indexes are declared in `backend/core/db.py` `init_db()` and created idempotently at startup.

**ProviderRouter in M10 is separate.** `backend/providers/router.py` (M10) handles call-time routing. The new `ModelDirectoryService` manages configuration and activation; on `activate_provider` it updates the `provider_configurations` collection that the runtime router will read in a future sprint. For M41, activation updates the DB only — no in-flight call migration is needed because there is no live call-routing integration yet.

**Test pattern.** All tests use `def run(coro): loop=asyncio.new_event_loop(); ...` — no `pytest-asyncio`, no `@pytest.mark.asyncio`. This matches M8, M10.

---

## Implementation Plan

- [ ] 1. Create `backend/models/model_directory.py` — three Pydantic MongoDB document models.
      Create `AIModelCatalogue(TimestampedModel)` with fields: `provider_name: str`, `model_id: str`, `capability: str` (one of `tts|stt|llm`), `hosting_mode: str` (one of `managed_api|local_runtime|self_hosted`), `supported_languages: list[str]`, `streaming_supported: bool`, `credential_requirements: list[str]`, `setup_requirements: str`, `license_spdx: str`, `commercial_use_allowed: bool`, `free_tier_info: dict | None`, `free_tier_verified_date: str | None`, `pricing_per_minute_usd: float | None`, `doc_url: str`, `model_card_url: str | None`, `implementation_status: str` (one of `supported|experimental|unavailable`), `notes: str | None`.
      Create `ProviderConfiguration(TimestampedModel)` with fields: `capability: str`, `provider_name: str`, `model_id: str`, `is_active: bool = False`, `is_fallback: bool = False`, `voice: str | None`, `language: str | None`, `extra_params: dict = {}`, `last_tested_at: datetime | None`, `last_test_result: str | None`, `last_test_latency_ms: int | None`, `activated_at: datetime | None`.
      Create `ProviderCredential(TimestampedModel)` with fields: `provider_name: str`, `encrypted_value: bytes`, `key_hint: str`, `created_by: str`, `rotated_at: datetime | None`.
      File: `backend/models/model_directory.py`
      Verify: `python -c "from backend.models.model_directory import AIModelCatalogue, ProviderConfiguration, ProviderCredential; print('models OK')"` — no import errors.

- [ ] 2. Create `backend/core/secrets.py` — Fernet credential store.
      `CredentialStore` derives a 32-byte Fernet key from `settings.secret_key` via `hashlib.sha256(settings.secret_key.encode()).digest()` then base64url-encodes it per Fernet spec (`base64.urlsafe_b64encode`). Methods: `encrypt(plaintext: str) -> bytes` (never log), `decrypt(ciphertext: bytes) -> str`, `key_hint(plaintext: str) -> str` (returns `plaintext[-4:]` or `'****'` if shorter than 4 chars). Module-level singleton `credential_store = CredentialStore()`. Raises `ValueError` if plaintext is empty before encrypting.
      File: `backend/core/secrets.py`
      Verify: `python -c "from backend.core.secrets import credential_store; e=credential_store.encrypt('ABCD1234'); d=credential_store.decrypt(e); assert d=='ABCD1234'; assert credential_store.key_hint('ABCD1234')=='1234'; print('secrets OK')"`.

- [ ] 3. Create `backend/repositories/model_directory_repo.py` — three repository classes extending `BaseRepository`.
      `AIModelCatalogueRepo`: `collection_name='ai_model_catalogue'`, `model_class=AIModelCatalogue`. Methods: `find_by_capability(capability: str)`, `find_by_status(status: str)`, `search(query: str)` using `$regex` with `$options:'i'` on `provider_name`, `model_id`, and `notes` combined with `$or`, `upsert_by_provider_model(doc: AIModelCatalogue)` using `update_one` with `upsert=True` filtering on `(provider_name, model_id)`.
      `ProviderConfigurationRepo`: `collection_name='provider_configurations'`, `model_class=ProviderConfiguration`. Methods: `find_active_for_capability(capability)` returns single active config or None, `find_all_for_capability(capability)`, `deactivate_all_for_capability(capability)` sets `is_active=False` on all, `find_by_id(config_id)`.
      `ProviderCredentialRepo`: `collection_name='provider_credentials'`, `model_class=ProviderCredential`. Methods: `find_by_provider(provider_name)` returns list of credentials, `store_credential(cred: ProviderCredential)`, `mark_rotated(provider_name)` sets `rotated_at=utcnow()` on all non-rotated entries, `delete_by_provider(provider_name)` removes all entries. IMPORTANT: these methods return `ProviderCredential` objects with `encrypted_value` field — callers must not forward `encrypted_value` in API responses.
      File: `backend/repositories/model_directory_repo.py`
      Verify: `python -c "from backend.repositories.model_directory_repo import AIModelCatalogueRepo, ProviderConfigurationRepo, ProviderCredentialRepo; print('repos OK')"`.

- [ ] 4. Add adapter stubs — no files removed, no existing behavior changed.
      In `backend/audio/tts.py`: add `class AI4BharatTTSEngine(TTSEngine)` and `class IndicF5Engine(TTSEngine)` — both `__init__` raise `NotImplementedError('AI4Bharat TTS adapter not yet implemented. Status: experimental.')`. Their `synthesize` methods also raise `NotImplementedError` (for abstract method compliance).
      In `backend/audio/stt.py`: add `class FasterWhisperSTT` (does NOT extend any existing abstract base) — `__init__` raises `NotImplementedError('faster-whisper adapter not yet implemented. Status: experimental.')`. Add `transcribe` method signature for IDE support, also raising `NotImplementedError`.
      In `backend/agent/llm.py`: add `class OllamaLLMClient` — `__init__(self, base_url: str = 'http://localhost:11434', model: str = 'llama3.2')` stores both. `async def is_runtime_reachable(self) -> bool` makes `GET {base_url}/api/tags` with 3s timeout; returns `True` if 200, `False` on any exception. `async def generate(self, messages: list[Message], system_prompt: str | None = None) -> str` calls `POST {base_url}/api/chat` with `{"model": self.model, "messages": messages, "stream": False}`; raises `RuntimeError('Ollama runtime not reachable')` if connectivity check fails first.
      Files: `backend/audio/tts.py`, `backend/audio/stt.py`, `backend/agent/llm.py`
      Verify: `python -c "from backend.audio.tts import AI4BharatTTSEngine; from backend.audio.stt import FasterWhisperSTT; from backend.agent.llm import OllamaLLMClient; print('stubs OK')"` — no import errors. Existing `from backend.audio.tts import PiperEngine, SarvamEngine, get_tts_engine` must still work.

- [ ] 5. Create `backend/services/model_test_service.py` — test inference for each provider type.
      `ModelTestService` class with `__init__(self)` and three async methods:
      `test_tts(provider_name, model_id, credential: str | None, voice: str | None, language: str | None) -> dict`: dispatches to the appropriate engine. For `sarvam`: instantiate `SarvamEngine` with the credential injected (subclass or monkey-patch for test isolation). For `piper`: call `get_tts_engine()` only if `TTS_ENGINE=piper`. For stubs (`ai4bharat-indicf5`, `ai4bharat-indic-tts`, `elevenlabs`): return `{status:'unavailable', error:'Adapter not yet implemented'}`. Records elapsed time. Returns `{status:'ok', latency_ms:N}` on success.
      `test_stt(provider_name, model_id, credential: str | None, language: str | None) -> dict`: For `groq-whisper`: instantiate `STTClient` with the credential, call `transcribe` with a 10-byte fake WAV. For `sarvam`: instantiate `SarvamSTT`. For stubs: return unavailable. Returns `{status:'ok', latency_ms:N, transcript:str}`.
      `test_llm(provider_name, model_id, credential: str | None) -> dict`: For `groq`: instantiate `LLMClient` with the credential and model, call `complete([{'role':'user','content':'Say hello in one sentence.'}])`. For `ollama`: instantiate `OllamaLLMClient`, call `is_runtime_reachable()` first — if False return `{status:'unavailable', error:'Ollama runtime not reachable on localhost:11434'}`, else call `generate`. For stubs: unavailable. Returns `{status:'ok', latency_ms:N, response:str}`.
      All methods catch exceptions and return `{status:'error', error: str(exc)}` — never propagate raw exceptions to callers.
      File: `backend/services/model_test_service.py`
      Verify: `python -c "from backend.services.model_test_service import ModelTestService; print('test service OK')"`.

- [ ] 6. Create `backend/services/model_directory_service.py` — main orchestration service.
      `ModelDirectoryService(db: AsyncIOMotorDatabase)` with:
      `list_catalogue(capability=None, status=None, search=None)` — filters from `AIModelCatalogueRepo`, adds a `pricing_stale: bool` flag to each result where `free_tier_verified_date` is older than 90 days.
      `get_model(model_id: str)` — single lookup by composite `(provider_name+':'+model_id)` pattern or scan; raise 404-like `LookupError` if missing.
      `connect_provider(req: dict, credential_plaintext: str | None, user: CurrentUser)` — validates user has platform role; validates `capability` is in `{tts,stt,llm}`; validates language against catalogue `supported_languages` (raise `ValueError` for incompatible language); if `credential_requirements` non-empty and `credential_plaintext` is empty/None raise `ValueError`; encrypt credential via `credential_store`; store `ProviderCredential`; store `ProviderConfiguration` with `is_active=False`; call `audit_log_repo.log(action='provider.configure', ...)`. Return created `ProviderConfiguration`.
      `test_provider(config_id: str, user: CurrentUser)` — load config; decrypt credential; check test-call rate limit (max 10 per provider per hour, tracked in `provider_test_log` collection); call `ModelTestService`; update config `last_tested_at`, `last_test_result`, `last_test_latency_ms`; log audit entry. Return test result dict.
      `activate_provider(config_id: str, user: CurrentUser)` — load config; if `last_test_result != 'ok'` raise `ValueError('Cannot activate untested or failed configuration')`; call `ProviderConfigurationRepo.deactivate_all_for_capability(capability)`; set this config `is_active=True`, `activated_at=utcnow()`; log audit `action='provider.activate'`. Return updated config.
      `get_active_config(capability: str)` — returns active `ProviderConfiguration` or None.
      `list_configs(capability: str | None = None)` — all configs, credential fields stripped.
      `list_credentials(provider_name: str)` — calls `ProviderCredentialRepo.find_by_provider`; returns list of dicts with ONLY `{provider_name, key_hint, created_at, rotated_at}` — never `encrypted_value`.
      `rotate_credential(provider_name: str, new_plaintext: str, user: CurrentUser)` — encrypt new; `mark_rotated` old; store new; log audit `action='provider.credential.rotate'`.
      `delete_credential(provider_name: str, user: CurrentUser)` — delete all credentials and all configurations for that provider; log audit `action='provider.credential.delete'`.
      `update_fallback(config_id: str, fallback_config_id: str, user: CurrentUser)` — set `is_fallback=True` on fallback config; log audit.
      File: `backend/services/model_directory_service.py`
      Verify: `python -c "from backend.services.model_directory_service import ModelDirectoryService; print('service OK')"`.

- [ ] 7. Create `backend/api/v1/model_directory.py` — 11 REST endpoints.
      `router = APIRouter(prefix='/model-directory', tags=['model-directory'])`. All routes use `Depends(require_platform('platform_owner', 'platform_admin'))` — NOT `require_platform()` (which includes `support` and `billing_admin`). Inject `CurrentUser` via `Depends(require_platform(...))`.
      Endpoint definitions:
      `GET /catalogue` — query params `capability: str|None`, `status: str|None`, `search: str|None`. Returns `list[dict]`. No credentials in response.
      `GET /catalogue/{model_id}` — returns single catalogue entry dict.
      `POST /configurations` — body `ConfigureProviderBody(provider_name, model_id, capability, credential_plaintext: str|None, voice: str|None, language: str|None, extra_params: dict, is_fallback: bool)`. Returns created config (no credential fields).
      `GET /configurations` — query `capability: str|None`. Returns list of configs.
      `GET /configurations/{config_id}` — returns single config.
      `POST /configurations/{config_id}/test` — returns test result dict.
      `POST /configurations/{config_id}/activate` — returns updated config.
      `POST /configurations/{config_id}/fallback` — body `{fallback_config_id: str}`. Returns updated config.
      `DELETE /configurations/{config_id}` — returns `{status: 'deleted', config_id: str}`.
      `GET /credentials/{provider_name}` — returns list of `{provider_name, key_hint, created_at, rotated_at}` only.
      `POST /credentials/{provider_name}/rotate` — body `{new_plaintext: str}`. Returns `{status: 'rotated'}`.
      `DELETE /credentials/{provider_name}` — returns `{status: 'deleted'}`.
      Error handling: catch `LookupError` → 404, `ValueError` → 400, `PermissionError` → 403, `RateLimitError` (custom exception from service) → 429 with message about quota.
      File: `backend/api/v1/model_directory.py`
      Verify: `python -c "from backend.api.v1.model_directory import router; print(len(router.routes), 'routes registered')"` — should print 12.

- [ ] 8. Register new router in `backend/api/v1/__init__.py`.
      Add `model_directory` to the existing `from backend.api.v1 import ..., model_directory` import line. Add `router.include_router(model_directory.router)` after the `provider_ops` include. DO NOT touch any other line in this file.
      File: `backend/api/v1/__init__.py`
      Verify: `python -c "from backend.api.v1 import router; routes=[r.path for r in router.routes]; assert any('/model-directory' in p for p in routes); print('router registered OK')"`.

- [ ] 9. Add MongoDB index declarations in `backend/core/db.py`.
      Find the `init_db` function. Add three index creation blocks after existing ones:
      `ai_model_catalogue`: `unique on [("provider_name",1),("model_id",1)]`, plus index on `[("capability",1),("implementation_status",1)]`.
      `provider_configurations`: index on `[("capability",1),("is_active",1)]`, index on `[("provider_name",1)]`.
      `provider_credentials`: unique on `[("provider_name",1)]` — NOTE: this means only one active credential per provider name; the `mark_rotated` pattern handles rotation history by setting `rotated_at` rather than deleting old entries, so the unique constraint is on non-rotated credentials. Actually use a non-unique index on `provider_name` to allow rotation history (multiple rows per provider). Revise: index on `[("provider_name",1)]` (non-unique), index on `[("provider_name",1),("rotated_at",1)]`.
      Use `await db["ai_model_catalogue"].create_index(...)` pattern matching the existing code in `init_db`.
      File: `backend/core/db.py`
      Verify: `python -m pytest tests/ -x -q` — all tests pass (init_db is called in test fixtures).

- [ ] 10. Create `backend/services/model_catalogue_seed.py` — seed all 12 catalogue entries.
      `async def seed_model_catalogue(db: AsyncIOMotorDatabase)` — instantiates `AIModelCatalogueRepo(db)` and calls `upsert_by_provider_model` for each of the 12 entries defined in FEAT-001 step 11. Idempotent: re-running changes nothing. Log counts of seeded vs skipped via `logging.getLogger('seed.catalogue')`.
      Call `await seed_model_catalogue(db)` inside `backend/main.py` lifespan function (alongside existing `seed_default_packs` and `seed_default_plans` calls).
      Files: `backend/services/model_catalogue_seed.py`, `backend/main.py`
      Verify: `python -c "import asyncio, mongomock_motor; from backend.services.model_catalogue_seed import seed_model_catalogue; db=mongomock_motor.AsyncMongoMockClient()['t']; asyncio.run(seed_model_catalogue(db)); print('seed OK')"`.

- [ ] 11. Create `backend/tests/test_m41_model_directory.py` — 15 test cases.
      Use `def run(coro)` pattern. All 15 test cases as specified in FEAT-002 steps 2–16. Label mock-based tests with docstring containing `[mock]`. Group into: catalogue tests (1), credential/connection tests (2–5), authorization tests (5), inference tests (6–10), lifecycle tests (11–14), isolation test (15).
      File: `backend/tests/test_m41_model_directory.py`
      Verify: `cd backend && python -m pytest tests/test_m41_model_directory.py -v` — all pass. Then `python -m pytest tests/ -x -q` — full regression passes.

- [ ] 12. Add TypeScript interfaces and `api.modelDirectory` namespace to `frontend/lib/api.ts`.
      Add five interfaces after the existing `VoiceProfile` interface: `AIModelCatalogue`, `ProviderConfiguration`, `ProviderCredentialMeta`, `ConnectProviderRequest`, `TestResult` — exact shapes from FEAT-003 step 1.
      Add `modelDirectory: { ... }` namespace to the `api` object with all 12 methods from FEAT-003 step 2.
      File: `frontend/lib/api.ts`
      Verify: `cd frontend && npx tsc --noEmit` — no TypeScript errors.

- [ ] 13. Update `frontend/components/layout/admin-sidebar.tsx` — add four new nav links.
      Add to `ADMIN_LINKS` array after the `{href:'/admin/providers'...}` entry:
      `{ href: '/admin/models', label: 'AI Models', icon: BrainCircuit }`,
      `{ href: '/admin/providers/tts', label: 'TTS Config', icon: Volume2 }`,
      `{ href: '/admin/providers/stt', label: 'STT Config', icon: AudioWaveform }`,
      `{ href: '/admin/providers/llm', label: 'LLM Config', icon: Bot }`.
      Add `BrainCircuit, Volume2, AudioWaveform, Bot` to the lucide-react import. If `BrainCircuit` is not available in the installed version, use `Brain` or `CircuitBoard` as fallback (check `frontend/node_modules/lucide-react/dist/index.js` for availability).
      File: `frontend/components/layout/admin-sidebar.tsx`
      Verify: `cd frontend && npx tsc --noEmit` — no errors on this file.

- [ ] 14. Create `frontend/app/(admin)/admin/models/page.tsx` — AI Models Directory page.
      Full implementation per FEAT-003 step 4. Key details:
      - Debounced search: use `useEffect` with a 300ms `setTimeout` on `search` state change, clearing previous timeout on re-render.
      - Capability tabs: four `Button` components with `variant={filter === cap ? 'primary' : 'secondary'}`. Values: `''` (All), `'llm'`, `'tts'`, `'stt'`.
      - `ModelCard` sub-component (defined in same file or extracted): card with fixed height, overflow-hidden, shows all metadata listed in FEAT-003 step 4. Action button at card bottom.
      - Free-tier staleness: `const isStale = (dateStr: string) => { const d = new Date(dateStr); return Date.now() - d.getTime() > 90*24*60*60*1000; }`. Show `<span className="text-warning text-xs">Pricing data may be stale</span>` if stale.
      - Never show 'Connected' state on this page.
      File: `frontend/app/(admin)/admin/models/page.tsx`
      Verify: `cd frontend && npm run build` — 0 errors.

- [ ] 15. Create `frontend/components/model-directory/ProviderConfigPanel.tsx` — shared config panel.
      Full implementation per FEAT-003 step 5. Key implementation details:
      - `ConnectModal` uses `<input type="password" autoComplete="new-password" />` for API key input — never `type="text"` for credentials.
      - Test button: shows inline spinner while testing (per-row `testing[configId]` state). On result, update a local `testResults: Record<string, TestResult>` state and show colored badge in the row.
      - Activate button: `disabled` attribute set when `testResults[config.id]?.status !== 'ok'`. Shows confirmation `window.confirm()` dialog before calling `activateConfig`.
      - Fallback section: a select dropdown listing all non-active configs for the same capability; save calls `api.modelDirectory.setFallback`.
      - Credential rotate form: inline collapsible `<details>` per provider showing rotate/delete actions.
      Files: `frontend/components/model-directory/ProviderConfigPanel.tsx` (create directory `frontend/components/model-directory/` first)
      Verify: `cd frontend && npm run build` — 0 errors.

- [ ] 16. Create three provider config pages.
      `frontend/app/(admin)/admin/providers/tts/page.tsx` — header 'TTS Provider Configuration', `<ProviderConfigPanel capability="tts" />`.
      `frontend/app/(admin)/admin/providers/stt/page.tsx` — header 'STT Provider Configuration', `<ProviderConfigPanel capability="stt" />`.
      `frontend/app/(admin)/admin/providers/llm/page.tsx` — header 'LLM Provider Configuration', `<ProviderConfigPanel capability="llm" />`. The LLM panel additionally shows a JSON `<textarea>` for `extra_params` in the ConnectModal; validated client-side with `JSON.parse` before submit.
      The existing `frontend/app/(admin)/admin/providers/page.tsx` MUST NOT be modified.
      Files: `frontend/app/(admin)/admin/providers/tts/page.tsx`, `frontend/app/(admin)/admin/providers/stt/page.tsx`, `frontend/app/(admin)/admin/providers/llm/page.tsx`
      Verify: `cd frontend && npm run build` — 0 errors. Confirm existing `/admin/providers` page builds without changes.

- [ ] 17. Update documentation and commit.
      In `MVP_PROGRESS.md`: add M41 checkpoint entry with: status PASS, objective, implementation summary (new files list), API changes (all 12 endpoints), database changes (3 new collections + indexes), test count, known gaps (AI4Bharat and faster-whisper adapters experimental, ElevenLabs not in call pipeline yet, Ollama routing not wired into call pipeline).
      Create `MVP_TEST_STATUS.md` if it doesn't exist, or append M41 section: list all 15 test cases, their mock/live status, and expected outcomes.
      Files: `MVP_PROGRESS.md`, `MVP_TEST_STATUS.md`
      Verify: Files updated, `git diff --check` shows no whitespace errors.

- [ ] 18. Final build verification and commit.
      Run `cd backend && python -m pytest tests/ -x -q` — all tests pass.
      Run `cd frontend && npm run build` — 0 TypeScript errors, 0 ESLint errors.
      Run `git diff --check` — no whitespace errors.
      Stage specific files (do NOT `git add .`):
      ```
      git add backend/models/model_directory.py
      git add backend/core/secrets.py
      git add backend/repositories/model_directory_repo.py
      git add backend/audio/tts.py
      git add backend/audio/stt.py
      git add backend/agent/llm.py
      git add backend/services/model_test_service.py
      git add backend/services/model_directory_service.py
      git add backend/api/v1/model_directory.py
      git add backend/api/v1/__init__.py
      git add backend/core/db.py
      git add backend/services/model_catalogue_seed.py
      git add backend/main.py
      git add backend/tests/test_m41_model_directory.py
      git add frontend/lib/api.ts
      git add frontend/components/layout/admin-sidebar.tsx
      git add "frontend/app/(admin)/admin/models/page.tsx"
      git add frontend/components/model-directory/ProviderConfigPanel.tsx
      git add "frontend/app/(admin)/admin/providers/tts/page.tsx"
      git add "frontend/app/(admin)/admin/providers/stt/page.tsx"
      git add "frontend/app/(admin)/admin/providers/llm/page.tsx"
      git add MVP_PROGRESS.md
      git add MVP_TEST_STATUS.md
      git commit -m "checkpoint: M41 AI models directory and one-click provider setup"
      ```
      Verify: `git log --oneline -1` shows the commit.

---

## Known gaps and non-blockers

- **AI4Bharat adapters** (`IndicConformer`, `IndicF5`, `Indic-TTS`): `experimental` status in catalogue, `NotImplementedError` stubs. Not connected to call pipeline.
- **faster-whisper**: `experimental` stub. Needs `pip install faster-whisper` and a full adapter implementation.
- **ElevenLabs TTS**: `M8` created `backend/providers/tts/elevenlabs.py` but it is not wired into `get_tts_engine()` or the call pipeline. Catalogue entry is `experimental`.
- **Runtime routing integration**: `activate_provider` writes to `provider_configurations` collection. A future sprint should update `backend/providers/router.py` to read from this collection for live call routing.
- **In-flight call safety**: No active call-pipeline integration in M41 means no risk to existing campaigns. Routing change safety (per the spec) is deferred to that future sprint.
- **Gemini adapter**: Catalogue entry present (`supported`), but actual `LLMClient` for Gemini not implemented. `test_llm('gemini', ...)` returns `{status:'unavailable'}`. Full Gemini adapter is a separate sprint.
