"use client";

import React from "react";
import { Phone, ArrowRight, Info, AlertCircle } from "lucide-react";
import toast from "react-hot-toast";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PhoneNumber } from "@/lib/api";

interface StepBasicsProps {
  name: string;
  description: string;
  callingNumberId: string;
  phoneNumbers: PhoneNumber[];
  onChange: (field: string, value: string) => void;
  onNext: () => void;
}

export function StepBasics({
  name,
  description,
  callingNumberId,
  phoneNumbers,
  onChange,
  onNext,
}: StepBasicsProps) {
  function handleNext(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Campaign name is required");
      return;
    }
    if (!callingNumberId) {
      toast.error("Please select an outbound caller phone number");
      return;
    }
    onNext();
  }

  return (
    <form onSubmit={handleNext} className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-primary/10 text-brand-primary font-bold text-sm">
              1
            </div>
            <div>
              <h3 className="text-base font-semibold text-text-primary">
                Campaign Information
              </h3>
              <p className="text-xs text-text-secondary">
                Set the foundational identity and outbound caller phone number for your campaign.
              </p>
            </div>
          </div>
        </CardHeader>
        <CardBody className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">
              Campaign Name <span className="text-accent-red">*</span>
            </label>
            <Input
              value={name}
              onChange={(e) => onChange("name", e.target.value)}
              placeholder="e.g. Q4 Inbound Follow-up or Product Demo Outreach"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">
              Description <span className="text-text-muted text-xs font-normal">(Optional)</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => onChange("description", e.target.value)}
              rows={3}
              placeholder="Brief context about this campaign's target audience and business goal..."
              className="w-full rounded-md border border-border-default bg-bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-brand-primary focus:outline-none focus:ring-1 focus:ring-brand-primary"
            />
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Phone className="h-5 w-5 text-brand-primary" />
              <div>
                <h3 className="text-base font-semibold text-text-primary">
                  Outbound Caller Number
                </h3>
                <p className="text-xs text-text-secondary">
                  The verified phone number your leads will see on their caller ID.
                </p>
              </div>
            </div>
            <span className="text-xs font-medium text-text-muted">
              {phoneNumbers.length} number{phoneNumbers.length !== 1 ? "s" : ""} available
            </span>
          </div>
        </CardHeader>
        <CardBody className="space-y-4">
          {phoneNumbers.length === 0 ? (
            <div className="flex items-start gap-3 rounded-lg border border-accent-amber/30 bg-accent-amber/5 p-4 text-xs text-accent-amber">
              <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-sm">No phone numbers found</p>
                <p className="mt-1">
                  You need an active telephony number configured to make outbound calls. Please purchase or link a phone number first in Settings &gt; Phone Numbers.
                </p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {phoneNumbers.map((p) => {
                const isSelected = p.id === callingNumberId;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => onChange("calling_number_id", p.id)}
                    className={`flex flex-col text-left p-4 rounded-xl border transition-all ${
                      isSelected
                        ? "border-brand-primary bg-brand-primary/5 ring-2 ring-brand-primary/30"
                        : "border-border-default bg-bg-surface hover:border-border-strong hover:bg-bg-subtle"
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="font-semibold text-sm text-text-primary font-mono">
                        {p.number}
                      </span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                          p.status === "active"
                            ? "bg-accent-green/10 text-accent-green border border-accent-green/20"
                            : "bg-bg-subtle text-text-muted"
                        }`}
                      >
                        {p.status}
                      </span>
                    </div>
                    {p.display_name && (
                      <span className="text-xs text-text-secondary mt-1">
                        {p.display_name}
                      </span>
                    )}
                    <span className="text-[11px] text-text-muted mt-2 capitalize">
                      Provider: {p.provider || "Standard"}
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          <div className="flex items-center gap-2 text-xs text-text-muted bg-bg-subtle p-3 rounded-lg">
            <Info className="h-4 w-4 text-brand-primary flex-shrink-0" />
            <span>
              Calls will originate from this number and adhere to local telecommunications regulations.
            </span>
          </div>
        </CardBody>
      </Card>

      <div className="flex justify-end pt-2">
        <Button
          type="submit"
          variant="primary"
          className="gap-2 px-6"
          disabled={phoneNumbers.length === 0}
        >
          Next: AI Agent & Criteria
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </form>
  );
}
