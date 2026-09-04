import { ReactNode } from "react";

/** A sharp-edged bordered panel — the base surface of the dashboard. */
export function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`border border-line bg-panel ${className}`}>{children}</div>
  );
}

/** A large metric tile (mirrors Groq's Token Usage / Total Spend cards). */
export function Metric({
  label,
  value,
  sub,
  accent = false,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <Panel className="p-5">
      <div className="text-[11px] uppercase tracking-wider text-muted">{label}</div>
      <div
        className={`mt-3 text-3xl font-semibold tabular-nums ${
          accent ? "text-accent" : "text-fg"
        }`}
      >
        {value}
      </div>
      {sub ? <div className="mt-1 text-xs text-faint">{sub}</div> : null}
    </Panel>
  );
}

const STATUS_STYLES: Record<string, string> = {
  booked: "border-good/40 text-good",
  qualified: "border-good/40 text-good",
  qualifying: "border-warn/40 text-warn",
  lost: "border-bad/40 text-bad",
  not_interested: "border-bad/40 text-bad",
  callback: "border-warn/40 text-warn",
  new: "border-line-strong text-muted",
  completed: "border-line-strong text-muted",
  active: "border-accent/50 text-accent",
};

export function Badge({ value }: { value: string | null }) {
  if (!value) return <span className="text-faint">—</span>;
  const style = STATUS_STYLES[value] ?? "border-line-strong text-muted";
  return (
    <span
      className={`inline-block border px-2 py-0.5 text-[11px] uppercase tracking-wide ${style}`}
    >
      {value.replace(/_/g, " ")}
    </span>
  );
}

/** A 0-100 score shown as a value + thin bar. */
export function Score({ value }: { value: number | null }) {
  if (value == null) return <span className="text-faint">—</span>;
  const color = value >= 70 ? "bg-good" : value >= 40 ? "bg-warn" : "bg-bad";
  return (
    <div className="flex items-center gap-2">
      <span className="w-8 tabular-nums text-fg">{value}</span>
      <div className="h-1.5 w-16 bg-panel-2 border border-line">
        <div className={`h-full ${color}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}
