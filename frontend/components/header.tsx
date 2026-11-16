"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { gsap } from "gsap";
import { ArrowUpRight, Minus, Plus, X } from "lucide-react";
import { Brand } from "@/components/brand";

const destinations = [
  { href: "/how-it-works", title: "Product flow", detail: "From device signals to a payment decision" },
  { href: "/demo", title: "Merchant demo", detail: "Run a check before test Checkout" },
  { href: "/admin", title: "Reviewer dashboard", detail: "Resolve cases and inspect their reasons" },
  { href: "/privacy", title: "Data use", detail: "Know what the demo collects and stores" },
];

export function Header(): React.JSX.Element {
  const pathname = usePathname();
  const [expanded, setExpanded] = useState(false);
  const [present, setPresent] = useState(false);
  const [mobile, setMobile] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const [panelNode, setPanelNode] = useState<HTMLDivElement | null>(null);
  const attachPanel = useCallback((node: HTMLDivElement | null) => { panel.current = node; setPanelNode(node); }, []);
  const backdrop = useRef<HTMLDivElement>(null);
  const links = useRef<HTMLElement>(null);
  const highlight = useRef<HTMLDivElement>(null);
  const ink = useRef<HTMLDivElement>(null);
  const timeline = useRef<gsap.core.Timeline | null>(null);
  const highlightTween = useRef<gsap.core.Tween | null>(null);
  const inkTween = useRef<gsap.core.Tween | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const openedBy = useRef<"pointer" | "click" | "keyboard">("click");
  const returningFocus = useRef(true);
  const hoverArmed = useRef(true);

  function cancelClose() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
  }
  function changeOpen(value: boolean) {
    cancelClose();
    returningFocus.current = true;
    if (!value) hoverArmed.current = false;
    if (value) setPresent(true);
    setExpanded(value);
  }
  function scheduleClose() {
    if (openedBy.current === "pointer") closeTimer.current = setTimeout(() => changeOpen(false), 180);
  }
  function moveHighlight(item: HTMLAnchorElement | null) {
    highlightTween.current?.kill();
    inkTween.current?.kill();
    if (!highlight.current || !ink.current) return;
    const duration = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : .32;
    if (!item || !links.current) {
      highlightTween.current = gsap.to([highlight.current, ink.current], { opacity: 0, duration: .12 });
      return;
    }
    const top = item.offsetTop, bottom = links.current.offsetHeight - top - item.offsetHeight;
    highlightTween.current = gsap.to(highlight.current, { y: top, height: item.offsetHeight, opacity: 1, duration, ease: "power3.out" });
    inkTween.current = gsap.to(ink.current, { clipPath: `inset(${top}px 0px ${bottom}px 0px)`, opacity: 1, duration, ease: "power3.out" });
  }

  useLayoutEffect(() => {
    if (!present || !panelNode) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const context = gsap.context(() => {
      timeline.current = gsap.timeline({ paused: true, onReverseComplete: () => setPresent(false) })
        .fromTo(backdrop.current, { opacity: 0 }, { opacity: 1, duration: reduced ? 0 : .3 }, 0)
        .fromTo(panel.current, { clipPath: "inset(0 0 100% 0)", y: -12, opacity: 0 }, { clipPath: "inset(0 0 0% 0)", y: 0, opacity: 1, duration: reduced ? 0 : .4, ease: "power3.inOut" }, 0)
        .fromTo(".explore-intro, .explore-links > a", { opacity: 0 }, { opacity: 1, duration: reduced ? 0 : .24, stagger: reduced ? 0 : .025, ease: "power3.out" }, reduced ? 0 : .06);
    }, panel);
    return () => { context.revert(); timeline.current = null; highlightTween.current?.kill(); inkTween.current?.kill(); };
  }, [present, panelNode]);

  useLayoutEffect(() => {
    if (!present) return;
    if (expanded) timeline.current?.play();
    else if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) queueMicrotask(() => setPresent(false));
    else timeline.current?.reverse();
  }, [expanded, present, panelNode]);

  useEffect(() => {
    queueMicrotask(() => { returningFocus.current = false; setExpanded(false); setPresent(false); });
  }, [pathname]);
  useEffect(() => {
    const resize = () => {
      cancelClose();
      setMobile(window.matchMedia("(max-width: 768px)").matches);
      setExpanded(false); setPresent(false);
    };
    queueMicrotask(resize);
    const rearmHover = (event: PointerEvent) => {
      const rect = trigger.current?.getBoundingClientRect();
      if (rect && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) hoverArmed.current = true;
    };
    window.addEventListener("pointermove", rearmHover);
    window.addEventListener("resize", resize);
    return () => { window.removeEventListener("resize", resize); window.removeEventListener("pointermove", rearmHover); cancelClose(); };
  }, []);

  const rows = destinations.map((item, index) => <div className="explore-row" key={item.href}><span className="explore-number">0{index + 1}</span><div><strong>{item.title}</strong><span>{item.detail}</span></div><ArrowUpRight size={23} aria-hidden="true" /></div>);

  return <header className="site-header" onPointerEnter={cancelClose} onPointerLeave={scheduleClose}>
    <div className="header-inner">
      <Brand />
      <nav className="header-navigation" aria-label="Main navigation"><Link className="header-guide" href="/how-it-works">How it works</Link>
        <Dialog.Root modal={mobile} open={expanded} onOpenChange={changeOpen}>
          <Dialog.Trigger asChild><button ref={trigger} className="explore-trigger" aria-controls="explore-panel" aria-expanded={expanded}
            onPointerEnter={event => { if (hoverArmed.current && event.pointerType === "mouse" && window.matchMedia("(hover: hover)").matches && !expanded) { openedBy.current = "pointer"; changeOpen(true); } }}
            onPointerDown={() => { openedBy.current = "click"; }}
            onKeyDown={() => { openedBy.current = "keyboard"; }}>
            Explore {expanded ? <Minus size={17} /> : <Plus size={17} />}
          </button></Dialog.Trigger>
          {present && <Dialog.Portal forceMount>
            <div ref={backdrop} className="explore-backdrop" aria-hidden="true" onPointerDown={() => changeOpen(false)} />
            <Dialog.Content forceMount ref={attachPanel} id="explore-panel" className="explore-panel" inert={!expanded}
              onPointerEnter={cancelClose} onPointerLeave={scheduleClose}
              onKeyDownCapture={() => { openedBy.current = "keyboard"; }}
              onOpenAutoFocus={event => { event.preventDefault(); if (openedBy.current !== "pointer") panel.current?.querySelector<HTMLAnchorElement>("a")?.focus({ preventScroll: true }); }}
              onCloseAutoFocus={event => { event.preventDefault(); if (returningFocus.current) trigger.current?.focus(); }}
              onInteractOutside={event => { if (trigger.current?.contains(event.target as Node)) event.preventDefault(); }}>
              <div className="explore-inner">
                <div className="explore-intro"><p className="eyebrow">EXPLORE FRAUDLENS</p><Dialog.Title>Before payment.<br />After the signals.</Dialog.Title><Dialog.Description>Understand the flow, run a test check, or review a decision.</Dialog.Description><p className="explore-limitation">Razorpay test mode only.<br />No real money moves in this demo.</p></div>
                <nav ref={links} className="explore-links" aria-label="Explore destinations" onPointerLeave={() => moveHighlight(links.current?.querySelector("a:focus-visible") || null)} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) moveHighlight(null); }}>
                  <div ref={highlight} className="explore-highlight" aria-hidden="true" />
                  {destinations.map((item, index) => <Link key={item.href} href={item.href} onClick={() => { returningFocus.current = false; changeOpen(false); returningFocus.current = false; }} onPointerEnter={event => { if (event.pointerType === "mouse") moveHighlight(event.currentTarget); }} onFocus={event => { if (event.currentTarget.matches(":focus-visible")) moveHighlight(event.currentTarget); }}>{rows[index]}</Link>)}
                  <div ref={ink} className="explore-ink" aria-hidden="true">{rows}</div>
                </nav>
                <Dialog.Close className="icon-button explore-close" aria-label="Close navigation"><X size={20} /></Dialog.Close>
              </div>
            </Dialog.Content>
          </Dialog.Portal>}
        </Dialog.Root>
      </nav>
      <Link className="nav-cta" href="/demo">Open demo <ArrowUpRight size={17} /></Link>
    </div>
  </header>;
}
