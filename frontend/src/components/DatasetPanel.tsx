/**
 * DatasetPanel - the "Reports" tab: the caller's records at a glance, the
 * PRISMA 2020 flow, a forest-plot preview and the exports.
 *
 * Counts come from the study list (owner-filtered by the backend). The PRISMA
 * boxes M-AIDA cannot know (records identified, duplicates removed, records
 * screened, reports assessed) are typed in and kept per account; the boxes
 * after them are counted from the records. Only locked records leave the
 * system: both CSV exports and the Notion sync read pi_locked records only.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { downloadCsv, downloadMetaforCsv, fetchReport, fetchStudies, savePrisma, syncToNotion } from "../api";
import { useI18n } from "../i18n";
import type { NotionSyncResponse, PrismaCounts, ReportPayload, StudyDatabaseEntry } from "../types";
import ForestPlot, { type Estimator, type ForestInclude } from "./ForestPlot";
import { Glyph, stateOf } from "./ReviewScreen";

const PRISMA_FIELDS = ["identified", "duplicates_removed", "screened", "assessed"] as const;
type PrismaField = (typeof PRISMA_FIELDS)[number];
type PrismaDraft = Record<PrismaField, string>;

function toDraft(p: PrismaCounts | undefined): PrismaDraft {
  const out = {} as PrismaDraft;
  for (const f of PRISMA_FIELDS) {
    const v = p?.[f];
    out[f] = v === null || v === undefined ? "" : String(v);
  }
  return out;
}

function fromDraft(d: PrismaDraft): PrismaCounts {
  const out: PrismaCounts = {};
  for (const f of PRISMA_FIELDS) {
    const v = d[f].trim();
    out[f] = v === "" ? null : Number(v);
  }
  return out;
}

export default function DatasetPanel({ refreshKey, ownerTools = true }: { refreshKey: number; ownerTools?: boolean }) {
  const { t } = useI18n();
  const [studies, setStudies] = useState<StudyDatabaseEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [csvLoading, setCsvLoading] = useState<"" | "full" | "metafor">("");
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncResult, setSyncResult] = useState<NotionSyncResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [include, setInclude] = useState<ForestInclude>("locked");
  const [estimator, setEstimator] = useState<Estimator>("fixed");

  const [report, setReport] = useState<ReportPayload | null>(null);
  const [draft, setDraft] = useState<PrismaDraft>(toDraft(undefined));
  const [prismaMsg, setPrismaMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [prismaBusy, setPrismaBusy] = useState(false);

  const errorText = useCallback((err: unknown) => (err instanceof Error ? err.message.replace(/^\d{3}: /, "") : t("error_generic")), [t]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [list, rep] = await Promise.all([fetchStudies({}), fetchReport().catch(() => null)]);
      setStudies(list);
      if (rep) {
        setReport(rep);
        setDraft(toDraft(rep.prisma));
      }
    } catch (err: unknown) {
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  }, [errorText]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  const counts = useMemo(() => {
    const c = { all: studies.length, pending: 0, approved: 0, locked: 0 };
    for (const s of studies) c[stateOf(s)] += 1;
    return c;
  }, [studies]);

  const exportCsv = useCallback(
    async (kind: "full" | "metafor") => {
      setCsvLoading(kind);
      setError(null);
      try {
        await (kind === "full" ? downloadCsv() : downloadMetaforCsv());
      } catch (err: unknown) {
        setError(errorText(err));
      } finally {
        setCsvLoading("");
      }
    },
    [errorText]
  );

  const sync = useCallback(async () => {
    setSyncLoading(true);
    setError(null);
    setSyncResult(null);
    try {
      setSyncResult(await syncToNotion());
    } catch (err: unknown) {
      setError(errorText(err));
    } finally {
      setSyncLoading(false);
    }
  }, [errorText]);

  const saveFlow = async (e: React.FormEvent) => {
    e.preventDefault();
    setPrismaBusy(true);
    setPrismaMsg(null);
    try {
      const rep = await savePrisma(fromDraft(draft));
      setReport(rep);
      setDraft(toDraft(rep.prisma));
      setPrismaMsg({ ok: true, text: t("rp_prisma_saved") });
    } catch (err: unknown) {
      setPrismaMsg({ ok: false, text: errorText(err).replace(/^\d{3}: /, "") });
    } finally {
      setPrismaBusy(false);
    }
  };

  const pct = counts.all ? Math.round((counts.locked / counts.all) * 100) : 0;
  const assessed = draft.assessed.trim() === "" ? null : Number(draft.assessed);
  const fewerAssessed = assessed !== null && assessed < counts.all;
  const prismaLabels: Record<PrismaField, string> = {
    identified: t("rp_identified"),
    duplicates_removed: t("rp_duplicates"),
    screened: t("rp_screened"),
    assessed: t("rp_assessed"),
  };

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
      {!ownerTools && <p className="note note-warn" data-testid="report-owner-only">{t("team_member_report_hint")}</p>}

      <section className="prisma" data-testid="prisma">
        <div className="prisma-head">
          <h3 className="export-card-title">{t("rp_prisma_title")}</h3>
          <p className="export-card-desc">{t("rp_prisma_desc")}</p>
        </div>
        <form className="prisma-flow" onSubmit={saveFlow}>
          {PRISMA_FIELDS.map((f) => (
            <label className="prisma-box prisma-box-input" key={f} htmlFor={`prisma-${f}`}>
              <span className="prisma-label">{prismaLabels[f]}</span>
              <input
                id={`prisma-${f}`}
                className="form-input mono"
                type="number"
                min={0}
                max={10000000}
                inputMode="numeric"
                value={draft[f]}
                readOnly={!ownerTools}
                onChange={(e) => setDraft((d) => ({ ...d, [f]: e.target.value }))}
                placeholder="–"
              />
            </label>
          ))}
          <div className="prisma-box prisma-box-auto" data-testid="prisma-included">
            <span className="prisma-label">{t("rp_included")}</span>
            <strong className="mono">{report?.counts.records ?? counts.all}</strong>
          </div>
          <div className="prisma-box prisma-box-auto">
            <span className="prisma-label">{t("rp_locked")}</span>
            <strong className="mono">{report?.counts.locked ?? counts.locked}</strong>
          </div>
          <div className="prisma-actions">
            <button className="btn btn-secondary btn-sm" type="submit" disabled={prismaBusy || !ownerTools} data-testid="prisma-save">
              {prismaBusy ? "…" : t("rp_prisma_save")}
            </button>
            {report?.prisma_updated_at && !prismaMsg && (
              <span className="hint-inline">{t("rp_prisma_updated")} {new Date(report.prisma_updated_at).toLocaleString()}</span>
            )}
            {prismaMsg && (
              <span className={prismaMsg.ok ? "hint-inline" : "error-message"} role="status">{prismaMsg.text}</span>
            )}
          </div>
        </form>
        {fewerAssessed && <p className="hint-text">{t("rp_prisma_warn")}</p>}
      </section>

      <div className="report-controls" aria-label={t("rp_controls")}>
        <div className="seg-group" role="group" aria-label={t("rp_set")}>
          {(["locked", "approved", "all"] as const).map((v) => (
            <button
              key={v}
              type="button"
              className={`seg ${include === v ? "seg-on" : ""}`}
              aria-pressed={include === v}
              onClick={() => setInclude(v)}
              data-testid={`forest-set-${v}`}
            >
              {t(`rp_set_${v}` as const)}
            </button>
          ))}
        </div>
        <div className="seg-group" role="group" aria-label={t("rp_estimator")}>
          {(["fixed", "random"] as const).map((v) => (
            <button
              key={v}
              type="button"
              className={`seg ${estimator === v ? "seg-on" : ""}`}
              aria-pressed={estimator === v}
              onClick={() => setEstimator(v)}
              data-testid={`forest-est-${v}`}
            >
              {t(`rp_est_${v}` as const)}
            </button>
          ))}
        </div>
      </div>
      {include === "all" && <p className="hint-text">{t("rp_all_warn")}</p>}

      <ForestPlot studies={studies} include={include} estimator={estimator} />

      <div className="export-actions" data-tour="export">
        <div className="export-card">
          <h3 className="export-card-title">{t("ds_csv_title")}</h3>
          <p className="export-card-desc">{t("ds_csv_desc")}</p>
          <div className="export-row">
            <button className="btn btn-primary" onClick={() => void exportCsv("full")} disabled={csvLoading !== "" || counts.locked === 0 || !ownerTools} data-testid="export-csv">
              {csvLoading === "full" ? "…" : t("ds_csv_btn")}
            </button>
            <button className="btn btn-secondary" onClick={() => void exportCsv("metafor")} disabled={csvLoading !== "" || counts.locked === 0 || !ownerTools} data-testid="export-metafor">
              {csvLoading === "metafor" ? "…" : t("rp_metafor_btn")}
            </button>
          </div>
          <p className="hint-text">{t("rp_metafor_desc")}</p>
          {counts.locked === 0 && <p className="hint-text">{t("ds_none_locked")}</p>}
        </div>

        <div className="export-card">
          <h3 className="export-card-title">{t("ds_notion_title")}</h3>
          <p className="export-card-desc">{t("ds_notion_desc")}</p>
          <button className="btn btn-ghost" onClick={sync} disabled={syncLoading || counts.locked === 0 || !ownerTools}>
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
