import type { Metadata } from "next";
import { AccessForm } from "@/components/access-form";

export const metadata: Metadata = { title: "Access", description: "Sign in to the merchant demo or reviewer workspace.", robots: { index: false, follow: false } };

export default async function Access({ searchParams }: { searchParams: Promise<{ role?: string }> }): Promise<React.JSX.Element> {
  const role = (await searchParams).role === "admin" ? "admin" : "merchant";
  return <main id="main" className="page-shell"><AccessForm role={role} /></main>;
}
