import type { Metadata } from "next";
import Link from "next/link";
import { ArrowUpRight, Fingerprint, ScanLine, ClipboardCheck, CreditCard, Webhook, ShieldX } from "lucide-react";

export const metadata: Metadata = { title: "How it works", description: "Follow a FraudLens check from device signals to a clear decision and Razorpay test payment.", alternates: process.env.SITE_URL ? { canonical: "/how-it-works" } : undefined };

const steps = [
  { icon: Fingerprint, title: "Register device context", body: "The merchant sends a stable install ID, platform, screen, language, and time zone. Location is optional and requested explicitly." },
  { icon: ScanLine, title: "Ask for a decision", body: "A check combines configured rules with the selected model. It returns ALLOW, REVIEW, or BLOCK, plus reasons and a check ID." },
  { icon: ClipboardCheck, title: "Resolve uncertain cases", body: "A reviewer can approve or reject a REVIEW case. That action writes labelled feedback for later evaluation." },
  { icon: CreditCard, title: "Continue to test Checkout", body: "ALLOW and approved REVIEW checks can create an INR order. Razorpay Checkout handles card and UPI details." },
  { icon: Webhook, title: "Confirm payment outcome", body: "FraudLens verifies the Checkout signature and the signed webhook. Only captured means paid." },
  { icon: ShieldX, title: "Stop blocked checks", body: "BLOCK cases cannot create orders. The merchant can show the decision without opening Checkout." },
];

export default function HowItWorks(): React.JSX.Element {
  return <main id="main" className="page-shell"><div className="page-header"><p className="eyebrow">THE PRODUCT FLOW</p><h1>One check. A clear next step.</h1><p>The gateway decides whether a test payment can proceed, requires review, or stops. It does not process the payment itself.</p></div><div className="prose-grid">{steps.map((step, index) => <article className="prose-card" key={step.title}><step.icon size={28} strokeWidth={1.5} aria-hidden="true" /><p className="mini-label">STEP {String(index + 1).padStart(2, "0")}</p><h2 className="section-label">{step.title}</h2><p>{step.body}</p></article>)}</div><Link className="button button-orange" href="/demo">Try a check <ArrowUpRight size={18} /></Link></main>;
}
