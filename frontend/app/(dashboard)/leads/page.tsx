"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Users, Plus, Upload, Search, Trash2, Sparkles, Tag } from "lucide-react";
import toast from "react-hot-toast";
import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Modal } from "@/components/ui/modal";
import { Pagination } from "@/components/ui/pagination";
import { Input, Select } from "@/components/ui/input";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, Lead, LeadListResponse, Campaign } from "@/lib/api";
import { formatDateTime, formatRelative } from "@/lib/utils";

const PAGE_SIZE = 50;

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "new", label: "New" },
  { value: "contacted", label: "Contacted" },
  { value: "qualified", label: "Qualified" },
  { value: "callback", label: "Callback" },
  { value: "not_interested", label: "Not Interested" },
  { value: "completed", label: "Completed" },
];

export default function LeadsPage() {
  const [result, setResult] = useState<LeadListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);

  const [form, setForm] = useState<{
    phone: string;
    name: string;
    email: string;
    tags: string;
    city: string;
    campaign_id: string;
    custom_vars: Array<{ key: string; value: string }>;
  }>({
    phone: "",
    name: "",
    email: "",
    tags: "",
    city: "",
    campaign_id: "",
    custom_vars: [],
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.leads.list({
        status: statusFilter || undefined,
        limit: PAGE_SIZE,
        skip: (page - 1) * PAGE_SIZE,
      });
      setResult(data);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load leads");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => { setPage(1); }, [statusFilter]);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    api.campaigns.list()
      .then((res) => setCampaigns(Array.isArray(res) ? res : []))
      .catch(() => {});
  }, []);

  function handleAddCustomVar() {
    setForm((f) => ({
      ...f,
      custom_vars: [...f.custom_vars, { key: "", value: "" }],
    }));
  }

  function handleRemoveCustomVar(idx: number) {
    setForm((f) => ({
      ...f,
      custom_vars: f.custom_vars.filter((_, i) => i !== idx),
    }));
  }

  function handleCustomVarChange(idx: number, field: "key" | "value", val: string) {
    setForm((f) => {
      const next = [...f.custom_vars];
      next[idx] = { ...next[idx], [field]: val };
      return { ...f, custom_vars: next };
    });
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.phone.trim()) {
      toast.error("Phone number is required");
      return;
    }

    setCreating(true);
    try {
      const custom_fields: Record<string, unknown> = {};
      if (form.city.trim()) {
        custom_fields["city"] = form.city.trim();
      }
      for (const cv of form.custom_vars) {
        if (cv.key.trim()) {
          const sanitizedKey = cv.key.trim().toLowerCase().replace(/[^a-z0-9_]/g, "");
          custom_fields[sanitizedKey] = cv.value.trim();
        }
      }

      const tagsList = form.tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);

      const created = await api.leads.create({
        phone: form.phone.trim(),
        name: form.name.trim() || undefined,
        email: form.email.trim() || undefined,
        tags: tagsList.length ? tagsList : undefined,
        custom_fields: Object.keys(custom_fields).length ? custom_fields : undefined,
        source: "manual",
      });

      if (form.campaign_id && created?.id) {
        try {
          await api.campaigns.enrollLeads(form.campaign_id, { lead_ids: [created.id] });
          toast.success("Lead created and enrolled in campaign!");
        } catch {
          toast.success("Lead created (campaign enrollment optional)");
        }
      } else {
        toast.success("Lead created with mapped variables!");
      }

      setShowCreate(false);
      setForm({
        phone: "",
        name: "",
        email: "",
        tags: "",
        city: "",
        campaign_id: "",
        custom_vars: [],
      });
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create lead");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this lead?")) return;
    try {
      await api.leads.delete(id);
      toast.success("Lead deleted");
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to delete lead");
    }
  }

  const leads = result?.leads ?? [];

  return (
    <AppShell title="Leads">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Leads & Contacts</h2>
          {result && (
            <p className="text-sm text-text-secondary">{result.total.toLocaleString("en-IN")} total contacts</p>
          )}
        </div>
        <div className="flex gap-2">
          <Link href="/leads/import">
            <Button variant="secondary" size="sm" className="gap-1.5">
              <Upload className="h-4 w-4" />
              Import CSV / XLSX / JSON
            </Button>
          </Link>
          <Button size="sm" onClick={() => setShowCreate(true)} className="gap-1.5">
            <Plus className="h-4 w-4" /> Add Lead & Variables
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative flex-1 min-w-48 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted pointer-events-none" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by phone, name, or variable…"
            className="w-full rounded-md border border-border bg-surface pl-9 pr-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
          />
        </div>
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          options={STATUS_OPTIONS}
          className="w-40"
        />
      </div>

      <Card>
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : leads.length === 0 ? (
          <EmptyState
            icon={Users}
            title="No leads found"
            description={statusFilter ? "Try a different status filter" : "Add contacts manually or import with the dynamic variable mapper"}
            action={
              <div className="flex gap-2">
                <Link href="/leads/import">
                  <Button variant="secondary" size="sm">Import CSV / Excel</Button>
                </Link>
                <Button size="sm" onClick={() => setShowCreate(true)}>Add Lead</Button>
              </div>
            }
          />
        ) : (
          <>
            <SimpleTable headers={["Phone", "Name & Prompt Var", "Tags & AI Variables", "Status", "Score", "Attempts", "Last Contact", ""]}>
              {leads
                .filter((l) => {
                  if (!search) return true;
                  const q = search.toLowerCase();
                  return (
                    l.phone?.toLowerCase().includes(q) ||
                    l.name?.toLowerCase().includes(q) ||
                    (l.tags && l.tags.some((t) => t.toLowerCase().includes(q)))
                  );
                })
                .map((lead) => {
                  const customFields = (lead.custom_fields || {}) as Record<string, unknown>;
                  const customEntries = Object.entries(customFields).filter(
                    ([k]) => !["name", "user_name", "phone"].includes(k)
                  );

                  return (
                    <TableRow key={lead.id}>
                      <TableCell className="font-mono text-xs">{lead.phone}</TableCell>
                      <TableCell>
                        {lead.name ? (
                          <div>
                            <span className="font-medium text-text-primary">{lead.name}</span>
                            <span className="block text-[11px] text-text-muted font-mono">&#123;user_name&#125;</span>
                          </div>
                        ) : (
                          <span className="text-text-muted italic">Unassigned</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap items-center gap-1.5 max-w-xs">
                          {lead.tags && lead.tags.length > 0 && lead.tags.map((tag) => (
                            <span
                              key={tag}
                              className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-primary/10 text-primary border border-primary/20"
                            >
                              <Tag className="h-2.5 w-2.5" />
                              {tag}
                            </span>
                          ))}
                          {customEntries.slice(0, 3).map(([k, v]) => (
                            <span
                              key={k}
                              className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono bg-surface-subtle text-text-secondary border border-border"
                              title={`{${k}} = ${String(v)}`}
                            >
                              &#123;{k}&#125;: {String(v).slice(0, 10)}
                            </span>
                          ))}
                          {customEntries.length > 3 && (
                            <span className="text-[10px] text-text-muted">+{customEntries.length - 3} more</span>
                          )}
                          {(!lead.tags || lead.tags.length === 0) && customEntries.length === 0 && (
                            <span className="text-xs text-text-muted">—</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell><StatusBadge status={lead.status} /></TableCell>
                      <TableCell>
                        {lead.score > 0 ? (
                          <ScoreBar score={lead.score} />
                        ) : <span className="text-text-muted">—</span>}
                      </TableCell>
                      <TableCell className="text-text-secondary">{lead.attempts}</TableCell>
                      <TableCell className="text-xs text-text-muted">{formatRelative(lead.last_contact_at)}</TableCell>
                      <TableCell>
                        <button
                          onClick={() => handleDelete(lead.id)}
                          className="p-1 rounded text-text-muted hover:text-danger transition-colors cursor-pointer"
                          title="Delete Lead"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </TableCell>
                    </TableRow>
                  );
                })}
            </SimpleTable>
            {result && result.total > PAGE_SIZE && (
              <div className="px-4 py-3 border-t border-border">
                <Pagination
                  page={page}
                  pageSize={PAGE_SIZE}
                  total={result.total}
                  onPageChange={setPage}
                />
              </div>
            )}
          </>
        )}
      </Card>

      {/* Enhanced Create Lead Modal with Variable Mapping */}
      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Add Lead & Map AI Variables">
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          <div className="rounded-lg bg-surface-subtle p-3 text-xs text-text-secondary flex items-start gap-2 border border-border">
            <Sparkles className="h-4 w-4 text-accent shrink-0 mt-0.5" />
            <p>
              Fields entered here map directly to AI agent variables during live calls.
              For instance, <strong>Name</strong> replaces <code className="text-accent">&#123;user_name&#125;</code> and <strong>Tags</strong> replace <code className="text-accent">&#123;tags&#125;</code>.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Phone number *"
              value={form.phone}
              onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
              placeholder="+919876543210"
              required
            />
            <Input
              label="Contact / User Name ({user_name})"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Rahul Sharma"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Lead Tags ({tags})"
              value={form.tags}
              onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
              placeholder="e.g. VIP, diwali-offer, lead"
            />
            <Input
              label="City ({city})"
              value={form.city}
              onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))}
              placeholder="e.g. Mumbai"
            />
          </div>

          <Input
            label="Email (optional)"
            type="email"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            placeholder="rahul@example.com"
          />

          {campaigns.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">
                Enroll directly into Campaign (optional)
              </label>
              <Select
                value={form.campaign_id}
                onChange={(e) => setForm((f) => ({ ...f, campaign_id: e.target.value }))}
                options={[
                  { value: "", label: "None (Save to general Contacts)" },
                  ...campaigns.map((c) => ({ value: c.id, label: `📢 ${c.name}` })),
                ]}
              />
            </div>
          )}

          {/* Custom Variables Section */}
          <div className="space-y-2 border-t border-border pt-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-text-primary">Custom AI Variables</span>
                <p className="text-[11px] text-text-muted">Add custom keys like balance, due_date, vehicle_model</p>
              </div>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={handleAddCustomVar}
                className="text-xs h-7 gap-1"
              >
                <Plus className="h-3 w-3" /> Add Variable
              </Button>
            </div>

            {form.custom_vars.length > 0 && (
              <div className="space-y-2">
                {form.custom_vars.map((cv, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className="text-xs text-text-muted font-mono">&#123;</span>
                    <Input
                      value={cv.key}
                      onChange={(e) => handleCustomVarChange(idx, "key", e.target.value)}
                      placeholder="variable_name"
                      className="font-mono text-xs flex-1"
                    />
                    <span className="text-xs text-text-muted font-mono">&#125; :</span>
                    <Input
                      value={cv.value}
                      onChange={(e) => handleCustomVarChange(idx, "value", e.target.value)}
                      placeholder="Value (e.g. ₹4,500)"
                      className="text-xs flex-1"
                    />
                    <button
                      type="button"
                      onClick={() => handleRemoveCustomVar(idx)}
                      className="p-1.5 text-text-muted hover:text-danger rounded"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button type="button" variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button type="submit" loading={creating}>Save Lead</Button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 70 ? "bg-success" : score >= 40 ? "bg-warning" : "bg-danger";
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs font-medium text-text-primary w-6">{score}</span>
      <div className="h-1.5 w-12 bg-surface-subtle rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}
