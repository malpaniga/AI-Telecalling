"use client";

import React, { useState, useEffect } from "react";
import toast from "react-hot-toast";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { api, Campaign, CallingHoursConfig } from "@/lib/api";

export interface DayOption {
  label: string;
  full: string;
  value: number; // 0=Sunday, 1=Monday, ..., 6=Saturday
}

export const DAY_OPTIONS: DayOption[] = [
  { label: "Mon", full: "Monday", value: 1 },
  { label: "Tue", full: "Tuesday", value: 2 },
  { label: "Wed", full: "Wednesday", value: 3 },
  { label: "Thu", full: "Thursday", value: 4 },
  { label: "Fri", full: "Friday", value: 5 },
  { label: "Sat", full: "Saturday", value: 6 },
  { label: "Sun", full: "Sunday", value: 0 },
];

export const TIMEZONE_OPTIONS = [
  { value: "Asia/Kolkata", label: "IST (Asia/Kolkata)" },
  { value: "Asia/Dubai", label: "GST (Asia/Dubai)" },
  { value: "UTC", label: "UTC" },
];

interface CallingHoursModalProps {
  isOpen: boolean;
  onClose: () => void;
  campaignId: string;
  initialCallingHours?: CallingHoursConfig | null;
  initialTimezone?: string;
  onUpdated: (campaign: Campaign) => void;
}

export function CallingHoursModal({
  isOpen,
  onClose,
  campaignId,
  initialCallingHours,
  initialTimezone = "Asia/Kolkata",
  onUpdated,
}: CallingHoursModalProps) {
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("18:00");
  const [selectedDays, setSelectedDays] = useState<number[]>([1, 2, 3, 4, 5]);
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setStartTime(initialCallingHours?.start_time || "09:00");
      setEndTime(initialCallingHours?.end_time || "18:00");
      setSelectedDays(
        initialCallingHours?.days_of_week && initialCallingHours.days_of_week.length > 0
          ? initialCallingHours.days_of_week
          : [1, 2, 3, 4, 5]
      );
      setTimezone(initialTimezone || "Asia/Kolkata");
    }
  }, [isOpen, initialCallingHours, initialTimezone]);

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

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (selectedDays.length === 0) {
      toast.error("Please select at least one calling day");
      return;
    }
    if (!startTime || !endTime) {
      toast.error("Please provide both start and end times");
      return;
    }

    setSaving(true);
    try {
      const updated = await api.campaigns.update(campaignId, {
        timezone,
        calling_hours: {
          start_time: startTime,
          end_time: endTime,
          days_of_week: selectedDays,
        },
      });
      toast.success("Calling hours updated");
      onUpdated(updated);
      onClose();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to update calling hours");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Configure Calling Hours" size="md">
      <form onSubmit={handleSave} className="space-y-4">
        <p className="text-xs text-text-secondary">
          Configure the active days and time window when outbound calls are allowed for this campaign.
        </p>

        <div>
          <Select
            label="Timezone"
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            options={TIMEZONE_OPTIONS}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Start Time"
            type="time"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            required
          />
          <Input
            label="End Time"
            type="time"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
            required
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
                className={`px-3 py-1.5 text-xs rounded-full border transition-colors cursor-pointer ${
                  selectedDays.includes(day.value)
                    ? "border-accent bg-accent text-white font-medium"
                    : "border-border text-text-secondary hover:border-accent-hover"
                }`}
              >
                {day.full}
              </button>
            ))}
          </div>
          {selectedDays.length === 0 && (
            <p className="text-xs text-danger mt-1">Please select at least one calling day.</p>
          )}
        </div>

        <div className="flex justify-end gap-2 pt-4 border-t border-border">
          <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" size="sm" loading={saving} disabled={selectedDays.length === 0}>
            Save Changes
          </Button>
        </div>
      </form>
    </Modal>
  );
}
