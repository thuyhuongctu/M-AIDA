/**
 * ExtractionPanel - PDF upload and extraction trigger.
 *
 * Supports both drag-and-drop and click-to-browse file selection.
 * Displays extracted results with confidence-tier colour coding.
 */

import React, { useCallback, useRef, useState } from "react";
import { createJob, fetchStudy, waitForJob } from "../api";
import { DEMO_META, DEMO_PDF_URL, sampleFile } from "../demo";
import { useI18n } from "../i18n";
import { getConfidenceTier, JobStatus, StudyDatabaseEntry } from "../types";

// ---------------------------------------------------------------------------
// Confidence badge
// ---------------------------------------------------------------------------

interface ConfidenceBadgeProps {
  confidence: number;
}

function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const tier = getConfidenceTier(confidence);
  const styles: Record<string, string> = {
    high: "badge-high",
    medium: "badge-medium",
    low: "badge-low",
  };
  const label = (confidence * 100).toFixed(0) + "%";
  return (
    <span className={`badge ${styles[tier]}`} title={`Confidence: ${label}`}>
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Extraction result display
// ---------------------------------------------------------------------------

interface ResultCardProps {
  entry: StudyDatabaseEntry;
}

function ResultCard({ entry }: ResultCardProps) {
  return (
    <div className="result-card" data-testid="result-card">
      <h3 className="result-title">{entry.paper_title || "(untitled)"}</h3>
      <p className="result-meta">
        {entry.authors} · {entry.year} · {entry.country}
      </p>

      <div className="result-grid">
        <div className="result-field">
          <span className="field-label">Effect r</span>
          <span className="field-value">
            {entry.effect_r !== null ? entry.effect_r.toFixed(4) : "-"}
          </span>
        </div>
        <div className="result-field">
          <span className="field-label">N</span>
          <span className="field-value">{entry.sample_n ?? "-"}</span>
        </div>
        <div className="result-field">
          <span className="field-label">t</span>
          <span className="field-value">
            {entry.effect_t !== null ? entry.effect_t.toFixed(3) : "-"}
          </span>
        </div>
        <div className="result-field">
          <span className="field-label">beta</span>
          <span className="field-value">
            {entry.effect_beta !== null ? entry.effect_beta.toFixed(3) : "-"}
          </span>
        </div>
        <div className="result-field">
          <span className="field-label">p-value</span>
          <span className="field-value">
            {entry.p_value !== null ? entry.p_value.toFixed(4) : "-"}
          </span>
        </div>
        <div className="result-field">
          <span className="field-label">DOI measure</span>
          <span className="field-value">{entry.doi_measure ?? "-"}</span>
        </div>
        <div className="result-field">
          <span className="field-label">Performance</span>
          <span className="field-value">{entry.performance_measure ?? "-"}</span>
        </div>
        <div className="result-field">
          <span className="field-label">ICRV regime</span>
          <span className="field-value">{entry.icrv_regime ?? "-"}</span>
        </div>
        <div className="result-field">
          <span className="field-label">DPL phase</span>
          <span className="field-value">{entry.dpl_phase ?? "-"}</span>
        </div>
      </div>

      <div className="result-footer">
        <ConfidenceBadge confidence={entry.extraction_confidence} />
        {entry.requires_verification && (
          <span className="badge badge-warn">Needs PI Review</span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface ExtractionPanelProps {
  onExtracted?: (entry: StudyDatabaseEntry) => void;
  /** True in the multi-user modes: show the credit note and job phases. */
  cloud?: boolean;
  /** 8.0: the in-browser demo; only the synthetic sample paper can be extracted. */
  demo?: boolean;
  credits?: number | null;
  onOpenReview?: (studyId: string) => void;
  /** Called when a job settles with any outcome (credits may have moved). */
  onSettled?: () => void;
}

type StepState = "waiting" | "running" | "passed" | "failed" | "rejected";

/** Map the job's coarse status onto the four pipeline steps shown to the user. */
function pipelineSteps(phase: JobStatus | null, outcome: JobStatus | null): StepState[] {
  if (outcome === "succeeded") return ["passed", "passed", "passed", "passed"];
  if (outcome === "rejected") return ["passed", "passed", "passed", "rejected"];
  if (outcome === "failed") return ["passed", "failed", "waiting", "waiting"];
  if (phase === "queued") return ["passed", "waiting", "waiting", "waiting"];
  if (phase === "running") return ["passed", "running", "running", "waiting"];
  return ["waiting", "waiting", "waiting", "waiting"];
}

export default function ExtractionPanel({ onExtracted, cloud = false, demo = false, credits = null, onOpenReview, onSettled }: ExtractionPanelProps) {
  const { t } = useI18n();
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState<JobStatus | null>(null);
  const [outcome, setOutcome] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<StudyDatabaseEntry | null>(null);

  // Metadata form state
  const [title, setTitle] = useState("");
  const [authors, setAuthors] = useState("");
  const [year, setYear] = useState<number>(new Date().getFullYear());
  const [country, setCountry] = useState("");

  const inputRef = useRef<HTMLInputElement>(null);

  const acceptFile = useCallback((f: File) => {
    if (!f.name.endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }
    setFile(f);
    setError(null);
    setResult(null);
    // Pre-fill title from filename if empty
    setTitle((prev) => prev || f.name.replace(/\.pdf$/i, ""));
  }, []);

  const loadSample = useCallback(async () => {
    try {
      const f = await sampleFile();
      setFile(f);
      setError(null);
      setResult(null);
      setTitle(DEMO_META.title);
      setAuthors(DEMO_META.authors);
      setYear(DEMO_META.year);
      setCountry(DEMO_META.country);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error_generic"));
    }
  }, [t]);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragOver(false);
      const dropped = e.dataTransfer.files[0];
      if (dropped) acceptFile(dropped);
    },
    [acceptFile]
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) acceptFile(selected);
    },
    [acceptFile]
  );

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!file) {
        setError("Please select a PDF file.");
        return;
      }
      setLoading(true);
      setError(null);
      setResult(null);
      setOutcome(null);
      setPhase("queued");
      try {
        // 8.0: one job per upload. The server reserves a credit, runs the
        // model in the background and the browser polls until it settles.
        const job = await createJob(file, { title, authors, year, country });
        const done = await waitForJob(job.id, (j) => setPhase(j.status));
        setOutcome(done.status);
        if (done.status === "succeeded" && done.study_id) {
          const entry = await fetchStudy(done.study_id);
          setResult(entry);
          onExtracted?.(entry);
        } else if (done.status === "rejected") {
          setError(`${t("ex_rejected")} ${done.error_message ?? ""}`.trim());
        } else {
          setError(`${t("ex_failed")} ${done.error_message ?? ""}`.trim());
        }
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : "Extraction failed. Check backend.";
        setError(msg.startsWith("402") ? t("ex_no_credits") : msg);
        setOutcome("failed");
      } finally {
        setLoading(false);
        setPhase(null);
        onSettled?.();
      }
    },
    [file, title, authors, year, country, onExtracted, onSettled, t]
  );

  const steps = pipelineSteps(phase, outcome);
  const stepLabel: Record<StepState, string> = {
    waiting: t("ex_waiting"),
    running: t("ex_running_s"),
    passed: t("ex_passed"),
    failed: t("ex_failed_s"),
    rejected: t("ex_rejected_s"),
  };

  return (
    <div className="extract">
    <div className="extract-form">
      <h2 className="page-title">Extract an effect size</h2>
      <p className="lede">The model proposes; nothing enters the dataset until you verify and lock it.</p>

      {demo && (
        <div className="demo-sample" data-testid="demo-sample-card">
          <div>
            <strong>{t("demo_sample_title")}</strong>
            <p className="hint-text">{t("demo_sample_desc")}</p>
          </div>
          <div className="demo-sample-actions">
            <button type="button" className="btn btn-primary btn-sm" onClick={() => void loadSample()} data-testid="demo-sample">
              {t("demo_sample_use")}
            </button>
            <a className="btn-link" href={DEMO_PDF_URL} target="_blank" rel="noopener noreferrer">
              {t("demo_sample_open")}
            </a>
          </div>
        </div>
      )}

      {/* Drop zone */}
      <div
        className={`drop-zone ${dragOver ? "drag-over" : ""} ${file ? "has-file" : ""}`}
        data-tour="drop"
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        aria-label="Drop PDF here or click to browse"
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />
        {file ? (
          <p className="drop-zone-text file-selected">
            {file.name} ({(file.size / 1024).toFixed(1)} KB)
          </p>
        ) : (
          <p className="drop-zone-text">
            Drop a PDF here, or click to browse
          </p>
        )}
      </div>

      {/* Metadata form */}
      <form className="metadata-form" onSubmit={handleSubmit}>
        <div className="form-row">
          <label className="form-label" htmlFor="ex-title">
            Paper Title
          </label>
          <input
            id="ex-title"
            className="form-input"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Full paper title"
          />
        </div>
        <div className="form-row">
          <label className="form-label" htmlFor="ex-authors">
            Authors
          </label>
          <input
            id="ex-authors"
            className="form-input"
            type="text"
            value={authors}
            onChange={(e) => setAuthors(e.target.value)}
            placeholder="Last, F. M.; Last2, F."
          />
        </div>
        <div className="form-row two-col">
          <div>
            <label className="form-label" htmlFor="ex-year">
              Year
            </label>
            <input
              id="ex-year"
              className="form-input"
              type="number"
              min={1990}
              max={2030}
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
            />
          </div>
          <div>
            <label className="form-label" htmlFor="ex-country">
              Country / Region
            </label>
            <input
              id="ex-country"
              className="form-input"
              type="text"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              placeholder="e.g. China, ASEAN"
            />
          </div>
        </div>

        {error && <p className="error-message" data-testid="extract-error">{error}</p>}

        <div className="extract-run">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading || !file || (cloud && credits !== null && credits < 1)}
            data-testid="extract-submit"
          >
            {loading ? "Extracting…" : "Run extraction"}
          </button>
          {cloud && credits !== null && (
            <span className="hint-inline">
              <span className="glyph glyph-locked" aria-hidden="true">◆</span> uses 1 {t("credit_one")} · {credits} left
            </span>
          )}
        </div>
        {loading && phase && (
          <p className="hint-text job-phase" data-testid="job-phase">
            {phase === "queued" ? t("ex_queued") : t("ex_running")}
          </p>
        )}
        {cloud && <p className="hint-text">{t("ex_cost_note")}</p>}
        <p className="hint-text mono">{t("ex_limits")}: 25 MB · 80 pages · 1 running job · 10 jobs per hour</p>
      </form>
    </div>

    <aside className="extract-pipeline" data-tour="pipeline">
      <span className="eyebrow">{t("ex_pipeline")}</span>
      <ol className="pipeline">
        {([["ex_s1", "ex_s1d"], ["ex_s2", "ex_s2d"], ["ex_s3", "ex_s3d"], ["ex_s4", "ex_s4d"]] as const).map(([k, d], i) => (
          <li key={k} className={`step step-${steps[i]}`} data-testid={`step-${i + 1}`} data-state={steps[i]}>
            <span className="step-n mono">0{i + 1}</span>
            <span className="step-body">
              <span className="step-title">{t(k)}</span>
              <span className="step-detail">{t(d)}</span>
            </span>
            <span className="step-state mono">{stepLabel[steps[i]]}</span>
          </li>
        ))}
      </ol>

      {result && (
        <div className="extract-result" data-testid="result-wrap">
          <ResultCard entry={result} />
          <p className="hint-text">{t("ex_mods_blank")}</p>
          {onOpenReview && (
            <button type="button" className="btn btn-link" onClick={() => onOpenReview(result.study_id)}>
              {t("ex_open_review")} →
            </button>
          )}
        </div>
      )}
    </aside>
    </div>
  );
}
