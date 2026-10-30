# Soniox STT & Google WaveNet TTS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add managed cloud provider support for Soniox Speech-to-Text (`soniox`) using `SONIOX_API_KEY` and Google Cloud WaveNet Text-to-Speech (`google-wavenet`) using `GOOGLE_API_KEY` across the SaaS pipeline, model directory, and model test service.

**Architecture:**
- Create `GoogleWaveNetTTSProvider` in `backend/providers/tts/google_wavenet.py` implementing `TTSProvider` via Google Cloud Text-to-Speech REST API (`https://texttospeech.googleapis.com/v1/text:synthesize`) with `X-Goog-Api-Key` header authentication.
- Create `SonioxSTTProvider` in `backend/providers/stt/soniox.py` implementing `STTProvider` via Soniox REST API (`https://api.soniox.com/v1/`) with `Authorization: Bearer <key>` authentication.
- Wire both into `CloudProviderRuntime` (`backend/services/provider_runtime.py`) and `ModelTestService` (`backend/services/model_test_service.py`).
- Add metadata entries to `backend/services/model_catalogue_seed.py`, `backend/services/model_directory_service.py`, and `backend/services/pricing_sync_service.py`.

**Tech Stack:** Python 3.13 / 3.14, FastAPI, httpx, pytest, motor/MongoDB.

**Spec:** Direct user request to add support for Soniox (STT) and Google WaveNet (TTS with Google Cloud API key).

## Global Constraints

- Never expose plaintext API keys in exceptions, tracebacks (`from None`), logs, or HTTP responses.
- Providers must adhere to `backend.providers.base.TTSProvider` and `backend.providers.base.STTProvider` interfaces.
- TTS `synthesize` must return `{"audio": pcm_bytes, "sample_rate": int}` with WAV headers stripped when returning raw PCM.
- STT `transcribe` must accept audio bytes and return clean transcript text.
- Must run in cloud-only deployment mode without local dependencies.

## Review Focus

1. **Google WaveNet Audio Format & Header Handling:** When Google Cloud TTS returns LINEAR16 base64 audio containing a 44-byte WAV header (`RIFF...`), strip the header to yield clean raw PCM16 frames matching telephony pipeline expectations.
2. **API Key Traceback Protection:** Both providers must use `raise RuntimeError(sanitized) from None` so raw HTTP exception details with keys cannot leak into `__cause__`.
3. **Missing Credential Handling:** Initializing either provider with empty or missing keys must raise a clean `ValueError`.
4. **Catalogue Idempotence:** New entries in `_ENTRIES` for `soniox` (stt) and `google-wavenet` (tts) must upsert cleanly by `(provider_name, model_id)`.
5. **Runtime Provider Resolution:** `CloudProviderRuntime._build_provider` must instantiate `GoogleWaveNetTTSProvider` when `capability == "tts"` and `provider_name in ("google-wavenet", "google-cloud-tts")`, and `SonioxSTTProvider` when `capability == "stt"` and `provider_name == "soniox"`.

---

### Task 1: Implement `GoogleWaveNetTTSProvider` in `backend/providers/tts/google_wavenet.py`

**Files:**
- Create: `backend/providers/tts/google_wavenet.py`
- Create: `backend/tests/test_soniox_and_google_wavenet.py`

**Interfaces:**
- Consumes: `backend.providers.base.TTSProvider`
- Produces: `GoogleWaveNetTTSProvider` with `synthesize(text, **kwargs) -> dict`, `stream(text, **kwargs) -> AsyncIterator[dict]`, `get_capabilities() -> dict`, `get_voices() -> list[dict]`, `get_models() -> list[str]`.

- [ ] **Step 1: Write failing tests for `GoogleWaveNetTTSProvider`**

In `backend/tests/test_soniox_and_google_wavenet.py`:
- `test_google_wavenet_synthesize_success`: Mock POST to `https://texttospeech.googleapis.com/v1/text:synthesize`, verify base64 audio decoded, 44-byte RIFF header stripped, returns `{"audio": ..., "sample_rate": 16000}`.
- `test_google_wavenet_missing_key_raises`: Verify empty key raises `ValueError("GOOGLE_API_KEY must be provided")`.
- `test_google_wavenet_auth_error_sanitized`: Verify 401/403 errors are sanitized and `__cause__` is `None`.
- `test_google_wavenet_get_capabilities`: Verify capabilities output contains provider name and sample rate.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest backend/tests/test_soniox_and_google_wavenet.py::test_google_wavenet_synthesize_success -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `GoogleWaveNetTTSProvider` in `backend/providers/tts/google_wavenet.py`**

- Implements `GoogleWaveNetTTSProvider(TTSProvider)`.
- Default model: `wavenet`.
- Default voice: `hi-IN-Wavenet-A` (or based on language).
- Connects using `X-Goog-Api-Key` header with `api_key`.
- Decodes base64 `audioContent` and strips 44-byte WAV header if starts with `b"RIFF"`.
- Uses `raise RuntimeError(sanitized) from None`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest backend/tests/test_soniox_and_google_wavenet.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/providers/tts/google_wavenet.py backend/tests/test_soniox_and_google_wavenet.py
git commit -m "feat(tts): implement GoogleWaveNetTTSProvider using Google Cloud API key"
```

---

### Task 2: Implement `SonioxSTTProvider` in `backend/providers/stt/soniox.py`

**Files:**
- Create: `backend/providers/stt/soniox.py`
- Modify: `backend/tests/test_soniox_and_google_wavenet.py`

**Interfaces:**
- Consumes: `backend.providers.base.STTProvider`
- Produces: `SonioxSTTProvider` with `transcribe(audio, **kwargs) -> str`, `get_capabilities() -> dict`, `get_models() -> list[str]`.

- [ ] **Step 1: Write failing tests for `SonioxSTTProvider`**

In `backend/tests/test_soniox_and_google_wavenet.py`:
- `test_soniox_stt_transcribe_success`: Mock file upload and transcription creation/fetch returning transcript text.
- `test_soniox_stt_missing_key_raises`: Verify empty key raises `ValueError("SONIOX_API_KEY must be provided")`.
- `test_soniox_stt_auth_error_sanitized`: Verify 401/403 sanitized with `__cause__ is None`.
- `test_soniox_stt_capabilities`: Verify capabilities report `soniox`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest backend/tests/test_soniox_and_google_wavenet.py::test_soniox_stt_transcribe_success -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `SonioxSTTProvider` in `backend/providers/stt/soniox.py`**

- Implements `SonioxSTTProvider(STTProvider)`.
- Default model: `stt-async-v5`.
- Calls Soniox API with `Authorization: Bearer <key>`.
- Sanitizes errors with `from None`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest backend/tests/test_soniox_and_google_wavenet.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/providers/stt/soniox.py backend/tests/test_soniox_and_google_wavenet.py
git commit -m "feat(stt): implement SonioxSTTProvider using Soniox API key"
```

---

### Task 3: Wire into `CloudProviderRuntime` and `ModelTestService`

**Files:**
- Modify: `backend/services/provider_runtime.py`
- Modify: `backend/services/model_test_service.py`
- Modify: `backend/tests/test_soniox_and_google_wavenet.py`

**Interfaces:**
- Produces: `CloudProviderRuntime._build_provider` returning `GoogleWaveNetTTSProvider` for `tts`/`google-wavenet` and `SonioxSTTProvider` for `stt`/`soniox`.
- Produces: `ModelTestService.test_tts` and `test_stt` routing to test adapters for both providers.

- [ ] **Step 1: Write failing tests for runtime and test service integration**

In `backend/tests/test_soniox_and_google_wavenet.py`:
- `test_runtime_builds_google_wavenet_tts`: Verifies `CloudProviderRuntime._build_provider` instantiates `GoogleWaveNetTTSProvider`.
- `test_runtime_builds_soniox_stt`: Verifies `CloudProviderRuntime._build_provider` instantiates `SonioxSTTProvider`.
- `test_model_test_service_google_wavenet`: Verifies `ModelTestService.test_tts` routes to Google WaveNet.
- `test_model_test_service_soniox`: Verifies `ModelTestService.test_stt` routes to Soniox.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest backend/tests/test_soniox_and_google_wavenet.py::test_runtime_builds_google_wavenet_tts -v`
Expected: FAIL with `ValueError: No managed-cloud runtime adapter`

- [ ] **Step 3: Update `provider_runtime.py` and `model_test_service.py`**

- In `provider_runtime.py`:
  - Under `capability == "tts"`: Add handler for `provider_name in ("google-wavenet", "google-cloud-tts")`.
  - Under `capability == "stt"`: Add handler for `provider_name == "soniox"`.
- In `model_test_service.py`:
  - In `test_tts`: Add handler for `google-wavenet` calling `_test_google_wavenet_tts`.
  - In `test_stt`: Add handler for `soniox` calling `_test_soniox_stt`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest backend/tests/test_soniox_and_google_wavenet.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/provider_runtime.py backend/services/model_test_service.py backend/tests/test_soniox_and_google_wavenet.py
git commit -m "feat: wire Google WaveNet and Soniox into provider runtime and test service"
```

---

### Task 4: Seed Catalogue, Directory Service, and Pricing Rate Cards

**Files:**
- Modify: `backend/services/model_catalogue_seed.py`
- Modify: `backend/services/model_directory_service.py`
- Modify: `backend/services/pricing_sync_service.py`
- Modify: `backend/tests/test_soniox_and_google_wavenet.py`

**Interfaces:**
- Produces: Catalogue seed entries for `google-wavenet` (TTS) and `soniox` (STT), directory service live model lists, and default rate cards.

- [ ] **Step 1: Write failing tests for catalogue, directory service, and pricing**

In `backend/tests/test_soniox_and_google_wavenet.py`:
- `test_catalogue_contains_soniox_and_google_wavenet`: Verifies `_ENTRIES` has `google-wavenet` in TTS and `soniox` in STT.
- `test_directory_service_lists_soniox_and_wavenet`: Verifies `list_provider_live_models` for both.
- `test_pricing_sync_contains_soniox_and_wavenet`: Verifies `DEFAULT_PROVIDER_DEFINITIONS` has entries for both.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest backend/tests/test_soniox_and_google_wavenet.py::test_catalogue_contains_soniox_and_google_wavenet -v`
Expected: FAIL

- [ ] **Step 3: Update `model_catalogue_seed.py`, `model_directory_service.py`, and `pricing_sync_service.py`**

- In `model_catalogue_seed.py`:
  - Add `soniox` (`stt-async-v5`, `SONIOX_API_KEY`) to STT section.
  - Add `google-wavenet` (`wavenet`, `GOOGLE_API_KEY`) to TTS section.
- In `model_directory_service.py`:
  - Add `soniox` and `google-wavenet` to `list_provider_live_models`.
- In `pricing_sync_service.py`:
  - Add default rate card for `soniox` (`₹0.10` / audio minute).
  - Add default rate card for `google-wavenet` (`₹0.0013` / 1k characters).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest backend/tests/test_soniox_and_google_wavenet.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/model_catalogue_seed.py backend/services/model_directory_service.py backend/services/pricing_sync_service.py backend/tests/test_soniox_and_google_wavenet.py
git commit -m "feat: seed Soniox and Google WaveNet in catalogue, directory, and pricing"
```

---

### Task 5: Regression Verification & Knowledge Graph Update

**Files:**
- Test: Full backend test suite
- Update: Knowledge graph via `graphify update .`

- [ ] **Step 1: Run comprehensive regression test suite**
- [ ] **Step 2: Update graphify knowledge graph**
- [ ] **Step 3: Final check and branch merge handoff**
