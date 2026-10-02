/**
 * Dashboard - credits, counts and the recent extraction jobs (8.0).
 *
 * Polls the job list while any job is queued/running so a user who left the
 * Extract tab still sees the outcome arrive.
 */

import React, { useCallback, useEffect, useState } from "react";
import { fetchJobs, fetchMe } from "../api";
import { useI18n } from "../i18n";
import type { ExtractionJob, MeResponse } from "../types";
import { JobStatusPill } from "./JobStatusPill";

interface DashboardProps {
  refreshKey: number;
  onNewExtraction: () => void;
  onOpenStudy: (studyId: string) => void;
}

function fmtWhen(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export default function Dashboard({ refreshKey, onNewExtraction, onOpenStudy }: DashboardProps) {
  const { t } = useI18n();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [jobs, setJobs] = useState<ExtractionJob[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [m, j] = await Promise.all([fetchMe(), fetchJobs(20)]);
      setMe(m);
      setJobs(j);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("error_generic"));
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  const active = jobs.some((j) => j.status === "queued" || j.status === "running");
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => void load(), 2500);
    return () => window.clearInterval(timer);
  }, [active, load]);

  return (
    <div className="panel dashboard-panel" data-testid="dashboard">
      <div className="panel-header">
        <h2 className="panel-title">{t("dash_title")}</h2>
        <button className="btn btn-primary btn-sm" onClick={onNewExtraction}>
          {t("dash_new_extraction")}
        </button>
      </div>

      {error && <p className="error-message">{error}</p>}

      <div className="summary-grid">
        <div className="summary-card summary-card-credits">
          <span className="summary-number" data-testid="credits-balance">
            {me ? (me.credits === null ? "∞" : me.credits) : "…"}
          </span>
          <span className="summary-label">{t("dash_credits")}</span>
        </div>
        <div className="summary-card">
          <span className="summary-number">{me ? me.studies : "…"}</span>
          <span className="summary-label">{t("dash_studies")}</span>
        </div>
        <div className="summary-card summary-card-locked">
          <span className="summary-number">{me ? me.locked : "…"}</span>
          <span className="summary-label">{t("dash_locked")}</span>
        </div>
      </div>

      <h3 className="panel-subtitle">{t("dash_recent_jobs")}</h3>
      {jobs.length === 0 ? (
        <p className="empty-text">{t("dash_no_jobs")}</p>
      ) : (
        <div className="table-container">
          <table className="studies-table jobs-table">
            <thead>
              <tr>
                <th>{t("job_file")}</th>
                <th>{t("job_status")}</th>
                <th>{t("job_result")}</th>
                <th>{t("job_when")}</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id} data-testid="job-row" data-status={job.status}>
                  <td className="title-cell" title={job.filename}>
                    {job.filename || job.metadata.title || job.id.slice(0, 8)}
                    {job.pages ? <span className="hint-inline"> · {job.pages} p.</span> : null}
                  </td>
                  <td>
                    <JobStatusPill status={job.status} />
                  </td>
                  <td className="job-result-cell">
                    {job.status === "succeeded" && job.study_id ? (
                      <button className="btn btn-link btn-sm" onClick={() => onOpenStudy(job.study_id as string)}>
                        {t("job_open_study")}
                      </button>
                    ) : job.status === "rejected" || job.status === "failed" ? (
                      <span className="job-error" title={job.error_message ?? ""}>
                        {job.error_code ?? job.status}
                        {job.status === "failed" && job.credits_charged === 0 ? ` · ${t("job_refunded")}` : ""}
                      </span>
                    ) : (
                      "…"
                    )}
                  </td>
                  <td className="mono small">{fmtWhen(job.finished_at ?? job.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
