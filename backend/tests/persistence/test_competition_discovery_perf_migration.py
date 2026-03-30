from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "20260330_0075_competition_discovery_perf_indexes.py"
)
MODULE_NAME = "migration_20260330_0075_competition_discovery_perf_indexes"


def _load_migration_module():
    spec = spec_from_file_location(MODULE_NAME, MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_competition_discovery_perf_migration_skips_missing_tables(monkeypatch) -> None:
    migration = _load_migration_module()
    create_calls: list[tuple[str, str, tuple[str, ...], bool]] = []

    class _Inspector:
        @staticmethod
        def has_table(_table_name: str) -> bool:
            return False

        @staticmethod
        def get_indexes(_table_name: str) -> list[dict[str, object]]:
            return []

    monkeypatch.setattr(migration.op, "get_bind", lambda: object())
    monkeypatch.setattr(migration.sa, "inspect", lambda _bind: _Inspector())
    monkeypatch.setattr(
        migration.op,
        "create_index",
        lambda index_name, table_name, columns, unique=False: create_calls.append(
            (index_name, table_name, tuple(columns), unique)
        ),
    )

    migration.upgrade()

    assert create_calls == []


def test_competition_discovery_perf_migration_adds_expected_indexes(monkeypatch) -> None:
    migration = _load_migration_module()
    create_calls: list[tuple[str, str, tuple[str, ...], bool]] = []

    class _Inspector:
        @staticmethod
        def has_table(_table_name: str) -> bool:
            return True

        @staticmethod
        def get_indexes(_table_name: str) -> list[dict[str, object]]:
            return []

    monkeypatch.setattr(migration.op, "get_bind", lambda: object())
    monkeypatch.setattr(migration.sa, "inspect", lambda _bind: _Inspector())
    monkeypatch.setattr(
        migration.op,
        "create_index",
        lambda index_name, table_name, columns, unique=False: create_calls.append(
            (index_name, table_name, tuple(columns), unique)
        ),
    )

    migration.upgrade()

    assert create_calls == [
        ("ix_user_competitions_visibility_created_at", "user_competitions", ("visibility", "created_at"), False),
        (
            "ix_user_competitions_format_visibility_created_at",
            "user_competitions",
            ("format", "visibility", "created_at"),
            False,
        ),
        ("ix_user_competitions_host_user_id_created_at", "user_competitions", ("host_user_id", "created_at"), False),
        (
            "ix_user_hosted_competitions_visibility_created_at",
            "user_hosted_competitions",
            ("visibility", "created_at"),
            False,
        ),
        (
            "ix_user_hosted_competitions_host_user_id_created_at",
            "user_hosted_competitions",
            ("host_user_id", "created_at"),
            False,
        ),
    ]
