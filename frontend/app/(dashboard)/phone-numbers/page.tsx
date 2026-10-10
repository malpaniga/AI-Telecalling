"use client";

import React, { useEffect, useState } from "react";
import { Hash, Phone } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, PhoneNumber } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import toast from "react-hot-toast";

export default function PhoneNumbersPage() {
  const [numbers, setNumbers] = useState<PhoneNumber[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.phoneNumbers.myNumbers()
      .then(setNumbers)
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell title="Phone Numbers">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-text-primary">Your Phone Numbers</h2>
        <p className="text-sm text-text-secondary">Numbers assigned to your organization for outbound calling</p>
      </div>

      <Card>
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : numbers.length === 0 ? (
          <EmptyState
            icon={Hash}
            title="No numbers assigned"
            description="Contact support to request phone numbers"
          />
        ) : (
          <SimpleTable headers={["Number", "Status", "Assigned On"]}>
            {numbers.map((n) => (
              <TableRow key={n.id}>
                <TableCell className="font-mono font-medium text-text-primary">
                  <div className="flex items-center gap-2">
                    <Phone className="h-4 w-4 text-text-muted" />
                    {n.number}
                  </div>
                </TableCell>
                <TableCell><StatusBadge status={n.status} /></TableCell>
                <TableCell className="text-xs text-text-muted">{formatDateTime(n.assigned_at)}</TableCell>
              </TableRow>
            ))}
          </SimpleTable>
        )}
      </Card>
    </AppShell>
  );
}
