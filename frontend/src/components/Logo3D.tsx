/**
 * Logo3D - the three-level M-AIDA logo in 3D (sign-in page, logo dialog).
 *
 * three.js is imported on demand (src/three/maidaLogo3d.ts), so the working
 * screens never download it. Without WebGL, or if the scene fails to load,
 * the 2D version of the same logo (map of Vietnam + M-AIDA, ink letters on
 * paper, star-white letters in the Cosmos look) is shown instead, and while
 * the scene loads. Under prefers-reduced-motion the model
 * stands still (no turntable, no floating islands) but can still be turned by
 * dragging.
 */

import { useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n";
import figureHuong from "../assets/people/figure-huong.webp";
import lockupPaper from "../assets/brand/maida-vn-lockup-horizontal-paper.svg";
import lockupCosmos from "../assets/brand/maida-vn-lockup-horizontal-cosmos.svg";

interface Logo3DProps {
  /** Wheel zoom (dialog) or not (sign-in page, where the wheel scrolls the page). */
  zoom?: boolean;
  framing?: number;
  className?: string;
}

type State = "loading" | "ready" | "fallback";
type Palette = "paper" | "cosmos";

const currentPalette = (): Palette => (document.documentElement.dataset.look === "cosmos" ? "cosmos" : "paper");

/** The look on <html data-look>, followed live so the model is rebuilt when it changes. */
function usePalette(): Palette {
  const [palette, setPalette] = useState<Palette>(currentPalette);
  useEffect(() => {
    const mo = new MutationObserver(() => setPalette(currentPalette()));
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-look"] });
    return () => mo.disconnect();
  }, []);
  return palette;
}

export default function Logo3D({ zoom = false, framing, className = "" }: Logo3DProps) {
  const { t } = useI18n();
  const host = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<State>("loading");
  const palette = usePalette();

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
          palette,
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
  }, [zoom, framing, palette]);

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
          <img className="logo2d logo2d-paper" src={lockupPaper} alt="" />
          <img className="logo2d logo2d-cosmos" src={lockupCosmos} alt="" />
        </div>
      )}
    </div>
  );
}
