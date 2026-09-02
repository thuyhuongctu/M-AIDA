"""7.2.0: the post-extraction path (PI overrides, locking, export, model output).

Each test pins one finding of the 31 August 2026 code review
(CODE_REVIEW_2026-08-31.md, reproduction cases in verify_findings.py) as FIXED:

A1  PI override of r recomputes variance_r and variance_z.
A2  PI switch to t/df relabels the estimand (partial) and its variance formula.
A3  beta outside the P&B domain leaves a flagged, unlockable record.
A4  CSV export carries every model field.
B1  pi_locked / locked_at cannot be set through /verify.
B2  study_id cannot be overridden (no duplicate rows).
B3  extraction_confidence / evidence_* cannot be overridden.
C1  non-numeric or non-JSON model output is a 422, never a 500 or an empty record.
C2  lambda_applied is True only when the +0.05·lambda term was applied.
C3  backend and analysis/effect_size.py agree on r, variance_r and var_z.
"""

from __future__ import annotations

import base64
import json
import os
import sys

import fitz
import pytest
from fastapi.testclient import TestClient

import main as app_module
from extractor import StatisticalExtractor

EV = {
    "evidence_page": 7,
    "evidence_quote": "Table 3 reports the focal coefficient for DOI.",
    "n_evidence_page": 4,
    "n_evidence_quote": "The final sample comprises 200 firms.",
}


class FakeEngine:
    provider, model = "fake", "fake-model-1"

    def __init__(self, payload, raw: str | None = None) -> None:
        self._payload, self._raw = payload, raw

    def complete(self, system, user, max_tokens=1024):
        return self._raw if self._raw is not None else json.dumps(self._payload)


def _pdf_b64(text: str = "dummy") -> str:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), text)
    pdf = doc.tobytes()
    doc.close()
    return base64.b64encode(pdf).decode()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MAIDA_DB_PATH", str(tmp_path / "t.db"))
    app_module._studies = app_module.StudyStore(str(tmp_path / "t.db")) if hasattr(app_module, "StudyStore") else app_module._studies
    return TestClient(app_module.app)


def make_study(client, payload, raw: str | None = None):
    app_module._get_extractor = lambda: StatisticalExtractor(engine=FakeEngine({**EV, **payload}, raw))
    r = client.post("/api/extract", json={"pdf_content": _pdf_b64(),
                                           "paper_metadata": {"title": "T", "authors": "A", "year": 2020, "country": "VN"}})
    return r


def verify(client, sid, overrides, approved=True):
    return client.patch(f"/api/studies/{sid}/verify",
                        json={"study_id": sid, "pi_approved": approved, "pi_notes": "n", "field_overrides": overrides})


# ----------------------------------------------------------------------------- A1
def test_A1_override_r_recomputes_variance(client):
    s = make_study(client, {"effect_r": 0.30, "sample_n": 200}).json()
    assert abs(s["variance_r"] - (1 - 0.3 ** 2) ** 2 / 199) < 1e-12
    assert abs(s["variance_z"] - 1 / 197) < 1e-12
    v = verify(client, s["study_id"], {"effect_r": 0.80}).json()
    assert v["effect_r"] == 0.80
    assert abs(v["variance_r"] - (1 - 0.8 ** 2) ** 2 / 199) < 1e-12
    assert v["variance_formula"] == "(1 - r^2)^2 / (n - 1)"
    assert v["pi_edited_fields"] == ["effect_r"] and v["pi_override_at"] is not None
    assert v["extraction_confidence"] == s["extraction_confidence"]  # machine score untouched
    assert v["machine_proposal"]["effect_r"] == 0.30


# ----------------------------------------------------------------------------- A2
def test_A2_switch_to_t_df_relabels_estimand(client):
    s = make_study(client, {"effect_r": 0.30, "sample_n": 200}).json()
    v = verify(client, s["study_id"], {"effect_t": 2.5, "effect_df": 187, "n_predictors": 12}).json()
    assert abs(v["effect_r"] - StatisticalExtractor.compute_r_from_t(2.5, 187)) < 1e-12
    assert v["metric_type"] == "partial"
    assert v["source_controls"] is True
    assert v["estimand_source"] == "observed"
    assert v["r_source"] == "derived"
    assert v["variance_formula"] == "(1 - r^2)^2 / df"
    assert abs(v["variance_r"] - (1 - v["effect_r"] ** 2) ** 2 / 187) < 1e-12
    assert abs(v["variance_z"] - 1 / 186) < 1e-12


# ----------------------------------------------------------------------------- A3
def test_A3_beta_outside_domain_stays_flagged_and_unlockable(client):
    s = make_study(client, {"effect_beta": 0.30, "sample_n": 200, "n_predictors": 12}).json()
    assert s["effect_r"] is not None
    v = verify(client, s["study_id"], {"effect_beta": 0.70}).json()
    assert v["effect_r"] is None
    assert v["beta_outside_pb_domain"] is True
    assert v["requires_verification"] is True
    assert v["variance_r"] is None
    lk = client.post(f"/api/studies/{s['study_id']}/lock")
    assert lk.status_code == 422


# ----------------------------------------------------------------------------- A4
def test_A4_csv_export_carries_every_field(client):
    s = make_study(client, {"effect_r": 0.30, "sample_n": 200}).json()
    verify(client, s["study_id"], {})
    assert client.post(f"/api/studies/{s['study_id']}/lock").status_code == 200
    header = client.get("/api/studies/export/csv").text.splitlines()[0].split(",")
    for col in ("variance_r", "variance_z", "variance_formula", "metric_type", "estimand_source",
                "source_controls", "df_source", "lambda_applied", "r_source", "n_source",
                "n_predictors", "evidence_quote", "evidence_page", "requires_verification",
                "beta_outside_pb_domain", "pi_edited_fields", "machine_proposal", "text_truncated"):
        assert col in header, col
    assert set(header) == set(app_module.StudyDatabaseEntry.model_fields)


# ----------------------------------------------------------------------------- B1
def test_B1_lock_fields_not_overridable(client):
    s = make_study(client, {"effect_beta": 0.30, "sample_n": 200, "n_predictors": 12}).json()
    assert client.post(f"/api/studies/{s['study_id']}/lock").status_code == 422
    r = verify(client, s["study_id"], {"pi_locked": True, "locked_at": "2020-01-01T00:00:00"}, approved=False)
    assert r.status_code == 422
    got = client.get(f"/api/studies/{s['study_id']}").json()
    assert got["pi_locked"] is False and got["locked_at"] is None
    assert verify(client, s["study_id"], {}).status_code == 200  # still correctable


# ----------------------------------------------------------------------------- B2
def test_B2_study_id_not_overridable_no_duplicates(client):
    s = make_study(client, {"effect_r": 0.30, "sample_n": 200}).json()
    before = len(client.get("/api/studies").json())
    r = verify(client, s["study_id"], {"study_id": "forged-id"})
    assert r.status_code == 422
    assert len(client.get("/api/studies").json()) == before


# ----------------------------------------------------------------------------- B3
def test_B3_confidence_and_evidence_not_overridable(client):
    s = make_study(client, {"effect_r": 0.30, "sample_n": 200}).json()
    for bad in ({"extraction_confidence": 0.99}, {"evidence_quote": "rewritten"},
                {"machine_proposal": None}, {"variance_r": 0.0}, {"metric_type": "partial"}):
        assert verify(client, s["study_id"], bad).status_code == 422, bad
    got = client.get(f"/api/studies/{s['study_id']}").json()
    assert got["extraction_confidence"] == s["extraction_confidence"]
    assert got["evidence_quote"] == EV["evidence_quote"]


# ----------------------------------------------------------------------------- C1
def test_C1_numeric_string_is_coerced_and_garbage_is_422(client):
    ok = make_study(client, {"effect_r": "0.35", "sample_n": "200"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["effect_r"] == 0.35 and ok.json()["sample_n"] == 200
    bad = make_study(client, {"effect_r": "zero point three", "sample_n": 200})
    assert bad.status_code == 422
    n_before = len(client.get("/api/studies").json())
    notjson = make_study(client, {}, raw="Sorry, I cannot help with that.")
    assert notjson.status_code == 422
    assert len(client.get("/api/studies").json()) == n_before  # no empty record created


# ----------------------------------------------------------------------------- C2
def test_C2_lambda_applied_only_for_nonnegative_beta(client):
    neg = make_study(client, {"effect_beta": -0.30, "sample_n": 200, "n_predictors": 12}).json()
    assert abs(neg["effect_r"] - (-0.294)) < 1e-9 and neg["lambda_applied"] is False
    pos = make_study(client, {"effect_beta": 0.30, "sample_n": 200, "n_predictors": 12}).json()
    assert abs(pos["effect_r"] - 0.344) < 1e-9 and pos["lambda_applied"] is True


# ----------------------------------------------------------------------------- C3
def test_C3_backend_agrees_with_analysis_module():
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(here, "..", "..", "analysis"))
    import effect_size as es  # noqa: E402

    S = StatisticalExtractor
    for r, n in ((0.10, 50), (0.30, 200), (-0.45, 1200)):
        d = S.derive_from_primary({"effect_r": r, "sample_n": n})
        rec = es.from_reported_r(r, n)
        assert abs(d["effect_r"] - rec.r) < 1e-12
        assert abs(d["variance_r"] - rec.variance) < 1e-12
        assert abs(d["variance_z"] - rec.var_z) < 1e-12
    for t, n, p in ((2.5, 200, 12), (-3.1, 400, 5)):
        d = S.derive_from_primary({"effect_t": t, "sample_n": n, "n_predictors": p})
        rec = es.from_t(t, n, n_predictors=p)
        assert abs(d["effect_r"] - rec.r) < 1e-12
        assert d["effect_df"] == rec.df
        assert abs(d["variance_r"] - rec.variance) < 1e-12
        assert abs(d["variance_z"] - rec.var_z) < 1e-12
    for b, n, p in ((0.30, 200, 12), (-0.30, 200, 12), (0.5, 300, 3)):
        d = S.derive_from_primary({"effect_beta": b, "sample_n": n, "n_predictors": p})
        rec = es.from_beta(b, n, n_predictors=p)
        assert abs(d["effect_r"] - rec.r) < 1e-12
        assert d["lambda_applied"] == rec.lambda_applied
        assert abs(d["variance_z"] - rec.var_z) < 1e-12


# ----------------------------------------------------------------------------- D
def test_D_text_truncation_is_recorded(client):
    app_module._get_extractor = lambda: StatisticalExtractor(engine=FakeEngine({**EV, "effect_r": 0.2, "sample_n": 100}))
    long = make_study(client, {"effect_r": 0.2, "sample_n": 100})
    assert long.json()["text_truncated"] is False
    from extractor import PDF_TEXT_LIMIT
    eff = StatisticalExtractor(engine=FakeEngine({**EV, "effect_r": 0.2, "sample_n": 100})).extract_from_text("x" * (PDF_TEXT_LIMIT + 1), {"year": 2020})
    assert eff.text_truncated is True
