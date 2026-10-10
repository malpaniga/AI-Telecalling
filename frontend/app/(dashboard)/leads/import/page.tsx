"use client";

import React, { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Upload, FileText, AlertTriangle } from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { api } from "@/lib/api";

export default function LeadsImportPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [tags, setTags] = useState("");
  const [campaignId, setCampaignId] = useState("");
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{
    imported: number;
    skipped: number;
    errors: number;
  } | null>(null);
  const [dragOver, setDragOver] = useState(false);

  function onFile(f: File | null | undefined) {
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
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      toast.error("Select a file to import");
      return;
    }
    setUploading(true);
    try {
      const res = await api.leads.import(file, {
        campaign_id: campaignId || undefined,
        tags: tags.trim() || undefined,
      });
      setResult(res);
      toast.success(`Imported ${res.imported} leads`);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Import failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-xl space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-3">
        <Link href="/leads">
          <Button variant="ghost" size="sm" className="gap-1">
            <ChevronLeft className="h-4 w-4" />
            Back
          </Button>
        </Link>
        <h2 className="text-lg font-semibold text-text-primary">
          Import Leads
        </h2>
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
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-lg bg-surface-subtle p-4">
                <p className="text-2xl font-bold text-success">
                  {result.imported}
                </p>
                <p className="text-xs text-text-muted mt-1">Imported</p>
              </div>
              <div className="rounded-lg bg-surface-subtle p-4">
                <p className="text-2xl font-bold text-text-secondary">
                  {result.skipped}
                </p>
                <p className="text-xs text-text-muted mt-1">Skipped</p>
              </div>
              <div className="rounded-lg bg-surface-subtle p-4">
                <p
                  className={`text-2xl font-bold ${result.errors > 0 ? "text-danger" : "text-text-secondary"}`}
                >
                  {result.errors}
                </p>
                <p className="text-xs text-text-muted mt-1">Errors</p>
              </div>
            </div>
            {result.errors > 0 && (
              <div className="flex items-start gap-2 rounded-lg bg-danger/5 border border-danger/20 p-3 text-sm text-danger">
                <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>
                  {result.errors} row(s) could not be imported. This is usually
                  due to duplicate phone numbers or missing required fields.
                </span>
              </div>
            )}
            <div className="flex gap-2 pt-2">
              <Button
                variant="secondary"
                onClick={() => {
                  setResult(null);
                  setFile(null);
                }}
              >
                Import More
              </Button>
              <Button onClick={() => router.push("/leads")}>
                View Leads
              </Button>
            </div>
          </CardBody>
        </Card>
      ) : (
        <form onSubmit={handleUpload} className="space-y-4">
          {/* Drop zone */}
          <Card>
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
                className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 cursor-pointer transition-colors ${
                  dragOver
                    ? "border-accent bg-accent-subtle"
                    : "border-border hover:border-accent/60"
                }`}
              >
                {file ? (
                  <>
                    <FileText className="h-8 w-8 text-accent mb-2" />
                    <p className="text-sm font-medium text-text-primary">
                      {file.name}
                    </p>
                    <p className="text-xs text-text-muted mt-1">
                      {(file.size / 1024).toFixed(1)} KB
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
                  accept=".csv,.xlsx,.json,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/json"
                  className="hidden"
                  onChange={(e) => onFile(e.target.files?.[0])}
                />
              </div>
            </CardBody>
          </Card>

          {/* Options */}
          <Card>
            <CardHeader>
              <h3 className="text-sm font-semibold text-text-primary">
                Import Options
              </h3>
            </CardHeader>
            <CardBody className="space-y-4">
              <Input
                label="Tags (optional)"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="e.g. cold-leads,q4-campaign"
                hint="Comma-separated tags to apply to all imported leads"
              />
              <Input
                label="Campaign ID (optional)"
                value={campaignId}
                onChange={(e) => setCampaignId(e.target.value)}
                placeholder="Leave blank to add unassigned leads"
              />
            </CardBody>
          </Card>

          <div className="flex justify-end gap-2">
            <Link href="/leads">
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </Link>
            <Button type="submit" loading={uploading} disabled={!file}>
              <Upload className="h-4 w-4 mr-1.5" />
              Import Leads
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
