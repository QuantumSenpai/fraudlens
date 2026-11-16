"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

export function SignOut(): React.JSX.Element {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function signOut() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/session", { method: "DELETE" });
      if (!response.ok) throw new Error("Could not sign out. Try again.");
      router.replace("/");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not sign out.");
      setBusy(false);
    }
  }

  return <div className="sign-out-control"><button type="button" className="button button-outline button-small" disabled={busy} onClick={() => void signOut()}><LogOut size={16} />{busy ? "Signing out…" : "Sign out"}</button>{error && <span className="field-error" role="alert">{error}</span>}</div>;
}
