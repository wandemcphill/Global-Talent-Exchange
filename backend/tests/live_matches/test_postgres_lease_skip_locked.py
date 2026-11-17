"""PostgreSQL row locking used by two worker connections.

SQLite ignores FOR UPDATE SKIP LOCKED. This test runs only when
GTE_TEST_POSTGRES_URL points at a real PostgreSQL database.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from app.core.database import create_database_engine

pytestmark = pytest.mark.skipif(
    not os.getenv("GTE_TEST_POSTGRES_URL"),
    reason="GTE_TEST_POSTGRES_URL is required to prove PostgreSQL SKIP LOCKED",
)


def test_skip_locked_hides_a_row_held_by_another_connection() -> None:
    engine = create_database_engine(os.environ["GTE_TEST_POSTGRES_URL"])
    holder = other = None
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS gtex_lease_probe"))
            connection.execute(text("CREATE TABLE gtex_lease_probe (id integer primary key, owner text)"))
            connection.execute(text("INSERT INTO gtex_lease_probe (id, owner) VALUES (1, 'worker-a')"))
        holder = engine.connect()
        transaction = holder.begin()
        holder.execute(text("SELECT id FROM gtex_lease_probe WHERE id = 1 FOR UPDATE"))
        other = engine.connect()
        hidden = other.execute(text("SELECT id FROM gtex_lease_probe WHERE id = 1 FOR UPDATE SKIP LOCKED")).all()
        assert hidden == []
        transaction.rollback()
    finally:
        if other is not None:
            other.close()
        if holder is not None:
            holder.close()
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS gtex_lease_probe"))
        engine.dispose()
