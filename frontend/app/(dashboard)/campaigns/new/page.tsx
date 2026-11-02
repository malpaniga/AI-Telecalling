"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, CheckCheck, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { api, Agent, PhoneNumber, QualificationSlot } from "@/lib/api";

const TIMEZONE_OPTIONS = [
  { value: "Asia/Kolkata", label: "IST (Asia/Kolkata)" },
  { value: "Asia/Dubai", label: "GST (Asia/Dubai)" },
  { value: "UTC", label: "UTC" },
];

const DAY_OPTIONS = [
  { label: "Mon", full: "Monday", value: 1 },
  { label: "Tue", full: "Tuesday", value: 2 },
  { label: "Wed", full: "Wednesday", value: 3 },
  { label: "Thu", full: "Thursday", value: 4 },
  { label: "Fri", full: "Friday", value: 5 },
  { label: "Sat", full: "Saturday", value: 6 },
  { label: "Sun", full: "Sunday", value: 0 },
];

export default function NewCampaignPage() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [phoneNumbers, setPhoneNumbers] = useState<PhoneNumber[]>([]);
  const [loadingData, setLoadingData] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [form, setForm] = useState({
    name: "",
    description: "",
    agent_id: "",
    calling_number_id: "",
    max_concurrent_calls: "3",
    timezone: "Asia/Kolkata",
    start_time: "09:00",
    end_time: "18:00",
    max_attempts: "3",
    retry_delay_minutes: "60",
    scheduled_at: "",
  });

  const [selectedDays, setSelectedDays] = useState<number[]>([1, 2, 3, 4, 5]);

  // Dynamic qualification schema according to selected AI agent
  const [qualificationSlots, setQualificationSlots] = useState<QualificationSlot[]>([]);
  const [loadingSchema, setLoadingSchema] = useState(false);
  const [newSlotKey, setNewSlotKey] = useState("");
  const [newSlotLabel, setNewSlotLabel] = useState("");
  const [newSlotRequired, setNewSlotRequired] = useState(true);
  const [showAddSlot, setShowAddSlot] = useState(false);

  const selectedAgent = agents.find((a) => a.id === form.agent_id);

  // Auto-populate dynamic qualification criteria when selected agent changes
  useEffect(() => {
    if (!form.agent_id) return;
    const ag = agents.find((a) => a.id === form.agent_id);
    if (!ag) return;

    if (ag.qualification_schema && ag.qualification_schema.length > 0) {
      setQualificationSlots(ag.qualification_schema);
    } else if (ag.slot_definitions && ag.slot_definitions.length > 0) {
      setQualificationSlots(ag.slot_definitions);
    }

    setLoadingSchema(true);
    api.agents
      .qualificationSchema(ag.id)
      .then((res) => {
        if (res.qualification_schema && res.qualification_schema.length > 0) {
          setQualificationSlots(res.qualification_schema);
        } else if (res.slot_definitions && res.slot_definitions.length > 0) {
          setQualificationSlots(res.slot_definitions);
        }
      })
      .catch(() => {
        // preserve current slots
      })
      .finally(() => setLoadingSchema(false));
  }, [form.agent_id, agents]);

  function handleAddSlot() {
    const key = newSlotKey.trim().toLowerCase().replace(/\s+/g, "_");
    if (!key) {
      toast.error("Attribute key is required");
      return;
    }
    if (qualificationSlots.some((s) => s.key === key)) {
      toast.error("An attribute with this key already exists");
      return;
    }
    const label =
      newSlotLabel.trim() ||
      key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    setQualificationSlots((prev) => [
      ...prev,
      { key, label, required: newSlotRequired },
    ]);
    setNewSlotKey("");
    setNewSlotLabel("");
    setNewSlotRequired(true);
    setShowAddSlot(false);
    toast.success(`Added criteria: ${label}`);
  }

  function handleRemoveSlot(keyToRemove: string) {
    setQualificationSlots((prev) => prev.filter((s) => s.key !== keyToRemove));
  }

  function handleToggleRequired(keyToToggle: string) {
    setQualificationSlots((prev) =>
      prev.map((s) =>
        s.key === keyToToggle ? { ...s, required: !s.required } : s
      )
    );
  }

  useEffect(() => {
    Promise.all([api.agents.list(), api.phoneNumbers.myNumbers()])
      .then(([ag, ph]) => {
        const activeAgents = ag.filter((a) => a.is_active);
        setAgents(activeAgents);
        setPhoneNumbers(ph);
        if (activeAgents.length > 0)
          setForm((f) => ({ ...f, agent_id: activeAgents[0].id }));
        if (ph.length > 0)
          setForm((f) => ({ ...f, calling_number_id: ph[0].id }));
      })
      .catch((e: unknown) =>
        toast.error(e instanceof Error ? e.message : "Failed to load options")
      )
      .finally(() => setLoadingData(false));
  }, []);

  function toggleDay(dayVal: number) {
    setSelectedDays((prev) =>
      prev.includes(dayVal)
        ? prev.filter((d) => d !== dayVal)
        : [...prev, dayVal].sort((a, b) => (a === 0 ? 7 : a) - (b === 0 ? 7 : b))
    );
  }

  function setWeekdaysOnly() {
    setSelectedDays([1, 2, 3, 4, 5]);
  }

  function setAllDays() {
    setSelectedDays([1, 2, 3, 4, 5, 6, 0]);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) {
      toast.error("Campaign name is required");
      return;
    }
    if (!selectedAgent) {
      toast.error("Select an agent");
      return;
    }
    const callingNumber = phoneNumbers.find(
      (p) => p.id === form.calling_number_id
    );
    if (!callingNumber) {
      toast.error("Select a phone number");
      return;
    }
    if (selectedDays.length === 0) {
      toast.error("Select at least one calling day");
      return;
    }

    setSubmitting(true);
    try {
      const campaign = await api.campaigns.create({
        name: form.name,
        description: form.description || undefined,
        agent_id: selectedAgent.id,
        agent_version: selectedAgent.active_version ?? 1,
        voice_profile_id: selectedAgent.voice_profile_id,
        voice_profile_version: selectedAgent.voice_profile_version,
        calling_number_id: callingNumber.id,
        calling_number: callingNumber.number,
        max_concurrent_calls: parseInt(form.max_concurrent_calls) || 3,
        timezone: form.timezone,
        calling_hours: {
          start_time: form.start_time,
          end_time: form.end_time,
          days_of_week: selectedDays,
        },
        retry_policy: {
          max_attempts: parseInt(form.max_attempts) || 3,
          retry_delay_minutes: parseInt(form.retry_delay_minutes) || 60,
        },
        qualification_schema: qualificationSlots,
        scheduled_at: form.scheduled_at || undefined,
      });
      toast.success("Campaign created");
      router.push(`/campaigns/${campaign.id}`);
    } catch (e: unknown) {
      toast.error(
        e instanceof Error ? e.message : "Failed to create campaign"
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loadingData) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-3">
        <Link href="/campaigns">
          <Button variant="ghost" size="sm" className="gap-1">
            <ChevronLeft className="h-4 w-4" />
            Back
          </Button>
        </Link>
        <h2 className="text-lg font-semibold text-text-primary">
          New Campaign
        </h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Basic info */}
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-text-primary">
              Campaign Details
            </h3>
          </CardHeader>
          <CardBody className="space-y-4">
            <Input
              label="Campaign Name"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Q4 Home Loan Outreach"
              required
            />
            <Input
              label="Description (optional)"
              value={form.description}
              onChange={(e) =>
                setForm((f) => ({ ...f, description: e.target.value }))
              }
              placeholder="Brief description"
            />
          </CardBody>
        </Card>

        {/* Agent + phone */}
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-text-primary">
              Agent &amp; Phone Number
            </h3>
          </CardHeader>
          <CardBody className="space-y-4">
            {agents.length === 0 ? (
              <p className="text-sm text-warning">
                No active agents found.{" "}
                <Link href="/agents/new" className="underline text-accent">
                  Create an agent first.
                </Link>
              </p>
            ) : (
              <Select
                label="Agent"
                value={form.agent_id}
                onChange={(e) =>
                  setForm((f) => ({ ...f, agent_id: e.target.value }))
                }
                options={agents.map((a) => ({
                  value: a.id,
                  label: `${a.name} (v${a.active_version ?? "—"})`,
                }))}
              />
            )}
            {selectedAgent && (
              <p className="text-xs text-text-muted">
                Template: {selectedAgent.template_slug} · Language:{" "}
                {selectedAgent.voice_profile_version}
              </p>
            )}
            {phoneNumbers.length === 0 ? (
              <p className="text-sm text-warning">
                No phone numbers assigned. Contact your admin.
              </p>
            ) : (
              <Select
                label="Calling Number"
                value={form.calling_number_id}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    calling_number_id: e.target.value,
                  }))
                }
                options={phoneNumbers.map((p) => ({
                  value: p.id,
                  label: p.number,
                }))}
              />
            )}
          </CardBody>
        </Card>

        {/* Dynamic Qualification Criteria Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <CheckCheck className="h-4 w-4 text-accent" />
                Dynamic Qualification Schema
              </h3>
              <p className="text-xs text-text-muted mt-0.5">
                Target attributes qualified by{" "}
                <span className="font-semibold text-text-primary">
                  {selectedAgent?.name || "selected AI agent"}
                </span>{" "}
                during live calls.
              </p>
            </div>
            {!showAddSlot && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setShowAddSlot(true)}
                className="text-xs gap-1"
              >
                <Plus className="h-3.5 w-3.5" /> Add Attribute
              </Button>
            )}
          </CardHeader>
          <CardBody className="space-y-3">
            {loadingSchema ? (
              <div className="flex items-center gap-2 text-xs text-text-muted py-2">
                <Spinner size="sm" /> Loading criteria for {selectedAgent?.name}...
              </div>
            ) : qualificationSlots.length === 0 ? (
              <p className="text-xs text-text-muted italic py-1">
                No custom qualification attributes configured. Leads will be evaluated on general interest and booking intent.
              </p>
            ) : (
              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                {qualificationSlots.map((slot) => (
                  <div
                    key={slot.key}
                    className="flex items-center justify-between p-2.5 rounded-lg border border-border bg-surface-subtle text-xs"
                  >
                    <div className="min-w-0 pr-2">
                      <div className="flex items-center gap-1.5 font-medium text-text-primary truncate">
                        <span>{slot.label}</span>
                        {slot.required ? (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
                            Required
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded text-[10px] text-text-muted bg-surface-hover">
                            Optional
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] font-mono text-text-muted">
                        key: {slot.key}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleToggleRequired(slot.key)}
                        title={slot.required ? "Mark as optional" : "Mark as required"}
                        className="px-2 py-1 text-[11px] font-medium rounded hover:bg-surface-hover text-text-secondary border border-border"
                      >
                        {slot.required ? "Make Optional" : "Make Required"}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRemoveSlot(slot.key)}
                        className="p-1 text-text-muted hover:text-red-500 rounded"
                        title="Remove attribute"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {showAddSlot && (
              <div className="p-3 rounded-lg border border-accent/30 bg-accent/5 space-y-3 mt-2">
                <p className="text-xs font-semibold text-text-primary">Add Custom Qualification Field</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <Input
                    label="Field Key (e.g. roof_area, monthly_bill)"
                    value={newSlotKey}
                    onChange={(e) => setNewSlotKey(e.target.value)}
                    placeholder="field_key"
                  />
                  <Input
                    label="Display Label"
                    value={newSlotLabel}
                    onChange={(e) => setNewSlotLabel(e.target.value)}
                    placeholder="e.g. Monthly Electricity Bill"
                  />
                </div>
                <div className="flex items-center justify-between pt-1">
                  <label className="flex items-center gap-2 text-xs text-text-secondary cursor-pointer">
                    <input
                      type="checkbox"
                      checked={newSlotRequired}
                      onChange={(e) => setNewSlotRequired(e.target.checked)}
                      className="rounded border-border text-accent focus:ring-accent"
                    />
                    Required attribute for qualification
                  </label>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowAddSlot(false)}
                      className="text-xs"
                    >
                      Cancel
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      onClick={handleAddSlot}
                      className="text-xs"
                    >
                      Add Field
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </CardBody>
        </Card>

        {/* Schedule */}
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-text-primary">
              Schedule &amp; Calling Hours
            </h3>
          </CardHeader>
          <CardBody className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Select
                label="Timezone"
                value={form.timezone}
                onChange={(e) =>
                  setForm((f) => ({ ...f, timezone: e.target.value }))
                }
                options={TIMEZONE_OPTIONS}
              />
              <Input
                label="Max Concurrent Calls"
                type="number"
                min={1}
                max={10}
                value={form.max_concurrent_calls}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    max_concurrent_calls: e.target.value,
                  }))
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Start Time"
                type="time"
                value={form.start_time}
                onChange={(e) =>
                  setForm((f) => ({ ...f, start_time: e.target.value }))
                }
              />
              <Input
                label="End Time"
                type="time"
                value={form.end_time}
                onChange={(e) =>
                  setForm((f) => ({ ...f, end_time: e.target.value }))
                }
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-text-primary">
                  Calling Days
                </label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={setWeekdaysOnly}
                    className="text-xs text-accent hover:underline cursor-pointer"
                  >
                    Weekdays
                  </button>
                  <span className="text-xs text-text-muted">·</span>
                  <button
                    type="button"
                    onClick={setAllDays}
                    className="text-xs text-accent hover:underline cursor-pointer"
                  >
                    All Days
                  </button>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {DAY_OPTIONS.map((day) => (
                  <button
                    key={day.value}
                    type="button"
                    onClick={() => toggleDay(day.value)}
                    className={`px-3 py-1 text-xs rounded-full border transition-colors cursor-pointer ${
                      selectedDays.includes(day.value)
                        ? "border-accent bg-accent text-white font-medium"
                        : "border-border text-text-secondary hover:border-accent-hover"
                    }`}
                  >
                    {day.label}
                  </button>
                ))}
              </div>
              {selectedDays.length === 0 && (
                <p className="text-xs text-danger mt-1">Please select at least one calling day.</p>
              )}
            </div>
          </CardBody>
        </Card>

        {/* Retry policy */}
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-text-primary">
              Retry Policy
            </h3>
          </CardHeader>
          <CardBody className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Max Attempts"
                type="number"
                min={1}
                max={10}
                value={form.max_attempts}
                onChange={(e) =>
                  setForm((f) => ({ ...f, max_attempts: e.target.value }))
                }
              />
              <Input
                label="Retry Delay (minutes)"
                type="number"
                value={form.retry_delay_minutes}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    retry_delay_minutes: e.target.value,
                  }))
                }
              />
            </div>
            <Input
              label="Scheduled Start (optional)"
              type="datetime-local"
              value={form.scheduled_at}
              onChange={(e) =>
                setForm((f) => ({ ...f, scheduled_at: e.target.value }))
              }
              hint="Leave blank to start manually"
            />
          </CardBody>
        </Card>

        <div className="flex justify-end gap-2">
          <Link href="/campaigns">
            <Button type="button" variant="secondary">
              Cancel
            </Button>
          </Link>
          <Button type="submit" loading={submitting}>
            Create Campaign
          </Button>
        </div>
      </form>
    </div>
  );
}
