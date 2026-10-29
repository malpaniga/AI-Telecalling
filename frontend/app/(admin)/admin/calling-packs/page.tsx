"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Package, Plus, Gift, Sliders, Sparkles, Pencil, Trash2, Eye, EyeOff } from "lucide-react";
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

interface PackFormData {
  name: string;
  slug: string;
  credits: string;
  bonus_credits: string;
  price_inr: string;
  validity_days: string;
  description: string;
  sort_order: string;
  is_public: boolean;
  is_active: boolean;
}

const initialFormData: PackFormData = {
  name: "",
  slug: "",
  credits: "",
  bonus_credits: "0",
  price_inr: "",
  validity_days: "365",
  description: "",
  sort_order: "0",
  is_public: true,
  is_active: true,
};

export default function AdminCallingPacksPage() {
  const [packs, setPacks] = useState<CallingPack[]>([]);
  const [loading, setLoading] = useState(true);

  // Create pack
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createForm, setCreateForm] = useState<PackFormData>(initialFormData);

  // Edit pack
  const [editingPack, setEditingPack] = useState<CallingPack | null>(null);
  const [updating, setUpdating] = useState(false);
  const [editForm, setEditForm] = useState<PackFormData>(initialFormData);

  // Delete pack
  const [deletingPack, setDeletingPack] = useState<CallingPack | null>(null);
  const [deleting, setDeleting] = useState(false);

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
      toast.error(e instanceof Error ? e.message : "Failed to load calling packs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Auto-slugify when name changes during creation
  function handleNameChange(name: string) {
    const autoSlug = name
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
    setCreateForm((f) => ({
      ...f,
      name,
      slug: f.slug === "" || f.slug === autoSlug.slice(0, -1) ? autoSlug : f.slug,
    }));
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const credits = parseInt(createForm.credits, 10);
    const priceInr = parseFloat(createForm.price_inr);

    if (isNaN(credits) || credits <= 0) {
      toast.error("Please enter a valid credit amount (> 0)");
      return;
    }
    if (isNaN(priceInr) || priceInr < 0) {
      toast.error("Please enter a valid price in ₹");
      return;
    }

    setCreating(true);
    try {
      await api.admin.callingPacks.create({
        name: createForm.name.trim(),
        slug: createForm.slug.trim(),
        credits,
        price_paise: Math.round(priceInr * 100),
        description: createForm.description.trim(),
        validity_days: parseInt(createForm.validity_days, 10) || 365,
        bonus_credits: parseInt(createForm.bonus_credits, 10) || 0,
        sort_order: parseInt(createForm.sort_order, 10) || 0,
        is_public: createForm.is_public,
      });
      toast.success("Calling pack created");
      setShowCreate(false);
      setCreateForm(initialFormData);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create pack");
    } finally {
      setCreating(false);
    }
  }

  function openEdit(pack: CallingPack) {
    setEditingPack(pack);
    setEditForm({
      name: pack.name,
      slug: pack.slug,
      credits: pack.credits.toString(),
      bonus_credits: (pack.bonus_credits || 0).toString(),
      price_inr: (pack.price_paise / 100).toString(),
      validity_days: pack.validity_days.toString(),
      description: pack.description || "",
      sort_order: (pack.sort_order ?? 0).toString(),
      is_public: pack.is_public ?? true,
      is_active: pack.is_active ?? true,
    });
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!editingPack) return;

    const credits = parseInt(editForm.credits, 10);
    const priceInr = parseFloat(editForm.price_inr);

    if (isNaN(credits) || credits <= 0) {
      toast.error("Please enter a valid credit amount (> 0)");
      return;
    }
    if (isNaN(priceInr) || priceInr < 0) {
      toast.error("Please enter a valid price in ₹");
      return;
    }

    setUpdating(true);
    try {
      await api.admin.callingPacks.update(editingPack.id, {
        name: editForm.name.trim(),
        slug: editForm.slug.trim(),
        credits,
        price_paise: Math.round(priceInr * 100),
        description: editForm.description.trim(),
        validity_days: parseInt(editForm.validity_days, 10) || 365,
        bonus_credits: parseInt(editForm.bonus_credits, 10) || 0,
        sort_order: parseInt(editForm.sort_order, 10) || 0,
        is_public: editForm.is_public,
        is_active: editForm.is_active,
      });
      toast.success("Calling pack updated");
      setEditingPack(null);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update pack");
    } finally {
      setUpdating(false);
    }
  }

  async function handleToggleStatus(pack: CallingPack) {
    try {
      await api.admin.callingPacks.update(pack.id, { is_active: !pack.is_active });
      toast.success(`Pack ${pack.is_active ? "deactivated" : "activated"}`);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update pack status");
    }
  }

  async function handleDelete() {
    if (!deletingPack) return;
    setDeleting(true);
    try {
      await api.admin.callingPacks.delete(deletingPack.id);
      toast.success(`Pack "${deletingPack.name}" deleted`);
      setDeletingPack(null);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to delete pack");
    } finally {
      setDeleting(false);
    }
  }

  async function handleBonus(e: React.FormEvent) {
    e.preventDefault();
    setBonusing(true);
    try {
      await api.admin.grantBonus({
        organization_id: bonusForm.organization_id.trim(),
        credits: parseInt(bonusForm.credits, 10),
        description: bonusForm.description.trim(),
        validity_days: parseInt(bonusForm.validity_days, 10) || 365,
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
      const delta = parseInt(adjustForm.credits_delta, 10);
      if (isNaN(delta)) {
        toast.error("Enter a valid credit delta");
        return;
      }
      await api.admin.wallets.adjust(
        adjustForm.organization_id.trim(),
        delta,
        adjustForm.reason.trim() || "admin adjustment"
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
        count: parseInt(grantTestsForm.count, 10) || 10,
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
        <div>
          <h2 className="text-lg font-semibold text-text-primary">
            Calling Packs
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Configure credit packs available for customer purchase in INR. 1 credit = 1 billable call minute.
          </p>
        </div>
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
              "Name & Details",
              "Slug",
              "Credits",
              "Bonus",
              "Total",
              "Price",
              "Validity",
              "Visibility",
              "Status",
              "Actions",
            ]}
          >
            {packs.map((p) => (
              <TableRow key={p.id}>
                <TableCell className="font-medium">
                  <div>
                    <span className="font-semibold text-text-primary block">{p.name}</span>
                    {p.description && (
                      <span className="text-xs text-text-muted block max-w-xs truncate" title={p.description}>
                        {p.description}
                      </span>
                    )}
                  </div>
                </TableCell>
                <TableCell className="font-mono text-xs text-text-muted">
                  {p.slug}
                </TableCell>
                <TableCell className="font-mono font-semibold text-text-primary">
                  {formatCredits(p.credits)}
                </TableCell>
                <TableCell className="text-success font-medium">
                  {p.bonus_credits > 0
                    ? `+${formatCredits(p.bonus_credits)}`
                    : "—"}
                </TableCell>
                <TableCell className="font-mono text-xs text-text-secondary">
                  {formatCredits(p.credits + (p.bonus_credits || 0))}
                </TableCell>
                <TableCell className="font-semibold text-text-primary">
                  {formatINR(p.price_paise)}
                </TableCell>
                <TableCell className="text-text-secondary text-xs">
                  {p.validity_days}d
                </TableCell>
                <TableCell>
                  {p.is_public ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded">
                      <Eye className="h-3 w-3" /> Public
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-text-muted bg-surface-hover px-2 py-0.5 rounded">
                      <EyeOff className="h-3 w-3" /> Hidden
                    </span>
                  )}
                </TableCell>
                <TableCell>
                  <button
                    type="button"
                    onClick={() => handleToggleStatus(p)}
                    title="Click to toggle active status"
                    className="cursor-pointer"
                  >
                    <StatusBadge
                      status={p.is_active ? "active" : "inactive"}
                    />
                  </button>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => openEdit(p)}
                      title="Edit Pack"
                    >
                      <Pencil className="h-3.5 w-3.5 mr-1" />
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setDeletingPack(p)}
                      className="text-danger hover:text-danger hover:bg-danger/10 p-1.5"
                      title="Delete Pack"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
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
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="e.g. Starter Pack"
              required
            />
            <Input
              label="Slug"
              value={createForm.slug}
              onChange={(e) =>
                setCreateForm((f) => ({ ...f, slug: e.target.value }))
              }
              placeholder="starter-pack"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Calling Credits"
              type="number"
              value={createForm.credits}
              onChange={(e) =>
                setCreateForm((f) => ({ ...f, credits: e.target.value }))
              }
              placeholder="1000"
              hint="1 credit = 1 minute of call time"
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
              placeholder="0"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Price (₹ INR)"
              type="number"
              step="any"
              value={createForm.price_inr}
              onChange={(e) =>
                setCreateForm((f) => ({ ...f, price_inr: e.target.value }))
              }
              placeholder="999"
              hint={createForm.price_inr ? `= ${(parseFloat(createForm.price_inr || "0") * 100).toLocaleString()} paise` : "e.g. 999 for ₹999"}
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
            placeholder="e.g. 1,000 calling credits for AI calling"
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Display Sort Order"
              type="number"
              value={createForm.sort_order}
              onChange={(e) =>
                setCreateForm((f) => ({ ...f, sort_order: e.target.value }))
              }
              placeholder="0"
            />
            <div className="flex items-center gap-4 pt-6">
              <label className="flex items-center gap-2 text-sm text-text-primary cursor-pointer">
                <input
                  type="checkbox"
                  checked={createForm.is_public}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, is_public: e.target.checked }))
                  }
                  className="rounded border-border text-accent focus:ring-accent"
                />
                Public (visible to users)
              </label>
            </div>
          </div>
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

      {/* Edit Pack modal */}
      <Modal
        isOpen={!!editingPack}
        onClose={() => setEditingPack(null)}
        title={`Edit Calling Pack: ${editingPack?.name || ""}`}
      >
        <form onSubmit={handleUpdate} className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Name"
              value={editForm.name}
              onChange={(e) =>
                setEditForm((f) => ({ ...f, name: e.target.value }))
              }
              required
            />
            <Input
              label="Slug"
              value={editForm.slug}
              onChange={(e) =>
                setEditForm((f) => ({ ...f, slug: e.target.value }))
              }
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Calling Credits"
              type="number"
              value={editForm.credits}
              onChange={(e) =>
                setEditForm((f) => ({ ...f, credits: e.target.value }))
              }
              hint="1 credit = 1 minute of call time"
              required
            />
            <Input
              label="Bonus Credits"
              type="number"
              value={editForm.bonus_credits}
              onChange={(e) =>
                setEditForm((f) => ({
                  ...f,
                  bonus_credits: e.target.value,
                }))
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Price (₹ INR)"
              type="number"
              step="any"
              value={editForm.price_inr}
              onChange={(e) =>
                setEditForm((f) => ({ ...f, price_inr: e.target.value }))
              }
              hint={editForm.price_inr ? `= ${(parseFloat(editForm.price_inr || "0") * 100).toLocaleString()} paise` : "e.g. 999"}
              required
            />
            <Input
              label="Validity (days)"
              type="number"
              value={editForm.validity_days}
              onChange={(e) =>
                setEditForm((f) => ({
                  ...f,
                  validity_days: e.target.value,
                }))
              }
            />
          </div>
          <Input
            label="Description"
            value={editForm.description}
            onChange={(e) =>
              setEditForm((f) => ({ ...f, description: e.target.value }))
            }
            placeholder="e.g. 1,000 calling credits. Best value."
          />
          <div className="grid grid-cols-3 gap-3 items-center pt-2">
            <Input
              label="Sort Order"
              type="number"
              value={editForm.sort_order}
              onChange={(e) =>
                setEditForm((f) => ({ ...f, sort_order: e.target.value }))
              }
            />
            <label className="flex items-center gap-2 text-sm text-text-primary cursor-pointer pt-4">
              <input
                type="checkbox"
                checked={editForm.is_public}
                onChange={(e) =>
                  setEditForm((f) => ({ ...f, is_public: e.target.checked }))
                }
                className="rounded border-border text-accent focus:ring-accent"
              />
              Public
            </label>
            <label className="flex items-center gap-2 text-sm text-text-primary cursor-pointer pt-4">
              <input
                type="checkbox"
                checked={editForm.is_active}
                onChange={(e) =>
                  setEditForm((f) => ({ ...f, is_active: e.target.checked }))
                }
                className="rounded border-border text-accent focus:ring-accent"
              />
              Active
            </label>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setEditingPack(null)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={updating}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deletingPack}
        onClose={() => setDeletingPack(null)}
        title="Delete Calling Pack"
      >
        <div className="space-y-4">
          <p className="text-sm text-text-secondary leading-relaxed">
            Are you sure you want to permanently delete the pack{" "}
            <strong className="text-text-primary font-semibold">
              &quot;{deletingPack?.name}&quot;
            </strong>{" "}
            ({deletingPack?.credits.toLocaleString()} credits for{" "}
            {deletingPack ? formatINR(deletingPack.price_paise) : ""})?
          </p>
          <p className="text-xs text-text-muted">
            Existing users with lots purchased from this pack will keep their balance until expiry. New users will no longer be able to purchase this pack.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setDeletingPack(null)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="danger"
              loading={deleting}
              onClick={handleDelete}
            >
              Delete Pack
            </Button>
          </div>
        </div>
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
