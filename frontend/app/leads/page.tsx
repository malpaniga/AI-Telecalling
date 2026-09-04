"use client";

import { useEffect, useState } from "react";
import { api, Lead } from "@/lib/api";
import { Topbar } from "@/components/nav";
import { Badge, Panel, Score } from "@/components/ui";

const TH = "px-4 py-2.5 text-left text-[11px] uppercase tracking-wider text-muted font-medium";
const TD = "px-4 py-3 align-middle";

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  useEffect(() => {
    api.leads(200).then(setLeads).catch(() => setLeads([]));
  }, []);

  return (
    <div>
      <Topbar title="Leads" />
      <div className="p-6">
        <Panel>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line bg-panel-2">
                <th className={TH}>City</th>
                <th className={TH}>Budget</th>
                <th className={TH}>Timeline</th>
                <th className={TH}>Property</th>
                <th className={TH}>Score</th>
                <th className={TH}>Status</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((l) => (
                <tr key={l.id} className="border-b border-line last:border-0 hover:bg-panel-2">
                  <td className={TD}>{l.city ?? "—"}</td>
                  <td className={`${TD} text-muted`}>{l.budget ?? "—"}</td>
                  <td className={`${TD} text-muted`}>{l.timeline ?? "—"}</td>
                  <td className={`${TD} text-muted`}>{l.property_type ?? "—"}</td>
                  <td className={TD}>
                    <Score value={l.score} />
                  </td>
                  <td className={TD}>
                    <Badge value={l.status} />
                  </td>
                </tr>
              ))}
              {leads.length === 0 ? (
                <tr>
                  <td className="px-4 py-8 text-center text-faint" colSpan={6}>
                    No leads yet.
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
