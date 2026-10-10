"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Building2 } from "lucide-react";
import toast from "react-hot-toast";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/input";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, Organization } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

const PAGE_SIZE = 50;

export default function AdminOrgsPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [acting, setActing] = useState<string | null>(null);

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
                    <Button
                      size="sm"
                      variant="ghost"
                      loading={acting === org.id}
                      onClick={() => toggleOrg(org)}
                      className={org.status === "active" ? "text-warning hover:text-warning" : "text-success hover:text-success"}
                    >
                      {org.status === "active" ? "Suspend" : "Reactivate"}
                    </Button>
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
    </div>
  );
}
