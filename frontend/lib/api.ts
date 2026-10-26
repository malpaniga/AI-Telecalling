import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "@/lib/auth";

export const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    message?: string
  ) {
    super(message ?? detail);
  }
}

// ---------------------------------------------------------------------------
// TypeScript interfaces matching backend response shapes
// ---------------------------------------------------------------------------

export interface User {
  id: string;
  email: string;
  role: string;
  organization_id: string | null;
  first_name: string | null;
  last_name: string | null;
  is_active: boolean;
  is_email_verified: boolean;
  last_login_at: string | null;
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
  billing_cycle: string;
  status: string;
  started_at: string;
  current_period_start: string;
  current_period_end: string | null;
  trial_ends_at: string | null;
  cancel_at_period_end: boolean;
  cancelled_at: string | null;
  created_at: string;
  limits?: {
    max_concurrent_calls: number;
    max_campaigns: number;
    max_agents: number;
    max_leads_per_campaign: number;
    max_team_members: number;
  };
  features?: Record<string, boolean>;
  has_subscription?: boolean;
}

export interface Entitlements {
  has_subscription: boolean;
  plan_slug: string | null;
  status: string | null;
  limits: Record<string, number>;
  features: Record<string, boolean>;
  usage: Record<string, number>;
}

export interface Order {
  id: string;
  order_type: string;
  description: string;
  amount_paise: number;
  amount_inr: number;
  status: string;
  provider: string;
  provider_order_id: string | null;
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
  provider_payment_id: string;
  paid_at: string;
  created_at: string;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  description: string;
  subtotal_paise: number;
  tax_paise: number;
  total_paise: number;
  total_inr: number;
  currency: string;
  status: string;
  org_name: string;
  issued_at: string;
  created_at: string;
}

export interface Agent {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  template_slug: string;
  voice_profile_id: string;
  voice_profile_version: number;
  active_version: number | null;
  active_version_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AgentVersion {
  id: string;
  agent_id: string;
  version: number;
  status: string;
  description: string;
  configuration: Record<string, unknown>;
  created_at: string;
}

export interface BusinessTemplate {
  slug: string;
  name: string;
  description: string;
  category?: string;
  icon_color?: string;
  slot_definitions: Record<string, unknown> | Array<Record<string, unknown>>;
  default_configuration: Record<string, unknown>;
}

export interface Lead {
  id: string;
  organization_id: string;
  campaign_id: string | null;
  phone: string;
  name: string | null;
  email: string | null;
  status: string;
  score: number;
  qualification: Record<string, unknown> | null;
  custom_fields: Record<string, unknown> | null;
  tags: string[];
  attempts: number;
  source: string;
  last_contact_at: string | null;
  next_contact_at: string | null;
  import_batch_id: string | null;
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
  reason: string | null;
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
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignStats {
  total_leads: number;
  leads_dialed: number;
  leads_connected: number;
  leads_completed: number;
  connected_rate_pct: number;
  outcomes: Record<string, number>;
}

export interface Call {
  id: string;
  organization_id: string;
  campaign_id: string | null;
  lead_id: string | null;
  to_number: string;
  from_number: string;
  direction: string;
  status: string;
  outcome: string | null;
  duration_s: number | null;
  talk_time_s: number | null;
  avg_latency_ms: number | null;
  turn_count: number;
  score: number;
  qualification: Record<string, unknown> | null;
  credits_reserved: number;
  credits_consumed: number;
  summary: string | null;
  started_at: string | null;
  connected_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface Appointment {
  id: string;
  organization_id: string;
  appointment_type: string;
  title: string | null;
  description: string | null;
  scheduled_at: string;
  duration_minutes: number;
  timezone: string;
  status: string;
  lead_id: string | null;
  lead_name: string | null;
  lead_phone: string | null;
  lead_email: string | null;
  call_id: string | null;
  campaign_id: string | null;
  assigned_user_id: string | null;
  location: string | null;
  location_type: string;
  notes: string | null;
  outcome_notes: string | null;
  custom_fields: Record<string, unknown> | null;
  reminder_sent: boolean;
  created_at: string;
  updated_at: string;
}

export interface PhoneNumber {
  id: string;
  number: string;
  status: string;
  organization_id: string | null;
  assigned_org_ids?: string[];
  inbound_organization_id?: string | null;
  inbound_agent_id?: string | null;
  display_name?: string | null;
  provider?: string;
  provider_metadata?: Record<string, unknown>;
  assigned_at: string | null;
  created_at: string;
}

export interface KnowledgeBase {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  document_count: number;
  created_at: string;
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
  organization_id: string;
  available_credits: number;
  reserved_credits: number;
  total_purchased: number;
  total_consumed: number;
  total_bonus: number;
  is_low: boolean;
  low_threshold: number;
}

export interface Transaction {
  id: string;
  transaction_type: string;
  credits_delta: number;
  balance_after: number;
  description: string;
  call_id: string | null;
  order_id: string | null;
  created_at: string;
}

export interface CreditLot {
  id: string;
  original_credits: number;
  remaining_credits: number;
  source: string;
  expires_at: string | null;
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

export interface VoiceProfile {
  id: string;
  display_name: string;
  language: string;
  is_platform: boolean;
  is_active: boolean;
  active_version: number | null;
  organization_id: string | null;
  created_at: string;
}

export interface DashboardData {
  organization_id: string;
  calls: {
    total: number;
    connected: number;
    completed: number;
    connected_rate_pct: number;
    avg_duration_s: number | null;
    avg_latency_ms: number | null;
    outcomes: Record<string, number>;
    qualified: number;
    not_interested: number;
  };
  campaigns: {
    total: number;
    by_status: Record<string, number>;
    running: number;
    running_campaigns: Array<{
      id: string;
      name: string;
      leads_dialed: number;
      leads_completed: number;
      status: string;
    }>;
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
  credits: {
    available_credits: number;
    reserved_credits: number;
    total_credits: number;
    total_consumed: number;
    is_low: boolean;
    low_threshold: number;
  };
  upcoming_appointments: Array<{
    id: string;
    appointment_type: string;
    title: string | null;
    scheduled_at: string;
    timezone: string;
    status: string;
    lead_name: string | null;
    lead_phone: string | null;
  }>;
  recent_calls: Array<{
    id: string;
    to_number: string;
    status: string;
    outcome: string | null;
    duration_s: number | null;
    score: number;
    started_at: string;
  }>;
  generated_at: string;
}

// ---------------------------------------------------------------------------
// AI Model Directory interfaces
// ---------------------------------------------------------------------------

export interface AIModelCatalogue {
  id: string;
  provider_name: string;
  model_id: string;
  capability: "tts" | "stt" | "llm";
  hosting_mode: "managed_api" | "local_runtime" | "self_hosted";
  supported_languages: string[];
  streaming_supported: boolean;
  credential_requirements: string[];
  setup_requirements: string | null;
  license_spdx: string | null;
  commercial_use_allowed: boolean | null;
  free_tier_info: Record<string, unknown> | string | null;
  free_tier_verified_date: string | null;
  pricing_per_minute_usd: number | null;
  doc_url: string | null;
  model_card_url: string | null;
  implementation_status: "supported" | "experimental" | "unavailable";
  notes: string | null;
}

export interface ProviderConfiguration {
  id: string;
  capability: "tts" | "stt" | "llm";
  provider_name: string;
  model_id: string;
  is_active: boolean;
  is_fallback: boolean;
  voice: string | null;
  language: string | null;
  extra_params: Record<string, unknown> | null;
  last_tested_at: string | null;
  last_test_result: "ok" | "error" | null;
  last_test_latency_ms: number | null;
  activated_at: string | null;
  created_at: string;
}

export interface ProviderCredentialMeta {
  provider_name: string;
  key_hint: string | null;
  created_at: string | null;
  rotated_at: string | null;
}

export interface ConnectProviderRequest {
  provider_name: string;
  model_id: string;
  capability: "tts" | "stt" | "llm";
  credential_plaintext?: string;
  voice?: string;
  language?: string;
  extra_params?: Record<string, unknown>;
  is_fallback?: boolean;
}

export interface TestResult {
  status: "ok" | "error";
  latency_ms: number | null;
  error?: string | null;
  sample_output_b64?: string | null;
  transcript?: string | null;
  response?: string | null;
}

export interface WizardCapabilityStatus {
  connected: boolean;
  tested: boolean;
  active: boolean;
  active_provider: string | null;
  active_latency_ms: number | null;
  configs: number;
}

export interface WizardStatusResponse {
  capabilities: {
    stt: WizardCapabilityStatus;
    tts: WizardCapabilityStatus;
    llm: WizardCapabilityStatus;
  };
  all_ready: boolean;
}

export interface AdminDashboard {
  organizations: {
    total_active: number;
    recent: Array<{
      id: string;
      name: string;
      status: string;
      created_at: string;
    }>;
  };
  subscriptions: {
    total: number;
    active: number;
    trialing: number;
    cancelled: number;
    by_status: Record<string, number>;
  };
  usage: {
    total_events: number;
    total_credits: number;
    total_charge_paise: number;
    total_charge_inr: number;
    total_provider_cost_paise: number;
    gross_profit_paise: number;
  };
}

// ---------------------------------------------------------------------------
// Core request function
// ---------------------------------------------------------------------------

let _refreshPromise: Promise<void> | null = null;

async function _doRefresh(): Promise<void> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) throw new ApiError(401, "No refresh token");
  const res = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) {
    clearTokens();
    throw new ApiError(401, "Session expired");
  }
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
}

export async function apiRequest<T>(
  method: string,
  path: string,
  body?: unknown,
  opts?: { signal?: AbortSignal; formData?: FormData }
): Promise<T> {
  const makeRequest = async (): Promise<Response> => {
    const token = getAccessToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    let fetchBody: BodyInit | undefined;
    if (opts?.formData) {
      fetchBody = opts.formData;
      // Don't set Content-Type — let browser set it with boundary
    } else if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      fetchBody = JSON.stringify(body);
    }

    return fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: fetchBody,
      signal: opts?.signal,
    });
  };

  let res = await makeRequest();

  // 401 → attempt one token refresh and retry
  if (res.status === 401) {
    try {
      if (!_refreshPromise) {
        _refreshPromise = _doRefresh().finally(() => {
          _refreshPromise = null;
        });
      }
      await _refreshPromise;
      res = await makeRequest();
    } catch {
      throw new ApiError(401, "Session expired. Please log in again.");
    }
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const errBody = await res.json();
      detail = errBody.detail ?? detail;
    } catch {
      // ignore parse error
    }
    throw new ApiError(res.status, detail);
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// API object — namespaced methods for every backend endpoint
// ---------------------------------------------------------------------------

export const api = {
  // ── Auth ──────────────────────────────────────────────────────────────────
  auth: {
    login: (email: string, password: string) =>
      apiRequest<{ access_token: string; refresh_token: string; token_type: string; expires_in: number; user: Partial<User>; organization_id: string | null }>(
        "POST", "/api/v1/auth/login", { email, password }
      ),
    signup: (body: {
      org_name: string;
      org_email: string;
      org_phone?: string;
      email: string;
      password: string;
      first_name?: string;
      last_name?: string;
    }) =>
      apiRequest<{ access_token: string; refresh_token: string; token_type: string; expires_in: number; user: Partial<User>; organization_id: string | null }>(
        "POST", "/api/v1/auth/signup", body
      ),
    logout: (refresh_token: string) =>
      apiRequest<{ status: string }>("POST", "/api/v1/auth/logout", {
        refresh_token,
      }),
    refresh: (refresh_token: string) =>
      apiRequest<{ access_token: string; refresh_token: string }>(
        "POST", "/api/v1/auth/refresh", { refresh_token }
      ),
    me: () => apiRequest<User>("GET", "/api/v1/auth/me"),
  },

  // ── Agents ────────────────────────────────────────────────────────────────
  agents: {
    templates: () =>
      apiRequest<BusinessTemplate[]>("GET", "/api/v1/agents/templates"),
    list: () => apiRequest<Agent[]>("GET", "/api/v1/agents"),
    get: (id: string) => apiRequest<Agent>("GET", `/api/v1/agents/${id}`),
    create: (body: {
      name: string;
      template_slug: string;
      voice_profile_id?: string;
      voice_profile_version?: number;
      description?: string;
      auto_init_version?: boolean;
      initial_configuration?: Record<string, unknown>;
    }) => apiRequest<Agent>("POST", "/api/v1/agents", body),
    update: (
      id: string,
      body: Partial<{
        name: string;
        description: string;
        voice_profile_id: string;
        voice_profile_version: number;
      }>
    ) => apiRequest<Agent>("PATCH", `/api/v1/agents/${id}`, body),
    improveWithGenie: (body: {
      instructions: string;
      greeting?: string;
      persona_focus?: string;
    }) =>
      apiRequest<{
        improved_instructions: string;
        suggestions: string[];
      }>("POST", "/api/v1/agents/improve-instructions", body),
    translateGreeting: (body: { text: string; target_language: string }) =>
      apiRequest<{ translated_text: string }>(
        "POST",
        "/api/v1/agents/translate-greeting",
        body,
      ),
    pipelineStatus: () =>
      apiRequest<{
        stt: { connected: boolean };
        llm: { connected: boolean };
        tts: { connected: boolean };
        all_ready: boolean;
      }>("GET", "/api/v1/agents/pipeline-status"),
    delete: (id: string) =>
      apiRequest<{ status: string; agent_id: string }>(
        "DELETE", `/api/v1/agents/${id}`
      ),
    versions: {
      list: (agentId: string) =>
        apiRequest<AgentVersion[]>("GET", `/api/v1/agents/${agentId}/versions`),
      create: (
        agentId: string,
        body: {
          configuration: Record<string, unknown>;
          description?: string;
          auto_activate?: boolean;
        }
      ) =>
        apiRequest<AgentVersion>(
          "POST", `/api/v1/agents/${agentId}/versions`, body
        ),
      update: (
        agentId: string,
        versionId: string,
        configuration: Record<string, unknown>
      ) =>
        apiRequest<AgentVersion>(
          "PATCH",
          `/api/v1/agents/${agentId}/versions/${versionId}`,
          { configuration }
        ),
      publish: (agentId: string, versionId: string) =>
        apiRequest<AgentVersion>(
          "POST",
          `/api/v1/agents/${agentId}/versions/${versionId}/publish`
        ),
    },
  },

  // ── Leads ─────────────────────────────────────────────────────────────────
  leads: {
    list: (params?: {
      campaign_id?: string;
      status?: string;
      limit?: number;
      skip?: number;
    }) => {
      const q = new URLSearchParams();
      if (params?.campaign_id) q.set("campaign_id", params.campaign_id);
      if (params?.status) q.set("status", params.status);
      if (params?.limit != null) q.set("limit", String(params.limit));
      if (params?.skip != null) q.set("skip", String(params.skip));
      return apiRequest<LeadListResponse>(
        "GET", `/api/v1/leads${q.toString() ? "?" + q : ""}`
      );
    },
    get: (id: string) => apiRequest<Lead>("GET", `/api/v1/leads/${id}`),
    create: (body: {
      phone: string;
      name?: string;
      email?: string;
      custom_fields?: Record<string, unknown>;
      tags?: string[];
      source?: string;
    }) => apiRequest<Lead>("POST", "/api/v1/leads", body),
    update: (id: string, body: Partial<Lead>) =>
      apiRequest<Lead>("PATCH", `/api/v1/leads/${id}`, body),
    delete: (id: string) =>
      apiRequest<void>("DELETE", `/api/v1/leads/${id}`),
    import: (file: File, opts?: { campaign_id?: string; tags?: string }) => {
      const fd = new FormData();
      fd.append("file", file);
      if (opts?.campaign_id) fd.append("campaign_id", opts.campaign_id);
      if (opts?.tags) fd.append("tags", opts.tags);
      return apiRequest<{ imported: number; skipped: number; errors: number }>(
        "POST", "/api/v1/leads/import", undefined, { formData: fd }
      );
    },
    dnc: {
      list: (params?: { limit?: number; skip?: number }) => {
        const q = new URLSearchParams();
        if (params?.limit != null) q.set("limit", String(params.limit));
        if (params?.skip != null) q.set("skip", String(params.skip));
        return apiRequest<DNCEntry[]>(
          "GET", `/api/v1/leads/dnc${q.toString() ? "?" + q : ""}`
        );
      },
      add: (body: { phone: string; reason?: string; source?: string }) =>
        apiRequest<{ added: boolean; phone: string }>(
          "POST", "/api/v1/leads/dnc", body
        ),
      remove: (phone: string) =>
        apiRequest<{ removed: boolean; phone: string }>(
          "DELETE", `/api/v1/leads/dnc/${encodeURIComponent(phone)}`
        ),
    },
  },

  // ── Campaigns ─────────────────────────────────────────────────────────────
  campaigns: {
    list: (params?: { status?: string; limit?: number; skip?: number }) => {
      const q = new URLSearchParams();
      if (params?.status) q.set("status", params.status);
      if (params?.limit != null) q.set("limit", String(params.limit));
      if (params?.skip != null) q.set("skip", String(params.skip));
      return apiRequest<Campaign[]>(
        "GET", `/api/v1/campaigns${q.toString() ? "?" + q : ""}`
      );
    },
    get: (id: string) =>
      apiRequest<Campaign>("GET", `/api/v1/campaigns/${id}`),
    create: (body: {
      name: string;
      agent_id: string;
      agent_version: number;
      voice_profile_id: string;
      voice_profile_version: number;
      calling_number_id: string;
      calling_number: string;
      max_concurrent_calls?: number;
      timezone?: string;
      description?: string;
      lead_filter?: Record<string, unknown>;
      calling_hours?: Record<string, unknown>;
      retry_policy?: Record<string, unknown>;
      scheduled_at?: string;
    }) => apiRequest<Campaign>("POST", "/api/v1/campaigns", body),
    update: (id: string, body: Partial<Campaign>) =>
      apiRequest<Campaign>("PATCH", `/api/v1/campaigns/${id}`, body),
    start: (id: string, skip_preflight?: boolean) =>
      apiRequest<Campaign>(
        "POST",
        `/api/v1/campaigns/${id}/start${skip_preflight ? "?skip_preflight=true" : ""}`
      ),
    pause: (id: string) =>
      apiRequest<Campaign>("POST", `/api/v1/campaigns/${id}/pause`),
    resume: (id: string) =>
      apiRequest<Campaign>("POST", `/api/v1/campaigns/${id}/resume`),
    cancel: (id: string) =>
      apiRequest<Campaign>("POST", `/api/v1/campaigns/${id}/cancel`),
    stats: (id: string) =>
      apiRequest<CampaignStats>("GET", `/api/v1/campaigns/${id}/stats`),
    preflight: (id: string) =>
      apiRequest<Record<string, unknown>>(
        "GET", `/api/v1/campaigns/${id}/preflight`
      ),
  },

  // ── Calls ─────────────────────────────────────────────────────────────────
  calls: {
    list: (params?: {
      campaign_id?: string;
      lead_id?: string;
      call_status?: string;
      limit?: number;
      skip?: number;
    }) => {
      const q = new URLSearchParams();
      if (params?.campaign_id) q.set("campaign_id", params.campaign_id);
      if (params?.lead_id) q.set("lead_id", params.lead_id);
      if (params?.call_status) q.set("call_status", params.call_status);
      if (params?.limit != null) q.set("limit", String(params.limit));
      if (params?.skip != null) q.set("skip", String(params.skip));
      return apiRequest<Call[]>(
        "GET", `/api/v1/calls${q.toString() ? "?" + q : ""}`
      );
    },
    get: (id: string) => apiRequest<Call>("GET", `/api/v1/calls/${id}`),
    initiate: (body: {
      to_number: string;
      from_number: string;
      campaign_id?: string;
      lead_id?: string;
      agent_id?: string;
      agent_version?: number;
      provider?: string;
      reserve_credits?: number;
    }) => apiRequest<{ call_id: string; status: string }>(
      "POST", "/api/v1/calls/initiate", body
    ),
    getTranscript: (callId: string) =>
      apiRequest<{
        call_id: string;
        status: string;
        turns: Array<{
          id: string;
          role: string;
          text: string;
          stage?: string;
          latency_ms?: number;
          ts?: string;
        }>;
        output_variables?: Record<string, string>;
      }>("GET", `/api/v1/calls/${callId}/transcript`),
    hangup: (callId: string) =>
      apiRequest<{ status: string; call_id: string }>(
        "POST", `/api/v1/calls/${callId}/hangup`
      ),
  },

  // ── Appointments ──────────────────────────────────────────────────────────
  appointments: {
    list: (params?: {
      appt_status?: string;
      appointment_type?: string;
      lead_id?: string;
      limit?: number;
      skip?: number;
    }) => {
      const q = new URLSearchParams();
      if (params?.appt_status) q.set("appt_status", params.appt_status);
      if (params?.appointment_type) q.set("appointment_type", params.appointment_type);
      if (params?.lead_id) q.set("lead_id", params.lead_id);
      if (params?.limit != null) q.set("limit", String(params.limit));
      if (params?.skip != null) q.set("skip", String(params.skip));
      return apiRequest<Appointment[]>(
        "GET", `/api/v1/appointments${q.toString() ? "?" + q : ""}`
      );
    },
    upcoming: (limit?: number) =>
      apiRequest<Appointment[]>(
        "GET", `/api/v1/appointments/upcoming${limit ? "?limit=" + limit : ""}`
      ),
    summary: () =>
      apiRequest<Record<string, unknown>>("GET", "/api/v1/appointments/summary"),
    get: (id: string) =>
      apiRequest<Appointment>("GET", `/api/v1/appointments/${id}`),
    create: (body: {
      scheduled_at: string;
      appointment_type?: string;
      lead_id?: string;
      call_id?: string;
      campaign_id?: string;
      assigned_user_id?: string;
      title?: string;
      description?: string;
      duration_minutes?: number;
      timezone?: string;
      location?: string;
      location_type?: string;
      notes?: string;
      custom_fields?: Record<string, unknown>;
    }) => apiRequest<Appointment>("POST", "/api/v1/appointments", body),
    update: (id: string, body: Partial<Appointment>) =>
      apiRequest<Appointment>("PATCH", `/api/v1/appointments/${id}`, body),
    confirm: (id: string) =>
      apiRequest<Appointment>("POST", `/api/v1/appointments/${id}/confirm`),
    complete: (id: string, outcome_notes?: string) =>
      apiRequest<Appointment>(
        "POST", `/api/v1/appointments/${id}/complete`,
        { outcome_notes }
      ),
    cancel: (id: string, reason?: string) =>
      apiRequest<Appointment>(
        "POST", `/api/v1/appointments/${id}/cancel`, { reason }
      ),
    noShow: (id: string) =>
      apiRequest<Appointment>(
        "POST", `/api/v1/appointments/${id}/no-show`
      ),
    reschedule: (id: string, scheduled_at: string, notes?: string) =>
      apiRequest<Appointment>(
        "POST", `/api/v1/appointments/${id}/reschedule`,
        { scheduled_at, notes }
      ),
  },

  // ── Wallet / Credits ──────────────────────────────────────────────────────
  wallet: {
    summary: () => apiRequest<WalletSummary>("GET", "/api/v1/wallet"),
    transactions: (params?: { limit?: number; skip?: number; txn_type?: string }) => {
      const q = new URLSearchParams();
      if (params?.limit != null) q.set("limit", String(params.limit));
      if (params?.skip != null) q.set("skip", String(params.skip));
      if (params?.txn_type) q.set("txn_type", params.txn_type);
      return apiRequest<Transaction[]>(
        "GET", `/api/v1/wallet/transactions${q.toString() ? "?" + q : ""}`
      );
    },
    lots: () => apiRequest<CreditLot[]>("GET", "/api/v1/wallet/lots"),
    packs: () => apiRequest<CallingPack[]>("GET", "/api/v1/wallet/packs"),
    getPack: (idOrSlug: string) =>
      apiRequest<CallingPack>("GET", `/api/v1/wallet/packs/${idOrSlug}`),
    orderPack: (packId: string) =>
      apiRequest<{ order_id: string; provider_order_id: string; amount_paise: number }>(
        "POST", `/api/v1/wallet/packs/${packId}/order`
      ),
  },

  // ── Billing ───────────────────────────────────────────────────────────────
  billing: {
    createSubscriptionOrder: (plan_id: string, billing_cycle: "monthly" | "yearly") =>
      apiRequest<{ order_id: string; provider_order_id: string; amount_paise: number }>(
        "POST", "/api/v1/billing/orders/subscription", { plan_id, billing_cycle }
      ),
    verifyPayment: (body: {
      order_id: string;
      provider_payment_id: string;
      provider_order_id: string;
      provider_signature: string;
    }) => apiRequest<{ status: string }>("POST", "/api/v1/billing/verify", body),
    orders: (params?: { limit?: number; skip?: number }) => {
      const q = new URLSearchParams();
      if (params?.limit != null) q.set("limit", String(params.limit));
      if (params?.skip != null) q.set("skip", String(params.skip));
      return apiRequest<Order[]>(
        "GET", `/api/v1/billing/orders${q.toString() ? "?" + q : ""}`
      );
    },
    payments: (params?: { limit?: number; skip?: number }) => {
      const q = new URLSearchParams();
      if (params?.limit != null) q.set("limit", String(params.limit));
      if (params?.skip != null) q.set("skip", String(params.skip));
      return apiRequest<Payment[]>(
        "GET", `/api/v1/billing/payments${q.toString() ? "?" + q : ""}`
      );
    },
    invoices: (params?: { limit?: number; skip?: number }) => {
      const q = new URLSearchParams();
      if (params?.limit != null) q.set("limit", String(params.limit));
      if (params?.skip != null) q.set("skip", String(params.skip));
      return apiRequest<Invoice[]>(
        "GET", `/api/v1/billing/invoices${q.toString() ? "?" + q : ""}`
      );
    },
    getInvoice: (id: string) =>
      apiRequest<Invoice>("GET", `/api/v1/billing/invoices/${id}`),
  },

  // ── Subscriptions ─────────────────────────────────────────────────────────
  subscriptions: {
    plans: () => apiRequest<SubscriptionPlan[]>("GET", "/api/v1/subscriptions/plans"),
    getPlan: (slug: string) =>
      apiRequest<SubscriptionPlan>("GET", `/api/v1/subscriptions/plans/${slug}`),
    my: () => apiRequest<Subscription>("GET", "/api/v1/subscriptions/my"),
    myEntitlements: () =>
      apiRequest<Entitlements>("GET", "/api/v1/subscriptions/my/entitlements"),
    cancel: (at_period_end?: boolean) =>
      apiRequest<{ status: string; cancel_at_period_end: boolean; current_period_end: string | null }>(
        "POST",
        `/api/v1/subscriptions/my/cancel${at_period_end === false ? "?at_period_end=false" : ""}`
      ),
    changePlan: (plan_id: string, billing_cycle: "monthly" | "yearly") =>
      apiRequest<Subscription>(
        "POST", "/api/v1/subscriptions/my/change", { plan_id, billing_cycle }
      ),
  },

  // ── Voice Profiles ────────────────────────────────────────────────────────
  voiceProfiles: {
    list: () =>
      apiRequest<VoiceProfile[]>("GET", "/api/v1/voice-profiles"),
    get: (id: string) =>
      apiRequest<VoiceProfile>("GET", `/api/v1/voice-profiles/${id}`),
  },

  // ── Phone Numbers ─────────────────────────────────────────────────────────
  phoneNumbers: {
    myNumbers: () =>
      apiRequest<PhoneNumber[]>("GET", "/api/v1/phone-numbers/my"),
    available: () =>
      apiRequest<PhoneNumber[]>("GET", "/api/v1/phone-numbers/available"),
    // Admin operations
    addAdmin: (body: {
      number: string;
      provider: string;
      provider_resource_id?: string;
      display_name?: string;
      country_code?: string;
      number_type?: string;
      rental_paise_per_month?: number;
      provider_metadata?: Record<string, unknown>;
    }) => apiRequest<PhoneNumber>("POST", "/api/v1/phone-numbers/admin", body),
    assign: (
      phoneNumberId: string,
      payload:
        | {
            organization_id?: string;
            org_ids?: string[];
            inbound_organization_id?: string;
            inbound_agent_id?: string;
          }
        | string
    ) => {
      const body = typeof payload === "string" ? { organization_id: payload } : payload;
      return apiRequest<PhoneNumber>(
        "POST",
        `/api/v1/phone-numbers/admin/${phoneNumberId}/assign`,
        body
      );
    },
    release: (phoneNumberId: string) =>
      apiRequest<PhoneNumber>(
        "POST", `/api/v1/phone-numbers/admin/${phoneNumberId}/release`
      ),
    suspend: (phoneNumberId: string) =>
      apiRequest<PhoneNumber>(
        "POST", `/api/v1/phone-numbers/admin/${phoneNumberId}/suspend`
      ),
    reactivate: (phoneNumberId: string) =>
      apiRequest<PhoneNumber>(
        "POST", `/api/v1/phone-numbers/admin/${phoneNumberId}/reactivate`
      ),
  },

  // ── Knowledge Base ────────────────────────────────────────────────────────
  knowledge: {
    list: () =>
      apiRequest<KnowledgeBase[]>("GET", "/api/v1/knowledge"),
    get: (id: string) =>
      apiRequest<KnowledgeBase>("GET", `/api/v1/knowledge/${id}`),
    create: (name: string, description?: string, tags?: string[]) =>
      apiRequest<KnowledgeBase>("POST", "/api/v1/knowledge", { name, description: description ?? "", tags }),
    deleteKb: (id: string) =>
      apiRequest<void>("DELETE", `/api/v1/knowledge/${id}`),
    listDocuments: (kbId: string, params?: { limit?: number; skip?: number }) => {
      const q = new URLSearchParams();
      if (params?.limit != null) q.set("limit", String(params.limit));
      if (params?.skip != null) q.set("skip", String(params.skip));
      return apiRequest<KnowledgeDocument[]>(
        "GET", `/api/v1/knowledge/${kbId}/documents${q.toString() ? "?" + q : ""}`
      );
    },
    addDocument: (kbId: string, title: string, content: string, document_type?: string, keywords?: string[], tags?: string[]) =>
      apiRequest<KnowledgeDocument>("POST", `/api/v1/knowledge/${kbId}/documents`, {
        title, content, document_type: document_type ?? "general", keywords, tags,
      }),
    deleteDocument: (kbId: string, docId: string) =>
      apiRequest<void>("DELETE", `/api/v1/knowledge/${kbId}/documents/${docId}`),
    search: (query: string, knowledge_base_ids?: string[], limit?: number) =>
      apiRequest<KnowledgeDocument[]>("POST", "/api/v1/knowledge/search", { query, knowledge_base_ids, limit }),
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
    getContext: (agentId: string, query?: string) =>
      apiRequest<{ agent_id: string; context: string; char_count: number }>(
        "GET",
        `/api/v1/knowledge/context/${agentId}${query ? `?query=${encodeURIComponent(query)}` : ""}`
      ),
  },

  // ── Users / Team ──────────────────────────────────────────────────────────
  users: {
    listOrg: (orgId: string) =>
      apiRequest<User[]>("GET", `/api/v1/users/org/${orgId}`),
    invite: (orgId: string, body: { email: string; password: string; role: string; first_name?: string; last_name?: string }) =>
      apiRequest<User>("POST", `/api/v1/users/org/${orgId}/invite`, body),
    get: (userId: string) =>
      apiRequest<User>("GET", `/api/v1/users/${userId}`),
    update: (userId: string, body: { first_name?: string; last_name?: string; role?: string }) =>
      apiRequest<User>("PATCH", `/api/v1/users/${userId}`, body),
    deactivate: (userId: string) =>
      apiRequest<{ status: string; user_id: string }>("DELETE", `/api/v1/users/${userId}`),
  },

  // ── Dashboard ─────────────────────────────────────────────────────────────
  dashboard: {
    summary: () => apiRequest<DashboardData>("GET", "/api/v1/dashboard"),
    calls: (days?: number) =>
      apiRequest<DashboardData["calls"] & { period_days: number }>(
        "GET", `/api/v1/dashboard/calls${days ? "?days=" + days : ""}`
      ),
    campaigns: () =>
      apiRequest<DashboardData["campaigns"]>("GET", "/api/v1/dashboard/campaigns"),
    leads: () =>
      apiRequest<DashboardData["leads"]>("GET", "/api/v1/dashboard/leads"),
    credits: () =>
      apiRequest<DashboardData["credits"]>("GET", "/api/v1/dashboard/credits"),
    appointments: (limit?: number) =>
      apiRequest<{ upcoming: DashboardData["upcoming_appointments"]; count: number }>(
        "GET", `/api/v1/dashboard/appointments${limit ? "?limit=" + limit : ""}`
      ),
    analytics: (days?: number) =>
      apiRequest<{
        period_days: number;
        daily: Array<{ date: string; calls_total: number; calls_qualified: number; credits_consumed: number }>;
        totals: { calls: number; qualified: number; qualified_rate_pct: number; credits_consumed: number };
      }>(
        "GET", `/api/v1/dashboard/analytics${days ? "?days=" + days : ""}`
      ),
  },

  // ── Admin ─────────────────────────────────────────────────────────────────
  admin: {
    dashboard: () => apiRequest<AdminDashboard>("GET", "/api/v1/admin/dashboard"),
    organizations: {
      list: (params?: { org_status?: string; limit?: number; skip?: number }) => {
        const q = new URLSearchParams();
        if (params?.org_status) q.set("org_status", params.org_status);
        if (params?.limit != null) q.set("limit", String(params.limit));
        if (params?.skip != null) q.set("skip", String(params.skip));
        return apiRequest<Organization[]>(
          "GET", `/api/v1/admin/organizations${q.toString() ? "?" + q : ""}`
        );
      },
      get: (id: string) =>
        apiRequest<Organization>("GET", `/api/v1/admin/organizations/${id}`),
      suspend: (id: string, reason?: string) =>
        apiRequest<{ status: string; org_id: string }>(
          "POST",
          `/api/v1/admin/organizations/${id}/suspend${reason ? "?reason=" + encodeURIComponent(reason) : ""}`
        ),
      reactivate: (id: string) =>
        apiRequest<{ status: string; org_id: string }>(
          "POST", `/api/v1/admin/organizations/${id}/reactivate`
        ),
    },
    subscriptions: {
      list: (params?: { sub_status?: string; limit?: number; skip?: number }) => {
        const q = new URLSearchParams();
        if (params?.sub_status) q.set("sub_status", params.sub_status);
        if (params?.limit != null) q.set("limit", String(params.limit));
        if (params?.skip != null) q.set("skip", String(params.skip));
        return apiRequest<Subscription[]>(
          "GET", `/api/v1/admin/subscriptions${q.toString() ? "?" + q : ""}`
        );
      },
      plans: {
        list: (include_inactive?: boolean) =>
          apiRequest<SubscriptionPlan[]>(
            "GET",
            `/api/v1/admin/plans${include_inactive ? "?include_inactive=true" : ""}`
          ),
        update: (planId: string, updates: Partial<SubscriptionPlan>) =>
          apiRequest<SubscriptionPlan>(
            "PATCH", `/api/v1/admin/plans/${planId}`, updates
          ),
      },
      activate: (orgId: string, body: { plan_id: string; billing_cycle: string; payment_id?: string }) =>
        apiRequest<Subscription>(
          "POST", `/api/v1/subscriptions/admin/orgs/${orgId}/activate`, body
        ),
    },
    callingPacks: {
      list: (include_inactive?: boolean) =>
        apiRequest<CallingPack[]>(
          "GET",
          `/api/v1/admin/calling-packs${include_inactive ? "?include_inactive=true" : ""}`
        ),
      create: (body: {
        name: string; slug: string; credits: number; price_paise: number;
        description?: string; validity_days?: number; bonus_credits?: number;
        is_public?: boolean; sort_order?: number;
      }) => apiRequest<CallingPack>("POST", "/api/v1/wallet/admin/packs", body),
      update: (packId: string, updates: Partial<CallingPack>) =>
        apiRequest<CallingPack>("PATCH", `/api/v1/wallet/admin/packs/${packId}`, updates),
    },
    payments: {
      list: (params?: { org_id?: string; limit?: number; skip?: number }) => {
        const q = new URLSearchParams();
        if (params?.org_id) q.set("org_id", params.org_id);
        if (params?.limit != null) q.set("limit", String(params.limit));
        if (params?.skip != null) q.set("skip", String(params.skip));
        return apiRequest<Payment[]>(
          "GET", `/api/v1/admin/payments${q.toString() ? "?" + q : ""}`
        );
      },
      refund: (paymentId: string, body: { amount_paise?: number; reason?: string }) =>
        apiRequest<{ status: string }>(
          "POST", `/api/v1/billing/refund/${paymentId}`, body
        ),
    },
    invoices: {
      list: (params?: { org_id?: string; limit?: number; skip?: number }) => {
        const q = new URLSearchParams();
        if (params?.org_id) q.set("org_id", params.org_id);
        if (params?.limit != null) q.set("limit", String(params.limit));
        if (params?.skip != null) q.set("skip", String(params.skip));
        return apiRequest<Invoice[]>(
          "GET", `/api/v1/admin/invoices${q.toString() ? "?" + q : ""}`
        );
      },
    },
    phoneNumbers: {
      list: (params?: { pn_status?: string; provider?: string; limit?: number; skip?: number }) => {
        const q = new URLSearchParams();
        if (params?.pn_status) q.set("pn_status", params.pn_status);
        if (params?.provider) q.set("provider", params.provider);
        if (params?.limit != null) q.set("limit", String(params.limit));
        if (params?.skip != null) q.set("skip", String(params.skip));
        return apiRequest<PhoneNumber[]>(
          "GET", `/api/v1/admin/phone-numbers${q.toString() ? "?" + q : ""}`
        );
      },
      stats: () =>
        apiRequest<Record<string, unknown>>(
          "GET", "/api/v1/admin/phone-numbers/stats"
        ),
    },
    voiceProfiles: {
      list: () =>
        apiRequest<VoiceProfile[]>("GET", "/api/v1/admin/voice-profiles"),
      create: (body: {
        display_name: string;
        language: string;
        organization_id?: string;
        is_platform?: boolean;
      }) => apiRequest<VoiceProfile>("POST", "/api/v1/voice-profiles/admin", body),
      createVersion: (profileId: string, routes: Record<string, unknown>) =>
        apiRequest<{ id: string; version: number; status: string }>(
          "POST", `/api/v1/voice-profiles/admin/${profileId}/versions`, { routes }
        ),
    },
    wallets: {
      get: (orgId: string) =>
        apiRequest<WalletSummary>("GET", `/api/v1/admin/wallets/${orgId}`),
      adjust: (orgId: string, credits_delta: number, reason: string) =>
        apiRequest<{ status: string }>(
          "POST",
          `/api/v1/admin/wallets/${orgId}/adjust?credits_delta=${credits_delta}&reason=${encodeURIComponent(reason)}`
        ),
    },
    usage: (params?: { org_id?: string; from_date?: string; to_date?: string }) => {
      const q = new URLSearchParams();
      if (params?.org_id) q.set("org_id", params.org_id);
      if (params?.from_date) q.set("from_date", params.from_date);
      if (params?.to_date) q.set("to_date", params.to_date);
      return apiRequest<Record<string, unknown>>(
        "GET", `/api/v1/admin/usage${q.toString() ? "?" + q : ""}`
      );
    },
    revenue: (params?: { from_date?: string; to_date?: string }) => {
      const q = new URLSearchParams();
      if (params?.from_date) q.set("from_date", params.from_date);
      if (params?.to_date) q.set("to_date", params.to_date);
      return apiRequest<{
        subscription_revenue_paise: number;
        subscription_revenue_inr: number;
        calling_revenue_paise: number;
        calling_revenue_inr: number;
        total_revenue_paise: number;
        total_revenue_inr: number;
      }>("GET", `/api/v1/admin/revenue${q.toString() ? "?" + q : ""}`);
    },
    auditLogs: (params?: { org_id?: string; limit?: number; skip?: number }) => {
      const q = new URLSearchParams();
      if (params?.org_id) q.set("org_id", params.org_id);
      if (params?.limit != null) q.set("limit", String(params.limit));
      if (params?.skip != null) q.set("skip", String(params.skip));
      return apiRequest<Array<{
        id: string;
        action: string;
        organization_id: string | null;
        user_email: string | null;
        user_role: string | null;
        resource_type: string | null;
        resource_id: string | null;
        status: string;
        ip_address: string | null;
        created_at: string;
      }>>("GET", `/api/v1/admin/audit-logs${q.toString() ? "?" + q : ""}`);
    },
    systemHealth: () =>
      apiRequest<Record<string, unknown>>("GET", "/api/v1/admin/system-health"),

    costs: (params?: { from_date?: string; to_date?: string }) => {
      const q = new URLSearchParams();
      if (params?.from_date) q.set("from_date", params.from_date);
      if (params?.to_date) q.set("to_date", params.to_date);
      return apiRequest<{
        total_provider_cost_paise: number;
        total_provider_cost_inr: number;
        provider_breakdown: Record<string, unknown>;
      }>("GET", `/api/v1/admin/costs${q.toString() ? "?" + q : ""}`);
    },

    margins: (params?: { org_id?: string; from_date?: string; to_date?: string }) => {
      const q = new URLSearchParams();
      if (params?.org_id) q.set("org_id", params.org_id);
      if (params?.from_date) q.set("from_date", params.from_date);
      if (params?.to_date) q.set("to_date", params.to_date);
      return apiRequest<Record<string, unknown>>(
        "GET", `/api/v1/admin/margins${q.toString() ? "?" + q : ""}`
      );
    },

    grantBonus: (body: { organization_id: string; credits: number; description: string; validity_days?: number }) =>
      apiRequest<{ status: string }>("POST", "/api/v1/wallet/admin/bonus", body),
  },

  // ── Analytics (admin) ─────────────────────────────────────────────────────
  analytics: {
    mrr: () =>
      apiRequest<{
        mrr_paise: number; mrr_inr: number;
        arr_paise: number; arr_inr: number;
        arpu_paise: number; arpu_inr: number;
        active_subscriptions: number;
      }>("GET", "/api/v1/analytics/mrr"),

    mrrMovement: (from_date?: string, to_date?: string) => {
      const q = new URLSearchParams();
      if (from_date) q.set("from_date", from_date);
      if (to_date) q.set("to_date", to_date);
      return apiRequest<{
        new_mrr_paise: number;
        expansion_mrr_paise: number;
        churn_mrr_paise: number;
        net_new_mrr_paise: number;
        [key: string]: unknown;
      }>("GET", `/api/v1/analytics/mrr-movement${q.toString() ? "?" + q : ""}`);
    },

    revenue: (from_date?: string, to_date?: string) => {
      const q = new URLSearchParams();
      if (from_date) q.set("from_date", from_date);
      if (to_date) q.set("to_date", to_date);
      return apiRequest<{
        subscription_revenue_paise: number;
        calling_revenue_paise: number;
        total_revenue_paise: number;
        provider_cost_paise: number;
        gross_profit_paise: number;
        gross_margin_pct: number;
        [key: string]: unknown;
      }>("GET", `/api/v1/analytics/revenue${q.toString() ? "?" + q : ""}`);
    },

    daily: (days?: number, organization_id?: string) => {
      const q = new URLSearchParams();
      if (days) q.set("days", String(days));
      if (organization_id) q.set("organization_id", organization_id);
      return apiRequest<{
        days: number;
        data: Array<{
          date: string;
          calls: number;
          credits_consumed: number;
          revenue_paise: number;
          provider_cost_paise: number;
        }>;
      }>("GET", `/api/v1/analytics/daily${q.toString() ? "?" + q : ""}`);
    },

    arpu: () =>
      apiRequest<{ arpu_paise: number; arpu_inr: number; active_orgs: number }>(
        "GET", "/api/v1/analytics/arpu"
      ),
  },

  // ── Provider Operations (admin) ───────────────────────────────────────────
  providerOps: {
    health: (hours?: number) =>
      apiRequest<{
        overall_status: string;
        providers: Array<{
          provider: string;
          provider_type: string;
          status: string;
          success_rate: number;
          call_count: number;
          avg_latency_ms: number;
          [key: string]: unknown;
        }>;
        [key: string]: unknown;
      }>("GET", `/api/v1/provider-ops/health${hours ? "?hours=" + hours : ""}`),

    metrics: (hours?: number, provider_type?: string) => {
      const q = new URLSearchParams();
      if (hours) q.set("hours", String(hours));
      if (provider_type) q.set("provider_type", provider_type);
      return apiRequest<Array<{
        provider: string;
        provider_type: string;
        success_rate: number;
        avg_latency_ms: number;
        call_count: number;
        total_cost_paise: number;
        [key: string]: unknown;
      }>>("GET", `/api/v1/provider-ops/metrics${q.toString() ? "?" + q : ""}`);
    },

    latency: (hours?: number) =>
      apiRequest<{
        avg_latency_ms: number;
        p50_ms: number;
        p95_ms: number;
        p99_ms: number;
        [key: string]: unknown;
      }>("GET", `/api/v1/provider-ops/latency${hours ? "?hours=" + hours : ""}`),

    voiceProfiles: () =>
      apiRequest<Array<{
        profile_id: string;
        display_name: string;
        status: string;
        [key: string]: unknown;
      }>>("GET", "/api/v1/provider-ops/voice-profiles"),
  },

  // ── Reconciliation (admin) ────────────────────────────────────────────────
  reconciliation: {
    run: (hours?: number) =>
      apiRequest<{
        checks: Array<{
          check_name: string;
          status: string;
          issues_found: number;
          details: string;
          [key: string]: unknown;
        }>;
        total_issues: number;
        run_at: string;
        [key: string]: unknown;
      }>("GET", `/api/v1/reconciliation/run${hours ? "?hours=" + hours : ""}`),
  },

  // ── Transcripts ───────────────────────────────────────────────────────────
  transcripts: {
    get: (callId: string) =>
      apiRequest<{
        call_id: string;
        turns: Array<{
          role: string;
          text: string;
          stage: string | null;
          latency_ms: number | null;
          ts: string | null;
        }>;
      }>("GET", `/api/v1/transcripts/${callId}`),
  },

  // ── Model Directory (admin) ───────────────────────────────────────────────
  modelDirectory: {
    wizardStatus: () =>
      apiRequest<WizardStatusResponse>("GET", "/api/v1/model-directory/wizard-status"),
    catalogue: (params?: { capability?: string; status?: string; search?: string }) => {
      const q = new URLSearchParams();
      if (params?.capability) q.set("capability", params.capability);
      if (params?.status) q.set("status", params.status);
      if (params?.search) q.set("search", params.search);
      return apiRequest<AIModelCatalogue[]>(
        "GET", `/api/v1/model-directory/catalogue${q.toString() ? "?" + q : ""}`
      );
    },
    getModel: (providerName: string, modelId: string) =>
      apiRequest<AIModelCatalogue>(
        "GET",
        `/api/v1/model-directory/catalogue/${encodeURIComponent(providerName)}/${encodeURIComponent(modelId)}`
      ),
    listConfigs: (capability?: string) => {
      const q = new URLSearchParams();
      if (capability) q.set("capability", capability);
      return apiRequest<ProviderConfiguration[]>(
        "GET", `/api/v1/model-directory/configurations${q.toString() ? "?" + q : ""}`
      );
    },
    getConfig: (configId: string) =>
      apiRequest<ProviderConfiguration>(
        "GET", `/api/v1/model-directory/configurations/${configId}`
      ),
    connect: (body: ConnectProviderRequest) =>
      apiRequest<ProviderConfiguration>(
        "POST", "/api/v1/model-directory/configurations", body
      ),
    testConfig: (configId: string) =>
      apiRequest<TestResult>(
        "POST", `/api/v1/model-directory/configurations/${configId}/test`
      ),
    activateConfig: (configId: string) =>
      apiRequest<ProviderConfiguration>(
        "POST", `/api/v1/model-directory/configurations/${configId}/activate`
      ),
    setFallback: (configId: string, fallbackConfigId: string) =>
      apiRequest<ProviderConfiguration>(
        "POST", `/api/v1/model-directory/configurations/${configId}/fallback`,
        { fallback_config_id: fallbackConfigId }
      ),
    deleteConfig: (configId: string) =>
      apiRequest<void>(
        "DELETE", `/api/v1/model-directory/configurations/${configId}`
      ),
    listCredentials: (providerName: string) =>
      apiRequest<ProviderCredentialMeta[]>(
        "GET", `/api/v1/model-directory/credentials/${encodeURIComponent(providerName)}`
      ),
    rotateCredential: (providerName: string, newPlaintext: string) =>
      apiRequest<ProviderCredentialMeta>(
        "POST",
        `/api/v1/model-directory/credentials/${encodeURIComponent(providerName)}/rotate`,
        { new_plaintext: newPlaintext }
      ),
    deleteCredential: (providerName: string) =>
      apiRequest<void>(
        "DELETE", `/api/v1/model-directory/credentials/${encodeURIComponent(providerName)}`
      ),
    testAgentInfo: () =>
      apiRequest<TestAgentInfoResponse>(
        "GET", "/api/v1/model-directory/test-agent/info"
      ),
    testChat: (body: {
      message: string;
      history?: Array<{ role: string; content: string }>;
      system_prompt?: string;
      language?: string;
    }) =>
      apiRequest<TestChatResponse>(
        "POST", "/api/v1/model-directory/test-chat", body
      ),
  },
  pricing: {
    rates: () => apiRequest<PricingRatesResponse>("GET", "/api/v1/pricing/rates"),
    pipelineCost: (params: Record<string, string | number | undefined>) => {
      const sp = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) sp.append(k, String(v));
      });
      return apiRequest<PipelineCostResponse>("GET", `/api/v1/pricing/pipeline-cost?${sp.toString()}`);
    },
    sync: (body?: { force_fx_rate?: number; force_safety_margin_pct?: number }) =>
      apiRequest<{ status: string; synced_count: number; usd_to_inr_fx_rate: number; safety_margin_pct: number; synced_at: string }>(
        "POST",
        "/api/v1/pricing/sync",
        body
      ),
    override: (body: {
      capability: string;
      provider_name: string;
      model_id: string;
      base_unit_rate: number;
      safety_margin_pct?: number;
      notes?: string;
    }) => apiRequest<{ status: string; card: ProviderRateCard }>("POST", "/api/v1/pricing/override", body),
  },
};

export interface ProviderRateCard {
  id: string;
  provider_name: string;
  model_id: string;
  capability: "stt" | "llm" | "tts" | "telephony";
  display_name: string;
  base_currency: "INR" | "USD";
  billing_unit: string;
  base_unit_rate: number;
  fx_rate_usd_inr: number;
  effective_unit_rate_inr: number;
  active_cost_per_sec_inr: number;
  blended_cost_per_sec_inr: number;
  safety_margin_pct: number;
  retail_rate_per_sec_inr: number;
  last_synced_at: string;
  sync_source: string;
  notes?: string | null;
}

export interface PricingSettings {
  id: string;
  usd_to_inr_fx_rate: number;
  fx_last_updated_at: string;
  default_safety_margin_pct: number;
  min_retail_paise_per_sec: number;
  auto_sync_enabled: boolean;
  last_daily_sync_at: string | null;
}

export interface PricingRatesResponse {
  settings: PricingSettings;
  rates_by_capability: {
    stt: ProviderRateCard[];
    llm: ProviderRateCard[];
    tts: ProviderRateCard[];
    telephony: ProviderRateCard[];
  };
  total_providers_tracked: number;
  last_synced_at: string | null;
}

export interface PipelineCostResponse {
  components: {
    stt: { provider: string; model: string; blended_cost_per_sec_inr: number; paise_per_sec: number };
    llm: { provider: string; model: string; blended_cost_per_sec_inr: number; paise_per_sec: number };
    tts: { provider: string; model: string; blended_cost_per_sec_inr: number; paise_per_sec: number };
    telephony: { provider: string; blended_cost_per_sec_inr: number; paise_per_sec: number };
  };
  raw_provider_cost_per_sec_inr: number;
  raw_provider_cost_per_min_inr: number;
  raw_provider_paise_per_sec: number;
  safety_margin_pct: number;
  safety_buffer_paise_per_sec: number;
  retail_billable_rate_per_sec_inr: number;
  retail_billable_rate_per_min_inr: number;
  retail_billable_paise_per_sec: number;
  projections: {
    one_minute_call_inr: number;
    three_minute_call_inr: number;
    thousand_calls_one_min_inr: number;
  };
  fx_usd_to_inr: number;
  last_synced_at: string | null;
}

export interface TestAgentScenario {
  id: string;
  name: string;
  agent_name: string;
  language: string;
  greeting: string;
  system_prompt: string;
  input_variables?: Record<string, string>;
  output_variables?: string[];
}

export interface TestAgentInfoResponse {
  all_ready: boolean;
  pipeline: {
    stt: ProviderConfiguration | null;
    llm: ProviderConfiguration | null;
    tts: ProviderConfiguration | null;
  };
  languages: Array<{ code: string; name: string; native: string }>;
  default_scenarios: TestAgentScenario[];
}

export interface TestChatResponse {
  reply: string;
  latency_ms: number;
  provider_name: string;
  model_id: string;
}

// Legacy re-export for backward compat during migration
export const API_BASE_URL = BASE_URL;
