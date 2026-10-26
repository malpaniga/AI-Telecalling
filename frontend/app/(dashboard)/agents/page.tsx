"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  Bot,
  Plus,
  Sparkles,
  Search,
  ArrowRight,
  Clock,
  UserCheck,
  CheckCircle2,
  Trash2,
  Filter,
  Wand2,
} from "lucide-react";
import toast from "react-hot-toast";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Modal } from "@/components/ui/modal";
import { Input, Select } from "@/components/ui/input";
import { api, Agent, VoiceProfile } from "@/lib/api";
import {
  SARVAM_CATALOG,
  TEMPLATE_CATEGORIES,
  MarketplaceTemplate,
} from "@/lib/template-catalog";
import Link from "next/link";

export default function AgentsPage() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [voiceProfiles, setVoiceProfiles] = useState<VoiceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showGenieModal, setShowGenieModal] = useState(false);
  const [geniePrompt, setGeniePrompt] = useState("");
  const [genieLoading, setGenieLoading] = useState(false);

  // Filter state for marketplace
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Create form state
  const [scratchForm, setScratchForm] = useState({
    name: "",
    template_slug: "generic" as const,
    voice_profile_id: "",
    description: "",
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [agentsList, profiles] = await Promise.all([
        api.agents.list(),
        api.voiceProfiles.list(),
      ]);
      setAgents(agentsList);
      setVoiceProfiles(profiles);
      if (profiles.length > 0) {
        setScratchForm((prev) => ({
          ...prev,
          voice_profile_id: prev.voice_profile_id || profiles[0].id,
        }));
      }
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load agents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Filtered templates
  const filteredTemplates = useMemo(() => {
    return SARVAM_CATALOG.filter((tmpl) => {
      const matchesCategory =
        selectedCategory === "All" || tmpl.category === selectedCategory;
      const matchesSearch =
        searchQuery === "" ||
        tmpl.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        tmpl.tagline.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [selectedCategory, searchQuery]);

  // Create agent from Marketplace Template
  async function handleUseTemplate(template: MarketplaceTemplate) {
    setCreating(true);
    try {
      let profile = voiceProfiles[0];
      if (!profile) {
        try {
          const refreshed = await api.voiceProfiles.list();
          if (refreshed.length > 0) {
            setVoiceProfiles(refreshed);
            profile = refreshed[0];
          }
        } catch {}
      }

      const newAgent = await api.agents.create({
        name: template.title,
        template_slug: template.baseTemplateSlug,
        voice_profile_id: profile?.id,
        voice_profile_version: profile?.active_version ?? 1,
        description: template.tagline,
        auto_init_version: true,
        initial_configuration: template.defaultConfig,
      });
      toast.success(`Agent "${template.title}" created!`);
      router.push(`/agents/${newAgent.id}`);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create agent");
      setCreating(false);
    }
  }

  // Create from scratch
  async function handleCreateScratch(e: React.FormEvent) {
    e.preventDefault();
    if (!scratchForm.name.trim()) {
      return toast.error("Please enter an agent name");
    }
    let profile =
      voiceProfiles.find((v) => v.id === scratchForm.voice_profile_id) ||
      voiceProfiles[0];
    if (!profile) {
      try {
        const refreshed = await api.voiceProfiles.list();
        if (refreshed.length > 0) {
          setVoiceProfiles(refreshed);
          profile = refreshed[0];
        }
      } catch {}
    }

    setCreating(true);
    try {
      const newAgent = await api.agents.create({
        name: scratchForm.name.trim(),
        template_slug: scratchForm.template_slug,
        voice_profile_id: profile?.id,
        voice_profile_version: profile?.active_version ?? 1,
        description: scratchForm.description.trim(),
        auto_init_version: true,
        initial_configuration: {
          agent_name: scratchForm.name.trim(),
          primary_language: "en-IN",
          greeting: "Hello, thank you for connecting with {partnerName}. My name is {salesRepName}. How may I help you today?",
          input_variables: {
            partnerName: "Our Company",
            salesRepName: scratchForm.name.trim(),
            userName: "",
            productCategory: "Services",
          },
          output_variables: ["disposition", "chosen_next_step"],
          system_prompt: (
            "# Role & Persona\n" +
            `- **Agent Name**: {salesRepName}\n` +
            `- **Role**: Warm, professional customer assistant at {partnerName}.\n` +
            `- **Tone**: Warm, polite, concise, consultative.\n\n` +
            "## Conversational Rules\n" +
            "1. Under 25 words per turn.\n" +
            "2. Acknowledge before asking.\n" +
            "3. Strictly one question per turn.\n\n" +
            "## Conversation Flow\n" +
            "- **Phase 1 (Framing)**: State purpose and ask the first qualification question.\n" +
            "- **Phase 2 (Resolution)**: Answer questions and schedule next steps."
          ),
        },
      });
      toast.success("Agent created successfully!");
      setShowCreateModal(false);
      router.push(`/agents/${newAgent.id}`);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create agent");
      setCreating(false);
    }
  }

  // Ask Genie Agent Generator
  async function handleGenieGenerate() {
    if (!geniePrompt.trim()) {
      return toast.error("Please describe what kind of agent you need");
    }
    setGenieLoading(true);
    try {
      const res = await api.agents.improveWithGenie({
        instructions: geniePrompt,
        persona_focus: "Conversational Indian enterprise phone agent",
      });

      const profile = voiceProfiles[0];
      const agentName = geniePrompt.slice(0, 32).trim();

      const newAgent = await api.agents.create({
        name: agentName || "Genie Voice Agent",
        template_slug: "generic",
        voice_profile_id: profile?.id || "default",
        voice_profile_version: profile?.active_version ?? 1,
        description: "Generated with Genie AI assistant",
        auto_init_version: true,
        initial_configuration: {
          agent_name: "Genie Agent",
          primary_language: "en-IN",
          greeting: "Hello, this is {salesRepName} from {partnerName}. How can I assist you today?",
          input_variables: {
            partnerName: "Our Organization",
            salesRepName: "Assistant",
            userName: "",
            productCategory: "Solutions",
          },
          output_variables: ["disposition", "chosen_next_step"],
          system_prompt: res.improved_instructions,
        },
      });

      toast.success("Agent generated with Genie!");
      setShowGenieModal(false);
      router.push(`/agents/${newAgent.id}`);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Genie generation failed");
    } finally {
      setGenieLoading(false);
    }
  }

  async function handleDeleteAgent(e: React.MouseEvent, id: string, name: string) {
    e.stopPropagation();
    e.preventDefault();
    if (!confirm(`Are you sure you want to deactivate agent "${name}"?`)) return;
    try {
      await api.agents.delete(id);
      toast.success("Agent deactivated");
      await loadData();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to deactivate agent");
    }
  }

  return (
    <AppShell title="Voice Agents">
      <div className="max-w-7xl mx-auto space-y-8 pb-16">
        {/* Top Header Bar matching Sarvam AI */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/40 pb-5">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-text-primary">
              Voice Agents
            </h1>
            <p className="text-sm text-text-muted mt-1">
              Select, configure, and test AI agents tailored for your business workflows.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowGenieModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-secondary/80 hover:bg-secondary text-text-primary border border-border transition-colors shadow-sm"
            >
              <Sparkles className="w-4 h-4 text-amber-400 animate-pulse" />
              Ask Genie
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-primary hover:bg-primary/90 text-primary-foreground transition-all shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Create from scratch
            </button>
          </div>
        </div>

        {/* Section 1: Active Agents List */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-text-primary flex items-center gap-2">
              <Bot className="w-4 h-4 text-primary" />
              Your Active Agents ({agents.length})
            </h2>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Spinner className="w-7 h-7 text-primary" />
            </div>
          ) : agents.length === 0 ? (
            <div className="border border-dashed border-border rounded-xl p-8 text-center bg-card/40">
              <Bot className="w-10 h-10 text-text-muted mx-auto mb-3" />
              <h3 className="text-sm font-medium text-text-primary">No agents configured yet</h3>
              <p className="text-xs text-text-muted mt-1 mb-4">
                Choose a pre-built template below or create an agent from scratch.
              </p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium bg-primary text-primary-foreground"
              >
                <Plus className="w-3.5 h-3.5" />
                Create from scratch
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {agents.map((agent) => (
                <Link
                  key={agent.id}
                  href={`/agents/${agent.id}`}
                  className="group relative flex flex-col justify-between p-4 rounded-xl border border-border bg-card/80 hover:border-primary/50 hover:bg-card hover:shadow-md transition-all cursor-pointer"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary font-bold text-base flex-shrink-0">
                      {agent.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h3 className="font-semibold text-sm text-text-primary truncate group-hover:text-primary transition-colors">
                          {agent.name}
                        </h3>
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <CheckCircle2 className="w-2.5 h-2.5" />
                          {agent.active_version ? `v${agent.active_version}` : "v1"}
                        </span>
                      </div>
                      <p className="text-xs text-text-muted truncate mt-0.5">
                        {agent.description || `Base: ${agent.template_slug}`}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between mt-4 pt-3 border-t border-border/50 text-[11px] text-text-muted">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(agent.created_at).toLocaleDateString()}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => handleDeleteAgent(e, agent.id, agent.name)}
                        className="p-1 hover:text-red-400 rounded transition-colors"
                        title="Deactivate agent"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                      <span className="text-primary font-medium flex items-center gap-0.5 group-hover:translate-x-0.5 transition-transform">
                        Open Studio <ArrowRight className="w-3 h-3" />
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Section 2: Sarvam Agent Templates Marketplace */}
        <div className="pt-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <div>
              <h2 className="text-lg font-bold text-text-primary">
                Agent Templates
              </h2>
              <p className="text-xs text-text-muted mt-0.5">
                Choose from pre-built enterprise templates or customize for your industry workflow
              </p>
            </div>

            {/* Search Input */}
            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search templates..."
                className="w-full pl-9 pr-3 py-1.5 rounded-lg text-xs bg-secondary/50 border border-border focus:outline-none focus:border-primary text-text-primary"
              />
            </div>
          </div>

          {/* Category Filter Pills */}
          <div className="flex items-center gap-2 overflow-x-auto pb-3 mb-6 scrollbar-none">
            {TEMPLATE_CATEGORIES.map((cat) => {
              const active = selectedCategory === cat;
              return (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
                    active
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "bg-secondary/60 text-text-secondary hover:bg-secondary hover:text-text-primary border border-border/60"
                  }`}
                >
                  {cat}
                </button>
              );
            })}
          </div>

          {/* Templates Grid with Retro Pixel-Art Card Style */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {filteredTemplates.map((template) => (
              <div
                key={template.id}
                className="flex flex-col justify-between p-5 rounded-2xl border border-border/80 bg-card/70 hover:bg-card hover:border-primary/40 hover:shadow-lg transition-all duration-200 group"
              >
                <div>
                  {/* Pixel Art Icon Badge */}
                  <div className="flex items-start justify-between mb-3.5">
                    <div
                      className={`w-12 h-12 rounded-xl flex items-center justify-center text-xl border ${template.iconBg} shadow-inner`}
                    >
                      <span>{template.iconEmoji}</span>
                    </div>
                    <span className="text-[10px] font-medium tracking-wide uppercase px-2 py-0.5 rounded-md bg-secondary/80 text-text-muted border border-border/50">
                      {template.category}
                    </span>
                  </div>

                  <h3 className="font-bold text-sm text-text-primary group-hover:text-primary transition-colors">
                    {template.title}
                  </h3>
                  <p className="text-xs text-text-muted line-clamp-3 mt-1.5 leading-relaxed">
                    {template.tagline}
                  </p>
                </div>

                <div className="mt-5 pt-3.5 border-t border-border/40 flex items-center justify-between">
                  <span className="text-[11px] text-text-muted">
                    Lang: <span className="text-text-secondary font-mono">{template.defaultConfig.primary_language}</span>
                  </span>
                  <button
                    onClick={() => handleUseTemplate(template)}
                    disabled={creating}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary/10 text-primary hover:bg-primary hover:text-primary-foreground border border-primary/20 transition-all"
                  >
                    Use Template
                    <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Modal: Create from Scratch */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create Agent from Scratch"
      >
        <form onSubmit={handleCreateScratch} className="space-y-4">
          <Input
            label="Agent Name"
            placeholder="e.g. Sales Consultant Priya"
            value={scratchForm.name}
            onChange={(e) =>
              setScratchForm({ ...scratchForm, name: e.target.value })
            }
            required
          />

          <Select
            label="Voice Profile"
            value={scratchForm.voice_profile_id}
            onChange={(e) =>
              setScratchForm({ ...scratchForm, voice_profile_id: e.target.value })
            }
          >
            {voiceProfiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.display_name} ({p.language})
              </option>
            ))}
          </Select>

          <Input
            label="Description (Optional)"
            placeholder="What does this agent do?"
            value={scratchForm.description}
            onChange={(e) =>
              setScratchForm({ ...scratchForm, description: e.target.value })
            }
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowCreateModal(false)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={creating}>
              Create & Open Studio
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Ask Genie Agent Generator */}
      <Modal
        isOpen={showGenieModal}
        onClose={() => setShowGenieModal(false)}
        title="✨ Ask Genie to Build an Agent"
      >
        <div className="space-y-4">
          <p className="text-xs text-text-muted leading-relaxed">
            Tell Genie about your business, the goal of the call, language preferences, and tone. Genie will craft the instructions, variables, and conversational guardrails for you.
          </p>

          <textarea
            rows={4}
            value={geniePrompt}
            onChange={(e) => setGeniePrompt(e.target.value)}
            placeholder="e.g. A friendly rooftop solar advisor calling homeowners in Maharashtra in Marathi to qualify monthly electricity bill and offer a PM Surya Ghar subsidy survey..."
            className="w-full p-3 rounded-lg text-xs bg-secondary/40 border border-border focus:outline-none focus:border-primary text-text-primary resize-none"
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowGenieModal(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleGenieGenerate}
              loading={genieLoading}
              className="bg-primary hover:bg-primary/90 text-primary-foreground gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              Generate Agent
            </Button>
          </div>
        </div>
      </Modal>
    </AppShell>
  );
}
