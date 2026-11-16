import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = process.env.SITE_URL?.replace(/\/$/, "");
  if (!base) return [];
  return ["", "/how-it-works", "/privacy"].map(path => ({ url: `${base}${path}`, changeFrequency: "monthly" as const, priority: path ? 0.6 : 1 }));
}
