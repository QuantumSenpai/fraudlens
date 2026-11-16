import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Dashboard } from "@/components/dashboard";

class FakeEventSource {
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(public url: string) {}
  addEventListener() {}
  close() {}
}

const json = (value: unknown) => new Response(JSON.stringify(value), { status: 200, headers: { "Content-Type": "application/json" } });
const stats = { total_checks: 0, decision_split: { ALLOW: 0, REVIEW: 0, BLOCK: 0 }, flagged_count: 0, flagged_rate_percent: 0, top_triggered_rules: [], average_latency_ms: null, p95_scoring_latency_ms: null, last_24h_hourly_counts: Array.from({length:24},(_,hour)=>({hour:String(hour),count:0})) };
const review = { id: "00000000-0000-0000-0000-000000000001", user_id: "user", device_id: "device", amount: 95000, currency: "INR", payment_method: "upi", final_score: 40, reasons: [{ rule: "STRUCTURING", detail: "Three nearby payments", weight: 35 }], created_at: "2026-11-16T00:00:00Z", review: null };

beforeEach(() => { vi.stubGlobal("EventSource", FakeEventSource); });

describe("admin dashboard", () => {
  it("shows zero-data states and reconnect control", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: string) => input.includes("evaluation") ? json({ labels_total: 0 }) : json(stats)));
    render(<Dashboard />);
    await screen.findByText("No hourly activity yet");
    expect(screen.getByText("No live events yet")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Reconnect feed/ }));
    expect(screen.getByText("Connecting")).toBeTruthy();
  });

  for (const outcome of ["approve", "reject"] as const) {
    it(`${outcome}s a review after confirmation`, async () => {
      const calls: { url: string; body?: string }[] = [];
      vi.stubGlobal("fetch", vi.fn(async (input: string, options?: RequestInit) => {
        calls.push({ url: input, body: options?.body as string | undefined });
        if (input.includes("/reviews/")) return json({ outcome });
        if (input.includes("/reviews?")) return json([review]);
        if (input.includes("evaluation")) return json({ labels_total: 0 });
        return json(stats);
      }));
      render(<Dashboard />);
      fireEvent.click(screen.getByRole("button", { name: "Reviews" }));
      await screen.findByText("Three nearby payments");
      fireEvent.click(screen.getByRole("button", { name: outcome === "approve" ? "Approve" : "Reject" }));
      expect(screen.getByRole("dialog")).toBeTruthy();
      fireEvent.change(screen.getByLabelText("Reviewer name"), { target: { value: "Analyst" } });
      fireEvent.click(screen.getByRole("button", { name: `Confirm ${outcome}` }));
      await waitFor(() => expect(calls.some(call => call.url.includes("/reviews/") && call.body?.includes(`"outcome":"${outcome}"`))).toBe(true));
    });
  }

  it("keeps a failed review visible inside its confirmation dialog", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: string) => {
      if (input.includes("/reviews/")) return new Response(JSON.stringify({ error: { message: "Review is already resolved" }, request_id: "review-409" }), { status: 409, headers: { "Content-Type": "application/json" } });
      if (input.includes("/reviews?")) return json([review]);
      if (input.includes("evaluation")) return json({ labels_total: 0 });
      return json(stats);
    }));
    render(<Dashboard />);
    fireEvent.click(screen.getByRole("button", { name: "Reviews" }));
    await screen.findByText("Three nearby payments");
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    fireEvent.change(screen.getByLabelText("Reviewer name"), { target: { value: "Analyst" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm approve" }));
    await waitFor(() => expect(screen.getByRole("dialog").textContent).toContain("Request ID: review-409"));
  });
});
