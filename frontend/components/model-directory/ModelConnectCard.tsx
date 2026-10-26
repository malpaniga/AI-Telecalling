"use client";

import React from "react";
import {
  Radio,
  HardDrive,
  Server,
  CheckCircle2,
  XCircle,
  ExternalLink,
  AlertTriangle,
  Zap,
  Check,
} from "lucide-react";
import { Card, CardBody } from "@/components/ui/card";
import { Badge, BadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AIModelCatalogue, ProviderConfiguration } from "@/lib/api";

export interface ModelConnectCardProps {
  model: AIModelCatalogue;
  activeConfig?: ProviderConfiguration | null;
  hasConfig?: boolean;
  onConnect: (model: AIModelCatalogue) => void;
  onTest?: (model: AIModelCatalogue, config: ProviderConfiguration) => void;
  onActivate?: (configId: string) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isStale(dateStr: string | null | undefined): boolean {
  if (!dateStr) return true;
  const verified = new Date(dateStr);
  const now = new Date();
  const diffDays = (now.getTime() - verified.getTime()) / (1000 * 60 * 60 * 24);
  return diffDays > 90;
}

function capabilityVariant(cap: string): BadgeVariant {
  switch (cap) {
    case "llm":
      return "info";
    case "tts":
      return "accent";
    case "stt":
      return "success";
    default:
      return "default";
  }
}

function hostingIcon(mode: string) {
  switch (mode) {
    case "managed_api":
      return <Radio className="h-3.5 w-3.5 text-text-secondary" />;
    case "local_runtime":
      return <HardDrive className="h-3.5 w-3.5 text-text-secondary" />;
    case "self_hosted":
      return <Server className="h-3.5 w-3.5 text-text-secondary" />;
    default:
      return null;
  }
}

function hostingLabel(mode: string): string {
  switch (mode) {
    case "managed_api":
      return "Managed API";
    case "local_runtime":
      return "Local Runtime";
    case "self_hosted":
      return "Self Hosted";
    default:
      return mode;
  }
}

export function ModelConnectCard({
  model,
  activeConfig,
  hasConfig,
  onConnect,
  onTest,
}: ModelConnectCardProps) {
  const langs = model.supported_languages ?? [];
  const displayLangs =
    langs.length > 5
      ? langs.slice(0, 5).join(", ") + ` +${langs.length - 5} more`
      : langs.join(", ") || "—";

  const freeTierStale =
    model.free_tier_info != null && isStale(model.free_tier_verified_date);

  const freeTierNote =
    typeof model.free_tier_info === "object" &&
    model.free_tier_info &&
    typeof (model.free_tier_info as Record<string, unknown>).note === "string"
      ? ((model.free_tier_info as Record<string, unknown>).note as string)
      : typeof model.free_tier_info === "string"
      ? model.free_tier_info
      : null;

  const freeTierCredits =
    typeof model.free_tier_info === "object" &&
    model.free_tier_info &&
    (model.free_tier_info as Record<string, unknown>).credits_per_month
      ? Number((model.free_tier_info as Record<string, unknown>).credits_per_month).toLocaleString() + " credits/mo"
      : typeof model.free_tier_info === "object" &&
        model.free_tier_info &&
        (model.free_tier_info as Record<string, unknown>).hours_per_month
      ? (model.free_tier_info as Record<string, unknown>).hours_per_month + " hrs/mo"
      : null;

  const statusVariant: BadgeVariant =
    model.implementation_status === "supported"
      ? "success"
      : model.implementation_status === "experimental"
      ? "warning"
      : "danger";

  const canConnect =
    model.implementation_status === "supported" ||
    model.implementation_status === "experimental";

  const isActive = activeConfig?.model_id === model.model_id && activeConfig?.provider_name === model.provider_name && activeConfig?.is_active;

  return (
    <Card className={`flex flex-col gap-0 transition-all duration-200 hover:shadow-md ${isActive ? "ring-2 ring-success border-success/40 bg-success/5" : ""}`}>
      <CardBody className="flex flex-col gap-3 p-5">
        {/* Title row */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="text-base font-semibold text-text-primary capitalize truncate">
              {model.provider_name}
            </h3>
            <p className="text-xs text-text-secondary font-mono truncate mt-0.5">
              {model.model_id}
            </p>
          </div>
          <div className="shrink-0 flex flex-col items-end gap-1.5">
            <Badge variant={capabilityVariant(model.capability)} className="uppercase text-[11px] font-semibold px-2">
              {model.capability.toUpperCase()}
            </Badge>
            <Badge variant={statusVariant} className="capitalize text-[11px] px-2">
              {model.implementation_status}
            </Badge>
          </div>
        </div>

        {/* Hosting mode & Features */}
        <div className="flex items-center gap-1.5 text-xs text-text-secondary">
          {hostingIcon(model.hosting_mode)}
          <span className="font-medium">{hostingLabel(model.hosting_mode)}</span>
          {model.streaming_supported && (
            <span className="ml-2 inline-flex items-center gap-0.5 text-success font-medium text-xs bg-success/10 px-1.5 py-0.5 rounded">
              <Zap className="h-3 w-3" /> Streaming
            </span>
          )}
          {isActive && (
            <span className="ml-auto inline-flex items-center gap-1 text-[11px] font-semibold text-success bg-[#EBF7F2] border border-[#C0E8D5] px-2 py-0.5 rounded-full">
              <Check className="h-3 w-3" /> Active Primary
            </span>
          )}
        </div>

        {/* Languages */}
        <div className="text-xs text-text-secondary">
          <span className="font-semibold text-text-primary">Languages: </span>
          <span>{displayLangs}</span>
        </div>

        {/* Free tier box - Styled identically to user screenshot */}
        {(freeTierNote || freeTierCredits) && (
          <div className="rounded-xl border border-[#F0EBE1] bg-[#FAF8F5] p-3 text-xs">
            <div className="flex items-center justify-between">
              <p className="font-semibold text-text-primary">Free-tier limits</p>
              {freeTierCredits && (
                <span className="font-mono text-[11px] font-medium text-text-muted">
                  {freeTierCredits}
                </span>
              )}
            </div>
            {freeTierNote && (
              <p className="mt-1.5 text-text-secondary leading-relaxed">
                {freeTierNote}
              </p>
            )}
            {freeTierStale && (
              <div className="mt-2.5 flex items-start gap-1.5 rounded-lg bg-[#FEF6E7] border border-[#F5D99A] p-2 leading-tight text-warning text-[11px]">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>
                  Limits were last verified {model.free_tier_verified_date ?? "recently"}. Confirm them with the provider before relying on them.
                </span>
              </div>
            )}
          </div>
        )}

        {/* Commercial use */}
        <div className="flex items-center gap-1.5 text-xs">
          {model.commercial_use_allowed === true ? (
            <>
              <CheckCircle2 className="h-4 w-4 text-success" />
              <span className="text-text-secondary font-medium">Commercial use allowed</span>
            </>
          ) : model.commercial_use_allowed === false ? (
            <>
              <XCircle className="h-4 w-4 text-danger" />
              <span className="text-text-secondary font-medium">Non-commercial only</span>
            </>
          ) : (
            <span className="text-text-muted">License: {model.license_spdx ?? "Proprietary"}</span>
          )}
        </div>

        {/* Doc links */}
        {(model.doc_url || model.model_card_url) && (
          <div className="flex items-center gap-3 text-xs pt-0.5">
            {model.doc_url && (
              <a
                href={model.doc_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-accent hover:text-accent-hover font-medium hover:underline"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                Docs
              </a>
            )}
            {model.model_card_url && (
              <a
                href={model.model_card_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-accent hover:text-accent-hover font-medium hover:underline"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                Model Card
              </a>
            )}
          </div>
        )}

        {/* Action Button - Exact orange button styling as in screenshot */}
        <div className="mt-auto pt-2">
          {isActive ? (
            <div className="flex gap-2">
              <Button
                size="md"
                variant="secondary"
                className="flex-1 text-xs"
                onClick={() => onConnect(model)}
              >
                Reconfigure
              </Button>
              {onTest && activeConfig && (
                <Button
                  size="md"
                  variant="primary"
                  className="flex-1 text-xs"
                  onClick={() => onTest(model, activeConfig)}
                >
                  Test Connection
                </Button>
              )}
            </div>
          ) : hasConfig ? (
            <div className="flex gap-2">
              <Button
                size="md"
                variant="primary"
                className="flex-1 bg-[#E07038] hover:bg-[#C85D26] text-white"
                onClick={() => onConnect(model)}
              >
                Configure & Test
              </Button>
            </div>
          ) : (
            <Button
              size="md"
              variant="primary"
              disabled={!canConnect}
              className="w-full bg-[#E07038] hover:bg-[#C85D26] text-white font-medium py-2 rounded-lg transition-colors shadow-sm"
              onClick={() => canConnect && onConnect(model)}
              title={
                model.implementation_status === "experimental"
                  ? "This integration is experimental and may not be stable."
                  : undefined
              }
            >
              {model.hosting_mode === "local_runtime" ? "Configure Local" : "Connect"}
            </Button>
          )}
        </div>
      </CardBody>
    </Card>
  );
}
