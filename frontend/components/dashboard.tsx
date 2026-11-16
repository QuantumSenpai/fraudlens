"use client";

import { gsap } from "gsap";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, ArrowLeft, ArrowRight, CircleHelp, ClipboardCheck, RefreshCw, ShieldCheck, X } from "lucide-react";
import { api, errorText } from "@/lib/client-api";
import { DecisionBadge } from "@/components/decision-badge";
import type { Evaluation, FeedEvent, Review, Stats } from "@/lib/types";

type Tab = "overview" | "reviews" | "evaluation";
type Filter = "pending" | "reviewed" | "all";
type Resolution = "approve" | "reject";

export function Dashboard(): React.JSX.Element {
  const content = useRef<HTMLDivElement>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<Stats | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [filter, setFilter] = useState<Filter>("pending");
  const [offset, setOffset] = useState(0);
  const [feed, setFeed] = useState<FeedEvent[]>([]);
  const [connection, setConnection] = useState<"connecting" | "connected" | "reconnecting">("connecting");
  const [feedVersion, setFeedVersion] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [dialogError, setDialogError] = useState("");
  const [active, setActive] = useState<{ review: Review; outcome: Resolution } | null>(null);
  const [reviewer, setReviewer] = useState("");
  const [note, setNote] = useState("");
  const [resolving, setResolving] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    const context = gsap.context(() => { gsap.fromTo(content.current, { opacity: .65 }, { opacity: 1, duration: .18, clearProps: "opacity" }); });
    return () => context.revert();
  }, [tab]);

  const loadOverview = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [statsData, evaluationData] = await Promise.all([api<Stats>("v1/admin/stats"), api<Evaluation>("v1/admin/evaluation")]);
      setStats(statsData); setEvaluation(evaluationData);
    } catch (caught) { setError(errorText(caught)); } finally { setLoading(false); }
  }, []);
  const loadReviews = useCallback(async () => {
    setLoading(true); setError("");
    try { setReviews(await api<Review[]>(`v1/admin/reviews?status=${filter}&limit=10&offset=${offset}`)); }
    catch (caught) { setError(errorText(caught)); } finally { setLoading(false); }
  }, [filter, offset]);

  useEffect(() => { queueMicrotask(() => { if (tab === "reviews") void loadReviews(); else void loadOverview(); }); }, [tab, loadOverview, loadReviews]);
  useEffect(() => {
    const source = new EventSource("/api/feed");
    source.onopen = () => setConnection("connected");
    source.onerror = () => setConnection("reconnecting");
    source.addEventListener("check", event => {
      try { const value = JSON.parse((event as MessageEvent).data) as FeedEvent; setFeed(current => [value, ...current].slice(0, 12)); void api<Stats>("v1/admin/stats").then(setStats).catch(() => {}); }
      catch { setConnection("reconnecting"); }
    });
    return () => source.close();
  }, [feedVersion]);

  useEffect(() => {
    if (!active) return;
    const node = dialogRef.current;
    node?.querySelector<HTMLInputElement>("input")?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !resolving) { setActive(null); previousFocus.current?.focus(); }
      if (event.key === "Tab" && node) {
        const targets = Array.from(node.querySelectorAll<HTMLElement>("button:not(:disabled), input, textarea"));
        const first = targets[0], last = targets[targets.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener("keydown", keydown);
    return () => document.removeEventListener("keydown", keydown);
  }, [active, resolving]);

  function openReview(review: Review, outcome: Resolution) {
    previousFocus.current = document.activeElement as HTMLElement;
    setReviewer(""); setNote(""); setActive({ review, outcome }); setError(""); setDialogError("");
  }
  function closeReview() { setActive(null); previousFocus.current?.focus(); }
  async function resolve() {
    if (!active || resolving || !reviewer.trim()) return;
    setResolving(true); setDialogError(""); setSuccess("");
    try {
      await api(`v1/admin/reviews/${active.review.id}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ outcome: active.outcome, reviewer: reviewer.trim(), note: note.trim() || null }) });
      setSuccess(`Review ${active.outcome === "approve" ? "approved" : "rejected"} and feedback label saved.`);
      closeReview();
      await Promise.all([loadReviews(), loadOverview()]);
    } catch (caught) { setDialogError(errorText(caught)); } finally { setResolving(false); }
  }
  const refresh = () => { if (tab === "reviews") void loadReviews(); else void loadOverview(); };
  const percent = (value: number | null | undefined) => value == null ? "Unavailable" : `${(value * 100).toFixed(1)}%`;

  return <><div className="app-heading"><div><p className="eyebrow">REVIEWER WORKSPACE</p><h1>Decision overview.</h1><p>Current checks, review cases, and labelled feedback from FraudLens.</p></div><button type="button" className="button button-outline button-small" onClick={refresh} disabled={loading}><RefreshCw size={16} />{loading ? "Refreshing…" : "Refresh data"}</button></div><div className="dashboard-tabs" role="group" aria-label="Dashboard views">{(["overview", "reviews", "evaluation"] as Tab[]).map(value => <button key={value} type="button" aria-pressed={tab === value} className="tab" onClick={() => setTab(value)}>{value === "overview" ? "Overview" : value === "reviews" ? "Reviews" : "Evaluation"}</button>)}</div><div ref={content} className="dashboard-content">{error && <div className="notice error" role="alert">{error} {error.includes("session has expired") && <Link className="text-link" href="/access?role=admin">Sign in again</Link>} <button type="button" className="text-link" onClick={refresh}>Retry</button></div>}{success && <div className="notice success" role="status">{success}</div>}{tab === "overview" && <><div className="stat-grid">{[{ label: "Total checks", value: stats?.total_checks }, { label: "Allow", value: stats?.decision_split?.ALLOW }, { label: "Review", value: stats?.decision_split?.REVIEW }, { label: "Block", value: stats?.decision_split?.BLOCK }].map(item => <div className="stat-card" key={item.label}><span>{item.label}</span>{loading && !stats ? <div className="skeleton" /> : <strong>{item.value ?? "N/A"}</strong>}</div>)}</div><div className="dashboard-columns"><section className="surface"><div className="panel-heading"><h2>Last 24 hours</h2><Activity size={18} /></div>{loading && !stats ? <div className="skeleton large" aria-label="Loading hourly activity" /> : stats?.last_24h_hourly_counts?.some(item => item.count > 0) ? <><div className="activity-chart" role="img" aria-label={`Hourly activity: ${stats.last_24h_hourly_counts.map(item => item.count).join(", ")} checks`} >{stats.last_24h_hourly_counts.map((item, index) => <div key={`${item.hour}-${index}`} title={`${item.hour}: ${item.count} checks`} style={{ height: `${Math.max(2, item.count / Math.max(...stats.last_24h_hourly_counts.map(row => row.count), 1) * 100)}%` }} />)}</div><div className="chart-labels"><span>24 hours ago</span><span>Now</span></div></> : <div className="empty-state"><Activity size={28} /><h3>No hourly activity yet</h3><p>New checks will appear here after the API receives them.</p></div>}</section><section className="surface"><div className="panel-heading"><h2>Decision health</h2><ShieldCheck size={18} /></div><div className="stat-grid"><div className="stat-card"><span>Flagged rate</span><strong>{stats ? `${stats.flagged_rate_percent.toFixed(1)}%` : "N/A"}</strong></div><div className="stat-card"><span>Avg scoring</span><strong>{stats?.average_latency_ms == null ? "N/A" : `${stats.average_latency_ms} ms`}</strong></div><div className="stat-card"><span>P95 scoring</span><strong>{stats?.p95_scoring_latency_ms == null ? "N/A" : `${stats.p95_scoring_latency_ms} ms`}</strong></div><div className="stat-card"><span>Labels</span><strong>{evaluation?.labels_total ?? "N/A"}</strong></div></div><p className="field-hint">Scoring latency excludes persistence. Decision thresholds and rules are demo heuristics.</p></section></div><div className="dashboard-columns" style={{ marginTop: 24 }}><section className="surface"><div className="panel-heading"><h2>Live checks</h2><span className={`connection ${connection}`}><i />{connection === "connected" ? "Connected" : connection === "connecting" ? "Connecting" : "Reconnecting"}</span></div><button type="button" className="text-link" onClick={() => { setConnection("connecting"); setFeedVersion(value => value + 1); }}>Reconnect feed <RefreshCw size={15} /></button>{feed.length ? <ul className="feed-list">{feed.map(item => <li key={item.check_id}><span className="mono" title={item.check_id}>{item.check_id}</span><DecisionBadge value={item.decision} /><strong>₹{Number(item.amount).toLocaleString("en-IN")}</strong></li>)}</ul> : <div className="empty-state"><Activity size={28} /><h3>No live events yet</h3><p>Checks created while this page is connected will appear here. Events are not replayed after reconnecting.</p></div>}</section><section className="surface"><div className="panel-heading"><h2>Top triggered rules</h2><CircleHelp size={18} /></div>{loading && !stats ? <div className="skeleton large" aria-label="Loading rule counts" /> : stats?.top_triggered_rules?.length ? <ol className="rule-rank">{stats.top_triggered_rules.map(item => <li key={item.rule}><span>{item.rule.replaceAll("_", " ")}</span><strong>{item.count}</strong></li>)}</ol> : <div className="empty-state"><h3>No rule triggers yet</h3><p>Rule counts appear when checks trigger them.</p></div>}</section></div></>}{tab === "reviews" && <section><div className="toolbar"><div className="dashboard-tabs" role="group" aria-label="Review status">{(["pending", "reviewed", "all"] as Filter[]).map(value => <button className="tab" type="button" key={value} aria-pressed={filter === value} onClick={() => { setFilter(value); setOffset(0); }}>{value[0].toUpperCase() + value.slice(1)}</button>)}</div><span className="muted">Showing {reviews.length ? offset + 1 : 0}–{offset + reviews.length}</span></div>{loading && !reviews.length ? <div className="surface"><div className="skeleton large" /></div> : reviews.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>Check</th><th>Reasons</th><th>Amount</th><th>Score</th><th>Status</th><th>Action</th></tr></thead><tbody>{reviews.map(review => <tr key={review.id}><td><div className="mono">{review.id}</div><span className="muted">{review.user_id}</span></td><td>{review.reasons?.length ? review.reasons.map(reason => <div key={reason.rule}><strong>{reason.rule.replaceAll("_", " ")}</strong><div>{reason.detail}</div></div>) : "No rule reasons"}</td><td>₹{Number(review.amount).toLocaleString("en-IN")}</td><td>{Number(review.final_score).toFixed(1)}</td><td>{review.review ? review.review.outcome : "Pending"}</td><td>{review.review ? <span className="muted">Resolved</span> : <div className="row-actions"><button type="button" className="button button-dark button-small" onClick={() => openReview(review, "approve")}>Approve</button><button type="button" className="button button-outline button-small" onClick={() => openReview(review, "reject")}>Reject</button></div>}</td></tr>)}</tbody></table></div> : <div className="surface empty-state"><ClipboardCheck size={30} /><h3>No {filter} reviews</h3><p>Cases appear when a check returns REVIEW.</p></div>}<div className="pagination"><button type="button" className="button button-outline button-small" disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - 10))}><ArrowLeft size={16} />Previous</button><span>Page {Math.floor(offset / 10) + 1}</span><button type="button" className="button button-outline button-small" disabled={reviews.length < 10 || loading} onClick={() => setOffset(offset + 10)}>Next<ArrowRight size={16} /></button></div></section>}{tab === "evaluation" && <section className="surface"><div className="panel-heading"><h2>Labelled-case evaluation</h2><ClipboardCheck size={19} /></div><p className="muted">REVIEW and BLOCK count as flagged. ALLOW counts as unflagged. These numbers reflect only labelled checks, not real-world accuracy.</p>{loading && !evaluation ? <div className="skeleton large" aria-label="Loading evaluation" /> : !evaluation || evaluation.labels_total === 0 ? <div className="empty-state"><CircleHelp size={30} /><h3>Not enough labelled cases</h3><p>Resolve reviews or add representative feedback before interpreting precision, recall, or false-positive rate.</p></div> : <><div className="stat-grid"><div className="stat-card"><span>Precision</span><strong>{percent(evaluation.precision)}</strong></div><div className="stat-card"><span>Recall</span><strong>{percent(evaluation.recall)}</strong></div><div className="stat-card"><span>False-positive rate</span><strong>{percent(evaluation.false_positive_rate)}</strong></div><div className="stat-card"><span>Labels</span><strong>{evaluation.labels_total}</strong></div></div><p className="field-hint">Unavailable means the metric’s denominator is zero. Reviewer feedback can be biased and should not be treated as production accuracy.</p></>}</section>}{active && <div className="dialog-backdrop" onMouseDown={event => { if (event.target === event.currentTarget && !resolving) closeReview(); }}><div ref={dialogRef} className="dialog" role="dialog" aria-modal="true" aria-labelledby="review-dialog-title"><div className="panel-heading"><h2 id="review-dialog-title">{active.outcome === "approve" ? "Approve" : "Reject"} this review?</h2><button className="icon-button" type="button" aria-label="Close review dialog" disabled={resolving} onClick={closeReview}><X size={18} /></button></div><p className="muted">Check <span className="mono">{active.review.id}</span>. This saves a {active.outcome === "approve" ? "legit" : "fraud"} feedback label.</p><div className="field"><label htmlFor="reviewer-name">Reviewer name</label><input id="reviewer-name" maxLength={160} required value={reviewer} onChange={event => setReviewer(event.target.value)} /></div><div className="field"><label htmlFor="review-note">Note</label><textarea id="review-note" maxLength={2000} value={note} onChange={event => setNote(event.target.value)} placeholder="Explain the decision" /></div>{dialogError && <div className="notice error" role="alert">{dialogError}</div>}<div className="dialog-actions"><button type="button" className="button button-outline" disabled={resolving} onClick={closeReview}>Cancel</button><button type="button" className="button button-orange" disabled={resolving || !reviewer.trim()} onClick={() => void resolve()}>{resolving ? "Saving…" : `Confirm ${active.outcome}`}</button></div></div></div>}</div></>;
}
