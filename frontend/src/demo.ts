/**
 * In-browser demo (8.0): "Try the demo" on the sign-in page, no account.
 *
 * While the demo runs, every request the app makes is answered here instead
 * of by the server (an axios adapter, see api.ts:setRequestAdapter). The real
 * screens run unchanged on a small workspace held in this tab's memory:
 *
 *   - five synthetic records (four locked, one waiting), so the forest plot
 *     has something to pool;
 *   - one synthetic sample PDF (public/demo/maida-demo-paper.pdf, made by
 *     demo/make_demo_paper.py) that the visitor "uploads". Its extraction is
 *     a fixed answer whose quotations are sentences of that PDF, word for
 *     word. Any other file is refused: the demo never reads a visitor's PDF.
 *
 * Nothing is sent to the server and no model is called, so the demo costs
 * nothing. Exports and payments are switched off. A reload, "Exit demo" or
 * "Sign out" ends it and the workspace is gone. All demo data is synthetic and
 * labelled as such; none of it is a research result.
 */

import {
  AxiosError,
  AxiosHeaders,
  type AxiosAdapter,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";
import { setRequestAdapter } from "./api";
import { enterDemo, leaveDemo } from "./auth";
import { readLang, translate, type StringKey } from "./i18n";
import type {
  ExtractedEffect,
  ExtractionJob,
  HealthResponse,
  LedgerEntry,
  MeResponse,
  PrismaCounts,
  ReportPayload,
  StudyDatabaseEntry,
} from "./types";

export const DEMO_PDF_URL = "/demo/maida-demo-paper.pdf";
export const DEMO_PDF_NAME = "maida-demo-paper.pdf";
export const DEMO_META = {
  title: "Export intensity and firm profitability: a synthetic example",
  authors: "M-AIDA demo (synthetic)",
  year: 2026,
  country: "Synthetic sample",
};
/** Sentences of the sample PDF, word for word (checked by demo/make_demo_paper.py). */
export const QUOTE_R =
  "Export intensity is positively correlated with return on assets (r = 0.18, p = 0.005, N = 240).";
export const QUOTE_N = "The synthetic sample contains 240 manufacturing firms observed between 2016 and 2019.";

const DEMO_CREDITS = 3;
const SEED_QUOTE = "Synthetic record for the M-AIDA demo; there is no source document.";

const PI_EDITABLE = new Set<keyof ExtractedEffect>([
  "effect_r", "effect_t", "effect_df", "effect_beta", "n_predictors", "sample_n",
  "sample_start", "sample_end", "p_value", "ci_lower", "ci_upper",
  "doi_measure", "performance_measure", "icrv_regime", "dpl_phase", "cdai_score",
  "country", "year", "paper_title", "authors",
]);
const PRIMARY = ["effect_r", "effect_t", "effect_df", "effect_beta", "n_predictors", "sample_n"] as const;

interface DemoJob extends ExtractionJob {
  runAt: number;
  doneAt: number;
}

interface Workspace {
  version: string;
  studies: StudyDatabaseEntry[];
  jobs: DemoJob[];
  ledger: LedgerEntry[];
  credits: number;
  prisma: PrismaCounts;
  prismaAt: string | null;
}

let ws: Workspace | null = null;
let sampleBytes: Promise<Uint8Array> | null = null;

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

const msg = (key: StringKey) => translate(readLang(), key);
const nowIso = (offsetMs = 0) => new Date(Date.now() + offsetMs).toISOString();

function uid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `demo-${Math.random().toString(16).slice(2)}-${Date.now().toString(16)}`;
}

/** Derived quantities, same rules as backend extractor.derive_from_primary. */
function derive(s: StudyDatabaseEntry): void {
  const n = s.sample_n;
  let r: number | null = null;
  let metric: "zero_order" | "partial" | null = null;
  let source: ExtractedEffect["r_source"] = null;
  let estimand: ExtractedEffect["estimand_source"] = null;
  let lambda = false;
  let outside = false;
  if (s.effect_r !== null) {
    r = Math.max(-1, Math.min(1, s.effect_r));
    metric = "zero_order";
    source = "reported";
    estimand = "observed";
  } else if (s.effect_t !== null && s.effect_df !== null) {
    const t2 = s.effect_t * s.effect_t;
    r = Math.sign(s.effect_t || 1) * Math.sqrt(t2 / (t2 + s.effect_df));
    metric = s.n_predictors !== null && s.n_predictors <= 1 ? "zero_order" : "partial";
    source = "derived";
    estimand = "observed";
  } else if (s.effect_beta !== null) {
    if (Math.abs(s.effect_beta) > 0.5) outside = true;
    else {
      lambda = s.effect_beta >= 0;
      r = Math.max(-1, Math.min(1, 0.98 * s.effect_beta + (lambda ? 0.05 : 0)));
      metric = "zero_order";
      source = "imputed";
      estimand = "imputed_pb2005";
    }
  }
  s.effect_r = r;
  s.metric_type = metric;
  s.r_source = source;
  s.estimand_source = estimand;
  s.source_controls = metric === null ? null : metric === "partial" || source === "imputed";
  s.lambda_applied = lambda;
  s.beta_outside_pb_domain = outside;
  s.variance_r = null;
  s.variance_formula = null;
  s.variance_z = null;
  if (r !== null && metric === "partial" && s.effect_df) {
    s.variance_r = (1 - r * r) ** 2 / s.effect_df;
    s.variance_formula = "(1 - r^2)^2 / df";
    s.variance_z = s.effect_df > 1 ? 1 / (s.effect_df - 1) : null;
  } else if (r !== null && metric === "zero_order" && n !== null && n > 1) {
    s.variance_r = (1 - r * r) ** 2 / (n - 1);
    s.variance_formula = "(1 - r^2)^2 / (n - 1)";
    s.variance_z = n > 3 ? 1 / (n - 3) : null;
  }
}

function blank(over: Partial<StudyDatabaseEntry>): StudyDatabaseEntry {
  const s: StudyDatabaseEntry = {
    study_id: uid(),
    paper_title: "",
    authors: "",
    year: 2026,
    country: "",
    sample_n: null,
    sample_start: null,
    sample_end: null,
    effect_r: null,
    effect_t: null,
    effect_beta: null,
    effect_df: null,
    p_value: null,
    ci_lower: null,
    ci_upper: null,
    doi_measure: null,
    performance_measure: null,
    icrv_regime: null,
    cdai_score: null,
    dpl_phase: null,
    n_predictors: null,
    metric_type: null,
    estimand_source: null,
    source_controls: null,
    df_source: null,
    df_imputed: false,
    lambda_applied: false,
    beta_outside_pb_domain: false,
    variance_r: null,
    variance_formula: null,
    variance_z: null,
    r_source: null,
    n_source: null,
    evidence_page: null,
    evidence_quote: null,
    n_evidence_page: null,
    n_evidence_quote: null,
    text_truncated: false,
    extraction_confidence: 0.86,
    requires_verification: true,
    pi_locked: false,
    pi_approved_at: null,
    pi_edited_fields: [],
    pi_override_at: null,
    derived_from: null,
    extracted_at: nowIso(),
    locked_at: null,
    notion_page_id: null,
    pi_notes: "",
    machine_proposal: null,
    ...over,
  };
  derive(s);
  return s;
}

function proposal(s: StudyDatabaseEntry): Record<string, unknown> {
  const keep = [
    "effect_r", "effect_t", "effect_beta", "effect_df", "sample_n", "p_value", "ci_lower", "ci_upper",
    "doi_measure", "performance_measure", "extraction_confidence", "df_imputed", "beta_outside_pb_domain",
  ] as const;
  return Object.fromEntries(keep.map((k) => [k, s[k]]));
}

/** Synthetic records: invented for the demo, labelled as such, never research results. */
function seedStudies(): StudyDatabaseEntry[] {
  const rows: [string, number, number, number, ExtractedEffect["icrv_regime"], ExtractedEffect["dpl_phase"],
    ExtractedEffect["doi_measure"], ExtractedEffect["performance_measure"], boolean][] = [
    ["B", 2018, 0.12, 410, "II", "PRE", "GEO", "ACC", true],
    ["C", 2020, 0.05, 1250, "III", "SPN", "EXP", "LAB", true],
    ["D", 2021, 0.21, 180, "I", "FOL", "FSTS", "MKT", true],
    ["E", 2022, -0.04, 620, "III", "FOL", "EXP", "ACC", true],
    ["F", 2023, 0.09, 300, "II", "FOL", "FSTS", "ACC", false],
  ];
  return rows.map(([id, year, r, n, icrv, dpl, doi, perf, locked], i) => {
    const s = blank({
      paper_title: `Synthetic record ${id} (M-AIDA demo)`,
      authors: `Demo ${id}`,
      year,
      country: "Synthetic sample",
      effect_r: r,
      sample_n: n,
      icrv_regime: icrv,
      dpl_phase: dpl,
      doi_measure: doi,
      performance_measure: perf,
      evidence_quote: SEED_QUOTE,
      n_evidence_quote: SEED_QUOTE,
      extraction_confidence: 0.9,
      extracted_at: nowIso(-(6 - i) * 86_400_000),
    });
    s.machine_proposal = proposal(s);
    s.n_source = "reported";
    if (locked) {
      s.requires_verification = false;
      s.pi_approved_at = nowIso(-(5 - i) * 86_400_000);
      s.locked_at = s.pi_approved_at;
      s.pi_locked = true;
      s.pi_notes = "Synthetic demo record.";
    }
    return s;
  });
}

/** What "the model" proposes for the sample PDF: fixed, quoted from that PDF. */
function sampleExtraction(meta: Partial<typeof DEMO_META>): StudyDatabaseEntry {
  const s = blank({
    paper_title: meta.title || DEMO_META.title,
    authors: meta.authors || DEMO_META.authors,
    year: meta.year || DEMO_META.year,
    country: meta.country || DEMO_META.country,
    effect_r: 0.18,
    p_value: 0.005,
    sample_n: 240,
    sample_start: 2016,
    sample_end: 2019,
    doi_measure: "EXP",
    performance_measure: "ACC",
    evidence_page: 1,
    evidence_quote: QUOTE_R,
    n_evidence_page: 1,
    n_evidence_quote: QUOTE_N,
    extraction_confidence: 0.86,
  });
  s.n_source = "reported";
  s.machine_proposal = proposal(s);
  return s;
}

function fresh(version: string): Workspace {
  return {
    version,
    studies: seedStudies(),
    jobs: [],
    ledger: [
      { id: 1, delta: DEMO_CREDITS, reason: "grant_beta", balance_after: DEMO_CREDITS, job_id: null, note: "demo", created_at: nowIso() },
    ],
    credits: DEMO_CREDITS,
    prisma: {},
    prismaAt: null,
  };
}

function charge(w: Workspace, delta: number, reason: LedgerEntry["reason"], jobId: string | null): void {
  w.credits += delta;
  w.ledger.unshift({
    id: w.ledger.length + 1,
    delta,
    reason,
    balance_after: w.credits,
    job_id: jobId,
    note: "demo",
    created_at: nowIso(),
  });
}

function advance(w: Workspace, job: DemoJob): DemoJob {
  const t = Date.now();
  if (job.status === "queued" && t >= job.runAt) {
    job.status = "running";
    job.started_at = new Date(job.runAt).toISOString();
  }
  if (job.status === "running" && t >= job.doneAt) {
    const study = sampleExtraction(job.metadata as Partial<typeof DEMO_META>);
    w.studies.push(study);
    job.status = "succeeded";
    job.study_id = study.study_id;
    job.finished_at = new Date(job.doneAt).toISOString();
    job.model = "demo (no model call)";
  }
  return job;
}

async function sampleIs(file: File): Promise<boolean> {
  if (!sampleBytes) {
    sampleBytes = fetch(DEMO_PDF_URL)
      .then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(new Error(String(r.status)))))
      .then((b) => new Uint8Array(b));
  }
  let ref: Uint8Array;
  try {
    ref = await sampleBytes;
  } catch {
    sampleBytes = null;
    return false;
  }
  const got = new Uint8Array(await file.arrayBuffer());
  if (got.length !== ref.length) return false;
  for (let i = 0; i < ref.length; i += 1) if (got[i] !== ref[i]) return false;
  return true;
}

function reportPayload(w: Workspace): ReportPayload {
  const c = { records: w.studies.length, pending: 0, approved: 0, locked: 0 };
  for (const s of w.studies) {
    if (s.pi_locked) c.locked += 1;
    else if (s.pi_approved_at) c.approved += 1;
    else c.pending += 1;
  }
  return { prisma: w.prisma, prisma_updated_at: w.prismaAt, counts: c };
}

// ---------------------------------------------------------------------------
// the adapter
// ---------------------------------------------------------------------------

class Reply {
  constructor(public status: number, public data: unknown) {}
}
const ok = (data: unknown) => new Reply(200, data);
const fail = (status: number, detail: string) => new Reply(status, { detail });

function body(config: InternalAxiosRequestConfig): Record<string, unknown> {
  const d = config.data;
  if (typeof d === "string") {
    try {
      return JSON.parse(d) as Record<string, unknown>;
    } catch {
      return {};
    }
  }
  return d && typeof d === "object" && !(d instanceof FormData) ? (d as Record<string, unknown>) : {};
}

async function route(w: Workspace, method: string, path: string, config: InternalAxiosRequestConfig): Promise<Reply> {
  const params = (config.params ?? {}) as Record<string, string | number | boolean | undefined>;
  const find = (id: string) => w.studies.find((s) => s.study_id === id);
  let m: RegExpMatchArray | null;

  if (method === "get" && path === "/api/health") {
    const h: HealthResponse = {
      status: "ok",
      version: w.version,
      study_count: null,
      notion_configured: false,
      storage: "demo: this browser tab only",
      demo_mode: true,
      extraction_mode: "live",
    };
    return ok(h);
  }
  if (method === "get" && path === "/api/me") {
    const me: MeResponse = {
      id: "demo",
      email: "",
      name: "Demo",
      role: "user",
      beta: true,
      credits: w.credits,
      studies: w.studies.length,
      locked: w.studies.filter((s) => s.pi_locked).length,
      auth_mode: "mock",
    };
    return ok(me);
  }
  if (method === "get" && path === "/api/me/ledger") return ok(w.ledger.slice(0, Number(params.limit ?? 100)));
  if (method === "get" && path === "/api/me/export") {
    return ok({ exported_at: nowIso(), version: w.version, demo: true, user: { id: "demo", email: "", name: "Demo" },
      studies: w.studies, jobs: w.jobs, ledger: w.ledger });
  }
  if (method === "get" && path === "/api/me/report") return ok(reportPayload(w));
  if (method === "put" && path === "/api/me/report/prisma") {
    const b = body(config) as PrismaCounts;
    const v = (k: keyof PrismaCounts) => (typeof b[k] === "number" ? (b[k] as number) : null);
    for (const k of ["identified", "duplicates_removed", "screened", "assessed"] as const) {
      const x = v(k);
      if (x !== null && (!Number.isInteger(x) || x < 0 || x > 10_000_000)) return fail(422, `${k}: whole number 0..10,000,000`);
    }
    const problems: string[] = [];
    const [idf, dup, scr, ass] = [v("identified"), v("duplicates_removed"), v("screened"), v("assessed")];
    if (idf !== null && dup !== null && dup > idf) problems.push("duplicates removed exceed records identified");
    if (idf !== null && scr !== null && scr > idf - (dup ?? 0)) problems.push("records screened exceed records left after removing duplicates");
    if (scr !== null && ass !== null && ass > scr) problems.push("reports assessed exceed records screened");
    if (problems.length) return fail(422, `PRISMA counts do not add up: ${problems.join("; ")}.`);
    w.prisma = { identified: idf, duplicates_removed: dup, screened: scr, assessed: ass };
    w.prismaAt = nowIso();
    return ok(reportPayload(w));
  }

  if (method === "post" && path === "/api/jobs") {
    const form = config.data instanceof FormData ? config.data : null;
    const file = form?.get("file");
    if (!(file instanceof File) || !(await sampleIs(file))) return fail(422, msg("demo_only_sample"));
    if (w.credits < 1) return fail(402, msg("ex_no_credits"));
    const t = Date.now();
    const job: DemoJob = {
      id: uid(),
      status: "queued",
      filename: file.name,
      size_bytes: file.size,
      pages: 1,
      metadata: {
        title: String(form?.get("title") ?? ""),
        authors: String(form?.get("authors") ?? ""),
        year: Number(form?.get("year") ?? 0) || undefined,
        country: String(form?.get("country") ?? ""),
      },
      study_id: null,
      error_code: null,
      error_message: null,
      model: null,
      credits_charged: 1,
      created_at: new Date(t).toISOString(),
      started_at: null,
      finished_at: null,
      runAt: t + 700,
      doneAt: t + 2400,
    };
    w.jobs.unshift(job);
    charge(w, -1, "extraction", job.id);
    return new Reply(202, strip(job));
  }
  if (method === "get" && path === "/api/jobs") return ok(w.jobs.slice(0, Number(params.limit ?? 20)).map((j) => strip(advance(w, j))));
  if (method === "get" && (m = path.match(/^\/api\/jobs\/([^/]+)$/))) {
    const job = w.jobs.find((j) => j.id === m![1]);
    return job ? ok(strip(advance(w, job))) : fail(404, "Job not found");
  }

  if (method === "get" && path === "/api/studies") {
    let list = [...w.studies];
    const flag = (x: unknown) => (x === undefined || x === null || x === "" ? null : String(x) === "true");
    const locked = flag(params.locked);
    const verified = flag(params.verified);
    if (params.icrv) list = list.filter((s) => s.icrv_regime === params.icrv);
    if (params.dpl) list = list.filter((s) => s.dpl_phase === params.dpl);
    if (verified !== null) list = list.filter((s) => !s.requires_verification === verified);
    if (locked !== null) list = list.filter((s) => s.pi_locked === locked);
    return ok(list);
  }
  if (path.startsWith("/api/studies/export/") || path === "/api/notion/sync") return fail(403, msg("demo_no_export"));
  if ((m = path.match(/^\/api\/studies\/([^/]+)$/))) {
    const s = find(m[1]);
    if (!s) return fail(404, "Study not found");
    if (method === "get") return ok(s);
    if (method === "delete") {
      if (s.pi_locked) return fail(409, "Locked studies cannot be deleted.");
      w.studies = w.studies.filter((x) => x !== s);
      return new Reply(204, "");
    }
  }
  if (method === "patch" && (m = path.match(/^\/api\/studies\/([^/]+)\/verify$/))) {
    const s = find(m[1]);
    if (!s) return fail(404, "Study not found");
    if (s.pi_locked) return fail(409, "Study is already locked; overrides are not permitted.");
    const b = body(config);
    const overrides = (b.field_overrides ?? {}) as Record<string, unknown>;
    const rejected = Object.keys(overrides).filter((k) => !PI_EDITABLE.has(k as keyof ExtractedEffect));
    if (rejected.length) return fail(422, `field_overrides may only touch PI-editable fields; rejected: ${rejected.join(", ")}`);
    const next = { ...s, ...overrides } as StudyDatabaseEntry;
    const touched = Object.keys(overrides).filter((k) => (PRIMARY as readonly string[]).includes(k));
    if (touched.length) {
      if (!("effect_r" in overrides)) {
        if (("effect_t" in overrides || "effect_df" in overrides) && next.effect_t !== null) next.effect_r = null;
        else if ("effect_beta" in overrides && next.effect_beta !== null) {
          next.effect_r = null;
          next.effect_t = null;
        }
      }
      derive(next);
    }
    if (Object.keys(overrides).length) {
      next.pi_edited_fields = Array.from(new Set([...next.pi_edited_fields, ...Object.keys(overrides)])).sort();
      next.pi_override_at = nowIso();
    }
    next.pi_notes = String(b.pi_notes ?? "");
    if (next.effect_r === null) {
      next.requires_verification = true;
      next.pi_approved_at = null;
    } else if (b.pi_approved) {
      next.requires_verification = false;
      next.pi_approved_at = nowIso();
    } else {
      next.pi_approved_at = null;
    }
    w.studies = w.studies.map((x) => (x === s ? next : x));
    return ok(next);
  }
  if (method === "post" && (m = path.match(/^\/api\/studies\/([^/]+)\/lock$/))) {
    const s = find(m[1]);
    if (!s) return fail(404, "Study not found");
    if (s.pi_locked) return ok(s);
    if (s.requires_verification || !s.pi_approved_at)
      return fail(422, "Study has not been approved by the PI; approve via PATCH /verify before locking.");
    if (s.effect_r === null || s.variance_r === null)
      return fail(422, "Study has no usable effect size / variance; it cannot be locked.");
    const next = { ...s, pi_locked: true, locked_at: nowIso() };
    w.studies = w.studies.map((x) => (x === s ? next : x));
    return ok(next);
  }

  return fail(404, msg("demo_unavailable"));
}

function strip(job: DemoJob): ExtractionJob {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { runAt, doneAt, ...rest } = job;
  return { ...rest, metadata: { ...job.metadata } };
}

const demoAdapter: AxiosAdapter = async (config) => {
  const w = ws;
  const method = (config.method ?? "get").toLowerCase();
  const path = (config.url ?? "").replace(/^https?:\/\/[^/]+/, "").split("?")[0];
  const reply = w ? await route(w, method, path, config) : fail(503, "demo not running");
  // A short pause, so the screens show their loading states as they would live.
  await new Promise((r) => setTimeout(r, 120));
  let data = reply.data;
  // Errors keep their JSON body so the message ("Exports are off…") reaches the screen.
  if (config.responseType === "blob" && reply.status < 400 && !(data instanceof Blob)) {
    data = new Blob([JSON.stringify(data)], { type: "application/json" });
  }
  const response: AxiosResponse = {
    data,
    status: reply.status,
    statusText: String(reply.status),
    headers: new AxiosHeaders(),
    config,
    request: null,
  };
  if (reply.status >= 400) {
    throw new AxiosError(`Request failed with status code ${reply.status}`, AxiosError.ERR_BAD_REQUEST, config, null, response);
  }
  return response;
};

// ---------------------------------------------------------------------------
// start / stop
// ---------------------------------------------------------------------------

export function startDemo(version: string): void {
  ws = fresh(version);
  setRequestAdapter(demoAdapter);
  enterDemo(
    { id: "demo", email: "", name: "Demo" },
    () => {
      ws = null;
      setRequestAdapter(null);
    }
  );
}

export function stopDemo(): void {
  leaveDemo();
}

/** The sample PDF as a File, for the Extract tab's "Use the sample paper". */
export async function sampleFile(): Promise<File> {
  const res = await fetch(DEMO_PDF_URL);
  if (!res.ok) throw new Error(`${res.status}: sample paper not found`);
  const blob = await res.blob();
  return new File([blob], DEMO_PDF_NAME, { type: "application/pdf" });
}
