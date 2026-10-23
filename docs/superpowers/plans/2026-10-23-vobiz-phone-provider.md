# Vobiz.ai Phone Number Provider & Multi-Organization Assignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add first-class support for Vobiz.ai as a telephony provider in the Admin Dashboard Phone Number Inventory, allow multi-organization assignment of numbers with per-number Vobiz credentials, and enable these numbers to be used for outbound campaigns, AI Agent Studio test calls, and inbound customer calls.

**Architecture:**
1. **Multi-Org Data Model:** `PhoneNumber` schema in MongoDB is enhanced to support `assigned_org_ids: list[str]`, `inbound_organization_id: Optional[str]`, and `inbound_agent_id: Optional[str]`, while keeping `organization_id` for backward compatibility. Per-number Vobiz credentials (`vobiz_auth_id`, `vobiz_auth_token`) are stored in `provider_metadata` and never exposed to customer-facing APIs.
2. **Telephony Adapter & Streaming:** `VobizTelephonyProvider` (`backend/providers/telephony/vobiz.py`) implements `TelephonyProvider` to trigger calls via Vobiz's REST API. `backend/telephony/vobiz.py` provides `/vobiz/voice` (VobizXML) and `/ws/vobiz` (WebSocket) with `VobizTransport` bridging 8 kHz mu-law and 16 kHz PCM audio to `CallSession`, supporting real-time speech, barge-in (`clearAudio`), and inbound credit settlement.
3. **Dispatch & Frontend UI:** `CallService.initiate_call` internally resolves number provider and credentials, dispatching calls transparently. The Admin Dashboard supports adding Vobiz numbers and assigning them to multiple organizations with inbound agent selection. AI Agent Studio allows users to pick their assigned calling number for phone testing.

**Tech Stack:** Python 3.11+, FastAPI, Motor (Async MongoDB), Redis, Next.js 14, TypeScript, Tailwind CSS, WebSockets, `audioop`/`scipy` audio resampling.

**Spec:** `docs/superpowers/specs/2026-10-23-vobiz-phone-provider-design.md`

## Global Constraints
- Preserve provider data isolation: `provider_metadata` must never be present in customer-facing API responses (`_to_customer_view`).
- Preserved provider interface: `VobizTelephonyProvider` must implement `TelephonyProvider` from `backend.providers.base`.
- Backwards compatibility: Existing calls, campaigns, and phone records with single `organization_id` must continue to work seamlessly.
- Audio specs: Vobiz audio is 8 kHz mu-law mono; internal `CallSession` operates at 16 kHz PCM16 mono.

## Review Focus
1. What if an organization attempts to call from a number not assigned to it? `CallService` must validate assignment and reject unauthorized outbound attempts.
2. What if an inbound call hits `/vobiz/voice` on a number with zero credits in the inbound organization's wallet? It must reject or speak an unavailable prompt without starting an unmetered `CallSession`.
3. What if a number is assigned to multiple organizations? Inbound calls must deterministically route to `inbound_organization_id` (or the first organization in `assigned_org_ids`), while all assigned orgs can use it for outbound calls.
4. What if Vobiz API credentials are invalid or missing? Outbound calls must roll back credit reservations, mark the call as failed, and return a clear error message.
5. What if the caller speaks over the AI (barge-in)? The system must dispatch `{ "event": "clearAudio", "streamId": streamId }` to flush buffered audio on Vobiz.

---

### Task 1: Phone Number Multi-Organization Data Model & Service Layer

**Files:**
- Modify: `backend/models/phone_number.py:28-70`
- Modify: `backend/repositories/phone_number_repo.py:22-190`
- Modify: `backend/services/phone_number_service.py:54-150`
- Modify: `backend/api/v1/phone_numbers.py:140-165`
- Test: `backend/tests/test_vobiz_phone_numbers.py`

**Interfaces:**
- Consumes: `PhoneNumberRepository`, `motor.motor_asyncio.AsyncIOMotorDatabase`
- Produces: `PhoneNumber.assigned_org_ids`, `PhoneNumber.inbound_organization_id`, `PhoneNumber.inbound_agent_id`, `PhoneNumberService.assign_to_orgs()`

- [ ] **Step 1: Write the failing tests for multi-org assignment and customer isolation**
Create `backend/tests/test_vobiz_phone_numbers.py` testing:
1. Adding a number with `provider: "vobiz"` and metadata (`vobiz_auth_id`, `vobiz_auth_token`).
2. Assigning the number to multiple organizations (`["org_1", "org_2"]`).
3. Calling `list_org_numbers("org_1")` and `list_org_numbers("org_2")` to ensure both organizations see the number.
4. Verifying customer view does NOT leak `vobiz_auth_token` or `provider_metadata`.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_vobiz_phone_numbers.py -v`
Expected: FAIL (missing fields/methods)

- [ ] **Step 3: Update `PhoneNumber` model, repository, and service**
1. In `backend/models/phone_number.py`:
   - Add `assigned_org_ids: list[str] = Field(default_factory=list)`
   - Add `inbound_organization_id: Optional[str] = None`
   - Add `inbound_agent_id: Optional[str] = None`
2. In `backend/repositories/phone_number_repo.py`:
   - Update `list_for_org(org_id)` to query `{"$or": [{"organization_id": org_id}, {"assigned_org_ids": org_id}], "status": {"$in": ["assigned", "available"]}}`.
   - Add `assign_to_orgs(phone_number_id, org_ids: list[str], inbound_org_id: Optional[str] = None, inbound_agent_id: Optional[str] = None)`.
3. In `backend/services/phone_number_service.py`:
   - Add `assign_to_orgs(phone_number_id, org_ids, inbound_org_id, inbound_agent_id, performed_by)`.
   - Ensure `_to_customer_view` omits `provider_metadata` and includes customer-safe assignment details.
4. In `backend/api/v1/phone_numbers.py`:
   - Update `assign_number` endpoint to accept optional `org_ids: list[str]`, `inbound_organization_id: Optional[str]`, `inbound_agent_id: Optional[str]`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_vobiz_phone_numbers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add backend/models/phone_number.py backend/repositories/phone_number_repo.py backend/services/phone_number_service.py backend/api/v1/phone_numbers.py backend/tests/test_vobiz_phone_numbers.py
git commit -m "feat(phone_numbers): support multi-org assignment and Vobiz provider metadata"
```

---

### Task 2: Vobiz Telephony Provider Adapter & Registry Integration

**Files:**
- Create: `backend/providers/telephony/vobiz.py`
- Modify: `backend/providers/registry.py:17-25`
- Test: `backend/tests/test_vobiz_telephony_provider.py`

**Interfaces:**
- Consumes: `backend.providers.base.TelephonyProvider`
- Produces: `VobizTelephonyProvider` (`initiate_call`, `hangup_call`, `get_call_status`)

- [ ] **Step 1: Write failing unit tests for `VobizTelephonyProvider`**
Create `backend/tests/test_vobiz_telephony_provider.py` mocking `httpx.AsyncClient`:
1. Test `initiate_call(to="+919876543210", from_number="+911234567890", auth_id="v_auth", auth_token="v_tok", url="https://test.com/vobiz/voice")`:
   - Verify `POST https://api.vobiz.ai/api/v1/Account/v_auth/Call/` is called with headers `X-Auth-ID: v_auth`, `X-Auth-Token: v_tok`.
   - Verify returned dict contains `provider_resource_id` and `status: "queued"`.
2. Test `hangup_call` and `get_call_status`.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_vobiz_telephony_provider.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement `VobizTelephonyProvider` and register it**
1. In `backend/providers/telephony/vobiz.py`:
   - Implement `VobizTelephonyProvider(TelephonyProvider)` with `provider_name = "vobiz"`.
   - Implement `initiate_call`, `hangup_call`, `get_call_status`.
   - Implement `get_capabilities()` returning `{"outbound_calling": True, "inbound_calling": True, "streaming_audio": True}`.
2. In `backend/providers/registry.py`:
   - Import and register `VobizTelephonyProvider` in `build_demo_registry()`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_vobiz_telephony_provider.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add backend/providers/telephony/vobiz.py backend/providers/registry.py backend/tests/test_vobiz_telephony_provider.py
git commit -m "feat(telephony): add VobizTelephonyProvider adapter"
```

---

### Task 3: Vobiz Real-Time Media Stream WebSocket & Webhook

**Files:**
- Create: `backend/telephony/vobiz.py`
- Modify: `backend/main.py:448-460`
- Test: `backend/tests/test_vobiz_streaming.py`

**Interfaces:**
- Consumes: `CallSession`, `CreditService`, `LeadRepository`, `PhoneNumberRepository`
- Produces: `POST /vobiz/voice`, `WebSocket /ws/vobiz`, `VobizTransport`

- [ ] **Step 1: Write failing tests for `/vobiz/voice` and `/ws/vobiz`**
Create `backend/tests/test_vobiz_streaming.py`:
1. Test `POST /vobiz/voice?call_id=123`: returns XML containing `<Response><Stream bidirectional="true">.../ws/vobiz...</Stream></Response>`.
2. Test inbound `POST /vobiz/voice` with `To` and `From` when credit balance > 0: resolves agent and returns stream XML.
3. Test inbound `POST /vobiz/voice` when credits <= 0: returns `<Response><Speak>...<Hangup/></Response>`.
4. Test `VobizTransport`: encoding PCM16 16kHz to 8kHz mu-law Base64 in `playAudio` frame, and sending `clearAudio` on `clear()`.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_vobiz_streaming.py -v`
Expected: FAIL (routes not found)

- [ ] **Step 3: Implement `backend/telephony/vobiz.py` and mount in `backend/main.py`**
1. Implement `VobizTransport`:
   - `play(pcm16: bytes, sample_rate: int)`: resample from `sample_rate` to 8000 Hz, convert `lin2ulaw`, chunk into base64 payload, and send `{"event": "playAudio", "streamId": stream_id, "media": {"contentType": "audio/x-mulaw", "sampleRate": 8000, "payload": b64}}`.
   - `clear()`: send `{"event": "clearAudio", "streamId": stream_id}`.
2. Implement route `POST /vobiz/voice`:
   - If `call_id` query param is present (outbound), render `<Stream>` with query params.
   - If no `call_id` (inbound):
     - Lookup number in `phone_numbers` where `number == To`.
     - Check credits on `inbound_organization_id`: if insufficient, reject with prompt.
     - Reserve credits and match/create `Lead` with `phone == From`.
     - Create call record and return `<Stream>` XML pointing to `/ws/vobiz`.
3. Implement `WebSocket /ws/vobiz`:
   - Connect `CallSession` with `VobizTransport`.
   - Parse JSON events: `start` (streamId), `media` (b64 mu-law 8kHz -> PCM16 16kHz -> push to session).
   - On disconnect, finalize session and settle credits.
4. Mount `vobiz_router` in `backend/main.py`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_vobiz_streaming.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add backend/telephony/vobiz.py backend/main.py backend/tests/test_vobiz_streaming.py
git commit -m "feat(telephony): add Vobiz voice webhook and realtime websocket streaming"
```

---

### Task 4: Outbound Calling Integration in `CallService` & Campaign Worker

**Files:**
- Modify: `backend/services/call_service.py:52-120`
- Modify: `backend/workers/campaign_worker.py:150-175`
- Test: `backend/tests/test_vobiz_call_dispatch.py`

**Interfaces:**
- Consumes: `PhoneNumberRepository`, `VobizTelephonyProvider`, `CallService`
- Produces: `CallService.initiate_call` with automatic Vobiz dispatch and rollback

- [ ] **Step 1: Write failing test for `CallService.initiate_call` dispatching via Vobiz**
Create `backend/tests/test_vobiz_call_dispatch.py`:
1. Seed a Vobiz phone number in `phone_numbers` with `provider: "vobiz"` and credentials in `provider_metadata`.
2. Call `CallService.initiate_call(...)` with `from_number` set to the seeded number.
3. Assert that `VobizTelephonyProvider.initiate_call` was called with the number's `vobiz_auth_id` and `vobiz_auth_token`.
4. Assert that if Vobiz API fails, credit reservation is cancelled and call is marked `failed`.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_vobiz_call_dispatch.py -v`
Expected: FAIL

- [ ] **Step 3: Implement dispatch and error rollback in `CallService`**
1. In `backend/services/call_service.py`:
   - In `initiate_call`, query `PhoneNumberRepository.find_by_number(from_number)`.
   - If the number's provider is `"vobiz"`:
     - Instantiate `VobizTelephonyProvider`.
     - Construct `answer_url = f"{public_base_url}/vobiz/voice?call_id={call.id}&agent_id={agent_id}&lang=en-IN"`.
     - Invoke `provider.initiate_call(to=to_number, from_number=from_number, auth_id=metadata['vobiz_auth_id'], auth_token=metadata['vobiz_auth_token'], url=answer_url)`.
     - Update call record with `provider_resource_id`.
   - On dispatch failure, rollback reservation via `credit_svc.refund(...)` and update status to `failed`.
2. In `backend/workers/campaign_worker.py`:
   - Ensure campaign worker passes `from_number=campaign.calling_number` without overriding to `"mock"`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_vobiz_call_dispatch.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add backend/services/call_service.py backend/workers/campaign_worker.py backend/tests/test_vobiz_call_dispatch.py
git commit -m "feat(calls): integrate Vobiz provider dispatch and error handling in CallService"
```

---

### Task 5: Frontend Admin Dashboard - Phone Number Inventory & Multi-Org UI

**Files:**
- Modify: `frontend/lib/api.ts:240-270`
- Modify: `frontend/app/(admin)/admin/phone-numbers/page.tsx:35-420`

**Interfaces:**
- Consumes: `api.admin.phoneNumbers`, `api.phoneNumbers`
- Produces: UI for adding Vobiz numbers with Auth ID & Token; UI for multi-org assignment

- [ ] **Step 1: Update `frontend/lib/api.ts`**
1. Update `PhoneNumber` interface in `frontend/lib/api.ts` to include:
   - `assigned_org_ids?: string[]`
   - `inbound_organization_id?: string`
   - `inbound_agent_id?: string`
   - `provider_metadata?: Record<string, unknown>`
2. Update `api.phoneNumbers.assign` signature to support `{ org_ids: string[], inbound_org_id?: string, inbound_agent_id?: string }`.

- [ ] **Step 2: Update `frontend/app/(admin)/admin/phone-numbers/page.tsx`**
1. In "Add Number" modal:
   - Add Provider dropdown option for `vobiz`.
   - When `vobiz` is selected, show required input fields:
     - `Vobiz Auth ID`
     - `Vobiz Auth Token` (with password mask toggle)
   - Include these in `provider_metadata` sent to `api.phoneNumbers.addAdmin`.
2. In "Assign Number" modal:
   - Fetch organizations list via `api.admin.organizations.list()`.
   - Allow selecting multiple organizations using multi-select checkboxes or badges.
   - Allow selecting the `Inbound Organization` from the selected organizations.
   - If an inbound organization is selected, load its agents via `api.agents.list({ org_id })` and allow selecting the `Inbound Agent`.
3. In Inventory Table:
   - Display assigned organizations as badge list or summary (e.g. "3 orgs").
   - Display Provider badge (e.g. `vobiz`, `exotel`, `twilio`).

- [ ] **Step 3: Verify TypeScript compilation**
Run: `npm run build` or `npx tsc --noEmit` in `frontend/`
Expected: No type errors

- [ ] **Step 4: Commit**
```bash
git add frontend/lib/api.ts frontend/app/\(admin\)/admin/phone-numbers/page.tsx
git commit -m "feat(admin): add Vobiz credentials and multi-org assignment UI in Phone Numbers"
```

---

### Task 6: Frontend AI Agent Studio - Calling Number Selection

**Files:**
- Modify: `frontend/app/(dashboard)/agents/[id]/page.tsx:864-885,1935-1965`

**Interfaces:**
- Consumes: `api.phoneNumbers.myNumbers()`, `api.calls.initiate`
- Produces: Calling Number dropdown in AI Agent Studio Phone Test tab

- [ ] **Step 1: Add Calling Number state and selector in Agent Studio**
In `frontend/app/(dashboard)/agents/[id]/page.tsx`:
1. Add state `assignedPhoneNumbers: PhoneNumber[]` and `selectedCallingNumber: string`.
2. On page load, fetch `api.phoneNumbers.myNumbers()`, set `assignedPhoneNumbers`, and default `selectedCallingNumber` to `numbers[0]?.number || ""`.
3. In `testTab === "phone"` (around lines 1948-1965):
   - If `assignedPhoneNumbers.length > 0`, render a Select dropdown for "Calling Number / Caller ID":
     ```tsx
     <Select
       label="Calling Number"
       value={selectedCallingNumber}
       onChange={(e) => setSelectedCallingNumber(e.target.value)}
       options={assignedPhoneNumbers.map((p) => ({ value: p.number, label: `${p.number} (${p.display_name || p.provider || 'Assigned'})` }))}
     />
     ```
   - If no numbers assigned, display warning: `"No phone numbers assigned to your organization. Contact your administrator."` and disable dial button.
4. In `handleDialPhone`:
   - Replace hardcoded `from_number: "+911234567890"` with `from_number: selectedCallingNumber`.

- [ ] **Step 2: Verify TypeScript compilation**
Run: `npm run build` or `npx tsc --noEmit` in `frontend/`
Expected: No type errors

- [ ] **Step 3: Commit**
```bash
git add frontend/app/\(dashboard\)/agents/\[id\]/page.tsx
git commit -m "feat(studio): support selecting assigned calling number for agent phone tests"
```

---

### Task 7: Full System Verification & Graphify Update

**Files:**
- Test: `backend/tests/`
- Documentation: `graphify update .`

- [ ] **Step 1: Run complete backend test suite**
Run: `pytest backend/tests/test_vobiz_phone_numbers.py backend/tests/test_vobiz_telephony_provider.py backend/tests/test_vobiz_streaming.py backend/tests/test_vobiz_call_dispatch.py -v`
Expected: All tests pass (100% green).

- [ ] **Step 2: Run frontend build verification**
Run: `npm run build` in `frontend/`
Expected: Build succeeds with 0 errors.

- [ ] **Step 3: Update knowledge graph**
Run: `graphify update .`
Expected: Knowledge graph updated with all new nodes and routes.

- [ ] **Step 4: Final commit**
```bash
git commit --allow-empty -m "chore: complete Vobiz telephony provider integration and verification"
```
