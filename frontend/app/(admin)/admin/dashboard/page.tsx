"use client";

import React, { useEffect, useState } from "react";
import { Building2, CreditCard, TrendingUp, Users } from "lucide-react";
import { MetricCard } from "@/components/ui/metric-card";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { api, AdminDashboard } from "@/lib/api";
import { formatDateTime, formatINR } from "@/lib/utils";
import toast from "react-hot-toast";

export default function AdminDashboardPage() {
  const [data, setData] = useState<AdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.admin.dashboard()
      .then(setData)
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-text-primary">Platform Overview</h2>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard
          label="Active Orgs"
          value={data.organizations.total_active.toLocaleString("en-IN")}
          icon={Building2}
          accent
        />
        <MetricCard
          label="Active Subs"
          value={data.subscriptions.active.toLocaleString("en-IN")}
          icon={CreditCard}
        />
        <MetricCard
          label="Total Revenue"
          value={formatINR(data.usage.total_charge_paise)}
          icon={TrendingUp}
        />
        <MetricCard
          label="Gross Profit"
          value={formatINR(data.usage.gross_profit_paise)}
          icon={Users}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Subscription breakdown */}
        <Card>
          <CardHeader><h3 className="text-sm font-medium text-text-primary">Subscriptions by Status</h3></CardHeader>
          <CardBody className="space-y-2">
            {Object.entries(data.subscriptions.by_status).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between">
                <StatusBadge status={status} />
                <span className="font-medium text-text-primary">{count}</span>
              </div>
            ))}
          </CardBody>
        </Card>

        {/* Recent orgs */}
        <Card>
          <CardHeader><h3 className="text-sm font-medium text-text-primary">Recent Organisations</h3></CardHeader>
          <CardBody className="space-y-3">
            {data.organizations.recent.map((org) => (
              <div key={org.id} className="flex items-center justify-between text-sm">
                <span className="text-text-primary">{org.name}</span>
                <div className="flex items-center gap-2">
                  <StatusBadge status={org.status} />
                  <span className="text-xs text-text-muted">{formatDateTime(org.created_at)}</span>
                </div>
              </div>
            ))}
          </CardBody>
        </Card>

        {/* Usage */}
        <Card className="lg:col-span-2">
          <CardHeader><h3 className="text-sm font-medium text-text-primary">Platform Usage</h3></CardHeader>
          <CardBody>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-sm">
              <div>
                <p className="text-text-muted text-xs uppercase tracking-wide">Events</p>
                <p className="text-xl font-semibold text-text-primary mt-1">{data.usage.total_events.toLocaleString("en-IN")}</p>
              </div>
              <div>
                <p className="text-text-muted text-xs uppercase tracking-wide">Credits Used</p>
                <p className="text-xl font-semibold text-text-primary mt-1">{data.usage.total_credits.toLocaleString("en-IN")}</p>
              </div>
              <div>
                <p className="text-text-muted text-xs uppercase tracking-wide">Revenue</p>
                <p className="text-xl font-semibold text-accent mt-1">{formatINR(data.usage.total_charge_paise)}</p>
              </div>
              <div>
                <p className="text-text-muted text-xs uppercase tracking-wide">Provider Cost</p>
                <p className="text-xl font-semibold text-text-primary mt-1">{formatINR(data.usage.total_provider_cost_paise)}</p>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
