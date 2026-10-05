/**
 * CosmosBackdrop - the night-sky backdrop of the "Cosmos" look (design package
 * of 04/10/2026): a fixed canvas behind the app with a few hundred stars, two
 * faint nebula glows and one orbit with a small planet.
 *
 * Plain 2D canvas, no library and nothing fetched. It draws one still frame
 * when the viewer prefers reduced motion, pauses while the tab is hidden, and
 * is only mounted while the Cosmos look is on.
 */

import React, { useEffect, useRef } from "react";

interface Star {
  x: number;
  y: number;
  size: number;
  alpha: number;
  speed: number;
  phase: number;
}

/** Small deterministic RNG so the sky does not reshuffle on every resize. */
function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export default function CosmosBackdrop() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    let w = 0;
    let h = 0;
    let raf = 0;
    let stars: Star[] = [];

    const resize = () => {
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const rand = rng(20261004);
      const count = Math.min(420, Math.round((w * h) / 5200));
      stars = Array.from({ length: count }, () => ({
        x: rand() * w,
        y: rand() * h,
        size: rand() < 0.08 ? 1.8 : rand() < 0.4 ? 1.2 : 0.8,
        alpha: 0.35 + rand() * 0.6,
        speed: 0.4 + rand() * 1.4,
        phase: rand() * Math.PI * 2,
      }));
    };

    const glow = (cx: number, cy: number, radius: number, rgb: string, alpha: number) => {
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
      g.addColorStop(0, `rgba(${rgb},${alpha})`);
      g.addColorStop(1, `rgba(${rgb},0)`);
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, w, h);
    };

    const draw = (time: number) => {
      ctx.clearRect(0, 0, w, h);
      const span = Math.max(w, h);
      glow(w * 0.74, h * 0.26, span * 0.55, "84,182,198", 0.11);
      glow(w * 0.16, h * 0.86, span * 0.45, "240,185,104", 0.07);

      // One orbit, tilted, with a small planet riding it.
      const rx = Math.min(w, h) * 0.42;
      const ry = rx * 0.3;
      ctx.save();
      ctx.translate(w * 0.72, h * 0.3);
      ctx.rotate(-0.32);
      ctx.strokeStyle = "rgba(124,201,214,0.16)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);
      ctx.stroke();
      const angle = reduce ? 0.9 : time * 0.00004;
      ctx.fillStyle = "rgba(240,185,104,0.9)";
      ctx.beginPath();
      ctx.arc(Math.cos(angle) * rx, Math.sin(angle) * ry, 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "rgba(255,210,122,0.85)";
      ctx.beginPath();
      ctx.arc(0, 0, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      for (const s of stars) {
        const twinkle = reduce ? 1 : 0.65 + 0.35 * Math.sin(time * 0.001 * s.speed + s.phase);
        ctx.fillStyle = `rgba(232,237,243,${(s.alpha * twinkle).toFixed(3)})`;
        ctx.fillRect(s.x, s.y, s.size, s.size);
      }
      if (!reduce && !document.hidden) raf = window.requestAnimationFrame(draw);
    };

    const onResize = () => {
      resize();
      if (reduce) draw(0);
    };
    const onVisibility = () => {
      if (!reduce && !document.hidden) {
        window.cancelAnimationFrame(raf);
        raf = window.requestAnimationFrame(draw);
      }
    };

    resize();
    draw(0);
    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return <canvas ref={ref} className="cosmos-backdrop" aria-hidden="true" data-testid="cosmos-backdrop" />;
}
