from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping, Sequence


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _serialize(payload: Any) -> str:
    if is_dataclass(payload):
        return json.dumps(asdict(payload), ensure_ascii=True, sort_keys=True)
    if isinstance(payload, Mapping):
        return json.dumps(dict(payload), ensure_ascii=True, sort_keys=True)
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        return json.dumps(list(payload), ensure_ascii=True, sort_keys=True)
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


class UniverseStore:
    def __init__(self, database_path: str | Path = "tmp/universe/universe.db") -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save_league(self, league: Any) -> None:
        payload = league.as_dict() if hasattr(league, "as_dict") else json.loads(_serialize(league))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO leagues (league_id, name, season, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(league_id) DO UPDATE SET
                    name = excluded.name,
                    season = excluded.season,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    str(payload["league_id"]),
                    str(payload["name"]),
                    int(payload["season"]),
                    json.dumps(payload, ensure_ascii=True, sort_keys=True),
                    _utcnow(),
                    _utcnow(),
                ),
            )

    def save_fixtures(self, *, league_id: str, fixtures: Sequence[Any]) -> None:
        with self._connect() as connection:
            for fixture in fixtures:
                payload = fixture.as_dict() if hasattr(fixture, "as_dict") else json.loads(_serialize(fixture))
                connection.execute(
                    """
                    INSERT INTO fixtures (
                        fixture_id,
                        league_id,
                        round_number,
                        leg,
                        home_club_id,
                        away_club_id,
                        status,
                        payload_json,
                        result_json,
                        created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(fixture_id) DO UPDATE SET
                        league_id = excluded.league_id,
                        round_number = excluded.round_number,
                        leg = excluded.leg,
                        home_club_id = excluded.home_club_id,
                        away_club_id = excluded.away_club_id,
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        str(payload["fixture_id"]),
                        league_id,
                        int(payload["round_number"]),
                        int(payload["leg"]),
                        str(payload["home_club_id"]),
                        str(payload["away_club_id"]),
                        "scheduled",
                        json.dumps(payload, ensure_ascii=True, sort_keys=True),
                        None,
                        _utcnow(),
                        _utcnow(),
                    ),
                )

    def save_match_result(self, result: Any) -> None:
        payload = result.as_dict() if hasattr(result, "as_dict") else json.loads(_serialize(result))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO match_results (
                    match_id,
                    league_id,
                    fixture_id,
                    home_club_id,
                    away_club_id,
                    winner_club_id,
                    home_goals,
                    away_goals,
                    payload_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    home_goals = excluded.home_goals,
                    away_goals = excluded.away_goals,
                    winner_club_id = excluded.winner_club_id
                """,
                (
                    str(payload["match_id"]),
                    str(payload["league_id"]),
                    str(payload["fixture_id"]),
                    str(payload["home_club_id"]),
                    str(payload["away_club_id"]),
                    payload["winner_club_id"],
                    int(payload["home_goals"]),
                    int(payload["away_goals"]),
                    json.dumps(payload, ensure_ascii=True, sort_keys=True),
                    _utcnow(),
                ),
            )
            connection.execute(
                """
                UPDATE fixtures
                SET status = 'completed',
                    result_json = ?,
                    updated_at = ?
                WHERE fixture_id = ?
                """,
                (
                    json.dumps(payload, ensure_ascii=True, sort_keys=True),
                    _utcnow(),
                    str(payload["fixture_id"]),
                ),
            )
            connection.execute(
                """
                DELETE FROM player_performances
                WHERE match_id = ?
                """,
                (str(payload["match_id"]),),
            )
            for performance in tuple(payload.get("player_performances") or ()):
                connection.execute(
                    """
                    INSERT INTO player_performances (
                        match_id,
                        player_id,
                        team_id,
                        team_name,
                        player_name,
                        position,
                        minutes,
                        rating,
                        goals,
                        assists,
                        shots,
                        shots_on_target,
                        xg,
                        key_passes,
                        passes_completed,
                        tackles_won,
                        fouls_committed,
                        yellow_cards,
                        red_card,
                        saves,
                        clean_sheet,
                        payload_json,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(match_id, player_id) DO UPDATE SET
                        team_id = excluded.team_id,
                        team_name = excluded.team_name,
                        player_name = excluded.player_name,
                        position = excluded.position,
                        minutes = excluded.minutes,
                        rating = excluded.rating,
                        goals = excluded.goals,
                        assists = excluded.assists,
                        shots = excluded.shots,
                        shots_on_target = excluded.shots_on_target,
                        xg = excluded.xg,
                        key_passes = excluded.key_passes,
                        passes_completed = excluded.passes_completed,
                        tackles_won = excluded.tackles_won,
                        fouls_committed = excluded.fouls_committed,
                        yellow_cards = excluded.yellow_cards,
                        red_card = excluded.red_card,
                        saves = excluded.saves,
                        clean_sheet = excluded.clean_sheet,
                        payload_json = excluded.payload_json,
                        created_at = excluded.created_at
                    """,
                    (
                        str(payload["match_id"]),
                        str(performance["player_id"]),
                        str(performance["team_id"]),
                        str(performance["team_name"]),
                        str(performance["player_name"]),
                        str(performance["position"]),
                        int(performance["minutes"]),
                        float(performance["rating"]),
                        int(performance["goals"]),
                        int(performance["assists"]),
                        int(performance["shots"]),
                        int(performance["shots_on_target"]),
                        float(performance["xg"]),
                        int(performance["key_passes"]),
                        int(performance["passes_completed"]),
                        int(performance["tackles_won"]),
                        int(performance["fouls_committed"]),
                        int(performance["yellow_cards"]),
                        int(bool(performance["red_card"])),
                        int(performance["saves"]),
                        int(bool(performance["clean_sheet"])),
                        json.dumps(performance, ensure_ascii=True, sort_keys=True),
                        _utcnow(),
                    ),
                )

    def list_fixtures(
        self,
        *,
        league_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        query = "SELECT payload_json FROM fixtures"
        clauses: list[str] = []
        params: list[object] = []
        if league_id:
            clauses.append("league_id = ?")
            params.append(league_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY round_number ASC LIMIT ?"
        params.append(max(limit, 1))
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [json.loads(str(row["payload_json"])) for row in rows]

    def recent_results(self, *, league_id: str | None = None, limit: int = 20) -> list[dict[str, object]]:
        query = "SELECT payload_json FROM match_results"
        params: list[object] = []
        if league_id:
            query += " WHERE league_id = ?"
            params.append(league_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(limit, 1))
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [json.loads(str(row["payload_json"])) for row in rows]

    def recent_head_to_head(self, *, club_a_id: str, club_b_id: str, limit: int = 5) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM match_results
                WHERE (home_club_id = ? AND away_club_id = ?)
                   OR (home_club_id = ? AND away_club_id = ?)
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (club_a_id, club_b_id, club_b_id, club_a_id, max(limit, 1)),
            ).fetchall()
        return [json.loads(str(row["payload_json"])) for row in rows]

    def player_performances(self, *, match_id: str, limit: int = 50) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT match_id, payload_json
                FROM player_performances
                WHERE match_id = ?
                ORDER BY rating DESC, goals DESC, assists DESC, player_name ASC
                LIMIT ?
                """,
                (match_id, max(limit, 1)),
            ).fetchall()
        return [
            {
                "match_id": str(row["match_id"]),
                **json.loads(str(row["payload_json"])),
            }
            for row in rows
        ]

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS leagues (
                    league_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS fixtures (
                    fixture_id TEXT PRIMARY KEY,
                    league_id TEXT NOT NULL,
                    round_number INTEGER NOT NULL,
                    leg INTEGER NOT NULL,
                    home_club_id TEXT NOT NULL,
                    away_club_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS match_results (
                    match_id TEXT PRIMARY KEY,
                    league_id TEXT NOT NULL,
                    fixture_id TEXT NOT NULL,
                    home_club_id TEXT NOT NULL,
                    away_club_id TEXT NOT NULL,
                    winner_club_id TEXT,
                    home_goals INTEGER NOT NULL,
                    away_goals INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS player_performances (
                    match_id TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    team_id TEXT NOT NULL,
                    team_name TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    position TEXT NOT NULL,
                    minutes INTEGER NOT NULL,
                    rating REAL NOT NULL,
                    goals INTEGER NOT NULL,
                    assists INTEGER NOT NULL,
                    shots INTEGER NOT NULL,
                    shots_on_target INTEGER NOT NULL,
                    xg REAL NOT NULL,
                    key_passes INTEGER NOT NULL,
                    passes_completed INTEGER NOT NULL,
                    tackles_won INTEGER NOT NULL,
                    fouls_committed INTEGER NOT NULL,
                    yellow_cards INTEGER NOT NULL,
                    red_card INTEGER NOT NULL,
                    saves INTEGER NOT NULL,
                    clean_sheet INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (match_id, player_id)
                );
                """)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection
