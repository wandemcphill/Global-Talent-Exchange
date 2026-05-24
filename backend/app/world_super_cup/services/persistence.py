from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.competition_match import CompetitionMatch
from app.models.world_super_cup_authority import (
    WorldSuperCupCoefficient,
    WorldSuperCupCountdown,
    WorldSuperCupFixture,
    WorldSuperCupGroup,
    WorldSuperCupQualifiedClub,
    WorldSuperCupSettlement,
    WorldSuperCupStanding,
    WorldSuperCupTournament,
)
from app.world_super_cup.models import (
    CoefficientEntry,
    Group,
    GroupMatch,
    GroupStageSnapshot,
    GroupStanding,
    KnockoutBracket,
    KnockoutMatch,
    KnockoutRound,
    PausePolicy,
    PlayoffMatch,
    QualificationPlan,
    QualifiedClub,
    TournamentCountdown,
    TournamentPlan,
    TrophyCeremonyMetadata,
    WorldSuperCupFixtureSnapshot,
    WorldSuperCupSettlementSnapshot,
)


class WorldSuperCupAuthorityError(ValueError):
    pass


@dataclass(slots=True)
class WorldSuperCupPersistenceService:
    session: Session

    def persist_plan(
        self,
        plan: TournamentPlan,
        *,
        tournament_id: str | None = None,
        competition_id: str | None = None,
        source: str = "competition_os",
    ) -> WorldSuperCupTournament:
        resolved_tournament_id = tournament_id or self.tournament_id_for_plan(plan)
        existing = self.session.get(WorldSuperCupTournament, resolved_tournament_id)
        if existing is not None and self._projection_exists(resolved_tournament_id):
            return existing

        if existing is None:
            existing = WorldSuperCupTournament(
                id=resolved_tournament_id,
                tournament_name=plan.countdown.tournament_name,
                season_label=self.season_label_for_plan(plan),
                starts_at=plan.countdown.starts_at,
            )
            self.session.add(existing)

        existing.competition_id = competition_id
        existing.tournament_name = plan.countdown.tournament_name
        existing.season_label = self.season_label_for_plan(plan)
        existing.status = "completed" if plan.knockout.champion is not None else "scheduled"
        existing.starts_at = plan.countdown.starts_at
        existing.ends_at = self._latest_fixture_time(plan)
        existing.reference_at = plan.countdown.reference_at
        existing.seasons_considered_json = list(plan.qualification.seasons_considered)
        existing.champion_club_id = plan.knockout.champion.club_id
        existing.runner_up_club_id = plan.knockout.runner_up.club_id
        existing.ceremony_json = self._ceremony_json(plan.knockout.ceremony)
        existing.metadata_json = {
            **dict(existing.metadata_json or {}),
            "source": source,
            "authority": "server_persisted",
        }
        self.session.flush()

        self._clear_projection(resolved_tournament_id)
        self._persist_countdown(resolved_tournament_id, plan.countdown)
        self._persist_coefficients(resolved_tournament_id, plan.qualification.coefficient_table)
        self._persist_qualified_clubs(resolved_tournament_id, "direct", plan.qualification.direct_qualifiers)
        self._persist_qualified_clubs(resolved_tournament_id, "playoff", plan.qualification.playoff_qualifiers)
        self._persist_qualified_clubs(resolved_tournament_id, "playoff_winner", plan.qualification.playoff_winners)
        self._persist_qualified_clubs(resolved_tournament_id, "main_event", plan.qualification.main_event_clubs)
        self._persist_groups(resolved_tournament_id, plan.group_stage.groups)
        self._persist_fixtures(resolved_tournament_id, plan)
        self._persist_standings(resolved_tournament_id, plan.group_stage.tables)
        self.session.flush()
        return existing

    def get_tournament(self, tournament_id: str | None = None) -> WorldSuperCupTournament | None:
        if tournament_id:
            return self.session.get(WorldSuperCupTournament, tournament_id)
        return self.session.scalar(
            select(WorldSuperCupTournament).order_by(
                WorldSuperCupTournament.starts_at.desc(),
                WorldSuperCupTournament.created_at.desc(),
            )
        )

    def read_plan(
        self,
        tournament_id: str | None = None,
        *,
        reference_at: datetime | None = None,
    ) -> TournamentPlan | None:
        tournament = self.get_tournament(tournament_id)
        if tournament is None:
            return None

        coefficients = tuple(
            CoefficientEntry(
                club_id=row.club_id,
                club_name=row.club_name,
                region=row.region,
                total_points=row.total_points,
                recent_season_points=row.recent_season_points,
                previous_season_points=row.previous_season_points,
                winner_seasons=tuple(row.winner_seasons_json or []),
                runner_up_seasons=tuple(row.runner_up_seasons_json or []),
            )
            for row in self._coefficient_rows(tournament.id)
        )
        direct = self._qualified_stage(tournament.id, "direct")
        playoff = self._qualified_stage(tournament.id, "playoff")
        playoff_winners = self._qualified_stage(tournament.id, "playoff_winner")
        main_event = self._qualified_stage(tournament.id, "main_event")
        club_by_id = self._club_map(tournament.id)
        groups = self._groups(tournament.id, club_by_id)
        group_matches = self._group_matches(tournament.id, club_by_id)
        tables = self._standings(tournament.id, club_by_id)
        advancing = tuple(
            row.club for row in sorted(tables, key=lambda item: (item.group_name, item.position)) if row.position <= 2
        )
        knockout = self._knockout(tournament, club_by_id)
        countdown = self._countdown(tournament, reference_at=reference_at)
        return TournamentPlan(
            qualification=QualificationPlan(
                seasons_considered=tuple(int(item) for item in tournament.seasons_considered_json[:2]),
                coefficient_table=coefficients,
                direct_qualifiers=direct,
                playoff_qualifiers=playoff,
                playoff_matches=self._playoff_matches(tournament.id, club_by_id),
                playoff_winners=playoff_winners,
                main_event_clubs=main_event,
            ),
            group_stage=GroupStageSnapshot(
                groups=groups,
                matches=group_matches,
                tables=tables,
                advancing_clubs=advancing,
            ),
            knockout=knockout,
            countdown=countdown,
        )

    def fixtures(self, tournament_id: str | None = None) -> tuple[WorldSuperCupFixtureSnapshot, ...]:
        tournament = self.get_tournament(tournament_id)
        if tournament is None:
            return ()
        club_by_id = self._club_map(tournament.id)
        rows = self._fixture_rows(tournament.id)
        return tuple(self._fixture_snapshot(row, club_by_id) for row in rows)

    def settle_fixture(
        self,
        *,
        fixture_id: str,
        home_score: int,
        away_score: int,
        idempotency_key: str | None = None,
        tournament_id: str | None = None,
        competition_id: str | None = None,
        match_id: str | None = None,
        winner_club_id: str | None = None,
        decided_by: str | None = None,
        completed_at: datetime | None = None,
        metadata: dict | None = None,
    ) -> WorldSuperCupSettlementSnapshot:
        if idempotency_key:
            existing = self.session.scalar(
                select(WorldSuperCupSettlement).where(WorldSuperCupSettlement.idempotency_key == idempotency_key)
            )
            if existing is not None:
                return self._settlement_snapshot(existing)
        if home_score < 0 or away_score < 0:
            raise WorldSuperCupAuthorityError("Fixture scores cannot be negative.")

        fixture = self._fixture_for_settlement(fixture_id=fixture_id, tournament_id=tournament_id)
        if fixture is None:
            raise WorldSuperCupAuthorityError("World Super Cup fixture was not found.")

        lifecycle_match = (
            self._competition_match_for_settlement(
                fixture,
                competition_id=competition_id,
                match_id=match_id,
            )
            if idempotency_key is None or competition_id or match_id
            else None
        )
        resolved_idempotency_key = idempotency_key or self._derive_lifecycle_idempotency_key(
            fixture,
            lifecycle_match,
            completed_at=completed_at,
        )
        existing = self.session.scalar(
            select(WorldSuperCupSettlement).where(WorldSuperCupSettlement.idempotency_key == resolved_idempotency_key)
        )
        if existing is not None:
            return self._settlement_snapshot(existing)

        resolved_winner = self._resolve_winner(fixture, home_score, away_score, winner_club_id)
        resolved_decided_by = decided_by or self._default_decision(home_score, away_score, resolved_winner)
        now = utcnow()
        fixture.home_score = home_score
        fixture.away_score = away_score
        fixture.winner_club_id = resolved_winner
        fixture.decided_by = resolved_decided_by
        fixture.status = "completed"
        fixture.completed_at = now
        fixture.metadata_json = {
            **dict(fixture.metadata_json or {}),
            "last_settlement_idempotency_key": resolved_idempotency_key,
        }
        settlement_metadata = self._settlement_metadata(
            metadata=metadata,
            fixture=fixture,
            lifecycle_match=lifecycle_match,
            competition_id=competition_id,
            match_id=match_id,
            idempotency_key_was_derived=idempotency_key is None,
        )
        settlement = WorldSuperCupSettlement(
            tournament_id=fixture.tournament_id,
            fixture_id=fixture.fixture_id,
            idempotency_key=resolved_idempotency_key,
            home_score=home_score,
            away_score=away_score,
            winner_club_id=resolved_winner,
            decided_by=resolved_decided_by,
            applied_at=now,
            metadata_json=settlement_metadata,
        )
        self.session.add(settlement)
        if fixture.stage == "group" and fixture.group_name:
            self._rebuild_group_standings(fixture.tournament_id, fixture.group_name)
        if fixture.stage == "knockout" and fixture.round_name == "final" and resolved_winner:
            self._sync_finalists(fixture, resolved_winner)
        self.session.flush()
        return self._settlement_snapshot(settlement)

    @staticmethod
    def tournament_id_for_plan(plan: TournamentPlan) -> str:
        return f"world-super-cup-{plan.countdown.starts_at.strftime('%Y%m%d%H%M')}"

    @staticmethod
    def season_label_for_plan(plan: TournamentPlan) -> str:
        seasons = "-".join(str(item) for item in plan.qualification.seasons_considered)
        return f"{seasons}-{plan.countdown.starts_at.strftime('%Y%m%d')}"

    def _projection_exists(self, tournament_id: str) -> bool:
        return bool(
            self.session.scalar(
                select(func.count(WorldSuperCupFixture.id)).where(WorldSuperCupFixture.tournament_id == tournament_id)
            )
        )

    def _clear_projection(self, tournament_id: str) -> None:
        for model in (
            WorldSuperCupCountdown,
            WorldSuperCupCoefficient,
            WorldSuperCupQualifiedClub,
            WorldSuperCupGroup,
            WorldSuperCupFixture,
            WorldSuperCupStanding,
        ):
            self.session.execute(delete(model).where(model.tournament_id == tournament_id))

    def _persist_countdown(self, tournament_id: str, countdown: TournamentCountdown) -> None:
        self.session.add(
            WorldSuperCupCountdown(
                tournament_id=tournament_id,
                tournament_name=countdown.tournament_name,
                starts_at=countdown.starts_at,
                reference_at=countdown.reference_at,
                minutes_until_start=countdown.minutes_until_start,
                pause_policy_json=self._pause_policy_json(countdown.pause_policy),
            )
        )

    def _persist_coefficients(self, tournament_id: str, rows: Iterable[CoefficientEntry]) -> None:
        self.session.add_all(
            WorldSuperCupCoefficient(
                tournament_id=tournament_id,
                ranking=index,
                club_id=row.club_id,
                club_name=row.club_name,
                region=row.region,
                total_points=row.total_points,
                recent_season_points=row.recent_season_points,
                previous_season_points=row.previous_season_points,
                winner_seasons_json=list(row.winner_seasons),
                runner_up_seasons_json=list(row.runner_up_seasons),
            )
            for index, row in enumerate(rows, start=1)
        )

    def _persist_qualified_clubs(
        self,
        tournament_id: str,
        stage: str,
        clubs: Iterable[QualifiedClub],
    ) -> None:
        self.session.add_all(
            WorldSuperCupQualifiedClub(
                tournament_id=tournament_id,
                qualification_stage=stage,
                display_order=index,
                club_id=club.club_id,
                club_name=club.club_name,
                region=club.region,
                qualification_path=club.qualification_path,
                coefficient_points=club.coefficient_points,
                regional_seed=club.regional_seed,
                overall_seed=club.overall_seed,
            )
            for index, club in enumerate(clubs, start=1)
        )

    def _persist_groups(self, tournament_id: str, groups: Iterable[Group]) -> None:
        self.session.add_all(
            WorldSuperCupGroup(
                tournament_id=tournament_id,
                group_name=group.group_name,
                display_order=index,
                club_ids_json=[club.club_id for club in group.clubs],
            )
            for index, group in enumerate(groups, start=1)
        )

    def _persist_fixtures(self, tournament_id: str, plan: TournamentPlan) -> None:
        sequence = 1
        fixtures: list[WorldSuperCupFixture] = []
        for match in plan.qualification.playoff_matches:
            fixtures.append(self._fixture_row(tournament_id, match, sequence, stage="playoff", requires_winner=True))
            sequence += 1
        for match in plan.group_stage.matches:
            fixtures.append(self._fixture_row(tournament_id, match, sequence, stage="group", requires_winner=False))
            sequence += 1
        for round_view in plan.knockout.rounds:
            for match in round_view.matches:
                fixtures.append(
                    self._fixture_row(tournament_id, match, sequence, stage="knockout", requires_winner=True)
                )
                sequence += 1
        self.session.add_all(fixtures)

    def _fixture_row(
        self,
        tournament_id: str,
        match: PlayoffMatch | GroupMatch | KnockoutMatch,
        sequence: int,
        *,
        stage: str,
        requires_winner: bool,
    ) -> WorldSuperCupFixture:
        winner = getattr(match, "winner", None)
        home_score = getattr(match, "home_score", None)
        away_score = getattr(match, "away_score", None)
        return WorldSuperCupFixture(
            tournament_id=tournament_id,
            fixture_id=match.match_id,
            stage=stage,
            round_name=getattr(match, "round_name", None) or getattr(match, "stage", None),
            group_name=getattr(match, "group_name", None),
            matchday=getattr(match, "matchday", None),
            sequence=sequence,
            home_club_id=match.home_club.club_id,
            away_club_id=match.away_club.club_id,
            kickoff_at=match.kickoff_at,
            venue=match.venue,
            status="completed" if home_score is not None and away_score is not None else "scheduled",
            home_score=home_score,
            away_score=away_score,
            winner_club_id=winner.club_id if winner is not None else None,
            decided_by=getattr(match, "decided_by", None),
            requires_winner=requires_winner,
            completed_at=utcnow() if home_score is not None and away_score is not None else None,
        )

    def _persist_standings(self, tournament_id: str, rows: Iterable[GroupStanding]) -> None:
        self.session.add_all(self._standing_row(tournament_id, row) for row in rows)

    def _standing_row(self, tournament_id: str, row: GroupStanding) -> WorldSuperCupStanding:
        return WorldSuperCupStanding(
            tournament_id=tournament_id,
            group_name=row.group_name,
            position=row.position,
            club_id=row.club.club_id,
            played=row.played,
            wins=row.wins,
            draws=row.draws,
            losses=row.losses,
            goals_for=row.goals_for,
            goals_against=row.goals_against,
            goal_difference=row.goal_difference,
            points=row.points,
        )

    def _coefficient_rows(self, tournament_id: str) -> tuple[WorldSuperCupCoefficient, ...]:
        return tuple(
            self.session.scalars(
                select(WorldSuperCupCoefficient)
                .where(WorldSuperCupCoefficient.tournament_id == tournament_id)
                .order_by(WorldSuperCupCoefficient.ranking.asc())
            )
        )

    def _qualified_rows(self, tournament_id: str) -> tuple[WorldSuperCupQualifiedClub, ...]:
        return tuple(
            self.session.scalars(
                select(WorldSuperCupQualifiedClub)
                .where(WorldSuperCupQualifiedClub.tournament_id == tournament_id)
                .order_by(
                    WorldSuperCupQualifiedClub.qualification_stage.asc(),
                    WorldSuperCupQualifiedClub.display_order.asc(),
                )
            )
        )

    def _qualified_stage(self, tournament_id: str, stage: str) -> tuple[QualifiedClub, ...]:
        return tuple(
            self._club_from_row(row)
            for row in self.session.scalars(
                select(WorldSuperCupQualifiedClub)
                .where(
                    WorldSuperCupQualifiedClub.tournament_id == tournament_id,
                    WorldSuperCupQualifiedClub.qualification_stage == stage,
                )
                .order_by(WorldSuperCupQualifiedClub.display_order.asc())
            )
        )

    def _club_map(self, tournament_id: str) -> dict[str, QualifiedClub]:
        priority = {"playoff": 1, "direct": 2, "playoff_winner": 3, "main_event": 4}
        rows = sorted(
            self._qualified_rows(tournament_id),
            key=lambda row: (priority.get(row.qualification_stage, 0), row.display_order),
        )
        return {row.club_id: self._club_from_row(row) for row in rows}

    def _groups(self, tournament_id: str, club_by_id: dict[str, QualifiedClub]) -> tuple[Group, ...]:
        return tuple(
            Group(
                group_name=row.group_name,
                clubs=tuple(club_by_id[club_id] for club_id in row.club_ids_json if club_id in club_by_id),
            )
            for row in self.session.scalars(
                select(WorldSuperCupGroup)
                .where(WorldSuperCupGroup.tournament_id == tournament_id)
                .order_by(WorldSuperCupGroup.display_order.asc())
            )
        )

    def _fixture_rows(self, tournament_id: str) -> tuple[WorldSuperCupFixture, ...]:
        return tuple(
            self.session.scalars(
                select(WorldSuperCupFixture)
                .where(WorldSuperCupFixture.tournament_id == tournament_id)
                .order_by(WorldSuperCupFixture.sequence.asc())
            )
        )

    def _playoff_matches(
        self,
        tournament_id: str,
        club_by_id: dict[str, QualifiedClub],
    ) -> tuple[PlayoffMatch, ...]:
        return tuple(
            PlayoffMatch(
                match_id=row.fixture_id,
                stage=row.round_name or "playoff",
                home_club=club_by_id[row.home_club_id],
                away_club=club_by_id[row.away_club_id],
                kickoff_at=row.kickoff_at,
                venue=row.venue,
                winner=club_by_id.get(row.winner_club_id or ""),
                decided_by=row.decided_by,
                home_score=row.home_score,
                away_score=row.away_score,
            )
            for row in self._fixture_rows(tournament_id)
            if row.stage == "playoff"
        )

    def _group_matches(
        self,
        tournament_id: str,
        club_by_id: dict[str, QualifiedClub],
    ) -> tuple[GroupMatch, ...]:
        return tuple(
            GroupMatch(
                match_id=row.fixture_id,
                group_name=row.group_name or "",
                matchday=row.matchday or 0,
                home_club=club_by_id[row.home_club_id],
                away_club=club_by_id[row.away_club_id],
                kickoff_at=row.kickoff_at,
                venue=row.venue,
                home_score=row.home_score,
                away_score=row.away_score,
            )
            for row in self._fixture_rows(tournament_id)
            if row.stage == "group"
        )

    def _standings(
        self,
        tournament_id: str,
        club_by_id: dict[str, QualifiedClub],
    ) -> tuple[GroupStanding, ...]:
        return tuple(
            GroupStanding(
                group_name=row.group_name,
                position=row.position,
                club=club_by_id[row.club_id],
                played=row.played,
                wins=row.wins,
                draws=row.draws,
                losses=row.losses,
                goals_for=row.goals_for,
                goals_against=row.goals_against,
                goal_difference=row.goal_difference,
                points=row.points,
            )
            for row in self.session.scalars(
                select(WorldSuperCupStanding)
                .where(WorldSuperCupStanding.tournament_id == tournament_id)
                .order_by(WorldSuperCupStanding.group_name.asc(), WorldSuperCupStanding.position.asc())
            )
        )

    def _knockout(
        self,
        tournament: WorldSuperCupTournament,
        club_by_id: dict[str, QualifiedClub],
    ) -> KnockoutBracket:
        grouped: dict[str, list[KnockoutMatch]] = {}
        for row in self._fixture_rows(tournament.id):
            if row.stage != "knockout" or not row.round_name:
                continue
            grouped.setdefault(row.round_name, []).append(
                KnockoutMatch(
                    match_id=row.fixture_id,
                    round_name=row.round_name,
                    home_club=club_by_id[row.home_club_id],
                    away_club=club_by_id[row.away_club_id],
                    kickoff_at=row.kickoff_at,
                    venue=row.venue,
                    winner=club_by_id.get(row.winner_club_id or ""),
                    decided_by=row.decided_by,
                    home_score=row.home_score,
                    away_score=row.away_score,
                )
            )
        round_order = ("round_of_16", "quarterfinal", "semifinal", "final")
        rounds = tuple(
            KnockoutRound(round_name=round_name, matches=tuple(grouped[round_name]))
            for round_name in round_order
            if round_name in grouped
        )
        champion = club_by_id.get(tournament.champion_club_id or "")
        runner_up = club_by_id.get(tournament.runner_up_club_id or "")
        if champion is None or runner_up is None:
            final = grouped.get("final", [])
            if final and final[0].winner is not None:
                champion = final[0].winner
                runner_up = final[0].away_club if champion.club_id == final[0].home_club.club_id else final[0].home_club
        if champion is None or runner_up is None:
            raise WorldSuperCupAuthorityError("Persisted World Super Cup bracket is missing final authority.")
        return KnockoutBracket(
            rounds=rounds,
            champion=champion,
            runner_up=runner_up,
            ceremony=self._ceremony_from_json(tournament.ceremony_json),
        )

    def _countdown(
        self,
        tournament: WorldSuperCupTournament,
        *,
        reference_at: datetime | None,
    ) -> TournamentCountdown:
        countdown = self.session.scalar(
            select(WorldSuperCupCountdown).where(WorldSuperCupCountdown.tournament_id == tournament.id)
        )
        if countdown is None:
            pause_policy = PausePolicy((), (), "")
            starts_at = self._as_utc(tournament.starts_at)
            stored_reference = self._as_utc(tournament.reference_at or utcnow())
            minutes_until_start = max(int((starts_at - stored_reference).total_seconds() // 60), 0)
            return TournamentCountdown(
                tournament_name=tournament.tournament_name,
                starts_at=starts_at,
                reference_at=stored_reference,
                minutes_until_start=minutes_until_start,
                pause_policy=pause_policy,
            )
        starts_at = self._as_utc(countdown.starts_at)
        resolved_reference = self._as_utc(reference_at or countdown.reference_at).replace(microsecond=0)
        minutes_until_start = max(int((starts_at - resolved_reference).total_seconds() // 60), 0)
        return TournamentCountdown(
            tournament_name=countdown.tournament_name,
            starts_at=starts_at,
            reference_at=resolved_reference,
            minutes_until_start=minutes_until_start,
            pause_policy=self._pause_policy_from_json(countdown.pause_policy_json),
        )

    def _fixture_snapshot(
        self,
        row: WorldSuperCupFixture,
        club_by_id: dict[str, QualifiedClub],
    ) -> WorldSuperCupFixtureSnapshot:
        return WorldSuperCupFixtureSnapshot(
            tournament_id=row.tournament_id,
            fixture_id=row.fixture_id,
            stage=row.stage,
            round_name=row.round_name,
            group_name=row.group_name,
            matchday=row.matchday,
            home_club=club_by_id[row.home_club_id],
            away_club=club_by_id[row.away_club_id],
            kickoff_at=row.kickoff_at,
            venue=row.venue,
            status=row.status,
            home_score=row.home_score,
            away_score=row.away_score,
            winner=club_by_id.get(row.winner_club_id or ""),
            decided_by=row.decided_by,
        )

    def _settlement_snapshot(self, row: WorldSuperCupSettlement) -> WorldSuperCupSettlementSnapshot:
        club_by_id = self._club_map(row.tournament_id)
        fixture = self._fixture_for_settlement(fixture_id=row.fixture_id, tournament_id=row.tournament_id)
        metadata = dict(row.metadata_json or {})
        return WorldSuperCupSettlementSnapshot(
            tournament_id=row.tournament_id,
            fixture_id=row.fixture_id,
            idempotency_key=row.idempotency_key,
            status=fixture.status if fixture is not None else "completed",
            home_score=row.home_score,
            away_score=row.away_score,
            winner=club_by_id.get(row.winner_club_id or ""),
            decided_by=row.decided_by,
            applied_at=row.applied_at,
            lifecycle_match_id=metadata.get("lifecycle_match_id"),
            lifecycle_competition_id=metadata.get("lifecycle_competition_id"),
            idempotency_source=str(metadata.get("idempotency_source") or "explicit_key"),
        )

    def _fixture_for_settlement(
        self,
        *,
        fixture_id: str,
        tournament_id: str | None,
    ) -> WorldSuperCupFixture | None:
        query = select(WorldSuperCupFixture).where(WorldSuperCupFixture.fixture_id == fixture_id)
        if tournament_id:
            query = query.where(WorldSuperCupFixture.tournament_id == tournament_id)
        return self.session.scalar(query.order_by(WorldSuperCupFixture.created_at.desc()))

    def _competition_match_for_settlement(
        self,
        fixture: WorldSuperCupFixture,
        *,
        competition_id: str | None,
        match_id: str | None,
    ) -> CompetitionMatch | None:
        candidate_ids = tuple(dict.fromkeys(item for item in (match_id, fixture.fixture_id) if item))
        tournament = self.session.get(WorldSuperCupTournament, fixture.tournament_id)
        expected_competition_id = competition_id or (tournament.competition_id if tournament is not None else None)
        for candidate_id in candidate_ids:
            row = self.session.get(CompetitionMatch, candidate_id)
            if row is None:
                continue
            if expected_competition_id and row.competition_id != expected_competition_id:
                raise WorldSuperCupAuthorityError(
                    "World Super Cup settlement match lifecycle does not belong to the requested competition."
                )
            return row
        return None

    def _derive_lifecycle_idempotency_key(
        self,
        fixture: WorldSuperCupFixture,
        lifecycle_match: CompetitionMatch | None,
        *,
        completed_at: datetime | None,
    ) -> str:
        if lifecycle_match is None:
            raise WorldSuperCupAuthorityError(
                "World Super Cup settlement idempotency key is required when no Competition OS match lifecycle row is available."
            )
        lifecycle_completed_at = lifecycle_match.completed_at or completed_at
        if lifecycle_completed_at is None:
            raise WorldSuperCupAuthorityError(
                "World Super Cup lifecycle-derived settlement idempotency requires a completed match timestamp."
            )
        completed_marker = self._as_utc(lifecycle_completed_at).replace(microsecond=0).isoformat()
        return (
            "competition-os:match-completed:"
            f"{lifecycle_match.competition_id}:{lifecycle_match.id}:{completed_marker}:{fixture.tournament_id}"
        )

    def _settlement_metadata(
        self,
        *,
        metadata: dict | None,
        fixture: WorldSuperCupFixture,
        lifecycle_match: CompetitionMatch | None,
        competition_id: str | None,
        match_id: str | None,
        idempotency_key_was_derived: bool,
    ) -> dict:
        resolved = dict(metadata or {})
        if lifecycle_match is not None:
            resolved.update(
                {
                    "lifecycle_match_id": lifecycle_match.id,
                    "lifecycle_competition_id": lifecycle_match.competition_id,
                    "idempotency_source": (
                        "competition_match_lifecycle" if idempotency_key_was_derived else "explicit_key"
                    ),
                }
            )
        else:
            resolved.setdefault("lifecycle_match_id", match_id or fixture.fixture_id)
            if competition_id:
                resolved.setdefault("lifecycle_competition_id", competition_id)
            resolved.setdefault("idempotency_source", "explicit_key")
        return resolved

    def _resolve_winner(
        self,
        fixture: WorldSuperCupFixture,
        home_score: int,
        away_score: int,
        winner_club_id: str | None,
    ) -> str | None:
        valid_ids = {fixture.home_club_id, fixture.away_club_id}
        if winner_club_id is not None and winner_club_id not in valid_ids:
            raise WorldSuperCupAuthorityError("Fixture winner must be one of the two fixture clubs.")
        if home_score > away_score:
            return fixture.home_club_id
        if away_score > home_score:
            return fixture.away_club_id
        if fixture.requires_winner:
            if winner_club_id is None:
                raise WorldSuperCupAuthorityError("Knockout World Super Cup fixtures require a winner.")
            return winner_club_id
        return winner_club_id

    @staticmethod
    def _default_decision(home_score: int, away_score: int, winner_club_id: str | None) -> str | None:
        if home_score != away_score:
            return "regulation"
        if winner_club_id is not None:
            return "penalties"
        return None

    def _rebuild_group_standings(self, tournament_id: str, group_name: str) -> None:
        group = self.session.scalar(
            select(WorldSuperCupGroup).where(
                WorldSuperCupGroup.tournament_id == tournament_id,
                WorldSuperCupGroup.group_name == group_name,
            )
        )
        if group is None:
            return
        club_by_id = self._club_map(tournament_id)
        stats = {
            club_id: {
                "club": club_by_id[club_id],
                "played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "points": 0,
            }
            for club_id in group.club_ids_json
            if club_id in club_by_id
        }
        matches = self.session.scalars(
            select(WorldSuperCupFixture).where(
                WorldSuperCupFixture.tournament_id == tournament_id,
                WorldSuperCupFixture.stage == "group",
                WorldSuperCupFixture.group_name == group_name,
                WorldSuperCupFixture.status == "completed",
            )
        )
        for match in matches:
            if match.home_score is None or match.away_score is None:
                continue
            home = stats[match.home_club_id]
            away = stats[match.away_club_id]
            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += match.home_score
            home["goals_against"] += match.away_score
            away["goals_for"] += match.away_score
            away["goals_against"] += match.home_score
            if match.home_score > match.away_score:
                home["wins"] += 1
                away["losses"] += 1
                home["points"] += 3
            elif match.away_score > match.home_score:
                away["wins"] += 1
                home["losses"] += 1
                away["points"] += 3
            else:
                home["draws"] += 1
                away["draws"] += 1
                home["points"] += 1
                away["points"] += 1

        rows = sorted(
            stats.values(),
            key=lambda row: (
                -int(row["points"]),
                -(int(row["goals_for"]) - int(row["goals_against"])),
                -int(row["goals_for"]),
                -row["club"].coefficient_points,
                row["club"].club_name,
            ),
        )
        self.session.execute(
            delete(WorldSuperCupStanding).where(
                WorldSuperCupStanding.tournament_id == tournament_id,
                WorldSuperCupStanding.group_name == group_name,
            )
        )
        self.session.add_all(
            self._standing_row(
                tournament_id,
                GroupStanding(
                    group_name=group_name,
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
                ),
            )
            for position, row in enumerate(rows, start=1)
        )

    def _sync_finalists(self, fixture: WorldSuperCupFixture, winner_club_id: str) -> None:
        tournament = self.session.get(WorldSuperCupTournament, fixture.tournament_id)
        if tournament is None:
            return
        tournament.champion_club_id = winner_club_id
        tournament.runner_up_club_id = (
            fixture.away_club_id if winner_club_id == fixture.home_club_id else fixture.home_club_id
        )
        tournament.status = "completed"

    @staticmethod
    def _club_from_row(row: WorldSuperCupQualifiedClub) -> QualifiedClub:
        return QualifiedClub(
            club_id=row.club_id,
            club_name=row.club_name,
            region=row.region,
            qualification_path=row.qualification_path,
            coefficient_points=row.coefficient_points,
            regional_seed=row.regional_seed,
            overall_seed=row.overall_seed,
        )

    @staticmethod
    def _pause_policy_json(pause_policy: PausePolicy) -> dict:
        return {
            "paused_competitions": list(pause_policy.paused_competitions),
            "active_competitions": list(pause_policy.active_competitions),
            "cadence_description": pause_policy.cadence_description,
        }

    @staticmethod
    def _pause_policy_from_json(payload: dict) -> PausePolicy:
        return PausePolicy(
            paused_competitions=tuple(payload.get("paused_competitions") or ()),
            active_competitions=tuple(payload.get("active_competitions") or ()),
            cadence_description=str(payload.get("cadence_description") or ""),
        )

    @staticmethod
    def _ceremony_json(ceremony: TrophyCeremonyMetadata) -> dict:
        return {
            "trophy_name": ceremony.trophy_name,
            "host_city": ceremony.host_city,
            "presentation_minutes": ceremony.presentation_minutes,
            "award_sequence": list(ceremony.award_sequence),
            "confetti_colors": list(ceremony.confetti_colors),
            "no_extra_time": ceremony.no_extra_time,
            "penalties_if_tied": ceremony.penalties_if_tied,
        }

    @staticmethod
    def _ceremony_from_json(payload: dict) -> TrophyCeremonyMetadata:
        return TrophyCeremonyMetadata(
            trophy_name=str(payload.get("trophy_name") or "GTEX World Super Cup"),
            host_city=str(payload.get("host_city") or "GTEX Global Hub"),
            presentation_minutes=int(payload.get("presentation_minutes") or 15),
            award_sequence=tuple(payload.get("award_sequence") or ()),
            confetti_colors=tuple(payload.get("confetti_colors") or ()),
            no_extra_time=bool(payload.get("no_extra_time", True)),
            penalties_if_tied=bool(payload.get("penalties_if_tied", True)),
        )

    @staticmethod
    def _latest_fixture_time(plan: TournamentPlan) -> datetime | None:
        kickoffs = [
            match.kickoff_at
            for match in (
                *plan.qualification.playoff_matches,
                *plan.group_stage.matches,
                *(match for round_view in plan.knockout.rounds for match in round_view.matches),
            )
        ]
        if not kickoffs:
            return None
        return max(kickoffs)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
