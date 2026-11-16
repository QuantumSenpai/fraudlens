"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { FormEvent, useState } from "react";
import { ArrowRight, LockKeyhole } from "lucide-react";

export function AccessForm({ role }: { role: "admin" | "merchant" }): React.JSX.Element {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/session", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role, password }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Access could not be verified");
      window.location.assign(role === "admin" ? "/admin" : "/demo");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not sign in");
      setBusy(false);
    }
  }
  return <form className="surface access-box" onSubmit={submit}><LockKeyhole size={28} strokeWidth={1.5} /><h1>{role === "admin" ? "Reviewer access" : "Merchant demo access"}</h1><p>Sign in to run test checks and follow their decisions.</p><div className="field"><label htmlFor="access-password">Password</label><input id="access-password" autoComplete="current-password" type="password" required minLength={8} value={password} onChange={event => setPassword(event.target.value)} /></div>{error && <div className="notice error" role="alert">{error}</div>}<Button type="submit" disabled={busy}>{busy ? "Checking access…" : "Continue"}<ArrowRight size={18} /></Button><p className="access-switch">{role === "admin" ? "Checking payments?" : "Reviewing cases?"} <Link className="text-link" href={role === "admin" ? "/access" : "/access?role=admin"}>{role === "admin" ? "Merchant access" : "Reviewer access"}</Link></p></form>;
}
