"""
Study store for M-AIDA (8.0: SQLAlchemy, SQLite or Postgres, per-owner).

History
-------
7.1.2 replaced the module-level dict with a SQLite file so verified and locked
records survive a restart. 8.0 keeps that guarantee and adds two things the
cloud deployment needs: a second backend (Postgres on Supabase) and an owner
on every record, so one database can hold many researchers' studies without
any of them seeing another's.

Design choices
--------------
* **Same surface as before** (``get``/``put``/``values``/``clear``/``__len__``/
  ``__contains__``) plus an ``owner_id`` argument. main.py, demo/run_defense.py
  and the 7.x tests keep working: with ``owner_id=None`` the store behaves as
  the single-operator store of 7.2 (owner "local").
* **One JSON payload column** remains the record of truth; a few columns are
  copied out of it for filtering and ordering (owner, lock state, year ...).
* **No schema code here**: tables come from the Alembic migration run by
  ``db.init_schema``.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.engine import Engine

from db import LOCAL_OWNER_ID, StudyRow, User, init_schema, make_engine, make_session_factory, utcnow
from models import StudyDatabaseEntry


def _as_url(target: str | Path) -> str:
    text = str(target)
    if "://" in text:
        return text
    return f"sqlite:///{text}"


class StudyStore:
    """Persistent collection of :class:`StudyDatabaseEntry`, isolated by owner."""

    def __init__(self, target: str | Path, *, engine: Engine | None = None) -> None:
        self.url = _as_url(target)
        self.engine = engine or make_engine(self.url)
        init_schema(self.engine)
        self.session_factory = make_session_factory(self.engine)
        self._ensure_local_owner()

    # -- helpers ------------------------------------------------------------

    def _ensure_local_owner(self) -> None:
        """The single-operator deployment writes every record under "local"."""
        with self.session_factory() as s:
            if s.get(User, LOCAL_OWNER_ID) is None:
                s.add(User(id=LOCAL_OWNER_ID, email="", name="Local operator", role="admin",
                           beta=False, credits_balance=0, created_at=utcnow()))
                s.commit()

    @staticmethod
    def _entry(row: StudyRow) -> StudyDatabaseEntry:
        payload = row.payload
        if isinstance(payload, str):  # defensive: legacy TEXT column
            payload = json.loads(payload)
        return StudyDatabaseEntry(**payload)

    # -- read ---------------------------------------------------------------

    def get(self, study_id: str, owner_id: str | None = None) -> StudyDatabaseEntry | None:
        """Return one entry, or ``None`` when unknown *or owned by someone else*."""
        with self.session_factory() as s:
            row = s.get(StudyRow, study_id)
        if row is None:
            return None
        if owner_id is not None and row.owner_id != owner_id:
            return None
        return self._entry(row)

    def owner_of(self, study_id: str) -> str | None:
        with self.session_factory() as s:
            row = s.get(StudyRow, study_id)
        return None if row is None else row.owner_id

    def values(self, owner_id: str | None = None) -> list[StudyDatabaseEntry]:
        """Every entry (of one owner when given), oldest first, so listings are stable."""
        stmt = select(StudyRow).order_by(StudyRow.updated_at, StudyRow.study_id)
        if owner_id is not None:
            stmt = stmt.where(StudyRow.owner_id == owner_id)
        with self.session_factory() as s:
            rows = s.scalars(stmt).all()
        return [self._entry(r) for r in rows]

    def count(self, owner_id: str | None = None, *, locked: bool | None = None) -> int:
        stmt = select(func.count()).select_from(StudyRow)
        if owner_id is not None:
            stmt = stmt.where(StudyRow.owner_id == owner_id)
        if locked is not None:
            stmt = stmt.where(StudyRow.pi_locked.is_(locked))
        with self.session_factory() as s:
            return int(s.scalar(stmt) or 0)

    def __contains__(self, study_id: object) -> bool:
        return isinstance(study_id, str) and self.get(study_id) is not None

    def __len__(self) -> int:
        return self.count()

    # -- write --------------------------------------------------------------

    def put(self, entry: StudyDatabaseEntry, owner_id: str | None = None) -> StudyDatabaseEntry:
        """Insert or replace one entry and return it unchanged.

        On update the owner is never changed: a record stays with the account
        that extracted it even if a caller passes another owner by mistake.
        """
        payload = json.loads(entry.model_dump_json())
        with self.session_factory() as s:
            row = s.get(StudyRow, entry.study_id)
            if row is None:
                owner = owner_id or LOCAL_OWNER_ID
                row = StudyRow(study_id=entry.study_id, owner_id=owner, workspace_id=owner)
                s.add(row)
            row.year = entry.year
            row.country = entry.country or ""
            row.pi_locked = bool(entry.pi_locked)
            row.requires_verification = bool(entry.requires_verification)
            row.extracted_at = entry.extracted_at
            row.locked_at = entry.locked_at
            row.updated_at = utcnow()
            row.payload = payload
            s.commit()
        return entry

    def delete(self, study_id: str, owner_id: str | None = None) -> bool:
        """Delete one entry; ``False`` when unknown or not owned by ``owner_id``."""
        with self.session_factory() as s:
            row = s.get(StudyRow, study_id)
            if row is None or (owner_id is not None and row.owner_id != owner_id):
                return False
            s.delete(row)
            s.commit()
            return True

    def clear(self, owner_id: str | None = None) -> int:
        """Delete every entry (of one owner when given); returns the count removed.

        Without an owner this is the demo-reset behaviour of 7.2 and is only
        reachable from demo/run_defense.py.
        """
        stmt = delete(StudyRow)
        if owner_id is not None:
            stmt = stmt.where(StudyRow.owner_id == owner_id)
        with self.session_factory() as s:
            result = s.execute(stmt)
            s.commit()
            return int(result.rowcount or 0)

    # -- lifecycle ----------------------------------------------------------

    def close(self) -> None:
        self.engine.dispose()
