"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  Mic,
  Bot,
  Volume2,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Search,
  Sparkles,
  Zap,
  Check,
  AlertCircle,
  Play,
  RotateCw,
  ExternalLink,
  Phone,
} from "lucide-react";
import { toast } from "react-hot-toast";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Modal } from "@/components/ui/modal";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { ModelConnectCard } from "./ModelConnectCard";
import { PipelineCostCalculator } from "./PipelineCostCalculator";
import { useTestAgent } from "@/contexts/test-agent-context";
import {
  api,
  AIModelCatalogue,
  ProviderConfiguration,
  ConnectProviderRequest,
  TestResult,
  WizardStatusResponse,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Wizard Steps Definition
// ---------------------------------------------------------------------------

export type CapabilityType = "stt" | "llm" | "tts";

interface StepConfig {
  id: CapabilityType;
  stepNumber: number;
  title: string;
  shortTitle: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  recommendedProviders: string[];
}

const STEPS: StepConfig[] = [
  {
    id: "stt",
    stepNumber: 1,
    title: "Speech-to-Text (STT)",
    shortTitle: "STT",
    description: "Converts inbound caller voice into real-time transcripts. High accuracy and low latency are critical.",
    icon: Mic,
    recommendedProviders: ["sarvam", "groq-whisper", "google-cloud-stt"],
  },
  {
    id: "llm",
    stepNumber: 2,
    title: "Reasoning Engine (LLM)",
    shortTitle: "LLM",
    description: "Drives conversational AI responses, intent detection, and business logic during calls.",
    icon: Bot,
    recommendedProviders: ["groq", "gemini"],
  },
  {
    id: "tts",
    stepNumber: 3,
    title: "Text-to-Speech (TTS)",
    shortTitle: "TTS",
    description: "Synthesizes bot replies into natural human speech. Low latency provides natural back-and-forth flow.",
    icon: Volume2,
    recommendedProviders: ["elevenlabs", "sarvam"],
  },
];

// Preset voice options for convenient selection
const VOICE_PRESETS: Record<string, Array<{ id: string; label: string; gender: string }>> = {
  elevenlabs: [
    { id: "JBFqnCBsd6RMkjVDRZzb", label: "George", gender: "Male" },
    { id: "21m00Tcm4TlvDq8ikWAM", label: "Rachel", gender: "Female" },
    { id: "pNInz6obpgDQGcFmaJgB", label: "Adam", gender: "Male" },
    { id: "ErXwobaYiN019PkySvjV", label: "Antoni", gender: "Male" },
  ],
  sarvam: [
    { id: "kavya", label: "Kavya", gender: "Female" },
    { id: "meera", label: "Meera", gender: "Female" },
    { id: "dhruv", label: "Dhruv", gender: "Male" },
    { id: "arvind", label: "Arvind", gender: "Male" },
  ],
};

export function ModelSetupWizard() {
  const { openTestAgent } = useTestAgent();
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [catalogue, setCatalogue] = useState<AIModelCatalogue[]>([]);
  const [configurations, setConfigurations] = useState<ProviderConfiguration[]>([]);
  const [wizardStatus, setWizardStatus] = useState<WizardStatusResponse | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedProviderFilter, setSelectedProviderFilter] = useState<string>("all");

  // Connect & Test Modal State
  const [connectModalOpen, setConnectModalOpen] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState<AIModelCatalogue | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState<string>("");
  const [voiceInput, setVoiceInput] = useState<string>("");
  const [languageInput, setLanguageInput] = useState<string>("");
  const [extraParamsInput, setExtraParamsInput] = useState<string>("");
  const [isFallback, setIsFallback] = useState<boolean>(false);

  // Connection & Test In-Progress State
  const [isConnecting, setIsConnecting] = useState<boolean>(false);
  const [isTesting, setIsTesting] = useState<boolean>(false);
  const [isActivating, setIsActivating] = useState<boolean>(false);
  const [connectedConfig, setConnectedConfig] = useState<ProviderConfiguration | null>(null);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testAudioUrl, setTestAudioUrl] = useState<string | null>(null);

  const currentStep = STEPS[currentStepIndex];

  // ---------------------------------------------------------------------------
  // Load data
  // ---------------------------------------------------------------------------

  const loadData = async () => {
    try {
      setLoading(true);
      const [catRes, cfgRes, statusRes] = await Promise.all([
        api.modelDirectory.catalogue(),
        api.modelDirectory.listConfigs(),
        api.modelDirectory.wizardStatus().catch(() => null),
      ]);
      setCatalogue(catRes);
      setConfigurations(cfgRes);
      if (statusRes) setWizardStatus(statusRes);
    } catch (err) {
      toast.error("Failed to load model directory data: " + String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // ---------------------------------------------------------------------------
  // Active configs by capability
  // ---------------------------------------------------------------------------

  const activeConfigsMap = useMemo(() => {
    const map: Record<CapabilityType, ProviderConfiguration | null> = {
      stt: null,
      llm: null,
      tts: null,
    };
    for (const cfg of configurations) {
      if (cfg.is_active && !cfg.is_fallback) {
        map[cfg.capability] = cfg;
      }
    }
    return map;
  }, [configurations]);

  // Current step's models
  const stepModels = useMemo(() => {
    return catalogue.filter((m) => m.capability === currentStep.id);
  }, [catalogue, currentStep.id]);

  // Unique providers in current step
  const availableProviders = useMemo(() => {
    const set = new Set<string>();
    stepModels.forEach((m) => set.add(m.provider_name));
    return Array.from(set).sort();
  }, [stepModels]);

  // Filtered models
  const filteredModels = useMemo(() => {
    return stepModels.filter((m) => {
      if (selectedProviderFilter !== "all" && m.provider_name !== selectedProviderFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesName = m.provider_name.toLowerCase().includes(query);
        const matchesId = m.model_id.toLowerCase().includes(query);
        const matchesNotes = m.notes?.toLowerCase().includes(query);
        const matchesLangs = m.supported_languages?.some((l) => l.toLowerCase().includes(query));
        if (!matchesName && !matchesId && !matchesNotes && !matchesLangs) {
          return false;
        }
      }
      return true;
    });
  }, [stepModels, selectedProviderFilter, searchQuery]);

  // ---------------------------------------------------------------------------
  // Open Connect Modal
  // ---------------------------------------------------------------------------

  const handleOpenConnect = (model: AIModelCatalogue) => {
    setSelectedModel(model);
    setApiKeyInput("");
    setVoiceInput(
      model.provider_name === "elevenlabs"
        ? "JBFqnCBsd6RMkjVDRZzb"
        : model.provider_name === "sarvam"
        ? "kavya"
        : ""
    );
    setLanguageInput(
      model.supported_languages?.includes("en-IN")
        ? "en-IN"
        : model.supported_languages?.[0] || ""
    );
    setExtraParamsInput("");
    setIsFallback(false);
    setConnectedConfig(null);
    setTestResult(null);
    setTestAudioUrl(null);

    // If there is an existing config for this provider & model, prefill
    const existing = configurations.find(
      (c) => c.provider_name === model.provider_name && c.model_id === model.model_id
    );
    if (existing) {
      setConnectedConfig(existing);
      if (existing.voice) setVoiceInput(existing.voice);
      if (existing.language) setLanguageInput(existing.language);
      if (existing.is_fallback) setIsFallback(existing.is_fallback);
      if (existing.last_test_result) {
        setTestResult({
          status: existing.last_test_result,
          latency_ms: existing.last_test_latency_ms,
        });
      }
    }

    setConnectModalOpen(true);
  };

  // ---------------------------------------------------------------------------
  // Connect / Save
  // ---------------------------------------------------------------------------

  const handleSaveAndConnect = async () => {
    if (!selectedModel) return;

    if (
      selectedModel.credential_requirements.length > 0 &&
      !apiKeyInput.trim() &&
      !connectedConfig
    ) {
      toast.error(`Please provide ${selectedModel.credential_requirements.join(" or ")}`);
      return;
    }

    try {
      setIsConnecting(true);
      const req: ConnectProviderRequest = {
        provider_name: selectedModel.provider_name,
        model_id: selectedModel.model_id,
        capability: selectedModel.capability,
        credential_plaintext: apiKeyInput.trim() || undefined,
        voice: voiceInput.trim() || undefined,
        language: languageInput.trim() || undefined,
        is_fallback: isFallback,
      };

      if (extraParamsInput.trim()) {
        try {
          req.extra_params = JSON.parse(extraParamsInput);
        } catch {
          toast.error("Model parameters must be valid JSON");
          setIsConnecting(false);
          return;
        }
      }

      const saved = await api.modelDirectory.connect(req);
      setConnectedConfig(saved);
      toast.success(`${selectedModel.provider_name} / ${selectedModel.model_id} configured!`);

      // Refresh configs list
      const updated = await api.modelDirectory.listConfigs();
      setConfigurations(updated);

      // Immediately run test
      await handleRunTest(saved.id);
    } catch (err) {
      toast.error("Failed to connect provider: " + String(err));
    } finally {
      setIsConnecting(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Test Config
  // ---------------------------------------------------------------------------

  const handleRunTest = async (configId?: string) => {
    const targetId = configId || connectedConfig?.id;
    if (!targetId) {
      toast.error("Please save configuration first");
      return;
    }

    try {
      setIsTesting(true);
      setTestResult(null);
      setTestAudioUrl(null);

      const res = await api.modelDirectory.testConfig(targetId);
      setTestResult(res);

      if (res.status === "ok") {
        toast.success(`Test succeeded in ${res.latency_ms ?? 0}ms!`);
        if (res.sample_output_b64) {
          try {
            const blob = new Blob(
              [Uint8Array.from(atob(res.sample_output_b64), (c) => c.charCodeAt(0))],
              { type: "audio/wav" }
            );
            const url = URL.createObjectURL(blob);
            setTestAudioUrl(url);
          } catch {
            // non-fatal
          }
        }
      } else {
        toast.error(`Test failed: ${res.error || "Unknown error"}`);
      }

      // Refresh configs to get latest test result
      const updated = await api.modelDirectory.listConfigs();
      setConfigurations(updated);
    } catch (err) {
      toast.error("Test failed: " + String(err));
      setTestResult({
        status: "error",
        latency_ms: null,
        error: String(err),
      });
    } finally {
      setIsTesting(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Activate Config
  // ---------------------------------------------------------------------------

  const handleActivate = async (configId?: string) => {
    const targetId = configId || connectedConfig?.id;
    if (!targetId) return;

    try {
      setIsActivating(true);
      const activated = await api.modelDirectory.activateConfig(targetId);
      toast.success(`${activated.provider_name} activated as primary ${activated.capability.toUpperCase()} provider!`);

      // Refresh
      const [updatedConfigs, statusRes] = await Promise.all([
        api.modelDirectory.listConfigs(),
        api.modelDirectory.wizardStatus().catch(() => null),
      ]);
      setConfigurations(updatedConfigs);
      if (statusRes) setWizardStatus(statusRes);

      setConnectModalOpen(false);
    } catch (err) {
      toast.error("Failed to activate provider: " + String(err));
    } finally {
      setIsActivating(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Wizard Navigation
  // ---------------------------------------------------------------------------

  const handleNextStep = () => {
    if (currentStepIndex < STEPS.length - 1) {
      setCurrentStepIndex((prev) => prev + 1);
      setSelectedProviderFilter("all");
      setSearchQuery("");
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handlePrevStep = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex((prev) => prev - 1);
      setSelectedProviderFilter("all");
      setSearchQuery("");
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  const isStepComplete = (cap: CapabilityType) => Boolean(activeConfigsMap[cap]);
  const allComplete = isStepComplete("stt") && isStepComplete("llm") && isStepComplete("tts");

  return (
    <div className="space-y-8">
      {/* ── Wizard Progress Header ── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/15 text-accent text-xs font-bold">
                W
              </span>
              <h1 className="text-xl font-bold text-text-primary">
                AI Voice Pipeline Setup Wizard
              </h1>
              {allComplete ? (
                <Badge variant="success" className="gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Pipeline Ready
                </Badge>
              ) : (
                <Badge variant="warning">Setup in Progress</Badge>
              )}
            </div>
            <p className="mt-1 text-sm text-text-secondary">
              Configure and test your Speech-to-Text, Reasoning, and Voice providers step-by-step for production calling.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => openTestAgent()}
              title="Try the agent in the playground"
              className="flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-black hover:bg-neutral-800 text-white dark:bg-white dark:text-black dark:hover:bg-neutral-200 shadow-sm transition-all active:scale-[0.98]"
            >
              <Phone className="h-3.5 w-3.5 fill-current" />
              <span>Test agent</span>
            </button>
            <span className="text-xs text-text-muted">
              Step {currentStepIndex + 1} of {STEPS.length}
            </span>
          </div>
        </div>

        {/* Step Indicator Tabs */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          {STEPS.map((step, idx) => {
            const Icon = step.icon;
            const isSelected = idx === currentStepIndex;
            const isDone = isStepComplete(step.id);
            const activeCfg = activeConfigsMap[step.id];

            return (
              <button
                key={step.id}
                onClick={() => {
                  setCurrentStepIndex(idx);
                  setSelectedProviderFilter("all");
                  setSearchQuery("");
                }}
                className={`flex items-start gap-3.5 rounded-xl border p-4 text-left transition-all ${
                  isSelected
                    ? "border-accent bg-accent/5 ring-2 ring-accent/20"
                    : isDone
                    ? "border-success/40 bg-success/5 hover:border-success"
                    : "border-border bg-surface hover:bg-surface-subtle"
                }`}
              >
                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
                    isDone
                      ? "bg-success text-white"
                      : isSelected
                      ? "bg-accent text-white"
                      : "bg-surface-subtle text-text-muted"
                  }`}
                >
                  {isDone ? <Check className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                      Step {step.stepNumber}
                    </span>
                    {isDone && (
                      <span className="text-[11px] font-medium text-success">
                        Active
                      </span>
                    )}
                  </div>
                  <p className="font-semibold text-text-primary text-sm truncate">
                    {step.title}
                  </p>
                  <p className="text-xs text-text-secondary truncate mt-0.5">
                    {activeCfg
                      ? `${activeCfg.provider_name} (${activeCfg.model_id})`
                      : "Not configured"}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Live 3-Step Pipeline Cost Calculator ── */}
      <PipelineCostCalculator
        activeConfigs={activeConfigsMap}
        currentStepId={currentStep.id}
      />

      {/* ── Current Step Main Container ── */}
      <div className="space-y-6">
        {/* Step Header & Guidelines */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold uppercase tracking-wider text-accent">
                Step {currentStep.stepNumber}
              </span>
              <span className="text-text-muted">•</span>
              <h2 className="text-lg font-bold text-text-primary">
                {currentStep.title} Configuration
              </h2>
            </div>
            <p className="text-sm text-text-secondary mt-1">
              {currentStep.description}
            </p>
          </div>

          {activeConfigsMap[currentStep.id] && (
            <div className="flex items-center gap-2 rounded-xl border border-success/30 bg-success/10 px-4 py-2">
              <CheckCircle2 className="h-4 w-4 text-success shrink-0" />
              <div className="text-xs">
                <span className="font-medium text-text-primary">Current Active: </span>
                <span className="font-semibold text-success">
                  {activeConfigsMap[currentStep.id]?.provider_name} / {activeConfigsMap[currentStep.id]?.model_id}
                </span>
                {activeConfigsMap[currentStep.id]?.last_test_latency_ms && (
                  <span className="text-text-muted ml-1.5 font-mono">
                    ({activeConfigsMap[currentStep.id]?.last_test_latency_ms}ms)
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Filters & Search */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          {/* Provider Pills */}
          <div className="flex flex-wrap items-center gap-1.5 flex-1">
            <button
              onClick={() => setSelectedProviderFilter("all")}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                selectedProviderFilter === "all"
                  ? "bg-accent text-white"
                  : "bg-surface border border-border text-text-secondary hover:bg-surface-subtle"
              }`}
            >
              All Providers ({stepModels.length})
            </button>
            {availableProviders.map((prov) => (
              <button
                key={prov}
                onClick={() => setSelectedProviderFilter(prov)}
                className={`capitalize rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  selectedProviderFilter === prov
                    ? "bg-accent text-white"
                    : "bg-surface border border-border text-text-secondary hover:bg-surface-subtle"
                }`}
              >
                {prov}
              </button>
            ))}
          </div>

          {/* Search box */}
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-text-muted" />
            <input
              type="text"
              placeholder={`Search ${currentStep.shortTitle} models…`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface pl-9 pr-3 py-1.5 text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
          </div>
        </div>

        {/* Model Cards Grid */}
        {filteredModels.length === 0 ? (
          <EmptyState
            title="No matching models found"
            description="Try adjusting your search query or provider filter."
            action={
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  setSearchQuery("");
                  setSelectedProviderFilter("all");
                }}
              >
                Reset Filters
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredModels.map((model) => {
              const active = activeConfigsMap[currentStep.id];
              const cfg = configurations.find(
                (c) => c.provider_name === model.provider_name && c.model_id === model.model_id
              );
              return (
                <ModelConnectCard
                  key={model.id || `${model.provider_name}-${model.model_id}`}
                  model={model}
                  activeConfig={active}
                  hasConfig={Boolean(cfg)}
                  onConnect={handleOpenConnect}
                  onTest={(m, c) => {
                    handleOpenConnect(m);
                    handleRunTest(c.id);
                  }}
                />
              );
            })}
          </div>
        )}

        {/* Step Navigation Footer */}
        <div className="flex items-center justify-between border-t border-border pt-6 mt-8">
          <Button
            variant="secondary"
            disabled={currentStepIndex === 0}
            onClick={handlePrevStep}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" /> Previous Step
          </Button>

          <div className="flex items-center gap-3">
            {currentStepIndex < STEPS.length - 1 ? (
              <Button
                variant="primary"
                onClick={handleNextStep}
                className="gap-2 bg-[#E07038] hover:bg-[#C85D26] text-white"
              >
                Next Step ({STEPS[currentStepIndex + 1].shortTitle}) <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                variant="primary"
                onClick={() => {
                  toast.success("Voice Pipeline setup complete!");
                  window.location.href = "/admin/providers";
                }}
                className="gap-2 bg-success hover:bg-success/90 text-white"
              >
                <CheckCircle2 className="h-4 w-4" /> Finish & View Dashboard
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* ── Pipeline Readiness Card (When all 3 are active) ── */}
      {allComplete && (
        <Card className="border-success/40 bg-gradient-to-r from-success/5 via-surface to-accent/5">
          <CardBody className="p-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-success text-white">
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <h3 className="text-base font-bold text-text-primary">
                    AI Voice Pipeline is Fully Configured!
                  </h3>
                </div>
                <p className="text-xs text-text-secondary">
                  Your pipeline has active providers for STT ({activeConfigsMap.stt?.provider_name}),
                  LLM ({activeConfigsMap.llm?.provider_name}), and TTS ({activeConfigsMap.tts?.provider_name}).
                  Ready for live inbound/outbound telecalling.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  variant="primary"
                  size="sm"
                  className="bg-black hover:bg-neutral-800 text-white dark:bg-white dark:text-black gap-1.5 shadow-sm"
                  onClick={() => openTestAgent()}
                >
                  <Phone className="h-3.5 w-3.5 fill-current" /> Test Agent (Browser)
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => (window.location.href = "/admin/providers")}
                >
                  Manage Providers
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  className="bg-[#E07038] hover:bg-[#C85D26] text-white"
                  onClick={() => (window.location.href = "/dashboard")}
                >
                  Open Dashboard
                </Button>
              </div>
            </div>
          </CardBody>
        </Card>
      )}

      {/* ── Connect & Test Modal ── */}
      <Modal
        isOpen={connectModalOpen}
        onClose={() => setConnectModalOpen(false)}
        title={
          selectedModel
            ? `Configure & Test ${selectedModel.provider_name.toUpperCase()} (${selectedModel.model_id})`
            : "Configure Model"
        }
        size="lg"
      >
        {selectedModel && (
          <div className="space-y-5">
            {/* Model Summary Strip */}
            <div className="flex items-center justify-between rounded-xl bg-surface-subtle border border-border p-3 text-xs">
              <div>
                <span className="font-semibold text-text-primary capitalize">
                  {selectedModel.provider_name}
                </span>{" "}
                <span className="text-text-muted">/</span>{" "}
                <span className="font-mono text-accent font-medium">{selectedModel.model_id}</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={selectedModel.capability === "stt" ? "success" : selectedModel.capability === "tts" ? "accent" : "info"}>
                  {selectedModel.capability.toUpperCase()}
                </Badge>
                {selectedModel.doc_url && (
                  <a
                    href={selectedModel.doc_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-accent hover:underline"
                  >
                    <ExternalLink className="h-3 w-3" /> Docs
                  </a>
                )}
              </div>
            </div>

            {/* Credential Inputs */}
            {selectedModel.credential_requirements.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-text-primary">
                    API Key / Secret Credential{" "}
                    <span className="text-danger" aria-hidden>*</span>
                  </label>
                  <span className="text-[11px] text-text-muted">
                    Required: {selectedModel.credential_requirements.join(", ")}
                  </span>
                </div>

                {selectedModel.credential_requirements.includes("GOOGLE_APPLICATION_CREDENTIALS_JSON") ? (
                  <div>
                    <p className="text-[11px] text-text-muted mb-2">
                      Paste your Google Cloud Service Account JSON key (roles/speech.client).
                    </p>
                    <textarea
                      rows={5}
                      placeholder={`{\n  "type": "service_account",\n  "project_id": "...",\n  "private_key": "-----BEGIN PRIVATE KEY-----...",\n  "client_email": "..."\n}`}
                      value={apiKeyInput}
                      onChange={(e) => setApiKeyInput(e.target.value)}
                      className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-xs font-mono text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30 resize-y"
                    />
                  </div>
                ) : (
                  <div>
                    <input
                      type="password"
                      autoComplete="new-password"
                      placeholder={
                        selectedModel.provider_name === "sarvam"
                          ? "Paste SARVAM_API_KEY from dashboard.sarvam.ai"
                          : selectedModel.provider_name === "elevenlabs"
                          ? "Paste ELEVENLABS_API_KEY from elevenlabs.io"
                          : "Paste API Key"
                      }
                      value={apiKeyInput}
                      onChange={(e) => setApiKeyInput(e.target.value)}
                      className="w-full h-10 rounded-lg border border-border bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30 font-mono"
                    />
                    <p className="text-[11px] text-text-muted mt-1.5">
                      {selectedModel.setup_requirements || "Stored with military-grade Fernet AES encryption."}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Voice Selection (TTS Only) */}
            {selectedModel.capability === "tts" && (
              <div>
                <label className="block text-xs font-semibold text-text-primary mb-1.5">
                  Voice Selection
                </label>
                {VOICE_PRESETS[selectedModel.provider_name] && (
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {VOICE_PRESETS[selectedModel.provider_name].map((vp) => (
                      <button
                        key={vp.id}
                        type="button"
                        onClick={() => setVoiceInput(vp.id)}
                        className={`text-xs px-2.5 py-1 rounded-md border transition-colors ${
                          voiceInput === vp.id
                            ? "bg-accent text-white border-accent font-medium"
                            : "bg-surface-subtle text-text-secondary border-border hover:bg-surface"
                        }`}
                      >
                        {vp.label} ({vp.gender})
                      </button>
                    ))}
                  </div>
                )}
                <input
                  type="text"
                  placeholder="Voice ID (e.g. JBFqnCBsd6RMkjVDRZzb, kavya, etc.)"
                  value={voiceInput}
                  onChange={(e) => setVoiceInput(e.target.value)}
                  className="w-full h-9 rounded-lg border border-border bg-surface px-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 font-mono"
                />
              </div>
            )}

            {/* Language Selection */}
            {selectedModel.supported_languages?.length > 0 && (
              <div>
                <label className="block text-xs font-semibold text-text-primary mb-1.5">
                  Primary Language
                </label>
                <select
                  value={languageInput}
                  onChange={(e) => setLanguageInput(e.target.value)}
                  className="w-full h-9 rounded-lg border border-border bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
                >
                  <option value="">Default (Auto / Multilingual)</option>
                  {selectedModel.supported_languages.map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* LLM Model Parameters */}
            {selectedModel.capability === "llm" && (
              <div>
                <label className="block text-xs font-semibold text-text-primary mb-1">
                  Model Parameters (JSON, optional)
                </label>
                <textarea
                  rows={2}
                  placeholder='{"temperature": 0.7, "max_tokens": 512}'
                  value={extraParamsInput}
                  onChange={(e) => setExtraParamsInput(e.target.value)}
                  className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-accent/30 resize-none"
                />
              </div>
            )}

            {/* Fallback Checkbox */}
            <label className="flex items-center gap-2 text-xs text-text-secondary cursor-pointer">
              <input
                type="checkbox"
                checked={isFallback}
                onChange={(e) => setIsFallback(e.target.checked)}
                className="h-4 w-4 rounded border-border accent-accent"
              />
              Configure as Fallback provider (invoked if primary encounters error or rate limit)
            </label>

            {/* ── Test Execution Box ── */}
            {testResult && (
              <div
                className={`rounded-xl border p-4 text-xs transition-all ${
                  testResult.status === "ok"
                    ? "bg-[#EBF7F2] border-[#C0E8D5] text-success"
                    : "bg-[#FDEEEE] border-[#F2C0C0] text-danger"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {testResult.status === "ok" ? (
                      <CheckCircle2 className="h-4 w-4 shrink-0" />
                    ) : (
                      <AlertCircle className="h-4 w-4 shrink-0" />
                    )}
                    <span className="font-bold">
                      {testResult.status === "ok"
                        ? "Test Verification Succeeded!"
                        : "Test Execution Failed"}
                    </span>
                  </div>
                  {testResult.latency_ms != null && (
                    <span className="font-mono text-xs font-semibold bg-white/70 px-2 py-0.5 rounded">
                      ⚡ {testResult.latency_ms} ms
                    </span>
                  )}
                </div>

                {testResult.error && (
                  <div className="mt-2 text-xs font-mono text-danger/90 leading-relaxed bg-white/50 p-2.5 rounded-lg border border-danger/20 space-y-2">
                    <p>{testResult.error}</p>
                    {(() => {
                      const prov = selectedModel.provider_name.toLowerCase();
                      const isAuthError =
                        testResult.error.includes("403") ||
                        testResult.error.includes("401") ||
                        testResult.error.toLowerCase().includes("invalid_api_key") ||
                        testResult.error.toLowerCase().includes("authentication") ||
                        testResult.error.toLowerCase().includes("api key");

                      if (!isAuthError) return null;

                      if (prov === "sarvam") {
                        return (
                          <div className="text-[11px] font-sans text-amber-900 bg-amber-50 border border-amber-200 p-2 rounded-md">
                            💡 <strong>Sarvam Tip:</strong> Sarvam returns 403 when the API subscription key is invalid, expired, or has insufficient credits. Generate or copy your valid key from{" "}
                            <a
                              href="https://dashboard.sarvam.ai"
                              target="_blank"
                              rel="noopener noreferrer"
                              className="underline font-semibold text-accent hover:text-accent-hover"
                            >
                              dashboard.sarvam.ai
                            </a>
                            , paste it into the field above, and click <em>Re-Test Connection</em>.
                          </div>
                        );
                      }

                      if (prov === "gemini") {
                        return (
                          <div className="text-[11px] font-sans text-amber-900 bg-amber-50 border border-amber-200 p-2 rounded-md">
                            💡 <strong>Gemini Tip:</strong> Ensure you are using a valid Gemini API key. Generate or copy your key from{" "}
                            <a
                              href="https://aistudio.google.com/app/apikey"
                              target="_blank"
                              rel="noopener noreferrer"
                              className="underline font-semibold text-accent hover:text-accent-hover"
                            >
                              aistudio.google.com
                            </a>
                            , paste it into the field above, and click <em>Re-Test Connection</em>.
                          </div>
                        );
                      }

                      if (prov === "groq" || prov === "groq-whisper") {
                        return (
                          <div className="text-[11px] font-sans text-amber-900 bg-amber-50 border border-amber-200 p-2 rounded-md">
                            💡 <strong>Groq Tip:</strong> Generate or copy your free Groq API key from{" "}
                            <a
                              href="https://console.groq.com/keys"
                              target="_blank"
                              rel="noopener noreferrer"
                              className="underline font-semibold text-accent hover:text-accent-hover"
                            >
                              console.groq.com
                            </a>
                            , paste it into the field above, and click <em>Re-Test Connection</em>.
                          </div>
                        );
                      }

                      if (prov === "elevenlabs") {
                        return (
                          <div className="text-[11px] font-sans text-amber-900 bg-amber-50 border border-amber-200 p-2 rounded-md">
                            💡 <strong>ElevenLabs Tip:</strong> Copy your API key from{" "}
                            <a
                              href="https://elevenlabs.io"
                              target="_blank"
                              rel="noopener noreferrer"
                              className="underline font-semibold text-accent hover:text-accent-hover"
                            >
                              elevenlabs.io
                            </a>
                            , paste it into the field above, and click <em>Re-Test Connection</em>.
                          </div>
                        );
                      }

                      return null;
                    })()}
                  </div>
                )}

                {testAudioUrl && (
                  <div className="mt-3 flex items-center gap-2">
                    <span className="font-medium text-text-primary text-xs">Audio output sample:</span>
                    <audio controls src={testAudioUrl} className="h-7 w-64" />
                  </div>
                )}
              </div>
            )}

            {/* Modal Actions */}
            <div className="flex items-center justify-between border-t border-border pt-4">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setConnectModalOpen(false)}
                disabled={isConnecting || isTesting || isActivating}
              >
                Cancel
              </Button>

              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  loading={isConnecting || isTesting}
                  onClick={handleSaveAndConnect}
                  className="gap-1.5"
                >
                  <RotateCw className="h-3.5 w-3.5" />
                  {connectedConfig ? "Re-Test Connection" : "Save & Run Test"}
                </Button>

                {connectedConfig && (
                  <Button
                    variant="primary"
                    size="sm"
                    loading={isActivating}
                    onClick={() => handleActivate()}
                    className="gap-1.5 bg-[#E07038] hover:bg-[#C85D26] text-white"
                  >
                    <Check className="h-3.5 w-3.5" />
                    Activate as Primary
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
