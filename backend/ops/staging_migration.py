"""Fail-closed SQLite migration for the protected M-AIDA staging environment.

The command refuses to run unless both the environment and confirmation phrase
match exactly. Before any schema change it runs SQLite integrity checks and
creates a timestamped online backup. All migration statements execute inside an
exclusive transaction, so failure rolls back without partially changing the DB.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EXPECTED_ENVIRONMENT = "staging"
EXPECTED_CONFIRMATION = "MIGRATE-STAGING"
TARGET_VERSION = 1
_REQUIRED_STUDY_COLUMNS = {"study_id", "payload", "updated_at"}


class MigrationBlocked(RuntimeError):
    """Raised when a staging safety precondition is not satisfied."""


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _study_count(conn: sqlite3.Connection) -> int:
    if not _table_exists(conn, "studies"):
        return 0
    row = conn.execute("SELECT COUNT(*) FROM studies").fetchone()
    return int(row[0])


def _integrity_check(conn: sqlite3.Connection) -> None:
    rows = [row[0] for row in conn.execute("PRAGMA quick_check").fetchall()]
    if rows != ["ok"]:
        raise MigrationBlocked(f"SQLite quick_check failed: {rows}")
    foreign_key_rows = conn.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_rows:
        raise MigrationBlocked(
            f"SQLite foreign_key_check failed: {foreign_key_rows[:5]}"
        )


def _validate_studies_schema(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "studies"):
        raise MigrationBlocked("Required table 'studies' does not exist.")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(studies)")}
    missing = sorted(_REQUIRED_STUDY_COLUMNS - columns)
    if missing:
        raise MigrationBlocked(f"studies table is missing columns: {missing}")


def _guard(environment: str, confirmation: str, database: Path) -> None:
    if environment != EXPECTED_ENVIRONMENT:
        raise MigrationBlocked(
            f"Refusing migration outside {EXPECTED_ENVIRONMENT!r}; "
            f"received {environment!r}."
        )
    if confirmation != EXPECTED_CONFIRMATION:
        raise MigrationBlocked("Confirmation phrase does not match exactly.")
    if not database.exists() or not database.is_file():
        raise MigrationBlocked(
            f"Database must already exist as a regular file: {database}"
        )


def _backup_database(conn: sqlite3.Connection, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise MigrationBlocked(f"Backup destination already exists: {destination}")
    backup = sqlite3.connect(destination)
    try:
        conn.backup(backup)
        backup.commit()
    finally:
        backup.close()


def migrate_database(
    database: str | Path,
    *,
    environment: str,
    confirmation: str,
    dry_run: bool = False,
    backup_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Validate and optionally migrate one existing staging SQLite database."""
    db_path = Path(database).expanduser().resolve()
    _guard(environment, confirmation, db_path)

    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    backup_path: Path | None = None
    try:
        _integrity_check(conn)
        _validate_studies_schema(conn)
        count_before = _study_count(conn)
        version_before = int(conn.execute("PRAGMA user_version").fetchone()[0])
        if version_before > TARGET_VERSION:
            raise MigrationBlocked(
                f"Database schema version {version_before} is newer than supported "
                f"version {TARGET_VERSION}."
            )

        report: dict[str, Any] = {
            "status": "dry-run" if dry_run else "migrated",
            "environment": environment,
            "database": str(db_path),
            "database_sha256_before": _sha256(db_path),
            "schema_version_before": version_before,
            "schema_version_target": TARGET_VERSION,
            "study_count_before": count_before,
            "started_at": datetime.now(UTC).isoformat(),
        }
        if dry_run:
            report.update(
                {
                    "schema_version_after": version_before,
                    "study_count_after": count_before,
                    "backup": None,
                    "finished_at": datetime.now(UTC).isoformat(),
                }
            )
            return report

        backup_root = (
            Path(backup_dir).expanduser().resolve()
            if backup_dir is not None
            else db_path.parent / "backups"
        )
        backup_path = backup_root / f"{db_path.name}.{_utc_stamp()}.bak"
        _backup_database(conn, backup_path)

        conn.execute("BEGIN EXCLUSIVE")
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version INTEGER PRIMARY KEY, "
                "name TEXT NOT NULL, "
                "applied_at TEXT NOT NULL DEFAULT (datetime('now'))"
                ")"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_studies_updated_at "
                "ON studies(updated_at)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, name) "
                "VALUES (1, 'baseline-schema-guard')"
            )
            conn.execute(f"PRAGMA user_version = {TARGET_VERSION}")
            _validate_studies_schema(conn)
            if _study_count(conn) != count_before:
                raise MigrationBlocked("Study count changed during schema migration.")
            _integrity_check(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        version_after = int(conn.execute("PRAGMA user_version").fetchone()[0])
        count_after = _study_count(conn)
        report.update(
            {
                "schema_version_after": version_after,
                "study_count_after": count_after,
                "backup": str(backup_path),
                "backup_sha256": _sha256(backup_path),
                "database_sha256_after": _sha256(db_path),
                "finished_at": datetime.now(UTC).isoformat(),
            }
        )
        return report
    finally:
        conn.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, help="Existing staging SQLite file")
    parser.add_argument("--environment", required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--backup-dir")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", help="Optional JSON report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = migrate_database(
            args.database,
            environment=args.environment,
            confirmation=args.confirm,
            dry_run=args.dry_run,
            backup_dir=args.backup_dir,
        )
    except (MigrationBlocked, sqlite3.Error, OSError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, indent=2))
        return 2

    payload = json.dumps(report, indent=2, sort_keys=True)
    print(payload)
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
