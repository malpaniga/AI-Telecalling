"use client";

import React from "react";
import { clsx } from "clsx";
import { Spinner } from "./spinner";
import { EmptyState } from "./empty-state";

// ---------------------------------------------------------------------------
// Simple generic DataTable — no TanStack Table v9 type complexity required
// Callers provide column definitions and rows to render.
// ---------------------------------------------------------------------------

export interface ColumnDef<TData> {
  id: string;
  header: React.ReactNode | (() => React.ReactNode);
  cell: (row: TData, index: number) => React.ReactNode;
  className?: string;
}

export interface DataTableProps<TData> {
  columns: ColumnDef<TData>[];
  data: TData[];
  loading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  className?: string;
  rowKey?: (row: TData, index: number) => string;
}

export function DataTable<TData>({
  columns,
  data,
  loading = false,
  emptyTitle = "No results",
  emptyDescription,
  className,
  rowKey,
}: DataTableProps<TData>) {
  return (
    <div className={clsx("w-full overflow-x-auto", className)}>
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-border">
            {columns.map((col) => (
              <th
                key={col.id}
                className={clsx(
                  "px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-text-muted whitespace-nowrap",
                  col.className
                )}
              >
                {typeof col.header === "function" ? col.header() : col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={columns.length} className="py-16 text-center">
                <Spinner size="md" />
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length}>
                <EmptyState title={emptyTitle} description={emptyDescription} />
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr
                key={rowKey ? rowKey(row, i) : i}
                className="border-b border-border last:border-b-0 hover:bg-surface-subtle transition-colors"
              >
                {columns.map((col) => (
                  <td
                    key={col.id}
                    className={clsx("px-4 py-3 text-text-primary", col.className)}
                  >
                    {col.cell(row, i)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Simple HTML table wrappers for ad-hoc tables
// ---------------------------------------------------------------------------

export interface SimpleTableProps {
  headers: string[];
  children: React.ReactNode;
  className?: string;
}

export function SimpleTable({ headers, children, className }: SimpleTableProps) {
  return (
    <div className={clsx("w-full overflow-x-auto", className)}>
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-border">
            {headers.map((h) => (
              <th
                key={h}
                className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-text-muted whitespace-nowrap"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function TableRow({
  children,
  className,
  onClick,
}: {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}) {
  return (
    <tr
      onClick={onClick}
      className={clsx(
        "border-b border-border last:border-b-0 hover:bg-surface-subtle transition-colors",
        onClick && "cursor-pointer",
        className
      )}
    >
      {children}
    </tr>
  );
}

export function TableCell({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <td className={clsx("px-4 py-3 text-text-primary", className)}>
      {children}
    </td>
  );
}
