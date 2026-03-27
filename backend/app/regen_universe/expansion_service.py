from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from itertools import combinations
from random import Random
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ingestion.models import Competition, Match, Player, PlayerMatchStat
from app.match_engine.schemas import (
    MatchClubContextInput,
    MatchCompetitionContextInput,
    MatchPlayerInput,
    MatchSimulationRequest,
    MatchTeamInput,
    TeamTacticalPlanInput,
)
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import MatchCompetitionType, PlayerRole, TacticalStyle
from app.models.academy_player import AcademyPlayer
from app.models.club_profile import ClubProfile
from app.models.competition_match_event import CompetitionMatchEvent
from app.models.notification_record import NotificationRecord
from app.models.player_career_entry import PlayerCareerEntry
from app.models.player_lifecycle_event import PlayerLifecycleEvent
from app.models.player_rivalry import PlayerRivalry
from app.models.player_story import PlayerStory
from app.models.regen import RegenLegacyRecord, RegenProfile
from app.models.youth_tournament import YouthTournament
from app.regen_universe.dna import (
    chemistry_fit_score,
    evolve_dna_profile,
    generate_dna_profile,
    growth_bias_multiplier,
    match_attribute_adjustments,
    normalize_dna_profile,
)
from app.regen_universe.models import RegenAwardWinner
from app.story_feed_engine.service import StoryFeedService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _position_text(player: Player | None, regen: RegenProfile | None = None) -> str:
    if regen is not None and regen.primary_position:
        return regen.primary_position
    return player.normalized_position or player.position or "midfielder" if player is not None else "midfielder"


def _position_group(position: str | None) -> str:
    resolved = (position or "").strip().lower()
    if "goal" in resolved or resolved in {"gk"}:
        return "goalkeeper"
    if any(token in resolved for token in ("back", "def", "cb", "rb", "lb", "wb")):
        return "defender"
    if any(token in resolved for token in ("mid", "cm", "dm", "am", "wing")):
        return "midfielder"
    return "forward"


def _resolve_role(position: str | None) -> PlayerRole:
    group = _position_group(position)
    if group == "goalkeeper":
        return PlayerRole.GOALKEEPER
    if group == "defender":
        return PlayerRole.DEFENDER
    if group == "midfielder":
        return PlayerRole.MIDFIELDER
    return PlayerRole.FORWARD


def _parse_age_limit(age_limit: str) -> int:
    value = "".join(ch for ch in age_limit if ch.isdigit())
    if not value:
        raise ValueError("invalid_age_limit")
    return int(value)


def _player_age(player: Player, *, today: date | None = None) -> int:
    current = today or date.today()
    if player.date_of_birth is None:
        return 18
    years = current.year - player.date_of_birth.year
    if (current.month, current.day) < (player.date_of_birth.month, player.date_of_birth.day):
        years -= 1
    return max(0, years)


def _surname(name: str) -> str:
    parts = [part for part in name.split() if part]
    return parts[-1][:16].upper() if parts else name[:16].upper()


def _match_occurred_on(match: Match) -> date | None:
    return match.kickoff_at.date() if match.kickoff_at is not None else None


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


@dataclass(slots=True)
class _TournamentPlayerSeed:
    source_type: str
    entity_id: str
    player_id: str | None
    display_name: str
    age: int
    position: str
    overall: int
    team_id: str | None
    market_value: float
    dna_profile: dict[str, Any]


class RegenUniverseExpansionError(ValueError):
    pass


class RegenUniverseExpansionNotFoundError(RegenUniverseExpansionError):
    pass


class RegenUniverseExpansionValidationError(RegenUniverseExpansionError):
    pass


class RegenUniverseExpansionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.match_service = MatchSimulationService()

    def get_player_story(self, player_id: str) -> dict[str, Any]:
        story = self.session.scalar(select(PlayerStory).where(PlayerStory.player_id == player_id))
        if story is None:
            story = self.refresh_story(player_id, trigger="on_demand", notify=False, publish=False)
        return self._story_view(story)

    def refresh_story(
        self,
        player_id: str,
        *,
        trigger: str,
        notify: bool = True,
        publish: bool = True,
    ) -> PlayerStory:
        player = self._require_player(player_id)
        story = self.session.scalar(select(PlayerStory).where(PlayerStory.player_id == player_id))
        if story is None:
            story = PlayerStory(player_id=player_id)
            self.session.add(story)
        payload = _json_safe(self._compose_story(player))
        story.chapters = payload
        story.narrative_score = float(payload["narrative_score"])
        self.session.flush()
        if publish and trigger in {"breakout_event", "major_trophy_win", "rivalry_peak", "retirement"}:
            StoryFeedService(self.session).publish(
                story_type="documentary",
                title=f"{player.full_name}: documentary chapter updated",
                body=payload["chapters"][0]["summary"] if payload.get("chapters") else f"New story beats were recorded for {player.full_name}.",
                audience="public",
                subject_type="player",
                subject_id=player.id,
                metadata_json={"trigger": trigger, "narrative_score": story.narrative_score},
                featured=story.narrative_score >= 65,
            )
        if notify:
            self._notify_player_owners(
                player,
                template_key="STORY_UPDATED",
                topic="documentary",
                message=f"{player.full_name}'s documentary story was updated.",
                resource_type="player_story",
                resource_id=story.id,
                metadata={"trigger": trigger, "player_id": player.id},
            )
        return story

    def get_player_dna(self, player_id: str) -> dict[str, Any]:
        player = self._require_player(player_id)
        regen = self._get_regen_profile(player_id)
        dna_profile = self._ensure_player_dna(player, regen=regen)
        return {
            "player_id": player.id,
            "archetype": dna_profile["archetype"],
            "traits": {
                "tempo": dna_profile["tempo"],
                "risk_taking": dna_profile["risk_taking"],
                "creativity": dna_profile["creativity"],
                "discipline": dna_profile["discipline"],
            },
            "evolution": list(dna_profile.get("evolution", [])),
        }

    def evolve_dna_profiles(self, *, player_id: str | None = None) -> dict[str, Any]:
        players = [self._require_player(player_id)] if player_id else list(
            self.session.scalars(select(Player).where(Player.source_provider == "gtex_regen")).all()
        )
        updated = 0
        for player in players:
            current = self._ensure_player_dna(player, regen=self._get_regen_profile(player.id))
            evolved = evolve_dna_profile(current, position=_position_text(player), reason="role_alignment")
            if evolved != current:
                player.dna_profile = evolved
                updated += 1
        self.session.flush()
        return {"players_scanned": len(players), "players_updated": updated}

    def regenerate_stories(self, *, player_id: str | None = None) -> dict[str, Any]:
        players = [self._require_player(player_id)] if player_id else list(
            self.session.scalars(select(Player).where(Player.source_provider == "gtex_regen")).all()
        )
        count = 0
        for player in players:
            self.refresh_story(player.id, trigger="manual", notify=False, publish=False)
            count += 1
        self.session.flush()
        return {"stories_regenerated": count}

    def list_player_rivalries(self, player_id: str, *, limit: int = 10) -> list[dict[str, Any]]:
        self._require_player(player_id)
        rivalries = list(
            self.session.scalars(
                select(PlayerRivalry)
                .where(or_(PlayerRivalry.player_a_id == player_id, PlayerRivalry.player_b_id == player_id))
                .order_by(PlayerRivalry.intensity_score.desc(), PlayerRivalry.updated_at.desc())
                .limit(limit)
            ).all()
        )
        if not rivalries:
            return []
        player_ids = {
            item
            for rivalry in rivalries
            for item in (rivalry.player_a_id, rivalry.player_b_id)
        }
        players = {
            player.id: player
            for player in self.session.scalars(select(Player).where(Player.id.in_(player_ids))).all()
        }
        club_ids = {player.current_club_profile_id for player in players.values() if player.current_club_profile_id}
        clubs = {
            club.id: club
            for club in self.session.scalars(select(ClubProfile).where(ClubProfile.id.in_(club_ids))).all()
        }
        views: list[dict[str, Any]] = []
        for rivalry in rivalries:
            left = players.get(rivalry.player_a_id)
            right = players.get(rivalry.player_b_id)
            if left is None or right is None:
                continue
            views.append(
                {
                    "id": rivalry.id,
                    "intensity_score": round(float(rivalry.intensity_score), 2),
                    "players": [
                        {
                            "player_id": left.id,
                            "player_name": left.full_name,
                            "club_id": left.current_club_profile_id,
                            "club_name": clubs.get(left.current_club_profile_id).club_name if left.current_club_profile_id in clubs else None,
                            "position": left.normalized_position or left.position,
                        },
                        {
                            "player_id": right.id,
                            "player_name": right.full_name,
                            "club_id": right.current_club_profile_id,
                            "club_name": clubs.get(right.current_club_profile_id).club_name if right.current_club_profile_id in clubs else None,
                            "position": right.normalized_position or right.position,
                        },
                    ],
                    "history": dict(rivalry.history_json or {}),
                    "stats_comparison": dict((rivalry.history_json or {}).get("stats_comparison", {})),
                }
            )
        return views

    def detect_rivalries(self, *, player_id: str | None = None) -> dict[str, Any]:
        query = select(PlayerMatchStat, Player, Match).join(Player, Player.id == PlayerMatchStat.player_id).join(Match, Match.id == PlayerMatchStat.match_id)
        if player_id:
            match_ids = list(
                self.session.scalars(select(PlayerMatchStat.match_id).where(PlayerMatchStat.player_id == player_id)).all()
            )
            if not match_ids:
                return {"pairs_scanned": 0, "rivalries_updated": 0}
            query = query.where(PlayerMatchStat.match_id.in_(match_ids))
        rows = list(self.session.execute(query).all())
        if not rows:
            return {"pairs_scanned": 0, "rivalries_updated": 0}

        by_match: dict[str, list[tuple[PlayerMatchStat, Player, Match]]] = defaultdict(list)
        for stat, player, match in rows:
            by_match[match.id].append((stat, player, match))

        buckets: dict[tuple[str, str], dict[str, Any]] = {}
        for match_rows in by_match.values():
            for left, right in combinations(match_rows, 2):
                stat_a, player_a, match = left
                stat_b, player_b, _ = right
                if stat_a.club_id is not None and stat_a.club_id == stat_b.club_id:
                    continue
                pair = tuple(sorted((player_a.id, player_b.id)))
                bucket = buckets.setdefault(
                    pair,
                    {
                        "player_a_id": pair[0],
                        "player_b_id": pair[1],
                        "matchup_count": 0,
                        "shared_position_group": 0,
                        "goals": {pair[0]: 0, pair[1]: 0},
                        "wins": {pair[0]: 0, pair[1]: 0},
                        "draws": 0,
                        "rating_total": {pair[0]: 0.0, pair[1]: 0.0},
                        "rating_count": {pair[0]: 0, pair[1]: 0},
                        "major_clashes": 0,
                        "latest_match_date": _match_occurred_on(match),
                    },
                )
                bucket["matchup_count"] += 1
                if _position_group(player_a.normalized_position or player_a.position) == _position_group(player_b.normalized_position or player_b.position):
                    bucket["shared_position_group"] += 1
                bucket["goals"][player_a.id] += int(stat_a.goals or 0)
                bucket["goals"][player_b.id] += int(stat_b.goals or 0)
                if stat_a.rating is not None:
                    bucket["rating_total"][player_a.id] += float(stat_a.rating)
                    bucket["rating_count"][player_a.id] += 1
                if stat_b.rating is not None:
                    bucket["rating_total"][player_b.id] += float(stat_b.rating)
                    bucket["rating_count"][player_b.id] += 1
                match_date = _match_occurred_on(match)
                if match_date and (bucket["latest_match_date"] is None or match_date > bucket["latest_match_date"]):
                    bucket["latest_match_date"] = match_date
                if stat_a.club_id == match.home_club_id:
                    score_a, score_b = match.home_score, match.away_score
                else:
                    score_a, score_b = match.away_score, match.home_score
                if score_a > score_b:
                    bucket["wins"][player_a.id] += 1
                elif score_b > score_a:
                    bucket["wins"][player_b.id] += 1
                else:
                    bucket["draws"] += 1

        candidate_ids = {entry for pair in buckets for entry in pair}
        if candidate_ids:
            events = list(
                self.session.scalars(
                    select(CompetitionMatchEvent).where(
                        or_(
                            CompetitionMatchEvent.player_id.in_(candidate_ids),
                            CompetitionMatchEvent.secondary_player_id.in_(candidate_ids),
                        )
                    )
                ).all()
            )
            for event in events:
                if not event.player_id or not event.secondary_player_id:
                    continue
                pair = tuple(sorted((event.player_id, event.secondary_player_id)))
                bucket = buckets.get(pair)
                if bucket is None:
                    continue
                if event.event_type in {"goal", "red_card", "yellow_card", "foul"}:
                    bucket["major_clashes"] += 1

        updated = 0
        for pair, bucket in buckets.items():
            shared_ratio = bucket["shared_position_group"] / max(bucket["matchup_count"], 1)
            rating_a = bucket["rating_total"][pair[0]] / max(bucket["rating_count"][pair[0]], 1)
            rating_b = bucket["rating_total"][pair[1]] / max(bucket["rating_count"][pair[1]], 1)
            rating_overlap = max(0.0, 1.0 - (abs(rating_a - rating_b) / 3.0))
            goal_gap = abs(bucket["goals"][pair[0]] - bucket["goals"][pair[1]])
            scoring_overlap = max(0.0, 1.0 - min(goal_gap / 6.0, 1.0))
            intensity = min(
                100.0,
                (bucket["matchup_count"] * 12.0)
                + (shared_ratio * 18.0)
                + (rating_overlap * 20.0)
                + (scoring_overlap * 16.0)
                + min(bucket["major_clashes"] * 4.0, 18.0),
            )
            if intensity < 25.0:
                continue
            rivalry = self.session.scalar(
                select(PlayerRivalry).where(
                    PlayerRivalry.player_a_id == pair[0],
                    PlayerRivalry.player_b_id == pair[1],
                )
            )
            previous_intensity = rivalry.intensity_score if rivalry is not None else 0.0
            if rivalry is None:
                rivalry = PlayerRivalry(player_a_id=pair[0], player_b_id=pair[1])
                self.session.add(rivalry)
            rivalry.intensity_score = round(intensity, 2)
            rivalry.history_json = {
                "matchup_count": bucket["matchup_count"],
                "wins": bucket["wins"],
                "draws": bucket["draws"],
                "goals_against_rival": bucket["goals"],
                "major_clashes": bucket["major_clashes"],
                "latest_match_date": bucket["latest_match_date"].isoformat() if bucket["latest_match_date"] else None,
                "stats_comparison": {
                    "average_rating": {
                        pair[0]: round(rating_a, 2) if bucket["rating_count"][pair[0]] else None,
                        pair[1]: round(rating_b, 2) if bucket["rating_count"][pair[1]] else None,
                    },
                    "goals": bucket["goals"],
                },
            }
            updated += 1
            if previous_intensity < 70 <= rivalry.intensity_score:
                for rival_player_id in pair:
                    player = self._require_player(rival_player_id)
                    self._notify_player_owners(
                        player,
                        template_key="RIVALRY_HEATING_UP",
                        topic="rivalry",
                        message=f"{player.full_name} is at the center of a defining rivalry.",
                        resource_type="player_rivalry",
                        resource_id=rivalry.id,
                        metadata={"player_id": player.id, "intensity_score": rivalry.intensity_score},
                    )
                    self.refresh_story(player.id, trigger="rivalry_peak", notify=False, publish=True)
        self.session.flush()
        return {"pairs_scanned": len(buckets), "rivalries_updated": updated}

    def list_youth_tournaments(self, *, status: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        stmt = select(YouthTournament).order_by(YouthTournament.start_date.desc(), YouthTournament.created_at.desc()).limit(limit)
        if status:
            stmt = (
                select(YouthTournament)
                .where(YouthTournament.status == status)
                .order_by(YouthTournament.start_date.desc(), YouthTournament.created_at.desc())
                .limit(limit)
            )
        return [self._tournament_view(item) for item in self.session.scalars(stmt).all()]

    def get_youth_tournament(self, tournament_id: str) -> dict[str, Any]:
        tournament = self.session.get(YouthTournament, tournament_id)
        if tournament is None:
            raise RegenUniverseExpansionNotFoundError("youth_tournament_not_found")
        return self._tournament_view(tournament)

    def create_youth_tournament(
        self,
        *,
        name: str,
        age_limit: str,
        rewards: dict[str, Any] | None,
        start_date: date,
        end_date: date,
        participant_club_ids: list[str] | None = None,
        participant_limit: int = 4,
        simulate_immediately: bool = True,
    ) -> YouthTournament:
        if end_date < start_date:
            raise RegenUniverseExpansionValidationError("youth_tournament_invalid_window")
        participants = self._resolve_tournament_participants(
            age_limit=_parse_age_limit(age_limit),
            participant_club_ids=participant_club_ids or [],
            participant_limit=participant_limit,
        )
        if len(participants) < 4:
            raise RegenUniverseExpansionValidationError("youth_tournament_requires_four_participants")
        tournament = YouthTournament(
            name=name,
            age_limit=age_limit,
            participants_json=participants,
            rewards_json=rewards or {},
            start_date=start_date,
            end_date=end_date,
            status="scheduled",
            metadata_json={"participant_limit": participant_limit},
        )
        self.session.add(tournament)
        self.session.flush()
        if simulate_immediately:
            self._notify_tournament_start(tournament)
            fixtures, standings, top_players = self._run_tournament(tournament)
            tournament.fixtures_json = fixtures
            tournament.standings_json = standings
            tournament.top_players_json = top_players
            tournament.status = "completed"
            self._apply_tournament_impacts(tournament)
            self._notify_tournament_stars(tournament)
        self.session.flush()
        return tournament

    def schedule_youth_tournaments(self, *, days_ahead: int = 21) -> dict[str, Any]:
        today = date.today()
        existing = self.session.scalar(
            select(YouthTournament).where(
                YouthTournament.start_date >= today,
                YouthTournament.start_date <= today + timedelta(days=days_ahead),
            )
        )
        if existing is not None:
            return {"created": 0, "scheduled_window_days": days_ahead}
        tournament = self.create_youth_tournament(
            name=f"Global NextGen {today.year}",
            age_limit="U19",
            rewards={"winner": "global_exposure_boost", "awards": ["Best Young Player", "Top Scorer", "Breakout Talent"]},
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(days=10),
            participant_limit=4,
            simulate_immediately=True,
        )
        return {"created": 1, "tournament_ids": [tournament.id]}

    def apply_match_context(self, home_team: MatchTeamInput, away_team: MatchTeamInput) -> tuple[MatchTeamInput, MatchTeamInput]:
        player_ids = {
            player.player_id
            for player in [*home_team.starters, *home_team.bench, *away_team.starters, *away_team.bench]
            if not player.player_id.startswith("academy:") and not player.player_id.startswith("synthetic:")
        }
        players = {
            player.id: player
            for player in self.session.scalars(select(Player).where(Player.id.in_(player_ids))).all()
        }
        regens = {
            regen.player_id: regen
            for regen in self.session.scalars(select(RegenProfile).where(RegenProfile.player_id.in_(player_ids))).all()
        }
        for player in players.values():
            self._ensure_player_dna(player, regen=regens.get(player.id))
        rivalry_lookup = {
            frozenset({item.player_a_id, item.player_b_id}): item
            for item in self.session.scalars(
                select(PlayerRivalry).where(
                    or_(
                        PlayerRivalry.player_a_id.in_(player_ids),
                        PlayerRivalry.player_b_id.in_(player_ids),
                    )
                )
            ).all()
        }
        updated_home, home_intensity = self._apply_team_context(home_team, players=players, rivalry_lookup=rivalry_lookup, opponent=away_team)
        updated_away, away_intensity = self._apply_team_context(away_team, players=players, rivalry_lookup=rivalry_lookup, opponent=home_team)
        rivalry_intensity = max(home_intensity, away_intensity)
        return (
            updated_home.model_copy(update={"club_context": updated_home.club_context.model_copy(update={"rivalry_intensity": rivalry_intensity})}),
            updated_away.model_copy(update={"club_context": updated_away.club_context.model_copy(update={"rivalry_intensity": rivalry_intensity})}),
        )

    def _apply_team_context(
        self,
        team: MatchTeamInput,
        *,
        players: dict[str, Player],
        rivalry_lookup: dict[frozenset[str], PlayerRivalry],
        opponent: MatchTeamInput,
    ) -> tuple[MatchTeamInput, int]:
        opponent_ids = {player.player_id for player in [*opponent.starters, *opponent.bench]}
        player_heat: dict[str, float] = defaultdict(float)
        for player_id in {player.player_id for player in [*team.starters, *team.bench]}:
            for opponent_id in opponent_ids:
                rivalry = rivalry_lookup.get(frozenset({player_id, opponent_id}))
                if rivalry is not None:
                    player_heat[player_id] += float(rivalry.intensity_score)
        updated_starters = [self._apply_player_context(player, players.get(player.player_id), player_heat.get(player.player_id, 0.0)) for player in team.starters]
        updated_bench = [self._apply_player_context(player, players.get(player.player_id), player_heat.get(player.player_id, 0.0)) for player in team.bench]
        chemistry_bonus = self._dna_chemistry_bonus(updated_starters, players)
        resolved_context = team.club_context.model_copy(update={"team_chemistry": _clamp_int(team.club_context.team_chemistry + chemistry_bonus, 1, 100)})
        highest_heat = max(player_heat.values()) if player_heat else 0.0
        return (
            team.model_copy(update={"starters": updated_starters, "bench": updated_bench, "club_context": resolved_context}),
            _clamp_int(round(highest_heat / 2.0), 0, 100),
        )

    def _apply_player_context(self, player_input: MatchPlayerInput, player: Player | None, rivalry_heat: float) -> MatchPlayerInput:
        payload = player_input.model_dump(mode="python")
        if player is not None:
            adjustments = match_attribute_adjustments(normalize_dna_profile(player.dna_profile, position=player.normalized_position or player.position))
            for key, delta in adjustments.items():
                if key in payload and payload[key] is not None:
                    payload[key] = _clamp_int(int(payload[key]) + delta, 1, 99)
            payload["position_archetype"] = str(player.dna_profile.get("archetype", payload.get("position_archetype") or "engine"))
        if rivalry_heat > 0:
            payload["discipline"] = _clamp_int(int(payload.get("discipline") or 70) - round(rivalry_heat / 12), 1, 99)
            payload["motivation"] = _clamp_int(int(payload.get("motivation") or 60) + round(rivalry_heat / 10), 1, 99)
            payload["consistency"] = _clamp_int(int(payload.get("consistency") or 50) - round(rivalry_heat / 16), 1, 99)
            payload["clutch_factor"] = _clamp_int(int(payload.get("clutch_factor") or 50) + round(rivalry_heat / 14), 1, 99)
            payload["big_match_temperament"] = _clamp_int(int(payload.get("big_match_temperament") or 50) + round(rivalry_heat / 12), 1, 99)
        return MatchPlayerInput.model_validate(payload)

    def _dna_chemistry_bonus(self, starters: list[MatchPlayerInput], players: dict[str, Player]) -> int:
        dna_profiles = [players[player.player_id].dna_profile for player in starters if player.player_id in players]
        if len(dna_profiles) < 2:
            return 0
        fit_scores = [chemistry_fit_score(left, right) for left, right in combinations(dna_profiles, 2)]
        average_fit = sum(fit_scores) / max(len(fit_scores), 1)
        return round((average_fit - 0.48) * 14)

    def _ensure_player_dna(self, player: Player, *, regen: RegenProfile | None = None) -> dict[str, Any]:
        current = player.dna_profile if isinstance(player.dna_profile, dict) else {}
        if {"archetype", "tempo", "risk_taking", "creativity", "discipline"}.issubset(current):
            normalized = normalize_dna_profile(current, position=_position_text(player, regen))
            if normalized != current:
                player.dna_profile = normalized
            return normalized
        generated = generate_dna_profile(
            position=_position_text(player, regen),
            country_code=regen.birth_country_code if regen is not None else None,
            lineage_metadata=dict((regen.metadata_json or {}).get("lineage", {})) if regen is not None else None,
        )
        player.dna_profile = generated
        return generated

    def _compose_story(self, player: Player) -> dict[str, Any]:
        regen = self._get_regen_profile(player.id)
        legacy = self.session.scalar(select(RegenLegacyRecord).where(RegenLegacyRecord.player_id == player.id))
        career_entries = list(
            self.session.scalars(
                select(PlayerCareerEntry)
                .where(PlayerCareerEntry.player_id == player.id)
                .order_by(PlayerCareerEntry.created_at.desc())
            ).all()
        )
        lifecycle_events = list(
            self.session.scalars(
                select(PlayerLifecycleEvent)
                .where(PlayerLifecycleEvent.player_id == player.id)
                .order_by(PlayerLifecycleEvent.occurred_on.desc(), PlayerLifecycleEvent.created_at.desc())
            ).all()
        )
        key_matches = self._collect_key_matches(player.id)
        trophies = self._collect_trophies(player.id, regen)
        milestones = self._collect_milestones(player, career_entries)
        rivalries = self.list_player_rivalries(player.id, limit=5)
        dna_profile = self._ensure_player_dna(player, regen=regen)

        origin_summary = self._origin_story_summary(player, regen, dna_profile)
        breakout_summary = trophies[0]["summary"] if trophies else (key_matches[0]["summary"] if key_matches else f"{player.full_name} is still building the first signature breakout.")
        turning_event = next(
            (
                event
                for event in lifecycle_events
                if event.event_type in {"transfer_completed", "regen_retired", "injury", "free_agency", "starter_bootstrap"}
            ),
            lifecycle_events[0] if lifecycle_events else None,
        )
        turning_summary = turning_event.summary if turning_event is not None else f"{player.full_name}'s story has not hit a decisive fork in the road yet."
        peak_entry = max(career_entries, key=lambda item: (item.goals + item.assists + item.appearances), default=None)
        peak_summary = (
            f"{peak_entry.season_label} with {peak_entry.club_name} marked the peak: "
            f"{peak_entry.appearances} appearances, {peak_entry.goals} goals, {peak_entry.assists} assists."
            if peak_entry is not None
            else (key_matches[0]["summary"] if key_matches else f"{player.full_name}'s peak era is still taking shape.")
        )
        legacy_summary = (
            legacy.narrative_summary
            or f"Legacy score {round(legacy.legacy_score, 1)} after {legacy.seasons_total} seasons."
            if legacy is not None
            else f"{player.full_name} projects as a {dna_profile['archetype']} whose final legacy is still unresolved."
        )

        chapters = [
            {"title": "Origin Story", "summary": origin_summary, "source_keys": ["regen_profile", "dna_profile", "career_entries"]},
            {"title": "Breakout Moment", "summary": breakout_summary, "source_keys": ["match_events", "trophies", "milestones"]},
            {"title": "Career Turning Point", "summary": turning_summary, "source_keys": ["career_events"]},
            {"title": "Peak Era", "summary": peak_summary, "source_keys": ["career_entries", "stats_milestones"]},
        ]
        if rivalries and float(rivalries[0]["intensity_score"]) >= 70:
            opponent = next(item for item in rivalries[0]["players"] if item["player_id"] != player.id)
            chapters.append(
                {
                    "title": "Defining Rivalry Chapter",
                    "summary": f"The running battle with {opponent['player_name']} became a defining thread with intensity {rivalries[0]['intensity_score']}.",
                    "source_keys": ["rivalries", "match_events"],
                }
            )
        chapters.append({"title": "Legacy Reflection", "summary": legacy_summary, "source_keys": ["legacy", "career_entries", "trophies"]})

        timeline = []
        for event in lifecycle_events[:5]:
            timeline.append(
                {
                    "title": event.event_type.replace("_", " ").title(),
                    "event_type": event.event_type,
                    "summary": event.summary,
                    "occurred_on": event.occurred_on,
                    "importance": 6.0,
                    "metadata": dict(event.details_json or {}),
                }
            )
        timeline.extend(trophies)
        timeline.extend(milestones)
        timeline.extend(
            {
                "title": f"Key Match: {item['competition'] or 'Competition'}",
                "event_type": "key_match",
                "summary": item["summary"],
                "occurred_on": item["match_date"],
                "importance": 7.0 + float(item.get("rating") or 0.0) / 2.0,
                "metadata": {"match_id": item["match_id"]},
            }
            for item in key_matches[:3]
        )
        if rivalries:
            timeline.append(
                {
                    "title": "Rivalry Peak",
                    "event_type": "rivalry_peak",
                    "summary": chapters[-2]["summary"] if chapters[-2]["title"] == "Defining Rivalry Chapter" else "Rivalry pressure is reshaping the narrative arc.",
                    "occurred_on": None,
                    "importance": 8.5,
                    "metadata": {"rivalry_id": rivalries[0]["id"], "intensity_score": rivalries[0]["intensity_score"]},
                }
            )

        timeline = sorted(
            timeline,
            key=lambda item: (item["occurred_on"] or date.min, float(item["importance"])),
            reverse=True,
        )
        key_moments = timeline[:5]
        narrative_score = min(
            100.0,
            round(
                22.0
                + (len(key_matches) * 7.0)
                + (len(trophies) * 6.0)
                + (len(milestones) * 4.0)
                + ((float(rivalries[0]["intensity_score"]) * 0.24) if rivalries else 0.0)
                + ((legacy.legacy_score * 0.08) if legacy is not None else 0.0),
                2,
            ),
        )
        return {
            "chapters": chapters,
            "key_moments": key_moments,
            "rivalries": rivalries,
            "timeline_narrative": timeline,
            "key_matches": key_matches,
            "defining_moments": key_moments[:3],
            "narrative_score": narrative_score,
        }

    def _origin_story_summary(self, player: Player, regen: RegenProfile | None, dna_profile: dict[str, Any]) -> str:
        if regen is not None:
            place_bits = [bit for bit in (regen.birth_city, regen.birth_region, regen.birth_country_code) if bit]
            lineage = dict((regen.metadata_json or {}).get("lineage", {}))
            lineage_text = ""
            if lineage:
                lineage_text = f" Special lineage traces back to {lineage.get('related_legend_ref_id', 'a footballing predecessor')}."
            return (
                f"{player.full_name} emerged from {' / '.join(place_bits) if place_bits else 'the regen universe'} "
                f"with a {dna_profile['archetype']} DNA profile built around tempo {dna_profile['tempo']} "
                f"and creativity {dna_profile['creativity']}."
                f"{lineage_text}"
            )
        return (
            f"{player.full_name} carries a {dna_profile['archetype']} profile shaped by "
            f"tempo {dna_profile['tempo']} and discipline {dna_profile['discipline']}."
        )

    def _collect_key_matches(self, player_id: str) -> list[dict[str, Any]]:
        rows = list(
            self.session.execute(
                select(PlayerMatchStat, Match, Competition)
                .join(Match, Match.id == PlayerMatchStat.match_id)
                .outerjoin(Competition, Competition.id == PlayerMatchStat.competition_id)
                .where(PlayerMatchStat.player_id == player_id)
            ).all()
        )
        ranked: list[tuple[float, dict[str, Any]]] = []
        for stat, match, competition in rows:
            score = (float(stat.rating or 0.0) * 5.0) + (int(stat.goals or 0) * 7.0) + (int(stat.assists or 0) * 5.0) + (int(stat.saves or 0) * 0.5)
            if stat.clean_sheet:
                score += 4.0
            if stat.club_id == match.home_club_id:
                club_name = match.home_club.name if match.home_club is not None else None
                opponent_name = match.away_club.name if match.away_club is not None else None
            else:
                club_name = match.away_club.name if match.away_club is not None else None
                opponent_name = match.home_club.name if match.home_club is not None else None
            ranked.append(
                (
                    score,
                    {
                        "match_id": match.id,
                        "match_date": _match_occurred_on(match),
                        "competition": competition.name if competition is not None else None,
                        "club_name": club_name,
                        "opponent_name": opponent_name,
                        "rating": round(float(stat.rating), 2) if stat.rating is not None else None,
                        "goals": int(stat.goals or 0),
                        "assists": int(stat.assists or 0),
                        "summary": (
                            f"{competition.name if competition is not None else 'Competition'}: "
                            f"rating {round(float(stat.rating or 0.0), 1)} with {int(stat.goals or 0)} goals "
                            f"and {int(stat.assists or 0)} assists."
                        ),
                    },
                )
            )
        return [item for _, item in sorted(ranked, key=lambda row: row[0], reverse=True)[:5]]

    def _collect_trophies(self, player_id: str, regen: RegenProfile | None) -> list[dict[str, Any]]:
        trophies: list[dict[str, Any]] = []
        for entry in self.session.scalars(select(PlayerCareerEntry).where(PlayerCareerEntry.player_id == player_id)).all():
            for honour in entry.honours_json or []:
                title = str(honour.get("name") or honour.get("title") or honour.get("honour") or "Major honour")
                trophies.append(
                    {
                        "title": title,
                        "event_type": "trophy",
                        "summary": f"{title} arrived during the {entry.season_label} campaign with {entry.club_name}.",
                        "occurred_on": entry.end_on or entry.start_on,
                        "importance": 7.5,
                        "metadata": {"season_label": entry.season_label},
                    }
                )
        if regen is not None:
            for award in self.session.scalars(
                select(RegenAwardWinner).where(RegenAwardWinner.player_id == player_id).order_by(RegenAwardWinner.awarded_at.desc())
            ).all():
                trophies.append(
                    {
                        "title": "Major Trophy Win",
                        "event_type": "award",
                        "summary": f"Collected a regen universe honour with ranking score {round(award.ranking_score, 1)}.",
                        "occurred_on": award.awarded_at.date(),
                        "importance": 8.0,
                        "metadata": {"award_id": award.award_id},
                    }
                )
        return sorted(trophies, key=lambda item: (item["occurred_on"] or date.min, item["importance"]), reverse=True)[:5]

    def _collect_milestones(self, player: Player, career_entries: list[PlayerCareerEntry]) -> list[dict[str, Any]]:
        total_appearances = sum(item.appearances for item in career_entries)
        total_goals = sum(item.goals for item in career_entries)
        total_assists = sum(item.assists for item in career_entries)
        milestones: list[dict[str, Any]] = []
        if total_appearances >= 50:
            milestones.append({"title": "50 Appearances", "event_type": "milestone", "summary": f"Reached {total_appearances} senior appearances.", "occurred_on": None, "importance": 6.5, "metadata": {"appearances": total_appearances}})
        if total_goals >= 25:
            milestones.append({"title": "Goal Milestone", "event_type": "milestone", "summary": f"Hit {total_goals} career goals.", "occurred_on": None, "importance": 7.0, "metadata": {"goals": total_goals}})
        if total_assists >= 20:
            milestones.append({"title": "Creator Milestone", "event_type": "milestone", "summary": f"Delivered {total_assists} career assists.", "occurred_on": None, "importance": 6.8, "metadata": {"assists": total_assists}})
        if player.market_value_eur and player.market_value_eur >= 20_000_000:
            milestones.append({"title": "Market Surge", "event_type": "market_value", "summary": f"Market value climbed above {round(player.market_value_eur / 1_000_000, 1)}M EUR.", "occurred_on": None, "importance": 6.2, "metadata": {"market_value_eur": player.market_value_eur}})
        return milestones

    def _story_view(self, story: PlayerStory) -> dict[str, Any]:
        payload = dict(story.chapters or {})
        return {
            "id": story.id,
            "player_id": story.player_id,
            "chapters": list(payload.get("chapters", [])),
            "key_moments": list(payload.get("key_moments", [])),
            "rivalries": list(payload.get("rivalries", [])),
            "timeline_narrative": list(payload.get("timeline_narrative", [])),
            "key_matches": list(payload.get("key_matches", [])),
            "defining_moments": list(payload.get("defining_moments", [])),
            "narrative_score": float(story.narrative_score),
            "created_at": story.created_at,
        }

    def _resolve_tournament_participants(
        self,
        *,
        age_limit: int,
        participant_club_ids: list[str],
        participant_limit: int,
    ) -> list[dict[str, Any]]:
        club_filter = set(participant_club_ids)
        grouped: dict[str, dict[str, Any]] = {}

        for regen, player in self.session.execute(
            select(RegenProfile, Player)
            .join(Player, Player.id == RegenProfile.player_id)
            .where(Player.current_club_profile_id.is_not(None))
        ).all():
            age = _player_age(player)
            if age > age_limit:
                continue
            if club_filter and player.current_club_profile_id not in club_filter:
                continue
            club_id = player.current_club_profile_id
            if club_id is None:
                continue
            participant = grouped.setdefault(club_id, {"team_id": club_id, "team_name": None, "source": "regen_pool", "players": []})
            if participant["source"] != "regen_pool":
                participant["source"] = "mixed"
            participant["players"].append(
                {
                    "source_type": "regen",
                    "entity_id": regen.id,
                    "player_id": player.id,
                    "display_name": player.full_name,
                    "age": age,
                    "position": regen.primary_position,
                    "overall": _clamp_int(round((regen.current_ability_range_json.get("minimum", regen.current_gsi) + regen.current_ability_range_json.get("maximum", regen.current_gsi)) / 2), 35, 95),
                    "team_id": club_id,
                    "market_value": float(player.market_value_eur or 0.0),
                    "dna_profile": self._ensure_player_dna(player, regen=regen),
                }
            )

        for academy in self.session.scalars(select(AcademyPlayer).where(AcademyPlayer.age <= age_limit)).all():
            if club_filter and academy.club_id not in club_filter:
                continue
            participant = grouped.setdefault(academy.club_id, {"team_id": academy.club_id, "team_name": None, "source": "academy", "players": []})
            if participant["source"] != "academy":
                participant["source"] = "mixed"
            participant["players"].append(
                {
                    "source_type": "academy",
                    "entity_id": academy.id,
                    "player_id": None,
                    "display_name": academy.display_name,
                    "age": academy.age,
                    "position": academy.primary_position,
                    "overall": _clamp_int(max(academy.overall_rating, academy.readiness_score + 6, 45), 35, 90),
                    "team_id": academy.club_id,
                    "market_value": float(max(academy.overall_rating, academy.readiness_score) * 50_000),
                    "dna_profile": {},
                }
            )

        clubs = {
            club.id: club
            for club in self.session.scalars(select(ClubProfile).where(ClubProfile.id.in_(grouped.keys()))).all()
        }
        participants: list[dict[str, Any]] = []
        for participant in grouped.values():
            players = participant["players"]
            if not players:
                continue
            participant["team_name"] = clubs.get(participant["team_id"]).club_name if participant["team_id"] in clubs else f"Youth Select {len(participants) + 1}"
            participant["player_count"] = len(players)
            participant["average_age"] = round(sum(int(player["age"]) for player in players) / len(players), 2)
            participant["average_rating"] = round(sum(int(player["overall"]) for player in players) / len(players), 2)
            participant["player_ids"] = [str(player["player_id"] or f"academy:{player['entity_id']}") for player in players]
            participants.append(participant)

        participants.sort(key=lambda item: (item["player_count"], item["average_rating"]), reverse=True)
        if len(participants) >= participant_limit:
            return participants[:participant_limit]

        pool = [player for participant in participants for player in participant["players"]]
        for index in range(max(0, participant_limit - len(participants))):
            team_players = pool[index::participant_limit] or pool
            participants.append(
                {
                    "team_id": f"showcase-{index + 1}",
                    "team_name": f"Global Select {index + 1}",
                    "source": "mixed",
                    "players": team_players[:12],
                    "player_count": len(team_players[:12]),
                    "average_age": round(sum(int(player["age"]) for player in team_players[:12]) / max(1, len(team_players[:12])), 2),
                    "average_rating": round(sum(int(player["overall"]) for player in team_players[:12]) / max(1, len(team_players[:12])), 2),
                    "player_ids": [str(player["player_id"] or f"academy:{player['entity_id']}") for player in team_players[:12]],
                }
            )
        return participants[:participant_limit]

    def _run_tournament(self, tournament: YouthTournament) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        participants = list(tournament.participants_json or [])
        groups = {"A": participants[:2], "B": participants[2:4]} if len(participants) == 4 else {"A": participants[:4]}
        standings: dict[str, dict[str, Any]] = {}
        member_lookup = self._participant_member_lookup(participants)
        fixtures: list[dict[str, Any]] = []
        player_board: dict[str, dict[str, Any]] = {}
        rng = Random(f"youth-tournament:{tournament.id}")

        for group_key, teams in groups.items():
            for team in teams:
                standings.setdefault(
                    team["team_id"],
                    {
                        "team_id": team["team_id"],
                        "team_name": team["team_name"],
                        "group": group_key,
                        "played": 0,
                        "won": 0,
                        "drawn": 0,
                        "lost": 0,
                        "goals_for": 0,
                        "goals_against": 0,
                        "goal_difference": 0,
                        "points": 0,
                    },
                )
            for home, away in combinations(teams, 2):
                summary = self._simulate_tournament_fixture(home, away, stage="group", group_key=group_key, rng=rng)
                fixtures.append(self._fixture_from_summary(summary, stage="group", group_key=group_key))
                self._apply_group_result(standings, summary)
                self._accumulate_player_board(player_board, member_lookup, summary)

        finalists = sorted(standings.values(), key=lambda item: (item["points"], item["goal_difference"], item["goals_for"]), reverse=True)[:2]
        team_lookup = {team["team_id"]: team for team in participants}
        final_summary = self._simulate_tournament_fixture(
            team_lookup[finalists[0]["team_id"]],
            team_lookup[finalists[1]["team_id"]],
            stage="final",
            group_key=None,
            rng=rng,
            requires_winner=True,
        )
        fixtures.append(self._fixture_from_summary(final_summary, stage="final", group_key=None))
        self._accumulate_player_board(player_board, member_lookup, final_summary)
        return fixtures, list(standings.values()), self._build_top_player_table(player_board)

    def _simulate_tournament_fixture(
        self,
        home_participant: dict[str, Any],
        away_participant: dict[str, Any],
        *,
        stage: str,
        group_key: str | None,
        rng: Random,
        requires_winner: bool = False,
    ):
        home_team = self._build_tournament_team_input(home_participant)
        away_team = self._build_tournament_team_input(away_participant)
        home_team, away_team = self.apply_match_context(home_team, away_team)
        request = MatchSimulationRequest(
            match_id=f"youth-{home_participant['team_id']}-{away_participant['team_id']}-{stage}-{rng.randrange(10_000, 99_999)}",
            seed=rng.randrange(1, 1_000_000),
            competition=MatchCompetitionContextInput(
                competition_type=MatchCompetitionType.CUP,
                stage=stage if group_key is None else f"group-{group_key}",
                is_final=stage == "final",
                requires_winner=requires_winner or stage == "final",
            ),
            home_team=home_team,
            away_team=away_team,
        )
        return self.match_service.build_summary(request)

    def _build_tournament_team_input(self, participant: dict[str, Any]) -> MatchTeamInput:
        seeds = [
            _TournamentPlayerSeed(
                source_type=str(player["source_type"]),
                entity_id=str(player["entity_id"]),
                player_id=str(player["player_id"]) if player.get("player_id") else None,
                display_name=str(player["display_name"]),
                age=int(player["age"]),
                position=str(player["position"]),
                overall=int(player["overall"]),
                team_id=str(player["team_id"]) if player.get("team_id") else None,
                market_value=float(player.get("market_value") or 0.0),
                dna_profile=dict(player.get("dna_profile") or {}),
            )
            for player in participant.get("players", [])
        ]
        team_key = str(participant["team_id"])
        starters, bench = self._select_tournament_squad(seeds, team_key=team_key)
        average_rating = round(sum(seed.overall for seed, _ in starters) / max(1, len(starters)))
        return MatchTeamInput(
            team_id=str(participant["team_id"]),
            team_name=str(participant["team_name"]),
            formation="4-3-3",
            tactics=TeamTacticalPlanInput(
                style=TacticalStyle.ATTACKING if average_rating >= 72 else TacticalStyle.BALANCED,
                pressing=_clamp_int(50 + ((average_rating - 55) // 2), 35, 85),
                tempo=_clamp_int(54 + ((average_rating - 55) // 2), 40, 88),
                aggression=_clamp_int(44 + ((average_rating - 55) // 3), 38, 80),
                substitution_windows=(58, 70, 82),
                red_card_fallback_formation="4-4-1",
                injury_auto_substitution=True,
                yellow_card_substitution_minute=68,
                yellow_card_replacement_roles=(PlayerRole.DEFENDER, PlayerRole.MIDFIELDER),
                max_substitutions=5,
                tactical_quality=_clamp_int(55 + ((average_rating - 55) // 2), 40, 90),
                adaptability=_clamp_int(54 + ((average_rating - 55) // 3), 40, 88),
                game_management=_clamp_int(53 + ((average_rating - 55) // 3), 40, 88),
            ),
            club_context=MatchClubContextInput(
                club_tier=_clamp_int(average_rating, 35, 90),
                competition_tier=_clamp_int(average_rating - 2, 35, 90),
                team_chemistry=62,
                recent_form=60,
                morale=62,
                motivation=66,
                fatigue_load=24,
                travel_load=22,
                rivalry_intensity=0,
                schedule_pressure=38,
            ),
            starters=[self._seed_to_match_player(seed, role=role, slot=index + 1) for index, (seed, role) in enumerate(starters)],
            bench=[self._seed_to_match_player(seed, role=role, slot=index + 21) for index, (seed, role) in enumerate(bench)],
        )

    def _select_tournament_squad(
        self,
        seeds: list[_TournamentPlayerSeed],
        *,
        team_key: str,
    ) -> tuple[list[tuple[_TournamentPlayerSeed, PlayerRole]], list[tuple[_TournamentPlayerSeed, PlayerRole]]]:
        required_roles = [PlayerRole.GOALKEEPER] + ([PlayerRole.DEFENDER] * 4) + ([PlayerRole.MIDFIELDER] * 3) + ([PlayerRole.FORWARD] * 3)
        remaining = list(seeds)
        starters: list[tuple[_TournamentPlayerSeed, PlayerRole]] = []
        for index, role in enumerate(required_roles, start=1):
            if remaining:
                best = max(remaining, key=lambda seed: (self._seed_role_fit(seed, role), seed.overall, -seed.age))
                if self._seed_role_fit(best, role) > 0:
                    starters.append((best, role))
                    remaining.remove(best)
                    continue
            starters.append((self._synthetic_seed(role, slot=index, team_key=team_key), role))
        bench = [(seed, _resolve_role(seed.position)) for seed in sorted(remaining, key=lambda item: item.overall, reverse=True)[:7]]
        while len(bench) < 7:
            role = [PlayerRole.GOALKEEPER, PlayerRole.DEFENDER, PlayerRole.MIDFIELDER, PlayerRole.FORWARD][len(bench) % 4]
            bench.append((self._synthetic_seed(role, slot=40 + len(bench), team_key=team_key), role))
        return starters, bench

    def _seed_role_fit(self, seed: _TournamentPlayerSeed, role: PlayerRole) -> int:
        actual = _resolve_role(seed.position)
        if actual == role:
            return 3
        if role == PlayerRole.MIDFIELDER and actual in {PlayerRole.DEFENDER, PlayerRole.FORWARD}:
            return 1
        if role == PlayerRole.FORWARD and actual == PlayerRole.MIDFIELDER:
            return 1
        if role == PlayerRole.DEFENDER and actual == PlayerRole.MIDFIELDER:
            return 1
        return 0

    def _synthetic_seed(self, role: PlayerRole, *, slot: int, team_key: str) -> _TournamentPlayerSeed:
        name = {PlayerRole.GOALKEEPER: "Youth Keeper", PlayerRole.DEFENDER: "Youth Defender", PlayerRole.MIDFIELDER: "Youth Midfielder", PlayerRole.FORWARD: "Youth Forward"}[role]
        team_slug = "".join(character if character.isalnum() else "-" for character in team_key.lower()).strip("-") or "team"
        return _TournamentPlayerSeed(
            source_type="synthetic",
            entity_id=f"synthetic-{team_slug}-{role.value.lower()}-{slot}",
            player_id=f"synthetic:{team_slug}:{role.value.lower()}:{slot}",
            display_name=f"{name} {slot}",
            age=17,
            position=role.value,
            overall=48,
            team_id=None,
            market_value=0.0,
            dna_profile={},
        )

    def _seed_to_match_player(self, seed: _TournamentPlayerSeed, *, role: PlayerRole, slot: int) -> MatchPlayerInput:
        overall = _clamp_int(seed.overall, 35, 95)
        base = {
            "player_id": seed.player_id or f"academy:{seed.entity_id}",
            "player_name": seed.display_name,
            "role": role,
            "overall": overall,
            "shirt_number": slot if slot <= 99 else None,
            "display_name": _surname(seed.display_name),
            "recent_form": _clamp_int(overall + 2, 35, 95),
            "morale": 62,
            "motivation": 65,
            "fitness": 76,
            "discipline": 69,
            "fatigue_load": 26,
            "injury_risk": 18,
            "leadership": _clamp_int(overall - 4, 20, 90),
        }
        role_updates = {
            PlayerRole.GOALKEEPER: {"finishing": 10, "creativity": 34, "defending": 52, "goalkeeping": _clamp_int(overall + 10, 40, 99), "position_archetype": "shot_stopper", "pace": _clamp_int(overall - 16, 20, 90), "composure": _clamp_int(overall + 4, 30, 99), "decision_making": _clamp_int(overall + 3, 30, 99), "positioning": _clamp_int(overall + 5, 30, 99), "off_ball_movement": _clamp_int(overall - 24, 10, 85), "aerial_ability": _clamp_int(overall + 7, 30, 99), "technique": _clamp_int(overall - 2, 20, 99), "stamina_curve": 70, "consistency": _clamp_int(overall + 2, 20, 99), "clutch_factor": _clamp_int(overall + 2, 20, 99), "big_match_temperament": _clamp_int(overall + 1, 20, 99)},
            PlayerRole.DEFENDER: {"finishing": _clamp_int(overall - 18, 10, 90), "creativity": _clamp_int(overall - 4, 15, 92), "defending": _clamp_int(overall + 8, 25, 99), "goalkeeping": 5, "position_archetype": "ball_playing_defender", "pace": _clamp_int(overall - 1, 20, 95), "composure": _clamp_int(overall + 1, 20, 95), "decision_making": _clamp_int(overall + 2, 20, 95), "positioning": _clamp_int(overall + 6, 20, 99), "off_ball_movement": _clamp_int(overall - 7, 10, 90), "aerial_ability": _clamp_int(overall + 5, 20, 99), "technique": _clamp_int(overall - 1, 20, 95), "stamina_curve": 74, "consistency": _clamp_int(overall + 2, 20, 95), "clutch_factor": _clamp_int(overall - 2, 15, 92), "big_match_temperament": _clamp_int(overall + 1, 20, 95)},
            PlayerRole.MIDFIELDER: {"finishing": _clamp_int(overall - 2, 18, 95), "creativity": _clamp_int(overall + 7, 25, 99), "defending": _clamp_int(overall - 4, 15, 92), "goalkeeping": 5, "position_archetype": "playmaker", "pace": _clamp_int(overall - 1, 20, 95), "composure": _clamp_int(overall + 3, 20, 99), "decision_making": _clamp_int(overall + 6, 20, 99), "positioning": _clamp_int(overall + 3, 20, 95), "off_ball_movement": _clamp_int(overall + 4, 20, 99), "aerial_ability": _clamp_int(overall - 6, 10, 90), "technique": _clamp_int(overall + 7, 20, 99), "stamina_curve": 78, "consistency": _clamp_int(overall + 4, 20, 99), "clutch_factor": _clamp_int(overall + 1, 18, 95), "big_match_temperament": _clamp_int(overall + 2, 20, 95)},
            PlayerRole.FORWARD: {"finishing": _clamp_int(overall + 8, 24, 99), "creativity": _clamp_int(overall + 1, 18, 95), "defending": _clamp_int(overall - 16, 10, 85), "goalkeeping": 5, "position_archetype": "poacher", "pace": _clamp_int(overall + 6, 20, 99), "composure": _clamp_int(overall + 6, 20, 99), "decision_making": _clamp_int(overall + 1, 20, 95), "positioning": _clamp_int(overall + 4, 20, 99), "off_ball_movement": _clamp_int(overall + 8, 20, 99), "aerial_ability": _clamp_int(overall - 2, 15, 92), "technique": _clamp_int(overall + 3, 20, 95), "stamina_curve": 74, "consistency": _clamp_int(overall + 2, 20, 95), "clutch_factor": _clamp_int(overall + 7, 22, 99), "big_match_temperament": _clamp_int(overall + 5, 20, 99)},
        }
        base.update(role_updates[role])
        for key, delta in match_attribute_adjustments(seed.dna_profile).items():
            if key in base:
                base[key] = _clamp_int(int(base[key]) + delta, 1, 99)
        return MatchPlayerInput.model_validate(base)

    def _fixture_from_summary(self, summary, *, stage: str, group_key: str | None) -> dict[str, Any]:
        top_performers = sorted(
            ({"player_id": item.player_id, "player_name": item.player_name, "team_id": item.team_id, "rating": item.rating, "goals": item.goals, "assists": item.assists} for item in summary.player_stats if item.rating is not None),
            key=lambda item: ((float(item["rating"] or 0.0)), item["goals"], item["assists"]),
            reverse=True,
        )[:3]
        return {"match_id": summary.match_id, "stage": stage, "group": group_key, "home_team_id": summary.home_stats.team_id, "home_team_name": summary.home_stats.team_name, "away_team_id": summary.away_stats.team_id, "away_team_name": summary.away_stats.team_name, "home_score": summary.home_score, "away_score": summary.away_score, "winner_team_id": summary.winner_team_id, "top_performers": top_performers}

    def _apply_group_result(self, standings: dict[str, dict[str, Any]], summary) -> None:
        home = standings[summary.home_stats.team_id]
        away = standings[summary.away_stats.team_id]
        home["played"] += 1
        away["played"] += 1
        home["goals_for"] += summary.home_score
        home["goals_against"] += summary.away_score
        away["goals_for"] += summary.away_score
        away["goals_against"] += summary.home_score
        home["goal_difference"] = home["goals_for"] - home["goals_against"]
        away["goal_difference"] = away["goals_for"] - away["goals_against"]
        if summary.home_score > summary.away_score:
            home["won"] += 1
            home["points"] += 3
            away["lost"] += 1
        elif summary.away_score > summary.home_score:
            away["won"] += 1
            away["points"] += 3
            home["lost"] += 1
        else:
            home["drawn"] += 1
            away["drawn"] += 1
            home["points"] += 1
            away["points"] += 1

    def _participant_member_lookup(self, participants: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        lookup: dict[str, dict[str, Any]] = {}
        for participant in participants:
            for player in participant.get("players", []):
                public_id = str(player["player_id"] or f"academy:{player['entity_id']}")
                lookup[public_id] = {"team_id": participant["team_id"], "team_name": participant["team_name"], "source_type": player["source_type"], "display_name": player["display_name"], "overall": player["overall"], "player_id": player["player_id"]}
        return lookup

    def _accumulate_player_board(self, board: dict[str, dict[str, Any]], lookup: dict[str, dict[str, Any]], summary) -> None:
        for stat in summary.player_stats:
            player = lookup.get(stat.player_id)
            if player is None:
                continue
            row = board.setdefault(stat.player_id, {"player_id": stat.player_id, "player_name": stat.player_name, "team_id": player["team_id"], "team_name": player["team_name"], "source_type": player["source_type"], "goals": 0, "assists": 0, "rating_total": 0.0, "appearances": 0, "baseline_overall": int(player["overall"])})
            row["goals"] += stat.goals
            row["assists"] += stat.assists
            row["rating_total"] += float(stat.rating or 0.0)
            row["appearances"] += 1

    def _build_top_player_table(self, board: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        if not board:
            return []
        ranked = sorted(board.values(), key=lambda row: (row["goals"] * 6 + row["assists"] * 4 + ((row["rating_total"] / max(row["appearances"], 1)) * 5) - (row["baseline_overall"] * 0.02), row["goals"], row["assists"]), reverse=True)
        top_scorer_id = max(ranked, key=lambda row: (row["goals"], row["assists"], row["rating_total"]))["player_id"]
        best_young_player_id = ranked[0]["player_id"]
        breakout_talent_id = max(ranked, key=lambda row: ((row["rating_total"] / max(row["appearances"], 1)) - (row["baseline_overall"] / 10.0), row["goals"]))["player_id"]
        views: list[dict[str, Any]] = []
        for row in ranked[:10]:
            award = "Top Scorer" if row["player_id"] == top_scorer_id else "Best Young Player" if row["player_id"] == best_young_player_id else "Breakout Talent" if row["player_id"] == breakout_talent_id else None
            views.append({"player_id": row["player_id"], "player_name": row["player_name"], "team_id": row["team_id"], "team_name": row["team_name"], "source_type": row["source_type"], "goals": row["goals"], "assists": row["assists"], "average_rating": round(row["rating_total"] / max(row["appearances"], 1), 2), "award": award})
        return views

    def _apply_tournament_impacts(self, tournament: YouthTournament) -> None:
        participant_lookup = self._participant_member_lookup(list(tournament.participants_json or []))
        for row in list(tournament.top_players_json or [])[:6]:
            member = participant_lookup.get(row["player_id"])
            if member is None or member["source_type"] == "synthetic":
                continue
            if member["source_type"] == "academy":
                academy = self.session.get(AcademyPlayer, row["player_id"].replace("academy:", "", 1))
                if academy is not None:
                    academy.readiness_score += 4 if row.get("award") else 2
                    academy.overall_rating += 1 if row.get("average_rating", 0.0) >= 7.5 else 0
                    academy.development_attributes_json = {**dict(academy.development_attributes_json or {}), "tournament_morale_boost": 1 if row.get("award") else 0}
                continue
            player = self.session.get(Player, row["player_id"])
            if player is None:
                continue
            regen = self._get_regen_profile(player.id)
            dna_profile = self._ensure_player_dna(player, regen=regen)
            potential_multiplier = growth_bias_multiplier(dna_profile, category="potential")
            market_multiplier = growth_bias_multiplier(dna_profile, category="market_value")
            morale_multiplier = growth_bias_multiplier(dna_profile, category="morale")
            boost_strength = 1.8 if row.get("award") else 1.0
            if regen is not None:
                current_max = int(regen.potential_range_json.get("maximum", regen.current_gsi))
                regen.potential_range_json = {**dict(regen.potential_range_json or {}), "maximum": _clamp_int(current_max + round(potential_multiplier * boost_strength), current_max, 99)}
                regen.metadata_json = {**dict(regen.metadata_json or {}), "visibility_multiplier": round(max(float((regen.metadata_json or {}).get("visibility_multiplier", 1.0)), 1.0 + ((market_multiplier - 1.0) * boost_strength * 2.0)), 4)}
            player.market_value_eur = float(player.market_value_eur or 0.0) * (1.0 + ((market_multiplier - 1.0) * 0.55 * boost_strength)) if player.market_value_eur is not None else 1_000_000 * market_multiplier
            if player.current_market_reference_value is not None:
                player.current_market_reference_value = float(player.current_market_reference_value) * (1.0 + ((market_multiplier - 1.0) * 0.45 * boost_strength))
            evolved = dict(dna_profile)
            evolved["morale_boost"] = round(min(0.25, float(dna_profile.get("morale_boost", 0.0)) + ((morale_multiplier - 1.0) * 0.12 * boost_strength)), 4)
            evolved["evolution"] = [*list(evolved.get("evolution", []))[-7:], {"at": _utcnow().isoformat(), "reason": "youth_tournament", "award": row.get("award")}]
            player.dna_profile = evolved
            if row.get("award") in {"Best Young Player", "Top Scorer", "Breakout Talent"}:
                self.refresh_story(player.id, trigger="major_trophy_win" if row["award"] != "Breakout Talent" else "breakout_event", notify=False, publish=True)
        self.session.flush()

    def _notify_tournament_start(self, tournament: YouthTournament) -> None:
        club_ids = {item.get("team_id") for item in tournament.participants_json or [] if item.get("team_id")}
        for club in self.session.scalars(select(ClubProfile).where(ClubProfile.id.in_(club_ids))).all():
            if not club.owner_user_id:
                continue
            self.session.add(NotificationRecord(user_id=club.owner_user_id, topic="youth_tournament", template_key="YOUTH_TOURNAMENT_START", resource_type="youth_tournament", resource_id=tournament.id, message=f"{tournament.name} is kicking off.", metadata_json={"tournament_id": tournament.id, "age_limit": tournament.age_limit}))

    def _notify_tournament_stars(self, tournament: YouthTournament) -> None:
        for row in tournament.top_players_json or []:
            if not row.get("award") or row["player_id"].startswith("academy:"):
                continue
            player = self.session.get(Player, row["player_id"])
            if player is not None:
                self._notify_player_owners(player, template_key="YOUTH_TOURNAMENT_STAR", topic="youth_tournament", message=f"{player.full_name} earned {row['award']} at {tournament.name}.", resource_type="youth_tournament", resource_id=tournament.id, metadata={"player_id": player.id, "award": row["award"], "tournament_id": tournament.id})

    def _notify_player_owners(self, player: Player, *, template_key: str, topic: str, message: str, resource_type: str, resource_id: str, metadata: dict[str, Any]) -> None:
        if not player.current_club_profile_id:
            return
        club = self.session.get(ClubProfile, player.current_club_profile_id)
        if club is None or not club.owner_user_id:
            return
        self.session.add(NotificationRecord(user_id=club.owner_user_id, topic=topic, template_key=template_key, resource_type=resource_type, resource_id=resource_id, message=message[:255], metadata_json=metadata))

    def _require_player(self, player_id: str) -> Player:
        player = self.session.get(Player, player_id)
        if player is None:
            raise RegenUniverseExpansionNotFoundError("player_not_found")
        return player

    def _get_regen_profile(self, player_id: str) -> RegenProfile | None:
        return self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player_id))

    def _tournament_view(self, tournament: YouthTournament) -> dict[str, Any]:
        participants = [
            {
                "team_id": item.get("team_id"),
                "team_name": item.get("team_name"),
                "source": item.get("source"),
                "player_count": item.get("player_count", 0),
                "average_age": item.get("average_age"),
                "average_rating": item.get("average_rating"),
                "player_ids": list(item.get("player_ids") or []),
            }
            for item in (tournament.participants_json or [])
        ]
        return {
            "id": tournament.id,
            "name": tournament.name,
            "age_limit": tournament.age_limit,
            "participants": participants,
            "rewards": dict(tournament.rewards_json or {}),
            "start_date": tournament.start_date,
            "end_date": tournament.end_date,
            "fixtures": list(tournament.fixtures_json or []),
            "standings": list(tournament.standings_json or []),
            "top_players": list(tournament.top_players_json or []),
            "status": tournament.status,
        }


__all__ = [
    "RegenUniverseExpansionError",
    "RegenUniverseExpansionNotFoundError",
    "RegenUniverseExpansionService",
    "RegenUniverseExpansionValidationError",
]
