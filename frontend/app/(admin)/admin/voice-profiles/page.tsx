"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Mic2, Plus } from "lucide-react";
import toast from "react-hot-toast";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { Modal } from "@/components/ui/modal";
import { Input, Select } from "@/components/ui/input";
import { SimpleTable, TableRow, TableCell } from "@/components/ui/table";
import { api, VoiceProfile } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

const LANGUAGE_OPTIONS = [
  { value: "en-IN", label: "English (India)" },
  { value: "hi-IN", label: "Hindi" },
  { value: "mr-IN", label: "Marathi" },
  { value: "gu-IN", label: "Gujarati" },
  { value: "ta-IN", label: "Tamil" },
  { value: "te-IN", label: "Telugu" },
  { value: "kn-IN", label: "Kannada" },
  { value: "ml-IN", label: "Malayalam" },
  { value: "bn-IN", label: "Bengali" },
  { value: "pa-IN", label: "Punjabi" },
];

export default function AdminVoiceProfilesPage() {
  const [profiles, setProfiles] = useState<VoiceProfile[]>([]);
  const [loading, setLoading] = useState(true);

  // Create profile
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createForm, setCreateForm] = useState({
    display_name: "",
    language: "en-IN",
    organization_id: "",
    is_platform: true,
  });

  // Create version
  const [showVersion, setShowVersion] = useState(false);
  const [versionProfileId, setVersionProfileId] = useState<string | null>(null);
  const [versionRoutes, setVersionRoutes] = useState("{}");
  const [creatingVersion, setCreatingVersion] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.admin.voiceProfiles.list();
      setProfiles(data);
    } catch (e: unknown) {
      toast.error(
        e instanceof Error ? e.message : "Failed to load voice profiles"
      );
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
      await api.admin.voiceProfiles.create({
        display_name: createForm.display_name,
        language: createForm.language,
        organization_id: createForm.organization_id || undefined,
        is_platform: createForm.is_platform,
      });
      toast.success("Voice profile created");
      setShowCreate(false);
      setCreateForm({
        display_name: "",
        language: "en-IN",
        organization_id: "",
        is_platform: true,
      });
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create profile");
    } finally {
      setCreating(false);
    }
  }

  async function handleCreateVersion(e: React.FormEvent) {
    e.preventDefault();
    if (!versionProfileId) return;
    setCreatingVersion(true);
    try {
      let routes: Record<string, unknown> = {};
      try {
        routes = JSON.parse(versionRoutes);
      } catch {
        toast.error("Routes must be valid JSON");
        setCreatingVersion(false);
        return;
      }
      await api.admin.voiceProfiles.createVersion(versionProfileId, routes);
      toast.success("Version created");
      setShowVersion(false);
      setVersionRoutes("{}");
      setVersionProfileId(null);
      await load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create version");
    } finally {
      setCreatingVersion(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">
          Voice Profiles
        </h2>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-1" />
          New Profile
        </Button>
      </div>

      <Card>
        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner size="lg" />
          </div>
        ) : profiles.length === 0 ? (
          <EmptyState
            icon={Mic2}
            title="No voice profiles"
            action={
              <Button onClick={() => setShowCreate(true)}>
                Create Profile
              </Button>
            }
          />
        ) : (
          <SimpleTable
            headers={[
              "Name",
              "Language",
              "Type",
              "Active Version",
              "Status",
              "Created",
              "Actions",
            ]}
          >
            {profiles.map((p) => (
              <TableRow key={p.id}>
                <TableCell className="font-medium">{p.display_name}</TableCell>
                <TableCell className="text-text-secondary">
                  {p.language}
                </TableCell>
                <TableCell>
                  <StatusBadge
                    status={p.is_platform ? "active" : "default"}
                  />
                  <span className="ml-1 text-xs text-text-muted">
                    {p.is_platform ? "platform" : "org"}
                  </span>
                </TableCell>
                <TableCell className="text-text-secondary">
                  {p.active_version != null ? `v${p.active_version}` : "—"}
                </TableCell>
                <TableCell>
                  <StatusBadge
                    status={p.is_active ? "active" : "inactive"}
                  />
                </TableCell>
                <TableCell className="text-xs text-text-muted">
                  {formatDateTime(p.created_at)}
                </TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setVersionProfileId(p.id);
                      setShowVersion(true);
                    }}
                  >
                    Add Version
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </SimpleTable>
        )}
      </Card>

      {/* Create Profile modal */}
      <Modal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        title="Create Voice Profile"
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <Input
            label="Display Name"
            value={createForm.display_name}
            onChange={(e) =>
              setCreateForm((f) => ({ ...f, display_name: e.target.value }))
            }
            placeholder="e.g. Priya — Warm Hindi"
            required
          />
          <Select
            label="Language"
            value={createForm.language}
            onChange={(e) =>
              setCreateForm((f) => ({ ...f, language: e.target.value }))
            }
            options={LANGUAGE_OPTIONS}
          />
          <Input
            label="Organisation ID (optional)"
            value={createForm.organization_id}
            onChange={(e) =>
              setCreateForm((f) => ({
                ...f,
                organization_id: e.target.value,
              }))
            }
            placeholder="Leave blank for platform profile"
            hint="Platform profiles are shared across all orgs"
          />
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={createForm.is_platform}
              onChange={(e) =>
                setCreateForm((f) => ({
                  ...f,
                  is_platform: e.target.checked,
                }))
              }
              className="rounded border-border accent-accent"
            />
            Platform profile (available to all organisations)
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowCreate(false)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={creating}>
              Create Profile
            </Button>
          </div>
        </form>
      </Modal>

      {/* Create Version modal */}
      <Modal
        isOpen={showVersion}
        onClose={() => {
          setShowVersion(false);
          setVersionProfileId(null);
        }}
        title="Add Voice Profile Version"
      >
        <form onSubmit={handleCreateVersion} className="space-y-4">
          <p className="text-sm text-text-secondary">
            Provider routes are stored internally and never exposed to
            customers. Enter a valid JSON object with the provider routing
            configuration.
          </p>
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1.5">
              Routes (JSON)
            </label>
            <textarea
              value={versionRoutes}
              onChange={(e) => setVersionRoutes(e.target.value)}
              rows={8}
              className="w-full rounded-[var(--radius-md)] border border-border bg-surface px-3 py-2 text-sm font-mono text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent resize-y"
              placeholder='{"provider": "sarvam", "voice_id": "..."}'
              required
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setShowVersion(false);
                setVersionProfileId(null);
              }}
            >
              Cancel
            </Button>
            <Button type="submit" loading={creatingVersion}>
              Create Version
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
