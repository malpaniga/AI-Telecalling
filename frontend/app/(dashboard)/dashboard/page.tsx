"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Phone, Users, Megaphone, CreditCard,
  Calendar, TrendingUp, ArrowRight,
} from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { MetricCard } from "@/components/ui/metric-card";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { api, DashboardData } from "@/lib/api";
import { formatDateTime, formatDuration, formatCredits } from "@/lib/utils";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboard.summary()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <AppShell title="Dashboard">
      {error && (
        <div className="mb-4 rounded-md bg-[#FDEEEE] border border-[#F2C0C0] px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      {!data ? (
        <div className="flex items-center justify-center py-20">
          <Spinner size="lg" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Metric row */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard
              label="Total Calls"
              value={data.calls.total.toLocaleString("en-IN")}
              icon={Phone}
              accent
            />
            <MetricCard
              label="Connected Rate"
              value={`${data.calls.connected_rate_pct}%`}
              icon={TrendingUp}
            />
            <MetricCard
              label="Total Leads"
              value={data.leads.total.toLocaleString("en-IN")}
              icon={Users}
            />
            <MetricCard
              label="Available Credits"
              value={formatCredits(data.credits.available_credits)}
              icon={CreditCard}
              accent={data.credits.is_low}
            />
          </div>

          {/* Campaigns + Leads row */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {/* Running campaigns */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-text-primary flex items-center gap-2">
                    <Megaphone className="h-4 w-4 text-text-muted" />
                    Campaigns
                  </h3>
                  <Link href="/campaigns">
                    <Button variant="ghost" size="sm" className="gap-1 text-xs">
                      View all <ArrowRight className="h-3 w-3" />
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardBody className="pt-2">
                <div className="grid grid-cols-3 gap-2 mb-4">
                  {Object.entries(data.campaigns.by_status).map(([s, c]) => (
                    <div key={s} className="text-center">
                      <p className="text-lg font-semibold text-text-primary">{c}</p>
                      <p className="text-xs text-text-muted capitalize">{s}</p>
                    </div>
                  ))}
                </div>
                {data.campaigns.running_campaigns.length > 0 ? (
                  <div className="space-y-2">
                    {data.campaigns.running_campaigns.map((c) => (
                      <div key={c.id} className="flex items-center justify-between text-sm border border-border rounded-md px-3 py-2">
                        <span className="text-text-primary truncate mr-2">{c.name}</span>
                        <span className="text-xs text-text-muted whitespace-nowrap">
                          {c.leads_dialed}/{c.leads_completed}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-text-muted">No running campaigns</p>
                )}
              </CardBody>
            </Card>

            {/* Lead pipeline */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-text-primary flex items-center gap-2">
                    <Users className="h-4 w-4 text-text-muted" />
                    Lead Pipeline
                  </h3>
                  <Link href="/leads">
                    <Button variant="ghost" size="sm" className="gap-1 text-xs">
                      View all <ArrowRight className="h-3 w-3" />
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardBody className="pt-2 space-y-2">
                {[
                  { label: "New", value: data.leads.new, color: "bg-info" },
                  { label: "Qualified", value: data.leads.qualified, color: "bg-success" },
                  { label: "Callback", value: data.leads.callback, color: "bg-warning" },
                  { label: "Not Interested", value: data.leads.not_interested, color: "bg-danger" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="flex items-center gap-2">
                    <span className="w-24 text-xs text-text-secondary">{label}</span>
                    <div className="flex-1 h-2 bg-surface-subtle rounded-full overflow-hidden">
                      <div
                        className={`h-full ${color} rounded-full`}
                        style={{ width: data.leads.total ? `${(value / data.leads.total) * 100}%` : "0%" }}
                      />
                    </div>
                    <span className="text-xs font-medium text-text-primary w-8 text-right">{value}</span>
                  </div>
                ))}
                <p className="text-xs text-text-muted pt-1">
                  Avg score: <span className="font-medium text-text-primary">{data.leads.avg_score}</span>
                </p>
              </CardBody>
            </Card>

            {/* Upcoming appointments */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-text-primary flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-text-muted" />
                    Upcoming
                  </h3>
                  <Link href="/appointments">
                    <Button variant="ghost" size="sm" className="gap-1 text-xs">
                      View all <ArrowRight className="h-3 w-3" />
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardBody className="pt-2 space-y-3">
                {data.upcoming_appointments.length === 0 ? (
                  <p className="text-sm text-text-muted">No upcoming appointments</p>
                ) : (
                  data.upcoming_appointments.map((a) => (
                    <div key={a.id} className="border-l-2 border-accent pl-3">
                      <p className="text-sm font-medium text-text-primary truncate">
                        {a.lead_name ?? a.title ?? "Appointment"}
                      </p>
                      <p className="text-xs text-text-secondary">
                        {formatDateTime(a.scheduled_at)}
                      </p>
                    </div>
                  ))
                )}
              </CardBody>
            </Card>
          </div>

          {/* Recent calls */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-text-primary flex items-center gap-2">
                  <Phone className="h-4 w-4 text-text-muted" />
                  Recent Calls
                </h3>
                <Link href="/calls">
                  <Button variant="ghost" size="sm" className="gap-1 text-xs">
                    View all <ArrowRight className="h-3 w-3" />
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-4 py-2 text-left text-xs font-medium text-text-muted">Number</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-text-muted">Status</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-text-muted">Outcome</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-text-muted">Duration</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-text-muted">When</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_calls.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-text-muted text-sm">
                        No calls yet
                      </td>
                    </tr>
                  ) : (
                    data.recent_calls.map((c) => (
                      <tr key={c.id} className="border-b border-border last:border-b-0 hover:bg-surface-subtle">
                        <td className="px-4 py-3 font-mono text-xs text-text-primary">{c.to_number}</td>
                        <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                        <td className="px-4 py-3">
                          {c.outcome ? <StatusBadge status={c.outcome} /> : <span className="text-text-muted">—</span>}
                        </td>
                        <td className="px-4 py-3 text-text-secondary">{formatDuration(c.duration_s)}</td>
                        <td className="px-4 py-3 text-text-muted text-xs">{formatDateTime(c.started_at)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </AppShell>
  );
}
