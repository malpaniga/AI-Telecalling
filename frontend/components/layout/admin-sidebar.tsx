"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import {
  LayoutDashboard,
  Building2,
  CreditCard,
  Package,
  Receipt,
  Hash,
  Mic2,
  Plug,
  Activity,
  BarChart2,
  ScrollText,
  LogOut,
  X,
  Shield,
  BrainCircuit,
  Volume2,
  AudioWaveform,
  Bot,
  Wand2,
  Settings,
} from "lucide-react";
import { useAuth } from "@/contexts/auth-context";

// ---------------------------------------------------------------------------
// Admin nav links
// ---------------------------------------------------------------------------

const ADMIN_LINKS = [
  { href: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/wizard", label: "Setup Wizard", icon: Wand2 },
  { href: "/admin/organizations", label: "Organizations", icon: Building2 },
  { href: "/admin/subscriptions", label: "Subscriptions", icon: CreditCard },
  { href: "/admin/calling-packs", label: "Calling Packs", icon: Package },
  { href: "/admin/payments", label: "Payments", icon: Receipt },
  { href: "/admin/phone-numbers", label: "Phone Numbers", icon: Hash },
  { href: "/admin/voice-profiles", label: "Voice Profiles", icon: Mic2 },
  { href: "/admin/providers", label: "Providers", icon: Plug },
  { href: "/admin/models", label: "AI Models", icon: BrainCircuit },
  { href: "/admin/providers/tts", label: "TTS Config", icon: Volume2 },
  { href: "/admin/providers/stt", label: "STT Config", icon: AudioWaveform },
  { href: "/admin/providers/llm", label: "LLM Config", icon: Bot },
  { href: "/admin/usage", label: "Usage", icon: Activity },
  { href: "/admin/analytics", label: "Analytics", icon: BarChart2 },
  { href: "/admin/audit-logs", label: "Audit Logs", icon: ScrollText },
  { href: "/admin/settings", label: "Settings", icon: Settings },
] as const;

// ---------------------------------------------------------------------------
// AdminSidebar component
// ---------------------------------------------------------------------------

export interface AdminSidebarProps {
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function AdminSidebar({
  isMobileOpen = false,
  onMobileClose,
}: AdminSidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : "??";

  return (
    <>
      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={onMobileClose}
          aria-hidden
        />
      )}

      {/* Sidebar panel — accent left border signals admin context */}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-border transition-transform duration-200",
          "bg-[#1A1814]", // dark admin sidebar to visually differentiate
          "lg:relative lg:translate-x-0",
          isMobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Accent left border */}
        <div className="absolute inset-y-0 left-0 w-0.5 bg-accent" aria-hidden />

        {/* Logo */}
        <div className="flex h-14 items-center gap-2.5 border-b border-white/10 px-5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-accent">
            <Shield className="h-4 w-4 text-white" />
          </div>
          <span className="text-sm font-semibold text-white tracking-tight">
            Super Admin
          </span>
          {isMobileOpen && onMobileClose && (
            <button
              onClick={onMobileClose}
              className="ml-auto rounded-md p-1 text-white/50 hover:text-white lg:hidden"
              aria-label="Close sidebar"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {ADMIN_LINKS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                onClick={onMobileClose}
                className={clsx(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-accent/20 text-accent font-medium"
                    : "text-white/60 hover:bg-white/10 hover:text-white"
                )}
              >
                <Icon
                  className={clsx(
                    "h-4 w-4 shrink-0",
                    active ? "text-accent" : "text-white/40"
                  )}
                />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="border-t border-white/10 p-3">
          <div className="flex items-center gap-2.5 rounded-md p-2">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent/20 text-accent text-xs font-semibold">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-white truncate">
                {user?.email ?? ""}
              </p>
              <p className="text-[10px] text-white/40 capitalize truncate">
                {user?.role?.replace(/_/g, " ") ?? ""}
              </p>
            </div>
            <button
              onClick={() => logout()}
              className="shrink-0 rounded-md p-1 text-white/40 hover:text-accent hover:bg-white/10 transition-colors"
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
