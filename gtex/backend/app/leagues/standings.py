from __future__ import annotations

from app.leagues.models import LeagueClub, LeagueFixture, LeagueStandingRow


class LeagueStandingsService:
    def compute(
        self,
        *,
        clubs: tuple[LeagueClub, ...],
        fixtures: tuple[LeagueFixture, ...],
    ) -> tuple[LeagueStandingRow, ...]:
        table = {
            club.club_id: {
                "club_name": club.club_name,
                "played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "points": 0,
            }
            for club in clubs
        }

        for fixture in fixtures:
            if fixture.result is None:
                continue
            home = table[fixture.home_club_id]
            away = table[fixture.away_club_id]
            home_goals = fixture.result.home_goals
            away_goals = fixture.result.away_goals

            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += home_goals
            home["goals_against"] += away_goals
            away["goals_for"] += away_goals
            away["goals_against"] += home_goals

            if home_goals > away_goals:
                home["wins"] += 1
                away["losses"] += 1
                home["points"] += 3
            elif away_goals > home_goals:
                away["wins"] += 1
                home["losses"] += 1
                away["points"] += 3
            else:
                home["draws"] += 1
                away["draws"] += 1
                home["points"] += 1
                away["points"] += 1

        ordered = sorted(
            table.items(),
            key=lambda item: (
                -item[1]["points"],
                -(item[1]["goals_for"] - item[1]["goals_against"]),
                -item[1]["goals_for"],
                item[1]["club_name"],
            ),
        )

        return tuple(
            LeagueStandingRow(
                position=index,
                club_id=club_id,
                club_name=stats["club_name"],
                played=stats["played"],
                wins=stats["wins"],
                draws=stats["draws"],
                losses=stats["losses"],
                goals_for=stats["goals_for"],
                goals_against=stats["goals_against"],
                goal_difference=stats["goals_for"] - stats["goals_against"],
                points=stats["points"],
            )
            for index, (club_id, stats) in enumerate(ordered, start=1)
        )


__all__ = ["LeagueStandingsService"]
