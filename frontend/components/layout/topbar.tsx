"use client";

import React from "react";
import { clsx } from "clsx";
import { Menu, Bell, ChevronRight } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";

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
  const { user } = useAuth();

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : "??";

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

      {/* Right: org name + notifications + avatar */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Notifications placeholder */}
        <button
          className="flex h-8 w-8 items-center justify-center rounded-md text-text-muted hover:text-text-primary hover:bg-surface-subtle transition-colors"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
        </button>

        {/* Avatar */}
        <div
          className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-subtle text-accent text-xs font-semibold"
          title={user?.email}
          aria-label="User menu"
        >
          {initials}
        </div>
      </div>
    </header>
  );
}
