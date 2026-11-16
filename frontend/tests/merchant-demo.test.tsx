import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MerchantDemo } from "@/components/merchant-demo";
import type { Check } from "@/lib/types";

const base: Check = { check_id: "00000000-0000-0000-0000-000000000001", decision: "ALLOW", final_score: 12, ml_score: 10, rule_score: 15, reasons: [], model_version: "xgb_live_v1", ml_factors: [], latency_ms: 18 };
const json = (value: unknown, status = 200, headers: Record<string, string> = {}) => new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json", ...headers } });

function fill() {
  fireEvent.change(screen.getByLabelText("Merchant user ID"), { target: { value: "test-user" } });
  fireEvent.change(screen.getByLabelText("Amount in INR"), { target: { value: "250" } });
  fireEvent.click(screen.getByRole("button", { name: /Run fraud check/ }));
}

beforeEach(() => {
  delete window.Razorpay;
  const values = new Map<string, string>();
  vi.stubGlobal("localStorage", { getItem: (key: string) => values.get(key) || null, setItem: (key: string, value: string) => values.set(key, value), clear: () => values.clear() });
  vi.stubGlobal("crypto", { randomUUID: () => "00000000-0000-4000-8000-000000000001" });
});

describe("merchant decisions", () => {
  for (const decision of ["ALLOW", "REVIEW", "BLOCK"] as const) {
    it(`shows ${decision} and gates payment`, async () => {
      const requests: string[] = [];
      vi.stubGlobal("fetch", vi.fn(async (input: string) => {
        requests.push(input);
        if (input.endsWith("/v1/signals")) return json({ device_id: "device" });
        if (input.endsWith("/v1/checks")) return json({ ...base, decision });
        return json({ error: { message: "Review approval is required" }, request_id: "request-review" }, 409);
      }));
      render(<MerchantDemo />);
      await screen.findByText(/Install ID:/);
      fill();
      await screen.findByText(decision === "ALLOW" ? "Clear to continue" : decision === "REVIEW" ? "Needs a reviewer" : "Payment stopped");
      expect(requests).toEqual(["/api/gateway/v1/signals", "/api/gateway/v1/checks"]);
      if (decision === "BLOCK") expect(screen.queryByRole("button", { name: /Checkout|continue/i })).toBeNull();
      if (decision === "REVIEW") {
        fireEvent.click(screen.getByRole("button", { name: /Check approval and continue/ }));
        await screen.findByText(/Request ID: request-review/);
      }
      if (decision === "ALLOW") expect(screen.getByRole("button", { name: /Continue to test Checkout/ })).toBeTruthy();
    });
  }

  it("surfaces rate limits and request IDs", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: string) => input.endsWith("/v1/signals") ? json({ device_id: "device" }) : json({ error: { message: "Rate limit exceeded" }, request_id: "req-429" }, 429, { "Retry-After": "12" })));
    render(<MerchantDemo />);
    await screen.findByText(/Install ID:/);
    fill();
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Try again in 12 seconds. Request ID: req-429"));
  });

  it("handles an empty check response", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: string) => input.endsWith("/v1/signals") ? json({ device_id: "device" }) : new Response("", { status: 200, headers: { "X-Request-ID": "empty-check" } })));
    render(<MerchantDemo />);
    await screen.findByText(/Install ID:/);
    fill();
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Request ID: empty-check"));
  });

  it("opens a test order and treats only captured as paid", async () => {
    let status: "authorized" | "captured" = "authorized";
    let checkoutHandler: ((value: { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }) => void) | undefined;
    const open = vi.fn();
    vi.stubGlobal("fetch", vi.fn(async (input: string) => {
      if (input.endsWith("/v1/signals")) return json({ device_id: "device" });
      if (input.endsWith("/v1/checks")) return json(base);
      if (input.endsWith("/v1/payments/order")) return json({ order_id: "order_test_1", amount: 25000, currency: "INR", key_id: "rzp_test_public" });
      return json({ order_id: "order_test_1", payment_id: "pay_test_1", status });
    }));
    window.Razorpay = class {
      constructor(options: Record<string, unknown>) { checkoutHandler = options.handler as typeof checkoutHandler; }
      open = open;
      on() {}
    };
    render(<MerchantDemo />);
    await screen.findByText(/Install ID:/);
    fill();
    await screen.findByText("Clear to continue");
    fireEvent.click(screen.getByRole("button", { name: /Continue to test Checkout/ }));
    await waitFor(() => expect(open).toHaveBeenCalledOnce());
    await act(async () => { checkoutHandler?.({ razorpay_order_id: "order_test_1", razorpay_payment_id: "pay_test_1", razorpay_signature: "a".repeat(64) }); });
    await screen.findByText(/Do not mark paid until captured/);
    status = "captured";
    fireEvent.click(screen.getByRole("button", { name: /Refresh capture status/ }));
    await screen.findByText(/Paid in test mode/);
  });
});

it("keeps the demo usable when browser storage is unavailable", async () => {
  vi.stubGlobal("localStorage", { getItem: () => { throw new Error("Storage blocked"); }, setItem: vi.fn() });
  render(<MerchantDemo />);
  await screen.findByRole("alert");
  expect(screen.getByRole("alert").textContent).toContain("Browser storage is unavailable");
});

it("rejects a whitespace-only merchant user ID before sending signals", async () => {
  const fetch = vi.fn(); vi.stubGlobal("fetch",fetch);
  render(<MerchantDemo />);
  await waitFor(() => expect(screen.getByRole("button", {name:/Run fraud check/}).hasAttribute("disabled")).toBe(false));
  fireEvent.change(screen.getByLabelText("Merchant user ID"), {target:{value:"   "}});
  fireEvent.change(screen.getByLabelText("Amount in INR"), {target:{value:"250"}});
  fireEvent.click(screen.getByRole("button", {name:/Run fraud check/}));
  await screen.findByText("Enter a merchant user ID.");
  expect(fetch).not.toHaveBeenCalled();
});
