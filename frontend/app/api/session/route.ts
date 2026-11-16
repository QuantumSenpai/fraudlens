import { isSameOrigin } from "@/lib/request-origin";
import { NextRequest, NextResponse } from "next/server";
import { clearSession, setSession, verifyPassword, type Role } from "@/lib/session";

export async function POST(request: NextRequest): Promise<Response> {
  if (!isSameOrigin(request)) return NextResponse.json({ error: "Origin is not allowed" }, { status: 403 });
  const value = await request.json().catch(() => null);
  const role: Role = value?.role === "admin" ? "admin" : "merchant";
  if (typeof value?.password !== "string" || !verifyPassword(value.password, role)) return NextResponse.json({ error: "Invalid password or access is not configured" }, { status: 401 });
  await setSession(role);
  return NextResponse.json({ role });
}

export async function DELETE(request: NextRequest): Promise<Response> {
  if (!isSameOrigin(request)) return NextResponse.json({ error: "Origin is not allowed" }, { status: 403 });
  await clearSession();
  return NextResponse.json({ signed_out: true });
}
