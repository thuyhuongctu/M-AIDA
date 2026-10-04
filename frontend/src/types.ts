/**
 * TypeScript interfaces matching the M-AIDA backend Pydantic models (7.2.x).
 *
 * Keep in sync with backend/models.py.
 */

// ---------------------------------------------------------------------------
// Domain literal types
// ---------------------------------------------------------------------------

// DOI measure: FSTS, GEO (geographic scope), EXP (export intensity),
// FDI (outward-FDI-based), COMP (composite/entropy, e.g. TNI), OTH (other)
export type DoiMeasure = "FSTS" | "GEO" | "EXP" | "FDI" | "COMP" | "OTH";
// Performance: ACC (accounting), MKT (market), LAB (labour productivity), MIX
export type PerformanceMeasure = "ACC" | "MKT" | "LAB" | "MIX";
// ICRV - Institutional Context Regime Variation (WGI Rule of Law, 2023):
// I=Advanced-Innovation, II=Upper-Middle, III=Emerging, FR=Frontier/SIDS,
// MX=Multi-country pooled. PI-assigned, never LLM-extracted.
export type IcrvRegime = "I" | "II" | "III" | "FR" | "MX";
// DPL phase (PRE/SPN/FOL), PI-derived from median data year.
export type DplPhase = "PRE" | "SPN" | "FOL";

// ---------------------------------------------------------------------------
// Core extracted effect model
// ---------------------------------------------------------------------------

export interface ExtractedEffect {
  study_id: string;
  paper_title: string;
  authors: string;
  year: number;
  country: string;

  // Sample
  sample_n: number | null;
  sample_start: number | null;
  sample_end: number | null;

  // Raw statistics
  effect_r: number | null;
  effect_t: number | null;
  effect_beta: number | null;
  effect_df: number | null;
  p_value: number | null;
  ci_lower: number | null;
  ci_upper: number | null;

  // Moderator coding
  doi_measure: DoiMeasure | null;
  performance_measure: PerformanceMeasure | null;
  icrv_regime: IcrvRegime | null;
  cdai_score: number | null;
  dpl_phase: DplPhase | null;

  // Derivation and weighting (7.1.2 formula fixes; exported since 7.2.0)
  n_predictors: number | null;
  metric_type: "zero_order" | "partial" | null;
  estimand_source: "observed" | "imputed_pb2005" | null;
  source_controls: boolean | null;
  df_source: "reported" | "derived" | null;
  df_imputed: boolean;
  lambda_applied: boolean;
  beta_outside_pb_domain: boolean;
  variance_r: number | null;
  variance_formula: string | null;
  variance_z: number | null;
  r_source: "reported" | "derived" | "imputed" | null;
  n_source: "reported" | null;

  // Evidence trail (gate E1)
  evidence_page: number | null;
  evidence_quote: string | null;
  n_evidence_page: number | null;
  n_evidence_quote: string | null;
  text_truncated: boolean;

  // Provenance
  extraction_confidence: number;
  requires_verification: boolean;
  pi_locked: boolean;
  /** 8.0: set by PATCH /verify with pi_approved=true; required before locking. */
  pi_approved_at: string | null;
  pi_edited_fields: string[];
  pi_override_at: string | null; // ISO 8601 or null
  derived_from: string | null;
  extracted_at: string; // ISO 8601
  locked_at: string | null; // ISO 8601 or null
}

// ---------------------------------------------------------------------------
// Study database entry (adds Notion sync info)
// ---------------------------------------------------------------------------

export interface StudyDatabaseEntry extends ExtractedEffect {
  notion_page_id: string | null;
  pi_notes: string;
  machine_proposal: Record<string, unknown> | null;
}

// ---------------------------------------------------------------------------
// API request / response models
// ---------------------------------------------------------------------------

export interface ExtractionRequest {
  pdf_content: string; // Base64-encoded PDF
  paper_metadata: PaperMetadata;
}

export interface PaperMetadata {
  title?: string;
  authors?: string;
  year?: number;
  country?: string;
  doi?: string;
  [key: string]: string | number | undefined;
}

export interface VerificationDecision {
  study_id: string;
  field_overrides: Partial<ExtractedEffect>;
  pi_approved: boolean;
  pi_notes: string;
}

// ---------------------------------------------------------------------------
// UI-only helpers
// ---------------------------------------------------------------------------

/** Confidence tier used to drive colour-coding in the dashboard. */
export type ConfidenceTier = "high" | "medium" | "low";

export function getConfidenceTier(confidence: number): ConfidenceTier {
  if (confidence >= 0.9) return "high";
  if (confidence >= 0.7) return "medium";
  return "low";
}

export interface StudyFilters {
  icrv?: IcrvRegime | "";
  dpl?: DplPhase | "";
  verified?: boolean | null;
  locked?: boolean | null;
}

/** What the next upload will actually do, as reported by the backend. */
export type ExtractionMode = "live" | "rehearsed_fallback" | "unavailable";

export interface ClientConfig {
  version: string;
  auth_mode: "admin_key" | "supabase" | "mock";
  supabase_url: string;
  supabase_anon_key: string;
  beta_credits: number;
  max_pdf_mb: number;
  max_pages: number;
  /** Payment provider for credit packs; "" (or absent on older servers) = no shop. */
  payments?: PaymentProvider;
}

export interface MockLoginResponse {
  access_token: string;
  token_type: string;
  user: { id: string; email: string; role: string; name: string };
}

export interface MeResponse {
  id: string;
  email: string;
  name: string;
  role: "user" | "admin";
  beta: boolean;
  /** null in admin_key mode (credits are not counted for the single operator). */
  credits: number | null;
  studies: number;
  locked: number;
  auth_mode: ClientConfig["auth_mode"];
}

export type JobStatus = "queued" | "running" | "succeeded" | "rejected" | "failed";

export interface ExtractionJob {
  id: string;
  status: JobStatus;
  filename: string;
  size_bytes: number;
  pages: number | null;
  metadata: PaperMetadata;
  study_id: string | null;
  error_code: string | null;
  error_message: string | null;
  model: string | null;
  credits_charged: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface LedgerEntry {
  id: number;
  delta: number;
  reason: "purchase" | "extraction" | "refund" | "grant_beta" | "adjust_admin";
  balance_after: number;
  job_id: string | null;
  note: string;
  created_at: string;
}

export interface AccountExport {
  exported_at: string;
  version: string;
  user: { id: string; email: string; name: string };
  studies: StudyDatabaseEntry[];
  jobs: ExtractionJob[];
  ledger: LedgerEntry[];
}

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: string;
  beta: boolean;
  credits: number;
  created_at: string;
  last_seen_at: string | null;
  studies: number;
}

export interface AdminUsage {
  days: number;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  per_user: { user_id: string; calls: number; estimated_cost_usd: number }[];
  outcomes: Record<string, number>;
  price_table: { input_per_mtok: number; output_per_mtok: number };
}

export interface HealthResponse {
  status: string;
  version: string;
  /** null in the multi-user modes (per-user counts come from /api/me). */
  study_count: number | null;
  llm_configured?: boolean;
  anthropic_configured?: boolean;
  notion_configured: boolean;
  /** Storage backend in use; "sqlite" means records survive a restart. */
  storage?: string;
  storage_path?: string;
  llm_ready?: boolean;
  demo_mode?: boolean;
  auth_mode?: ClientConfig["auth_mode"];
  extraction_mode?: ExtractionMode;
}

export interface NotionSyncResponse {
  synced: number;
  failed: number;
  errors: string[];
  message: string;
}

// ---------------------------------------------------------------------------
// Payments: credit packs (8.0, backend/payments.py)
// ---------------------------------------------------------------------------

export type PaymentProvider = "" | "payos" | "mock";

export interface CreditPack {
  id: string;
  credits: number;
  price_vnd: number;
}

export interface PacksResponse {
  enabled: boolean;
  provider: PaymentProvider;
  currency: "VND";
  packs: CreditPack[];
}

export type OrderStatus = "pending" | "paid" | "cancelled" | "expired" | "failed";

export interface PaymentOrder {
  id: string;
  /** Numeric code the payment provider knows the order by (shown to the buyer). */
  order_code: number;
  pack_id: string;
  credits: number;
  amount: number;
  currency: string;
  status: OrderStatus;
  provider: string;
  /** Payment page; empty unless the order is still pending. */
  checkout_url: string;
  /** Bank reference once paid; "UNDERPAID <amount> <ref>" when too little arrived. */
  payment_reference: string;
  created_at: string;
  paid_at: string | null;
  expires_at: string | null;
  /** Only in the operator's list. */
  email?: string;
}

export interface AdminOrders {
  orders: PaymentOrder[];
  paid_orders: number;
  paid_amount_vnd: number;
  paid_credits: number;
}
