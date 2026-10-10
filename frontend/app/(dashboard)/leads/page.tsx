"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { Users, Plus, Upload, Search, Filter, Trash2 } from "lucide-react";
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
import { api, Lead, LeadListResponse } from "@/lib/api";
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
  const [showImport, setShowImport] = useState(false);
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState({ phone: "", name: "", email: "", source: "manual" });

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

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await api.leads.create({
        phone: form.phone,
        name: form.name || undefined,
        email: form.email || undefined,
        source: form.source,
      });
      toast.success("Lead created");
      setShowCreate(false);
      setForm({ phone: "", name: "", email: "", source: "manual" });
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

  async function handleImport(e: React.FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return toast.error("Select a file");
    setImporting(true);
    try {
      const result = await api.leads.import(file);
      toast.success(`Imported ${result.imported} leads (${result.skipped} skipped)`);
      setShowImport(false);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Import failed");
    } finally {
      setImporting(false);
    }
  }

  const leads = result?.leads ?? [];

  return (
    <AppShell title="Leads">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Leads</h2>
          {result && (
            <p className="text-sm text-text-secondary">{result.total.toLocaleString("en-IN")} total</p>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => setShowImport(true)}>
            <Upload className="h-4 w-4 mr-1" /> Import
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4 mr-1" /> Add Lead
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
            placeholder="Search by phone or name…"
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
            description={statusFilter ? "Try a different status filter" : "Add or import leads to get started"}
            action={
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => setShowImport(true)}>Import CSV</Button>
                <Button size="sm" onClick={() => setShowCreate(true)}>Add Lead</Button>
              </div>
            }
          />
        ) : (
          <>
            <SimpleTable headers={["Phone", "Name", "Status", "Score", "Attempts", "Last Contact", "Created", ""]}>
              {leads
                .filter((l) => {
                  if (!search) return true;
                  const q = search.toLowerCase();
                  return l.phone?.toLowerCase().includes(q) || l.name?.toLowerCase().includes(q);
                })
                .map((lead) => (
                  <TableRow key={lead.id}>
                    <TableCell className="font-mono text-xs">{lead.phone}</TableCell>
                    <TableCell>{lead.name ?? <span className="text-text-muted">—</span>}</TableCell>
                    <TableCell><StatusBadge status={lead.status} /></TableCell>
                    <TableCell>
                      {lead.score > 0 ? (
                        <ScoreBar score={lead.score} />
                      ) : <span className="text-text-muted">—</span>}
                    </TableCell>
                    <TableCell className="text-text-secondary">{lead.attempts}</TableCell>
                    <TableCell className="text-xs text-text-muted">{formatRelative(lead.last_contact_at)}</TableCell>
                    <TableCell className="text-xs text-text-muted">{formatDateTime(lead.created_at)}</TableCell>
                    <TableCell>
                      <button
                        onClick={() => handleDelete(lead.id)}
                        className="p-1 rounded text-text-muted hover:text-danger transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </TableCell>
                  </TableRow>
                ))}
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

      {/* Create lead modal */}
      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Add Lead">
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          <Input
            label="Phone number"
            value={form.phone}
            onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
            placeholder="+919876543210"
            required
          />
          <Input
            label="Name (optional)"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="Rahul Sharma"
          />
          <Input
            label="Email (optional)"
            type="email"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            placeholder="rahul@example.com"
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button type="submit" loading={creating}>Add Lead</Button>
          </div>
        </form>
      </Modal>

      {/* Import modal */}
      <Modal isOpen={showImport} onClose={() => setShowImport(false)} title="Import Leads">
        <form onSubmit={handleImport} className="flex flex-col gap-4">
          <div>
            <p className="text-sm text-text-secondary mb-3">
              Upload a CSV, XLSX, or JSON file. The file must include a <code className="bg-surface-subtle px-1 rounded text-xs">phone</code> column.
              Optional columns: <code className="bg-surface-subtle px-1 rounded text-xs">name</code>, <code className="bg-surface-subtle px-1 rounded text-xs">email</code>.
            </p>
            <label className="flex flex-col items-center justify-center border-2 border-dashed border-border rounded-lg p-6 cursor-pointer hover:border-accent transition-colors">
              <Upload className="h-8 w-8 text-text-muted mb-2" />
              <span className="text-sm text-text-secondary">Click to select file</span>
              <span className="text-xs text-text-muted mt-0.5">CSV, XLSX, JSON</span>
              <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls,.json" className="hidden" />
            </label>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setShowImport(false)}>Cancel</Button>
            <Button type="submit" loading={importing}>Import</Button>
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
