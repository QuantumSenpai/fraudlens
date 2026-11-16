import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return { name: "FraudLens", short_name: "FraudLens", description: "Fraud decisions before test payments", start_url: "/", display: "standalone", background_color: "#FEF8E8", theme_color: "#161616", icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }] };
}
