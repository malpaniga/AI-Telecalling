# Campaign Creation Wizard & Enhanced Contact Filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the campaign creation workflow into a multi-step interactive wizard with agent qualification defaults, rich contact filtering (search, city, tags, status), inline contact upload, and one-click launch.

**Architecture:** Modularize the frontend campaign creation page into 5 step components coordinated by a central wizard state machine. Extend backend lead repositories and API endpoints to support multi-attribute filtering (city, tags, search) and distinct filter metadata for fast client-side dropdowns.

**Tech Stack:** Next.js 14 (React 18, Tailwind CSS, Lucide icons), FastAPI, MongoDB (Motor async driver), Pytest, TypeScript.

**Spec:** [`docs/superpowers/specs/2026-11-03-campaign-creation-wizard-design.md`](file:///c:/Programs/saas/docs/superpowers/specs/2026-11-03-campaign-creation-wizard-design.md)

## Global Constraints

- Preserve organization tenant isolation on all queries (`organization_id` required).
- Maintain backward compatibility with existing campaign and lead endpoints.
- Preserve all existing qualification schema and calling hours validation.
- All code edits must preserve existing comments and docstrings.
- Code modifications must trigger `graphify update .` to keep the codebase knowledge graph synchronized.

## Review Focus

1. Partial or empty search strings must return uncorrupted lead lists rather than raising regex errors.
2. Distinct filter options must filter by `organization_id` so one organization's tags or cities are never leaked to another.
3. "Use Agent Defaults" / "Skip with Defaults" must properly copy agent qualification schema even if the agent defines slots under either `qualification_schema` or `slot_definitions`.
4. Bulk-enrolling contacts into a newly created campaign must avoid duplicate enrollment and tolerate batch sizes up to 5,000 leads.
5. Inlining the file upload modal within the wizard must update the wizard's selected contacts state without resetting earlier step form inputs.

---

### Task 1: Backend Lead Filtering API & Repositories

**Files:**
- Modify: [`backend/repositories/lead_repo.py`](file:///c:/Programs/saas/backend/repositories/lead_repo.py)
- Modify: [`backend/services/lead_service.py`](file:///c:/Programs/saas/backend/services/lead_service.py)
- Modify: [`backend/api/v1/leads.py`](file:///c:/Programs/saas/backend/api/v1/leads.py)
- Test: `tests/test_lead_filters.py`

**Interfaces:**
- Consumes: `organization_id: str`, filter query parameters (`search`, `city`, `tag`, `tags`, `status`, `campaign_id`).
- Produces:
  - `LeadRepository.list_for_org(organization_id, campaign_id, status, city, tags, search, limit, skip)`
  - `LeadRepository.count_for_org(organization_id, campaign_id, status, city, tags, search)`
  - `LeadRepository.get_filter_options(organization_id) -> {"cities": list[str], "tags": list[str]}`
  - `GET /api/v1/leads?search=...&city=...&tag=...&status=...`
  - `GET /api/v1/leads/filters` -> `{"cities": [...], "tags": [...]}`

- [ ] **Step 1: Write the failing test**

Create `tests/test_lead_filters.py`:
```python
import pytest
from httpx import AsyncClient
from backend.main import app

@pytest.mark.asyncio
async def test_leads_filter_and_options(client: AsyncClient, auth_headers: dict):
    # Test GET /api/v1/leads/filters
    res = await client.get("/api/v1/leads/filters", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "cities" in data
    assert "tags" in data

    # Test filtering by city and search
    res = await client.get("/api/v1/leads?search=test&city=Mumbai", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert "leads" in body
    assert "total" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_lead_filters.py -v`
Expected: FAIL with 404 or missing filter route.

- [ ] **Step 3: Implement filter logic in repository, service, and API**

In `backend/repositories/lead_repo.py`:
- Update `list_for_org` and `count_for_org` to build MongoDB filters:
  - `city`: `{"$or": [{"custom_fields.city": {"$regex": f"^{city}$", "$options": "i"}}, {"custom_fields.Town": {"$regex": f"^{city}$", "$options": "i"}}]}`
  - `tags`: `{"tags": {"$in": tag_list}}`
  - `search`: `{"$or": [{"phone": {"$regex": search, "$options": "i"}}, {"name": {"$regex": search, "$options": "i"}}, {"email": {"$regex": search, "$options": "i"}}]}`
- Add `get_filter_options(organization_id)` returning distinct cities and tags.

In `backend/services/lead_service.py`:
- Pass filter params from `list_leads` to `lead_repo`.
- Add `get_filter_options(organization_id)`.

In `backend/api/v1/leads.py`:
- Add query parameters to `list_leads`: `search`, `city`, `tag`, `tags`.
- Add `@router.get("/filters")` endpoint returning `svc.get_filter_options(org_id)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_lead_filters.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/repositories/lead_repo.py backend/services/lead_service.py backend/api/v1/leads.py tests/test_lead_filters.py
git commit -m "feat(leads): add city, tags, search filters and filter options endpoint"
```

---

### Task 2: Backend Campaign Lead Enrollment Filters

**Files:**
- Modify: [`backend/api/v1/campaigns.py`](file:///c:/Programs/saas/backend/api/v1/campaigns.py)
- Test: `tests/test_campaign_enroll_filters.py`

**Interfaces:**
- Consumes: `EnrollCampaignLeadsRequest` with `city`, `status`, `tags`, `lead_ids`, `all_contacts`.
- Produces: `POST /api/v1/campaigns/{id}/leads` enrolling contacts matching given filter criteria.

- [ ] **Step 1: Write the failing test**

Create `tests/test_campaign_enroll_filters.py`:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_campaign_enroll_by_city(client: AsyncClient, auth_headers: dict):
    # Verify EnrollCampaignLeadsRequest accepts city and status
    from backend.api.v1.campaigns import EnrollCampaignLeadsRequest
    req = EnrollCampaignLeadsRequest(city="Mumbai", status="new")
    assert req.city == "Mumbai"
    assert req.status == "new"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_campaign_enroll_filters.py -v`
Expected: FAIL if fields don't exist in `EnrollCampaignLeadsRequest`.

- [ ] **Step 3: Implement `city` and `status` in `EnrollCampaignLeadsRequest` and `enroll_campaign_leads`**

In `backend/api/v1/campaigns.py`:
- Add `city: Optional[str] = None` and `status: Optional[str] = None` to `EnrollCampaignLeadsRequest`.
- Update `enroll_campaign_leads` query logic to apply `city` and `status` if present.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_campaign_enroll_filters.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/api/v1/campaigns.py tests/test_campaign_enroll_filters.py
git commit -m "feat(campaigns): expand lead enrollment request to support city and status filters"
```

---

### Task 3: Frontend API Client Extension

**Files:**
- Modify: [`frontend/lib/api.ts`](file:///c:/Programs/saas/frontend/lib/api.ts)

**Interfaces:**
- Consumes: Updated backend endpoints.
- Produces:
  - `api.leads.list(params?: { search?: string; city?: string; tag?: string; status?: string; limit?: number; skip?: number; campaign_id?: string })`
  - `api.leads.filters() -> Promise<{ cities: string[]; tags: string[] }>`
  - `api.campaigns.enrollLeads(id, body: { lead_ids?: string[]; tags?: string[]; city?: string; status?: string; all_contacts?: boolean })`

- [ ] **Step 1: Update TypeScript interfaces and client methods in `frontend/lib/api.ts`**

Update `api.leads.list` to accept `search`, `city`, `tag`.
Add `api.leads.filters: () => apiRequest<{ cities: string[]; tags: string[] }>("GET", "/api/v1/leads/filters")`.
Update `api.campaigns.enrollLeads` signature to support `city` and `status`.

- [ ] **Step 2: Verify type check passes**

Run: `npm --prefix frontend run lint` or `npx tsc --noEmit`
Expected: PASS without type errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat(frontend): extend API client with lead filters and enrollment parameters"
```

---

### Task 4: Campaign Wizard Step Components (Basics, Agent, Schedule)

**Files:**
- Create: `frontend/app/(dashboard)/campaigns/new/step-basics.tsx`
- Create: `frontend/app/(dashboard)/campaigns/new/step-agent.tsx`
- Create: `frontend/app/(dashboard)/campaigns/new/step-schedule.tsx`

**Interfaces:**
- Consumes: Form state and setters from parent wizard container.
- Produces:
  - `StepBasics`: Name, description, caller number selection.
  - `StepAgent`: Agent picker, qualification slot list, and **"Use Agent Defaults" / "Skip with Defaults"** button that populates default criteria and advances.
  - `StepSchedule`: Calling window hours, active days pills, timezone, concurrency, retry policy.

- [ ] **Step 1: Implement `step-basics.tsx`**
Includes Campaign Name, Description, and Phone Number selection cards with caller status indicator.

- [ ] **Step 2: Implement `step-agent.tsx`**
Includes voice agent selector, dynamic slot list, add/remove/toggle required slots, and a prominent "Use Agent Defaults" button that loads the schema and calls `onNext()`.

- [ ] **Step 3: Implement `step-schedule.tsx`**
Includes timezone dropdown, day toggle buttons with Weekdays / All Days presets, start/end time pickers, concurrency slider/input, and retry configuration.

- [ ] **Step 4: Verify type checking**

Run: `npx --prefix frontend tsc --noEmit`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/\(dashboard\)/campaigns/new/step-basics.tsx frontend/app/\(dashboard\)/campaigns/new/step-agent.tsx frontend/app/\(dashboard\)/campaigns/new/step-schedule.tsx
git commit -m "feat(campaigns): add modular wizard steps for basics, agent, and schedule"
```

---

### Task 5: Contact Selection Step with Live Filtering, Bulk Selection, and Inline Upload Modal

**Files:**
- Create: `frontend/app/(dashboard)/campaigns/new/inline-lead-upload-modal.tsx`
- Create: `frontend/app/(dashboard)/campaigns/new/step-contacts.tsx`

**Interfaces:**
- Consumes: `api.leads.list`, `api.leads.filters`, `api.leads.importFile`.
- Produces:
  - `InlineLeadUploadModal`: Drag-and-drop file upload for CSV/XLSX with column mapping preview. On success, passes new lead IDs back to parent.
  - `StepContacts`: Interactive filter bar (search, city, tags, status), select all / bulk select toggle, live count badge (*"X contacts selected"*), and contact preview table.

- [ ] **Step 1: Implement `inline-lead-upload-modal.tsx`**
Provides an inline modal with file selection, preview, column mapping (if needed), tag assignment, and upload. On completion, notifies parent and auto-selects newly uploaded leads.

- [ ] **Step 2: Implement `step-contacts.tsx`**
Provides filter controls, search bar, active tag pills, city dropdown, status dropdown, "Select All Filtered" toggle, table with row checkboxes, and an "Upload New Contacts" trigger button.

- [ ] **Step 3: Verify type checking**

Run: `npx --prefix frontend tsc --noEmit`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(dashboard\)/campaigns/new/inline-lead-upload-modal.tsx frontend/app/\(dashboard\)/campaigns/new/step-contacts.tsx
git commit -m "feat(campaigns): add contact selection step with rich filtering and inline file upload"
```

---

### Task 6: Review & Launch Step & Wizard Container Integration

**Files:**
- Create: `frontend/app/(dashboard)/campaigns/new/step-review.tsx`
- Modify: [`frontend/app/(dashboard)/campaigns/new/page.tsx`](file:///c:/Programs/saas/frontend/app/(dashboard)/campaigns/new/page.tsx)

**Interfaces:**
- Consumes: All step components and campaign API.
- Produces:
  - Top stepper navigation showing 5 numbered/checked steps.
  - Central form state management across steps.
  - `StepReview`: Summary card breakdown of basics, agent, schedule, and selected contact count.
  - Submission handler: Creates campaign, bulk-enrolls selected contacts, and either saves as draft or calls `api.campaigns.start(id)` immediately based on user action.

- [ ] **Step 1: Implement `step-review.tsx`**
Renders 4 clear summary cards (Basics, Agent, Schedule, Audience) and dual submission buttons: "Save as Draft" and "Create & Start Campaign".

- [ ] **Step 2: Rewrite `campaigns/new/page.tsx` as Wizard Controller**
Integrate the stepper header, step transition animation, step navigation state (`step 1..5`), validation guards, and API submit workflow.

- [ ] **Step 3: Verify type checking and build**

Run: `npm --prefix frontend run build`
Expected: PASS with 0 build errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(dashboard\)/campaigns/new/step-review.tsx frontend/app/\(dashboard\)/campaigns/new/page.tsx
git commit -m "feat(campaigns): assemble complete 5-step campaign creation wizard with draft and start actions"
```

---

### Task 7: End-to-end Integration Verification & Knowledge Graph Update

**Files:**
- Run: Full backend test suite (`pytest`)
- Run: Frontend build check (`npm run build`)
- Update: Knowledge graph (`graphify update .`)

- [ ] **Step 1: Run all project backend tests**

Run: `pytest tests/ -v`
Expected: PASS (all tests pass).

- [ ] **Step 2: Verify frontend production build**

Run: `npm --prefix frontend run build`
Expected: PASS with no compilation or ESLint errors.

- [ ] **Step 3: Update knowledge graph**

Run: `graphify update .`
Expected: Graph updated with new modules and API routes.

- [ ] **Step 4: Commit any remaining updates**

```bash
git commit --allow-empty -m "chore: verify campaign wizard integration and update knowledge graph"
```
