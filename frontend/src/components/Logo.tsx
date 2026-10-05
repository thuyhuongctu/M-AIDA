import React, { useId } from "react";

/**
 * Wordmark: the mark and the name in serif.
 *
 * Paper look: two opposed triangles (the lock glyph), the primary mark.
 * Cosmos look: the orbit mark (05/10/2026), a secondary mark used only with
 * the night-sky look: the centre is the pooled estimate, the three rings the
 * three levels of the meta-analytic model, the planet one study. CSS shows one
 * or the other from <html data-look>; the orbit is not the registered logo.
 */
export function Logo({ compact = false }: { compact?: boolean }) {
  const gap = `orbit-gap-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
  return (
    <span className={`logo ${compact ? "logo-compact" : ""}`} aria-label="M-AIDA">
      <svg className="logo-mark" viewBox="0 0 48 32" width="42" height="28" aria-hidden="true">
        <polygon points="2,16 18,4 18,28" fill="var(--accent)" />
        <polygon points="46,16 30,4 30,28" fill="var(--ink)" />
        <rect x="20" y="15" width="8" height="2" fill="var(--ink)" />
      </svg>
      <svg className="logo-orbit" viewBox="0 0 32 32" width="30" height="30" aria-hidden="true" data-testid="logo-orbit">
        <defs>
          <mask id={gap}>
            <rect width="32" height="32" fill="#fff" />
            <circle cx="23.07" cy="8.93" r="4" fill="#000" />
          </mask>
        </defs>
        <circle cx="16" cy="16" r="14.6" fill="none" stroke="var(--orbit-ring)" strokeWidth="0.9" />
        <circle cx="16" cy="16" r="10" fill="none" stroke="var(--accent-dark)" strokeWidth="1.7" mask={`url(#${gap})`} />
        <circle cx="16" cy="16" r="5.4" fill="none" stroke="var(--ok)" strokeWidth="1.1" />
        <circle cx="16" cy="16" r="1.7" fill="var(--ink)" />
        <circle cx="23.07" cy="8.93" r="2.7" fill="var(--accent-dark)" />
      </svg>
      <span className="logo-text">
        M<span className="logo-dash">-</span>AIDA
      </span>
    </span>
  );
}
