"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, CallRow, Stats } from "@/lib/api";
import { Topbar } from "@/components/nav";
import { Badge, Metric, Panel, Score } from "@/components/ui";

function fmtTime(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
function fmtDur(s: number | null) {
  if (s == null) return "—";
  const m = Math.floor(s / 60);
  return m ? `${m}m ${s % 60}s` : `${s}s`;
}

export default function Overview() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [calls, setCalls] = useState<CallRow[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.stats(), api.calls(8)])
      .then(([s, c]) => {
        setStats(s);
        setCalls(c);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  return (
    <div>
      <Topbar title="Overview" />
      <div className="p-6">
        {err ? (
          <Panel className="p-4 text-sm text-bad">
            Could not reach the API ({err}). Is the backend running on :8000?
          </Panel>
        ) : null}

        {/* Metric grid */}
        <div className="grid grid-cols-2 gap-px bg-line md:grid-cols-4">
          <Metric label="Total Calls" value={stats ? `${stats.total_calls}` : "—"} />
          <Metric label="Leads" value={stats ? `${stats.total_leads}` : "—"} />
          <Metric
            label="Booked"
            value={stats ? `${stats.booked}` : "—"}
            accent
            sub={stats ? `${stats.qualified} qualified` : undefined}
          />
          <Metric
            label="Avg Latency"
            value={stats?.avg_latency_ms ? `${stats.avg_latency_ms}ms` : "—"}
            sub={stats ? `avg score ${stats.avg_score}` : undefined}
          />
        </div>

        {/* Outcome breakdown */}
        {stats ? (
          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Panel className="p-5 lg:col-span-1">
              <div className="text-[11px] uppercase tracking-wider text-muted">
                Call Outcomes
              </div>
              <div className="mt-4 space-y-3">
                {Object.entries(stats.outcomes).map(([k, v]) => {
                  const pct = stats.total_calls
                    ? Math.round((v / stats.total_calls) * 100)
                    : 0;
                  return (
                    <div key={k}>
                      <div className="mb-1 flex justify-between text-xs">
                        <span className="capitalize text-muted">
                          {k.replace(/_/g, " ")}
                        </span>
                        <span className="tabular-nums text-fg">{v}</span>
                      </div>
                      <div className="h-1.5 w-full bg-panel-2 border border-line">
                        <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Panel>

            {/* Recent calls */}
            <Panel className="lg:col-span-2">
              <div className="flex items-center justify-between border-b border-line px-5 py-3">
                <span className="text-[11px] uppercase tracking-wider text-muted">
                  Recent Calls
                </span>
                <Link href="/calls" className="text-xs text-accent hover:underline">
                  View all →
                </Link>
              </div>
              <table className="w-full text-sm">
                <tbody>
                  {calls.map((c) => (
                    <tr
                      key={c.id}
                      className="border-b border-line last:border-0 hover:bg-panel-2"
                    >
                      <td className="px-5 py-3 text-muted">{fmtTime(c.started_at)}</td>
                      <td className="px-2 py-3">{c.lead_city ?? "—"}</td>
                      <td className="px-2 py-3">
                        <Score value={c.lead_score} />
                      </td>
                      <td className="px-2 py-3">
                        <Badge value={c.outcome} />
                      </td>
                      <td className="px-5 py-3 text-right">
                        <Link
                          href={`/calls/${c.id}`}
                          className="text-xs text-accent hover:underline"
                        >
                          open
                        </Link>
                      </td>
                    </tr>
                  ))}
                  {calls.length === 0 ? (
                    <tr>
                      <td className="px-5 py-6 text-center text-faint" colSpan={5}>
                        No calls yet.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </Panel>
          </div>
        ) : null}
      </div>
    </div>
  );
}
