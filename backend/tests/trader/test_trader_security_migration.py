from __future__ import annotations

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa


def test_optional_trader_recovery_credentials_migration_preserves_existing_rows() -> None:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "migrations"
        / "versions"
        / "20261116_0255_optional_trader_recovery_credentials.py"
    )
    spec = importlib.util.spec_from_file_location("optional_trader_recovery_credentials", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "CREATE TABLE trader_security ("
                "id VARCHAR(36) PRIMARY KEY, "
                "user_id VARCHAR(36) NOT NULL, "
                "totp_secret_hash VARCHAR(255) NOT NULL, "
                "two_factor_enabled BOOLEAN NOT NULL, "
                "backup_codes_json JSON NOT NULL, "
                "recovery_phrase_hash VARCHAR(255) NOT NULL, "
                "security_pin_hash VARCHAR(255) NOT NULL)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO trader_security VALUES "
                "('security-1', 'user-1', 'totp-hash', 1, '[]', 'recovery-hash', 'pin-hash')"
            )
        )
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()

        columns = {column["name"]: column for column in sa.inspect(connection).get_columns("trader_security")}
        assert columns["recovery_phrase_hash"]["nullable"] is True
        assert columns["security_pin_hash"]["nullable"] is True
        row = connection.execute(
            sa.text("SELECT id, recovery_phrase_hash, security_pin_hash FROM trader_security")
        ).one()
        assert tuple(row) == ("security-1", "recovery-hash", "pin-hash")
    engine.dispose()
