"""Regression coverage for canonical match institutional projections."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.owner_console.canonical_match_projection import normalize_authoritative_appearances
from app.owner_console.living_club_world import emit_canonical_club_event
from app.owner_console.models import OwnerClubEvent


def test_authoritative_appearances_include_used_substitutes_and_exclude_unused_bench() -> None:
    rows = normalize_authoritative_appearances(
        [
            {"player_id": "starter", "team_id": "club-a", "minutes_played": 90, "started": True},
            {
                "player_id": "sub",
                "team_id": "club-a",
                "minutes_played": 24,
                "started": False,
                "substituted_in_minute": 66,
                "goals": 1,
            },
            {"player_id": "unused", "team_id": "club-a", "minutes_played": 0, "started": False},
            {"player_id": "opponent", "team_id": "club-b", "minutes_played": 90, "started": True},
        ],
        "club-a",
    )

    assert [row["player_id"] for row in rows] == ["starter", "sub"]
    assert rows[1]["minutes_played"] == 24
    assert rows[1]["substituted_in_minute"] == 66
    assert rows[1]["goals"] == 1


def test_canonical_source_events_are_idempotent_per_club() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    OwnerClubEvent.__table__.create(engine)

    with Session(engine) as session:
        home, created_home = emit_canonical_club_event(
            session,
            anchor_club_id="home-club",
            match_id="canonical-match-1",
            competition_id="competition-1",
            world_day=12,
            title="Home 2-1 Away",
            description="Completed canonical match",
            required_projections=["club:home-club:institutional_consequences"],
        )
        home_again, created_again = emit_canonical_club_event(
            session,
            anchor_club_id="home-club",
            match_id="canonical-match-1",
            competition_id="competition-1",
            world_day=12,
            title="Home 2-1 Away",
            description="Completed canonical match",
            required_projections=["club:home-club:institutional_consequences"],
        )
        away, created_away = emit_canonical_club_event(
            session,
            anchor_club_id="away-club",
            match_id="canonical-match-1",
            competition_id="competition-1",
            world_day=12,
            title="Home 2-1 Away",
            description="Completed canonical match",
            required_projections=["club:away-club:institutional_consequences"],
        )

        assert created_home is True
        assert created_again is False
        assert created_away is True
        assert home.id == home_again.id
        assert home.id != away.id
        assert home.club_id == "home-club"
        assert away.club_id == "away-club"
        assert home.source_id == away.source_id == "canonical-match-1"
