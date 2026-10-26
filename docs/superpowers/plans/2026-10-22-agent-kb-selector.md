# Agent Multi-KB Selector and Response Grounding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable multi-KB association for each AI agent, provide a strict vs. flexible grounding mode toggle, and automatically inject the active KB documents into the call system prompt at runtime.

**Architecture:** 
1. Frontend exposes a Knowledge Base selection card on the Agent Details page (`/agents/[id]`) with checkboxes for each organization KB and a radio selector for Strict vs. Flexible grounding.
2. `frontend/lib/api.ts` provides `api.knowledge.getForAgent`, `api.knowledge.associateAgent`, and `api.knowledge.disassociateAgent`.
3. Backend `KnowledgeService.get_context_for_agent()` is enhanced to support `mode="strict" | "flexible"` directive formatting.
4. `backend/main.py` (`/ws/call`) resolves the agent's associated KBs and strictness setting from `db.agents` and active `agent_versions`, appending the grounding block to `system_prompt` before starting `CallSession`.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, FastAPI, Motor (Async MongoDB), Python 3.11+.

**Spec:** `docs/superpowers/specs/2026-10-22-agent-kb-selector-design.md`

## Global Constraints
- Preserve existing MongoDB collections: `knowledge_bases`, `knowledge_documents`, `knowledge_base_agents`, `agents`, `agent_versions`.
- Keep character budget intact: max 4,000 chars for KB context injection to stay within LLM latency targets.
- Multi-tenant safety: only KBs matching the agent's `organization_id` can be retrieved or associated.

## Review Focus
1. What if an agent has no KBs attached? Prompt must not contain empty or misleading `# Reference Knowledge Base` headers.
2. What if an agent is associated with multiple KBs? Content from all associated KBs should be merged up to the char limit without error.
3. What if a KB document contains Markdown headers or special chars? Truncation and formatting should be safe.
4. Mode switching: Changing from `flexible` to `strict` should take effect on subsequent calls without needing a server restart.
5. Frontend UI updates: Selecting/unselecting KBs should reflect immediately without page refresh.

---

### Task 1: Frontend API Client KB Association Methods

**Files:**
- Modify: `frontend/lib/api.ts:1107-1135`

- [ ] **Step 1: Add TypeScript client methods for KB agent association**
In `frontend/lib/api.ts`, add the following methods under `api.knowledge`:
```typescript
getForAgent: (agentId: string) =>
  apiRequest<KnowledgeBase[]>("GET", `/api/v1/knowledge/agents/${agentId}`),
associateAgent: (kbId: string, agentId: string, priority: number = 0) =>
  apiRequest<{ status: string; kb_id: string; agent_id: string }>(
    "POST",
    `/api/v1/knowledge/${kbId}/agents/${agentId}?priority=${priority}`
  ),
disassociateAgent: (kbId: string, agentId: string) =>
  apiRequest<{ status: string; kb_id: string; agent_id: string }>(
    "DELETE",
    `/api/v1/knowledge/${kbId}/agents/${agentId}`
  ),
```
- [ ] **Step 2: Verify TypeScript compilation**
Run `npm run build` or `npx tsc --noEmit` in `frontend/` to confirm types are correct.

---

### Task 2: Backend Prompt Grounding & Strictness Mode Enhancement

**Files:**
- Modify: `backend/services/knowledge_service.py:227-271`
- Modify: `backend/main.py:323-368`

- [ ] **Step 1: Enhance `KnowledgeService.get_context_for_agent` to support strict/flexible directives**
In `backend/services/knowledge_service.py`, update `get_context_for_agent`:
```python
async def get_context_for_agent(
    self,
    agent_id: str,
    organization_id: str,
    query_text: Optional[str] = None,
    max_chars: int = MAX_CONTEXT_CHARS,
    mode: str = "flexible",
) -> str:
    ...
```
If docs are present, append the corresponding system directive:
- If `mode == "strict"`:
  ```text
  # Reference Knowledge Base (Strict Mode)
  [Document contents]
  CRITICAL INSTRUCTION: Answer questions about products, services, terms, and pricing ONLY using the facts in this reference knowledge base. If asked about something not covered here, politely state that you do not have that information handy and offer to have a team member follow up. Do not fabricate facts.
  ```
- If `mode == "flexible"`:
  ```text
  # Reference Knowledge Base
  [Document contents]
  INSTRUCTION: Use the above reference knowledge as your primary source of truth for facts and answers. For general chit-chat or questions outside this knowledge, reply politely and helpfully.
  ```

- [ ] **Step 2: Inject KB context into `backend/main.py:ws_call`**
In `backend/main.py`, before instantiating `CallSession`:
Look up `agent_id` from the init frame / query params:
1. Fetch agent from `db.agents.find_one({"_id": agent_id})`.
2. Extract `org_id` and check active version config for `knowledge_strictness` (default `"flexible"`).
3. Call `knowledge_svc.get_context_for_agent(agent_id, org_id, mode=mode)`.
4. If context returned, append to `system_prompt`.

---

### Task 3: Backend Unit Tests

**Files:**
- Modify or Add: `backend/tests/test_m19_knowledge.py`

- [ ] **Step 1: Add tests for strict and flexible directive generation**
Test `get_context_for_agent(..., mode="strict")` checks for the strict warning directive.
Test `get_context_for_agent(..., mode="flexible")` checks for the flexible guidance directive.
Test that an agent with no KBs returns an empty string without any directive.

- [ ] **Step 2: Run pytest to verify all tests pass**
Run `pytest backend/tests/test_m19_knowledge.py`.

---

### Task 4: Frontend Agent Knowledge Base Selector UI

**Files:**
- Modify: `frontend/app/(dashboard)/agents/[id]/page.tsx`

- [ ] **Step 1: Add state and fetch functions for Knowledge Bases**
- Fetch all organization KBs using `api.knowledge.list()`.
- Fetch currently associated KBs using `api.knowledge.getForAgent(agentId)`.
- Store `associatedKbIds: Set<string>` and `groundingMode: "flexible" | "strict"`.

- [ ] **Step 2: Render Knowledge Base Card in Agent Configuration**
Include:
1. Section heading: "Knowledge Bases" with badge indicating linked count.
2. Checkboxes for each available Knowledge Base in the organization.
3. Option to toggle between "Flexible (Conversational)" and "Strict Grounding (Never Guess)".
4. Save handler that synchronizes associations via `associateAgent` and `disassociateAgent` and updates version configuration.

- [ ] **Step 3: Test UI interactivity and verify Next.js build**
Build frontend to ensure no lint or type regressions.

---

### Task 5: Verification & Demo

- [ ] **Step 1: Test creating a KB document and linking to an agent.**
- [ ] **Step 2: Verify `GET /api/v1/knowledge/context/{agent_id}` returns formatted KB content with chosen mode.**
- [ ] **Step 3: Verify the call pipeline in `main.py` loads the prompt correctly.**
