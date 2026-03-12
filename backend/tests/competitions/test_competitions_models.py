from __future__ import annotations

from datetime import datetime, timezone

from alembic import command
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
import pytest

from backend.app.core.database import build_alembic_config
from backend.app.models.base import Base
from backend.app.models.competition_wallet_ledger import CompetitionWalletLedger
from backend.app.schemas.competition_core import CompetitionCreateRequest
from backend.app.services.competition_creation_service import CompetitionCreationService


def _league_request() -> CompetitionCreateRequest:
    return CompetitionCreateRequest.model_validate(
        {
            "core": {
                "host_user_id": "host-1",
                "name": "Saturday Skill League",
                "description": "Community-hosted skill contest.",
                "format": "league",
                "visibility": "public",
                "start_mode": "scheduled",
                "scheduled_start_at": datetime(2026, 4, 1, 18, 0, tzinfo=timezone.utc),
                "status": "draft",
            },
            "rules": {
                "format": "league",
                "league_rules": {
                    "win_points": 3,
                    "draw_points": 1,
                    "loss_points": 0,
                    "tie_break_order": ["points", "goal_diff", "goals_for"],
                    "home_away": True,
                    "min_participants": 4,
                    "max_participants": 8,
                },
            },
            "financials": {
                "entry_fee_minor": 1000,
                "currency": "USD",
                "platform_fee_bps": 1000,
                "host_creation_fee_minor": 500,
                "payout_mode": "winner_take_all",
            },
        }
    )


def test_alembic_upgrade_creates_user_created_competition_tables(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'user_competitions.db').as_posix()}"
    command.upgrade(build_alembic_config(database_url), "head")

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    try:
        inspector = inspect(engine)
        assert {
            "user_competitions",
            "competition_rule_sets",
            "competition_prize_rules",
            "competition_participants",
            "competition_invites",
            "competition_wallet_ledger",
        }.issubset(set(inspector.get_table_names()))
    finally:
        engine.dispose()


def test_creation_service_builds_linked_competition_aggregate() -> None:
    result = CompetitionCreationService().build_competition(_league_request())

    assert result.competition.id
    assert result.rule_set.competition_id == result.competition.id
    assert result.prize_rule.competition_id == result.competition.id
    assert [entry.competition_id for entry in result.ledger_entries] == [result.competition.id, result.competition.id]
    assert result.competition.gross_pool_minor == 8_000
    assert result.competition.net_prize_pool_minor == 6_700
    assert result.prize_rule.payout_percentages == [100]
    assert result.rule_set.league_tie_break_order == ["points", "goal_diff", "goals_for"]
    assert [entry.entry_type for entry in result.ledger_entries] == [
        "host_creation_fee",
        "platform_fee_projection",
    ]


def test_competition_wallet_ledger_is_append_only() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine, tables=[CompetitionWalletLedger.__table__])
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    try:
        with SessionLocal() as session:
            entry = CompetitionWalletLedger(
                competition_id="competition-1",
                entry_type="entry_fee_escrow",
                amount_minor=1000,
                currency="USD",
                reference_id="host-1",
                payload_json={"status": "held"},
            )
            session.add(entry)
            session.commit()

            entry.payload_json = {"status": "tampered"}
            with pytest.raises(ValueError, match="append-only"):
                session.commit()
            session.rollback()

            persisted = session.get(CompetitionWalletLedger, entry.id)
            assert persisted is not None
            session.delete(persisted)
            with pytest.raises(ValueError, match="append-only"):
                session.commit()
    finally:
        engine.dispose()
