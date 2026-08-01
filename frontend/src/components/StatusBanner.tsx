/**
 * Status strip shown above the tabs during a live demo.
 *
 * Purpose: a presenter should never have to guess, mid-defence, whether the
 * backend is reachable, whether the store is persistent, whether the browser
 * is online, and what the next upload will actually do. All four are shown
 * together and refreshed on a timer, so a failure is visible before it is
 * demonstrated rather than after.
 *
 * The extraction indicator deliberately distinguishes three states rather than
 * two: live extraction, the rehearsed fallback, and genuinely unavailable. If
 * the fallback is what will run, the strip says so in plain words, so nothing
 * shown on screen can be mistaken for a live model output.
 */

import React, { useCallback, useEffect, useState } from "react";
import { fetchHealth } from "../api";
import type { HealthResponse } from "../types";

const POLL_INTERVAL_MS = 15_000;

type Tone = "ok" | "warn" | "bad";

function Pill({ tone, label, value }: { tone: Tone; label: string; value: string }) {
  const cls = tone === "ok" ? "badge-success" : tone === "warn" ? "badge-medium" : "badge-low";
  return (
    <span className="status-pill">
      <span className="status-pill-label">{label}</span>
      <span className={`badge ${cls}`}>{value}</span>
    </span>
  );
}

export default function StatusBanner() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [reachable, setReachable] = useState<boolean | null>(null);
  const [online, setOnline] = useState<boolean>(
    typeof navigator === "undefined" ? true : navigator.onLine
  );

  const poll = useCallback(async () => {
    try {
      setHealth(await fetchHealth());
      setReachable(true);
    } catch {
      // A failed health call is itself the signal; keep the last known payload
      // so the strip can still say what the backend reported before it died.
      setReachable(false);
    }
  }, []);

  useEffect(() => {
    void poll();
    const timer = window.setInterval(() => void poll(), POLL_INTERVAL_MS);
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, [poll]);

  const mode = health?.extraction_mode;
  const extraction: { tone: Tone; value: string } =
    reachable === false
      ? { tone: "bad", value: "backend unreachable" }
      : mode === "live"
      ? { tone: "ok", value: "live" }
      : mode === "rehearsed_fallback"
      ? { tone: "warn", value: "rehearsed fallback" }
      : mode === "unavailable"
      ? { tone: "bad", value: "unavailable" }
      : { tone: "warn", value: "checking…" };

  const persistent = health?.storage === "sqlite";

  return (
    <div className="status-banner" role="status" aria-live="polite">
      <Pill
        tone={reachable ? "ok" : reachable === false ? "bad" : "warn"}
        label="Backend"
        value={reachable ? `up · v${health?.version ?? "?"}` : reachable === false ? "down" : "checking…"}
      />
      <Pill
        tone={persistent ? "ok" : "warn"}
        label="Data"
        value={
          health
            ? `${persistent ? "persistent" : health.storage ?? "unknown"} · ${health.study_count} record(s)`
            : "checking…"
        }
      />
      <Pill tone={extraction.tone} label="Extraction" value={extraction.value} />
      <Pill tone={online ? "ok" : "warn"} label="Network" value={online ? "online" : "offline"} />

      {mode === "rehearsed_fallback" && reachable && (
        <p className="status-banner-note">
          Live extraction is unavailable, so an upload will return a{" "}
          <strong>rehearsed fallback record</strong>, clearly stamped as such and
          still requiring human verification. It is illustrative only and is not
          part of the frozen analysis corpus.
        </p>
      )}
    </div>
  );
}
