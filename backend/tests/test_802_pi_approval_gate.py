"""8.0: the lock gate requires a recorded PI approval, not only the machine's
confidence flag. "The machine proposes, a person verifies and locks."""

from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

import main as app_module
from conftest import ADMIN_HEADERS, make_minimal_pdf
from extractor import StatisticalExtractor


class FakeEngine:
    provider, model = "fake", "fake-model-1"

    def __init__(self, payload):
        self._payload = payload

    def complete(self, system, user, max_tokens=1024):
        return json.dumps(self._payload)


HIGH_CONFIDENCE = {
    "sample_n": 200, "effect_r": 0.30, "evidence_page": 2, "evidence_quote": "r = 0.30",
    "n_evidence_page": 1, "n_evidence_quote": "200 firms",
}


def _client(tmp_path):
    app_module._studies = app_module.StudyStore(str(tmp_path / "gate.db"))
    app_module._get_extractor = lambda: StatisticalExtractor(engine=FakeEngine(HIGH_CONFIDENCE))
    return TestClient(app_module.app, headers=ADMIN_HEADERS)


def _extract(client):
    pdf = base64.b64encode(make_minimal_pdf("r = 0.30 (n = 200)")).decode()
    return client.post("/api/extract", json={"pdf_content": pdf, "paper_metadata": {"title": "T", "year": 2020}}).json()


def test_high_confidence_record_still_needs_a_person_before_locking(tmp_path):
    client = _client(tmp_path)
    s = _extract(client)
    assert s["requires_verification"] is False and s["pi_approved_at"] is None  # machine confident, nobody approved
    r = client.post(f"/api/studies/{s['study_id']}/lock")
    assert r.status_code == 422 and "approved by the PI" in r.json()["detail"]
    v = client.patch(f"/api/studies/{s['study_id']}/verify",
                     json={"study_id": s["study_id"], "pi_approved": True, "pi_notes": "checked", "field_overrides": {}}).json()
    assert v["pi_approved_at"] is not None
    assert client.post(f"/api/studies/{s['study_id']}/lock").status_code == 200


def test_flagging_withdraws_the_approval(tmp_path):
    client = _client(tmp_path)
    s = _extract(client)
    sid = s["study_id"]
    client.patch(f"/api/studies/{sid}/verify", json={"study_id": sid, "pi_approved": True, "pi_notes": "ok", "field_overrides": {}})
    flagged = client.patch(f"/api/studies/{sid}/verify",
                           json={"study_id": sid, "pi_approved": False, "pi_notes": "[Flagged] wrong table", "field_overrides": {}}).json()
    assert flagged["pi_approved_at"] is None
    assert client.post(f"/api/studies/{sid}/lock").status_code == 422
