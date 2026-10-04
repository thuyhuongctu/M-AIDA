/**
 * M-AIDA API client.
 *
 * All routes proxied from the React dev server to the FastAPI backend
 * (default: http://localhost:8765).  Set VITE_API_URL in .env.local
 * to override the base URL.
 */

import axios, { AxiosInstance, AxiosResponse } from "axios";
import type {
  AccountExport,
  AdminOrders,
  AdminUsage,
  AdminUser,
  ClientConfig,
  ExtractionJob,
  ExtractionRequest,
  HealthResponse,
  LedgerEntry,
  MeResponse,
  MockLoginResponse,
  NotionSyncResponse,
  PacksResponse,
  PaymentOrder,
  StudyDatabaseEntry,
  StudyFilters,
  VerificationDecision,
} from "./types";

// Production builds are same-origin by default (nginx or the backend itself
// serves the bundle and /api/*); the Vite dev server talks to the local
// backend. VITE_API_URL overrides both.
const BASE_URL =
  import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? "http://localhost:8765" : "");

const http: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// 7.2.2: the backend rejects every mutating request (extract/verify/lock/
// Notion-sync) without X-MAIDA-Admin-Key (main.py:admin_key_guard), since
// nginx proxies /api/ publicly in the production deployment. The key is
// entered once by the PI (see the header input in App.tsx), kept only in
// this browser's localStorage, and never baked into the built JS bundle -
// a build-time env var would ship it to every visitor.
const ADMIN_KEY_STORAGE_KEY = "maida_admin_key";

export function getAdminKey(): string {
  try {
    return localStorage.getItem(ADMIN_KEY_STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setAdminKey(key: string): void {
  try {
    if (key) localStorage.setItem(ADMIN_KEY_STORAGE_KEY, key);
    else localStorage.removeItem(ADMIN_KEY_STORAGE_KEY);
  } catch {
    // localStorage unavailable (private mode, etc.) - key just won't persist.
  }
  http.defaults.headers.common["X-MAIDA-Admin-Key"] = key;
}

setAdminKey(getAdminKey());

// 8.0: in the cloud modes (supabase / mock) every request carries the user's
// own bearer token instead. auth.ts registers the provider at start-up so
// this module does not import auth.ts (which imports this one).
let tokenProvider: () => string | null = () => null;
let unauthorizedHandler: () => void = () => undefined;

export function registerAuth(provider: () => string | null, onUnauthorized: () => void): void {
  tokenProvider = provider;
  unauthorizedHandler = onUnauthorized;
}

http.interceptors.request.use((cfg) => {
  const token = tokenProvider();
  if (token) {
    cfg.headers = cfg.headers ?? {};
    cfg.headers.Authorization = `Bearer ${token}`;
  }
  return cfg;
});

// 7.2.1: FastAPI puts the human-readable reason in `detail` (e.g. the 422 from
// the PI-editable whitelist, or the lock gate refusing a record without an
// effect size). Surface it as the Error message instead of axios's generic
// "Request failed with status code 422".
http.interceptors.response.use(
  (res) => res,
  (err: unknown) => {
    if (axios.isAxiosError(err) && err.response) {
      if (err.response.status === 401 && tokenProvider()) unauthorizedHandler();
      const data = err.response.data as { detail?: unknown } | undefined;
      const detail = data?.detail;
      const text =
        typeof detail === "string"
          ? detail
          : detail !== undefined
            ? JSON.stringify(detail)
            : err.message;
      return Promise.reject(new Error(`${err.response.status}: ${text}`));
    }
    return Promise.reject(err);
  }
);

/** True when the backend refused the caller as not invited to the closed beta (403 not_invited). */
export function isNotInvited(err: unknown): boolean {
  return err instanceof Error && err.message.includes("not_invited");
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function fetchHealth(): Promise<HealthResponse> {
  const res: AxiosResponse<HealthResponse> = await http.get("/api/health");
  return res.data;
}

export async function fetchConfig(): Promise<ClientConfig> {
  const res: AxiosResponse<ClientConfig> = await http.get("/api/config");
  return res.data;
}

export async function mockLogin(email: string, name = ""): Promise<MockLoginResponse> {
  const res: AxiosResponse<MockLoginResponse> = await http.post("/api/auth/mock-login", { email, name });
  return res.data;
}

// ---------------------------------------------------------------------------
// Account (8.0)
// ---------------------------------------------------------------------------

export async function fetchMe(): Promise<MeResponse> {
  const res: AxiosResponse<MeResponse> = await http.get("/api/me");
  return res.data;
}

export async function fetchLedger(limit = 100): Promise<LedgerEntry[]> {
  const res: AxiosResponse<LedgerEntry[]> = await http.get("/api/me/ledger", { params: { limit } });
  return res.data;
}

export async function downloadAccountExport(): Promise<void> {
  const res: AxiosResponse<AccountExport> = await http.get("/api/me/export");
  const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "maida_account_export.json";
  anchor.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Extraction jobs (8.0)
// ---------------------------------------------------------------------------

export async function createJob(
  file: File,
  metadata: { title?: string; authors?: string; year?: number; country?: string } = {}
): Promise<ExtractionJob> {
  const form = new FormData();
  form.append("file", file);
  if (metadata.title) form.append("title", metadata.title);
  if (metadata.authors) form.append("authors", metadata.authors);
  if (metadata.year) form.append("year", String(metadata.year));
  if (metadata.country) form.append("country", metadata.country);
  const res: AxiosResponse<ExtractionJob> = await http.post("/api/jobs", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function fetchJob(jobId: string): Promise<ExtractionJob> {
  const res: AxiosResponse<ExtractionJob> = await http.get(`/api/jobs/${jobId}`);
  return res.data;
}

export async function fetchJobs(limit = 20): Promise<ExtractionJob[]> {
  const res: AxiosResponse<ExtractionJob[]> = await http.get("/api/jobs", { params: { limit } });
  return res.data;
}

/** Poll a job until it leaves queued/running. */
export async function waitForJob(
  jobId: string,
  onUpdate?: (job: ExtractionJob) => void,
  intervalMs = 2000
): Promise<ExtractionJob> {
  for (;;) {
    const job = await fetchJob(jobId);
    onUpdate?.(job);
    if (job.status !== "queued" && job.status !== "running") return job;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

export async function deleteStudy(studyId: string): Promise<void> {
  await http.delete(`/api/studies/${studyId}`);
}

// ---------------------------------------------------------------------------
// Payments: credit packs (8.0)
// ---------------------------------------------------------------------------

/** Absolute URL for a path the backend returns (the mock checkout page is relative). */
export function apiUrl(pathOrUrl: string): string {
  return pathOrUrl.startsWith("/") ? `${BASE_URL}${pathOrUrl}` : pathOrUrl;
}

export async function fetchPacks(): Promise<PacksResponse> {
  const res: AxiosResponse<PacksResponse> = await http.get("/api/payments/packs");
  return res.data;
}

/** Create a payment link for a pack; the caller then sends the browser to `checkout_url`. */
export async function createOrder(packId: string): Promise<PaymentOrder> {
  const res: AxiosResponse<PaymentOrder> = await http.post("/api/payments/orders", { pack_id: packId });
  return res.data;
}

export async function fetchOrders(limit = 20): Promise<PaymentOrder[]> {
  const res: AxiosResponse<PaymentOrder[]> = await http.get("/api/payments/orders", { params: { limit } });
  return res.data;
}

/** Ask the server to check one order with the payment provider (id or order code). */
export async function syncOrder(ref: string | number): Promise<PaymentOrder> {
  const res: AxiosResponse<PaymentOrder> = await http.post(
    `/api/payments/orders/${encodeURIComponent(String(ref))}/sync`
  );
  return res.data;
}

export async function cancelOrder(ref: string | number): Promise<PaymentOrder> {
  const res: AxiosResponse<PaymentOrder> = await http.post(
    `/api/payments/orders/${encodeURIComponent(String(ref))}/cancel`
  );
  return res.data;
}

// ---------------------------------------------------------------------------
// Operator (admin) routes (8.0)
// ---------------------------------------------------------------------------

export async function adminUsers(): Promise<AdminUser[]> {
  const res: AxiosResponse<AdminUser[]> = await http.get("/api/admin/users");
  return res.data;
}

export async function adminGrantCredits(email: string, credits: number, note = ""): Promise<{ credits: number }> {
  const res: AxiosResponse<{ credits: number }> = await http.post("/api/admin/credits", { email, credits, note });
  return res.data;
}

export async function adminUsage(days = 30): Promise<AdminUsage> {
  const res: AxiosResponse<AdminUsage> = await http.get("/api/admin/usage", { params: { days } });
  return res.data;
}

export async function adminOrders(limit = 200): Promise<AdminOrders> {
  const res: AxiosResponse<AdminOrders> = await http.get("/api/admin/orders", { params: { limit } });
  return res.data;
}

// ---------------------------------------------------------------------------
// Extraction
// ---------------------------------------------------------------------------

/**
 * Send a Base64-encoded PDF with metadata to the extraction endpoint.
 *
 * @param request ExtractionRequest containing Base64 PDF and metadata dict.
 * @returns The extracted StudyDatabaseEntry (not yet locked).
 */
export async function extractPdf(
  request: ExtractionRequest
): Promise<StudyDatabaseEntry> {
  const res: AxiosResponse<StudyDatabaseEntry> = await http.post(
    "/api/extract",
    request
  );
  return res.data;
}

/**
 * Upload a PDF file as multipart/form-data.
 *
 * @param file The PDF File object from a file input / drop zone.
 * @param metadata Optional bibliographic metadata.
 * @returns The extracted StudyDatabaseEntry.
 */
export async function uploadPdf(
  file: File,
  metadata: {
    title?: string;
    authors?: string;
    year?: number;
    country?: string;
  } = {}
): Promise<StudyDatabaseEntry> {
  const form = new FormData();
  form.append("file", file);

  const params = new URLSearchParams();
  if (metadata.title) params.set("title", metadata.title);
  if (metadata.authors) params.set("authors", metadata.authors);
  if (metadata.year) params.set("year", String(metadata.year));
  if (metadata.country) params.set("country", metadata.country);

  const res: AxiosResponse<StudyDatabaseEntry> = await http.post(
    `/api/extract/upload?${params.toString()}`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return res.data;
}

// ---------------------------------------------------------------------------
// Studies
// ---------------------------------------------------------------------------

/**
 * Fetch all studies, with optional filters applied server-side.
 */
export async function fetchStudies(
  filters: StudyFilters = {}
): Promise<StudyDatabaseEntry[]> {
  const params: Record<string, string> = {};
  if (filters.icrv) params.icrv = filters.icrv;
  if (filters.dpl) params.dpl = filters.dpl;
  if (filters.verified !== null && filters.verified !== undefined)
    params.verified = String(filters.verified);
  if (filters.locked !== null && filters.locked !== undefined)
    params.locked = String(filters.locked);

  const res: AxiosResponse<StudyDatabaseEntry[]> = await http.get(
    "/api/studies",
    { params }
  );
  return res.data;
}

/**
 * Fetch a single study by its UUID.
 */
export async function fetchStudy(
  studyId: string
): Promise<StudyDatabaseEntry> {
  const res: AxiosResponse<StudyDatabaseEntry> = await http.get(
    `/api/studies/${studyId}`
  );
  return res.data;
}

/**
 * Apply PI field overrides and approval to a study (does NOT lock).
 */
export async function verifyStudy(
  studyId: string,
  decision: VerificationDecision
): Promise<StudyDatabaseEntry> {
  const res: AxiosResponse<StudyDatabaseEntry> = await http.patch(
    `/api/studies/${studyId}/verify`,
    decision
  );
  return res.data;
}

/**
 * Permanently lock a study record (irreversible).
 */
export async function lockStudy(
  studyId: string
): Promise<StudyDatabaseEntry> {
  const res: AxiosResponse<StudyDatabaseEntry> = await http.post(
    `/api/studies/${studyId}/lock`
  );
  return res.data;
}

/**
 * Download all locked studies as a CSV file and trigger browser download.
 */
export async function downloadCsv(): Promise<void> {
  const res = await http.get("/api/studies/export/csv", {
    responseType: "blob",
  });
  const url = URL.createObjectURL(new Blob([res.data], { type: "text/csv" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "maida_locked_studies.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Notion sync
// ---------------------------------------------------------------------------

/**
 * Push all PI-locked studies to Notion.
 */
export async function syncToNotion(): Promise<NotionSyncResponse> {
  const res: AxiosResponse<NotionSyncResponse> = await http.post(
    "/api/notion/sync"
  );
  return res.data;
}
