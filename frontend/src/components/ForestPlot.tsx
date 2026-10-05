/**
 * ForestPlot - preview of the locked effect sizes (8.0, phase 2 of the design).
 *
 * One row per record in the chosen set (locked by default; "approved" adds
 * approved-but-unlocked records, "all" adds unverified machine proposals and
 * marks them open): r with a 95% interval computed on Fisher's z
 * (z = atanh r, SE_z from the server's variance_z, or 1/(n-3) when absent),
 * back-transformed to r. The pooled diamond is a preview, fixed-effect
 * (inverse-variance) or random-effects (DerSimonian-Laird tau^2), and says so:
 * the dissertation's three-level model runs in metafor on the exported CSV,
 * not here. Nothing on this chart is stored; it is read from the records
 * every time.
 *
 * Marks follow the house chart rules: 2px interval lines, square markers of
 * at least 8px sized by weight, text in ink tokens, hairline axis, hover
 * tooltip per row; the value column doubles as the table view.
 */

import React, { useMemo, useState } from "react";
import { useI18n } from "../i18n";
import type { StudyDatabaseEntry } from "../types";

interface Row {
  id: string;
  label: string;
  r: number;
  lo: number;
  hi: number;
  w: number;
  n: number | null;
  locked: boolean;
}

export type ForestInclude = "locked" | "approved" | "all";
export type Estimator = "fixed" | "random";

export interface Pooled {
  r: number;
  lo: number;
  hi: number;
  k: number;
  /** Random effects only: between-study variance on the z scale, Q-based I² (%). */
  tau2?: number;
  i2?: number;
}

const Z = 1.959964;

function fisher(r: number): number {
  const c = Math.max(-0.999999, Math.min(0.999999, r));
  return 0.5 * Math.log((1 + c) / (1 - c));
}
const invFisher = (z: number): number => Math.tanh(z);

function fmt(v: number): string {
  return (v < 0 ? "−" : "") + Math.abs(v).toFixed(3);
}

function included(s: StudyDatabaseEntry, include: ForestInclude): boolean {
  if (include === "all") return true;
  if (include === "approved") return s.pi_locked || !!s.pi_approved_at;
  return s.pi_locked;
}

export function forestRows(studies: StudyDatabaseEntry[], include: ForestInclude = "locked"): Row[] {
  const rows: Row[] = [];
  for (const s of studies) {
    if (!included(s, include) || s.effect_r === null) continue;
    let varZ = s.variance_z;
    if ((varZ === null || varZ === undefined || varZ <= 0) && s.sample_n !== null && s.sample_n > 3) varZ = 1 / (s.sample_n - 3);
    if (varZ === null || varZ === undefined || varZ <= 0) continue;
    const z = fisher(s.effect_r);
    const se = Math.sqrt(varZ);
    const first = (s.authors || s.paper_title || s.study_id).split(/[;,&]| and /)[0].trim();
    rows.push({
      id: s.study_id,
      label: `${first} (${s.year}) · ${s.study_id.slice(0, 8)}`,
      r: s.effect_r,
      lo: invFisher(z - Z * se),
      hi: invFisher(z + Z * se),
      w: 1 / varZ,
      n: s.sample_n,
      locked: s.pi_locked,
    });
  }
  return rows;
}

export function pooledFixed(rows: Row[]): Pooled | null {
  if (rows.length === 0) return null;
  let sw = 0;
  let swz = 0;
  for (const row of rows) {
    sw += row.w;
    swz += row.w * fisher(row.r);
  }
  const z = swz / sw;
  const se = Math.sqrt(1 / sw);
  return { r: invFisher(z), lo: invFisher(z - Z * se), hi: invFisher(z + Z * se), k: rows.length };
}

/** DerSimonian-Laird random effects on Fisher's z (one level: effects treated as independent). */
export function pooledRandom(rows: Row[]): Pooled | null {
  const fixed = pooledFixed(rows);
  if (!fixed) return null;
  const zf = fisher(fixed.r);
  let sw = 0;
  let sw2 = 0;
  let q = 0;
  for (const row of rows) {
    sw += row.w;
    sw2 += row.w * row.w;
    q += row.w * (fisher(row.r) - zf) ** 2;
  }
  const df = rows.length - 1;
  const c = sw - sw2 / sw;
  const tau2 = df > 0 && c > 0 ? Math.max(0, (q - df) / c) : 0;
  let swr = 0;
  let swrz = 0;
  for (const row of rows) {
    const wr = 1 / (1 / row.w + tau2);
    swr += wr;
    swrz += wr * fisher(row.r);
  }
  const z = swrz / swr;
  const se = Math.sqrt(1 / swr);
  const i2 = q > 0 && df > 0 ? Math.max(0, (q - df) / q) * 100 : 0;
  return { r: invFisher(z), lo: invFisher(z - Z * se), hi: invFisher(z + Z * se), k: rows.length, tau2, i2 };
}

export default function ForestPlot({
  studies,
  include = "locked",
  estimator = "fixed",
}: {
  studies: StudyDatabaseEntry[];
  include?: ForestInclude;
  estimator?: Estimator;
}) {
  const { t } = useI18n();
  const [hover, setHover] = useState<string | null>(null);
  const rows = useMemo(() => forestRows(studies, include), [studies, include]);
  const pooled = useMemo(() => (estimator === "random" ? pooledRandom(rows) : pooledFixed(rows)), [rows, estimator]);
  const setLabel = include === "locked" ? t("ds_forest") : include === "approved" ? t("rp_set_approved_long") : t("rp_set_all_long");
  const pooledLabel = `${t("ds_pooled")} · ${estimator === "random" ? t("rp_est_random_short") : t("rp_est_fixed_short")}`;

  if (rows.length === 0) {
    return <p className="hint-text forest-empty">{t("ds_forest_empty")}</p>;
  }

  // Scale: symmetric-ish range covering every interval, snapped to 0.1 and clamped to [-1, 1].
  let lo = Math.min(...rows.map((r) => r.lo), pooled ? pooled.lo : 0, 0);
  let hi = Math.max(...rows.map((r) => r.hi), pooled ? pooled.hi : 0, 0);
  lo = Math.max(-1, Math.floor((lo - 0.05) * 10) / 10);
  hi = Math.min(1, Math.ceil((hi + 0.05) * 10) / 10);
  const span = hi - lo || 0.2;
  const step = span > 0.9 ? 0.25 : span > 0.45 ? 0.2 : 0.1;
  const ticks: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) ticks.push(Math.round(v * 1000) / 1000);

  const W = 420;
  const x = (v: number) => ((v - lo) / span) * W;
  const maxW = Math.max(...rows.map((r) => r.w));
  const size = (w: number) => 8 + 6 * Math.sqrt(w / maxW); // 8..14 px, area ~ weight

  return (
    <div className="forest" data-testid="forest-plot">
      <div className="forest-head">
        <span className="eyebrow">{setLabel} · k = {rows.length}</span>
        <span className="hint-inline">
          {t("ds_forest_note")}
          {estimator === "random" && pooled?.tau2 !== undefined && (
            <span className="mono" data-testid="forest-tau">
              {" "}τ² = {pooled.tau2.toFixed(4)} · I² = {(pooled.i2 ?? 0).toFixed(1)}%
            </span>
          )}
        </span>
      </div>
      <div className="forest-rows" role="table" aria-label={t("ds_forest")}>
        {rows.map((row) => {
          const s = size(row.w);
          const on = hover === row.id;
          return (
            <div
              key={row.id}
              role="row"
              className={`forest-row ${on ? "forest-row-on" : ""} ${row.locked ? "" : "forest-row-open"}`}
              onMouseEnter={() => setHover(row.id)}
              onMouseLeave={() => setHover(null)}
              title={`r = ${fmt(row.r)} [${fmt(row.lo)}, ${fmt(row.hi)}]${row.n ? ` · n = ${row.n}` : ""}${row.locked ? "" : ` · ${t("rp_not_locked")}`}`}
            >
              <span role="cell" className="forest-label">{row.label}</span>
              <svg role="cell" className="forest-cell" viewBox={`0 0 ${W} 24`} preserveAspectRatio="none" aria-hidden="true">
                <line x1={x(0)} x2={x(0)} y1={0} y2={24} className="forest-zero" />
                <line x1={x(row.lo)} x2={x(row.hi)} y1={12} y2={12} className="forest-ci" />
                <rect x={x(row.r) - s / 2} y={12 - s / 2} width={s} height={s} className="forest-mark" />
              </svg>
              <span role="cell" className="forest-value mono">
                {fmt(row.r)} [{fmt(row.lo)}, {fmt(row.hi)}]
              </span>
            </div>
          );
        })}
        {pooled && (
          <div role="row" className="forest-row forest-pooled" title={`${pooledLabel}: ${fmt(pooled.r)} [${fmt(pooled.lo)}, ${fmt(pooled.hi)}]`}>
            <span role="cell" className="forest-label"><strong>{pooledLabel}</strong></span>
            <svg role="cell" className="forest-cell" viewBox={`0 0 ${W} 24`} preserveAspectRatio="none" aria-hidden="true">
              <line x1={x(0)} x2={x(0)} y1={0} y2={24} className="forest-zero" />
              <polygon
                points={`${x(pooled.lo)},12 ${x(pooled.r)},3 ${x(pooled.hi)},12 ${x(pooled.r)},21`}
                className="forest-diamond"
              />
            </svg>
            <span role="cell" className="forest-value mono"><strong>{fmt(pooled.r)} [{fmt(pooled.lo)}, {fmt(pooled.hi)}]</strong></span>
          </div>
        )}
        <div className="forest-row forest-axis" aria-hidden="true">
          <span className="forest-label" />
          <svg className="forest-cell" viewBox={`0 0 ${W} 24`} preserveAspectRatio="none">
            <line x1={0} x2={W} y1={2} y2={2} className="forest-axisline" />
            {ticks.map((v) => (
              <g key={v}>
                <line x1={x(v)} x2={x(v)} y1={2} y2={7} className="forest-axisline" />
                <text x={x(v)} y={20} textAnchor="middle" className="forest-tick">{v === 0 ? "0" : fmt(v).replace(/0+$/, "").replace(/\.$/, "")}</text>
              </g>
            ))}
          </svg>
          <span className="forest-value" />
        </div>
      </div>
    </div>
  );
}
