"""
Pydantic data models for M-AIDA v7.1.1.

All models represent domain objects for the internationalization-performance
meta-analysis pipeline: extracted effect sizes, verification decisions, and
Notion-synchronized study database entries.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Domain Enums / Literal Types
# ---------------------------------------------------------------------------

# Codes below mirror the canonical P6 analysis database (p6/data/p6_study_database.csv)
# and the dissertation's construct definitions; keep the three artefacts in sync.
#
# DOI (degree-of-internationalisation) measure reported by the primary study:
#   FSTS = foreign sales / total sales; GEO = geographic scope / country count;
#   EXP  = export intensity or exporter dummy; FDI = outward-FDI-based measure;
#   COMP = composite / entropy index (e.g. TNI); OTH = other.
DoiMeasure = Literal["FSTS", "GEO", "EXP", "FDI", "COMP", "OTH"]
# Firm-performance construct: ACC = accounting (ROA/ROE/ROS); MKT = market
# (Tobin's Q, returns); LAB = labour productivity; MIX = composite/mixed.
PerformanceMeasure = Literal["ACC", "MKT", "LAB", "MIX"]
# ICRV - Institutional Context Regime Variation. Assigned by the PI from the
# sample country's World Bank WGI Rule of Law score (2023 vintage), NOT
# extracted by the LLM:
#   I   = Advanced-Innovation        (WGI > +0.80)
#   II  = Upper-Middle               (0 to +0.80)
#   III = Emerging                   (-0.50 to 0)
#   FR  = Frontier / SIDS            (<= -0.50, or small-island state)
#   MX  = Multi-country pooled       (no modal regime >= 60 %)
IcrvRegime = Literal["I", "II", "III", "FR", "MX"]
# DPL phase, assigned by the PI from the study's median data year:
#   PRE = Precede, SPN = Span, FOL = Follow.
DplPhase = Literal["PRE", "SPN", "FOL"]
# What kind of correlation the canonical r is. Zero-order and partial
# correlations answer different questions AND have different sampling
# variances, so they must never be pooled under one formula:
#   zero_order  = bivariate Pearson r (correlation-matrix value)
#   partial     = from a coefficient in a multiple regression (t → r)
#   semipartial = semipartial correlation, kept separate; not poolable with
#                 either of the above without an explicit decision
MetricType = Literal["zero_order", "partial", "semipartial"]
# Provenance of the degrees of freedom paired with a t-statistic:
#   reported = taken verbatim from the paper
#   derived  = computed as n − p − 1 from sample_n and n_predictors
DfSource = Literal["reported", "derived"]
# Whether the canonical r is an observed statistic or an imputed estimate.
# metric_type describes the ESTIMAND; estimand_source describes the ORIGIN —
# two different things that must never be conflated:
#   observed       = reported r, or r computed exactly from t and df
#   imputed_pb2005 = estimated from β via Peterson & Brown (2005); feeds
#                    sensitivity analyses only, never the main model
EstimandSource = Literal["observed", "imputed_pb2005"]


# ---------------------------------------------------------------------------
# Core Extracted Effect Model
# ---------------------------------------------------------------------------


class ExtractedEffect(BaseModel):
    """One study-level effect size record produced by the LLM extractor.

    Fields prefixed with ``effect_`` are the raw statistics as reported in the
    paper.  ``effect_r`` is the canonical Pearson r used in the meta-analysis;
    the other ``effect_*`` fields are intermediary values from which r may be
    computed when a direct correlation is not reported.
    """

    study_id: str = Field(..., description="UUID assigned at extraction time")
    paper_title: str
    authors: str
    year: int
    country: str = Field(..., description="Focal country / region of sample")

    # Sample information
    sample_n: int | None = Field(None, description="Total sample size (N)")
    sample_start: int | None = Field(
        None, description="First year of the study's data window"
    )
    sample_end: int | None = Field(
        None, description="Last year of the study's data window"
    )

    # Raw reported statistics
    effect_r: float | None = Field(
        None,
        description="Pearson's r as directly reported (preferred); confidence = 1.0",
    )
    effect_t: float | None = Field(
        None, description="t-statistic; converted to r via Cohen (1988)"
    )
    effect_beta: float | None = Field(
        None,
        description="Standardised regression coefficient β; converted via P&B (2005)",
    )
    effect_df: int | None = Field(
        None, description="Degrees of freedom paired with t-statistic"
    )
    n_predictors: int | None = Field(
        None,
        ge=1,
        description=(
            "Number of predictors p in the regression model supplying t or β "
            "(focal variable plus controls, excluding intercept); df = n − p − 1"
        ),
    )
    metric_type: MetricType | None = Field(
        None,
        description=(
            "Kind of correlation the canonical r is: zero_order | partial | "
            "semipartial. Determines the sampling-variance formula; PI-confirmed "
            "at Gate 2."
        ),
    )
    estimand_source: EstimandSource | None = Field(
        None,
        description=(
            "observed = reported r or exact t→r conversion; imputed_pb2005 = "
            "estimated from β via Peterson & Brown (2005) — sensitivity "
            "analyses only, never the main pooling model"
        ),
    )
    source_controls: bool | None = Field(
        None,
        description=(
            "True when the source statistic came from a model controlling for "
            "other variables (t from multiple regression, standardised β); "
            "False for a plain correlation-matrix r"
        ),
    )
    df_source: DfSource | None = Field(
        None,
        description="Whether effect_df was reported verbatim or derived as n − p − 1",
    )
    lambda_applied: bool = Field(
        False,
        description=(
            "True when the +0.05·λ term of Peterson & Brown (2005) was applied "
            "in the β → r conversion (λ = 1 for β ≥ 0, else 0)"
        ),
    )
    variance_r: float | None = Field(
        None,
        description=(
            "Sampling variance of r: (1 − r²)²/(n − 1) for zero-order, "
            "(1 − r²)²/df for partial correlations"
        ),
    )
    variance_formula: str | None = Field(
        None,
        description="Exact variance formula applied to this record, for audit",
    )
    p_value: float | None = Field(None, description="Reported p-value")
    ci_lower: float | None = Field(
        None, description="Lower bound of 95 % confidence interval for r"
    )
    ci_upper: float | None = Field(
        None, description="Upper bound of 95 % confidence interval for r"
    )

    # Moderator coding variables (dissertation-specific)
    doi_measure: DoiMeasure | None = Field(
        None, description="Degree-of-internationalisation measure used"
    )
    performance_measure: PerformanceMeasure | None = Field(
        None, description="Firm-performance construct used"
    )
    icrv_regime: IcrvRegime | None = Field(
        None,
        description=(
            "ICRV institutional regime (I/II/III/FR/MX). PI-assigned from the "
            "WGI Rule of Law lookup table (2023 vintage); never LLM-extracted."
        ),
    )
    cdai_score: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description=(
            "Country Digital Adoption Index, 0-1 (World Bank DAI 2016, or ITU "
            "DDI rescaled), assigned by the PI from the study's median data "
            "year; never LLM-extracted."
        ),
    )
    dpl_phase: DplPhase | None = Field(
        None,
        description=(
            "Digital Paradox Lifecycle phase (PRE/SPN/FOL), derived by the PI "
            "from the study's median data year; never LLM-extracted."
        ),
    )

    # Extraction provenance
    extraction_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Confidence score: 1.0 = direct r; 0.8 = converted from t; "
            "0.6 = converted from β (Peterson & Brown, 2005)"
        ),
    )
    df_imputed: bool = Field(
        False,
        description=(
            "True when df was unreported and derived as n − p − 1 from "
            "sample_n and n_predictors (never as a bare n − 2)"
        ),
    )
    beta_outside_pb_domain: bool = Field(
        False,
        description=(
            "True when |beta| > 0.5, outside the Peterson & Brown (2005) "
            "derivation domain; such records receive no converted r and are "
            "excluded from pooling"
        ),
    )
    requires_verification: bool = Field(
        ...,
        description="True when confidence < 0.7 or ambiguous statistics detected",
    )
    pi_locked: bool = Field(
        False, description="True after Principal Investigator permanently locks entry"
    )
    derived_from: str | None = Field(
        None,
        description=(
            "study_id/effect_id of the prior-generation locked record this one "
            "was re-coded from. Locked records are never edited in place: a "
            "formula correction produces a NEW lock generation whose records "
            "point back to their v7.1.1 originals via this field."
        ),
    )
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    locked_at: datetime | None = None


# ---------------------------------------------------------------------------
# API Request / Response Models
# ---------------------------------------------------------------------------


class ExtractionRequest(BaseModel):
    """Payload sent to POST /api/extract.

    ``pdf_content`` is a Base64-encoded PDF byte string.  ``paper_metadata``
    carries any bibliographic information already known (title, DOI, etc.)
    before LLM extraction so the extractor can cross-check against the PDF.
    """

    pdf_content: str = Field(
        ..., description="Base64-encoded PDF binary content"
    )
    paper_metadata: dict = Field(
        default_factory=dict,
        description="Pre-known bibliographic metadata (title, year, doi, …)",
    )


class VerificationDecision(BaseModel):
    """PI verification payload sent to PATCH /api/studies/{id}/verify.

    ``field_overrides`` maps ExtractedEffect field names to corrected values so
    the PI can adjust any LLM-extracted statistic without re-running extraction.
    """

    study_id: str
    field_overrides: dict = Field(
        default_factory=dict,
        description="Map of field_name → corrected_value supplied by the PI",
    )
    pi_approved: bool = Field(
        False, description="True when PI accepts the (possibly overridden) record"
    )
    pi_notes: str = Field(
        "",
        description="Free-text notes from the PI recorded alongside the decision",
    )


class StudyDatabaseEntry(ExtractedEffect):
    """Extends ExtractedEffect with Notion synchronization metadata."""

    notion_page_id: str | None = Field(
        None, description="Notion page ID after successful sync"
    )
    pi_notes: str = ""
    machine_proposal: dict | None = Field(
        None,
        description=(
            "Immutable snapshot of the effect fields as first proposed by the "
            "model, captured at extraction time and never editable by PI "
            "overrides (7.1.2). Preserves the machine-vs-human distinction "
            "per record."
        ),
    )
