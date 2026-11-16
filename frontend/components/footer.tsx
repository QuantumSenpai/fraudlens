import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Brand } from "@/components/brand";

export function Footer(): React.JSX.Element {
  return <footer className="site-footer"><div className="footer-main"><div><Brand /><p>Clear decisions before a test payment begins.</p></div><nav aria-label="Footer navigation"><Link href="/how-it-works">How it works</Link><Link href="/demo">Merchant demo</Link><Link href="/admin">Dashboard</Link><Link href="/privacy">Data use</Link><a href="https://github.com/QuantumSenpai/fraudlens" target="_blank" rel="noreferrer">GitHub <ArrowUpRight size={14} /></a></nav></div><div className="footer-bottom"><span>© {new Date().getFullYear()} FraudLens</span><span>Made by QuantumSenpai</span><span>Razorpay integration is test mode only. No real money moves through this demo.</span></div></footer>;
}
