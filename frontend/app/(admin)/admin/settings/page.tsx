"use client";

import React, { useState } from "react";
import { Shield, KeyRound, Eye, EyeOff, User, CheckCircle2 } from "lucide-react";
import toast from "react-hot-toast";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";

export default function AdminSettingsPage() {
  const { user } = useAuth();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault();

    if (!currentPassword) {
      toast.error("Please enter your current password");
      return;
    }

    if (newPassword.length < 8) {
      toast.error("New password must be at least 8 characters long");
      return;
    }

    if (newPassword !== confirmPassword) {
      toast.error("New passwords do not match");
      return;
    }

    if (currentPassword === newPassword) {
      toast.error("New password must be different from current password");
      return;
    }

    setSavingPassword(true);
    try {
      const res = await api.auth.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast.success(res.message || "Admin password updated successfully");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update password");
    } finally {
      setSavingPassword(false);
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-lg font-semibold text-text-primary">Admin Settings</h2>
        <p className="text-xs text-text-muted mt-0.5">
          Manage your super admin credentials and security preferences.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left col: Admin profile info */}
        <div className="md:col-span-1 space-y-4">
          <Card>
            <CardHeader>
              <h3 className="text-sm font-medium text-text-primary flex items-center gap-2">
                <User className="h-4 w-4 text-accent" />
                <span>Admin Profile</span>
              </h3>
            </CardHeader>
            <CardBody className="space-y-4 text-xs">
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-full bg-accent/20 text-accent font-bold flex items-center justify-center text-sm">
                  {user?.email ? user.email.slice(0, 2).toUpperCase() : "AD"}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-text-primary truncate">
                    {user?.email}
                  </p>
                  <span className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-accent/10 text-accent capitalize">
                    <Shield className="h-3 w-3" />
                    {user?.role?.replace(/_/g, " ") ?? "Platform Admin"}
                  </span>
                </div>
              </div>

              <div className="pt-3 border-t border-border space-y-2">
                <div className="flex justify-between">
                  <span className="text-text-muted">Account Status</span>
                  <span className="text-success font-medium flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Active
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Role Scope</span>
                  <span className="text-text-primary font-medium">Platform-wide</span>
                </div>
              </div>
            </CardBody>
          </Card>
        </div>

        {/* Right col: Password update form */}
        <div className="md:col-span-2">
          <Card>
            <CardHeader>
              <h3 className="text-sm font-medium text-text-primary flex items-center gap-2">
                <KeyRound className="h-4 w-4 text-accent" />
                <span>Update Admin Password</span>
              </h3>
            </CardHeader>
            <CardBody>
              <form onSubmit={handlePasswordChange} className="space-y-4">
                <p className="text-xs text-text-secondary">
                  Ensure your super administrator account is secured with a strong password of at least 8 characters.
                </p>

                <div className="space-y-3">
                  <div className="relative">
                    <Input
                      label="Current Password"
                      type={showCurrent ? "text" : "password"}
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      placeholder="Enter current password"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowCurrent((prev) => !prev)}
                      className="absolute right-3 top-8 text-text-muted hover:text-text-primary transition-colors"
                      title={showCurrent ? "Hide password" : "Show password"}
                    >
                      {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>

                  <div className="relative">
                    <Input
                      label="New Password"
                      type={showNew ? "text" : "password"}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Enter at least 8 characters"
                      hint="Must be at least 8 characters long"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowNew((prev) => !prev)}
                      className="absolute right-3 top-8 text-text-muted hover:text-text-primary transition-colors"
                      title={showNew ? "Hide password" : "Show password"}
                    >
                      {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>

                  <Input
                    label="Confirm New Password"
                    type={showNew ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter new password"
                    required
                  />
                </div>

                <div className="flex justify-end pt-3 border-t border-border">
                  <Button
                    type="submit"
                    size="sm"
                    loading={savingPassword}
                    disabled={!currentPassword || !newPassword || newPassword.length < 8 || newPassword !== confirmPassword}
                  >
                    Update Admin Password
                  </Button>
                </div>
              </form>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}
