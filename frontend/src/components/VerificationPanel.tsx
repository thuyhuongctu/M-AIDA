/**
 * VerificationPanel - detailed per-study review and PI decision form.
 *
 * Allows the PI to inspect each extracted field, override incorrect values,
 * add notes, then either approve+lock the record or flag it for re-extraction.
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
      const verified = await verifyStudy(study.study_id, {
        study_id: study.study_id,
        field_overrides: overrides,
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
