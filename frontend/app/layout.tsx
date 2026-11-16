import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import { Header } from "@/components/header";
import { Footer } from "@/components/footer";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const space = Space_Grotesk({ subsets: ["latin"], variable: "--font-space", display: "swap" });
const siteUrl = process.env.SITE_URL;

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl || "http://localhost:3000"),
  title: { default: "FraudLens | Decide before payment", template: "%s | FraudLens" },
  description: "FraudLens checks device and payment signals before a Razorpay test payment, then gives a clear allow, review, or block decision.",
  openGraph: { title: "FraudLens | From signal to decision", description: "Clear fraud decisions before test payments begin.", type: "website", images: ["/opengraph-image"] },
  twitter: { card: "summary_large_image", title: "FraudLens", description: "From signal to decision." },
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = { themeColor: "#161616", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>): React.JSX.Element {
  return <html lang="en" data-scroll-behavior="smooth" className={`${inter.variable} ${space.variable}`}><body><a className="skip-link" href="#main">Skip to content</a><Header />{children}<Footer /></body></html>;
}
