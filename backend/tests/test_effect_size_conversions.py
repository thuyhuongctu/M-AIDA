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
# Peterson & Brown (2005):  r = 0.98·β + 0.05·λ,  λ = 1 if β >= 0 else 0
# Valid only for |β| <= 0.5; outside that domain no conversion is made.
# Hand-computed expectations are written out digit by digit on each line.
# --------------------------------------------------------------------------- #
class TestConvertBetaToR:
    @pytest.mark.parametrize(
        "beta, expected",
        [
            (0.30, 0.344),    # 0.98·0.30 + 0.05·1 = 0.294 + 0.05
            (0.50, 0.540),    # 0.98·0.50 + 0.05·1 = 0.490 + 0.05 (domain edge)
            (0.10, 0.148),    # 0.98·0.10 + 0.05·1 = 0.098 + 0.05
            (0.0, 0.050),     # λ = 1 at β = 0 (β non-negative)
            (-0.30, -0.294),  # 0.98·(−0.30) + 0.05·0: no λ term for β < 0
            (-0.50, -0.490),  # 0.98·(−0.50) + 0.05·0 (domain edge)
        ],
    )
    def test_full_peterson_brown_formula(self, beta, expected):
        assert StatisticalExtractor.convert_beta_to_r(beta) == pytest.approx(expected)

    def test_lambda_term_is_asymmetric(self):
        # The λ intercept applies only on the non-negative side, so the
        # conversion is NOT an odd function: |r(+β)| = |r(−β)| + 0.05.
        pos = StatisticalExtractor.convert_beta_to_r(0.3)
        neg = StatisticalExtractor.convert_beta_to_r(-0.3)
        assert pos == pytest.approx(-neg + 0.05)

    @pytest.mark.parametrize("beta", [0.51, -0.51, 0.7, -0.7, 1.0, -1.0])
    def test_outside_domain_returns_none(self, beta):
        # |β| > 0.5 is outside the Peterson & Brown derivation domain: the
        # record must carry no converted r at all, not a clamped guess.
        assert StatisticalExtractor.convert_beta_to_r(beta) is None

    def test_sign_is_preserved_within_domain(self):
        assert StatisticalExtractor.convert_beta_to_r(-0.4) < 0
        assert StatisticalExtractor.convert_beta_to_r(0.4) > 0


# --------------------------------------------------------------------------- #
# Degrees of freedom for a regression t-statistic:  df = n − p − 1
# --------------------------------------------------------------------------- #
class TestDegreesOfFreedom:
    @pytest.mark.parametrize(
        "n, p, expected",
        [
            (100, 1, 98),    # bivariate case reduces to the familiar n − 2
            (231, 10, 220),  # typical internationalisation model: 10 predictors
            (250, 12, 237),  # 250 − 12 − 1
            (60, 15, 44),    # heavy control set on a small sample
        ],
    )
    def test_n_minus_p_minus_one(self, n, p, expected):
        assert StatisticalExtractor.degrees_of_freedom(n, p) == expected

    def test_bare_n_minus_2_would_inflate_df_for_multiple_regression(self):
        # The old n − 2 default overstates df by p − 1, which shrinks the
        # converted r. With t = 2.14, n = 231, p = 10:
        #   wrong df = 229 → r = 2.14/√(2.14² + 229) = 0.1401…
        #   right df = 220 → r = 2.14/√(2.14² + 220) = 0.1429…
        t, n, p = 2.14, 231, 10
        df_right = StatisticalExtractor.degrees_of_freedom(n, p)
        r_wrong = StatisticalExtractor.compute_r_from_t(t, n - 2)
        r_right = StatisticalExtractor.compute_r_from_t(t, df_right)
        assert df_right == 220
        assert r_right > r_wrong
        assert r_right == pytest.approx(2.14 / math.sqrt(2.14**2 + 220))


# --------------------------------------------------------------------------- #
# Sampling variance by metric type, the two denominators differ:
#   zero-order: (1 − r²)² / (n − 1)      partial: (1 − r²)² / df
# --------------------------------------------------------------------------- #
class TestVarianceOfR:
    def test_zero_order_hand_example(self):
        # r = .30, n = 101: (1 − .09)² / 100 = .91² / 100 = .8281 / 100
        v = StatisticalExtractor.variance_of_r(
            0.30, sample_n=101, metric_type="zero_order"
        )
        assert v == pytest.approx(0.008281)

    def test_zero_order_null_effect(self):
        # r = 0, n = 5: 1 / 4 = 0.25
        v = StatisticalExtractor.variance_of_r(
            0.0, sample_n=5, metric_type="zero_order"
        )
        assert v == pytest.approx(0.25)

    def test_partial_hand_example(self):
        # r_p = .30, n = 114, p = 13 → df = 100: .91² / 100
        df = StatisticalExtractor.degrees_of_freedom(114, 13)
        assert df == 100
        v = StatisticalExtractor.variance_of_r(0.30, df=df, metric_type="partial")
        assert v == pytest.approx(0.008281)

    def test_same_r_same_n_different_variance_by_type(self):
        # The heart of finding A3: with r = .30 and n = 114 the zero-order
        # denominator is n − 1 = 113 but the partial denominator (13
        # predictors) is df = 100: the partial variance must be larger.
        v_zero = StatisticalExtractor.variance_of_r(
            0.30, sample_n=114, metric_type="zero_order"
        )
        v_partial = StatisticalExtractor.variance_of_r(
            0.30, df=100, metric_type="partial"
        )
        assert v_partial > v_zero
        assert v_zero == pytest.approx(0.8281 / 113)

    def test_missing_inputs_raise(self):
        with pytest.raises(ValueError):
            StatisticalExtractor.variance_of_r(0.3, metric_type="zero_order")
        with pytest.raises(ValueError):
            StatisticalExtractor.variance_of_r(0.3, metric_type="partial")
        with pytest.raises(ValueError):
            StatisticalExtractor.variance_of_r(0.3, sample_n=100, metric_type="odd")


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
        assert r == pytest.approx(0.54)  # 0.98·0.5 + 0.05·1

    def test_beta_override_outside_domain_yields_no_r(self):
        data = {"effect_r": 0.10, "effect_t": None, "effect_df": None, "effect_beta": 0.8}
        r = StatisticalExtractor.resolve_overridden_r(data, {"effect_beta"})
        assert r is None  # |β| > 0.5: no valid conversion exists

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
