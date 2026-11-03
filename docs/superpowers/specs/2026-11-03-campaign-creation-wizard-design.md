# Design: Multi-Step Campaign Creation Wizard & Enhanced Contact Filtering

## 1. Intent and Context
Currently in the platform:
1. **Monolithic Campaign Creation Page**:
   - [`frontend/app/(dashboard)/campaigns/new/page.tsx`](file:///c:/Programs/saas/frontend/app/(dashboard)/campaigns/new/page.tsx) is a single 600+ line form that packs campaign basics, agent selection, qualification schema editing, and calling schedule into one long scrolling screen.
2. **Contact Selection is Disconnected**:
   - Creating a campaign currently does not include contact or audience selection at all. Users must first create an empty draft campaign, wait to be redirected to the campaign details page, and then locate separate buttons to add leads.
3. **Limited Lead Filtering**:
   - Contact filtering is restricted to only basic status (`new`, `contacted`, etc.).
   - Users cannot filter existing contacts by **city**, **tags**, or perform freeform search across names and phone numbers.
   - There is no way to upload new contacts directly within the campaign creation workflow without losing entered campaign form state.

This feature introduces:
- A **5-Stage Step-by-Step Wizard** with intuitive progress tracking, back/next navigation, and quick defaults.
- **"Use Agent Defaults" / "Skip with Defaults"** action on the AI Agent & Qualification step for frictionless setup.
- An **Integrated Audience & Contact Selection Step** with rich filters (City, Tags, Status, Search), bulk selection, live counter badge, and an **Inline Contact Upload Modal** (CSV/XLSX) to add new contacts on the fly.
- A **Comprehensive Review & Launch Step** offering both *"Save as Draft"* and *"Create & Start Campaign"*.
- **Backend API & Repository Enhancements** for lead filtering (city, tags, search) and distinct filter metadata options.

---

## 2. Goals & Non-Goals

### Goals
1. **Interactive Multi-Step Wizard**:
   - Stage 1: Campaign Basics (Name, description, caller phone number).
   - Stage 2: AI Agent & Qualification (Voice agent selection, dynamic qualification criteria preview & editor, with a prominent *"Use Agent Defaults"* button).
   - Stage 3: Calling Schedule & Limits (Timezone, active days of week pills with presets, start/end time, concurrency limit, retry policy).
   - Stage 4: Contact Selection & Inline Import (Search, City filter, Tag filter, Status filter, select-all matching checkbox, live selected count pill, and inline file upload).
   - Stage 5: Review & Launch (Clean summary breakdown, validation checks, with "Save as Draft" and "Create & Start Now" actions).
2. **Modular Frontend Architecture**:
   - Decompose `campaigns/new/page.tsx` into modular step components (`step-basics.tsx`, `step-agent.tsx`, `step-schedule.tsx`, `step-contacts.tsx`, `step-review.tsx`, and `inline-lead-upload-modal.tsx`).
3. **Backend Lead Filtering & Enrollment Support**:
   - Expand `LeadRepository.list_for_org` and `count_for_org` to support `city`, `tags` (array `$in` match), and regex `search` (name, phone, email).
   - Add `GET /api/v1/leads/filters` to return distinct cities and tags available to the organization.
   - Update `POST /api/v1/campaigns/{id}/leads` to support enrolling by `city`, `status`, or specific `lead_ids`.

### Non-Goals
- Modifying campaign runtime execution loops (`campaign_service.py` / `outbound_worker.py`), which already dial enrolled leads correctly.
- Replacing the global `/leads` page (this design enhances its underlying API and reuses the patterns for campaign creation).

---

## 3. Architecture & API Specifications

### 3.1 Backend API Extensions

#### 3.1.1 `GET /api/v1/leads`
Query parameters:
- `search: Optional[str] = None` (case-insensitive substring match on `name`, `phone`, `email`)
- `city: Optional[str] = None` (case-insensitive match on `custom_fields.city` or `custom_fields.Town`)
- `tag: Optional[str] = None` or `tags: Optional[str] = None` (comma-separated tags to match)
- `status: Optional[str] = None`
- `campaign_id: Optional[str] = None`
- `limit: int = 100`, `skip: int = 0`

Response:
```json
{
  "total": 124,
  "limit": 100,
  "skip": 0,
  "leads": [...]
}
```

#### 3.1.2 `GET /api/v1/leads/filters`
Returns distinct filter values for the organization to populate dropdowns:
```json
{
  "cities": ["Mumbai", "Pune", "Delhi", "Bangalore"],
  "tags": ["vip", "q4_outreach", "real_estate", "inbound_web"]
}
```

#### 3.1.3 `POST /api/v1/campaigns/{campaign_id}/leads`
Accepts `EnrollCampaignLeadsRequest`:
```python
class EnrollCampaignLeadsRequest(BaseModel):
    lead_ids: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    city: Optional[str] = None
    status: Optional[str] = None
    all_contacts: bool = False
```

---

## 4. Frontend Wizard Structure & Components

### 4.1 Stepper Navigation
A top horizontal stepper displaying:
1. Basics
2. AI Agent
3. Schedule
4. Contacts
5. Review

Each step shows a numerical badge (or checkmark if completed) and title. Users can click any previously visited step to jump back.

### 4.2 Step Breakdown
1. **Step 1: Campaign Basics**
   - Inputs: Campaign Name (required), Description (optional), Caller Phone Number (required).
   - Validation: Name and Caller Number must be chosen before proceeding.
2. **Step 2: AI Voice Agent & Qualification**
   - Agent dropdown with language and voice profile info.
   - Dynamic qualification slots fetched from agent's qualification schema.
   - **"Use Agent Defaults" / "Skip with Defaults" button**: populates criteria with the agent's recommended slots and proceeds immediately to Step 3.
   - Add custom criteria slot modal/form.
3. **Step 3: Schedule & Limits**
   - Timezone selector.
   - Days of the week pills (Mon–Sun) with quick presets (*"Weekdays (Mon-Fri)"*, *"All Days (Mon-Sun)"*).
   - Calling window: Start time (e.g. 09:00) and End time (e.g. 18:00).
   - Concurrency limit (default 3).
   - Retry policy: Max attempts (default 3), Retry delay minutes (default 60).
4. **Step 4: Contact Selection & Inline Import**
   - Search bar: text search for name, phone, email.
   - Dropdown filters: City, Tags, Status.
   - Bulk action: "Select All Filtered Contacts" checkbox vs individual row checkboxes.
   - Selected Counter Badge: e.g. "Selected 120 / 540 contacts".
   - "Upload New Contacts" button: Opens inline modal (`inline-lead-upload-modal.tsx`) to upload CSV/XLSX. Upon successful upload, newly added leads are immediately pre-selected.
5. **Step 5: Review & Launch**
   - Review cards summarizing:
     - Basics & Outbound Phone Number.
     - Agent & Qualification Criteria count.
     - Calling Hours & Concurrency settings.
     - Audience count (e.g. 120 contacts ready to enroll).
   - Two execution actions:
     - **"Save as Draft"**: Creates campaign, enrolls selected contacts, redirects to `/campaigns/${id}`.
     - **"Create & Start Campaign"**: Creates campaign, enrolls contacts, calls `api.campaigns.start(id)`, redirects to `/campaigns/${id}` with live dialing active.
