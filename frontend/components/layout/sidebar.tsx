"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import {
  LayoutDashboard,
  Bot,
  Megaphone,
  Users,
  Phone,
  Calendar,
  Hash,
  CreditCard,
  BookOpen,
  BarChart2,
  UsersRound,
  Receipt,
  Settings,
  LogOut,
  Menu,
  X,
  Mic2,
} from "lucide-react";
import { useAuth } from "@/contexts/auth-context";

// ---------------------------------------------------------------------------
// Nav link definitions
// ---------------------------------------------------------------------------

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/agents", label: "AI Agents", icon: Bot },
  { href: "/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/calls", label: "Calls", icon: Phone },
  { href: "/appointments", label: "Appointments", icon: Calendar },
  { href: "/phone-numbers", label: "Phone Numbers", icon: Hash },
  { href: "/credits", label: "Credits", icon: CreditCard },
  { href: "/knowledge", label: "Knowledge Base", icon: BookOpen },
  { href: "/analytics", label: "Analytics", icon: BarChart2 },
  { href: "/team", label: "Team", icon: UsersRound },
  { href: "/billing", label: "Billing", icon: Receipt },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

// ---------------------------------------------------------------------------
// Sidebar component
// ---------------------------------------------------------------------------

export interface SidebarProps {
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function Sidebar({ isMobileOpen = false, onMobileClose }: SidebarProps) {
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

      {/* Sidebar panel */}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-40 flex w-60 flex-col bg-surface border-r border-border transition-transform duration-200",
          "lg:relative lg:translate-x-0",
          isMobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Logo */}
        <div className="flex h-14 items-center gap-2.5 border-b border-border px-5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-accent">
            <Mic2 className="h-4 w-4 text-white" />
          </div>
          <span className="text-sm font-semibold text-text-primary tracking-tight">
            NivLabs-Connect
          </span>
          {isMobileOpen && onMobileClose && (
            <button
              onClick={onMobileClose}
              className="ml-auto rounded-md p-1 text-text-muted hover:text-text-primary lg:hidden"
              aria-label="Close sidebar"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {NAV_LINKS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                onClick={onMobileClose}
                className={clsx(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-accent-subtle text-accent font-medium"
                    : "text-text-secondary hover:bg-surface-subtle hover:text-text-primary"
                )}
              >
                <Icon
                  className={clsx(
                    "h-4 w-4 shrink-0",
                    active ? "text-accent" : "text-text-muted"
                  )}
                />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="border-t border-border p-3">
          <div className="flex items-center gap-2.5 rounded-md p-2">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-subtle text-accent text-xs font-semibold">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-text-primary truncate">
                {user?.email ?? ""}
              </p>
              <p className="text-[10px] text-text-muted capitalize truncate">
                {user?.role?.replace(/_/g, " ") ?? ""}
              </p>
            </div>
            <button
              onClick={() => logout()}
              className="shrink-0 rounded-md p-1 text-text-muted hover:text-danger hover:bg-[#FDEEEE] transition-colors"
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
