"use client";

import React, { useEffect, useState, useCallback } from "react";
import { UsersRound, Plus, Trash2 } from "lucide-react";
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
import { api, User } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { formatDateTime, initials } from "@/lib/utils";

const ORG_ROLES = [
  { value: "agent", label: "Agent" },
  { value: "supervisor", label: "Supervisor" },
  { value: "organization_admin", label: "Admin" },
];

export default function TeamPage() {
  const { user } = useAuth();
  const [members, setMembers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showInvite, setShowInvite] = useState(false);
  const [inviting, setInviting] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", role: "agent", first_name: "", last_name: "" });

  const canManage = user?.role === "organization_owner" || user?.role === "organization_admin";

  const load = useCallback(async () => {
    if (!user?.org_id) return;
    setLoading(true);
    try {
      const data = await api.users.listOrg(user.org_id);
      setMembers(data);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load team");
    } finally {
      setLoading(false);
    }
  }, [user?.org_id]);

  useEffect(() => { load(); }, [load]);

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    if (!user?.org_id) return;
    setInviting(true);
    try {
      await api.users.invite(user.org_id, {
        email: form.email,
        password: form.password,
        role: form.role,
        first_name: form.first_name || undefined,
        last_name: form.last_name || undefined,
      });
      toast.success("Team member added");
      setShowInvite(false);
      setForm({ email: "", password: "", role: "agent", first_name: "", last_name: "" });
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to add member");
    } finally {
      setInviting(false);
    }
  }

  async function handleDeactivate(userId: string) {
    if (!confirm("Deactivate this team member?")) return;
    try {
      await api.users.deactivate(userId);
      toast.success("Member deactivated");
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to deactivate");
    }
  }

  return (
    <AppShell title="Team">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Team Members</h2>
          <p className="text-sm text-text-secondary">{members.length} members</p>
        </div>
        {canManage && (
          <Button size="sm" onClick={() => setShowInvite(true)}>
            <Plus className="h-4 w-4 mr-1" /> Add Member
          </Button>
        )}
      </div>

      <Card>
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : members.length === 0 ? (
          <EmptyState icon={UsersRound} title="No team members" description="Invite teammates to collaborate" />
        ) : (
          <SimpleTable headers={["Member", "Role", "Status", "Joined", ""]}>
            {members.map((m) => (
              <TableRow key={m.id}>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div className="h-7 w-7 rounded-full bg-accent-subtle flex items-center justify-center text-xs font-medium text-accent">
                      {initials(m.email)}
                    </div>
                    <div>
                      <p className="text-text-primary">
                        {m.first_name || m.last_name
                          ? `${m.first_name ?? ""} ${m.last_name ?? ""}`.trim()
                          : m.email}
                      </p>
                      <p className="text-xs text-text-muted">{m.email}</p>
                    </div>
                  </div>
                </TableCell>
                <TableCell className="capitalize text-text-secondary">
                  {m.role.replace(/_/g, " ")}
                </TableCell>
                <TableCell>
                  <StatusBadge status={m.is_active ? "active" : "inactive"} />
                </TableCell>
                <TableCell className="text-xs text-text-muted">{formatDateTime(m.created_at)}</TableCell>
                <TableCell>
                  {canManage && m.id !== user?.user_id && (
                    <button
                      onClick={() => handleDeactivate(m.id)}
                      className="p-1 rounded text-text-muted hover:text-danger transition-colors"
                      title="Deactivate"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </SimpleTable>
        )}
      </Card>

      <Modal isOpen={showInvite} onClose={() => setShowInvite(false)} title="Add Team Member">
        <form onSubmit={handleInvite} className="flex flex-col gap-4">
          <Input
            label="Email"
            type="email"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            required
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="First name"
              value={form.first_name}
              onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))}
            />
            <Input
              label="Last name"
              value={form.last_name}
              onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))}
            />
          </div>
          <Select
            label="Role"
            value={form.role}
            onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
            options={ORG_ROLES}
          />
          <Input
            label="Temporary password"
            type="password"
            value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            hint="The member can change this after signing in"
            required
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setShowInvite(false)}>Cancel</Button>
            <Button type="submit" loading={inviting}>Add Member</Button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
}
