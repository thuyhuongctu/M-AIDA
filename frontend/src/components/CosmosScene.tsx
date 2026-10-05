/**
 * CosmosScene - the 3D background of the Cosmos look (design package
 * "M-AIDA Cloud Cosmos", 04/10/2026). See cosmos/scene.ts for the scene and
 * cosmos/stations.ts for where each screen sits on the flight path.
 *
 * three.js and the map are loaded with import() when this component mounts,
 * so the paper look never downloads them. Without WebGL (or if the scene
 * fails to start) the 2D night sky of CosmosBackdrop is shown instead.
 */

import React, { useEffect, useRef, useState } from "react";
import CosmosBackdrop from "./CosmosBackdrop";
import authorHuong from "../assets/people/author-huong.webp";
import authorTu from "../assets/people/author-tu.webp";
import { stationPoint, type Station } from "../cosmos/stations";
import type { CosmosEffect, CosmosPalette, CosmosScene as SceneInstance } from "../cosmos/scene";

interface Props {
  station: Station;
  palette: CosmosPalette;
  lang: "en" | "vi";
  effects: CosmosEffect[];
  /** Working screens: lower frame rate once the camera has arrived. */
  calm: boolean;
}

type State = "loading" | "ready" | "fallback";

function useReducedMotion(): boolean {
  const query = "(prefers-reduced-motion: reduce)";
  const [reduce, setReduce] = useState(() => window.matchMedia?.(query).matches ?? false);
  useEffect(() => {
    const mq = window.matchMedia?.(query);
    if (!mq) return;
    const on = () => setReduce(mq.matches);
    mq.addEventListener?.("change", on);
    return () => mq.removeEventListener?.("change", on);
  }, []);
  return reduce;
}

/** Fraction of the page scrolled, 0..1. */
function scrollFraction(): number {
  const max = document.documentElement.scrollHeight - innerHeight;
  return max > 0 ? Math.min(1, scrollY / max) : 0;
}

export default function CosmosScene({ station, palette, lang, effects, calm }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const scene = useRef<SceneInstance | null>(null);
  const [state, setState] = useState<State>("loading");
  const reduceMotion = useReducedMotion();

  // Latest props for the mount effect and the scroll listener.
  const latest = useRef({ station, palette, lang, effects, calm, reduceMotion });
  latest.current = { station, palette, lang, effects, calm, reduceMotion };

  // Mount once; later changes go through update() / setProgress().
  useEffect(() => {
    let cancelled = false;
    import("../cosmos/scene")
      .then((mod) => {
        const el = host.current;
        if (cancelled || !el) return;
        if (!mod.webglAvailable()) {
          setState("fallback");
          return;
        }
        const p = latest.current;
        try {
          const s = new mod.CosmosScene(el, {
            palette: p.palette,
            lang: p.lang,
            effects: p.effects,
            calm: p.calm,
            reduceMotion: p.reduceMotion,
            authorPhotos: [authorHuong, authorTu],
          });
          s.setProgress(stationPoint(p.station, scrollFraction()), true);
          scene.current = s;
          setState("ready");
        } catch (err) {
          console.warn("M-AIDA cosmos scene unavailable:", err);
          setState("fallback");
        }
      })
      .catch((err: unknown) => {
        console.warn("M-AIDA cosmos scene unavailable:", err);
        if (!cancelled) setState("fallback");
      });
    return () => {
      cancelled = true;
      scene.current?.dispose();
      scene.current = null;
    };
  }, []);

  useEffect(() => {
    scene.current?.update({ palette, lang, effects, calm, reduceMotion });
  }, [palette, lang, effects, calm, reduceMotion, state]);

  // A new screen: fly to its station (from the top of the page).
  useEffect(() => {
    scene.current?.setProgress(stationPoint(station, scrollFraction()));
  }, [station, state]);

  // Scrolling a screen moves the camera along that screen's stretch.
  useEffect(() => {
    const onScroll = () => scene.current?.setProgress(stationPoint(latest.current.station, scrollFraction()));
    addEventListener("scroll", onScroll, { passive: true });
    return () => removeEventListener("scroll", onScroll);
  }, []);

  return (
    <>
      <div
        ref={host}
        className={`cosmos-scene cosmos-sky-${palette}`}
        aria-hidden="true"
        data-testid="cosmos-scene"
        data-state={state}
        data-station={station}
      />
      {state === "fallback" && <CosmosBackdrop calm={calm} />}
      <div className="cosmos-vignette" aria-hidden="true" />
    </>
  );
}
