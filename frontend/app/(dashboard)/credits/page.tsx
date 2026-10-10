"use client";

import React, { useEffect, useState } from "react";
import { CreditCard, Package, ArrowDownLeft, ArrowUpRight } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Spinner } from "@/components/ui/spinner";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, WalletSummary, Transaction, CallingPack } from "@/lib/api";
import { formatDateTime, formatCredits, formatINR } from "@/lib/utils";
import toast from "react-hot-toast";

export default function CreditsPage() {
  const [wallet, setWallet] = useState<WalletSummary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [packs, setPacks] = useState<CallingPack[]>([]);
  const [loading, setLoading] = useState(true);
  const [showBuy, setShowBuy] = useState(false);
  const [buyingPack, setBuyingPack] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.wallet.summary(),
      api.wallet.transactions({ limit: 50 }),
      api.wallet.packs(),
    ])
      .then(([w, t, p]) => { setWallet(w); setTransactions(t); setPacks(p); })
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  async function handleBuyPack(packId: string) {
    setBuyingPack(packId);
    try {
      const order = await api.wallet.orderPack(packId);
      // In production: integrate Razorpay checkout here
      toast.success(`Order created: ${order.order_id}. Complete payment to receive credits.`);
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
    <AppShell title="Credits">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Calling Credits</h2>
          <p className="text-sm text-text-secondary">Manage your calling credits and purchase history</p>
        </div>
        <Button onClick={() => setShowBuy(true)}>
          <Package className="h-4 w-4 mr-1" /> Buy Credits
        </Button>
      </div>

      {wallet && (
        <>
          <div className="grid grid-cols-2 gap-4 mb-6 lg:grid-cols-4">
            <MetricCard
              label="Available"
              value={formatCredits(wallet.available_credits)}
              icon={CreditCard}
              accent={wallet.is_low}
            />
            <MetricCard
              label="Reserved"
              value={formatCredits(wallet.reserved_credits)}
            />
            <MetricCard
              label="Total Purchased"
              value={formatCredits(wallet.total_purchased)}
            />
            <MetricCard
              label="Total Consumed"
              value={formatCredits(wallet.total_consumed)}
            />
          </div>

          {wallet.is_low && (
            <div className="mb-4 rounded-md bg-[#FEF6E7] border border-[#F5D99A] px-4 py-3 text-sm text-warning">
              ⚠ Low credits — below threshold of {formatCredits(wallet.low_threshold)}
            </div>
          )}
        </>
      )}

      {/* Transactions */}
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium text-text-primary">Transaction History</h3>
        </CardHeader>
        {transactions.length === 0 ? (
          <div className="px-6 py-8 text-center text-sm text-text-muted">No transactions yet</div>
        ) : (
          <SimpleTable headers={["Type", "Credits", "Balance After", "Description", "Date"]}>
            {transactions.map((t) => (
              <TableRow key={t.id}>
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    {t.credits_delta > 0 ? (
                      <ArrowDownLeft className="h-3.5 w-3.5 text-success" />
                    ) : (
                      <ArrowUpRight className="h-3.5 w-3.5 text-danger" />
                    )}
                    <span className="text-xs capitalize">{t.transaction_type.replace(/_/g, " ")}</span>
                  </div>
                </TableCell>
                <TableCell className={`font-mono font-medium ${t.credits_delta > 0 ? "text-success" : "text-danger"}`}>
                  {t.credits_delta > 0 ? "+" : ""}{t.credits_delta.toLocaleString("en-IN")}
                </TableCell>
                <TableCell className="font-mono text-text-secondary">
                  {t.balance_after.toLocaleString("en-IN")}
                </TableCell>
                <TableCell className="text-text-secondary max-w-xs truncate">{t.description}</TableCell>
                <TableCell className="text-xs text-text-muted whitespace-nowrap">{formatDateTime(t.created_at)}</TableCell>
              </TableRow>
            ))}
          </SimpleTable>
        )}
      </Card>

      {/* Buy credits modal */}
      <Modal isOpen={showBuy} onClose={() => setShowBuy(false)} title="Buy Calling Credits" size="lg">
        {packs.length === 0 ? (
          <p className="text-sm text-text-muted">No calling packs available</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {packs.map((pack) => (
              <div key={pack.id} className="border border-border rounded-lg p-4 hover:border-accent transition-colors">
                <div className="flex justify-between items-start mb-2">
                  <p className="font-medium text-text-primary">{pack.name}</p>
                  <p className="font-semibold text-accent">{formatINR(pack.price_paise)}</p>
                </div>
                <p className="text-sm text-text-secondary mb-1">
                  {formatCredits(pack.credits)} credits
                  {pack.bonus_credits > 0 && (
                    <span className="text-success ml-1">+{formatCredits(pack.bonus_credits)} bonus</span>
                  )}
                </p>
                {pack.description && (
                  <p className="text-xs text-text-muted mb-3">{pack.description}</p>
                )}
                <p className="text-xs text-text-muted mb-3">Valid {pack.validity_days} days</p>
                <Button
                  size="sm"
                  className="w-full"
                  loading={buyingPack === pack.id}
                  onClick={() => handleBuyPack(pack.id)}
                >
                  Buy Pack
                </Button>
              </div>
            ))}
          </div>
        )}
      </Modal>
    </AppShell>
  );
}
