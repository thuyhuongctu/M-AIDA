"""Per-account report settings (PRISMA 2020 counts entered on the Reports tab).

M-AIDA does not run the search or the screening, so the first boxes of a
PRISMA flow (records identified, duplicates removed, records screened, reports
assessed) are typed in by the researcher and kept per account in
``users.report_settings`` (JSON text). The later boxes are counted from the
records themselves. No table is added, so 0002's lock-down list is unchanged.

Revision ID: 0004_report_settings
Revises: 0003_payments
Create Date: 2026-10-05
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004_report_settings"
down_revision = "0003_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("report_settings", sa.Text(), nullable=False, server_default="{}"))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("report_settings")
