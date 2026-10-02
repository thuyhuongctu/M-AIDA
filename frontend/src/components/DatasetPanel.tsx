/**
 * DatasetPanel - the caller's dataset at a glance, CSV export and Notion sync.
 *
 * Counts come from the study list (owner-filtered by the backend). Only
 * locked records leave the system: the CSV and the Notion sync both read
 * pi_locked records only, so the export is the final, quality-controlled set.
 * A forest-plot preview of the locked effects is planned for phase 2.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { downloadCsv, fetchStudies, syncToNotion } from "../api";
import { useI18n } from "../i18n";
import type { NotionSyncResponse, StudyDatabaseEntry } from "../types";
import { Glyph, stateOf } from "./ReviewScreen";

export default function DatasetPanel({ refreshKey }: { refreshKey: number }) {
  const { t } = useI18n();
  const [studies, setStudies] = useState<StudyDatabaseEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [csvLoading, setCsvLoading] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncResult, setSyncResult] = useState<NotionSyncResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStudies(await fetchStudies({}));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error_generic"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  const counts = useMemo(() => {
    const c = { all: studies.length, pending: 0, approved: 0, locked: 0 };
    for (const s of studies) c[stateOf(s)] += 1;
    return c;
  }, [studies]);

  const exportCsv = useCallback(async () => {
    setCsvLoading(true);
    setError(null);
    try {
      await downloadCsv();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error_generic"));
    } finally {
      setCsvLoading(false);
    }
  }, [t]);

  const sync = useCallback(async () => {
    setSyncLoading(true);
    setError(null);
    setSyncResult(null);
    try {
      setSyncResult(await syncToNotion());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error_generic"));
    } finally {
      setSyncLoading(false);
    }
  }, [t]);

  const pct = counts.all ? Math.round((counts.locked / counts.all) * 100) : 0;

  return (
    <div className="dataset" data-testid="dataset-panel">
      <div className="dataset-head">
        <h2 className="page-title">{t("ds_title")}</h2>
        <div className="dataset-counts mono">
          <span><Glyph state="pending" /> <strong>{counts.all}</strong> {t("ds_records")}</span>
          <span><Glyph state="pending" /> <strong>{counts.pending}</strong> {t("rv_pending")}</span>
          <span><Glyph state="approved" /> <strong>{counts.approved}</strong> {t("rv_approved")}</span>
          <span><Glyph state="locked" /> <strong>{counts.locked}</strong> {t("rv_locked")}</span>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={() => void load()} disabled={loading}>
          {t("ds_refresh")}
        </button>
      </div>
      <div className="dataset-bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <span style={{ width: `${pct}%` }} />
      </div>

      {error && <p className="error-message">{error}</p>}

      <div className="export-actions">
        <div className="export-card">
          <h3 className="export-card-title">{t("ds_csv_title")}</h3>
          <p className="export-card-desc">{t("ds_csv_desc")}</p>
          <div className="export-row">
            <button className="btn btn-primary" onClick={exportCsv} disabled={csvLoading || counts.locked === 0} data-testid="export-csv">
              {csvLoading ? "…" : t("ds_csv_btn")}
            </button>
            <span className="mono hint-inline">GET /api/studies/export/csv</span>
          </div>
          {counts.locked === 0 && <p className="hint-text">{t("ds_none_locked")}</p>}
        </div>

        <div className="export-card">
          <h3 className="export-card-title">{t("ds_notion_title")}</h3>
          <p className="export-card-desc">{t("ds_notion_desc")}</p>
          <button className="btn btn-ghost" onClick={sync} disabled={syncLoading || counts.locked === 0}>
            {syncLoading ? "…" : t("ds_notion_btn")}
          </button>
          {syncResult && (
            <div className={`note ${syncResult.failed === 0 ? "note-ok" : "note-warn"}`}>
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
    </div>
  );
}
