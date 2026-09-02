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

export interface HealthResponse {
  status: string;
  version: string;
  study_count: number;
  llm_configured?: boolean;
  anthropic_configured?: boolean;
  notion_configured: boolean;
  /** Storage backend in use; "sqlite" means records survive a restart. */
  storage?: string;
  storage_path?: string;
  llm_ready?: boolean;
  demo_mode?: boolean;
  extraction_mode?: ExtractionMode;
}

export interface NotionSyncResponse {
  synced: number;
  failed: number;
  errors: string[];
  message: string;
}
