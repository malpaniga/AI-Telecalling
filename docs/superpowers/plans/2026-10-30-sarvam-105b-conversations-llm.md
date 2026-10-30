# Sarvam 105B Conversations LLM Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `sarvam-105b-conversations` as a supported LLM in the SaaS platform using Sarvam AI's managed cloud chat completions API with the existing `SARVAM_API_KEY` credential setup.

**Architecture:** 
- Implement `SarvamLLMProvider` in `backend/providers/llm/sarvam.py` inheriting from `backend.providers.base.LLMProvider` using `httpx.AsyncClient` targeting `https://api.sarvam.ai/v1/chat/completions`.
- Wire `SarvamLLMProvider` into `ProviderRuntimeService` (`backend/services/provider_runtime.py`) and `ModelTestService` (`backend/services/model_test_service.py`).
- Add `sarvam-105b-conversations` catalogue metadata to `backend/services/model_catalogue_seed.py`, `backend/services/model_directory_service.py`, and `backend/services/pricing_sync_service.py`.
- Re-use the existing `sarvam` credential (`SARVAM_API_KEY`) configured in the Super Admin credential store.

**Tech Stack:** Python 3.14 / 3.13, FastAPI, httpx, pytest, motor/MongoDB.

**Spec:** Direct user request to add `sarvam-105b-conversations` in LLM using Sarvam's managed cloud API and existing `SARVAM_API_KEY` credentials.

## Global Constraints

- Never expose plaintext API keys or credentials in logs, error exceptions, or HTTP responses.
- All pricing numbers must be handled with standard integer paise or explicit float base rates per turn.
- Providers must adhere to `backend.providers.base.LLMProvider` interface (`generate`, `stream`, `get_capabilities`, `get_models`).
- Must run in cloud-only deployment mode without local dependencies.

## Review Focus

1. **API Key Redaction:** When Sarvam API returns 401 Unauthorized or 429 Rate Limit containing the secret key, ensure `_sanitize_sarvam_error` never leaks the key in the raised `RuntimeError`.
2. **Missing Credential Handling:** Attempting to initialize `SarvamLLMProvider` with empty/None API key must raise a clean `ValueError`.
3. **SSE Stream Chunk Parsing:** Streaming from `https://api.sarvam.ai/v1/chat/completions` must properly parse `data: {"choices":[{"delta":{"content":"..."}}]}` lines and gracefully terminate on `data: [DONE]`.
4. **Catalogue Idempotence:** The seed entry for `sarvam-105b-conversations` in `model_catalogue_seed.py` must upsert cleanly alongside existing LLMs without duplicating records.
5. **Runtime Provider Building:** `ProviderRuntimeService._build_provider` must instantiate `SarvamLLMProvider` when `capability == "llm"` and `provider_name == "sarvam"`.

---

### Task 1: Implement `SarvamLLMProvider` in `backend/providers/llm/sarvam.py`

**Files:**
- Create: `backend/providers/llm/sarvam.py`
- Create: `backend/tests/test_sarvam_llm.py`

**Interfaces:**
- Consumes: `backend.providers.base.LLMProvider`
- Produces: `SarvamLLMProvider` with methods `generate(messages, **kwargs) -> str`, `stream(messages, **kwargs) -> AsyncIterator[str]`, `get_capabilities() -> dict`, `get_models() -> list[str]`.

- [ ] **Step 1: Write the failing tests for `SarvamLLMProvider`**

In `backend/tests/test_sarvam_llm.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.providers.llm.sarvam import SarvamLLMProvider, DEFAULT_MODEL

@pytest.mark.anyio
async def test_sarvam_llm_provider_generate_success():
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Namaste! How can I help you today?"}}]
    }
    mock_client.post = AsyncMock(return_value=mock_resp)

    provider = SarvamLLMProvider(api_key="test-sarvam-key", _client=mock_client)
    res = await provider.generate([{"role": "user", "content": "Hello"}])
    assert res == "Namaste! How can I help you today?"

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args.kwargs
    assert call_kwargs["json"]["model"] == DEFAULT_MODEL
    assert call_kwargs["headers"]["api-subscription-key"] == "test-sarvam-key"

@pytest.mark.anyio
async def test_sarvam_llm_provider_stream_success():
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    async def mock_aiter_lines():
        lines = [
            'data: {"choices":[{"delta":{"content":"Namaste"}}]}',
            'data: {"choices":[{"delta":{"content":" ji!"}}]}',
            'data: [DONE]',
        ]
        for line in lines:
            yield line

    mock_resp.aiter_lines = mock_aiter_lines
    mock_client.stream = MagicMock()
    mock_client.stream.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_client.stream.return_value.__aexit__ = AsyncMock(return_value=None)

    provider = SarvamLLMProvider(api_key="test-sarvam-key", _client=mock_client)
    chunks = []
    async for chunk in provider.stream([{"role": "user", "content": "Hello"}]):
        chunks.append(chunk)

    assert "".join(chunks) == "Namaste ji!"

def test_sarvam_llm_provider_missing_key_raises():
    with pytest.raises(ValueError, match="SARVAM_API_KEY"):
        SarvamLLMProvider(api_key="")

@pytest.mark.anyio
async def test_sarvam_llm_provider_auth_error_sanitized():
    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("401 Unauthorized: key secret-key-xyz invalid")
    provider = SarvamLLMProvider(api_key="secret-key-xyz", _client=mock_client)
    with pytest.raises(RuntimeError) as exc_info:
        await provider.generate([{"role": "user", "content": "hi"}])
    assert "secret-key-xyz" not in str(exc_info.value)
    assert "Sarvam" in str(exc_info.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_sarvam_llm.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.providers.llm.sarvam'`

- [ ] **Step 3: Implement `SarvamLLMProvider` in `backend/providers/llm/sarvam.py`**

Implement `SarvamLLMProvider` with:
- `DEFAULT_MODEL = "sarvam-105b-conversations"`
- `SUPPORTED_MODELS = {"sarvam-105b-conversations", "sarvam-105b"}`
- `__init__(self, api_key: str, model: str = DEFAULT_MODEL, timeout: float = 30.0, max_tokens: int = 512, temperature: float = 0.6, _client: httpx.AsyncClient | None = None)`
- Strips leading "Bearer " and whitespace from `api_key`.
- Handles `generate` via HTTP POST to `https://api.sarvam.ai/v1/chat/completions`.
- Handles `stream` via HTTP SSE streaming to `https://api.sarvam.ai/v1/chat/completions`.
- Sanitizes error with `_sanitize_sarvam_error(exc, model)` to strip secret keys.
- Implements `get_capabilities()` and `get_models()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_sarvam_llm.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/providers/llm/sarvam.py backend/tests/test_sarvam_llm.py
git commit -m "feat(llm): implement SarvamLLMProvider for sarvam-105b-conversations"
```

---

### Task 2: Integrate `SarvamLLMProvider` into `ProviderRuntimeService` and `ModelTestService`

**Files:**
- Modify: `backend/services/provider_runtime.py`
- Modify: `backend/services/model_test_service.py`
- Modify: `backend/tests/test_sarvam_llm.py`

**Interfaces:**
- Consumes: `SarvamLLMProvider`
- Produces: `ProviderRuntimeService._build_provider` instantiating `SarvamLLMProvider` for capability `llm` and provider `sarvam`; `ModelTestService.test_llm` routing `sarvam` to `_test_sarvam_llm`.

- [ ] **Step 1: Write the failing tests for runtime provider and test service integration**

In `backend/tests/test_sarvam_llm.py`, add:
```python
from backend.services.provider_runtime import ProviderRuntimeService
from backend.models.model_directory import ProviderConfiguration
from backend.services.model_test_service import ModelTestService

def test_runtime_service_builds_sarvam_llm():
    config = ProviderConfiguration(
        provider_name="sarvam",
        capability="llm",
        model_id="sarvam-105b-conversations",
        is_active=True,
    )
    provider = ProviderRuntimeService._build_provider(config, credential="test-key-123")
    assert isinstance(provider, SarvamLLMProvider)
    assert provider.model == "sarvam-105b-conversations"

@pytest.mark.anyio
async def test_model_test_service_sarvam_llm(monkeypatch):
    svc = ModelTestService()
    mock_generate = AsyncMock(return_value="Hello from Sarvam!")
    monkeypatch.setattr(SarvamLLMProvider, "generate", mock_generate)

    res = await svc.test_llm("sarvam", "sarvam-105b-conversations", credential="test-key")
    assert res["status"] == "ok"
    assert res["response"] == "Hello from Sarvam!"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_sarvam_llm.py::test_runtime_service_builds_sarvam_llm -v`
Expected: FAIL because `provider_runtime.py` does not handle `sarvam` under `llm`.

- [ ] **Step 3: Implement runtime and model test integrations**

1. In `backend/services/provider_runtime.py`:
Add inside `if config.capability == "llm":`:
```python
if config.provider_name == "sarvam":
    from backend.providers.llm.sarvam import SarvamLLMProvider
    return SarvamLLMProvider(
        api_key=_required_credential(config, credential),
        model=config.model_id or "sarvam-105b-conversations",
        **_llm_options(params),
    )
```

2. In `backend/services/model_test_service.py`:
In `test_llm`:
```python
elif provider_name == "sarvam":
    response = await self._test_sarvam_llm(credential, model_id)
```
Add method:
```python
async def _test_sarvam_llm(self, credential: str | None, model_id: str) -> str:
    if not credential:
        raise ValueError("SARVAM_API_KEY is required for Sarvam LLM")
    from backend.providers.llm.sarvam import SarvamLLMProvider
    provider = SarvamLLMProvider(
        api_key=credential,
        model=model_id or "sarvam-105b-conversations",
    )
    return await provider.generate(
        [{"role": "user", "content": "Say hello in one sentence."}]
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_sarvam_llm.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/provider_runtime.py backend/services/model_test_service.py backend/tests/test_sarvam_llm.py
git commit -m "feat(llm): wire SarvamLLMProvider into provider runtime and test service"
```

---

### Task 3: Seed `sarvam-105b-conversations` in Model Catalogue, Directory Service, and Pricing

**Files:**
- Modify: `backend/services/model_catalogue_seed.py`
- Modify: `backend/services/model_directory_service.py`
- Modify: `backend/services/pricing_sync_service.py`
- Modify: `backend/tests/test_sarvam_llm.py`

**Interfaces:**
- Produces: `sarvam-105b-conversations` entry in `_ENTRIES`, `list_live_models("sarvam")` including `sarvam-105b-conversations`, and default pricing definition.

- [ ] **Step 1: Write the failing tests for catalogue, directory service, and pricing**

In `backend/tests/test_sarvam_llm.py`, add:
```python
from backend.services.model_catalogue_seed import _ENTRIES
from backend.services.pricing_sync_service import DEFAULT_PROVIDER_DEFINITIONS

def test_catalogue_seed_contains_sarvam_105b_conversations():
    matching = [
        entry for entry in _ENTRIES
        if entry["provider_name"] == "sarvam"
        and entry["model_id"] == "sarvam-105b-conversations"
        and entry["capability"] == "llm"
    ]
    assert len(matching) == 1
    entry = matching[0]
    assert entry["streaming_supported"] is True
    assert "SARVAM_API_KEY" in entry["credential_requirements"]

def test_pricing_sync_contains_sarvam_llm():
    matching = [
        defn for defn in DEFAULT_PROVIDER_DEFINITIONS
        if defn["provider_name"] == "sarvam"
        and defn["model_id"] == "sarvam-105b-conversations"
        and defn["capability"] == "llm"
    ]
    assert len(matching) == 1
    assert matching[0]["base_currency"] == "INR"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_sarvam_llm.py::test_catalogue_seed_contains_sarvam_105b_conversations -v`
Expected: FAIL because `sarvam-105b-conversations` is not yet seeded.

- [ ] **Step 3: Update `model_catalogue_seed.py`, `model_directory_service.py`, and `pricing_sync_service.py`**

1. In `backend/services/model_catalogue_seed.py`:
Add to `_ENTRIES` (in LLM section):
```python
    {
        "provider_name": "sarvam",
        "model_id": "sarvam-105b-conversations",
        "capability": "llm",
        "hosting_mode": "managed_api",
        "supported_languages": ["hi", "ta", "te", "kn", "mr", "bn", "gu", "ml", "pa", "en-IN", "multilingual"],
        "streaming_supported": True,
        "credential_requirements": ["SARVAM_API_KEY"],
        "setup_requirements": "Create API key at dashboard.sarvam.ai",
        "license_spdx": "Proprietary",
        "commercial_use_allowed": True,
        "free_tier_info": {"note": "Free tier available; contact Sarvam for current quota. Verified 2026-Q1."},
        "free_tier_verified_date": "2026-01-01",
        "pricing_per_minute_usd": None,
        "doc_url": "https://docs.sarvam.ai",
        "model_card_url": None,
        "implementation_status": "supported",
        "notes": "Sarvam 105B conversational model optimized for real-time dialogue and voice agent interactions across Indian languages.",
    },
```

2. In `backend/services/model_directory_service.py`:
In `list_live_models(provider_name)` under `elif provider_name == "sarvam":`:
Add `"sarvam-105b-conversations"` and `"sarvam-105b"` to the models list.

3. In `backend/services/pricing_sync_service.py`:
Add to `DEFAULT_PROVIDER_DEFINITIONS` under `LLM`:
```python
    {
        "provider_name": "sarvam",
        "model_id": "sarvam-105b-conversations",
        "capability": "llm",
        "display_name": "Sarvam 105B Conversations",
        "base_currency": "INR",
        "billing_unit": "turn",
        "base_unit_rate": 0.05,
        "notes": "Sarvam 105B conversational LLM rate per dialogue turn.",
    },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_sarvam_llm.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/model_catalogue_seed.py backend/services/model_directory_service.py backend/services/pricing_sync_service.py backend/tests/test_sarvam_llm.py
git commit -m "feat(llm): seed sarvam-105b-conversations in catalogue, directory, and pricing"
```

---

### Task 4: Regression Verification & Graphify Update

**Files:**
- Test: `backend/tests/test_sarvam_llm.py`
- Test: `backend/tests/test_m42_cloud_providers.py`
- Test: `backend/tests/test_m41_model_directory.py`

- [ ] **Step 1: Run comprehensive tests**

Run:
```bash
pytest backend/tests/test_sarvam_llm.py backend/tests/test_m42_cloud_providers.py backend/tests/test_m41_model_directory.py -v
```
Expected: All tests PASS without regressions.

- [ ] **Step 2: Update graphify knowledge graph**

Run:
```bash
graphify update .
```
Expected: Knowledge graph updated cleanly.

- [ ] **Step 3: Final Git status check**

Run: `git status`
Expected: Clean working tree.
