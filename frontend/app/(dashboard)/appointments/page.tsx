"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Calendar, Plus, Check, X, RefreshCw } from "lucide-react";
import toast from "react-hot-toast";
import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Modal } from "@/components/ui/modal";
import { Input, Select } from "@/components/ui/input";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { Pagination } from "@/components/ui/pagination";
import { api, Appointment } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

const PAGE_SIZE = 50;
const STATUS_OPTIONS = [
  { value: "", label: "All" },
  { value: "scheduled", label: "Scheduled" },
  { value: "confirmed", label: "Confirmed" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "no_show", label: "No Show" },
];

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);

  const [form, setForm] = useState({
    scheduled_at: "",
    appointment_type: "general",
    title: "",
    duration_minutes: "30",
    notes: "",
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.appointments.list({
        appt_status: statusFilter || undefined,
        limit: PAGE_SIZE,
        skip: (page - 1) * PAGE_SIZE,
      });
      setAppointments(data);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load appointments");
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
      await api.appointments.create({
        scheduled_at: new Date(form.scheduled_at).toISOString(),
        appointment_type: form.appointment_type,
        title: form.title || undefined,
        duration_minutes: parseInt(form.duration_minutes) || 30,
        notes: form.notes || undefined,
      });
      toast.success("Appointment created");
      setShowCreate(false);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create appointment");
    } finally {
      setCreating(false);
    }
  }

  async function handleAction(id: string, fn: () => Promise<Appointment>, label: string) {
    setActionId(id);
    try {
      await fn();
      toast.success(`Appointment ${label}`);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : `Failed to ${label}`);
    } finally {
      setActionId(null);
    }
  }

  return (
    <AppShell title="Appointments">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Appointments</h2>
          <p className="text-sm text-text-secondary">{appointments.length} shown</p>
        </div>
        <div className="flex gap-2">
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            options={STATUS_OPTIONS}
            className="w-36"
          />
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4 mr-1" /> New
          </Button>
        </div>
      </div>

      <Card>
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : appointments.length === 0 ? (
          <EmptyState
            icon={Calendar}
            title="No appointments"
            description={statusFilter ? "No appointments with this status" : "Appointments set during calls appear here"}
            action={<Button onClick={() => setShowCreate(true)}>New Appointment</Button>}
          />
        ) : (
          <>
            <SimpleTable headers={["Lead", "Title", "Type", "Scheduled", "Duration", "Status", "Actions"]}>
              {appointments.map((a) => (
                <TableRow key={a.id}>
                  <TableCell>
                    <div>
                      <p className="text-text-primary">{a.lead_name ?? "—"}</p>
                      <p className="text-xs text-text-muted font-mono">{a.lead_phone ?? ""}</p>
                    </div>
                  </TableCell>
                  <TableCell>{a.title ?? a.appointment_type}</TableCell>
                  <TableCell className="text-text-secondary capitalize">{a.appointment_type.replace(/_/g, " ")}</TableCell>
                  <TableCell className="text-xs whitespace-nowrap">{formatDateTime(a.scheduled_at)}</TableCell>
                  <TableCell className="text-text-secondary">{a.duration_minutes}m</TableCell>
                  <TableCell><StatusBadge status={a.status} /></TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {a.status === "scheduled" && (
                        <button
                          onClick={() => handleAction(a.id, () => api.appointments.confirm(a.id), "confirmed")}
                          className="p-1 rounded text-text-muted hover:text-success transition-colors"
                          title="Confirm"
                          disabled={actionId === a.id}
                        >
                          <Check className="h-4 w-4" />
                        </button>
                      )}
                      {["scheduled", "confirmed"].includes(a.status) && (
                        <button
                          onClick={() => handleAction(a.id, () => api.appointments.cancel(a.id), "cancelled")}
                          className="p-1 rounded text-text-muted hover:text-danger transition-colors"
                          title="Cancel"
                          disabled={actionId === a.id}
                        >
                          <X className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </SimpleTable>
            {appointments.length === PAGE_SIZE && (
              <div className="px-4 py-3 border-t border-border">
                <Pagination page={page} pageSize={PAGE_SIZE} total={page * PAGE_SIZE + 1} onPageChange={setPage} />
              </div>
            )}
          </>
        )}
      </Card>

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="New Appointment">
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          <Input
            label="Date & Time"
            type="datetime-local"
            value={form.scheduled_at}
            onChange={(e) => setForm((f) => ({ ...f, scheduled_at: e.target.value }))}
            required
          />
          <Input
            label="Title (optional)"
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            placeholder="Follow-up call"
          />
          <div className="grid grid-cols-2 gap-3">
            <Select
              label="Type"
              value={form.appointment_type}
              onChange={(e) => setForm((f) => ({ ...f, appointment_type: e.target.value }))}
              options={[
                { value: "general", label: "General" },
                { value: "follow_up", label: "Follow-up" },
                { value: "demo", label: "Demo" },
                { value: "site_visit", label: "Site Visit" },
              ]}
            />
            <Input
              label="Duration (minutes)"
              type="number"
              min="5"
              value={form.duration_minutes}
              onChange={(e) => setForm((f) => ({ ...f, duration_minutes: e.target.value }))}
            />
          </div>
          <Input
            label="Notes (optional)"
            value={form.notes}
            onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button type="submit" loading={creating}>Create</Button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
}
