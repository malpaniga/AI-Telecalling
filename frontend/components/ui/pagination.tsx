"use client";

import React from "react";
import { clsx } from "clsx";
import { ChevronLeft, ChevronRight } from "lucide-react";

export interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  className?: string;
}

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  className,
}: PaginationProps) {
  const totalPages = Math.ceil(total / pageSize);
  const from = Math.min((page - 1) * pageSize + 1, total);
  const to = Math.min(page * pageSize, total);

  if (totalPages <= 1) {
    return (
      <div className={clsx("text-xs text-text-muted text-right", className)}>
        {total} result{total !== 1 ? "s" : ""}
      </div>
    );
  }

  // Build page window (max 5 visible pages)
  const windowSize = 5;
  let startPage = Math.max(1, page - Math.floor(windowSize / 2));
  const endPage = Math.min(totalPages, startPage + windowSize - 1);
  startPage = Math.max(1, endPage - windowSize + 1);
  const pages = Array.from(
    { length: endPage - startPage + 1 },
    (_, i) => startPage + i
  );

  return (
    <div
      className={clsx(
        "flex items-center justify-between gap-4 text-sm",
        className
      )}
    >
      <span className="text-xs text-text-muted">
        Showing {from}–{to} of {total}
      </span>

      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border text-text-secondary hover:bg-surface-subtle disabled:pointer-events-none disabled:opacity-40 transition-colors"
          aria-label="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>

        {startPage > 1 && (
          <>
            <PageButton current={page} target={1} onClick={onPageChange} />
            {startPage > 2 && (
              <span className="px-1 text-text-muted text-xs">…</span>
            )}
          </>
        )}

        {pages.map((p) => (
          <PageButton key={p} current={page} target={p} onClick={onPageChange} />
        ))}

        {endPage < totalPages && (
          <>
            {endPage < totalPages - 1 && (
              <span className="px-1 text-text-muted text-xs">…</span>
            )}
            <PageButton current={page} target={totalPages} onClick={onPageChange} />
          </>
        )}

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border text-text-secondary hover:bg-surface-subtle disabled:pointer-events-none disabled:opacity-40 transition-colors"
          aria-label="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function PageButton({
  current,
  target,
  onClick,
}: {
  current: number;
  target: number;
  onClick: (p: number) => void;
}) {
  const active = current === target;
  return (
    <button
      onClick={() => onClick(target)}
      aria-current={active ? "page" : undefined}
      className={clsx(
        "inline-flex h-8 min-w-[2rem] items-center justify-center rounded-md px-2 text-xs font-medium transition-colors",
        active
          ? "bg-accent text-white border border-accent"
          : "border border-border text-text-secondary hover:bg-surface-subtle"
      )}
    >
      {target}
    </button>
  );
}
