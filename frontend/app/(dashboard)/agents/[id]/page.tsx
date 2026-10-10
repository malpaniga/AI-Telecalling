"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Plus, Check, Upload } from "lucide-react";
import toast from "react-hot-toast";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { Modal } from "@/components/ui/modal";
import { Input } from "@/components/ui/input";
import { api, Agent, AgentVersion, BusinessTemplate } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [versions, setVersions] = useState<AgentVersion[]>([]);
  const [template, setTemplate] = useState<BusinessTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [showNewVersion, setShowNewVersion] = useState(false);
  const [creating, setCreating] = useState(false);
  const [publishing, setPublishing] = useState<string | null>(null);
  const [configText, setConfigText] = useState("{}");
  const [configError, setConfigError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [a, v, templates] = await Promise.all([
        api.agents.get(id),
        api.agents.versions.list(id),
        api.agents.templates(),
      ]);
      setAgent(a);
      setVersions(v);
      const tmpl = templates.find((t) => t.slug === a.template_slug);
      if (tmpl) {
        setTemplate(tmpl);
        setConfigText(JSON.stringify(tmpl.default_configuration, null, 2));
      }
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load agent");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  async function handleCreateVersion(e: React.FormEvent) {
    e.preventDefault();
    setConfigError(null);
    let config: Record<string, unknown>;
    try {
      config = JSON.parse(configText);
    } catch {
      setConfigError("Invalid JSON configuration");
      return;
    }
    if (!id) return;
    setCreating(true);
    try {
      await api.agents.versions.create(id, { configuration: config, auto_activate: false });
      toast.success("Draft version created");
      setShowNewVersion(false);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create version");
    } finally {
      setCreating(false);
    }
  }

  async function handlePublish(versionId: string) {
    if (!id) return;
    setPublishing(versionId);
    try {
      await api.agents.versions.publish(id, versionId);
      toast.success("Version published and activated");
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to publish");
    } finally {
      setPublishing(null);
    }
  }

  if (loading) {
    return (
      <AppShell title="Agent">
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      </AppShell>
    );
  }

  if (!agent) return null;

  return (
    <AppShell
      title={agent.name}
      breadcrumb={[{ label: "AI Agents", href: "/agents" }, { label: agent.name }]}
    >
      <div className="mb-4">
        <Link href="/agents">
          <Button variant="ghost" size="sm" className="gap-1 text-text-secondary">
            <ChevronLeft className="h-4 w-4" /> Back to Agents
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Agent info */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <h3 className="text-sm font-medium text-text-primary">Agent Details</h3>
          </CardHeader>
          <CardBody className="space-y-3 text-sm">
            <Row label="Template" value={agent.template_slug.replace(/_/g, " ")} />
            <Row label="Status">
              <StatusBadge status={agent.is_active ? "active" : "inactive"} />
            </Row>
            <Row label="Active version" value={agent.active_version ? `v${agent.active_version}` : "None"} />
            <Row label="Created" value={formatDateTime(agent.created_at)} />
            {agent.description && (
              <div>
                <p className="text-xs text-text-muted mb-1">Description</p>
                <p className="text-text-secondary">{agent.description}</p>
              </div>
            )}
          </CardBody>
        </Card>

        {/* Versions */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-text-primary">Versions</h3>
              <Button size="sm" onClick={() => setShowNewVersion(true)}>
                <Plus className="h-4 w-4 mr-1" /> New Draft
              </Button>
            </div>
          </CardHeader>
          <div>
            {versions.length === 0 ? (
              <div className="px-6 py-8 text-center text-sm text-text-muted">
                No versions yet. Create a draft to configure this agent.
              </div>
            ) : (
              versions.map((v) => (
                <div
                  key={v.id}
                  className="border-b border-border last:border-b-0 px-6 py-4 flex items-center justify-between gap-4"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-text-primary">v{v.version}</span>
                      <StatusBadge status={v.status} />
                      {agent.active_version_id === v.id && (
                        <span className="text-xs text-success flex items-center gap-1">
                          <Check className="h-3 w-3" /> Active
                        </span>
                      )}
                    </div>
                    {v.description && (
                      <p className="text-xs text-text-secondary">{v.description}</p>
                    )}
                    <p className="text-xs text-text-muted">{formatDateTime(v.created_at)}</p>
                  </div>
                  {v.status === "draft" && (
                    <Button
                      size="sm"
                      variant="secondary"
                      loading={publishing === v.id}
                      onClick={() => handlePublish(v.id)}
                      className="gap-1 shrink-0"
                    >
                      <Upload className="h-3.5 w-3.5" /> Publish
                    </Button>
                  )}
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Template info */}
        {template && (
          <Card className="lg:col-span-3">
            <CardHeader>
              <h3 className="text-sm font-medium text-text-primary">
                Template: {template.name}
              </h3>
            </CardHeader>
            <CardBody>
              <p className="text-sm text-text-secondary mb-4">{template.description}</p>
              {Object.keys(template.slot_definitions).length > 0 && (
                <div>
                  <p className="text-xs font-medium text-text-muted uppercase tracking-wide mb-2">Configuration Slots</p>
                  <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
                    {Object.entries(template.slot_definitions).map(([key, def]) => (
                      <div key={key} className="border border-border rounded-md p-3">
                        <p className="text-xs font-medium text-text-primary">{key}</p>
                        <p className="text-xs text-text-muted mt-0.5">
                          {typeof def === "object" && def !== null && "description" in def
                            ? String((def as Record<string, unknown>).description)
                            : ""}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardBody>
          </Card>
        )}
      </div>

      {/* New version modal */}
      <Modal isOpen={showNewVersion} onClose={() => setShowNewVersion(false)} title="Create Draft Version" size="lg">
        <form onSubmit={handleCreateVersion} className="flex flex-col gap-4">
          <div>
            <label className="text-sm font-medium text-text-primary block mb-1">
              Configuration (JSON)
            </label>
            <textarea
              value={configText}
              onChange={(e) => setConfigText(e.target.value)}
              rows={12}
              className="w-full rounded-md border border-border bg-surface px-3 py-2 font-mono text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              spellCheck={false}
            />
            {configError && <p className="text-xs text-danger mt-1">{configError}</p>}
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setShowNewVersion(false)}>Cancel</Button>
            <Button type="submit" loading={creating}>Create Draft</Button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
}

function Row({ label, value, children }: { label: string; value?: string; children?: React.ReactNode }) {
  return (
    <div className="flex justify-between items-start gap-2">
      <span className="text-text-muted shrink-0">{label}</span>
      <span className="text-text-primary text-right font-medium">
        {children ?? value}
      </span>
    </div>
  );
}
