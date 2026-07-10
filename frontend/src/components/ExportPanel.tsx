/**
 * ExportPanel - summary counts, CSV export, and Notion sync controls.
 */

import React, { useCallback, useEffect, useState } from "react";
import { downloadCsv, fetchStudies, syncToNotion } from "../api";
import { NotionSyncResponse, StudyDatabaseEntry } from "../types";

interface StudySummary {
  total: number;
  verified: number;
  locked: number;
}

export default function ExportPanel() {
  const [summary, setSummary] = useState<StudySummary>({
    total: 0,
    verified: 0,
    locked: 0,
  });
  const [loadingStats, setLoadingStats] = useState(false);
  const [csvLoading, setCsvLoading] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncResult, setSyncResult] = useState<NotionSyncResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshSummary = useCallback(async () => {
    setLoadingStats(true);
    setError(null);
    try {
      const all: StudyDatabaseEntry[] = await fetchStudies({});
      const verified = all.filter((s) => !s.requires_verification).length;
      const locked = all.filter((s) => s.pi_locked).length;
      setSummary({ total: all.length, verified, locked });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load summary.");
    } finally {
      setLoadingStats(false);
    }
  }, []);

  useEffect(() => {
    void refreshSummary();
  }, [refreshSummary]);

  const handleCsvExport = useCallback(async () => {
    setCsvLoading(true);
    setError(null);
    try {
      await downloadCsv();
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "CSV export failed. Are any studies locked?"
      );
    } finally {
      setCsvLoading(false);
    }
  }, []);

  const handleNotionSync = useCallback(async () => {
    setSyncLoading(true);
    setError(null);
    setSyncResult(null);
    try {
      const result = await syncToNotion();
      setSyncResult(result);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Notion sync failed. Check NOTION_TOKEN."
      );
    } finally {
      setSyncLoading(false);
    }
  }, []);

  return (
    <div className="panel export-panel">
      <h2 className="panel-title">Export & Sync</h2>

      {/* Summary cards */}
      <div className="summary-grid">
        <div className="summary-card">
          <span className="summary-number">
            {loadingStats ? "…" : summary.total}
          </span>
          <span className="summary-label">Total Studies</span>
        </div>
        <div className="summary-card summary-card-verified">
          <span className="summary-number">
            {loadingStats ? "…" : summary.verified}
          </span>
          <span className="summary-label">Verified</span>
        </div>
        <div className="summary-card summary-card-locked">
          <span className="summary-number">
            {loadingStats ? "…" : summary.locked}
          </span>
          <span className="summary-label">Locked</span>
        </div>
      </div>

      <button
        className="btn btn-ghost btn-sm"
        onClick={() => void refreshSummary()}
        disabled={loadingStats}
      >
        Refresh counts
      </button>

      {/* Export actions */}
      <div className="export-actions">
        <div className="export-card">
          <h3 className="export-card-title">CSV Export</h3>
          <p className="export-card-desc">
            Downloads all PI-locked studies as a comma-separated file suitable
            for import into R (metafor) or Stata.
          </p>
          <button
            className="btn btn-primary"
            onClick={handleCsvExport}
            disabled={csvLoading || summary.locked === 0}
          >
            {csvLoading ? "Preparing…" : "Export to CSV"}
          </button>
          {summary.locked === 0 && (
            <p className="hint-text">No locked studies yet.</p>
          )}
        </div>

        <div className="export-card">
          <h3 className="export-card-title">Notion Sync</h3>
          <p className="export-card-desc">
            Pushes all locked studies to the configured Notion database.
            Requires NOTION_TOKEN and NOTION_DATABASE_ID in the backend .env.
          </p>
          <button
            className="btn btn-secondary"
            onClick={handleNotionSync}
            disabled={syncLoading || summary.locked === 0}
          >
            {syncLoading ? "Syncing…" : "Sync to Notion"}
          </button>

          {syncResult && (
            <div
              className={`alert ${syncResult.failed === 0 ? "alert-success" : "alert-warn"}`}
            >
              <p>{syncResult.message}</p>
              {syncResult.errors.length > 0 && (
                <ul className="error-list">
                  {syncResult.errors.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>

      {error && <p className="error-message">{error}</p>}
    </div>
  );
}
