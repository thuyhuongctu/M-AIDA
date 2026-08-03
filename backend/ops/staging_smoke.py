"""Read-only smoke checks for a migrated M-AIDA staging deployment."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SmokeFailure(RuntimeError):
    """Raised when a smoke-test assertion fails."""


def _get_json(url: str, *, token: str | None, timeout: float) -> Any:
    headers = {"Accept": "application/json", "User-Agent": "maida-staging-smoke/1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            if response.status != 200:
                raise SmokeFailure(f"GET {url} returned HTTP {response.status}.")
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SmokeFailure(f"GET {url} failed: {exc}") from exc


def check_database(database: str | Path) -> dict[str, Any]:
    db_path = Path(database).expanduser().resolve()
    if not db_path.exists() or not db_path.is_file():
        raise SmokeFailure(f"Database does not exist: {db_path}")
    uri = f"{db_path.as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        quick = [row[0] for row in conn.execute("PRAGMA quick_check").fetchall()]
        if quick != ["ok"]:
            raise SmokeFailure(f"SQLite quick_check failed: {quick}")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(studies)")}
        required = {"study_id", "payload", "updated_at"}
        if not required.issubset(columns):
            raise SmokeFailure(
                f"studies table is missing columns: {sorted(required - columns)}"
            )
        count = int(conn.execute("SELECT COUNT(*) FROM studies").fetchone()[0])
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        index_row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' "
            "AND name='idx_studies_updated_at'"
        ).fetchone()
        if version < 1 or index_row is None:
            raise SmokeFailure("Protected staging migration is not applied.")
        return {
            "database": str(db_path),
            "schema_version": version,
            "study_count": count,
            "quick_check": "ok",
        }
    finally:
        conn.close()


def check_api(
    base_url: str,
    *,
    token: str | None = None,
    timeout: float = 10,
    allow_demo_mode: bool = False,
) -> dict[str, Any]:
    root = base_url.rstrip("/")
    health = _get_json(f"{root}/api/health", token=token, timeout=timeout)
    studies = _get_json(f"{root}/api/studies", token=token, timeout=timeout)
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise SmokeFailure("Health payload does not report status='ok'.")
    if health.get("storage") != "sqlite":
        raise SmokeFailure("Staging API is not reporting SQLite persistence.")
    if health.get("demo_mode") and not allow_demo_mode:
        raise SmokeFailure("MAIDA_DEMO_MODE must be off for protected staging.")
    if not isinstance(studies, list):
        raise SmokeFailure("GET /api/studies did not return a list.")
    if health.get("study_count") != len(studies):
        raise SmokeFailure(
            "Health study_count does not match the studies endpoint response."
        )
    return {
        "base_url": root,
        "version": health.get("version"),
        "study_count": len(studies),
        "demo_mode": bool(health.get("demo_mode")),
        "storage": health.get("storage"),
    }


def run_smoke(
    *,
    database: str | Path,
    base_url: str,
    token: str | None = None,
    timeout: float = 10,
    allow_demo_mode: bool = False,
) -> dict[str, Any]:
    database_result = check_database(database)
    api_result = check_api(
        base_url,
        token=token,
        timeout=timeout,
        allow_demo_mode=allow_demo_mode,
    )
    if database_result["study_count"] != api_result["study_count"]:
        raise SmokeFailure(
            "Database study count does not match the running staging API."
        )
    return {
        "status": "passed",
        "checked_at": datetime.now(UTC).isoformat(),
        "database": database_result,
        "api": api_result,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--bearer-token")
    parser.add_argument("--bearer-token-stdin", action="store_true")
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--allow-demo-mode", action="store_true")
    parser.add_argument("--report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    token = args.bearer_token
    if args.bearer_token_stdin:
        token = sys.stdin.read().strip() or None
    try:
        report = run_smoke(
            database=args.database,
            base_url=args.base_url,
            token=token,
            timeout=args.timeout,
            allow_demo_mode=args.allow_demo_mode,
        )
    except (SmokeFailure, sqlite3.Error, OSError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 3
    payload = json.dumps(report, indent=2, sort_keys=True)
    print(payload)
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
