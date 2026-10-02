"""8.0 initial schema: users, studies (with owner), jobs, llm_calls, ledger, orders, audit.

Revision ID: 0001_v8_initial
Revises:
Create Date: 2026-10-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_v8_initial"
down_revision = None
branch_labels = None
depends_on = None

JSONV = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, server_default=""),
        sa.Column("name", sa.String(200), nullable=False, server_default=""),
        sa.Column("role", sa.String(16), nullable=False, server_default="user"),
        sa.Column("beta", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("credits_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("last_seen_at", TZ, nullable=True),
    )

    # A pre-8.0 SQLite file already has a `studies` table (study_id, payload,
    # updated_at) with no owner. Migrate it in place: every existing record
    # belongs to the single local operator.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "studies" in insp.get_table_names():
        existing = {c["name"] for c in insp.get_columns("studies")}
        with op.batch_alter_table("studies") as batch:
            if "owner_id" not in existing:
                batch.add_column(sa.Column("owner_id", sa.String(64), nullable=False, server_default="local"))
            if "workspace_id" not in existing:
                batch.add_column(sa.Column("workspace_id", sa.String(64), nullable=False, server_default="local"))
            if "year" not in existing:
                batch.add_column(sa.Column("year", sa.Integer(), nullable=True))
            if "country" not in existing:
                batch.add_column(sa.Column("country", sa.String(120), nullable=False, server_default=""))
            if "pi_locked" not in existing:
                batch.add_column(sa.Column("pi_locked", sa.Boolean(), nullable=False, server_default=sa.false()))
            if "requires_verification" not in existing:
                batch.add_column(sa.Column("requires_verification", sa.Boolean(), nullable=False, server_default=sa.true()))
            if "extracted_at" not in existing:
                batch.add_column(sa.Column("extracted_at", TZ, nullable=True))
            if "locked_at" not in existing:
                batch.add_column(sa.Column("locked_at", TZ, nullable=True))
        op.execute(
            "INSERT INTO users (id, email, name, role, beta, credits_balance, created_at) "
            "SELECT 'local', '', 'Local operator', 'admin', 0, 0, CURRENT_TIMESTAMP "
            "WHERE NOT EXISTS (SELECT 1 FROM users WHERE id = 'local')"
        )
        # Back-fill the filter columns from the JSON payload (SQLite json_extract).
        # Timestamps stay NULL here; the payload keeps them and the store
        # rewrites every column on the next put().
        if bind.dialect.name == "sqlite":
            op.execute(
                "UPDATE studies SET "
                "pi_locked = COALESCE(json_extract(payload, '$.pi_locked'), 0), "
                "requires_verification = COALESCE(json_extract(payload, '$.requires_verification'), 1), "
                "year = json_extract(payload, '$.year'), "
                "country = COALESCE(json_extract(payload, '$.country'), '')"
            )
    else:
        op.create_table(
            "studies",
            sa.Column("study_id", sa.String(64), primary_key=True),
            sa.Column("owner_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("workspace_id", sa.String(64), nullable=False),
            sa.Column("year", sa.Integer(), nullable=True),
            sa.Column("country", sa.String(120), nullable=False, server_default=""),
            sa.Column("pi_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("requires_verification", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("extracted_at", TZ, nullable=True),
            sa.Column("locked_at", TZ, nullable=True),
            sa.Column("updated_at", TZ, nullable=False),
            sa.Column("payload", JSONV, nullable=False),
        )
    op.create_index("ix_studies_owner_updated", "studies", ["owner_id", "updated_at"])

    op.create_table(
        "extraction_jobs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("owner_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("filename", sa.String(300), nullable=False, server_default=""),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages", sa.Integer(), nullable=True),
        sa.Column("metadata_json", JSONV, nullable=False),
        sa.Column("study_id", sa.String(64), nullable=True),
        sa.Column("error_code", sa.String(40), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("model", sa.String(120), nullable=True),
        sa.Column("credits_charged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("started_at", TZ, nullable=True),
        sa.Column("finished_at", TZ, nullable=True),
    )
    op.create_index("ix_jobs_owner_created", "extraction_jobs", ["owner_id", "created_at"])
    op.create_index("ix_jobs_status", "extraction_jobs", ["status"])

    op.create_table(
        "llm_calls",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(64), nullable=True),
        sa.Column("owner_id", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False, server_default=""),
        sa.Column("model", sa.String(120), nullable=False, server_default=""),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("outcome", sa.String(40), nullable=False, server_default="ok"),
        sa.Column("created_at", TZ, nullable=False),
    )
    op.create_index("ix_llm_calls_owner_created", "llm_calls", ["owner_id", "created_at"])

    op.create_table(
        "credit_ledger",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("ref_job_id", sa.String(64), nullable=True),
        sa.Column("ref_order_id", sa.String(64), nullable=True),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(300), nullable=False, server_default=""),
        sa.Column("created_at", TZ, nullable=False),
    )
    op.create_index("ix_ledger_owner_created", "credit_ledger", ["owner_id", "created_at"])

    op.create_table(
        "orders",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("owner_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False, server_default=""),
        sa.Column("provider_order_id", sa.String(120), nullable=False, server_default=""),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="USD"),
        sa.Column("credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", TZ, nullable=False),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("study_id", sa.String(64), nullable=True),
        sa.Column("detail", JSONV, nullable=False),
        sa.Column("created_at", TZ, nullable=False),
    )
    op.create_index("ix_audit_owner_created", "audit_log", ["owner_id", "created_at"])


def downgrade() -> None:
    for name in ("audit_log", "orders", "credit_ledger", "llm_calls", "extraction_jobs"):
        op.drop_table(name)
    op.drop_index("ix_studies_owner_updated", table_name="studies")
    # The studies table is kept on downgrade: dropping it would destroy records.
    op.drop_table("users")
