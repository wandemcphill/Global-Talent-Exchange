from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.db import get_database_url, get_target_metadata, load_model_modules  # noqa: E402
from migrations.version_table import ensure_postgresql_version_table_capacity, version_table_options  # noqa: E402

config = context.config

load_model_modules()
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", get_database_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = get_target_metadata()


def _context_configure_kwargs() -> dict[str, object]:
    return {
        "target_metadata": target_metadata,
        "compare_type": True,
        **version_table_options(),
    }


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_context_configure_kwargs(),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        with connection.begin():
            ensure_postgresql_version_table_capacity(connection)

        context.configure(connection=connection, **_context_configure_kwargs())

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
