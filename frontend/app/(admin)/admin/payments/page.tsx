"use client";

import React, { useEffect, useState } from "react";
import { Receipt } from "lucide-react";
import toast from "react-hot-toast";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Pagination } from "@/components/ui/pagination";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, Payment } from "@/lib/api";
import { formatDateTime, formatINR } from "@/lib/utils";

const PAGE_SIZE = 50;

export default function AdminPaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  useEffect(() => {
    setLoading(true);
    api.admin.payments.list({ limit: PAGE_SIZE, skip: (page - 1) * PAGE_SIZE })
      .then(setPayments)
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [page]);

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-text-primary">Payments</h2>
      <Card>
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : payments.length === 0 ? (
          <EmptyState icon={Receipt} title="No payments" />
        ) : (
          <>
            <SimpleTable headers={["Amount", "Status", "Date"]}>
              {payments.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="font-medium">{formatINR(p.amount_paise)}</TableCell>
                  <TableCell><StatusBadge status={p.status} /></TableCell>
                  <TableCell className="text-xs text-text-muted">{formatDateTime(p.paid_at)}</TableCell>
                </TableRow>
              ))}
            </SimpleTable>
            {payments.length === PAGE_SIZE && (
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
