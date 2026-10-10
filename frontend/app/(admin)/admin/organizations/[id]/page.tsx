"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Wallet, CreditCard, Users, Info } from "lucide-react";
import toast from "react-hot-toast";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { Modal } from "@/components/ui/modal";
import { Input } from "@/components/ui/input";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, Organization, Subscription, User, WalletSummary } from "@/lib/api";
import { formatDateTime, formatINR, formatCredits } from "@/lib/utils";

type Tab = "overview" | "subscription" | "wallet" | "users";

export default function AdminOrgDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("overview");

  // Tab-specific data
  const [sub, setSub] = useState<Subscription | null>(null);
  const [wallet, setWallet] = useState<WalletSummary | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [tabLoading, setTabLoading] = useState(false);

  // Suspend/reactivate
  const [acting, setActing] = useState(false);
  const [showSuspend, setShowSuspend] = useState(false);
  const [suspendReason, setSuspendReason] = useState("");

  // Adjust credits
  const [showAdjust, setShowAdjust] = useState(false);
  const [adjustDelta, setAdjustDelta] = useState("");
  const [adjustReason, setAdjustReason] = useState("");
  const [adjusting, setAdjusting] = useState(false);

  // Load org
  useEffect(() => {
    if (!id) return;
    api.admin.organizations.get(id)
      .then(setOrg)
      .catch((e: unknown) =>
        toast.error(e instanceof Error ? e.message : "Failed to load org")
      )
      .finally(() => setLoading(false));
  }, [id]);

  // Load tab data
  const loadTab = useCallback(
    async (t: Tab) => {
      if (!id) return;
      setTabLoading(true);
      try {
        if (t === "subscription") {
          const subs = await api.admin.subscriptions.list({ limit: 10 });
          const orgSub = subs.find((s) => s.organization_id === id) ?? null;
          setSub(orgSub);
        } else if (t === "wallet") {
          const w = await api.admin.wallets.get(id);
          setWallet(w);
        } else if (t === "users") {
          const us = await api.users.listOrg(id);
          setUsers(us);
        }
      } catch (e: unknown) {
        toast.error(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setTabLoading(false);
      }
    },
    [id]
  );

  useEffect(() => {
    if (tab !== "overview") {
      loadTab(tab);
    }
  }, [tab, loadTab]);

  // Suspend
  async function handleSuspend() {
    if (!id) return;
    setActing(true);
    try {
      await api.admin.organizations.suspend(id, suspendReason || "policy violation");
      toast.success("Organisation suspended");
      setShowSuspend(false);
      setSuspendReason("");
      const updated = await api.admin.organizations.get(id);
      setOrg(updated);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to suspend");
    } finally {
      setActing(false);
    }
  }

  // Reactivate
  async function handleReactivate() {
    if (!id) return;
    setActing(true);
    try {
      await api.admin.organizations.reactivate(id);
      toast.success("Organisation reactivated");
      const updated = await api.admin.organizations.get(id);
      setOrg(updated);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to reactivate");
    } finally {
      setActing(false);
    }
  }

  // Adjust credits
  async function handleAdjust(e: React.FormEvent) {
    e.preventDefault();
    if (!id) return;
    const delta = parseInt(adjustDelta);
    if (isNaN(delta)) {
      toast.error("Enter a valid credit amount");
      return;
    }
    setAdjusting(true);
    try {
      await api.admin.wallets.adjust(id, delta, adjustReason || "admin adjustment");
      toast.success("Credits adjusted");
      setShowAdjust(false);
      setAdjustDelta("");
      setAdjustReason("");
      const w = await api.admin.wallets.get(id);
      setWallet(w);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to adjust credits");
    } finally {
      setAdjusting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }
  if (!org) return null;

  const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: "overview", label: "Overview", icon: <Info className="h-3.5 w-3.5" /> },
    { key: "subscription", label: "Subscription", icon: <CreditCard className="h-3.5 w-3.5" /> },
    { key: "wallet", label: "Wallet", icon: <Wallet className="h-3.5 w-3.5" /> },
    { key: "users", label: "Users", icon: <Users className="h-3.5 w-3.5" /> },
  ];

  return (
    <div className="space-y-6">
      {/* Breadcrumb + actions */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link href="/admin/organizations">
            <Button variant="ghost" size="sm" className="gap-1">
              <ChevronLeft className="h-4 w-4" />
              Back
            </Button>
          </Link>
          <h2 className="text-lg font-semibold text-text-primary">
            {org.name}
          </h2>
          <StatusBadge status={org.status} />
        </div>
        <div className="flex gap-2">
          {org.status === "active" ? (
            <Button
              size="sm"
              variant="danger"
              loading={acting}
              onClick={() => setShowSuspend(true)}
            >
              Suspend
            </Button>
          ) : (
            <Button
              size="sm"
              variant="secondary"
              loading={acting}
              onClick={handleReactivate}
            >
              Reactivate
            </Button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {TABS.map(({ key, label, icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === key
                ? "border-accent text-accent"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            {icon}
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tabLoading && tab !== "overview" ? (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : (
        <>
          {/* Overview */}
          {tab === "overview" && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <h3 className="text-sm font-medium text-text-primary">
                    Organisation Details
                  </h3>
                </CardHeader>
                <CardBody className="space-y-3 text-sm">
                  {[
                    ["Name", org.name],
                    ["Email", org.email],
                    ["Slug", org.slug],
                    ["Verified", org.is_verified ? "Yes" : "No"],
                    ["Created", formatDateTime(org.created_at)],
                  ].map(([label, value]) => (
                    <div key={label as string} className="flex justify-between">
                      <span className="text-text-muted">{label as string}</span>
                      <span className="font-medium text-text-primary">
                        {value as string}
                      </span>
                    </div>
                  ))}
                  <div className="flex justify-between">
                    <span className="text-text-muted">Status</span>
                    <StatusBadge status={org.status} />
                  </div>
                </CardBody>
              </Card>

              <Card>
                <CardHeader>
                  <h3 className="text-sm font-medium text-text-primary">
                    Limits
                  </h3>
                </CardHeader>
                <CardBody className="space-y-3 text-sm">
                  {[
                    ["Max Agents", org.max_agents],
                    ["Max Campaigns", org.max_campaigns],
                    ["Max Concurrent Calls", org.max_concurrent_calls],
                  ].map(([label, value]) => (
                    <div key={label as string} className="flex justify-between">
                      <span className="text-text-muted">{label as string}</span>
                      <span className="font-medium text-text-primary">
                        {value as number}
                      </span>
                    </div>
                  ))}
                </CardBody>
              </Card>
            </div>
          )}

          {/* Subscription */}
          {tab === "subscription" && (
            <Card>
              <CardHeader>
                <h3 className="text-sm font-medium text-text-primary">
                  Active Subscription
                </h3>
              </CardHeader>
              <CardBody className="text-sm">
                {!sub ? (
                  <p className="text-text-muted py-6 text-center">
                    No active subscription found for this organisation.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {[
                      ["Plan", sub.plan_slug?.replace(/_/g, " ")],
                      ["Billing Cycle", sub.billing_cycle],
                      ["Status", null],
                      ["Period End", formatDateTime(sub.current_period_end)],
                      ["Cancel at Period End", sub.cancel_at_period_end ? "Yes" : "No"],
                    ].map(([label, value]) => (
                      <div key={label as string} className="flex justify-between">
                        <span className="text-text-muted">{label as string}</span>
                        {label === "Status" ? (
                          <StatusBadge status={sub.status} />
                        ) : (
                          <span className="font-medium text-text-primary capitalize">
                            {value as string}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardBody>
            </Card>
          )}

          {/* Wallet */}
          {tab === "wallet" && (
            <div className="space-y-4">
              {wallet && (
                <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                  <Card>
                    <CardBody>
                      <p className="text-xs text-text-muted uppercase tracking-wide">
                        Available Credits
                      </p>
                      <p className="text-2xl font-semibold text-accent mt-1">
                        {formatCredits(wallet.available_credits)}
                      </p>
                    </CardBody>
                  </Card>
                  <Card>
                    <CardBody>
                      <p className="text-xs text-text-muted uppercase tracking-wide">
                        Reserved Credits
                      </p>
                      <p className="text-2xl font-semibold text-text-primary mt-1">
                        {formatCredits(wallet.reserved_credits)}
                      </p>
                    </CardBody>
                  </Card>
                  <Card>
                    <CardBody>
                      <p className="text-xs text-text-muted uppercase tracking-wide">
                        Total Purchased
                      </p>
                      <p className="text-2xl font-semibold text-text-primary mt-1">
                        {formatCredits(wallet.total_purchased)}
                      </p>
                    </CardBody>
                  </Card>
                  <Card>
                    <CardBody>
                      <p className="text-xs text-text-muted uppercase tracking-wide">
                        Total Consumed
                      </p>
                      <p className="text-2xl font-semibold text-text-primary mt-1">
                        {formatCredits(wallet.total_consumed)}
                      </p>
                    </CardBody>
                  </Card>
                </div>
              )}
              <div className="flex justify-end">
                <Button size="sm" onClick={() => setShowAdjust(true)}>
                  Adjust Credits
                </Button>
              </div>
            </div>
          )}

          {/* Users */}
          {tab === "users" && (
            <Card>
              <CardHeader>
                <h3 className="text-sm font-medium text-text-primary">
                  Team Members
                </h3>
              </CardHeader>
              <CardBody>
                {users.length === 0 ? (
                  <p className="text-text-muted py-6 text-center text-sm">
                    No users found
                  </p>
                ) : (
                  <SimpleTable
                    headers={["Email", "Role", "Status", "Last Login"]}
                  >
                    {users.map((u) => (
                      <TableRow key={u.id}>
                        <TableCell className="font-medium">
                          {u.email}
                        </TableCell>
                        <TableCell className="capitalize text-text-secondary">
                          {u.role.replace(/_/g, " ")}
                        </TableCell>
                        <TableCell>
                          <StatusBadge
                            status={u.is_active ? "active" : "inactive"}
                          />
                        </TableCell>
                        <TableCell className="text-xs text-text-muted">
                          {formatDateTime(u.last_login_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </SimpleTable>
                )}
              </CardBody>
            </Card>
          )}
        </>
      )}

      {/* Suspend confirmation dialog */}
      <Modal
        isOpen={showSuspend}
        onClose={() => setShowSuspend(false)}
        title="Suspend Organisation"
      >
        <div className="space-y-4">
          <p className="text-sm text-text-secondary">
            This will prevent the organisation from making API calls and
            accessing their account. You can reactivate at any time.
          </p>
          <Input
            label="Reason"
            value={suspendReason}
            onChange={(e) => setSuspendReason(e.target.value)}
            placeholder="e.g. payment failure, policy violation"
          />
          <div className="flex justify-end gap-2 pt-1">
            <Button
              variant="secondary"
              onClick={() => setShowSuspend(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={acting}
              onClick={handleSuspend}
            >
              Confirm Suspend
            </Button>
          </div>
        </div>
      </Modal>

      {/* Adjust credits dialog */}
      <Modal
        isOpen={showAdjust}
        onClose={() => setShowAdjust(false)}
        title="Adjust Credits"
      >
        <form onSubmit={handleAdjust} className="space-y-4">
          <p className="text-sm text-text-secondary">
            Enter a positive number to add credits, or a negative number to
            deduct. A deduction will fail if the organisation has insufficient
            balance.
          </p>
          <Input
            label="Credits Delta"
            type="number"
            value={adjustDelta}
            onChange={(e) => setAdjustDelta(e.target.value)}
            placeholder="+500 or -100"
            hint="Positive = add, negative = deduct"
            required
          />
          <Input
            label="Reason"
            value={adjustReason}
            onChange={(e) => setAdjustReason(e.target.value)}
            placeholder="e.g. goodwill credit, billing correction"
            required
          />
          <div className="flex justify-end gap-2 pt-1">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowAdjust(false)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={adjusting}>
              Apply Adjustment
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
