/**
 * Dashboard - credits, counts and the recent extraction jobs (8.0).
 *
 * Polls the job list while any job is queued/running so a user who left the
 * Extract tab still sees the outcome arrive.
 */

import React, { useCallback, useEffect, useState } from "react";
import { fetchJobs, fetchMe, fetchStudies } from "../api";
import { useI18n } from "../i18n";
import type { ExtractionJob, MeResponse, StudyDatabaseEntry } from "../types";
import { JobStatusPill } from "./JobStatusPill";
import WorldClocks from "./WorldClocks";

interface DashboardProps {
  refreshKey: number;
  onNewExtraction: () => void;
  onOpenStudy: (studyId: string) => void;
}

/** Records still waiting for the PI, lowest confidence first. */
function nextUp(pending: StudyDatabaseEntry[]): StudyDatabaseEntry | null {
  if (pending.length === 0) return null;
  return [...pending].sort((a, b) => a.extraction_confidence - b.extraction_confidence)[0];
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
  const [pending, setPending] = useState<StudyDatabaseEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [m, j, unlocked] = await Promise.all([fetchMe(), fetchJobs(20), fetchStudies({ locked: false })]);
      setMe(m);
      setJobs(j);
      setPending(unlocked.filter((s) => !s.pi_approved_at));
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

      <WorldClocks variant="card" />

      <div className="summary-grid">
        <div className="summary-card summary-card-credits" data-tour="credits">
          <span className="summary-number">
            <span className="glyph glyph-locked" aria-hidden="true">◆</span>
            <span data-testid="credits-balance">{me ? (me.credits === null ? "∞" : me.credits) : "…"}</span>
          </span>
          <span className="summary-label">{t("dash_credits")}</span>
        </div>
        <div className="summary-card">
          <span className="summary-number">
            <span className="glyph glyph-pending" aria-hidden="true">◇</span>
            {me ? me.studies : "…"}
          </span>
          <span className="summary-label">{t("dash_studies")}</span>
        </div>
        <div className="summary-card summary-card-locked">
          <span className="summary-number">
            <span className="glyph glyph-locked" aria-hidden="true">◆</span>
            {me ? me.locked : "…"}
          </span>
          <span className="summary-label">{t("dash_locked")}</span>
        </div>
      </div>

      {(() => {
        const next = nextUp(pending);
        return (
          <div className={`next-up ${next ? "" : "next-up-empty"}`} data-testid="next-up">
            <span className="glyph glyph-pending" aria-hidden="true">◇</span>
            <div className="next-up-text">
              <strong>
                {pending.length === 0
                  ? t("next_up_none")
                  : pending.length === 1
                    ? t("next_up_one")
                    : `${pending.length} ${t("next_up_many")}`}
              </strong>
              {next && (
                <span className="hint-inline">
                  {t("next_up_next")}: {next.authors || next.paper_title} ({next.year}) · {t("next_up_conf")}{" "}
                  {next.extraction_confidence.toFixed(2)}
                </span>
              )}
            </div>
            {next && (
              <button className="btn btn-primary btn-sm" onClick={() => onOpenStudy(next.study_id)} data-testid="continue-review">
                {t("continue_review")} →
              </button>
            )}
          </div>
        );
      })()}

      <h3 className="eyebrow">{t("dash_recent_jobs")}</h3>
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
                        {t("job_open_study")} · <span className="mono">{job.study_id.slice(0, 8)}</span>
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
