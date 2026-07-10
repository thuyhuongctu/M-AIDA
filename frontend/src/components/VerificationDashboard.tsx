/**
 * VerificationDashboard - tabular overview of all extracted studies.
 *
 * Supports per-column filtering by ICRV regime, DPL phase, verification
 * status, and lock status.  Row click opens the VerificationPanel.
 */

import React, { useCallback, useEffect, useState } from "react";
import { fetchStudies } from "../api";
import {
  DplPhase,
  getConfidenceTier,
  IcrvRegime,
  StudyDatabaseEntry,
  StudyFilters,
} from "../types";
import VerificationPanel from "./VerificationPanel";

// ---------------------------------------------------------------------------
// Status cell badge
// ---------------------------------------------------------------------------

function StatusBadge({ study }: { study: StudyDatabaseEntry }) {
  if (study.pi_locked) return <span className="badge badge-success">Locked</span>;
  if (!study.requires_verification)
    return <span className="badge badge-medium">Approved</span>;
  return <span className="badge badge-warn">Needs Review</span>;
}

// ---------------------------------------------------------------------------
// Filter bar
// ---------------------------------------------------------------------------

interface FilterBarProps {
  filters: StudyFilters;
  onChange: (f: StudyFilters) => void;
}

function FilterBar({ filters, onChange }: FilterBarProps) {
  return (
    <div className="filter-bar">
      <select
        className="filter-select"
        value={filters.icrv ?? ""}
        onChange={(e) =>
          onChange({ ...filters, icrv: (e.target.value as IcrvRegime) || undefined })
        }
        aria-label="Filter by ICRV regime"
      >
        <option value="">All ICRV</option>
        {(["I", "II", "III", "FR", "MX"] as IcrvRegime[]).map((r) => (
          <option key={r} value={r}>
            Regime {r}
          </option>
        ))}
      </select>

      <select
        className="filter-select"
        value={filters.dpl ?? ""}
        onChange={(e) =>
          onChange({ ...filters, dpl: (e.target.value as DplPhase) || undefined })
        }
        aria-label="Filter by DPL phase"
      >
        <option value="">All DPL</option>
        {(["PRE", "SPN", "FOL"] as DplPhase[]).map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </select>

      <select
        className="filter-select"
        value={
          filters.verified === true
            ? "true"
            : filters.verified === false
            ? "false"
            : ""
        }
        onChange={(e) =>
          onChange({
            ...filters,
            verified:
              e.target.value === "true"
                ? true
                : e.target.value === "false"
                ? false
                : null,
          })
        }
        aria-label="Filter by verification status"
      >
        <option value="">All verification</option>
        <option value="true">Verified</option>
        <option value="false">Needs review</option>
      </select>

      <select
        className="filter-select"
        value={
          filters.locked === true
            ? "true"
            : filters.locked === false
            ? "false"
            : ""
        }
        onChange={(e) =>
          onChange({
            ...filters,
            locked:
              e.target.value === "true"
                ? true
                : e.target.value === "false"
                ? false
                : null,
          })
        }
        aria-label="Filter by lock status"
      >
        <option value="">All lock status</option>
        <option value="true">Locked</option>
        <option value="false">Unlocked</option>
      </select>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function VerificationDashboard() {
  const [studies, setStudies] = useState<StudyDatabaseEntry[]>([]);
  const [filters, setFilters] = useState<StudyFilters>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<StudyDatabaseEntry | null>(null);

  const loadStudies = useCallback(async (f: StudyFilters) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchStudies(f);
      setStudies(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load studies.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStudies(filters);
  }, [filters, loadStudies]);

  const handleFilterChange = useCallback(
    (f: StudyFilters) => {
      setFilters(f);
    },
    []
  );

  const handleUpdated = useCallback((updated: StudyDatabaseEntry) => {
    setStudies((prev) =>
      prev.map((s) => (s.study_id === updated.study_id ? updated : s))
    );
    setSelected(updated);
  }, []);

  return (
    <div className="dashboard-layout">
      {/* Study list pane */}
      <div className="studies-pane">
        <h2 className="panel-title">Study Database</h2>
        <FilterBar filters={filters} onChange={handleFilterChange} />

        {loading && <p className="loading-text">Loading studies…</p>}
        {error && <p className="error-message">{error}</p>}

        {!loading && studies.length === 0 && (
          <p className="empty-text">
            No studies match the current filters. Upload PDFs in the Extract tab.
          </p>
        )}

        {studies.length > 0 && (
          <div className="table-container">
            <table className="studies-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Year</th>
                  <th>Country</th>
                  <th>r</th>
                  <th>N</th>
                  <th>Confidence</th>
                  <th>ICRV</th>
                  <th>DPL</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {studies.map((study) => {
                  const tier = getConfidenceTier(study.extraction_confidence);
                  return (
                    <tr
                      key={study.study_id}
                      className={`study-row ${
                        selected?.study_id === study.study_id ? "selected" : ""
                      }`}
                      onClick={() => setSelected(study)}
                      tabIndex={0}
                      onKeyDown={(e) => e.key === "Enter" && setSelected(study)}
                      aria-label={`Open study: ${study.paper_title}`}
                    >
                      <td
                        className="title-cell"
                        title={study.paper_title}
                      >
                        {study.paper_title.length > 50
                          ? study.paper_title.slice(0, 47) + "…"
                          : study.paper_title}
                      </td>
                      <td>{study.year}</td>
                      <td>{study.country || "-"}</td>
                      <td className="mono">
                        {study.effect_r !== null
                          ? study.effect_r.toFixed(3)
                          : "-"}
                      </td>
                      <td className="mono">{study.sample_n ?? "-"}</td>
                      <td>
                        <span
                          className={`badge badge-${
                            tier === "high"
                              ? "success"
                              : tier === "medium"
                              ? "medium"
                              : "low"
                          }`}
                        >
                          {(study.extraction_confidence * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td>{study.icrv_regime ?? "-"}</td>
                      <td>{study.dpl_phase ?? "-"}</td>
                      <td>
                        <StatusBadge study={study} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Detail pane */}
      {selected && (
        <div className="detail-pane">
          <VerificationPanel
            study={selected}
            onClose={() => setSelected(null)}
            onUpdated={handleUpdated}
          />
        </div>
      )}
    </div>
  );
}
