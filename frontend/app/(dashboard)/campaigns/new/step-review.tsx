"use client";

import React from "react";
import {
  CheckCircle2,
  Phone,
  Bot,
  Calendar,
  Users,
  Clock,
  Layers,
  ArrowLeft,
  Play,
  Save,
  Sparkles,
  AlertCircle,
} from "lucide-react";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Agent, PhoneNumber, QualificationSlot } from "@/lib/api";

const DAY_NAMES: Record<number, string> = {
  1: "Mon",
  2: "Tue",
  3: "Wed",
  4: "Thu",
  5: "Fri",
  6: "Sat",
  0: "Sun",
};

interface StepReviewProps {
  form: {
    name: string;
    description: string;
    calling_number_id: string;
    agent_id: string;
    max_concurrent_calls: string;
    timezone: string;
    start_time: string;
    end_time: string;
    max_attempts: string;
    retry_delay_minutes: string;
    scheduled_at: string;
  };
  selectedDays: number[];
  qualificationSlots: QualificationSlot[];
  selectedLeadIds: string[];
  selectAllMatched: boolean;
  contactFilters?: {
    search?: string;
    city?: string;
    tag?: string;
    status?: string;
  };
  agents: Agent[];
  phoneNumbers: PhoneNumber[];
  submitting: boolean;
  onBack: () => void;
  onSaveDraft: () => void;
  onCreateAndStart: () => void;
}

export function StepReview({
  form,
  selectedDays,
  qualificationSlots,
  selectedLeadIds,
  selectAllMatched,
  contactFilters,
  agents,
  phoneNumbers,
  submitting,
  onBack,
  onSaveDraft,
  onCreateAndStart,
}: StepReviewProps) {
  const selectedAgent = agents.find((a) => a.id === form.agent_id);
  const selectedPhone = phoneNumbers.find((p) => p.id === form.calling_number_id);

  const formattedDays = selectedDays
    .map((d) => DAY_NAMES[d])
    .filter(Boolean)
    .join(", ");

  const filterDesc: string[] = [];
  if (contactFilters?.city) filterDesc.push(`City: ${contactFilters.city}`);
  if (contactFilters?.tag) filterDesc.push(`Tag: #${contactFilters.tag}`);
  if (contactFilters?.status) filterDesc.push(`Status: ${contactFilters.status}`);
  if (contactFilters?.search) filterDesc.push(`Search: "${contactFilters.search}"`);

  const audienceLabel = selectAllMatched
    ? filterDesc.length > 0
      ? `All matching leads (${filterDesc.join(", ")})`
      : "All organization contacts"
    : `${selectedLeadIds.length} contact${selectedLeadIds.length !== 1 ? "s" : ""} selected`;

  return (
    <div className="space-y-6">
      {/* Review Header Banner */}
      <div className="p-4 rounded-xl bg-success/10 border border-success/20 flex items-start gap-3">
        <CheckCircle2 className="h-5 w-5 text-success mt-0.5 flex-shrink-0" />
        <div>
          <h4 className="text-sm font-semibold text-text-primary">
            Ready to Launch Campaign
          </h4>
          <p className="text-xs text-text-secondary mt-0.5">
            Please review the configuration details below. You can save this campaign as a draft or immediately start dialing.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Card 1: Basics & Telephony */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Phone className="h-4 w-4 text-accent" />
              <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Identity & Telephony
              </h4>
            </div>
          </CardHeader>
          <CardBody className="space-y-3 text-xs">
            <div>
              <span className="text-text-muted block">Campaign Name</span>
              <span className="font-semibold text-sm text-text-primary">
                {form.name}
              </span>
            </div>
            {form.description && (
              <div>
                <span className="text-text-muted block">Description</span>
                <span className="text-text-secondary">{form.description}</span>
              </div>
            )}
            <div>
              <span className="text-text-muted block">Outbound Caller Number</span>
              <span className="font-mono font-medium text-text-primary">
                {selectedPhone ? selectedPhone.number : "None selected"}
              </span>
              {selectedPhone?.display_name && (
                <span className="text-text-muted ml-1">
                  ({selectedPhone.display_name})
                </span>
              )}
            </div>
          </CardBody>
        </Card>

        {/* Card 2: AI Voice Agent */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bot className="h-4 w-4 text-accent" />
              <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                AI Voice Agent
              </h4>
            </div>
          </CardHeader>
          <CardBody className="space-y-3 text-xs">
            <div>
              <span className="text-text-muted block">Assigned Agent</span>
              <span className="font-semibold text-sm text-text-primary">
                {selectedAgent?.name || "None selected"}
              </span>
              <span className="text-text-muted ml-2">
                (v{selectedAgent?.active_version ?? 1} • {selectedAgent?.template_slug || "Voice Agent"})
              </span>
            </div>
            <div>
              <span className="text-text-muted block">Qualification Rules</span>
              {qualificationSlots.length === 0 ? (
                <span className="text-text-muted">Standard transcript & call disposition</span>
              ) : (
                <div className="flex flex-wrap gap-1 mt-1">
                  {qualificationSlots.map((s) => (
                    <span
                      key={s.key}
                      className="bg-surface-subtle border border-border px-2 py-0.5 rounded text-[11px] font-mono text-text-secondary"
                    >
                      {s.key} {s.required && <span className="text-accent-red">*</span>}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </CardBody>
        </Card>

        {/* Card 3: Schedule & Limits */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-accent" />
              <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Calling Window & Limits
              </h4>
            </div>
          </CardHeader>
          <CardBody className="space-y-3 text-xs">
            <div>
              <span className="text-text-muted block">Active Days & Hours</span>
              <span className="font-semibold text-text-primary">
                {formattedDays || "No days selected"}
              </span>
              <span className="text-text-muted ml-2">
                ({form.start_time} - {form.end_time} {form.timezone})
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="text-text-muted block">Concurrent Calls</span>
                <span className="font-semibold text-text-primary">
                  {form.max_concurrent_calls} lines
                </span>
              </div>
              <div>
                <span className="text-text-muted block">Retry Policy</span>
                <span className="font-semibold text-text-primary">
                  {form.max_attempts} attempts • {form.retry_delay_minutes}m delay
                </span>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Card 4: Target Audience */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-accent" />
              <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Target Audience
              </h4>
            </div>
          </CardHeader>
          <CardBody className="space-y-3 text-xs">
            <div>
              <span className="text-text-muted block">Enrolled Contacts</span>
              <span className="font-semibold text-sm text-text-primary block">
                {audienceLabel}
              </span>
            </div>
            {form.scheduled_at && (
              <div>
                <span className="text-text-muted block">Scheduled Launch</span>
                <span className="font-mono text-text-primary">
                  {new Date(form.scheduled_at).toLocaleString()}
                </span>
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      {/* Action Footer */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-border">
        <Button
          type="button"
          variant="ghost"
          onClick={onBack}
          disabled={submitting}
          className="gap-2 w-full sm:w-auto"
        >
          <ArrowLeft className="h-4 w-4" />
          Back: Select Contacts
        </Button>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <Button
            type="button"
            variant="secondary"
            onClick={onSaveDraft}
            disabled={submitting}
            className="gap-2 flex-1 sm:flex-initial"
          >
            {submitting ? (
              <Spinner size="sm" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save as Draft
          </Button>

          <Button
            type="button"
            variant="primary"
            onClick={onCreateAndStart}
            disabled={submitting}
            className="gap-2 flex-1 sm:flex-initial bg-success hover:bg-success/90 border-success text-white"
          >
            {submitting ? (
              <Spinner size="sm" />
            ) : (
              <Play className="h-4 w-4 fill-current" />
            )}
            Create & Start Campaign
          </Button>
        </div>
      </div>
    </div>
  );
}
