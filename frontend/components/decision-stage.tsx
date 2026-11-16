"use client";

import Link from "next/link";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { ArrowRight, ArrowUpRight, Check, Fingerprint, Pause, ScanLine, ShieldX } from "lucide-react";

const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2, maximumFractionDigits: 2 });

const scenarios = [
  { name: "ALLOW", amount: 1250, icon: Check, heading: "Create a test order.", reason: "Established device, usual spending, and no payment burst.", action: "Eligible for test Checkout", destination: "/demo", link: "Run a test check", note: "An allowed check can create a Razorpay test order." },
  { name: "REVIEW", amount: 45000, icon: Pause, heading: "Wait for a reviewer.", reason: "New device and payment burst, alongside model risk.", action: "Waiting for reviewer approval", destination: "/admin", link: "Explore the reviewer workspace", note: "A reviewer must approve the check before an order can be created." },
  { name: "BLOCK", amount: 250000, icon: ShieldX, heading: "Stop before Checkout.", reason: "High amount, impossible travel, and elevated model risk.", action: "Checkout stays closed", destination: "/how-it-works", link: "Understand the decision flow", note: "Blocked checks cannot create a payment order." },
];

export function DecisionStage(): React.JSX.Element {
  const [selected, setSelected] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const amountValue = useRef<HTMLSpanElement>(null);
  const outcome = scenarios[selected];
  const [whole, fraction] = inr.format(outcome.amount).split(".");

  useLayoutEffect(() => {
    const value = amountValue.current;
    const container = value?.parentElement;
    if (!value || !container) return;
    const fit = () => { value.style.scale = String(Math.min(1, container.clientWidth / value.scrollWidth)); };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(container);
    observer.observe(value);
    const media = gsap.matchMedia();
    media.add("(prefers-reduced-motion: no-preference)", () => {
      gsap.fromTo(value, { y: 3, opacity: .6 }, { y: 0, opacity: 1, duration: .2, ease: "power3.out" });
    });
    return () => { observer.disconnect(); media.revert(); value.style.scale = ""; };
  }, [outcome.amount]);
  useEffect(() => {
    const media = gsap.matchMedia();
    media.add("(prefers-reduced-motion: no-preference)", () => {
      const tl = gsap.timeline();
      tl.fromTo(".signal-path", { scaleX: 0 }, { scaleX: selected === 2 ? .5 : 1, duration: .42, ease: "power2.inOut" }, 0)
        .fromTo(".stage-stamp", { y: 10, opacity: .35 }, { y: 0, opacity: 1, duration: .32, ease: "power3.out" }, .12)
        .fromTo(".stage-consequence > :not(.sr-only)", { x: 10, opacity: .4 }, { x: 0, opacity: 1, duration: .3, stagger: .035, ease: "power3.out" }, .2);
    }, root);
    return () => media.revert();
  }, [selected]);

  return <div className="decision-stage" ref={root} data-decision={outcome.name}>
    <div className="stage-top"><p><span className="stage-indicator" /> INTERACTIVE WALKTHROUGH</p><span>ILLUSTRATIVE TRANSACTION · NOT LIVE DATA</span></div>
    <div className="stage-heading"><h2>Three checks. Three possible paths.</h2><div className="decision-options" role="group" aria-label="Explore illustrative decisions">{scenarios.map((item, index) => <button key={item.name} type="button" aria-pressed={selected === index} onClick={() => setSelected(index)}><item.icon size={15} aria-hidden="true" />{item.name}</button>)}</div></div>
    <div className="stage-scene">
      <div className="stage-origin"><span className="stage-label">01 / PAYMENT INTENT</span><div className="stage-ticket"><div><span>TEST TRANSACTION</span><ArrowUpRight size={17} /></div><strong className="stage-amount"><span ref={amountValue} className="amount-value">{whole}<span className="amount-decimal">.{fraction}</span></span></strong><footer><span>INR</span><span>UPI</span><span>DEMO USER</span></footer></div><p><Fingerprint size={15} /> Device context registered</p></div>
      <div className="stage-evaluation"><span className="stage-label">02 / FRAUD CHECK</span><div className="signal-track" aria-hidden="true"><div className="signal-path" /><ScanLine size={30} strokeWidth={1.3} /></div><strong>Rules + model</strong><span>Signals become a decision</span></div>
      <div className="stage-consequence" aria-live="polite" aria-atomic="true"><span className="sr-only">{inr.format(outcome.amount)} illustrative transaction. </span><span className="stage-label">03 / NEXT STEP</span><div className="stage-stamp"><outcome.icon size={31} strokeWidth={1.5} aria-hidden="true" /><strong>{outcome.name}</strong></div><h3>{outcome.heading}</h3><p>{outcome.note}</p><span className="stage-action"><outcome.icon size={15} aria-hidden="true" />{outcome.action}</span></div>
    </div>
    <div className="stage-bottom"><p><span>EXAMPLE REASON</span>{outcome.reason}</p><Link href={outcome.destination}>{outcome.link}<ArrowRight size={17} /></Link></div>
  </div>;
}
