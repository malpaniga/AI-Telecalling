# Admin UI Implementation Plan — M40 FEAT-005A

## 1. Current State (post FEAT-005A)

All admin pages are implemented and building. Summary:

### Admin pages (12 pages — all exist)
| Route | File | Status |
|-------|------|--------|
| `/admin/dashboard` | `(admin)/admin/dashboard/page.tsx` | ✅ Full |
| `/admin/organizations` | `(admin)/admin/organizations/page.tsx` | ✅ Full (search, suspend/reactivate) |
| `/admin/organizations/[id]` | `(admin)/admin/organizations/[id]/page.tsx` | ✅ Full (4 tabs: overview, subscription, wallet, users) |
| `/admin/subscriptions` | `(admin)/admin/subscriptions/page.tsx` | ✅ Full (2 tabs: subscriptions + plans management) |
| `/admin/calling-packs` | `(admin)/admin/calling-packs/page.tsx` | ✅ Full (create + grant bonus + adjust credits) |
| `/admin/payments` | `(admin)/admin/payments/page.tsx` | ✅ Full (2 tabs: payments + invoices, org filter) |
| `/admin/phone-numbers` | `(admin)/admin/phone-numbers/page.tsx` | ✅ Full (stats + add/assign/release/suspend/reactivate) |
| `/admin/voice-profiles` | `(admin)/admin/voice-profiles/page.tsx` | ✅ Full (create profile + create version) |
| `/admin/providers` | `(admin)/admin/providers/page.tsx` | ✅ Full (health + metrics + latency + VP health) |
| `/admin/usage` | `(admin)/admin/usage/page.tsx` | ✅ Full (usage + revenue breakdown) |
| `/admin/analytics` | `(admin)/admin/analytics/page.tsx` | ✅ Full (MRR, ARR, ARPU, movement, revenue, daily charts) |
| `/admin/audit-logs` | `(admin)/admin/audit-logs/page.tsx` | ✅ Full (paginated, org filter) |

### Customer pages (22 pages — all exist)
All dashboard pages plus `/agents/new`, `/campaigns/new`, `/leads/import`.

---

## 2. File Structure

```
frontend/
├── app/
│   ├── (admin)/
│   │   ├── layout.tsx                       # Auth guard (platform roles only)
│   │   └── admin/
│   │       ├── dashboard/page.tsx
│   │       ├── organizations/page.tsx
│   │       ├── organizations/[id]/page.tsx
│   │       ├── subscriptions/page.tsx
│   │       ├── calling-packs/page.tsx
│   │       ├── payments/page.tsx
│   │       ├── phone-numbers/page.tsx
│   │       ├── voice-profiles/page.tsx
│   │       ├── providers/page.tsx
│   │       ├── usage/page.tsx
│   │       ├── analytics/page.tsx
│   │       └── audit-logs/page.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx                       # Auth guard (org users)
│   │   ├── dashboard/page.tsx
│   │   ├── agents/page.tsx
│   │   ├── agents/new/page.tsx              # Multi-step create form
│   │   ├── agents/[id]/page.tsx
│   │   ├── campaigns/page.tsx
│   │   ├── campaigns/new/page.tsx           # Full create form
│   │   ├── campaigns/[id]/page.tsx
│   │   ├── leads/page.tsx
│   │   ├── leads/import/page.tsx            # CSV/XLSX/JSON upload
│   │   ├── calls/page.tsx
│   │   ├── calls/[id]/page.tsx
│   │   ├── appointments/page.tsx
│   │   ├── phone-numbers/page.tsx
│   │   ├── credits/page.tsx
│   │   ├── billing/page.tsx
│   │   ├── knowledge/page.tsx
│   │   ├── analytics/page.tsx
│   │   ├── team/page.tsx
│   │   └── settings/page.tsx
│   ├── (auth)/
│   │   ├── layout.tsx
│   │   ├── login/page.tsx
│   │   └── signup/page.tsx
│   ├── layout.tsx                           # Root: Inter font, AuthProvider, Toaster
│   └── page.tsx                             # Public landing page
├── components/
│   ├── layout/
│   │   ├── admin-sidebar.tsx                # Dark admin sidebar (brand-differentiated)
│   │   ├── sidebar.tsx                      # Light customer sidebar
│   │   ├── topbar.tsx
│   │   ├── app-shell.tsx
│   │   └── index.ts
│   └── ui/
│       ├── button.tsx
│       ├── badge.tsx
│       ├── card.tsx
│       ├── input.tsx
│       ├── modal.tsx
│       ├── table.tsx
│       ├── pagination.tsx
│       ├── spinner.tsx
│       ├── empty-state.tsx
│       ├── metric-card.tsx
│       └── index.ts
├── lib/
│   ├── api.ts                               # Complete API client (all namespaces)
│   ├── auth.ts                              # Token storage/decode
│   └── utils.ts                             # formatINR, formatDate, etc.
└── contexts/
    └── auth-context.tsx                     # AuthProvider + useAuth hook
```

---

## 3. Shared Component Reuse

Every admin and customer page uses these from `@/components/ui/`:
- `Button` — primary/secondary/ghost/danger variants
- `Card`, `CardHeader`, `CardBody` — surface containers
- `StatusBadge` — maps any status string to color
- `EmptyState` — icon + title + optional action
- `Spinner`, `LoadingScreen` — loading states
- `Pagination` — skip/limit based
- `SimpleTable`, `TableRow`, `TableCell` — data tables
- `Input`, `Select` — form controls with label/error/hint
- `Modal` — portal-based dialog with backdrop
- `MetricCard` — KPI card with label/value/icon

---

## 4. Auth/Permission Guard Strategy

From `backend/core/rbac.py`:
- `platform_owner`, `platform_admin`, `billing_admin` → allowed into admin shell
- `support` role: NOT included in current admin guard (conservative)
- Org roles (`organization_owner`, `organization_admin`, `manager`, `agent`, `viewer`) → redirected to `/dashboard`

Guards implemented in:
- `app/(admin)/layout.tsx` — checks `PLATFORM_ROLES = ["platform_owner", "platform_admin", "billing_admin"]`
- `app/(dashboard)/layout.tsx` — checks `isLoggedIn()`, redirects to `/login` if not

---

## 5. Design System

Light theme CSS variables (defined in `app/globals.css`):
```css
--color-background: #FAF9F6     /* page bg */
--color-surface: #FFFFFF         /* cards */
--color-surface-subtle: #F4F2ED /* subtle tones */
--color-text-primary: #202020
--color-text-secondary: #77716B
--color-text-muted: #928C85
--color-border: #EAE7E0
--color-accent: #E9814D          /* warm orange */
--color-success: #287D55
--color-warning: #A96717
--color-danger: #C44848
--color-info: #3975B8
```

Admin sidebar exception: uses `bg-[#1A1814]` (very dark) to clearly signal admin context. This was a deliberate design decision per FEAT-001 findings.

---

## 6. API Client Namespaces (lib/api.ts)

| Namespace | Endpoints covered |
|-----------|------------------|
| `api.auth.*` | login, signup, logout, refresh, me |
| `api.agents.*` | CRUD + versions |
| `api.leads.*` | list, CRUD, import, DNC |
| `api.campaigns.*` | list, CRUD, start/pause/resume/cancel, stats, preflight |
| `api.calls.*` | list, get, initiate |
| `api.appointments.*` | list, CRUD, confirm/complete/cancel/no-show/reschedule |
| `api.wallet.*` | summary, transactions, lots, packs, order |
| `api.billing.*` | orders, verify, payments, invoices |
| `api.subscriptions.*` | plans, my subscription, cancel/change |
| `api.voiceProfiles.*` | list, get |
| `api.phoneNumbers.*` | my, available, admin CRUD (add/assign/release/suspend/reactivate) |
| `api.knowledge.*` | KB CRUD, documents CRUD, search |
| `api.users.*` | list, invite, get, update, deactivate |
| `api.dashboard.*` | summary, calls, campaigns, leads, credits, appointments, analytics |
| `api.transcripts.*` | get by call ID |
| `api.admin.*` | full platform management (all admin endpoints) |
| `api.analytics.*` | mrr, mrrMovement, revenue, daily, arpu |
| `api.providerOps.*` | health, metrics, latency, voiceProfiles |
| `api.reconciliation.*` | run |

---

## 7. Verification Commands

```bash
cd frontend && npm run build   # Must pass with zero TypeScript errors
cd frontend && npm run lint    # Must pass with zero ESLint errors
```

Both pass as of this implementation.

---

## 8. Known Gaps / Future Work

1. **Org subscription activate** (`POST /api/v1/subscriptions/admin/orgs/{id}/activate`) — no dedicated UI; admin can activate manually via API
2. **Calling pack edit** (PATCH) — no edit modal in calling-packs page; create-only currently
3. **Refund action** in payments — `api.admin.payments.refund()` exists in api.ts but no UI button
4. **Expire lots** (`POST /api/v1/wallet/admin/expire`) — no UI
5. **Reconciliation page** — `/api/v1/reconciliation/run` exists but no dedicated UI page; not in sidebar
6. **System health** — surfaced implicitly in providers page; no dedicated `/admin/system-health` route
7. **ARPU card** on analytics page — `api.analytics.arpu()` exists but not rendered (could add as a 5th MRR card)

These are backend capabilities that exist but were not in the required MVP scope. They can be added as future enhancements.
