"""
Regression tests for extraction integrity (finding E1) and persistence.

Pinned properties:

1. Verified and locked records survive a backend restart.
2. There is NO fallback path: with no API key, /api/extract surfaces an
   error in demo mode and production alike. A tool whose contribution is
   data integrity must never answer a real upload with an invented record.
3. /api/health reports extraction as live or plainly unavailable - no
   third mode exists.
4. Two different PDFs must never yield identical records (the E1 failure
   shape), and statistics without verbatim evidence are rejected with 422.
"""

from __future__ import annotations

import base64
import importlib
import json
import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _make_pdf(marker: str = "t = 2.40, df = 248") -> str:
    """Return a Base64 one-page PDF so the route reaches the extractor stage."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), f"Rehearsal paper. {marker}.")
    data = doc.tobytes()
    doc.close()
    return base64.b64encode(data).decode()


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, demo: bool) -> TestClient:
    """Boot a fresh app instance bound to its own SQLite file."""
    monkeypatch.setenv("MAIDA_DB_PATH", str(tmp_path / "maida.db"))
    monkeypatch.setenv("MAIDA_DEMO_MODE", "true" if demo else "false")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    import settings as settings_module

    settings_module._settings = None  # drop the cached singleton
    main = importlib.import_module("main")
    importlib.reload(main)
    return TestClient(main.app)


class EchoEngine:
    """Engine whose output depends on the input text.

    Parses "r = <value> (n = <n>)" out of the user prompt, so different PDFs
    produce different records - the property E1 violated.
    """

    provider = "echo"
    model = "echo-1"

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        m = re.search(r"r = (-?[\d.]+) \(n = (\d+)\)", user)
        if not m:
            return json.dumps({})
        return json.dumps({
            "effect_r": float(m.group(1)),
            "sample_n": int(m.group(2)),
            "evidence_page": 1,
            "evidence_quote": m.group(0),
            "n_evidence_page": 1,
            "n_evidence_quote": f"n = {m.group(2)}",
        })


class NoEvidenceEngine:
    """Engine that proposes statistics but never quotes the source (E1 gate)."""

    provider = "noev"
    model = "noev-1"

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        return json.dumps({"effect_r": 0.25, "sample_n": 50})


class NoNEvidenceEngine:
    """Engine that evidences r but guesses the sample size (finding E2-n)."""

    provider = "nonev"
    model = "nonev-1"

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        return json.dumps({
            "effect_r": 0.25,
            "sample_n": 200,
            "evidence_page": 3,
            "evidence_quote": "The correlation between DOI and ROA is .25.",
        })


def _inject(main_module, engine) -> None:
    from extractor import StatisticalExtractor

    main_module._get_extractor = lambda: StatisticalExtractor(engine=engine)


def test_records_survive_a_restart(tmp_path, monkeypatch):
    """A locked record must still be there after the process is replaced."""
    client = _client(tmp_path, monkeypatch, demo=False)
    import main as main_module

    _inject(main_module, EchoEngine())
    entry = client.post(
        "/api/extract",
        json={
            "pdf_content": _make_pdf("r = 0.24 (n = 231)"),
            "paper_metadata": {"title": "Rehearsal"},
        },
    ).json()
    study_id = entry["study_id"]

    client.patch(
        f"/api/studies/{study_id}/verify",
        json={"study_id": study_id, "field_overrides": {}, "pi_approved": True, "pi_notes": "checked"},
    )
    assert client.post(f"/api/studies/{study_id}/lock").status_code == 200

    # Same database file, brand-new app instance: this is the restart.
    restarted = _client(tmp_path, monkeypatch, demo=False)
    reloaded = restarted.get(f"/api/studies/{study_id}")
    assert reloaded.status_code == 200
    assert reloaded.json()["pi_locked"] is True
    assert restarted.get("/api/studies/export/csv").status_code == 200


def test_no_fallback_in_any_mode(tmp_path, monkeypatch):
    """With no API key, demo mode and production both surface the error."""
    for label, demo in (("demo", True), ("prod", False)):
        client = _client(tmp_path / label, monkeypatch, demo=demo)
        res = client.post(
            "/api/extract", json={"pdf_content": _make_pdf(), "paper_metadata": {}}
        )
        assert res.status_code == 503, f"{label}: expected plain 503, got {res.status_code}"


def test_health_never_reports_a_fallback_mode(tmp_path, monkeypatch):
    for label, demo in (("demo", True), ("prod", False)):
        health = _client(tmp_path / label, monkeypatch, demo=demo).get("/api/health").json()
        assert health["storage"] == "sqlite"
        assert health["llm_ready"] is False
        assert health["extraction_mode"] == "unavailable"


def test_two_different_pdfs_give_two_different_records(tmp_path, monkeypatch):
    """The E1 regression: identical outputs for different inputs = defect."""
    client = _client(tmp_path, monkeypatch, demo=False)
    import main as main_module

    _inject(main_module, EchoEngine())
    a = client.post(
        "/api/extract",
        json={"pdf_content": _make_pdf("r = 0.24 (n = 231)"), "paper_metadata": {}},
    ).json()
    b = client.post(
        "/api/extract",
        json={"pdf_content": _make_pdf("r = -0.05 (n = 88)"), "paper_metadata": {}},
    ).json()
    assert a["effect_r"] != b["effect_r"]
    assert a["sample_n"] != b["sample_n"]
    assert a["evidence_quote"] != b["evidence_quote"]


def test_statistics_without_evidence_are_rejected(tmp_path, monkeypatch):
    """The E1 gate: an unevidenced record is refused, not created-and-flagged."""
    client = _client(tmp_path, monkeypatch, demo=False)
    import main as main_module

    _inject(main_module, NoEvidenceEngine())
    res = client.post(
        "/api/extract", json={"pdf_content": _make_pdf(), "paper_metadata": {}}
    )
    assert res.status_code == 422
    assert "evidence" in res.json()["detail"].lower()
    # And nothing was persisted.
    assert client.get("/api/health").json()["study_count"] == 0


def test_sample_size_without_evidence_is_rejected(tmp_path, monkeypatch):
    """A guessed n is a guessed weight: n passes the same gate as r."""
    client = _client(tmp_path, monkeypatch, demo=False)
    import main as main_module

    _inject(main_module, NoNEvidenceEngine())
    res = client.post(
        "/api/extract", json={"pdf_content": _make_pdf(), "paper_metadata": {}}
    )
    assert res.status_code == 422
    assert "n_evidence" in res.json()["detail"]
    assert client.get("/api/health").json()["study_count"] == 0
