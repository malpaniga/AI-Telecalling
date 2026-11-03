"use client";

import React, { useState } from "react";
import {
  Bot,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  CheckCheck,
  Plus,
  Trash2,
  HelpCircle,
  Zap,
} from "lucide-react";
import toast from "react-hot-toast";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Agent, QualificationSlot } from "@/lib/api";

interface StepAgentProps {
  agentId: string;
  agents: Agent[];
  qualificationSlots: QualificationSlot[];
  loadingSchema: boolean;
  onSelectAgent: (agentId: string) => void;
  onSetSlots: (slots: QualificationSlot[]) => void;
  onBack: () => void;
  onNext: () => void;
}

export function StepAgent({
  agentId,
  agents,
  qualificationSlots,
  loadingSchema,
  onSelectAgent,
  onSetSlots,
  onBack,
  onNext,
}: StepAgentProps) {
  const [newSlotKey, setNewSlotKey] = useState("");
  const [newSlotLabel, setNewSlotLabel] = useState("");
  const [newSlotRequired, setNewSlotRequired] = useState(true);
  const [showAddSlot, setShowAddSlot] = useState(false);

  const selectedAgent = agents.find((a) => a.id === agentId);

  function handleSkipWithDefaults() {
    if (!selectedAgent) {
      toast.error("Please select an AI Agent first");
      return;
    }
    const defaultSlots =
      selectedAgent.qualification_schema && selectedAgent.qualification_schema.length > 0
        ? selectedAgent.qualification_schema
        : selectedAgent.slot_definitions && selectedAgent.slot_definitions.length > 0
        ? selectedAgent.slot_definitions
        : [];

    if (defaultSlots.length > 0) {
      onSetSlots(defaultSlots);
      toast.success(`Loaded ${defaultSlots.length} default criteria from ${selectedAgent.name}`);
    } else {
      toast.success("Proceeding with standard agent configuration");
    }
    onNext();
  }

  function handleAddSlot(e: React.FormEvent) {
    e.preventDefault();
    const key = newSlotKey.trim().toLowerCase().replace(/\s+/g, "_");
    if (!key) {
      toast.error("Slot key is required");
      return;
    }
    if (qualificationSlots.some((s) => s.key === key)) {
      toast.error(`Criteria '${key}' is already configured`);
      return;
    }
    const label =
      newSlotLabel.trim() ||
      key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

    onSetSlots([
      ...qualificationSlots,
      { key, label, required: newSlotRequired },
    ]);
    setNewSlotKey("");
    setNewSlotLabel("");
    setNewSlotRequired(true);
    setShowAddSlot(false);
    toast.success(`Added criteria: ${label}`);
  }

  function handleRemoveSlot(keyToRemove: string) {
    onSetSlots(qualificationSlots.filter((s) => s.key !== keyToRemove));
  }

  function handleToggleRequired(keyToToggle: string) {
    onSetSlots(
      qualificationSlots.map((s) =>
        s.key === keyToToggle ? { ...s, required: !s.required } : s
      )
    );
  }

  function handleProceedNext() {
    if (!selectedAgent) {
      toast.error("Please select an AI Agent");
      return;
    }
    onNext();
  }

  return (
    <div className="space-y-6">
      {/* Agent Selector Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-primary/10 text-brand-primary font-bold text-sm">
                2
              </div>
              <div>
                <h3 className="text-base font-semibold text-text-primary">
                  Select AI Voice Agent
                </h3>
                <p className="text-xs text-text-secondary">
                  Choose the conversational agent that will conduct calls for this campaign.
                </p>
              </div>
            </div>
            {selectedAgent && (
              <span className="text-xs font-mono bg-brand-primary/10 text-brand-primary px-2.5 py-1 rounded-full">
                v{selectedAgent.active_version ?? 1}
              </span>
            )}
          </div>
        </CardHeader>
        <CardBody className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">
              Active Agent <span className="text-accent-red">*</span>
            </label>
            <Select
              value={agentId}
              onChange={(e) => onSelectAgent(e.target.value)}
              className="w-full"
            >
              <option value="" disabled>
                Select an agent...
              </option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} (v{a.active_version ?? 1})
                </option>
              ))}
            </Select>
          </div>

          {selectedAgent && (
            <div className="rounded-xl border border-border-default bg-bg-subtle/50 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-text-secondary">
                  Agent Template
                </span>
                <span className="text-xs font-semibold text-text-primary capitalize tracking-wider">
                  {selectedAgent.template_slug || "Standard"}
                </span>
              </div>
              {selectedAgent.description && (
                <p className="text-xs text-text-muted italic">
                  &ldquo;{selectedAgent.description}&rdquo;
                </p>
              )}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Qualification Criteria Card */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-brand-primary" />
              <div>
                <h3 className="text-base font-semibold text-text-primary">
                  Qualification Criteria
                </h3>
                <p className="text-xs text-text-secondary">
                  Information the agent must extract during calls to qualify each lead.
                </p>
              </div>
            </div>

            {/* Quick Skip with Defaults button */}
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleSkipWithDefaults}
              className="gap-1.5 border-brand-primary/30 text-brand-primary hover:bg-brand-primary/10 self-start sm:self-auto"
            >
              <Zap className="h-3.5 w-3.5 fill-current" />
              Use Agent Defaults & Continue
            </Button>
          </div>
        </CardHeader>
        <CardBody className="space-y-4">
          {loadingSchema ? (
            <div className="flex items-center justify-center py-6 gap-2 text-xs text-text-muted">
              <Spinner size="sm" />
              Loading agent qualification schema...
            </div>
          ) : qualificationSlots.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border-default p-6 text-center">
              <HelpCircle className="h-8 w-8 text-text-muted mx-auto mb-2 opacity-50" />
              <p className="text-sm font-medium text-text-primary">
                No custom qualification slots configured
              </p>
              <p className="text-xs text-text-muted mt-1 max-w-md mx-auto">
                Calls will record standard call transcripts and conversation outcomes. You can add specific criteria below or skip to default.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {qualificationSlots.map((slot) => (
                <div
                  key={slot.key}
                  className="flex items-center justify-between p-3 rounded-lg border border-border-default bg-bg-surface hover:border-border-strong transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs font-semibold text-text-primary bg-bg-subtle px-2 py-0.5 rounded">
                      {slot.key}
                    </span>
                    <span className="text-sm text-text-secondary">{slot.label}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleToggleRequired(slot.key)}
                      className={`text-[11px] px-2.5 py-0.5 rounded-full font-medium transition-colors ${
                        slot.required
                          ? "bg-accent-blue/10 text-accent-blue border border-accent-blue/20"
                          : "bg-bg-subtle text-text-muted hover:text-text-primary"
                      }`}
                    >
                      {slot.required ? "Required" : "Optional"}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRemoveSlot(slot.key)}
                      className="p-1 text-text-muted hover:text-accent-red rounded transition-colors"
                      title="Remove criteria"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Add Criteria Form */}
          {showAddSlot ? (
            <form
              onSubmit={handleAddSlot}
              className="p-4 rounded-xl border border-brand-primary/20 bg-brand-primary/5 space-y-3"
            >
              <div className="font-medium text-xs text-brand-primary">
                Add Custom Lead Qualification Slot
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1">
                    Slot Key (machine-readable)
                  </label>
                  <Input
                    value={newSlotKey}
                    onChange={(e) => setNewSlotKey(e.target.value)}
                    placeholder="e.g. budget_approved or timeline"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1">
                    Display Label
                  </label>
                  <Input
                    value={newSlotLabel}
                    onChange={(e) => setNewSlotLabel(e.target.value)}
                    placeholder="e.g. Budget Approved"
                  />
                </div>
              </div>
              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 text-xs text-text-secondary cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newSlotRequired}
                    onChange={(e) => setNewSlotRequired(e.target.checked)}
                    className="rounded border-border-default text-brand-primary focus:ring-brand-primary"
                  />
                  Mark as mandatory for lead qualification
                </label>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowAddSlot(false)}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary" size="sm">
                    Add Slot
                  </Button>
                </div>
              </div>
            </form>
          ) : (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setShowAddSlot(true)}
              className="gap-1.5 text-xs w-full sm:w-auto"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Custom Criteria Slot
            </Button>
          )}
        </CardBody>
      </Card>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between pt-2">
        <Button
          type="button"
          variant="ghost"
          onClick={onBack}
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back: Basics
        </Button>
        <Button
          type="button"
          variant="primary"
          onClick={handleProceedNext}
          disabled={!selectedAgent}
          className="gap-2 px-6"
        >
          Next: Calling Schedule
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
