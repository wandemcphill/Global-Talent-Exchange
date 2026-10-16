from __future__ import annotations


def global_player_id(player_id: str) -> str:
    return f"player:{str(player_id).strip()}"


def global_competition_id(competition_id: str) -> str:
    return f"competition:{str(competition_id).strip()}"


def global_match_id(match_id: str) -> str:
    return f"match:{str(match_id).strip()}"


def global_country_id(country_code: str) -> str:
    return f"country:{str(country_code).strip().upper()}"


def global_user_id(user_id: str) -> str:
    return f"user:{str(user_id).strip()}"


__all__ = [
    "global_competition_id",
    "global_country_id",
    "global_match_id",
    "global_player_id",
    "global_user_id",
]
