/**
 * Logo3D - the three-level M-AIDA logo in 3D (sign-in page, logo dialog).
 *
 * three.js is imported on demand (src/three/maidaLogo3d.ts), so the working
 * screens never download it. Without WebGL, or if the scene fails to load,
 * the flat wordmark is shown instead. Under prefers-reduced-motion the model
 * stands still (no turntable, no floating islands) but can still be turned by
 * dragging.
 */

import { useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n";
import { Logo } from "./Logo";
import figureHuong from "../assets/people/figure-huong.webp";

interface Logo3DProps {
  /** Wheel zoom (dialog) or not (sign-in page, where the wheel scrolls the page). */
  zoom?: boolean;
  framing?: number;
  className?: string;
}

type State = "loading" | "ready" | "fallback";

export default function Logo3D({ zoom = false, framing, className = "" }: Logo3DProps) {
  const { t } = useI18n();
  const host = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<State>("loading");

  useEffect(() => {
    let cancelled = false;
    let dispose: (() => void) | null = null;
    const el = host.current;
    if (!el) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    const bg = getComputedStyle(el).getPropertyValue("--logo3d-bg").trim() || "#efe8da";
    import("../three/maidaLogo3d")
      .then(async (mod) => {
        if (cancelled) return;
        if (!mod.webglAvailable()) {
          setState("fallback");
          return;
        }
        const handle = await mod.mountLogo3D(el, {
          background: bg,
          huongUrl: figureHuong,
          animate: !reduce,
          zoom,
          framing,
        });
        if (cancelled) handle.dispose();
        else {
          dispose = handle.dispose;
          setState("ready");
        }
      })
      .catch((err: unknown) => {
        console.warn("M-AIDA 3D logo unavailable:", err);
        if (!cancelled) setState("fallback");
      });
    return () => {
      cancelled = true;
      dispose?.();
    };
  }, [zoom, framing]);

  return (
    <div
      className={`logo3d logo3d-${state} ${className}`}
      role="img"
      aria-label={t("logo3d_alt")}
      data-testid="logo3d"
      data-state={state}
    >
      <div ref={host} className="logo3d-canvas" />
      {state !== "ready" && (
        <div className="logo3d-flat" aria-hidden="true">
          <Logo />
        </div>
      )}
    </div>
  );
}
