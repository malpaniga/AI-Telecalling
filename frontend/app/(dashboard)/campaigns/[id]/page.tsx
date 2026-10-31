"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ChevronLeft,
  Play,
  Pause,
  StopCircle,
  RefreshCw,
  Phone,
  Users,
  Clock,
  Edit2,
  AlertTriangle,
} from "lucide-react";
import toast from "react-hot-toast";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { api, Campaign, CampaignStats } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import {
  CallingHoursModal,
  DAY_OPTIONS,
} from "@/components/campaigns/calling-hours-modal";

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [stats, setStats] = useState<CampaignStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [editCallingHoursOpen, setEditCallingHoursOpen] = useState(false);
  const [preflightFailure, setPreflightFailure] = useState<{
    message: string;
    isCallingHours: boolean;
  } | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [c, s] = await Promise.all([
        api.campaigns.get(id),
        api.campaigns.stats(id).catch(() => null),
      ]);
      setCampaign(c);
      setStats(s);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load campaign");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  async function action(fn: () => Promise<Campaign>, label: string) {
    setActing(true);
    try {
      const updated = await fn();
      setCampaign(updated);
      toast.success(`Campaign ${label}`);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : `Failed to ${label}`);
    } finally {
      setActing(false);
    }
  }

  async function handleStart(skipPreflight = false) {
    if (!campaign) return;
    setActing(true);
    try {
      const updated = await api.campaigns.start(campaign.id, skipPreflight);
      setCampaign(updated);
      setPreflightFailure(null);
      toast.success("Campaign started");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to start campaign";
      const isHours =
        msg.toLowerCase().includes("calling_hours") ||
        msg.toLowerCase().includes("calling day") ||
        msg.toLowerCase().includes("calling window");
      setPreflightFailure({
        message: msg,
        isCallingHours: isHours,
      });
      toast.error(msg);
    } finally {
      setActing(false);
    }
  }

  if (loading) {
    return (
      <AppShell title="Campaign">
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      </AppShell>
    );
  }

  if (!campaign) return null;

  return (
    <AppShell
      title={campaign.name}
      breadcrumb={[{ label: "Campaigns", href: "/campaigns" }, { label: campaign.name }]}
    >
      <div className="mb-4 flex items-center justify-between">
        <Link href="/campaigns">
          <Button variant="ghost" size="sm" className="gap-1 text-text-secondary">
            <ChevronLeft className="h-4 w-4" /> Back
          </Button>
        </Link>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
          {campaign.status === "draft" && (
            <Button size="sm" loading={acting} onClick={() => handleStart(false)}>
              <Play className="h-4 w-4 mr-1" /> Start
            </Button>
          )}
          {campaign.status === "running" && (
            <Button size="sm" variant="secondary" loading={acting} onClick={() => action(() => api.campaigns.pause(campaign.id), "paused")}>
              <Pause className="h-4 w-4 mr-1" /> Pause
            </Button>
          )}
          {campaign.status === "paused" && (
            <Button size="sm" loading={acting} onClick={() => action(() => api.campaigns.resume(campaign.id), "resumed")}>
              <Play className="h-4 w-4 mr-1" /> Resume
            </Button>
          )}
          {["draft", "running", "paused"].includes(campaign.status) && (
            <Button size="sm" variant="danger" loading={acting} onClick={() => action(() => api.campaigns.cancel(campaign.id), "cancelled")}>
              <StopCircle className="h-4 w-4 mr-1" /> Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Pre-flight Failure Banner */}
      {preflightFailure && (
        <div className="mb-6 rounded-lg border border-warning/40 bg-warning/10 p-4 text-sm">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-text-primary">
                {preflightFailure.isCallingHours
                  ? "Pre-Flight Check: Outside Allowed Calling Hours"
                  : "Pre-Flight Validation Check Failed"}
              </h4>
              <p className="mt-1 text-text-secondary">{preflightFailure.message}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {campaign.status === "draft" && (
                  <Button
                    size="sm"
                    onClick={() => setEditCallingHoursOpen(true)}
                    className="gap-1.5"
                  >
                    <Clock className="h-3.5 w-3.5" /> Configure Calling Hours
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="secondary"
                  loading={acting}
                  onClick={() => handleStart(true)}
                  className="gap-1.5"
                >
                  Start Anyway (Bypass Pre-flight)
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setPreflightFailure(null)}
                >
                  Dismiss
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-4 mb-6 lg:grid-cols-4">
        <MetricCard label="Total Leads" value={campaign.total_leads.toLocaleString("en-IN")} icon={Users} />
        <MetricCard label="Dialed" value={campaign.leads_dialed.toLocaleString("en-IN")} icon={Phone} />
        <MetricCard label="Connected" value={campaign.leads_connected.toLocaleString("en-IN")} accent />
        <MetricCard label="Completed" value={campaign.leads_completed.toLocaleString("en-IN")} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left Column: Details + Schedule */}
        <div className="space-y-6">
          {/* Details */}
          <Card>
            <CardHeader><h3 className="text-sm font-medium text-text-primary">Details</h3></CardHeader>
            <CardBody className="space-y-3 text-sm">
              <Row label="Status"><StatusBadge status={campaign.status} /></Row>
              <Row label="Timezone" value={campaign.timezone} />
              <Row label="Max Concurrent" value={String(campaign.max_concurrent_calls)} />
              <Row label="Calling Number" value={campaign.calling_number} />
              <Row label="Created" value={formatDateTime(campaign.created_at)} />
              {campaign.started_at && <Row label="Started" value={formatDateTime(campaign.started_at)} />}
              {campaign.completed_at && <Row label="Completed" value={formatDateTime(campaign.completed_at)} />}
              {campaign.cancelled_at && <Row label="Cancelled" value={formatDateTime(campaign.cancelled_at)} />}
            </CardBody>
          </Card>

          {/* Calling Hours & Schedule */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <h3 className="text-sm font-medium text-text-primary flex items-center gap-1.5">
                <Clock className="h-4 w-4 text-accent" /> Calling Hours &amp; Schedule
              </h3>
              {campaign.status === "draft" && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setEditCallingHoursOpen(true)}
                  className="h-7 text-xs gap-1 text-accent hover:text-accent-hover cursor-pointer"
                >
                  <Edit2 className="h-3 w-3" /> Edit
                </Button>
              )}
            </CardHeader>
            <CardBody className="space-y-3 text-sm">
              <Row
                label="Window"
                value={`${campaign.calling_hours?.start_time || "09:00"} – ${campaign.calling_hours?.end_time || "18:00"}`}
              />
              <Row label="Timezone" value={campaign.timezone} />
              <div>
                <span className="text-text-muted block text-xs mb-1.5">Allowed Days</span>
                <div className="flex flex-wrap gap-1.5">
                  {DAY_OPTIONS.map((day) => {
                    const allowedDays = campaign.calling_hours?.days_of_week ?? [1, 2, 3, 4, 5];
                    const isAllowed = allowedDays.includes(day.value);
                    return (
                      <span
                        key={day.value}
                        className={`px-2 py-0.5 text-xs rounded-full border transition-colors ${
                          isAllowed
                            ? "border-accent/40 bg-accent/15 text-accent font-medium"
                            : "border-border text-text-muted/60 bg-surface-subtle line-through opacity-50"
                        }`}
                      >
                        {day.label}
                      </span>
                    );
                  })}
                </div>
              </div>
              {campaign.scheduled_at && (
                <Row label="Scheduled Start" value={formatDateTime(campaign.scheduled_at)} />
              )}
            </CardBody>
          </Card>
        </div>

        {/* Progress */}
        <div className="lg:col-span-2">
          {campaign.total_leads > 0 ? (
            <Card>
              <CardHeader><h3 className="text-sm font-medium text-text-primary">Progress</h3></CardHeader>
              <CardBody>
                {[
                  { label: "Dialed", value: campaign.leads_dialed, color: "bg-info" },
                  { label: "Connected", value: campaign.leads_connected, color: "bg-success" },
                  { label: "Completed", value: campaign.leads_completed, color: "bg-accent" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="mb-4">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-text-secondary">{label}</span>
                      <span className="font-medium text-text-primary">{value} / {campaign.total_leads}</span>
                    </div>
                    <div className="h-2 bg-surface-subtle rounded-full overflow-hidden">
                      <div
                        className={`h-full ${color} rounded-full transition-all`}
                        style={{ width: `${(value / campaign.total_leads) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}

                {stats && stats.outcomes && Object.keys(stats.outcomes).length > 0 && (
                  <div className="mt-4 pt-4 border-t border-border">
                    <p className="text-xs font-medium text-text-muted uppercase tracking-wide mb-3">Outcomes</p>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(stats.outcomes).map(([outcome, count]) => (
                        <div key={outcome} className="flex justify-between text-sm">
                          <StatusBadge status={outcome} />
                          <span className="font-medium text-text-primary">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardBody>
            </Card>
          ) : (
            <Card>
              <CardHeader><h3 className="text-sm font-medium text-text-primary">Progress</h3></CardHeader>
              <CardBody className="py-12 text-center text-text-muted text-sm">
                No leads dialed yet. Once you start the campaign, dialing progress and outcomes will appear here.
              </CardBody>
            </Card>
          )}
        </div>
      </div>

      <CallingHoursModal
        isOpen={editCallingHoursOpen}
        onClose={() => setEditCallingHoursOpen(false)}
        campaignId={campaign.id}
        initialCallingHours={campaign.calling_hours}
        initialTimezone={campaign.timezone}
        onUpdated={(updated) => {
          setCampaign(updated);
          setPreflightFailure(null);
        }}
      />
    </AppShell>
  );
}

function Row({ label, value, children }: { label: string; value?: string; children?: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center gap-2">
      <span className="text-text-muted">{label}</span>
      <span className="font-medium text-text-primary">{children ?? value}</span>
    </div>
  );
}
