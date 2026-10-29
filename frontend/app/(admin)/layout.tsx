"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthProvider, useAuth } from "@/contexts/auth-context";
import { Toaster } from "react-hot-toast";
import { LoadingScreen } from "@/components/ui/spinner";
import { AdminSidebar } from "@/components/layout/admin-sidebar";
import { Topbar } from "@/components/layout/topbar";

import { TestAgentProvider } from "@/contexts/test-agent-context";
import { TestAgentModal } from "@/components/test-agent/TestAgentModal";
import { isAdmin } from "@/lib/auth";

function AdminGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!loading) {
      if (!user) router.replace("/login");
      else if (!isAdmin(user)) router.replace("/dashboard");
    }
  }, [loading, user, router]);

  if (loading) return <LoadingScreen />;
  if (!user || !isAdmin(user)) return null;

  return (
    <TestAgentProvider>
      <div className="flex min-h-screen bg-background">
        <AdminSidebar isMobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />
        <div className="flex flex-1 flex-col min-w-0">
          <Topbar
            title="Admin"
            onMenuToggle={() => setMobileOpen(true)}
          />
          <main className="flex-1 overflow-auto p-4 md:p-6">{children}</main>
        </div>
      </div>
      <TestAgentModal />
    </TestAgentProvider>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <AdminGuard>{children}</AdminGuard>
      <Toaster position="top-right" />
    </AuthProvider>
  );
}
