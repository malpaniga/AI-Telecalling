"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  CreditCard,
  Edit2,
  QrCode,
  Check,
  X,
  Copy,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Clock,
} from "lucide-react";
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
import {
  api,
  Subscription,
  SubscriptionPlan,
  BillingSettings,
  ManualSubscriptionRequest,
} from "@/lib/api";
import { formatDateTime, formatINR } from "@/lib/utils";

type Tab = "subscriptions" | "manual_requests" | "plans" | "settings";

const PAGE_SIZE = 50;

export default function AdminSubscriptionsPage() {
  const [tab, setTab] = useState<Tab>("subscriptions");

  // ── Global Billing Settings & Stats ────────────────────────────────────
  const [billingSettings, setBillingSettings] = useState<BillingSettings | null>(null);
  const [pendingCount, setPendingCount] = useState<number>(0);

  const loadSettingsAndStats = useCallback(async () => {
    try {
      const [settings, pendingReqs] = await Promise.all([
        api.admin.billing.getSettings(),
        api.admin.billing.getManualRequests("pending").catch(() => [] as ManualSubscriptionRequest[]),
      ]);
      setBillingSettings(settings);
      setSettingsForm({
        payment_mode: settings.payment_mode || "razorpay",
        admin_upi_id: settings.admin_upi_id || "",
        admin_payee_name: settings.admin_payee_name || "",
      });
      setPendingCount(pendingReqs.length);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadSettingsAndStats();
  }, [loadSettingsAndStats]);

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

  useEffect(() => {
    setPage(1);
  }, [statusFilter]);

  useEffect(() => {
    if (tab === "subscriptions") loadSubs();
  }, [tab, loadSubs]);

  // ── Manual Requests tab ────────────────────────────────────────────────
  const [manualRequests, setManualRequests] = useState<ManualSubscriptionRequest[]>([]);
  const [manualLoading, setManualLoading] = useState(false);
  const [manualFilter, setManualFilter] = useState("pending");

  // Approval / Rejection modal state
  const [approvingReq, setApprovingReq] = useState<ManualSubscriptionRequest | null>(null);
  const [approvingLoading, setApprovingLoading] = useState(false);
  const [rejectingReq, setRejectingReq] = useState<ManualSubscriptionRequest | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [rejectingLoading, setRejectingLoading] = useState(false);

  const loadManualRequests = useCallback(async () => {
    setManualLoading(true);
    try {
      const data = await api.admin.billing.getManualRequests(manualFilter || undefined);
      setManualRequests(data);
      if (manualFilter === "pending") {
        setPendingCount(data.length);
      }
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load manual requests");
    } finally {
      setManualLoading(false);
    }
  }, [manualFilter]);

  useEffect(() => {
    if (tab === "manual_requests") {
      loadManualRequests();
    }
  }, [tab, loadManualRequests]);

  async function handleApprove() {
    if (!approvingReq) return;
    setApprovingLoading(true);
    try {
      await api.admin.billing.approveManualRequest(approvingReq.id);
      toast.success(`Subscription activated for ${approvingReq.org_name}`);
      setApprovingReq(null);
      await Promise.all([loadManualRequests(), loadSettingsAndStats()]);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to approve request");
    } finally {
      setApprovingLoading(false);
    }
  }

  async function handleReject() {
    if (!rejectingReq) return;
    setRejectingLoading(true);
    try {
      await api.admin.billing.rejectManualRequest(rejectingReq.id, rejectionReason);
      toast.success(`Request from ${rejectingReq.org_name} rejected`);
      setRejectingReq(null);
      setRejectionReason("");
      await Promise.all([loadManualRequests(), loadSettingsAndStats()]);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to reject request");
    } finally {
      setRejectingLoading(false);
    }
  }

  function copyUtr(utr: string) {
    if (!utr) return;
    navigator.clipboard?.writeText(utr);
    toast.success("UTR copied to clipboard");
  }

  // ── Payment Gateway Settings tab ──────────────────────────────────────
  const [settingsForm, setSettingsForm] = useState({
    payment_mode: "razorpay" as "razorpay" | "manual",
    admin_upi_id: "",
    admin_payee_name: "",
  });
  const [savingSettings, setSavingSettings] = useState(false);

  async function handleSaveSettings(e?: React.FormEvent) {
    if (e) e.preventDefault();
    setSavingSettings(true);
    try {
      const updated = await api.admin.billing.updateSettings({
        payment_mode: settingsForm.payment_mode,
        admin_upi_id: settingsForm.admin_upi_id.trim(),
        admin_payee_name: settingsForm.admin_payee_name.trim(),
      });
      setBillingSettings(updated);
      toast.success("Payment gateway settings updated");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update settings");
    } finally {
      setSavingSettings(false);
    }
  }

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

  useEffect(() => {
    if (tab === "plans") loadPlans();
  }, [tab, loadPlans]);

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

  const tabs: { key: Tab; label: string; badge?: number }[] = [
    { key: "subscriptions", label: "Subscriptions" },
    { key: "manual_requests", label: "Manual Approvals", badge: pendingCount },
    { key: "plans", label: "Plan Tiers" },
    { key: "settings", label: "Payment Gateway Settings" },
  ];

  return (
    <div className="space-y-6">
      {/* Header + Current Mode Status */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">
            Subscriptions &amp; Payments
          </h2>
          <p className="text-xs text-text-secondary">
            Manage organization subscriptions, plan tiers, payment modes, and offline UPI approvals.
          </p>
        </div>

        {billingSettings && (
          <button
            onClick={() => setTab("settings")}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border border-border bg-surface hover:bg-surface-subtle transition-colors shadow-xs"
          >
            <span className="text-text-muted">Payment Mode:</span>
            {billingSettings.payment_mode === "manual" ? (
              <span className="flex items-center gap-1.5 text-amber-600 font-semibold">
                <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                Manual UPI Approval
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-emerald-600 font-semibold">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Razorpay Automated
              </span>
            )}
          </button>
        )}
      </div>

      {/* Tabs navigation */}
      <div className="flex gap-1 border-b border-border">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px flex items-center gap-2 ${
              tab === t.key
                ? "border-accent text-accent"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            <span>{t.label}</span>
            {Boolean(t.badge && t.badge > 0) && (
              <span className="px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-accent text-white">
                {t.badge}
              </span>
            )}
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
              <EmptyState icon={CreditCard} title="No subscriptions found" />
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

      {/* Manual Requests tab */}
      {tab === "manual_requests" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <Select
                value={manualFilter}
                onChange={(e) => setManualFilter(e.target.value)}
                options={[
                  { value: "pending", label: "Pending Verification" },
                  { value: "", label: "All Requests" },
                  { value: "approved", label: "Approved" },
                  { value: "rejected", label: "Rejected" },
                  { value: "cancelled", label: "Cancelled" },
                ]}
                className="w-48"
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={loadManualRequests}
                disabled={manualLoading}
                title="Refresh requests"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${manualLoading ? "animate-spin" : ""}`} />
              </Button>
            </div>

            <div className="text-xs text-text-muted flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              <span>Verify UTR against your bank/UPI app before approving</span>
            </div>
          </div>

          <Card>
            {manualLoading ? (
              <div className="flex justify-center py-16">
                <Spinner size="lg" />
              </div>
            ) : manualRequests.length === 0 ? (
              <EmptyState
                icon={QrCode}
                title="No manual subscription requests"
                description={
                  manualFilter === "pending"
                    ? "There are currently no pending payments awaiting verification."
                    : "No requests found matching the current filter."
                }
              />
            ) : (
              <SimpleTable
                headers={[
                  "Organization & User",
                  "Plan & Cycle",
                  "Amount",
                  "UTR / Transaction ID",
                  "Submitted At",
                  "Status",
                  "Actions",
                ]}
              >
                {manualRequests.map((req) => (
                  <TableRow key={req.id}>
                    {/* Organization & User */}
                    <TableCell>
                      <div className="font-medium text-text-primary">
                        {req.org_name || "Unknown Org"}
                      </div>
                      <div className="text-xs text-text-muted">
                        {req.user_email}
                      </div>
                      <div className="font-mono text-[10px] text-text-muted mt-0.5">
                        {req.organization_id}
                      </div>
                    </TableCell>

                    {/* Plan & Cycle */}
                    <TableCell>
                      <div className="font-medium capitalize text-text-primary">
                        {req.plan_name || req.plan_slug}
                      </div>
                      <div className="text-xs capitalize text-text-secondary">
                        {req.billing_cycle}
                      </div>
                    </TableCell>

                    {/* Amount */}
                    <TableCell>
                      <div className="font-semibold text-accent">
                        {formatINR(req.amount_paise)}
                      </div>
                    </TableCell>

                    {/* UTR / Transaction ID */}
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs bg-surface-subtle px-2 py-0.5 rounded border border-border select-all font-semibold">
                          {req.utr_number}
                        </span>
                        <button
                          onClick={() => copyUtr(req.utr_number)}
                          className="p-1 text-text-muted hover:text-text-primary hover:bg-surface-subtle rounded transition-colors"
                          title="Copy UTR number"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      {req.payer_note && (
                        <div
                          className="text-xs text-text-muted mt-1 italic max-w-xs truncate"
                          title={req.payer_note}
                        >
                          &ldquo;{req.payer_note}&rdquo;
                        </div>
                      )}
                    </TableCell>

                    {/* Submitted At */}
                    <TableCell className="text-xs text-text-muted whitespace-nowrap">
                      {formatDateTime(req.created_at)}
                    </TableCell>

                    {/* Status */}
                    <TableCell>
                      <StatusBadge status={req.status} />
                      {req.status === "rejected" && req.rejection_reason && (
                        <div
                          className="text-[11px] text-danger mt-1 max-w-xs truncate"
                          title={req.rejection_reason}
                        >
                          Reason: {req.rejection_reason}
                        </div>
                      )}
                    </TableCell>

                    {/* Actions */}
                    <TableCell>
                      {req.status === "pending" ? (
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            className="bg-emerald-600 hover:bg-emerald-700 text-white h-7 px-2.5 text-xs"
                            onClick={() => setApprovingReq(req)}
                          >
                            <Check className="w-3.5 h-3.5 mr-1" />
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="danger"
                            className="h-7 px-2.5 text-xs"
                            onClick={() => {
                              setRejectingReq(req);
                              setRejectionReason("");
                            }}
                          >
                            <X className="w-3.5 h-3.5 mr-1" />
                            Reject
                          </Button>
                        </div>
                      ) : req.status === "approved" ? (
                        <div className="text-xs text-text-muted">
                          {req.reviewed_at ? (
                            <span>Activated {formatDateTime(req.reviewed_at)}</span>
                          ) : (
                            <span>Activated</span>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-text-muted">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </SimpleTable>
            )}
          </Card>
        </div>
      )}

      {/* Payment Gateway Settings tab */}
      {tab === "settings" && (
        <div className="max-w-4xl space-y-6">
          {/* Payment Mode Selection Card */}
          <Card className="p-6">
            <div className="mb-4">
              <h3 className="text-base font-semibold text-text-primary">
                Payment Collection Mode
              </h3>
              <p className="text-sm text-text-secondary mt-1">
                Select how your platform accepts subscription payments from customers.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Razorpay Option */}
              <div
                onClick={() =>
                  setSettingsForm((f) => ({ ...f, payment_mode: "razorpay" }))
                }
                className={`cursor-pointer rounded-xl border-2 p-4 transition-all ${
                  settingsForm.payment_mode === "razorpay"
                    ? "border-accent bg-accent/5 ring-1 ring-accent"
                    : "border-border hover:border-border-strong bg-surface"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2 rounded-lg ${
                        settingsForm.payment_mode === "razorpay"
                          ? "bg-accent text-white"
                          : "bg-surface-subtle text-text-muted"
                      }`}
                    >
                      <CreditCard className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-semibold text-text-primary flex items-center gap-2">
                        Razorpay Automated
                        {settingsForm.payment_mode === "razorpay" && (
                          <span className="text-[10px] font-bold tracking-wider uppercase px-1.5 py-0.5 rounded bg-accent text-white">
                            Active
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-text-muted">
                        Online Payment Gateway
                      </div>
                    </div>
                  </div>
                  <input
                    type="radio"
                    name="payment_mode"
                    checked={settingsForm.payment_mode === "razorpay"}
                    onChange={() =>
                      setSettingsForm((f) => ({ ...f, payment_mode: "razorpay" }))
                    }
                    className="accent-accent mt-1"
                  />
                </div>
                <p className="text-xs text-text-secondary mt-3 leading-relaxed">
                  Opens the Razorpay checkout modal popup for automated payment via UPI, Credit/Debit cards, or NetBanking. Instant automated activation via signature verification.
                </p>
                <div className="mt-3 pt-3 border-t border-border flex items-center justify-between text-xs">
                  <span className="text-text-muted">Gateway Key Status:</span>
                  <span className="font-mono text-text-primary">
                    {billingSettings?.razorpay_key_id ? (
                      <span className="text-emerald-600 font-medium">
                        Configured ({billingSettings.razorpay_key_id.slice(0, 8)}...)
                      </span>
                    ) : (
                      <span className="text-warning font-medium">Not configured in backend .env</span>
                    )}
                  </span>
                </div>
              </div>

              {/* Manual UPI Option */}
              <div
                onClick={() =>
                  setSettingsForm((f) => ({ ...f, payment_mode: "manual" }))
                }
                className={`cursor-pointer rounded-xl border-2 p-4 transition-all ${
                  settingsForm.payment_mode === "manual"
                    ? "border-accent bg-accent/5 ring-1 ring-accent"
                    : "border-border hover:border-border-strong bg-surface"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2 rounded-lg ${
                        settingsForm.payment_mode === "manual"
                          ? "bg-accent text-white"
                          : "bg-surface-subtle text-text-muted"
                      }`}
                    >
                      <QrCode className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-semibold text-text-primary flex items-center gap-2">
                        Manual UPI Approval
                        {settingsForm.payment_mode === "manual" && (
                          <span className="text-[10px] font-bold tracking-wider uppercase px-1.5 py-0.5 rounded bg-amber-500 text-white">
                            Active
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-text-muted">
                        QR Code &amp; UTR Verification
                      </div>
                    </div>
                  </div>
                  <input
                    type="radio"
                    name="payment_mode"
                    checked={settingsForm.payment_mode === "manual"}
                    onChange={() =>
                      setSettingsForm((f) => ({ ...f, payment_mode: "manual" }))
                    }
                    className="accent-accent mt-1"
                  />
                </div>
                <p className="text-xs text-text-secondary mt-3 leading-relaxed">
                  Displays your custom UPI QR code and UPI ID to customers. Customer pays via any UPI app (GPay, PhonePe, Paytm) and submits their 12-digit UTR for admin approval.
                </p>
                <div className="mt-3 pt-3 border-t border-border flex items-center justify-between text-xs">
                  <span className="text-text-muted">Target UPI ID:</span>
                  <span className="font-mono text-text-primary">
                    {settingsForm.admin_upi_id || "Not configured"}
                  </span>
                </div>
              </div>
            </div>
          </Card>

          {/* Admin UPI Details Card */}
          <Card className="p-6">
            <h3 className="text-base font-semibold text-text-primary mb-1">
              Admin UPI Account Details
            </h3>
            <p className="text-sm text-text-secondary mb-4">
              These details are encoded into the UPI QR code shown to customers on the billing page.
            </p>

            <form onSubmit={handleSaveSettings} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Admin UPI ID (VPA)"
                  value={settingsForm.admin_upi_id}
                  onChange={(e) =>
                    setSettingsForm((f) => ({
                      ...f,
                      admin_upi_id: e.target.value,
                    }))
                  }
                  placeholder="e.g. nivcall@icici or 9876543210@paytm"
                  hint="The UPI ID where you receive customer payments"
                  required
                />
                <Input
                  label="Admin Payee Name"
                  value={settingsForm.admin_payee_name}
                  onChange={(e) =>
                    setSettingsForm((f) => ({
                      ...f,
                      admin_payee_name: e.target.value,
                    }))
                  }
                  placeholder="e.g. NivCall Connect"
                  hint="Business or account holder name displayed in UPI apps"
                  required
                />
              </div>

              {settingsForm.payment_mode === "manual" && (
                <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-700 flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-600" />
                  <div>
                    <span className="font-semibold">Manual Mode is Active:</span> Customers subscribing will receive the scannable UPI QR code and won&apos;t go through Razorpay. Ensure your UPI ID is verified and can receive payments.
                  </div>
                </div>
              )}

              <div className="flex justify-end pt-3 border-t border-border">
                <Button type="submit" loading={savingSettings}>
                  Save Payment Settings
                </Button>
              </div>
            </form>
          </Card>
        </div>
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

      {/* Manual Request Approval Confirmation Modal */}
      <Modal
        isOpen={!!approvingReq}
        onClose={() => !approvingLoading && setApprovingReq(null)}
        title="Approve & Activate Subscription"
      >
        {approvingReq && (
          <div className="space-y-4">
            <p className="text-sm text-text-secondary leading-relaxed">
              Please confirm that you have checked your bank / UPI app and verified the payment credit for this transaction:
            </p>

            <div className="p-4 rounded-lg bg-surface-subtle border border-border space-y-2.5 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-text-muted">Organization:</span>
                <span className="font-semibold text-text-primary">
                  {approvingReq.org_name || approvingReq.organization_id}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-text-muted">User Email:</span>
                <span className="font-medium text-text-primary">
                  {approvingReq.user_email}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-text-muted">Plan &amp; Cycle:</span>
                <span className="font-medium text-text-primary capitalize">
                  {approvingReq.plan_name || approvingReq.plan_slug} ({approvingReq.billing_cycle})
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-text-muted">Amount Received:</span>
                <span className="font-bold text-base text-accent">
                  {formatINR(approvingReq.amount_paise)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-text-muted">Submitted UTR:</span>
                <span className="font-mono font-bold text-text-primary bg-surface px-2 py-0.5 rounded border border-border">
                  {approvingReq.utr_number}
                </span>
              </div>
              {approvingReq.payer_note && (
                <div className="flex justify-between items-start">
                  <span className="text-text-muted">Payer Note:</span>
                  <span className="text-text-primary italic text-right max-w-[240px]">
                    {approvingReq.payer_note}
                  </span>
                </div>
              )}
            </div>

            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-800 flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                Approving will immediately activate this organization&apos;s subscription for{" "}
                <span className="font-semibold">
                  {approvingReq.billing_cycle === "yearly" ? "365 days" : "30 days"}
                </span>
                , mark an order and payment as captured, and issue a paid invoice.
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setApprovingReq(null)}
                disabled={approvingLoading}
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={handleApprove}
                loading={approvingLoading}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                Approve &amp; Activate
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Manual Request Rejection Modal */}
      <Modal
        isOpen={!!rejectingReq}
        onClose={() => !rejectingLoading && setRejectingReq(null)}
        title="Reject Subscription Request"
      >
        {rejectingReq && (
          <div className="space-y-4">
            <p className="text-sm text-text-secondary leading-relaxed">
              Are you sure you want to reject the subscription request from{" "}
              <strong className="text-text-primary">
                {rejectingReq.org_name || rejectingReq.organization_id}
              </strong>{" "}
              for{" "}
              <strong className="text-text-primary">
                {rejectingReq.plan_name || rejectingReq.plan_slug}
              </strong>{" "}
              (UTR: <span className="font-mono">{rejectingReq.utr_number}</span>)?
            </p>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-text-secondary">
                Rejection Reason (shown to customer)
              </label>
              <textarea
                className="w-full px-3 py-2 text-sm rounded-md border border-border bg-surface text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
                rows={3}
                placeholder="e.g. UTR number not found in bank statement, amount mismatch..."
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
              />
            </div>

            <p className="text-xs text-text-muted">
              The customer will be notified of the rejection and will be able to retry with a corrected UTR number.
            </p>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setRejectingReq(null)}
                disabled={rejectingLoading}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="danger"
                onClick={handleReject}
                loading={rejectingLoading}
              >
                Confirm Rejection
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
