import type { NextConfig } from "next";

const config: NextConfig = { reactStrictMode: true, devIndicators: false, turbopack: { root: process.cwd() } };

export default config;
