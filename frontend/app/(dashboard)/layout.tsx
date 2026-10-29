"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AuthProvider, useAuth } from "@/contexts/auth-context";
import { Toaster } from "react-hot-toast";
import { LoadingScreen } from "@/components/ui/spinner";
import { isAdmin } from "@/lib/auth";

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (!user) {
        router.replace("/login");
      } else if (isAdmin(user)) {
        router.replace("/admin/dashboard");
      }
    }
  }, [loading, user, router]);

  if (loading) return <LoadingScreen />;
  if (!user || isAdmin(user)) return null;

  return <>{children}</>;
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <AuthGuard>{children}</AuthGuard>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "var(--color-surface)",
            color: "var(--color-text-primary)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-md)",
            fontSize: "14px",
          },
        }}
      />
    </AuthProvider>
  );
}
