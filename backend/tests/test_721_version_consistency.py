"""7.2.1: one version string, everywhere it is shown.

The 7.2.0 release shipped with /api/health still answering "7.1.1" while the
OpenAPI document said "7.2.0". This test pins the version reported at runtime
to the packaged version (backend/pyproject.toml) and to CITATION.cff.
"""

from __future__ import annotations

import os
import re

from fastapi.testclient import TestClient

import main as app_module

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def _read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def test_health_reports_app_version(tmp_path, monkeypatch):
    monkeypatch.setenv("MAIDA_DB_PATH", str(tmp_path / "v.db"))
    health = TestClient(app_module.app).get("/api/health").json()
    assert health["version"] == app_module.APP_VERSION
    assert app_module.app.version == app_module.APP_VERSION
    assert app_module.app.title.endswith(app_module.APP_VERSION)


def test_packaged_and_cited_versions_match_app_version():
    pyproject = re.search(r'^version\s*=\s*"([^"]+)"', _read("backend/pyproject.toml"), re.M)
    citation = re.search(r'^version:\s*"([^"]+)"', _read("CITATION.cff"), re.M)
    zenodo = re.search(r'"version":\s*"([^"]+)"', _read(".zenodo.json"))
    assert pyproject and pyproject.group(1) == app_module.APP_VERSION
    assert citation and citation.group(1) == app_module.APP_VERSION
    assert zenodo and zenodo.group(1) == app_module.APP_VERSION


def test_legacy_record_without_variance_is_derived_on_verify(tmp_path, monkeypatch):
    """7.2.1: a pre-7.2.0 record (r and n, no variance) becomes lockable after
    the PI's first verification, without any override."""
    monkeypatch.setenv("MAIDA_DB_PATH", str(tmp_path / "legacy.db"))
    from models import StudyDatabaseEntry

    legacy = StudyDatabaseEntry(
        study_id="legacy-1", paper_title="Old", authors="A", year=2010, country="VN",
        sample_n=150, effect_r=0.20, extraction_confidence=1.0,
        requires_verification=True, pi_locked=False,
    )
    assert legacy.variance_r is None
    app_module._studies.put(legacy)
    client = TestClient(app_module.app)
    v = client.patch("/api/studies/legacy-1/verify",
                     json={"study_id": "legacy-1", "pi_approved": True, "pi_notes": "ok",
                           "field_overrides": {}}).json()
    assert abs(v["variance_r"] - (1 - 0.2 ** 2) ** 2 / 149) < 1e-12
    assert abs(v["variance_z"] - 1 / 147) < 1e-12
    assert v["metric_type"] == "zero_order" and v["variance_formula"] == "(1 - r^2)^2 / (n - 1)"
    assert v["pi_edited_fields"] == []  # nothing was overridden
    assert v["extraction_confidence"] == 1.0
    assert client.post("/api/studies/legacy-1/lock").status_code == 200
