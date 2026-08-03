"""Regression guards for the single-host persistence and staging boundary."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_production_compose_mounts_sqlite_on_durable_host_storage() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.prod.yml").read_text())
    backend = compose["services"]["backend"]

    assert backend["environment"]["MAIDA_DB_PATH"] == "/data/maida.db"
    assert "${MAIDA_DATA_DIR:-./data}:/data" in backend["volumes"]
    assert "/data/" in (ROOT / ".gitignore").read_text().splitlines()
    assert "MAIDA_DATA_DIR" in (ROOT / "DEPLOY.md").read_text()


def test_staging_workflow_requires_absolute_paths_and_https() -> None:
    workflow = (ROOT / ".github/workflows/staging-migration.yml").read_text()

    assert '[[ "$STAGING_APP_DIR" = /* ]]' in workflow
    assert '[[ "$STAGING_DB_PATH" = /* ]]' in workflow
    assert '[[ "$STAGING_BASE_URL" == https://* ]]' in workflow
    assert '[[ "$STAGING_BASE_URL" != */ ]]' in workflow
