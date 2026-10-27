"use client";

import React, { useEffect, useState } from "react";
import { CreditCard, Package, ArrowDownLeft, ArrowUpRight, Clock, ShieldCheck, Sparkles, HelpCircle } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Spinner } from "@/components/ui/spinner";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, WalletSummary, Transaction, CallingPack } from "@/lib/api";
import { formatDateTime, formatINR } from "@/lib/utils";
import toast from "react-hot-toast";

interface TrialStatus {
  free_tests_remaining: number;
  free_test_session_max_minutes: number;
  max_call_duration_minutes: number;
}

export default function CreditsPage() {
  const [wallet, setWallet] = useState<WalletSummary | null>(null);
  const [trialStatus, setTrialStatus] = useState<TrialStatus | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [packs, setPacks] = useState<CallingPack[]>([]);
  const [loading, setLoading] = useState(true);
  const [showBuy, setShowBuy] = useState(false);
  const [buyingPack, setBuyingPack] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.wallet.summary(),
      api.wallet.trialStatus().catch(() => ({
        free_tests_remaining: 10,
        free_test_session_max_minutes: 3,
        max_call_duration_minutes: 7,
      })),
      api.wallet.transactions({ limit: 50 }),
      api.wallet.packs(),
    ])
      .then(([w, ts, t, p]) => {
        setWallet(w);
        setTrialStatus(ts);
        setTransactions(t);
        setPacks(p);
      })
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load credits"))
      .finally(() => setLoading(false));
  }, []);

  async function handleBuyPack(packId: string) {
    setBuyingPack(packId);
    try {
      const order = await api.wallet.orderPack(packId);
      toast.success(`Order created: ${order.order_id}. Complete payment to receive minutes.`);
      setShowBuy(false);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create order");
    } finally {
      setBuyingPack(null);
    }
  }

  if (loading) {
    return (
      <AppShell title="Credits">
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      </AppShell>
    );
  }

  return (
    <AppShell title="Credits & Calling Minutes">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-xl font-semibold text-text-primary">Calling Minutes & Wallet</h2>
          <p className="text-sm text-text-secondary">
            Simple 1 credit = 1 billable minute. Never pay for seconds you don&apos;t understand.
          </p>
        </div>
        <Button onClick={() => setShowBuy(true)}>
          <Package className="h-4 w-4 mr-1.5" /> Buy Calling Packs
        </Button>
      </div>

      {/* Explainer Banner */}
      <div className="mb-6 rounded-lg bg-surface border border-border p-4 shadow-sm flex items-start gap-3">
        <Sparkles className="h-5 w-5 text-accent mt-0.5 shrink-0" />
        <div className="text-sm text-text-secondary leading-relaxed">
          <strong className="text-text-primary font-medium">How Calling Billing Works:</strong> Every 1 credit equals 1 minute of call time (rounded up to the next minute). Calls that do not connect (0 seconds) cost 0 credits. Initiating a phone call holds 5 credits temporarily to safeguard the call; any unspent credits return to your balance immediately upon disconnect.
        </div>
      </div>

      {/* Metric Cards */}
      {wallet && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <MetricCard
              label="Available Calling Time"
              value={`${wallet.available_credits.toLocaleString("en-IN")} mins`}
              icon={CreditCard}
              accent={wallet.is_low}
            />
            <MetricCard
              label="Active Live Holds"
              value={`${wallet.reserved_credits.toLocaleString("en-IN")} mins`}
              icon={Clock}
            />
            <MetricCard
              label="Free Browser Tests"
              value={`${trialStatus?.free_tests_remaining ?? 10} / 10 Left`}
              icon={ShieldCheck}
            />
            <MetricCard
              label="Total Minutes Consumed"
              value={`${wallet.total_consumed.toLocaleString("en-IN")} mins`}
              icon={Package}
            />
          </div>

          {wallet.is_low && (
            <div className="mb-6 rounded-md bg-[#FEF6E7] border border-[#F5D99A] px-4 py-3 text-sm text-warning flex items-center justify-between">
              <span>⚠ Low calling balance — your wallet has dropped below {wallet.low_threshold} minutes.</span>
              <Button size="sm" variant="secondary" onClick={() => setShowBuy(true)}>Top Up</Button>
            </div>
          )}
        </>
      )}

      {/* Detailed Activity & Receipt Ledger */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <div>
            <h3 className="text-base font-semibold text-text-primary">Calling Activity & Receipts</h3>
            <p className="text-xs text-text-muted mt-0.5">Itemized call durations, holds, refunds, and pack purchases</p>
          </div>
          <div className="text-xs text-text-muted bg-surface-hover px-2.5 py-1 rounded border border-border">
            1 credit = 1 minute
          </div>
        </CardHeader>
        {transactions.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-text-muted">No transactions recorded yet</div>
        ) : (
          <SimpleTable headers={["Activity / Event", "Details & Duration", "Cost / Change", "Hold Lifecycle", "Date", "Balance After"]}>
            {transactions.map((t) => {
              const isPositive = t.credits_delta > 0;
              const isZero = t.credits_delta === 0;

              let typeLabel = t.transaction_type.replace(/_/g, " ");
              let holdStatus = "Completed";

              if (t.transaction_type === "call_reserve") {
                typeLabel = "Call Hold";
                holdStatus = "5 min held";
              } else if (t.transaction_type === "call_settle") {
                typeLabel = "Call Finished";
                holdStatus = "Settled & released";
              } else if (t.transaction_type === "call_refund") {
                typeLabel = "Hold Released";
                holdStatus = "Returned to wallet";
              } else if (t.transaction_type === "calling_pack_purchase") {
                typeLabel = "Pack Purchase";
                holdStatus = "Direct top-up";
              } else if (t.transaction_type === "bonus") {
                typeLabel = "Bonus Granted";
                holdStatus = "Direct bonus";
              }

              return (
                <TableRow key={t.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {isPositive ? (
                        <div className="w-6 h-6 rounded-full bg-emerald-50 dark:bg-emerald-950/40 flex items-center justify-center shrink-0">
                          <ArrowDownLeft className="h-3.5 w-3.5 text-success" />
                        </div>
                      ) : isZero ? (
                        <div className="w-6 h-6 rounded-full bg-surface-hover flex items-center justify-center shrink-0">
                          <Clock className="h-3.5 w-3.5 text-text-muted" />
                        </div>
                      ) : (
                        <div className="w-6 h-6 rounded-full bg-rose-50 dark:bg-rose-950/40 flex items-center justify-center shrink-0">
                          <ArrowUpRight className="h-3.5 w-3.5 text-danger" />
                        </div>
                      )}
                      <div>
                        <span className="text-xs font-medium text-text-primary capitalize block">{typeLabel}</span>
                        {t.call_id && (
                          <span className="text-[11px] font-mono text-text-muted">#{t.call_id.slice(-8)}</span>
                        )}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-text-secondary max-w-sm">
                    {t.description || "—"}
                  </TableCell>
                  <TableCell className={`font-mono text-xs font-semibold ${isPositive ? "text-success" : isZero ? "text-text-muted" : "text-danger"}`}>
                    {isPositive ? `+${t.credits_delta} mins` : isZero ? "0 mins" : `${t.credits_delta} mins`}
                  </TableCell>
                  <TableCell>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-surface-hover border border-border text-text-secondary">
                      {holdStatus}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs text-text-muted whitespace-nowrap">
                    {formatDateTime(t.created_at)}
                  </TableCell>
                  <TableCell className="font-mono text-xs font-medium text-text-primary">
                    {t.balance_after.toLocaleString("en-IN")} mins
                  </TableCell>
                </TableRow>
              );
            })}
          </SimpleTable>
        )}
      </Card>

      {/* Buy credits modal */}
      <Modal isOpen={showBuy} onClose={() => setShowBuy(false)} title="Buy Calling Minutes" size="lg">
        {packs.length === 0 ? (
          <p className="text-sm text-text-muted">No calling packs available at this moment.</p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 pt-2">
            {packs.map((pack) => (
              <div key={pack.id} className="border border-border rounded-xl p-5 hover:border-accent hover:shadow-sm transition-all bg-surface flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <p className="font-semibold text-text-primary text-base">{pack.name}</p>
                    <p className="font-bold text-accent text-lg">{formatINR(pack.price_paise)}</p>
                  </div>
                  <div className="flex items-baseline gap-2 mb-2">
                    <span className="text-2xl font-bold text-text-primary">{pack.credits}</span>
                    <span className="text-sm text-text-secondary font-medium">Calling Minutes</span>
                    {pack.bonus_credits > 0 && (
                      <span className="text-xs font-semibold text-success bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-full">
                        +{pack.bonus_credits} bonus
                      </span>
                    )}
                  </div>
                  {pack.description && (
                    <p className="text-xs text-text-secondary mb-3 leading-relaxed">{pack.description}</p>
                  )}
                  <div className="flex items-center gap-1.5 text-xs text-text-muted mb-4">
                    <Clock className="h-3.5 w-3.5" />
                    <span>Valid for {pack.validity_days} days</span>
                  </div>
                </div>
                <Button
                  className="w-full"
                  loading={buyingPack === pack.id}
                  onClick={() => handleBuyPack(pack.id)}
                >
                  Buy {pack.credits} Minutes
                </Button>
              </div>
            ))}
          </div>
        )}
      </Modal>
    </AppShell>
  );
}
