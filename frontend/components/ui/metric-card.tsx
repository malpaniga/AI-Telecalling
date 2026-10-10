import React from "react";
import type { LucideIcon } from "lucide-react";
import { clsx } from "clsx";
import { TrendingUp, TrendingDown } from "lucide-react";
import { Card } from "./card";

export interface MetricCardProps {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: LucideIcon;
  accent?: boolean;
  className?: string;
}

export function MetricCard({
  label,
  value,
  change,
  changeLabel,
  icon: Icon,
  accent = false,
  className,
}: MetricCardProps) {
  const isPositive = change !== undefined && change >= 0;
  const changeColor = isPositive ? "text-success" : "text-danger";
  const ChangeIcon = isPositive ? TrendingUp : TrendingDown;

  return (
    <Card className={clsx("p-5", className)}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-1 min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-text-muted truncate">
            {label}
          </p>
          <p
            className={clsx(
              "text-2xl font-semibold tabular-nums",
              accent ? "text-accent" : "text-text-primary"
            )}
          >
            {value}
          </p>
          {change !== undefined && (
            <div className={clsx("flex items-center gap-1 text-xs", changeColor)}>
              <ChangeIcon className="h-3 w-3 shrink-0" />
              <span>
                {isPositive ? "+" : ""}
                {change.toFixed(1)}%{changeLabel ? ` ${changeLabel}` : ""}
              </span>
            </div>
          )}
        </div>
        {Icon && (
          <div
            className={clsx(
              "shrink-0 rounded-md p-2",
              accent
                ? "bg-accent-subtle text-accent"
                : "bg-surface-subtle text-text-secondary"
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
    </Card>
  );
}
