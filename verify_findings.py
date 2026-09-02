"""Reproduction cases for the 31 August 2026 review findings, written against 7.1.x.

Kept as the historical reproduction record. Against 7.2.0 the prints no longer describe
the behaviour (F3 stops at the 422 lock refusal, which is the fix); the regression
suite for the fixed behaviour is backend/tests/test_720_post_extraction.py.
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
os.environ["MAIDA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "verify.db")

from fastapi.testclient import TestClient  # noqa: E402
import main as app_module  # noqa: E402
from extractor import StatisticalExtractor  # noqa: E402

EV = {
    "evidence_page": 7,
    "evidence_quote": "Table 3 reports the focal coefficient for DOI.",
    "n_evidence_page": 4,
    "n_evidence_quote": "The final sample comprises 200 firms.",
}


class FakeEngine:
    provider, model = "fake", "fake-model-1"

    def __init__(self, payload):
        self._payload = payload

    def complete(self, system, user, max_tokens=1024):
        return json.dumps(self._payload)


def make_study(client, payload):
    app_module._get_extractor = lambda: StatisticalExtractor(
        engine=FakeEngine({**EV, **payload})
    )
    import base64
    import fitz

    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "dummy")
    pdf = doc.tobytes()
    doc.close()
    r = client.post(
        "/api/extract",
        json={
            "pdf_content": base64.b64encode(pdf).decode(),
            "paper_metadata": {"title": "T", "authors": "A", "year": 2020,
                               "country": "VN"},
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def line(n, t):
    print(f"\n{'=' * 72}\nFINDING {n}: {t}\n{'=' * 72}")


def main():
    client = TestClient(app_module.app)

    # ---------------------------------------------------------------- F1
    line(1, "PI override recomputes effect_r but leaves variance_r/metric_type stale")
    s = make_study(client, {"effect_r": 0.30, "sample_n": 200})
    print(f"  after extraction : r={s['effect_r']} metric={s['metric_type']} "
          f"var={s['variance_r']:.8f} formula={s['variance_formula']}")
    r = client.patch(
        f"/api/studies/{s['study_id']}/verify",
        json={"study_id": s["study_id"], "pi_approved": True,
              "pi_notes": "corrected from Table 3",
              "field_overrides": {"effect_r": 0.80}},
    )
    v = r.json()
    import math
    expected = (1 - 0.80 ** 2) ** 2 / (200 - 1)
    print(f"  after PI override: r={v['effect_r']} metric={v['metric_type']} "
          f"var={v['variance_r']:.8f} formula={v['variance_formula']}")
    print(f"  variance implied by the NEW r would be {expected:.8f}")
    print(f"  --> STALE: stored variance is {v['variance_r'] / expected:.1f}x the "
          f"correct one; the meta-analytic weight is wrong.")

    # ---------------------------------------------------------------- F2
    line(2, "PI override of t/df flips the estimand but metric_type stays zero_order")
    s = make_study(client, {"effect_r": 0.30, "sample_n": 200})
    r = client.patch(
        f"/api/studies/{s['study_id']}/verify",
        json={"study_id": s["study_id"], "pi_approved": True,
              "pi_notes": "use the regression t instead",
              "field_overrides": {"effect_t": 2.5, "effect_df": 187,
                                  "n_predictors": 12}},
    )
    v = r.json()
    print(f"  r recomputed to {v['effect_r']:.4f} (a PARTIAL correlation)")
    print(f"  metric_type      = {v['metric_type']}   <-- still zero_order")
    print(f"  estimand_source  = {v['estimand_source']}")
    print(f"  source_controls  = {v['source_controls']}")
    print(f"  variance_formula = {v['variance_formula']}  <-- zero-order formula")
    print("  --> a partial correlation is exported as if it were zero-order")

    # ---------------------------------------------------------------- F3
    line(3, "Out-of-domain beta override blanks effect_r, record still lockable")
    s = make_study(client, {"effect_beta": 0.30, "sample_n": 200,
                            "n_predictors": 12})
    print(f"  after extraction : r={s['effect_r']} beta={s['effect_beta']}")
    r = client.patch(
        f"/api/studies/{s['study_id']}/verify",
        json={"study_id": s["study_id"], "pi_approved": True,
              "pi_notes": "beta corrected to 0.70",
              "field_overrides": {"effect_beta": 0.70}},
    )
    v = r.json()
    print(f"  after override   : r={v['effect_r']} beta={v['effect_beta']} "
          f"beta_outside_pb_domain={v['beta_outside_pb_domain']} "
          f"requires_verification={v['requires_verification']}")
    lk = client.post(f"/api/studies/{s['study_id']}/lock")
    print(f"  lock status      : {lk.status_code}, pi_locked={lk.json()['pi_locked']}")
    print("  --> a record with NO effect size is locked as final data")

    # ---------------------------------------------------------------- F4
    line(4, "pi_locked can be set through /verify, bypassing the lock gate")
    s = make_study(client, {"effect_beta": 0.30, "sample_n": 200,
                            "n_predictors": 12})
    print(f"  requires_verification after extraction = {s['requires_verification']}")
    direct = client.post(f"/api/studies/{s['study_id']}/lock")
    print(f"  honest lock attempt -> {direct.status_code} (gate works)")
    r = client.patch(
        f"/api/studies/{s['study_id']}/verify",
        json={"study_id": s["study_id"], "pi_approved": False, "pi_notes": "",
              "field_overrides": {"pi_locked": True,
                                  "locked_at": "2020-01-01T00:00:00"}},
    )
    v = r.json()
    print(f"  via field_overrides -> pi_locked={v['pi_locked']} "
          f"locked_at={v['locked_at']} requires_verification={v['requires_verification']}")
    again = client.patch(
        f"/api/studies/{s['study_id']}/verify",
        json={"study_id": s["study_id"], "pi_approved": True, "pi_notes": "x",
              "field_overrides": {}},
    )
    print(f"  record is now frozen: further /verify -> {again.status_code}")
    print("  --> an unverified record is locked, with a back-dated timestamp,"
          " and can no longer be corrected")

    # ---------------------------------------------------------------- F5
    line(5, "CSV export drops every provenance and weighting column")
    s = make_study(client, {"effect_r": 0.30, "sample_n": 200})
    client.patch(f"/api/studies/{s['study_id']}/verify",
                 json={"study_id": s["study_id"], "pi_approved": True,
                       "pi_notes": "ok", "field_overrides": {}})
    client.post(f"/api/studies/{s['study_id']}/lock")
    csv_text = client.get("/api/studies/export/csv").text
    header = csv_text.splitlines()[0].split(",")
    missing = [c for c in ("variance_r", "variance_formula", "metric_type",
                           "estimand_source", "source_controls", "df_source",
                           "lambda_applied", "r_source", "n_source",
                           "n_predictors", "evidence_quote", "evidence_page",
                           "requires_verification", "beta_outside_pb_domain")
               if c not in header]
    print(f"  exported columns : {len(header)}")
    print(f"  absent from CSV  : {', '.join(missing)}")
    print("  --> the Stata hand-off carries no variance and no metric type")

    # ---------------------------------------------------------------- F6
    line(6, "lambda_applied is True even when the lambda term was not applied")
    s = make_study(client, {"effect_beta": -0.30, "sample_n": 200,
                            "n_predictors": 12})
    print(f"  beta=-0.30 -> r={s['effect_r']:.4f} "
          f"(0.98*-0.30 + 0.05*0 = -0.294, no lambda term)")
    print(f"  lambda_applied   = {s['lambda_applied']}   <-- claims it was applied")
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "analysis"))
    import effect_size as es
    rec = es.convert("beta", -0.30, 200, n_predictors=12)
    print(f"  analysis/effect_size.py agrees on r={rec.r:.4f} but also reports "
          f"lambda_applied={rec.lambda_applied}")

    # ---------------------------------------------------------------- F7
    line(7, "Non-numeric LLM output crashes extraction with a 500")
    app_module._get_extractor = lambda: StatisticalExtractor(
        engine=FakeEngine({**EV, "effect_r": "0.35", "sample_n": 200})
    )
    import base64
    import fitz
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "dummy")
    pdf = doc.tobytes()
    doc.close()
    r = client.post("/api/extract", json={
        "pdf_content": base64.b64encode(pdf).decode(),
        "paper_metadata": {"title": "T", "authors": "A", "year": 2020,
                           "country": "VN"}})
    print(f"  effect_r returned as the string \"0.35\" -> HTTP {r.status_code}")
    print(f"  detail: {r.json().get('detail', '')[:90]}")

    # ---------------------------------------------------------------- F8
    line(8, "analysis/effect_size.py (v8.0.0) is imported by nothing")
    import subprocess
    out = subprocess.run(
        ["grep", "-rn", "effect_size", "--include=*.py", "backend", "frontend",
         "scripts", "validation", "demo"],
        capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
    print(f"  references from the running code: {out or '(none)'}")
    print("  --> two independent implementations of the same statistics")


if __name__ == "__main__":
    main()
