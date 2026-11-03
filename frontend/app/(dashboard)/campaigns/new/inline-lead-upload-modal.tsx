"use client";

import React, { useRef, useState } from "react";
import { Upload, FileText, Sparkles, AlertTriangle, X, Check } from "lucide-react";
import toast from "react-hot-toast";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { api } from "@/lib/api";

interface PreviewData {
  headers: string[];
  sample_rows: any[][];
  total_rows: number;
}

const MAPPING_OPTIONS = [
  { value: "phone", label: "📞 Phone Number (Required)" },
  { value: "name", label: "👤 Contact / Lead Name ({name})" },
  { value: "user_name", label: "👤 User Name ({user_name})" },
  { value: "email", label: "✉️ Email Address ({email})" },
  { value: "city", label: "🏙️ City ({city})" },
  { value: "address", label: "📍 Address ({address})" },
  { value: "company", label: "🏢 Company ({company})" },
  { value: "tags", label: "🏷️ Lead Tags ({tags})" },
  { value: "__custom__", label: "✨ Custom AI Variable..." },
  { value: "__skip__", label: "🚫 Skip this column" },
];

interface InlineLeadUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (importedCount: number, appliedTags?: string[]) => void;
}

export function InlineLeadUploadModal({
  isOpen,
  onClose,
  onSuccess,
}: InlineLeadUploadModalProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [tags, setTags] = useState("");
  const [uploading, setUploading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});
  const [customVariables, setCustomVariables] = useState<Record<string, string>>({});

  function resetState() {
    setFile(null);
    setPreview(null);
    setColumnMapping({});
    setCustomVariables({});
    setTags("");
    setUploading(false);
    setPreviewLoading(false);
  }

  function handleClose() {
    resetState();
    onClose();
  }

  async function handleFileSelect(f: File | null | undefined) {
    if (!f) return;
    const allowed = [
      "text/csv",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "application/json",
    ];
    if (!allowed.includes(f.type) && !f.name.match(/\.(csv|xlsx|xls|json)$/i)) {
      toast.error("Only CSV, XLSX, or JSON files are supported");
      return;
    }
    setFile(f);
    setPreview(null);
    setPreviewLoading(true);

    try {
      const data = await api.leads.preview(f);
      setPreview(data);

      const initialMapping: Record<string, string> = {};
      for (const h of data.headers) {
        const norm = h.trim().toLowerCase().replace(/[\s\-_]+/g, "");
        if (["phone", "mob", "mobile", "contact", "phonenumber"].some((k) => norm.includes(k))) {
          initialMapping[h] = "phone";
        } else if (["username", "fullname", "customername"].some((k) => norm.includes(k))) {
          initialMapping[h] = "user_name";
        } else if (norm === "name") {
          initialMapping[h] = "name";
        } else if (norm.includes("email") || norm.includes("mail")) {
          initialMapping[h] = "email";
        } else if (["city", "town", "location", "district"].some((k) => norm.includes(k))) {
          initialMapping[h] = "city";
        } else if (["address", "addr", "street"].some((k) => norm.includes(k))) {
          initialMapping[h] = "address";
        } else if (["company", "org", "business"].some((k) => norm.includes(k))) {
          initialMapping[h] = "company";
        } else if (["tag", "tags", "category"].some((k) => norm.includes(k))) {
          initialMapping[h] = "tags";
        } else {
          initialMapping[h] = "__skip__";
        }
      }
      setColumnMapping(initialMapping);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to parse preview");
      setFile(null);
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleImport() {
    if (!file) {
      toast.error("Please choose a file to upload");
      return;
    }

    let phoneMapped = false;
    const finalMapping: Record<string, string> = {};

    for (const [header, target] of Object.entries(columnMapping)) {
      if (target === "__skip__") continue;
      if (target === "phone") {
        phoneMapped = true;
        finalMapping[header] = "phone";
      } else if (target === "__custom__") {
        const customVar = customVariables[header]?.trim();
        if (customVar) {
          finalMapping[header] = customVar;
        }
      } else {
        finalMapping[header] = target;
      }
    }

    if (!phoneMapped) {
      toast.error("Please map at least one column to Phone Number");
      return;
    }

    setUploading(true);
    try {
      const res = await api.leads.import(file, {
        tags: tags.trim() || undefined,
        column_mapping: finalMapping,
      });

      const parsedTags = tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);

      toast.success(`Imported ${res.imported} new contacts!`);
      resetState();
      onClose();
      onSuccess(res.imported, parsedTags);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Import failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <Modal
      open={isOpen}
      onClose={handleClose}
      title="Upload Contacts"
      description="Upload a CSV or Excel spreadsheet of leads to immediately include in this campaign."
      maxWidth="max-w-2xl"
    >
      <div className="space-y-5">
        {/* Drag & Drop zone */}
        {!file && (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handleFileSelect(e.dataTransfer.files?.[0]);
            }}
            onClick={() => fileRef.current?.click()}
            className={`flex flex-col items-center justify-center p-8 rounded-xl border-2 border-dashed cursor-pointer transition-colors ${
              dragOver
                ? "border-brand-primary bg-brand-primary/5"
                : "border-border-default bg-bg-surface hover:border-border-strong hover:bg-bg-subtle"
            }`}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.xlsx,.xls,.json"
              className="hidden"
              onChange={(e) => handleFileSelect(e.target.files?.[0])}
            />
            <Upload className="h-10 w-10 text-brand-primary mb-3" />
            <p className="text-sm font-semibold text-text-primary">
              Click to select or drag and drop a file
            </p>
            <p className="text-xs text-text-muted mt-1">
              Supports CSV, Excel (.xlsx/.xls), or JSON (up to 5,000 rows)
            </p>
          </div>
        )}

        {previewLoading && (
          <div className="flex items-center justify-center py-8 gap-2 text-xs text-text-muted">
            <Spinner size="md" />
            Parsing file headers and sample records...
          </div>
        )}

        {/* Selected File & Mapping */}
        {file && preview && (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-xl border border-border-default bg-bg-subtle">
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-brand-primary" />
                <div>
                  <p className="text-xs font-semibold text-text-primary">{file.name}</p>
                  <p className="text-[11px] text-text-muted">
                    {preview.total_rows} row{preview.total_rows !== 1 ? "s" : ""} detected •{" "}
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setFile(null);
                  setPreview(null);
                }}
                className="text-xs text-text-muted hover:text-accent-red"
              >
                Change File
              </Button>
            </div>

            {/* Tags input */}
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">
                Assign Tags to Uploaded Leads <span className="text-text-muted">(Optional, comma-separated)</span>
              </label>
              <Input
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="e.g. q4_outreach, mumbai_leads, vip"
                className="text-xs"
              />
            </div>

            {/* Column Mapping Table */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-text-primary">
                  Column to Variable Mapping
                </span>
                <span className="text-[11px] text-text-muted">
                  Auto-mapped from headers
                </span>
              </div>
              <div className="max-h-56 overflow-y-auto rounded-lg border border-border-default divide-y divide-border-subtle bg-bg-surface">
                {preview.headers.map((header, idx) => {
                  const sampleVal = preview.sample_rows[0]?.[idx] ?? "";
                  const currentTarget = columnMapping[header] || "__skip__";

                  return (
                    <div
                      key={header}
                      className="p-2.5 flex items-center justify-between gap-3 text-xs"
                    >
                      <div className="min-w-0 flex-1">
                        <span className="font-semibold text-text-primary truncate block">
                          {header}
                        </span>
                        {sampleVal !== "" && (
                          <span className="text-[11px] text-text-muted truncate block">
                            e.g. {String(sampleVal).slice(0, 30)}
                          </span>
                        )}
                      </div>

                      <div className="flex-1 max-w-xs">
                        <Select
                          value={currentTarget}
                          onChange={(e) =>
                            setColumnMapping((prev) => ({
                              ...prev,
                              [header]: e.target.value,
                            }))
                          }
                          className="text-xs h-8 py-1"
                        >
                          {MAPPING_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </Select>

                        {currentTarget === "__custom__" && (
                          <Input
                            placeholder="Variable key (e.g. city)"
                            value={customVariables[header] || ""}
                            onChange={(e) =>
                              setCustomVariables((prev) => ({
                                ...prev,
                                [header]: e.target.value,
                              }))
                            }
                            className="text-xs h-7 mt-1.5"
                          />
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-border-default">
          <Button type="button" variant="ghost" size="sm" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={handleImport}
            disabled={!file || uploading}
            className="gap-2"
          >
            {uploading ? (
              <>
                <Spinner size="sm" />
                Importing...
              </>
            ) : (
              <>
                <Check className="h-4 w-4" />
                Import & Add to Selection
              </>
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
