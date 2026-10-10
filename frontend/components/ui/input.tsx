import React from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// ---------------------------------------------------------------------------
// Shared field wrapper
// ---------------------------------------------------------------------------

interface FieldWrapperProps {
  label?: string;
  error?: string;
  hint?: string;
  required?: boolean;
  id?: string;
  children: React.ReactNode;
}

export function FieldWrapper({
  label,
  error,
  hint,
  required,
  id,
  children,
}: FieldWrapperProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label
          htmlFor={id}
          className="text-sm font-medium text-text-primary"
        >
          {label}
          {required && (
            <span className="ml-0.5 text-danger" aria-hidden>
              *
            </span>
          )}
        </label>
      )}
      {children}
      {error && (
        <p className="text-xs text-danger" role="alert">
          {error}
        </p>
      )}
      {hint && !error && (
        <p className="text-xs text-text-muted">{hint}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Base input class builder
// ---------------------------------------------------------------------------

function inputClasses(hasError?: boolean, className?: string) {
  return twMerge(
    clsx(
      "w-full rounded-md border bg-surface px-3 py-2 text-sm text-text-primary",
      "placeholder:text-text-muted",
      "transition-colors",
      "focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent",
      "disabled:cursor-not-allowed disabled:opacity-50",
      hasError
        ? "border-danger focus:ring-danger/30 focus:border-danger"
        : "border-border hover:border-border-strong",
      className
    )
  );
}

// ---------------------------------------------------------------------------
// Input
// ---------------------------------------------------------------------------

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, id, required, className, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
    return (
      <FieldWrapper
        label={label}
        error={error}
        hint={hint}
        required={required}
        id={inputId}
      >
        <input
          ref={ref}
          id={inputId}
          required={required}
          className={inputClasses(!!error, className)}
          {...props}
        />
      </FieldWrapper>
    );
  }
);
Input.displayName = "Input";

// ---------------------------------------------------------------------------
// Textarea
// ---------------------------------------------------------------------------

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, hint, id, required, className, rows = 3, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
    return (
      <FieldWrapper
        label={label}
        error={error}
        hint={hint}
        required={required}
        id={inputId}
      >
        <textarea
          ref={ref}
          id={inputId}
          required={required}
          rows={rows}
          className={clsx(inputClasses(!!error, className), "resize-y")}
          {...props}
        />
      </FieldWrapper>
    );
  }
);
Textarea.displayName = "Textarea";

// ---------------------------------------------------------------------------
// Select
// ---------------------------------------------------------------------------

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  hint?: string;
  options?: Array<{ value: string; label: string }>;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  (
    { label, error, hint, id, required, options, className, children, ...props },
    ref
  ) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
    return (
      <FieldWrapper
        label={label}
        error={error}
        hint={hint}
        required={required}
        id={inputId}
      >
        <select
          ref={ref}
          id={inputId}
          required={required}
          className={clsx(
            inputClasses(!!error, className),
            "appearance-none bg-[url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2377716B' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")] bg-no-repeat bg-[right_12px_center] pr-8"
          )}
          {...props}
        >
          {options
            ? options.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))
            : children}
        </select>
      </FieldWrapper>
    );
  }
);
Select.displayName = "Select";
