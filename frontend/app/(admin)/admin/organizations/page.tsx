"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Building2, KeyRound, Eye, EyeOff, Sparkles } from "lucide-react";
import toast from "react-hot-toast";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Pagination } from "@/components/ui/pagination";
import { Select, Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, Organization } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

const PAGE_SIZE = 50;

function generateRandomPassword(length = 12): string {
  const chars = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%&*";
  let pass = "";
  for (let i = 0; i < length; i++) {
    pass += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return pass;
}

export default function AdminOrgsPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [acting, setActing] = useState<string | null>(null);

  // Password update modal state
  const [passwordOrg, setPasswordOrg] = useState<Organization | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [updatingPassword, setUpdatingPassword] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.admin.organizations.list({
        org_status: statusFilter || undefined,
        limit: PAGE_SIZE,
        skip: (page - 1) * PAGE_SIZE,
      });
      setOrgs(data);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => { setPage(1); }, [statusFilter]);
  useEffect(() => { load(); }, [load]);

  async function toggleOrg(org: Organization) {
    setActing(org.id);
    try {
      if (org.status === "active") {
        await api.admin.organizations.suspend(org.id);
        toast.success("Org suspended");
      } else {
        await api.admin.organizations.reactivate(org.id);
        toast.success("Org reactivated");
      }
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Action failed");
    } finally {
      setActing(null);
    }
  }

  function openPasswordModal(org: Organization) {
    setPasswordOrg(org);
    setNewPassword("");
    setConfirmPassword("");
    setShowPassword(false);
  }

  function handleGeneratePassword() {
    const generated = generateRandomPassword();
    setNewPassword(generated);
    setConfirmPassword(generated);
    setShowPassword(true);
  }

  async function handleUpdatePassword(e: React.FormEvent) {
    e.preventDefault();
    if (!passwordOrg) return;

    if (newPassword.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }

    if (newPassword !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    setUpdatingPassword(true);
    try {
      const res = await api.admin.organizations.updatePassword(passwordOrg.id, newPassword);
      toast.success(res.message || `Password updated for ${passwordOrg.name}`);
      setPasswordOrg(null);
      setNewPassword("");
      setConfirmPassword("");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update password");
    } finally {
      setUpdatingPassword(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">Organisations</h2>
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          options={[
            { value: "", label: "All Statuses" },
            { value: "active", label: "Active" },
            { value: "suspended", label: "Suspended" },
          ]}
          className="w-40"
        />
      </div>

      <Card>
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : orgs.length === 0 ? (
          <EmptyState icon={Building2} title="No organisations" />
        ) : (
          <>
            <SimpleTable headers={["Name", "Email", "Status", "Agents", "Campaigns", "Created", "Actions"]}>
              {orgs.map((org) => (
                <TableRow key={org.id}>
                  <TableCell>
                    <Link href={`/admin/organizations/${org.id}`} className="text-accent hover:underline font-medium">
                      {org.name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-text-secondary">{org.email}</TableCell>
                  <TableCell><StatusBadge status={org.status} /></TableCell>
                  <TableCell className="text-text-secondary">{org.max_agents}</TableCell>
                  <TableCell className="text-text-secondary">{org.max_campaigns}</TableCell>
                  <TableCell className="text-xs text-text-muted whitespace-nowrap">{formatDateTime(org.created_at)}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => openPasswordModal(org)}
                        className="text-text-secondary hover:text-accent flex items-center gap-1 px-2"
                        title="Update organization password"
                      >
                        <KeyRound className="h-3.5 w-3.5" />
                        <span>Password</span>
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        loading={acting === org.id}
                        onClick={() => toggleOrg(org)}
                        className={org.status === "active" ? "text-warning hover:text-warning" : "text-success hover:text-success"}
                      >
                        {org.status === "active" ? "Suspend" : "Reactivate"}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </SimpleTable>
            {orgs.length === PAGE_SIZE && (
              <div className="px-4 py-3 border-t border-border">
                <Pagination page={page} pageSize={PAGE_SIZE} total={page * PAGE_SIZE + 1} onPageChange={setPage} />
              </div>
            )}
          </>
        )}
      </Card>

      {/* Update Password Modal */}
      <Modal
        isOpen={passwordOrg !== null}
        onClose={() => {
          if (!updatingPassword) {
            setPasswordOrg(null);
            setNewPassword("");
            setConfirmPassword("");
          }
        }}
        title={`Update Password — ${passwordOrg?.name ?? ""}`}
        size="md"
      >
        <form onSubmit={handleUpdatePassword} className="p-6 space-y-4">
          <div className="rounded-lg bg-surface-subtle p-3.5 border border-border text-xs text-text-secondary space-y-1">
            <p className="font-semibold text-text-primary">Target Organization Account</p>
            <p>
              Organization: <span className="font-medium text-text-primary">{passwordOrg?.name}</span>
            </p>
            <p>
              Account Email: <span className="font-medium text-text-primary">{passwordOrg?.email}</span>
            </p>
            <p className="text-text-muted pt-1">
              Updating this will set a new login password for the organization&apos;s owner user.
            </p>
          </div>

          <div className="space-y-3">
            <div className="relative">
              <Input
                label="New Password"
                type={showPassword ? "text" : "password"}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="At least 8 characters"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute right-3 top-8 text-text-muted hover:text-text-primary transition-colors"
                title={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-[11px] text-text-muted">Min 8 characters</span>
              <button
                type="button"
                onClick={handleGeneratePassword}
                className="text-xs text-accent hover:underline flex items-center gap-1 font-medium"
              >
                <Sparkles className="h-3 w-3" />
                <span>Generate random password</span>
              </button>
            </div>

            <Input
              label="Confirm New Password"
              type={showPassword ? "text" : "password"}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter new password"
              required
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-4 border-t border-border">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={updatingPassword}
              onClick={() => {
                setPasswordOrg(null);
                setNewPassword("");
                setConfirmPassword("");
              }}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              loading={updatingPassword}
              disabled={!newPassword || newPassword.length < 8 || newPassword !== confirmPassword}
            >
              Update Password
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
