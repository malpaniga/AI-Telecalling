"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import toast from "react-hot-toast";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { api, Organization } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

export default function AdminOrgDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    api.admin.organizations.get(id)
      .then(setOrg)
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;
  if (!org) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/admin/organizations">
          <Button variant="ghost" size="sm" className="gap-1">
            <ChevronLeft className="h-4 w-4" /> Back
          </Button>
        </Link>
        <h2 className="text-lg font-semibold text-text-primary">{org.name}</h2>
        <StatusBadge status={org.status} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><h3 className="text-sm font-medium text-text-primary">Organisation Details</h3></CardHeader>
          <CardBody className="space-y-3 text-sm">
            {[
              ["Name", org.name],
              ["Email", org.email],
              ["Slug", org.slug],
              ["Status", null],
              ["Verified", org.is_verified ? "Yes" : "No"],
              ["Created", formatDateTime(org.created_at)],
            ].map(([label, value]) => (
              <div key={label as string} className="flex justify-between">
                <span className="text-text-muted">{label}</span>
                {label === "Status" ? (
                  <StatusBadge status={org.status} />
                ) : (
                  <span className="font-medium text-text-primary">{value as string}</span>
                )}
              </div>
            ))}
          </CardBody>
        </Card>

        <Card>
          <CardHeader><h3 className="text-sm font-medium text-text-primary">Limits</h3></CardHeader>
          <CardBody className="space-y-3 text-sm">
            {[
              ["Max Agents", org.max_agents],
              ["Max Campaigns", org.max_campaigns],
              ["Max Concurrent Calls", org.max_concurrent_calls],
            ].map(([label, value]) => (
              <div key={label as string} className="flex justify-between">
                <span className="text-text-muted">{label}</span>
                <span className="font-medium text-text-primary">{value as number}</span>
              </div>
            ))}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
