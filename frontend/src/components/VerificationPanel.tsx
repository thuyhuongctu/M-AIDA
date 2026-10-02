/**
 * VerificationPanel - per-record review and PI decision (8.0 layout).
 *
 * Columns: Field · Machine · Current. The Machine column is the model's
 * immutable proposal (machine_proposal); Current is what the record holds,
 * editable until the record is locked. Moderators (ICRV, DPL, DOI,
 * performance) are chip groups because they are PI-assigned codes, not
 * extracted values. Derived quantities are read-only: the backend recomputes
 * them on every override (7.2.0, findings A1–A3).
 *
 * Decisions: Approve (PATCH /verify with pi_approved=true and the overrides;
 * notes required), Lock… (POST /lock after typing the study id; irreversible),
 * Flag for re-extraction (PATCH with pi_approved=false). Only the 7.2.0
 * whitelist of fields is ever sent as overrides.
 */

import React, { forwardRef, useCallback, useImperativeHandle, useRef, useState } from "react";
import { deleteStudy, lockStudy, verifyStudy } from "../api";
import { useI18n } from "../i18n";
import type { ExtractedEffect, StudyDatabaseEntry } from "../types";

const PI_EDITABLE_FIELDS: ReadonlySet<keyof ExtractedEffect> = new Set<keyof ExtractedEffect>([
  "effect_r", "effect_t", "effect_df", "effect_beta", "n_predictors", "sample_n",
  "sample_start", "sample_end", "p_value", "ci_lower", "ci_upper",
  "doi_measure", "performance_measure", "icrv_regime", "dpl_phase", "cdai_score",
  "country", "year", "paper_title", "authors",
]);

const STAT_ROWS: { key: keyof ExtractedEffect; label: string; step?: string }[] = [
  { key: "effect_r", label: "Pearson r", step: "0.001" },
  { key: "effect_t", label: "t", step: "0.01" },
  { key: "effect_beta", label: "β", step: "0.001" },
  { key: "effect_df", label: "df", step: "1" },
  { key: "n_predictors", label: "p (predictors)", step: "1" },
  { key: "sample_n", label: "N", step: "1" },
  { key: "p_value", label: "p-value", step: "0.001" },
  { key: "ci_lower", label: "CI lower", step: "0.001" },
  { key: "ci_upper", label: "CI upper", step: "0.001" },
  { key: "sample_start", label: "Sample start", step: "1" },
  { key: "sample_end", label: "Sample end", step: "1" },
];

const MOD_GROUPS: { key: keyof ExtractedEffect; label: string; options: string[] }[] = [
  { key: "icrv_regime", label: "ICRV", options: ["I", "II", "III", "FR", "MX"] },
  { key: "dpl_phase", label: "DPL", options: ["PRE", "SPN", "FOL"] },
  { key: "doi_measure", label: "DOI", options: ["FSTS", "GEO", "EXP", "FDI", "COMP", "OTH"] },
  { key: "performance_measure", label: "Performance", options: ["ACC", "MKT", "LAB", "MIX"] },
];

function fmt(v: unknown, digits = 6): string {
  if (v === null || v === undefined) return "–";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(digits);
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "–";
  return String(v);
}

function fmtWhen(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export interface VerificationPanelHandle {
  approve: () => void;
  openLock: () => void;
}

interface VerificationPanelProps {
  study: StudyDatabaseEntry;
  onUpdated: (updated: StudyDatabaseEntry) => void;
  onDeleted?: (studyId: string) => void;
}

const VerificationPanel = forwardRef<VerificationPanelHandle, VerificationPanelProps>(function VerificationPanel(
  { study, onUpdated, onDeleted },
  ref
) {
  const { t } = useI18n();
  const [overrides, setOverrides] = useState<Partial<ExtractedEffect>>({});
  const [piNotes, setPiNotes] = useState(study.pi_notes ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [lockText, setLockText] = useState("");
  const [deleteArmed, setDeleteArmed] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);

  const locked = study.pi_locked;
  const approved = !!study.pi_approved_at && !locked;
  const machine = (study.machine_proposal ?? {}) as Record<string, unknown>;

  const current = useCallback(
    (key: keyof ExtractedEffect): unknown => (overrides[key] !== undefined ? overrides[key] : study[key]),
    [overrides, study]
  );

  const setOverride = useCallback((key: keyof ExtractedEffect, value: unknown) => {
    setOverrides((prev) => ({ ...prev, [key]: value }));
  }, []);

  const collectOverrides = useCallback((): Partial<ExtractedEffect> => {
    const out: Partial<ExtractedEffect> = {};
    for (const [k, v] of Object.entries(overrides)) {
      if (v !== undefined && PI_EDITABLE_FIELDS.has(k as keyof ExtractedEffect)) {
        (out as Record<string, unknown>)[k] = v;
      }
    }
    return out;
  }, [overrides]);

  const approve = useCallback(async () => {
    if (locked || busy) return;
    if (piNotes.trim().length < 3) {
      setError(t("rv_notes_req"));
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await verifyStudy(study.study_id, {
        study_id: study.study_id,
        field_overrides: collectOverrides(),
        pi_approved: true,
        pi_notes: piNotes,
      });
      setOverrides({});
      onUpdated(updated);
      setNotice(t("rv_approved_msg"));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error_generic"));
    } finally {
      setBusy(false);
    }
  }, [locked, busy, piNotes, study.study_id, collectOverrides, onUpdated, t]);

  const flag = useCallback(async () => {
    if (locked || busy) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await verifyStudy(study.study_id, {
        study_id: study.study_id,
        field_overrides: {},
        pi_approved: false,
        pi_notes: `[Flagged for re-extraction] ${piNotes}`.trim(),
      });
      onUpdated(updated);
      setNotice(t("rv_flagged"));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error_generic"));
    } finally {
      setBusy(false);
    }
  }, [locked, busy, piNotes, study.study_id, onUpdated, t]);

  const openLock = useCallback(() => {
    if (locked || !approved || busy) return;
    setLockText("");
    dialogRef.current?.showModal();
  }, [locked, approved, busy]);

  const confirmLock = useCallback(async () => {
    if (lockText.trim() !== study.study_id) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await lockStudy(study.study_id);
      dialogRef.current?.close();
      onUpdated(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error_generic"));
      dialogRef.current?.close();
    } finally {
      setBusy(false);
    }
  }, [lockText, study.study_id, onUpdated, t]);

  const remove = useCallback(async () => {
    if (locked || busy) return;
    if (!deleteArmed) {
      setDeleteArmed(true);
      return;
    }
    setBusy(true);
    try {
      await deleteStudy(study.study_id);
      onDeleted?.(study.study_id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error_generic"));
    } finally {
      setBusy(false);
      setDeleteArmed(false);
    }
  }, [locked, busy, deleteArmed, study.study_id, onDeleted, t]);

  useImperativeHandle(ref, () => ({ approve: () => void approve(), openLock }), [approve, openLock]);

  const years =
    study.sample_start || study.sample_end ? `${study.sample_start ?? "?"}–${study.sample_end ?? "?"}` : "";
  const lowConf = study.extraction_confidence < 0.7 && !locked;
  const noR = study.effect_r === null;

  return (
    <div className="vp" data-testid="verification-panel">
      <div className="vp-head">
        <span className="eyebrow mono">
          {study.study_id.slice(0, 8)} · {study.country || "–"}
          {years ? ` · ${years}` : ""}
        </span>
        <h2 className="vp-title">{study.paper_title || "(untitled)"}</h2>
        <p className="vp-authors">
          {study.authors} ({study.year})
        </p>
      </div>

      {locked && (
        <div className="note note-locked" data-testid="locked-banner">
          <strong>{t("rv_locked_on")}</strong> · {fmtWhen(study.locked_at)} · {t("rv_read_only")}
        </div>
      )}
      {lowConf && <div className="note note-warn">{t("rv_low_conf")}</div>}
      {noR && <div className="note note-warn">{t("rv_needs_r")}</div>}

      <h3 className="eyebrow">{t("rv_statistics")}</h3>
      <table className="vp-table" data-tour="stats">
        <thead>
          <tr>
            <th>{t("rv_field")}</th>
            <th>{t("rv_machine")}</th>
            <th>{t("rv_current")}</th>
          </tr>
        </thead>
        <tbody>
          {STAT_ROWS.map(({ key, label, step }) => {
            const value = current(key);
            const dirty = overrides[key] !== undefined && overrides[key] !== study[key];
            const machineValue = key in machine ? machine[key] : study[key];
            return (
              <tr key={key} className={dirty ? "dirty" : ""}>
                <td className="vp-field">{label}</td>
                <td className="mono vp-machine">{fmt(machineValue, 4)}</td>
                <td>
                  <input
                    className="vp-input mono"
                    type="number"
                    step={step ?? "any"}
                    value={value === null || value === undefined ? "" : String(value)}
                    disabled={locked}
                    aria-label={label}
                    onChange={(e) => setOverride(key, e.target.value === "" ? null : Number(e.target.value))}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <h3 className="eyebrow">{t("rv_moderators")}</h3>
      <div className="vp-mods" data-tour="mods">
        {MOD_GROUPS.map(({ key, label, options }) => {
          const value = current(key);
          return (
            <div className="vp-mod-row" key={key}>
              <span className="vp-field">{label}</span>
              <div className="chips">
                {options.map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    className={`chip mono ${value === opt ? "chip-on" : ""}`}
                    disabled={locked}
                    onClick={() => setOverride(key, value === opt ? null : opt)}
                    aria-pressed={value === opt}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
        <div className="vp-mod-row">
          <span className="vp-field">cDAI</span>
          <input
            className="vp-input mono vp-input-short"
            type="number"
            step="0.01"
            min={0}
            max={1}
            value={current("cdai_score") === null || current("cdai_score") === undefined ? "" : String(current("cdai_score"))}
            disabled={locked}
            aria-label="cDAI"
            onChange={(e) => setOverride("cdai_score", e.target.value === "" ? null : Number(e.target.value))}
          />
        </div>
      </div>

      <h3 className="eyebrow">{t("rv_derived")}</h3>
      <dl className="vp-derived mono">
        <dt>metric_type</dt><dd>{fmt(study.metric_type)}</dd>
        <dt>estimand_source</dt><dd>{fmt(study.estimand_source)}</dd>
        <dt>r_source</dt><dd>{fmt(study.r_source)}</dd>
        <dt>df_source</dt><dd>{fmt(study.df_source)}{study.df_imputed ? " (imputed)" : ""}</dd>
        <dt>variance_r</dt><dd>{fmt(study.variance_r)}</dd>
        <dt>variance_z</dt><dd>{fmt(study.variance_z)}</dd>
        <dt>formula</dt><dd>{fmt(study.variance_formula)}</dd>
        <dt>source_controls</dt><dd>{fmt(study.source_controls)}</dd>
        <dt>lambda_applied</dt><dd>{fmt(study.lambda_applied)}</dd>
        <dt>beta_outside_pb</dt><dd>{fmt(study.beta_outside_pb_domain)}</dd>
      </dl>

      <h3 className="eyebrow">{t("rv_evidence_meta")}</h3>
      <dl className="vp-derived mono">
        <dt>confidence</dt><dd>{study.extraction_confidence.toFixed(2)}</dd>
        <dt>requires_verification</dt><dd>{fmt(study.requires_verification)}</dd>
        {study.text_truncated && (<><dt>text_truncated</dt><dd className="text-warning">{t("rv_truncated")}</dd></>)}
        {study.pi_edited_fields.length > 0 && (<><dt>{t("rv_pi_edits")}</dt><dd>{study.pi_edited_fields.join(", ")}{study.pi_override_at ? ` · ${fmtWhen(study.pi_override_at)}` : ""}</dd></>)}
      </dl>

      <div className="vp-notes">
        <label className="eyebrow" htmlFor="vp-notes">
          {t("rv_notes")} {!locked && <span className="vp-req">· {t("rv_notes_req")}</span>}
        </label>
        <textarea
          id="vp-notes"
          className="vp-textarea"
          value={piNotes}
          onChange={(e) => setPiNotes(e.target.value)}
          placeholder={t("rv_notes_ph")}
          rows={3}
          disabled={locked}
          data-testid="vp-notes"
        />
      </div>

      {error && <p className="error-message" data-testid="vp-error">{error}</p>}
      {notice && <p className="success-message">{notice}</p>}

      {!locked && (
        <div className="vp-actions" data-tour="actions">
          <span className="vp-actions-right">
            <button type="button" className="btn btn-primary" onClick={() => void approve()} disabled={busy} data-testid="vp-approve">
              {busy ? t("rv_saving") : approved ? `${t("rv_approved_msg")} ✓` : t("rv_approve")}
            </button>
            <button type="button" className="btn btn-accent" onClick={openLock} disabled={busy || !approved} data-testid="vp-lock">
              {t("rv_lock")}
            </button>
          </span>
          <span className="vp-actions-secondary">
            <button type="button" className="btn btn-link btn-danger-text" onClick={flag} disabled={busy}>
              {t("rv_flag")}
            </button>
            <button type="button" className="btn btn-link" onClick={remove} disabled={busy} data-testid="vp-delete">
              {deleteArmed ? `${t("rv_delete")}?` : t("rv_delete")}
            </button>
          </span>
        </div>
      )}

      <dialog ref={dialogRef} className="vp-dialog" data-testid="lock-dialog">
        <form
          method="dialog"
          onSubmit={(e) => {
            e.preventDefault();
            void confirmLock();
          }}
        >
          <h3>{t("rv_confirm_title")}</h3>
          <p>{t("rv_confirm_body")}</p>
          <label htmlFor="vp-lock-id">
            {t("rv_confirm_type")} <code>{study.study_id}</code>
          </label>
          <input
            id="vp-lock-id"
            className="vp-input mono"
            value={lockText}
            onChange={(e) => setLockText(e.target.value)}
            autoComplete="off"
            spellCheck={false}
            data-testid="lock-id-input"
          />
          <div className="vp-dialog-btns">
            <button type="button" className="btn btn-ghost" onClick={() => dialogRef.current?.close()}>
              {t("rv_cancel")}
            </button>
            <button type="submit" className="btn btn-accent" disabled={lockText.trim() !== study.study_id || busy} data-testid="lock-confirm">
              {t("rv_confirm_lock")}
            </button>
          </div>
        </form>
      </dialog>
    </div>
  );
});

export default VerificationPanel;
