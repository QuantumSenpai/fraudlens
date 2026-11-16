import { NextResponse } from "next/server";
import { getSession } from "@/lib/session";

export const maxDuration = 300;

export async function GET(request: Request): Promise<Response> {
  if (await getSession() !== "admin") return NextResponse.json({ error: "Sign in as an administrator" }, { status: 401 });
  if (!process.env.FRAUDLENS_API_URL || !process.env.FRAUDLENS_ADMIN_TOKEN) return NextResponse.json({ error: "FraudLens API is not configured" }, { status: 503 });
  try {
    const upstream = await fetch(new URL("/v1/admin/feed", process.env.FRAUDLENS_API_URL), {
      headers: { Authorization: `Bearer ${process.env.FRAUDLENS_ADMIN_TOKEN}`, Accept: "text/event-stream" },
      cache: "no-store",
      signal: request.signal,
    });
    if (!upstream.ok || !upstream.body) return NextResponse.json({ error: "Live feed is unavailable" }, { status: upstream.status });
    return new Response(upstream.body, { headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no" } });
  } catch {
    return NextResponse.json({ error: "Live feed is unavailable" }, { status: 503 });
  }
}
