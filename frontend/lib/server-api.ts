import { isSameOrigin } from "@/lib/request-origin";
import "server-only";
import { NextRequest, NextResponse } from "next/server";
import { allows, getSession, type Role } from "@/lib/session";

const merchant = new Set(["v1/signals", "v1/checks", "v1/payments/order", "v1/payments/verify"]);
const adminGet = new Set(["v1/admin/stats", "v1/admin/evaluation", "v1/admin/reviews"]);

function error(status: number, message: string): NextResponse {
  const requestId = crypto.randomUUID();
  const code = status === 400 ? "request_failed" : status === 401 ? "unauthorized" : status === 403 ? "forbidden" : status === 404 ? "not_found" : status === 413 ? "request_too_large" : "service_unavailable";
  return NextResponse.json({ error: { code, message }, request_id: requestId }, { status, headers: { "X-Request-ID": requestId } });
}

export async function forward(request: NextRequest, segments: string[], method: "GET" | "POST"): Promise<Response> {
  const path = segments.join("/");
  const isReviewPost = method === "POST" && /^v1\/admin\/reviews\/[0-9a-f-]{36}$/i.test(path);
  const required: Role | null = method === "POST" && merchant.has(path) ? "merchant" : method === "GET" && adminGet.has(path) || isReviewPost ? "admin" : null;
  if (!required) return error(404, "Route unavailable");
  if (!allows(await getSession(), required)) return error(401, "Sign in to continue");
  const configured = process.env.FRAUDLENS_API_URL;
  const credential = required === "admin" ? process.env.FRAUDLENS_ADMIN_TOKEN : process.env.FRAUDLENS_API_KEY;
  if (!configured || !credential) return error(503, "FraudLens API credentials are not configured");
  if (method === "POST" && !isSameOrigin(request)) return error(403, "Origin is not allowed");
  const url = new URL(`/${path}`, configured);
  if (path === "v1/admin/reviews") {
    for (const name of ["status", "limit", "offset"]) {
      const value = request.nextUrl.searchParams.get(name);
      if (value !== null) url.searchParams.set(name, value);
    }
  }
  const headers = new Headers({ "Content-Type": "application/json" });
  headers.set(required === "admin" ? "Authorization" : "X-API-Key", required === "admin" ? `Bearer ${credential}` : credential);
  if (["v1/checks", "v1/payments/order"].includes(path)) {
    const key = request.headers.get("Idempotency-Key");
    if (!key || key.length > 128) return error(400, "Idempotency-Key is required and must be at most 128 characters");
    headers.set("Idempotency-Key", key);
  }
  let body: string | undefined;
  if (method === "POST") {
    body = await request.text();
    if (body.length > 16000) return error(413, "Request is too large");
    try { JSON.parse(body); } catch { return error(400, "Invalid JSON"); }
  }
  try {
    const upstream = await fetch(url, { method, headers, body, cache: "no-store", signal: AbortSignal.timeout(20000) });
    const outputHeaders = new Headers({ "Content-Type": upstream.headers.get("content-type") || "application/json", "Cache-Control": "no-store" });
    for (const name of ["x-request-id", "retry-after", "server-timing"]) {
      const value = upstream.headers.get(name);
      if (value) outputHeaders.set(name, value);
    }
    return new Response(await upstream.text(), { status: upstream.status, headers: outputHeaders });
  } catch {
    return error(503, "FraudLens API is unavailable. Try again shortly.");
  }
}
