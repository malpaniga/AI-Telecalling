"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  Megaphone,
  Plus,
  Play,
  Pause,
  StopCircle,
  ArrowRight,
  Edit2,
  Trash2,
  Search,
  Clock,
  RotateCcw,
  Sliders,
} from "lucide-react";
import toast from "react-hot-toast";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardBody } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Modal } from "@/components/ui/modal";
import { Input, Select } from "@/components/ui/input";
import { api, Campaign, Agent, VoiceProfile, PhoneNumber } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

const STATUS_FILTER_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "draft", label: "Draft" },
  { value: "running", label: "Running" },
  { value: "paused", label: "Paused" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [voiceProfiles, setVoiceProfiles] = useState<VoiceProfile[]>([]);
  const [phoneNumbers, setPhoneNumbers] = useState<PhoneNumber[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [editing, setEditing] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);

  // Create Form State
  const [form, setForm] = useState({
    name: "",
    agent_id: "",
    voice_profile_id: "",
    calling_number_id: "",
    max_concurrent_calls: "1",
    timezone: "Asia/Kolkata",
    description: "",
  });

  // Edit Form State
  const [editForm, setEditForm] = useState<{
    id: string;
    name: string;
    description: string;
    max_concurrent_calls: string;
    agent_id: string;
    calling_number_id: string;
    status: string;
    start_time: string;
    end_time: string;
    max_attempts: string;
    retry_interval_minutes: string;
  }>({
    id: "",
    name: "",
    description: "",
    max_concurrent_calls: "1",
    agent_id: "",
    calling_number_id: "",
    status: "draft",
    start_time: "09:00",
    end_time: "19:00",
    max_attempts: "3",
    retry_interval_minutes: "60",
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [c, a, v, p] = await Promise.all([
        api.campaigns.list(),
        api.agents.list(),
        api.voiceProfiles.list(),
        api.phoneNumbers.myNumbers(),
      ]);
      setCampaigns(c);
      setAgents(a);
      setVoiceProfiles(v);
      setPhoneNumbers(p);
      if (a.length > 0) setForm((f) => ({ ...f, agent_id: a[0].id }));
      if (v.length > 0) setForm((f) => ({ ...f, voice_profile_id: v[0].id }));
      if (p.length > 0) setForm((f) => ({ ...f, calling_number_id: p[0].id }));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load campaigns");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const agent = agents.find((a) => a.id === form.agent_id);
    const profile = voiceProfiles.find((v) => v.id === form.voice_profile_id);
    const number = phoneNumbers.find((p) => p.id === form.calling_number_id);
    if (!agent || !profile || !number) return toast.error("Select all required fields");
    if (!agent.active_version) return toast.error("Agent has no published version");

    setCreating(true);
    try {
      await api.campaigns.create({
        name: form.name.trim(),
        agent_id: form.agent_id,
        agent_version: agent.active_version,
        voice_profile_id: form.voice_profile_id,
        voice_profile_version: profile.active_version ?? 1,
        calling_number_id: form.calling_number_id,
        calling_number: number.number,
        max_concurrent_calls: parseInt(form.max_concurrent_calls) || 1,
        timezone: form.timezone,
        description: form.description.trim(),
      });
      toast.success("Campaign created successfully!");
      setShowCreate(false);
      setForm((f) => ({ ...f, name: "", description: "" }));
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create campaign");
    } finally {
      setCreating(false);
    }
  }

  function openEditModal(c: Campaign) {
    const ch = c.calling_hours;
    const rp = c.retry_policy;

    setEditForm({
      id: c.id,
      name: c.name,
      description: c.description || "",
      max_concurrent_calls: String(c.max_concurrent_calls || 1),
      agent_id: c.agent_id,
      calling_number_id: c.calling_number_id,
      status: c.status,
      start_time: ch?.start_time || "09:00",
      end_time: ch?.end_time || "19:00",
      max_attempts: String(rp?.max_attempts || "3"),
      retry_interval_minutes: String(rp?.retry_delay_minutes || "60"),
    });
    setShowEdit(true);
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!editForm.id) return;

    setEditing(true);
    try {
      const payload: Record<string, unknown> = {
        name: editForm.name.trim(),
        description: editForm.description.trim(),
        max_concurrent_calls: parseInt(editForm.max_concurrent_calls) || 1,
        calling_hours: {
          start_time: editForm.start_time,
          end_time: editForm.end_time,
          days_of_week: [1, 2, 3, 4, 5, 6, 7],
        },
        retry_policy: {
          max_attempts: parseInt(editForm.max_attempts) || 3,
          retry_delay_minutes: parseInt(editForm.retry_interval_minutes) || 60,
        },
      };

      if (editForm.status !== "running") {
        if (editForm.agent_id) payload["agent_id"] = editForm.agent_id;
        if (editForm.calling_number_id) {
          payload["calling_number_id"] = editForm.calling_number_id;
          const num = phoneNumbers.find((p) => p.id === editForm.calling_number_id);
          if (num) payload["calling_number"] = num.number;
        }
      }

      await api.campaigns.update(editForm.id, payload);
      toast.success("Campaign updated successfully!");
      setShowEdit(false);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update campaign");
    } finally {
      setEditing(false);
    }
  }

  async function handleDelete(c: Campaign) {
    if (c.status === "running") {
      toast.error("Cannot delete a running campaign. Please pause or cancel it first.");
      return;
    }
    if (!confirm(`Are you sure you want to delete campaign "${c.name}"?\nThis will remove the campaign and unenroll all leads.`)) {
      return;
    }

    setActionId(c.id + "-delete");
    try {
      await api.campaigns.delete(c.id);
      toast.success(`Campaign "${c.name}" deleted.`);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to delete campaign");
    } finally {
      setActionId(null);
    }
  }

  async function action(fn: () => Promise<Campaign>, label: string) {
    try {
      await fn();
      toast.success(`Campaign ${label}`);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : `Failed to ${label}`);
    } finally {
      setActionId(null);
    }
  }

  const filteredCampaigns = campaigns.filter((c) => {
    if (statusFilter && c.status !== statusFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        c.name.toLowerCase().includes(q) ||
        (c.description && c.description.toLowerCase().includes(q))
      );
    }
    return true;
  });

  return (
    <AppShell title="Campaigns">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Campaigns</h2>
          <p className="text-sm text-text-secondary">
            {campaigns.length} total · {campaigns.filter((c) => c.status === "running").length} active
          </p>
        </div>
        <Button size="sm" onClick={() => setShowCreate(true)} className="gap-1.5">
          <Plus className="h-4 w-4" /> New Campaign
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative flex-1 min-w-48 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted pointer-events-none" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search campaigns by name or description…"
            className="w-full rounded-md border border-border bg-surface pl-9 pr-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
          />
        </div>
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          options={STATUS_FILTER_OPTIONS}
          className="w-40"
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : filteredCampaigns.length === 0 ? (
        <EmptyState
          icon={Megaphone}
          title={search || statusFilter ? "No matching campaigns" : "No campaigns yet"}
          description={
            search || statusFilter
              ? "Try adjusting your search terms or status filter"
              : "Create an outbound campaign to start automated calling to your leads"
          }
          action={
            <Button onClick={() => setShowCreate(true)} className="gap-1.5">
              <Plus className="h-4 w-4" /> Create Campaign
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {filteredCampaigns.map((c) => (
            <Card key={c.id}>
              <CardBody className="p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Link href={`/campaigns/${c.id}`} className="hover:underline">
                        <p className="text-sm font-semibold text-text-primary truncate">{c.name}</p>
                      </Link>
                      <StatusBadge status={c.status} />
                    </div>
                    {c.description && (
                      <p className="text-xs text-text-secondary truncate mb-1">{c.description}</p>
                    )}
                    <div className="flex flex-wrap gap-4 text-xs text-text-muted">
                      <span>{c.total_leads} enrolled · {c.leads_dialed} dialed · {c.leads_completed} completed</span>
                      <span>Max {c.max_concurrent_calls} concurrent</span>
                      <span>{formatDateTime(c.created_at)}</span>
                    </div>
                  </div>

                  {/* Progress bar */}
                  {c.total_leads > 0 && (
                    <div className="w-32 hidden md:block">
                      <div className="flex justify-between text-xs text-text-muted mb-1">
                        <span>{c.leads_dialed}</span>
                        <span>{c.total_leads}</span>
                      </div>
                      <div className="h-1.5 bg-surface-subtle rounded-full overflow-hidden">
                        <div
                          className="h-full bg-accent rounded-full transition-all"
                          style={{ width: `${Math.min(100, (c.leads_dialed / c.total_leads) * 100)}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="flex items-center gap-2">
                    {c.status === "draft" && (
                      <Button
                        size="sm"
                        loading={actionId === c.id}
                        onClick={() => { setActionId(c.id); action(() => api.campaigns.start(c.id), "started"); }}
                      >
                        <Play className="h-3.5 w-3.5 mr-1" /> Start
                      </Button>
                    )}
                    {c.status === "running" && (
                      <Button
                        size="sm"
                        variant="secondary"
                        loading={actionId === c.id}
                        onClick={() => { setActionId(c.id); action(() => api.campaigns.pause(c.id), "paused"); }}
                      >
                        <Pause className="h-3.5 w-3.5 mr-1" /> Pause
                      </Button>
                    )}
                    {c.status === "paused" && (
                      <Button
                        size="sm"
                        loading={actionId === c.id}
                        onClick={() => { setActionId(c.id); action(() => api.campaigns.resume(c.id), "resumed"); }}
                      >
                        <Play className="h-3.5 w-3.5 mr-1" /> Resume
                      </Button>
                    )}
                    {["draft", "running", "paused"].includes(c.status) && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-text-muted hover:text-danger cursor-pointer"
                        title="Cancel Campaign"
                        onClick={() => { setActionId(c.id + "-cancel"); action(() => api.campaigns.cancel(c.id), "cancelled"); }}
                      >
                        <StopCircle className="h-4 w-4" />
                      </Button>
                    )}

                    {/* Edit Campaign Button */}
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-text-muted hover:text-accent cursor-pointer"
                      title="Edit Campaign"
                      onClick={() => openEditModal(c)}
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                    </Button>

                    {/* Delete Campaign Button */}
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-text-muted hover:text-danger cursor-pointer"
                      title="Delete Campaign"
                      loading={actionId === c.id + "-delete"}
                      onClick={() => handleDelete(c)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>

                    <Link href={`/campaigns/${c.id}`}>
                      <Button variant="ghost" size="sm" title="View Campaign Details">
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </Link>
                  </div>
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* Create Modal */}
      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="New Outbound Campaign" size="lg">
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          <Input
            label="Campaign Name *"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="e.g. Diwali Festive Offer"
            required
          />
          <div className="grid grid-cols-2 gap-3">
            <Select
              label="AI Agent *"
              value={form.agent_id}
              onChange={(e) => setForm((f) => ({ ...f, agent_id: e.target.value }))}
              required
            >
              {agents.length === 0 ? (
                <option value="">No agents — create one first</option>
              ) : (
                agents.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))
              )}
            </Select>
            <Select
              label="Voice Profile *"
              value={form.voice_profile_id}
              onChange={(e) => setForm((f) => ({ ...f, voice_profile_id: e.target.value }))}
              required
            >
              {voiceProfiles.length === 0 ? (
                <option value="">No voice profiles</option>
              ) : (
                voiceProfiles.map((v) => (
                  <option key={v.id} value={v.id}>{v.display_name} ({v.language})</option>
                ))
              )}
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Select
              label="Calling Phone Number *"
              value={form.calling_number_id}
              onChange={(e) => setForm((f) => ({ ...f, calling_number_id: e.target.value }))}
              required
            >
              {phoneNumbers.length === 0 ? (
                <option value="">No numbers assigned</option>
              ) : (
                phoneNumbers.map((p) => (
                  <option key={p.id} value={p.id}>{p.number}</option>
                ))
              )}
            </Select>
            <Input
              label="Max Concurrent Calls"
              type="number"
              min="1"
              max="50"
              value={form.max_concurrent_calls}
              onChange={(e) => setForm((f) => ({ ...f, max_concurrent_calls: e.target.value }))}
            />
          </div>
          <Input
            label="Description (optional)"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            placeholder="Notes or campaign goals..."
          />
          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button type="button" variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button type="submit" loading={creating}>Create Campaign</Button>
          </div>
        </form>
      </Modal>

      {/* Edit Campaign Modal */}
      <Modal isOpen={showEdit} onClose={() => setShowEdit(false)} title={`Edit Campaign: ${editForm.name}`} size="lg">
        <form onSubmit={handleUpdate} className="flex flex-col gap-4">
          <Input
            label="Campaign Name *"
            value={editForm.name}
            onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
            required
          />

          <Input
            label="Description"
            value={editForm.description}
            onChange={(e) => setEditForm((f) => ({ ...f, description: e.target.value }))}
            placeholder="Campaign notes..."
          />

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Max Concurrent Calls"
              type="number"
              min="1"
              max="50"
              value={editForm.max_concurrent_calls}
              onChange={(e) => setEditForm((f) => ({ ...f, max_concurrent_calls: e.target.value }))}
            />

            {editForm.status !== "running" ? (
              <Select
                label="AI Agent"
                value={editForm.agent_id}
                onChange={(e) => setEditForm((f) => ({ ...f, agent_id: e.target.value }))}
              >
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </Select>
            ) : (
              <Input
                label="Status"
                value="Running (Agent locked while active)"
                disabled
              />
            )}
          </div>

          {/* Calling Hours Section */}
          <div className="p-3.5 rounded-lg border border-border bg-surface-subtle space-y-3">
            <div className="flex items-center gap-1.5 font-semibold text-xs text-text-primary">
              <Clock className="h-3.5 w-3.5 text-accent" />
              Calling Hours Window
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Start Time (e.g. 09:00)"
                type="time"
                value={editForm.start_time}
                onChange={(e) => setEditForm((f) => ({ ...f, start_time: e.target.value }))}
              />
              <Input
                label="End Time (e.g. 19:00)"
                type="time"
                value={editForm.end_time}
                onChange={(e) => setEditForm((f) => ({ ...f, end_time: e.target.value }))}
              />
            </div>
          </div>

          {/* Retry Policy Section */}
          <div className="p-3.5 rounded-lg border border-border bg-surface-subtle space-y-3">
            <div className="flex items-center gap-1.5 font-semibold text-xs text-text-primary">
              <RotateCcw className="h-3.5 w-3.5 text-accent" />
              Retry Policy
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Max Call Attempts per Lead"
                type="number"
                min="1"
                max="10"
                value={editForm.max_attempts}
                onChange={(e) => setEditForm((f) => ({ ...f, max_attempts: e.target.value }))}
              />
              <Input
                label="Retry Delay (Minutes)"
                type="number"
                min="5"
                max="1440"
                value={editForm.retry_interval_minutes}
                onChange={(e) => setEditForm((f) => ({ ...f, retry_interval_minutes: e.target.value }))}
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button type="button" variant="secondary" onClick={() => setShowEdit(false)}>Cancel</Button>
            <Button type="submit" loading={editing}>Save Changes</Button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
}
