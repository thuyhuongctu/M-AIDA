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
from datetime import datetime
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
        return self._build_effect(raw, metadata)

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
        records — not as clamped numbers).
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
        is therefore required — there is no silent default across types.
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
            f"---BEGIN PDF TEXT---\n{text[:40_000]}\n---END PDF TEXT---\n\n"
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
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON output: %s\n%s", exc, raw_text)
            return {}

    def _build_effect(
        self, raw: dict[str, Any], metadata: dict[str, Any]
    ) -> ExtractedEffect:
        """Resolve the canonical Pearson r and compute confidence / verification flag."""
        effect_r: float | None = raw.get("effect_r")
        effect_t: float | None = raw.get("effect_t")
        effect_beta: float | None = raw.get("effect_beta")
        effect_df: int | None = raw.get("effect_df")

        confidence: float
        computed_r: float | None = None

        n_predictors_raw = raw.get("n_predictors")
        n_predictors: int | None = (
            int(n_predictors_raw) if n_predictors_raw is not None else None
        )

        sample_n_for_df = raw.get("sample_n")
        df_source: str | None = "reported" if effect_df is not None else None
        df_imputed = False
        if (
            (effect_t is not None or effect_beta is not None)
            and effect_df is None
            and sample_n_for_df is not None
            and n_predictors is not None
            and int(sample_n_for_df) - n_predictors - 1 > 0
        ):
            # df = n − p − 1. Without a predictor count there is no valid
            # imputation: the record stays unconverted and flagged instead
            # of silently receiving the bivariate n − 2.
            effect_df = self.degrees_of_freedom(int(sample_n_for_df), n_predictors)
            df_source = "derived"
            df_imputed = True

        beta_outside_pb_domain = False
        lambda_applied = False
        metric_type: str | None = None
        estimand_source: str | None = None
        source_controls: bool | None = None

        if effect_r is not None:
            computed_r = self.clamp_r(effect_r)
            confidence = CONFIDENCE_DIRECT_R
            # Directly reported r in this literature is normally the
            # correlation-matrix (zero-order) value; the PI confirms at Gate 2.
            metric_type = "zero_order"
            estimand_source = "observed"
            source_controls = False
        elif effect_t is not None and effect_df is not None:
            computed_r = self.compute_r_from_t(effect_t, effect_df)
            confidence = CONFIDENCE_FROM_T
            # A t taken from a coefficient in a multiple regression yields a
            # partial correlation; only the bivariate p = 1 case is zero-order.
            metric_type = (
                "zero_order"
                if n_predictors is not None and n_predictors <= 1
                else "partial"
            )
            estimand_source = "observed"
            source_controls = metric_type == "partial"
        elif effect_beta is not None:
            computed_r = self.convert_beta_to_r(effect_beta)
            beta_outside_pb_domain = computed_r is None
            if computed_r is not None:
                confidence = CONFIDENCE_FROM_BETA
                lambda_applied = True
                # Peterson & Brown calibrated the imputation against observed
                # ZERO-ORDER correlations (the .05·λ term exists because of
                # that fit), so the estimand is zero-order. The imputed origin
                # lives in estimand_source; such records feed sensitivity
                # analyses only, never the main model.
                metric_type = "zero_order"
                estimand_source = "imputed_pb2005"
                source_controls = True
            else:
                confidence = 0.0
        else:
            computed_r = None
            confidence = 0.0

        variance_r: float | None = None
        variance_formula: str | None = None
        if computed_r is not None and metric_type == "partial" and effect_df:
            variance_r = self.variance_of_r(
                computed_r, df=effect_df, metric_type="partial"
            )
            variance_formula = "(1 - r^2)^2 / df"
        elif (
            computed_r is not None
            and metric_type == "zero_order"
            and sample_n_for_df is not None
            and int(sample_n_for_df) > 1
        ):
            variance_r = self.variance_of_r(
                computed_r,
                sample_n=int(sample_n_for_df),
                metric_type="zero_order",
            )
            variance_formula = "(1 - r^2)^2 / (n - 1)"

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
            metric_type=metric_type,
            estimand_source=estimand_source,
            source_controls=source_controls,
            df_source=df_source,
            lambda_applied=lambda_applied,
            variance_r=variance_r,
            variance_formula=variance_formula,
            extraction_confidence=confidence,
            requires_verification=requires_verification,
            df_imputed=df_imputed,
            beta_outside_pb_domain=beta_outside_pb_domain,
            pi_locked=False,
            extracted_at=datetime.utcnow(),
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
