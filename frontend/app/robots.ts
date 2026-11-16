import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return { rules: [{ userAgent: "*", allow: ["/", "/how-it-works", "/privacy"], disallow: ["/admin", "/demo", "/access", "/api/"] }], sitemap: process.env.SITE_URL ? `${process.env.SITE_URL.replace(/\/$/, "")}/sitemap.xml` : undefined };
}
