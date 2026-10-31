# Plivo Phone Number Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add first-class support for Plivo as a telephony provider in the Admin Dashboard Phone Number Inventory using API keys, enable multi-organization assignment of Plivo numbers, and support outbound campaigns, AI Agent Studio test calls, and inbound customer calls over real-time WebSockets.

**Architecture:** 
1. **Telephony Adapter & Registry:** `PlivoTelephonyProvider` (`backend/providers/telephony/plivo.py`) implements `TelephonyProvider` to trigger calls via Plivo REST API (`POST https://api.plivo.com/v1/Account/{auth_id}/Call/` with HTTP Basic Auth).
2. **Streaming & Inbound Webhook:** `backend/telephony/plivo.py` provides `/plivo/voice` (PlivoXML) and `/ws/plivo` (WebSocket) with `PlivoTransport` bridging 8 kHz mu-law and 16 kHz PCM audio to `CallSession`, supporting real-time speech, barge-in (`clearAudio`), and inbound credit settlement.
3. **Dispatch & Admin UI:** `CallService.initiate_call` internally resolves number provider and credentials, dispatching calls transparently, while `backend/api/v1/calls.py` handles hangup. The Admin Dashboard supports adding Plivo numbers with `plivo_auth_id`, `plivo_auth_token`, and optional `plivo_app_id` stored in `provider_metadata`.

**Tech Stack:** Python 3.11+, FastAPI, HTTPX, Motor (Async MongoDB), Redis, Next.js 14, TypeScript, Tailwind CSS, WebSockets, `audioop` audio transcoding.

**Spec:** `docs/superpowers/specs/2026-10-31-plivo-phone-provider-design.md`

## Global Constraints
- Preserve provider data isolation: `provider_metadata` must never be present in customer-facing API responses (`_to_customer_view`).
- Preserved provider interface: `PlivoTelephonyProvider` must implement `TelephonyProvider` from `backend.providers.base`.
- Backwards compatibility: Existing calls, campaigns, and phone records with Vobiz and mock numbers must continue to work without modification.
- Audio specs: Plivo audio is 8 kHz mu-law mono; internal `CallSession` operates at 16 kHz PCM16 mono.

## Review Focus
1. What if an organization attempts to call from a Plivo number not assigned to it? `CallService` must validate assignment and reject unauthorized outbound attempts.
2. What if an inbound call hits `/plivo/voice` on a number with zero credits in the inbound organization's wallet? It must reject with an unavailable prompt without starting an unmetered `CallSession`.
3. What if Plivo API credentials are invalid or missing? Outbound calls must roll back credit reservations, mark the call as failed, and return a clear error message.
4. What if the caller speaks over the AI (barge-in)? The system must dispatch `{ "event": "clearAudio", "streamId": streamId }` to flush buffered audio on Plivo.
5. What if the Admin adds a Plivo number without Auth Token? The frontend and backend validation must reject missing required credentials.

---

### Task 1: Plivo Telephony Provider Adapter & Registry Integration

**Files:**
- Create: `backend/providers/telephony/plivo.py`
- Modify: `backend/providers/registry.py:18-34`
- Test: `backend/tests/test_plivo_telephony_provider.py`

**Interfaces:**
- Consumes: `backend.providers.base.TelephonyProvider`
- Produces: `PlivoTelephonyProvider` (`initiate_call`, `hangup_call`, `get_call_status`, `get_capabilities`)

- [ ] **Step 1: Write failing unit tests for `PlivoTelephonyProvider`**
Create `backend/tests/test_plivo_telephony_provider.py` mocking `httpx.AsyncClient`:
1. Test `provider_name == "plivo"` and capabilities (`outbound_calling`, `inbound_calling`, `streaming_audio`).
2. Test `initiate_call(to="+919876543210", from_number="+911234567890", auth_id="p_auth", auth_token="p_tok", url="https://test.com/plivo/voice")`:
   - Verify `POST https://api.plivo.com/v1/Account/p_auth/Call/` is called with HTTP Basic Auth `("p_auth", "p_tok")`.
   - Verify payload contains `from`, `to`, `answer_url`, `answer_method: "POST"`.
   - Verify returned dict contains `provider_resource_id` (from `request_uuid`) and `status: "queued"`.
3. Test `hangup_call` calling `DELETE https://api.plivo.com/v1/Account/p_auth/Call/{call_id}/`.
4. Test `get_call_status` calling `GET https://api.plivo.com/v1/Account/p_auth/Call/{call_id}/`.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_plivo_telephony_provider.py -v`
Expected: FAIL (module `backend.providers.telephony.plivo` not found)

- [ ] **Step 3: Implement `PlivoTelephonyProvider` and register it**
1. In `backend/providers/telephony/plivo.py`:
   - Implement `PlivoTelephonyProvider(TelephonyProvider)` with `provider_name = "plivo"`.
   - In `initiate_call`, `hangup_call`, `get_call_status`, use HTTP Basic Auth with `auth_id` and `auth_token`.
   - In `get_capabilities()`, return `{"outbound_calling": True, "inbound_calling": True, "streaming_audio": True}`.
2. In `backend/providers/registry.py`:
   - Register `PlivoTelephonyProvider` in `build_demo_registry()`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_plivo_telephony_provider.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add backend/providers/telephony/plivo.py backend/providers/registry.py backend/tests/test_plivo_telephony_provider.py
git commit -m "feat(telephony): add PlivoTelephonyProvider adapter"
```

---

### Task 2: Plivo Real-Time Media Stream Webhook & WebSocket

**Files:**
- Create: `backend/telephony/plivo.py`
- Modify: `backend/main.py:545-555`
- Test: `backend/tests/test_plivo_streaming.py`

**Interfaces:**
- Consumes: `CallSession`, `CreditService`, `LeadRepository`, `PhoneNumberRepository`
- Produces: `POST /plivo/voice`, `WebSocket /ws/plivo`, `PlivoTransport`, `hangup_plivo_call`

- [ ] **Step 1: Write failing tests for `/plivo/voice` and `/ws/plivo`**
Create `backend/tests/test_plivo_streaming.py`:
1. Test `POST /plivo/voice?call_id=123`: returns XML containing `<Response><Stream bidirectional="true" keepCallAlive="true">.../ws/plivo?...</Stream><Hangup/></Response>`.
2. Test inbound `POST /plivo/voice` with `To` and `From` when credit balance > 0: resolves agent, reserves credits, creates lead & call, and returns stream XML.
3. Test inbound `POST /plivo/voice` when credits <= 0: returns `<Response><Speak>This number is temporarily unavailable.</Speak><Hangup/></Response>`.
4. Test `PlivoTransport`: encoding PCM16 16kHz to 8kHz mu-law Base64 in `playAudio` frame, and sending `clearAudio` on `clear()`.
5. Test `hangup_plivo_call`: closes WebSocket connection gracefully.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_plivo_streaming.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement `backend/telephony/plivo.py` and mount in `backend/main.py`**
1. Implement `PlivoTransport`:
   - `play(pcm16: bytes, sample_rate: int)`: resample to 8 kHz, convert `lin2ulaw`, chunk into 160-byte blocks, and send:
     `{"event": "playAudio", "streamId": stream_id, "media": {"contentType": "audio/x-mulaw", "sampleRate": 8000, "payload": payload}}`
   - `clear()`: send `{"event": "clearAudio", "streamId": stream_id}`.
   - `close()`: close websocket.
2. Implement route `POST /plivo/voice` (and GET for testing):
   - Outbound: if `call_id` query param present, return PlivoXML `<Stream>`.
   - Inbound: lookup number in `phone_numbers`, verify credit balance, resolve inbound agent and lead, create inbound call, reserve credits, and return PlivoXML `<Stream>`.
3. Implement `WebSocket /ws/plivo`:
   - Initialize `CallSession` with `PlivoTransport`.
   - Receive JSON events (`start`, `media`, `stop`), decode audio, feed into session.
   - On disconnect, finalize session and settle credits.
4. Mount `plivo_router` in `backend/main.py`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_plivo_streaming.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add backend/telephony/plivo.py backend/main.py backend/tests/test_plivo_streaming.py
git commit -m "feat(telephony): add Plivo voice webhook and realtime websocket streaming"
```

---

### Task 3: Plivo Outbound Calling Dispatch & Hangup

**Files:**
- Modify: `backend/services/call_service.py:110-185`
- Modify: `backend/api/v1/calls.py:220-235`
- Test: `backend/tests/test_plivo_call_dispatch.py`

**Interfaces:**
- Consumes: `PhoneNumberRepository`, `PlivoTelephonyProvider`, `CallService`
- Produces: `CallService.initiate_call` with automatic Plivo dispatch and rollback, `hangup_call` endpoint terminating Plivo calls

- [ ] **Step 1: Write failing test for `CallService.initiate_call` dispatching via Plivo**
Create `backend/tests/test_plivo_call_dispatch.py`:
1. Seed a Plivo phone number in `phone_numbers` with `provider: "plivo"` and credentials in `provider_metadata` (`plivo_auth_id`, `plivo_auth_token`).
2. Call `CallService.initiate_call(...)` with `from_number` set to the seeded number.
3. Assert that `PlivoTelephonyProvider.initiate_call` was called with the number's `plivo_auth_id`, `plivo_auth_token`, and answer URL `/plivo/voice`.
4. Assert that if Plivo API fails, credit reservation is released and call status is marked `failed`.
5. Assert that unauthorized org calling from the number is rejected.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_plivo_call_dispatch.py -v`
Expected: FAIL

- [ ] **Step 3: Implement dispatch and error rollback in `CallService` & hangup in `backend/api/v1/calls.py`**
1. In `backend/services/call_service.py`:
   - If `provider == "plivo"` and `phone_doc`:
     - Resolve `auth_id = metadata.get("plivo_auth_id") or metadata.get("auth_id")` and `auth_token = metadata.get("plivo_auth_token") or metadata.get("auth_token")`.
     - Construct `answer_url = f"{base_public}/plivo/voice?call_id={call.id}&agent_id={agent_id or ''}&lang={call_lang}"`.
     - Invoke `PlivoTelephonyProvider().initiate_call(...)`.
     - Update call with `provider_resource_id`.
     - On exception: update call to `failed`, release credits, and raise error.
2. In `backend/api/v1/calls.py`:
   - In `hangup_call`, if `call.get("provider") == "plivo"`:
     - Invoke `hangup_plivo_call(call_id, db=db)`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_plivo_call_dispatch.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add backend/services/call_service.py backend/api/v1/calls.py backend/tests/test_plivo_call_dispatch.py
git commit -m "feat(calls): integrate Plivo provider dispatch and hangup handling"
```

---

### Task 4: Phone Number Model & Privacy Tests for Plivo

**Files:**
- Test: `backend/tests/test_plivo_phone_numbers.py`

**Interfaces:**
- Consumes: `PhoneNumber`, `PhoneNumberService`, `_to_customer_view`
- Produces: Test verification of Plivo credentials isolation and multi-org listing

- [ ] **Step 1: Write test for Plivo phone number isolation and multi-org assignment**
Create `backend/tests/test_plivo_phone_numbers.py`:
1. Verify adding a phone number with `provider: "plivo"` and metadata (`plivo_auth_id`, `plivo_auth_token`).
2. Verify customer view (`_to_customer_view`) never leaks `provider` or `plivo_auth_token` or `provider_metadata`.
3. Verify multi-org assignment allows all assigned orgs to list and see the Plivo number.

- [ ] **Step 2: Run test to verify it passes**
Run: `pytest backend/tests/test_plivo_phone_numbers.py -v`
Expected: PASS

- [ ] **Step 3: Commit**
```bash
git add backend/tests/test_plivo_phone_numbers.py
git commit -m "test(phone_numbers): verify Plivo provider metadata isolation and multi-org assignment"
```

---

### Task 5: Admin Dashboard UI - Plivo Phone Number Support

**Files:**
- Modify: `frontend/app/(admin)/admin/phone-numbers/page.tsx:50-200, 345-360, 480-555`

**Interfaces:**
- Consumes: `api.admin.phoneNumbers.create`
- Produces: UI for adding Plivo numbers with Auth ID & Token; provider badge in inventory table

- [ ] **Step 1: Update `page.tsx` state and form fields**
1. Add `plivo_auth_id`, `plivo_auth_token`, `plivo_app_id` to `addForm` state.
2. In `handleAdd`:
   - If `addForm.provider === "plivo"`, validate that `plivo_auth_id` and `plivo_auth_token` are non-empty.
   - Build `provider_metadata`:
     ```typescript
     provider_metadata: isPlivo
       ? {
           plivo_auth_id: addForm.plivo_auth_id.trim(),
           plivo_auth_token: addForm.plivo_auth_token.trim(),
           plivo_app_id: addForm.plivo_app_id.trim() || undefined,
         }
       : isVobiz
       ? { ... }
       : undefined
     ```
   - Reset form fields on success.

- [ ] **Step 2: Add Plivo Option & Credentials Input Section**
1. In `Select` for Telephony Provider, add:
   `{ value: "plivo", label: "Plivo" }`.
2. When `addForm.provider === "plivo"`, display the Plivo account credentials card (blue-themed):
   - `Plivo Auth ID` (required)
   - `Plivo Auth Token` (required, with toggleable password visibility)
   - `Plivo App / Subaccount ID (Optional)`
3. In table provider badge:
   - If `n.provider === "plivo"`, render blue badge: `"bg-blue-500/10 text-blue-400 border border-blue-500/20"`.

- [ ] **Step 3: Build frontend and verify TypeScript compilation**
Run: `npm run build` inside `frontend/` (or check TypeScript with `npx tsc --noEmit`).
Expected: 0 errors.

- [ ] **Step 4: Commit**
```bash
git add frontend/app/\(admin\)/admin/phone-numbers/page.tsx
git commit -m "feat(admin): add Plivo provider inputs and badge in phone numbers page"
```

---

### Task 6: End-to-End Verification & Graph Update

- [ ] **Step 1: Run all backend tests**
Run: `pytest backend/tests/test_plivo_*.py backend/tests/test_vobiz_*.py -v`
Expected: All tests pass.

- [ ] **Step 2: Run graphify update**
Run: `graphify update .`
Expected: AST update completes successfully.

- [ ] **Step 3: Final git status review**
Verify clean working tree.
