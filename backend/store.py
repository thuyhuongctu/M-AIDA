"""
SQLite-backed study store for M-AIDA.

Why this exists
---------------
Studies used to live in a module-level ``dict``, so every backend restart threw
away the researcher's verified and locked records. That is acceptable for a
throwaway prototype and unacceptable for a live defence demo, where a crashed
or reloaded process in front of the committee would silently erase the work
just demonstrated.

Design choices
--------------
* **Standard-library ``sqlite3`` only.** The API routes are synchronous ``def``
  functions, so an async driver would buy nothing and would add a dependency.
* **One JSON payload column** rather than a column per field. ``StudyDatabaseEntry``
  is a Pydantic model that still evolves; storing the serialised model keeps the
  schema stable across model changes and keeps filtering logic in Python, exactly
  where it already lived. Effect sizes are never queried by SQL predicates here.
* **Dict-like surface** (``get``/``put``/``values``/``__len__``/``__contains__``)
  so call sites read the same as the old dict and the diff stays reviewable.

The store is safe to use from FastAPI's threadpool: the connection is opened with
``check_same_thread=False`` and every operation is serialised through a lock.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from models import StudyDatabaseEntry

_SCHEMA = """
CREATE TABLE IF NOT EXISTS studies (
    study_id   TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class StudyStore:
    """Persistent, dict-like collection of :class:`StudyDatabaseEntry` records."""

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._lock = threading.Lock()
        if self._path.parent and str(self._path.parent) not in ("", "."):
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            # WAL keeps readers from blocking on the writer, which matters when
            # the demo UI polls /api/health while an extraction is being saved.
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # -- read -------------------------------------------------------------

    def get(self, study_id: str) -> StudyDatabaseEntry | None:
        """Return one entry, or ``None`` when the id is unknown."""
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM studies WHERE study_id = ?", (study_id,)
            ).fetchone()
        if row is None:
            return None
        return StudyDatabaseEntry(**json.loads(row["payload"]))

    def values(self) -> list[StudyDatabaseEntry]:
        """Return every entry, oldest first, so listings are stable across calls."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT payload FROM studies ORDER BY updated_at, study_id"
            ).fetchall()
        return [StudyDatabaseEntry(**json.loads(r["payload"])) for r in rows]

    def __contains__(self, study_id: object) -> bool:
        return isinstance(study_id, str) and self.get(study_id) is not None

    def __len__(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM studies").fetchone()
        return int(row["n"])

    # -- write ------------------------------------------------------------

    def put(self, entry: StudyDatabaseEntry) -> StudyDatabaseEntry:
        """Insert or replace one entry and return it unchanged."""
        payload = entry.model_dump_json()
        with self._lock:
            self._conn.execute(
                "INSERT INTO studies (study_id, payload, updated_at) "
                "VALUES (?, ?, datetime('now')) "
                "ON CONFLICT(study_id) DO UPDATE SET "
                "payload = excluded.payload, updated_at = excluded.updated_at",
                (entry.study_id, payload),
            )
            self._conn.commit()
        return entry

    def clear(self) -> int:
        """Delete every entry and return how many were removed.

        Used only by the demo-reset route so a rehearsal can be replayed from a
        clean state; it is never reachable when demo mode is off.
        """
        with self._lock:
            cur = self._conn.execute("DELETE FROM studies")
            self._conn.commit()
            return int(cur.rowcount)

    # -- lifecycle --------------------------------------------------------

    def close(self) -> None:
        with self._lock:
            self._conn.close()
