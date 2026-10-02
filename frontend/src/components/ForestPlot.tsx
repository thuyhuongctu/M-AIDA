/**
 * ForestPlot - preview of the locked effect sizes (8.0, phase 2 of the design).
 *
 * One row per locked record: r with a 95% interval computed on Fisher's z
 * (z = atanh r, SE_z from the server's variance_z, or 1/(n-3) when absent),
 * back-transformed to r. The pooled diamond is a FIXED-EFFECT preview
 * (inverse-variance weights on z) and says so: the dissertation's three-level
 * model runs in metafor on the exported CSV, not here. Nothing on this chart
 * is stored; it is read from the records every time.
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

export function forestRows(studies: StudyDatabaseEntry[]): Row[] {
  const rows: Row[] = [];
  for (const s of studies) {
    if (!s.pi_locked || s.effect_r === null) continue;
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
    });
  }
  return rows;
}

export function pooledFixed(rows: Row[]): { r: number; lo: number; hi: number } | null {
  if (rows.length === 0) return null;
  let sw = 0;
  let swz = 0;
  for (const row of rows) {
    sw += row.w;
    swz += row.w * fisher(row.r);
  }
  const z = swz / sw;
  const se = Math.sqrt(1 / sw);
  return { r: invFisher(z), lo: invFisher(z - Z * se), hi: invFisher(z + Z * se) };
}

export default function ForestPlot({ studies }: { studies: StudyDatabaseEntry[] }) {
  const { t } = useI18n();
  const [hover, setHover] = useState<string | null>(null);
  const rows = useMemo(() => forestRows(studies), [studies]);
  const pooled = useMemo(() => pooledFixed(rows), [rows]);

  if (rows.length === 0) {
    return <p className="hint-text">{t("ds_forest_empty")}</p>;
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
        <span className="eyebrow">{t("ds_forest")} · k = {rows.length}</span>
        <span className="hint-inline">{t("ds_forest_note")}</span>
      </div>
      <div className="forest-rows" role="table" aria-label={t("ds_forest")}>
        {rows.map((row) => {
          const s = size(row.w);
          const on = hover === row.id;
          return (
            <div
              key={row.id}
              role="row"
              className={`forest-row ${on ? "forest-row-on" : ""}`}
              onMouseEnter={() => setHover(row.id)}
              onMouseLeave={() => setHover(null)}
              title={`r = ${fmt(row.r)} [${fmt(row.lo)}, ${fmt(row.hi)}]${row.n ? ` · n = ${row.n}` : ""}`}
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
          <div role="row" className="forest-row forest-pooled" title={`${t("ds_pooled")}: ${fmt(pooled.r)} [${fmt(pooled.lo)}, ${fmt(pooled.hi)}]`}>
            <span role="cell" className="forest-label"><strong>{t("ds_pooled")}</strong></span>
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
