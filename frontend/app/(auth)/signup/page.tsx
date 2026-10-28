"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mic2 } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import { setTokens } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SignupPage() {
  const { refresh } = useAuth();
  const router = useRouter();

  const [form, setForm] = useState({
    org_name: "",
    org_email: "",
    email: "",
    password: "",
    first_name: "",
    last_name: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function set(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (form.password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);
    try {
      const data = await api.auth.signup({
        org_name: form.org_name,
        org_email: form.org_email || form.email,
        email: form.email,
        password: form.password,
        first_name: form.first_name || undefined,
        last_name: form.last_name || undefined,
      });
      setTokens(data.access_token, data.refresh_token);
      await refresh();
      router.replace("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-sm">
      <div className="flex flex-col items-center gap-3 mb-8">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent shadow-sm">
          <Mic2 className="h-5 w-5 text-white" />
        </div>
        <div className="text-center">
          <h1 className="text-xl font-semibold text-text-primary">Create your account</h1>
          <p className="text-sm text-text-secondary mt-0.5">Get started with NivLabs-Connect</p>
        </div>
      </div>

      <div className="bg-surface rounded-lg border border-border shadow-sm p-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="Organisation name"
            value={form.org_name}
            onChange={set("org_name")}
            placeholder="Acme Pvt Ltd"
            required
          />
          <Input
            label="Work email"
            type="email"
            value={form.email}
            onChange={set("email")}
            placeholder="you@company.com"
            required
            autoComplete="email"
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="First name"
              value={form.first_name}
              onChange={set("first_name")}
              placeholder="Rahul"
            />
            <Input
              label="Last name"
              value={form.last_name}
              onChange={set("last_name")}
              placeholder="Sharma"
            />
          </div>
          <Input
            label="Password"
            type="password"
            value={form.password}
            onChange={set("password")}
            placeholder="Min. 8 characters"
            required
            minLength={8}
            autoComplete="new-password"
          />

          {error && (
            <p className="text-sm text-danger bg-[#FDEEEE] rounded-md px-3 py-2 border border-[#F2C0C0]">
              {error}
            </p>
          )}

          <Button type="submit" loading={loading} className="w-full mt-1">
            Create account
          </Button>
        </form>
      </div>

      <p className="text-center text-sm text-text-secondary mt-4">
        Already have an account?{" "}
        <Link href="/login" className="text-accent hover:underline font-medium">
          Sign in
        </Link>
      </p>
    </div>
  );
}
