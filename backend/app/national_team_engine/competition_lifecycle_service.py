from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
import math
import random
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.event_backbone import build_outbox_event, defer_event_publish_until_commit
from app.core.events import DomainEvent, EventPublisher
from app.core.global_ids import global_competition_id, global_match_id
from app.global_memory.constants import COMPETITION_ADVANCED
from app.global_memory.models import NationalTeamCountryRanking
from app.ingestion.models import Country, Player
from app.models.base import utcnow
from app.models.national_team import NationalTeamCompetition, NationalTeamCompetitionEntry
from app.models.user import User
from app.national_team_engine.competition_profiles import infer_competition_family, profile_for


class NationalCompetitionLifecycleError(ValueError):
    def __init__(self, detail: str, *, reason: str) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason


@dataclass(slots=True)
class NationalCompetitionLifecycleService:
    session: Session
    event_publisher: EventPublisher | None = None

    def submit_entry(self, *, competition_id: str, actor: User, payload) -> dict[str, Any]:
        competition = self._require_competition(competition_id)
        self._validate_submission_window(competition)
        existing = self.session.scalar(
            select(NationalTeamCompetitionEntry).where(
                NationalTeamCompetitionEntry.competition_id == competition_id,
                NationalTeamCompetitionEntry.user_id == actor.id,
            )
        )
        if existing is not None and existing.locked:
            raise NationalCompetitionLifecycleError(
                "Locked competition entries cannot be updated.",
                reason="entry_locked",
            )

        country_code = payload.country_code.strip().upper()
        country_name = payload.country_name.strip()
        profile = self._competition_profile(competition)
        confederation_code = self._country_confederation(country_code)
        self._validate_confederation(
            profile=profile,
            country_code=country_code,
            confederation_code=confederation_code,
        )
        squad = self._normalize_squad(
            payload.squad,
            competition=competition,
            country_code=country_code,
        )

        entry = existing or NationalTeamCompetitionEntry(
            competition_id=competition.id,
            user_id=actor.id,
        )
        if existing is None:
            self.session.add(entry)
        entry.country_code = country_code
        entry.country_name = country_name
        entry.squad_json = squad
        entry.locked = False
        entry.qualified = False
        entry.status = "submitted"
        entry.metadata_json = {
            **dict(entry.metadata_json or {}),
            "competition_family": profile["family"],
            "confederation_code": confederation_code,
            "submitted_at": utcnow().isoformat(),
            "strength_rating": round(self._squad_strength(squad)),
        }
        self._clear_lifecycle_state(competition)
        self.session.flush()
        return self._entry_payload(entry)

    def list_entries(self, *, competition_id: str) -> list[dict[str, Any]]:
        competition = self._require_competition(competition_id)
        return [self._entry_payload(entry) for entry in self._ordered_entries(competition)]

    def lock_entries(self, *, competition_id: str) -> dict[str, Any]:
        competition = self._require_competition(competition_id)
        entries = self._ordered_entries(competition)
        if not entries:
            raise NationalCompetitionLifecycleError(
                "At least one submitted entry is required before entries can be locked.",
                reason="entries_missing",
            )

        profile = self._competition_profile(competition)
        representatives = self._default_representative_ids(entries)
        for entry in entries:
            normalized = self._normalize_squad(
                entry.squad_json,
                competition=competition,
                country_code=entry.country_code,
            )
            entry.squad_json = normalized
            entry.locked = True
            entry.qualified = False
            entry.status = "locked"
            entry.metadata_json = {
                **dict(entry.metadata_json or {}),
                "strength_rating": round(self._squad_strength(normalized)),
                "locked_at": utcnow().isoformat(),
            }

        lifecycle_state = {
            "current_stage": self._initial_stage(entries=entries, profile=profile),
            "profile": profile,
            "schedule_plan": self._schedule_plan(
                profile=profile,
                has_pre_qualifier=self._has_pre_qualifier(entries),
                has_qualifier=len(representatives) > int(profile["tournament_slots"]),
            ),
            "stage_history": [],
            "stage_results": {},
            "representative_entry_ids": representatives if not self._has_pre_qualifier(entries) else [],
            "qualified_entry_ids": [],
            "champion_entry_id": None,
            "locked_at": utcnow().isoformat(),
        }
        competition.metadata_json = {
            **dict(competition.metadata_json or {}),
            "lifecycle_state": lifecycle_state,
        }
        competition.status = "locked"
        self.session.flush()
        return self.get_lifecycle_payload(competition_id=competition_id)

    def advance_lifecycle(self, *, competition_id: str) -> dict[str, Any]:
        competition = self._require_competition(competition_id)
        if not competition.submitted_entries:
            raise NationalCompetitionLifecycleError(
                "No submitted entries are available for this competition.",
                reason="entries_missing",
            )
        if not all(entry.locked for entry in competition.submitted_entries):
            self.lock_entries(competition_id=competition_id)
            competition = self._require_competition(competition_id)

        lifecycle_state = self._lifecycle_state(competition)
        current_stage = str(lifecycle_state.get("current_stage") or "registration")
        if current_stage == "completed":
            raise NationalCompetitionLifecycleError(
                "Competition lifecycle has already completed.",
                reason="lifecycle_completed",
            )

        profile = self._competition_profile(competition)
        entries = self._ordered_entries(competition)
        entry_map = {entry.id: entry for entry in entries}

        if current_stage == "pre_qualifier":
            result = self._run_pre_qualifier(competition=competition, entries=entries)
            representative_ids = list(result["representative_entry_ids"])
            lifecycle_state["stage_results"]["pre_qualifier"] = result
            lifecycle_state["representative_entry_ids"] = representative_ids
            lifecycle_state["current_stage"] = (
                "qualifier" if len(representative_ids) > int(profile["tournament_slots"]) else "tournament"
            )
            self._append_stage_history(
                lifecycle_state,
                stage="pre_qualifier",
                summary=f"Resolved {len(representative_ids)} country representative(s).",
            )
            competition.status = "live"
        elif current_stage == "qualifier":
            representative_ids = list(
                lifecycle_state.get("representative_entry_ids") or self._default_representative_ids(entries)
            )
            representative_entries = [entry_map[entry_id] for entry_id in representative_ids if entry_id in entry_map]
            result = self._run_group_qualification(
                competition=competition,
                stage_code="qualifier",
                entries=representative_entries,
                slots=int(profile["tournament_slots"]),
                group_size=int(profile["qualifier_group_size"]),
            )
            qualified_ids = list(result["qualified_entry_ids"])
            lifecycle_state["stage_results"]["qualifier"] = result
            lifecycle_state["qualified_entry_ids"] = qualified_ids
            lifecycle_state["current_stage"] = "tournament"
            self._append_stage_history(
                lifecycle_state,
                stage="qualifier",
                summary=f"Advanced {len(qualified_ids)} team(s) into the tournament stage.",
            )
            for entry in representative_entries:
                entry.qualified = entry.id in qualified_ids
                entry.status = "qualified" if entry.qualified else "eliminated"
            competition.status = "live"
        elif current_stage == "tournament":
            tournament_ids = list(
                lifecycle_state.get("qualified_entry_ids")
                or lifecycle_state.get("representative_entry_ids")
                or self._default_representative_ids(entries)
            )
            tournament_entries = [entry_map[entry_id] for entry_id in tournament_ids if entry_id in entry_map]
            result = self._run_tournament(
                competition=competition,
                entries=tournament_entries,
                profile=profile,
            )
            champion_id = result.get("champion_entry_id")
            lifecycle_state["stage_results"]["tournament"] = result
            lifecycle_state["champion_entry_id"] = champion_id
            lifecycle_state["current_stage"] = "completed"
            self._append_stage_history(
                lifecycle_state,
                stage="tournament",
                summary=f"Completed the tournament stage and crowned {self._entry_label(entry_map.get(champion_id))}.",
            )
            competition.status = "completed"
            competition.completed_at = utcnow()
            for entry in tournament_entries:
                if champion_id and entry.id == champion_id:
                    entry.status = "champion"
                    entry.qualified = True
                else:
                    entry.status = "eliminated"
        else:
            raise NationalCompetitionLifecycleError(
                f"Unsupported lifecycle stage '{current_stage}'.",
                reason="stage_invalid",
            )

        competition.metadata_json = {
            **dict(competition.metadata_json or {}),
            "lifecycle_state": lifecycle_state,
        }
        stage_matches = self._extract_matches_from_stage_result(stage=current_stage, result=result)
        self._update_country_rankings(
            competition=competition,
            stage=current_stage,
            matches=stage_matches,
            champion_entry=entry_map.get(lifecycle_state.get("champion_entry_id")),
        )
        self._emit_competition_advanced_event(
            competition=competition,
            stage=current_stage,
            next_stage=str(lifecycle_state.get("current_stage") or current_stage),
            matches=stage_matches,
            champion_entry=entry_map.get(lifecycle_state.get("champion_entry_id")),
        )
        self.session.flush()
        return self.get_lifecycle_payload(competition_id=competition_id)

    def get_lifecycle_payload(self, *, competition_id: str) -> dict[str, Any]:
        competition = self._require_competition(competition_id)
        entries = self._ordered_entries(competition)
        lifecycle_state = self._lifecycle_state(competition)
        entry_map = {entry.id: entry for entry in entries}
        representative_ids = list(lifecycle_state.get("representative_entry_ids") or [])
        qualified_ids = list(lifecycle_state.get("qualified_entry_ids") or [])
        champion_id = lifecycle_state.get("champion_entry_id")
        return {
            "competition": competition,
            "profile": self._competition_profile(competition),
            "current_stage": str(lifecycle_state.get("current_stage") or "registration"),
            "submitted_entries": [self._entry_payload(entry) for entry in entries],
            "representative_entries": [
                self._entry_payload(entry_map[entry_id]) for entry_id in representative_ids if entry_id in entry_map
            ],
            "qualified_entries": [
                self._entry_payload(entry_map[entry_id]) for entry_id in qualified_ids if entry_id in entry_map
            ],
            "champion_entry_id": champion_id,
            "schedule_plan": list(lifecycle_state.get("schedule_plan") or []),
            "stage_history": list(lifecycle_state.get("stage_history") or []),
            "stage_results": dict(lifecycle_state.get("stage_results") or {}),
        }

    def list_country_rankings(self, *, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(NationalTeamCountryRanking)
            .order_by(
                NationalTeamCountryRanking.elo_rating.desc(),
                NationalTeamCountryRanking.titles.desc(),
                NationalTeamCountryRanking.wins.desc(),
                NationalTeamCountryRanking.country_name.asc(),
            )
            .limit(limit)
        ).all()
        return [
            {
                "country_code": item.country_code,
                "country_name": item.country_name,
                "elo_rating": round(float(item.elo_rating), 2),
                "matches_played": item.matches_played,
                "wins": item.wins,
                "draws": item.draws,
                "losses": item.losses,
                "titles": item.titles,
                "metadata_json": dict(item.metadata_json or {}),
            }
            for item in rows
        ]

    def _require_competition(self, competition_id: str) -> NationalTeamCompetition:
        competition = self.session.scalar(
            select(NationalTeamCompetition)
            .where(NationalTeamCompetition.id == competition_id)
            .options(selectinload(NationalTeamCompetition.submitted_entries))
            .execution_options(populate_existing=True)
        )
        if competition is None:
            raise NationalCompetitionLifecycleError(
                "National team competition was not found.",
                reason="competition_not_found",
            )
        return competition

    @staticmethod
    def _validate_submission_window(competition: NationalTeamCompetition) -> None:
        now = utcnow()
        entry_opens_at = NationalCompetitionLifecycleService._as_utc_datetime(competition.entry_opens_at)
        entry_closes_at = NationalCompetitionLifecycleService._as_utc_datetime(competition.entry_closes_at)
        if entry_opens_at is not None and entry_opens_at > now:
            raise NationalCompetitionLifecycleError(
                "Competition entry is not open yet.",
                reason="competition_entry_not_open",
            )
        if entry_closes_at is not None and entry_closes_at < now:
            raise NationalCompetitionLifecycleError(
                "Competition entry is closed.",
                reason="competition_entry_closed",
            )
        if competition.completed_at is not None:
            raise NationalCompetitionLifecycleError(
                "Competition has already completed.",
                reason="competition_completed",
            )
        lifecycle_state = dict((competition.metadata_json or {}).get("lifecycle_state") or {})
        competition_status = str(competition.status or "").strip().lower()
        if lifecycle_state or competition_status in {"locked", "live"}:
            raise NationalCompetitionLifecycleError(
                "Competition entries are locked once qualifiers have started.",
                reason="entry_locked",
            )

    @staticmethod
    def _as_utc_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _competition_profile(self, competition: NationalTeamCompetition) -> dict[str, Any]:
        family = infer_competition_family(
            key=competition.key,
            title=competition.title,
            metadata_json=dict(competition.metadata_json or {}),
        )
        return profile_for(
            family=family,
            age_band=competition.age_band,
            metadata_json=dict(competition.metadata_json or {}),
        )

    def _ordered_entries(self, competition: NationalTeamCompetition) -> list[NationalTeamCompetitionEntry]:
        entries = list(competition.submitted_entries or [])
        entries.sort(
            key=lambda entry: (
                entry.country_code,
                entry.country_name.lower(),
                entry.created_at,
                entry.user_id,
            )
        )
        return entries

    def _country_confederation(self, country_code: str) -> str | None:
        code = country_code.strip().upper()
        if not code:
            return None
        return self.session.scalar(
            select(Country.confederation_code).where(
                or_(
                    func.upper(Country.alpha2_code) == code,
                    func.upper(Country.alpha3_code) == code,
                    func.upper(Country.fifa_code) == code,
                )
            )
        )

    @staticmethod
    def _validate_confederation(*, profile: dict[str, Any], country_code: str, confederation_code: str | None) -> None:
        eligible = list(profile.get("eligible_confederations") or [])
        if not eligible or confederation_code is None:
            return
        if confederation_code not in eligible:
            raise NationalCompetitionLifecycleError(
                f"Country '{country_code}' is not eligible for this competition family.",
                reason="country_not_eligible",
            )

    def _normalize_squad(
        self,
        raw_squad: list[Any],
        *,
        competition: NationalTeamCompetition,
        country_code: str,
    ) -> list[dict[str, Any]]:
        metadata = dict(competition.metadata_json or {})
        minimum_squad_size = max(1, int(metadata.get("minimum_squad_size", 18)))
        maximum_squad_size = max(minimum_squad_size, int(metadata.get("maximum_squad_size", 30)))
        if not raw_squad:
            raise NationalCompetitionLifecycleError(
                "Competition squads must include at least one player.",
                reason="squad_missing",
            )
        if len(raw_squad) < minimum_squad_size:
            raise NationalCompetitionLifecycleError(
                f"Competition squad is smaller than the minimum size of {minimum_squad_size}.",
                reason="squad_too_small",
            )
        if len(raw_squad) > maximum_squad_size:
            raise NationalCompetitionLifecycleError(
                f"Competition squad exceeds the maximum size of {maximum_squad_size}.",
                reason="squad_too_large",
            )

        seen_player_ids: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(raw_squad, start=1):
            record = item.model_dump() if hasattr(item, "model_dump") else dict(item)
            player_id = str(record.get("player_id") or "").strip() or None
            player_name = str(record.get("player_name") or "").strip()
            date_of_birth = record.get("date_of_birth")
            explicit_age = record.get("age")
            overall_rating = record.get("overall_rating")
            position = str(record.get("position") or "").strip() or None
            player = self.session.get(Player, player_id) if player_id else None

            if player_id:
                if player is None:
                    raise NationalCompetitionLifecycleError(
                        f"Player '{player_id}' was not found.",
                        reason="player_not_found",
                    )
                if player_id in seen_player_ids:
                    raise NationalCompetitionLifecycleError(
                        "Competition squads cannot contain duplicate players.",
                        reason="duplicate_player",
                    )
                seen_player_ids.add(player_id)
                if not player_name:
                    player_name = (
                        player.canonical_display_name
                        or player.short_name
                        or " ".join(part for part in [player.first_name, player.last_name] if part)
                        or player.full_name
                    )
                if date_of_birth is None:
                    date_of_birth = player.date_of_birth
                if overall_rating is None:
                    overall_rating = self._player_rating(player)
                if position is None:
                    position = player.normalized_position or player.position
            elif not player_name:
                raise NationalCompetitionLifecycleError(
                    f"Squad player #{index} is missing a player name.",
                    reason="player_name_missing",
                )

            resolved_age = self._resolve_player_age(
                date_of_birth=date_of_birth,
                explicit_age=explicit_age,
                competition=competition,
            )
            self._validate_age_band(
                competition=competition,
                player_name=player_name,
                resolved_age=resolved_age,
            )

            normalized.append(
                {
                    "player_id": player_id,
                    "player_name": player_name,
                    "country_code": country_code,
                    "date_of_birth": (
                        date_of_birth.isoformat() if hasattr(date_of_birth, "isoformat") else date_of_birth
                    ),
                    "age": explicit_age,
                    "resolved_age": resolved_age,
                    "overall_rating": max(40, min(int(overall_rating or 70), 99)),
                    "position": position,
                    "metadata_json": dict(record.get("metadata_json") or {}),
                }
            )
        return normalized

    @staticmethod
    def _player_rating(player: Player) -> int:
        market_value = float(player.current_market_reference_value or player.market_value_eur or 0.0)
        if market_value >= 90_000_000:
            return 91
        if market_value >= 60_000_000:
            return 88
        if market_value >= 35_000_000:
            return 85
        if market_value >= 20_000_000:
            return 82
        if market_value >= 10_000_000:
            return 79
        if market_value >= 5_000_000:
            return 76
        if market_value >= 2_000_000:
            return 73
        return 70

    def _resolve_player_age(
        self,
        *,
        date_of_birth,
        explicit_age: int | None,
        competition: NationalTeamCompetition,
    ) -> int | None:
        if explicit_age is not None:
            return int(explicit_age)
        if date_of_birth is None:
            return None
        if isinstance(date_of_birth, str):
            date_of_birth = date.fromisoformat(date_of_birth)
        reference_date = self._reference_date(competition)
        return self._calculate_age(date_of_birth, reference_date)

    @staticmethod
    def _calculate_age(date_of_birth: date, reference_date: date) -> int:
        years = reference_date.year - date_of_birth.year
        birthday_passed = (reference_date.month, reference_date.day) >= (date_of_birth.month, date_of_birth.day)
        return years if birthday_passed else years - 1

    @staticmethod
    def _reference_date(competition: NationalTeamCompetition) -> date:
        if competition.kickoff_at is not None:
            return competition.kickoff_at.date()
        if competition.entry_closes_at is not None:
            return competition.entry_closes_at.date()
        return utcnow().date()

    @staticmethod
    def _validate_age_band(
        *,
        competition: NationalTeamCompetition,
        player_name: str,
        resolved_age: int | None,
    ) -> None:
        age_band = str(competition.age_band or "senior").strip().lower()
        if age_band not in {"u17", "u20"}:
            return
        if resolved_age is None:
            raise NationalCompetitionLifecycleError(
                f"Player '{player_name}' is missing age data for an age-locked competition.",
                reason="player_age_missing",
            )
        limit = 17 if age_band == "u17" else 20
        if resolved_age > limit:
            raise NationalCompetitionLifecycleError(
                f"Player '{player_name}' exceeds the {age_band.upper()} age limit.",
                reason="invalid_squad_age",
            )

    @staticmethod
    def _squad_strength(squad: list[dict[str, Any]]) -> float:
        if not squad:
            return 65.0
        ratings = [int(item.get("overall_rating") or 70) for item in squad]
        return (sum(ratings) / len(ratings)) + min(len(ratings), 23) * 0.12

    def _entry_strength(self, entry: NationalTeamCompetitionEntry) -> float:
        base_strength = self._squad_strength(list(entry.squad_json or []))
        ranking = self._country_ranking(entry.country_code, country_name=entry.country_name, create=False)
        if ranking is None:
            return base_strength
        seeding_bonus = max(-4.0, min(6.0, (float(ranking.elo_rating) - 1500.0) / 80.0))
        return base_strength + seeding_bonus

    @staticmethod
    def _clear_lifecycle_state(competition: NationalTeamCompetition) -> None:
        metadata = dict(competition.metadata_json or {})
        metadata.pop("lifecycle_state", None)
        competition.metadata_json = metadata

    @staticmethod
    def _lifecycle_state(competition: NationalTeamCompetition) -> dict[str, Any]:
        return dict((competition.metadata_json or {}).get("lifecycle_state") or {})

    def _default_representative_ids(self, entries: list[NationalTeamCompetitionEntry]) -> list[str]:
        grouped: dict[str, list[NationalTeamCompetitionEntry]] = {}
        for entry in entries:
            grouped.setdefault(entry.country_code, []).append(entry)
        return [
            sorted(group_entries, key=lambda item: (-self._entry_strength(item), item.created_at, item.id))[0].id
            for _country_code, group_entries in sorted(grouped.items())
        ]

    @staticmethod
    def _has_pre_qualifier(entries: list[NationalTeamCompetitionEntry]) -> bool:
        counts: dict[str, int] = {}
        for entry in entries:
            counts[entry.country_code] = counts.get(entry.country_code, 0) + 1
        return any(count > 1 for count in counts.values())

    def _initial_stage(self, *, entries: list[NationalTeamCompetitionEntry], profile: dict[str, Any]) -> str:
        representatives = self._default_representative_ids(entries)
        if self._has_pre_qualifier(entries):
            return "pre_qualifier"
        if len(representatives) > int(profile["tournament_slots"]):
            return "qualifier"
        return "tournament"

    @staticmethod
    def _schedule_plan(
        *, profile: dict[str, Any], has_pre_qualifier: bool, has_qualifier: bool
    ) -> list[dict[str, Any]]:
        week = int(profile["preferred_cycle_week"])
        plan: list[dict[str, Any]] = []
        if has_pre_qualifier:
            plan.append({"stage": "pre_qualifier", "week": week})
            week += 1
        if has_qualifier:
            plan.append({"stage": "qualifier", "week": week})
            week += 1
        plan.append({"stage": "tournament", "week": week})
        return plan

    def _run_pre_qualifier(
        self,
        *,
        competition: NationalTeamCompetition,
        entries: list[NationalTeamCompetitionEntry],
    ) -> dict[str, Any]:
        grouped: dict[str, list[NationalTeamCompetitionEntry]] = {}
        for entry in entries:
            grouped.setdefault(entry.country_code, []).append(entry)

        representatives: list[str] = []
        country_results: list[dict[str, Any]] = []
        for country_code, country_entries in sorted(grouped.items()):
            ordered = sorted(country_entries, key=lambda item: (-self._entry_strength(item), item.created_at, item.id))
            if len(ordered) == 1:
                winner = ordered[0]
                winner.status = "representative"
                winner.qualified = False
                representatives.append(winner.id)
                country_results.append(
                    {
                        "country_code": country_code,
                        "country_name": winner.country_name,
                        "entrant_count": 1,
                        "winner_entry_id": winner.id,
                        "matches": [],
                    }
                )
                continue

            current_round: list[NationalTeamCompetitionEntry | None] = list(ordered)
            while len(current_round) < self._next_power_of_two(len(current_round)):
                current_round.append(None)

            round_number = 1
            round_results: list[dict[str, Any]] = []
            while len(current_round) > 1:
                winners: list[NationalTeamCompetitionEntry] = []
                matches: list[dict[str, Any]] = []
                pair_count = len(current_round) // 2
                for index in range(pair_count):
                    home = current_round[index]
                    away = current_round[-(index + 1)]
                    if home is None and away is None:
                        continue
                    if home is None:
                        assert away is not None
                        winners.append(away)
                        matches.append(
                            self._bye_match(stage="pre_qualifier", round_label=f"round_{round_number}", winner=away)
                        )
                        continue
                    if away is None:
                        winners.append(home)
                        matches.append(
                            self._bye_match(stage="pre_qualifier", round_label=f"round_{round_number}", winner=home)
                        )
                        continue
                    match = self._simulate_match(
                        competition=competition,
                        stage_code="pre_qualifier",
                        stage_label=f"round_{round_number}",
                        left=home,
                        right=away,
                        allow_draw=False,
                    )
                    winners.append(home if match["winner_entry_id"] == home.id else away)
                    matches.append(match)
                round_results.append({"round": round_number, "matches": matches})
                current_round = winners
                round_number += 1

            winner = current_round[0]
            assert winner is not None
            representatives.append(winner.id)
            for entry in ordered:
                entry.status = "representative" if entry.id == winner.id else "eliminated"
                entry.qualified = False
            country_results.append(
                {
                    "country_code": country_code,
                    "country_name": winner.country_name,
                    "entrant_count": len(ordered),
                    "winner_entry_id": winner.id,
                    "rounds": round_results,
                }
            )
        return {
            "representative_entry_ids": representatives,
            "countries": country_results,
        }

    def _run_group_qualification(
        self,
        *,
        competition: NationalTeamCompetition,
        stage_code: str,
        entries: list[NationalTeamCompetitionEntry],
        slots: int,
        group_size: int,
    ) -> dict[str, Any]:
        if len(entries) <= slots:
            qualified_ids = [entry.id for entry in entries]
            return {
                "groups": [],
                "qualified_entry_ids": qualified_ids,
                "summary": "All representatives qualified directly because entries did not exceed tournament slots.",
            }

        group_count = max(2, math.ceil(len(entries) / max(group_size, 2)))
        group_count = min(group_count, len(entries))
        groups = self._seed_groups(entries, group_count)
        group_results, ranked_rows = self._run_group_stage(
            competition=competition,
            stage_code=stage_code,
            groups=groups,
            advance_per_group=1,
            best_third_slots=0,
        )
        all_rows = [dict(row) for group in group_results for row in group["standings"]]

        all_rows.sort(
            key=lambda row: (
                -int(row["group_rank"] == 1),
                -int(row["points"]),
                -int(row["goal_difference"]),
                -int(row["goals_for"]),
                -float(row["strength_rating"]),
                row["country_name"].lower(),
            )
        )
        qualified_ids = [row["entry_id"] for row in all_rows[:slots]]
        for group in group_results:
            for row in group["standings"]:
                row["qualified"] = row["entry_id"] in qualified_ids
        return {
            "groups": group_results,
            "qualified_entry_ids": qualified_ids,
            "summary": f"Qualified {len(qualified_ids)} team(s) from {len(entries)} representative(s).",
        }

    def _run_tournament(
        self,
        *,
        competition: NationalTeamCompetition,
        entries: list[NationalTeamCompetitionEntry],
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        if len(entries) < 2:
            raise NationalCompetitionLifecycleError(
                "At least two teams are required to run the tournament stage.",
                reason="insufficient_tournament_entries",
            )

        if len(entries) == 2:
            final_match = self._simulate_match(
                competition=competition,
                stage_code="tournament",
                stage_label="final",
                left=entries[0],
                right=entries[1],
                allow_draw=False,
            )
            return {
                "groups": [],
                "knockout_rounds": [{"stage": "final", "matches": [final_match]}],
                "champion_entry_id": final_match["winner_entry_id"],
            }

        group_count = max(1, math.ceil(len(entries) / max(int(profile["group_size"]), 2)))
        groups = self._seed_groups(entries, group_count)
        group_results, ranked_rows = self._run_group_stage(
            competition=competition,
            stage_code="tournament",
            groups=groups,
            advance_per_group=int(profile["advance_per_group"]),
            best_third_slots=int(profile["best_third_slots"]),
        )
        knockout_entry_ids = [row["entry_id"] for row in ranked_rows]
        knockout_entries = {entry.id: entry for entry in entries}
        bracket_entries = [
            knockout_entries[entry_id] for entry_id in knockout_entry_ids if entry_id in knockout_entries
        ]
        knockout_rounds, champion_id = self._run_knockout(
            competition=competition,
            stage_code="tournament",
            entries=bracket_entries,
        )
        return {
            "groups": group_results,
            "knockout_rounds": knockout_rounds,
            "champion_entry_id": champion_id,
        }

    def _seed_groups(
        self,
        entries: list[NationalTeamCompetitionEntry],
        group_count: int,
    ) -> list[list[NationalTeamCompetitionEntry]]:
        ordered = sorted(entries, key=lambda item: (-self._entry_strength(item), item.country_name.lower(), item.id))
        groups: list[list[NationalTeamCompetitionEntry]] = [[] for _ in range(group_count)]
        for index, entry in enumerate(ordered):
            block = index // group_count
            slot = index % group_count
            group_index = slot if block % 2 == 0 else (group_count - slot - 1)
            groups[group_index].append(entry)
        return [group for group in groups if group]

    def _run_group_stage(
        self,
        *,
        competition: NationalTeamCompetition,
        stage_code: str,
        groups: list[list[NationalTeamCompetitionEntry]],
        advance_per_group: int,
        best_third_slots: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        best_remaining: list[dict[str, Any]] = []
        qualified_rows: list[dict[str, Any]] = []
        rendered_groups: list[dict[str, Any]] = []
        for index, group_entries in enumerate(groups):
            group_name = chr(ord("A") + index)
            standings = {
                entry.id: {
                    "entry_id": entry.id,
                    "country_code": entry.country_code,
                    "country_name": entry.country_name,
                    "played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "goal_difference": 0,
                    "points": 0,
                    "strength_rating": round(self._entry_strength(entry), 2),
                }
                for entry in group_entries
            }
            matches: list[dict[str, Any]] = []
            for home_index in range(len(group_entries)):
                for away_index in range(home_index + 1, len(group_entries)):
                    home = group_entries[home_index]
                    away = group_entries[away_index]
                    match = self._simulate_match(
                        competition=competition,
                        stage_code=stage_code,
                        stage_label=f"group_{group_name}",
                        left=home,
                        right=away,
                        allow_draw=True,
                    )
                    matches.append(match)
                    self._apply_group_result(standings[home.id], standings[away.id], match)

            ordered_rows = sorted(
                standings.values(),
                key=lambda row: (
                    -int(row["points"]),
                    -int(row["goal_difference"]),
                    -int(row["goals_for"]),
                    -float(row["strength_rating"]),
                    row["country_name"].lower(),
                ),
            )
            for rank, row in enumerate(ordered_rows, start=1):
                row["group"] = group_name
                row["group_rank"] = rank
                if rank <= advance_per_group:
                    qualified_rows.append(dict(row))
                elif rank == advance_per_group + 1:
                    best_remaining.append(dict(row))

            rendered_groups.append(
                {
                    "group": group_name,
                    "teams": [
                        {
                            "entry_id": entry.id,
                            "country_code": entry.country_code,
                            "country_name": entry.country_name,
                        }
                        for entry in group_entries
                    ],
                    "matches": matches,
                    "standings": ordered_rows,
                }
            )

        if best_third_slots:
            best_remaining.sort(
                key=lambda row: (
                    -int(row["points"]),
                    -int(row["goal_difference"]),
                    -int(row["goals_for"]),
                    -float(row["strength_rating"]),
                    row["country_name"].lower(),
                )
            )
            qualified_rows.extend(best_remaining[:best_third_slots])

        qualified_rows.sort(
            key=lambda row: (
                int(row["group_rank"]),
                -int(row["points"]),
                -int(row["goal_difference"]),
                -int(row["goals_for"]),
                -float(row["strength_rating"]),
                row["country_name"].lower(),
            )
        )
        qualified_ids = {row["entry_id"] for row in qualified_rows}
        for group in rendered_groups:
            for row in group["standings"]:
                row["advanced"] = row["entry_id"] in qualified_ids
        return rendered_groups, qualified_rows

    @staticmethod
    def _apply_group_result(home: dict[str, Any], away: dict[str, Any], match: dict[str, Any]) -> None:
        home["played"] += 1
        away["played"] += 1
        home["goals_for"] += int(match["home_score"])
        home["goals_against"] += int(match["away_score"])
        away["goals_for"] += int(match["away_score"])
        away["goals_against"] += int(match["home_score"])
        home["goal_difference"] = home["goals_for"] - home["goals_against"]
        away["goal_difference"] = away["goals_for"] - away["goals_against"]
        if match["home_score"] > match["away_score"]:
            home["wins"] += 1
            home["points"] += 3
            away["losses"] += 1
        elif match["away_score"] > match["home_score"]:
            away["wins"] += 1
            away["points"] += 3
            home["losses"] += 1
        else:
            home["draws"] += 1
            away["draws"] += 1
            home["points"] += 1
            away["points"] += 1

    def _run_knockout(
        self,
        *,
        competition: NationalTeamCompetition,
        stage_code: str,
        entries: list[NationalTeamCompetitionEntry],
    ) -> tuple[list[dict[str, Any]], str | None]:
        if not entries:
            return [], None
        ordered = list(entries)
        bracket_size = self._next_power_of_two(len(ordered))
        while len(ordered) < bracket_size:
            ordered.append(None)

        rounds: list[dict[str, Any]] = []
        current = ordered
        while len(current) > 1:
            round_stage = self._round_label(len(current))
            winners: list[NationalTeamCompetitionEntry] = []
            matches: list[dict[str, Any]] = []
            for index in range(0, len(current), 2):
                left = current[index]
                right = current[index + 1]
                if left is None and right is None:
                    continue
                if left is None:
                    assert right is not None
                    winners.append(right)
                    matches.append(self._bye_match(stage=stage_code, round_label=round_stage, winner=right))
                    continue
                if right is None:
                    winners.append(left)
                    matches.append(self._bye_match(stage=stage_code, round_label=round_stage, winner=left))
                    continue
                match = self._simulate_match(
                    competition=competition,
                    stage_code=stage_code,
                    stage_label=round_stage,
                    left=left,
                    right=right,
                    allow_draw=False,
                )
                winners.append(left if match["winner_entry_id"] == left.id else right)
                matches.append(match)
            rounds.append({"stage": round_stage, "matches": matches})
            current = winners
        champion = current[0] if current else None
        return rounds, champion.id if champion is not None else None

    def _simulate_match(
        self,
        *,
        competition: NationalTeamCompetition,
        stage_code: str,
        stage_label: str,
        left: NationalTeamCompetitionEntry,
        right: NationalTeamCompetitionEntry,
        allow_draw: bool,
    ) -> dict[str, Any]:
        seed = self._stable_seed(competition.id, stage_code, stage_label, left.id, right.id)
        rng = random.Random(seed)
        left_strength = self._entry_strength(left)
        right_strength = self._entry_strength(right)
        left_score = self._simulate_goals(rng=rng, own_strength=left_strength, other_strength=right_strength)
        right_score = self._simulate_goals(rng=rng, own_strength=right_strength, other_strength=left_strength)
        resolution = "regular_time"
        winner_entry_id: str | None = None
        if left_score > right_score:
            winner_entry_id = left.id
        elif right_score > left_score:
            winner_entry_id = right.id
        elif allow_draw:
            resolution = "draw"
        else:
            resolution = "penalties"
            if (left_strength - right_strength) + rng.uniform(-8.0, 8.0) >= 0:
                left_score += 1
                winner_entry_id = left.id
            else:
                right_score += 1
                winner_entry_id = right.id

        return {
            "stage": stage_label,
            "home_entry_id": left.id,
            "home_country_code": left.country_code,
            "home_country_name": left.country_name,
            "away_entry_id": right.id,
            "away_country_code": right.country_code,
            "away_country_name": right.country_name,
            "home_score": left_score,
            "away_score": right_score,
            "winner_entry_id": winner_entry_id,
            "resolution": resolution,
        }

    @staticmethod
    def _simulate_goals(*, rng: random.Random, own_strength: float, other_strength: float) -> int:
        delta = (own_strength - other_strength) / 12.0
        baseline = 1.1 + max(-0.6, min(0.8, delta))
        noise = rng.random() * 2.2 + rng.random() * 1.2
        goals = int(round(max(0.0, baseline + noise - 0.9)))
        return min(goals, 6)

    @staticmethod
    def _bye_match(*, stage: str, round_label: str, winner: NationalTeamCompetitionEntry) -> dict[str, Any]:
        return {
            "stage": round_label,
            "home_entry_id": winner.id,
            "home_country_code": winner.country_code,
            "home_country_name": winner.country_name,
            "away_entry_id": None,
            "away_country_code": None,
            "away_country_name": None,
            "home_score": 1,
            "away_score": 0,
            "winner_entry_id": winner.id,
            "resolution": f"{stage}_bye",
        }

    @staticmethod
    def _next_power_of_two(value: int) -> int:
        power = 1
        while power < value:
            power *= 2
        return power

    @staticmethod
    def _round_label(field_size: int) -> str:
        mapping = {
            2: "final",
            4: "semifinal",
            8: "quarterfinal",
            16: "round_of_16",
            32: "round_of_32",
            64: "round_of_64",
        }
        return mapping.get(field_size, f"round_of_{field_size}")

    @staticmethod
    def _stable_seed(*parts: str) -> int:
        digest = sha256("|".join(parts).encode("utf-8")).hexdigest()
        return int(digest[:16], 16)

    def _country_ranking(
        self,
        country_code: str,
        *,
        country_name: str | None = None,
        create: bool = True,
    ) -> NationalTeamCountryRanking | None:
        normalized = country_code.strip().upper()
        if not normalized:
            return None
        ranking = self.session.scalar(
            select(NationalTeamCountryRanking).where(NationalTeamCountryRanking.country_code == normalized)
        )
        if ranking is not None or not create:
            return ranking
        ranking = NationalTeamCountryRanking(
            country_code=normalized,
            country_name=(country_name or normalized).strip() or normalized,
            elo_rating=1500.0,
            metadata_json={},
        )
        self.session.add(ranking)
        self.session.flush()
        return ranking

    def _update_country_rankings(
        self,
        *,
        competition: NationalTeamCompetition,
        stage: str,
        matches: list[dict[str, Any]],
        champion_entry: NationalTeamCompetitionEntry | None,
    ) -> None:
        k_factor = {"pre_qualifier": 16.0, "qualifier": 20.0, "tournament": 24.0}.get(stage, 20.0)
        for match in matches:
            if str(match.get("resolution") or "").endswith("_bye"):
                continue
            home_code = str(match.get("home_country_code") or "").strip().upper()
            away_code = str(match.get("away_country_code") or "").strip().upper()
            if not home_code or not away_code:
                continue
            home = self._country_ranking(home_code, country_name=str(match.get("home_country_name") or home_code))
            away = self._country_ranking(away_code, country_name=str(match.get("away_country_name") or away_code))
            if home is None or away is None:
                continue

            home_rating = float(home.elo_rating)
            away_rating = float(away.elo_rating)
            expected_home = 1.0 / (1.0 + 10.0 ** ((away_rating - home_rating) / 400.0))
            expected_away = 1.0 - expected_home
            home_score = int(match.get("home_score") or 0)
            away_score = int(match.get("away_score") or 0)
            if home_score > away_score:
                actual_home, actual_away = 1.0, 0.0
                home.wins += 1
                away.losses += 1
            elif away_score > home_score:
                actual_home, actual_away = 0.0, 1.0
                away.wins += 1
                home.losses += 1
            else:
                actual_home = actual_away = 0.5
                home.draws += 1
                away.draws += 1
            home.matches_played += 1
            away.matches_played += 1
            home.elo_rating = round(home_rating + k_factor * (actual_home - expected_home), 4)
            away.elo_rating = round(away_rating + k_factor * (actual_away - expected_away), 4)
            home.last_competition_id = competition.id
            away.last_competition_id = competition.id
            home.metadata_json = {**dict(home.metadata_json or {}), "last_stage": stage}
            away.metadata_json = {**dict(away.metadata_json or {}), "last_stage": stage}

        if champion_entry is not None and stage == "tournament":
            champion = self._country_ranking(
                champion_entry.country_code,
                country_name=champion_entry.country_name,
            )
            if champion is not None:
                champion.titles += 1
                champion.last_competition_id = competition.id
                champion.metadata_json = {
                    **dict(champion.metadata_json or {}),
                    "last_title_season": competition.season_label,
                    "last_title_competition": competition.title,
                }

    def _extract_matches_from_stage_result(self, *, stage: str, result: dict[str, Any]) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        if stage == "pre_qualifier":
            for country in list(result.get("countries") or []):
                for round_payload in list(country.get("rounds") or []):
                    matches.extend(dict(item) for item in list(round_payload.get("matches") or []))
            return matches
        for group in list(result.get("groups") or []):
            matches.extend(dict(item) for item in list(group.get("matches") or []))
        for round_payload in list(result.get("knockout_rounds") or []):
            matches.extend(dict(item) for item in list(round_payload.get("matches") or []))
        return matches

    def _emit_competition_advanced_event(
        self,
        *,
        competition: NationalTeamCompetition,
        stage: str,
        next_stage: str,
        matches: list[dict[str, Any]],
        champion_entry: NationalTeamCompetitionEntry | None,
    ) -> None:
        if self.event_publisher is None:
            return
        payload_matches = [
            {
                **dict(match),
                "global_match_id": self._global_stage_match_id(competition.id, stage, match),
            }
            for match in matches
        ]
        event = DomainEvent(
            name=COMPETITION_ADVANCED,
            payload={
                "competition_id": competition.id,
                "global_competition_id": global_competition_id(competition.id),
                "competition_title": competition.title,
                "stage": stage,
                "next_stage": next_stage,
                "matches": payload_matches,
                "champion_entry_id": champion_entry.id if champion_entry is not None else None,
                "champion_country_code": champion_entry.country_code if champion_entry is not None else None,
                "champion_country_name": champion_entry.country_name if champion_entry is not None else None,
            },
            aggregate_id=competition.id,
            aggregate_type="national_team_competition",
            producer="national_team_lifecycle",
            partition_key=competition.id,
        )
        self.session.add(build_outbox_event(domain_event=event))
        defer_event_publish_until_commit(self.session, publisher=self.event_publisher, event=event)

    def _global_stage_match_id(self, competition_id: str, stage: str, match: dict[str, Any]) -> str:
        key = ":".join(
            [
                competition_id,
                stage,
                str(match.get("stage") or ""),
                str(match.get("home_entry_id") or ""),
                str(match.get("away_entry_id") or ""),
            ]
        )
        return global_match_id(key)

    @staticmethod
    def _append_stage_history(lifecycle_state: dict[str, Any], *, stage: str, summary: str) -> None:
        history = list(lifecycle_state.get("stage_history") or [])
        history.append(
            {
                "stage": stage,
                "completed_at": utcnow().isoformat(),
                "summary": summary,
            }
        )
        lifecycle_state["stage_history"] = history

    def _entry_payload(self, entry: NationalTeamCompetitionEntry) -> dict[str, Any]:
        return {
            "id": entry.id,
            "competition_id": entry.competition_id,
            "user_id": entry.user_id,
            "country_code": entry.country_code,
            "country_name": entry.country_name,
            "locked": entry.locked,
            "qualified": entry.qualified,
            "status": entry.status,
            "strength_rating": round(self._entry_strength(entry), 2),
            "squad": [self._player_payload(item) for item in list(entry.squad_json or [])],
            "metadata_json": dict(entry.metadata_json or {}),
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
        }

    @staticmethod
    def _player_payload(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "player_id": item.get("player_id"),
            "player_name": item.get("player_name"),
            "date_of_birth": item.get("date_of_birth"),
            "age": item.get("age"),
            "resolved_age": item.get("resolved_age"),
            "overall_rating": item.get("overall_rating"),
            "position": item.get("position"),
            "metadata_json": dict(item.get("metadata_json") or {}),
        }

    @staticmethod
    def _entry_label(entry: NationalTeamCompetitionEntry | None) -> str:
        if entry is None:
            return "an unknown champion"
        return entry.country_name
