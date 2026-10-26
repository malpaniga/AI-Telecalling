"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Wifi,
  Server,
  HardDrive,
  AlertTriangle,
  Wand2,
  Sparkles,
  Phone,
} from "lucide-react";
import toast from "react-hot-toast";
import { Card, CardBody } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { api, AIModelCatalogue } from "@/lib/api";
import { ModelConnectCard } from "@/components/model-directory/ModelConnectCard";
import { useTestAgent } from "@/contexts/test-agent-context";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type Capability = "all" | "tts" | "stt" | "llm";
type StatusFilter = "all" | "supported" | "experimental" | "unavailable";

function capabilityVariant(
  cap: string
): "accent" | "info" | "success" | "default" {
  if (cap === "llm") return "accent";
  if (cap === "tts") return "info";
  if (cap === "stt") return "success";
  return "default";
}

function hostingIcon(mode: string) {
  if (mode === "managed_api") return <Wifi className="h-3.5 w-3.5" />;
  if (mode === "local_runtime") return <HardDrive className="h-3.5 w-3.5" />;
  return <Server className="h-3.5 w-3.5" />;
}

function hostingLabel(mode: string) {
  if (mode === "managed_api") return "Managed API";
  if (mode === "local_runtime") return "Local Runtime";
  return "Self-Hosted";
}

function isStale(dateStr: string | null): boolean {
  if (!dateStr) return true;
  const verifiedDate = new Date(dateStr);
  const ninetyDaysAgo = new Date();
  ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90);
  return verifiedDate < ninetyDaysAgo;
}

function formatFreeTierInfo(
  freeTierInfo: AIModelCatalogue["free_tier_info"]
): string {
  if (!freeTierInfo) return "";
  if (typeof freeTierInfo === "string") return freeTierInfo;

  const values = Object.entries(freeTierInfo)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => {
      const label = key.replace(/_/g, " ");
      return `${label}: ${String(value)}`;
    });
  return values.join(" · ");
}

function freeTierDetails(freeTierInfo: AIModelCatalogue["free_tier_info"]) {
  if (!freeTierInfo || typeof freeTierInfo === "string") return [];
  return Object.entries(freeTierInfo).filter(
    ([key, value]) => key !== "note" && value !== null && value !== undefined && value !== ""
  );
}

// ---------------------------------------------------------------------------
// ModelCard component
// ---------------------------------------------------------------------------

function ModelCard({
  model,
  onConnect,
}: {
  model: AIModelCatalogue;
  onConnect: (model: AIModelCatalogue) => void;
}) {
  const langs = model.supported_languages ?? [];
  const displayLangs =
    langs.length > 5
      ? langs.slice(0, 5).join(", ") + ` +${langs.length - 5} more`
      : langs.join(", ") || "—";

  const freeTierStale =
    model.free_tier_info != null && isStale(model.free_tier_verified_date);
  const freeTierInfo = formatFreeTierInfo(model.free_tier_info);
  const freeTierDetailsList = freeTierDetails(model.free_tier_info);
  const freeTierNote =
    typeof model.free_tier_info === "object" && model.free_tier_info && typeof model.free_tier_info.note === "string"
      ? model.free_tier_info.note
      : null;

  const statusVariant =
    model.implementation_status === "supported"
      ? ("success" as const)
      : model.implementation_status === "experimental"
        ? ("warning" as const)
        : ("danger" as const);

  const canConnect =
    model.implementation_status === "supported" ||
    model.implementation_status === "experimental";

  const connectLabel =
    model.implementation_status === "supported"
      ? model.hosting_mode === "local_runtime"
        ? "Configure Local"
        : "Connect"
      : model.implementation_status === "experimental"
        ? "Experimental"
        : "Unavailable";

  return (
    <Card className="flex flex-col gap-0">
      <CardBody className="flex flex-col gap-3">
        {/* Title row */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-text-primary truncate">
              {model.provider_name}
            </p>
            <p className="text-xs text-text-secondary font-mono truncate">
              {model.model_id}
            </p>
          </div>
          <div className="shrink-0 flex flex-col items-end gap-1">
            <Badge variant={capabilityVariant(model.capability)}>
              {model.capability.toUpperCase()}
            </Badge>
            <Badge variant={statusVariant}>
              {model.implementation_status}
            </Badge>
          </div>
        </div>

        {/* Hosting mode */}
        <div className="flex items-center gap-1.5 text-xs text-text-secondary">
          {hostingIcon(model.hosting_mode)}
          <span>{hostingLabel(model.hosting_mode)}</span>
          {model.streaming_supported && (
            <span className="ml-2 text-success text-xs">⚡ Streaming</span>
          )}
        </div>

        {/* Languages */}
        <div className="text-xs text-text-secondary">
          <span className="font-medium text-text-primary">Languages: </span>
          {displayLangs}
        </div>

        {/* Free tier / pricing */}
        {freeTierInfo && (
          <div className="rounded-md border border-border bg-surface-subtle p-3 text-xs">
            <p className="font-medium text-text-primary">Free-tier limits</p>
            {freeTierDetailsList.length > 0 && (
              <dl className="mt-2 grid grid-cols-2 gap-2">
                {freeTierDetailsList.map(([key, value]) => (
                  <div key={key} className="rounded bg-surface px-2 py-1.5">
                    <dt className="capitalize text-text-muted">{key.replace(/_/g, " ")}</dt>
                    <dd className="mt-0.5 font-medium text-text-primary">{String(value)}</dd>
                  </div>
                ))}
              </dl>
            )}
            {freeTierNote && <p className="mt-2 leading-5 text-text-secondary">{String(freeTierNote)}</p>}
            {freeTierStale && (
              <p className="mt-2 flex items-start gap-1.5 rounded bg-[#FEF6E7] px-2 py-1.5 leading-5 text-warning">
                <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                Limits were last verified {model.free_tier_verified_date ?? "on an unknown date"}. Confirm them with the provider before relying on them.
              </p>
            )}
          </div>
        )}

        {/* Commercial use */}
        <div className="flex items-center gap-1.5 text-xs">
          {model.commercial_use_allowed === true ? (
            <>
              <CheckCircle2 className="h-3.5 w-3.5 text-success" />
              <span className="text-text-secondary">Commercial use allowed</span>
            </>
          ) : model.commercial_use_allowed === false ? (
            <>
              <XCircle className="h-3.5 w-3.5 text-danger" />
              <span className="text-text-secondary">
                Non-commercial only
              </span>
            </>
          ) : (
            <span className="text-text-muted">License: {model.license_spdx ?? "—"}</span>
          )}
        </div>

        {/* Doc links */}
        {(model.doc_url || model.model_card_url) && (
          <div className="flex items-center gap-3 text-xs">
            {model.doc_url && (
              <a
                href={model.doc_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-accent hover:underline"
              >
                <ExternalLink className="h-3 w-3" />
                Docs
              </a>
            )}
            {model.model_card_url && (
              <a
                href={model.model_card_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-accent hover:underline"
              >
                <ExternalLink className="h-3 w-3" />
                Model Card
              </a>
            )}
          </div>
        )}

        {/* Action button */}
        <div className="mt-auto pt-1">
          <Button
            size="sm"
            variant={
              model.implementation_status === "supported"
                ? "primary"
                : "secondary"
            }
            disabled={!canConnect}
            className="w-full"
            onClick={() => canConnect && onConnect(model)}
            title={
              model.implementation_status === "experimental"
                ? "This integration is experimental and may not be stable."
                : undefined
            }
          >
            {connectLabel}
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AdminModelsPage() {
  const router = useRouter();
  const { openTestAgent } = useTestAgent();
  const [models, setModels] = useState<AIModelCatalogue[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [capabilityFilter, setCapabilityFilter] = useState<Capability>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  // Debounce timer ref
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(
    async (searchVal: string, cap: Capability, status: StatusFilter) => {
      setLoading(true);
      try {
        const params: Record<string, string> = {};
        if (cap !== "all") params.capability = cap;
        if (status !== "all") params.status = status;
        if (searchVal.trim()) params.search = searchVal.trim();
        const data = await api.modelDirectory.catalogue(params);
        setModels(data ?? []);
      } catch (e: unknown) {
        toast.error(
          e instanceof Error ? e.message : "Failed to load model catalogue"
        );
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Initial load
  useEffect(() => {
    load(search, capabilityFilter, statusFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Debounced search
  const handleSearchChange = (val: string) => {
    setSearch(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      load(val, capabilityFilter, statusFilter);
    }, 300);
  };

  const handleCapabilityChange = (cap: Capability) => {
    setCapabilityFilter(cap);
    load(search, cap, statusFilter);
  };

  const handleStatusChange = (status: StatusFilter) => {
    setStatusFilter(status);
    load(search, capabilityFilter, status);
  };

  const handleConnect = (model: AIModelCatalogue) => {
    const params = new URLSearchParams({
      model: model.model_id,
      provider: model.provider_name,
    });
    router.push(`/admin/providers/${model.capability}?${params.toString()}`);
  };

  const CAPABILITY_TABS: { value: Capability; label: string }[] = [
    { value: "all", label: "All" },
    { value: "llm", label: "LLM" },
    { value: "tts", label: "TTS" },
    { value: "stt", label: "STT" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">
            AI Models Directory
          </h2>
          <p className="text-sm text-text-secondary mt-0.5">
            Browse and connect AI providers for TTS, STT, and LLM capabilities.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            size="sm"
            onClick={() => openTestAgent()}
            className="gap-1.5 bg-black hover:bg-neutral-800 text-white dark:bg-white dark:text-black shadow-sm"
          >
            <Phone className="h-3.5 w-3.5 fill-current" />
            Test Agent
          </Button>
          <Button
            variant="primary"
            onClick={() => router.push("/admin/wizard")}
            className="gap-2 bg-[#E07038] hover:bg-[#C85D26] text-white shadow-sm"
          >
            <Wand2 className="h-4 w-4" />
            Launch Setup Wizard
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted pointer-events-none" />
          <input
            type="text"
            placeholder="Search models..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="w-full h-9 rounded-md border border-border bg-surface pl-9 pr-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>

        {/* Capability tabs */}
        <div className="flex items-center gap-1 rounded-md border border-border bg-surface-subtle p-1">
          {CAPABILITY_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => handleCapabilityChange(tab.value)}
              className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                capabilityFilter === tab.value
                  ? "bg-surface shadow-sm text-text-primary"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={(e) =>
            handleStatusChange(e.target.value as StatusFilter)
          }
          className="h-9 rounded-md border border-border bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
        >
          <option value="all">All Status</option>
          <option value="supported">Supported</option>
          <option value="experimental">Experimental</option>
          <option value="unavailable">Unavailable</option>
        </select>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-20">
          <Spinner size="lg" />
        </div>
      ) : models.length === 0 ? (
        <EmptyState
          title="No models found"
          description="Try adjusting your search or filters."
        />
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {models.map((model) => (
            <ModelConnectCard
              key={model.id}
              model={model}
              onConnect={handleConnect}
            />
          ))}
        </div>
      )}
    </div>
  );
}
