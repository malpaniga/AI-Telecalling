"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Hash, Plus, ShieldCheck, PhoneCall, Building2 } from "lucide-react";
import toast from "react-hot-toast";
import { Card, CardBody } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Pagination } from "@/components/ui/pagination";
import { Modal } from "@/components/ui/modal";
import { Input, Select } from "@/components/ui/input";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, PhoneNumber } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

const PAGE_SIZE = 100;

type Stats = {
  available: number;
  assigned: number;
  suspended: number;
  maintenance: number;
  total: number;
  [key: string]: unknown;
};

interface OrgItem {
  id: string;
  name: string;
}

interface AgentItem {
  id: string;
  name: string;
}

export default function AdminPhoneNumbersPage() {
  const [numbers, setNumbers] = useState<PhoneNumber[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [stats, setStats] = useState<Stats | null>(null);

  // Organizations list for assignment
  const [organizations, setOrganizations] = useState<OrgItem[]>([]);

  // Add number
  const [showAdd, setShowAdd] = useState(false);
  const [adding, setAdding] = useState(false);
  const [showToken, setShowToken] = useState(false);
  const [addForm, setAddForm] = useState({
    number: "",
    provider: "vobiz",
    provider_resource_id: "",
    vobiz_auth_id: "",
    vobiz_auth_token: "",
    vobiz_trunk_id: "",
    plivo_auth_id: "",
    plivo_auth_token: "",
    plivo_app_id: "",
    display_name: "",
    country_code: "IN",
    number_type: "local",
    rental_paise_per_month: "",
  });

  // Assign number
  const [showAssign, setShowAssign] = useState(false);
  const [assigningId, setAssigningId] = useState<string | null>(null);
  const [assigningNumber, setAssigningNumber] = useState<PhoneNumber | null>(null);
  const [selectedOrgIds, setSelectedOrgIds] = useState<string[]>([]);
  const [inboundOrgId, setInboundOrgId] = useState<string>("");
  const [inboundAgentId, setInboundAgentId] = useState<string>("");
  const [availableAgents, setAvailableAgents] = useState<AgentItem[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [assigning, setAssigning] = useState(false);

  // Action in-progress
  const [actingId, setActingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nums, st, orgsRes] = await Promise.all([
        api.admin.phoneNumbers.list({
          limit: PAGE_SIZE,
          skip: (page - 1) * PAGE_SIZE,
        }),
        api.admin.phoneNumbers.stats(),
        api.admin.organizations.list({ limit: 100 }),
      ]);
      setNumbers(nums);
      setStats(st as Stats);
      setOrganizations(
        orgsRes.map((o) => ({ id: o.id, name: o.name || o.id }))
      );
    } catch (e: unknown) {
      toast.error(
        e instanceof Error ? e.message : "Failed to load phone numbers"
      );
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

  // Load agents whenever inboundOrgId changes
  useEffect(() => {
    if (!inboundOrgId) {
      setAvailableAgents([]);
      setInboundAgentId("");
      return;
    }
    let cancelled = false;
    setLoadingAgents(true);
    api.agents
      .list()
      .then((agents) => {
        if (!cancelled) {
          const orgAgents = agents.filter(
            (a) => a.organization_id === inboundOrgId
          );
          setAvailableAgents(
            orgAgents.map((a) => ({ id: a.id, name: a.name || a.id }))
          );
          if (orgAgents.length > 0 && !inboundAgentId) {
            setInboundAgentId(orgAgents[0].id);
          }
        }
      })
      .catch(() => {
        if (!cancelled) setAvailableAgents([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingAgents(false);
      });
    return () => {
      cancelled = true;
    };
  }, [inboundOrgId, inboundAgentId]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setAdding(true);
    try {
      const isVobiz = addForm.provider === "vobiz";
      const isPlivo = addForm.provider === "plivo";
      if (isPlivo && (!addForm.plivo_auth_id.trim() || !addForm.plivo_auth_token.trim())) {
        toast.error("Plivo Auth ID and Auth Token are required");
        setAdding(false);
        return;
      }
      if (isVobiz && (!addForm.vobiz_auth_id.trim() || !addForm.vobiz_auth_token.trim())) {
        toast.error("Vobiz Auth ID and Auth Token are required");
        setAdding(false);
        return;
      }
      await api.phoneNumbers.addAdmin({
        number: addForm.number.trim(),
        provider: addForm.provider,
        provider_resource_id: isPlivo
          ? addForm.plivo_auth_id.trim() || addForm.number.trim()
          : isVobiz
          ? addForm.vobiz_auth_id || addForm.number.trim()
          : addForm.provider_resource_id || addForm.number.trim(),
        display_name: addForm.display_name || undefined,
        country_code: addForm.country_code,
        number_type: addForm.number_type,
        rental_paise_per_month: addForm.rental_paise_per_month
          ? parseInt(addForm.rental_paise_per_month)
          : undefined,
        provider_metadata: isPlivo
          ? {
              plivo_auth_id: addForm.plivo_auth_id.trim(),
              plivo_auth_token: addForm.plivo_auth_token.trim(),
              plivo_app_id: addForm.plivo_app_id.trim() || undefined,
            }
          : isVobiz
          ? {
              vobiz_auth_id: addForm.vobiz_auth_id.trim(),
              vobiz_auth_token: addForm.vobiz_auth_token.trim(),
              vobiz_trunk_id: addForm.vobiz_trunk_id.trim() || undefined,
            }
          : undefined,
      });
      toast.success("Phone number added to inventory");
      setShowAdd(false);
      setAddForm({
        number: "",
        provider: "vobiz",
        provider_resource_id: "",
        vobiz_auth_id: "",
        vobiz_auth_token: "",
        vobiz_trunk_id: "",
        plivo_auth_id: "",
        plivo_auth_token: "",
        plivo_app_id: "",
        display_name: "",
        country_code: "IN",
        number_type: "local",
        rental_paise_per_month: "",
      });
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to add number");
    } finally {
      setAdding(false);
    }
  }

  function openAssignModal(n: PhoneNumber) {
    setAssigningId(n.id);
    setAssigningNumber(n);
    const existing = n.assigned_org_ids?.length
      ? n.assigned_org_ids
      : n.organization_id
      ? [n.organization_id]
      : [];
    setSelectedOrgIds(existing);
    setInboundOrgId(n.inbound_organization_id || existing[0] || "");
    setInboundAgentId(n.inbound_agent_id || "");
    setShowAssign(true);
  }

  async function handleAssign(e: React.FormEvent) {
    e.preventDefault();
    if (!assigningId) return;
    if (selectedOrgIds.length === 0) {
      return toast.error("Please select at least one organization");
    }
    setAssigning(true);
    try {
      await api.phoneNumbers.assign(assigningId, {
        org_ids: selectedOrgIds,
        inbound_organization_id: inboundOrgId || selectedOrgIds[0],
        inbound_agent_id: inboundAgentId || undefined,
      });
      toast.success("Number assigned successfully");
      setShowAssign(false);
      setAssigningId(null);
      setAssigningNumber(null);
      setSelectedOrgIds([]);
      setInboundOrgId("");
      setInboundAgentId("");
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to assign");
    } finally {
      setAssigning(false);
    }
  }

  function toggleOrgSelection(orgId: string) {
    setSelectedOrgIds((prev) => {
      const next = prev.includes(orgId)
        ? prev.filter((id) => id !== orgId)
        : [...prev, orgId];
      if (inboundOrgId === orgId && !next.includes(orgId)) {
        setInboundOrgId(next[0] || "");
      } else if (!inboundOrgId && next.length > 0) {
        setInboundOrgId(next[0]);
      }
      return next;
    });
  }

  async function doAction(
    id: string,
    action: "release" | "suspend" | "reactivate"
  ) {
    setActingId(id);
    try {
      if (action === "release") await api.phoneNumbers.release(id);
      else if (action === "suspend") await api.phoneNumbers.suspend(id);
      else await api.phoneNumbers.reactivate(id);
      toast.success(`Number ${action}d`);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : `Failed to ${action}`);
    } finally {
      setActingId(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">
            Phone Number Inventory
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Manage provider DIDs, multi-tenant organization assignments, and inbound routing.
          </p>
        </div>
        <Button size="sm" onClick={() => setShowAdd(true)}>
          <Plus className="h-4 w-4 mr-1" />
          Add Number
        </Button>
      </div>

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            ["Available", stats.available, "text-success"],
            ["Assigned", stats.assigned, "text-accent"],
            ["Suspended", stats.suspended, "text-warning"],
            ["Maintenance", stats.maintenance, "text-danger"],
          ].map(([label, value, cls]) => (
            <Card key={label as string}>
              <CardBody>
                <p className="text-xs text-text-muted uppercase tracking-wide">
                  {label as string}
                </p>
                <p className={`text-2xl font-semibold mt-1 ${cls as string}`}>
                  {((value as number) ?? 0).toLocaleString("en-IN")}
                </p>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* Table */}
      <Card>
        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner size="lg" />
          </div>
        ) : numbers.length === 0 ? (
          <EmptyState
            icon={Hash}
            title="No phone numbers in inventory"
            action={
              <Button onClick={() => setShowAdd(true)}>Add Number</Button>
            }
          />
        ) : (
          <>
            <SimpleTable
              headers={[
                "Number",
                "Provider",
                "Status",
                "Assigned Organizations",
                "Inbound Routing",
                "Actions",
              ]}
            >
              {numbers.map((n) => {
                const assignedList = n.assigned_org_ids?.length
                  ? n.assigned_org_ids
                  : n.organization_id
                  ? [n.organization_id]
                  : [];
                return (
                  <TableRow key={n.id}>
                    <TableCell className="font-mono font-medium">
                      {n.number}
                      {n.display_name && (
                        <span className="block text-[11px] font-sans text-text-muted">
                          {n.display_name}
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold uppercase ${
                          n.provider === "vobiz"
                            ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                            : n.provider === "plivo"
                            ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                            : n.provider === "twilio"
                            ? "bg-red-500/10 text-red-400 border border-red-500/20"
                            : "bg-secondary text-text-muted"
                        }`}
                      >
                        {n.provider || "mock"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={n.status} />
                    </TableCell>
                    <TableCell>
                      {assignedList.length === 0 ? (
                        <span className="text-xs text-text-muted">—</span>
                      ) : (
                        <div className="flex flex-wrap gap-1 items-center">
                          {assignedList.map((oid) => {
                            const orgName =
                              organizations.find((o) => o.id === oid)?.name ||
                              oid;
                            return (
                              <span
                                key={oid}
                                title={oid}
                                className="px-2 py-0.5 rounded text-[11px] bg-secondary/80 text-text-primary border border-border/40 font-mono"
                              >
                                {orgName}
                              </span>
                            );
                          })}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-text-muted">
                      {n.inbound_organization_id ? (
                        <div className="flex items-center gap-1.5 text-text-primary">
                          <PhoneCall className="w-3.5 h-3.5 text-accent" />
                          <span>
                            {organizations.find(
                              (o) => o.id === n.inbound_organization_id
                            )?.name || n.inbound_organization_id}
                          </span>
                        </div>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap">
                        {n.status === "available" && (
                          <Button
                            size="sm"
                            variant="ghost"
                            loading={actingId === n.id}
                            onClick={() => openAssignModal(n)}
                          >
                            Assign
                          </Button>
                        )}
                        {n.status === "assigned" && (
                          <>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => openAssignModal(n)}
                            >
                              Edit Assign
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              loading={actingId === n.id}
                              onClick={() => doAction(n.id, "release")}
                            >
                              Release
                            </Button>
                          </>
                        )}
                        {n.status !== "suspended" &&
                          n.status !== "maintenance" && (
                            <Button
                              size="sm"
                              variant="ghost"
                              loading={actingId === n.id}
                              className="text-warning hover:text-warning"
                              onClick={() => doAction(n.id, "suspend")}
                            >
                              Suspend
                            </Button>
                          )}
                        {(n.status === "suspended" ||
                          n.status === "maintenance") && (
                          <Button
                            size="sm"
                            variant="ghost"
                            loading={actingId === n.id}
                            className="text-success hover:text-success"
                            onClick={() => doAction(n.id, "reactivate")}
                          >
                            Reactivate
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </SimpleTable>
            {numbers.length === PAGE_SIZE && (
              <div className="px-4 py-3 border-t border-border">
                <Pagination
                  page={page}
                  pageSize={PAGE_SIZE}
                  total={page * PAGE_SIZE + 1}
                  onPageChange={setPage}
                />
              </div>
            )}
          </>
        )}
      </Card>

      {/* Add Number modal */}
      <Modal
        isOpen={showAdd}
        onClose={() => setShowAdd(false)}
        title="Add Phone Number"
      >
        <form onSubmit={handleAdd} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="E.164 Number"
              value={addForm.number}
              onChange={(e) =>
                setAddForm((f) => ({ ...f, number: e.target.value }))
              }
              placeholder="+91XXXXXXXXXX"
              required
            />
            <Select
              label="Telephony Provider"
              value={addForm.provider}
              onChange={(e) =>
                setAddForm((f) => ({ ...f, provider: e.target.value }))
              }
              options={[
                { value: "vobiz", label: "Vobiz.ai (Recommended)" },
                { value: "plivo", label: "Plivo" },
                { value: "twilio", label: "Twilio" },
                { value: "exotel", label: "Exotel" },
                { value: "mock", label: "Mock / Simulator" },
              ]}
              required
            />
          </div>

          {/* Plivo Specific Credentials */}
          {addForm.provider === "plivo" ? (
            <div className="p-3.5 rounded-xl border border-blue-500/20 bg-blue-500/5 space-y-3">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-400">
                <ShieldCheck className="w-4 h-4" />
                <span>Plivo Account Credentials</span>
              </div>
              <Input
                label="Plivo Auth ID"
                value={addForm.plivo_auth_id}
                onChange={(e) =>
                  setAddForm((f) => ({ ...f, plivo_auth_id: e.target.value }))
                }
                placeholder="Account Auth ID from Plivo console"
                required
              />
              <div className="relative">
                <Input
                  label="Plivo Auth Token"
                  type={showToken ? "text" : "password"}
                  value={addForm.plivo_auth_token}
                  onChange={(e) =>
                    setAddForm((f) => ({ ...f, plivo_auth_token: e.target.value }))
                  }
                  placeholder="Secret API Auth Token"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowToken(!showToken)}
                  className="absolute right-3 top-8 text-xs text-text-muted hover:text-text-primary"
                >
                  {showToken ? "Hide" : "Show"}
                </button>
              </div>
              <Input
                label="Application / Subaccount ID (Optional)"
                value={addForm.plivo_app_id}
                onChange={(e) =>
                  setAddForm((f) => ({ ...f, plivo_app_id: e.target.value }))
                }
                placeholder="Optional Plivo App SID"
              />
            </div>
          ) : addForm.provider === "vobiz" ? (
            <div className="p-3.5 rounded-xl border border-purple-500/20 bg-purple-500/5 space-y-3">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-purple-400">
                <ShieldCheck className="w-4 h-4" />
                <span>Vobiz.ai Account Credentials</span>
              </div>
              <Input
                label="Vobiz Auth ID"
                value={addForm.vobiz_auth_id}
                onChange={(e) =>
                  setAddForm((f) => ({ ...f, vobiz_auth_id: e.target.value }))
                }
                placeholder="Account Auth ID from Vobiz console"
                required
              />
              <div className="relative">
                <Input
                  label="Vobiz Auth Token"
                  type={showToken ? "text" : "password"}
                  value={addForm.vobiz_auth_token}
                  onChange={(e) =>
                    setAddForm((f) => ({ ...f, vobiz_auth_token: e.target.value }))
                  }
                  placeholder="Secret API Auth Token"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowToken(!showToken)}
                  className="absolute right-3 top-8 text-xs text-text-muted hover:text-text-primary"
                >
                  {showToken ? "Hide" : "Show"}
                </button>
              </div>
              <Input
                label="Trunk / Application ID (Optional)"
                value={addForm.vobiz_trunk_id}
                onChange={(e) =>
                  setAddForm((f) => ({ ...f, vobiz_trunk_id: e.target.value }))
                }
                placeholder="Optional SIP Trunk or App SID"
              />
            </div>
          ) : (
            <Input
              label="Provider Resource ID"
              value={addForm.provider_resource_id}
              onChange={(e) =>
                setAddForm((f) => ({
                  ...f,
                  provider_resource_id: e.target.value,
                }))
              }
              placeholder="Twilio SID or Exotel DID ID"
              required
            />
          )}

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Display Name"
              value={addForm.display_name}
              onChange={(e) =>
                setAddForm((f) => ({ ...f, display_name: e.target.value }))
              }
              placeholder="e.g. Mumbai Campaign DID"
            />
            <Input
              label="Country Code"
              value={addForm.country_code}
              onChange={(e) =>
                setAddForm((f) => ({ ...f, country_code: e.target.value }))
              }
              placeholder="IN"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Number Type"
              value={addForm.number_type}
              onChange={(e) =>
                setAddForm((f) => ({ ...f, number_type: e.target.value }))
              }
              placeholder="local / mobile / toll_free"
            />
            <Input
              label="Monthly Rental (paise)"
              type="number"
              value={addForm.rental_paise_per_month}
              onChange={(e) =>
                setAddForm((f) => ({
                  ...f,
                  rental_paise_per_month: e.target.value,
                }))
              }
              hint="100 = ₹1"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowAdd(false)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={adding}>
              Add Number
            </Button>
          </div>
        </form>
      </Modal>

      {/* Assign modal */}
      <Modal
        isOpen={showAssign}
        onClose={() => {
          setShowAssign(false);
          setAssigningId(null);
          setAssigningNumber(null);
        }}
        title={`Assign Number: ${assigningNumber?.number || ""}`}
      >
        <form onSubmit={handleAssign} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-text-primary block mb-1">
              Select Organizations (1 or more)
            </label>
            <p className="text-xs text-text-muted mb-2.5">
              All selected organizations will be able to choose this number for outbound campaigns and AI Agent Studio tests.
            </p>

            <div className="max-h-48 overflow-y-auto space-y-1.5 p-2 rounded-xl border border-border bg-secondary/30">
              {organizations.length === 0 ? (
                <p className="text-xs text-text-muted text-center py-4">
                  No organizations found.
                </p>
              ) : (
                organizations.map((org) => {
                  const isChecked = selectedOrgIds.includes(org.id);
                  return (
                    <label
                      key={org.id}
                      className={`flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer transition-colors text-xs ${
                        isChecked
                          ? "bg-primary/10 border border-primary/30 text-text-primary font-medium"
                          : "hover:bg-secondary/60 text-text-secondary"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleOrgSelection(org.id)}
                        className="rounded border-border text-primary focus:ring-0"
                      />
                      <Building2 className="w-3.5 h-3.5 text-text-muted" />
                      <span className="flex-1">{org.name}</span>
                      <span className="text-[10px] font-mono text-text-muted">
                        {org.id}
                      </span>
                    </label>
                  );
                })
              )}
            </div>
          </div>

          {/* Inbound Routing Configuration */}
          {selectedOrgIds.length > 0 && (
            <div className="p-3.5 rounded-xl border border-border bg-secondary/20 space-y-3">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-text-primary">
                <PhoneCall className="w-3.5 h-3.5 text-accent" />
                <span>Inbound Call Handling</span>
              </div>

              <Select
                label="Primary Inbound Organization"
                value={inboundOrgId}
                onChange={(e) => setInboundOrgId(e.target.value)}
                options={selectedOrgIds.map((id) => ({
                  value: id,
                  label:
                    organizations.find((o) => o.id === id)?.name || id,
                }))}
                hint="When a customer dials this number, calls will route to this organization."
              />

              {inboundOrgId && (
                <Select
                  label="Inbound AI Voice Agent"
                  value={inboundAgentId}
                  onChange={(e) => setInboundAgentId(e.target.value)}
                  options={
                    availableAgents.length > 0
                      ? availableAgents.map((a) => ({
                          value: a.id,
                          label: a.name,
                        }))
                      : [{ value: "", label: loadingAgents ? "Loading agents..." : "Organization Default Agent" }]
                  }
                  hint="The AI Agent that will converse live with incoming callers."
                />
              )}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setShowAssign(false);
                setAssigningId(null);
                setAssigningNumber(null);
              }}
            >
              Cancel
            </Button>
            <Button type="submit" loading={assigning}>
              Save Assignment
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
