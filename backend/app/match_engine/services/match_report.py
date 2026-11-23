from __future__ import annotations

from typing import Any

from app.match_engine.schemas import MatchReplayPayloadView

_GOAL_EVENT_TYPES = frozenset({"goal", "penalty_goal", "penalty_scored"})
_PENALTY_GOAL_TYPES = frozenset({"penalty_goal", "penalty_scored"})
_CARD_EVENT_TYPES = frozenset({"yellow_card", "red_card"})
_SHOT_EVENT_TYPES = frozenset(
    {
        "goal",
        "penalty_goal",
        "penalty_scored",
        "shot",
        "shot_on_target",
        "missed_chance",
        "missed_big_chance",
        "woodwork",
        "save",
        "goalkeeper_save",
        "double_save",
        "penalty_missed",
        "penalty_miss",
        "miss",
    }
)


def _side_for_team(
    *,
    team_id: str | None,
    team_name: str | None,
    home_team_id: str,
    away_team_id: str,
    home_team_name: str,
    away_team_name: str,
) -> str | None:
    raw_id = str(team_id or "").strip()
    if raw_id:
        if raw_id == home_team_id or raw_id.lower() == "home":
            return "home"
        if raw_id == away_team_id or raw_id.lower() == "away":
            return "away"
    raw_name = str(team_name or "").strip().lower()
    if raw_name:
        if raw_name == home_team_name.strip().lower():
            return "home"
        if raw_name == away_team_name.strip().lower():
            return "away"
    return None


def build_simulated_match_report(
    replay_payload: MatchReplayPayloadView,
    *,
    home_team_name: str | None = None,
    away_team_name: str | None = None,
    result_label: str | None = None,
) -> dict[str, Any]:
    """Extract an authoritative full-time stats & scorers report from a simulated replay payload."""
    summary = replay_payload.summary
    home_stats = summary.home_stats
    away_stats = summary.away_stats
    home_id = str(home_stats.team_id)
    away_id = str(away_stats.team_id)
    resolved_home_name = str(home_team_name or home_stats.team_name or "Home")
    resolved_away_name = str(away_team_name or away_stats.team_name or "Away")

    home_player_ids = {str(p.player_id) for p in summary.player_stats if str(p.team_id) == home_id}
    away_player_ids = {str(p.player_id) for p in summary.player_stats if str(p.team_id) == away_id}

    goals: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
    for event in replay_payload.timeline.events:
        ev_type = str(getattr(event.event_type, "value", event.event_type) or "").lower()
        side = _side_for_team(
            team_id=event.team_id,
            team_name=event.team_name,
            home_team_id=home_id,
            away_team_id=away_id,
            home_team_name=resolved_home_name,
            away_team_name=resolved_away_name,
        )
        if side is None and event.primary_player is not None:
            pid = str(event.primary_player.player_id)
            if pid in home_player_ids:
                side = "home"
            elif pid in away_player_ids:
                side = "away"
        if side is None:
            continue

        resolved_team_id = home_id if side == "home" else away_id
        resolved_team_name = resolved_home_name if side == "home" else resolved_away_name

        if ev_type in _GOAL_EVENT_TYPES:
            is_penalty = ev_type in _PENALTY_GOAL_TYPES
            scorer_id = str(event.primary_player.player_id) if event.primary_player else None
            scorer_name = (
                str(event.primary_player.player_name)
                if event.primary_player and event.primary_player.player_name
                else f"{resolved_team_name} Scorer"
            )
            assist_id: str | None = None
            assist_name: str | None = None
            if not is_penalty and event.secondary_player is not None:
                cand_id = str(event.secondary_player.player_id or "")
                cand_name = str(event.secondary_player.player_name or "").strip()
                same_team = (side == "home" and cand_id in home_player_ids) or (
                    side == "away" and cand_id in away_player_ids
                )
                if cand_name and cand_id != scorer_id and (same_team or (not home_player_ids and not away_player_ids)):
                    assist_id = cand_id or None
                    assist_name = cand_name
            goals.append(
                {
                    "minute": int(event.minute),
                    "added_time": int(event.added_time or 0),
                    "clock_label": str(event.clock_label or f"{event.minute}'"),
                    "side": side,
                    "team_id": resolved_team_id,
                    "team_name": resolved_team_name,
                    "scorer_id": scorer_id,
                    "scorer_name": scorer_name,
                    "assist_id": assist_id,
                    "assist_name": assist_name,
                    "is_penalty": is_penalty,
                    "home_score": int(event.home_score),
                    "away_score": int(event.away_score),
                    "commentary": str(event.commentary or ""),
                }
            )
        elif ev_type in _CARD_EVENT_TYPES:
            cards.append(
                {
                    "minute": int(event.minute),
                    "clock_label": str(event.clock_label or f"{event.minute}'"),
                    "side": side,
                    "team_id": resolved_team_id,
                    "team_name": resolved_team_name,
                    "player_id": str(event.primary_player.player_id) if event.primary_player else None,
                    "player_name": (
                        str(event.primary_player.player_name)
                        if event.primary_player and event.primary_player.player_name
                        else f"{resolved_team_name} Player"
                    ),
                    "card_type": ev_type,
                    "commentary": str(event.commentary or ""),
                }
            )

    player_rows: list[dict[str, Any]] = []
    home_assists = 0
    away_assists = 0
    home_key_passes = 0
    away_key_passes = 0
    home_tackles = 0
    away_tackles = 0
    home_interceptions = 0
    away_interceptions = 0

    for player in summary.player_stats:
        p_side = _side_for_team(
            team_id=player.team_id,
            team_name=player.team_name,
            home_team_id=home_id,
            away_team_id=away_id,
            home_team_name=resolved_home_name,
            away_team_name=resolved_away_name,
        )
        if p_side == "home":
            home_assists += int(player.assists or 0)
            home_key_passes += int(player.key_passes or 0)
            home_tackles += int(player.tackles_won or 0)
            home_interceptions += int(player.interceptions or 0)
        elif p_side == "away":
            away_assists += int(player.assists or 0)
            away_key_passes += int(player.key_passes or 0)
            away_tackles += int(player.tackles_won or 0)
            away_interceptions += int(player.interceptions or 0)

        if int(player.minutes_played or 0) <= 0 and not player.started:
            continue

        player_rows.append(
            {
                "player_id": str(player.player_id),
                "player_name": str(player.player_name),
                "team_id": str(player.team_id),
                "team_name": resolved_home_name if p_side == "home" else resolved_away_name,
                "side": p_side or "home",
                "role": str(getattr(player.role, "value", player.role) or ""),
                "started": bool(player.started),
                "minutes_played": int(player.minutes_played or 0),
                "goals": int(player.goals or 0),
                "assists": int(player.assists or 0),
                "saves": int(player.saves or 0),
                "shots_on_target": int(player.shots_on_target or 0),
                "key_passes": int(player.key_passes or 0),
                "tackles_won": int(player.tackles_won or 0),
                "interceptions": int(player.interceptions or 0),
                "yellow_cards": int(player.yellow_cards or 0),
                "red_card": bool(player.red_card),
                "xg": round(float(player.xg or 0.0), 2),
                "rating": round(float(player.rating), 1) if player.rating is not None else None,
                "rating_summary": player.rating_summary,
            }
        )

    player_rows.sort(
        key=lambda row: (
            -(row["rating"] if row["rating"] is not None else -1.0),
            -row["goals"],
            -row["assists"],
            row["player_name"],
        )
    )

    motm: dict[str, Any] = {"available": False}
    if player_rows:
        best = player_rows[0]
        motm = {
            "available": True,
            "player_id": best["player_id"],
            "player_name": best["player_name"],
            "team_id": best["team_id"],
            "team_name": best["team_name"],
            "side": best["side"],
            "role": best["role"],
            "goals": best["goals"],
            "assists": best["assists"],
            "rating": best["rating"],
            "summary": best.get("rating_summary") or None,
        }

    home_xg = round(float(summary.expected_goals_home or 0.0), 2)
    away_xg = round(float(summary.expected_goals_away or 0.0), 2)

    stats = {
        "home_possession": int(home_stats.possession),
        "away_possession": int(away_stats.possession),
        "home_shots": int(home_stats.shots),
        "away_shots": int(away_stats.shots),
        "home_shots_on_target": int(home_stats.shots_on_target),
        "away_shots_on_target": int(away_stats.shots_on_target),
        "home_saves": int(home_stats.saves),
        "away_saves": int(away_stats.saves),
        "home_expected_goals": home_xg,
        "away_expected_goals": away_xg,
        "home_yellow_cards": int(home_stats.yellow_cards),
        "away_yellow_cards": int(away_stats.yellow_cards),
        "home_red_cards": int(home_stats.red_cards),
        "away_red_cards": int(away_stats.red_cards),
        "home_big_chances": int(home_stats.big_chances),
        "away_big_chances": int(away_stats.big_chances),
        "home_woodwork": int(home_stats.woodwork),
        "away_woodwork": int(away_stats.woodwork),
        "home_substitutions": int(home_stats.substitutions),
        "away_substitutions": int(away_stats.substitutions),
        "home_assists": home_assists,
        "away_assists": away_assists,
        "home_key_passes": home_key_passes,
        "away_key_passes": away_key_passes,
        "home_tackles_won": home_tackles,
        "away_tackles_won": away_tackles,
        "home_interceptions": home_interceptions,
        "away_interceptions": away_interceptions,
    }

    if result_label is None:
        if summary.home_score > summary.away_score:
            result_label = "win"
        elif summary.away_score > summary.home_score:
            result_label = "loss"
        else:
            result_label = "draw"

    return {
        "match_id": str(summary.match_id),
        "home_team_id": home_id,
        "away_team_id": away_id,
        "home_team_name": resolved_home_name,
        "away_team_name": resolved_away_name,
        "home_score": int(summary.home_score),
        "away_score": int(summary.away_score),
        "decided_by_penalties": bool(summary.decided_by_penalties),
        "home_penalty_score": summary.home_penalty_score,
        "away_penalty_score": summary.away_penalty_score,
        "result": result_label,
        "summary_line": str(summary.summary_line or ""),
        "stats": stats,
        "goals": goals,
        "cards": cards,
        "player_stats": player_rows,
        "motm": motm,
        "key_highlights": [str(item) for item in (summary.key_highlights or [])],
        "is_simulated": True,
    }


def build_simulated_match_report_from_payload(
    *,
    match_id: str,
    home_team_id: str,
    away_team_id: str,
    home_team_name: str,
    away_team_name: str,
    home_score: int,
    away_score: int,
    events: list[dict[str, Any]] | None = None,
    narrative: dict[str, Any] | None = None,
    result_label: str | None = None,
) -> dict[str, Any]:
    """Reconstruct a simulated match report from persisted viewer/owner events for legacy matches."""
    existing = (narrative or {}).get("match_report") if isinstance(narrative, dict) else None
    if isinstance(existing, dict) and existing.get("stats"):
        return dict(existing)

    goals: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
    home_shots = 0
    away_shots = 0
    home_saves = 0
    away_saves = 0
    home_yellows = 0
    away_yellows = 0
    home_reds = 0
    away_reds = 0
    home_assists = 0
    away_assists = 0
    home_goals_running = 0
    away_goals_running = 0

    for raw in events or []:
        if not isinstance(raw, dict):
            continue
        ev_type = str(raw.get("event_type") or raw.get("type") or "").lower()
        side = _side_for_team(
            team_id=raw.get("team_id") or raw.get("team") or raw.get("side"),
            team_name=raw.get("team_name"),
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_team_name=home_team_name,
            away_team_name=away_team_name,
        )
        if side is None:
            continue
        minute = int(raw.get("minute") or 0)
        clock_label = str(raw.get("clock_label") or f"{minute}'")
        commentary = str(raw.get("commentary") or raw.get("text") or raw.get("description") or "")
        team_id = home_team_id if side == "home" else away_team_id
        team_name = home_team_name if side == "home" else away_team_name

        if ev_type in _GOAL_EVENT_TYPES:
            is_penalty = ev_type in _PENALTY_GOAL_TYPES or bool(raw.get("is_penalty"))
            if side == "home":
                home_goals_running += 1
                home_shots += 1
            else:
                away_goals_running += 1
                away_shots += 1
            scorer_name = str(
                raw.get("scorer")
                or raw.get("scorer_name")
                or raw.get("primary_player_name")
                or raw.get("player_name")
                or f"{team_name} Scorer"
            )
            assist_name = None
            if not is_penalty:
                cand_assist = str(
                    raw.get("assist") or raw.get("assist_name") or raw.get("secondary_player_name") or ""
                ).strip()
                if cand_assist and cand_assist != scorer_name:
                    assist_name = cand_assist
                    if side == "home":
                        home_assists += 1
                    else:
                        away_assists += 1
            goals.append(
                {
                    "minute": minute,
                    "added_time": int(raw.get("added_time") or 0),
                    "clock_label": clock_label,
                    "side": side,
                    "team_id": team_id,
                    "team_name": team_name,
                    "scorer_id": raw.get("scorer_id") or raw.get("primary_player_id"),
                    "scorer_name": scorer_name,
                    "assist_id": (raw.get("assist_id") or raw.get("secondary_player_id")) if assist_name else None,
                    "assist_name": assist_name,
                    "is_penalty": is_penalty,
                    "home_score": int(
                        raw.get("home_score") if raw.get("home_score") is not None else home_goals_running
                    ),
                    "away_score": int(
                        raw.get("away_score") if raw.get("away_score") is not None else away_goals_running
                    ),
                    "commentary": commentary,
                }
            )
        elif ev_type in _CARD_EVENT_TYPES:
            if ev_type == "yellow_card":
                if side == "home":
                    home_yellows += 1
                else:
                    away_yellows += 1
            else:
                if side == "home":
                    home_reds += 1
                else:
                    away_reds += 1
            cards.append(
                {
                    "minute": minute,
                    "clock_label": clock_label,
                    "side": side,
                    "team_id": team_id,
                    "team_name": team_name,
                    "player_id": raw.get("primary_player_id") or raw.get("player_id"),
                    "player_name": str(
                        raw.get("primary_player_name")
                        or raw.get("player_name")
                        or raw.get("player")
                        or f"{team_name} Player"
                    ),
                    "card_type": ev_type,
                    "commentary": commentary,
                }
            )
        elif ev_type in {"save", "goalkeeper_save", "double_save"}:
            if side == "home":
                home_saves += 1
                away_shots += 1
            else:
                away_saves += 1
                home_shots += 1
        elif ev_type in _SHOT_EVENT_TYPES or ev_type == "chance":
            if side == "home":
                home_shots += 1
            else:
                away_shots += 1

    persisted_stats = dict((narrative or {}).get("stats") or {}) if isinstance(narrative, dict) else {}
    xg_pair = (narrative or {}).get("expected_goals") if isinstance(narrative, dict) else None
    fallback_home_xg = round(float(xg_pair[0]), 2) if isinstance(xg_pair, (list, tuple)) and len(xg_pair) >= 2 else None
    fallback_away_xg = round(float(xg_pair[1]), 2) if isinstance(xg_pair, (list, tuple)) and len(xg_pair) >= 2 else None

    momentum = (narrative or {}).get("momentum") if isinstance(narrative, dict) else None
    fallback_home_poss: int | None = None
    fallback_away_poss: int | None = None
    if isinstance(momentum, list) and momentum:
        numeric_mom = [float(v) for v in momentum if isinstance(v, (int, float))]
        if numeric_mom:
            avg_mom = sum(numeric_mom) / len(numeric_mom)
            fallback_home_poss = max(25, min(75, int(round(avg_mom))))
            fallback_away_poss = 100 - fallback_home_poss

    stats = {
        "home_possession": persisted_stats.get("home_possession", fallback_home_poss),
        "away_possession": persisted_stats.get("away_possession", fallback_away_poss),
        "home_shots": persisted_stats.get("home_shots", home_shots),
        "away_shots": persisted_stats.get("away_shots", away_shots),
        "home_shots_on_target": persisted_stats.get("home_shots_on_target", home_score + away_saves),
        "away_shots_on_target": persisted_stats.get("away_shots_on_target", away_score + home_saves),
        "home_saves": persisted_stats.get("home_saves", home_saves),
        "away_saves": persisted_stats.get("away_saves", away_saves),
        "home_expected_goals": persisted_stats.get("home_expected_goals", fallback_home_xg),
        "away_expected_goals": persisted_stats.get("away_expected_goals", fallback_away_xg),
        "home_yellow_cards": persisted_stats.get("home_yellow_cards", home_yellows),
        "away_yellow_cards": persisted_stats.get("away_yellow_cards", away_yellows),
        "home_red_cards": persisted_stats.get("home_red_cards", home_reds),
        "away_red_cards": persisted_stats.get("away_red_cards", away_reds),
        "home_big_chances": persisted_stats.get("home_big_chances"),
        "away_big_chances": persisted_stats.get("away_big_chances"),
        "home_assists": persisted_stats.get("home_assists", home_assists),
        "away_assists": persisted_stats.get("away_assists", away_assists),
        "home_key_passes": persisted_stats.get("home_key_passes"),
        "away_key_passes": persisted_stats.get("away_key_passes"),
        "home_tackles_won": persisted_stats.get("home_tackles_won"),
        "away_tackles_won": persisted_stats.get("away_tackles_won"),
        "home_interceptions": persisted_stats.get("home_interceptions"),
        "away_interceptions": persisted_stats.get("away_interceptions"),
    }

    if result_label is None:
        if home_score > away_score:
            result_label = "win"
        elif away_score > home_score:
            result_label = "loss"
        else:
            result_label = "draw"

    return {
        "match_id": str(match_id),
        "home_team_id": str(home_team_id),
        "away_team_id": str(away_team_id),
        "home_team_name": str(home_team_name),
        "away_team_name": str(away_team_name),
        "home_score": int(home_score),
        "away_score": int(away_score),
        "decided_by_penalties": False,
        "home_penalty_score": None,
        "away_penalty_score": None,
        "result": result_label,
        "summary_line": f"{home_team_name} {home_score} - {away_score} {away_team_name}",
        "stats": stats,
        "goals": goals,
        "cards": cards,
        "player_stats": list((narrative or {}).get("player_stats") or []) if isinstance(narrative, dict) else [],
        "motm": (
            dict((narrative or {}).get("motm") or {"available": False})
            if isinstance(narrative, dict)
            else {"available": False}
        ),
        "key_highlights": list((narrative or {}).get("key_highlights") or []) if isinstance(narrative, dict) else [],
        "is_simulated": True,
    }


__all__ = [
    "build_simulated_match_report",
    "build_simulated_match_report_from_payload",
]
