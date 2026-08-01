"""
Regression tests for the defence-demo hardening.

Three properties are pinned here because each one, if it silently broke, would
break in front of an audience rather than in development:

1. Verified and locked records survive a backend restart.
2. The rehearsed fallback is reachable ONLY in demo mode, is stamped as a
   fallback, and can never arrive pre-verified.
3. /api/health reports the mode the next upload will actually take, which is
   what the on-screen status strip renders.

The presenter-facing reset route lives in ``demo/run_defense.py`` behind a PIN
and is covered by ``demo/smoke_test.py``; it is deliberately not duplicated in
the API layer, because two implementations of the same path would shadow each
other at registration time.
"""

from __future__ import annotations

import base64
import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _make_pdf() -> str:
    """Return a Base64 one-page PDF so the route reaches the extractor stage."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Rehearsal paper. t = 2.40, df = 248.")
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


def test_records_survive_a_restart(tmp_path, monkeypatch):
    """A locked record must still be there after the process is replaced."""
    client = _client(tmp_path, monkeypatch, demo=True)
    entry = client.post(
        "/api/extract",
        json={"pdf_content": _make_pdf(), "paper_metadata": {"title": "Rehearsal"}},
    ).json()
    study_id = entry["study_id"]

    client.patch(
        f"/api/studies/{study_id}/verify",
        json={"study_id": study_id, "field_overrides": {}, "pi_approved": True, "pi_notes": "checked"},
    )
    assert client.post(f"/api/studies/{study_id}/lock").status_code == 200

    # Same database file, brand-new app instance: this is the restart.
    restarted = _client(tmp_path, monkeypatch, demo=True)
    reloaded = restarted.get(f"/api/studies/{study_id}")
    assert reloaded.status_code == 200
    assert reloaded.json()["pi_locked"] is True
    assert restarted.get("/api/studies/export/csv").status_code == 200


def test_fallback_is_demo_only_and_clearly_stamped(tmp_path, monkeypatch):
    """With no API key: demo mode yields a stamped fallback, production a 503."""
    demo_client = _client(tmp_path / "demo", monkeypatch, demo=True)
    entry = demo_client.post(
        "/api/extract", json={"pdf_content": _make_pdf(), "paper_metadata": {}}
    ).json()
    assert entry["machine_proposal"]["extraction_source"] == "rehearsed_fallback"
    assert "NOT A LIVE EXTRACTION" in entry["pi_notes"]
    # A fallback record must always pass through a human decision.
    assert entry["requires_verification"] is True
    assert entry["pi_locked"] is False

    prod_client = _client(tmp_path / "prod", monkeypatch, demo=False)
    assert (
        prod_client.post(
            "/api/extract", json={"pdf_content": _make_pdf(), "paper_metadata": {}}
        ).status_code
        == 503
    )


def test_health_reports_the_mode_the_next_upload_will_take(tmp_path, monkeypatch):
    """The status strip depends on these fields, so pin their contract."""
    demo_health = _client(tmp_path / "demo", monkeypatch, demo=True).get("/api/health").json()
    assert demo_health["storage"] == "sqlite"
    assert demo_health["llm_ready"] is False
    assert demo_health["extraction_mode"] == "rehearsed_fallback"

    prod_health = _client(tmp_path / "prod", monkeypatch, demo=False).get("/api/health").json()
    assert prod_health["extraction_mode"] == "unavailable"
