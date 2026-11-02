"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Phone, Search, Volume2, Download } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/input";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, Call } from "@/lib/api";
import { formatDateTime, formatDuration } from "@/lib/utils";
import toast from "react-hot-toast";

const PAGE_SIZE = 50;
const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "initiating", label: "Initiating" },
  { value: "ringing", label: "Ringing" },
  { value: "talking", label: "Talking" },
  { value: "completed", label: "Completed" },
  { value: "no_answer", label: "Not Answered" },
  { value: "busy", label: "Busy" },
  { value: "failed", label: "Failed" },
];

export default function CallsPage() {
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [total, setTotal] = useState(0);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const data = await api.calls.list({
        call_status: statusFilter || undefined,
        limit: PAGE_SIZE,
        skip: (page - 1) * PAGE_SIZE,
      });
      setCalls(data);
      // calls endpoint returns array; estimate total from returned count
      if (data.length === PAGE_SIZE) setTotal((page - 1) * PAGE_SIZE + PAGE_SIZE + 1);
      else setTotal((page - 1) * PAGE_SIZE + data.length);
    } catch (e: unknown) {
      if (!silent) {
        toast.error(e instanceof Error ? e.message : "Failed to load calls");
      }
    } finally {
      if (!silent) setLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => { setPage(1); }, [statusFilter]);
  useEffect(() => { load(); }, [load]);

  // Live auto-refresh when any call is active in the list
  useEffect(() => {
    const hasActiveCall = calls.some((c) =>
      ["initiating", "ringing", "talking", "connected"].includes(c.status?.toLowerCase() || "")
    );
    if (!hasActiveCall) return;

    const interval = setInterval(() => {
      load(true);
    }, 2500);

    return () => clearInterval(interval);
  }, [calls, load]);

  return (
    <AppShell title="Calls">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Call History</h2>
          <p className="text-xs text-text-muted mt-0.5">Review full-duplex conversations, recordings, and duration metrics</p>
        </div>
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          options={STATUS_OPTIONS}
          className="w-40"
        />
      </div>

      <Card>
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : calls.length === 0 ? (
          <EmptyState
            icon={Phone}
            title="No calls yet"
            description={statusFilter ? "No calls with this status" : "Calls will appear here once campaigns run"}
          />
        ) : (
          <>
            <SimpleTable headers={["To", "From", "Status", "Outcome", "Duration", "Recording", "Score", "Credits", "Date", ""]}>
              {calls.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="font-mono text-xs">{c.to_number}</TableCell>
                  <TableCell className="font-mono text-xs text-text-muted">{c.from_number}</TableCell>
                  <TableCell><StatusBadge status={c.status} /></TableCell>
                  <TableCell>
                    {c.outcome ? <StatusBadge status={c.outcome} /> : <span className="text-text-muted">—</span>}
                  </TableCell>
                  <TableCell className="text-text-secondary font-mono text-xs whitespace-nowrap">
                    {formatDuration(c.duration_s)}
                  </TableCell>
                  <TableCell>
                    {c.recording_url ? (
                      <div className="flex items-center gap-1.5">
                        <Link
                          href={`/calls/${c.id}`}
                          title="Listen to recording"
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
                        >
                          <Volume2 className="h-3 w-3" />
                          <span>Play</span>
                        </Link>
                        <a
                          href={api.calls.getRecordingUrl(c.id, true)}
                          download={`call_${c.id}.wav`}
                          title="Download recording (.wav)"
                          className="p-1 rounded text-text-muted hover:text-accent hover:bg-surface-subtle transition-colors"
                        >
                          <Download className="h-3.5 w-3.5" />
                        </a>
                      </div>
                    ) : (
                      <span className="text-text-muted text-xs">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-text-secondary">{c.score || "—"}</TableCell>
                  <TableCell className="text-xs text-text-muted">{c.credits_consumed}</TableCell>
                  <TableCell className="text-xs text-text-muted whitespace-nowrap">{formatDateTime(c.started_at)}</TableCell>
                  <TableCell>
                    <Link href={`/calls/${c.id}`} className="text-xs text-accent hover:underline">
                      Details →
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </SimpleTable>
            {total > PAGE_SIZE && (
              <div className="px-4 py-3 border-t border-border">
                <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
              </div>
            )}
          </>
        )}
      </Card>
    </AppShell>
  );
}
