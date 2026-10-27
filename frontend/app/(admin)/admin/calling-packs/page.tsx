"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Package, Plus, Gift, Sliders, Sparkles } from "lucide-react";
import toast from "react-hot-toast";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Modal } from "@/components/ui/modal";
import { Input } from "@/components/ui/input";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, CallingPack } from "@/lib/api";
import { formatINR, formatCredits } from "@/lib/utils";

export default function AdminCallingPacksPage() {
  const [packs, setPacks] = useState<CallingPack[]>([]);
  const [loading, setLoading] = useState(true);

  // Create pack
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: "",
    slug: "",
    credits: "",
    price_paise: "",
    description: "",
    validity_days: "365",
    bonus_credits: "0",
  });

  // Grant bonus
  const [showBonus, setShowBonus] = useState(false);
  const [bonusing, setBonusing] = useState(false);
  const [bonusForm, setBonusForm] = useState({
    organization_id: "",
    credits: "",
    description: "Goodwill bonus",
    validity_days: "365",
  });

  // Adjust credits
  const [showAdjust, setShowAdjust] = useState(false);
  const [adjusting, setAdjusting] = useState(false);
  const [adjustForm, setAdjustForm] = useState({
    organization_id: "",
    credits_delta: "",
    reason: "",
  });

  // Grant free test sessions
  const [showGrantTests, setShowGrantTests] = useState(false);
  const [grantingTests, setGrantingTests] = useState(false);
  const [grantTestsForm, setGrantTestsForm] = useState({
    organization_id: "",
    count: "10",
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.admin.callingPacks.list(true);
      setPacks(data);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await api.admin.callingPacks.create({
        name: createForm.name,
        slug: createForm.slug,
        credits: parseInt(createForm.credits),
        price_paise: parseInt(createForm.price_paise),
        description: createForm.description,
        validity_days: parseInt(createForm.validity_days) || 365,
        bonus_credits: parseInt(createForm.bonus_credits) || 0,
      });
      toast.success("Calling pack created");
      setShowCreate(false);
      setCreateForm({
        name: "",
        slug: "",
        credits: "",
        price_paise: "",
        description: "",
        validity_days: "365",
        bonus_credits: "0",
      });
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create");
    } finally {
      setCreating(false);
    }
  }

  async function handleBonus(e: React.FormEvent) {
    e.preventDefault();
    setBonusing(true);
    try {
      await api.admin.grantBonus({
        organization_id: bonusForm.organization_id,
        credits: parseInt(bonusForm.credits),
        description: bonusForm.description,
        validity_days: parseInt(bonusForm.validity_days) || 365,
      });
      toast.success("Bonus credits granted");
      setShowBonus(false);
      setBonusForm({
        organization_id: "",
        credits: "",
        description: "Goodwill bonus",
        validity_days: "365",
      });
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to grant bonus");
    } finally {
      setBonusing(false);
    }
  }

  async function handleAdjust(e: React.FormEvent) {
    e.preventDefault();
    setAdjusting(true);
    try {
      const delta = parseInt(adjustForm.credits_delta);
      if (isNaN(delta)) {
        toast.error("Enter a valid credit delta");
        return;
      }
      await api.admin.wallets.adjust(
        adjustForm.organization_id,
        delta,
        adjustForm.reason || "admin adjustment"
      );
      toast.success("Credits adjusted");
      setShowAdjust(false);
      setAdjustForm({ organization_id: "", credits_delta: "", reason: "" });
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to adjust credits");
    } finally {
      setAdjusting(false);
    }
  }

  async function handleGrantTests(e: React.FormEvent) {
    e.preventDefault();
    setGrantingTests(true);
    try {
      const res = await api.admin.grantFreeTests({
        organization_id: grantTestsForm.organization_id.trim(),
        count: parseInt(grantTestsForm.count) || 10,
      });
      toast.success(
        `Granted ${grantTestsForm.count} free tests. Organization now has ${res.free_test_sessions_remaining} total free test sessions.`
      );
      setShowGrantTests(false);
      setGrantTestsForm({ organization_id: "", count: "10" });
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to grant free tests");
    } finally {
      setGrantingTests(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-lg font-semibold text-text-primary">
          Calling Packs
        </h2>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => setShowAdjust(true)}
          >
            <Sliders className="h-3.5 w-3.5 mr-1.5" />
            Adjust Credits
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => setShowBonus(true)}
          >
            <Gift className="h-3.5 w-3.5 mr-1.5" />
            Grant Bonus
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => setShowGrantTests(true)}
          >
            <Sparkles className="h-3.5 w-3.5 mr-1.5" />
            Grant Free Tests
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4 mr-1" />
            New Pack
          </Button>
        </div>
      </div>

      <Card>
        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner size="lg" />
          </div>
        ) : packs.length === 0 ? (
          <EmptyState
            icon={Package}
            title="No calling packs"
            action={
              <Button onClick={() => setShowCreate(true)}>Create Pack</Button>
            }
          />
        ) : (
          <SimpleTable
            headers={[
              "Name",
              "Slug",
              "Credits",
              "Bonus",
              "Price",
              "Validity",
              "Status",
            ]}
          >
            {packs.map((p) => (
              <TableRow key={p.id}>
                <TableCell className="font-medium">{p.name}</TableCell>
                <TableCell className="font-mono text-xs text-text-muted">
                  {p.slug}
                </TableCell>
                <TableCell className="font-mono">
                  {formatCredits(p.credits)}
                </TableCell>
                <TableCell className="text-success">
                  {p.bonus_credits > 0
                    ? `+${formatCredits(p.bonus_credits)}`
                    : "—"}
                </TableCell>
                <TableCell className="font-medium">
                  {formatINR(p.price_paise)}
                </TableCell>
                <TableCell className="text-text-secondary">
                  {p.validity_days}d
                </TableCell>
                <TableCell>
                  <StatusBadge
                    status={p.is_active ? "active" : "inactive"}
                  />
                </TableCell>
              </TableRow>
            ))}
          </SimpleTable>
        )}
      </Card>

      {/* Create Pack modal */}
      <Modal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        title="New Calling Pack"
      >
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Name"
              value={createForm.name}
              onChange={(e) =>
                setCreateForm((f) => ({ ...f, name: e.target.value }))
              }
              required
            />
            <Input
              label="Slug"
              value={createForm.slug}
              onChange={(e) =>
                setCreateForm((f) => ({ ...f, slug: e.target.value }))
              }
              placeholder="starter-500"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Credits"
              type="number"
              value={createForm.credits}
              onChange={(e) =>
                setCreateForm((f) => ({ ...f, credits: e.target.value }))
              }
              required
            />
            <Input
              label="Bonus Credits"
              type="number"
              value={createForm.bonus_credits}
              onChange={(e) =>
                setCreateForm((f) => ({
                  ...f,
                  bonus_credits: e.target.value,
                }))
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Price (paise)"
              type="number"
              value={createForm.price_paise}
              onChange={(e) =>
                setCreateForm((f) => ({ ...f, price_paise: e.target.value }))
              }
              hint="100 = ₹1"
              required
            />
            <Input
              label="Validity (days)"
              type="number"
              value={createForm.validity_days}
              onChange={(e) =>
                setCreateForm((f) => ({
                  ...f,
                  validity_days: e.target.value,
                }))
              }
            />
          </div>
          <Input
            label="Description"
            value={createForm.description}
            onChange={(e) =>
              setCreateForm((f) => ({ ...f, description: e.target.value }))
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowCreate(false)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={creating}>
              Create Pack
            </Button>
          </div>
        </form>
      </Modal>

      {/* Grant Bonus modal */}
      <Modal
        isOpen={showBonus}
        onClose={() => setShowBonus(false)}
        title="Grant Bonus Credits"
      >
        <form onSubmit={handleBonus} className="space-y-4">
          <p className="text-sm text-text-secondary">
            Credits are added directly to the organisation&apos;s wallet as a
            bonus lot. They expire based on the validity days set.
          </p>
          <Input
            label="Organisation ID"
            value={bonusForm.organization_id}
            onChange={(e) =>
              setBonusForm((f) => ({ ...f, organization_id: e.target.value }))
            }
            placeholder="org_..."
            required
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Credits"
              type="number"
              value={bonusForm.credits}
              onChange={(e) =>
                setBonusForm((f) => ({ ...f, credits: e.target.value }))
              }
              required
            />
            <Input
              label="Validity (days)"
              type="number"
              value={bonusForm.validity_days}
              onChange={(e) =>
                setBonusForm((f) => ({ ...f, validity_days: e.target.value }))
              }
            />
          </div>
          <Input
            label="Description"
            value={bonusForm.description}
            onChange={(e) =>
              setBonusForm((f) => ({ ...f, description: e.target.value }))
            }
            required
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowBonus(false)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={bonusing}>
              Grant Bonus
            </Button>
          </div>
        </form>
      </Modal>

      {/* Adjust Credits modal */}
      <Modal
        isOpen={showAdjust}
        onClose={() => setShowAdjust(false)}
        title="Adjust Credits"
      >
        <form onSubmit={handleAdjust} className="space-y-4">
          <p className="text-sm text-text-secondary">
            Positive delta adds credits; negative delta deducts them. A
            deduction fails if the organisation has insufficient balance.
          </p>
          <Input
            label="Organisation ID"
            value={adjustForm.organization_id}
            onChange={(e) =>
              setAdjustForm((f) => ({ ...f, organization_id: e.target.value }))
            }
            placeholder="org_..."
            required
          />
          <Input
            label="Credits Delta"
            type="number"
            value={adjustForm.credits_delta}
            onChange={(e) =>
              setAdjustForm((f) => ({ ...f, credits_delta: e.target.value }))
            }
            placeholder="+500 or -100"
            hint="Positive = add, negative = deduct"
            required
          />
          <Input
            label="Reason"
            value={adjustForm.reason}
            onChange={(e) =>
              setAdjustForm((f) => ({ ...f, reason: e.target.value }))
            }
            placeholder="e.g. goodwill, billing error"
            required
          />
          <div className="flex justify-end gap-2 pt-2">
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

      {/* Grant Free Tests modal */}
      <Modal
        isOpen={showGrantTests}
        onClose={() => setShowGrantTests(false)}
        title="Grant Free Browser Test Sessions"
      >
        <form onSubmit={handleGrantTests} className="space-y-4">
          <p className="text-sm text-text-secondary">
            Assign additional complimentary in-browser testing sessions (3 minutes each) to an organization.
          </p>
          <Input
            label="Organisation ID"
            value={grantTestsForm.organization_id}
            onChange={(e) =>
              setGrantTestsForm((f) => ({ ...f, organization_id: e.target.value }))
            }
            placeholder="org_..."
            required
          />
          <Input
            label="Number of Test Sessions"
            type="number"
            value={grantTestsForm.count}
            onChange={(e) =>
              setGrantTestsForm((f) => ({ ...f, count: e.target.value }))
            }
            placeholder="10"
            hint="Number of 3-minute browser sessions to grant"
            required
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowGrantTests(false)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={grantingTests}>
              Grant Sessions
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
