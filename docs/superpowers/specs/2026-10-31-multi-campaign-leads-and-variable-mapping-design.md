# Design: Multi-Campaign Leads, Custom Column Variable Mapping & Dynamic Prompt Interpolation

## 1. Intent and Context
Currently in the platform:
1. **Leads are constrained to a single campaign**:
   - A `Lead` record stores a single `campaign_id` and a single shared `status` (`new`, `calling`, `contacted`, etc.).
   - When an organization uploads a contact list, `LeadService.import_leads` rejects any existing phone number in the organization as a duplicate (`skipped_duplicate`).
   - If Campaign A dials a lead and marks them `contacted`, Campaign B cannot call that lead because Campaign B's query filters for `status: {"$in": ["new", "scheduled"]}`.
2. **Column mapping is rigid and unconfigurable**:
   - `LeadService._apply_mapping` only recognizes hardcoded standard fields (`phone`, `name`, `email`).
   - Non-standard columns (`city`, `address`, `account_balance`, etc.) are dumped into a generic `_custom` dictionary.
   - The frontend file upload modal does not provide an interactive column mapping interface or preview.
3. **Agent prompts do not receive lead data**:
   - Even though `CallSession` supports `{variable}` string template interpolation, neither `CallService` nor the telephony stream workers (`vobiz.py`, `plivo.py`, `twilio.py`) pass the lead's stored contact info or custom fields into `CallSession.variables`.
   - As a result, `{user_name}`, `{city}`, or `{address}` in greetings and system prompts are never interpolated during outbound campaign calls.

This design introduces:
- **Campaign Membership (`CampaignLead`)**: Decouples contacts from campaigns so an organization's leads can be enrolled in multiple independent campaigns, each with its own lifecycle status and call attempts.
- **Interactive Import Column & Variable Mapper**: A user-friendly CSV/XLSX/JSON mapping workflow in the UI where users can inspect sample rows and map any file column to standard contact fields or custom AI prompt variables (e.g. `Client Name` $\rightarrow$ `{user_name}`, `Town` $\rightarrow$ `{city}`).
- **Dynamic Prompt & Greeting Interpolation**: Complete runtime injection of lead details and custom variables into `CallSession` so the AI agent speaks and reasons with the lead's personalized data.

---

## 2. Goals & Non-Goals

### Goals
1. **Multi-Campaign Participation**:
   - Maintain contacts at the organization level (`leads` collection). A contact is unique by phone number per organization.
   - Support multiple campaigns calling the same contact at different times via a `campaign_leads` junction collection with independent statuses (`new`, `scheduled`, `calling`, `contacted`, `qualified`, `callback`, `not_interested`, `failed`, `dnc`).
   - Calling or completing a lead in Campaign A has zero adverse impact on Campaign B.
2. **Contact Upsert on Re-Import**:
   - When importing leads for Campaign B, existing phone numbers are not discarded as errors. Instead, their details are updated/merged into the contact record, and they are enrolled into Campaign B with `status = "new"`.
3. **Interactive Column Mapping UI**:
   - Let users upload CSV, XLSX, or JSON files, preview headers and sample data rows, and configure column-to-variable mappings before importing.
   - Support mapping to standard fields (`phone`, `name`, `email`) and arbitrary AI prompt variables (e.g. `user_name`, `city`, `address`, `company_name`, `balance`, etc.).
4. **Runtime AI Variable Interpolation**:
   - When any outbound campaign call or direct dial connects, look up the lead record and combine standard fields (`name`, `user_name`, `phone`, `email`) and all `custom_fields`.
   - Pass them into `CallSession.variables` so that `{user_name}`, `{city}`, `{address}`, etc. in `custom_greeting` and `system_prompt` are substituted dynamically.
5. **Campaign Lead Management in UI**:
   - In `/campaigns/[id]`, display the list of leads enrolled in that campaign, their status for that campaign, and an "Add Leads" action (by file upload or by selecting existing contacts / tags).

### Non-Goals
- Real-time modification of prompt variables *during* an active call (prompt variables are bound at call initiation).
- Full CRM workflow triggers (e.g. Zapier / webhook pipelines on every disposition change), which belongs to a future integration milestone.

---

## 3. Data Architecture & Schema Changes

### 3.1. Campaign Lead Junction Model (`CampaignLead`)
Create a new collection `campaign_leads` represented by `CampaignLead` in `backend/models/campaign_lead.py`:

```python
class CampaignLead(TimestampedModel):
    """Enrollment of a Lead in a specific Campaign."""
    organization_id: str
    campaign_id: str
    lead_id: str
    phone: str                          # Denormalized for worker performance
    status: str = "new"                 # new | scheduled | calling | contacted | qualified | callback | not_interested | failed | dnc
    attempts: int = 0
    max_attempts: int = 3
    last_called_at: Optional[datetime] = None
    next_attempt_at: Optional[datetime] = None
    call_id: Optional[str] = None
    disposition: Optional[str] = None
    notes: Optional[str] = None
    # Scoped variables specifically for this campaign execution
    custom_fields: dict[str, Any] = Field(default_factory=dict)
```

**Indexes**:
- Compound Unique: `{"campaign_id": 1, "lead_id": 1}` (enforces that a lead is enrolled at most once per campaign).
- Worker Index: `{"campaign_id": 1, "status": 1, "next_attempt_at": 1}` (for fast polling of eligible leads).
- Organization Index: `{"organization_id": 1, "campaign_id": 1}`.

### 3.2. Lead Model Updates (`backend/models/lead.py`)
- Keep `Lead` as the master contact record for the organization.
- `phone` is unique per `organization_id`.
- `custom_fields: dict[str, Any]` stores persistent contact-level variables (e.g. `{"city": "Mumbai", "company": "Acme Corp"}`).
- Retain `campaign_id: Optional[str]` on `Lead` for backward-compatibility with legacy single-campaign imports, but use `campaign_leads` as the primary multi-campaign source.

### 3.3. Variable Scoping & Hierarchy (Builder Decision)
Variables are resolved hierarchically when an outbound call connects:
1. **Agent Version Defaults**: Default input variables defined in agent configuration (`agent_versions.configuration.input_variables`).
2. **Master Contact Attributes & Custom Fields**: `name`, `phone`, `email`, and `Lead.custom_fields` (e.g. `city`, `address`).
3. **Campaign Enrollment Overrides**: `CampaignLead.custom_fields` (e.g., campaign-specific values like `due_date`, `offer_code`, `appointment_time`).

*Why*: Contact-level attributes (like City and Address) stay consistent across all campaigns, while campaign-specific data from a specific upload will never corrupt or overwrite other campaigns' values.

---

## 4. Import & Column Mapping Pipeline

### 4.1. Import Endpoint & Mapping Schema
Update `POST /api/v1/leads/import`:
- Accepts:
  - `file`: Uploaded CSV, XLSX, or JSON.
  - `column_mapping`: JSON string or dict mapping file headers to variable names, e.g.:
    ```json
    {
      "Customer Phone": "phone",
      "Full Name": "user_name",
      "Residence City": "city",
      "Property Type": "property_type",
      "Outstanding Dues": "due_amount"
    }
    ```
  - `campaign_id`: Optional target campaign ID to automatically enroll imported leads into.
  - `tags`: Optional list of tags.

### 4.2. Lead Service Processing (`backend/services/lead_service.py`)
1. **Parsing**: Parse uploaded file into headers and raw rows.
2. **Field Categorization**:
   - Reserved standard fields:
     - `phone`: Required. Normalized to E.164.
     - `name`: Contact name. If `user_name` or `customer_name` is mapped and `name` is omitted, set `name` to that value.
     - `email`: Optional email address.
   - Prompt / Custom variables: Any other mapped key is placed into `custom_fields[mapped_key] = row_value`.
     - Also auto-alias common variants: if mapped to `user_name`, store both `name = val` and `custom_fields["user_name"] = val`.
3. **Upsert Logic for Existing Contacts**:
   - Query existing phone numbers in `organization_id`.
   - For existing leads:
     - Merge new contact-level `custom_fields` into `Lead.custom_fields`.
     - Update `name` or `email` if previously blank.
     - Add any new tags.
   - For new leads:
     - Insert new `Lead` document with `status = "new"`.
4. **Campaign Enrollment**:
   - If `campaign_id` is provided:
     - Upsert into `campaign_leads` with `campaign_id`, `lead_id`, `organization_id`, `phone`, `custom_fields = row_custom_fields`, and `status = "new"`.
     - If the lead was already enrolled in this exact same campaign, preserve existing status unless explicitly requested.

---

## 5. Dialing Engine & Dynamic Variable Interpolation

### 5.1. Campaign Worker Execution & Retry Lifecycle (`backend/workers/campaign_worker.py`)
1. **Eligible Lead Selection**:
   Worker queries `campaign_leads`:
   ```python
   camp_lead = await self._db["campaign_leads"].find_one_and_update(
       {
           "campaign_id": campaign.id,
           "status": {"$in": ["new", "callback"]},
           "$or": [
               {"next_attempt_at": None},
               {"next_attempt_at": {"$lte": utcnow()}},
           ],
       },
       {"$set": {"status": "scheduled", "last_called_at": utcnow()}},
       return_document=True,
   )
   ```
2. **Retry & Completion Logic (Builder Decision)**:
   - When picking a lead returns `None`:
     - Check if there are active calls in flight. If yes $\rightarrow$ wait.
     - Check if any leads in this campaign are waiting for a scheduled retry (`status in ["new", "callback"]` with `next_attempt_at > utcnow()`). If yes $\rightarrow$ the campaign stays in `running` state; do **NOT** complete.
     - If and only if zero leads remain in `new`, `scheduled`, or `callback` and zero calls are active $\rightarrow$ mark campaign `completed`.
3. **Just-in-Time DNC Verification (Builder Decision)**:
   - Before dispatching the call, check `await dnc_repo.is_dnc(campaign.organization_id, camp_lead["phone"])`.
   - If DNC: update `camp_lead["status"] = "dnc"` and immediately skip without placing the call.
4. **Call Dispatch**:
   - Initiate call via `CallService.initiate_call`, passing `campaign_id=campaign.id` and `lead_id=camp_lead["lead_id"]`.

### 5.2. Telephony Stream & Prompt Interpolation (`backend/telephony/vobiz.py`, `plivo.py`, `twilio.py`)
When the WebSocket connects for an outbound call (`event == "start"`):
1. Query `call_doc = await db.calls.find_one({"_id": call_id})`.
2. Extract `lead_id = call_doc.get("lead_id")` and `campaign_id = call_doc.get("campaign_id")`.
3. Construct runtime variables:
   ```python
   runtime_vars = dict(agent_input_variables or {})
   
   # 1. Master Lead Contact Fields
   if lead_id:
       lead_doc = await db.leads.find_one({"_id": lead_id})
       if lead_doc:
           lead_name = lead_doc.get("name") or ""
           lead_phone = lead_doc.get("phone") or ""
           lead_email = lead_doc.get("email") or ""
           
           if lead_name:
               runtime_vars.setdefault("name", lead_name)
               runtime_vars.setdefault("user_name", lead_name)
               runtime_vars.setdefault("customer_name", lead_name)
           if lead_phone:
               runtime_vars.setdefault("phone", lead_phone)
               runtime_vars.setdefault("phone_number", lead_phone)
           if lead_email:
               runtime_vars.setdefault("email", lead_email)
               
           for k, v in (lead_doc.get("custom_fields") or {}).items():
               runtime_vars[k] = str(v)
               norm_key = k.strip().lower().replace(" ", "_")
               runtime_vars[norm_key] = str(v)
               
   # 2. Campaign Lead Overrides (takes precedence for campaign-specific values)
   if campaign_id and lead_id:
       camp_lead = await db.campaign_leads.find_one({"campaign_id": campaign_id, "lead_id": lead_id})
       if camp_lead and camp_lead.get("custom_fields"):
           for k, v in camp_lead["custom_fields"].items():
               runtime_vars[k] = str(v)
               norm_key = k.strip().lower().replace(" ", "_")
               runtime_vars[norm_key] = str(v)
   ```
4. Pass `variables=runtime_vars` to `CallSession(..., variables=runtime_vars)`.
5. `CallSession` evaluates:
   - `custom_greeting = interpolate_template(raw_greeting, runtime_vars)`
   - `system_prompt = interpolate_template(raw_system_prompt, runtime_vars)`
   Placeholders like `{user_name}`, `{city}`, or `{due_amount}` are replaced with the contact's actual values before speech synthesis and prompt generation begin.

### 5.3. Call Finalization & Retry Policy Execution
In `CallService.finalize_call`:
- If `call.campaign_id` and `call.lead_id` are set:
  - Query `campaign` and `campaign_lead`.
  - Increment `attempts += 1`.
  - Evaluate outcome:
    - If `call_status == "completed"`: set `campaign_lead.status = "contacted"`.
    - If `call_status in campaign.retry_policy.retry_on` (e.g. `no_answer`, `busy`, `failed`):
      - If `attempts < campaign.retry_policy.max_attempts`:
        - `campaign_lead.status = "callback"`
        - `campaign_lead.next_attempt_at = utcnow() + timedelta(minutes=campaign.retry_policy.retry_delay_minutes)`
      - Else:
        - `campaign_lead.status = "failed"`
  - Update campaign counters (`leads_dialed`, `leads_connected`, `leads_completed`).

### 5.4. Data Migration & Single Source of Truth (Builder Decision)
- At startup, run an automatic one-time migration (`ensure_campaign_leads_backfilled(db)`):
  - Find all documents in `leads` where `campaign_id` is not null.
  - Upsert corresponding `campaign_leads` records.
- All campaign services (`PreflightService`, `CampaignService`, `campaign_worker`) use `campaign_leads` exclusively for campaign lead queries, eliminating risky fallback paths.

---

## 6. Campaign Lead Management APIs & Frontend UI

### 6.1. Campaign Lead REST Endpoints (`backend/api/v1/campaigns.py`)
1. `GET /api/v1/campaigns/{campaign_id}/leads`:
   - Paginated list of leads enrolled in this campaign (`limit`, `skip`, `status` filter).
   - Joins `campaign_leads` with `leads` to return contact details (`name`, `phone`, `email`), campaign `status`, `attempts`, `last_called_at`, `next_attempt_at`.
2. `POST /api/v1/campaigns/{campaign_id}/leads`:
   - Enrolls existing organization contacts into this campaign.
   - Body: `{ "lead_ids": ["..."], "tags": ["..."], "all_contacts": false }`.
3. `DELETE /api/v1/campaigns/{campaign_id}/leads/{lead_id}`:
   - Removes a lead from the campaign (allowed if status is `new` or `callback`).

### 6.2. Interactive Column Mapping UI (`frontend/app/(dashboard)/leads/import/page.tsx`)
- **Step 1: Upload**: Drag & drop or browse file (CSV, XLSX, JSON).
- **Step 2: Preview & Map**:
  - Sample table displaying first 3 rows.
  - Column mapping dropdown per header:
    - Standard: `phone` (Required), `name` / `user_name`, `email`.
    - AI Variables: `city`, `address`, or custom variable input (e.g. `{loan_amount}`, `{appointment_time}`).
    - Option to Skip Column.
  - Auto-matching logic for standard fields (`Phone`, `Mobile`, `Customer Name`, `Email`, `City`, `Address`).
- **Step 3: Target Campaign Selection**:
  - Optional dropdown to select a Campaign to enroll leads into immediately.
- **Step 4: Execute & Import**:
  - Calls `api.leads.import` with `column_mapping` and `campaign_id`.

### 6.3. Campaign Detail Page Leads Tab (`frontend/app/(dashboard)/campaigns/[id]/page.tsx`)
- Display an **Enrolled Leads** section with:
  - Enrolled count, dialed count, and status breakdown.
  - Table of contacts: Name, Phone, Status Badge (`new`, `scheduled`, `contacted`, `failed`, `callback`), Attempts, Last Called.
  - **"Import Leads to Campaign"** button: Opens mapper pre-targeted to this campaign.
  - **"Add from Contacts"** modal: Select existing organization contacts by tag or checkbox.

---

## 7. Verification & Testing Strategy
1. **Unit Tests**:
   - `test_lead_service_column_mapping`: Verifies custom column mapping maps standard fields to root and arbitrary custom keys into `custom_fields`.
   - `test_lead_service_upsert_reimport`: Verifies re-importing an existing phone number updates custom fields and does not fail with duplicate errors.
   - `test_multi_campaign_membership`: Verifies the same contact can be enrolled in Campaign A and Campaign B with separate independent statuses.
   - `test_call_session_variable_interpolation`: Verifies `CallSession` properly interpolates lead `{user_name}` and `{city}` into greeting and system prompt.
   - `test_campaign_retry_policy_execution`: Verifies failed calls schedule retries using `retry_delay_minutes` without prematurely ending the campaign.
2. **Integration & Telephony Tests**:
   - Verify Vobiz/Plivo/Twilio stream initialization resolves `lead_doc` and passes merged variables to `CallSession`.
   - Campaign worker accurately queries `campaign_leads` and updates only the campaign-specific lead status on completion.
3. **End-to-End Campaign Test**:
   - Create Campaign 1 and Campaign 2.
   - Import a test lead mapped to Campaign 1 with custom variable `city: "Mumbai"` and `user_name: "John Doe"`.
   - Dial Campaign 1 $\rightarrow$ Verify call greeting says `"Hello John Doe from Mumbai"`.
   - Verify Campaign 1 status becomes `completed`, while Campaign 2 can still enroll and call the same contact.
