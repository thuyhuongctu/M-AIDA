import {
  AlertTriangle,
  BrainCircuit,
  Database,
  Globe2,
  Layers3,
  LockKeyhole,
  Network,
  RefreshCw,
  ScanSearch,
  Sparkles,
} from "lucide-react";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { fetchStudies } from "../api";
import type {
  DoiMeasure,
  PerformanceMeasure,
  StudyDatabaseEntry,
} from "../types";

type MapPoint = {
  label: string;
  x: number;
  y: number;
  count: number;
};

const countryPositions: Array<{
  match: RegExp;
  label: string;
  x: number;
  y: number;
}> = [
  { match: /uk|united kingdom/i, label: "United Kingdom", x: 47, y: 30 },
  { match: /spain/i, label: "Spain", x: 45, y: 39 },
  { match: /sweden/i, label: "Sweden", x: 50, y: 22 },
  { match: /poland/i, label: "Poland", x: 52, y: 32 },
  { match: /turkey/i, label: "Türkiye", x: 57, y: 41 },
  { match: /india/i, label: "India", x: 69, y: 53 },
  { match: /china/i, label: "China", x: 78, y: 42 },
  { match: /vietnam/i, label: "Vietnam", x: 80, y: 57 },
  { match: /usa|canada/i, label: "North America", x: 20, y: 36 },
  { match: /multi/i, label: "Multi-country", x: 50, y: 55 },
];

const doiMeasures: DoiMeasure[] = ["FSTS", "GEO", "EXP", "FDI", "COMP", "OTH"];
const performanceMeasures: PerformanceMeasure[] = ["ACC", "MKT", "LAB", "MIX"];

function toMapPoints(studies: StudyDatabaseEntry[]): MapPoint[] {
  const points = new Map<string, MapPoint>();
  studies.forEach((study) => {
    const position = countryPositions.find(({ match }) => match.test(study.country));
    if (!position) return;
    const current = points.get(position.label);
    points.set(position.label, {
      label: position.label,
      x: position.x,
      y: position.y,
      count: (current?.count ?? 0) + 1,
    });
  });
  return [...points.values()];
}

function getIssueSummary(studies: StudyDatabaseEntry[]) {
  const countries = new Map<string, number>();
  const doiCounts = new Map<string, number>();
  let totalSample = 0;
  let reviewCount = 0;
  let missingEffect = 0;
  let lockedCount = 0;
  let positive = 0;
  let negative = 0;
  let nearZero = 0;

  studies.forEach((study) => {
    const country = study.country.trim() || "Unspecified";
    countries.set(country, (countries.get(country) ?? 0) + 1);
    if (study.doi_measure) {
      doiCounts.set(study.doi_measure, (doiCounts.get(study.doi_measure) ?? 0) + 1);
    }
    totalSample += study.sample_n ?? 0;
    if (study.requires_verification) reviewCount += 1;
    if (study.pi_locked) lockedCount += 1;
    if (study.effect_r === null) missingEffect += 1;
    else if (study.effect_r > 0.05) positive += 1;
    else if (study.effect_r < -0.05) negative += 1;
    else nearZero += 1;
  });

  const largestCountry = [...countries.entries()].sort((a, b) => b[1] - a[1])[0];
  const dominantMeasure = [...doiCounts.entries()].sort((a, b) => b[1] - a[1])[0];
  const effects = studies
    .map((study) => study.effect_r)
    .filter((value): value is number => value !== null);
  const descriptiveMean = effects.length
    ? effects.reduce((sum, value) => sum + value, 0) / effects.length
    : null;

  return {
    countries,
    descriptiveMean,
    dominantMeasure,
    largestCountry,
    lockedCount,
    missingEffect,
    negative,
    nearZero,
    positive,
    reviewCount,
    totalSample,
  };
}

function EvidenceMap({ points }: { points: MapPoint[] }) {
  return (
    <div className="ri-map" role="img" aria-label="Geographic distribution of extracted evidence">
      <svg viewBox="0 0 100 64" aria-hidden="true">
        <defs>
          <radialGradient id="mapGlow">
            <stop offset="0" stopColor="#38bdf8" stopOpacity=".65" />
            <stop offset="1" stopColor="#38bdf8" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="routeGradient" x1="0" x2="1">
            <stop stopColor="#22d3ee" stopOpacity=".25" />
            <stop offset=".55" stopColor="#60a5fa" stopOpacity=".85" />
            <stop offset="1" stopColor="#a78bfa" stopOpacity=".3" />
          </linearGradient>
        </defs>
        <g className="ri-grid-lines">
          {[20, 40, 60, 80].map((x) => <line key={`x-${x}`} x1={x} y1="4" x2={x} y2="60" />)}
          {[16, 32, 48].map((y) => <line key={`y-${y}`} x1="4" y1={y} x2="96" y2={y} />)}
        </g>
        <g className="ri-continents">
          <path d="M7 20 13 11 25 9 32 16 28 24 20 28 17 38 11 34 13 26Z" />
          <path d="m27 37 8 3 4 9-5 12-6-8-4-10Z" />
          <path d="m41 17 9-7 10 3 4 8 13 2 13 10-6 11-14-2-9 7-11-3-6-11-8-6Z" />
          <path d="m47 38 11 1 7 8-5 14-9-3-5-11Z" />
          <path d="m79 47 10 1 7 7-7 5-12-5Z" />
        </g>
        <g className="ri-routes">
          {points.map((point, index) => {
            const bend = 14 + (index % 3) * 4;
            return (
              <path
                key={`route-${point.label}`}
                d={`M ${point.x} ${point.y} Q 52 ${bend} 50 35`}
              />
            );
          })}
        </g>
        <circle cx="50" cy="35" r="12" fill="url(#mapGlow)" />
        <g className="ri-map-points">
          {points.map((point) => (
            <g key={point.label}>
              <circle className="ri-point-pulse" cx={point.x} cy={point.y} r={2.2 + Math.min(point.count, 5) * .35} />
              <circle cx={point.x} cy={point.y} r={0.8 + Math.min(point.count, 5) * .15} />
            </g>
          ))}
        </g>
      </svg>
      <div className="ri-map-caption">
        <span><i className="ri-dot ri-dot-cyan" />Observed study location</span>
        <span><i className="ri-dot ri-dot-purple" />Synthesis workspace</span>
      </div>
      <div className="ri-map-labels" aria-hidden="true">
        {points.slice(0, 7).map((point) => (
          <span key={point.label} style={{ left: `${point.x}%`, top: `${point.y}%` }}>
            {point.label} · {point.count}
          </span>
        ))}
      </div>
    </div>
  );
}

function EffectLandscape({ studies }: { studies: StudyDatabaseEntry[] }) {
  const effects = studies.filter((study) => study.effect_r !== null).slice(0, 12);
  return (
    <div className="ri-effect-plot">
      <div className="ri-effect-axis" aria-hidden="true">
        <span>−.25</span><span>−.10</span><span>0</span><span>+.10</span><span>+.25</span>
      </div>
      <div className="ri-zero-line" aria-hidden="true" />
      {effects.map((study) => {
        const value = study.effect_r ?? 0;
        const position = Math.max(2, Math.min(98, ((value + .25) / .5) * 100));
        return (
          <div className="ri-effect-row" key={study.study_id}>
            <span className="ri-effect-name" title={study.paper_title}>{study.paper_title}</span>
            <div className="ri-effect-track">
              <span
                className={`ri-effect-point ${study.pi_locked ? "is-locked" : "is-review"}`}
                style={{ left: `${position}%` }}
                title={`${study.paper_title}: r = ${value.toFixed(3)}`}
              />
            </div>
            <span className="ri-effect-value">{value > 0 ? "+" : ""}{value.toFixed(3)}</span>
          </div>
        );
      })}
      {!effects.length && <p className="ri-empty">No effect-size records available.</p>}
    </div>
  );
}

export default function ResearchIntelligence() {
  const [studies, setStudies] = useState<StudyDatabaseEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStudies(await fetchStudies());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Evidence data could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const summary = useMemo(() => getIssueSummary(studies), [studies]);
  const mapPoints = useMemo(() => toMapPoints(studies), [studies]);
  const maxCell = useMemo(() => {
    let max = 1;
    doiMeasures.forEach((doi) => performanceMeasures.forEach((performance) => {
      max = Math.max(max, studies.filter((study) => study.doi_measure === doi && study.performance_measure === performance).length);
    }));
    return max;
  }, [studies]);

  const issues = [
    {
      icon: ScanSearch,
      tone: "amber",
      title: "Verification queue",
      value: summary.reviewCount,
      detail: summary.reviewCount ? "Records still require PI review before analysis." : "No current records await PI review.",
    },
    {
      icon: Globe2,
      tone: "cyan",
      title: "Geographic concentration",
      value: summary.largestCountry ? `${Math.round((summary.largestCountry[1] / Math.max(studies.length, 1)) * 100)}%` : "—",
      detail: summary.largestCountry ? `${summary.largestCountry[0]} is the largest location label in this dataset.` : "No location data available.",
    },
    {
      icon: Layers3,
      tone: "purple",
      title: "Measure concentration",
      value: summary.dominantMeasure?.[0] ?? "—",
      detail: summary.dominantMeasure ? `${summary.dominantMeasure[1]} records use the most common internationalization measure.` : "No DOI measure has been coded.",
    },
    {
      icon: AlertTriangle,
      tone: "rose",
      title: "Missing effects",
      value: summary.missingEffect,
      detail: summary.missingEffect ? "These records cannot enter an r-based synthesis yet." : "All loaded records contain an r effect size.",
    },
  ];

  return (
    <section className="research-intelligence" aria-labelledby="ri-title">
      <header className="ri-hero">
        <div>
          <span className="ri-eyebrow"><Sparkles size={14} /> M‑AIDA Research Intelligence</span>
          <h2 id="ri-title">See the evidence landscape—not only the spreadsheet.</h2>
          <p>Interactive descriptive diagnostics for the internationalization–performance evidence base.</p>
        </div>
        <div className="ri-hero-actions">
          <span className="ri-live"><i /> {loading ? "Syncing evidence" : `${studies.length} records mapped`}</span>
          <button type="button" className="ri-refresh" onClick={() => void load()} disabled={loading}>
            <RefreshCw size={15} className={loading ? "is-spinning" : ""} /> Refresh
          </button>
        </div>
      </header>

      {error && (
        <div className="ri-error" role="alert">
          <AlertTriangle size={18} />
          <span><strong>Backend connection required.</strong> {error}</span>
        </div>
      )}

      <div className="ri-kpis">
        <article><Database size={18} /><span>Evidence records</span><strong>{studies.length}</strong><small>Current filtered database</small></article>
        <article><Network size={18} /><span>Location labels</span><strong>{summary.countries.size}</strong><small>Geographic coverage</small></article>
        <article><LockKeyhole size={18} /><span>PI locked</span><strong>{summary.lockedCount}</strong><small>Analysis-ready governance</small></article>
        <article><BrainCircuit size={18} /><span>Descriptive mean r</span><strong>{summary.descriptiveMean === null ? "—" : `${summary.descriptiveMean >= 0 ? "+" : ""}${summary.descriptiveMean.toFixed(3)}`}</strong><small>Unweighted; not a pooled estimate</small></article>
      </div>

      <div className="ri-grid ri-grid-main">
        <article className="ri-card ri-map-card">
          <div className="ri-card-heading">
            <div><span>Evidence geography</span><h3>Where the current evidence comes from</h3></div>
            <span className="ri-card-badge">Live data</span>
          </div>
          <EvidenceMap points={mapPoints} />
        </article>

        <article className="ri-card ri-lens-card">
          <div className="ri-card-heading">
            <div><span>Evidence Lens</span><h3>What deserves attention now</h3></div>
            <BrainCircuit size={20} />
          </div>
          <div className="ri-lens-lead">
            <Sparkles size={18} />
            <p>The database spans <strong>{summary.countries.size} location labels</strong>, but coverage and measurement remain uneven.</p>
          </div>
          <ul className="ri-lens-list">
            <li><i className="ri-dot ri-dot-green" /><span><strong>{summary.positive}</strong> effects are above +.05</span></li>
            <li><i className="ri-dot ri-dot-rose" /><span><strong>{summary.negative}</strong> effects are below −.05</span></li>
            <li><i className="ri-dot ri-dot-amber" /><span><strong>{summary.nearZero}</strong> effects fall in the descriptive −.05 to +.05 band</span></li>
            <li><i className="ri-dot ri-dot-purple" /><span><strong>{summary.reviewCount}</strong> records still require human verification</span></li>
          </ul>
          <div className="ri-integrity-note">
            <LockKeyhole size={15} /> These are descriptive diagnostics. Causal or pooled claims require the locked meta-analysis model.
          </div>
        </article>
      </div>

      <div className="ri-section-heading">
        <div><span>Research problem radar</span><h3>Four issues visible in the current evidence base</h3></div>
        <small>Computed from loaded records</small>
      </div>
      <div className="ri-issues">
        {issues.map(({ icon: Icon, tone, title, value, detail }) => (
          <article className={`ri-issue ri-tone-${tone}`} key={title}>
            <div><Icon size={18} /><span>{title}</span></div>
            <strong>{value}</strong>
            <p>{detail}</p>
          </article>
        ))}
      </div>

      <div className="ri-grid ri-grid-analysis">
        <article className="ri-card">
          <div className="ri-card-heading">
            <div><span>Effect landscape</span><h3>Direction and dispersion of extracted r</h3></div>
            <span className="ri-legend"><i className="is-locked" /> Locked <i className="is-review" /> Review</span>
          </div>
          <EffectLandscape studies={studies} />
        </article>

        <article className="ri-card">
          <div className="ri-card-heading">
            <div><span>Coverage matrix</span><h3>Internationalization × performance measures</h3></div>
          </div>
          <div className="ri-matrix" role="table" aria-label="Coverage matrix">
            <span className="ri-matrix-corner" />
            {performanceMeasures.map((measure) => <strong key={measure}>{measure}</strong>)}
            {doiMeasures.map((doi) => (
              <React.Fragment key={doi}>
                <strong>{doi}</strong>
                {performanceMeasures.map((performance) => {
                  const count = studies.filter((study) => study.doi_measure === doi && study.performance_measure === performance).length;
                  return (
                    <span
                      key={`${doi}-${performance}`}
                      className={count ? "has-data" : "is-gap"}
                      style={{ "--cell-strength": count / maxCell } as React.CSSProperties}
                      title={`${doi} × ${performance}: ${count} record${count === 1 ? "" : "s"}`}
                    >{count || "·"}</span>
                  );
                })}
              </React.Fragment>
            ))}
          </div>
          <p className="ri-matrix-note"><i /> Empty cells are candidate evidence gaps, not proof that no studies exist.</p>
        </article>
      </div>

      <footer className="ri-footer-note">
        <span><Database size={15} /> Total coded sample: <strong>{summary.totalSample.toLocaleString()}</strong></span>
        <span><LockKeyhole size={15} /> Human verification remains authoritative</span>
      </footer>
    </section>
  );
}
