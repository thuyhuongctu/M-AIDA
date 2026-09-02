/**
 * VerificationPanel - detailed per-study review and PI decision form.
 *
 * Allows the PI to inspect each extracted field, override incorrect values,
 * add notes, then either approve+lock the record or flag it for re-extraction.
 *
 * 7.2.1: the panel now shows what the server derives from the primary
 * statistics (metric type, variance, formula, λ, provenance) and the machine's
 * own evidence (confidence, quotes, truncation), so the PI can see why a
 * record is or is not lockable. Only the 7.2.0 whitelist of fields is sent as
 * overrides; derived fields are read-only here because the backend recomputes
 * them on every override (findings A1–A3 of the 31/08/2026 review).
 */

import React, { useCallback, useState } from "react";
import { lockStudy, verifyStudy } from "../api";
import {
  DoiMeasure,
  DplPhase,
  ExtractedEffect,
  IcrvRegime,
  PerformanceMeasure,
  StudyDatabaseEntry,
} from "../types";

// Fields the backend accepts in `field_overrides` (PI_EDITABLE_FIELDS, 7.2.0).
// Anything else is rejected with 422, so the panel never sends it.
const PI_EDITABLE_FIELDS: ReadonlySet<keyof ExtractedEffect> = new Set<keyof ExtractedEffect>([
  "effect_r", "effect_t", "effect_df", "effect_beta", "n_predictors", "sample_n",
  "sample_start", "sample_end", "p_value", "ci_lower", "ci_upper",
  "doi_measure", "performance_measure", "icrv_regime", "dpl_phase", "cdai_score",
  "country", "year", "paper_title", "authors",
]);

function fmt(v: unknown, digits = 6): string {
  if (v === null || v === undefined) return "-";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(digits);
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "-";
  return String(v);
}

// ---------------------------------------------------------------------------
// Editable field row
// ---------------------------------------------------------------------------

interface FieldRowProps {
  label: string;
  fieldKey: keyof ExtractedEffect;
  original: unknown;
  override: unknown;
  onOverride: (key: keyof ExtractedEffect, value: unknown) => void;
  inputType?: "text" | "number" | "select";
  selectOptions?: string[];
}

function FieldRow({
  label,
  fieldKey,
  original,
  override,
  onOverride,
  inputType = "text",
  selectOptions,
}: FieldRowProps) {
  const display = override !== undefined ? override : original;
  const isDirty = override !== undefined && override !== original;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const raw = e.target.value;
    const coerced =
      inputType === "number" && raw !== "" ? Number(raw) : raw === "" ? null : raw;
    onOverride(fieldKey, coerced);
  };

  return (
    <tr className={`field-row ${isDirty ? "dirty" : ""}`}>
      <td className="field-label">{label}</td>
      <td className="field-original">
        {original !== null && original !== undefined ? String(original) : "-"}
      </td>
      <td className="field-override">
        {inputType === "select" && selectOptions ? (
          <select
            className="form-input form-input-sm"
            value={String(display ?? "")}
            onChange={handleChange}
          >
            <option value="">-</option>
            {selectOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        ) : (
          <input
            className="form-input form-input-sm"
            type={inputType}
            value={display !== null && display !== undefined ? String(display) : ""}
            onChange={handleChange}
            step={inputType === "number" ? "any" : undefined}
          />
        )}
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface VerificationPanelProps {
  study: StudyDatabaseEntry;
  onClose: () => void;
  onUpdated: (updated: StudyDatabaseEntry) => void;
}

export default function VerificationPanel({
  study,
  onClose,
  onUpdated,
}: VerificationPanelProps) {
  const [overrides, setOverrides] = useState<Partial<ExtractedEffect>>({});
  const [piNotes, setPiNotes] = useState(study.pi_notes ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flagged, setFlagged] = useState(false);

  const setOverride = useCallback(
    (key: keyof ExtractedEffect, value: unknown) => {
      setOverrides((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const handleApproveAndLock = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Step 1: apply overrides + approval
      const fieldOverrides: Partial<ExtractedEffect> = {};
      for (const [k, v] of Object.entries(overrides)) {
        if (v !== undefined && PI_EDITABLE_FIELDS.has(k as keyof ExtractedEffect)) {
          (fieldOverrides as Record<string, unknown>)[k] = v;
        }
      }
      const verified = await verifyStudy(study.study_id, {
        study_id: study.study_id,
        field_overrides: fieldOverrides,
        pi_approved: true,
        pi_notes: piNotes,
      });
      // Step 2: permanent lock
      const locked = await lockStudy(verified.study_id);
      onUpdated(locked);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Operation failed.");
    } finally {
      setLoading(false);
    }
  }, [study.study_id, overrides, piNotes, onUpdated, onClose]);

  const handleFlag = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const updated = await verifyStudy(study.study_id, {
        study_id: study.study_id,
        field_overrides: {},
        pi_approved: false,
        pi_notes: `[Flagged for re-extraction] ${piNotes}`.trim(),
      });
      setFlagged(true);
      onUpdated(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Flag operation failed.");
    } finally {
      setLoading(false);
    }
  }, [study.study_id, piNotes, onUpdated]);

  if (flagged) {
    return (
      <div className="panel verification-panel">
        <p className="success-message">
          Study flagged for re-extraction. Close this panel to continue.
        </p>
        <button className="btn btn-secondary" onClick={onClose}>
          Close
        </button>
      </div>
    );
  }

  return (
    <div className="panel verification-panel">
      <div className="panel-header">
        <h2 className="panel-title">PI Verification</h2>
        <button className="btn-icon" onClick={onClose} aria-label="Close panel">
          ✕
        </button>
      </div>

      <p className="study-subtitle">
        <strong>{study.paper_title}</strong> - {study.authors} ({study.year})
      </p>

      {study.pi_locked && (
        <div className="alert alert-success">
          This study is permanently locked. Read-only view.
        </div>
      )}

      <table className="field-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>Extracted</th>
            <th>Override</th>
          </tr>
        </thead>
        <tbody>
          <FieldRow
            label="Effect r"
            fieldKey="effect_r"
            original={study.effect_r}
            override={overrides.effect_r}
            onOverride={setOverride}
            inputType="number"
          />
          <FieldRow
            label="t-statistic"
            fieldKey="effect_t"
            original={study.effect_t}
            override={overrides.effect_t}
            onOverride={setOverride}
            inputType="number"
          />
          <FieldRow
            label="Beta (β)"
            fieldKey="effect_beta"
            original={study.effect_beta}
            override={overrides.effect_beta}
            onOverride={setOverride}
            inputType="number"
          />
          <FieldRow
            label="df"
            fieldKey="effect_df"
            original={study.effect_df}
            override={overrides.effect_df}
            onOverride={setOverride}
            inputType="number"
          />
          <FieldRow
            label="Predictors p (for t/β from a regression; df = n − p − 1)"
            fieldKey="n_predictors"
            original={study.n_predictors}
            override={overrides.n_predictors}
            onOverride={setOverride}
            inputType="number"
          />
          <FieldRow
            label="N (sample size)"
            fieldKey="sample_n"
            original={study.sample_n}
            override={overrides.sample_n}
            onOverride={setOverride}
            inputType="number"
          />
          <FieldRow
            label="p-value"
            fieldKey="p_value"
            original={study.p_value}
            override={overrides.p_value}
            onOverride={setOverride}
            inputType="number"
          />
          <FieldRow
            label="CI lower"
            fieldKey="ci_lower"
            original={study.ci_lower}
            override={overrides.ci_lower}
            onOverride={setOverride}
            inputType="number"
          />
          <FieldRow
            label="CI upper"
            fieldKey="ci_upper"
            original={study.ci_upper}
            override={overrides.ci_upper}
            onOverride={setOverride}
            inputType="number"
          />
          <FieldRow
            label="DOI measure"
            fieldKey="doi_measure"
            original={study.doi_measure}
            override={overrides.doi_measure}
            onOverride={setOverride}
            inputType="select"
            selectOptions={["FSTS", "GEO", "EXP", "FDI", "COMP", "OTH"] satisfies DoiMeasure[]}
          />
          <FieldRow
            label="Performance measure"
            fieldKey="performance_measure"
            original={study.performance_measure}
            override={overrides.performance_measure}
            onOverride={setOverride}
            inputType="select"
            selectOptions={["ACC", "MKT", "LAB", "MIX"] satisfies PerformanceMeasure[]}
          />
          <FieldRow
            label="ICRV regime (PI-assigned: WGI lookup)"
            fieldKey="icrv_regime"
            original={study.icrv_regime}
            override={overrides.icrv_regime}
            onOverride={setOverride}
            inputType="select"
            selectOptions={["I", "II", "III", "FR", "MX"] satisfies IcrvRegime[]}
          />
          <FieldRow
            label="DPL phase (PI-derived: median year)"
            fieldKey="dpl_phase"
            original={study.dpl_phase}
            override={overrides.dpl_phase}
            onOverride={setOverride}
            inputType="select"
            selectOptions={["PRE", "SPN", "FOL"] satisfies DplPhase[]}
          />
          <FieldRow
            label="cDAI 0-1 (PI-assigned: WB DAI/ITU DDI)"
            fieldKey="cdai_score"
            original={study.cdai_score}
            override={overrides.cdai_score}
            onOverride={setOverride}
            inputType="number"
          />
        </tbody>
      </table>

      {/* Derived by the server (7.2.0): recomputed on every override, read-only here */}
      <h3 className="panel-subtitle">Derived by the server (recomputed after each override)</h3>
      {study.effect_r === null && (
        <div className="alert alert-warning">
          This record has no effect size
          {study.beta_outside_pb_domain ? " (β outside the Peterson–Brown domain |β| ≤ 0.5)" : ""}
          , so it cannot be locked. Correct the primary statistic or flag it for re-extraction.
        </div>
      )}
      <table className="field-table derived-table">
        <tbody>
          <tr><td className="field-label">Metric type</td><td>{fmt(study.metric_type)}</td>
              <td className="field-label">Estimand source</td><td>{fmt(study.estimand_source)}</td></tr>
          <tr><td className="field-label">r source</td><td>{fmt(study.r_source)}</td>
              <td className="field-label">df source</td><td>{fmt(study.df_source)}{study.df_imputed ? " (imputed)" : ""}</td></tr>
          <tr><td className="field-label">Variance of r</td><td>{fmt(study.variance_r)}</td>
              <td className="field-label">Formula</td><td><code>{fmt(study.variance_formula)}</code></td></tr>
          <tr><td className="field-label">Variance of z</td><td>{fmt(study.variance_z)}</td>
              <td className="field-label">Source controls</td><td>{fmt(study.source_controls)}</td></tr>
          <tr><td className="field-label">λ term applied (β ≥ 0)</td><td>{fmt(study.lambda_applied)}</td>
              <td className="field-label">β outside P&amp;B domain</td><td>{fmt(study.beta_outside_pb_domain)}</td></tr>
        </tbody>
      </table>

      {/* Machine evidence: immutable, never overridable */}
      <h3 className="panel-subtitle">Machine proposal (immutable)</h3>
      <table className="field-table derived-table">
        <tbody>
          <tr><td className="field-label">Extraction confidence</td><td>{fmt(study.extraction_confidence, 3)}</td>
              <td className="field-label">Requires verification</td><td>{fmt(study.requires_verification)}</td></tr>
          <tr><td className="field-label">Evidence (effect)</td>
              <td colSpan={3}>{study.evidence_quote ? `“${study.evidence_quote}”` : "-"}{study.evidence_page !== null ? ` (p. ${study.evidence_page})` : ""}</td></tr>
          <tr><td className="field-label">Evidence (N)</td>
              <td colSpan={3}>{study.n_evidence_quote ? `“${study.n_evidence_quote}”` : "-"}{study.n_evidence_page !== null ? ` (p. ${study.n_evidence_page})` : ""}</td></tr>
          {study.text_truncated && (
            <tr><td className="field-label">PDF text</td>
                <td colSpan={3} className="text-warning">Truncated before extraction (PDF_TEXT_LIMIT) — statistics reported after the cut were not seen by the model.</td></tr>
          )}
          {study.pi_edited_fields.length > 0 && (
            <tr><td className="field-label">PI edits</td>
                <td colSpan={3}>{study.pi_edited_fields.join(", ")}{study.pi_override_at ? ` · ${study.pi_override_at}` : ""}</td></tr>
          )}
        </tbody>
      </table>

      {/* PI notes */}
      <div className="form-row" style={{ marginTop: "1rem" }}>
        <label className="form-label" htmlFor="vp-notes">
          PI Notes
        </label>
        <textarea
          id="vp-notes"
          className="form-input form-textarea"
          value={piNotes}
          onChange={(e) => setPiNotes(e.target.value)}
          placeholder="Add notes about decisions, ambiguities, or exclusion rationale…"
          rows={4}
          disabled={study.pi_locked}
        />
      </div>

      {error && <p className="error-message">{error}</p>}

      {!study.pi_locked && (
        <div className="action-row">
          <button
            className="btn btn-danger"
            onClick={handleFlag}
            disabled={loading}
          >
            Flag for Re-extraction
          </button>
          <button
            className="btn btn-primary"
            onClick={handleApproveAndLock}
            disabled={loading}
          >
            {loading ? "Saving…" : "Approve & Lock"}
          </button>
        </div>
      )}
    </div>
  );
}
