"use client";

import { AuthProvider } from "@/contexts/auth-context";
import { Toaster } from "react-hot-toast";

export function AuthClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        {children}
      </div>
      <Toaster position="top-right" />
    </AuthProvider>
  );
}
