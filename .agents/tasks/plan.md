# M40 Implementation Plan — Complete Frontend Redesign, Backend Integration & Light Theme

## Repository Audit Findings

### What exists (BEFORE M40)
- **Frontend**: Next.js 14 App Router with 4 pages (`/`, `/call`, `/calls`, `/leads`). Dark "Groq-inspired" theme (ink/panel/fg dark palette). Real-estate "Ava Console" branding. No auth. Calls legacy `/api/stats`, `/api/calls`, `/api/leads` (NOT the new v1 API). No routing groups, no sidebar with auth, no multi-tenancy.
- **Backend**: Complete FastAPI MVP through M33 with full authentication, multi-tenancy, billing, campaigns, leads, calls, analytics, etc. All endpoints are under `/api/v1/`.

### The gap
The frontend is a DEMO for a real-estate voice agent. The backend is a production multi-tenant AI telecalling SaaS. Everything must be replaced.

---

## Backend API Inventory

### Auth — `/api/v1/auth/*`
| Method | Path | Request | Response | Roles |
|--------|------|---------|----------|-------|
| POST | /signup | `{org_name, org_email, org_phone?, email, password, first_name?, last_name?}` | `{access_token, refresh_token, token_type, expires_in, user, organization_id}` | Public |
| POST | /login | `{email, password}` | Same as signup | Public |
| POST | /logout | `{refresh_token}` | `{status: "logged out"}` | Authenticated |
| POST | /refresh | `{refresh_token}` | Same as signup | Authenticated |
| GET | /me | — | `{id, email, role, organization_id, first_name, last_name, is_active, is_email_verified}` | Authenticated |

### Agents — `/api/v1/agents/*`
| Method | Path | Request | Response | Roles |
|--------|------|---------|----------|-------|
| GET | /agents/templates | — | `[{slug, name, description, slot_definitions, default_configuration}]` | Authenticated |
| POST | /agents | `{name, template_slug, voice_profile_id, voice_profile_version, description?}` | Agent object | Org member |
| GET | /agents | — | `[Agent]` | Org member |
| GET | /agents/{id} | — | Agent object | Org member |
| DELETE | /agents/{id} | — | `{status, agent_id}` | Org member |
| POST | /agents/{id}/versions | `{configuration, description?, auto_activate?}` | AgentVersion object | Org member |
| GET | /agents/{id}/versions | — | `[AgentVersion]` | Org member |
| POST | /agents/{id}/versions/{vid}/publish | — | AgentVersion object | Org member |
| PATCH | /agents/{id}/versions/{vid} | `{configuration}` | AgentVersion object | Org member |

**Agent object**: `{id, organization_id, name, description, template_slug, voice_profile_id, voice_profile_version, active_version, active_version_id, is_active, created_at}`

**AgentVersion object**: `{id, agent_id, version, status, description, configuration, created_at}`

### Leads — `/api/v1/leads/*`
**Pagination**: `limit` (default 100, max 1000) + `skip` (default 0). Response: `{total, limit, skip, leads: [Lead]}`

| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| POST | /leads | `{phone, name?, email?, custom_fields?, tags?, source?}` | Lead object | |
| GET | /leads | `?campaign_id&status&limit&skip` | `{total, limit, skip, leads}` | |
| GET | /leads/{id} | — | Lead object | |
| PATCH | /leads/{id} | `{name?, email?, status?, score?, qualification?, custom_fields?, tags?, next_contact_at?}` | Lead object | |
| DELETE | /leads/{id} | — | 204 | |
| POST | /leads/import | multipart: `file`, `column_mapping?` (JSON string), `campaign_id?`, `tags?` | `{imported, skipped, errors}` | |
| GET | /leads/dnc | `?limit&skip` | `[{phone, reason, added_at}]` | |
| POST | /leads/dnc | `{phone, reason?, source?}` | `{added, phone}` | |
| DELETE | /leads/dnc/{phone} | — | `{removed, phone}` | |

**Lead object**: `{id, organization_id, campaign_id, phone, name, email, status, score, qualification, custom_fields, tags, attempts, source, last_contact_at, next_contact_at, import_batch_id, created_at, updated_at}`

**Lead statuses**: `new | scheduled | calling | contacted | qualified | not_interested | callback | dnc | failed`

### Campaigns — `/api/v1/campaigns/*`
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| POST | /campaigns | CreateCampaignRequest | Campaign object | |
| GET | /campaigns | `?status&limit&skip` | `[Campaign]` | |
| GET | /campaigns/{id} | — | Campaign object | |
| PATCH | /campaigns/{id} | UpdateCampaignRequest | Campaign object | Draft only |
| GET | /campaigns/{id}/preflight | `?skip_calling_hours` | preflight result | |
| POST | /campaigns/{id}/start | `?skip_preflight` | Campaign object | |
| POST | /campaigns/{id}/pause | — | Campaign object | |
| POST | /campaigns/{id}/resume | — | Campaign object | |
| POST | /campaigns/{id}/cancel | — | Campaign object | |
| GET | /campaigns/{id}/stats | — | stats object | |

**CreateCampaignRequest**: `{name, agent_id, agent_version, voice_profile_id, voice_profile_version, calling_number_id, calling_number, max_concurrent_calls?, timezone?, description?, lead_filter?, calling_hours?, retry_policy?, scheduled_at?}`

**Campaign statuses**: `draft | scheduled | running | paused | paused_low_credits | completed | cancelled | failed`

**Campaign object**: `{id, organization_id, name, description, agent_id, agent_version, voice_profile_id, voice_profile_version, calling_number_id, calling_number, max_concurrent_calls, timezone, status, total_leads, leads_dialed, leads_connected, leads_completed, scheduled_at, started_at, completed_at, cancelled_at, created_at, updated_at}`

### Calls — `/api/v1/calls/*`
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| GET | /calls | `?campaign_id&lead_id&call_status&limit&skip` | `[Call]` | |
| GET | /calls/{id} | — | Call object | |
| POST | /calls/initiate | `{to_number, from_number, campaign_id?, lead_id?, agent_id?, agent_version?, provider?, reserve_credits?}` | result | |
| POST | /calls/{id}/finalize | FinalizeCallRequest | result | Internal |

**Call statuses**: `initiating | ringing | connected | completed | no_answer | busy | failed | cancelled`
**Call outcomes**: `qualified | not_interested | callback | appointment_set | no_answer | voicemail | transferred | failed`

**Call object**: `{id, organization_id, campaign_id, lead_id, to_number, from_number, direction, status, outcome, duration_s, talk_time_s, avg_latency_ms, turn_count, score, qualification, credits_reserved, credits_consumed, summary, started_at, connected_at, ended_at, created_at}`

### Wallet — `/api/v1/wallet/*`
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| GET | /wallet | — | WalletSummary | |
| GET | /wallet/transactions | `?limit&skip&txn_type` | `[Transaction]` | |
| GET | /wallet/lots | — | `[CreditLot]` | |
| GET | /wallet/packs | — | `[CallingPack]` | Public (no auth) |
| GET | /wallet/packs/{id} | — | CallingPack | Public |
| POST | /wallet/packs/{id}/order | — | `{order_id, razorpay_order_id, amount_paise, currency}` | |
| POST | /wallet/admin/bonus | `{organization_id, credits, description?, validity_days?}` | result | Platform admin |
| POST | /wallet/admin/adjust | `{organization_id, credits_delta, reason}` | result | Platform admin |
| GET | /wallet/admin/orgs/{org_id} | — | WalletSummary | Platform |
| POST | /wallet/admin/packs | PackCreateRequest | CallingPack | Platform admin |
| PATCH | /wallet/admin/packs/{id} | PackUpdateRequest | CallingPack | Platform admin |

**CallingPack**: `{id, name, slug, description, credits, bonus_credits, total_credits, price_paise, price_inr, validity_days, is_active, is_public, sort_order}`

**Transaction**: `{id, transaction_type, credits_delta, balance_after, description, call_id, order_id, created_at}`

**WalletSummary** (from service): `{available_credits, reserved_credits, total_credits, total_consumed, total_purchased, is_low, low_threshold}`

### Billing — `/api/v1/billing/*`
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| POST | /billing/orders/subscription | `{plan_id, billing_cycle}` | `{order_id, razorpay_order_id, amount_paise, ...}` | Org owner/admin |
| POST | /billing/verify | `{order_id, provider_payment_id, provider_order_id, provider_signature}` | result | |
| GET | /billing/orders | `?limit&skip` | `[Order]` | |
| GET | /billing/payments | `?limit&skip` | `[Payment]` | |
| GET | /billing/invoices | `?limit&skip` | `[Invoice]` | |
| GET | /billing/invoices/{id} | — | Invoice | |
| POST | /billing/refund/{payment_id} | `{amount_paise?, reason?}` | result | Platform admin |

**Order**: `{id, order_type, description, amount_paise, amount_inr, status, provider, provider_order_id, created_at}`
**Payment**: `{id, order_id, amount_paise, amount_inr, refunded_paise, status, provider, provider_payment_id, paid_at, created_at}`
**Invoice**: `{id, invoice_number, description, subtotal_paise, tax_paise, total_paise, total_inr, currency, status, org_name, issued_at, created_at}`

### Subscriptions — `/api/v1/subscriptions/*`
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| GET | /subscriptions/plans | — | `[Plan]` | Public |
| GET | /subscriptions/plans/{slug} | — | Plan | Public |
| GET | /subscriptions/my | — | Subscription or `{has_subscription: false}` | |
| GET | /subscriptions/my/entitlements | — | Entitlements | |
| POST | /subscriptions/my/cancel | `?at_period_end` | result | Org owner/admin |
| POST | /subscriptions/my/change | `{plan_id, billing_cycle}` | Subscription | Org owner/admin |
| GET | /subscriptions/admin/plans | `?include_inactive` | `[Plan]` | Platform admin |
| POST | /subscriptions/admin/plans | PlanCreateRequest | Plan | Platform admin |
| PATCH | /subscriptions/admin/plans/{id} | PlanUpdateRequest | Plan | Platform admin |
| GET | /subscriptions/admin/all | `?sub_status&limit&skip` | `[Subscription]` | Platform |
| POST | /subscriptions/admin/orgs/{id}/activate | `{plan_id, billing_cycle, payment_id?}` | Subscription | Platform admin |

**Plan**: `{id, name, slug, description, price_monthly_paise, price_monthly_inr, price_yearly_paise, price_yearly_inr, max_concurrent_calls, max_campaigns, max_agents, max_leads_per_campaign, max_team_members, analytics_retention_days, knowledge_base_enabled, api_access, custom_voice_profiles, priority_support, trial_days, is_active, is_public, sort_order}`

**Subscription**: `{id, organization_id, plan_id, plan_slug, billing_cycle, status, started_at, current_period_start, current_period_end, trial_ends_at, cancel_at_period_end, cancelled_at, created_at, limits, features}`

### Voice Profiles — `/api/v1/voice-profiles/*`
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| GET | /voice-profiles | — | `[VoiceProfile]` | Org member — NO provider details |
| GET | /voice-profiles/{id} | — | VoiceProfile | Org member |
| POST | /voice-profiles/admin | `{display_name, language, organization_id?}` | VoiceProfile (with provider) | Platform admin |
| POST | /voice-profiles/admin/{id}/versions | `{routes: {...}}` | VoiceProfileVersion | Platform admin |

**VoiceProfile (customer)**: `{id, display_name, language, is_active, active_version}` — NO provider/model/cost

### Phone Numbers — `/api/v1/phone-numbers/*`
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| GET | /phone-numbers/available | `?country_code&number_type&limit` | `[PhoneNumber]` | No provider details |
| GET | /phone-numbers/my | — | `[PhoneNumber]` | No provider details |
| GET | /phone-numbers/my/{id} | — | PhoneNumber | No provider details |
| GET | /phone-numbers/admin | `?status&provider&limit&skip` | `[PhoneNumber with provider]` | Platform |
| POST | /phone-numbers/admin | AddNumberRequest | PhoneNumber with provider | Platform admin |
| POST | /phone-numbers/admin/{id}/assign | `{organization_id}` | result | Platform admin |
| POST | /phone-numbers/admin/{id}/release | `{notes?}` | result | Platform admin |
| POST | /phone-numbers/admin/{id}/suspend | `{reason?}` | result | Platform admin |
| POST | /phone-numbers/admin/{id}/reactivate | — | result | Platform admin |
| GET | /phone-numbers/admin/stats | — | stats | Platform |

### Appointments — `/api/v1/appointments/*`
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| POST | /appointments | CreateAppointmentRequest | Appointment | |
| GET | /appointments | `?appt_status&appointment_type&lead_id&limit&skip` | `[Appointment]` | |
| GET | /appointments/upcoming | `?limit` | `[Appointment]` | |
| GET | /appointments/summary | — | summary | |
| GET | /appointments/{id} | — | Appointment | |
| PATCH | /appointments/{id} | UpdateAppointmentRequest | Appointment | |
| POST | /appointments/{id}/confirm | — | Appointment | |
| POST | /appointments/{id}/complete | `{outcome_notes?}` | Appointment | |
| POST | /appointments/{id}/cancel | `{reason?}` | Appointment | |
| POST | /appointments/{id}/no-show | — | Appointment | |
| POST | /appointments/{id}/reschedule | `{scheduled_at, notes?}` | Appointment | |

**Appointment statuses**: `scheduled | confirmed | completed | cancelled | no_show`

### Knowledge Base — `/api/v1/knowledge/*`
| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| GET | /knowledge | — | `[KnowledgeBase]` | |
| POST | /knowledge | `{name, description?, tags?}` | KnowledgeBase | |
| GET | /knowledge/{kb_id} | — | KnowledgeBase | |
| DELETE | /knowledge/{kb_id} | — | 204 | |
| GET | /knowledge/{kb_id}/documents | `?document_type&limit&skip` | `[Document]` | |
| POST | /knowledge/{kb_id}/documents | `{title, content, document_type?, keywords?, tags?}` | Document | |
| GET | /knowledge/{kb_id}/documents/{id} | — | Document | |
| PUT | /knowledge/{kb_id}/documents/{id} | `{content, title?}` | Document | Creates new version |
| DELETE | /knowledge/{kb_id}/documents/{id} | — | 204 | |
| POST | /knowledge/{kb_id}/agents/{agent_id} | `?priority` | result | |
| DELETE | /knowledge/{kb_id}/agents/{agent_id} | — | result | |
| GET | /knowledge/agents/{agent_id} | — | `[KnowledgeBase]` | |
| POST | /knowledge/search | `{query, knowledge_base_ids?, limit?}` | `[Document]` | |

### Dashboard — `/api/v1/dashboard/*`
| Method | Path | Notes |
|--------|------|-------|
| GET | /dashboard | Full dashboard: `{calls, campaigns, leads, credits, upcoming_appointments, recent_calls, generated_at}` |
| GET | /dashboard/calls | `?days` (default 7) |
| GET | /dashboard/campaigns | Campaign status breakdown |
| GET | /dashboard/leads | Lead pipeline by status |
| GET | /dashboard/credits | Wallet summary |
| GET | /dashboard/appointments | `?limit` |
| GET | /dashboard/analytics | `?days` (default 30) — daily: `[{date, calls_total, calls_qualified, credits_consumed}]` |

### Users — `/api/v1/users/*`
| Method | Path | Notes |
|--------|------|-------|
| POST | /users/org/{org_id}/invite | Invite team member (org roles only) |
| GET | /users/org/{org_id} | List org users (viewer+) |
| GET | /users/{user_id} | Get user (self or org_admin or platform) |
| PATCH | /users/{user_id} | Update user profile/role |
| DELETE | /users/{user_id} | Deactivate user |

### Admin — `/api/v1/admin/*` (platform roles only)
| Method | Path | Notes |
|--------|------|-------|
| GET | /admin/dashboard | Platform overview |
| GET | /admin/organizations | List all orgs `?org_status&limit&skip` |
| GET | /admin/organizations/{id} | Org detail |
| POST | /admin/organizations/{id}/suspend | Suspend org `?reason` |
| POST | /admin/organizations/{id}/reactivate | Reactivate org |
| GET | /admin/subscriptions | All subscriptions |
| GET | /admin/plans | All plans |
| PATCH | /admin/plans/{id} | Update plan |
| GET | /admin/calling-packs | All packs |
| GET | /admin/payments | All payments `?org_id&limit&skip` |
| GET | /admin/invoices | All invoices `?org_id&limit&skip` |
| GET | /admin/wallets/{org_id} | Org wallet |
| POST | /admin/wallets/{org_id}/adjust | Adjust credits |
| GET | /admin/phone-numbers | All phone numbers |
| GET | /admin/phone-numbers/stats | Inventory stats |
| GET | /admin/voice-profiles | All voice profiles |
| GET | /admin/usage | Platform usage |
| GET | /admin/revenue | Revenue breakdown |
| GET | /admin/costs | Provider cost breakdown |
| GET | /admin/margins | Gross margin |
| GET | /admin/audit-logs | Audit trail `?org_id&limit&skip` |
| GET | /admin/system-health | MongoDB/Redis/provider health |

### Analytics — `/api/v1/analytics/*` (platform roles only)
| Method | Path | Notes |
|--------|------|-------|
| GET | /analytics/mrr | MRR/ARR/ARPU |
| GET | /analytics/mrr-movement | New/expansion/churn |
| GET | /analytics/revenue | Revenue breakdown |
| GET | /analytics/costs | Provider costs |
| GET | /analytics/margins | Gross margin |
| GET | /analytics/arpu | ARPU |
| GET | /analytics/daily | `?days&organization_id` |
| GET | /analytics/report | Full report |

### Provider Ops — `/api/v1/provider-ops/*` (platform roles only)
| Method | Path | Notes |
|--------|------|-------|
| GET | /provider-ops/health | `?hours` |
| GET | /provider-ops/metrics | `?hours&provider_type` |
| GET | /provider-ops/latency | `?hours` |
| GET | /provider-ops/voice-profiles | Voice profile health |

---

## TypeScript Interfaces

```typescript
// lib/api.ts — complete type definitions

export interface AuthUser {
  user_id: string;
  email: string;
  role: string;
  org_id: string | null;
  exp: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: { id: string; email: string; role: string; first_name?: string; last_name?: string };
  organization_id: string | null;
}

export interface User {
  id: string;
  organization_id: string | null;
  email: string;
  role: string;
  first_name?: string;
  last_name?: string;
  is_active: boolean;
  is_email_verified: boolean;
  last_login_at?: string;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  email: string;
  status: string;
  is_verified: boolean;
  max_concurrent_calls: number;
  max_campaigns: number;
  max_agents: number;
  created_at: string;
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  slug: string;
  description: string;
  price_monthly_paise: number;
  price_monthly_inr: number;
  price_yearly_paise: number;
  price_yearly_inr: number;
  max_concurrent_calls: number;
  max_campaigns: number;
  max_agents: number;
  max_leads_per_campaign: number;
  max_team_members: number;
  analytics_retention_days: number;
  knowledge_base_enabled: boolean;
  api_access: boolean;
  custom_voice_profiles: boolean;
  priority_support: boolean;
  trial_days: number;
  is_active: boolean;
  is_public: boolean;
  sort_order: number;
}

export interface Subscription {
  id: string;
  organization_id: string;
  plan_id: string;
  plan_slug: string;
  billing_cycle: 'monthly' | 'yearly';
  status: string;
  started_at: string;
  current_period_start: string;
  current_period_end?: string;
  trial_ends_at?: string;
  cancel_at_period_end: boolean;
  cancelled_at?: string;
  created_at: string;
  limits?: {
    max_concurrent_calls: number;
    max_campaigns: number;
    max_agents: number;
    max_leads_per_campaign: number;
    max_team_members: number;
  };
  features?: Record<string, boolean>;
}

export interface Agent {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  template_slug: string;
  voice_profile_id: string;
  voice_profile_version: number;
  active_version?: number;
  active_version_id?: string;
  is_active: boolean;
  created_at: string;
}

export interface AgentVersion {
  id: string;
  agent_id: string;
  version: number;
  status: 'draft' | 'published';
  description: string;
  configuration: Record<string, unknown>;
  created_at: string;
}

export interface BusinessTemplate {
  slug: string;
  name: string;
  description: string;
  slot_definitions: Record<string, unknown>[];
  default_configuration: Record<string, unknown>;
}

export interface Lead {
  id: string;
  organization_id: string;
  campaign_id?: string;
  phone: string;
  name?: string;
  email?: string;
  status: string;
  score: number;
  qualification: Record<string, unknown>;
  custom_fields: Record<string, unknown>;
  tags: string[];
  attempts: number;
  source: string;
  last_contact_at?: string;
  next_contact_at?: string;
  import_batch_id?: string;
  created_at: string;
  updated_at: string;
}

export interface LeadListResponse {
  total: number;
  limit: number;
  skip: number;
  leads: Lead[];
}

export interface DNCEntry {
  phone: string;
  reason?: string;
  added_at: string;
}

export interface Campaign {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  agent_id: string;
  agent_version: number;
  voice_profile_id: string;
  voice_profile_version: number;
  calling_number_id: string;
  calling_number: string;
  max_concurrent_calls: number;
  timezone: string;
  status: string;
  total_leads: number;
  leads_dialed: number;
  leads_connected: number;
  leads_completed: number;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  cancelled_at?: string;
  created_at: string;
  updated_at: string;
}

export interface Call {
  id: string;
  organization_id: string;
  campaign_id?: string;
  lead_id?: string;
  to_number?: string;
  from_number?: string;
  direction: string;
  status: string;
  outcome?: string;
  duration_s?: number;
  talk_time_s?: number;
  avg_latency_ms?: number;
  turn_count: number;
  score: number;
  qualification: Record<string, unknown>;
  credits_reserved: number;
  credits_consumed: number;
  summary?: string;
  started_at?: string;
  connected_at?: string;
  ended_at?: string;
  created_at: string;
}

export interface Appointment {
  id: string;
  organization_id: string;
  appointment_type: string;
  title?: string;
  description?: string;
  scheduled_at: string;
  duration_minutes: number;
  timezone: string;
  status: string;
  lead_id?: string;
  lead_name?: string;
  lead_phone?: string;
  lead_email?: string;
  call_id?: string;
  campaign_id?: string;
  assigned_user_id?: string;
  location?: string;
  location_type: string;
  notes?: string;
  outcome_notes?: string;
  custom_fields: Record<string, unknown>;
  reminder_sent: boolean;
  created_at: string;
  updated_at: string;
}

export interface PhoneNumber {
  id: string;
  number: string;
  display_name?: string;
  country_code: string;
  number_type: string;
  status: string;
  can_voice: boolean;
  can_sms: boolean;
  can_whatsapp: boolean;
  // Admin only:
  provider?: string;
  provider_resource_id?: string;
  rental_paise_per_month?: number;
  organization_id?: string;
}

export interface KnowledgeBase {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  document_count: number;
  is_active: boolean;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocument {
  id: string;
  knowledge_base_id: string;
  title: string;
  content: string;
  document_type: string;
  version: number;
  keywords: string[];
  tags: string[];
  is_active: boolean;
  created_at: string;
}

export interface WalletSummary {
  available_credits: number;
  reserved_credits: number;
  total_credits: number;
  total_consumed: number;
  total_purchased: number;
  is_low: boolean;
  low_threshold: number;
}

export interface Transaction {
  id: string;
  transaction_type: string;
  credits_delta: number;
  balance_after: number;
  description?: string;
  call_id?: string;
  order_id?: string;
  created_at: string;
}

export interface CreditLot {
  id: string;
  original_credits: number;
  remaining_credits: number;
  source: string;
  expires_at?: string;
  is_expired: boolean;
  purchased_at: string;
}

export interface CallingPack {
  id: string;
  name: string;
  slug: string;
  description: string;
  credits: number;
  bonus_credits: number;
  total_credits: number;
  price_paise: number;
  price_inr: number;
  validity_days: number;
  is_active: boolean;
  is_public: boolean;
  sort_order: number;
}

export interface Order {
  id: string;
  order_type: string;
  description?: string;
  amount_paise: number;
  amount_inr: number;
  status: string;
  provider: string;
  provider_order_id?: string;
  created_at: string;
}

export interface Payment {
  id: string;
  order_id: string;
  amount_paise: number;
  amount_inr: number;
  refunded_paise: number;
  status: string;
  provider: string;
  provider_payment_id?: string;
  paid_at: string;
  created_at: string;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  description?: string;
  subtotal_paise: number;
  tax_paise: number;
  total_paise: number;
  total_inr: number;
  currency: string;
  status: string;
  org_name?: string;
  issued_at: string;
  created_at: string;
}

export interface VoiceProfile {
  id: string;
  display_name: string;
  language: string;
  is_active: boolean;
  active_version?: number;
  // Admin only:
  is_platform?: boolean;
  organization_id?: string;
}

export interface DashboardData {
  organization_id: string;
  calls: {
    total: number;
    connected: number;
    completed: number;
    connected_rate_pct: number;
    avg_duration_s?: number;
    avg_latency_ms?: number;
    outcomes: Record<string, number>;
    qualified: number;
    not_interested: number;
  };
  campaigns: {
    total: number;
    by_status: Record<string, number>;
    running: number;
    running_campaigns: Array<{id: string; name: string; leads_dialed: number; leads_completed: number; status: string}>;
  };
  leads: {
    total: number;
    by_status: Record<string, number>;
    new: number;
    qualified: number;
    not_interested: number;
    callback: number;
    avg_score: number;
  };
  credits: WalletSummary;
  upcoming_appointments: Array<{id: string; appointment_type: string; title?: string; scheduled_at: string; timezone: string; status: string; lead_name?: string; lead_phone?: string}>;
  recent_calls: Array<{id: string; to_number?: string; status: string; outcome?: string; duration_s?: number; score: number; started_at: string}>;
  generated_at: string;
}

export interface AdminDashboard {
  organizations: { total_active: number; recent: Array<{id: string; name: string; status: string; created_at: string}> };
  subscriptions: { total: number; active: number; trialing: number; cancelled: number; by_status: Record<string, number> };
  usage: { total_events: number; total_credits: number; total_charge_paise: number; total_charge_inr: number; total_provider_cost_paise: number; gross_profit_paise: number };
}
```

---

## Implementation Phases

This plan is implemented as 5 sequential FEATs. Each FEAT is in `c:\Programs\saas\.agents\tasks\task-m40-frontend-redesign\features\`. Full step details are in the FEAT JSON files.

---

- [ ] 1. **FEAT-001: Design Foundations + API Client + Component Library**
      Replace tailwind.config.ts with light palette. Replace globals.css with CSS variables. Update next.config.mjs. Create lib/auth.ts (token storage). Create contexts/auth-context.tsx (React auth context). Completely rewrite lib/api.ts (all endpoints, JWT, error handling). Create components/ui/ (Button, Badge, Card, Input, Select, Modal, Table, Pagination, Spinner, EmptyState, MetricCard). Create components/layout/ (Sidebar, Topbar, AppShell, AdminSidebar).
      Files: `frontend/tailwind.config.ts`, `frontend/app/globals.css`, `frontend/next.config.mjs`, `frontend/lib/auth.ts`, `frontend/contexts/auth-context.tsx`, `frontend/lib/api.ts`, `frontend/components/ui/*.tsx`, `frontend/components/layout/*.tsx`
      Verify: `cd frontend && npm run build` — TypeScript must compile with zero errors.

- [ ] 2. **FEAT-002: App Shell, Routing, Auth Pages, Landing Page**
      Update app/layout.tsx with Inter font and AuthProvider. Create (auth)/layout.tsx, (auth)/login/page.tsx, (auth)/signup/page.tsx. Create (dashboard)/layout.tsx (auth guard). Create (admin)/layout.tsx (role guard). Replace app/page.tsx with light-theme AI telecalling landing page (NOT real estate). Clean up old dark nav/ui stubs.
      Files: `frontend/app/layout.tsx`, `frontend/app/(auth)/layout.tsx`, `frontend/app/(auth)/login/page.tsx`, `frontend/app/(auth)/signup/page.tsx`, `frontend/app/(dashboard)/layout.tsx`, `frontend/app/(admin)/layout.tsx`, `frontend/app/page.tsx`
      Verify: `cd frontend && npm run build` — zero errors. Landing page must not mention real estate.

- [ ] 3. **FEAT-003: All Customer Dashboard Pages (19 pages)**
      Implement all authenticated customer pages connected to the real backend API. See FEAT-003.json for detailed steps for each of the 19 pages.
      Files: `frontend/app/(dashboard)/dashboard/page.tsx`, `frontend/app/(dashboard)/agents/page.tsx`, `frontend/app/(dashboard)/agents/new/page.tsx`, `frontend/app/(dashboard)/agents/[id]/page.tsx`, `frontend/app/(dashboard)/campaigns/page.tsx`, `frontend/app/(dashboard)/campaigns/new/page.tsx`, `frontend/app/(dashboard)/campaigns/[id]/page.tsx`, `frontend/app/(dashboard)/leads/page.tsx`, `frontend/app/(dashboard)/leads/import/page.tsx`, `frontend/app/(dashboard)/calls/page.tsx`, `frontend/app/(dashboard)/calls/[id]/page.tsx`, `frontend/app/(dashboard)/appointments/page.tsx`, `frontend/app/(dashboard)/phone-numbers/page.tsx`, `frontend/app/(dashboard)/credits/page.tsx`, `frontend/app/(dashboard)/billing/page.tsx`, `frontend/app/(dashboard)/knowledge/page.tsx`, `frontend/app/(dashboard)/analytics/page.tsx`, `frontend/app/(dashboard)/team/page.tsx`, `frontend/app/(dashboard)/settings/page.tsx`
      Verify: `cd frontend && npm run build` — zero errors.

- [ ] 4. **FEAT-004: All Super Admin Pages (12 pages)**
      Implement all platform-admin-only pages. See FEAT-004.json for detailed steps.
      Files: `frontend/app/(admin)/admin/dashboard/page.tsx`, `frontend/app/(admin)/admin/organizations/page.tsx`, `frontend/app/(admin)/admin/organizations/[id]/page.tsx`, `frontend/app/(admin)/admin/subscriptions/page.tsx`, `frontend/app/(admin)/admin/calling-packs/page.tsx`, `frontend/app/(admin)/admin/payments/page.tsx`, `frontend/app/(admin)/admin/phone-numbers/page.tsx`, `frontend/app/(admin)/admin/voice-profiles/page.tsx`, `frontend/app/(admin)/admin/providers/page.tsx`, `frontend/app/(admin)/admin/usage/page.tsx`, `frontend/app/(admin)/admin/analytics/page.tsx`, `frontend/app/(admin)/admin/audit-logs/page.tsx`
      Verify: `cd frontend && npm run build` — zero errors.

- [ ] 5. **FEAT-005: Integration, Build Verification, Documentation**
      Fix any TypeScript errors from integration. Verify Razorpay payment flow. Run full build + lint. Verify no dark-theme remnants. Update MVP_PROGRESS.md. Git commit.
      Files: Any files needing fixes + `MVP_PROGRESS.md` + `.agents/tasks/review.json`
      Verify: `cd frontend && npm run build` + `npm run lint` — both pass with zero errors/warnings.

---

## Gaps and Issues Found

1. **No `tsconfig.json` path alias check needed** — existing tsconfig likely has `@/*` mapped to root. Verify this works for new subdirectories.
2. **Razorpay script** — must be loaded dynamically via `<Script>` (next/script) since it's a CDN script, not an npm package. The `window.Razorpay` usage needs a type declaration or `// @ts-ignore`.
3. **Transcript endpoint** — `/api/v1/transcripts/{call_id}` is referenced in `backend/api/v1/__init__.py` but not audited above. The call detail page should handle 404 gracefully if no transcript exists.
4. **No PATCH /organizations endpoint** — the settings page shows org info as read-only. User profile updates use PATCH /users/{id}.
5. **Pagination pattern** — backend uses `skip/limit`, not `page/pageSize`. The Pagination component must translate page number to skip value: `skip = (page - 1) * limit`.
6. **Auth token refresh** — the `lib/api.ts` apiRequest should handle 401 by calling POST /api/v1/auth/refresh with the stored refresh_token, updating tokens, and retrying the original request once.
7. **Missing `tsconfig.json` `paths`** — verify `"@/*": ["./*"]` is in frontend/tsconfig.json. If not, add it.

---

## Notes for the Coder

- **Absolute worktree path**: `c:\Programs\saas\frontend\`
- **Read FEAT files first**: `c:\Programs\saas\.agents\tasks\task-m40-frontend-redesign\context.json` and the relevant FEAT JSON before starting each feature.
- **No mock data in production flows** — every page must fetch from the real API. Use loading skeletons.
- **Error handling** — every API call must be wrapped in try/catch with user-visible error feedback (react-hot-toast).
- **Loading states** — every page must show a spinner/skeleton while data loads.
- **Empty states** — every list/table must show an EmptyState component when there's no data.
- **Provider names** — NEVER show Sarvam, ElevenLabs, Exotel, Twilio, etc. in customer-facing pages.
- **INR formatting** — prices in paise must be displayed as ₹X,XXX (divide by 100, format with Indian locale).
- **Credits** — 1 credit = 1 billable second. Display in minutes where appropriate (credits / 60 = approx minutes).
- **The verdict file** — the build loop watches `c:\Programs\saas\.agents\tasks\review.json` for `{"verdict": "APPROVED"}`. Do NOT write this file yourself. The reviewer writes it.
