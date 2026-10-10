"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Hash, Plus } from "lucide-react";
import toast from "react-hot-toast";
import { Card, CardBody } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Pagination } from "@/components/ui/pagination";
import { Modal } from "@/components/ui/modal";
import { Input } from "@/components/ui/input";
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

export default function AdminPhoneNumbersPage() {
  const [numbers, setNumbers] = useState<PhoneNumber[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [stats, setStats] = useState<Stats | null>(null);

  // Add number
  const [showAdd, setShowAdd] = useState(false);
  const [adding, setAdding] = useState(false);
  const [addForm, setAddForm] = useState({
    number: "",
    provider: "",
    provider_resource_id: "",
    display_name: "",
    country_code: "IN",
    number_type: "local",
    rental_paise_per_month: "",
  });

  // Assign number
  const [showAssign, setShowAssign] = useState(false);
  const [assignOrgId, setAssignOrgId] = useState("");
  const [assigningId, setAssigningId] = useState<string | null>(null);
  const [assigning, setAssigning] = useState(false);

  // Action in-progress
  const [actingId, setActingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nums, st] = await Promise.all([
        api.admin.phoneNumbers.list({
          limit: PAGE_SIZE,
          skip: (page - 1) * PAGE_SIZE,
        }),
        api.admin.phoneNumbers.stats(),
      ]);
      setNumbers(nums);
      setStats(st as Stats);
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

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setAdding(true);
    try {
      // POST /api/v1/phone-numbers/admin
      await api.phoneNumbers.addAdmin({
        number: addForm.number,
        provider: addForm.provider,
        provider_resource_id: addForm.provider_resource_id,
        display_name: addForm.display_name || undefined,
        country_code: addForm.country_code,
        number_type: addForm.number_type,
        rental_paise_per_month: addForm.rental_paise_per_month
          ? parseInt(addForm.rental_paise_per_month)
          : undefined,
      });
      toast.success("Phone number added");
      setShowAdd(false);
      setAddForm({
        number: "",
        provider: "",
        provider_resource_id: "",
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

  async function handleAssign(e: React.FormEvent) {
    e.preventDefault();
    if (!assigningId) return;
    setAssigning(true);
    try {
      await api.phoneNumbers.assign(assigningId, assignOrgId);
      toast.success("Number assigned");
      setShowAssign(false);
      setAssignOrgId("");
      setAssigningId(null);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to assign");
    } finally {
      setAssigning(false);
    }
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
        <h2 className="text-lg font-semibold text-text-primary">
          Phone Number Inventory
        </h2>
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
                  {(value as number).toLocaleString("en-IN")}
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
                "Status",
                "Assigned To",
                "Assigned On",
                "Actions",
              ]}
            >
              {numbers.map((n) => (
                <TableRow key={n.id}>
                  <TableCell className="font-mono font-medium">
                    {n.number}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={n.status} />
                  </TableCell>
                  <TableCell className="font-mono text-xs text-text-muted">
                    {n.organization_id ?? "—"}
                  </TableCell>
                  <TableCell className="text-xs text-text-muted">
                    {formatDateTime(n.assigned_at)}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1 flex-wrap">
                      {n.status === "available" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          loading={actingId === n.id}
                          onClick={() => {
                            setAssigningId(n.id);
                            setShowAssign(true);
                          }}
                        >
                          Assign
                        </Button>
                      )}
                      {n.status === "assigned" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          loading={actingId === n.id}
                          onClick={() => doAction(n.id, "release")}
                        >
                          Release
                        </Button>
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
              ))}
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
            <Input
              label="Provider"
              value={addForm.provider}
              onChange={(e) =>
                setAddForm((f) => ({ ...f, provider: e.target.value }))
              }
              placeholder="exotel"
              required
            />
          </div>
          <Input
            label="Provider Resource ID"
            value={addForm.provider_resource_id}
            onChange={(e) =>
              setAddForm((f) => ({
                ...f,
                provider_resource_id: e.target.value,
              }))
            }
            required
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Display Name"
              value={addForm.display_name}
              onChange={(e) =>
                setAddForm((f) => ({ ...f, display_name: e.target.value }))
              }
              placeholder="Optional"
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
              placeholder="local / mobile"
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
        }}
        title="Assign Number"
      >
        <form onSubmit={handleAssign} className="space-y-4">
          <p className="text-sm text-text-secondary">
            Enter the Organisation ID to assign this number to. The number
            will be moved to the &apos;assigned&apos; state.
          </p>
          <Input
            label="Organisation ID"
            value={assignOrgId}
            onChange={(e) => setAssignOrgId(e.target.value)}
            placeholder="org_..."
            required
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setShowAssign(false);
                setAssigningId(null);
              }}
            >
              Cancel
            </Button>
            <Button type="submit" loading={assigning}>
              Assign
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
