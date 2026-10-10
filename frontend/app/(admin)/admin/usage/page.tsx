"use client";

import React, { useEffect, useState } from "react";
import { Activity } from "lucide-react";
import toast from "react-hot-toast";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Spinner } from "@/components/ui/spinner";
import { api } from "@/lib/api";
import { formatINR } from "@/lib/utils";

interface UsageSummary {
  total_events?: number;
  total_credits_consumed?: number;
  total_customer_charge_paise?: number;
  total_provider_cost_paise?: number;
  gross_profit_paise?: number;
  gross_margin_pct?: number;
  [key: string]: unknown;
}

export default function AdminUsagePage() {
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [revenue, setRevenue] = useState<Record<string, number> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.admin.usage(),
      api.admin.revenue(),
    ])
      .then(([u, r]) => { setUsage(u as UsageSummary); setRevenue(r as Record<string, number>); })
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-text-primary">Platform Usage & Revenue</h2>

      {revenue && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <MetricCard label="Subscription Revenue" value={formatINR(revenue.subscription_revenue_paise)} accent />
          <MetricCard label="Calling Revenue" value={formatINR(revenue.calling_revenue_paise)} />
          <MetricCard label="Total Revenue" value={formatINR(revenue.total_revenue_paise)} />
          <MetricCard label="Gross Margin" value={usage?.gross_margin_pct != null ? `${(usage.gross_margin_pct as number).toFixed(1)}%` : "—"} />
        </div>
      )}

      {usage && (
        <Card>
          <CardHeader><h3 className="text-sm font-medium text-text-primary">Calling Usage</h3></CardHeader>
          <CardBody>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 text-sm">
              {[
                ["Total Events", usage.total_events],
                ["Credits Consumed", usage.total_credits_consumed],
                ["Customer Charges", usage.total_customer_charge_paise != null ? formatINR(usage.total_customer_charge_paise as number) : null],
                ["Provider Cost", usage.total_provider_cost_paise != null ? formatINR(usage.total_provider_cost_paise as number) : null],
                ["Gross Profit", usage.gross_profit_paise != null ? formatINR(usage.gross_profit_paise as number) : null],
              ].map(([label, value]) => value != null && (
                <div key={label as string}>
                  <p className="text-text-muted text-xs uppercase tracking-wide">{label}</p>
                  <p className="text-lg font-semibold text-text-primary mt-1">{String(value)}</p>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
