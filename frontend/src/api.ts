/**
 * M-AIDA v7.0 API client.
 *
 * All routes proxied from the React dev server to the FastAPI backend
 * (default: http://localhost:8765).  Set VITE_API_URL in .env.local
 * to override the base URL.
 */

import axios, { AxiosInstance, AxiosResponse } from "axios";
import type {
  ExtractionRequest,
  HealthResponse,
  NotionSyncResponse,
  StudyDatabaseEntry,
  StudyFilters,
  VerificationDecision,
} from "./types";

const BASE_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8765";

const http: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function fetchHealth(): Promise<HealthResponse> {
  const res: AxiosResponse<HealthResponse> = await http.get("/api/health");
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
