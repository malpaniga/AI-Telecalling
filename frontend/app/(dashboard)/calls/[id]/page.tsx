"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { api, Call } from "@/lib/api";
import { formatDateTime, formatDuration } from "@/lib/utils";
import toast from "react-hot-toast";

export default function CallDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [call, setCall] = useState<Call | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    api.calls.get(id)
      .then(setCall)
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load call"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <AppShell title="Call Detail">
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      </AppShell>
    );
  }

  if (!call) return null;

  return (
    <AppShell
      title="Call Detail"
      breadcrumb={[{ label: "Calls", href: "/calls" }, { label: call.to_number }]}
    >
      <div className="mb-4">
        <Link href="/calls">
          <Button variant="ghost" size="sm" className="gap-1 text-text-secondary">
            <ChevronLeft className="h-4 w-4" /> Back to Calls
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Meta */}
        <Card>
          <CardHeader><h3 className="text-sm font-medium text-text-primary">Call Details</h3></CardHeader>
          <CardBody className="space-y-3 text-sm">
            <Row label="To" value={call.to_number} mono />
            <Row label="From" value={call.from_number} mono />
            <Row label="Direction" value={call.direction} />
            <Row label="Status"><StatusBadge status={call.status} /></Row>
            <Row label="Outcome">
              {call.outcome ? <StatusBadge status={call.outcome} /> : <span className="text-text-muted">—</span>}
            </Row>
            <Row label="Duration" value={formatDuration(call.duration_s)} />
            <Row label="Score" value={call.score > 0 ? String(call.score) : "—"} />
            <Row label="Credits" value={String(call.credits_consumed)} />
            <Row label="Latency" value={call.avg_latency_ms ? `${call.avg_latency_ms}ms` : "—"} />
            <Row label="Started" value={formatDateTime(call.started_at)} />
            {call.connected_at && <Row label="Connected" value={formatDateTime(call.connected_at)} />}
            {call.ended_at && <Row label="Ended" value={formatDateTime(call.ended_at)} />}
          </CardBody>
        </Card>

        {/* Summary + Qualification */}
        <Card className="lg:col-span-2">
          <CardHeader><h3 className="text-sm font-medium text-text-primary">Summary</h3></CardHeader>
          <CardBody>
            {call.summary ? (
              <p className="text-sm text-text-secondary whitespace-pre-wrap leading-relaxed">{call.summary}</p>
            ) : (
              <p className="text-sm text-text-muted">No summary available</p>
            )}

            {call.qualification && Object.keys(call.qualification).length > 0 && (
              <div className="mt-4 pt-4 border-t border-border">
                <p className="text-xs font-medium text-text-muted uppercase tracking-wide mb-3">Qualification</p>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(call.qualification).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-text-secondary capitalize">{k.replace(/_/g, " ")}</span>
                      <span className="font-medium text-text-primary">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </AppShell>
  );
}

function Row({ label, value, mono, children }: { label: string; value?: string; mono?: boolean; children?: React.ReactNode }) {
  return (
    <div className="flex justify-between items-start gap-2">
      <span className="text-text-muted shrink-0">{label}</span>
      <span className={`text-right font-medium text-text-primary ${mono ? "font-mono text-xs" : ""}`}>
        {children ?? value}
      </span>
    </div>
  );
}
