import React from "react";

/** Wordmark: two opposed triangles (the lock glyph) and the name in serif. */
export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <span className={`logo ${compact ? "logo-compact" : ""}`} aria-label="M-AIDA">
      <svg className="logo-mark" viewBox="0 0 48 32" width="42" height="28" aria-hidden="true">
        <polygon points="2,16 18,4 18,28" fill="var(--accent)" />
        <polygon points="46,16 30,4 30,28" fill="var(--ink)" />
        <rect x="20" y="15" width="8" height="2" fill="var(--ink)" />
      </svg>
      <span className="logo-text">
        M<span className="logo-dash">-</span>AIDA
      </span>
    </span>
  );
}
