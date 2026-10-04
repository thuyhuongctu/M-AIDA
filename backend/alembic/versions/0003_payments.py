"""Credit-pack purchases: payment fields on orders, one purchase credit per order.

Adds to ``orders`` what a payOS payment link needs (numeric order code,
pack, checkout URL, bank reference, paid/expiry/updated timestamps) and two
indexes:

* ``ux_orders_order_code`` - payOS identifies an order by its numeric code,
  so the code must be unique.
* ``ux_ledger_purchase_order`` - a partial unique index on
  ``credit_ledger(ref_order_id) WHERE reason = 'purchase'``: whatever happens
  (a webhook retried by payOS, a webhook racing the "check payment" button),
  one order can add credits only once.

Both indexes are plain SQL on Postgres and SQLite (partial indexes exist in
both). No table is added, so 0002's lock-down list is unchanged.

Revision ID: 0003_payments
Revises: 0002_lock_down_data_api
Create Date: 2026-10-04
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003_payments"
down_revision = "0002_lock_down_data_api"
branch_labels = None
depends_on = None


def _tz():
    return sa.DateTime(timezone=True)


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("order_code", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("pack_id", sa.String(32), nullable=False, server_default=""))
        batch.add_column(sa.Column("checkout_url", sa.String(500), nullable=False, server_default=""))
        batch.add_column(sa.Column("payment_reference", sa.String(120), nullable=False, server_default=""))
        batch.add_column(sa.Column("paid_at", _tz(), nullable=True))
        batch.add_column(sa.Column("expires_at", _tz(), nullable=True))
        batch.add_column(sa.Column("updated_at", _tz(), nullable=True))
    op.create_index("ux_orders_order_code", "orders", ["order_code"], unique=True)
    op.create_index("ix_orders_owner_created", "orders", ["owner_id", "created_at"])
    op.create_index(
        "ux_ledger_purchase_order", "credit_ledger", ["ref_order_id"], unique=True,
        postgresql_where=sa.text("reason = 'purchase'"),
        sqlite_where=sa.text("reason = 'purchase'"),
    )


def downgrade() -> None:
    op.drop_index("ux_ledger_purchase_order", table_name="credit_ledger")
    op.drop_index("ix_orders_owner_created", table_name="orders")
    op.drop_index("ux_orders_order_code", table_name="orders")
    with op.batch_alter_table("orders") as batch:
        for col in ("updated_at", "expires_at", "paid_at", "payment_reference",
                    "checkout_url", "pack_id", "order_code"):
            batch.drop_column(col)

