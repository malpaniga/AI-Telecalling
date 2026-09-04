"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/call", label: "New Call" },
  { href: "/calls", label: "Calls" },
  { href: "/leads", label: "Leads" },
];

export function Sidebar() {
  const path = usePathname();
  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-line bg-panel">
      <div className="flex h-14 items-center gap-2 border-b border-line px-5">
        <div className="flex h-6 w-6 items-center justify-center bg-accent text-ink">
          <span className="text-sm font-bold">A</span>
        </div>
        <span className="text-sm font-semibold tracking-tight">Ava Console</span>
      </div>
      <nav className="flex flex-col p-2">
        {LINKS.map((l) => {
          const active = l.href === "/" ? path === "/" : path.startsWith(l.href);
          return (
            <Link
              key={l.href}
              href={l.href}
              className={`px-3 py-2 text-sm border-l-2 transition-colors ${
                active
                  ? "border-accent bg-panel-2 text-fg"
                  : "border-transparent text-muted hover:text-fg hover:bg-panel-2"
              }`}
            >
              {l.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto border-t border-line p-4 text-[11px] text-faint">
        Real Estate Voice Agent
        <br />
        gpt-oss · whisper · piper
      </div>
    </aside>
  );
}

export function Topbar({ title }: { title: string }) {
  return (
    <div className="flex h-14 items-center justify-between border-b border-line px-6">
      <h1 className="text-sm font-medium tracking-tight text-fg">{title}</h1>
      <div className="flex items-center gap-2 text-xs text-muted">
        <span className="inline-block h-1.5 w-1.5 bg-good" />
        live
      </div>
    </div>
  );
}
