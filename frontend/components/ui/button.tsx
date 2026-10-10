import React from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { Loader2 } from "lucide-react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "link";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  asChild?: boolean;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-white hover:bg-accent-hover focus-visible:ring-accent/40",
  secondary:
    "bg-surface-subtle border border-border text-text-primary hover:bg-[var(--color-border)] focus-visible:ring-border",
  ghost:
    "bg-transparent text-text-secondary hover:bg-surface-subtle hover:text-text-primary focus-visible:ring-border",
  danger:
    "bg-danger text-white hover:opacity-90 focus-visible:ring-danger/40",
  link:
    "bg-transparent text-accent underline-offset-4 hover:underline p-0 h-auto focus-visible:ring-accent/40",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-xs gap-1.5",
  md: "h-9 px-4 text-sm gap-2",
  lg: "h-11 px-5 text-base gap-2",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  className,
  children,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      disabled={isDisabled}
      className={twMerge(
        clsx(
          "inline-flex items-center justify-center rounded-md font-medium transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1",
          "disabled:pointer-events-none disabled:opacity-50",
          variantClasses[variant],
          variant !== "link" && sizeClasses[size],
          className
        )
      )}
      {...props}
    >
      {loading && (
        <Loader2
          className={clsx("animate-spin shrink-0", size === "sm" ? "h-3 w-3" : "h-4 w-4")}
        />
      )}
      {children}
    </button>
  );
}
