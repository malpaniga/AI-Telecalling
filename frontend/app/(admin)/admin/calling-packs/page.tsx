"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Package, Plus } from "lucide-react";
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
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name: "", slug: "", credits: "", price_paise: "", description: "", validity_days: "365", bonus_credits: "0",
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

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await api.admin.callingPacks.create({
        name: form.name,
        slug: form.slug,
        credits: parseInt(form.credits),
        price_paise: parseInt(form.price_paise),
        description: form.description,
        validity_days: parseInt(form.validity_days) || 365,
        bonus_credits: parseInt(form.bonus_credits) || 0,
      });
      toast.success("Calling pack created");
      setShowCreate(false);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">Calling Packs</h2>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-1" /> New Pack
        </Button>
      </div>

      <Card>
        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : packs.length === 0 ? (
          <EmptyState icon={Package} title="No calling packs" action={<Button onClick={() => setShowCreate(true)}>Create Pack</Button>} />
        ) : (
          <SimpleTable headers={["Name", "Slug", "Credits", "Bonus", "Price", "Validity", "Status"]}>
            {packs.map((p) => (
              <TableRow key={p.id}>
                <TableCell className="font-medium">{p.name}</TableCell>
                <TableCell className="font-mono text-xs text-text-muted">{p.slug}</TableCell>
                <TableCell className="font-mono">{formatCredits(p.credits)}</TableCell>
                <TableCell className="text-success">{p.bonus_credits > 0 ? `+${formatCredits(p.bonus_credits)}` : "—"}</TableCell>
                <TableCell className="font-medium">{formatINR(p.price_paise)}</TableCell>
                <TableCell className="text-text-secondary">{p.validity_days}d</TableCell>
                <TableCell><StatusBadge status={p.is_active ? "active" : "inactive"} /></TableCell>
              </TableRow>
            ))}
          </SimpleTable>
        )}
      </Card>

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="New Calling Pack">
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required />
            <Input label="Slug" value={form.slug} onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value }))} placeholder="starter-500" required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Credits" type="number" value={form.credits} onChange={(e) => setForm((f) => ({ ...f, credits: e.target.value }))} required />
            <Input label="Bonus Credits" type="number" value={form.bonus_credits} onChange={(e) => setForm((f) => ({ ...f, bonus_credits: e.target.value }))} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Price (paise)" type="number" value={form.price_paise} onChange={(e) => setForm((f) => ({ ...f, price_paise: e.target.value }))} hint="100 = ₹1" required />
            <Input label="Validity (days)" type="number" value={form.validity_days} onChange={(e) => setForm((f) => ({ ...f, validity_days: e.target.value }))} />
          </div>
          <Input label="Description" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button type="submit" loading={creating}>Create Pack</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
