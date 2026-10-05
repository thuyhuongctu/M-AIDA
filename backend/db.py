"""
Relational schema and engine factory for M-AIDA 8.x.

SQLAlchemy 2 declarative models shared by the study store (store.py), the
credit ledger (credits.py) and the job pipeline (jobs.py). One schema serves
both backends:

* SQLite  - single-operator and demo deployments, the Windows runner, tests.
* Postgres - the multi-user cloud deployment (Supabase).

Every table that holds user data carries ``owner_id`` so the backend can
isolate accounts without Row Level Security: only the backend touches the
database, with one service connection, and every query filters by owner.
``workspace_id`` is written equal to ``owner_id`` for now; it exists so a
future "research group" feature does not need a migration of existing rows.

Schema changes go through Alembic (backend/alembic/versions). ``init_schema``
upgrades to head at startup, which also creates the tables of a fresh file.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    event,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

#: JSON column that becomes JSONB on Postgres and plain JSON (text) on SQLite.
JSONVariant = JSON().with_variant(postgresql.JSONB(), "postgresql")

#: Timezone-aware timestamps on Postgres; SQLite stores ISO strings.
TZDateTime = DateTime(timezone=True)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    #: Supabase ``sub`` (a UUID string) in cloud mode; "local" in admin-key mode.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    beta: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    #: Cache of the ledger balance; credit_ledger is the source of truth.
    credits_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    #: Per-account report settings as JSON text (migration 0004), e.g. the
    #: PRISMA 2020 counts the researcher enters by hand on the Reports tab.
    report_settings: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class StudyRow(Base):
    __tablename__ = "studies"

    study_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    country: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    pi_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_verification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    extracted_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)
    #: Full StudyDatabaseEntry as JSON (the record of truth; columns above are
    #: filter/sort copies). ``machine_proposal`` lives inside it and is never
    #: rewritten after extraction (main.py only copies it forward).
    payload: Mapped[dict] = mapped_column(JSONVariant, nullable=False)

    __table_args__ = (
        Index("ix_studies_owner_updated", "owner_id", "updated_at"),
    )


class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False)
    #: queued | running | succeeded | rejected | failed
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    filename: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONVariant, nullable=False, default=dict)
    study_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    #: evidence_missing | malformed_output | pdf_unreadable | provider_error |
    #: internal_error | no_api_key
    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    credits_charged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)

    __table_args__ = (
        Index("ix_jobs_owner_created", "owner_id", "created_at"),
        Index("ix_jobs_status", "status"),
    )


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    model: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: ok | evidence_missing | malformed_output | provider_error
    outcome: Mapped[str] = mapped_column(String(40), nullable=False, default="ok")
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)

    __table_args__ = (Index("ix_llm_calls_owner_created", "owner_id", "created_at"),)


class CreditLedger(Base):
    __tablename__ = "credit_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    #: purchase | extraction | refund | grant_beta | adjust_admin
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    ref_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ref_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_ledger_owner_created", "owner_id", "created_at"),
        # One purchase credit per order, whatever races (migration 0003).
        Index("ux_ledger_purchase_order", "ref_order_id", unique=True,
              postgresql_where=text("reason = 'purchase'"),
              sqlite_where=text("reason = 'purchase'")),
    )


class Order(Base):
    """Credit-pack purchases (payments.py). One row per payment link.

    ``status``: pending -> paid (credits added, exactly once) | cancelled |
    expired. The ledger entry of a paid order carries ``ref_order_id`` and a
    unique index (migration 0003) makes a second credit for the same order
    impossible even if two notifications race.
    """

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    #: Provider-side id (payOS paymentLinkId).
    provider_order_id: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    #: Price actually charged, in ``currency`` units (VND for payOS).
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)
    # -- 0003 --
    #: Numeric order code sent to payOS (unique; payOS identifies orders by it).
    order_code: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pack_id: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    checkout_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    #: Bank transfer reference reported by the provider when paid.
    payment_reference: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    paid_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)

    __table_args__ = (
        Index("ux_orders_order_code", "order_code", unique=True),
        Index("ix_orders_owner_created", "owner_id", "created_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False)
    #: extract | verify | lock | export | delete | grant | login
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    study_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict] = mapped_column(JSONVariant, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow)

    __table_args__ = (Index("ix_audit_owner_created", "owner_id", "created_at"),)


# ---------------------------------------------------------------------------
# Engine / session factory
# ---------------------------------------------------------------------------

#: Owner id used when the deployment has a single operator (auth mode admin_key).
LOCAL_OWNER_ID = "local"

_BACKEND_DIR = Path(__file__).resolve().parent


def make_engine(url: str) -> Engine:
    """Create the SQLAlchemy engine for ``url`` with backend-specific tuning."""
    if url.startswith("sqlite"):
        # One file, many FastAPI threads: allow cross-thread use and keep WAL
        # so the UI's polling reads do not block a write in progress.
        path = url.replace("sqlite:///", "", 1)
        if path and path != ":memory:":
            parent = Path(path).parent
            if str(parent) not in ("", "."):
                parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            url, connect_args={"check_same_thread": False, "timeout": 30}, future=True
        )

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):  # pragma: no cover - trivial
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        return engine
    # Postgres (Supabase): small pool, pre-ping so a pooler-side drop is
    # noticed before a request uses a dead connection. prepare_threshold=None
    # disables psycopg's server-side prepared statements, which Supabase's
    # transaction-mode pooler (port 6543) does not support.
    connect_args = {"prepare_threshold": None, "connect_timeout": 10} if "psycopg" in url else {}
    return create_engine(
        url, pool_size=5, max_overflow=5, pool_pre_ping=True, future=True,
        connect_args=connect_args,
    )


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


_migrate_lock = threading.Lock()


def init_schema(engine: Engine) -> None:
    """Bring the database to the current schema (Alembic head)."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
    cfg.attributes["connection_engine"] = engine
    with _migrate_lock:
        command.upgrade(cfg, "head")
