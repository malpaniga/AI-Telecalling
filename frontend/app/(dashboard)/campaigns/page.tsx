"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Megaphone, Plus, Play, Pause, StopCircle, ArrowRight } from "lucide-react";
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

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [voiceProfiles, setVoiceProfiles] = useState<VoiceProfile[]>([]);
  const [phoneNumbers, setPhoneNumbers] = useState<PhoneNumber[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    agent_id: "",
    voice_profile_id: "",
    calling_number_id: "",
    max_concurrent_calls: "1",
    timezone: "Asia/Kolkata",
    description: "",
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
      toast.error(e instanceof Error ? e.message : "Failed to load");
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
        name: form.name,
        agent_id: form.agent_id,
        agent_version: agent.active_version,
        voice_profile_id: form.voice_profile_id,
        voice_profile_version: profile.active_version ?? 1,
        calling_number_id: form.calling_number_id,
        calling_number: number.number,
        max_concurrent_calls: parseInt(form.max_concurrent_calls) || 1,
        timezone: form.timezone,
        description: form.description,
      });
      toast.success("Campaign created");
      setShowCreate(false);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create campaign");
    } finally {
      setCreating(false);
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

  return (
    <AppShell title="Campaigns">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Campaigns</h2>
          <p className="text-sm text-text-secondary">{campaigns.length} total</p>
        </div>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-1" /> New Campaign
        </Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : campaigns.length === 0 ? (
        <EmptyState
          icon={Megaphone}
          title="No campaigns yet"
          description="Create a campaign to start automated outbound calling"
          action={<Button onClick={() => setShowCreate(true)}>Create Campaign</Button>}
        />
      ) : (
        <div className="space-y-3">
          {campaigns.map((c) => (
            <Card key={c.id}>
              <CardBody className="p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-medium text-text-primary truncate">{c.name}</p>
                      <StatusBadge status={c.status} />
                    </div>
                    {c.description && (
                      <p className="text-xs text-text-secondary truncate mb-1">{c.description}</p>
                    )}
                    <div className="flex flex-wrap gap-4 text-xs text-text-muted">
                      <span>{c.total_leads} leads · {c.leads_dialed} dialed · {c.leads_completed} completed</span>
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
                          style={{ width: `${(c.leads_dialed / c.total_leads) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}

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
                        className="text-text-muted hover:text-danger"
                        onClick={() => { setActionId(c.id + "-cancel"); action(() => api.campaigns.cancel(c.id), "cancelled"); }}
                      >
                        <StopCircle className="h-4 w-4" />
                      </Button>
                    )}
                    <Link href={`/campaigns/${c.id}`}>
                      <Button variant="ghost" size="sm">
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

      {/* Create modal */}
      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="New Campaign" size="lg">
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          <Input
            label="Campaign name"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="Q4 Sales Outreach"
            required
          />
          <div className="grid grid-cols-2 gap-3">
            <Select
              label="AI Agent"
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
              label="Voice Profile"
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
              label="Calling Number"
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
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button type="submit" loading={creating}>Create Campaign</Button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
}
