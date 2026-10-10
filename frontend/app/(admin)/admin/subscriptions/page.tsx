"use client";

import React, { useEffect, useState, useCallback } from "react";
import { CreditCard, Edit2 } from "lucide-react";
import toast from "react-hot-toast";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Input } from "@/components/ui/input";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, Subscription, SubscriptionPlan } from "@/lib/api";
import { formatDateTime, formatINR } from "@/lib/utils";

type Tab = "subscriptions" | "plans";

const PAGE_SIZE = 50;

export default function AdminSubscriptionsPage() {
  const [tab, setTab] = useState<Tab>("subscriptions");

  // ── Subscriptions tab ──────────────────────────────────────────────────
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [subsLoading, setSubsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");

  const loadSubs = useCallback(async () => {
    setSubsLoading(true);
    try {
      const data = await api.admin.subscriptions.list({
        sub_status: statusFilter || undefined,
        limit: PAGE_SIZE,
        skip: (page - 1) * PAGE_SIZE,
      });
      setSubs(data);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setSubsLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => { setPage(1); }, [statusFilter]);
  useEffect(() => { if (tab === "subscriptions") loadSubs(); }, [tab, loadSubs]);

  // ── Plans tab ──────────────────────────────────────────────────────────
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [plansLoading, setPlansLoading] = useState(false);
  const [editingPlan, setEditingPlan] = useState<SubscriptionPlan | null>(null);
  const [planForm, setPlanForm] = useState({
    name: "",
    price_monthly_paise: "",
    price_yearly_paise: "",
    max_agents: "",
    max_campaigns: "",
    max_concurrent_calls: "",
    is_active: true,
    is_public: true,
  });
  const [savingPlan, setSavingPlan] = useState(false);

  const loadPlans = useCallback(async () => {
    setPlansLoading(true);
    try {
      const data = await api.admin.subscriptions.plans.list(true);
      setPlans(data);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load plans");
    } finally {
      setPlansLoading(false);
    }
  }, []);

  useEffect(() => { if (tab === "plans") loadPlans(); }, [tab, loadPlans]);

  function openEdit(plan: SubscriptionPlan) {
    setEditingPlan(plan);
    setPlanForm({
      name: plan.name,
      price_monthly_paise: String(plan.price_monthly_paise),
      price_yearly_paise: String(plan.price_yearly_paise ?? 0),
      max_agents: String(plan.max_agents),
      max_campaigns: String(plan.max_campaigns),
      max_concurrent_calls: String(plan.max_concurrent_calls),
      is_active: plan.is_active,
      is_public: plan.is_public,
    });
  }

  async function handleSavePlan(e: React.FormEvent) {
    e.preventDefault();
    if (!editingPlan) return;
    setSavingPlan(true);
    try {
      await api.admin.subscriptions.plans.update(editingPlan.id, {
        name: planForm.name,
        price_monthly_paise: parseInt(planForm.price_monthly_paise),
        price_yearly_paise: parseInt(planForm.price_yearly_paise) || 0,
        max_agents: parseInt(planForm.max_agents),
        max_campaigns: parseInt(planForm.max_campaigns),
        max_concurrent_calls: parseInt(planForm.max_concurrent_calls),
        is_active: planForm.is_active,
        is_public: planForm.is_public,
      });
      toast.success("Plan updated");
      setEditingPlan(null);
      await loadPlans();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update plan");
    } finally {
      setSavingPlan(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header + tabs */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-lg font-semibold text-text-primary">
          Subscriptions &amp; Plans
        </h2>
      </div>

      <div className="flex gap-1 border-b border-border">
        {(["subscriptions", "plans"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px capitalize ${
              tab === t
                ? "border-accent text-accent"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Subscriptions tab */}
      {tab === "subscriptions" && (
        <>
          <div className="flex justify-end">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={[
                { value: "", label: "All Statuses" },
                { value: "active", label: "Active" },
                { value: "trialing", label: "Trialing" },
                { value: "cancelled", label: "Cancelled" },
              ]}
              className="w-40"
            />
          </div>
          <Card>
            {subsLoading ? (
              <div className="flex justify-center py-16">
                <Spinner size="lg" />
              </div>
            ) : subs.length === 0 ? (
              <EmptyState icon={CreditCard} title="No subscriptions" />
            ) : (
              <>
                <SimpleTable
                  headers={[
                    "Org ID",
                    "Plan",
                    "Cycle",
                    "Status",
                    "Period End",
                    "Cancel?",
                  ]}
                >
                  {subs.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="font-mono text-xs text-text-muted">
                        {s.organization_id}
                      </TableCell>
                      <TableCell className="font-medium capitalize">
                        {s.plan_slug?.replace(/_/g, " ")}
                      </TableCell>
                      <TableCell className="capitalize text-text-secondary">
                        {s.billing_cycle}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={s.status} />
                      </TableCell>
                      <TableCell className="text-xs text-text-muted whitespace-nowrap">
                        {formatDateTime(s.current_period_end)}
                      </TableCell>
                      <TableCell>
                        {s.cancel_at_period_end ? (
                          <StatusBadge status="warning" />
                        ) : (
                          <span className="text-text-muted">—</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </SimpleTable>
                {subs.length === PAGE_SIZE && (
                  <div className="px-4 py-3 border-t border-border">
                    <Pagination
                      page={page}
                      pageSize={PAGE_SIZE}
                      total={page * PAGE_SIZE + 1}
                      onPageChange={setPage}
                    />
                  </div>
                )}
              </>
            )}
          </Card>
        </>
      )}

      {/* Plans tab */}
      {tab === "plans" && (
        <Card>
          {plansLoading ? (
            <div className="flex justify-center py-16">
              <Spinner size="lg" />
            </div>
          ) : plans.length === 0 ? (
            <EmptyState icon={CreditCard} title="No plans found" />
          ) : (
            <SimpleTable
              headers={[
                "Name",
                "Slug",
                "Monthly Price",
                "Agents",
                "Campaigns",
                "Concurrent Calls",
                "Active",
                "Public",
                "Actions",
              ]}
            >
              {plans.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="font-medium">{p.name}</TableCell>
                  <TableCell className="font-mono text-xs text-text-muted">
                    {p.slug}
                  </TableCell>
                  <TableCell className="font-medium">
                    {formatINR(p.price_monthly_paise)}
                  </TableCell>
                  <TableCell className="text-text-secondary">
                    {p.max_agents}
                  </TableCell>
                  <TableCell className="text-text-secondary">
                    {p.max_campaigns}
                  </TableCell>
                  <TableCell className="text-text-secondary">
                    {p.max_concurrent_calls}
                  </TableCell>
                  <TableCell>
                    <StatusBadge
                      status={p.is_active ? "active" : "inactive"}
                    />
                  </TableCell>
                  <TableCell>
                    <StatusBadge
                      status={p.is_public ? "active" : "inactive"}
                    />
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => openEdit(p)}
                    >
                      <Edit2 className="h-3.5 w-3.5 mr-1" />
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </SimpleTable>
          )}
        </Card>
      )}

      {/* Edit plan modal */}
      <Modal
        isOpen={!!editingPlan}
        onClose={() => setEditingPlan(null)}
        title={`Edit Plan: ${editingPlan?.name ?? ""}`}
      >
        <form onSubmit={handleSavePlan} className="space-y-4">
          <Input
            label="Name"
            value={planForm.name}
            onChange={(e) =>
              setPlanForm((f) => ({ ...f, name: e.target.value }))
            }
            required
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Monthly Price (paise)"
              type="number"
              value={planForm.price_monthly_paise}
              onChange={(e) =>
                setPlanForm((f) => ({
                  ...f,
                  price_monthly_paise: e.target.value,
                }))
              }
              hint="100 = ₹1"
              required
            />
            <Input
              label="Yearly Price (paise)"
              type="number"
              value={planForm.price_yearly_paise}
              onChange={(e) =>
                setPlanForm((f) => ({
                  ...f,
                  price_yearly_paise: e.target.value,
                }))
              }
              hint="0 = same as monthly × 12"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Input
              label="Max Agents"
              type="number"
              value={planForm.max_agents}
              onChange={(e) =>
                setPlanForm((f) => ({ ...f, max_agents: e.target.value }))
              }
              required
            />
            <Input
              label="Max Campaigns"
              type="number"
              value={planForm.max_campaigns}
              onChange={(e) =>
                setPlanForm((f) => ({
                  ...f,
                  max_campaigns: e.target.value,
                }))
              }
              required
            />
            <Input
              label="Max Concurrent Calls"
              type="number"
              value={planForm.max_concurrent_calls}
              onChange={(e) =>
                setPlanForm((f) => ({
                  ...f,
                  max_concurrent_calls: e.target.value,
                }))
              }
              required
            />
          </div>
          <div className="flex gap-4 text-sm">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={planForm.is_active}
                onChange={(e) =>
                  setPlanForm((f) => ({ ...f, is_active: e.target.checked }))
                }
                className="rounded border-border accent-accent"
              />
              Active
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={planForm.is_public}
                onChange={(e) =>
                  setPlanForm((f) => ({ ...f, is_public: e.target.checked }))
                }
                className="rounded border-border accent-accent"
              />
              Public
            </label>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setEditingPlan(null)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={savingPlan}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
