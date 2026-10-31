# Campaign Calling Hours UI & Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable users to configure campaign calling hours and days directly in the UI during campaign creation, on the campaign detail page via an edit modal, and with actionable resolution options when a calling-hours pre-flight check fails.

**Architecture:** Extend FastAPI backend models and serializer to support day-name/integer normalization and expose calling hours in the campaign API response. In Next.js frontend, fix the campaign creation day-picker to send numeric day indices, add a Schedule & Calling Hours card with an edit modal to the campaign detail page, and handle pre-flight calling hour failures with an interactive recovery dialog.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, Motor (MongoDB), TypeScript, Next.js 14 (App Router), Tailwind CSS.

**Spec:** Inferred from system model `0=Sunday, 1=Monday, ..., 6=Saturday`, `CallingHours` timestamped model, and user request to configure calling hours in the UI.

## Global Constraints

- Day index convention: `0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday`.
- Backward-compatible: `CallingHours.days_of_week` must accept both numeric indices (`[1, 2, 3, 4, 5]`) and string names (`["Monday", "Saturday"]`).
- Only campaigns in `draft` status can have their configuration updated via `PATCH /api/v1/campaigns/{id}`.
- Pre-flight bypass flag `skip_preflight=true` is supported by `POST /api/v1/campaigns/{id}/start?skip_preflight=true`.

## Review Focus

1. User selects Saturday and Sunday in UI: verify days serialize as `[0, 6]` or `[1, 2, 3, 4, 5, 6, 0]` and pass validation.
2. Existing campaign in draft mode has `calling_hours` null or missing in older records: UI must gracefully fall back to default `09:00 - 18:00` and `[1, 2, 3, 4, 5]`.
3. Preflight fails with calling hours on Saturday: UI displays clear recovery modal offering both "Edit Calling Hours" and "Start Anyway (Bypass Calling Hours)".
4. Updating calling hours via `PATCH /api/v1/campaigns/{id}`: backend must validate input using `CallingHours` before persisting to database.
5. All days empty: backend validator rejects empty `days_of_week` with clear validation error.

---

### Task 1: Backend CallingHours Validation & Serializer

**Files:**
- Modify: `backend/models/campaign.py:38-46`
- Modify: `backend/api/v1/campaigns.py:75-101, 160-178`
- Create: `backend/tests/test_campaign_calling_hours.py`

**Interfaces:**
- Consumes: `CallingHours` model, `Campaign` model, `_campaign_response` helper.
- Produces: Normalized `days_of_week: list[int]` supporting string names and int indices, `calling_hours` included in `_campaign_response`.

- [ ] **Step 1: Write the failing backend test**

Create `backend/tests/test_campaign_calling_hours.py`:
```python
import pytest
from backend.models.campaign import CallingHours
from pydantic import ValidationError

def test_calling_hours_accepts_integers():
    ch = CallingHours(days_of_week=[1, 2, 3, 4, 5, 6])
    assert ch.days_of_week == [1, 2, 3, 4, 5, 6]

def test_calling_hours_accepts_day_strings():
    ch = CallingHours(days_of_week=["Monday", "Saturday", "friday"])
    assert ch.days_of_week == [1, 5, 6]

def test_calling_hours_rejects_invalid_day():
    with pytest.raises(ValidationError):
        CallingHours(days_of_week=["Funday"])

def test_calling_hours_rejects_empty_days():
    with pytest.raises(ValidationError):
        CallingHours(days_of_week=[])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_campaign_calling_hours.py`
Expected: FAIL with `ValidationError` for string inputs.

- [ ] **Step 3: Implement CallingHours validator in `backend/models/campaign.py` and update `_campaign_response` in `backend/api/v1/campaigns.py`**

In `backend/models/campaign.py`:
Add a validator on `days_of_week` mapping strings to integers (`sun`/`sunday`: 0, `mon`/`monday`: 1, etc.) and ensuring days are in range 0..6, sorted and deduplicated, and not empty.

In `backend/api/v1/campaigns.py`:
- In `_campaign_response`, add:
  ```python
  "calling_hours": c.calling_hours.model_dump() if hasattr(c.calling_hours, "model_dump") else c.calling_hours,
  "retry_policy": c.retry_policy.model_dump() if hasattr(c.retry_policy, "model_dump") else c.retry_policy,
  ```
- In `update_campaign`, validate `body.calling_hours` with `CallingHours(**body.calling_hours).model_dump()` if present.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_campaign_calling_hours.py`
Expected: PASS.

---

### Task 2: Frontend API Client Types & Campaign Creation Day Selector

**Files:**
- Modify: `frontend/lib/api.ts:319-344, 1002-1004`
- Modify: `frontend/app/(dashboard)/campaigns/new/page.tsx:20-28, 52-59, 116-120, 294-315`

**Interfaces:**
- Consumes: `CallingHours` schema from backend.
- Produces: `Campaign.calling_hours` in TypeScript definitions, numeric `days_of_week` array sent on campaign creation.

- [ ] **Step 1: Update TypeScript types in `frontend/lib/api.ts`**

Add `calling_hours` and `retry_policy` to `Campaign` interface:
```typescript
export interface CallingHoursConfig {
  start_time: string;
  end_time: string;
  days_of_week: number[];
}

export interface Campaign {
  // ... existing fields
  calling_hours?: CallingHoursConfig;
  retry_policy?: {
    max_attempts: number;
    retry_delay_minutes: number;
    retry_on?: string[];
  };
}
```
Update `api.campaigns.update` type to accept `calling_hours?: CallingHoursConfig; timezone?: string`.

- [ ] **Step 2: Update Campaign Creation Day Selector in `frontend/app/(dashboard)/campaigns/new/page.tsx`**

Replace string-based `DAYS_OF_WEEK` with structured day items:
```typescript
const DAY_OPTIONS = [
  { label: "Mon", full: "Monday", value: 1 },
  { label: "Tue", full: "Tuesday", value: 2 },
  { label: "Wed", full: "Wednesday", value: 3 },
  { label: "Thu", full: "Thursday", value: 4 },
  { label: "Fri", full: "Friday", value: 5 },
  { label: "Sat", full: "Saturday", value: 6 },
  { label: "Sun", full: "Sunday", value: 0 },
];
```
- Update `selectedDays` state to `number[]`, default to `[1, 2, 3, 4, 5]`.
- Add quick preset buttons: "Weekdays (Mon-Fri)", "All Days (Mon-Sun)".
- Submit `days_of_week: selectedDays` as `number[]`.

- [ ] **Step 3: Verify frontend type check on `new/page.tsx`**

Run: `npx tsc --noEmit` inside `frontend/`.
Expected: No type errors in `new/page.tsx`.

---

### Task 3: Campaign Detail Page Schedule View & Calling Hours Edit Modal

**Files:**
- Modify: `frontend/app/(dashboard)/campaigns/[id]/page.tsx`
- Create: `frontend/components/campaigns/calling-hours-modal.tsx`

**Interfaces:**
- Consumes: `campaign.calling_hours`, `campaign.timezone`, `api.campaigns.update`.
- Produces: Schedule & Calling Hours card on campaign detail page, interactive modal for updating schedule on draft campaigns.

- [ ] **Step 1: Create `CallingHoursModal` component**

Create `frontend/components/campaigns/calling-hours-modal.tsx`:
- Props: `isOpen`, `onClose`, `campaignId`, `initialCallingHours`, `initialTimezone`, `onUpdated`.
- Allows toggling each day (Mon–Sun), quick presets "Weekdays" and "All Days", Start Time, End Time, and Timezone.
- Calls `api.campaigns.update(campaignId, { timezone, calling_hours: { start_time, end_time, days_of_week } })`.
- Handles loading and error toasts.

- [ ] **Step 2: Add Schedule & Calling Hours section and Edit button in `campaigns/[id]/page.tsx`**

In `frontend/app/(dashboard)/campaigns/[id]/page.tsx`:
- Add a "Schedule & Calling Hours" Card in the detail grid.
- Display Timezone, Calling Window (`09:00 - 18:00`), and Day Badges showing which days are enabled.
- If campaign is `draft`, show an "Edit Schedule" button that opens `CallingHoursModal`.

- [ ] **Step 3: Verify frontend type check on `campaigns/[id]/page.tsx`**

Run: `npx tsc --noEmit` inside `frontend/`.
Expected: No type errors.

---

### Task 4: Pre-flight Error Recovery Dialog in UI

**Files:**
- Modify: `frontend/app/(dashboard)/campaigns/[id]/page.tsx`

**Interfaces:**
- Consumes: Start action catch block, `api.campaigns.start(id, skip_preflight)`.
- Produces: Actionable error banner/modal when pre-flight fails with calling hours or other checks.

- [ ] **Step 1: Implement pre-flight failure state and recovery dialog in `campaigns/[id]/page.tsx`**

When starting a campaign and receiving pre-flight error:
- Detect if the error relates to `calling_hours` (e.g. `Today (...) is not a calling day` or `outside calling window`).
- Open a dedicated recovery dialog:
  - Explains the exact calling hours issue.
  - Button 1: "Configure Calling Hours" -> opens `CallingHoursModal` immediately.
  - Button 2: "Start Anyway (Bypass Pre-flight)" -> triggers `api.campaigns.start(campaign.id, true)` with confirmation.

- [ ] **Step 2: Verify build and type check**

Run: `npx tsc --noEmit` in `frontend/`.
Expected: Build passes cleanly.

---

### Task 5: Verification & Testing

**Files:**
- Test files and graphify sync.

- [ ] **Step 1: Run all backend tests**

Run: `pytest backend/tests/test_campaign_calling_hours.py backend/tests/test_m14_preflight.py`
Verify calling hours validation and pre-flight tests pass.

- [ ] **Step 2: Run frontend build check**

Run: `npm run build` or `npx tsc --noEmit` in `frontend/`.
Verify zero compiler errors.

- [ ] **Step 3: Update knowledge graph**

Run: `graphify update .`
