# API-to-UI Mapping — Super Admin Dashboard

Generated from backend audit of `backend/api/v1/` and frontend routes as of commit `42010f3` + FEAT-005A additions.

---

## Dashboard

| UI Page | Endpoint | Method | Required Role | Request Params | Response Shape | Notes |
|---------|----------|--------|---------------|----------------|----------------|-------|
| `/admin/dashboard` | `/api/v1/admin/dashboard` | GET | platform_* | — | `{ organizations: { total_active, recent[] }, subscriptions: { total, active, by_status }, usage: { total_events, total_credits, total_charge_paise, gross_profit_paise } }` | Platform overview |

---

## Organizations

| UI Page | Endpoint | Method | Required Role | Request Params | Response Shape | Notes |
|---------|----------|--------|---------------|----------------|----------------|-------|
| `/admin/organizations` | `/api/v1/admin/organizations` | GET | platform_* | `org_status, limit, skip` | `Organization[]` | Paginated list |
| `/admin/organizations/[id]` | `/api/v1/admin/organizations/{id}` | GET | platform_* | — | `Organization` | Full org detail |
| `/admin/organizations/[id]` | `/api/v1/admin/organizations/{id}/suspend` | POST | platform_* | `?reason=` | `{ status, org_id }` | Confirm dialog required |
| `/admin/organizations/[id]` | `/api/v1/admin/organizations/{id}/reactivate` | POST | platform_* | — | `{ status, org_id }` | — |
| `/admin/organizations/[id]` (Wallet tab) | `/api/v1/admin/wallets/{org_id}` | GET | platform_* | — | `WalletSummary` | Available/reserved/consumed |
| `/admin/organizations/[id]` (Wallet tab) | `/api/v1/admin/wallets/{org_id}/adjust` | POST | platform_* | `?credits_delta=&reason=` | `{ status }` | Ledger adjustment, confirm dialog |
| `/admin/organizations/[id]` (Users tab) | `/api/v1/users/org/{org_id}` | GET | platform_* | — | `User[]` | Uses existing user endpoint |
| `/admin/organizations/[id]` (Subscription tab) | `/api/v1/admin/subscriptions` | GET | platform_* | `limit=10` | `Subscription[]` | Filter client-side by org_id |

---

## Subscriptions & Plans

| UI Page | Endpoint | Method | Required Role | Request Params | Response Shape | Notes |
|---------|----------|--------|---------------|----------------|----------------|-------|
| `/admin/subscriptions` (Subs tab) | `/api/v1/admin/subscriptions` | GET | platform_* | `sub_status, limit, skip` | `Subscription[]` | — |
| `/admin/subscriptions` (Plans tab) | `/api/v1/admin/plans` | GET | platform_* | `include_inactive=true` | `SubscriptionPlan[]` | — |
| `/admin/subscriptions` (Plans tab) | `/api/v1/admin/plans/{plan_id}` | PATCH | platform_* | JSON body updates | `SubscriptionPlan` | Edit modal |
| `/admin/subscriptions` | `/api/v1/subscriptions/admin/orgs/{org_id}/activate` | POST | platform_* | `{ plan_id, billing_cycle, payment_id? }` | `Subscription` | MISSING from UI — not yet built |

---

## Calling Packs & Credits

| UI Page | Endpoint | Method | Required Role | Request Params | Response Shape | Notes |
|---------|----------|--------|---------------|----------------|----------------|-------|
| `/admin/calling-packs` | `/api/v1/admin/calling-packs` | GET | platform_* | `include_inactive=true` | `CallingPack[]` | — |
| `/admin/calling-packs` | `/api/v1/wallet/admin/packs` | POST | platform_* | Pack body | `CallingPack` | Create modal |
| `/admin/calling-packs` | `/api/v1/wallet/admin/packs/{id}` | PATCH | platform_* | Updates | `CallingPack` | MISSING from UI — edit not wired |
| `/admin/calling-packs` | `/api/v1/wallet/admin/bonus` | POST | platform_* | `{ organization_id, credits, description, validity_days }` | `{ status }` | Grant bonus modal |
| `/admin/calling-packs` | `/api/v1/admin/wallets/{org_id}/adjust` | POST | platform_* | `?credits_delta=&reason=` | `{ status }` | Adjust credits modal |
| — | `/api/v1/wallet/admin/expire` | POST | platform_* | — | — | MISSING from UI — expire old lots |

---

## Payments & Invoices

| UI Page | Endpoint | Method | Required Role | Request Params | Response Shape | Notes |
|---------|----------|--------|---------------|----------------|----------------|-------|
| `/admin/payments` (Payments tab) | `/api/v1/admin/payments` | GET | platform_* | `org_id?, limit, skip` | `Payment[]` | — |
| `/admin/payments` (Invoices tab) | `/api/v1/admin/invoices` | GET | platform_* | `org_id?, limit, skip` | `Invoice[]` | — |
| `/admin/payments` | `/api/v1/billing/refund/{payment_id}` | POST | billing_admin/platform_owner | `{ amount_paise?, reason? }` | `{ status }` | MISSING from UI — refund action not wired |

---

## Phone Numbers

| UI Page | Endpoint | Method | Required Role | Request Params | Response Shape | Notes |
|---------|----------|--------|---------------|----------------|----------------|-------|
| `/admin/phone-numbers` | `/api/v1/admin/phone-numbers` | GET | platform_* | `pn_status?, provider?, limit, skip` | `PhoneNumber[]` | Admin sees provider details |
| `/admin/phone-numbers` | `/api/v1/admin/phone-numbers/stats` | GET | platform_* | — | `{ available, assigned, suspended, maintenance, total }` | Stats cards |
| `/admin/phone-numbers` | `/api/v1/phone-numbers/admin` | POST | platform_* | `{ number, provider, provider_resource_id, ... }` | `PhoneNumber` | Add number modal |
| `/admin/phone-numbers` | `/api/v1/phone-numbers/admin/{id}/assign` | POST | platform_* | `{ organization_id }` | `PhoneNumber` | Assign modal |
| `/admin/phone-numbers` | `/api/v1/phone-numbers/admin/{id}/release` | POST | platform_* | — | `PhoneNumber` | Release action |
| `/admin/phone-numbers` | `/api/v1/phone-numbers/admin/{id}/suspend` | POST | platform_* | — | `PhoneNumber` | Suspend action |
| `/admin/phone-numbers` | `/api/v1/phone-numbers/admin/{id}/reactivate` | POST | platform_* | — | `PhoneNumber` | Reactivate action |

---

## Voice Profiles

| UI Page | Endpoint | Method | Required Role | Request Params | Response Shape | Notes |
|---------|----------|--------|---------------|----------------|----------------|-------|
| `/admin/voice-profiles` | `/api/v1/admin/voice-profiles` | GET | platform_* | — | `VoiceProfile[]` | Admin view includes org_id, routes |
| `/admin/voice-profiles` | `/api/v1/voice-profiles/admin` | POST | platform_admin/owner | `{ display_name, language, organization_id?, is_platform? }` | `VoiceProfile` | Create modal |
| `/admin/voice-profiles` | `/api/v1/voice-profiles/admin/{id}/versions` | POST | platform_admin/owner | `{ routes: {} }` | `{ id, version, status }` | Add version modal |

---

## Providers

| UI Page | Endpoint | Method | Required Role | Request Params | Response Shape | Notes |
|---------|----------|--------|---------------|----------------|----------------|-------|
| `/admin/providers` | `/api/v1/provider-ops/health` | GET | platform_* | `hours=24` | `{ overall_status, providers[] }` | — |
| `/admin/providers` | `/api/v1/provider-ops/metrics` | GET | platform_* | `hours=24, provider_type?` | `ProviderMetric[]` | Cost breakdown |
| `/admin/providers` | `/api/v1/provider-ops/latency` | GET | platform_* | `hours=24` | `{ avg, p50, p95, p99 }` | Latency cards |
| `/admin/providers` | `/api/v1/provider-ops/voice-profiles` | GET | platform_* | — | `VPHealth[]` | — |

---

## Usage, Revenue, Costs, Margins

| UI Page | Endpoint | Method | Required Role | Request Params | Response Shape | Notes |
|---------|----------|--------|---------------|----------------|----------------|-------|
| `/admin/usage` | `/api/v1/admin/usage` | GET | platform_* | `org_id?, from_date?, to_date?` | `UsageSummary` | Credits, cost, profit |
| `/admin/usage` | `/api/v1/admin/revenue` | GET | platform_* | `from_date?, to_date?` | `{ subscription_revenue_paise, calling_revenue_paise, total_revenue_paise }` | Revenue breakdown |
| `/admin/analytics` | `/api/v1/analytics/mrr` | GET | platform_* | — | `{ mrr_paise, arr_paise, arpu_paise, active_subscriptions }` | MRR/ARR/ARPU |
| `/admin/analytics` | `/api/v1/analytics/mrr-movement` | GET | platform_* | `from_date?, to_date?` | `{ new_mrr_paise, expansion_mrr_paise, churn_mrr_paise, net_new_mrr_paise }` | Movement cards |
| `/admin/analytics` | `/api/v1/analytics/revenue` | GET | platform_* | `from_date?, to_date?` | `{ total_revenue_paise, gross_profit_paise, gross_margin_pct }` | Gross margin |
| `/admin/analytics` | `/api/v1/analytics/daily` | GET | platform_* | `days=30, organization_id?` | `{ data: [{ date, calls, credits_consumed, revenue_paise }] }` | Charts |
| — | `/api/v1/admin/costs` | GET | platform_* | — | `{ total_provider_cost_paise, provider_breakdown }` | MISSING from UI — not surfaced |
| — | `/api/v1/admin/margins` | GET | platform_* | — | `UsageSummary` | Aliased to usage |
| — | `/api/v1/analytics/arpu` | GET | platform_* | — | `{ arpu_paise, active_orgs }` | MISSING from UI — could add to analytics |
| — | `/api/v1/analytics/report` | GET | platform_* | — | Full report | MISSING from UI — full combined report |

---

## Audit Logs

| UI Page | Endpoint | Method | Required Role | Request Params | Response Shape | Notes |
|---------|----------|--------|---------------|----------------|----------------|-------|
| `/admin/audit-logs` | `/api/v1/admin/audit-logs` | GET | platform_* | `org_id?, limit, skip` | `AuditLog[]` | Read-only |

---

## System Health

| UI Page | Endpoint | Method | Required Role | Request Params | Response Shape | Notes |
|---------|----------|--------|---------------|----------------|----------------|-------|
| MISSING | `/api/v1/admin/system-health` | GET | platform_* | — | `{ mongodb, redis, providers }` | API exists, no dedicated UI page — system health is surfaced in Providers page |

---

## Reconciliation (admin)

| UI Page | Endpoint | Method | Required Role | Request Params | Response Shape | Notes |
|---------|----------|--------|---------------|----------------|----------------|-------|
| MISSING | `/api/v1/reconciliation/run` | GET | platform_* | `hours=24` | `{ checks[], total_issues, run_at }` | No UI page built — backend only |
| MISSING | `/api/v1/reconciliation/report` | GET | platform_* | `hours=24` | Same as above | Alias |

---

## Customer Dashboard Pages (for completeness)

| UI Page | Endpoint | Method | Notes |
|---------|----------|--------|-------|
| `/dashboard` | `/api/v1/dashboard` | GET | Main overview |
| `/agents` | `/api/v1/agents` | GET | List + CRUD |
| `/agents/new` | `/api/v1/agents`, `/api/v1/agents/{id}/versions` | POST | Multi-step form |
| `/agents/[id]` | `/api/v1/agents/{id}`, `/api/v1/agents/{id}/versions` | GET/POST | Detail + version |
| `/campaigns` | `/api/v1/campaigns` | GET | With status filter |
| `/campaigns/new` | `/api/v1/campaigns` | POST | Full create form |
| `/campaigns/[id]` | `/api/v1/campaigns/{id}`, `/stats`, `/preflight` | GET | Detail + actions |
| `/leads` | `/api/v1/leads` | GET | Paginated + DNC tab |
| `/leads/import` | `/api/v1/leads/import` | POST | File upload |
| `/calls` | `/api/v1/calls` | GET | — |
| `/calls/[id]` | `/api/v1/calls/{id}`, `/api/v1/transcripts/{call_id}` | GET | Detail + transcript |
| `/appointments` | `/api/v1/appointments` | GET | + FSM actions |
| `/phone-numbers` | `/api/v1/phone-numbers/my`, `/available` | GET | Read-only for customers |
| `/credits` | `/api/v1/wallet`, `/transactions`, `/lots`, `/packs` | GET | + Razorpay purchase |
| `/billing` | `/api/v1/subscriptions/my`, `/billing/invoices`, `/billing/payments` | GET | + plan change |
| `/knowledge` | `/api/v1/knowledge` | GET/POST | KB + documents |
| `/analytics` | `/api/v1/dashboard/analytics` | GET | Charts |
| `/team` | `/api/v1/users/org/{id}` | GET/POST | Team management |
| `/settings` | `/api/v1/auth/me`, `/api/v1/users/{id}` | GET/PATCH | Profile |
