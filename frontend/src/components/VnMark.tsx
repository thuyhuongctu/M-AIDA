/**
 * VnMark - the line map of Vietnam that sits under the page, as on the 7.x
 * site: mainland outline, the Paracel (Hoang Sa) and Spratly (Truong Sa)
 * archipelagos, the flag at the northern tip, a star at Can Tho and four
 * blinking lighthouses (the blink stops under prefers-reduced-motion).
 * Decorative only: hidden from assistive technology, never intercepts clicks.
 */

import React from "react";
import vnmark from "../assets/vnmark.svg";

export default function VnMark({ variant = "page" }: { variant?: "page" | "hero" }) {
  return (
    <div className={`vnmark vnmark-${variant}`} aria-hidden="true">
      <img src={vnmark} alt="" draggable={false} />
    </div>
  );
}
