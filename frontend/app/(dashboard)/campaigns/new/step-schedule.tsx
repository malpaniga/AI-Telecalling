"use client";

import React from "react";
import {
  Clock,
  Calendar,
  Layers,
  Repeat,
  ArrowRight,
  ArrowLeft,
  Info,
  ShieldCheck,
} from "lucide-react";
import toast from "react-hot-toast";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";

const TIMEZONE_OPTIONS = [
  { value: "Asia/Kolkata", label: "IST (Asia/Kolkata - GMT+5:30)" },
  { value: "Asia/Dubai", label: "GST (Asia/Dubai - GMT+4:00)" },
  { value: "Europe/London", label: "GMT/BST (Europe/London)" },
  { value: "America/New_York", label: "EST/EDT (America/New_York)" },
  { value: "America/Los_Angeles", label: "PST/PDT (America/Los_Angeles)" },
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

interface StepScheduleProps {
  timezone: string;
  startTime: string;
  endTime: string;
  selectedDays: number[];
  maxConcurrentCalls: string;
  maxAttempts: string;
  retryDelayMinutes: string;
  scheduledAt: string;
  detectVoicemail: boolean;
  onChange: (field: string, value: string) => void;
  onToggleVoicemail: (val: boolean) => void;
  onToggleDay: (dayVal: number) => void;
  onSetWeekdaysOnly: () => void;
  onSetAllDays: () => void;
  onBack: () => void;
  onNext: () => void;
}

export function StepSchedule({
  timezone,
  startTime,
  endTime,
  selectedDays,
  maxConcurrentCalls,
  maxAttempts,
  retryDelayMinutes,
  scheduledAt,
  detectVoicemail,
  onChange,
  onToggleVoicemail,
  onToggleDay,
  onSetWeekdaysOnly,
  onSetAllDays,
  onBack,
  onNext,
}: StepScheduleProps) {
  function handleNext(e: React.FormEvent) {
    e.preventDefault();
    if (selectedDays.length === 0) {
      toast.error("Please select at least one active calling day");
      return;
    }
    if (startTime >= endTime) {
      toast.error("Start time must be before end time");
      return;
    }
    const conc = parseInt(maxConcurrentCalls, 10);
    if (isNaN(conc) || conc < 1) {
      toast.error("Max concurrent calls must be at least 1");
      return;
    }
    onNext();
  }

  return (
    <form onSubmit={handleNext} className="space-y-6">
      {/* Calling Window Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/10 text-accent font-bold text-sm">
              3
            </div>
            <div>
              <h3 className="text-base font-semibold text-text-primary">
                Calling Hours & Operating Schedule
              </h3>
              <p className="text-xs text-text-secondary">
                Ensure outbound calls are placed strictly within appropriate local business hours.
              </p>
            </div>
          </div>
        </CardHeader>
        <CardBody className="space-y-5">
          {/* Timezone */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">
              Campaign Timezone
            </label>
            <Select
              value={timezone}
              onChange={(e) => onChange("timezone", e.target.value)}
              className="w-full"
            >
              {TIMEZONE_OPTIONS.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </Select>
          </div>

          {/* Active Days */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-text-primary">
                Active Calling Days <span className="text-accent-red">*</span>
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={onSetWeekdaysOnly}
                  className="text-xs text-accent hover:underline"
                >
                  Weekdays
                </button>
                <span className="text-xs text-text-muted">•</span>
                <button
                  type="button"
                  onClick={onSetAllDays}
                  className="text-xs text-accent hover:underline"
                >
                  All Days
                </button>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {DAY_OPTIONS.map((day) => {
                const isSelected = selectedDays.includes(day.value);
                return (
                  <button
                    key={day.value}
                    type="button"
                    onClick={() => onToggleDay(day.value)}
                    className={`flex-1 min-w-[50px] py-2 px-3 rounded-xl border text-center text-xs font-semibold transition-all ${
                      isSelected
                        ? "border-accent bg-accent text-white shadow-sm"
                        : "border-border bg-surface text-text-secondary hover:border-border-strong hover:bg-surface-subtle"
                    }`}
                  >
                    {day.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Start and End Time */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">
                Start Time
              </label>
              <div className="relative">
                <Clock className="absolute left-3 top-2.5 h-4 w-4 text-text-muted" />
                <Input
                  type="time"
                  value={startTime}
                  onChange={(e) => onChange("start_time", e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">
                End Time
              </label>
              <div className="relative">
                <Clock className="absolute left-3 top-2.5 h-4 w-4 text-text-muted" />
                <Input
                  type="time"
                  value={endTime}
                  onChange={(e) => onChange("end_time", e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-text-muted bg-surface-subtle p-3 rounded-lg">
            <Info className="h-4 w-4 text-accent flex-shrink-0" />
            <span>
              Calls outside these hours are automatically queued and paused until the next available window.
            </span>
          </div>
        </CardBody>
      </Card>

      {/* Voicemail & Call Screening Detection (AMD) Card */}
      <Card className="border-accent/20 bg-gradient-to-r from-surface to-surface-subtle">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-accent" />
              <div>
                <h3 className="text-base font-semibold text-text-primary">
                  Voicemail & Call Screening Detection (AMD)
                </h3>
                <p className="text-xs text-text-secondary">
                  Automatically disconnect when Apple Siri, Google Call Screen, or carrier answering machines answer.
                </p>
              </div>
            </div>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              Credit Saver
            </span>
          </div>
        </CardHeader>
        <CardBody className="space-y-4">
          <label className="flex items-start gap-3 p-3.5 rounded-xl border border-border bg-surface cursor-pointer hover:bg-surface-subtle transition-colors shadow-sm">
            <input
              type="checkbox"
              checked={detectVoicemail}
              onChange={(e) => onToggleVoicemail(e.target.checked)}
              className="mt-1 h-4 w-4 rounded border-border text-accent focus:ring-accent"
            />
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-text-primary">
                  Detect Voicemail & Siri/Google Screening (Recommended)
                </span>
                <span className="text-[11px] font-semibold text-accent bg-accent/10 px-2 py-0.5 rounded">
                  Closes &le; 1 min
                </span>
              </div>
              <p className="text-xs text-text-muted leading-relaxed">
                When enabled, the AI stops talking immediately upon detecting Apple Live Voicemail, Google Call Screen, or carrier greetings. The call closes within seconds, bills only for actual talk time (&le; 1 min / 1 credit), and reschedules the lead for retry.
              </p>
            </div>
          </label>
        </CardBody>
      </Card>

      {/* Concurrency and Retry Policy Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-accent" />
            <div>
              <h3 className="text-base font-semibold text-text-primary">
                Call Concurrency & Retry Settings
              </h3>
              <p className="text-xs text-text-secondary">
                Control telephony line throughput and unreached lead retry rules.
              </p>
            </div>
          </div>
        </CardHeader>
        <CardBody className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">
                Max Concurrent Calls
              </label>
              <Input
                type="number"
                min="1"
                max="50"
                value={maxConcurrentCalls}
                onChange={(e) => onChange("max_concurrent_calls", e.target.value)}
                required
              />
              <span className="text-[11px] text-text-muted mt-1 block">
                Simultaneous dialing lines
              </span>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">
                Max Attempts Per Lead
              </label>
              <Input
                type="number"
                min="1"
                max="10"
                value={maxAttempts}
                onChange={(e) => onChange("max_attempts", e.target.value)}
                required
              />
              <span className="text-[11px] text-text-muted mt-1 block">
                Number of retry dials
              </span>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">
                Retry Delay (Minutes)
              </label>
              <Input
                type="number"
                min="5"
                max="1440"
                value={retryDelayMinutes}
                onChange={(e) => onChange("retry_delay_minutes", e.target.value)}
                required
              />
              <span className="text-[11px] text-text-muted mt-1 block">
                Wait between attempts
              </span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-primary mb-1">
              Scheduled Launch Date & Time <span className="text-text-muted text-xs font-normal">(Optional)</span>
            </label>
            <Input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => onChange("scheduled_at", e.target.value)}
            />
            <span className="text-[11px] text-text-muted mt-1 block">
              Leave blank to enable immediate manual campaign starting.
            </span>
          </div>
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
          Back: AI Agent
        </Button>
        <Button
          type="submit"
          variant="primary"
          className="gap-2 px-6"
        >
          Next: Select Contacts
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </form>
  );
}
