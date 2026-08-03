"""Regression tests for protected staging migration and smoke checks."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from ops import staging_migration, staging_smoke


def _database(path: Path, *, rows: int = 1) -> Path:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE studies (
                study_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        for index in range(rows):
            conn.execute(
                "INSERT INTO studies(study_id, payload) VALUES (?, ?)",
                (f"study-{index}", json.dumps({"study_id": f"study-{index}"})),
            )
        conn.commit()
    finally:
        conn.close()
    return path


def test_migration_is_fail_closed(tmp_path):
    database = _database(tmp_path / "maida.db")
    with pytest.raises(staging_migration.MigrationBlocked):
        staging_migration.migrate_database(
            database,
            environment="production",
            confirmation=staging_migration.EXPECTED_CONFIRMATION,
        )
    with pytest.raises(staging_migration.MigrationBlocked):
        staging_migration.migrate_database(
            database,
            environment="staging",
            confirmation="yes",
        )


def test_migration_backs_up_and_preserves_records(tmp_path):
    database = _database(tmp_path / "maida.db", rows=2)
    report = staging_migration.migrate_database(
        database,
        environment="staging",
        confirmation=staging_migration.EXPECTED_CONFIRMATION,
        backup_dir=tmp_path / "backups",
    )
    assert report["status"] == "migrated"
    assert report["study_count_before"] == report["study_count_after"] == 2
    assert Path(report["backup"]).exists()

    conn = sqlite3.connect(database)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' "
            "AND name='idx_studies_updated_at'"
        ).fetchone()
    finally:
        conn.close()


def test_dry_run_does_not_change_database(tmp_path):
    database = _database(tmp_path / "maida.db")
    before = database.read_bytes()
    report = staging_migration.migrate_database(
        database,
        environment="staging",
        confirmation=staging_migration.EXPECTED_CONFIRMATION,
        dry_run=True,
    )
    assert report["status"] == "dry-run"
    assert report["backup"] is None
    assert database.read_bytes() == before


class _Response:
    def __init__(self, payload):
        self.status = 200
        self._payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._payload


def test_smoke_is_read_only_and_cross_checks_counts(tmp_path, monkeypatch):
    database = _database(tmp_path / "maida.db", rows=2)
    staging_migration.migrate_database(
        database,
        environment="staging",
        confirmation=staging_migration.EXPECTED_CONFIRMATION,
    )

    def fake_urlopen(request: Request, timeout: float):
        assert timeout == 4
        if request.full_url.endswith("/api/health"):
            return _Response(
                {
                    "status": "ok",
                    "version": "7.1.1",
                    "storage": "sqlite",
                    "study_count": 2,
                    "demo_mode": False,
                }
            )
        if request.full_url.endswith("/api/studies"):
            return _Response([{"study_id": "study-0"}, {"study_id": "study-1"}])
        raise AssertionError(request.full_url)

    monkeypatch.setattr(staging_smoke, "urlopen", fake_urlopen)
    report = staging_smoke.run_smoke(
        database=database,
        base_url="https://staging.example.test",
        timeout=4,
    )
    assert report["status"] == "passed"
    assert report["database"]["study_count"] == 2
