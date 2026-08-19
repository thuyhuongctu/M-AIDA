"""Tests for the 7.1.2 governance patch (updated for the formula fixes).

Pins the fixes that align the code with the corrected protocol:
(1) defensive clamp of r into [-1, 1]; (2) a beta outside the Peterson &
Brown (2005) derivation domain |beta| <= 0.5 yields NO converted r and is
excluded, not clamped; (3) df is only ever derived as n − p − 1 when a
predictor count is known: records missing both df and n_predictors stay
unconverted and flagged; (4) the machine's original proposal is stored per
record and survives PI overrides, and locked records reject changes with
HTTP 409.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import main as app_module
from extractor import StatisticalExtractor


class FakeEngine:
    provider = "fake"
    model = "fake-model-1"

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        return json.dumps(self._payload)


DEFAULT_EVIDENCE = {
    "evidence_page": 7,
    "evidence_quote": "Table 3 reports the focal coefficient for DOI.",
    "n_evidence_page": 4,
    "n_evidence_quote": "The final sample comprises the firms described above.",
}


def _extract(payload: dict):
    # Evidence is mandatory whenever statistics are present (E1); tests that
    # probe the missing-evidence gate override these defaults explicitly.
    ex = StatisticalExtractor(engine=FakeEngine({**DEFAULT_EVIDENCE, **payload}))
    return ex.extract_from_text("dummy", {"title": "T", "authors": "A", "year": 2020, "country": "VN"})


class TestClamp:
    def test_beta_outside_domain_yields_none_not_clamp(self):
        # Out-of-domain betas used to be converted and clamped to ±1; the
        # corrected behaviour is no conversion at all.
        assert StatisticalExtractor.convert_beta_to_r(1.2) is None
        assert StatisticalExtractor.convert_beta_to_r(-1.5) is None

    def test_in_range_beta_uses_full_peterson_brown(self):
        # 0.98·0.3 + 0.05·1 = 0.344 (the λ term is no longer dropped)
        assert StatisticalExtractor.convert_beta_to_r(0.3) == pytest.approx(0.344)

    def test_direct_r_override_is_clamped(self):
        r = StatisticalExtractor.resolve_overridden_r({"effect_r": 1.7}, {"effect_r"})
        assert r == 1.0


class TestBetaDomain:
    def test_beta_above_half_is_excluded_and_flagged(self):
        eff = _extract({"effect_beta": 0.6, "sample_n": 100})
        assert eff.beta_outside_pb_domain is True
        assert eff.requires_verification is True
        assert eff.effect_r is None  # excluded, not converted-and-clamped

    def test_beta_within_domain_is_imputed_zero_order(self):
        # P&B calibrated the imputation against observed zero-order r, so the
        # estimand is zero-order; the imputed origin lives in estimand_source.
        eff = _extract({"effect_beta": 0.3, "sample_n": 100})
        assert eff.beta_outside_pb_domain is False
        assert eff.lambda_applied is True
        assert eff.effect_r == pytest.approx(0.344)
        assert eff.metric_type == "zero_order"
        assert eff.estimand_source == "imputed_pb2005"
        assert eff.source_controls is True
        assert eff.variance_r == pytest.approx((1 - 0.344**2) ** 2 / 99)
        assert eff.variance_formula == "(1 - r^2)^2 / (n - 1)"

    def test_beta_with_predictor_count_keeps_zero_order_variance(self):
        # df is still derived (n = 268, p = 11 → 256) for the audit trail, but
        # the variance follows the zero-order estimand, not df.
        eff = _extract({"effect_beta": 0.18, "sample_n": 268, "n_predictors": 11})
        assert eff.effect_df == 256
        assert eff.df_source == "derived"
        assert eff.metric_type == "zero_order"
        assert eff.estimand_source == "imputed_pb2005"
        assert eff.effect_r == pytest.approx(0.2264)
        assert eff.variance_r == pytest.approx((1 - 0.2264**2) ** 2 / 267)
        assert eff.variance_formula == "(1 - r^2)^2 / (n - 1)"

    def test_three_layer_separation(self):
        # r reported: zero_order · observed; t from regression: partial ·
        # observed; β: zero_order · imputed, only observed feeds the main model.
        r_eff = _extract({"effect_r": 0.24, "sample_n": 231})
        t_eff = _extract({"effect_t": 2.14, "effect_df": 220, "sample_n": 231,
                          "n_predictors": 10})
        b_eff = _extract({"effect_beta": 0.3, "sample_n": 100})
        assert (r_eff.metric_type, r_eff.estimand_source, r_eff.source_controls) == \
            ("zero_order", "observed", False)
        assert (t_eff.metric_type, t_eff.estimand_source, t_eff.source_controls) == \
            ("partial", "observed", True)
        assert (b_eff.metric_type, b_eff.estimand_source, b_eff.source_controls) == \
            ("zero_order", "imputed_pb2005", True)


class TestDfImputation:
    def test_no_imputation_without_predictor_count(self):
        # The old code silently defaulted to df = n − 2 here. Without a
        # predictor count there is no valid df: the record stays
        # unconverted and flagged for PI review.
        eff = _extract({"effect_t": 2.0, "sample_n": 102})
        assert eff.effect_df is None
        assert eff.df_imputed is False
        assert eff.effect_r is None
        assert eff.requires_verification is True

    def test_df_derived_as_n_minus_p_minus_1(self):
        # n = 102, p = 12 → df = 89 (a bare n − 2 would have said 100)
        eff = _extract({"effect_t": 2.0, "sample_n": 102, "n_predictors": 12})
        assert eff.effect_df == 89
        assert eff.df_source == "derived"
        assert eff.df_imputed is True
        assert eff.metric_type == "partial"
        assert eff.requires_verification is True

    def test_reported_df_not_flagged(self):
        eff = _extract({"effect_t": 2.0, "effect_df": 100, "sample_n": 102})
        assert eff.df_imputed is False
        assert eff.df_source == "reported"


class TestGovernanceApi:
    @pytest.fixture()
    def client(self, monkeypatch):
        app_module._studies.clear()
        monkeypatch.setattr(
            app_module,
            "_get_extractor",
            lambda: StatisticalExtractor(
                engine=FakeEngine({"effect_r": 0.25, "sample_n": 50, **DEFAULT_EVIDENCE})
            ),
        )
        return TestClient(app_module.app)

    def _make_entry(self, client):
        import base64

        # a one-page blank PDF
        pdf = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 10 10]>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
        )
        res = client.post(
            "/api/extract",
            json={
                "pdf_content": base64.b64encode(pdf).decode(),
                "paper_metadata": {"title": "T", "authors": "A", "year": 2020, "country": "VN"},
            },
        )
        assert res.status_code == 200, res.text
        return res.json()

    def test_machine_proposal_captured_and_immutable(self, client):
        entry = self._make_entry(client)
        assert entry["machine_proposal"]["effect_r"] == 0.25
        sid = entry["study_id"]
        res = client.patch(
            f"/api/studies/{sid}/verify",
            json={
                "study_id": sid,
                "field_overrides": {"effect_r": 0.30, "machine_proposal": None},
                "pi_notes": "corrected against source table 3",
                "pi_approved": True,
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["effect_r"] == 0.30
        assert body["machine_proposal"]["effect_r"] == 0.25

    def test_locked_record_rejects_override_with_409(self, client):
        entry = self._make_entry(client)
        sid = entry["study_id"]
        client.patch(
            f"/api/studies/{sid}/verify",
            json={"study_id": sid, "field_overrides": {}, "pi_notes": "ok", "pi_approved": True},
        )
        res = client.post(f"/api/studies/{sid}/lock")
        assert res.status_code == 200, res.text
        res = client.patch(
            f"/api/studies/{sid}/verify",
            json={"study_id": sid, "field_overrides": {"effect_r": 0.9}, "pi_notes": "x", "pi_approved": True},
        )
        assert res.status_code == 409
