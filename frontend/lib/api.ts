const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Stats = {
  total_calls: number;
  total_leads: number;
  booked: number;
  qualified: number;
  avg_score: number;
  avg_latency_ms: number | null;
  outcomes: Record<string, number>;
};

export type CallRow = {
  id: string;
  direction: string;
  status: string;
  outcome: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_s: number | null;
  avg_latency_ms: number | null;
  lead_city: string | null;
  lead_budget: string | null;
  lead_score: number | null;
  lead_status: string | null;
};

export type Turn = {
  role: string;
  text: string;
  stage: string | null;
  latency_ms: number | null;
  ts: string | null;
};

export type CallDetail = {
  id: string;
  direction: string;
  status: string;
  outcome: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_s: number | null;
  avg_latency_ms: number | null;
  turns: Turn[];
};

export type Lead = {
  id: string;
  phone: string | null;
  city: string | null;
  budget: string | null;
  timeline: string | null;
  property_type: string | null;
  score: number;
  status: string;
  created_at: string | null;
};

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export type OutboundResult = {
  status?: string;
  call_sid?: string;
  to?: string;
  error?: string;
};

export const API_BASE_URL = API_BASE;

/** ws:// base derived from the API base, for the browser test call. */
export function wsBase(): string {
  return API_BASE.replace(/^http/, "ws");
}

export type Language = { code: string; name: string; native: string };
export type LanguagesResp = { default: string; languages: Language[] };

export const api = {
  stats: () => get<Stats>("/api/stats"),
  calls: (limit = 50) => get<CallRow[]>(`/api/calls?limit=${limit}`),
  call: (id: string) => get<CallDetail>(`/api/calls/${id}`),
  leads: (limit = 100) => get<Lead[]>(`/api/leads?limit=${limit}`),
  languages: () => get<LanguagesResp>("/api/languages"),
  placeOutbound: async (to: string, lang: string): Promise<OutboundResult> => {
    const res = await fetch(`${API_BASE}/calls/outbound`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ to, lang }).toString(),
    });
    return res.json() as Promise<OutboundResult>;
  },
};
