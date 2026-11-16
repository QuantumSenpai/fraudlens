import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Dashboard } from "@/components/dashboard";
import { getSession } from "@/lib/session";
import { SignOut } from "@/components/sign-out";

export const metadata: Metadata = { title: "Admin dashboard", description: "Inspect checks, resolve review cases, and evaluate labelled feedback.", robots: { index: false, follow: false } };
export const dynamic = "force-dynamic";

export default async function Admin(): Promise<React.JSX.Element> {
  if (await getSession() !== "admin") redirect("/access?role=admin");
  return <main id="main" className="app-shell"><div className="workspace-signout"><SignOut /></div><Dashboard /></main>;
}
