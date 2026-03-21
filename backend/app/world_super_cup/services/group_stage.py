from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.world_super_cup.models import Group, GroupMatch, GroupStageSnapshot, GroupStanding, QualifiedClub
from app.world_super_cup.services.match_resolution import resolve_seeded_score


@dataclass(slots=True)
class GroupStageService:
    group_names: tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H")

    def build_snapshot(
        self,
        main_event_clubs: tuple[QualifiedClub, ...],
        tournament_start: datetime,
    ) -> GroupStageSnapshot:
        groups = self.create_groups(main_event_clubs)
        scheduled_matches = self.schedule_matches(groups, tournament_start)
        played_matches = self.simulate_matches(scheduled_matches)
        tables = self.build_tables(groups, played_matches)
        advancing_clubs = self.advancing_clubs(tables)
        return GroupStageSnapshot(
            groups=groups,
            matches=played_matches,
            tables=tables,
            advancing_clubs=advancing_clubs,
        )

    def create_groups(self, main_event_clubs: tuple[QualifiedClub, ...]) -> tuple[Group, ...]:
        if len(main_event_clubs) != 32:
            raise ValueError("World Super Cup group stage requires exactly 32 clubs")

        ordered = tuple(
            sorted(main_event_clubs, key=lambda club: (-club.coefficient_points, club.club_name))
        )
        pots = [ordered[index : index + 8] for index in range(0, len(ordered), 8)]
        grouped: dict[str, list[QualifiedClub]] = {name: [] for name in self.group_names}

        for pot_index, pot in enumerate(pots):
            assignment_order = self.group_names if pot_index % 2 == 0 else tuple(reversed(self.group_names))
            for group_name, club in zip(assignment_order, pot):
                grouped[group_name].append(club)

        return tuple(Group(group_name=name, clubs=tuple(grouped[name])) for name in self.group_names)

    def schedule_matches(
        self,
        groups: tuple[Group, ...],
        tournament_start: datetime,
    ) -> tuple[GroupMatch, ...]:
        round_robin_pairs = (
            ((0, 3), (1, 2)),
            ((0, 2), (3, 1)),
            ((0, 1), (2, 3)),
        )
        kickoff_offsets = {
            1: timedelta(hours=4),
            2: timedelta(days=1, hours=2),
            3: timedelta(days=1, hours=10),
        }
        matches: list[GroupMatch] = []
        for group_index, group in enumerate(groups):
            for matchday, pairings in enumerate(round_robin_pairs, start=1):
                for pairing_index, (home_index, away_index) in enumerate(pairings, start=1):
                    matches.append(
                        GroupMatch(
                            match_id=f"group-{group.group_name}-{matchday}-{pairing_index}",
                            group_name=group.group_name,
                            matchday=matchday,
                            home_club=group.clubs[home_index],
                            away_club=group.clubs[away_index],
                            kickoff_at=tournament_start + kickoff_offsets[matchday] + timedelta(minutes=group_index * 15),
                            venue=f"World Super Cup Hub {group_index + 1}",
                        )
                    )
        return tuple(matches)

    def simulate_matches(self, matches: tuple[GroupMatch, ...]) -> tuple[GroupMatch, ...]:
        played_matches: list[GroupMatch] = []
        for match in matches:
            home_score, away_score, _ = resolve_seeded_score(
                match.home_club.coefficient_points,
                match.away_club.coefficient_points,
                allow_draw=True,
            )
            played_matches.append(
                GroupMatch(
                    match_id=match.match_id,
                    group_name=match.group_name,
                    matchday=match.matchday,
                    home_club=match.home_club,
                    away_club=match.away_club,
                    kickoff_at=match.kickoff_at,
                    venue=match.venue,
                    home_score=home_score,
                    away_score=away_score,
                )
            )
        return tuple(played_matches)

    def build_tables(
        self,
        groups: tuple[Group, ...],
        matches: tuple[GroupMatch, ...],
    ) -> tuple[GroupStanding, ...]:
        grouped_matches: dict[str, list[GroupMatch]] = {}
        for match in matches:
            grouped_matches.setdefault(match.group_name, []).append(match)

        tables: list[GroupStanding] = []
        for group in groups:
            stats = {
                club.club_id: {
                    "club": club,
                    "played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "points": 0,
                }
                for club in group.clubs
            }

            for match in grouped_matches[group.group_name]:
                home = stats[match.home_club.club_id]
                away = stats[match.away_club.club_id]
                home["played"] += 1
                away["played"] += 1
                home["goals_for"] += int(match.home_score or 0)
                home["goals_against"] += int(match.away_score or 0)
                away["goals_for"] += int(match.away_score or 0)
                away["goals_against"] += int(match.home_score or 0)

                if (match.home_score or 0) > (match.away_score or 0):
                    home["wins"] += 1
                    away["losses"] += 1
                    home["points"] += 3
                elif (match.home_score or 0) < (match.away_score or 0):
                    away["wins"] += 1
                    home["losses"] += 1
                    away["points"] += 3
                else:
                    home["draws"] += 1
                    away["draws"] += 1
                    home["points"] += 1
                    away["points"] += 1

            ordered_rows = sorted(
                stats.values(),
                key=lambda row: (
                    -int(row["points"]),
                    -(int(row["goals_for"]) - int(row["goals_against"])),
                    -int(row["goals_for"]),
                    -row["club"].coefficient_points,
                    row["club"].club_name,
                ),
            )

            for position, row in enumerate(ordered_rows, start=1):
                tables.append(
                    GroupStanding(
                        group_name=group.group_name,
                        position=position,
                        club=row["club"],
                        played=int(row["played"]),
                        wins=int(row["wins"]),
                        draws=int(row["draws"]),
                        losses=int(row["losses"]),
                        goals_for=int(row["goals_for"]),
                        goals_against=int(row["goals_against"]),
                        goal_difference=int(row["goals_for"]) - int(row["goals_against"]),
                        points=int(row["points"]),
                    )
                )

        return tuple(tables)

    def advancing_clubs(self, tables: tuple[GroupStanding, ...]) -> tuple[QualifiedClub, ...]:
        advancing = [
            standing.club
            for standing in sorted(tables, key=lambda row: (row.group_name, row.position))
            if standing.position <= 2
        ]
        return tuple(advancing)
