from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.ultimate_league.league_service import LeagueCompetitor, LeagueTier, UltimateLeagueService


def _competitor(
    competitor_id: str,
    display_name: str,
    elo_rating: int,
    *,
    wins: int = 0,
    draws: int = 0,
    losses: int = 0,
    region: str = "AF-WEST",
    queued_minutes_ago: int = 0,
) -> LeagueCompetitor:
    return LeagueCompetitor(
        competitor_id=competitor_id,
        display_name=display_name,
        elo_rating=elo_rating,
        wins=wins,
        draws=draws,
        losses=losses,
        region=region,
        queue_entered_at=datetime.now(timezone.utc) - timedelta(minutes=queued_minutes_ago),
    )


def test_tier_assignment_covers_bronze_to_legend() -> None:
    service = UltimateLeagueService()

    assert service.tier_for_rating(1199).tier == LeagueTier.BRONZE
    assert service.tier_for_rating(1200).tier == LeagueTier.SILVER
    assert service.tier_for_rating(1400).tier == LeagueTier.GOLD
    assert service.tier_for_rating(1600).tier == LeagueTier.PLATINUM
    assert service.tier_for_rating(1800).tier == LeagueTier.DIAMOND
    assert service.tier_for_rating(2000).tier == LeagueTier.MASTER
    assert service.tier_for_rating(2200).tier == LeagueTier.LEGEND


def test_build_tier_tables_orders_by_points_then_elo() -> None:
    service = UltimateLeagueService()
    bronze_a = _competitor("bronze-a", "Bronze A", 1185, wins=4, draws=1)
    bronze_b = _competitor("bronze-b", "Bronze B", 1190, wins=4, draws=1)
    silver = _competitor("silver-a", "Silver A", 1300, wins=5, losses=1)

    tables = service.build_tier_tables([bronze_a, bronze_b, silver])

    bronze_table = tables[LeagueTier.BRONZE]
    assert [row.competitor.competitor_id for row in bronze_table] == ["bronze-b", "bronze-a"]
    assert bronze_table[0].zone == "promotion"
    assert tables[LeagueTier.SILVER][0].competitor.competitor_id == "silver-a"


def test_matchmaking_prefers_closest_elo_pairings_inside_tier() -> None:
    service = UltimateLeagueService()
    players = [
        _competitor("c1", "Club 1", 1080, queued_minutes_ago=6),
        _competitor("c2", "Club 2", 1093, queued_minutes_ago=5),
        _competitor("c3", "Club 3", 1122, queued_minutes_ago=4),
        _competitor("c4", "Club 4", 1135, queued_minutes_ago=3),
    ]

    batch = service.create_matchmaking_batch(players)

    pairings = {
        tuple(sorted((proposal.home.competitor_id, proposal.away.competitor_id)))
        for proposal in batch.proposals
    }
    assert pairings == {("c1", "c2"), ("c3", "c4")}
    assert not batch.unmatched
    assert all(proposal.same_tier for proposal in batch.proposals)


def test_apply_match_result_updates_elo_and_records_wins_losses() -> None:
    service = UltimateLeagueService()
    home = _competitor("home", "Home", 1500)
    away = _competitor("away", "Away", 1650)

    updated_home, updated_away, rating_update = service.apply_match_result(
        home=home,
        away=away,
        home_score=2,
        away_score=0,
        importance=1.25,
    )

    assert rating_update.expected_home_score < 0.30
    assert updated_home.elo_rating > home.elo_rating
    assert updated_away.elo_rating < away.elo_rating
    assert updated_home.wins == 1
    assert updated_away.losses == 1
    assert rating_update.home_delta == -rating_update.away_delta


def test_tournament_scheduler_creates_seeded_bracket_with_byes() -> None:
    service = UltimateLeagueService()
    starts_at = datetime(2026, 4, 4, 18, 0, tzinfo=timezone.utc)
    gold_players = [
        _competitor("g1", "Gold 1", 1580, wins=8),
        _competitor("g2", "Gold 2", 1565, wins=7),
        _competitor("g3", "Gold 3", 1550, wins=6),
        _competitor("g4", "Gold 4", 1535, wins=5),
        _competitor("g5", "Gold 5", 1520, wins=4),
        _competitor("g6", "Gold 6", 1505, wins=3),
    ]

    plan = service.schedule_tier_tournament(
        tournament_id="gold-weekly-1",
        tier=LeagueTier.GOLD,
        competitors=gold_players,
        starts_at=starts_at,
        field_size=6,
        parallel_matches=2,
    )

    assert plan.bracket.bracket_size == 8
    assert len(plan.bracket.rounds) == 3
    round_one = plan.bracket.rounds[0]
    assert [match.round_name for match in plan.bracket.rounds] == ["Quarterfinal", "Semifinal", "Final"]
    assert round_one.matches[0].home is not None
    assert round_one.matches[0].home.seed == 1
    assert round_one.matches[0].away is None
    assert round_one.matches[2].home is not None
    assert round_one.matches[2].home.seed == 2
    assert round_one.matches[2].away is None
    assert round_one.matches[1].starts_at == round_one.matches[0].starts_at
    assert round_one.matches[2].starts_at > round_one.matches[0].starts_at


def test_prize_distribution_returns_gtex_coin_payouts() -> None:
    service = UltimateLeagueService()
    placements = [
        _competitor("p1", "Player 1", 1580),
        _competitor("p2", "Player 2", 1560),
        _competitor("p3", "Player 3", 1540),
        _competitor("p4", "Player 4", 1520),
    ]

    payouts = service.distribute_prize_pool(
        tournament_id="gold-weekly-1",
        tier=LeagueTier.GOLD,
        placements=placements,
        gross_pool_gtex=Decimal("1000.0000"),
        entrant_count=8,
    )

    assert [payout.amount for payout in payouts] == [
        Decimal("550.0000"),
        Decimal("250.0000"),
        Decimal("120.0000"),
        Decimal("80.0000"),
    ]
    assert sum((payout.amount for payout in payouts), start=Decimal("0.0000")) == Decimal("1000.0000")
    assert all(payout.unit is LedgerUnit.COIN for payout in payouts)
    assert all(payout.source_tag is LedgerSourceTag.PLATFORM_COMPETITION_REWARD for payout in payouts)
    assert all(payout.reason is LedgerEntryReason.COMPETITION_REWARD for payout in payouts)
