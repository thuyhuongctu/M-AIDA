/**
 * WorldClocks - the time in Cần Thơ (where M-AIDA is made), in Paris and on
 * the viewer's own clock (design package 04/10/2026). The viewer's clock is
 * left out when it shows the same time as one of the other two.
 *
 * Plain Intl, nothing fetched; refreshed on the minute and when the tab
 * comes back into view.
 */

import React, { useEffect, useState } from "react";
import { useI18n, type StringKey } from "../i18n";

interface Zone {
  id: string;
  tz: string;
  label: StringKey | null;
}

const FIXED: Zone[] = [
  { id: "can-tho", tz: "Asia/Ho_Chi_Minh", label: "clock_cantho" },
  { id: "paris", tz: "Europe/Paris", label: "clock_paris" },
];

function localZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "";
  } catch {
    return "";
  }
}

/** Minutes east of UTC for a time zone at a given instant. */
export function offsetMinutes(tz: string, at: Date): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).formatToParts(at);
  const get = (type: Intl.DateTimeFormatPartTypes) => Number(parts.find((p) => p.type === type)?.value ?? 0);
  const wall = Date.UTC(get("year"), get("month") - 1, get("day"), get("hour") % 24, get("minute"));
  const utc = Date.UTC(at.getUTCFullYear(), at.getUTCMonth(), at.getUTCDate(), at.getUTCHours(), at.getUTCMinutes());
  return Math.round((wall - utc) / 60000);
}

function utcLabel(minutes: number): string {
  const sign = minutes < 0 ? "−" : "+";
  const abs = Math.abs(minutes);
  const h = Math.floor(abs / 60);
  const m = abs % 60;
  return `UTC${sign}${h}${m ? `:${String(m).padStart(2, "0")}` : ""}`;
}

function useMinute(): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    let timer = 0;
    const tick = () => {
      const d = new Date();
      setNow(d);
      timer = window.setTimeout(tick, 60_000 - (d.getSeconds() * 1000 + d.getMilliseconds()) + 50);
    };
    timer = window.setTimeout(tick, 60_000 - (now.getSeconds() * 1000 + now.getMilliseconds()) + 50);
    const onVisible = () => {
      if (!document.hidden) setNow(new Date());
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return now;
}

export default function WorldClocks({ variant = "strip" }: { variant?: "strip" | "card" }) {
  const { t, lang } = useI18n();
  const now = useMinute();
  const locale = lang === "vi" ? "vi-VN" : "en-GB";

  const local = localZone();
  const localOffset = -now.getTimezoneOffset();
  const zones: Zone[] = [...FIXED];
  if (!FIXED.some((z) => offsetMinutes(z.tz, now) === localOffset)) {
    zones.push({ id: "local", tz: local || "UTC", label: null });
  }

  return (
    <div className={`clocks clocks-${variant}`} data-testid="world-clocks" aria-label={t("clock_title")}>
      {zones.map((z) => {
        const off = z.id === "local" ? localOffset : offsetMinutes(z.tz, now);
        const time = new Intl.DateTimeFormat(locale, { timeZone: z.tz, hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(now);
        const day = new Intl.DateTimeFormat(locale, { timeZone: z.tz, weekday: "short", day: "numeric", month: "short" }).format(now);
        const hour = Number(new Intl.DateTimeFormat("en-US", { timeZone: z.tz, hour: "numeric", hourCycle: "h23" }).format(now));
        const daytime = hour >= 6 && hour < 18;
        const name = z.label ? t(z.label) : t("clock_local");
        return (
          <div className="clock" key={z.id} data-testid={`clock-${z.id}`}>
            <span className={`clock-sun ${daytime ? "clock-day" : "clock-night"}`} aria-hidden="true" />
            <span className="clock-place">
              {name}
              {z.id === "local" && local ? <small className="clock-zone"> · {local.replace(/_/g, " ")}</small> : null}
            </span>
            <time className="clock-time mono" dateTime={now.toISOString()} data-testid={`clock-${z.id}-time`}>
              {time}
            </time>
            <span className="clock-day-line mono">
              {day} · {utcLabel(off)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
