/**
 * StatusPill - one pill in the header that says whether the service is usable.
 *
 * 8.0 replaces the four-pill status strip of 7.2 with a single indicator;
 * the detail (backend version, storage, extraction mode, network) is in the
 * tooltip and in the expanded view on click. The logic is unchanged: a
 * failed /api/health call is itself the signal, and the extraction state is
 * either live or plainly unavailable - no third mode exists.
 */

import React, { useCallback, useEffect, useState } from "react";
import { fetchHealth } from "../api";
import { useI18n } from "../i18n";
import type { HealthResponse } from "../types";

const POLL_INTERVAL_MS = 15_000;

export default function StatusPill() {
  const { t } = useI18n();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [reachable, setReachable] = useState<boolean | null>(null);
  const [online, setOnline] = useState<boolean>(typeof navigator === "undefined" ? true : navigator.onLine);
  const [open, setOpen] = useState(false);

  const poll = useCallback(async () => {
    try {
      setHealth(await fetchHealth());
      setReachable(true);
    } catch {
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

  let tone: "ok" | "warn" | "bad" = "warn";
  let label = t("status_checking");
  if (!online) {
    tone = "bad";
    label = t("status_offline");
  } else if (reachable === false) {
    tone = "bad";
    label = t("status_backend_down");
  } else if (reachable && health) {
    if (health.extraction_mode === "live") {
      tone = "ok";
      label = t("status_ok");
    } else {
      tone = "warn";
      label = t("status_llm_off");
    }
  }

  const details = health
    ? [
        `backend v${health.version}`,
        health.storage ?? "",
        health.auth_mode ?? "",
        health.extraction_mode === "live" ? "llm ready" : "llm unavailable",
        online ? "online" : "offline",
      ].filter(Boolean)
    : [];

  return (
    <div className="status-wrap">
      <button
        type="button"
        className={`status-pill status-${tone}`}
        onClick={() => setOpen((o) => !o)}
        title={details.join(" · ")}
        aria-expanded={open}
        data-testid="status-pill"
      >
        <span className="status-dot" aria-hidden="true" />
        {label}
      </button>
      {open && details.length > 0 && (
        <div className="status-pop" role="status">
          <strong>{t("status_title")}</strong>
          <ul>
            {details.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
