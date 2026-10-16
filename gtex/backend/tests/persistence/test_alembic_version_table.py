from __future__ import annotations

from unittest.mock import Mock

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import dialect as postgresql_dialect

from migrations import version_table
from migrations.version_table import ALEMBIC_VERSION_NUM_LENGTH, GtexPostgresqlImpl, ensure_postgresql_version_table_capacity


def test_postgresql_version_table_impl_uses_extended_version_num_length() -> None:
    impl = GtexPostgresqlImpl(postgresql_dialect(), None, False, None, None, {})

    table = impl.version_table_impl(
        version_table="alembic_version",
        version_table_schema=None,
        version_table_pk=True,
    )

    assert table.c.version_num.type.length == ALEMBIC_VERSION_NUM_LENGTH


def test_existing_short_postgresql_version_table_is_widened(monkeypatch) -> None:
    connection = Mock()
    connection.dialect.name = "postgresql"

    inspector = Mock()
    inspector.has_table.return_value = True
    inspector.get_columns.return_value = [{"name": "version_num", "type": String(32)}]
    monkeypatch.setattr(version_table, "inspect", lambda _connection: inspector)

    changed = ensure_postgresql_version_table_capacity(connection)

    assert changed is True
    executed = str(connection.execute.call_args.args[0])
    assert executed == 'ALTER TABLE "alembic_version" ALTER COLUMN "version_num" TYPE VARCHAR(64)'


def test_existing_wide_postgresql_version_table_is_left_unchanged(monkeypatch) -> None:
    connection = Mock()
    connection.dialect.name = "postgresql"

    inspector = Mock()
    inspector.has_table.return_value = True
    inspector.get_columns.return_value = [{"name": "version_num", "type": String(ALEMBIC_VERSION_NUM_LENGTH)}]
    monkeypatch.setattr(version_table, "inspect", lambda _connection: inspector)

    changed = ensure_postgresql_version_table_capacity(connection)

    assert changed is False
    connection.execute.assert_not_called()
