from __future__ import annotations

from alembic.ddl.postgresql import PostgresqlImpl
from sqlalchemy import Column, MetaData, PrimaryKeyConstraint, String, Table, inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.sql import sqltypes

ALEMBIC_VERSION_NUM_LENGTH = 64
ALEMBIC_VERSION_TABLE = "alembic_version"
ALEMBIC_VERSION_TABLE_SCHEMA: str | None = None


class GtexPostgresqlImpl(PostgresqlImpl):
    __dialect__ = "postgresql"

    def version_table_impl(
        self,
        *,
        version_table: str,
        version_table_schema: str | None,
        version_table_pk: bool,
        **kw: object,
    ) -> Table:
        version_table_definition = Table(
            version_table,
            MetaData(),
            Column("version_num", String(ALEMBIC_VERSION_NUM_LENGTH), nullable=False),
            schema=version_table_schema,
        )
        if version_table_pk:
            version_table_definition.append_constraint(
                PrimaryKeyConstraint("version_num", name=f"{version_table}_pkc")
            )
        return version_table_definition


def version_table_options() -> dict[str, object]:
    options: dict[str, object] = {"version_table": ALEMBIC_VERSION_TABLE}
    if ALEMBIC_VERSION_TABLE_SCHEMA is not None:
        options["version_table_schema"] = ALEMBIC_VERSION_TABLE_SCHEMA
    return options


def ensure_postgresql_version_table_capacity(
    connection: Connection,
    *,
    version_table: str = ALEMBIC_VERSION_TABLE,
    version_table_schema: str | None = ALEMBIC_VERSION_TABLE_SCHEMA,
) -> bool:
    if connection.dialect.name != "postgresql":
        return False

    inspector = inspect(connection)
    if not inspector.has_table(version_table, schema=version_table_schema):
        return False

    columns = inspector.get_columns(version_table, schema=version_table_schema)
    for column in columns:
        if column.get("name") != "version_num":
            continue
        column_type = column.get("type")
        length = getattr(column_type, "length", None)
        if isinstance(column_type, sqltypes.String) and (length is None or length >= ALEMBIC_VERSION_NUM_LENGTH):
            return False

        connection.execute(
            text(
                "ALTER TABLE "
                f"{_qualified_table_name(version_table, version_table_schema)} "
                f'ALTER COLUMN "{_quote_identifier("version_num", include_quotes=False)}" '
                f"TYPE VARCHAR({ALEMBIC_VERSION_NUM_LENGTH})"
            )
        )
        return True

    return False


def _qualified_table_name(table_name: str, schema: str | None) -> str:
    quoted_table_name = _quote_identifier(table_name)
    if schema is None:
        return quoted_table_name
    return f"{_quote_identifier(schema)}.{quoted_table_name}"


def _quote_identifier(identifier: str, *, include_quotes: bool = True) -> str:
    escaped = identifier.replace('"', '""')
    if not include_quotes:
        return escaped
    return f'"{escaped}"'
