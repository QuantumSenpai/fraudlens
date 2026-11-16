import type { NextRequest } from "next/server";

export function isSameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  // NextURL normalizes numeric loopback hosts to localhost. Host retains the browser's authority.
  const host = request.headers.get("host") || request.nextUrl.host;
  try {
    return origin === new URL(`${request.nextUrl.protocol}//${host}`).origin;
  } catch {
    return false;
  }
}
