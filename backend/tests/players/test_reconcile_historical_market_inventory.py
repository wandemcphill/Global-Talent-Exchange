from __future__ import annotations

import json
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.models.base import Base
from app.models.player_token_market import PlayerShareEvent, PlayerShareHolding, PlayerShareMarket
from app.models.user import User, UserRole
from scripts.reconcile_historical_market_inventory import (
    audit_market_inventory,
    generate_csv_report,
)


def _user(session, user_id: str) -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.USER,
    )
    session.add(user)
    session.flush()
    return user


def test_reconciliation_script_identifies_conflicts_and_generates_reports() -> None:
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with Session() as session:
        user1 = _user(session, "user-001")
        user2 = _user(session, "user-002")

        # 1. Real player with a holding > 1 (held 5 units)
        real_player = Player(
            id="real-player-001",
            source_provider="test",
            provider_external_id="real-001",
            full_name="Bukayo Saka",
            canonical_display_name="Bukayo Saka",
            is_real_player=True,
            is_tradable=True,
        )
        session.add(real_player)
        market_real = PlayerShareMarket(
            id="market-real-001",
            player_id=real_player.id,
            total_shares=600,
            circulating_shares=5,
            share_price_coin=Decimal("10.0000"),
        )
        session.add(market_real)
        holding_real = PlayerShareHolding(
            id="holding-real-001",
            user_id=user1.id,
            player_id=real_player.id,
            share_count=5,  # > 1 under whole-player rule
            average_cost_coin=Decimal("10.0000"),
        )
        session.add(holding_real)
        session.add(
            PlayerShareEvent(
                id="event-real-001",
                player_id=real_player.id,
                user_id=user1.id,
                event_type="buy",
                share_delta=5,
                price_per_share_coin=Decimal("10.0000"),
                gross_amount_coin=Decimal("50.0000"),
            )
        )

        # 2. Legendary 1-of-1 player with multi-holder conflict (2 holders)
        legend_player = Player(
            id="legend-player-001",
            source_provider="gtex_legend",
            provider_external_id="legend-001",
            full_name="Jay Jay Okocha",
            canonical_display_name="Jay Jay Okocha",
            is_real_player=False,
            is_tradable=True,
        )
        session.add(legend_player)
        market_legend = PlayerShareMarket(
            id="market-legend-001",
            player_id=legend_player.id,
            total_shares=1,
            circulating_shares=2,  # Conflict: 2 circulating for 1-of-1
            share_price_coin=Decimal("100.0000"),
        )
        session.add(market_legend)
        holding_legend_1 = PlayerShareHolding(
            id="holding-legend-001",
            user_id=user1.id,
            player_id=legend_player.id,
            share_count=1,
            average_cost_coin=Decimal("100.0000"),
        )
        holding_legend_2 = PlayerShareHolding(
            id="holding-legend-002",
            user_id=user2.id,
            player_id=legend_player.id,
            share_count=1,
            average_cost_coin=Decimal("100.0000"),
        )
        session.add(holding_legend_1)
        session.add(holding_legend_2)
        session.add(
            PlayerShareEvent(
                id="event-legend-001",
                player_id=legend_player.id,
                user_id=user1.id,
                event_type="buy",
                share_delta=1,
                price_per_share_coin=Decimal("100.0000"),
                gross_amount_coin=Decimal("100.0000"),
            )
        )
        session.add(
            PlayerShareEvent(
                id="event-legend-002",
                player_id=legend_player.id,
                user_id=user2.id,
                event_type="buy",
                share_delta=1,
                price_per_share_coin=Decimal("100.0000"),
                gross_amount_coin=Decimal("100.0000"),
            )
        )

        # 3. Duplicate player identity: two records with the same name
        dup_player = Player(
            id="real-player-002",
            source_provider="manual",
            provider_external_id="dup-002",
            full_name="Bukayo Saka",  # Duplicate of real_player
            canonical_display_name="Bukayo Saka",
            is_real_player=True,
            is_tradable=True,
        )
        session.add(dup_player)
        session.commit()

        # Run audit
        report = audit_market_inventory(session, dry_run=True)

        assert report.dry_run is True
        assert report.total_markets == 2
        assert report.total_holdings == 3
        assert report.total_holders == 2
        assert report.current_total_circulating == 7  # 5 real + 2 legend
        # Proposed compliant: 1 for user1 on real player + 1 max for 1-of-1 legend = 2
        assert report.proposed_compliant_circulating == 2
        assert report.excess_circulating_units == 5

        # Check identified holding > 1
        assert report.holdings_greater_than_one_count == 1
        assert report.holdings_greater_than_one[0].holding_id == "holding-real-001"
        assert report.holdings_greater_than_one[0].share_count == 5

        # Check identified 1-of-1 conflict
        assert report.one_of_one_conflicts_count == 1
        assert report.one_of_one_conflicts[0].player_id == legend_player.id
        assert report.one_of_one_conflicts[0].holder_count == 2
        assert report.one_of_one_conflicts[0].circulating_shares == 2

        # Check duplicate identity conflict
        assert report.duplicate_identity_groups_count == 1
        assert report.duplicate_identity_conflicts[0].canonical_normalized_name == "bukayo saka"
        assert set(report.duplicate_identity_conflicts[0].player_ids) == {real_player.id, dup_player.id}

        # Check report serialization
        json_dict = report.to_dict()
        assert isinstance(json_dict, dict)
        csv_text = generate_csv_report(report)
        assert "GTEX HISTORICAL MARKET INVENTORY RECONCILIATION REPORT" in csv_text
        assert "HOLDINGS GREATER THAN ONE" in csv_text
        assert "ONE-OF-ONE MARKET CONFLICTS" in csv_text
        assert "DUPLICATE IDENTITY CONFLICTS" in csv_text
