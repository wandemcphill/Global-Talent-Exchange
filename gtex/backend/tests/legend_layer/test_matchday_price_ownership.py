"""Matchday form must not own tradable price or the valuation input.

GTEX has one canonical contract between football and money:
``app.value_engine.matchday_signal``. Its own docstring states the terms --
bounded, gradual, deterministic, auditable, and *secondary*: "an overlay applied
on top of the existing valuation, which remains the primary source of truth. It
adjusts; it does not replace." It is applied by ``ValueSnapshotJob`` to a
``ValueSnapshot``, and it is wired into production in
``value_engine/service.py`` via ``MatchdayValuationSignalProvider``.

``legend_layer`` predates that contract (2026-03-29 versus 2026-09-02) and grew
its own second matchday pricing path, which bypassed every one of those terms:

* it wrote ``PlayerShareMarket.share_price_coin`` -- the tradable price, whose
  writers are otherwise only trading, issuance and governed admin repricing;
* it wrote ``Player.market_value_eur``, which is the value engine's *input*, so
  a single match moved the baseline the bounded overlay is computed from -- that
  is how an 18% swing escaped a 2.4% bound;
* it derived from one match rather than a rolling window, so nothing enforced
  the minimum sample the signal's confidence depends on;
* it fabricated a market value out of a rating when the player had none.

These tests pin the ownership boundary. They do not assert that matchday has no
economic consequence -- it does, through the value engine -- only that it does
not reach around it.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.legend_layer.service import LegendLayerService
from app.models.base import Base
from app.models.player_token_market import PlayerShareEvent, PlayerShareMarket


def _build_session() -> tuple[object, Session]:
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, session_factory()


def _seed_player(session: Session, *, external_id: str, market_value_eur: float | None) -> Player:
    player = Player(
        source_provider="legend-ownership-test",
        provider_external_id=external_id,
        full_name="Kelechi Star",
        canonical_display_name="Kelechi Star",
        market_value_eur=market_value_eur,
        current_market_reference_value=market_value_eur,
        normalized_position="forward",
    )
    session.add(player)
    session.flush()
    return player


def _seed_market(session: Session, *, player: Player, price: str) -> PlayerShareMarket:
    market = PlayerShareMarket(
        player_id=player.id,
        total_shares=1000,
        circulating_shares=0,
        share_price_coin=Decimal(price),
        status="active",
    )
    session.add(market)
    session.flush()
    return market


#: A performance emphatic enough that the old path would certainly have repriced:
#: 9.4 against the 6.5 baseline, with a strongly positive perception delta.
STANDOUT_STAT = {"rating": 9.4, "goals": 3, "assists": 1}


class _Article:
    """Minimal stand-in for the narrative article the reaction reads."""

    id = "article-under-test"
    perception_delta = 60.0


def test_matchday_narrative_does_not_move_the_tradable_share_price() -> None:
    engine, session = _build_session()
    try:
        player = _seed_player(session, external_id="price-owner", market_value_eur=1_500_000.0)
        market = _seed_market(session, player=player, price="1.0000")
        price_before = Decimal(market.share_price_coin)

        LegendLayerService(session=session)._apply_market_reaction(
            player=player,
            article=_Article(),
            stat=STANDOUT_STAT,
        )
        session.flush()

        session.refresh(market)
        assert Decimal(market.share_price_coin) == price_before, (
            "matchday form repriced the tradable market; price is owned by trading, "
            "issuance and governed admin repricing only"
        )
    finally:
        session.close()
        engine.dispose()


def test_matchday_narrative_writes_no_share_event() -> None:
    """The event existed to audit a price change that no longer happens."""
    engine, session = _build_session()
    try:
        player = _seed_player(session, external_id="event-owner", market_value_eur=1_500_000.0)
        _seed_market(session, player=player, price="1.0000")

        LegendLayerService(session=session)._apply_market_reaction(
            player=player,
            article=_Article(),
            stat=STANDOUT_STAT,
        )
        session.flush()

        events = list(session.scalars(select(PlayerShareEvent).where(PlayerShareEvent.player_id == player.id)))
        assert events == [], f"matchday wrote share-ledger provenance: {[e.event_type for e in events]}"
    finally:
        session.close()
        engine.dispose()


def test_matchday_narrative_does_not_rewrite_the_valuation_input() -> None:
    """``market_value_eur`` is ingestion-owned and is what the value engine reads."""
    engine, session = _build_session()
    try:
        player = _seed_player(session, external_id="value-owner", market_value_eur=1_500_000.0)
        _seed_market(session, player=player, price="1.0000")

        LegendLayerService(session=session)._apply_market_reaction(
            player=player,
            article=_Article(),
            stat=STANDOUT_STAT,
        )
        session.flush()

        assert player.market_value_eur == 1_500_000.0
        assert player.current_market_reference_value == 1_500_000.0
    finally:
        session.close()
        engine.dispose()


def test_matchday_narrative_does_not_fabricate_an_absent_market_value() -> None:
    """Unknown stays unknown. A rating is not a valuation."""
    engine, session = _build_session()
    try:
        player = _seed_player(session, external_id="absent-value", market_value_eur=None)
        _seed_market(session, player=player, price="1.0000")

        LegendLayerService(session=session)._apply_market_reaction(
            player=player,
            article=_Article(),
            stat=STANDOUT_STAT,
        )
        session.flush()

        assert (
            player.market_value_eur is None
        ), f"an absent market value was invented from a rating: {player.market_value_eur}"
        assert player.current_market_reference_value is None
    finally:
        session.close()
        engine.dispose()


def test_matchday_narrative_still_annotates_the_market_with_the_story() -> None:
    """The narrative linkage is not economic state and is deliberately kept."""
    engine, session = _build_session()
    try:
        player = _seed_player(session, external_id="annotated", market_value_eur=1_500_000.0)
        market = _seed_market(session, player=player, price="1.0000")

        LegendLayerService(session=session)._apply_market_reaction(
            player=player,
            article=_Article(),
            stat=STANDOUT_STAT,
        )
        session.flush()

        session.refresh(market)
        metadata = dict(market.metadata_json or {})
        assert metadata["last_narrative_article_id"] == "article-under-test"
        assert metadata["last_narrative_rating"] == 9.4
    finally:
        session.close()
        engine.dispose()


def test_a_player_with_no_market_is_still_narrated_without_error() -> None:
    engine, session = _build_session()
    try:
        player = _seed_player(session, external_id="no-market", market_value_eur=1_500_000.0)

        LegendLayerService(session=session)._apply_market_reaction(
            player=player,
            article=_Article(),
            stat=STANDOUT_STAT,
        )
        session.flush()

        assert player.market_value_eur == 1_500_000.0
        assert session.scalar(select(PlayerShareMarket).where(PlayerShareMarket.player_id == player.id)) is None
    finally:
        session.close()
        engine.dispose()
