import React from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export type BadgeVariant =
  | "default"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "accent";

export interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  default:
    "bg-surface-subtle text-text-secondary border border-border",
  success:
    "bg-[#EBF7F2] text-success border border-[#C0E8D5]",
  warning:
    "bg-[#FEF6E7] text-warning border border-[#F5D99A]",
  danger:
    "bg-[#FDEEEE] text-danger border border-[#F2C0C0]",
  info:
    "bg-[#EBF2FC] text-info border border-[#B8D0EF]",
  accent:
    "bg-accent-subtle text-accent border border-[#F5C5A8]",
};

export function Badge({ variant = "default", children, className }: BadgeProps) {
  return (
    <span
      className={twMerge(
        clsx(
          "inline-flex items-center rounded-sm px-2 py-0.5 text-xs font-medium",
          variantClasses[variant],
          className
        )
      )}
    >
      {children}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Status → variant mapping helpers
// ---------------------------------------------------------------------------

type StatusVariant = BadgeVariant;

const STATUS_MAP: Record<string, StatusVariant> = {
  // Success states
  running: "success",
  active: "success",
  connected: "success",
  qualified: "success",
  completed: "success",
  paid: "success",
  verified: "success",
  confirmed: "success",
  appointment_set: "success",
  booked: "success",

  // Default / neutral states
  draft: "default",
  new: "default",
  initiating: "default",
  ringing: "default",
  scheduled: "default",
  pending: "default",
  trialing: "info",

  // Warning states
  paused: "warning",
  callback: "warning",
  contacted: "warning",
  cancel_at_period_end: "warning",
  no_show: "warning",

  // Danger states
  cancelled: "danger",
  failed: "danger",
  no_answer: "danger",
  not_interested: "danger",
  busy: "danger",
  suspended: "danger",
  expired: "danger",
  refunded: "danger",
};

export function statusVariant(status: string): StatusVariant {
  return STATUS_MAP[status.toLowerCase()] ?? "default";
}

export function StatusBadge({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  const variant = statusVariant(status);
  const label = status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <Badge variant={variant} className={className}>
      {label}
    </Badge>
  );
}
