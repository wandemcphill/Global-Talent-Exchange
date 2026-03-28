from __future__ import annotations

from typing import Any

def analyze_match(payload) -> dict[str, Any]:
    home = payload.summary.home_stats
    away = payload.summary.away_stats
    top_player = max(
        payload.summary.player_stats,
        key=lambda item: (item.rating or 0.0, item.goals, item.assists, item.saves),
        default=None,
    )
    turning_point = payload.summary.turning_points[0] if payload.summary.turning_points else None
    return {
        "score": f"{payload.summary.home_score}-{payload.summary.away_score}",
        "winner_team_name": payload.summary.winner_team_name,
        "xg_diff": round(payload.summary.expected_goals_home - payload.summary.expected_goals_away, 2),
        "shot_diff": home.shots - away.shots,
        "possession_winner": home.team_name if home.possession > away.possession else away.team_name if away.possession > home.possession else None,
        "upset": payload.summary.upset,
        "is_final": payload.summary.is_final,
        "key_player": top_player.player_name if top_player is not None else None,
        "key_player_team": top_player.team_name if top_player is not None else None,
        "key_player_rating": round(top_player.rating or 0.0, 1) if top_player is not None else None,
        "summary_line": payload.summary.summary_line,
        "turning_point": turning_point,
    }
