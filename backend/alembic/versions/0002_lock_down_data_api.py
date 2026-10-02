"""Close the Supabase Data API to M-AIDA's tables (Postgres only).

Why: on Supabase every table created in the ``public`` schema is granted ALL
to the ``anon`` and ``authenticated`` roles by default privileges, and the
project's REST API (PostgREST) serves those roles to anyone holding the
anon/publishable key - which is public, because the browser needs it to sign
in. Without this migration a visitor could read and write every study, job,
ledger entry and user row directly at https://<ref>.supabase.co/rest/v1/...,
bypassing the backend's owner checks entirely.

What: for every M-AIDA table (and Alembic's own version table)
  1. REVOKE ALL from anon and authenticated (the roles PostgREST uses);
  2. ENABLE ROW LEVEL SECURITY with no policy, so even a future accidental
     GRANT returns nothing to those roles.
The backend connects as the table owner (``postgres``), which RLS does not
restrict unless forced, so the application is unaffected. On a Postgres
without the Supabase roles (self-hosted), the REVOKE is skipped.

Revision ID: 0002_lock_down_data_api
Revises: 0001_v8_initial
Create Date: 2026-10-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_lock_down_data_api"
down_revision = "0001_v8_initial"
branch_labels = None
depends_on = None

#: Every table this application owns. tests/test_803_postgres.py asserts
#: that this list covers db.Base.metadata, so a table added later without
#: being listed here fails the suite.
TABLES = (
    "users",
    "studies",
    "extraction_jobs",
    "llm_calls",
    "credit_ledger",
    "orders",
    "audit_log",
    "alembic_version",
)

API_ROLES = ("anon", "authenticated")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f'ALTER TABLE IF EXISTS public."{table}" ENABLE ROW LEVEL SECURITY')
    roles = [r for (r,) in bind.execute(sa.text(
        "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated') ORDER BY rolname"
    ))]
    for role in roles:
        for table in TABLES:
            op.execute(f'REVOKE ALL ON TABLE public."{table}" FROM "{role}"')
        # Sequences behind the integer primary keys (llm_calls, credit_ledger, audit_log).
        op.execute(f'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM "{role}"')


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f'ALTER TABLE IF EXISTS public."{table}" DISABLE ROW LEVEL SECURITY')
    # Privileges are deliberately not re-granted: re-opening the Data API
    # must be a conscious, separate decision.
