# Model Directory Catalogue & Auto-Loading Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand and modernize AI model support across STT, LLM, and TTS with working Groq models (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`), allow dynamic live model loading from provider APIs, enable smooth model selection in dropdowns, and support credential reuse.

**Architecture:** 
1. Update `GroqLLMProvider` in `backend/providers/llm/groq.py` with modern supported models and a dynamic `list_available_models()` method.
2. Seed all active production models across STT, LLM, and TTS in `backend/services/model_catalogue_seed.py`.
3. In `ModelDirectoryService`, allow connecting new model configurations using existing credentials and provide a `list_provider_live_models()` endpoint.
4. Enhance frontend `ProviderConfigPanel` and `ModelSetupWizard` to auto-load available models in dropdowns, show credential reuse badges, and allow custom model selection.

**Tech Stack:** Python 3.11+, FastAPI, Motor/MongoDB, Groq Python SDK, Next.js 14, TypeScript, Tailwind CSS.

---

## Global Constraints
- Do not expose decrypted API keys in responses or logs.
- Keep backwards compatibility with existing provider configurations and audio pipelines.
- Strictly adhere to `graphify update .` rule after modifying codebase files.

---

### Task 1: Update Groq LLM Provider Adapter
**Files:**
- Modify: `backend/providers/llm/groq.py`
- Modify: `backend/tests/test_m42_cloud_providers.py`

- [ ] Add `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `qwen/qwen3.8-27b` to `SUPPORTED_MODELS` and set `DEFAULT_MODEL = "openai/gpt-oss-20b"`.
- [ ] Add `async def list_available_models(self) -> list[str]` to query `client.models.list()`.
- [ ] Run provider tests with pytest.

---

### Task 2: Catalogue Seeding, Credential Reuse & Live Models Endpoint
**Files:**
- Modify: `backend/services/model_catalogue_seed.py`
- Modify: `backend/services/model_directory_service.py`
- Modify: `backend/api/v1/model_directory.py`
- Modify: `backend/tests/test_m41_model_directory.py`

- [ ] Seed Groq, Gemini, Sarvam, ElevenLabs, and Google Cloud STT active models in `backend/services/model_catalogue_seed.py`.
- [ ] Fix credential reuse in `connect_provider` in `backend/services/model_directory_service.py` so existing credentials can be used without re-entering plaintext.
- [ ] Add `list_provider_live_models` in `ModelDirectoryService` and expose `GET /api/v1/model-directory/providers/{provider_name}/live-models` in `backend/api/v1/model_directory.py`.
- [ ] Run backend tests with pytest.

---

### Task 3: Frontend API & Dropdown Auto-Loading
**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/components/model-directory/ProviderConfigPanel.tsx`
- Modify: `frontend/components/model-directory/ModelSetupWizard.tsx`

- [ ] Add `listLiveModels` to `api.modelDirectory` in `frontend/lib/api.ts`.
- [ ] In `ProviderConfigPanel.tsx`:
  - Show all capability models in dropdown.
  - Dynamically load live models when a provider is selected.
  - Support credential reuse (API key optional if already stored).
  - Support custom model ID input.
- [ ] In `ModelSetupWizard.tsx`:
  - Display updated cards for all seeded models.
  - Support credential reuse and flexible model selection in Connect Modal.

---

### Task 4: Verification & Graphify Update
- [ ] Run backend test suites.
- [ ] Test local seed script.
- [ ] Run frontend build test.
- [ ] Run `graphify update .`.
