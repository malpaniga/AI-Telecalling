"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  Calculator,
  Zap,
  Clock,
  Coins,
  TrendingDown,
  Info,
  CheckCircle2,
  AlertCircle,
  PhoneCall,
  Sparkles,
  RotateCw,
  ShieldCheck,
  ShieldAlert,
  Edit3,
  ExternalLink,
} from "lucide-react";
import { toast } from "react-hot-toast";
import {
  api,
  ProviderConfiguration,
  PricingRatesResponse,
  ProviderRateCard,
} from "@/lib/api";
import { CapabilityType } from "./ModelSetupWizard";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";

// ---------------------------------------------------------------------------
// Fallback Rate Card (used if offline / before API loads)
// ---------------------------------------------------------------------------

const FALLBACK_RATES: Record<string, Record<string, { unit: string; display: string; activePerSec: number; blendedPerSec: number }>> = {
  stt: {
    sarvam: {
      unit: "₹0.45 / min audio",
      display: "₹0.45/min",
      activePerSec: 0.0075,
      blendedPerSec: 0.0075 * (25 / 60), // ~0.31 paise/s
    },
    "groq-whisper": {
      unit: "$0.00185 / min (~₹0.16/min)",
      display: "₹0.16/min",
      activePerSec: 0.0026,
      blendedPerSec: 0.0026 * (25 / 60), // ~0.11 paise/s
    },
    "google-cloud-stt": {
      unit: "$0.016 / min Chirp 2 (~₹1.35/min)",
      display: "₹1.35/min",
      activePerSec: 0.0225,
      blendedPerSec: 0.0225 * (25 / 60), // ~0.94 paise/s
    },
    deepgram: {
      unit: "$0.0043 / min Nova-2 (~₹0.36/min)",
      display: "₹0.36/min",
      activePerSec: 0.006,
      blendedPerSec: 0.006 * (25 / 60),
    },
    "faster-whisper": {
      unit: "Local runtime",
      display: "₹0.00 (Self-hosted)",
      activePerSec: 0.0,
      blendedPerSec: 0.0,
    },
  },
  llm: {
    gemini: {
      unit: "$0.075 / 1M in · $0.30 / 1M out",
      display: "₹0.003 / turn",
      activePerSec: 0.0007,
      blendedPerSec: 0.0135 / 60, // ~0.023 paise/s
    },
    groq: {
      unit: "$0.59 / 1M in · $0.79 / 1M out",
      display: "₹0.006 / turn",
      activePerSec: 0.0012,
      blendedPerSec: 0.025 / 60, // ~0.041 paise/s
    },
    ollama: {
      unit: "Local runtime",
      display: "₹0.00 (Self-hosted)",
      activePerSec: 0.0,
      blendedPerSec: 0.0,
    },
  },
  tts: {
    sarvam: {
      unit: "₹0.18 / 1k chars Bulbul",
      display: "₹0.18/1k chars",
      activePerSec: 0.008,
      blendedPerSec: 0.008 * (25 / 60), // ~0.33 paise/s
    },
    elevenlabs: {
      unit: "$0.015 / 1k chars Flash v2.5",
      display: "₹1.27/1k chars",
      activePerSec: 0.018,
      blendedPerSec: 0.018 * (25 / 60), // ~0.75 paise/s
    },
    cartesia: {
      unit: "$0.075 / 1k chars Sonic",
      display: "₹6.35/1k chars",
      activePerSec: 0.09,
      blendedPerSec: 0.09 * (25 / 60), // ~3.75 paise/s
    },
    piper: {
      unit: "Local runtime",
      display: "₹0.00 (Self-hosted)",
      activePerSec: 0.0,
      blendedPerSec: 0.0,
    },
  },
};

export interface PipelineCostCalculatorProps {
  activeConfigs: Record<CapabilityType, ProviderConfiguration | null>;
  currentStepId?: CapabilityType;
}

export function PipelineCostCalculator({ activeConfigs }: PipelineCostCalculatorProps) {
  const [ratesData, setRatesData] = useState<PricingRatesResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);

  // Settings
  const [includeCarrierTelephony, setIncludeCarrierTelephony] = useState<boolean>(false);
  const [lossProtectionEnabled, setLossProtectionEnabled] = useState<boolean>(true);
  const [safetyMarginPct, setSafetyMarginPct] = useState<number>(15);
  const [activeTab, setActiveTab] = useState<"summary" | "projections" | "loss_prevention">("summary");

  // Admin Override Modal State
  const [overrideModalOpen, setOverrideModalOpen] = useState<boolean>(false);
  const [editingCard, setEditingCard] = useState<ProviderRateCard | null>(null);
  const [overrideRateInput, setOverrideRateInput] = useState<string>("");
  const [overrideMarginInput, setOverrideMarginInput] = useState<string>("15");
  const [overrideNotesInput, setOverrideNotesInput] = useState<string>("");
  const [isSavingOverride, setIsSavingOverride] = useState<boolean>(false);

  // Load live rate cards and FX rate from backend
  const loadRates = async () => {
    try {
      setLoading(true);
      const res = await api.pricing.rates();
      setRatesData(res);
      if (res.settings?.default_safety_margin_pct) {
        setSafetyMarginPct(res.settings.default_safety_margin_pct);
      }
    } catch (err) {
      console.warn("Could not load dynamic pricing rates, using built-in rates:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRates();
  }, []);

  // Trigger on-demand sync of FX and rates
  const handleSyncNow = async () => {
    try {
      setIsSyncing(true);
      const res = await api.pricing.sync();
      toast.success(
        `Synchronized ${res.synced_count} models! USD/INR FX updated to ₹${res.usd_to_inr_fx_rate.toFixed(2)}.`
      );
      await loadRates();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Sync failed";
      toast.error(msg);
    } finally {
      setIsSyncing(false);
    }
  };

  // Open override modal
  const handleOpenOverride = (card: ProviderRateCard) => {
    setEditingCard(card);
    setOverrideRateInput(String(card.base_unit_rate));
    setOverrideMarginInput(String(card.safety_margin_pct || 15));
    setOverrideNotesInput(card.notes || "");
    setOverrideModalOpen(true);
  };

  // Save admin override
  const handleSaveOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCard) return;
    const rateNum = parseFloat(overrideRateInput);
    if (isNaN(rateNum) || rateNum < 0) {
      toast.error("Please enter a valid rate number");
      return;
    }
    const marginNum = parseFloat(overrideMarginInput) || 15;

    try {
      setIsSavingOverride(true);
      await api.pricing.override({
        capability: editingCard.capability,
        provider_name: editingCard.provider_name,
        model_id: editingCard.model_id,
        base_unit_rate: rateNum,
        safety_margin_pct: marginNum,
        notes: overrideNotesInput || "Manual admin override",
      });
      toast.success(`Updated ${editingCard.provider_name.toUpperCase()} rate to guard against loss.`);
      setOverrideModalOpen(false);
      await loadRates();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Override failed";
      toast.error(msg);
    } finally {
      setIsSavingOverride(false);
    }
  };

  // Telephony rate: WebRTC = 0.0, PSTN = ~₹0.40/min
  const telephonyCostPerSecInr = includeCarrierTelephony ? 0.0067 : 0.0;
  const currentFx = ratesData?.settings?.usd_to_inr_fx_rate || 84.85;

  // Resolve dynamic pricing for each capability step
  const resolvedPricing = useMemo(() => {
    const resolve = (cap: CapabilityType) => {
      const cfg = activeConfigs[cap];
      const provKey = cfg?.provider_name?.toLowerCase() || (cap === "stt" ? "sarvam" : cap === "llm" ? "gemini" : "sarvam");

      // Check backend dynamic rate card
      const dynamicList = ratesData?.rates_by_capability?.[cap] || [];
      const dynamicMatch = dynamicList.find(
        (c) => c.provider_name.toLowerCase() === provKey
      );

      if (dynamicMatch) {
        return {
          card: dynamicMatch,
          configured: Boolean(cfg),
          providerName: dynamicMatch.provider_name,
          modelId: cfg?.model_id || dynamicMatch.model_id,
          unit: `${dynamicMatch.base_currency === "USD" ? "$" : "₹"}${dynamicMatch.base_unit_rate} / ${dynamicMatch.billing_unit}`,
          display: `₹${dynamicMatch.effective_unit_rate_inr.toFixed(2)} (${dynamicMatch.base_currency})`,
          activeCostPerSec: dynamicMatch.active_cost_per_sec_inr,
          blendedCostPerSec: dynamicMatch.blended_cost_per_sec_inr,
          safetyMarginPct: dynamicMatch.safety_margin_pct || safetyMarginPct,
          isOverridden: dynamicMatch.sync_source === "admin_override",
        };
      }

      // Fallback to static verified rates
      const fallback = FALLBACK_RATES[cap]?.[provKey] || {
        unit: "Standard cloud rate",
        display: "₹0.45/min",
        activePerSec: 0.0075,
        blendedPerSec: 0.0031,
      };

      return {
        card: null as ProviderRateCard | null,
        configured: Boolean(cfg),
        providerName: provKey,
        modelId: cfg?.model_id || "default",
        unit: fallback.unit,
        display: fallback.display,
        activeCostPerSec: fallback.activePerSec,
        blendedCostPerSec: fallback.blendedPerSec,
        safetyMarginPct: safetyMarginPct,
        isOverridden: false,
      };
    };

    const stt = resolve("stt");
    const llm = resolve("llm");
    const tts = resolve("tts");

    // Raw vendor cost (what providers invoice us)
    const rawAiPerSecInr = stt.blendedCostPerSec + llm.blendedCostPerSec + tts.blendedCostPerSec;
    const rawTotalPerSecInr = rawAiPerSecInr + telephonyCostPerSecInr;
    const rawTotalPerMinInr = rawTotalPerSecInr * 60;
    const rawPaisePerSec = rawTotalPerSecInr * 100;

    // Loss-Protected Retail Rate (what we bill customers with safety buffer)
    const appliedMargin = lossProtectionEnabled ? safetyMarginPct : 0;
    const retailTotalPerSecInr = rawTotalPerSecInr * (1 + appliedMargin / 100);
    const retailTotalPerMinInr = retailTotalPerSecInr * 60;
    const retailPaisePerSec = retailTotalPerSecInr * 100;

    const safetyBufferPaisePerSec = retailPaisePerSec - rawPaisePerSec;
    const allConfigured = stt.configured && llm.configured && tts.configured;

    return {
      stt,
      llm,
      tts,
      rawTotalPerSecInr,
      rawTotalPerMinInr,
      rawPaisePerSec,
      appliedMargin,
      retailTotalPerSecInr,
      retailTotalPerMinInr,
      retailPaisePerSec,
      safetyBufferPaisePerSec,
      allConfigured,
    };
  }, [activeConfigs, ratesData, telephonyCostPerSecInr, lossProtectionEnabled, safetyMarginPct]);

  const lastSyncStr = ratesData?.last_synced_at
    ? new Date(ratesData.last_synced_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : "Today (Auto)";

  return (
    <div className="rounded-2xl border border-border bg-gradient-to-br from-surface via-surface to-secondary/30 p-5 shadow-sm space-y-4">
      {/* ── Header: Live Daily Sync & FX Ribbon ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/60 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#E07038]/10 text-[#E07038] border border-[#E07038]/20">
            <Calculator className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-sm font-bold text-text-primary">
                Daily Dynamic Pipeline Rate Card
              </h3>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 flex items-center gap-1">
                <Zap className="h-2.5 w-2.5" /> Live Daily FX: $1 = ₹{currentFx.toFixed(2)}
              </span>
              <span className="text-[10px] text-text-muted">
                Synced at {lastSyncStr}
              </span>
            </div>
            <p className="text-xs text-text-muted mt-0.5">
              Automated daily vendor pricing sync & loss-prevention markup for STT, LLM, TTS, and PSTN.
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Daily Sync Button */}
          <Button
            variant="secondary"
            size="sm"
            onClick={handleSyncNow}
            disabled={isSyncing}
            className="text-xs gap-1.5 h-8 bg-surface border-border hover:bg-surface-subtle"
            title="Fetch today's USD/INR FX and recalculate effective vendor rates"
          >
            <RotateCw className={`h-3 w-3 ${isSyncing ? "animate-spin text-accent" : ""}`} />
            <span>{isSyncing ? "Syncing Rates..." : "Sync FX & Rates"}</span>
          </Button>

          {/* Carrier Trunk Toggle */}
          <button
            type="button"
            onClick={() => setIncludeCarrierTelephony(!includeCarrierTelephony)}
            className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-semibold border transition-all h-8 ${
              includeCarrierTelephony
                ? "bg-accent/10 text-accent border-accent/30 shadow-sm"
                : "bg-surface-subtle text-text-secondary border-border hover:bg-surface"
            }`}
            title="Toggle Indian Cellular SIP Trunk cost (~₹0.40/min)"
          >
            <PhoneCall className="h-3 w-3" />
            <span>{includeCarrierTelephony ? "+ Tata/Airtel SIP (₹0.40/m)" : "WebRTC (₹0.00)"}</span>
          </button>
        </div>
      </div>

      {/* ── Sub-Navigation Tabs ── */}
      <div className="flex items-center justify-between border-b border-border/40 pb-2">
        <div className="flex gap-2 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab("summary")}
            className={`px-3 py-1 rounded-lg font-medium transition-colors ${
              activeTab === "summary"
                ? "bg-[#E07038] text-white shadow-xs"
                : "text-text-secondary hover:text-text-primary hover:bg-surface"
            }`}
          >
            3-Step Breakdown
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("loss_prevention")}
            className={`px-3 py-1 rounded-lg font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === "loss_prevention"
                ? "bg-emerald-600 text-white shadow-xs"
                : "text-text-secondary hover:text-text-primary hover:bg-surface"
            }`}
          >
            <ShieldCheck className="h-3 w-3" /> Loss-Protection Margin (+{safetyMarginPct}%)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("projections")}
            className={`px-3 py-1 rounded-lg font-medium transition-colors ${
              activeTab === "projections"
                ? "bg-[#E07038] text-white shadow-xs"
                : "text-text-secondary hover:text-text-primary hover:bg-surface"
            }`}
          >
            Volume Projections
          </button>
        </div>

        {/* Loss Protection Toggle Switch */}
        <div className="flex items-center gap-2">
          <label className="text-[11px] font-semibold text-text-primary flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={lossProtectionEnabled}
              onChange={(e) => setLossProtectionEnabled(e.target.checked)}
              className="rounded border-border text-emerald-600 focus:ring-emerald-500 h-3.5 w-3.5 cursor-pointer"
            />
            <span className={lossProtectionEnabled ? "text-emerald-500 font-bold" : "text-text-muted"}>
              Loss-Protection Buffer
            </span>
          </label>
        </div>
      </div>

      {/* ── Tab 1: 3-Step Breakdown ── */}
      {activeTab === "summary" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Step 1 STT */}
          <div className="p-3.5 rounded-xl border border-border/80 bg-surface/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-text-muted">
                Step 1: STT
              </span>
              {resolvedPricing.stt.card && (
                <button
                  type="button"
                  onClick={() => handleOpenOverride(resolvedPricing.stt.card!)}
                  className="text-[10px] text-accent hover:underline flex items-center gap-0.5"
                  title="Override rate if provider announced price change"
                >
                  <Edit3 className="h-2.5 w-2.5" /> Edit Rate
                </button>
              )}
            </div>
            <div>
              <p className="text-xs font-semibold text-text-primary capitalize truncate">
                {resolvedPricing.stt.providerName}
              </p>
              <p className="text-[11px] text-text-muted font-mono truncate">
                {resolvedPricing.stt.unit}
              </p>
            </div>
            <div className="pt-1 border-t border-border/40 flex items-center justify-between">
              <span className="text-[11px] text-text-secondary">Blended per sec:</span>
              <span className="text-xs font-bold font-mono text-text-primary">
                {(resolvedPricing.stt.blendedCostPerSec * 100).toFixed(2)} paise
              </span>
            </div>
          </div>

          {/* Step 2 LLM */}
          <div className="p-3.5 rounded-xl border border-border/80 bg-surface/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-text-muted">
                Step 2: LLM
              </span>
              {resolvedPricing.llm.card && (
                <button
                  type="button"
                  onClick={() => handleOpenOverride(resolvedPricing.llm.card!)}
                  className="text-[10px] text-accent hover:underline flex items-center gap-0.5"
                  title="Override rate if provider announced price change"
                >
                  <Edit3 className="h-2.5 w-2.5" /> Edit Rate
                </button>
              )}
            </div>
            <div>
              <p className="text-xs font-semibold text-text-primary capitalize truncate">
                {resolvedPricing.llm.providerName}
              </p>
              <p className="text-[11px] text-text-muted font-mono truncate">
                {resolvedPricing.llm.unit}
              </p>
            </div>
            <div className="pt-1 border-t border-border/40 flex items-center justify-between">
              <span className="text-[11px] text-text-secondary">Blended per sec:</span>
              <span className="text-xs font-bold font-mono text-text-primary">
                {(resolvedPricing.llm.blendedCostPerSec * 100).toFixed(2)} paise
              </span>
            </div>
          </div>

          {/* Step 3 TTS */}
          <div className="p-3.5 rounded-xl border border-border/80 bg-surface/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-text-muted">
                Step 3: TTS
              </span>
              {resolvedPricing.tts.card && (
                <button
                  type="button"
                  onClick={() => handleOpenOverride(resolvedPricing.tts.card!)}
                  className="text-[10px] text-accent hover:underline flex items-center gap-0.5"
                  title="Override rate if provider announced price change"
                >
                  <Edit3 className="h-2.5 w-2.5" /> Edit Rate
                </button>
              )}
            </div>
            <div>
              <p className="text-xs font-semibold text-text-primary capitalize truncate">
                {resolvedPricing.tts.providerName}
              </p>
              <p className="text-[11px] text-text-muted font-mono truncate">
                {resolvedPricing.tts.unit}
              </p>
            </div>
            <div className="pt-1 border-t border-border/40 flex items-center justify-between">
              <span className="text-[11px] text-text-secondary">Blended per sec:</span>
              <span className="text-xs font-bold font-mono text-text-primary">
                {(resolvedPricing.tts.blendedCostPerSec * 100).toFixed(2)} paise
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab 2: Loss-Prevention & Safety Buffer ── */}
      {activeTab === "loss_prevention" && (
        <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 space-y-3">
          <div className="flex items-start gap-2.5">
            <ShieldCheck className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
            <div>
              <h4 className="text-xs font-bold text-text-primary">
                Why Loss-Protection Buffer is Essential
              </h4>
              <p className="text-[11px] text-text-secondary mt-0.5 leading-relaxed">
                If vendors hike prices mid-cycle, currency rates fluctuate, or prospect calls generate extra conversational tokens, 
                billing strictly at raw cost would result in net losses. The <strong>+{safetyMarginPct}% buffer</strong> ensures every 
                billable second covers unexpected token bursts and intra-day vendor adjustments.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
            <div className="p-2.5 rounded-lg bg-surface border border-border">
              <span className="block text-[10px] text-text-muted">Net Provider Cost</span>
              <span className="font-mono font-bold text-xs text-text-primary">
                {resolvedPricing.rawPaisePerSec.toFixed(2)} paise / sec
              </span>
              <span className="block text-[10px] text-text-muted">₹{resolvedPricing.rawTotalPerMinInr.toFixed(2)} / min</span>
            </div>

            <div className="p-2.5 rounded-lg bg-surface border border-border">
              <span className="block text-[10px] text-text-muted">Safety Buffer (+{safetyMarginPct}%)</span>
              <span className="font-mono font-bold text-xs text-emerald-500">
                +{resolvedPricing.safetyBufferPaisePerSec.toFixed(2)} paise / sec
              </span>
              <span className="block text-[10px] text-text-muted">Protects against price hikes</span>
            </div>

            <div className="p-2.5 rounded-lg bg-surface border border-emerald-500/30 bg-emerald-500/10">
              <span className="block text-[10px] text-emerald-600 font-semibold">Loss-Proof Billed Rate</span>
              <span className="font-mono font-extrabold text-sm text-emerald-600">
                {resolvedPricing.retailPaisePerSec.toFixed(2)} paise / sec
              </span>
              <span className="block text-[10px] text-text-primary font-bold">₹{resolvedPricing.retailTotalPerMinInr.toFixed(2)} / min</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab 3: Projections ── */}
      {activeTab === "projections" && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3 rounded-xl bg-surface border border-border text-center">
            <span className="block text-[11px] text-text-muted font-medium">1-Minute Call</span>
            <span className="font-mono font-bold text-sm text-text-primary block mt-0.5">
              ₹{resolvedPricing.retailTotalPerMinInr.toFixed(2)}
            </span>
            <span className="text-[10px] text-text-muted">
              (Raw cost: ₹{resolvedPricing.rawTotalPerMinInr.toFixed(2)})
            </span>
          </div>

          <div className="p-3 rounded-xl bg-surface border border-border text-center">
            <span className="block text-[11px] text-text-muted font-medium">3-Minute Call</span>
            <span className="font-mono font-bold text-sm text-text-primary block mt-0.5">
              ₹{(resolvedPricing.retailTotalPerMinInr * 3).toFixed(2)}
            </span>
            <span className="text-[10px] text-text-muted">
              (Raw cost: ₹{(resolvedPricing.rawTotalPerMinInr * 3).toFixed(2)})
            </span>
          </div>

          <div className="p-3 rounded-xl bg-surface border border-border text-center">
            <span className="block text-[11px] text-text-muted font-medium">1,000 Calls (1-min)</span>
            <span className="font-mono font-bold text-sm text-emerald-500 block mt-0.5">
              ₹{(resolvedPricing.retailTotalPerMinInr * 1000).toFixed(0)}
            </span>
            <span className="text-[10px] text-text-muted">
              Guaranteed profitable batch
            </span>
          </div>
        </div>
      )}

      {/* ── Summary Ribbon ── */}
      <div className="p-4 rounded-xl border border-[#E07038]/20 bg-[#E07038]/5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-[#E07038] flex items-center gap-1">
            <Coins className="h-3.5 w-3.5" /> Effective Pipeline Rate
          </div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-extrabold text-text-primary font-mono tracking-tight">
              {resolvedPricing.retailPaisePerSec.toFixed(2)}
              <span className="text-sm font-semibold text-text-muted font-sans ml-1">paise / sec</span>
            </span>
            <span className="text-xs text-text-muted">
              (₹{resolvedPricing.retailTotalPerSecInr.toFixed(4)}/s)
            </span>
            <span className="text-sm font-bold text-emerald-500 font-mono ml-3">
              ₹{resolvedPricing.retailTotalPerMinInr.toFixed(2)} / min
            </span>
          </div>
          <p className="text-[11px] text-text-muted mt-0.5">
            {lossProtectionEnabled
              ? `Includes ${safetyMarginPct}% loss-protection safety buffer over raw vendor costs (${resolvedPricing.rawPaisePerSec.toFixed(2)}p/s).`
              : "Raw provider pass-through rate (no loss buffer enabled)."}
          </p>
        </div>

        {/* Quick Projection Badges */}
        <div className="flex items-center gap-2">
          <div className="px-3 py-1.5 rounded-lg bg-surface border border-border/80 text-center">
            <span className="block text-[10px] text-text-muted">1-Min Call</span>
            <span className="font-mono font-bold text-xs text-text-primary">
              ₹{resolvedPricing.retailTotalPerMinInr.toFixed(2)}
            </span>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-surface border border-border/80 text-center">
            <span className="block text-[10px] text-text-muted">1k Calls</span>
            <span className="font-mono font-bold text-xs text-emerald-500">
              ₹{(resolvedPricing.retailTotalPerMinInr * 1000).toFixed(0)}
            </span>
          </div>
        </div>
      </div>

      {/* ── Admin Override Modal ── */}
      <Modal
        isOpen={overrideModalOpen}
        onClose={() => setOverrideModalOpen(false)}
        title={editingCard ? `Override Rate: ${editingCard.provider_name.toUpperCase()} (${editingCard.capability.toUpperCase()})` : "Override Rate"}
      >
        <form onSubmit={handleSaveOverride} className="space-y-4">
          <p className="text-xs text-text-secondary">
            Instantly update this provider&apos;s base rate if you received an email notification or price increase announcement.
          </p>

          <div>
            <label className="block text-xs font-semibold text-text-primary mb-1">
              Base Unit Rate ({editingCard?.base_currency || "INR"})
            </label>
            <input
              type="number"
              step="any"
              value={overrideRateInput}
              onChange={(e) => setOverrideRateInput(e.target.value)}
              required
              className="w-full px-3 py-2 text-sm rounded-xl border border-border bg-surface text-text-primary focus:ring-2 focus:ring-accent"
              placeholder={`e.g. ${editingCard?.base_unit_rate || "0.45"}`}
            />
            <span className="text-[10px] text-text-muted mt-0.5 block">
              Unit: {editingCard?.billing_unit || "audio_minute / 1k_chars"}
            </span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-text-primary mb-1">
              Safety Margin Buffer (%)
            </label>
            <input
              type="number"
              step="any"
              value={overrideMarginInput}
              onChange={(e) => setOverrideMarginInput(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-xl border border-border bg-surface text-text-primary focus:ring-2 focus:ring-accent"
              placeholder="15"
            />
            <span className="text-[10px] text-text-muted mt-0.5 block">
              Percentage added to protect against token bloat or currency fluctuations.
            </span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-text-primary mb-1">
              Reason / Notes
            </label>
            <input
              type="text"
              value={overrideNotesInput}
              onChange={(e) => setOverrideNotesInput(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-xl border border-border bg-surface text-text-primary focus:ring-2 focus:ring-accent"
              placeholder="e.g. Official vendor email notice received"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setOverrideModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isSavingOverride}
              className="bg-[#E07038] hover:bg-[#C85D26] text-white"
            >
              {isSavingOverride ? "Saving..." : "Apply & Guard Loss"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
