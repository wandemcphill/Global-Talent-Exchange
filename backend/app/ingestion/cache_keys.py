from __future__ import annotations

from .constants import (
    CLUB_ROSTER_SNAPSHOT_TTL_SECONDS,
    COMPETITION_TABLE_TTL_SECONDS,
    PLAYER_PROFILE_SUMMARY_TTL_SECONDS,
    TOP_PROSPECTS_TTL_SECONDS,
    TRENDING_PLAYERS_TTL_SECONDS,
)


def top_prospects_key(scope: str = "global") -> str:
    return f"ingestion:top_prospects:{scope}"


def player_profile_summary_key(player_id: str) -> str:
    return f"ingestion:player_profile_summary:{player_id}"


def trending_players_key(scope: str = "global") -> str:
    return f"ingestion:trending_players:{scope}"


def competition_table_key(competition_id: str, season_id: str | None = None) -> str:
    season_part = season_id or "current"
    return f"ingestion:competition_table:{competition_id}:{season_part}"


def club_roster_snapshot_key(club_id: str, season_id: str | None = None) -> str:
    season_part = season_id or "current"
    return f"ingestion:club_roster_snapshot:{club_id}:{season_part}"


def competition_cache_keys(competition_id: str, season_id: str | None = None) -> list[str]:
    return [
        top_prospects_key(competition_id),
        trending_players_key(competition_id),
        competition_table_key(competition_id, season_id),
    ]


def club_cache_keys(club_id: str, season_id: str | None = None) -> list[str]:
    return [club_roster_snapshot_key(club_id, season_id)]


def player_cache_keys(player_id: str) -> list[str]:
    return [player_profile_summary_key(player_id), trending_players_key(player_id)]


CACHE_TTLS = {
    "top_prospects": TOP_PROSPECTS_TTL_SECONDS,
    "player_profile_summary": PLAYER_PROFILE_SUMMARY_TTL_SECONDS,
    "trending_players": TRENDING_PLAYERS_TTL_SECONDS,
    "competition_table": COMPETITION_TABLE_TTL_SECONDS,
    "club_roster_snapshot": CLUB_ROSTER_SNAPSHOT_TTL_SECONDS,
}
