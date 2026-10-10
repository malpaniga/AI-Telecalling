import { redirect } from "next/navigation";

// Root redirects to the dashboard (authenticated pages handled by middleware/layout in later FEATs)
export default function RootPage() {
  redirect("/dashboard");
}
