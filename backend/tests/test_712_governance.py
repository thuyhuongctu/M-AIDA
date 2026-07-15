"""Tests for the 7.1.2 governance patch.

Pins the four fixes that align the code with the documented protocol:
(1) defensive clamp of r into [-1, 1]; (2) mandatory review when a beta
conversion falls outside the Peterson & Brown (2005) derivation domain
|beta| <= 0.5; (3) the documented df = n - 2 fallback, now implemented and
flagged; (4) the machine's original proposal is stored per record and
survives PI overrides, and locked records reject changes with HTTP 409.
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


def _extract(payload: dict):
    ex = StatisticalExtractor(engine=FakeEngine(payload))
    return ex.extract_from_text("dummy", {"title": "T", "authors": "A", "year": 2020, "country": "VN"})


class TestClamp:
    def test_beta_conversion_is_clamped_high(self):
        assert StatisticalExtractor.convert_beta_to_r(1.2) == 1.0

    def test_beta_conversion_is_clamped_low(self):
        assert StatisticalExtractor.convert_beta_to_r(-1.5) == -1.0

    def test_in_range_beta_unchanged(self):
        assert StatisticalExtractor.convert_beta_to_r(0.3) == pytest.approx(0.294)

    def test_direct_r_override_is_clamped(self):
        r = StatisticalExtractor.resolve_overridden_r({"effect_r": 1.7}, {"effect_r"})
        assert r == 1.0


class TestBetaDomain:
    def test_beta_above_half_forces_review(self):
        eff = _extract({"effect_beta": 0.6, "sample_n": 100})
        assert eff.beta_outside_pb_domain is True
        assert eff.requires_verification is True

    def test_beta_within_domain_not_flagged(self):
        eff = _extract({"effect_beta": 0.3, "sample_n": 100})
        assert eff.beta_outside_pb_domain is False


class TestDfImputation:
    def test_df_imputed_as_n_minus_2(self):
        eff = _extract({"effect_t": 2.0, "sample_n": 102})
        assert eff.effect_df == 100
        assert eff.df_imputed is True
        assert eff.requires_verification is True

    def test_reported_df_not_flagged(self):
        eff = _extract({"effect_t": 2.0, "effect_df": 100, "sample_n": 102})
        assert eff.df_imputed is False


class TestGovernanceApi:
    @pytest.fixture()
    def client(self, monkeypatch):
        app_module._studies.clear()
        monkeypatch.setattr(
            app_module,
            "_get_extractor",
            lambda: StatisticalExtractor(
                engine=FakeEngine({"effect_r": 0.25, "sample_n": 50})
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
