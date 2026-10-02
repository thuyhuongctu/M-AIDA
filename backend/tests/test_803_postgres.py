"""8.0: Postgres/Supabase specifics. Runs only with MAIDA_TEST_PG_URL set
(see conftest.py); skipped on the default SQLite run.

Pins the fix for the Supabase Data API exposure: after migrating, the roles
PostgREST uses (anon, authenticated) hold no privilege on any M-AIDA table
and every table has row level security enabled, while the backend (the table
owner) keeps working.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

from conftest import PG_URL, fresh_database_url

pytestmark = pytest.mark.skipif(not PG_URL, reason="MAIDA_TEST_PG_URL not set")

MIGRATION = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0002_lock_down_data_api.py"


def _locked_tables() -> set[str]:
    spec = importlib.util.spec_from_file_location("m0002", MIGRATION)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return set(mod.TABLES)


def test_every_table_in_the_schema_is_covered_by_the_lockdown():
    from db import Base

    assert set(Base.metadata.tables) | {"alembic_version"} == _locked_tables()


def test_migration_revokes_api_roles_and_enables_rls(tmp_path):
    from store import StudyStore

    url = fresh_database_url(tmp_path, "rls")
    store = StudyStore(url)  # runs alembic upgrade head
    eng = create_engine(url)
    with eng.connect() as conn:
        rls = dict(conn.execute(text(
            "SELECT c.relname, c.relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r'"
        )).all())
        assert set(rls) == _locked_tables()
        assert all(rls.values()), rls
        grants = conn.execute(text(
            "SELECT grantee, table_name, privilege_type FROM information_schema.role_table_grants "
            "WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated')"
        )).all()
        assert grants == [], grants
        seq = conn.execute(text(
            "SELECT count(*) FROM information_schema.role_usage_grants "
            "WHERE object_schema = 'public' AND grantee IN ('anon', 'authenticated')"
        )).scalar()
        assert seq == 0
        # The anon role, as PostgREST would use it, cannot read a single row.
        conn.execute(text("SET ROLE anon"))
        with pytest.raises(ProgrammingError, match="permission denied"):
            conn.execute(text("SELECT * FROM studies")).all()
        conn.rollback()
    eng.dispose()
    # The owner (the backend's connection) is unaffected.
    assert store.count() == 0
    store.close()


def test_postgres_types_round_trip(tmp_path):
    """JSONB payload, timezone-aware timestamps and the ledger lock on Postgres."""
    from credits import CreditService, InsufficientCredits
    from db import User, utcnow
    from models import StudyDatabaseEntry
    from store import StudyStore

    store = StudyStore(fresh_database_url(tmp_path, "types"))
    entry = StudyDatabaseEntry(study_id="P1", paper_title="Tiếng Việt có dấu", authors="Đỗ, T. H.", year=2024,
                               country="Việt Nam", effect_r=0.12, sample_n=300, extraction_confidence=1.0,
                               requires_verification=False)
    with store.session_factory() as s:
        s.add(User(id="u1", email="u1@example.org", created_at=utcnow()))
        s.commit()
    store.put(entry, owner_id="u1")
    got = store.get("P1", owner_id="u1")
    assert got is not None and got.paper_title == "Tiếng Việt có dấu" and got.country == "Việt Nam"
    assert got.extracted_at.tzinfo is not None
    assert store.get("P1", owner_id="someone-else") is None
    credits = CreditService(store.session_factory)
    credits.grant("u1", 2, reason="grant_beta")
    credits.charge("u1", "job-1")
    credits.charge("u1", "job-2")
    with pytest.raises(InsufficientCredits):
        credits.charge("u1", "job-3")
    assert credits.balance("u1") == 0
    store.close()
