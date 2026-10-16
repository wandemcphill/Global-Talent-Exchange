from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.competition_engine.queue_contracts import MatchSimulationJob
from app.fairness.fairness_guard import FairnessGuard, FairnessViolation
from app.fairness.match_integrity_service import MatchIntegrityService, MatchIntegrityViolation
from app.fairness.spend_balance_controller import SpendBalanceController, SpendTier
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models import Base, GiftCatalogItem, GiftTransaction, LedgerUnit
from app.models.base import utcnow
from app.models.media_engine import PremiumVideoPurchase
from app.services.match_timeline_service import MatchTimelineService
from backend.tests.match_engine.helpers import build_request


def _build_job() -> MatchSimulationJob:
    return MatchSimulationJob(
        fixture_id="fairness-match",
        competition_id="competition-1",
        competition_type=CompetitionType.LEAGUE,
        match_date=date(2026, 3, 24),
        window=FixtureWindow.SENIOR_1,
        home_club_id="club-home",
        away_club_id="club-away",
        home_club_name="Home Club",
        away_club_name="Away Club",
    )


def test_fairness_guard_rejects_monetization_injection() -> None:
    request = build_request(seed=12)
    home_team = request.home_team.model_copy(
        update={
            "tactics": request.home_team.tactics.model_copy(
                update={"player_instructions": {"premium_camera_boost": True}}
            )
        }
    )
    injected_request = request.model_copy(update={"home_team": home_team})

    with pytest.raises(FairnessViolation, match="Monetization cannot affect match logic"):
        FairnessGuard().validate_public_request(injected_request)


def test_locked_inputs_ignore_client_seed_and_produce_identical_results() -> None:
    base_request = build_request(seed=12)
    alternate_seed_request = build_request(seed=99)

    locked_a = FairnessGuard().lock_official_request(base_request)
    locked_b = FairnessGuard().lock_official_request(alternate_seed_request)

    assert locked_a.match_hash == locked_b.match_hash
    assert locked_a.match_seed == locked_b.match_seed

    service = MatchSimulationService()
    replay_a = service.build_replay_payload(locked_a.request)
    replay_b = service.build_replay_payload(locked_b.request)

    assert replay_a.seed == replay_b.seed
    assert replay_a.summary.home_score == replay_b.summary.home_score
    assert replay_a.summary.away_score == replay_b.summary.away_score
    assert [event.event_type for event in replay_a.timeline.events] == [
        event.event_type for event in replay_b.timeline.events
    ]


def test_spend_balance_controller_blocks_squads_over_the_s_plus_cap() -> None:
    request = build_request(seed=13)
    boosted_starters = [
        player.model_copy(update={"overall": 92}) if index < 6 else player
        for index, player in enumerate(request.home_team.starters)
    ]
    boosted_home = request.home_team.model_copy(update={"starters": boosted_starters})
    boosted_request = request.model_copy(update={"home_team": boosted_home})

    with pytest.raises(FairnessViolation, match="S\\+ player cap"):
        SpendBalanceController().apply_balance_controls(
            request=boosted_request,
            job=_build_job(),
            match_seed=101,
            competition_metadata_json={},
        )


def test_match_integrity_service_rejects_tampered_timeline_payloads() -> None:
    request = build_request(seed=14)
    locked = FairnessGuard().lock_official_request(request)
    replay_payload = MatchSimulationService().build_replay_payload(locked.request)
    view_state = MatchTimelineService().build_from_replay_payload(replay_payload)
    integrity = MatchIntegrityService()
    fairness = integrity.build_fairness_envelope(
        locked_context=locked,
        view_state=view_state,
        balance_metadata={},
        competition_metadata_json={},
    )
    tampered_view = view_state.model_copy(update={"events": view_state.events[:-1]})

    with pytest.raises(MatchIntegrityViolation, match="timeline proof"):
        integrity.validate_view_state(view_state=tampered_view, fairness_metadata=fairness)


def test_match_integrity_service_builds_32_bit_visible_hashes() -> None:
    request = build_request(seed=15)
    locked = FairnessGuard().lock_official_request(request)
    replay_payload = MatchSimulationService().build_replay_payload(locked.request)
    view_state = MatchTimelineService().build_from_replay_payload(replay_payload)
    integrity = MatchIntegrityService()

    fairness = integrity.build_fairness_envelope(
        locked_context=locked,
        view_state=view_state,
        balance_metadata={},
        competition_metadata_json={},
    )

    visible_hash = fairness["visible_timeline_hash"]
    assert visible_hash == integrity._visible_hash_view_state(view_state)
    assert len(visible_hash) == 8
    assert all(char in "0123456789abcdef" for char in visible_hash)


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def _create_user(session, *, email: str, username: str):
    user = AuthService().register_user(session, email=email, username=username, password="SuperSecret1")
    session.commit()
    return user


def _seed_gift_catalog(session, *, key: str = "spend-tier-gift") -> GiftCatalogItem:
    gift = GiftCatalogItem(key=key, display_name="Spend Tier Gift", fancoin_price=Decimal("100.0000"), active=True)
    session.add(gift)
    session.commit()
    return gift


def _add_gift_transaction(
    session,
    *,
    sender,
    recipient,
    gift: GiftCatalogItem,
    gross_amount: Decimal,
    source_ledger_unit: LedgerUnit,
    destination_ledger_unit: LedgerUnit = LedgerUnit.COIN,
) -> None:
    session.add(
        GiftTransaction(
            sender_user_id=sender.id,
            recipient_user_id=recipient.id,
            gift_catalog_item_id=gift.id,
            quantity=Decimal("1.0000"),
            unit_price=gross_amount,
            gross_amount=gross_amount,
            platform_rake_amount=Decimal("0.0000"),
            recipient_net_amount=gross_amount,
            # `ledger_unit` is the deprecated compatibility field: it always records
            # the destination unit for a canonical (converted) gift, regardless of
            # what the sender actually spent. Classification must key off
            # `source_ledger_unit` instead, or every Fan-Coin-funded gift gets
            # misclassified as GTEX Coin spend.
            ledger_unit=destination_ledger_unit,
            source_ledger_unit=source_ledger_unit,
            destination_ledger_unit=destination_ledger_unit,
        )
    )
    session.commit()


def _add_premium_video_purchase(session, *, user, price_coin: Decimal, match_key: str) -> None:
    session.add(
        PremiumVideoPurchase(
            user_id=user.id,
            match_key=match_key,
            price_coin=price_coin,
        )
    )
    session.commit()


def test_spend_classifier_excludes_fan_coin_funded_gifts_from_coin_spend() -> None:
    session = _make_session()
    try:
        sender = _create_user(session, email="fancoin-spender@example.com", username="fancoin-spender")
        recipient = _create_user(session, email="fancoin-recipient@example.com", username="fancoin-recipient")
        gift = _seed_gift_catalog(session)

        # Every live gift is funded in Fan Coin (CREDIT) even though the deprecated
        # `ledger_unit` field records the post-conversion GTEX Coin destination unit.
        _add_gift_transaction(
            session,
            sender=sender,
            recipient=recipient,
            gift=gift,
            gross_amount=Decimal("2000.0000"),
            source_ledger_unit=LedgerUnit.CREDIT,
            destination_ledger_unit=LedgerUnit.COIN,
        )

        profile = SpendBalanceController(session=session)._classify_user(sender.id)

        assert profile.compatible_total_coin == Decimal("0.0000")
        assert profile.tier == SpendTier.CASUAL
        assert profile.excluded_sources == ("gift_transactions_incompatible_unit",)
    finally:
        session.close()


def test_spend_classifier_counts_real_gtex_coin_spend() -> None:
    session = _make_session()
    try:
        user = _create_user(session, email="coin-spender@example.com", username="coin-spender")
        _add_premium_video_purchase(session, user=user, price_coin=Decimal("1800.0000"), match_key="match-1")

        profile = SpendBalanceController(session=session)._classify_user(user.id)

        assert profile.compatible_total_coin == Decimal("1800.0000")
        assert profile.tier == SpendTier.WHALE
    finally:
        session.close()


def test_spend_classifier_counts_a_gift_actually_funded_in_gtex_coin() -> None:
    session = _make_session()
    try:
        sender = _create_user(session, email="coin-gifter@example.com", username="coin-gifter")
        recipient = _create_user(session, email="coin-gift-recipient@example.com", username="coin-gift-recipient")
        gift = _seed_gift_catalog(session, key="coin-funded-gift")

        _add_gift_transaction(
            session,
            sender=sender,
            recipient=recipient,
            gift=gift,
            gross_amount=Decimal("300.0000"),
            source_ledger_unit=LedgerUnit.COIN,
            destination_ledger_unit=LedgerUnit.COIN,
        )

        profile = SpendBalanceController(session=session)._classify_user(sender.id)

        assert profile.compatible_total_coin == Decimal("300.0000")
        assert profile.tier == SpendTier.COMPETITIVE
    finally:
        session.close()


def test_spend_classifier_ignores_gifts_outside_the_lookback_window() -> None:
    session = _make_session()
    try:
        user = _create_user(session, email="stale-spender@example.com", username="stale-spender")
        _add_premium_video_purchase(session, user=user, price_coin=Decimal("5000.0000"), match_key="match-old")
        session.query(PremiumVideoPurchase).filter_by(user_id=user.id).update(
            {"created_at": utcnow() - timedelta(days=45)}
        )
        session.commit()

        profile = SpendBalanceController(session=session)._classify_user(user.id)

        assert profile.compatible_total_coin == Decimal("0.0000")
        assert profile.tier == SpendTier.CASUAL
    finally:
        session.close()


def test_spend_classifier_defaults_to_casual_with_no_session() -> None:
    profile = SpendBalanceController(session=None)._classify_user("some-user")

    assert profile.tier == SpendTier.CASUAL
    assert profile.compatible_total_coin == Decimal("0.0000")
