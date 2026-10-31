# Multi-Campaign Leads, Custom Column Variable Mapping & Dynamic Prompt Interpolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the same contacts to participate in multiple independent outbound campaigns with separate call statuses, provide an interactive file upload column mapper for standard fields and AI variables, and dynamically interpolate contact/custom variables into AI agent greetings and system prompts during live calls.

**Architecture:** 
- Decouple contact records (`leads` collection) from campaign enrollments (`campaign_leads` junction collection).
- Update the lead import pipeline to support custom column mapping, contact upserting without duplicate phone errors, and campaign enrollment.
- Inject contact attributes and campaign-scoped custom variables hierarchically into `CallSession.variables` during call startup.
- Update the dialing worker, preflight validation, and call finalization to execute against `campaign_leads` with smart retry handling and defense-in-depth DNC enforcement.
- Provide a preview & column-mapping wizard in the frontend import flow and an enrolled leads view with contact management in the campaign detail page.

**Tech Stack:** Python 3.14, FastAPI, Motor/MongoDB, Redis, Pydantic v2, Next.js 14, React, Tailwind CSS, TypeScript.

**Spec:** `docs/superpowers/specs/2026-10-31-multi-campaign-leads-and-variable-mapping-design.md`

## Global Constraints
- Target python files must maintain compatibility with Python 3.14 and existing async patterns (`MotorDatabase`, `AsyncIOMotorDatabase`).
- Phone numbers must always be normalized to E.164 format.
- Backward compatibility: existing campaigns must be automatically backfilled into `campaign_leads` at startup without data loss.
- All file links in documentation and messages must follow the `file://` scheme with forward slashes.
- Existing docstrings and comments unrelated to code changes must be preserved.

## Review Focus
1. **Empty / unmapped phone column during import**: Upload missing a valid phone mapping or row without phone must be rejected gracefully with row-level error reporting.
2. **Header normalization & alias preservation**: File column headers with spaces/capitalization (e.g. `"Customer Name"`, `"Current City"`) must normalize to valid Python identifiers (`customer_name`, `current_city`) while preserving the exact header text as an alias.
3. **Multi-campaign isolation**: Enrolling a contact into Campaign B while they are `contacted` or `failed` in Campaign A must leave Campaign A unchanged and set Campaign B status to `new`.
4. **Retry scheduling without premature campaign completion**: A campaign with pending retries (`status == "callback"` and `next_attempt_at > now`) must remain `running` and not auto-complete until all retry attempts are exhausted.
5. **DNC propagation across active enrollments**: Adding a contact to the organization DNC list must mark all their enrollments across every campaign as `dnc` and immediately prevent any pending dials.

---

### Task 1: CampaignLead Model & CampaignLeadRepository

**Files:**
- Create: `backend/models/campaign_lead.py`
- Create: `backend/repositories/campaign_lead_repo.py`
- Test: `backend/tests/test_campaign_lead_repo.py`

**Interfaces:**
- Produces:
  - `CampaignLead`: Pydantic model with fields `organization_id: str`, `campaign_id: str`, `lead_id: str`, `phone: str`, `status: str = "new"`, `attempts: int = 0`, `max_attempts: int = 3`, `last_called_at: Optional[datetime] = None`, `next_attempt_at: Optional[datetime] = None`, `call_id: Optional[str] = None`, `disposition: Optional[str] = None`, `notes: Optional[str] = None`, `custom_fields: dict[str, Any] = Field(default_factory=dict)`.
  - `CampaignLeadRepository`:
    - `enroll_lead(campaign_id: str, lead_id: str, organization_id: str, phone: str, custom_fields: Optional[dict] = None) -> CampaignLead`
    - `bulk_enroll(campaign_id: str, organization_id: str, items: list[dict]) -> dict`
    - `find_by_campaign_lead(campaign_id: str, lead_id: str) -> Optional[CampaignLead]`
    - `list_for_campaign(campaign_id: str, organization_id: str, status: Optional[str] = None, limit: int = 50, skip: int = 0) -> tuple[list[dict], int]`
    - `pick_next_eligible(campaign_id: str) -> Optional[dict]`
    - `update_status(campaign_id: str, lead_id: str, status: str, extra_updates: Optional[dict] = None) -> bool`
    - `mark_dnc_for_phone(organization_id: str, phone: str) -> int`

- [ ] **Step 1: Write the failing tests in `backend/tests/test_campaign_lead_repo.py`**

```python
import pytest
from backend.models.campaign_lead import CampaignLead
from backend.repositories.campaign_lead_repo import CampaignLeadRepository

@pytest.mark.anyio
async def test_enroll_and_find_campaign_lead(db):
    repo = CampaignLeadRepository(db)
    lead = await repo.enroll_lead(
        campaign_id="camp_1",
        lead_id="lead_1",
        organization_id="org_1",
        phone="+919876543210",
        custom_fields={"city": "Mumbai", "loan_amount": "50000"}
    )
    assert lead.campaign_id == "camp_1"
    assert lead.status == "new"
    assert lead.custom_fields["city"] == "Mumbai"

    found = await repo.find_by_campaign_lead("camp_1", "lead_1")
    assert found is not None
    assert found.phone == "+919876543210"

@pytest.mark.anyio
async def test_multi_campaign_enrollment_isolation(db):
    repo = CampaignLeadRepository(db)
    # Enroll same lead into camp_1 and camp_2
    await repo.enroll_lead("camp_1", "lead_1", "org_1", "+919876543210")
    await repo.enroll_lead("camp_2", "lead_1", "org_1", "+919876543210")

    # Update camp_1 to contacted
    await repo.update_status("camp_1", "lead_1", "contacted")
    
    lead_1 = await repo.find_by_campaign_lead("camp_1", "lead_1")
    lead_2 = await repo.find_by_campaign_lead("camp_2", "lead_1")
    assert lead_1.status == "contacted"
    assert lead_2.status == "new"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_campaign_lead_repo.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'backend.models.campaign_lead')

- [ ] **Step 3: Implement `CampaignLead` model in `backend/models/campaign_lead.py` and `CampaignLeadRepository` in `backend/repositories/campaign_lead_repo.py`**
- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_campaign_lead_repo.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/models/campaign_lead.py backend/repositories/campaign_lead_repo.py backend/tests/test_campaign_lead_repo.py
git commit -m "feat: add CampaignLead model and repository"
```

---

### Task 2: Lead Import with Custom Column Mapping & Contact Upsert

**Files:**
- Modify: `backend/services/lead_service.py:100-390`
- Modify: `backend/api/v1/leads.py`
- Test: `backend/tests/test_lead_import_mapping.py`

**Interfaces:**
- Consumes: `CampaignLeadRepository` from Task 1
- Modifies: `LeadService.import_leads` to:
  - Parse `column_mapping` where keys map to standard fields (`phone`, `name`, `email`) or arbitrary AI prompt variables (e.g. `user_name`, `city`, `address`, `loan_amount`).
  - Auto-normalize variable names to lowercase snake_case while keeping raw key aliases.
  - If a contact phone number already exists in `organization_id`, update contact's `custom_fields`, merge tags, and update name if previously blank (upsert instead of duplicate failure).
  - If `campaign_id` is supplied, enroll the contact into `campaign_leads` for that campaign with campaign-scoped `custom_fields`.

- [ ] **Step 1: Write the failing tests in `backend/tests/test_lead_import_mapping.py`**

```python
import pytest
from backend.services.lead_service import LeadService, _apply_mapping

def test_apply_mapping_custom_variables():
    headers = ["Mobile Number", "Customer Name", "Residence City", "Balance Due"]
    rows = [["+919876543210", "Aarav Sharma", "Delhi", "15000"]]
    mapping = {
        "Mobile Number": "phone",
        "Customer Name": "user_name",
        "Residence City": "city",
        "Balance Due": "due_amount",
    }
    mapped = _apply_mapping(headers, rows, mapping)
    assert len(mapped) == 1
    assert mapped[0]["phone"] == "+919876543210"
    assert mapped[0]["name"] == "Aarav Sharma"
    assert mapped[0]["_custom"]["city"] == "Delhi"
    assert mapped[0]["_custom"]["due_amount"] == "15000"
    assert mapped[0]["_custom"]["user_name"] == "Aarav Sharma"

@pytest.mark.anyio
async def test_import_leads_upsert_and_campaign_enrollment(db):
    service = LeadService(db)
    csv_content = b"phone,name,city\n+919876543210,Aarav,Delhi\n"
    res1 = await service.import_leads(
        organization_id="org_test",
        content=csv_content,
        file_format="csv",
        campaign_id="camp_A",
        column_mapping={"phone": "phone", "name": "name", "city": "city"}
    )
    assert res1["imported"] == 1
    
    # Re-import same phone for camp_B with updated custom field
    csv_content_b = b"phone,name,city,offer\n+919876543210,Aarav Sharma,Mumbai,DISCOUNT50\n"
    res2 = await service.import_leads(
        organization_id="org_test",
        content=csv_content_b,
        file_format="csv",
        campaign_id="camp_B",
        column_mapping={"phone": "phone", "name": "name", "city": "city", "offer": "offer"}
    )
    assert res2["skipped_duplicate"] == 0
    assert res2["imported"] == 1

    # Check both campaigns have the lead
    camp_lead_a = await db["campaign_leads"].find_one({"campaign_id": "camp_A"})
    camp_lead_b = await db["campaign_leads"].find_one({"campaign_id": "camp_B"})
    assert camp_lead_a is not None
    assert camp_lead_b is not None
    assert camp_lead_b["custom_fields"]["offer"] == "DISCOUNT50"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_lead_import_mapping.py -v`
Expected: FAIL

- [ ] **Step 3: Update `backend/services/lead_service.py` to handle custom variable mapping, contact upsert, and `campaign_leads` enrollment**
- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_lead_import_mapping.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/lead_service.py backend/api/v1/leads.py backend/tests/test_lead_import_mapping.py
git commit -m "feat: support custom column mapping, contact upsert and campaign enrollment"
```

---

### Task 3: Dynamic Variable Injection in Telephony & CallSession

**Files:**
- Modify: `backend/telephony/vobiz.py:380-465`
- Modify: `backend/telephony/plivo.py:380-460`
- Modify: `backend/telephony/twilio.py:140-220`
- Modify: `backend/services/call_service.py:110-170`
- Test: `backend/tests/test_call_session_variable_injection.py`

**Interfaces:**
- Consumes: `CallSession`, `Lead`, `CampaignLead`
- Injects: Combined `runtime_variables` into `CallSession(variables=runtime_variables)`:
  - Agent defaults $\rightarrow$ Master Contact fields (`name`, `user_name`, `phone`, `custom_fields`) $\rightarrow$ Campaign-scoped overrides (`CampaignLead.custom_fields`).

- [ ] **Step 1: Write the failing tests in `backend/tests/test_call_session_variable_injection.py`**

```python
import pytest
from backend.call_session import CallSession
from backend.telephony.vobiz import resolve_call_variables

@pytest.mark.anyio
async def test_resolve_call_variables_hierarchy(db):
    # Setup agent config, master lead, and campaign lead
    await db.agents.insert_one({"_id": "ag_1", "organization_id": "org_1"})
    await db.agent_versions.insert_one({
        "_id": "ver_1",
        "agent_id": "ag_1",
        "configuration": {
            "system_prompt": "Hello {user_name}, your balance is {balance} in {city}.",
            "greeting": "Hi {user_name} from {city}!",
            "input_variables": {"balance": "0", "city": "Unknown"}
        }
    })
    await db.leads.insert_one({
        "_id": "lead_1",
        "organization_id": "org_1",
        "name": "Priya Patel",
        "phone": "+919876543210",
        "custom_fields": {"city": "Ahmedabad"}
    })
    await db.campaign_leads.insert_one({
        "campaign_id": "camp_1",
        "lead_id": "lead_1",
        "custom_fields": {"balance": "12500"}
    })
    await db.calls.insert_one({
        "_id": "call_1",
        "lead_id": "lead_1",
        "campaign_id": "camp_1",
        "agent_id": "ag_1"
    })

    vars = await resolve_call_variables(db, "call_1", "ag_1")
    assert vars["user_name"] == "Priya Patel"
    assert vars["name"] == "Priya Patel"
    assert vars["city"] == "Ahmedabad"
    assert vars["balance"] == "12500"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_call_session_variable_injection.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `resolve_call_variables` helper and integrate into `vobiz.py`, `plivo.py`, `twilio.py`**
- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_call_session_variable_injection.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/telephony/ backend/services/call_service.py backend/tests/test_call_session_variable_injection.py
git commit -m "feat: inject dynamic lead and campaign variables into call runtime"
```

---

### Task 4: Dialing Worker, Retry Lifecycle & Completion Engine

**Files:**
- Modify: `backend/workers/campaign_worker.py:90-180`
- Modify: `backend/services/call_service.py:320-420` (`finalize_call`)
- Modify: `backend/services/preflight_service.py:320-350`
- Modify: `backend/services/campaign_service.py:160-205`
- Test: `backend/tests/test_campaign_multi_lead_worker.py`

**Interfaces:**
- Modifies `campaign_worker.py`:
  - Query `campaign_leads` for eligible leads (`status in ["new", "callback"]` with `next_attempt_at <= now`).
  - Just-in-time DNC check against `dnc_repo.is_dnc`: mark `dnc` and skip if blacklisted.
  - Smart completion check: if no lead is currently eligible, check if any leads have `next_attempt_at > now`. If pending retries exist, stay `running`; only complete when all retries and calls are finished.
- Modifies `finalize_call`:
  - Update `campaign_leads` status (`contacted` on success; on retryable failure, increment attempts and set `next_attempt_at = now + retry_delay_minutes` with status `callback` until `max_attempts` reached).
- Adds automatic one-time migration helper `ensure_campaign_leads_backfilled(db)` on service startup.

- [ ] **Step 1: Write the failing tests in `backend/tests/test_campaign_multi_lead_worker.py`**

```python
import pytest
from datetime import timedelta
from backend.models.base import utcnow
from backend.workers.campaign_worker import CampaignWorker
from backend.services.call_service import CallService

@pytest.mark.anyio
async def test_worker_respects_pending_retry_without_completing(db, redis_client):
    # Setup campaign with retry policy
    camp_id = "camp_retry_test"
    org_id = "org_1"
    await db.campaigns.insert_one({
        "_id": camp_id,
        "organization_id": org_id,
        "status": "running",
        "calling_number": "+911234567890",
        "agent_id": "ag_1",
        "retry_policy": {"max_attempts": 2, "retry_delay_minutes": 30, "retry_on": ["busy"]}
    })
    # Lead has retry scheduled in 30 minutes
    await db.campaign_leads.insert_one({
        "campaign_id": camp_id,
        "organization_id": org_id,
        "lead_id": "lead_1",
        "phone": "+919876543210",
        "status": "callback",
        "attempts": 1,
        "max_attempts": 2,
        "next_attempt_at": utcnow() + timedelta(minutes=30)
    })

    worker = CampaignWorker(db, redis=redis_client)
    camp_doc = await db.campaigns.find_one({"_id": camp_id})
    from backend.models.campaign import Campaign
    campaign = Campaign.model_validate(camp_doc)

    await worker._process_campaign(campaign)
    # Campaign must STILL be running because lead is waiting for retry!
    updated = await db.campaigns.find_one({"_id": camp_id})
    assert updated["status"] == "running"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_campaign_multi_lead_worker.py -v`
Expected: FAIL

- [ ] **Step 3: Update `campaign_worker.py`, `call_service.py`, `preflight_service.py`, and `campaign_service.py` to use `campaign_leads` and handle retries**
- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_campaign_multi_lead_worker.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/workers/campaign_worker.py backend/services/call_service.py backend/services/campaign_service.py backend/services/preflight_service.py backend/tests/test_campaign_multi_lead_worker.py
git commit -m "feat: dial from campaign_leads with retry lifecycle and completion verification"
```

---

### Task 5: Campaign Leads API Endpoints

**Files:**
- Modify: `backend/api/v1/campaigns.py:200-288`
- Test: `backend/tests/test_campaign_leads_api.py`

**Interfaces:**
- Produces:
  - `GET /api/v1/campaigns/{campaign_id}/leads`: Returns `{"items": [...], "total": int}`
  - `POST /api/v1/campaigns/{campaign_id}/leads`: Body `{ "lead_ids": list[str], "tags": list[str], "all_contacts": bool }`
  - `DELETE /api/v1/campaigns/{campaign_id}/leads/{lead_id}`: Removes lead if status is `new` or `callback`.

- [ ] **Step 1: Write the failing tests in `backend/tests/test_campaign_leads_api.py`**

```python
import pytest
from httpx import AsyncClient

@pytest.mark.anyio
async def test_campaign_leads_endpoints(client: AsyncClient, auth_headers, test_campaign, test_lead):
    camp_id = test_campaign["id"]
    lead_id = test_lead["id"]

    # 1. Enroll lead into campaign
    res = await client.post(
        f"/api/v1/campaigns/{camp_id}/leads",
        json={"lead_ids": [lead_id]},
        headers=auth_headers
    )
    assert res.status_code == 200
    assert res.json()["enrolled"] == 1

    # 2. List enrolled leads
    list_res = await client.get(
        f"/api/v1/campaigns/{camp_id}/leads",
        headers=auth_headers
    )
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] == 1
    assert data["items"][0]["lead_id"] == lead_id
    assert data["items"][0]["phone"] == test_lead["phone"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_campaign_leads_api.py -v`
Expected: FAIL

- [ ] **Step 3: Implement endpoints in `backend/api/v1/campaigns.py`**
- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_campaign_leads_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/api/v1/campaigns.py backend/tests/test_campaign_leads_api.py
git commit -m "feat: add campaign leads management REST endpoints"
```

---

### Task 6: Frontend Interactive Column Mapper & Campaign Leads UI

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/app/(dashboard)/leads/import/page.tsx`
- Modify: `frontend/app/(dashboard)/campaigns/[id]/page.tsx`

**Interfaces:**
- `api.campaigns.leads(campaignId, params)`
- `api.campaigns.enrollLeads(campaignId, body)`
- `api.campaigns.removeLead(campaignId, leadId)`
- UI Features:
  - Interactive CSV/XLSX/JSON header preview & mapping table with target field select (`phone`, `name`/`user_name`, `email`, `city`, `address`, custom `{variable}`).
  - Target campaign picker in import flow.
  - Enrolled Leads Table with status badges and "Add from Contacts" modal in `/campaigns/[id]`.

- [ ] **Step 1: Add Campaign Leads methods to `frontend/lib/api.ts`**
- [ ] **Step 2: Implement interactive column mapping wizard in `frontend/app/(dashboard)/leads/import/page.tsx`**
- [ ] **Step 3: Add Enrolled Leads section and "Add Leads" modal to `frontend/app/(dashboard)/campaigns/[id]/page.tsx`**
- [ ] **Step 4: Run frontend build verification**

Run: `cd frontend && npm run build`
Expected: Successful compilation with 0 TypeScript/ESLint errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add interactive column mapper and campaign leads management UI"
```

---

### Task 7: Full Test Suite, Deployment & Knowledge Graph Update

**Files:**
- Modify: none (verification task)

- [ ] **Step 1: Run full backend test suite**

Run: `pytest backend/tests/ -v`
Expected: All tests pass.

- [ ] **Step 2: Update knowledge graph**

Run: `graphify update .`

- [ ] **Step 3: Synchronize git repository and deploy to VPS `92.5.149.29`**

Sync with git, rebuild docker containers (`docker compose -f docker-compose.prod.yml up -d --build api worker frontend`), verify live status.
