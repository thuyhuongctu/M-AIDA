/**
 * MusicPlayer - the "♪" button in the header and on the sign-in page, with a
 * small panel: the two M-AIDA songs, play/pause and volume (see music.ts).
 * Off until the listener presses play.
 */

import React, { useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n";
import { TRACKS, choose, setVolume, toggle, useMusic } from "../music";

export default function MusicPlayer() {
  const { t } = useI18n();
  const music = useMusic();
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const busy = music.playing || music.loading;
  const current = TRACKS[music.track];

  return (
    <div className="music" ref={wrap}>
      <button
        type="button"
        className={`btn btn-ghost btn-sm music-btn ${busy ? "music-btn-on" : ""}`}
        aria-expanded={open}
        aria-haspopup="dialog"
        title={t("music_title")}
        onClick={() => setOpen((o) => !o)}
        data-testid="music-open"
        data-playing={music.playing ? "true" : "false"}
      >
        <span aria-hidden="true">♪</span>
        {music.playing ? <span className="music-eq" aria-hidden="true"><i /><i /><i /></span> : null}
        <span className="sr-only">{t("music_title")}</span>
      </button>
      {open && (
        <div className="music-panel" role="dialog" aria-label={t("music_title")} data-testid="music-panel">
          <div className="music-head">
            <strong>{t("music_title")}</strong>
            <span className="hint-inline">{t("music_by")}</span>
          </div>
          <ol className="music-list">
            {TRACKS.map((track, i) => (
              <li key={track.id}>
                <button
                  type="button"
                  className={`music-track ${i === music.track ? "music-track-on" : ""}`}
                  aria-current={i === music.track ? "true" : undefined}
                  onClick={() => choose(i, true)}
                  data-testid={`music-track-${track.id}`}
                >
                  {track.title}
                </button>
              </li>
            ))}
          </ol>
          <div className="music-controls">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={toggle}
              aria-label={busy ? t("music_pause") : t("music_play")}
              data-testid="music-toggle"
            >
              {busy ? `❚❚ ${t("music_pause")}` : `▶ ${t("music_play")}`}
            </button>
            <label className="music-volume">
              <span className="sr-only">{t("music_volume")}</span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={music.volume}
                onChange={(e) => setVolume(Number(e.target.value))}
                aria-label={t("music_volume")}
              />
            </label>
          </div>
          <p className="music-now hint-inline" aria-live="polite">
            {music.failed ? t("music_failed") : music.loading ? t("loading") : music.playing ? current.title : t("music_off")}
          </p>
        </div>
      )}
    </div>
  );
}
