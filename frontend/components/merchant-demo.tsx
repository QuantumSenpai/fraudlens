"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";
import { ArrowRight, CircleHelp, CreditCard, Fingerprint, LocateFixed, RefreshCw, ScanLine, ShieldCheck } from "lucide-react";
import { api, errorText } from "@/lib/client-api";
import type { Check, Order, PaymentMethod, Verification } from "@/lib/types";
import { DecisionBadge } from "@/components/decision-badge";

type CheckoutResult = { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string };
type RazorpayInstance = { open(): void; on(event: string, handler: () => void): void };
type RazorpayConstructor = new (options: Record<string, unknown>) => RazorpayInstance;
declare global { interface Window { Razorpay?: RazorpayConstructor } }

function installId(): string {
  const key = "fraudlens_demo_install_id";
  let value = localStorage.getItem(key);
  if (!value) { value = crypto.randomUUID(); localStorage.setItem(key, value); }
  return value;
}

function checkoutScript(): Promise<void> {
  if (window.Razorpay) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Razorpay Checkout could not load. Try again."));
    document.head.append(script);
  });
}

export function MerchantDemo(): React.JSX.Element {
  const [userId, setUserId] = useState("");
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<PaymentMethod>("upi");
  const [location, setLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [deviceId, setDeviceId] = useState("");
  const [check, setCheck] = useState<Check | null>(null);
  const [order, setOrder] = useState<Order | null>(null);
  const [checkoutResult, setCheckoutResult] = useState<CheckoutResult | null>(null);
  const [verification, setVerification] = useState<Verification | null>(null);
  const [busy, setBusy] = useState<"check" | "order" | "verify" | "location" | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const orderKey = useRef("");
  const locked = useRef(false);
  useEffect(() => { queueMicrotask(() => {
    try { setDeviceId(installId()); }
    catch { setDeviceId(crypto.randomUUID()); setError("Browser storage is unavailable. Using a temporary install ID for this visit."); }
  }); }, []);

  async function requestLocation() {
    if (!navigator.geolocation) { setError("Location is unavailable in this browser."); return; }
    setBusy("location"); setError("");
    navigator.geolocation.getCurrentPosition(position => {
      setLocation({ lat: Number(position.coords.latitude.toFixed(3)), lon: Number(position.coords.longitude.toFixed(3)) });
      setBusy(null);
    }, () => { setError("Location was not shared. You can continue without it."); setBusy(null); }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked.current || !deviceId) return;
    if (!userId.trim()) { setError("Enter a merchant user ID."); return; }
    const numericAmount = Number(amount);
    if (!Number.isFinite(numericAmount) || numericAmount <= 0 || numericAmount >= 10000000) { setError("Amount must be above ₹0 and below ₹10,000,000."); return; }
    locked.current = true; orderKey.current = ""; setBusy("check"); setError(""); setMessage(""); setCheck(null); setOrder(null); setVerification(null); setCheckoutResult(null);
    try {
      const platform = /android|iphone|ipad|ipod|mobile/i.test(navigator.userAgent) ? "mobile" : "web";
      await api("v1/signals", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ device_id: deviceId, user_id: userId.trim(), platform, user_agent: navigator.userAgent.slice(0, 512), screen: { width: screen.width, height: screen.height, pixel_ratio: devicePixelRatio }, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC", language: navigator.language || "en", ...location }) });
      const next = await api<Check>("v1/checks", { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ user_id: userId.trim(), device_id: deviceId, amount: numericAmount, currency: "INR", payment_method: method, ...location }) });
      setCheck(next);
    } catch (caught) { setError(errorText(caught)); } finally { locked.current = false; setBusy(null); }
  }

  async function verify(result: CheckoutResult) {
    setBusy("verify"); setError("");
    try {
      const value = await api<Verification>("v1/payments/verify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(result) });
      setVerification(value);
      setMessage(value.status === "captured" ? "Payment captured in Razorpay test mode." : value.status === "authorized" ? "Payment authorized. Waiting for a captured webhook before treating it as paid." : `Payment status: ${value.status}.`);
    } catch (caught) { setError(errorText(caught)); } finally { setBusy(null); }
  }

  async function startPayment() {
    if (!check || check.decision === "BLOCK" || locked.current) return;
    locked.current = true; setBusy("order"); setError(""); setMessage("");
    try {
      if (!orderKey.current) orderKey.current = crypto.randomUUID();
      const next = order || await api<Order>("v1/payments/order", { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": orderKey.current }, body: JSON.stringify({ check_id: check.check_id }) });
      if (!next.key_id.startsWith("rzp_test_")) throw new Error("Checkout is restricted to Razorpay test mode.");
      setOrder(next);
      await checkoutScript();
      if (!window.Razorpay) throw new Error("Razorpay Checkout is unavailable.");
      const instance = new window.Razorpay({ key: next.key_id, amount: next.amount, currency: next.currency, order_id: next.order_id, name: "FraudLens test checkout", description: "Test payment only", handler: (result: CheckoutResult) => { setCheckoutResult(result); void verify(result); }, modal: { ondismiss: () => setMessage("Checkout closed. You can reopen the same test order.") } });
      instance.on("payment.failed", () => setError("The test payment failed. You can reopen Checkout to try again."));
      instance.open();
    } catch (caught) { setError(errorText(caught)); } finally { locked.current = false; setBusy(null); }
  }

  return <div className="app-grid"><section className="surface" aria-labelledby="check-heading"><h2 id="check-heading" className="section-label">Transaction details</h2><form onSubmit={submit}><div className="form-grid"><div className="field"><label htmlFor="demo-user">Merchant user ID</label><input id="demo-user" value={userId} onChange={event => setUserId(event.target.value)} required minLength={1} maxLength={160} autoComplete="off" placeholder="Your test user ID" /><p className="field-hint">Use a test user ID from your merchant flow.</p></div><div className="field"><label htmlFor="demo-amount">Amount in INR</label><input id="demo-amount" value={amount} onChange={event => setAmount(event.target.value)} required type="number" min="0.01" max="9999999.99" step="0.01" inputMode="decimal" placeholder="250.00" /></div></div><div className="field"><label htmlFor="demo-method">Payment method</label><select id="demo-method" value={method} onChange={event => setMethod(event.target.value as PaymentMethod)}><option value="upi">UPI</option><option value="card">Card</option><option value="netbanking">Netbanking</option><option value="wallet">Wallet</option></select></div><div className="helper-row"><Fingerprint size={19} /><p>Install ID: <span className="mono">{deviceId || "Preparing device…"}</span>. Stored on this device, without invasive fingerprinting.</p></div><div className="form-actions"><button className="button button-outline button-small" type="button" onClick={requestLocation} disabled={busy !== null}><LocateFixed size={17} />{busy === "location" ? "Finding location…" : location ? "Update location" : "Add optional location"}</button>{location && <button className="text-link" type="button" onClick={() => setLocation(null)}>Remove location</button>}</div>{location && <p className="field-hint">Approximate location added: {location.lat.toFixed(3)}, {location.lon.toFixed(3)}</p>}<div className="form-actions"><button className="button button-orange" type="submit" disabled={busy !== null || !deviceId}>{busy === "check" ? "Checking signals…" : "Run fraud check"}<ArrowRight size={18} /></button></div></form>{error && <div className="notice error" role="alert">{error}{error.includes("session has expired") && <Link className="text-link" href="/access">Sign in again</Link>}</div>}{message && <div className="notice info" role="status">{message}</div>}</section><div className="helper-panel"><section className="surface" aria-live="polite">{busy === "check" && !check ? <><div className="skeleton large" /><p className="muted">Registering signals and checking the payment…</p></> : check ? <div className="result-card"><div className="result-head"><div><p className="mini-label">Payment decision</p><h2>{check.decision === "ALLOW" ? "Clear to continue" : check.decision === "REVIEW" ? "Needs a reviewer" : "Payment stopped"}</h2></div><DecisionBadge value={check.decision} /></div><div className="score-row"><div><strong>{check.final_score.toFixed(1)}</strong><span>Final score</span></div><div><strong>{check.ml_score.toFixed(1)}</strong><span>ML score</span></div><div><strong>{check.rule_score}</strong><span>Rule score</span></div></div><p className="mini-label">Triggered rules</p>{check.reasons.length ? <ul className="reason-list">{check.reasons.map((reason, index) => <li key={`${reason.rule}-${index}`}><strong>{reason.rule.replaceAll("_", " ")} · {reason.weight > 0 ? "+" : ""}{reason.weight}</strong><span>{reason.detail}</span></li>)}</ul> : <p>No rule reasons were returned for this check.</p>}<p className="mini-label">Model factors</p><p>Raw model-margin contributions. These are not probability percentages.</p>{check.ml_factors.length ? <ul className="factor-list">{check.ml_factors.map(factor => <li key={factor.feature}><span>{factor.feature.replaceAll("_", " ")}</span><strong>{factor.contribution > 0 ? "+" : ""}{factor.contribution.toFixed(3)}</strong></li>)}</ul> : <p>No model factors were returned.</p>}<div className="result-id"><div className="mono">Check ID: {check.check_id}</div><div className="mono">Model: {check.model_version} · Scoring: {check.latency_ms} ms</div></div></div> : <div className="empty-state"><ScanLine size={32} /><h3>Waiting for a check</h3><p>Run a payment through FraudLens to see the decision and its reasons here.</p></div>}</section>{check && <section className="surface payment-panel"><h2 className="section-label">Next step</h2>{check.decision === "BLOCK" ? <div className="notice error"><p>Payment is blocked. Checkout is unavailable for this check.</p></div> : <><p>{check.decision === "REVIEW" ? "A reviewer must approve this check before an order can be created. If approval is pending, the server will reject the request." : "This check can continue to Razorpay test Checkout."}</p><button className="button button-dark" type="button" disabled={busy !== null} onClick={startPayment}>{busy === "order" ? "Preparing test order…" : check.decision === "REVIEW" ? "Check approval and continue" : order ? "Reopen test Checkout" : "Continue to test Checkout"}<CreditCard size={17} /></button></>}{checkoutResult && <button type="button" className="button button-outline button-small" disabled={busy !== null} onClick={() => void verify(checkoutResult)}><RefreshCw size={16} />{busy === "verify" ? "Checking status…" : "Refresh capture status"}</button>}{verification && <div className={`notice ${verification.status === "captured" ? "success" : "info"}`} role="status">{verification.status === "captured" ? <ShieldCheck size={16} /> : <CircleHelp size={16} />} {verification.status.toUpperCase()}: {verification.status === "captured" ? "Paid in test mode" : "Do not mark paid until captured"}</div>}</section>}</div></div>;
}
