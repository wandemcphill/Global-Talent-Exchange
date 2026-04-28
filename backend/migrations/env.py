from __future__ import annotations

from logging.config import fileConfig
import os
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import Column, MetaData, String, Table, create_engine, inspect, pool, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.core.config import normalize_database_url, reset_settings_cache  # noqa: E402
from app.db import get_target_metadata, load_model_modules  # noqa: E402

config = context.config
_database_url_override = config.get_main_option("sqlalchemy.url").strip() or None
_previous_database_url = os.environ.get("DATABASE_URL")
_previous_gte_database_url = os.environ.get("GTE_DATABASE_URL")
_restore_database_url_override = False


def _apply_database_url_override() -> None:
    global _restore_database_url_override
    if _database_url_override is None:
        return
    os.environ["DATABASE_URL"] = _database_url_override
    os.environ["GTE_DATABASE_URL"] = _database_url_override
    reset_settings_cache()
    _restore_database_url_override = True


def _restore_database_url() -> None:
    if not _restore_database_url_override:
        return
    if _previous_database_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = _previous_database_url
    if _previous_gte_database_url is None:
        os.environ.pop("GTE_DATABASE_URL", None)
    else:
        os.environ["GTE_DATABASE_URL"] = _previous_gte_database_url
    reset_settings_cache()


def _effective_database_url() -> str:
    for candidate in (
        _database_url_override,
        os.environ.get("DATABASE_URL"),
        os.environ.get("GTE_DATABASE_URL"),
    ):
        if candidate and candidate.strip():
            return normalize_database_url(candidate)
    raise RuntimeError("Alembic requires sqlalchemy.url, DATABASE_URL, or GTE_DATABASE_URL.")


_apply_database_url_override()
load_model_modules()
config.set_main_option("sqlalchemy.url", _effective_database_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = get_target_metadata()
ALEMBIC_VERSION_TABLE = "alembic_version"
ALEMBIC_VERSION_COLUMN = "version_num"
ALEMBIC_VERSION_LENGTH = 255


def _ensure_alembic_version_capacity(connection) -> None:
    """Widen Alembic's version column before long revision IDs are applied."""
    if connection.dialect.name == "sqlite":
        return

    inspector = inspect(connection)
    if not inspector.has_table(ALEMBIC_VERSION_TABLE):
        Table(
            ALEMBIC_VERSION_TABLE,
            MetaData(),
            Column(ALEMBIC_VERSION_COLUMN, String(ALEMBIC_VERSION_LENGTH), nullable=False, primary_key=True),
        ).create(bind=connection)
        return

    version_column = next(
        (
            column
            for column in inspector.get_columns(ALEMBIC_VERSION_TABLE)
            if column.get("name") == ALEMBIC_VERSION_COLUMN
        ),
        None,
    )
    if version_column is None:
        return

    version_type = version_column.get("type")
    max_length = getattr(version_type, "length", None)
    if max_length is not None and max_length >= ALEMBIC_VERSION_LENGTH:
        return

    connection.execute(
        text(f"ALTER TABLE {ALEMBIC_VERSION_TABLE} ALTER COLUMN {ALEMBIC_VERSION_COLUMN} TYPE VARCHAR(255)")
    )


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        _effective_database_url(),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _ensure_alembic_version_capacity(connection)
        # Inspector queries above can autobegin a transaction on SQLAlchemy 2.x.
        # Commit that preflight work so Alembic controls the migration transaction.
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


try:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
finally:
    _restore_database_url()
