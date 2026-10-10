"use client";

import React, { useEffect, useState } from "react";
import { Hash } from "lucide-react";
import toast from "react-hot-toast";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Pagination } from "@/components/ui/pagination";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, PhoneNumber } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

const PAGE_SIZE = 100;

export default function AdminPhoneNumbersPage() {
  const [numbers, setNumbers] = useState<PhoneNumber[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  useEffect(() => {
    setLoading(true);
    api.admin.phoneNumbers.list({ limit: PAGE_SIZE, skip: (page - 1) * PAGE_SIZE })
      .then(setNumbers)
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [page]);

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-text-primary">Phone Number Inventory</h2>
      <Card>
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : numbers.length === 0 ? (
          <EmptyState icon={Hash} title="No phone numbers in inventory" />
        ) : (
          <>
            <SimpleTable headers={["Number", "Status", "Assigned To", "Assigned On"]}>
              {numbers.map((n) => (
                <TableRow key={n.id}>
                  <TableCell className="font-mono font-medium">{n.number}</TableCell>
                  <TableCell><StatusBadge status={n.status} /></TableCell>
                  <TableCell className="font-mono text-xs text-text-muted">{n.organization_id ?? "—"}</TableCell>
                  <TableCell className="text-xs text-text-muted">{formatDateTime(n.assigned_at)}</TableCell>
                </TableRow>
              ))}
            </SimpleTable>
            {numbers.length === PAGE_SIZE && (
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
