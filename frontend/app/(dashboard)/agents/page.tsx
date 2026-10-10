"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Bot, Plus, Trash2, Settings, CheckCircle, Circle } from "lucide-react";
import toast from "react-hot-toast";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardBody } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Modal } from "@/components/ui/modal";
import { Input, Select } from "@/components/ui/input";
import { api, Agent, BusinessTemplate, VoiceProfile } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import Link from "next/link";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [templates, setTemplates] = useState<BusinessTemplate[]>([]);
  const [voiceProfiles, setVoiceProfiles] = useState<VoiceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  const [form, setForm] = useState({
    name: "",
    template_slug: "",
    voice_profile_id: "",
    description: "",
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, t, v] = await Promise.all([
        api.agents.list(),
        api.agents.templates(),
        api.voiceProfiles.list(),
      ]);
      setAgents(a);
      setTemplates(t);
      setVoiceProfiles(v);
      if (t.length > 0) setForm((f) => ({ ...f, template_slug: t[0].slug }));
      if (v.length > 0) setForm((f) => ({ ...f, voice_profile_id: v[0].id }));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load agents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.voice_profile_id) return toast.error("Select a voice profile");
    const profile = voiceProfiles.find((v) => v.id === form.voice_profile_id);
    if (!profile) return toast.error("Voice profile not found");
    setCreating(true);
    try {
      await api.agents.create({
        name: form.name,
        template_slug: form.template_slug,
        voice_profile_id: form.voice_profile_id,
        voice_profile_version: profile.active_version ?? 1,
        description: form.description,
      });
      toast.success("Agent created");
      setShowCreate(false);
      setForm({ name: "", template_slug: templates[0]?.slug ?? "", voice_profile_id: voiceProfiles[0]?.id ?? "", description: "" });
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create agent");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Deactivate agent "${name}"?`)) return;
    try {
      await api.agents.delete(id);
      toast.success("Agent deactivated");
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to deactivate");
    }
  }

  return (
    <AppShell title="AI Agents">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Your AI Agents</h2>
          <p className="text-sm text-text-secondary mt-0.5">Configure agents that handle your calls</p>
        </div>
        <Button onClick={() => setShowCreate(true)} size="sm">
          <Plus className="h-4 w-4 mr-1" /> New Agent
        </Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : agents.length === 0 ? (
        <EmptyState
          icon={Bot}
          title="No agents yet"
          description="Create your first AI agent to start making calls"
          action={<Button onClick={() => setShowCreate(true)}>Create Agent</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <Card key={agent.id} className="hover:shadow-md transition-shadow">
              <CardBody className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-md bg-accent-subtle flex items-center justify-center">
                      <Bot className="h-4 w-4 text-accent" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-text-primary">{agent.name}</p>
                      <p className="text-xs text-text-muted capitalize">{agent.template_slug.replace(/_/g, " ")}</p>
                    </div>
                  </div>
                  {agent.is_active ? (
                    <CheckCircle className="h-4 w-4 text-success" />
                  ) : (
                    <Circle className="h-4 w-4 text-text-muted" />
                  )}
                </div>

                {agent.description && (
                  <p className="text-xs text-text-secondary mb-3 line-clamp-2">{agent.description}</p>
                )}

                <div className="flex items-center gap-2 mb-4">
                  {agent.active_version ? (
                    <StatusBadge status="active" />
                  ) : (
                    <StatusBadge status="draft" />
                  )}
                  {agent.active_version && (
                    <span className="text-xs text-text-muted">v{agent.active_version}</span>
                  )}
                </div>

                <p className="text-xs text-text-muted mb-4">{formatDateTime(agent.created_at)}</p>

                <div className="flex gap-2">
                  <Link href={`/agents/${agent.id}`} className="flex-1">
                    <Button variant="secondary" size="sm" className="w-full gap-1">
                      <Settings className="h-3.5 w-3.5" /> Configure
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(agent.id, agent.name)}
                    className="text-text-muted hover:text-danger"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* Create modal */}
      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create AI Agent">
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          <Input
            label="Agent name"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="Sales Agent — Hindi"
            required
          />
          <Select
            label="Business template"
            value={form.template_slug}
            onChange={(e) => setForm((f) => ({ ...f, template_slug: e.target.value }))}
            required
          >
            {templates.map((t) => (
              <option key={t.slug} value={t.slug}>{t.name}</option>
            ))}
          </Select>
          <Select
            label="Voice profile"
            value={form.voice_profile_id}
            onChange={(e) => setForm((f) => ({ ...f, voice_profile_id: e.target.value }))}
            required
          >
            {voiceProfiles.length === 0 ? (
              <option value="">No voice profiles available</option>
            ) : (
              voiceProfiles.map((v) => (
                <option key={v.id} value={v.id}>{v.display_name} ({v.language})</option>
              ))
            )}
          </Select>
          <Input
            label="Description (optional)"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            placeholder="Handles outbound sales calls in Hindi"
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button type="submit" loading={creating}>Create Agent</Button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
}
