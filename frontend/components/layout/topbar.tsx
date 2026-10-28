"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clsx } from "clsx";
import { Menu, Bell, ChevronRight, Phone, LogOut, Settings } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { useTestAgent } from "@/contexts/test-agent-context";

export interface TopbarProps {
  title: string;
  breadcrumb?: Array<{ label: string; href?: string }>;
  onMenuToggle?: () => void;
  className?: string;
}

export function Topbar({
  title,
  breadcrumb,
  onMenuToggle,
  className,
}: TopbarProps) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const { openTestAgent } = useTestAgent();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : "??";

  const isPlatformUser = user?.role && ["platform_owner", "platform_admin", "billing_admin", "support"].includes(user.role);
  const settingsHref = isPlatformUser ? "/admin/settings" : "/settings";

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setDropdownOpen(false);
      }
    }

    if (dropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [dropdownOpen]);

  const handleLogout = async () => {
    setDropdownOpen(false);
    try {
      await logout();
    } catch (err) {
      console.error("Logout error:", err);
    }
    router.push("/login");
  };

  return (
    <header
      className={clsx(
        "flex h-14 items-center justify-between border-b border-border bg-surface px-4 md:px-6 shrink-0",
        className
      )}
    >
      {/* Left: mobile menu + title / breadcrumb */}
      <div className="flex items-center gap-3 min-w-0">
        {onMenuToggle && (
          <button
            onClick={onMenuToggle}
            className="flex h-8 w-8 items-center justify-center rounded-md text-text-muted hover:text-text-primary hover:bg-surface-subtle transition-colors lg:hidden"
            aria-label="Toggle sidebar"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}

        {breadcrumb && breadcrumb.length > 0 ? (
          <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm min-w-0">
            {breadcrumb.map((crumb, i) => (
              <React.Fragment key={i}>
                {i > 0 && (
                  <ChevronRight className="h-3.5 w-3.5 text-text-muted shrink-0" />
                )}
                {crumb.href ? (
                  <a
                    href={crumb.href}
                    className="text-text-secondary hover:text-text-primary transition-colors truncate"
                  >
                    {crumb.label}
                  </a>
                ) : (
                  <span className="font-medium text-text-primary truncate">
                    {crumb.label}
                  </span>
                )}
              </React.Fragment>
            ))}
          </nav>
        ) : (
          <h1 className="text-sm font-semibold text-text-primary truncate">
            {title}
          </h1>
        )}
      </div>

      {/* Right: Test Agent button + notifications + avatar dropdown */}
      <div className="flex items-center gap-2.5 shrink-0">
        <button
          onClick={() => openTestAgent()}
          title="Try the agent in the playground"
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-black hover:bg-neutral-800 text-white dark:bg-white dark:text-black dark:hover:bg-neutral-200 shadow-sm transition-all active:scale-[0.98]"
        >
          <Phone className="h-3.5 w-3.5 fill-current" />
          <span>Test agent</span>
        </button>

        {/* Notifications placeholder */}
        <button
          className="flex h-8 w-8 items-center justify-center rounded-md text-text-muted hover:text-text-primary hover:bg-surface-subtle transition-colors"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
        </button>

        {/* Avatar & User Dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setDropdownOpen((prev) => !prev)}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-subtle text-accent text-xs font-semibold hover:ring-2 hover:ring-accent/40 transition-all focus:outline-none focus:ring-2 focus:ring-accent cursor-pointer"
            title={user?.email || "User menu"}
            aria-label="User menu"
            aria-expanded={dropdownOpen}
            aria-haspopup="true"
          >
            {initials}
          </button>

          {dropdownOpen && (
            <div
              role="menu"
              aria-orientation="vertical"
              className="absolute right-0 top-full mt-2 w-56 rounded-xl border border-border bg-surface shadow-lg py-1.5 z-50 animate-in fade-in slide-in-from-top-1"
            >
              {/* User details header */}
              <div className="px-3.5 py-2.5 border-b border-border">
                <p className="text-xs font-semibold text-text-primary truncate">
                  {user?.email ?? "Signed in"}
                </p>
                {user?.role && (
                  <p className="text-[11px] text-text-muted capitalize truncate mt-0.5">
                    {user.role.replace(/_/g, " ")}
                  </p>
                )}
              </div>

              {/* Menu items */}
              <div className="py-1">
                <Link
                  href={settingsHref}
                  role="menuitem"
                  onClick={() => setDropdownOpen(false)}
                  className="flex items-center gap-2.5 px-3.5 py-2 text-xs text-text-secondary hover:text-text-primary hover:bg-surface-subtle transition-colors"
                >
                  <Settings className="h-4 w-4 text-text-muted" />
                  <span>Settings</span>
                </Link>
              </div>

              <div className="border-t border-border my-1" />

              {/* Logout button */}
              <div className="py-0.5">
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-danger hover:bg-[#FDEEEE] dark:hover:bg-red-950/20 transition-colors text-left font-medium cursor-pointer"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Log out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
