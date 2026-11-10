# Voicemail & Siri/Screening Detection (AMD) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect Apple Siri (Live Voicemail), Google Call Screen, and carrier voicemail greetings in real-time, close the call as fast as possible (always under 1 minute), bill credits based on actual talk time used (duration rounded to standard 1-min increments), reschedule the lead for retry, and provide a toggle to enable/disable this feature in the Campaign Wizard.

**Architecture:** 
1. Real-time phrase & pattern detector in `backend/call_session.py` on caller utterances (turns 1–2) covering Apple Live Voicemail, Google Call Screen, carrier answering machines, and multilingual voicemails.
2. Immediate short-circuit hangup on match: terminates audio, skips further LLM & TTS generation, sets outcome to `"voicemail"`, and closes transport immediately (target < 10s, guaranteed < 60s).
3. Billing & retry integration in `backend/services/call_service.py`: bills according to actual connected talk time (`actual_credits = (duration_s + 59) // 60`), meaning calls closing under 1 minute only consume 1 credit (and refund the remaining 4 reserved credits), while updating `CampaignLead` to `"callback"` for future retry attempts up to `max_attempts`.
4. Schema & API extensions in `Campaign`, `Call`, `CampaignRepository`, `CampaignService`, and `api/v1/campaigns.py` to persist and propagate `detect_voicemail: bool = True`.
5. Frontend Campaign Creation Wizard updates in `frontend/app/(dashboard)/campaigns/new/` (`step-schedule.tsx`, `step-review.tsx`, `page.tsx`) and `frontend/lib/api.ts` adding a toggle with clear credit-saving guidance.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, Motor (MongoDB), Redis, Next.js 14 (App Router), TypeScript, Tailwind CSS.

**Spec:** User request: "sometimes iphone siri or android voice mail pickup the call and ask our agent to leave a msg so our agent pitch them which burn our credits so how we can avoid this to happened..?" + "yes but give option to enable or disable it while creating campaign in campain wizard..."

---

## Global Constraints

- Default behavior: `detect_voicemail = True` (protects user credits out-of-the-box).
- Under-1-minute hangup: When voicemail/screening is detected, the call must disconnect immediately (target < 5–10s, guaranteed < 60s) so it never spills into multiple minutes.
- Fair usage billing: Connected voicemail calls bill according to actual duration: `(duration_s + 59) // 60` credits (e.g. 15s talk time bills 1 credit, refunding the remaining 4 reserved credits back to the organization wallet).
- Campaign retry safety: Voicemail calls must NOT be marked as `failed` or `contacted`; they must transition to `callback` and schedule a retry according to the campaign's `retry_policy.retry_delay_minutes`.
- Telephony neutrality: Works seamlessly across all transports (Vobiz, Plivo, Web browser).
- Backward compatibility: Existing campaigns without `detect_voicemail` field in DB default to `True`.

---

## Review Focus

1. **Siri Live Voicemail phrase on turn 1:** STT transcribes "Hi, please state your name and why you're calling"; session immediately halts, emits no pitch, closes under 1 minute, bills for actual talk time (1 credit if connected < 60s), sets outcome to `voicemail`.
2. **Google Call Screen on turn 1:** STT transcribes "Hi, the person you're reaching is using a screening service from Google..."; session immediately halts and sets outcome to `voicemail`.
3. **Voicemail detection disabled on campaign:** User explicitly set `detect_voicemail: false` in wizard; agent ignores screening phrases and pitches as usual.
4. **Legitimate human answering:** Human says "Hello, who is this?" or "Yes, speaking"; detector does NOT trigger, normal conversation proceeds.
5. **Credit settlement:** Org wallet balance before call: 49 available, 0 reserved. Call starts: 44 available, 5 reserved. Voicemail detected & closed in 12s: 1 credit billed (`duration_s=12`), 4 credits refunded. New balance: 48 available, 0 reserved. Exactly 1 credit consumed instead of 2–5 credits.

---

### Task 1: Backend Voicemail Detection & CallSession Hangup Pipeline

**Files:**
- Create: `backend/tests/test_voicemail_detection.py`
- Modify: `backend/call_session.py:73-105, 120-188, 420-560`
- Modify: `backend/models/call.py:60-70`
- Modify: `backend/repositories/call_repo.py:25-50`

**Interfaces:**
- Consumes: `user_text` from STT transcription, `detect_voicemail: bool` on session.
- Produces: Instant disconnect, `outcome: "voicemail"`, `reason: "voicemail_detected"`.

- [ ] **Step 1: Write unit tests for voicemail detection patterns and CallSession short-circuit**

Create `backend/tests/test_voicemail_detection.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.call_session import _is_voicemail_or_screening

def test_siri_live_voicemail_patterns():
    assert _is_voicemail_or_screening("Hi, please state your name and why you're calling") is True
    assert _is_voicemail_or_screening("State your name and why you are calling and I'll see if they are available") is True
    assert _is_voicemail_or_screening("The person you are trying to reach is not available, please leave a message") is True

def test_google_call_screen_patterns():
    assert _is_voicemail_or_screening("Hi, the person you're reaching is using a screening service from Google") is True
    assert _is_voicemail_or_screening("Google screening service, please say why you are calling") is True

def test_carrier_voicemail_patterns():
    assert _is_voicemail_or_screening("Please leave your message after the tone") is True
    assert _is_voicemail_or_screening("At the tone, please record your message") is True
    assert _is_voicemail_or_screening("You have reached the voicemail of 8698732771") is True
    assert _is_voicemail_or_screening("कृपया संदेश छोड़ें") is True

def test_human_answers_not_detected_as_voicemail():
    assert _is_voicemail_or_screening("Hello, who is calling?") is False
    assert _is_voicemail_or_screening("Yes, speaking, what is this about?") is False
    assert _is_voicemail_or_screening("Namaste, kaun bol raha hai?") is False
    assert _is_voicemail_or_screening("Sure, tell me more about the project") is False
```

- [ ] **Step 2: Run pytest to verify initial failure**

Run command: `pytest backend/tests/test_voicemail_detection.py` and ensure it fails because `_is_voicemail_or_screening` does not exist yet.

- [ ] **Step 3: Implement pattern matcher and CallSession hangup hook**

In `backend/call_session.py`:
1. Define comprehensive `_VOICEMAIL_PATTERNS` (Siri, Google Call Screen, Carrier Answering Machines, Multilingual).
2. Implement `_is_voicemail_or_screening(text: str) -> bool`.
3. In `CallSession.__init__`: accept `detect_voicemail: bool = True` and store `self.detect_voicemail = detect_voicemail`.
4. In `_handle_utterance`:
   At the start of utterance handling (when `self.turn_count <= 2`):
   ```python
   if self.detect_voicemail and _is_voicemail_or_screening(user_text):
       log.info("Voicemail / screening detected: %r for call %s; hanging up immediately to save credits", user_text, self.call_id)
       self._call_ending = True
       self.state["output_variables"]["disposition"] = "voicemail"
       await self.t.notify({"type": "hangup", "reason": "voicemail_detected", "outcome": "voicemail"})
       if self.call_id:
           try:
               from backend.telephony.broadcaster import call_broadcaster
               await call_broadcaster.broadcast(str(self.call_id), {"type": "hangup", "reason": "voicemail_detected", "outcome": "voicemail"})
           except Exception:
               pass
       # Persist turn
       await self._persist_turn("user", user_text, "voicemail")
       await self._save_session()
       # Trigger rapid close
       if hasattr(self.t, "close"):
           asyncio.create_task(self.t.close())
       return
   ```
5. Add `detect_voicemail: bool = True` to `Call` model in `backend/models/call.py` and `backend/repositories/call_repo.py`.

- [ ] **Step 4: Run pytest and confirm tests pass**

Run `pytest backend/tests/test_voicemail_detection.py` and verify all pattern tests pass.

---

### Task 2: Call Settlement and Lead Retry Integration for Voicemail

**Files:**
- Modify: `backend/services/call_service.py:380-420, 475-520`
- Modify: `backend/telephony/vobiz.py:405-415, 650-675`
- Modify: `backend/telephony/plivo.py:405-415, 650-675`
- Test: `backend/tests/test_voicemail_call_settlement.py`

**Interfaces:**
- Consumes: `CallService.finalize_call(outcome="voicemail")`.
- Produces: 0 credits consumed, all 5 reserved credits released back to org wallet, `CampaignLead` rescheduled with `callback` status.

- [ ] **Step 1: Write integration test for voicemail settlement & lead retry**

Create `backend/tests/test_voicemail_call_settlement.py`:
- Test that calling `finalize_call` with `outcome="voicemail"` settles 0 credits and releases the 5-credit hold.
- Test that `campaign_leads` status updates to `"callback"` and calculates `next_attempt_at = now + retry_delay_minutes`.

- [ ] **Step 2: Update `backend/services/call_service.py`**
1. In credit settlement logic:
   ```python
   # Unconnected, unanswered, or voicemail screening calls cost 0 credits
   if (status in ("no_answer", "busy", "failed", "cancelled") or outcome == "voicemail") and (not call.connected_at or outcome == "voicemail"):
       actual_credits = 0
   ```
2. In lead status & retry logic:
   Map `outcome == "voicemail"` to `new_cl_status = "callback"` when `attempts < max_attempts`, scheduling `next_attempt_at`.

3. In `initiate_call`:
   If `campaign_id` is passed, query campaign document to inherit `detect_voicemail = camp_doc.get("detect_voicemail", True)` and save on `Call` doc.

4. In `backend/telephony/vobiz.py` and `plivo.py`:
   Extract `detect_voicemail = call_doc.get("detect_voicemail", True)` when instantiating `CallSession`.

- [ ] **Step 3: Run pytest on settlement test**

Run `pytest backend/tests/test_voicemail_call_settlement.py` and confirm clean execution.

---

### Task 3: Campaign Backend Model, API, and Repository

**Files:**
- Modify: `backend/models/campaign.py:100-140`
- Modify: `backend/repositories/campaign_repo.py:20-60`
- Modify: `backend/services/campaign_service.py:155-200`
- Modify: `backend/api/v1/campaigns.py:30-55, 85-115`
- Test: `backend/tests/test_campaign_voicemail_config.py`

**Interfaces:**
- Consumes: `detect_voicemail: bool = True` in `POST /api/v1/campaigns`.
- Produces: `detect_voicemail` persisted in MongoDB and returned in GET `/api/v1/campaigns/{id}`.

- [ ] **Step 1: Write tests for campaign creation with detect_voicemail flag**

Create `backend/tests/test_campaign_voicemail_config.py`:
- Test campaign created with default `detect_voicemail=True`.
- Test campaign created with explicit `detect_voicemail=False`.
- Test serialization in API response.

- [ ] **Step 2: Update Campaign model, repo, service, and API schemas**
1. In `backend/models/campaign.py`: Add `detect_voicemail: bool = True`.
2. In `backend/repositories/campaign_repo.py`: Add parameter `detect_voicemail: bool = True`.
3. In `backend/services/campaign_service.py`: Pass `detect_voicemail` through `create_campaign`.
4. In `backend/api/v1/campaigns.py`:
   - `CreateCampaignRequest`: `detect_voicemail: bool = True`.
   - `UpdateCampaignRequest`: `detect_voicemail: Optional[bool] = None`.
   - `_campaign_response`: include `"detect_voicemail": getattr(c, "detect_voicemail", True)`.

- [ ] **Step 3: Run pytest on campaign config test**

Run `pytest backend/tests/test_campaign_voicemail_config.py`.

---

### Task 4: Frontend Campaign Wizard UI Toggle & Review

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/app/(dashboard)/campaigns/new/page.tsx`
- Modify: `frontend/app/(dashboard)/campaigns/new/step-schedule.tsx`
- Modify: `frontend/app/(dashboard)/campaigns/new/step-review.tsx`

**Interfaces:**
- Consumes: User toggles Voicemail Detection in Step 3 (Schedule & Policy).
- Produces: `detect_voicemail: boolean` sent in `api.campaigns.create` payload and displayed in Step 5 (Review).

- [ ] **Step 1: Update TypeScript interfaces in `frontend/lib/api.ts`**
- In `Campaign`: add `detect_voicemail?: boolean`.
- In `CampaignCreatePayload`: add `detect_voicemail?: boolean`.

- [ ] **Step 2: Add `detect_voicemail` to wizard form state in `page.tsx`**
- Initialize `detect_voicemail: true` in `form` state.
- Include `detect_voicemail: form.detect_voicemail` in `api.campaigns.create` payload.

- [ ] **Step 3: Add Voicemail & Screening Detection card in `step-schedule.tsx`**
- Add card with an intuitive toggle switch (or styled checkbox) and Shield/Voicemail icon:
  - Title: **"Voicemail & Siri/Screening Detection (AMD)"**
  - Subtitle: **"Automatically detect iPhone Live Voicemail, Google Call Screen, and carrier answering machines to hang up instantly and protect your credits."**
  - Badge: **"Recommended (Saves Credits)"**
  - Toggle states: `Enabled` (Hang up on voicemail & retry later) vs `Disabled` (Let agent leave full pitch on machines).

- [ ] **Step 4: Update `step-review.tsx`**
- Under Campaign Configuration review, display:
  - **Voicemail Detection:** `Enabled (Auto-hangup to save credits)` with a green badge, or `Disabled` with a neutral badge.

- [ ] **Step 5: Verify frontend builds without type errors**
Run `npm run build` or `npm run type-check` in `frontend/` to confirm zero compilation or TypeScript errors.

---

### Task 5: End-to-End Verification and Deployment

**Files:**
- Run all test suites: `pytest backend/tests/test_voicemail_*.py`
- Run regression tests: `pytest backend/tests/test_call_status_lifecycle.py backend/tests/test_call_credit_release_bug.py`
- Deploy to server via `redeploy.ps1 -SkipGit` (or full deploy) and verify health check.

- [ ] **Step 1: Run full automated backend test suite**
- [ ] **Step 2: Build frontend and verify no errors**
- [ ] **Step 3: Deploy to production Oracle server & verify live backend health**
- [ ] **Step 4: Confirm wizard live at `https://nivcall.vercel.app/campaigns/new`**
