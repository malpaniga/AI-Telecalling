"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, CallDetail } from "@/lib/api";
import { Topbar } from "@/components/nav";
import { Badge, Panel } from "@/components/ui";

function fmtTime(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export default function CallDetailPage() {
  const params = useParams<{ id: string }>();
  const [call, setCall] = useState<CallDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!params?.id) return;
    api.call(params.id).then(setCall).catch((e) => setErr(String(e)));
  }, [params?.id]);

  return (
    <div>
      <Topbar title="Call Detail" />
      <div className="p-6">
        <Link href="/calls" className="mb-4 inline-block text-xs text-accent hover:underline">
          ← back to calls
        </Link>

        {err ? <Panel className="p-4 text-sm text-bad">{err}</Panel> : null}

        {call ? (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Meta panel */}
            <Panel className="h-fit p-5 lg:col-span-1">
              <div className="text-[11px] uppercase tracking-wider text-muted">Call</div>
              <div className="mt-1 font-mono text-xs text-faint">{call.id}</div>
              <dl className="mt-4 space-y-3 text-sm">
                <Row label="Direction" value={<span className="capitalize">{call.direction}</span>} />
                <Row label="Status" value={<Badge value={call.status} />} />
                <Row label="Outcome" value={<Badge value={call.outcome} />} />
                <Row label="Started" value={<span className="text-muted">{fmtTime(call.started_at)}</span>} />
                <Row label="Duration" value={<span className="text-muted">{call.duration_s ?? "—"}s</span>} />
                <Row
                  label="Avg latency"
                  value={<span className="text-muted">{call.avg_latency_ms ? `${call.avg_latency_ms}ms` : "—"}</span>}
                />
              </dl>
            </Panel>

            {/* Transcript */}
            <Panel className="lg:col-span-2">
              <div className="border-b border-line px-5 py-3 text-[11px] uppercase tracking-wider text-muted">
                Transcript · {call.turns.length} turns
              </div>
              <div className="divide-y divide-line">
                {call.turns.map((t, i) => (
                  <div key={i} className="flex gap-4 px-5 py-3">
                    <div className="w-16 shrink-0">
                      <span
                        className={`text-[11px] uppercase tracking-wide ${
                          t.role === "agent" ? "text-accent" : "text-fg"
                        }`}
                      >
                        {t.role}
                      </span>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm leading-relaxed">{t.text}</p>
                      <div className="mt-1 flex gap-3 text-[11px] text-faint">
                        {t.stage ? <span>stage: {t.stage}</span> : null}
                        {t.latency_ms ? <span>{t.latency_ms}ms</span> : null}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
          </div>
        ) : !err ? (
          <div className="text-sm text-muted">Loading…</div>
        ) : null}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-muted">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
