/**
 * Stations of the cosmos flight (design package "M-AIDA Cloud Cosmos"): each
 * screen of the app owns a stretch [start, span] of the camera path, 0..1.
 * Opening a screen flies the camera to `start`; scrolling that screen moves
 * it up to `start + span`.
 *
 * Where the path goes: galaxy core (0-0.2), the six workflow planets
 * PARSE 0.25, IDENTIFY 0.325, CONVERT 0.4, EVIDENCE 0.475, VERIFY 0.55,
 * LOCK 0.625, the Earth with Can Tho (0.76), the nine streams and the
 * constellation of effect sizes (0.86 on).
 *
 * Kept apart from scene.ts so the app can use it without loading three.js.
 */

export const STATIONS = {
  login: [0.12, 0.04],
  billing: [0.18, 0.06],
  extract: [0.22, 0.08],
  dashboard: [0.3, 0.12],
  verify: [0.44, 0.1],
  account: [0.6, 0.06],
  team: [0.74, 0.06],
  dataset: [0.86, 0.12],
} as const;

export type Station = keyof typeof STATIONS;

/** Point of the path for a station at scroll fraction f (0..1). */
export function stationPoint(station: Station, f: number): number {
  const [start, span] = STATIONS[station];
  return start + Math.max(0, Math.min(1, f)) * span;
}
