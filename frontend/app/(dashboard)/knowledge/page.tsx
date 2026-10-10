"use client";

import React, { useEffect, useState, useCallback } from "react";
import { BookOpen, Plus, Trash2, FileText } from "lucide-react";
import toast from "react-hot-toast";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Modal } from "@/components/ui/modal";
import { Input, Textarea } from "@/components/ui/input";
import { api, KnowledgeBase, KnowledgeDocument } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

export default function KnowledgePage() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [selectedKb, setSelectedKb] = useState<KnowledgeBase | null>(null);
  const [docs, setDocs] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [showCreateKb, setShowCreateKb] = useState(false);
  const [showCreateDoc, setShowCreateDoc] = useState(false);
  const [creating, setCreating] = useState(false);

  const [kbForm, setKbForm] = useState({ name: "", description: "" });
  const [docForm, setDocForm] = useState({ title: "", content: "", document_type: "general" });

  const loadKbs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.knowledge.list();
      setKbs(data);
      if (data.length > 0 && !selectedKb) setSelectedKb(data[0]);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [selectedKb]);

  useEffect(() => { loadKbs(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!selectedKb) return;
    setLoadingDocs(true);
    api.knowledge.listDocuments(selectedKb.id)
      .then(setDocs)
      .catch(() => setDocs([]))
      .finally(() => setLoadingDocs(false));
  }, [selectedKb]);

  async function handleCreateKb(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      const kb = await api.knowledge.create(kbForm.name, kbForm.description);
      toast.success("Knowledge base created");
      setShowCreateKb(false);
      setKbForm({ name: "", description: "" });
      setKbs((prev) => [...prev, kb]);
      setSelectedKb(kb);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create");
    } finally {
      setCreating(false);
    }
  }

  async function handleCreateDoc(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedKb) return;
    setCreating(true);
    try {
      await api.knowledge.addDocument(selectedKb.id, docForm.title, docForm.content, docForm.document_type);
      toast.success("Document added");
      setShowCreateDoc(false);
      setDocForm({ title: "", content: "", document_type: "general" });
      // reload docs
      setSelectedKb({ ...selectedKb });
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to add document");
    } finally {
      setCreating(false);
    }
  }

  async function handleDeleteKb(id: string) {
    if (!confirm("Delete this knowledge base?")) return;
    try {
      await api.knowledge.deleteKb(id);
      toast.success("Deleted");
      setKbs((prev) => prev.filter((k) => k.id !== id));
      if (selectedKb?.id === id) setSelectedKb(kbs.find((k) => k.id !== id) ?? null);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to delete");
    }
  }

  return (
    <AppShell title="Knowledge Base">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Knowledge Bases</h2>
          <p className="text-sm text-text-secondary">Documents your AI agents use during calls</p>
        </div>
        <Button size="sm" onClick={() => setShowCreateKb(true)}>
          <Plus className="h-4 w-4 mr-1" /> New KB
        </Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : kbs.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="No knowledge bases"
          description="Create a knowledge base and add documents your AI agent can reference during calls"
          action={<Button onClick={() => setShowCreateKb(true)}>Create Knowledge Base</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
          {/* KB list */}
          <div className="lg:col-span-1 space-y-2">
            {kbs.map((kb) => (
              <button
                key={kb.id}
                onClick={() => setSelectedKb(kb)}
                className={`w-full text-left rounded-lg border px-3 py-3 transition-colors ${
                  selectedKb?.id === kb.id
                    ? "border-accent bg-accent-subtle"
                    : "border-border bg-surface hover:border-border-strong"
                }`}
              >
                <div className="flex justify-between items-start">
                  <p className="text-sm font-medium text-text-primary truncate">{kb.name}</p>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDeleteKb(kb.id); }}
                    className="ml-2 p-0.5 text-text-muted hover:text-danger"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
                <p className="text-xs text-text-muted">{kb.document_count} docs</p>
              </button>
            ))}
          </div>

          {/* Documents */}
          <Card className="lg:col-span-3">
            <CardHeader>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-text-primary">{selectedKb?.name}</h3>
                {selectedKb && (
                  <Button size="sm" onClick={() => setShowCreateDoc(true)}>
                    <Plus className="h-4 w-4 mr-1" /> Add Document
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardBody>
              {loadingDocs ? (
                <div className="flex justify-center py-8"><Spinner /></div>
              ) : docs.length === 0 ? (
                <EmptyState
                  icon={FileText}
                  title="No documents"
                  description="Add documents this knowledge base can use"
                />
              ) : (
                <div className="space-y-3">
                  {docs.map((doc) => (
                    <div key={doc.id} className="border border-border rounded-md p-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="text-sm font-medium text-text-primary">{doc.title}</p>
                          <p className="text-xs text-text-muted mt-0.5 capitalize">
                            {doc.document_type} · v{doc.version} · {formatDateTime(doc.created_at)}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>
        </div>
      )}

      <Modal isOpen={showCreateKb} onClose={() => setShowCreateKb(false)} title="New Knowledge Base">
        <form onSubmit={handleCreateKb} className="flex flex-col gap-4">
          <Input
            label="Name"
            value={kbForm.name}
            onChange={(e) => setKbForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="Product FAQ"
            required
          />
          <Input
            label="Description (optional)"
            value={kbForm.description}
            onChange={(e) => setKbForm((f) => ({ ...f, description: e.target.value }))}
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setShowCreateKb(false)}>Cancel</Button>
            <Button type="submit" loading={creating}>Create</Button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={showCreateDoc} onClose={() => setShowCreateDoc(false)} title="Add Document" size="lg">
        <form onSubmit={handleCreateDoc} className="flex flex-col gap-4">
          <Input
            label="Title"
            value={docForm.title}
            onChange={(e) => setDocForm((f) => ({ ...f, title: e.target.value }))}
            required
          />
          <Textarea
            label="Content"
            value={docForm.content}
            onChange={(e) => setDocForm((f) => ({ ...f, content: e.target.value }))}
            rows={8}
            required
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setShowCreateDoc(false)}>Cancel</Button>
            <Button type="submit" loading={creating}>Add Document</Button>
          </div>
        </form>
      </Modal>
    </AppShell>
  );
}
