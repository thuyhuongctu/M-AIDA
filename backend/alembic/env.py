"""Alembic environment: runs migrations against the engine handed over by
db.init_schema (attribute "connection_engine"), or against DATABASE_URL /
MAIDA_DB_PATH when invoked from the command line."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import Base  # noqa: E402

config = context.config
target_metadata = Base.metadata


def _url_from_env() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if url:
        return url
    return f"sqlite:///{os.environ.get('MAIDA_DB_PATH', 'maida.db')}"


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url") or _url_from_env(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = config.attributes.get("connection_engine")
    if engine is None:
        section = config.get_section(config.config_ini_section) or {}
        section["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url") or _url_from_env()
        engine = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
