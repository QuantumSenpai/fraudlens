"use client";
import { useEffect } from "react";
import { gsap } from "gsap";

export function PageMotion() {
  useEffect(() => {
    const media = gsap.matchMedia();
    media.add("(prefers-reduced-motion: no-preference)", context => {
      gsap.timeline()
        .from(".hero-title .eyebrow", { opacity: .2, duration: .3 }, 0)
        .from(".hero-title h1", { y: 16, opacity: .4, duration: .45, ease: "power3.out", clearProps: "all" }, 0)
        .from(".hero-copy", { x: 16, opacity: .4, duration: .4, ease: "power3.out", clearProps: "all" }, .08);
      const observer = new IntersectionObserver(entries => entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        context.add(() => {
          if (entry.target.matches(".flow-grid")) {
            gsap.from(entry.target.children, { x: 14, opacity: .5, stagger: .06, duration: .4, ease: "power3.out", clearProps: "all" });
          } else {
            gsap.from(entry.target, { y: 12, duration: .4, ease: "power3.out", clearProps: "all" });
          }
        });
        observer.unobserve(entry.target);
      }), { threshold: .2 });
      document.querySelectorAll(".flow-grid,.sample-panel,.flow-strip").forEach(node => observer.observe(node));
      return () => observer.disconnect();
    });
    return () => media.revert();
  }, []);
  return null;
}
