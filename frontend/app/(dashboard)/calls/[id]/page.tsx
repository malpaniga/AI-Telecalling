"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Download, Volume2, ExternalLink, Clock, FileAudio } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { api, Call } from "@/lib/api";
import { formatDateTime, formatDuration, formatDurationSec } from "@/lib/utils";
import toast from "react-hot-toast";

export default function CallDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [call, setCall] = useState<Call | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    api.calls.get(id)
      .then(setCall)
      .catch((e: unknown) => toast.error(e instanceof Error ? e.message : "Failed to load call"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <AppShell title="Call Detail">
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      </AppShell>
    );
  }

  if (!call) return null;

  const hasRecording = Boolean(call.recording_url);
  const recordingPlayUrl = api.calls.getRecordingUrl(call.id, false);
  const recordingDownloadUrl = api.calls.getRecordingUrl(call.id, true);

  return (
    <AppShell
      title="Call Detail"
      breadcrumb={[{ label: "Calls", href: "/calls" }, { label: call.to_number }]}
    >
      <div className="mb-4">
        <Link href="/calls">
          <Button variant="ghost" size="sm" className="gap-1 text-text-secondary">
            <ChevronLeft className="h-4 w-4" /> Back to Calls
          </Button>
        </Link>
      </div>

      {/* Recording Player Banner */}
      <Card className="mb-6 border-accent/20 bg-gradient-to-r from-surface to-surface-subtle">
        <CardHeader className="flex flex-row items-center justify-between pb-2 border-b border-border/60">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-accent/10 text-accent">
              <Volume2 className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary">Call Audio Recording</h3>
              <p className="text-xs text-text-muted">Full conversation audio (Caller + AI Agent)</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-surface-subtle border border-border text-text-secondary">
              <Clock className="h-3 w-3 text-accent" />
              <span>{formatDuration(call.duration_s)}</span>
            </div>
            {hasRecording && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                Ready
              </span>
            )}
          </div>
        </CardHeader>
        <CardBody className="pt-4 space-y-4">
          {hasRecording ? (
            <div className="space-y-3">
              <div className="p-2 rounded-xl bg-surface border border-border">
                <audio
                  controls
                  preload="metadata"
                  className="w-full h-10 outline-none"
                  src={recordingPlayUrl}
                >
                  Your browser does not support the audio element.
                </audio>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                <div className="flex items-center gap-2 text-xs text-text-muted">
                  <FileAudio className="h-3.5 w-3.5 text-text-secondary" />
                  <span>Audio Format: 16 kHz Mono WAV</span>
                  <span>•</span>
                  <span>Length: {formatDuration(call.duration_s)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <a
                    href={recordingPlayUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-border bg-surface text-text-secondary hover:text-text-primary hover:bg-surface-subtle transition-colors"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    Open in Tab
                  </a>
                  <a
                    href={recordingDownloadUrl}
                    download={`call_${call.id}.wav`}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-accent text-white hover:bg-accent/90 transition-colors shadow-sm"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download Recording
                  </a>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-6 text-center text-text-muted space-y-1.5">
              <Volume2 className="h-8 w-8 text-text-muted/40" />
              <p className="text-sm font-medium text-text-secondary">No audio recording available</p>
              <p className="text-xs max-w-md">
                {call.status === "completed"
                  ? "This call either had no audio streamed or ended before media was established."
                  : `Call status is '${call.status}'. Recordings are saved once calls conclude.`}
              </p>
            </div>
          )}
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Meta */}
        <Card>
          <CardHeader><h3 className="text-sm font-medium text-text-primary">Call Details</h3></CardHeader>
          <CardBody className="space-y-3 text-sm">
            <Row label="To" value={call.to_number} mono />
            <Row label="From" value={call.from_number} mono />
            <Row label="Direction" value={call.direction} />
            <Row label="Status"><StatusBadge status={call.status} /></Row>
            <Row label="Outcome">
              {call.outcome ? <StatusBadge status={call.outcome} /> : <span className="text-text-muted">—</span>}
            </Row>
            <Row label="Duration" value={formatDurationSec(call.duration_s)} />
            <Row label="Score" value={call.score > 0 ? String(call.score) : "—"} />
            <Row label="Credits" value={String(call.credits_consumed)} />
            <Row label="Latency" value={call.avg_latency_ms ? `${call.avg_latency_ms}ms` : "—"} />
            <Row label="Recording">
              {hasRecording ? (
                <span className="text-emerald-500 font-semibold text-xs">Available</span>
              ) : (
                <span className="text-text-muted text-xs">—</span>
              )}
            </Row>
            <Row label="Started" value={formatDateTime(call.started_at)} />
            {call.connected_at && <Row label="Connected" value={formatDateTime(call.connected_at)} />}
            {call.ended_at && <Row label="Ended" value={formatDateTime(call.ended_at)} />}
          </CardBody>
        </Card>

        {/* Summary + Qualification */}
        <Card className="lg:col-span-2">
          <CardHeader><h3 className="text-sm font-medium text-text-primary">Summary & Notes</h3></CardHeader>
          <CardBody>
            {call.summary ? (
              <p className="text-sm text-text-secondary whitespace-pre-wrap leading-relaxed">{call.summary}</p>
            ) : (
              <p className="text-sm text-text-muted">No summary available</p>
            )}

            {call.qualification && Object.entries(call.qualification).filter(([_, v]) => v !== null && v !== undefined && v !== "null" && v !== "None" && v !== "").length > 0 && (
              <div className="mt-4 pt-4 border-t border-border">
                <p className="text-xs font-medium text-text-muted uppercase tracking-wide mb-3">Qualification</p>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(call.qualification)
                    .filter(([_, v]) => v !== null && v !== undefined && v !== "null" && v !== "None" && v !== "")
                    .map(([k, v]) => (
                      <div key={k} className="flex justify-between items-center py-1 border-b border-border/40 last:border-b-0">
                        <span className="text-text-secondary capitalize font-medium">{k.replace(/_/g, " ")}</span>
                        <span className="font-semibold text-text-primary text-right">
                          {v === true || v === "true" ? "Yes" : v === false || v === "false" ? "No" : String(v)}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </AppShell>
  );
}

function Row({ label, value, mono, children }: { label: string; value?: string; mono?: boolean; children?: React.ReactNode }) {
  return (
    <div className="flex justify-between items-start gap-2">
      <span className="text-text-muted shrink-0">{label}</span>
      <span className={`text-right font-medium text-text-primary ${mono ? "font-mono text-xs" : ""}`}>
        {children ?? value}
      </span>
    </div>
  );
}
