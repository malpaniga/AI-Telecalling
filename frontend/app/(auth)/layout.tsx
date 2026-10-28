import type { Metadata } from "next";
import { AuthClientLayout } from "./auth-client-layout";

export const metadata: Metadata = {
  title: "NivLabs-Connect — Sign in",
};

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <AuthClientLayout>{children}</AuthClientLayout>;
}
