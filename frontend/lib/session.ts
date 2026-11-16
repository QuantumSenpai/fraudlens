import "server-only";
import { createHmac, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";

export type Role = "merchant" | "admin";
const cookieName = "fraudlens_session";

function signature(value: string): string {
  return createHmac("sha256", process.env.SESSION_SECRET || "").update(value).digest("base64url");
}

export function verifyPassword(input: string, role: Role): boolean {
  const expected = role === "admin" ? process.env.ADMIN_PASSWORD : process.env.DEMO_PASSWORD;
  if (!expected || !process.env.SESSION_SECRET || input.length > 256) return false;
  const left = createHmac("sha256", process.env.SESSION_SECRET).update(input).digest();
  const right = createHmac("sha256", process.env.SESSION_SECRET).update(expected).digest();
  return timingSafeEqual(left, right);
}

export async function setSession(role: Role): Promise<void> {
  const payload = Buffer.from(JSON.stringify({ role, exp: Date.now() + 8 * 60 * 60 * 1000 })).toString("base64url");
  (await cookies()).set(cookieName, `${payload}.${signature(payload)}`, {
    httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: 8 * 60 * 60,
  });
}

export async function clearSession(): Promise<void> {
  (await cookies()).delete(cookieName);
}

export async function getSession(): Promise<Role | null> {
  if (!process.env.SESSION_SECRET) return null;
  const raw = (await cookies()).get(cookieName)?.value;
  if (!raw) return null;
  const [payload, proof] = raw.split(".");
  if (!payload || !proof) return null;
  const expected = Buffer.from(signature(payload));
  const received = Buffer.from(proof);
  if (expected.length !== received.length || !timingSafeEqual(expected, received)) return null;
  try {
    const value = JSON.parse(Buffer.from(payload, "base64url").toString());
    return value.exp > Date.now() && (value.role === "merchant" || value.role === "admin") ? value.role : null;
  } catch {
    return null;
  }
}

export function allows(role: Role | null, required: Role): boolean {
  return role === "admin" || (required === "merchant" && role === "merchant");
}
