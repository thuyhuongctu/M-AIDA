/**
 * ReviewScreen - the three-pane "Verify & Lock" workspace (8.0).
 *
 *   left   queue: every record of the caller, filterable by state, with the
 *          confidence score; J / K move, A approves, L opens the lock dialog
 *   middle evidence: the verbatim quotation and page for the statistic and
 *          for the sample size, plus how the server derived r. The PDF is not
 *          retained (privacy policy), so the quotation is the evidence.
 *   right  VerificationPanel: machine vs current values, moderators, derived
 *          quantities, notes, approve / lock / flag.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchStudies } from "../api";
import { useI18n } from "../i18n";
import type { StudyDatabaseEntry } from "../types";
import VerificationPanel, { VerificationPanelHandle } from "./VerificationPanel";

type Filter = "all" | "pending" | "approved" | "locked";

/** Queue state: a record is "approved" only once a person approved it (8.0),
 *  whatever the machine's confidence flag says. */
export function stateOf(s: StudyDatabaseEntry): "pending" | "approved" | "locked" {
  if (s.pi_locked) return "locked";
  if (s.pi_approved_at) return "approved";
  return "pending";
}

export function Glyph({ state }: { state: "pending" | "approved" | "locked" }) {
  return (
    <span className={`glyph glyph-${state}`} aria-hidden="true">
      {state === "pending" ? "◇" : "◆"}
    </span>
  );
}

function fmtR(v: number | null): string {
  return v === null ? "–" : (v >= 0 ? "" : "−") + Math.abs(v).toFixed(3);
}

function derivation(s: StudyDatabaseEntry): string | null {
  if (s.effect_r === null) return null;
  const r = fmtR(s.effect_r);
  if (s.r_source === "reported") return `effect_r = ${r} (reported)`;
  if (s.effect_t !== null && s.effect_df !== null && s.r_source === "derived")
    return `effect_t = ${fmtR(s.effect_t)}, df = ${s.effect_df} → r = t / √(t² + df) = ${r}`;
  if (s.effect_beta !== null && s.r_source === "imputed")
    return `β = ${fmtR(s.effect_beta)} → r ≈ 0.98·β${s.lambda_applied ? " + 0.05" : ""} (Peterson & Brown 2005) = ${r}`;
  return `effect_r = ${r}`;
}

interface ReviewScreenProps {
  /** Study to select when the screen opens (from the dashboard's "next up"). */
  initialStudyId?: string | null;
  refreshKey: number;
  onChanged?: () => void;
}

export default function ReviewScreen({ initialStudyId, refreshKey, onChanged }: ReviewScreenProps) {
  const { t } = useI18n();
  const [studies, setStudies] = useState<StudyDatabaseEntry[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [selectedId, setSelectedId] = useState<string | null>(initialStudyId ?? null);
  const [evidenceTab, setEvidenceTab] = useState<"stat" | "n">("stat");
  const [error, setError] = useState<string | null>(null);
  const panelRef = useRef<VerificationPanelHandle>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchStudies({});
      // newest first so a fresh extraction sits at the top of the queue
      data.sort((a, b) => (a.extracted_at < b.extracted_at ? 1 : -1));
      setStudies(data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error_generic"));
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  useEffect(() => {
    if (initialStudyId) setSelectedId(initialStudyId);
  }, [initialStudyId]);

  const counts = useMemo(() => {
    const c = { all: studies.length, pending: 0, approved: 0, locked: 0 };
    for (const s of studies) c[stateOf(s)] += 1;
    return c;
  }, [studies]);

  const visible = useMemo(
    () => (filter === "all" ? studies : studies.filter((s) => stateOf(s) === filter)),
    [studies, filter]
  );

  const selected = useMemo(() => studies.find((s) => s.study_id === selectedId) ?? null, [studies, selectedId]);
  const index = visible.findIndex((s) => s.study_id === selectedId);

  const move = useCallback(
    (delta: number) => {
      if (visible.length === 0) return;
      const next = index < 0 ? 0 : Math.min(visible.length - 1, Math.max(0, index + delta));
      setSelectedId(visible[next].study_id);
      setEvidenceTab("stat");
    },
    [visible, index]
  );

  // Keyboard: ignore when typing in a field or when a dialog is open.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select" || target?.isContentEditable) return;
      if (document.querySelector("dialog[open]")) return;
      if (e.key === "j" || e.key === "J") move(1);
      else if (e.key === "k" || e.key === "K") move(-1);
      else if ((e.key === "a" || e.key === "A") && selected && !selected.pi_locked) panelRef.current?.approve();
      else if ((e.key === "l" || e.key === "L") && selected && !selected.pi_locked) panelRef.current?.openLock();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [move, selected]);

  const handleUpdated = useCallback(
    (updated: StudyDatabaseEntry) => {
      setStudies((prev) => prev.map((s) => (s.study_id === updated.study_id ? updated : s)));
      onChanged?.();
    },
    [onChanged]
  );

  const handleDeleted = useCallback(
    (studyId: string) => {
      setStudies((prev) => prev.filter((s) => s.study_id !== studyId));
      setSelectedId(null);
      onChanged?.();
    },
    [onChanged]
  );

  const quote = selected
    ? evidenceTab === "stat"
      ? { page: selected.evidence_page, text: selected.evidence_quote, reads: derivation(selected) }
      : { page: selected.n_evidence_page, text: selected.n_evidence_quote, reads: selected.sample_n !== null ? `sample_n = ${selected.sample_n}` : null }
    : null;
  const hasAnyEvidence = !!(selected && (selected.evidence_quote || selected.n_evidence_quote));

  return (
    <div className="review" data-testid="review-screen">
      <aside className="rv-queue" data-tour="queue">
        <div className="rv-queue-head">
          <span className="eyebrow">{t("rv_queue")}</span>
          <div className="chips">
            {(["all", "pending", "approved", "locked"] as Filter[]).map((f) => (
              <button
                key={f}
                type="button"
                className={`chip ${filter === f ? "chip-on" : ""}`}
                onClick={() => setFilter(f)}
                data-testid={`rv-filter-${f}`}
              >
                {t(`rv_${f}` as const)} <span className="chip-count">{counts[f]}</span>
              </button>
            ))}
          </div>
        </div>
        {error && <p className="error-message">{error}</p>}
        {visible.length === 0 ? (
          <p className="empty-text">{t("rv_empty")}</p>
        ) : (
          <ul className="rv-list" role="listbox" aria-label={t("rv_queue")}>
            {visible.map((s) => {
              const st = stateOf(s);
              const low = s.extraction_confidence < 0.7;
              return (
                <li key={s.study_id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={s.study_id === selectedId}
                    className={`rv-item ${s.study_id === selectedId ? "rv-item-on" : ""}`}
                    onClick={() => {
                      setSelectedId(s.study_id);
                      setEvidenceTab("stat");
                    }}
                    data-testid="rv-item"
                    data-state={st}
                  >
                    <Glyph state={st} />
                    <span className="rv-item-main">
                      <span className="rv-item-title">{s.authors || s.paper_title || s.study_id}</span>
                      <span className="rv-item-sub mono">
                        {s.study_id.slice(0, 8)} · {s.year} · {s.country || "–"}
                      </span>
                    </span>
                    <span className="rv-item-nums mono">
                      <span>{fmtR(s.effect_r)}</span>
                      <span className={low ? "conf-low" : "conf"}>{s.extraction_confidence.toFixed(2)}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        <div className="rv-queue-foot">
          <span className="mono hint-inline">{t("rv_kbd")}</span>
          <div className="rv-nav">
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => move(-1)} disabled={index <= 0}>
              ↑ {t("rv_prev")}
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => move(1)} disabled={index < 0 || index >= visible.length - 1}>
              ↓ {t("rv_next")}
            </button>
            <span className="mono hint-inline">
              {index < 0 ? "–" : index + 1} {t("rv_of")} {visible.length}
            </span>
          </div>
        </div>
      </aside>

      <section className="rv-evidence" data-tour="evidence">
        {!selected ? (
          <p className="empty-text">{t("rv_pick")}</p>
        ) : (
          <>
            <div className="rv-evidence-head">
              <span className="eyebrow">{t("rv_source")}</span>
              <div className="chips">
                <button type="button" className={`chip ${evidenceTab === "stat" ? "chip-on" : ""}`} onClick={() => setEvidenceTab("stat")}>
                  {t("rv_stat")} · {t("rv_page")} {selected.evidence_page ?? "–"}
                </button>
                <button type="button" className={`chip ${evidenceTab === "n" ? "chip-on" : ""}`} onClick={() => setEvidenceTab("n")}>
                  {t("rv_n")} · {t("rv_page")} {selected.n_evidence_page ?? "–"}
                </button>
              </div>
            </div>
            {hasAnyEvidence ? (
              <div className="rv-page">
                <div className="rv-quote-card" data-testid="evidence-card">
                  <span className="eyebrow">
                    {evidenceTab === "stat" ? t("rv_stat") : t("rv_n")} · {t("rv_page")} {quote?.page ?? "–"}
                  </span>
                  {quote?.text ? <p className="rv-quote">“{quote.text}”</p> : <p className="hint-text">{t("rv_no_quote")}</p>}
                  {quote?.reads && (
                    <p className="rv-reads mono">
                      <span className="eyebrow">{t("rv_reads")}</span> {quote.reads}
                    </p>
                  )}
                </div>
                <p className="rv-page-note">{t("rv_no_pdf")}</p>
              </div>
            ) : (
              <div className="rv-noev">
                <strong>{t("rv_no_evidence_title")}</strong>
                <p>{t("rv_no_evidence_body")}</p>
              </div>
            )}
          </>
        )}
      </section>

      <section className="rv-panel">
        {selected ? (
          <VerificationPanel
            ref={panelRef}
            key={selected.study_id}
            study={selected}
            onUpdated={handleUpdated}
            onDeleted={handleDeleted}
          />
        ) : null}
      </section>
    </div>
  );
}
