from __future__ import annotations

import pytest

from app.core.config import normalize_database_url, normalize_psycopg_url
from scripts.seed_coherent_regens import _clean_db_url


@pytest.mark.parametrize(
    "raw_input,expected",
    [
        (
            '""postgresql://postgres.example:sample_pass@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode"',  # pragma: allowlist secret
            "postgresql://postgres.example:sample_pass@aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode",  # pragma: allowlist secret
        ),
        (
            '"postgresql://user:pass@host:5432/db"',  # pragma: allowlist secret
            "postgresql://user:pass@host:5432/db",  # pragma: allowlist secret
        ),
        (
            "'postgresql://user:pass@host:5432/db'",  # pragma: allowlist secret
            "postgresql://user:pass@host:5432/db",  # pragma: allowlist secret
        ),
        (
            'export DATABASE_URL="postgresql://user:pass@host:5432/db"',  # pragma: allowlist secret
            "postgresql://user:pass@host:5432/db",  # pragma: allowlist secret
        ),
        (
            "DATABASE_URL=postgresql://user:pass@host:5432/db",  # pragma: allowlist secret
            "postgresql://user:pass@host:5432/db",  # pragma: allowlist secret
        ),
        (
            "postgresql+psycopg://user:pass@host:5432/db",  # pragma: allowlist secret
            "postgresql://user:pass@host:5432/db",  # pragma: allowlist secret
        ),
        (
            "   postgresql://user:pass@host:5432/db   ",  # pragma: allowlist secret
            "postgresql://user:pass@host:5432/db",  # pragma: allowlist secret
        ),
    ],
)
def test_normalize_psycopg_url(raw_input: str, expected: str) -> None:
    assert normalize_psycopg_url(raw_input) == expected
    assert _clean_db_url(raw_input) == expected


def test_normalize_database_url_strips_stray_quotes() -> None:
    raw = '""postgresql://user:pass@host:5432/db"'  # pragma: allowlist secret
    normalized = normalize_database_url(raw)
    assert normalized == "postgresql+psycopg://user:pass@host:5432/db"  # pragma: allowlist secret
