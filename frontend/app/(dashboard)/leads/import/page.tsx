"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ChevronLeft,
  Upload,
  FileText,
  AlertTriangle,
  ArrowRight,
  Sparkles,
  Settings,
  HelpCircle,
} from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { api, Campaign } from "@/lib/api";

interface PreviewData {
  headers: string[];
  sample_rows: any[][];
  total_rows: number;
}

const MAPPING_OPTIONS = [
  { value: "phone", label: "📞 Phone Number (Required)" },
  { value: "user_name", label: "👤 Full / User Name ({user_name})" },
  { value: "name", label: "👤 Contact Name ({name})" },
  { value: "email", label: "✉️ Email Address ({email})" },
  { value: "city", label: "🏙️ City ({city})" },
  { value: "address", label: "📍 Address ({address})" },
  { value: "company", label: "🏢 Company ({company})" },
  { value: "tags", label: "🏷️ Lead Tags ({tags})" },
  { value: "__custom__", label: "✨ Custom AI Variable..." },
  { value: "__skip__", label: "🚫 Skip this column" },
];

export default function LeadsImportPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const fileRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [tags, setTags] = useState("");
  const [campaignId, setCampaignId] = useState(searchParams?.get("campaign_id") || "");
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [uploading, setUploading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});
  const [customVariables, setCustomVariables] = useState<Record<string, string>>({});

  const [result, setResult] = useState<{
    imported: number;
    skipped_duplicate: number;
    skipped_dnc: number;
    skipped_invalid: number;
    total_rows: number;
    errors: any[];
  } | null>(null);

  useEffect(() => {
    api.campaigns.list({ limit: 100 })
      .then((camps) => setCampaigns(camps))
      .catch(() => {});
  }, []);

  async function onFile(f: File | null | undefined) {
    if (!f) return;
    const allowed = [
      "text/csv",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "application/json",
    ];
    if (!allowed.includes(f.type) && !f.name.match(/\.(csv|xlsx|json)$/i)) {
      toast.error("Only CSV, XLSX, or JSON files are supported");
      return;
    }
    setFile(f);
    setPreview(null);
    setPreviewLoading(true);

    try {
      const data = await api.leads.preview(f);
      setPreview(data);

      // Auto-match headers to common mappings
      const initialMapping: Record<string, string> = {};
      const initialCustoms: Record<string, string> = {};

      for (const h of data.headers) {
        const norm = h.trim().toLowerCase().replace(/[\s\-_]+/g, "");
        if (["phone", "mob", "mobile", "contact", "phonenumber"].some((k) => norm.includes(k))) {
          initialMapping[h] = "phone";
        } else if (["fullname", "customername", "clientname", "username", "leadname"].some((k) => norm.includes(k))) {
          initialMapping[h] = "user_name";
        } else if (norm === "name") {
          initialMapping[h] = "user_name";
        } else if (["email", "mail"].some((k) => norm.includes(k))) {
          initialMapping[h] = "email";
        } else if (["city", "town", "locality"].some((k) => norm.includes(k))) {
          initialMapping[h] = "city";
        } else if (["address", "location", "residence"].some((k) => norm.includes(k))) {
          initialMapping[h] = "address";
        } else if (["company", "organization", "org"].some((k) => norm.includes(k))) {
          initialMapping[h] = "company";
        } else if (["tag", "tags", "label", "labels", "category"].some((k) => norm.includes(k))) {
          initialMapping[h] = "tags";
        } else {
          // Default to custom variable using snake_case header name
          const slug = h.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
          initialMapping[h] = "__custom__";
          initialCustoms[h] = slug;
        }
      }

      setColumnMapping(initialMapping);
      setCustomVariables(initialCustoms);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to preview file headers");
    } finally {
      setPreviewLoading(false);
    }
  }

  function handleMappingChange(header: string, val: string) {
    setColumnMapping((prev) => ({ ...prev, [header]: val }));
    if (val === "__custom__" && !customVariables[header]) {
      const slug = header.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
      setCustomVariables((prev) => ({ ...prev, [header]: slug }));
    }
  }

  function handleCustomVariableChange(header: string, val: string) {
    const sanitized = val.toLowerCase().replace(/[^a-z0-9_]/g, "");
    setCustomVariables((prev) => ({ ...prev, [header]: sanitized }));
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      toast.error("Select a file to import");
      return;
    }

    // Verify phone is mapped
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
        campaign_id: campaignId || undefined,
        tags: tags.trim() || undefined,
        column_mapping: finalMapping,
      });
      setResult(res);
      toast.success(`Successfully imported ${res.imported} leads!`);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Import failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-3">
        <Link href={campaignId ? `/campaigns/${campaignId}` : "/leads"}>
          <Button variant="ghost" size="sm" className="gap-1">
            <ChevronLeft className="h-4 w-4" />
            Back
          </Button>
        </Link>
        <div>
          <h2 className="text-lg font-semibold text-text-primary">
            Import Leads & Map AI Variables
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Upload contact files and map headers directly to AI agent prompt variables
          </p>
        </div>
      </div>

      {result ? (
        /* Result card */
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-text-primary">
              Import Complete
            </h3>
          </CardHeader>
          <CardBody className="space-y-4">
            <div className="grid grid-cols-4 gap-3 text-center">
              <div className="rounded-lg bg-surface-subtle p-4">
                <p className="text-2xl font-bold text-success">
                  {result.imported}
                </p>
                <p className="text-xs text-text-muted mt-1">Imported</p>
              </div>
              <div className="rounded-lg bg-surface-subtle p-4">
                <p className="text-2xl font-bold text-text-secondary">
                  {result.skipped_duplicate}
                </p>
                <p className="text-xs text-text-muted mt-1">Duplicate</p>
              </div>
              <div className="rounded-lg bg-surface-subtle p-4">
                <p className="text-2xl font-bold text-text-secondary">
                  {result.skipped_dnc}
                </p>
                <p className="text-xs text-text-muted mt-1">DNC Filtered</p>
              </div>
              <div className="rounded-lg bg-surface-subtle p-4">
                <p
                  className={`text-2xl font-bold ${
                    result.skipped_invalid > 0 ? "text-danger" : "text-text-secondary"
                  }`}
                >
                  {result.skipped_invalid}
                </p>
                <p className="text-xs text-text-muted mt-1">Invalid</p>
              </div>
            </div>

            {result.errors && result.errors.length > 0 && (
              <div className="flex items-start gap-2 rounded-lg bg-danger/5 border border-danger/20 p-3 text-sm text-danger">
                <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>
                  {result.errors.length} row(s) had errors and were skipped.
                </span>
              </div>
            )}

            <div className="flex gap-2 pt-2">
              <Button
                variant="secondary"
                onClick={() => {
                  setResult(null);
                  setFile(null);
                  setPreview(null);
                }}
              >
                Import More
              </Button>
              {campaignId ? (
                <Button onClick={() => router.push(`/campaigns/${campaignId}`)}>
                  Go to Campaign
                </Button>
              ) : (
                <Button onClick={() => router.push("/leads")}>
                  View Leads
                </Button>
              )}
            </div>
          </CardBody>
        </Card>
      ) : (
        <form onSubmit={handleUpload} className="space-y-6">
          {/* Step 1: Upload Dropzone */}
          <Card>
            <CardHeader className="flex justify-between items-center">
              <div>
                <h3 className="text-sm font-semibold text-text-primary">
                  1. Select Contact File
                </h3>
                <p className="text-xs text-text-muted">
                  Supports CSV, XLSX, or JSON
                </p>
              </div>
              {file && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setFile(null);
                    setPreview(null);
                  }}
                >
                  Change File
                </Button>
              )}
            </CardHeader>
            <CardBody>
              <div
                onClick={() => fileRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  onFile(e.dataTransfer.files?.[0]);
                }}
                className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 cursor-pointer transition-colors ${
                  dragOver
                    ? "border-accent bg-accent-subtle"
                    : "border-border hover:border-accent/60"
                }`}
              >
                {previewLoading ? (
                  <div className="flex flex-col items-center py-4">
                    <Spinner size="md" />
                    <p className="text-xs text-text-muted mt-2">
                      Inspecting file headers...
                    </p>
                  </div>
                ) : file ? (
                  <>
                    <FileText className="h-8 w-8 text-accent mb-2" />
                    <p className="text-sm font-medium text-text-primary">
                      {file.name}
                    </p>
                    <p className="text-xs text-text-muted mt-1">
                      {(file.size / 1024).toFixed(1)} KB • {preview?.total_rows || 0} rows detected
                    </p>
                  </>
                ) : (
                  <>
                    <Upload className="h-8 w-8 text-text-muted mb-2" />
                    <p className="text-sm font-medium text-text-primary">
                      Drop your file here, or click to browse
                    </p>
                    <p className="text-xs text-text-muted mt-1">
                      Supports CSV, XLSX, JSON
                    </p>
                  </>
                )}
                <input
                  ref={fileRef}
                  type="file"
                  accept=".csv,.xlsx,.xls,.json,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/json"
                  className="hidden"
                  onChange={(e) => onFile(e.target.files?.[0])}
                />
              </div>
            </CardBody>
          </Card>

          {/* Step 2: Column & AI Variable Mapping */}
          {preview && (
            <Card>
              <CardHeader className="flex justify-between items-center">
                <div>
                  <h3 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
                    <Sparkles className="h-4 w-4 text-accent" />
                    2. Map Columns to Agent Variables
                  </h3>
                  <p className="text-xs text-text-muted">
                    Variables mapped below will be automatically replaced in your agent&apos;s greeting and prompt (e.g. {"{user_name}"}, {"{city}"}).
                  </p>
                </div>
              </CardHeader>
              <CardBody className="space-y-4">
                <div className="rounded-lg border border-border divide-y divide-border overflow-hidden">
                  <div className="grid grid-cols-12 bg-surface-subtle px-4 py-2 text-xs font-semibold text-text-secondary">
                    <div className="col-span-4">File Column & Preview</div>
                    <div className="col-span-8">Map to Field / AI Variable</div>
                  </div>

                  {preview.headers.map((header, idx) => {
                    const sampleVal = preview.sample_rows?.[0]?.[idx] ?? "";
                    const currentTarget = columnMapping[header] || "__skip__";
                    const isCustom = currentTarget === "__custom__";

                    return (
                      <div
                        key={header}
                        className="grid grid-cols-12 items-center px-4 py-3 gap-3 bg-surface"
                      >
                        <div className="col-span-4 min-w-0">
                          <p className="text-sm font-medium text-text-primary truncate">
                            {header}
                          </p>
                          <p className="text-xs text-text-muted truncate mt-0.5">
                            Sample: {sampleVal ? String(sampleVal) : <span className="italic">empty</span>}
                          </p>
                        </div>

                        <div className="col-span-8 space-y-2">
                          <Select
                            value={currentTarget}
                            onChange={(e) => handleMappingChange(header, e.target.value)}
                            options={MAPPING_OPTIONS}
                          />

                          {isCustom && (
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-text-muted shrink-0 font-mono">
                                {"{"}
                              </span>
                              <Input
                                value={customVariables[header] || ""}
                                onChange={(e) => handleCustomVariableChange(header, e.target.value)}
                                placeholder="variable_name"
                                className="font-mono text-xs"
                              />
                              <span className="text-xs text-text-muted shrink-0 font-mono">
                                {"}"}
                              </span>
                              <span className="text-xs text-text-muted shrink-0">
                                (Used in prompts as {"{" + (customVariables[header] || "var") + "}"})
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardBody>
            </Card>
          )}

          {/* Step 3: Destination & Tags */}
          <Card>
            <CardHeader>
              <h3 className="text-sm font-semibold text-text-primary">
                3. Destination Campaign & Tags
              </h3>
            </CardHeader>
            <CardBody className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-1">
                  Target Campaign (Optional)
                </label>
                <select
                  value={campaignId}
                  onChange={(e) => setCampaignId(e.target.value)}
                  className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
                >
                  <option value="">Do not enroll in a campaign (Contacts only)</option>
                  {campaigns.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.status})
                    </option>
                  ))}
                </select>
                <p className="text-xs text-text-muted mt-1">
                  Enrolling in a campaign lets this campaign dial these contacts independently without affecting other campaigns.
                </p>
              </div>

              <Input
                label="Tags (optional)"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="e.g. cold-leads, q4-outreach"
                hint="Comma-separated tags to label these contacts in your contact book"
              />
            </CardBody>
          </Card>

          <div className="flex justify-end gap-2">
            <Link href={campaignId ? `/campaigns/${campaignId}` : "/leads"}>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </Link>
            <Button type="submit" loading={uploading} disabled={!file || previewLoading}>
              <Upload className="h-4 w-4 mr-1.5" />
              Start Import
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
