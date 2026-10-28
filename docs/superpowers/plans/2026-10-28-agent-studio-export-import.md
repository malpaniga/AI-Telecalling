# Agent Studio: Export & Import AI Agents and Separate Knowledge Bases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build export and import capabilities for AI voice agents (`.agent.json`) and separate export/import for knowledge bases (`.kb.json`) so organizations can share their agents and domain knowledge securely across workspaces.

**Architecture:** A decoupled JSON export/import pattern where agent configs and knowledge bases have independent standardized schemas (`sarvam_agent_export_v1` and `sarvam_kb_export_v1`). Backend FastAPI services enforce strict multi-tenant sanitization (stripping org IDs, internal IDs, SIP numbers, credentials) and entitlement limits, while Next.js modals provide file validation, preview, and voice profile mapping.

**Tech Stack:** FastAPI, Pydantic v2, Motor (Async MongoDB), Next.js 14 App Router, TypeScript, React 18, Tailwind CSS, Lucide Icons, Pytest.

**Spec:** `docs/superpowers/specs/2026-10-28-agent-studio-export-import-design.md`

## Global Constraints

- **Export schemas:** Agent export MUST conform to `sarvam_agent_export_v1`; Knowledge Base export MUST conform to `sarvam_kb_export_v1`.
- **Tenant isolation:** Never export or preserve `organization_id`, `id`, `_id`, telephony secrets, or private database keys in exported packages.
- **Knowledge base decoupling:** The agent export file MUST NOT contain knowledge base document contents; knowledge bases are exported and imported as distinct `.kb.json` files.
- **Agent limits:** Agent import MUST verify subscription `max_agents` limit before creating agents in the target organization.
- **Voice profile mapping:** When importing an agent without an explicit voice profile, automatically select the active voice profile matching the primary language, falling back to the organization's default.

## Review Focus

1. **Malformed or foreign JSON file uploaded to Agent Import:** The modal and API must reject files without `format: "sarvam_agent_export_v1"` with a clear HTTP 400 error rather than crashing.
2. **Missing or corrupted required configuration fields in import:** If `greeting` or `system_prompt` is missing in the JSON, validation must catch it before DB insertion.
3. **Agent limit reached in destination organization:** If `current_agents >= max_agents`, `POST /api/v1/agents/import` must fail with HTTP 403 / "Agent limit reached" message.
4. **Knowledge base import with empty documents list:** `POST /api/v1/knowledge/import` must handle a knowledge base with 0 documents gracefully without failing.
5. **Cross-org leakage of webhook URLs with internal secrets:** Webhook tool config must preserve URL only if valid, without embedding credentials.

---

### Task 1: Backend Agent Export & Import Services and Endpoints

**Files:**
- Modify: `backend/services/agent_service.py`
- Modify: `backend/api/v1/agents.py`
- Test: `backend/tests/test_m28_agent_export_import.py`

**Interfaces:**
- Consumes: `AgentRepository`, `AgentVersionRepository`, `BusinessTemplateRepository`, `SubscriptionService.check_can_add_agent`
- Produces:
  - `AgentService.export_agent(agent_id: str, organization_id: str) -> dict[str, Any]`
  - `AgentService.import_agent(organization_id: str, name: str, template_slug: str, configuration: dict[str, Any], voice_profile_id: Optional[str] = None, description: str = "") -> Agent`
  - `GET /api/v1/agents/{agent_id}/export` -> returns `sarvam_agent_export_v1` JSON
  - `POST /api/v1/agents/import` -> accepts `ImportAgentRequest`, returns `AgentResponse`

- [ ] **Step 1: Write failing tests for agent export and import**
  Create `backend/tests/test_m28_agent_export_import.py` covering:
  - Exporting an active agent produces a valid `sarvam_agent_export_v1` payload with no `organization_id` or internal Mongo `_id`.
  - Importing that payload into Org B creates a new agent scoped to Org B with an active version 1 containing the original greeting and instructions.
  - Attempting to import when Org B has reached its `max_agents` limit raises an HTTP 403 / ValueError.
  - Attempting to import an invalid schema raises HTTP 400.

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest backend/tests/test_m28_agent_export_import.py -v`
  Expected: FAIL with missing methods / endpoints.

- [ ] **Step 3: Implement `export_agent` and `import_agent` in `AgentService`**
  In `backend/services/agent_service.py`:
  - `export_agent`: Retrieve agent and active configuration version; assemble `sarvam_agent_export_v1` dictionary; omit sensitive IDs and set `knowledge_base_ids` to empty list.
  - `import_agent`: Call `SubscriptionService(self.db).check_can_add_agent(organization_id, current_count)`; resolve `voice_profile_id` (find active voice profile for `configuration.get("primary_language")` or default); create agent; create version 1 with auto-publish & activate.

- [ ] **Step 4: Implement `GET /{id}/export` and `POST /import` in `backend/api/v1/agents.py`**
  - Define `ImportAgentRequest(BaseModel)` with `name`, `template_slug`, `description`, `voice_profile_id`, `configuration`.
  - Add `GET /{agent_id}/export` and `POST /import` with `_require_org(user)`.

- [ ] **Step 5: Run tests to verify they pass**
  Run: `pytest backend/tests/test_m28_agent_export_import.py -v`
  Expected: PASS.

- [ ] **Step 6: Commit**
  Run: `git add backend/services/agent_service.py backend/api/v1/agents.py backend/tests/test_m28_agent_export_import.py && git commit -m "feat(backend): add agent export and import endpoints"`

---

### Task 2: Backend Knowledge Base Export & Import Services and Endpoints

**Files:**
- Modify: `backend/services/knowledge_service.py`
- Modify: `backend/api/v1/knowledge.py`
- Test: `backend/tests/test_m29_kb_export_import.py`

**Interfaces:**
- Consumes: `KnowledgeBaseRepository`, `KnowledgeDocumentRepository`
- Produces:
  - `KnowledgeService.export_knowledge_base(kb_id: str, organization_id: str) -> dict[str, Any]`
  - `KnowledgeService.import_knowledge_base(organization_id: str, name: str, description: str, tags: list[str], documents: list[dict[str, Any]]) -> KnowledgeBase`
  - `GET /api/v1/knowledge/{kb_id}/export` -> returns `sarvam_kb_export_v1` JSON
  - `POST /api/v1/knowledge/import` -> accepts `ImportKBRequest`, returns created `KnowledgeBase`

- [ ] **Step 1: Write failing tests for knowledge base export and import**
  Create `backend/tests/test_m29_kb_export_import.py` covering:
  - Exporting a KB with 2 documents returns `sarvam_kb_export_v1` structure with document titles, contents, and types, scrubbed of internal IDs.
  - Importing into Org B creates a new KB in Org B and imports all documents with `organization_id=Org B`.
  - Exporting a KB that belongs to another organization fails with 404 / tenant violation.

- [ ] **Step 2: Run test to verify it fails**
  Run: `pytest backend/tests/test_m29_kb_export_import.py -v`
  Expected: FAIL with missing methods.

- [ ] **Step 3: Implement `export_knowledge_base` and `import_knowledge_base` in `KnowledgeService`**
  In `backend/services/knowledge_service.py`:
  - `export_knowledge_base`: Fetch KB, verify org isolation, list active documents, format into `sarvam_kb_export_v1`.
  - `import_knowledge_base`: Create new KnowledgeBase for target org, iterate through documents and insert each via `KnowledgeDocumentRepository`.

- [ ] **Step 4: Implement `GET /{kb_id}/export` and `POST /import` in `backend/api/v1/knowledge.py`**
  - Add `ImportKBRequest(BaseModel)` with `name`, `description`, `tags`, `documents`.
  - Wire up endpoints and response serialization.

- [ ] **Step 5: Run tests to verify they pass**
  Run: `pytest backend/tests/test_m29_kb_export_import.py -v`
  Expected: PASS.

- [ ] **Step 6: Commit**
  Run: `git add backend/services/knowledge_service.py backend/api/v1/knowledge.py backend/tests/test_m29_kb_export_import.py && git commit -m "feat(backend): add knowledge base export and import endpoints"`

---

### Task 3: Frontend API Client & Agent Import/Export UI Components

**Files:**
- Modify: `frontend/lib/api.ts`
- Create: `frontend/components/agents/import-agent-modal.tsx`
- Modify: `frontend/app/(dashboard)/agents/page.tsx`
- Modify: `frontend/app/(dashboard)/agents/[id]/page.tsx`

**Interfaces:**
- Consumes: `api.agents.export`, `api.agents.import`, `api.voiceProfiles.list`
- Produces:
  - `ImportAgentModal`: Modal for uploading `.agent.json`, validating schema, previewing configuration, selecting voice profile, and submitting import.
  - Export button in Agent Studio top bar (`/agents/[id]`) that downloads `<name>.agent.json`.
  - Export button on agent card in `/agents`.
  - Import Agent button in `/agents` header opening `ImportAgentModal`.

- [ ] **Step 1: Add export and import functions to `frontend/lib/api.ts`**
  - Under `api.agents`:
    - `export: (id: string) => apiRequest<AgentExportPackage>("GET", \`/api/v1/agents/\${id}/export\`)`
    - `import: (body: ImportAgentRequest) => apiRequest<Agent>("POST", "/api/v1/agents/import", body)`
  - Under `api.knowledge`:
    - `export: (id: string) => apiRequest<KBExportPackage>("GET", \`/api/v1/knowledge/\${id}/export\`)`
    - `import: (body: ImportKBRequest) => apiRequest<KnowledgeBase>("POST", "/api/v1/knowledge/import", body)`

- [ ] **Step 2: Build `ImportAgentModal` component**
  Create `frontend/components/agents/import-agent-modal.tsx`:
  - Drag-and-drop / file selector for `.json` / `.agent.json`.
  - Reads and parses JSON; validates `format === "sarvam_agent_export_v1"` and presence of `agent.configuration`.
  - Previews greeting, instructions snippet, primary language, variable counts, tool status.
  - Input field for customizing Agent Name.
  - Dropdown for Voice Profile, auto-selecting best match for `primary_language`.
  - On confirm, calls `api.agents.import`, shows success toast, and navigates to `/agents/${newAgent.id}`.

- [ ] **Step 3: Add Export & Import buttons to `frontend/app/(dashboard)/agents/page.tsx`**
  - In header actions, add **"Import Agent"** button opening `ImportAgentModal`.
  - On each agent card, add a clean **Export** button (`Download` / `FileDown` icon) that fetches export package and downloads `<agent_name>.agent.json`.

- [ ] **Step 4: Add Export button to Agent Studio top bar (`frontend/app/(dashboard)/agents/[id]/page.tsx`)**
  - In the top action bar next to "Save Draft", add an **"Export Agent"** button with a download icon.
  - Clicking calls `api.agents.export(id)` and triggers a browser download.

- [ ] **Step 5: Run typecheck to verify frontend integrity**
  Run: `cd frontend; npx tsc --noEmit`
  Expected: PASS with 0 errors.

- [ ] **Step 6: Commit**
  Run: `git add frontend/lib/api.ts frontend/components/agents/import-agent-modal.tsx "frontend/app/(dashboard)/agents/page.tsx" "frontend/app/(dashboard)/agents/[id]/page.tsx" && git commit -m "feat(frontend): add agent export and import UI components"`

---

### Task 4: Frontend Separate Knowledge Base Import/Export Components

**Files:**
- Create: `frontend/components/knowledge/import-kb-modal.tsx`
- Modify: `frontend/app/(dashboard)/knowledge/page.tsx`
- Modify: `frontend/app/(dashboard)/agents/[id]/page.tsx` (Knowledge tab)

**Interfaces:**
- Consumes: `api.knowledge.export`, `api.knowledge.import`
- Produces:
  - `ImportKbModal`: Modal for uploading `<name>.kb.json`, previewing documents, and importing.
  - Export action on `/knowledge` and Agent Studio Knowledge tab.
  - Import button on `/knowledge` dashboard.

- [ ] **Step 1: Build `ImportKbModal` component**
  Create `frontend/components/knowledge/import-kb-modal.tsx`:
  - Upload file with client-side validation for `format === "sarvam_kb_export_v1"`.
  - Previews KB name, description, tags, and document list (titles and types).
  - Editable KB name field.
  - On submit, calls `api.knowledge.import`, shows toast, and refreshes KB list.

- [ ] **Step 2: Add Export & Import to `frontend/app/(dashboard)/knowledge/page.tsx`**
  - Add **"Import Knowledge Base"** button to the header actions.
  - Add **"Export"** button on the selected KB header/card to download `<kb_name>.kb.json`.

- [ ] **Step 3: Add Export action in Agent Studio Knowledge Tab (`frontend/app/(dashboard)/agents/[id]/page.tsx`)**
  - On each linked/available knowledge base card, provide an export icon button so users can export knowledge bases directly from Agent Studio.

- [ ] **Step 4: Run typecheck to verify frontend integrity**
  Run: `cd frontend; npx tsc --noEmit`
  Expected: PASS with 0 errors.

- [ ] **Step 5: Commit**
  Run: `git add frontend/components/knowledge/import-kb-modal.tsx "frontend/app/(dashboard)/knowledge/page.tsx" "frontend/app/(dashboard)/agents/[id]/page.tsx" && git commit -m "feat(frontend): add separate knowledge base export and import UI"`

---

### Task 5: End-to-End System Verification and Graphify Update

**Files:**
- Modify: `backend/tests/test_m28_agent_export_import.py`
- Modify: `backend/tests/test_m29_kb_export_import.py`

**Interfaces:**
- Full system regression check across backend tests and frontend typecheck.

- [ ] **Step 1: Run complete backend pytest suite for export/import**
  Run: `pytest backend/tests/test_m28_agent_export_import.py backend/tests/test_m29_kb_export_import.py -v`
  Expected: PASS all tests.

- [ ] **Step 2: Run frontend build verification**
  Run: `cd frontend; npm run build`
  Expected: Build succeeds with 0 errors.

- [ ] **Step 3: Run Graphify update per workspace rule**
  Run: `graphify update .`
  Expected: Knowledge graph updated successfully.

- [ ] **Step 4: Commit**
  Run: `git add -A && git commit -m "chore: verify export-import end-to-end and update graphify"`
