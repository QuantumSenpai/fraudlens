import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DecisionStage } from "@/components/decision-stage";

vi.mock("gsap", () => ({ gsap: { matchMedia: () => ({ add: vi.fn(), revert: vi.fn() }) } }));

beforeEach(() => { vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} }); });

describe("illustrative decision walkthrough", () => {
  it("labels the transaction as illustrative and changes the consequence and destination", () => {
    render(<DecisionStage />);
    expect(screen.getByText(/ILLUSTRATIVE TRANSACTION/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Run a test check" }).getAttribute("href")).toBe("/demo");
    expect(document.querySelector(".stage-ticket > strong")?.textContent).toBe("₹1,250.00");
    fireEvent.click(screen.getByRole("button", { name: "REVIEW" }));
    expect(screen.getByRole("button", { name: "REVIEW" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("Waiting for reviewer approval")).toBeTruthy();
    expect(document.querySelector(".stage-ticket > strong")?.textContent).toBe("₹45,000.00");
    expect(screen.getByText(/New device.*payment burst/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Explore the reviewer workspace" }).getAttribute("href")).toBe("/admin");
    fireEvent.click(screen.getByRole("button", { name: "BLOCK" }));
    expect(screen.getByText("Checkout stays closed")).toBeTruthy();
    expect(document.querySelector(".stage-ticket > strong")?.textContent).toBe("₹2,50,000.00");
    expect(screen.getByText(/High amount.*impossible travel/)).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Run a test check" })).toBeNull();
    expect(screen.getByRole("link", { name: "Understand the decision flow" }).getAttribute("href")).toBe("/how-it-works");
  });
  it("keeps a single selected outcome after rapid changes", () => {
    render(<DecisionStage />);
    for (const name of ["BLOCK", "REVIEW", "ALLOW", "BLOCK", "ALLOW"]) fireEvent.click(screen.getByRole("button", { name }));
    expect(screen.getAllByRole("button").filter(node => node.getAttribute("aria-pressed") === "true")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "ALLOW" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("Eligible for test Checkout")).toBeTruthy();
    expect(document.querySelector(".stage-ticket > strong")?.textContent).toBe("₹1,250.00");
  });
});
