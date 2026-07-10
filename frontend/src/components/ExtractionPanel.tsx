/**
 * ExtractionPanel - PDF upload and extraction trigger.
 *
 * Supports both drag-and-drop and click-to-browse file selection.
 * Displays extracted results with confidence-tier colour coding.
 */

import React, { useCallback, useRef, useState } from "react";
import { uploadPdf } from "../api";
import { getConfidenceTier, StudyDatabaseEntry } from "../types";

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
    <div className="result-card">
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
}

export default function ExtractionPanel({ onExtracted }: ExtractionPanelProps) {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
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
      try {
        const entry = await uploadPdf(file, { title, authors, year, country });
        setResult(entry);
        onExtracted?.(entry);
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : "Extraction failed. Check backend.";
        setError(msg);
      } finally {
        setLoading(false);
      }
    },
    [file, title, authors, year, country, onExtracted]
  );

  return (
    <div className="panel extraction-panel">
      <h2 className="panel-title">Extract Effect Size from PDF</h2>

      {/* Drop zone */}
      <div
        className={`drop-zone ${dragOver ? "drag-over" : ""} ${file ? "has-file" : ""}`}
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

        {error && <p className="error-message">{error}</p>}

        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading || !file}
        >
          {loading ? "Extracting…" : "Extract Effect Size"}
        </button>
      </form>

      {/* Result */}
      {result && <ResultCard entry={result} />}
    </div>
  );
}
