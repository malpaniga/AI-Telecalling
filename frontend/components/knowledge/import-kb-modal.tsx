"use client";

import React, { useState, useRef } from "react";
import {
  Upload,
  BookOpen,
  CheckCircle2,
  AlertCircle,
  FileText,
  Tag,
} from "lucide-react";
import toast from "react-hot-toast";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, KnowledgeBase, KBExportPackage } from "@/lib/api";

interface ImportKbModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImportSuccess?: (newKb: KnowledgeBase) => void;
}

export function ImportKbModal({
  isOpen,
  onClose,
  onImportSuccess,
}: ImportKbModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [exportPkg, setExportPkg] = useState<KBExportPackage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [importing, setImporting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function resetState() {
    setFile(null);
    setExportPkg(null);
    setError(null);
    setName("");
    setDescription("");
    setImporting(false);
  }

  function handleClose() {
    resetState();
    onClose();
  }

  function processFile(selectedFile: File) {
    setError(null);
    if (!selectedFile.name.endsWith(".json")) {
      setError("Please select a valid JSON export file (.kb.json or .json).");
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        const parsed = JSON.parse(text);

        if (parsed.format !== "sarvam_kb_export_v1" || !parsed.knowledge_base) {
          setError(
            'Invalid file format. Expected a Sarvam Knowledge Base export file with "format": "sarvam_kb_export_v1".'
          );
          setExportPkg(null);
          return;
        }

        const pkg = parsed as KBExportPackage;
        setFile(selectedFile);
        setExportPkg(pkg);
        setName(
          pkg.knowledge_base.name
            ? `${pkg.knowledge_base.name} (Imported)`
            : "Imported Knowledge Base"
        );
        setDescription(pkg.knowledge_base.description || "");
      } catch (err: unknown) {
        setError(
          `Failed to parse JSON file: ${err instanceof Error ? err.message : "Invalid JSON syntax"}`
        );
        setExportPkg(null);
      }
    };
    reader.onerror = () => {
      setError("Error reading the selected file.");
    };
    reader.readAsText(selectedFile);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  }

  async function handleImport() {
    if (!exportPkg || !name.trim()) {
      toast.error("Please provide a valid knowledge base name.");
      return;
    }

    setImporting(true);
    try {
      const newKb = await api.knowledge.import({
        name: name.trim(),
        description: description.trim(),
        tags: exportPkg.knowledge_base.tags || [],
        documents: exportPkg.knowledge_base.documents || [],
      });

      toast.success(
        `Knowledge base "${newKb.name}" imported with ${exportPkg.knowledge_base.documents?.length || 0} document(s)!`
      );
      handleClose();
      if (onImportSuccess) {
        onImportSuccess(newKb);
      }
    } catch (err: unknown) {
      toast.error(
        err instanceof Error ? err.message : "Failed to import knowledge base."
      );
    } finally {
      setImporting(false);
    }
  }

  const docs = exportPkg?.knowledge_base.documents || [];
  const tags = exportPkg?.knowledge_base.tags || [];

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Import Knowledge Base"
      size="lg"
    >
      <div className="p-6 space-y-6">
        {/* Upload Dropzone */}
        {!exportPkg ? (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`cursor-pointer border-2 border-dashed rounded-xl p-8 text-center transition-all ${
              dragOver
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50 bg-secondary/20 hover:bg-secondary/40"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,.kb.json"
              className="hidden"
              onChange={handleFileChange}
            />
            <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto mb-3">
              <Upload className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-semibold text-text-primary">
              Choose a knowledge base file or drag it here
            </h3>
            <p className="text-xs text-text-muted mt-1">
              Upload an exported <code className="text-primary font-mono">.kb.json</code> file
            </p>
          </div>
        ) : (
          <div className="flex items-center justify-between p-3.5 bg-secondary/30 rounded-lg border border-border">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                <BookOpen className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-semibold text-text-primary">
                  {file?.name || "Knowledge Base Export"}
                </p>
                <p className="text-[11px] text-text-muted">
                  Exported at:{" "}
                  {exportPkg.exported_at
                    ? new Date(exportPkg.exported_at).toLocaleString()
                    : "Unknown date"}
                </p>
              </div>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setExportPkg(null);
                setFile(null);
              }}
              className="text-xs"
            >
              Change File
            </Button>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="flex items-start gap-2.5 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Configuration preview & overrides */}
        {exportPkg && (
          <div className="space-y-4">
            <Input
              label="Knowledge Base Name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Solar Technical FAQs"
            />

            <Input
              label="Description (Optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of documents in this knowledge base"
            />

            {tags.length > 0 && (
              <div>
                <span className="text-[11px] font-medium text-text-secondary block mb-1.5 flex items-center gap-1">
                  <Tag className="w-3 h-3 text-primary" />
                  Tags:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {tags.map((t, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded-full text-[11px] bg-secondary text-text-secondary border border-border"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Document list preview */}
            <div className="rounded-lg border border-border bg-card/60 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-text-primary flex items-center gap-1.5 uppercase tracking-wider">
                  <FileText className="w-3.5 h-3.5 text-primary" />
                  Documents Included ({docs.length})
                </h4>
              </div>

              {docs.length === 0 ? (
                <p className="text-xs text-text-muted italic">
                  This knowledge base does not contain any documents yet.
                </p>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {docs.map((doc, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded bg-surface/80 border border-border/40 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-text-primary">{doc.title}</span>
                        <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-secondary text-text-muted">
                          {doc.document_type || "general"}
                        </span>
                      </div>
                      <p className="text-[11px] text-text-muted line-clamp-2">
                        {doc.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
          <Button variant="secondary" onClick={handleClose} disabled={importing}>
            Cancel
          </Button>
          <Button
            onClick={handleImport}
            disabled={!exportPkg || !name.trim() || importing}
            loading={importing}
            className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold"
          >
            <CheckCircle2 className="w-4 h-4 mr-1.5" />
            Import Knowledge Base
          </Button>
        </div>
      </div>
    </Modal>
  );
}
