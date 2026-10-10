"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  TrendingUp,
  DollarSign,
  Users,
  BarChart2,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import toast from "react-hot-toast";
import { MetricCard } from "@/components/ui/metric-card";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { formatINR } from "@/lib/utils";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

type MRRData = {
  mrr_paise: number;
  mrr_inr: number;
  arr_paise: number;
  arr_inr: number;
  arpu_paise: number;
  arpu_inr: number;
  active_subscriptions: number;
};

type MRRMovement = {
  new_mrr_paise: number;
  expansion_mrr_paise: number;
  churn_mrr_paise: number;
  net_new_mrr_paise: number;
  [key: string]: unknown;
};

type RevenueData = {
  subscription_revenue_paise: number;
  calling_revenue_paise: number;
  total_revenue_paise: number;
  provider_cost_paise: number;
  gross_profit_paise: number;
  gross_margin_pct: number;
};

type DailyEntry = {
  date: string;
  calls: number;
  credits_consumed: number;
  revenue_paise: number;
  provider_cost_paise: number;
};

const PERIOD_OPTIONS = [
  { label: "7 days", value: 7 },
  { label: "30 days", value: 30 },
  { label: "90 days", value: 90 },
];

export default function AdminAnalyticsPage() {
  const [mrr, setMrr] = useState<MRRData | null>(null);
  const [movement, setMovement] = useState<MRRMovement | null>(null);
  const [revenue, setRevenue] = useState<RevenueData | null>(null);
  const [daily, setDaily] = useState<DailyEntry[]>([]);
  const [period, setPeriod] = useState(30);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [mrrData, movData, revData, dailyData] = await Promise.all([
        api.analytics.mrr(),
        api.analytics.mrrMovement(),
        api.analytics.revenue(),
        api.analytics.daily(period),
      ]);
      setMrr(mrrData);
      setMovement(movData);
      setRevenue(revData);
      setDaily((dailyData.data ?? []) as DailyEntry[]);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  // Format daily data for charts — shorten date labels
  const chartData = daily.map((d) => ({
    ...d,
    dateLabel: d.date.slice(5), // MM-DD
    revenue_inr: d.revenue_paise / 100,
    cost_inr: d.provider_cost_paise / 100,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">
          Revenue Analytics
        </h2>
        <div className="flex gap-1.5">
          {PERIOD_OPTIONS.map((opt) => (
            <Button
              key={opt.value}
              size="sm"
              variant={period === opt.value ? "primary" : "secondary"}
              onClick={() => setPeriod(opt.value)}
            >
              {opt.label}
            </Button>
          ))}
        </div>
      </div>

      {/* MRR / ARR / ARPU cards */}
      {mrr && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <MetricCard
            label="Monthly Recurring Revenue"
            value={formatINR(mrr.mrr_paise)}
            icon={TrendingUp}
            accent
          />
          <MetricCard
            label="Annual Run Rate"
            value={formatINR(mrr.arr_paise)}
            icon={BarChart2}
          />
          <MetricCard
            label="Avg Revenue Per Org"
            value={formatINR(mrr.arpu_paise)}
            icon={DollarSign}
          />
          <MetricCard
            label="Active Subscriptions"
            value={mrr.active_subscriptions.toLocaleString("en-IN")}
            icon={Users}
          />
        </div>
      )}

      {/* MRR Movement */}
      {movement && (
        <Card>
          <CardHeader>
            <h3 className="text-sm font-medium text-text-primary">
              MRR Movement (this period)
            </h3>
          </CardHeader>
          <CardBody>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {[
                {
                  label: "New MRR",
                  value: movement.new_mrr_paise as number,
                  positive: true,
                },
                {
                  label: "Expansion MRR",
                  value: movement.expansion_mrr_paise as number,
                  positive: true,
                },
                {
                  label: "Churned MRR",
                  value: movement.churn_mrr_paise as number,
                  positive: false,
                },
                {
                  label: "Net New MRR",
                  value: movement.net_new_mrr_paise as number,
                  positive: (movement.net_new_mrr_paise as number) >= 0,
                },
              ].map(({ label, value, positive }) => (
                <div key={label} className="space-y-1">
                  <p className="text-xs text-text-muted uppercase tracking-wide">
                    {label}
                  </p>
                  <div className="flex items-center gap-1">
                    {positive ? (
                      <ArrowUpRight className="h-4 w-4 text-success shrink-0" />
                    ) : (
                      <ArrowDownRight className="h-4 w-4 text-danger shrink-0" />
                    )}
                    <span className="text-lg font-semibold text-text-primary">
                      {formatINR(value)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Revenue breakdown */}
      {revenue && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <h3 className="text-sm font-medium text-text-primary">
                Revenue Breakdown
              </h3>
            </CardHeader>
            <CardBody className="space-y-3 text-sm">
              {[
                [
                  "Subscription Revenue",
                  revenue.subscription_revenue_paise,
                  "text-text-primary",
                ],
                [
                  "Calling Revenue",
                  revenue.calling_revenue_paise,
                  "text-text-primary",
                ],
                [
                  "Total Revenue",
                  revenue.total_revenue_paise,
                  "text-accent font-semibold",
                ],
                [
                  "Provider Cost",
                  revenue.provider_cost_paise,
                  "text-danger",
                ],
                [
                  "Gross Profit",
                  revenue.gross_profit_paise,
                  "text-success font-semibold",
                ],
              ].map(([label, value, cls]) => (
                <div
                  key={label as string}
                  className="flex items-center justify-between"
                >
                  <span className="text-text-muted">{label as string}</span>
                  <span className={String(cls)}>
                    {formatINR(value as number)}
                  </span>
                </div>
              ))}
              <div className="flex items-center justify-between pt-1 border-t border-border">
                <span className="text-text-muted">Gross Margin</span>
                <span className="font-semibold text-success">
                  {revenue.gross_margin_pct.toFixed(1)}%
                </span>
              </div>
            </CardBody>
          </Card>

          {/* Revenue bar chart */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <h3 className="text-sm font-medium text-text-primary">
                Revenue vs Cost — last {period} days
              </h3>
            </CardHeader>
            <CardBody>
              {chartData.length === 0 ? (
                <p className="text-sm text-text-muted py-8 text-center">
                  No data for this period
                </p>
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={chartData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="var(--color-border)"
                    />
                    <XAxis
                      dataKey="dateLabel"
                      tick={{ fontSize: 11 }}
                      stroke="var(--color-text-muted)"
                    />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      stroke="var(--color-text-muted)"
                      tickFormatter={(v) => `₹${(v / 100).toFixed(0)}`}
                    />
                    <Tooltip
                      formatter={(v) => formatINR(typeof v === "number" ? v : 0)}
                      contentStyle={{
                        background: "var(--color-surface)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-md)",
                        fontSize: 12,
                      }}
                    />
                    <Legend />
                    <Bar
                      dataKey="revenue_paise"
                      name="Revenue"
                      fill="var(--color-accent)"
                      radius={[3, 3, 0, 0]}
                    />
                    <Bar
                      dataKey="cost_inr"
                      name="Cost (INR)"
                      fill="var(--color-danger)"
                      radius={[3, 3, 0, 0]}
                      opacity={0.7}
                    />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardBody>
          </Card>
        </div>
      )}

      {/* Daily calls + credits chart */}
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium text-text-primary">
            Daily Calls &amp; Credits — last {period} days
          </h3>
        </CardHeader>
        <CardBody>
          {chartData.length === 0 ? (
            <p className="text-sm text-text-muted py-8 text-center">
              No data for this period
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--color-border)"
                />
                <XAxis
                  dataKey="dateLabel"
                  tick={{ fontSize: 11 }}
                  stroke="var(--color-text-muted)"
                />
                <YAxis
                  yAxisId="calls"
                  tick={{ fontSize: 11 }}
                  stroke="var(--color-text-muted)"
                />
                <YAxis
                  yAxisId="credits"
                  orientation="right"
                  tick={{ fontSize: 11 }}
                  stroke="var(--color-text-muted)"
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--color-surface)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-md)",
                    fontSize: 12,
                  }}
                />
                <Legend />
                <Line
                  yAxisId="calls"
                  type="monotone"
                  dataKey="calls"
                  name="Calls"
                  stroke="var(--color-accent)"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  yAxisId="credits"
                  type="monotone"
                  dataKey="credits_consumed"
                  name="Credits"
                  stroke="var(--color-info)"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
