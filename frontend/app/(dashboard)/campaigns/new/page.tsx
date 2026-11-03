"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Check, Sparkles } from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { AppShell } from "@/components/layout/app-shell";
import { api, Agent, PhoneNumber, QualificationSlot } from "@/lib/api";

import { StepBasics } from "./step-basics";
import { StepAgent } from "./step-agent";
import { StepSchedule } from "./step-schedule";
import { StepContacts, ContactFilters } from "./step-contacts";
import { StepReview } from "./step-review";

const WIZARD_STEPS = [
  { step: 1, title: "Basics" },
  { step: 2, title: "AI Agent" },
  { step: 3, title: "Schedule" },
  { step: 4, title: "Contacts" },
  { step: 5, title: "Review" },
];

export default function NewCampaignWizardPage() {
  const router = useRouter();

  // Wizard Step
  const [currentStep, setCurrentStep] = useState(1);
  const [highestStep, setHighestStep] = useState(1);

  // External options
  const [agents, setAgents] = useState<Agent[]>([]);
  const [phoneNumbers, setPhoneNumbers] = useState<PhoneNumber[]>([]);
  const [loadingData, setLoadingData] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // Form State
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

  // Qualification slots
  const [qualificationSlots, setQualificationSlots] = useState<QualificationSlot[]>([]);
  const [loadingSchema, setLoadingSchema] = useState(false);

  // Audience selection state
  const [selectedLeadIds, setSelectedLeadIds] = useState<string[]>([]);
  const [selectAllMatched, setSelectAllMatched] = useState(false);
  const [contactFilters, setContactFilters] = useState<ContactFilters>({
    search: "",
    city: "",
    tag: "",
    status: "",
  });

  // Initial load
  useEffect(() => {
    Promise.all([api.agents.list(), api.phoneNumbers.myNumbers()])
      .then(([ag, ph]) => {
        const activeAgents = ag.filter((a) => a.is_active);
        setAgents(activeAgents);
        setPhoneNumbers(ph);
        if (activeAgents.length > 0) {
          setForm((f) => ({ ...f, agent_id: activeAgents[0].id }));
        }
        if (ph.length > 0) {
          setForm((f) => ({ ...f, calling_number_id: ph[0].id }));
        }
      })
      .catch((e: unknown) =>
        toast.error(e instanceof Error ? e.message : "Failed to load options")
      )
      .finally(() => setLoadingData(false));
  }, []);

  // When agent changes, populate qualification schema
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
        }
      })
      .catch(() => {})
      .finally(() => setLoadingSchema(false));
  }, [form.agent_id, agents]);

  function handleFormChange(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function handleSelectAgent(newAgentId: string) {
    setForm((f) => ({ ...f, agent_id: newAgentId }));
  }

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

  function handleToggleLead(leadId: string) {
    setSelectedLeadIds((prev) =>
      prev.includes(leadId) ? prev.filter((id) => id !== leadId) : [...prev, leadId]
    );
  }

  function goToStep(targetStep: number) {
    if (targetStep <= highestStep) {
      setCurrentStep(targetStep);
    }
  }

  function advanceStep(nextStep: number) {
    setCurrentStep(nextStep);
    if (nextStep > highestStep) {
      setHighestStep(nextStep);
    }
  }

  // Create & Enroll submission handler
  async function handleCreateCampaign(startImmediate: boolean) {
    const selectedAgent = agents.find((a) => a.id === form.agent_id);
    const callingNumber = phoneNumbers.find((p) => p.id === form.calling_number_id);

    if (!form.name.trim()) {
      toast.error("Campaign name is required");
      setCurrentStep(1);
      return;
    }
    if (!selectedAgent) {
      toast.error("Please select an AI agent");
      setCurrentStep(2);
      return;
    }
    if (!callingNumber) {
      toast.error("Please select an outbound phone number");
      setCurrentStep(1);
      return;
    }

    setSubmitting(true);
    try {
      // 1. Create campaign
      const campaign = await api.campaigns.create({
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        agent_id: selectedAgent.id,
        agent_version: selectedAgent.active_version ?? 1,
        voice_profile_id: selectedAgent.voice_profile_id,
        voice_profile_version: selectedAgent.voice_profile_version,
        calling_number_id: callingNumber.id,
        calling_number: callingNumber.number,
        max_concurrent_calls: parseInt(form.max_concurrent_calls, 10) || 3,
        timezone: form.timezone,
        calling_hours: {
          start_time: form.start_time,
          end_time: form.end_time,
          days_of_week: selectedDays,
        },
        retry_policy: {
          max_attempts: parseInt(form.max_attempts, 10) || 3,
          retry_delay_minutes: parseInt(form.retry_delay_minutes, 10) || 60,
        },
        qualification_schema: qualificationSlots,
        scheduled_at: form.scheduled_at || undefined,
      });

      // 2. Enroll contacts if selected
      if (selectAllMatched) {
        await api.campaigns.enrollLeads(campaign.id, {
          city: contactFilters.city || undefined,
          tags: contactFilters.tag ? [contactFilters.tag] : undefined,
          status: contactFilters.status || undefined,
          all_contacts:
            !contactFilters.city &&
            !contactFilters.tag &&
            !contactFilters.status,
        });
      } else if (selectedLeadIds.length > 0) {
        await api.campaigns.enrollLeads(campaign.id, { lead_ids: selectedLeadIds });
      }

      // 3. Start campaign if chosen
      if (startImmediate) {
        try {
          await api.campaigns.start(campaign.id);
          toast.success("Campaign created & launched!");
        } catch (startErr: unknown) {
          toast.error(
            startErr instanceof Error
              ? `Campaign saved as draft: ${startErr.message}`
              : "Failed to start campaign automatically"
          );
        }
      } else {
        toast.success("Campaign saved as draft");
      }

      router.push(`/campaigns/${campaign.id}`);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create campaign");
    } finally {
      setSubmitting(false);
    }
  }

  if (loadingData) {
    return (
      <AppShell title="New Campaign Wizard">
        <div className="flex flex-col items-center justify-center py-24 gap-3">
          <Spinner size="lg" />
          <p className="text-sm text-text-muted">Loading campaign studio options...</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title="New Campaign Wizard">
      <div className="max-w-3xl mx-auto space-y-6 pb-12">
      {/* Top Header & Breadcrumb */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/campaigns">
            <Button variant="ghost" size="sm" className="gap-1 text-xs">
              <ChevronLeft className="h-4 w-4" />
              Campaigns
            </Button>
          </Link>
          <span className="text-text-muted">/</span>
          <h2 className="text-lg font-bold text-text-primary">
            New Campaign Wizard
          </h2>
        </div>
      </div>

      {/* Stepper Progress Bar */}
      <div className="bg-surface border border-border rounded-xl p-4 shadow-sm">
        <div className="flex items-center justify-between">
          {WIZARD_STEPS.map((st, idx) => {
            const isCompleted = currentStep > st.step;
            const isCurrent = currentStep === st.step;
            const isClickable = st.step <= highestStep;

            return (
              <React.Fragment key={st.step}>
                <button
                  type="button"
                  disabled={!isClickable}
                  onClick={() => goToStep(st.step)}
                  className={`flex flex-col sm:flex-row items-center gap-2 group transition-all ${
                    isClickable ? "cursor-pointer" : "cursor-not-allowed opacity-50"
                  }`}
                >
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-all ${
                      isCompleted
                        ? "bg-success text-white ring-4 ring-success/20"
                        : isCurrent
                        ? "bg-accent text-white ring-4 ring-accent/20 shadow-sm"
                        : "bg-surface-subtle text-text-secondary border border-border"
                    }`}
                  >
                    {isCompleted ? <Check className="h-4 w-4 stroke-[2.5]" /> : st.step}
                  </div>
                  <span
                    className={`text-xs font-semibold ${
                      isCurrent
                        ? "text-accent"
                        : isCompleted
                        ? "text-text-primary"
                        : "text-text-muted"
                    }`}
                  >
                    {st.title}
                  </span>
                </button>

                {idx < WIZARD_STEPS.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 mx-2 rounded transition-all ${
                      currentStep > st.step ? "bg-success" : "bg-border"
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Wizard Step Renderings */}
      {currentStep === 1 && (
        <StepBasics
          name={form.name}
          description={form.description}
          callingNumberId={form.calling_number_id}
          phoneNumbers={phoneNumbers}
          onChange={handleFormChange}
          onNext={() => advanceStep(2)}
        />
      )}

      {currentStep === 2 && (
        <StepAgent
          agentId={form.agent_id}
          agents={agents}
          qualificationSlots={qualificationSlots}
          loadingSchema={loadingSchema}
          onSelectAgent={handleSelectAgent}
          onSetSlots={setQualificationSlots}
          onBack={() => setCurrentStep(1)}
          onNext={() => advanceStep(3)}
        />
      )}

      {currentStep === 3 && (
        <StepSchedule
          timezone={form.timezone}
          startTime={form.start_time}
          endTime={form.end_time}
          selectedDays={selectedDays}
          maxConcurrentCalls={form.max_concurrent_calls}
          maxAttempts={form.max_attempts}
          retryDelayMinutes={form.retry_delay_minutes}
          scheduledAt={form.scheduled_at}
          onChange={handleFormChange}
          onToggleDay={toggleDay}
          onSetWeekdaysOnly={setWeekdaysOnly}
          onSetAllDays={setAllDays}
          onBack={() => setCurrentStep(2)}
          onNext={() => advanceStep(4)}
        />
      )}

      {currentStep === 4 && (
        <StepContacts
          selectedLeadIds={selectedLeadIds}
          selectAllMatched={selectAllMatched}
          filters={contactFilters}
          onFilterChange={setContactFilters}
          onToggleLead={handleToggleLead}
          onSetSelectedLeads={setSelectedLeadIds}
          onSetSelectAllMatched={setSelectAllMatched}
          onBack={() => setCurrentStep(3)}
          onNext={() => advanceStep(5)}
        />
      )}

      {currentStep === 5 && (
        <StepReview
          form={form}
          selectedDays={selectedDays}
          qualificationSlots={qualificationSlots}
          selectedLeadIds={selectedLeadIds}
          selectAllMatched={selectAllMatched}
          contactFilters={contactFilters}
          agents={agents}
          phoneNumbers={phoneNumbers}
          submitting={submitting}
          onBack={() => setCurrentStep(4)}
          onSaveDraft={() => handleCreateCampaign(false)}
          onCreateAndStart={() => handleCreateCampaign(true)}
        />
      )}
    </div>
    </AppShell>
  );
}
