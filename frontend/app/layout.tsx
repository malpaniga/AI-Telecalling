import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/nav";

export const metadata: Metadata = {
  title: "Ava Console — Voice Agent Dashboard",
  description: "Real estate voice agent: calls, leads, analytics",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ink text-fg antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="grid-bg flex-1 overflow-x-hidden">{children}</main>
        </div>
      </body>
    </html>
  );
}
