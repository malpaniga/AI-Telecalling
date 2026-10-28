"use client";

import React, { useState, useRef } from "react";
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Info,
  Bot,
  Volume2,
  Sparkles,
} from "lucide-react";
import toast from "react-hot-toast";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { api, Agent, VoiceProfile, AgentExportPackage } from "@/lib/api";

interface ImportAgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  voiceProfiles: VoiceProfile[];
  onImportSuccess?: (newAgent: Agent) => void;
}

export function ImportAgentModal({
  isOpen,
  onClose,
  voiceProfiles,
  onImportSuccess,
}: ImportAgentModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [exportPkg, setExportPkg] = useState<AgentExportPackage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [agentName, setAgentName] = useState("");
  const [description, setDescription] = useState("");
  const [voiceProfileId, setVoiceProfileId] = useState("");
  const [importing, setImporting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function resetState() {
    setFile(null);
    setExportPkg(null);
    setError(null);
    setAgentName("");
    setDescription("");
    setVoiceProfileId("");
    setImporting(false);
  }

  function handleClose() {
    resetState();
    onClose();
  }

  function processFile(selectedFile: File) {
    setError(null);
    if (!selectedFile.name.endsWith(".json")) {
      setError("Please select a valid JSON export file (.agent.json or .json).");
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        const parsed = JSON.parse(text);

        if (parsed.format !== "sarvam_agent_export_v1" || !parsed.agent) {
          setError(
            'Invalid file format. Expected a Sarvam Agent export file with "format": "sarvam_agent_export_v1".'
          );
          setExportPkg(null);
          return;
        }

        const pkg = parsed as AgentExportPackage;
        setFile(selectedFile);
        setExportPkg(pkg);
        setAgentName(pkg.agent.name ? `${pkg.agent.name} (Imported)` : "Imported Agent");
        setDescription(pkg.agent.description || "");

        // Auto-match voice profile by language if possible
        const targetLang =
          pkg.agent.configuration?.primary_language ||
          pkg.agent.voice_profile?.language ||
          "";
        const matchingProfile = voiceProfiles.find(
          (p) => p.language.toLowerCase() === targetLang.toLowerCase()
        );

        if (matchingProfile) {
          setVoiceProfileId(matchingProfile.id);
        } else if (voiceProfiles.length > 0) {
          setVoiceProfileId(voiceProfiles[0].id);
        }
      } catch (err: unknown) {
        setError(
          `Failed to parse JSON file: ${err instanceof Error ? err.message : "Invalid JSON syntax"}`
        );
        setExportPkg(null);
      }
    };
    reader.onerror = () => {
      setError("Error reading the selected file.");
    };
    reader.readAsText(selectedFile);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  }

  async function handleImport() {
    if (!exportPkg || !agentName.trim()) {
      toast.error("Please provide a valid agent name.");
      return;
    }

    setImporting(true);
    try {
      const newAgent = await api.agents.import({
        name: agentName.trim(),
        description: description.trim(),
        template_slug: exportPkg.agent.template_slug || "generic",
        voice_profile_id: voiceProfileId || undefined,
        configuration: exportPkg.agent.configuration,
      });

      toast.success(`Agent "${newAgent.name}" imported successfully!`);
      handleClose();
      if (onImportSuccess) {
        onImportSuccess(newAgent);
      }
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Failed to import agent. Please try again."
      );
    } finally {
      setImporting(false);
    }
  }

  // Previews
  const cfg = exportPkg?.agent.configuration;
  const inputVars = cfg?.input_variables
    ? Object.keys(cfg.input_variables as Record<string, unknown>)
    : [];
  const outputVars = Array.isArray(cfg?.output_variables)
    ? cfg.output_variables
    : [];
  const tools = Array.isArray(cfg?.tools) ? cfg.tools : [];

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Import AI Calling Agent"
      size="lg"
    >
      <div className="p-6 space-y-6">
        {/* Upload Dropzone */}
        {!exportPkg ? (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`cursor-pointer border-2 border-dashed rounded-xl p-8 text-center transition-all ${
              dragOver
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50 bg-secondary/20 hover:bg-secondary/40"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,.agent.json"
              className="hidden"
              onChange={handleFileChange}
            />
            <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto mb-3">
              <Upload className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-semibold text-text-primary">
              Choose an agent file or drag it here
            </h3>
            <p className="text-xs text-text-muted mt-1">
              Upload an exported <code className="text-primary font-mono">.agent.json</code> file
            </p>
          </div>
        ) : (
          <div className="flex items-center justify-between p-3.5 bg-secondary/30 rounded-lg border border-border">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-semibold text-text-primary">
                  {file?.name || "Agent Export Package"}
                </p>
                <p className="text-[11px] text-text-muted">
                  Exported at:{" "}
                  {exportPkg.exported_at
                    ? new Date(exportPkg.exported_at).toLocaleString()
                    : "Unknown date"}
                </p>
              </div>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setExportPkg(null);
                setFile(null);
              }}
              className="text-xs"
            >
              Change File
            </Button>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="flex items-start gap-2.5 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Configuration preview & overrides */}
        {exportPkg && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Agent Name"
                required
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                placeholder="e.g. Inbound Support Representative"
              />

              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  Voice Profile for Calling
                </label>
                <select
                  value={voiceProfileId}
                  onChange={(e) => setVoiceProfileId(e.target.value)}
                  className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                >
                  {voiceProfiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.display_name} ({p.language}) {p.is_platform ? "• Platform" : ""}
                    </option>
                  ))}
                  {voiceProfiles.length === 0 && (
                    <option value="">No voice profiles found (default will be used)</option>
                  )}
                </select>
                {exportPkg.agent.voice_profile && (
                  <p className="text-[11px] text-text-muted mt-1 flex items-center gap-1">
                    <Volume2 className="w-3 h-3 text-primary" />
                    Original export voice: {exportPkg.agent.voice_profile.display_name} (
                    {exportPkg.agent.voice_profile.language})
                  </p>
                )}
              </div>
            </div>

            <Input
              label="Description (Optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief summary of this agent's purpose"
            />

            {/* Inspection / Preview Box */}
            <div className="rounded-lg border border-border bg-card/60 p-4 space-y-3">
              <h4 className="text-xs font-semibold text-text-primary flex items-center gap-1.5 uppercase tracking-wider">
                <Sparkles className="w-3.5 h-3.5 text-primary" />
                Import Configuration Summary
              </h4>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                <div className="p-2 rounded bg-surface/80 border border-border/40">
                  <span className="text-[10px] text-text-muted block">Language</span>
                  <span className="font-semibold text-text-primary">
                    {cfg?.primary_language || "en-IN"}
                  </span>
                </div>
                <div className="p-2 rounded bg-surface/80 border border-border/40">
                  <span className="text-[10px] text-text-muted block">Template Base</span>
                  <span className="font-semibold text-text-primary">
                    {exportPkg.agent.template_slug || "generic"}
                  </span>
                </div>
                <div className="p-2 rounded bg-surface/80 border border-border/40">
                  <span className="text-[10px] text-text-muted block">Variables</span>
                  <span className="font-semibold text-text-primary">
                    {inputVars.length} in / {outputVars.length} out
                  </span>
                </div>
                <div className="p-2 rounded bg-surface/80 border border-border/40">
                  <span className="text-[10px] text-text-muted block">Tools</span>
                  <span className="font-semibold text-text-primary">
                    {tools.length} configured
                  </span>
                </div>
              </div>

              {cfg?.greeting && (
                <div>
                  <span className="text-[11px] font-medium text-text-secondary block mb-1">
                    Greeting:
                  </span>
                  <p className="text-xs bg-surface/80 p-2.5 rounded border border-border/40 text-text-primary italic line-clamp-2">
                    &ldquo;{String(cfg.greeting)}&rdquo;
                  </p>
                </div>
              )}

              {cfg?.instructions && (
                <div>
                  <span className="text-[11px] font-medium text-text-secondary block mb-1">
                    System Instructions Snippet:
                  </span>
                  <pre className="text-[11px] font-mono bg-surface/80 p-2.5 rounded border border-border/40 text-text-secondary whitespace-pre-wrap max-h-24 overflow-y-auto">
                    {String(cfg.instructions).slice(0, 400)}
                    {String(cfg.instructions).length > 400 ? "..." : ""}
                  </pre>
                </div>
              )}

              <div className="flex items-start gap-2 p-2.5 bg-amber-500/10 border border-amber-500/20 rounded text-amber-300 text-[11px]">
                <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                <span>
                  <strong>Knowledge Bases:</strong> Exported separately per system policy. If
                  this agent relies on knowledge bases, export them from the source organization,
                  import them via the Knowledge page, and associate them in Agent Studio.
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
          <Button variant="secondary" onClick={handleClose} disabled={importing}>
            Cancel
          </Button>
          <Button
            onClick={handleImport}
            disabled={!exportPkg || !agentName.trim() || importing}
            loading={importing}
            className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold"
          >
            <CheckCircle2 className="w-4 h-4 mr-1.5" />
            Import Agent
          </Button>
        </div>
      </div>
    </Modal>
  );
}
