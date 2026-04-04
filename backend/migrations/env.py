from __future__ import annotations

from logging.config import fileConfig
import os
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import create_engine, pool, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.core.config import reset_settings_cache  # noqa: E402
from app.db import get_database_url, get_target_metadata, load_model_modules  # noqa: E402

config = context.config
_database_url_override = config.get_main_option("sqlalchemy.url").strip() or None
_previous_database_url = os.environ.get("DATABASE_URL")
_restore_database_url_override = False


def _apply_database_url_override() -> None:
    global _restore_database_url_override
    if _database_url_override is None:
        return
    os.environ["DATABASE_URL"] = _database_url_override
    reset_settings_cache()
    _restore_database_url_override = True


def _restore_database_url() -> None:
    if not _restore_database_url_override:
        return
    if _previous_database_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = _previous_database_url
    reset_settings_cache()


_apply_database_url_override()
load_model_modules()
config.set_main_option("sqlalchemy.url", get_database_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = get_target_metadata()


def _ensure_alembic_version_capacity(connection) -> None:
    """Widen Alembic's version column before long revision IDs are applied."""
    version_type = connection.execute(text("""
            SELECT data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'alembic_version'
              AND column_name = 'version_num'
            """)).fetchone()
    if version_type is None:
        return

    data_type, max_length = version_type
    if data_type != "character varying":
        return
    if max_length is not None and max_length >= 255:
        return

    connection.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"))


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
        get_database_url(),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _ensure_alembic_version_capacity(connection)
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
