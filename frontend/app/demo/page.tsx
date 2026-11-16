import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { ArrowUpRight } from "lucide-react";
import { MerchantDemo } from "@/components/merchant-demo";
import { allows, getSession } from "@/lib/session";
import { SignOut } from "@/components/sign-out";

export const metadata: Metadata = { title: "Merchant demo", description: "Run a payment check, inspect its reasons, and continue to eligible Razorpay test Checkout.", robots: { index: false, follow: false } };
export const dynamic = "force-dynamic";

export default async function Demo(): Promise<React.JSX.Element> {
  if (!allows(await getSession(), "merchant")) redirect("/access");
  return <main id="main" className="app-shell"><div className="app-heading"><div><p className="eyebrow">MERCHANT WORKSPACE</p><h1>Check a payment.</h1><p>Register device context, get a decision, and continue only when eligible.</p></div><div className="form-actions"><a className="text-link" href="/how-it-works">How it works <ArrowUpRight size={17} /></a><SignOut /></div></div><MerchantDemo /></main>;
}
