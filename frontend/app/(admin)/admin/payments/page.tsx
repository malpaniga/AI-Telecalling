"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Receipt } from "lucide-react";
import toast from "react-hot-toast";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Pagination } from "@/components/ui/pagination";
import { Input } from "@/components/ui/input";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, Payment, Invoice } from "@/lib/api";
import { formatDateTime, formatINR } from "@/lib/utils";

type Tab = "payments" | "invoices";
const PAGE_SIZE = 50;

export default function AdminPaymentsPage() {
  const [tab, setTab] = useState<Tab>("payments");
  const [orgFilter, setOrgFilter] = useState("");
  const [debouncedOrg, setDebouncedOrg] = useState("");

  // Debounce org filter input
  useEffect(() => {
    const t = setTimeout(() => setDebouncedOrg(orgFilter.trim()), 400);
    return () => clearTimeout(t);
  }, [orgFilter]);

  // ── Payments ──────────────────────────────────────────────────────────
  const [payments, setPayments] = useState<Payment[]>([]);
  const [paymentsLoading, setPaymentsLoading] = useState(true);
  const [paymentsPage, setPaymentsPage] = useState(1);

  const loadPayments = useCallback(async () => {
    setPaymentsLoading(true);
    try {
      const data = await api.admin.payments.list({
        org_id: debouncedOrg || undefined,
        limit: PAGE_SIZE,
        skip: (paymentsPage - 1) * PAGE_SIZE,
      });
      setPayments(data);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load payments");
    } finally {
      setPaymentsLoading(false);
    }
  }, [debouncedOrg, paymentsPage]);

  useEffect(() => { setPaymentsPage(1); }, [debouncedOrg]);
  useEffect(() => { if (tab === "payments") loadPayments(); }, [tab, loadPayments]);

  // ── Invoices ──────────────────────────────────────────────────────────
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [invoicesLoading, setInvoicesLoading] = useState(false);
  const [invoicesPage, setInvoicesPage] = useState(1);

  const loadInvoices = useCallback(async () => {
    setInvoicesLoading(true);
    try {
      const data = await api.admin.invoices.list({
        org_id: debouncedOrg || undefined,
        limit: PAGE_SIZE,
        skip: (invoicesPage - 1) * PAGE_SIZE,
      });
      setInvoices(data);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load invoices");
    } finally {
      setInvoicesLoading(false);
    }
  }, [debouncedOrg, invoicesPage]);

  useEffect(() => { setInvoicesPage(1); }, [debouncedOrg]);
  useEffect(() => { if (tab === "invoices") loadInvoices(); }, [tab, loadInvoices]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-lg font-semibold text-text-primary">
          Payments &amp; Invoices
        </h2>
        <Input
          value={orgFilter}
          onChange={(e) => setOrgFilter(e.target.value)}
          placeholder="Filter by Organisation ID"
          className="w-64"
        />
      </div>

      <div className="flex gap-1 border-b border-border">
        {(["payments", "invoices"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px capitalize ${
              tab === t
                ? "border-accent text-accent"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Payments */}
      {tab === "payments" && (
        <Card>
          {paymentsLoading ? (
            <div className="flex justify-center py-16">
              <Spinner size="lg" />
            </div>
          ) : payments.length === 0 ? (
            <EmptyState icon={Receipt} title="No payments" />
          ) : (
            <>
              <SimpleTable
                headers={[
                  "Amount",
                  "Status",
                  "Provider",
                  "Organisation",
                  "Paid At",
                ]}
              >
                {payments.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="font-medium">
                      {formatINR(p.amount_paise)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={p.status} />
                    </TableCell>
                    <TableCell className="text-text-secondary capitalize">
                      {p.provider ?? "—"}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-text-muted">
                      {p.order_id ?? "—"}
                    </TableCell>
                    <TableCell className="text-xs text-text-muted whitespace-nowrap">
                      {formatDateTime(p.paid_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </SimpleTable>
              {payments.length === PAGE_SIZE && (
                <div className="px-4 py-3 border-t border-border">
                  <Pagination
                    page={paymentsPage}
                    pageSize={PAGE_SIZE}
                    total={paymentsPage * PAGE_SIZE + 1}
                    onPageChange={setPaymentsPage}
                  />
                </div>
              )}
            </>
          )}
        </Card>
      )}

      {/* Invoices */}
      {tab === "invoices" && (
        <Card>
          {invoicesLoading ? (
            <div className="flex justify-center py-16">
              <Spinner size="lg" />
            </div>
          ) : invoices.length === 0 ? (
            <EmptyState icon={Receipt} title="No invoices" />
          ) : (
            <>
              <SimpleTable
                headers={[
                  "Invoice No.",
                  "Organisation",
                  "Total",
                  "Status",
                  "Issued At",
                ]}
              >
                {invoices.map((inv) => (
                  <TableRow key={inv.id}>
                    <TableCell className="font-mono text-sm font-medium">
                      {inv.invoice_number}
                    </TableCell>
                    <TableCell className="text-text-secondary">
                      {inv.org_name ?? "—"}
                    </TableCell>
                    <TableCell className="font-medium">
                      {formatINR(inv.total_paise)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={inv.status} />
                    </TableCell>
                    <TableCell className="text-xs text-text-muted whitespace-nowrap">
                      {formatDateTime(inv.issued_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </SimpleTable>
              {invoices.length === PAGE_SIZE && (
                <div className="px-4 py-3 border-t border-border">
                  <Pagination
                    page={invoicesPage}
                    pageSize={PAGE_SIZE}
                    total={invoicesPage * PAGE_SIZE + 1}
                    onPageChange={setInvoicesPage}
                  />
                </div>
              )}
            </>
          )}
        </Card>
      )}
    </div>
  );
}
