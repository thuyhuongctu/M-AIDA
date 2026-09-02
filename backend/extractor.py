"""
Statistical parameter extractor for M-AIDA v7.1.1.

Uses a pluggable :class:`~engines.ExtractionEngine` (BYOK provider adapter) to
locate and parse effect-size statistics from academic PDF text, then converts
them to Pearson's r following:

    Peterson, R. A., & Brown, S. P. (2005). On the use of beta coefficients in
    meta-analysis. Journal of Applied Psychology, 90(1), 175-181.
    https://doi.org/10.1037/0021-9010.90.1.175
"""

from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any

from engines import EngineError, ExtractionEngine, make_engine
from models import (
    DoiMeasure,
    DplPhase,
    ExtractedEffect,
    IcrvRegime,
    PerformanceMeasure,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Confidence thresholds (Peterson & Brown, 2005)
# ---------------------------------------------------------------------------
CONFIDENCE_DIRECT_R: float = 1.0   # Pearson r reported directly
CONFIDENCE_FROM_T: float = 0.8     # Derived from t-statistic + df
CONFIDENCE_FROM_BETA: float = 0.6  # Derived from standardised β coefficient
CONFIDENCE_REVIEW_THRESHOLD: float = 0.7  # Flag for PI review if below this
PDF_TEXT_LIMIT: int = 40_000  # characters of PDF text sent to the model (documented, 7.2.0)

# ---------------------------------------------------------------------------
# Extraction system prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are a precision meta-analysis data extraction assistant
specialised in international business research. Your job is to identify and
extract statistical parameters that quantify the relationship between a firm's
degree of internationalisation (DOI) and firm performance.

Extract ONLY the following statistics:
- N  : total sample size
- r  : Pearson's product-moment correlation coefficient (PREFERRED)
- t  : t-statistic (report alongside df if both present)
- df : degrees of freedom
- β  : standardised regression coefficient (beta)
- p# : number of predictor variables in the regression model that the reported
       t or β comes from (focal variable plus all controls, excluding the
       intercept); null when the statistic is not from a regression or the
       count cannot be determined from the text
- F  : F-statistic (for context; not directly convertible)
- p  : reported p-value (exact or inequality, e.g. p < 0.05)
- CI : 95 % confidence interval for r if reported
- evidence_page  : 1-based page number where the focal statistic appears
- evidence_quote : the VERBATIM sentence (or table caption row) from the text
                   that contains the focal statistic. Copy it exactly; do not
                   paraphrase. If you cannot quote it, return null statistics.
- n_evidence_page  : 1-based page number where the sample size is stated
- n_evidence_quote : the VERBATIM sentence stating the sample size. Same rule:
                     if you cannot quote it, return null sample_n. Never round
                     or estimate a sample size.

Also classify the study on these two text-determinable dimensions, and report
the data window:
- doi_measure : how internationalisation is measured -
    FSTS (foreign sales/total sales) | GEO (geographic scope/country count) |
    EXP (export intensity or exporter dummy) | FDI (outward-FDI-based) |
    COMP (composite/entropy index, e.g. TNI) | OTH (other)
- performance_measure : how firm performance is measured -
    ACC (accounting: ROA/ROE/ROS) | MKT (market: Tobin's Q, stock returns) |
    LAB (labour productivity) | MIX (composite/mixed)
- sample_start, sample_end : first and last calendar year of the sample data

Do NOT attempt to code ICRV regime, DPL phase, or cDAI: those moderators are
assigned by the Principal Investigator from external lookup tables (World Bank
WGI Rule of Law; World Bank DAI / ITU DDI; median data year), not from the
paper's text.

Return a single JSON object - no markdown, no prose - with exactly these keys:
{
  "sample_n": <int|null>,
  "sample_start": <int|null>,
  "sample_end": <int|null>,
  "effect_r": <float|null>,
  "effect_t": <float|null>,
  "effect_beta": <float|null>,
  "effect_df": <int|null>,
  "n_predictors": <int|null>,
  "p_value": <float|null>,
  "ci_lower": <float|null>,
  "ci_upper": <float|null>,
  "evidence_page": <int|null>,
  "evidence_quote": <string|null>,
  "n_evidence_page": <int|null>,
  "n_evidence_quote": <string|null>,
  "doi_measure": <"FSTS"|"GEO"|"EXP"|"FDI"|"COMP"|"OTH"|null>,
  "performance_measure": <"ACC"|"MKT"|"LAB"|"MIX"|null>
}

Rules:
1. If multiple models are reported, prefer the main/fully-specified model.
2. Prefer Pearson r over t over β for the primary effect size.
3. If a p-value is given as an inequality (e.g. "p < .001"), encode as the
   boundary value (0.001).
4. If the paper reports a negative t or β, preserve the sign.
5. Never hallucinate statistics; return null for any field not found.
6. evidence_quote is MANDATORY whenever any statistic is non-null, and
   n_evidence_quote is MANDATORY whenever sample_n is non-null: a record
   without verbatim evidence will be rejected by the pipeline.
"""


class MalformedLLMOutputError(ValueError):
    """The model's reply is not a JSON object with the expected field types.

    LLM output is untrusted input. A reply that is not JSON, or that carries a
    non-numeric value where a number is required, is rejected with a visible
    error (HTTP 422) instead of silently producing an empty record or an
    internal server error (7.2.0, findings C1).
    """


#: Fields the model must return as numbers (or null). Numeric strings such as
#: "0.35" are coerced; anything else is a MalformedLLMOutputError.
NUMERIC_LLM_FIELDS: tuple[str, ...] = (
    "effect_r", "effect_t", "effect_beta", "effect_df", "sample_n",
    "sample_start", "sample_end", "p_value", "ci_lower", "ci_upper",
    "n_predictors", "evidence_page", "n_evidence_page",
)

#: Primary statistics a PI may correct; every derived quantity (r, variance,
#: metric_type, estimand_source, source_controls, df_source, lambda_applied,
#: r_source, beta_outside_pb_domain) is recomputed from them, never edited.
PRIMARY_STAT_FIELDS: tuple[str, ...] = (
    "effect_r", "effect_t", "effect_df", "effect_beta", "n_predictors", "sample_n",
)


def coerce_numeric_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``raw`` with NUMERIC_LLM_FIELDS parsed to numbers.

    ``None``/"" stay ``None``; numeric strings are parsed; booleans and other
    types raise MalformedLLMOutputError naming the field.
    """
    out = dict(raw)
    for key in NUMERIC_LLM_FIELDS:
        if key not in out:
            continue
        val = out[key]
        if val is None or (isinstance(val, str) and not val.strip()):
            out[key] = None
            continue
        if isinstance(val, bool):
            raise MalformedLLMOutputError(f"{key}: boolean where a number is required")
        if isinstance(val, (int, float)):
            continue
        if isinstance(val, str):
            try:
                out[key] = float(val.strip().replace(",", ""))
                continue
            except ValueError:
                pass
        raise MalformedLLMOutputError(f"{key}: {val!r} is not numeric")
    return out


class EvidenceMissingError(ValueError):
    """The model proposed statistics without verbatim evidence (finding E1).

    A record whose numbers cannot be traced to a page and sentence in the
    source PDF is indistinguishable from a default; it is rejected at the
    gate, not created-and-flagged.
    """


class StatisticalExtractor:
    """Wraps an extraction engine to extract effect sizes from PDF text.

    Usage::

        extractor = StatisticalExtractor(api_key="provider-key")  # legacy path
        extractor = StatisticalExtractor(engine=my_engine)         # injected
        effect = extractor.extract_from_text(pdf_text, metadata)
    """

    DEFAULT_MODEL = ""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        *,
        engine: ExtractionEngine | None = None,
    ) -> None:
        if engine is not None:
            self._engine = engine
        else:
            if not api_key:
                raise ValueError(
                    "StatisticalExtractor requires either an api_key or an engine"
                )
            self._engine = make_engine(
                "anthropic", api_key=api_key, model=model or self.DEFAULT_MODEL
            )
        self._model = self._engine.model

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def extract_from_text(
        self, text: str, metadata: dict[str, Any]
    ) -> ExtractedEffect:
        """Run LLM extraction on plain text from a PDF and return an effect.

        Args:
            text: Full text content extracted from the PDF.
            metadata: Pre-known bibliographic fields (title, authors, year,
                country, doi, …).

        Returns:
            An ``ExtractedEffect`` with all parseable fields populated.
        """
        raw = self._call_llm(text, metadata)
        effect = self._build_effect(raw, metadata)
        # The prompt carries at most PDF_TEXT_LIMIT characters; a table that
        # sits beyond the cut is invisible to the model, so the record says so.
        effect.text_truncated = len(text) > PDF_TEXT_LIMIT
        return effect

    # ------------------------------------------------------------------
    # Effect-size conversion formulas
    # ------------------------------------------------------------------

    @staticmethod
    def clamp_r(r: float) -> float:
        """Defensive bound: a Pearson correlation must lie in [-1, 1].

        The t conversion is bounded by construction; the Peterson & Brown
        beta approximation is not, so out-of-range inputs are capped here
        (added in 7.1.2; such records are always flagged for review).
        """
        return max(-1.0, min(1.0, r))

    @staticmethod
    def compute_r_from_t(t: float, df: int) -> float:
        """Convert a t-statistic to Pearson's r.

        Formula (Cohen, 1988):
            r = sqrt( t² / (t² + df) )

        The sign of t is preserved in the returned r.
        """
        t_sq = t * t
        r_unsigned = math.sqrt(t_sq / (t_sq + df))
        return r_unsigned if t >= 0 else -r_unsigned

    #: Peterson & Brown (2005) derived their approximation for |β| <= 0.5;
    #: outside this domain the imputation is undefined and must not be used.
    PB_BETA_DOMAIN = 0.5

    @staticmethod
    def convert_beta_to_r(beta: float) -> float | None:
        """Approximate Pearson's r from a standardised regression coefficient.

        Full Peterson & Brown (2005) formula:

            r = 0.98·β + 0.05·λ,   λ = 1 if β >= 0, else 0

        Returns ``None`` when |β| > 0.5: the approximation was derived only
        for that domain, so such records carry no usable effect size and are
        excluded from conversion (they surface as flagged, unconverted
        records: not as clamped numbers).
        """
        if abs(beta) > StatisticalExtractor.PB_BETA_DOMAIN:
            return None
        lam = 1.0 if beta >= 0 else 0.0
        return StatisticalExtractor.clamp_r(0.98 * beta + 0.05 * lam)

    @staticmethod
    def degrees_of_freedom(sample_n: int, n_predictors: int) -> int:
        """Residual df for a t-statistic taken from a regression model.

            df = n − p − 1

        where p counts every predictor in the model (focal variable plus
        controls, excluding the intercept). The bivariate case p = 1 reduces
        to the familiar n − 2; a bare n − 2 default is wrong whenever the t
        comes from a multiple regression and is never applied here.
        """
        return sample_n - n_predictors - 1

    @staticmethod
    def variance_of_r(
        r: float,
        *,
        sample_n: int | None = None,
        df: int | None = None,
        metric_type: str = "zero_order",
    ) -> float:
        """Sampling variance of a correlation, by metric type.

        Zero-order (Pearson) correlation:
            Var(r)   = (1 − r²)² / (n − 1)
        Partial correlation (Aloe & Thompson, 2013):
            Var(r_p) = (1 − r_p²)² / df,   df = n − p − 1

        The two denominators differ, so pooling weights computed with the
        zero-order formula are wrong for partial correlations. ``metric_type``
        is therefore required: there is no silent default across types.
        """
        if metric_type == "zero_order":
            if sample_n is None or sample_n <= 1:
                raise ValueError("zero-order variance requires sample_n > 1")
            return (1.0 - r * r) ** 2 / (sample_n - 1)
        if metric_type == "partial":
            if df is None or df <= 0:
                raise ValueError("partial-correlation variance requires df > 0")
            return (1.0 - r * r) ** 2 / df
        raise ValueError(f"unsupported metric_type: {metric_type!r}")

    @staticmethod
    def variance_of_z(
        *, sample_n: int | None = None, df: int | None = None, metric_type: str = "zero_order"
    ) -> float | None:
        """Sampling variance on the Fisher-z scale, the quantity the three-level
        model actually weights with (7.2.0; same formulas as analysis/effect_size.py):

            zero-order: Var(z)   = 1 / (n − 3)
            partial:    Var(z_p) = 1 / (df − 1)

        Returns ``None`` when the denominator is not positive.
        """
        if metric_type == "zero_order":
            return 1.0 / (sample_n - 3) if sample_n is not None and sample_n > 3 else None
        if metric_type == "partial":
            return 1.0 / (df - 1) if df is not None and df > 1 else None
        return None

    @staticmethod
    def derive_from_primary(fields: dict[str, Any]) -> dict[str, Any]:
        """Re-derive every derived quantity from the primary statistics.

        Input keys: effect_r, effect_t, effect_df, effect_beta, n_predictors,
        sample_n (any may be None). Precedence r > t > beta, as at extraction.
        Output keys: effect_r (canonical), effect_df, df_source, df_imputed,
        metric_type, estimand_source, source_controls, lambda_applied,
        beta_outside_pb_domain, variance_r, variance_formula, variance_z,
        r_source, confidence. Used by both live extraction and PI overrides so
        the two paths cannot drift (7.2.0, findings A1–A3).
        """
        S = StatisticalExtractor
        effect_r = fields.get("effect_r")
        effect_t = fields.get("effect_t")
        effect_beta = fields.get("effect_beta")
        effect_df = fields.get("effect_df")
        n_predictors = fields.get("n_predictors")
        n_predictors = int(n_predictors) if n_predictors is not None else None
        sample_n = fields.get("sample_n")
        sample_n = int(sample_n) if sample_n is not None else None
        effect_df = int(effect_df) if effect_df is not None else None

        df_source: str | None = "reported" if effect_df is not None else None
        df_imputed = False
        if (
            (effect_t is not None or effect_beta is not None)
            and effect_df is None
            and sample_n is not None
            and n_predictors is not None
            and sample_n - n_predictors - 1 > 0
        ):
            effect_df = S.degrees_of_freedom(sample_n, n_predictors)
            df_source = "derived"
            df_imputed = True

        out: dict[str, Any] = dict(
            effect_r=None, effect_df=effect_df, df_source=df_source, df_imputed=df_imputed,
            metric_type=None, estimand_source=None, source_controls=None,
            lambda_applied=False, beta_outside_pb_domain=False,
            variance_r=None, variance_formula=None, variance_z=None,
            r_source=None, confidence=0.0,
        )
        if effect_r is not None:
            out.update(effect_r=S.clamp_r(float(effect_r)), confidence=CONFIDENCE_DIRECT_R,
                       metric_type="zero_order", estimand_source="observed",
                       source_controls=False, r_source="reported")
        elif effect_t is not None and effect_df is not None:
            mt = "zero_order" if n_predictors is not None and n_predictors <= 1 else "partial"
            out.update(effect_r=S.compute_r_from_t(float(effect_t), effect_df),
                       confidence=CONFIDENCE_FROM_T, metric_type=mt, estimand_source="observed",
                       source_controls=(mt == "partial"), r_source="derived")
        elif effect_beta is not None:
            r = S.convert_beta_to_r(float(effect_beta))
            if r is None:
                out.update(beta_outside_pb_domain=True)
            else:
                # lambda_applied records whether the +0.05·λ term was actually
                # added, i.e. only for non-negative beta (7.2.0, finding C2).
                out.update(effect_r=r, confidence=CONFIDENCE_FROM_BETA,
                           lambda_applied=float(effect_beta) >= 0,
                           metric_type="zero_order", estimand_source="imputed_pb2005",
                           source_controls=True, r_source="imputed")
        r = out["effect_r"]
        if r is not None and out["metric_type"] == "partial" and effect_df:
            out.update(variance_r=S.variance_of_r(r, df=effect_df, metric_type="partial"),
                       variance_formula="(1 - r^2)^2 / df",
                       variance_z=S.variance_of_z(df=effect_df, metric_type="partial"))
        elif r is not None and out["metric_type"] == "zero_order" and sample_n is not None and sample_n > 1:
            out.update(variance_r=S.variance_of_r(r, sample_n=sample_n, metric_type="zero_order"),
                       variance_formula="(1 - r^2)^2 / (n - 1)",
                       variance_z=S.variance_of_z(sample_n=sample_n, metric_type="zero_order"))
        return out

    @staticmethod
    def resolve_overridden_r(
        data: dict[str, Any], overridden_keys: Any
    ) -> float | None:
        """Resolve the canonical Pearson r after a PI override."""
        keys = set(overridden_keys)
        if "effect_r" in keys:
            r = data.get("effect_r")
            return None if r is None else StatisticalExtractor.clamp_r(float(r))
        if (
            ("effect_t" in keys or "effect_df" in keys)
            and data.get("effect_t") is not None
            and data.get("effect_df") is not None
        ):
            return StatisticalExtractor.compute_r_from_t(
                float(data["effect_t"]), int(data["effect_df"])
            )
        if "effect_beta" in keys and data.get("effect_beta") is not None:
            return StatisticalExtractor.convert_beta_to_r(float(data["effect_beta"]))
        return data.get("effect_r")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_llm(self, text: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """Send the extraction prompt to the engine and parse the JSON response."""
        user_content = (
            f"Paper metadata provided by the researcher:\n{json.dumps(metadata)}\n\n"
            f"---BEGIN PDF TEXT---\n{text[:PDF_TEXT_LIMIT]}\n---END PDF TEXT---\n\n"
            "Extract the statistical parameters as described and return valid JSON."
        )

        try:
            raw_text = self._engine.complete(
                system=_SYSTEM_PROMPT, user=user_content, max_tokens=1024
            )
        except EngineError as exc:
            logger.error("Extraction engine call failed: %s", exc)
            raise

        # Strip accidental markdown fences that models sometimes emit
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON output: %s\n%s", exc, raw_text)
            raise MalformedLLMOutputError(f"model reply is not JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise MalformedLLMOutputError("model reply is not a JSON object")
        return coerce_numeric_fields(parsed)

    def _build_effect(
        self, raw: dict[str, Any], metadata: dict[str, Any]
    ) -> ExtractedEffect:
        """Resolve the canonical Pearson r and compute confidence / verification flag."""
        raw = coerce_numeric_fields(raw)
        effect_r: float | None = raw.get("effect_r")
        effect_t: float | None = raw.get("effect_t")
        effect_beta: float | None = raw.get("effect_beta")
        effect_df_raw = raw.get("effect_df")
        n_predictors_raw = raw.get("n_predictors")
        n_predictors: int | None = (
            int(n_predictors_raw) if n_predictors_raw is not None else None
        )
        sample_n_for_df = raw.get("sample_n")

        d = self.derive_from_primary({
            "effect_r": effect_r, "effect_t": effect_t, "effect_beta": effect_beta,
            "effect_df": int(effect_df_raw) if effect_df_raw is not None else None,
            "n_predictors": n_predictors, "sample_n": sample_n_for_df,
        })
        computed_r: float | None = d["effect_r"]
        effect_df: int | None = d["effect_df"]
        df_source: str | None = d["df_source"]
        df_imputed: bool = d["df_imputed"]
        confidence: float = d["confidence"]
        beta_outside_pb_domain: bool = d["beta_outside_pb_domain"]
        lambda_applied: bool = d["lambda_applied"]
        metric_type: str | None = d["metric_type"]
        estimand_source: str | None = d["estimand_source"]
        source_controls: bool | None = d["source_controls"]
        variance_r: float | None = d["variance_r"]
        variance_formula: str | None = d["variance_formula"]
        variance_z: float | None = d["variance_z"]

        evidence_page_raw = raw.get("evidence_page")
        evidence_page: int | None = (
            int(evidence_page_raw) if evidence_page_raw is not None else None
        )
        evidence_quote: str | None = (raw.get("evidence_quote") or "").strip() or None
        n_evidence_page_raw = raw.get("n_evidence_page")
        n_evidence_page: int | None = (
            int(n_evidence_page_raw) if n_evidence_page_raw is not None else None
        )
        n_evidence_quote: str | None = (
            (raw.get("n_evidence_quote") or "").strip() or None
        )
        if computed_r is not None and not evidence_quote:
            # E1 gate: statistics with no verbatim evidence are rejected
            # outright: an unevidenced number is indistinguishable from a
            # default value.
            raise EvidenceMissingError(
                "statistics proposed with no evidence_quote"
            )
        if sample_n_for_df is not None and not n_evidence_quote:
            # Same gate for n: a guessed sample size is a guessed WEIGHT, and
            # it distorts every other study in the pooled model.
            raise EvidenceMissingError(
                "sample_n proposed with no n_evidence_quote"
            )

        # Per-quantity provenance: r by conversion path (from derive_from_primary);
        # n is always reported at live extraction (the evidence gate guarantees it).
        r_source: str | None = d["r_source"]
        n_source: str | None = "reported" if sample_n_for_df is not None else None

        requires_verification = (
            confidence < CONFIDENCE_REVIEW_THRESHOLD
            or beta_outside_pb_domain
            or df_imputed
        )

        doi_measure: DoiMeasure | None = _safe_literal(
            raw.get("doi_measure"), ("FSTS", "GEO", "EXP", "FDI", "COMP", "OTH")
        )
        performance_measure: PerformanceMeasure | None = _safe_literal(
            raw.get("performance_measure"), ("ACC", "MKT", "LAB", "MIX")
        )
        # ICRV regime, DPL phase, and cDAI are PI-assigned from external lookup
        # tables during verification; the LLM never codes them.
        icrv_regime: IcrvRegime | None = None
        dpl_phase: DplPhase | None = None
        cdai_score: float | None = None

        p_raw = raw.get("p_value")
        p_value: float | None = float(p_raw) if p_raw is not None else None

        sample_n_raw = raw.get("sample_n")
        sample_n: int | None = int(sample_n_raw) if sample_n_raw is not None else None
        start_raw = raw.get("sample_start")
        sample_start: int | None = int(start_raw) if start_raw is not None else None
        end_raw = raw.get("sample_end")
        sample_end: int | None = int(end_raw) if end_raw is not None else None

        ci_lower_raw = raw.get("ci_lower")
        ci_upper_raw = raw.get("ci_upper")

        return ExtractedEffect(
            study_id=str(uuid.uuid4()),
            paper_title=metadata.get("title", ""),
            authors=metadata.get("authors", ""),
            year=int(metadata.get("year", 0)),
            country=metadata.get("country", ""),
            sample_n=sample_n,
            sample_start=sample_start,
            sample_end=sample_end,
            effect_r=computed_r,
            effect_t=effect_t,
            effect_beta=effect_beta,
            effect_df=effect_df,
            p_value=p_value,
            ci_lower=float(ci_lower_raw) if ci_lower_raw is not None else None,
            ci_upper=float(ci_upper_raw) if ci_upper_raw is not None else None,
            doi_measure=doi_measure,
            performance_measure=performance_measure,
            icrv_regime=icrv_regime,
            cdai_score=cdai_score,
            dpl_phase=dpl_phase,
            n_predictors=n_predictors,
            r_source=r_source,
            n_source=n_source,
            evidence_page=evidence_page,
            evidence_quote=evidence_quote,
            n_evidence_page=n_evidence_page,
            n_evidence_quote=n_evidence_quote,
            metric_type=metric_type,
            estimand_source=estimand_source,
            source_controls=source_controls,
            df_source=df_source,
            lambda_applied=lambda_applied,
            variance_r=variance_r,
            variance_formula=variance_formula,
            variance_z=variance_z,
            extraction_confidence=confidence,
            requires_verification=requires_verification,
            df_imputed=df_imputed,
            beta_outside_pb_domain=beta_outside_pb_domain,
            pi_locked=False,
            extracted_at=datetime.now(timezone.utc),
            locked_at=None,
        )


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _safe_literal(value: Any, allowed: tuple[str, ...]) -> Any | None:
    """Return value if it is one of allowed strings, else None."""
    if value in allowed:
        return value
    return None
