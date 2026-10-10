"use client";

import React, { useEffect, useState } from "react";
import { BarChart2, TrendingUp } from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend,
} from "recharts";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Select } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import toast from "react-hot-toast";

type DailyRow = { date: string; calls_total: number; calls_qualified: number; credits_consumed: number };
type Totals = { calls: number; qualified: number; qualified_rate_pct: number; credits_consumed: number };

export default function AnalyticsPage() {
  const [daily, setDaily] = useState<DailyRow[]>([]);
  const [totals, setTotals] = useState<Totals | null>(null);
  const [days, setDays] = useState("30");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.dashboard.analytics(parseInt(days))
      .then((data) => { setDaily(data.daily); setTotals(data.totals); })
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load analytics"))
      .finally(() => setLoading(false));
  }, [days]);

  const chartData = daily.map((d) => ({
    date: formatDate(d.date, "dd MMM"),
    "Total Calls": d.calls_total,
    "Qualified": d.calls_qualified,
    "Credits": d.credits_consumed,
  }));

  return (
    <AppShell title="Analytics">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Call Analytics</h2>
        </div>
        <Select
          value={days}
          onChange={(e) => setDays(e.target.value)}
          options={[
            { value: "7", label: "Last 7 days" },
            { value: "30", label: "Last 30 days" },
            { value: "90", label: "Last 90 days" },
          ]}
          className="w-40"
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : (
        <div className="space-y-6">
          {totals && (
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <MetricCard label="Total Calls" value={totals.calls.toLocaleString("en-IN")} icon={BarChart2} />
              <MetricCard label="Qualified" value={totals.qualified.toLocaleString("en-IN")} icon={TrendingUp} accent />
              <MetricCard label="Qualified Rate" value={`${totals.qualified_rate_pct}%`} />
              <MetricCard label="Credits Used" value={totals.credits_consumed.toLocaleString("en-IN")} />
            </div>
          )}

          <Card>
            <CardHeader><h3 className="text-sm font-medium text-text-primary">Call Volume</h3></CardHeader>
            <CardBody>
              {chartData.length === 0 ? (
                <p className="text-sm text-text-muted text-center py-8">No data for this period</p>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--color-text-muted)" }} />
                    <YAxis tick={{ fontSize: 11, fill: "var(--color-text-muted)" }} />
                    <Tooltip
                      contentStyle={{
                        background: "var(--color-surface)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-md)",
                        fontSize: 12,
                      }}
                    />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="Total Calls"
                      stroke="var(--color-info)"
                      fill="rgba(57,117,184,0.1)"
                      strokeWidth={2}
                    />
                    <Area
                      type="monotone"
                      dataKey="Qualified"
                      stroke="var(--color-success)"
                      fill="rgba(40,125,85,0.1)"
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader><h3 className="text-sm font-medium text-text-primary">Credits Consumed</h3></CardHeader>
            <CardBody>
              {chartData.length === 0 ? (
                <p className="text-sm text-text-muted text-center py-8">No data for this period</p>
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--color-text-muted)" }} />
                    <YAxis tick={{ fontSize: 11, fill: "var(--color-text-muted)" }} />
                    <Tooltip
                      contentStyle={{
                        background: "var(--color-surface)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-md)",
                        fontSize: 12,
                      }}
                    />
                    <Bar dataKey="Credits" fill="var(--color-accent)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardBody>
          </Card>
        </div>
      )}
    </AppShell>
  );
}
