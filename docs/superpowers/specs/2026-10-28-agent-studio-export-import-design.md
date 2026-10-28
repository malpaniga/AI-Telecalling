# Agent Studio: Export & Import AI Agents & Separate Knowledge Bases Across Organizations

**Date:** 2026-10-28  
**Status:** In Design Review  
**Topic:** Export and import AI voice agent configurations and separate knowledge bases between organizations via portable `.json` files.

---

## 1. Intent and The Why

Organizations using the SaaS platform need the ability to share custom-crafted AI voice agents and business knowledge with other organizations (e.g., enterprise branches, agency clients, partner networks, or marketplace distributions). Currently, replicating an agent or knowledge base in another organization requires manually re-entering prompts, variables, settings, and documents from scratch.

This feature enables:
1. **1-Click Agent Export/Import:** Export any AI voice agent configuration into a standardized `.agent.json` file, and import it into another organization.
2. **Dedicated Knowledge Base Export/Import:** Export any Knowledge Base (including its FAQs, objections, and policy documents) into a separate `.kb.json` file, and import it into another organization.

By decoupling the files:
- An organization that only wants to share the conversational agent logic (instructions, greetings, variables) shares **only the agent file**.
- An organization that also wants to share their domain knowledge base shares **both files** (agent file + knowledge base file).

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **Export Agent Configuration:** Provide an **Export Agent** action in Agent Studio (`/agents/[id]`) and on individual agent cards on `/agents`. Export downloads a cleanly formatted `.agent.json` file.
- **Import Agent Workflow:** Provide an **Import Agent** button on the `/agents` dashboard that opens an interactive modal. The modal validates the JSON structure, shows a rich preview of the imported agent, allows name customization, maps an appropriate voice profile, and creates the new agent.
- **Separate Knowledge Base Export & Import:**
  - **Export KB:** Action on `/knowledge` (and Knowledge tab in Agent Studio) to download `<kb_name>.kb.json`.
  - **Import KB:** Action on `/knowledge` to upload and import `<kb_name>.kb.json`, creating the KnowledgeBase and all its contained documents (title, content, type, keywords, tags) in the destination organization.
- **Full Configuration Fidelity:** Preserve all agent parameters:
  - Agent Name & Description
  - Base Template Slug
  - Primary Language
  - Greeting text
  - System Prompt / Structured Instructions
  - Input Variables & Output Variables
  - Speech settings (speed, barge-in sensitivity)
  - Tool configurations (WhatsApp, Calendar, Webhook settings)
- **Strict Tenant Isolation & Sanitization:** Automatically strip all tenant-specific and private identifiers:
  - Organization IDs (`organization_id`)
  - Internal database IDs (`id`, `_id`, `version_id`)
  - Telephony assignments (phone numbers, SIP credentials)
  - Call history, transcripts, and analytics

### Non-Goals
- Embedding private knowledge base files inside the agent JSON file itself (they are strictly separate files).
- Exporting purchased phone numbers, SIP trunks, or payment details.
- Real-time live synchronization between two orgs (importing creates an independent fork/copy in the receiving org).

### Anti-Goals
- Breaking tenant isolation: Never allow an imported agent or KB to retain or reference the originating organization's private IDs or resources.
- Silently overwriting an existing agent or KB in the destination org without clear naming.

---

## 3. Constraints

- **Backend:** FastAPI, Pydantic v2 schemas, MongoDB via Motor (`AsyncIOMotorDatabase`).
- **Frontend:** Next.js 14 App Router, React 18, Tailwind CSS, Lucide icons, `react-hot-toast`.
- **Authentication & RBAC:** Multi-tenant scoping enforced via `CurrentUser.org_id`.
- **Portability:** Export files must be plain UTF-8 JSON with `.agent.json` and `.kb.json` extensions.

---

## 4. The Parts of the How Decided

### 4.1 Export Package Formats

#### A. Agent Export Format (`sarvam_agent_export_v1`)
```json
{
  "format": "sarvam_agent_export_v1",
  "exported_at": "2026-10-28T12:00:00Z",
  "agent": {
    "name": "Solar Lead Qualifier (Priya)",
    "description": "Consultative rooftop solar advisor for Maharashtra",
    "template_slug": "solar",
    "primary_language": "mr-IN",
    "configuration": {
      "agent_name": "Priya",
      "primary_language": "mr-IN",
      "greeting": "नमस्कार, मी {partnerName} टीममधून {salesRepName} बोलतेय...",
      "system_prompt": "# Role & Persona\n- **Agent Name**: {salesRepName}...",
      "input_variables": {
        "partnerName": "SolarCorp",
        "salesRepName": "Priya",
        "productCategory": "Rooftop Solar"
      },
      "output_variables": [
        "disposition",
        "monthly_bill",
        "roof_type",
        "chosen_next_step"
      ],
      "speech_speed": 1.0,
      "barge_in_sensitivity": 70,
      "voice_id": null,
      "knowledge_strictness": "flexible",
      "tools": {
        "whatsapp": true,
        "calendar": true,
        "webhook": false,
        "webhook_url": ""
      }
    }
  }
}
```

#### B. Knowledge Base Export Format (`sarvam_kb_export_v1`)
```json
{
  "format": "sarvam_kb_export_v1",
  "exported_at": "2026-10-28T12:00:00Z",
  "knowledge_base": {
    "name": "Solar FAQs & Subsidies",
    "description": "PM Surya Ghar subsidy guidelines and technical rooftop specs",
    "tags": ["solar", "subsidy", "faq"],
    "documents": [
      {
        "title": "PM Surya Ghar Subsidy Breakdown",
        "content": "For 2kW systems, standard government subsidy is ₹78,000...",
        "document_type": "faq",
        "keywords": ["subsidy", "cost", "price", "pm surya ghar"],
        "tags": ["pricing"]
      },
      {
        "title": "Roof Space Requirements",
        "content": "Minimum 200 sq ft shadow-free rooftop space required...",
        "document_type": "product_info",
        "keywords": ["roof", "area", "shadow", "space"],
        "tags": ["technical"]
      }
    ]
  }
}
```

### 4.2 User Experience & Interactions

1. **Agent Export & Import:**
   - **Export:** In Agent Studio top navigation bar (`/agents/[id]`) and on each agent card on `/agents`. Downloads `<name>.agent.json`.
   - **Import:** Button on `/agents` opens the **Import Agent Modal** (validates file, previews greeting/instructions/variables, allows renaming, maps org voice profile, creates agent).
2. **Knowledge Base Export & Import (Separated):**
   - **Export:** On `/knowledge` (and Knowledge tab in Agent Studio), an **Export KB** action downloads `<kb_name>.kb.json`.
   - **Import:** On `/knowledge`, an **Import KB** button opens the **Import Knowledge Base Modal** (validates format, shows document count and titles, allows renaming, creates KB + documents).
3. **Sharing Workflow:**
   - **Agent Only:** Org 1 exports agent file -> Org 2 imports agent file.
   - **Agent + Knowledge Base:** Org 1 exports agent file and exports KB file -> Org 2 imports agent file, imports KB file, and links them with one click.

---

## 5. What's Left to the Builder

1. **Backend Endpoints:**
   - `GET /api/v1/agents/{id}/export`: Exports agent in `sarvam_agent_export_v1` format.
   - `POST /api/v1/agents/import`: Imports agent into current organization.
   - `GET /api/v1/knowledge/{id}/export`: Exports KB and its active documents in `sarvam_kb_export_v1` format.
   - `POST /api/v1/knowledge/import`: Imports KB and documents into current organization.
2. **Frontend Components:**
   - Agent Studio top bar export button + Agent list card export button.
   - `ImportAgentModal` on `/agents`.
   - Knowledge Base export button on `/knowledge` and in Agent Studio Knowledge tab.
   - `ImportKnowledgeBaseModal` on `/knowledge`.
   - API client helpers in `frontend/lib/api.ts`.
3. **Automated Tests:**
   - Unit and integration tests verifying export schema generation, import validation, tenant scrubbing, and end-to-end import flow for both agents and knowledge bases.
