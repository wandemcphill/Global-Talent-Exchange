from __future__ import annotations

from decimal import Decimal

from app.common.enums.qualification_status import QualificationStatus as SharedQualificationStatus
from app.champions_league.models.domain import QualificationStatus
from app.champions_league.services.tournament import ChampionsLeagueService, LeaguePhaseTableService


def test_48_to_36_pathway(build_candidates) -> None:
    service = ChampionsLeagueService()

    qualification = service.build_qualification_map(build_candidates())
    playoff = service.build_playoff_bracket(build_candidates())

    assert len(qualification.direct_qualifiers) == 24
    assert len(qualification.playoff_qualifiers) == 24
    assert len([entry for entry in qualification.entries if entry.status is QualificationStatus.ELIMINATED]) == 12
    assert len(playoff.ties) == 12
    assert len(playoff.advancing_clubs) == 36
    assert len({club.club_id for club in playoff.advancing_clubs}) == 36


def test_standings_tie_breakers_prioritize_goal_difference_then_goals_for(build_league_clubs) -> None:
    seeded_clubs = build_league_clubs(4)
    table = LeaguePhaseTableService().build_table(
        clubs=seeded_clubs,
        matches=[
            _match("m1", seeded_clubs[0].club_id, seeded_clubs[3].club_id, 2, 0),
            _match("m2", seeded_clubs[1].club_id, seeded_clubs[2].club_id, 3, 1),
            _match("m3", seeded_clubs[0].club_id, seeded_clubs[1].club_id, 1, 1),
            _match("m4", seeded_clubs[2].club_id, seeded_clubs[3].club_id, 0, 0),
            _match("m5", seeded_clubs[0].club_id, seeded_clubs[2].club_id, 0, 0),
            _match("m6", seeded_clubs[1].club_id, seeded_clubs[3].club_id, 0, 0),
        ],
    )

    assert [row.club_id for row in table.rows[:2]] == [seeded_clubs[1].club_id, seeded_clubs[0].club_id]
    assert table.rows[0].points == table.rows[1].points
    assert table.rows[0].goal_difference == table.rows[1].goal_difference
    assert table.rows[0].goals_for > table.rows[1].goals_for


def test_ranks_9_through_24_enter_knockout_playoff(build_standings_rows) -> None:
    service = ChampionsLeagueService()

    bracket = service.build_knockout_bracket(build_standings_rows())

    assert len(bracket.knockout_playoff) == 8
    assert bracket.knockout_playoff[0].home_club.seed == 9
    assert bracket.knockout_playoff[0].away_club.seed == 24
    assert bracket.knockout_playoff[-1].home_club.seed == 16
    assert bracket.knockout_playoff[-1].away_club.seed == 17
    assert bracket.champion.seed == 1


def test_champion_settlement_preview_uses_append_only_event_hooks() -> None:
    preview = ChampionsLeagueService().build_prize_pool_preview(
        season_id="ucl-2026",
        league_leftover_allocation=Decimal("1000"),
        champion_club_id="club-01",
        champion_club_name="Club 01",
        currency="credit",
    )

    assert preview.funded_pool == Decimal("350.0000")
    assert preview.champion_share == Decimal("245.0000")
    assert preview.platform_share == Decimal("105.0000")
    assert [event.event_type for event in preview.events] == [
        "champions_league.prize_pool_funded",
        "champions_league.champion_awarded",
        "champions_league.platform_awarded",
    ]


def test_match_fees_pay_results_without_changing_the_champion_share() -> None:
    service = ChampionsLeagueService()
    preview = service.build_prize_pool_preview(
        season_id="ucl-2026",
        league_leftover_allocation=Decimal("1000"),
        champion_club_id="club-01",
        champion_club_name="Club 01",
    )
    plans = service.plan_match_fees(
        season_id="ucl-2026",
        matches=[_match("m1", "club-01", "club-02", 2, 0)],
        stage_reached={"club-01": "champion"},
    )

    assert preview.champion_share == Decimal("245.0000")
    assert [event.event_type for event in preview.events] == [
        "champions_league.prize_pool_funded",
        "champions_league.champion_awarded",
        "champions_league.platform_awarded",
    ]
    by_club = {plan.payload["club_id"]: plan.amount for plan in plans}
    assert by_club["club-01"] == Decimal("3370.0000")
    assert by_club["club-02"] == Decimal("280.0000")
    assert all(plan.event_type == "champions_league.match_fee" for plan in plans)


def test_match_fee_settlement_credits_each_owner_once() -> None:
    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.admin_engine.schemas import AdminRewardRuleStabilityControls
    from app.auth.service import AuthService
    from app.models import AdminRewardRule, Base, RewardSettlement
    from app.reward_engine.service import RewardEngineService

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as session:
        admin = AuthService().register_user(
            session,
            email="cl-admin@example.com",
            username="cl-admin",
            password="SuperSecret1",  # pragma: allowlist secret
        )
        winner = AuthService().register_user(
            session,
            email="cl-winner@example.com",
            username="cl-winner",
            password="SuperSecret1",  # pragma: allowlist secret
        )
        loser = AuthService().register_user(
            session,
            email="cl-loser@example.com",
            username="cl-loser",
            password="SuperSecret1",  # pragma: allowlist secret
        )
        session.add(
            AdminRewardRule(
                rule_key="cl-match-fees",
                title="Champions League match fees",
                description="Pay match coin from the promo pool.",
                trading_fee_bps=0,
                gift_platform_rake_bps=0,
                withdrawal_fee_bps=0,
                minimum_withdrawal_fee_credits=Decimal("0.0000"),
                competition_platform_fee_bps=1000,
                stability_controls_json=AdminRewardRuleStabilityControls(
                    reward={
                        "max_amount": "10000.0000",
                        "daily_user_limit": "10000.0000",
                        "daily_user_count_limit": 20,
                        "burst_window_seconds": 3600,
                        "burst_max_count": 20,
                        "duplicate_window_seconds": 60,
                        "review_threshold_bps": 10000,
                    }
                ).model_dump(mode="json"),
                active=True,
            )
        )
        session.commit()
        RewardEngineService(session).credit_promo_pool(actor=admin, amount=Decimal("5000.0000"))
        session.commit()
        service = ChampionsLeagueService()
        kwargs = {
            "season_id": "ucl-fees",
            "matches": [_match("m1", "club-01", "club-02", 1, 0)],
            "club_user_ids": {"club-01": winner.id, "club-02": loser.id},
        }
        first = service.settle_match_fees(session=session, actor=admin, **kwargs)
        session.commit()
        second = service.settle_match_fees(session=session, actor=admin, **kwargs)
        session.commit()

        assert {item.user_id for item in first} == {winner.id, loser.id}
        assert {item.id for item in second} == {item.id for item in first}
        assert session.scalar(select(func.count()).select_from(RewardSettlement)) == 4


def test_record_match_and_pay_settles_once_per_match() -> None:
    from sqlalchemy import func, select

    from app.models import RewardSettlement
    from app.models.wallet import LedgerUnit
    from app.wallets.service import WalletService

    service = ChampionsLeagueService()
    season_id = "ucl-pay-once"
    winner_match = _match("m-pay", "club-01", "club-02", 2, 0)
    with _match_fee_session() as (session, admin, winner, loser):
        club_user_ids = {"club-01": winner.id, "club-02": loser.id}
        service.record_match_and_pay(
            session=session,
            actor=admin,
            season_id=season_id,
            match=winner_match,
            club_user_ids=club_user_ids,
        )
        session.commit()

        rows = list(session.scalars(select(RewardSettlement)))
        assert len(rows) == 4
        match_rows = [row for row in rows if ":m-pay:" in row.competition_key]
        qualification_rows = [row for row in rows if ":qual:" in row.competition_key]
        assert len(match_rows) == 2
        assert len(qualification_rows) == 2
        assert all(row.note and "qualification=0" in row.note for row in match_rows)
        assert all(row.note and "qualification=1" in row.note for row in qualification_rows)

        wallet = WalletService()
        winner_balance = wallet.get_balance(session, wallet.get_user_account(session, winner, LedgerUnit.COIN))
        loser_balance = wallet.get_balance(session, wallet.get_user_account(session, loser, LedgerUnit.COIN))
        service.record_match_and_pay(
            session=session,
            actor=admin,
            season_id=season_id,
            match=winner_match,
            club_user_ids=club_user_ids,
        )
        session.commit()

        assert session.scalar(select(func.count()).select_from(RewardSettlement)) == 4
        assert wallet.get_balance(session, wallet.get_user_account(session, winner, LedgerUnit.COIN)) == winner_balance
        assert wallet.get_balance(session, wallet.get_user_account(session, loser, LedgerUnit.COIN)) == loser_balance

        ChampionsLeagueService().record_match_and_pay(
            session=session,
            actor=admin,
            season_id=season_id,
            match=winner_match,
            club_user_ids=club_user_ids,
        )
        session.commit()
        assert session.scalar(select(func.count()).select_from(RewardSettlement)) == 4

        preview = service.build_prize_pool_preview(
            season_id="ucl-2026",
            league_leftover_allocation=Decimal("1000"),
            champion_club_id="club-01",
            champion_club_name="Club 01",
        )
        assert preview.funded_pool == Decimal("350.0000")
        assert preview.champion_share == Decimal("245.0000")
        assert preview.platform_share == Decimal("105.0000")
        assert [event.event_type for event in preview.events] == [
            "champions_league.prize_pool_funded",
            "champions_league.champion_awarded",
            "champions_league.platform_awarded",
        ]

        service.record_match_and_pay(
            session=session,
            actor=admin,
            season_id=season_id,
            match=_match("m-pay-2", "club-01", "club-02", 1, 1),
            club_user_ids=club_user_ids,
        )
        session.commit()
        paid = list(session.scalars(select(RewardSettlement)))
        assert len(paid) == 6
        second_match = [row for row in paid if ":m-pay-2:" in row.competition_key]
        qualification_rows = [row for row in paid if ":qual:" in row.competition_key]
        assert len(second_match) == 2
        assert len(qualification_rows) == 2
        assert all(row.note and "qualification=0" in row.note for row in second_match)
        assert all(row.gross_amount > 0 for row in second_match)

        service.record_match_and_pay(
            session=session,
            actor=admin,
            season_id=season_id,
            match=_match("m-pay-2", "club-01", "club-02", 1, 1),
            club_user_ids=club_user_ids,
        )
        session.commit()
        assert session.scalar(select(func.count()).select_from(RewardSettlement)) == 6


def test_deepest_stage_bonus_tops_up_once() -> None:
    from sqlalchemy import func, select

    from app.models import RewardSettlement

    service = ChampionsLeagueService()
    season_id = "ucl-stage-once"
    match = _match("m-stage", "club-01", "club-02", 1, 0)
    with _match_fee_session() as (session, admin, winner, loser):
        club_user_ids = {"club-01": winner.id, "club-02": loser.id}
        service.record_match_and_pay(
            session=session,
            actor=admin,
            season_id=season_id,
            match=match,
            club_user_ids=club_user_ids,
            stage_reached={"club-01": "round_of_16"},
        )
        session.commit()
        assert session.scalar(select(func.count()).select_from(RewardSettlement)) == 5
        assert _stage_amounts(session, club_id="club-01") == {"round_of_16": Decimal("350.0000")}

        service.record_match_and_pay(
            session=session,
            actor=admin,
            season_id=season_id,
            match=match,
            club_user_ids=club_user_ids,
            stage_reached={"club-01": "champion"},
        )
        session.commit()
        assert session.scalar(select(func.count()).select_from(RewardSettlement)) == 6
        stage_amounts = _stage_amounts(session, club_id="club-01")
        assert stage_amounts["round_of_16"] == Decimal("350.0000")
        assert stage_amounts["champion"] == Decimal("2650.0000")
        assert sum(stage_amounts.values(), Decimal("0")) == Decimal("3000.0000")

        preview = service.build_prize_pool_preview(
            season_id="ucl-2026",
            league_leftover_allocation=Decimal("1000"),
            champion_club_id="club-01",
            champion_club_name="Club 01",
        )
        assert preview.champion_share == Decimal("245.0000")
        assert [event.event_type for event in preview.events] == [
            "champions_league.prize_pool_funded",
            "champions_league.champion_awarded",
            "champions_league.platform_awarded",
        ]

        service.record_match_and_pay(
            session=session,
            actor=admin,
            season_id=season_id,
            match=match,
            club_user_ids=club_user_ids,
            stage_reached={"club-01": "quarterfinal"},
        )
        session.commit()
        assert session.scalar(select(func.count()).select_from(RewardSettlement)) == 6
        assert "quarterfinal" not in _stage_amounts(session, club_id="club-01")
        assert sum(_stage_amounts(session, club_id="club-01").values(), Decimal("0")) == Decimal("3000.0000")


def test_unpaid_match_stays_owed_until_the_promo_pool_can_pay() -> None:
    from sqlalchemy import func, select

    from app.models import RewardSettlement
    from app.models.champions_league_played_match import ChampionsLeaguePlayedMatch
    from app.reward_engine.service import RewardEngineError, RewardEngineService

    service = ChampionsLeagueService()
    season_id = "ucl-owed"
    match = _match("m-owed", "club-01", "club-02", 1, 0)
    with _match_fee_session(Decimal("0")) as (session, admin, winner, loser):
        club_user_ids = {"club-01": winner.id, "club-02": loser.id}
        try:
            service.record_match_and_pay(
                session=session,
                actor=admin,
                season_id=season_id,
                match=match,
                club_user_ids=club_user_ids,
            )
        except RewardEngineError as exc:
            assert exc.reason == "promo_pool_insufficient"
        else:
            raise AssertionError("Match coin was paid from an empty promo pool.")
        session.rollback()
        stored = session.scalar(
            select(ChampionsLeaguePlayedMatch).where(ChampionsLeaguePlayedMatch.match_id == "m-owed")
        )
        assert stored is None

        service.remember_played_match(
            session=session,
            season_id=season_id,
            match=match,
            club_user_ids=club_user_ids,
        )
        session.commit()
        try:
            service.record_match_and_pay(
                session=session,
                actor=admin,
                season_id=season_id,
                match=match,
                club_user_ids=club_user_ids,
            )
        except RewardEngineError as exc:
            assert exc.reason == "promo_pool_insufficient"
        else:
            raise AssertionError("A stored result paid from an empty promo pool.")
        session.rollback()
        stored = session.scalar(
            select(ChampionsLeaguePlayedMatch).where(ChampionsLeaguePlayedMatch.match_id == "m-owed")
        )
        assert stored is not None
        assert stored.fee_status == "owed"
        assert session.scalar(select(RewardSettlement).limit(1)) is None

        RewardEngineService(session).credit_promo_pool(actor=admin, amount=Decimal("5000.0000"))
        session.commit()
        service.record_match_and_pay(
            session=session,
            actor=admin,
            season_id=season_id,
            match=match,
            club_user_ids=club_user_ids,
        )
        session.commit()
        stored = session.scalar(
            select(ChampionsLeaguePlayedMatch).where(ChampionsLeaguePlayedMatch.match_id == "m-owed")
        )
        assert stored.fee_status == "settled"
        assert session.scalar(select(func.count()).select_from(RewardSettlement)) == 4


def test_qualification_color_and_status_mapping(build_candidates) -> None:
    qualification = ChampionsLeagueService().build_qualification_map(build_candidates())

    assert qualification.direct_qualifiers[0].status is QualificationStatus.DIRECT
    assert qualification.direct_qualifiers[0].display_color == "emerald"
    assert qualification.playoff_qualifiers[0].status is QualificationStatus.PLAYOFF
    assert qualification.playoff_qualifiers[0].display_color == "amber"
    assert qualification.entries[-1].status is QualificationStatus.ELIMINATED
    assert qualification.entries[-1].display_color == "slate"


def test_champions_league_reuses_shared_qualification_status_enum() -> None:
    assert QualificationStatus is SharedQualificationStatus


def _stage_amounts(session, *, club_id: str) -> dict[str, Decimal]:
    from sqlalchemy import select

    from app.models import RewardSettlement

    amounts: dict[str, Decimal] = {}
    prefix = "kind=stage;season="
    for note in session.scalars(select(RewardSettlement.note)):
        if not note or not note.startswith(prefix) or f";club={club_id};" not in note:
            continue
        stage = note.split("stage=", 1)[1].split(";", 1)[0]
        amount = Decimal(note.split("amount=", 1)[1].split(";", 1)[0])
        amounts[stage] = amount
    return amounts


def _match_fee_session(promo_amount: Decimal = Decimal("5000.0000")):
    from contextlib import contextmanager

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.admin_engine.schemas import AdminRewardRuleStabilityControls
    from app.auth.service import AuthService
    from app.models import AdminRewardRule, Base
    from app.reward_engine.service import RewardEngineService

    @contextmanager
    def _open():
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        with SessionLocal() as session:
            admin = AuthService().register_user(
                session,
                email="cl-pay-admin@example.com",
                username="cl-pay-admin",
                password="SuperSecret1",  # pragma: allowlist secret
            )
            winner = AuthService().register_user(
                session,
                email="cl-pay-winner@example.com",
                username="cl-pay-winner",
                password="SuperSecret1",  # pragma: allowlist secret
            )
            loser = AuthService().register_user(
                session,
                email="cl-pay-loser@example.com",
                username="cl-pay-loser",
                password="SuperSecret1",  # pragma: allowlist secret
            )
            session.add(
                AdminRewardRule(
                    rule_key="cl-match-fees-pay",
                    title="Champions League match fees",
                    description="Pay match coin from the promo pool.",
                    trading_fee_bps=0,
                    gift_platform_rake_bps=0,
                    withdrawal_fee_bps=0,
                    minimum_withdrawal_fee_credits=Decimal("0.0000"),
                    competition_platform_fee_bps=1000,
                    stability_controls_json=AdminRewardRuleStabilityControls(
                        reward={
                            "max_amount": "10000.0000",
                            "daily_user_limit": "10000.0000",
                            "daily_user_count_limit": 20,
                            "burst_window_seconds": 3600,
                            "burst_max_count": 20,
                            "duplicate_window_seconds": 60,
                            "review_threshold_bps": 10000,
                        }
                    ).model_dump(mode="json"),
                    active=True,
                )
            )
            session.commit()
            if promo_amount > 0:
                RewardEngineService(session).credit_promo_pool(actor=admin, amount=promo_amount)
                session.commit()
            yield session, admin, winner, loser

    return _open()


def _match(match_id: str, home_club_id: str, away_club_id: str, home_goals: int, away_goals: int):
    from app.champions_league.models.domain import LeagueMatchResult

    return LeagueMatchResult(
        match_id=match_id,
        home_club_id=home_club_id,
        away_club_id=away_club_id,
        home_goals=home_goals,
        away_goals=away_goals,
    )
