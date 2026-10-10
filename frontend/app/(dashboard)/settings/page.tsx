"use client";

import React, { useState } from "react";
import { Settings, User, Bell } from "lucide-react";
import toast from "react-hot-toast";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

export default function SettingsPage() {
  const { user } = useAuth();
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
  });

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!user?.user_id) return;
    setSaving(true);
    try {
      await api.users.update(user.user_id, {
        first_name: form.first_name || undefined,
        last_name: form.last_name || undefined,
      });
      toast.success("Profile updated");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update profile");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell title="Settings">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-text-primary">Settings</h2>
      </div>

      <div className="max-w-2xl space-y-6">
        {/* Profile */}
        <Card>
          <CardHeader>
            <h3 className="text-sm font-medium text-text-primary flex items-center gap-2">
              <User className="h-4 w-4 text-text-muted" /> Profile
            </h3>
          </CardHeader>
          <CardBody>
            <form onSubmit={handleSaveProfile} className="flex flex-col gap-4">
              <div className="flex items-center gap-3 mb-2">
                <div className="h-12 w-12 rounded-full bg-accent-subtle flex items-center justify-center text-accent font-semibold">
                  {user?.email?.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <p className="font-medium text-text-primary">{user?.email}</p>
                  <p className="text-xs text-text-muted capitalize">{user?.role?.replace(/_/g, " ")}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="First name"
                  value={form.first_name}
                  onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))}
                  placeholder="Rahul"
                />
                <Input
                  label="Last name"
                  value={form.last_name}
                  onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))}
                  placeholder="Sharma"
                />
              </div>
              <div className="flex justify-end">
                <Button type="submit" loading={saving} size="sm">Save Profile</Button>
              </div>
            </form>
          </CardBody>
        </Card>

        {/* Account info */}
        <Card>
          <CardHeader>
            <h3 className="text-sm font-medium text-text-primary flex items-center gap-2">
              <Settings className="h-4 w-4 text-text-muted" /> Account
            </h3>
          </CardHeader>
          <CardBody className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-text-muted">Email</span>
              <span className="text-text-primary font-medium">{user?.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Role</span>
              <span className="text-text-primary font-medium capitalize">{user?.role?.replace(/_/g, " ")}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Organisation ID</span>
              <span className="text-text-primary font-mono text-xs">{user?.org_id ?? "—"}</span>
            </div>
          </CardBody>
        </Card>
      </div>
    </AppShell>
  );
}
