"use client";

import React, { useEffect, useState, useCallback } from "react";
import { RefreshCw, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import toast from "react-hot-toast";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatINR } from "@/lib/utils";

type ProviderHealth = {
  provider: string;
  provider_type: string;
  status: string;
  success_rate: number;
  call_count: number;
  avg_latency_ms: number;
  [key: string]: unknown;
};

type HealthSummary = {
  overall_status: string;
  providers: ProviderHealth[];
  [key: string]: unknown;
};

type ProviderMetric = {
  provider: string;
  provider_type: string;
  success_rate: number;
  avg_latency_ms: number;
  call_count: number;
  total_cost_paise: number;
  [key: string]: unknown;
};

type LatencyStats = {
  avg_latency_ms: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  [key: string]: unknown;
};

type VoiceProfileHealth = {
  profile_id: string;
  display_name: string;
  status: string;
  [key: string]: unknown;
};

function statusIcon(status: string) {
  if (status === "healthy")
    return <CheckCircle2 className="h-4 w-4 text-success" />;
  if (status === "degraded")
    return <AlertTriangle className="h-4 w-4 text-warning" />;
  return <XCircle className="h-4 w-4 text-danger" />;
}

export default function AdminProvidersPage() {
  const [health, setHealth] = useState<HealthSummary | null>(null);
  const [metrics, setMetrics] = useState<ProviderMetric[]>([]);
  const [latency, setLatency] = useState<LatencyStats | null>(null);
  const [vpHealth, setVpHealth] = useState<VoiceProfileHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const [h, m, l, v] = await Promise.all([
        api.providerOps.health(),
        api.providerOps.metrics(),
        api.providerOps.latency(),
        api.providerOps.voiceProfiles(),
      ]);
      setHealth(h);
      setMetrics(m ?? []);
      setLatency(l);
      setVpHealth(v ?? []);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load provider data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">
            Provider Health
          </h2>
          {health && (
            <div className="flex items-center gap-1.5 mt-0.5">
              {statusIcon(health.overall_status)}
              <span className="text-sm text-text-secondary capitalize">
                Overall: {health.overall_status}
              </span>
            </div>
          )}
        </div>
        <Button
          size="sm"
          variant="secondary"
          loading={refreshing}
          onClick={() => load(true)}
        >
          <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
          Refresh
        </Button>
      </div>

      {/* Latency cards */}
      {latency && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <MetricCard
            label="Avg Latency"
            value={`${latency.avg_latency_ms ?? 0}ms`}
          />
          <MetricCard
            label="p50 Latency"
            value={`${latency.p50_ms ?? 0}ms`}
          />
          <MetricCard
            label="p95 Latency"
            value={`${latency.p95_ms ?? 0}ms`}
            accent={latency.p95_ms > 2000}
          />
          <MetricCard
            label="p99 Latency"
            value={`${latency.p99_ms ?? 0}ms`}
          />
        </div>
      )}

      {/* Per-provider health */}
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium text-text-primary">
            Provider Health (last 24h)
          </h3>
        </CardHeader>
        <CardBody>
          {!health?.providers?.length ? (
            <EmptyState
              icon={CheckCircle2}
              title="No provider events recorded"
              description="Provider health data appears once calls are processed"
            />
          ) : (
            <SimpleTable
              headers={[
                "Provider",
                "Type",
                "Status",
                "Success Rate",
                "Avg Latency",
                "Calls",
              ]}
            >
              {health.providers.map((p) => (
                <TableRow key={`${p.provider}-${p.provider_type}`}>
                  <TableCell className="font-medium">{p.provider}</TableCell>
                  <TableCell className="text-text-secondary capitalize">
                    {p.provider_type?.replace(/_/g, " ")}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      {statusIcon(p.status)}
                      <StatusBadge status={p.status} />
                    </div>
                  </TableCell>
                  <TableCell className="font-mono">
                    {(p.success_rate * 100).toFixed(1)}%
                  </TableCell>
                  <TableCell className="font-mono">
                    {p.avg_latency_ms ?? 0}ms
                  </TableCell>
                  <TableCell className="text-text-secondary">
                    {p.call_count.toLocaleString("en-IN")}
                  </TableCell>
                </TableRow>
              ))}
            </SimpleTable>
          )}
        </CardBody>
      </Card>

      {/* Per-provider metrics with cost */}
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium text-text-primary">
            Provider Metrics &amp; Cost
          </h3>
        </CardHeader>
        <CardBody>
          {metrics.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="No metrics recorded"
              description="Metrics appear once provider calls are processed"
            />
          ) : (
            <SimpleTable
              headers={[
                "Provider",
                "Type",
                "Calls",
                "Success Rate",
                "Avg Latency",
                "Total Cost",
              ]}
            >
              {metrics.map((m) => (
                <TableRow key={`${m.provider}-${m.provider_type}`}>
                  <TableCell className="font-medium">{m.provider}</TableCell>
                  <TableCell className="text-text-secondary capitalize">
                    {m.provider_type?.replace(/_/g, " ")}
                  </TableCell>
                  <TableCell className="text-text-secondary">
                    {m.call_count.toLocaleString("en-IN")}
                  </TableCell>
                  <TableCell className="font-mono">
                    {(m.success_rate * 100).toFixed(1)}%
                  </TableCell>
                  <TableCell className="font-mono">
                    {m.avg_latency_ms ?? 0}ms
                  </TableCell>
                  <TableCell className="font-medium">
                    {formatINR(m.total_cost_paise)}
                  </TableCell>
                </TableRow>
              ))}
            </SimpleTable>
          )}
        </CardBody>
      </Card>

      {/* Voice profile health */}
      <Card>
        <CardHeader>
          <h3 className="text-sm font-medium text-text-primary">
            Voice Profile Health
          </h3>
        </CardHeader>
        <CardBody>
          {vpHealth.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="No voice profile health data"
              description="Data appears once voice profiles are active"
            />
          ) : (
            <SimpleTable headers={["Profile", "Status"]}>
              {vpHealth.map((vp) => (
                <TableRow key={vp.profile_id}>
                  <TableCell className="font-medium">{vp.display_name}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      {statusIcon(vp.status)}
                      <StatusBadge status={vp.status} />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </SimpleTable>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
