"""Regression test: a fresh database must reach alembic head.

Revisions 0108-0111 shipped with bare op.alter_column / op.create_foreign_key
calls (rejected by SQLite, which supports neither) and compared the boolean
`active` column against the integer 1 (rejected by PostgreSQL). Neither backend
could replay the chain, which meant no new environment could be provisioned and
every HTTP-level backend test errored during fixture setup.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"

# Every revision that predates 0108 already guards these operations behind a
# dialect check or batch_alter_table; this list pins the ones that regressed.
PORTABILITY_SENSITIVE_REVISIONS = (
    "20260821_0108_gift_currency_semantics.py",
    "20260822_0109_competition_fee_policy_default.py",
    "20260822_0110_agent_wallet_fail_closed.py",
    "20260822_0111_hosted_competition_template_fee_default.py",
)

_BARE_ALTER = re.compile(r"^\s*op\.(alter_column|create_foreign_key|drop_constraint)\(", re.MULTILINE)
_BOOLEAN_INT_COMPARISON = re.compile(r"\bactive\s*=\s*[01]\b")


@pytest.mark.parametrize("filename", PORTABILITY_SENSITIVE_REVISIONS)
def test_revision_avoids_sqlite_incompatible_operations(filename: str) -> None:
    source = (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")
    offenders = _BARE_ALTER.findall(source)
    assert not offenders, f"{filename} uses bare op.{offenders} instead of batch_alter_table"


@pytest.mark.parametrize("filename", PORTABILITY_SENSITIVE_REVISIONS)
def test_revision_avoids_boolean_integer_comparison(filename: str) -> None:
    source = (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")
    match = _BOOLEAN_INT_COMPARISON.search(source)
    assert match is None, f"{filename} compares the boolean 'active' column to {match.group(0)!r}"


def test_fresh_database_upgrades_to_head(tmp_path: Path) -> None:
    from alembic import command
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine

    from app.core.database import build_alembic_config

    database_url = f"sqlite+pysqlite:///{(tmp_path / 'migration_replay.db').as_posix()}"
    config = build_alembic_config(database_url)
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            applied = tuple(sorted(MigrationContext.configure(connection).get_current_heads()))
    finally:
        engine.dispose()

    expected_head = ScriptDirectory.from_config(config).get_current_head()
    assert applied == (expected_head,)
