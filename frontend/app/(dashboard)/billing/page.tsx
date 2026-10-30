"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Receipt, CreditCard, FileText, ArrowUpRight } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { Modal } from "@/components/ui/modal";
import { Spinner } from "@/components/ui/spinner";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, Subscription, SubscriptionPlan, Invoice, Payment } from "@/lib/api";
import { formatDateTime, formatINR } from "@/lib/utils";
import toast from "react-hot-toast";

export default function BillingPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingPlans, setLoadingPlans] = useState(false);
  const [showPlans, setShowPlans] = useState(false);
  const [changingPlan, setChangingPlan] = useState<string | null>(null);

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
      const [subRes, plansRes, invRes, payRes] = await Promise.allSettled([
        api.subscriptions.my(),
        api.subscriptions.plans(),
        api.billing.invoices({ limit: 20 }),
        api.billing.payments({ limit: 20 }),
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

  async function handleChangePlan(planId: string) {
    setChangingPlan(planId);
    try {
      const order = await api.billing.createSubscriptionOrder(planId, "monthly");
      // In production: open Razorpay checkout here, then call verify
      toast.success(`Order created: ${order.order_id}. Complete payment to activate.`);
      setShowPlans(false);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create order");
    } finally {
      setChangingPlan(null);
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

  return (
    <AppShell title="Billing">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-text-primary">Billing & Subscription</h2>
      </div>

      {/* Current subscription */}
      <Card className="mb-6">
        <CardHeader>
          <h3 className="text-sm font-medium text-text-primary">Current Plan</h3>
        </CardHeader>
        <CardBody>
          {!subscription || (subscription as { has_subscription?: boolean }).has_subscription === false ? (
            <div className="flex items-center justify-between">
              <p className="text-text-secondary text-sm">No active subscription</p>
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
                className={`border rounded-lg p-4 transition-colors ${
                  subscription?.plan_slug === plan.slug
                    ? "border-accent bg-accent-subtle"
                    : "border-border hover:border-accent"
                }`}
              >
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
                <Button
                  size="sm"
                  className="w-full mt-4"
                  variant={subscription?.plan_slug === plan.slug ? "secondary" : "primary"}
                  loading={changingPlan === plan.id}
                  disabled={subscription?.plan_slug === plan.slug}
                  onClick={() => handleChangePlan(plan.id)}
                >
                  {subscription?.plan_slug === plan.slug ? "Current Plan" : "Select Plan"}
                </Button>
              </div>
            ))}
          </div>
        )}
      </Modal>
    </AppShell>
  );
}
