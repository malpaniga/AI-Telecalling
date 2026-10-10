"use client";

import React, { useEffect, useState } from "react";
import { ScrollText } from "lucide-react";
import toast from "react-hot-toast";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Pagination } from "@/components/ui/pagination";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

type AuditLog = {
  id: string; action: string; organization_id: string | null; user_email: string | null;
  user_role: string | null; resource_type: string | null; resource_id: string | null;
  status: string; ip_address: string | null; created_at: string;
};

const PAGE_SIZE = 100;

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  useEffect(() => {
    setLoading(true);
    api.admin.auditLogs({ limit: PAGE_SIZE, skip: (page - 1) * PAGE_SIZE })
      .then((data) => setLogs(data as AuditLog[]))
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [page]);

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-text-primary">Audit Logs</h2>
      <Card>
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : logs.length === 0 ? (
          <EmptyState icon={ScrollText} title="No audit logs" />
        ) : (
          <>
            <SimpleTable headers={["Action", "User", "Role", "Resource", "Status", "IP", "When"]}>
              {logs.map((l) => (
                <TableRow key={l.id}>
                  <TableCell className="font-mono text-xs">{l.action}</TableCell>
                  <TableCell className="text-xs text-text-secondary">{l.user_email ?? "—"}</TableCell>
                  <TableCell className="text-xs text-text-muted capitalize">{l.user_role?.replace(/_/g, " ") ?? "—"}</TableCell>
                  <TableCell className="text-xs text-text-muted">{l.resource_type ?? "—"}</TableCell>
                  <TableCell><StatusBadge status={l.status || "success"} /></TableCell>
                  <TableCell className="font-mono text-xs text-text-muted">{l.ip_address ?? "—"}</TableCell>
                  <TableCell className="text-xs text-text-muted whitespace-nowrap">{formatDateTime(l.created_at)}</TableCell>
                </TableRow>
              ))}
            </SimpleTable>
            {logs.length === PAGE_SIZE && (
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
