"""Teams: members invited into the owner's workspace; who uploaded each job.

Adds:

* ``team_members`` - one row per e-mail the owner invited into the owner's
  workspace (``owner_id``); ``member_id`` is filled in the first time that
  address signs in. Unique on (owner_id, email).
* ``extraction_jobs.submitted_by`` - the account that uploaded the PDF, so
  a team member's uploads are rate-limited per person while the owner pays.

The new table is closed to the Supabase Data API exactly like the tables of
0002 (REVOKE ALL from anon/authenticated, ENABLE ROW LEVEL SECURITY with no
policy). tests/test_803_postgres.py and tests/test_806_team.py check that the
TABLES lists of 0002 and of this migration together cover db.Base.metadata.

Revision ID: 0005_team
Revises: 0004_report_settings
Create Date: 2026-10-05
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0005_team"
down_revision = "0004_report_settings"
branch_labels = None
depends_on = None

#: Tables this migration adds; locked down below (see 0002 for the reason).
TABLES = ("team_members",)


def upgrade() -> None:
    op.create_table(
        "team_members",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("member_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ux_team_owner_email", "team_members", ["owner_id", "email"], unique=True)
    op.create_index("ix_team_member", "team_members", ["member_id"])
    op.create_index("ix_team_email", "team_members", ["email"])
    with op.batch_alter_table("extraction_jobs") as batch:
        batch.add_column(sa.Column("submitted_by", sa.String(64), nullable=True))

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
        op.execute(f'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM "{role}"')


def downgrade() -> None:
    with op.batch_alter_table("extraction_jobs") as batch:
        batch.drop_column("submitted_by")
    op.drop_index("ix_team_email", table_name="team_members")
    op.drop_index("ix_team_member", table_name="team_members")
    op.drop_index("ux_team_owner_email", table_name="team_members")
    op.drop_table("team_members")
