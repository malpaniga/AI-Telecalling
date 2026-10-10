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
  slot_definitions: Record<string, unknown>;
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
  kb_id: string;
  title: string;
  content_type: string;
  status: string;
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
      voice_profile_id: string;
      voice_profile_version: number;
      description?: string;
    }) => apiRequest<Agent>("POST", "/api/v1/agents", body),
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
  },

  // ── Knowledge Base ────────────────────────────────────────────────────────
  knowledge: {
    list: () =>
      apiRequest<KnowledgeBase[]>("GET", "/api/v1/knowledge"),
    get: (id: string) =>
      apiRequest<KnowledgeBase>("GET", `/api/v1/knowledge/${id}`),
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
  },
};

// Legacy re-export for backward compat during migration
export const API_BASE_URL = BASE_URL;
