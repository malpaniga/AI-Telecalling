"use client";

import React, { useEffect, useState } from "react";
import { CreditCard } from "lucide-react";
import toast from "react-hot-toast";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/input";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, Subscription } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

const PAGE_SIZE = 50;

export default function AdminSubscriptionsPage() {
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    setLoading(true);
    api.admin.subscriptions.list({
      sub_status: statusFilter || undefined,
      limit: PAGE_SIZE,
      skip: (page - 1) * PAGE_SIZE,
    })
      .then(setSubs)
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [statusFilter, page]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">Subscriptions</h2>
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          options={[
            { value: "", label: "All Statuses" },
            { value: "active", label: "Active" },
            { value: "trialing", label: "Trialing" },
            { value: "cancelled", label: "Cancelled" },
          ]}
          className="w-40"
        />
      </div>
      <Card>
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : subs.length === 0 ? (
          <EmptyState icon={CreditCard} title="No subscriptions" />
        ) : (
          <>
            <SimpleTable headers={["Org ID", "Plan", "Cycle", "Status", "Period End", "Cancel?"]}>
              {subs.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-mono text-xs text-text-muted">{s.organization_id}</TableCell>
                  <TableCell className="font-medium capitalize">{s.plan_slug?.replace(/_/g, " ")}</TableCell>
                  <TableCell className="capitalize text-text-secondary">{s.billing_cycle}</TableCell>
                  <TableCell><StatusBadge status={s.status} /></TableCell>
                  <TableCell className="text-xs text-text-muted whitespace-nowrap">{formatDateTime(s.current_period_end)}</TableCell>
                  <TableCell>{s.cancel_at_period_end ? <StatusBadge status="warning" /> : <span className="text-text-muted">—</span>}</TableCell>
                </TableRow>
              ))}
            </SimpleTable>
            {subs.length === PAGE_SIZE && (
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
