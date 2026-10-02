import React from "react";
import { useI18n } from "../i18n";
import type { JobStatus } from "../types";

const CLASS: Record<JobStatus, string> = {
  queued: "badge-medium",
  running: "badge-medium",
  succeeded: "badge-success",
  rejected: "badge-warn",
  failed: "badge-low",
};

export function JobStatusPill({ status }: { status: JobStatus }) {
  const { t } = useI18n();
  const key = `job_status_${status}` as const;
  return (
    <span className={`badge ${CLASS[status]}`} data-testid="job-status">
      {t(key)}
    </span>
  );
}
