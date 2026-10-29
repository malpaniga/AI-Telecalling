"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AuthProvider, useAuth } from "@/contexts/auth-context";
import { LoadingScreen } from "@/components/ui/spinner";
import { isAdmin } from "@/lib/auth";

function RootRedirect() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (!user) {
        router.replace("/login");
      } else if (isAdmin(user)) {
        router.replace("/admin/dashboard");
      } else {
        router.replace("/dashboard");
      }
    }
  }, [loading, user, router]);

  return <LoadingScreen />;
}

export default function RootPage() {
  return (
    <AuthProvider>
      <RootRedirect />
    </AuthProvider>
  );
}
