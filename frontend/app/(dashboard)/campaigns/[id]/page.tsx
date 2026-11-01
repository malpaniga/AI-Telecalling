"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
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
  Upload,
  UserPlus,
  Trash2,
} from "lucide-react";
import toast from "react-hot-toast";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { Modal } from "@/components/ui/modal";
import { Input } from "@/components/ui/input";
import { api, Campaign, CampaignStats, CampaignLead } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import {
  CallingHoursModal,
  DAY_OPTIONS,
} from "@/components/campaigns/calling-hours-modal";

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [savingEdit, setSavingEdit] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editMaxConcurrent, setEditMaxConcurrent] = useState("1");
  const [editStartTime, setEditStartTime] = useState("09:00");
  const [editEndTime, setEditEndTime] = useState("19:00");
  const [editMaxAttempts, setEditMaxAttempts] = useState("3");
  const [editRetryInterval, setEditRetryInterval] = useState("60");
  const [stats, setStats] = useState<CampaignStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [editCallingHoursOpen, setEditCallingHoursOpen] = useState(false);
  const [preflightFailure, setPreflightFailure] = useState<{
    message: string;
    isCallingHours: boolean;
  } | null>(null);

  // Campaign Leads state
  const [campaignLeads, setCampaignLeads] = useState<CampaignLead[]>([]);
  const [leadsTotal, setLeadsTotal] = useState(0);
  const [leadsLoading, setLeadsLoading] = useState(false);
  const [addContactsModalOpen, setAddContactsModalOpen] = useState(false);
  const [addMode, setAddMode] = useState<"all" | "tags">("all");
  const [tagsInput, setTagsInput] = useState("");
  const [enrolling, setEnrolling] = useState(false);

  const loadLeads = useCallback(async () => {
    if (!id) return;
    setLeadsLoading(true);
    try {
      const res = await api.campaigns.leads(id, { limit: 50 });
      setCampaignLeads(res.items);
      setLeadsTotal(res.total);
    } catch {
      // ignore
    } finally {
      setLeadsLoading(false);
    }
  }, [id]);

  function openEditModal() {
    if (!campaign) return;
    const ch = campaign.calling_hours;
    const rp = campaign.retry_policy;
    setEditName(campaign.name);
    setEditDescription(campaign.description || "");
    setEditMaxConcurrent(String(campaign.max_concurrent_calls || 1));
    setEditStartTime(ch?.start_time || "09:00");
    setEditEndTime(ch?.end_time || "19:00");
    setEditMaxAttempts(String(rp?.max_attempts || "3"));
    setEditRetryInterval(String(rp?.retry_delay_minutes || "60"));
    setShowEditModal(true);
  }

  async function handleUpdateCampaign(e: React.FormEvent) {
    e.preventDefault();
    if (!campaign) return;
    setSavingEdit(true);
    try {
      await api.campaigns.update(campaign.id, {
        name: editName.trim(),
        description: editDescription.trim(),
        max_concurrent_calls: parseInt(editMaxConcurrent) || 1,
        calling_hours: {
          start_time: editStartTime,
          end_time: editEndTime,
          days_of_week: [1, 2, 3, 4, 5, 6, 7],
        },
        retry_policy: {
          max_attempts: parseInt(editMaxAttempts) || 3,
          retry_delay_minutes: parseInt(editRetryInterval) || 60,
        },
      });
      toast.success("Campaign updated successfully!");
      setShowEditModal(false);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update campaign");
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleDeleteCampaign() {
    if (!campaign) return;
    if (campaign.status === "running") {
      toast.error("Cannot delete a running campaign. Please pause or cancel it first.");
      return;
    }
    if (!confirm(`Are you sure you want to delete campaign "${campaign.name}"?\nThis will unenroll all leads and delete this campaign permanently.`)) {
      return;
    }
    try {
      await api.campaigns.delete(campaign.id);
      toast.success(`Campaign "${campaign.name}" deleted.`);
      router.push("/campaigns");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to delete campaign");
    }
  }

  const load = useCallback(async (silent = false) => {
    if (!id) return;
    if (!silent) setLoading(true);
    try {
      const [c, s] = await Promise.all([
        api.campaigns.get(id),
        api.campaigns.stats(id).catch(() => null),
      ]);
      setCampaign(c);
      setStats(s);
      loadLeads();
    } catch (e: unknown) {
      if (!silent) {
        toast.error(e instanceof Error ? e.message : "Failed to load campaign");
      }
    } finally {
      if (!silent) setLoading(false);
    }
  }, [id, loadLeads]);

  useEffect(() => { load(); }, [load]);

  // Real-time polling when campaign is running
  useEffect(() => {
    if (!campaign || campaign.status !== "running") return;
    const interval = setInterval(() => {
      load(true);
    }, 3000);
    return () => clearInterval(interval);
  }, [campaign?.status, load]);

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

  async function handleEnrollContacts(e: React.FormEvent) {
    e.preventDefault();
    if (!campaign) return;
    setEnrolling(true);
    try {
      const payload =
        addMode === "all"
          ? { all_contacts: true }
          : { tags: tagsInput.split(",").map((t) => t.trim()).filter(Boolean) };
      const res = await api.campaigns.enrollLeads(campaign.id, payload);
      toast.success(`Enrolled ${res.enrolled} contacts (${res.skipped} already enrolled)`);
      setAddContactsModalOpen(false);
      setTagsInput("");
      await Promise.all([load(true), loadLeads()]);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to enroll contacts");
    } finally {
      setEnrolling(false);
    }
  }

  async function handleRemoveLead(leadId: string) {
    if (!campaign || !confirm("Remove this lead from this campaign?")) return;
    try {
      await api.campaigns.removeLead(campaign.id, leadId);
      toast.success("Lead removed from campaign");
      await Promise.all([load(true), loadLeads()]);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to remove lead");
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
          <Button variant="ghost" size="sm" onClick={() => load()} disabled={loading}>
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
          <Button
            size="sm"
            variant="secondary"
            onClick={openEditModal}
            className="gap-1"
          >
            <Edit2 className="h-3.5 w-3.5" /> Edit Campaign
          </Button>
          {campaign.status !== "running" && (
            <Button
              size="sm"
              variant="danger"
              onClick={handleDeleteCampaign}
              className="gap-1"
            >
              <Trash2 className="h-3.5 w-3.5" /> Delete
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

      {/* Enrolled Leads Section */}
      <div className="mt-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <Users className="h-4 w-4 text-accent" />
                Enrolled Leads ({leadsTotal})
              </h3>
              <p className="text-xs text-text-muted mt-0.5">
                Contacts enrolled in this campaign with dedicated campaign statuses and variables
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                className="gap-1.5"
                onClick={() => setAddContactsModalOpen(true)}
              >
                <UserPlus className="h-3.5 w-3.5" />
                Add from Contacts
              </Button>
              <Link href={`/leads/import?campaign_id=${campaign.id}`}>
                <Button size="sm" className="gap-1.5">
                  <Upload className="h-3.5 w-3.5" />
                  Import File
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardBody>
            {leadsLoading ? (
              <div className="flex justify-center py-8">
                <Spinner size="md" />
              </div>
            ) : campaignLeads.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-border text-xs text-text-muted">
                      <th className="pb-2 font-medium">Name</th>
                      <th className="pb-2 font-medium">Phone</th>
                      <th className="pb-2 font-medium">Campaign Status</th>
                      <th className="pb-2 font-medium">Attempts</th>
                      <th className="pb-2 font-medium">Last Called</th>
                      <th className="pb-2 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {campaignLeads.map((cl) => (
                      <tr key={cl.id} className="text-text-primary hover:bg-surface-subtle transition-colors">
                        <td className="py-2.5 font-medium">{cl.name || <span className="text-text-muted italic">Unknown</span>}</td>
                        <td className="py-2.5 font-mono text-xs">{cl.phone}</td>
                        <td className="py-2.5"><StatusBadge status={cl.status} /></td>
                        <td className="py-2.5 text-xs text-text-secondary">{cl.attempts} / {cl.max_attempts}</td>
                        <td className="py-2.5 text-xs text-text-secondary">
                          {cl.last_called_at ? formatDateTime(cl.last_called_at) : "Never"}
                        </td>
                        <td className="py-2.5 text-right">
                          {["new", "callback"].includes(cl.status) && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 w-7 p-0 text-text-muted hover:text-danger cursor-pointer"
                              onClick={() => handleRemoveLead(cl.lead_id)}
                              title="Remove from campaign"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-10">
                <Users className="h-8 w-8 text-text-muted mx-auto mb-2 opacity-50" />
                <p className="text-sm font-medium text-text-primary">No leads enrolled yet</p>
                <p className="text-xs text-text-muted mt-1 max-w-sm mx-auto">
                  Import a contact list or add existing contacts to this campaign before starting.
                </p>
                <div className="flex justify-center gap-2 mt-4">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="gap-1.5"
                    onClick={() => setAddContactsModalOpen(true)}
                  >
                    <UserPlus className="h-3.5 w-3.5" /> Add from Contacts
                  </Button>
                  <Link href={`/leads/import?campaign_id=${campaign.id}`}>
                    <Button size="sm" className="gap-1.5">
                      <Upload className="h-3.5 w-3.5" /> Import File
                    </Button>
                  </Link>
                </div>
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      {/* Enroll Contacts Modal */}
      <Modal
        isOpen={addContactsModalOpen}
        onClose={() => setAddContactsModalOpen(false)}
        title="Add Existing Contacts to Campaign"
      >
        <form onSubmit={handleEnrollContacts} className="space-y-4">
          <p className="text-xs text-text-muted">
            Contacts added to this campaign will receive independent campaign statuses. Calling them here will not affect other campaigns.
          </p>

          <div className="space-y-3">
            <label className="flex items-center gap-2 text-sm text-text-primary cursor-pointer">
              <input
                type="radio"
                name="addMode"
                value="all"
                checked={addMode === "all"}
                onChange={() => setAddMode("all")}
                className="text-accent"
              />
              <span>Enroll all organization contacts</span>
            </label>

            <label className="flex items-center gap-2 text-sm text-text-primary cursor-pointer">
              <input
                type="radio"
                name="addMode"
                value="tags"
                checked={addMode === "tags"}
                onChange={() => setAddMode("tags")}
                className="text-accent"
              />
              <span>Filter by contact tags</span>
            </label>
          </div>

          {addMode === "tags" && (
            <div className="pt-2">
              <Input
                label="Tags (comma-separated)"
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="e.g. vip, warm-leads"
                required
              />
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4 border-t border-border">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setAddContactsModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={enrolling}>
              Enroll Contacts
            </Button>
          </div>
        </form>
      </Modal>

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
      {/* Edit Campaign Modal */}
      <Modal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        title={`Edit Campaign: ${campaign.name}`}
        size="lg"
      >
        <form onSubmit={handleUpdateCampaign} className="flex flex-col gap-4">
          <Input
            label="Campaign Name *"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            required
          />

          <Input
            label="Description"
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
            placeholder="Campaign goals or details..."
          />

          <Input
            label="Max Concurrent Calls"
            type="number"
            min="1"
            max="50"
            value={editMaxConcurrent}
            onChange={(e) => setEditMaxConcurrent(e.target.value)}
          />

          <div className="p-3.5 rounded-lg border border-border bg-surface-subtle space-y-3">
            <div className="flex items-center gap-1.5 font-semibold text-xs text-text-primary">
              <Clock className="h-3.5 w-3.5 text-accent" />
              Allowed Calling Hours
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Start Time"
                type="time"
                value={editStartTime}
                onChange={(e) => setEditStartTime(e.target.value)}
              />
              <Input
                label="End Time"
                type="time"
                value={editEndTime}
                onChange={(e) => setEditEndTime(e.target.value)}
              />
            </div>
          </div>

          <div className="p-3.5 rounded-lg border border-border bg-surface-subtle space-y-3">
            <div className="flex items-center gap-1.5 font-semibold text-xs text-text-primary">
              <Clock className="h-3.5 w-3.5 text-accent" />
              Lead Retry Policy
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Max Attempts per Lead"
                type="number"
                min="1"
                max="10"
                value={editMaxAttempts}
                onChange={(e) => setEditMaxAttempts(e.target.value)}
              />
              <Input
                label="Retry Delay (Minutes)"
                type="number"
                min="5"
                max="1440"
                value={editRetryInterval}
                onChange={(e) => setEditRetryInterval(e.target.value)}
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button type="button" variant="secondary" onClick={() => setShowEditModal(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={savingEdit}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>
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
