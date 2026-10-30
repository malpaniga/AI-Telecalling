"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Receipt, CreditCard, FileText, ArrowUpRight, Clock, AlertCircle, Copy, CheckCircle2, X } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { Modal } from "@/components/ui/modal";
import { Spinner } from "@/components/ui/spinner";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import {
  api,
  Subscription,
  SubscriptionPlan,
  Invoice,
  Payment,
  BillingSettings,
  ManualSubscriptionRequest,
} from "@/lib/api";
import { loadRazorpayScript, openRazorpayCheckout } from "@/lib/razorpay";
import { formatDateTime, formatINR } from "@/lib/utils";
import toast from "react-hot-toast";

export default function BillingPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [settings, setSettings] = useState<BillingSettings | null>(null);
  const [manualRequests, setManualRequests] = useState<ManualSubscriptionRequest[]>([]);
  const [dismissedRejected, setDismissedRejected] = useState(false);

  const [loading, setLoading] = useState(true);
  const [loadingPlans, setLoadingPlans] = useState(false);
  const [showPlans, setShowPlans] = useState(false);
  const [changingPlan, setChangingPlan] = useState<string | null>(null);

  // Manual payment modal state
  const [showManualModal, setShowManualModal] = useState(false);
  const [selectedPlanForManual, setSelectedPlanForManual] = useState<SubscriptionPlan | null>(null);
  const [utrNumber, setUtrNumber] = useState("");
  const [payerNote, setPayerNote] = useState("");
  const [submittingManual, setSubmittingManual] = useState(false);
  const [cancellingRequestId, setCancellingRequestId] = useState<string | null>(null);

  const loadPlans = useCallback(async () => {
    setLoadingPlans(true);
    try {
      const p = await api.subscriptions.plans();
      setPlans(Array.isArray(p) ? p : []);
    } catch (e: unknown) {
      console.error("Failed to load plans:", e);
      toast.error(e instanceof Error ? e.message : "Failed to load subscription plans");
    } finally {
      setLoadingPlans(false);
    }
  }, []);

  const loadBillingData = useCallback(async () => {
    setLoading(true);
    try {
      const [subRes, plansRes, invRes, payRes, setRes, reqRes] = await Promise.allSettled([
        api.subscriptions.my(),
        api.subscriptions.plans(),
        api.billing.invoices({ limit: 20 }),
        api.billing.payments({ limit: 20 }),
        api.billing.getSettings(),
        api.billing.getMyManualRequests(),
      ]);

      if (subRes.status === "fulfilled" && subRes.value) {
        setSubscription(subRes.value);
      }
      if (plansRes.status === "fulfilled" && Array.isArray(plansRes.value)) {
        setPlans(plansRes.value);
      }
      if (invRes.status === "fulfilled" && Array.isArray(invRes.value)) {
        setInvoices(invRes.value);
      }
      if (payRes.status === "fulfilled" && Array.isArray(payRes.value)) {
        setPayments(payRes.value);
      }
      if (setRes.status === "fulfilled" && setRes.value) {
        setSettings(setRes.value);
      }
      if (reqRes.status === "fulfilled" && Array.isArray(reqRes.value)) {
        setManualRequests(reqRes.value);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBillingData();
  }, [loadBillingData]);

  // When modal is opened, if plans are empty, ensure they are loaded
  useEffect(() => {
    if (showPlans && plans.length === 0 && !loadingPlans) {
      loadPlans();
    }
  }, [showPlans, plans.length, loadingPlans, loadPlans]);

  // Handle plan selection button
  async function handleSelectPlan(plan: SubscriptionPlan) {
    if (settings?.payment_mode === "manual") {
      // Manual UPI mode: open UPI QR code modal
      setSelectedPlanForManual(plan);
      setUtrNumber("");
      setPayerNote("");
      setShowPlans(false);
      setShowManualModal(true);
      return;
    }

    // Automated Razorpay mode
    setChangingPlan(plan.id);
    try {
      const loaded = await loadRazorpayScript();
      if (!loaded) {
        throw new Error("Unable to load Razorpay payment gateway. Please check your internet connection.");
      }

      const order = await api.billing.createSubscriptionOrder(plan.id, "monthly");

      openRazorpayCheckout({
        key: settings?.razorpay_key_id || (order as { key_id?: string }).key_id || "",
        amount: order.amount_paise,
        currency: "INR",
        name: "NivCall Connect",
        description: `${plan.name} Plan Subscription`,
        order_id: order.provider_order_id,
        handler: async (response) => {
          toast.loading("Verifying payment...", { id: "rzp-verify" });
          try {
            await api.billing.verifyPayment({
              order_id: order.order_id,
              provider_payment_id: response.razorpay_payment_id,
              provider_order_id: response.razorpay_order_id,
              provider_signature: response.razorpay_signature,
            });
            toast.success("Subscription activated successfully!", { id: "rzp-verify" });
            setShowPlans(false);
            await loadBillingData();
          } catch (err: unknown) {
            toast.error(err instanceof Error ? err.message : "Payment verification failed", { id: "rzp-verify" });
          }
        },
        modal: {
          ondismiss: () => {
            setChangingPlan(null);
          },
        },
      });
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to initiate payment");
    } finally {
      setChangingPlan(null);
    }
  }

  // Handle manual request submission
  async function handleSubmitManualRequest(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedPlanForManual) return;
    if (!utrNumber.trim()) {
      toast.error("Please enter the 12-digit UPI / UTR Transaction ID");
      return;
    }

    setSubmittingManual(true);
    try {
      await api.billing.submitManualRequest({
        plan_id: selectedPlanForManual.id,
        billing_cycle: "monthly",
        utr_number: utrNumber.trim(),
        payer_note: payerNote.trim() || undefined,
      });
      toast.success("Payment details submitted! Admin will verify and activate your subscription.");
      setShowManualModal(false);
      setSelectedPlanForManual(null);
      await loadBillingData();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to submit payment request");
    } finally {
      setSubmittingManual(false);
    }
  }

  // Handle cancellation of pending request
  async function handleCancelManualRequest(requestId: string) {
    if (!confirm("Are you sure you want to cancel this pending payment request?")) return;
    setCancellingRequestId(requestId);
    try {
      await api.billing.cancelManualRequest(requestId);
      toast.success("Payment request cancelled.");
      await loadBillingData();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to cancel request");
    } finally {
      setCancellingRequestId(null);
    }
  }

  // Copy UPI ID helper
  function handleCopyUPI(upiId: string) {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(upiId);
      toast.success("UPI ID copied to clipboard!");
    }
  }

  async function handleCancel() {
    if (!confirm("Cancel subscription at period end?")) return;
    try {
      const res = await api.subscriptions.cancel(true);
      toast.success(`Subscription will cancel on ${res.current_period_end ?? "period end"}`);
      const updated = await api.subscriptions.my().catch(() => null);
      setSubscription(updated);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to cancel");
    }
  }

  if (loading) {
    return (
      <AppShell title="Billing">
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      </AppShell>
    );
  }

  const pendingRequest = manualRequests.find((r) => r.status === "pending");
  const latestRejectedRequest = !dismissedRejected
    ? manualRequests.find((r) => r.status === "rejected")
    : null;

  const adminUpiId = settings?.admin_upi_id || "nivcall@icici";
  const adminPayeeName = settings?.admin_payee_name || "NivCall Connect";
  const manualAmountPaise = selectedPlanForManual?.price_monthly_paise || 0;
  const manualAmountINR = manualAmountPaise / 100;
  const upiUri = `upi://pay?pa=${encodeURIComponent(adminUpiId)}&pn=${encodeURIComponent(adminPayeeName)}&am=${manualAmountINR}&cu=INR&tn=${encodeURIComponent(
    (selectedPlanForManual?.name || "Plan") + " Subscription"
  )}`;

  return (
    <AppShell title="Billing">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Billing & Subscription</h2>
          <p className="text-xs text-text-secondary mt-0.5">Manage your organization's subscription plan, invoices, and payments</p>
        </div>
      </div>

      {/* Pending Manual Verification Banner */}
      {pendingRequest && (
        <div className="mb-6 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 p-4 shadow-sm flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <Clock className="h-5 w-5 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-amber-900 dark:text-amber-200">
                Payment Verification Pending for {pendingRequest.plan_name} Plan
              </p>
              <p className="text-xs text-amber-800 dark:text-amber-300 mt-1 leading-relaxed">
                We received your payment submission of <strong>{formatINR(pendingRequest.amount_paise)}</strong> with Transaction / UTR ID:{" "}
                <code className="bg-amber-100 dark:bg-amber-900/60 px-1.5 py-0.5 rounded font-mono font-medium">
                  {pendingRequest.utr_number}
                </code>
                . Our team is verifying the payment and will activate your subscription shortly.
              </p>
            </div>
          </div>
          <Button
            size="sm"
            variant="ghost"
            className="text-xs text-amber-700 hover:text-danger shrink-0"
            loading={cancellingRequestId === pendingRequest.id}
            onClick={() => handleCancelManualRequest(pendingRequest.id)}
          >
            Cancel Request
          </Button>
        </div>
      )}

      {/* Rejected Alert Banner */}
      {latestRejectedRequest && (
        <div className="mb-6 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800/50 p-4 shadow-sm flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-red-900 dark:text-red-200">
                Payment Verification Rejected for {latestRejectedRequest.plan_name} Plan
              </p>
              <p className="text-xs text-red-800 dark:text-red-300 mt-1 leading-relaxed">
                Reason: {latestRejectedRequest.rejection_reason || "Payment could not be verified in bank records"}.
                You may choose a plan and re-submit your payment verification details.
              </p>
            </div>
          </div>
          <button
            onClick={() => setDismissedRejected(true)}
            className="text-red-400 hover:text-red-600 dark:hover:text-red-200 p-1"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Current subscription */}
      <Card className="mb-6">
        <CardHeader>
          <h3 className="text-sm font-medium text-text-primary">Current Plan</h3>
        </CardHeader>
        <CardBody>
          {!subscription || (subscription as { has_subscription?: boolean }).has_subscription === false ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-primary font-medium">No active subscription</p>
                <p className="text-text-secondary text-xs mt-0.5">Choose a subscription plan to unlock full AI calling features and concurrency.</p>
              </div>
              <Button size="sm" onClick={() => setShowPlans(true)}>Choose a Plan</Button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="font-medium text-text-primary capitalize">{subscription.plan_slug?.replace(/_/g, " ")} Plan</p>
                <div className="flex items-center gap-3 mt-1 text-sm text-text-secondary">
                  <StatusBadge status={subscription.status} />
                  <span>{subscription.billing_cycle}</span>
                  {subscription.current_period_end && (
                    <span>Renews {formatDateTime(subscription.current_period_end)}</span>
                  )}
                </div>
                {subscription.cancel_at_period_end && (
                  <p className="text-xs text-warning mt-1">Cancels at period end</p>
                )}
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => setShowPlans(true)}>
                  Change Plan
                </Button>
                {!subscription.cancel_at_period_end && (
                  <Button variant="ghost" size="sm" className="text-danger hover:text-danger" onClick={handleCancel}>
                    Cancel
                  </Button>
                )}
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Invoices */}
      <Card className="mb-6">
        <CardHeader><h3 className="text-sm font-medium text-text-primary">Invoices</h3></CardHeader>
        {invoices.length === 0 ? (
          <div className="px-6 py-6 text-sm text-text-muted">No invoices yet</div>
        ) : (
          <SimpleTable headers={["Invoice #", "Amount", "Status", "Date"]}>
            {invoices.map((inv) => (
              <TableRow key={inv.id}>
                <TableCell className="font-mono text-xs">{inv.invoice_number}</TableCell>
                <TableCell className="font-medium">{formatINR(inv.total_paise)}</TableCell>
                <TableCell><StatusBadge status={inv.status} /></TableCell>
                <TableCell className="text-xs text-text-muted">{formatDateTime(inv.issued_at)}</TableCell>
              </TableRow>
            ))}
          </SimpleTable>
        )}
      </Card>

      {/* Payments */}
      <Card>
        <CardHeader><h3 className="text-sm font-medium text-text-primary">Payment History</h3></CardHeader>
        {payments.length === 0 ? (
          <div className="px-6 py-6 text-sm text-text-muted">No payments yet</div>
        ) : (
          <SimpleTable headers={["Amount", "Status", "Paid On"]}>
            {payments.map((p) => (
              <TableRow key={p.id}>
                <TableCell className="font-medium">{formatINR(p.amount_paise)}</TableCell>
                <TableCell><StatusBadge status={p.status} /></TableCell>
                <TableCell className="text-xs text-text-muted">{formatDateTime(p.paid_at)}</TableCell>
              </TableRow>
            ))}
          </SimpleTable>
        )}
      </Card>

      {/* Plan selection modal */}
      <Modal isOpen={showPlans} onClose={() => setShowPlans(false)} title="Choose a Plan" size="lg">
        {loadingPlans ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Spinner size="lg" />
            <p className="text-sm text-text-muted">Loading subscription plans...</p>
          </div>
        ) : plans.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
            <p className="text-sm text-text-secondary">No subscription plans could be loaded.</p>
            <Button size="sm" variant="secondary" onClick={loadPlans}>
              Retry Loading Plans
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className={`border rounded-lg p-4 transition-colors flex flex-col justify-between ${
                  subscription?.plan_slug === plan.slug
                    ? "border-accent bg-accent-subtle"
                    : "border-border hover:border-accent"
                }`}
              >
                <div>
                  <p className="font-semibold text-text-primary">{plan.name}</p>
                  <p className="text-2xl font-bold text-accent mt-1">
                    {formatINR(plan.price_monthly_paise)}
                    <span className="text-sm font-normal text-text-muted">/mo</span>
                  </p>
                  {plan.description && (
                    <p className="text-xs text-text-secondary mt-1">{plan.description}</p>
                  )}
                  <ul className="mt-3 space-y-1 text-xs text-text-secondary">
                    <li>Up to {plan.max_agents} agents</li>
                    <li>Up to {plan.max_campaigns} campaigns</li>
                    <li>{plan.max_concurrent_calls} concurrent calls</li>
                    {plan.knowledge_base_enabled && <li>Knowledge base</li>}
                    {plan.api_access && <li>API access</li>}
                  </ul>
                </div>
                <Button
                  size="sm"
                  className="w-full mt-4"
                  variant={subscription?.plan_slug === plan.slug ? "secondary" : "primary"}
                  loading={changingPlan === plan.id}
                  disabled={subscription?.plan_slug === plan.slug || Boolean(pendingRequest)}
                  onClick={() => handleSelectPlan(plan)}
                >
                  {subscription?.plan_slug === plan.slug
                    ? "Current Plan"
                    : pendingRequest
                    ? "Verification Pending"
                    : "Select Plan"}
                </Button>
              </div>
            ))}
          </div>
        )}
      </Modal>

      {/* Manual UPI QR Payment Modal */}
      <Modal
        isOpen={showManualModal}
        onClose={() => setShowManualModal(false)}
        title="Pay via UPI QR Code"
        size="md"
      >
        {selectedPlanForManual && (
          <form onSubmit={handleSubmitManualRequest} className="space-y-4 pt-1">
            <div className="rounded-lg bg-surface-hover border border-border p-3 flex items-center justify-between">
              <div>
                <p className="text-xs text-text-muted">Selected Subscription Plan</p>
                <p className="text-sm font-semibold text-text-primary">{selectedPlanForManual.name} Plan (Monthly)</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-text-muted">Payable Amount</p>
                <p className="text-base font-bold text-accent">{formatINR(selectedPlanForManual.price_monthly_paise)}</p>
              </div>
            </div>

            {/* QR Code and UPI ID */}
            <div className="rounded-xl border border-border bg-surface p-4 flex flex-col items-center justify-center text-center">
              <div className="bg-white p-3 rounded-lg border border-border shadow-sm mb-3">
                <QRCodeSVG value={upiUri} size={150} level="M" />
              </div>
              <p className="text-xs font-semibold text-text-primary">Scan with Google Pay, PhonePe, Paytm, or BHIM</p>
              <div className="mt-2.5 flex items-center gap-2 bg-surface-hover px-3 py-1.5 rounded-md border border-border text-xs">
                <span className="text-text-muted">UPI ID:</span>
                <code className="font-mono font-semibold text-text-primary">{adminUpiId}</code>
                <button
                  type="button"
                  onClick={() => handleCopyUPI(adminUpiId)}
                  className="text-text-secondary hover:text-accent ml-1 p-0.5"
                  title="Copy UPI ID"
                >
                  <Copy className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            {/* UTR / Transaction ID input */}
            <div>
              <label className="block text-xs font-medium text-text-primary mb-1">
                UPI / Bank Transaction ID (UTR Number) <span className="text-danger">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. 429381729102"
                value={utrNumber}
                onChange={(e) => setUtrNumber(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-md border border-border bg-surface focus:outline-none focus:ring-1 focus:ring-accent"
              />
              <p className="text-[11px] text-text-muted mt-1">
                Enter the 12-digit UTR or Reference number found on your payment receipt.
              </p>
            </div>

            {/* Optional Note */}
            <div>
              <label className="block text-xs font-medium text-text-primary mb-1">
                Note / Payer Name (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. Paid from HDFC account ending in 4102"
                value={payerNote}
                onChange={(e) => setPayerNote(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-md border border-border bg-surface focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>

            <div className="flex gap-2 pt-2">
              <Button
                type="button"
                variant="secondary"
                className="w-1/3"
                onClick={() => setShowManualModal(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="w-2/3"
                loading={submittingManual}
              >
                Submit for Verification
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </AppShell>
  );
}
