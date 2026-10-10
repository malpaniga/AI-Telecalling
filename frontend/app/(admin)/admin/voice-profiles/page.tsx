"use client";

import React, { useEffect, useState } from "react";
import { Mic2 } from "lucide-react";
import toast from "react-hot-toast";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, VoiceProfile } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

export default function AdminVoiceProfilesPage() {
  const [profiles, setProfiles] = useState<VoiceProfile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.admin.voiceProfiles.list()
      .then(setProfiles)
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-text-primary">Voice Profiles</h2>
      <Card>
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : profiles.length === 0 ? (
          <EmptyState icon={Mic2} title="No voice profiles" />
        ) : (
          <SimpleTable headers={["Name", "Language", "Type", "Version", "Status", "Created"]}>
            {profiles.map((p) => (
              <TableRow key={p.id}>
                <TableCell className="font-medium">{p.display_name}</TableCell>
                <TableCell className="text-text-secondary">{p.language}</TableCell>
                <TableCell><StatusBadge status={p.is_platform ? "active" : "default"} /></TableCell>
                <TableCell className="text-text-secondary">{p.active_version ?? "—"}</TableCell>
                <TableCell><StatusBadge status={p.is_active ? "active" : "inactive"} /></TableCell>
                <TableCell className="text-xs text-text-muted">{formatDateTime(p.created_at)}</TableCell>
              </TableRow>
            ))}
          </SimpleTable>
        )}
      </Card>
    </div>
  );
}
