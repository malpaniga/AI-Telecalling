"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  Plus,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  Trash2,
  Zap,
  ChevronDown,
  ChevronUp,
  KeyRound,
} from "lucide-react";
import toast from "react-hot-toast";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { Modal } from "@/components/ui/modal";
import {
  api,
  AIModelCatalogue,
  ProviderConfiguration,
  ProviderCredentialMeta,
  ConnectProviderRequest,
} from "@/lib/api";

const LANGUAGE_LABELS: Record<string, string> = {
  "mr-IN": "Marathi (mr-IN)",
  "hi-IN": "Hindi (hi-IN)",
  "en-IN": "English (en-IN)",
  "gu-IN": "Gujarati (gu-IN)",
  "ta-IN": "Tamil (ta-IN)",
  "te-IN": "Telugu (te-IN)",
  "kn-IN": "Kannada (kn-IN)",
  "ml-IN": "Malayalam (ml-IN)",
  "pa-IN": "Punjabi (pa-IN)",
  "bn-IN": "Bengali (bn-IN)",
  "od-IN": "Odia (od-IN)",
  "mr": "Marathi (mr)",
  "hi": "Hindi (hi)",
  "en": "English (en)",
  "gu": "Gujarati (gu)",
  "ta": "Tamil (ta)",
  "te": "Telugu (te)",
  "kn": "Kannada (kn)",
  "ml": "Malayalam (ml)",
  "pa": "Punjabi (pa)",
  "bn": "Bengali (bn)",
  "multilingual": "Multilingual (All Languages)",
};

function formatLanguageLabel(code: string): string {
  return LANGUAGE_LABELS[code] || code;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ProviderConfigPanelProps {
  capability: "tts" | "stt" | "llm";
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function configStatus(config: ProviderConfiguration): {
  label: string;
  variant: "success" | "info" | "warning" | "default";
} {
  if (config.is_active)
    return { label: "Active", variant: "success" };
  if (config.last_test_result === "ok")
    return { label: "Tested", variant: "info" };
  if (config.last_tested_at)
    return { label: "Test Failed", variant: "warning" };
  return { label: "Configured", variant: "default" };
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function truncate(s: string, n = 20): string {
  return s.length > n ? s.slice(0, n) + "…" : s;
}

// ---------------------------------------------------------------------------
// ProviderConfigPanel
// ---------------------------------------------------------------------------

export function ProviderConfigPanel({ capability }: ProviderConfigPanelProps) {
  // ── state ──
  const [configs, setConfigs] = useState<ProviderConfiguration[]>([]);
  const [credentials, setCredentials] = useState<
    Record<string, ProviderCredentialMeta[]>
  >({});
  const [catalogue, setCatalogue] = useState<AIModelCatalogue[]>([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState<Record<string, boolean>>({});
  const [testResults, setTestResults] = useState<
    Record<string, { ok: boolean; latency?: number | null; error?: string | null }>
  >({});
  const [activating, setActivating] = useState<Record<string, boolean>>({});
  const [deleting, setDeleting] = useState<Record<string, boolean>>({});

  // Connect modal
  const [showConnect, setShowConnect] = useState(false);
  const [selectedModel, setSelectedModel] = useState<AIModelCatalogue | null>(
    null
  );
  const [liveModels, setLiveModels] = useState<string[]>([]);
  const [loadingLiveModels, setLoadingLiveModels] = useState(false);
  const [customModelId, setCustomModelId] = useState("");
  const [isCustomModel, setIsCustomModel] = useState(false);
  const [connectForm, setConnectForm] = useState({
    credential_plaintext: "",
    voice: "",
    language: "",
    extra_params_json: "",
    is_fallback: false,
  });
  const [connectError, setConnectError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  // Credentials collapsible
  const [credOpen, setCredOpen] = useState(false);
  const [rotatingProvider, setRotatingProvider] = useState<string | null>(null);
  const [rotateValue, setRotateValue] = useState("");
  const [rotateError, setRotateError] = useState<string | null>(null);
  const [rotateSaving, setRotateSaving] = useState(false);
  const [deletingCred, setDeletingCred] = useState<string | null>(null);

  // ── load ──
  const load = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true);
      try {
        const [cfgs, cat] = await Promise.all([
          api.modelDirectory.listConfigs(capability),
          api.modelDirectory.catalogue({ capability }),
        ]);
        setConfigs(cfgs ?? []);
        setCatalogue(cat ?? []);

        // Load credentials for every distinct provider in configs
        const providers = [
          ...new Set((cfgs ?? []).map((c) => c.provider_name)),
        ];
        const credMap: Record<string, ProviderCredentialMeta[]> = {};
        await Promise.all(
          providers.map(async (p) => {
            try {
              const meta = await api.modelDirectory.listCredentials(p);
              credMap[p] = meta ?? [];
            } catch {
              credMap[p] = [];
            }
          })
        );
        setCredentials(credMap);
      } catch (e: unknown) {
        toast.error(
          e instanceof Error ? e.message : "Failed to load configurations"
        );
      } finally {
        setLoading(false);
      }
    },
    [capability]
  );

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (selectedModel?.provider_name) {
      setLoadingLiveModels(true);
      api.modelDirectory
        .listLiveModels(selectedModel.provider_name)
        .then((mList) => {
          setLiveModels(mList || []);
        })
        .catch(() => {
          setLiveModels([]);
        })
        .finally(() => {
          setLoadingLiveModels(false);
        });
    } else {
      setLiveModels([]);
    }
  }, [selectedModel?.provider_name]);

  // ── active / fallback ──
  const activeConfig = configs.find((c) => c.is_active);
  const fallbackConfig = configs.find((c) => c.is_fallback && !c.is_active);

  // ── test ──
  const handleTest = async (configId: string) => {
    setTesting((prev) => ({ ...prev, [configId]: true }));
    setTestResults((prev) => ({ ...prev, [configId]: { ok: false } }));
    try {
      const result = await api.modelDirectory.testConfig(configId);
      if (result.status === "ok") {
        setTestResults((prev) => ({
          ...prev,
          [configId]: { ok: true, latency: result.latency_ms },
        }));
        toast.success(`Test passed (${result.latency_ms ?? "?"}ms)`);
      } else {
        setTestResults((prev) => ({
          ...prev,
          [configId]: { ok: false, error: result.error },
        }));
        toast.error(`Test failed: ${result.error ?? "Unknown error"}`);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Test failed";
      setTestResults((prev) => ({
        ...prev,
        [configId]: { ok: false, error: msg },
      }));
      toast.error(msg);
    } finally {
      setTesting((prev) => ({ ...prev, [configId]: false }));
      await load(true);
    }
  };

  // ── activate ──
  const handleActivate = async (configId: string) => {
    if (
      !window.confirm(
        "Activate this configuration? This will update the live routing for all calls."
      )
    )
      return;
    setActivating((prev) => ({ ...prev, [configId]: true }));
    try {
      await api.modelDirectory.activateConfig(configId);
      toast.success("Configuration activated");
      await load(true);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Activation failed");
    } finally {
      setActivating((prev) => ({ ...prev, [configId]: false }));
    }
  };

  // ── delete config ──
  const handleDeleteConfig = async (configId: string) => {
    if (
      !window.confirm(
        "Delete this configuration? This cannot be undone."
      )
    )
      return;
    setDeleting((prev) => ({ ...prev, [configId]: true }));
    try {
      await api.modelDirectory.deleteConfig(configId);
      toast.success("Configuration deleted");
      await load(true);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleting((prev) => ({ ...prev, [configId]: false }));
    }
  };

  // ── connect modal ──
  const openConnect = () => {
    setSelectedModel(null);
    setLiveModels([]);
    setIsCustomModel(false);
    setCustomModelId("");
    setConnectForm({
      credential_plaintext: "",
      voice: "",
      language: "",
      extra_params_json: "",
      is_fallback: false,
    });
    setConnectError(null);
    setShowConnect(true);
  };

  const handleConnect = async () => {
    if (!selectedModel) {
      setConnectError("Please select a model.");
      return;
    }
    const finalModelId = (isCustomModel ? customModelId.trim() : (customModelId || selectedModel.model_id)).trim();
    if (!finalModelId) {
      setConnectError("Please choose or enter a valid Model ID.");
      return;
    }

    const hasStoredCred = Boolean(credentials[selectedModel.provider_name]?.length);
    const isGoogleSTT =
      selectedModel.provider_name === "google-cloud-stt" ||
      selectedModel.credential_requirements.includes(
        "GOOGLE_APPLICATION_CREDENTIALS_JSON"
      );

    if (
      selectedModel.credential_requirements.length > 0 &&
      !connectForm.credential_plaintext &&
      !hasStoredCred
    ) {
      setConnectError(
        isGoogleSTT
          ? "Service Account JSON is required for Google Cloud STT."
          : `API key required for ${selectedModel.provider_name}.`
      );
      return;
    }

    if (isGoogleSTT && connectForm.credential_plaintext) {
      try {
        const parsed = JSON.parse(connectForm.credential_plaintext.trim());
        if (
          typeof parsed !== "object" ||
          parsed === null ||
          (parsed.type && parsed.type !== "service_account")
        ) {
          setConnectError(
            'Google Cloud STT requires a valid Service Account JSON key (must contain \'"type": "service_account"\'). API keys are not supported.'
          );
          return;
        }
      } catch {
        setConnectError(
          "Invalid JSON format. Please paste the full contents of your Google Cloud Service Account .json key file."
        );
        return;
      }
    }

    // Validate extra_params JSON for LLM
    let extra_params: Record<string, unknown> | undefined;
    if (capability === "llm" && connectForm.extra_params_json.trim()) {
      try {
        extra_params = JSON.parse(connectForm.extra_params_json);
      } catch {
        setConnectError(
          "Extra parameters must be valid JSON."
        );
        return;
      }
    }

    setConnecting(true);
    setConnectError(null);
    try {
      const body: ConnectProviderRequest = {
        provider_name: selectedModel.provider_name,
        model_id: finalModelId,
        capability,
        is_fallback: connectForm.is_fallback,
      };
      if (connectForm.credential_plaintext)
        body.credential_plaintext = connectForm.credential_plaintext;
      if (connectForm.voice) body.voice = connectForm.voice;
      if (connectForm.language) body.language = connectForm.language;
      if (extra_params) body.extra_params = extra_params;

      await api.modelDirectory.connect(body);
      toast.success("Provider connected successfully");
      setShowConnect(false);
      await load(true);
    } catch (e: unknown) {
      setConnectError(
        e instanceof Error ? e.message : "Connection failed"
      );
    } finally {
      setConnecting(false);
    }
  };

  // ── credential rotate ──
  const handleRotate = async (providerName: string) => {
    const isGoogleSTT = providerName === "google-cloud-stt";
    if (!rotateValue) {
      setRotateError(
        isGoogleSTT
          ? "Service Account JSON is required."
          : "New API key is required."
      );
      return;
    }

    if (isGoogleSTT) {
      try {
        const parsed = JSON.parse(rotateValue.trim());
        if (
          typeof parsed !== "object" ||
          parsed === null ||
          (parsed.type && parsed.type !== "service_account")
        ) {
          setRotateError(
            'Google Cloud STT requires a valid Service Account JSON key (must contain \'"type": "service_account"\'). API keys are not supported.'
          );
          return;
        }
      } catch {
        setRotateError(
          "Invalid JSON format. Please paste the full contents of your Google Cloud Service Account .json key file."
        );
        return;
      }
    }
    setRotateSaving(true);
    setRotateError(null);
    try {
      await api.modelDirectory.rotateCredential(providerName, rotateValue);
      toast.success("Credential rotated");
      setRotatingProvider(null);
      setRotateValue("");
      await load(true);
    } catch (e: unknown) {
      setRotateError(
        e instanceof Error ? e.message : "Rotation failed"
      );
    } finally {
      setRotateSaving(false);
    }
  };

  // ── credential delete ──
  const handleDeleteCred = async (providerName: string) => {
    if (
      !window.confirm(
        `Delete stored credentials for ${providerName}? This will break any configuration using this provider.`
      )
    )
      return;
    setDeletingCred(providerName);
    try {
      await api.modelDirectory.deleteCredential(providerName);
      toast.success("Credential deleted");
      await load(true);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeletingCred(null);
    }
  };

  // ── render ──
  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  const credProviders = Object.keys(credentials);
  const catalogueOptions = catalogue.filter(
    (m) => m.implementation_status !== "unavailable"
  );

  // Determine whether a row's test result is "ok" (either from fresh test or existing db value)
  const isTestOk = (config: ProviderConfiguration): boolean => {
    const fresh = testResults[config.id];
    if (fresh !== undefined) return fresh.ok;
    return config.last_test_result === "ok";
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardBody className="py-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-text-primary">{capability.toUpperCase()} setup path</p>
              <p className="mt-0.5 text-xs text-text-secondary">A telecalling agent needs one tested, active cloud provider for this capability.</p>
            </div>
            <div className="flex items-center gap-2 text-xs">
              {[
                ["1", "Connect", configs.length > 0],
                ["2", "Test", configs.some((config) => config.last_test_result === "ok")],
                ["3", "Activate", Boolean(activeConfig)],
              ].map(([step, label, complete]) => (
                <React.Fragment key={label as string}>
                  <span className={`inline-flex items-center gap-1.5 ${complete ? "text-success" : "text-text-muted"}`}>
                    <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold ${complete ? "bg-[#EBF7F2]" : "bg-surface-subtle"}`}>{complete ? "✓" : step}</span>
                    {label}
                  </span>
                  {label !== "Activate" && <span className="h-px w-4 bg-border" />}
                </React.Fragment>
              ))}
            </div>
          </div>
        </CardBody>
      </Card>

      {/* ── Active Configuration ── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-text-primary">
              Active Configuration
            </h3>
            <Button size="sm" variant="secondary" onClick={() => load(true)}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardBody>
          {!activeConfig ? (
            <EmptyState
              title="No active provider"
              description="Connect and activate a provider to enable this capability."
            />
          ) : (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
                <div>
                  <p className="text-xs text-text-muted">Provider</p>
                  <p className="font-medium text-text-primary">
                    {activeConfig.provider_name}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Model</p>
                  <p className="font-medium text-text-primary font-mono">
                    {activeConfig.model_id}
                  </p>
                </div>
                {activeConfig.voice && (
                  <div>
                    <p className="text-xs text-text-muted">Voice</p>
                    <p className="text-text-primary">{activeConfig.voice}</p>
                  </div>
                )}
                {activeConfig.language && (
                  <div>
                    <p className="text-xs text-text-muted">Language</p>
                    <p className="text-text-primary">
                      {activeConfig.language}
                    </p>
                  </div>
                )}
                <div>
                  <p className="text-xs text-text-muted">Last Test</p>
                  <div className="flex items-center gap-1">
                    {activeConfig.last_test_result === "ok" ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                    ) : activeConfig.last_test_result === "error" ? (
                      <XCircle className="h-3.5 w-3.5 text-danger" />
                    ) : null}
                    <span className="text-text-primary">
                      {activeConfig.last_test_result === "ok"
                        ? `OK (${activeConfig.last_test_latency_ms ?? "?"}ms)`
                        : activeConfig.last_test_result === "error"
                          ? "Failed"
                          : "—"}
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Activated</p>
                  <p className="text-text-primary">
                    {formatDate(activeConfig.activated_at)}
                  </p>
                </div>
              </div>

              {/* Fallback */}
              {fallbackConfig && (
                <div className="mt-3 rounded-md border border-border bg-surface-subtle px-4 py-2 text-xs text-text-secondary">
                  <span className="font-medium text-text-primary">
                    Fallback:{" "}
                  </span>
                  {fallbackConfig.provider_name} / {fallbackConfig.model_id}
                </div>
              )}
            </div>
          )}
        </CardBody>
      </Card>

      {/* ── Available Configurations ── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-text-primary">
              Available Configurations
            </h3>
            <Button size="sm" variant="primary" onClick={openConnect}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              Add Configuration
            </Button>
          </div>
        </CardHeader>
        <CardBody className="p-0">
          {configs.length === 0 ? (
            <div className="px-6 py-4">
              <EmptyState
                title="No configurations yet"
                description="Add a provider configuration to get started."
              />
            </div>
          ) : (
            <SimpleTable
              headers={[
                "Provider",
                "Model",
                "Status",
                "Last Tested",
                "Actions",
              ]}
            >
              {configs.map((config) => {
                const st = configStatus(config);
                const isTesting = testing[config.id] ?? false;
                const isActivating = activating[config.id] ?? false;
                const isDeleting = deleting[config.id] ?? false;
                const freshResult = testResults[config.id];
                const testOk = isTestOk(config);

                return (
                  <TableRow key={config.id}>
                    <TableCell className="font-medium">
                      {config.provider_name}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {truncate(config.model_id, 28)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={st.variant}>{st.label}</Badge>
                    </TableCell>
                    <TableCell className="text-text-secondary text-xs">
                      {formatDate(config.last_tested_at)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2 flex-wrap">
                        {/* Test button */}
                        <button
                          onClick={() => handleTest(config.id)}
                          disabled={isTesting}
                          className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-text-primary hover:bg-surface-subtle disabled:opacity-50 transition-colors"
                          title="Run test inference"
                        >
                          {isTesting ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : freshResult?.ok === true ? (
                            <CheckCircle2 className="h-3 w-3 text-success" />
                          ) : freshResult?.ok === false ? (
                            <XCircle className="h-3 w-3 text-danger" />
                          ) : null}
                          Test
                          {freshResult?.ok === true && freshResult.latency != null && (
                            <span className="text-success ml-0.5">
                              {freshResult.latency}ms
                            </span>
                          )}
                          {freshResult?.ok === false && freshResult.error && (
                            <span
                              className="text-danger ml-0.5 max-w-[8rem] truncate"
                              title={freshResult.error}
                            >
                              {truncate(freshResult.error, 20)}
                            </span>
                          )}
                        </button>

                        {/* Activate button */}
                        {!config.is_active && (
                          <button
                            onClick={() => handleActivate(config.id)}
                            disabled={!testOk || isActivating}
                            className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-text-primary hover:bg-surface-subtle disabled:opacity-50 transition-colors"
                            title={
                              !testOk
                                ? "Run a successful test before activating"
                                : "Activate this configuration"
                            }
                          >
                            {isActivating ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <Zap className="h-3 w-3" />
                            )}
                            Activate
                          </button>
                        )}
                        {config.is_active && (
                          <Badge variant="success">Active</Badge>
                        )}

                        {/* Delete button */}
                        <button
                          onClick={() => handleDeleteConfig(config.id)}
                          disabled={isDeleting || config.is_active}
                          className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1 text-xs font-medium text-danger hover:bg-[#FDEEEE] disabled:opacity-50 transition-colors"
                          title={
                            config.is_active
                              ? "Cannot delete active configuration"
                              : "Delete configuration"
                          }
                        >
                          {isDeleting ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Trash2 className="h-3 w-3" />
                          )}
                          Delete
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </SimpleTable>
          )}
        </CardBody>
      </Card>

      {/* ── Credentials (collapsible) ── */}
      {credProviders.length > 0 && (
        <Card>
          <CardHeader>
            <button
              className="flex w-full items-center justify-between"
              onClick={() => setCredOpen((v) => !v)}
              aria-expanded={credOpen}
            >
              <div className="flex items-center gap-2">
                <KeyRound className="h-4 w-4 text-text-muted" />
                <h3 className="text-sm font-medium text-text-primary">
                  Stored Credentials
                </h3>
              </div>
              {credOpen ? (
                <ChevronUp className="h-4 w-4 text-text-muted" />
              ) : (
                <ChevronDown className="h-4 w-4 text-text-muted" />
              )}
            </button>
          </CardHeader>
          {credOpen && (
            <CardBody>
              <div className="space-y-4">
                {credProviders.map((provName) => {
                  const metas = credentials[provName] ?? [];
                  const isRotating = rotatingProvider === provName;
                  const isDelCred = deletingCred === provName;

                  return (
                    <div
                      key={provName}
                      className="rounded-md border border-border p-4 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-text-primary">
                          {provName}
                        </p>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => {
                              setRotatingProvider(
                                isRotating ? null : provName
                              );
                              setRotateValue("");
                              setRotateError(null);
                            }}
                          >
                            Rotate
                          </Button>
                          <Button
                            size="sm"
                            variant="danger"
                            loading={isDelCred}
                            onClick={() => handleDeleteCred(provName)}
                          >
                            <Trash2 className="h-3 w-3 mr-1" />
                            Delete
                          </Button>
                        </div>
                      </div>

                      {metas.map((meta, idx) => (
                        <div
                          key={idx}
                          className="text-xs text-text-secondary flex flex-wrap gap-x-4 gap-y-1"
                        >
                          <span>
                            Key:{" "}
                            <span className="font-mono text-text-primary">
                              {meta.key_hint ?? "••••"}
                            </span>
                          </span>
                          {meta.created_at && (
                            <span>Added: {formatDate(meta.created_at)}</span>
                          )}
                          {meta.rotated_at && (
                            <span>Rotated: {formatDate(meta.rotated_at)}</span>
                          )}
                        </div>
                      ))}

                      {isRotating && (
                        <div className="mt-2 space-y-2">
                          {provName === "google-cloud-stt" ? (
                            <div>
                              <p className="text-xs text-text-muted mb-1.5">
                                Paste the contents of your Google Cloud Service Account JSON key (roles/speech.client):
                              </p>
                              <textarea
                                rows={5}
                                placeholder={`{\n  "type": "service_account",\n  "project_id": "...",\n  "private_key": "..."\n}`}
                                value={rotateValue}
                                onChange={(e) => setRotateValue(e.target.value)}
                                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-xs font-mono text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30 resize-y"
                              />
                            </div>
                          ) : (
                            <input
                              type="password"
                              autoComplete="new-password"
                              placeholder="New API key"
                              value={rotateValue}
                              onChange={(e) => setRotateValue(e.target.value)}
                              className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
                            />
                          )}
                          {rotateError && (
                            <p className="text-xs text-danger">{rotateError}</p>
                          )}
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="primary"
                              loading={rotateSaving}
                              onClick={() => handleRotate(provName)}
                            >
                              Save New Key
                            </Button>
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => {
                                setRotatingProvider(null);
                                setRotateValue("");
                                setRotateError(null);
                              }}
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardBody>
          )}
        </Card>
      )}

      {/* ── Connect Modal ── */}
      <Modal
        isOpen={showConnect}
        onClose={() => setShowConnect(false)}
        title={`Connect ${capability.toUpperCase()} provider — Step 1 of 3`}
        size="md"
      >
        <div className="space-y-4">
          {/* Model selector */}
          <div>
            <label className="block text-xs font-medium text-text-primary mb-1">
              Provider & Catalogue Model{" "}
              <span className="text-danger" aria-hidden>
                *
              </span>
            </label>
            <select
              value={selectedModel?.id ?? ""}
              onChange={(e) => {
                const found = catalogueOptions.find(
                  (m) => m.id === e.target.value
                );
                setSelectedModel(found ?? null);
                setIsCustomModel(false);
                setCustomModelId(found?.model_id ?? "");
                setConnectForm((f) => ({ ...f, language: "", voice: "" }));
              }}
              className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
            >
              <option value="">Select a provider / model from catalogue…</option>
              {catalogueOptions.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.provider_name.toUpperCase()} — {m.model_id}{" "}
                  {m.implementation_status === "experimental"
                    ? "(experimental)"
                    : ""}
                </option>
              ))}
            </select>
          </div>

          {/* Model Variant Selector / Live models / Custom */}
          {selectedModel && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-medium text-text-primary">
                  Specific Model Variant / ID{" "}
                  <span className="text-danger" aria-hidden>*</span>
                </label>
                <button
                  type="button"
                  onClick={() => setIsCustomModel(!isCustomModel)}
                  className="text-[11px] text-accent hover:underline"
                >
                  {isCustomModel ? "Choose from available list" : "+ Enter custom model ID"}
                </button>
              </div>

              {isCustomModel ? (
                <input
                  type="text"
                  placeholder="e.g. openai/gpt-oss-20b or custom identifier"
                  value={customModelId}
                  onChange={(e) => setCustomModelId(e.target.value)}
                  className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm font-mono text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
                />
              ) : (
                <div className="relative">
                  <select
                    value={customModelId || selectedModel.model_id}
                    onChange={(e) => {
                      if (e.target.value === "__custom__") {
                        setIsCustomModel(true);
                        setCustomModelId("");
                      } else {
                        setCustomModelId(e.target.value);
                      }
                    }}
                    className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm font-mono text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
                  >
                    {Array.from(new Set([selectedModel.model_id, ...liveModels])).map((mId) => (
                      <option key={mId} value={mId}>
                        {mId} {mId === selectedModel.model_id ? "(template default)" : ""}
                      </option>
                    ))}
                    <option value="__custom__">+ Enter custom model ID…</option>
                  </select>
                  {loadingLiveModels && (
                    <span className="absolute right-8 top-2.5 text-[10px] text-text-muted">
                      fetching live models…
                    </span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* API key / Service Account JSON — only when credentials required */}
          {selectedModel && selectedModel.credential_requirements.length > 0 && (
            <div>
              {selectedModel.provider_name === "google-cloud-stt" ||
              selectedModel.credential_requirements.includes(
                "GOOGLE_APPLICATION_CREDENTIALS_JSON"
              ) ? (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-xs font-medium text-text-primary">
                      Service Account JSON Key{" "}
                      {!Boolean(credentials[selectedModel.provider_name]?.length) && (
                        <span className="text-danger" aria-hidden>*</span>
                      )}
                    </label>
                    <span className="text-[11px] text-accent font-medium">
                      roles/speech.client
                    </span>
                  </div>
                  {Boolean(credentials[selectedModel.provider_name]?.length) && (
                    <div className="mb-1.5 flex items-center gap-1.5 rounded bg-success/10 px-2 py-1 text-[11px] text-success">
                      <CheckCircle2 className="h-3 w-3 shrink-0" />
                      <span>Stored service account active. Optional: paste new key to rotate.</span>
                    </div>
                  )}
                  <p className="text-[11px] text-text-muted mb-1.5 leading-relaxed">
                    Google Cloud Speech-to-Text requires a Service Account JSON key file. API keys are not supported by the Google Cloud Speech API.
                  </p>
                  <textarea
                    rows={5}
                    placeholder={`{\n  "type": "service_account",\n  "project_id": "your-project-id",\n  "private_key": "-----BEGIN PRIVATE KEY-----...",\n  "client_email": "...@...iam.gserviceaccount.com"\n}`}
                    value={connectForm.credential_plaintext}
                    onChange={(e) =>
                      setConnectForm((f) => ({
                        ...f,
                        credential_plaintext: e.target.value,
                      }))
                    }
                    className="w-full rounded-md border border-border bg-surface px-3 py-2 text-xs font-mono text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30 resize-y"
                  />
                </div>
              ) : (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-xs font-medium text-text-primary">
                      API Key{" "}
                      {!Boolean(credentials[selectedModel.provider_name]?.length) && (
                        <span className="text-danger" aria-hidden>*</span>
                      )}
                      <span className="ml-1 text-text-muted font-normal">
                        ({selectedModel.credential_requirements.join(", ")})
                      </span>
                    </label>
                    {Boolean(credentials[selectedModel.provider_name]?.length) && (
                      <span className="text-[11px] text-success font-medium flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3 inline" /> Stored key active ({credentials[selectedModel.provider_name]?.[0]?.key_hint || "••••"})
                      </span>
                    )}
                  </div>
                  <input
                    type="password"
                    autoComplete="new-password"
                    placeholder={
                      Boolean(credentials[selectedModel.provider_name]?.length)
                        ? "Optional: paste new key to update stored credential"
                        : "Paste your API key"
                    }
                    value={connectForm.credential_plaintext}
                    onChange={(e) =>
                      setConnectForm((f) => ({
                        ...f,
                        credential_plaintext: e.target.value,
                      }))
                    }
                    className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
                  />
                  {Boolean(credentials[selectedModel.provider_name]?.length) && !connectForm.credential_plaintext && (
                    <p className="text-[11px] text-text-muted mt-1">
                      Reusing existing encrypted credential for {selectedModel.provider_name}.
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Language selector */}
          {selectedModel &&
            selectedModel.supported_languages.length > 0 && (
              <div>
                <label className="block text-xs font-medium text-text-primary mb-1">
                  Language
                </label>
                <select
                  value={connectForm.language}
                  onChange={(e) =>
                    setConnectForm((f) => ({
                      ...f,
                      language: e.target.value,
                    }))
                  }
                  className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
                >
                  <option value="">Default / any</option>
                  {selectedModel.supported_languages.map((lang) => (
                    <option key={lang} value={lang}>
                      {formatLanguageLabel(lang)}
                    </option>
                  ))}
                </select>
              </div>
            )}

          {/* Voice selector — TTS only */}
          {capability === "tts" && selectedModel && (
            <div>
              <label className="block text-xs font-medium text-text-primary mb-1">
                Voice
              </label>
              <input
                type="text"
                placeholder="e.g. en-IN-female-1"
                value={connectForm.voice}
                onChange={(e) =>
                  setConnectForm((f) => ({ ...f, voice: e.target.value }))
                }
                className="w-full h-9 rounded-md border border-border bg-surface px-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
              />
            </div>
          )}

          {/* Extra params — LLM only */}
          {capability === "llm" && (
            <div>
              <label className="block text-xs font-medium text-text-primary mb-1">
                Model Parameters{" "}
                <span className="text-text-muted font-normal">
                  (JSON, optional — e.g. temperature, max_tokens)
                </span>
              </label>
              <textarea
                rows={3}
                placeholder={'{"temperature": 0.7, "max_tokens": 512}'}
                value={connectForm.extra_params_json}
                onChange={(e) =>
                  setConnectForm((f) => ({
                    ...f,
                    extra_params_json: e.target.value,
                  }))
                }
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-accent/30 resize-none"
              />
            </div>
          )}

          {/* Fallback toggle */}
          <label className="flex items-center gap-2 text-sm text-text-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={connectForm.is_fallback}
              onChange={(e) =>
                setConnectForm((f) => ({
                  ...f,
                  is_fallback: e.target.checked,
                }))
              }
              className="h-4 w-4 rounded border-border accent-accent"
            />
            Set as fallback provider
          </label>

          {/* Error */}
          {connectError && (
            <p className="rounded-md bg-[#FDEEEE] border border-[#F2C0C0] px-3 py-2 text-xs text-danger">
              {connectError}
            </p>
          )}

          {/* Actions */}
          <p className="text-xs text-text-muted">Next: run a safe test inference, then activate only after it passes.</p>
          <div className="flex justify-end gap-2 pt-1">
            <Button
              variant="secondary"
              onClick={() => setShowConnect(false)}
              disabled={connecting}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              loading={connecting}
              onClick={handleConnect}
            >
              Connect
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
