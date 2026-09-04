"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, CallRow } from "@/lib/api";
import { Topbar } from "@/components/nav";
import { Badge, Panel, Score } from "@/components/ui";

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

const TH = "px-4 py-2.5 text-left text-[11px] uppercase tracking-wider text-muted font-medium";
const TD = "px-4 py-3 align-middle";

export default function CallsPage() {
  const [calls, setCalls] = useState<CallRow[]>([]);
  useEffect(() => {
    api.calls(100).then(setCalls).catch(() => setCalls([]));
  }, []);

  return (
    <div>
      <Topbar title="Calls" />
      <div className="p-6">
        <Panel>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line bg-panel-2">
                <th className={TH}>Started</th>
                <th className={TH}>Dir</th>
                <th className={TH}>City</th>
                <th className={TH}>Budget</th>
                <th className={TH}>Score</th>
                <th className={TH}>Outcome</th>
                <th className={TH}>Duration</th>
                <th className={TH}>Latency</th>
                <th className={TH}></th>
              </tr>
            </thead>
            <tbody>
              {calls.map((c) => (
                <tr key={c.id} className="border-b border-line last:border-0 hover:bg-panel-2">
                  <td className={`${TD} text-muted`}>{fmtTime(c.started_at)}</td>
                  <td className={`${TD} capitalize text-muted`}>{c.direction}</td>
                  <td className={TD}>{c.lead_city ?? "—"}</td>
                  <td className={`${TD} text-muted`}>{c.lead_budget ?? "—"}</td>
                  <td className={TD}>
                    <Score value={c.lead_score} />
                  </td>
                  <td className={TD}>
                    <Badge value={c.outcome} />
                  </td>
                  <td className={`${TD} tabular-nums text-muted`}>{fmtDur(c.duration_s)}</td>
                  <td className={`${TD} tabular-nums text-muted`}>
                    {c.avg_latency_ms ? `${c.avg_latency_ms}ms` : "—"}
                  </td>
                  <td className={`${TD} text-right`}>
                    <Link href={`/calls/${c.id}`} className="text-xs text-accent hover:underline">
                      open →
                    </Link>
                  </td>
                </tr>
              ))}
              {calls.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-faint" colSpan={9}>
                    No calls recorded yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </Panel>
      </div>
    </div>
  );
}
