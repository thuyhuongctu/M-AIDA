"""Unit tests for M-AIDA's effect-size conversion logic.

These tests pin the two published conversions the extractor relies on -
Cohen (1988) t -> r and Peterson & Brown (2005) beta -> r - plus the
three-level confidence scheme and its PI-review threshold. They give the
dissertation's reproducibility claim (Phụ lục B) an executable guarantee:
if a refactor silently changes a formula or a sign, CI fails.
"""

import math

import pytest

from extractor import (
    CONFIDENCE_DIRECT_R,
    CONFIDENCE_FROM_BETA,
    CONFIDENCE_FROM_T,
    CONFIDENCE_REVIEW_THRESHOLD,
    StatisticalExtractor,
)


# --------------------------------------------------------------------------- #
# Cohen (1988):  r = sqrt( t^2 / (t^2 + df) ), sign of t preserved
# --------------------------------------------------------------------------- #
class TestComputeRFromT:
    @pytest.mark.parametrize(
        "t, df, expected",
        [
            (2.0, 4, math.sqrt(0.5)),     # 4 / (4 + 4) = 0.5
            (3.0, 9, math.sqrt(0.5)),     # 9 / (9 + 9) = 0.5
            (1.0, 3, 0.5),                # 1 / (1 + 3) = 0.25 -> sqrt = 0.5
            (0.0, 10, 0.0),               # t = 0 -> r = 0
        ],
    )
    def test_magnitude_matches_cohen(self, t, df, expected):
        assert StatisticalExtractor.compute_r_from_t(t, df) == pytest.approx(expected)

    def test_sign_is_preserved(self):
        pos = StatisticalExtractor.compute_r_from_t(2.0, 4)
        neg = StatisticalExtractor.compute_r_from_t(-2.0, 4)
        assert pos > 0 and neg < 0
        assert neg == pytest.approx(-pos)

    def test_large_t_approaches_unity(self):
        r = StatisticalExtractor.compute_r_from_t(1000.0, 5)
        assert 0.99 < r <= 1.0

    def test_result_within_unit_interval(self):
        for t in (-50.0, -1.0, 0.0, 0.7, 12.0):
            r = StatisticalExtractor.compute_r_from_t(t, 8)
            assert -1.0 <= r <= 1.0


# --------------------------------------------------------------------------- #
# Peterson & Brown (2005):  r ~= 0.98 * beta  (sign preserved)
# --------------------------------------------------------------------------- #
class TestConvertBetaToR:
    @pytest.mark.parametrize(
        "beta, expected",
        [
            (0.5, 0.49),
            (-0.3, -0.294),
            (0.0, 0.0),
            (1.0, 0.98),
        ],
    )
    def test_linear_attenuation(self, beta, expected):
        assert StatisticalExtractor.convert_beta_to_r(beta) == pytest.approx(expected)

    def test_sign_is_preserved(self):
        assert StatisticalExtractor.convert_beta_to_r(-0.7) < 0
        assert StatisticalExtractor.convert_beta_to_r(0.7) > 0


# --------------------------------------------------------------------------- #
# Three-level confidence scheme and PI-review threshold
# --------------------------------------------------------------------------- #
class TestConfidenceScheme:
    def test_levels_are_strictly_ordered(self):
        assert CONFIDENCE_DIRECT_R > CONFIDENCE_FROM_T > CONFIDENCE_FROM_BETA

    def test_threshold_flags_beta_only(self):
        # beta-derived effects must be flagged for PI review; t- and r-derived
        # effects must not be.
        assert CONFIDENCE_FROM_BETA < CONFIDENCE_REVIEW_THRESHOLD
        assert CONFIDENCE_FROM_T >= CONFIDENCE_REVIEW_THRESHOLD
        assert CONFIDENCE_DIRECT_R >= CONFIDENCE_REVIEW_THRESHOLD

    def test_expected_canonical_values(self):
        assert (CONFIDENCE_DIRECT_R, CONFIDENCE_FROM_T, CONFIDENCE_FROM_BETA) == (1.0, 0.8, 0.6)
        assert CONFIDENCE_REVIEW_THRESHOLD == 0.7


# --------------------------------------------------------------------------- #
# resolve_overridden_r: a PI correction to an upstream statistic must
# propagate to effect_r (regression test for the verify_study contract)
# --------------------------------------------------------------------------- #
class TestResolveOverriddenR:
    def test_recompute_from_t_when_t_df_overridden(self):
        data = {"effect_r": 0.10, "effect_t": 2.0, "effect_df": 4, "effect_beta": None}
        r = StatisticalExtractor.resolve_overridden_r(data, {"effect_t", "effect_df"})
        assert r == pytest.approx(math.sqrt(0.5))  # not the stale 0.10

    def test_recompute_from_beta_when_beta_overridden(self):
        data = {"effect_r": 0.10, "effect_t": None, "effect_df": None, "effect_beta": 0.5}
        r = StatisticalExtractor.resolve_overridden_r(data, {"effect_beta"})
        assert r == pytest.approx(0.49)

    def test_explicit_r_override_wins(self):
        data = {"effect_r": 0.33, "effect_t": 2.0, "effect_df": 4, "effect_beta": None}
        r = StatisticalExtractor.resolve_overridden_r(
            data, {"effect_r", "effect_t", "effect_df"}
        )
        assert r == pytest.approx(0.33)

    def test_no_relevant_override_keeps_existing_r(self):
        data = {"effect_r": 0.10, "effect_t": 2.0, "effect_df": 4, "effect_beta": None}
        r = StatisticalExtractor.resolve_overridden_r(data, {"p_value", "sample_n"})
        assert r == pytest.approx(0.10)

    def test_t_override_without_df_keeps_existing_r(self):
        data = {"effect_r": 0.10, "effect_t": 2.0, "effect_df": None, "effect_beta": None}
        r = StatisticalExtractor.resolve_overridden_r(data, {"effect_t"})
        assert r == pytest.approx(0.10)  # cannot compute without df → no stale overwrite
