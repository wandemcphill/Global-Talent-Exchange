from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.event_backbone import build_outbox_event, defer_event_publish_until_commit
from app.core.events import DomainEvent, EventPublisher
from app.core.global_ids import global_competition_id, global_player_id
from app.global_memory.constants import DYNASTY_UPDATED, PLAYER_EVOLVED, REGEN_PROMOTED
from app.global_memory.models import (
    GlobalCompetitionEntry,
    GlobalPlayerRental,
    GlobalRegenEvolution,
    PlayerHistory,
    UserDynasty,
)
from app.global_memory.schemas import (
    ClubHistoryView,
    CompetitionEntryResultView,
    CompetitionEnterRequest,
    CompetitionHistoryView,
    CompetitionListItemView,
    DynastyLeaderboardEntryView,
    DynastyTitleView,
    HallOfFamePlayerView,
    NationalPoolPlayerView,
    PlayerCareerArcView,
    PlayerHistoryEntryView,
    PlayerHistoryResponseView,
    PlayerPerformanceTimelineEntryView,
    PlayerRentRequest,
    PlayerRentResultView,
    RegenEvolutionView,
    UserDynastyView,
)
from app.ingestion.models import Competition, Country, Player
from app.models.club_hall_of_fame import ClubHallOfFameEntry
from app.models.club_profile import ClubProfile
from app.models.player_cards import PlayerCard
from app.models.player_lifecycle_event import PlayerLifecycleEvent
from app.models.regen import RegenOnboardingFlag, RegenProfile
from app.models.user import User
from app.services.club_hall_of_fame_service import ClubHallOfFameService

if TYPE_CHECKING:
    from app.schemas.player_lifecycle import PlayerCareerSummaryView

_PRESEEDED_TYPES = {"starter_bundle", "starter_regen", "preseeded"}
# Only a rented starter regen is excluded from the tradable-promotion path below: it isn't
# owned outright, so it shouldn't convert into a permanently tradable unique asset. Owned
# starter_bundle/starter_regen players are meant to graduate into tradable assets by starring
# in a title-winning campaign, same as any other preseeded regen.
_STARTER_REGEN_TYPES = {"starter_rental"}
_PEAK_AGE_BY_POSITION = {
    "GK": (28, 32),
    "CB": (27, 31),
    "DM": (26, 30),
    "CM": (25, 29),
    "AM": (24, 28),
    "RB": (24, 29),
    "LB": (24, 29),
    "RW": (23, 27),
    "LW": (23, 27),
    "ST": (24, 29),
}


class GlobalMemoryError(ValueError):
    pass


class GlobalMemoryNotFoundError(GlobalMemoryError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class GlobalMemoryService:
    session: Session
    event_publisher: EventPublisher | None = None

    def list_competitions(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        country_code: str | None = None,
        age_bracket: str | None = None,
    ) -> tuple[CompetitionListItemView, ...]:
        stmt = (
            select(Competition, Country.alpha2_code)
            .outerjoin(Country, Country.id == Competition.country_id)
            .order_by(Competition.is_major.desc(), Competition.competition_strength.desc(), Competition.name.asc())
            .offset(offset)
            .limit(limit)
        )
        if country_code:
            stmt = stmt.where(func.upper(Country.alpha2_code) == country_code.upper())
        if age_bracket:
            stmt = stmt.where(func.lower(func.coalesce(Competition.age_bracket, "")) == age_bracket.lower())
        rows = self.session.execute(stmt).all()
        return tuple(
            CompetitionListItemView(
                id=competition.id,
                global_competition_id=global_competition_id(competition.id),
                name=competition.name,
                slug=competition.slug,
                competition_type=competition.competition_type,
                age_bracket=competition.age_bracket,
                country_code=resolved_country_code,
                is_major=competition.is_major,
            )
            for competition, resolved_country_code in rows
        )

    def enter_competition(self, payload: CompetitionEnterRequest) -> CompetitionEntryResultView:
        self._require_user(payload.user_id)
        competition = self._require_competition(payload.competition_id)
        player = self._require_player(payload.player_id)
        dynasty = self._ensure_user_dynasty(payload.user_id)

        entry = self.session.scalar(
            select(GlobalCompetitionEntry).where(
                GlobalCompetitionEntry.user_id == payload.user_id,
                GlobalCompetitionEntry.competition_id == competition.id,
                GlobalCompetitionEntry.player_id == player.id,
            )
        )
        if entry is None:
            entry = GlobalCompetitionEntry(
                user_id=payload.user_id,
                competition_id=competition.id,
                player_id=player.id,
                status="entered",
                performance_score=payload.performance_score,
                title_awarded=False,
                metadata_json={
                    "age_bracket": competition.age_bracket,
                    "global_player_id": global_player_id(player.id),
                    "global_competition_id": global_competition_id(competition.id),
                },
            )
            self.session.add(entry)
            self._record_history(
                player_id=player.id,
                competition=competition,
                event_type="competition_entered",
                event=f"Entered {competition.name}.",
                timeline_json={"status": "entered"},
            )
        else:
            entry.performance_score = max(entry.performance_score, payload.performance_score)

        title_granted = payload.won_title and not entry.title_awarded
        promotion_payload: dict[str, Any] | None = None
        if title_granted:
            entry.title_awarded = True
            entry.status = "champion"
            self._record_history(
                player_id=player.id,
                competition=competition,
                event_type="competition_won",
                event=f"Won {competition.name}.",
                timeline_json={"status": "champion"},
            )

        evolution, promotion_payload = self._apply_regen_evolution(
            player=player,
            competition=competition,
            performance_score=payload.performance_score,
            title_awarded=title_granted,
        )
        if title_granted:
            legacy_boost_delta = float((promotion_payload or {}).get("legacy_boost_delta") or 0.0)
            self._increment_dynasty(
                dynasty,
                competition=competition,
                performance_score=payload.performance_score,
                legacy_boost_delta=legacy_boost_delta,
            )

        self.session.flush()

        if title_granted:
            self._emit_event(
                name=DYNASTY_UPDATED,
                payload={
                    "user_id": payload.user_id,
                    "competition_id": competition.id,
                    "global_competition_id": global_competition_id(competition.id),
                    "player_id": player.id,
                    "global_player_id": global_player_id(player.id),
                    "title_awarded": True,
                    "player_development_delta": payload.performance_score,
                    "legacy_boost_delta": float((promotion_payload or {}).get("legacy_boost_delta") or 0.0),
                },
                aggregate_id=payload.user_id,
                aggregate_type="user_dynasty",
            )
        self._emit_player_event(
            competition=competition,
            player=player,
            performance_score=payload.performance_score,
            evolution=evolution,
        )
        if promotion_payload is not None:
            self._emit_event(
                name=REGEN_PROMOTED,
                payload=promotion_payload,
                aggregate_id=player.id,
                aggregate_type="player_regen",
            )

        return CompetitionEntryResultView(
            entry_id=entry.id,
            competition_id=competition.id,
            global_competition_id=global_competition_id(competition.id),
            competition_name=competition.name,
            player_id=player.id,
            global_player_id=global_player_id(player.id),
            status=entry.status,
            title_awarded=entry.title_awarded,
            performance_score=entry.performance_score,
            dynasty=self._to_dynasty_view(dynasty),
            evolution=evolution,
        )

    def rent_player(self, payload: PlayerRentRequest) -> PlayerRentResultView:
        self._require_user(payload.user_id)
        competition = self._require_competition(payload.competition_id)
        player = self._require_player(payload.player_id)

        rental = self.session.scalar(
            select(GlobalPlayerRental).where(
                GlobalPlayerRental.user_id == payload.user_id,
                GlobalPlayerRental.competition_id == competition.id,
                GlobalPlayerRental.player_id == player.id,
            )
        )
        if rental is None:
            rental = GlobalPlayerRental(
                user_id=payload.user_id,
                competition_id=competition.id,
                player_id=player.id,
                rental_fee_minor=payload.rental_fee_minor,
                performance_score=payload.performance_score,
                status="active",
                metadata_json={
                    "global_player_id": global_player_id(player.id),
                    "global_competition_id": global_competition_id(competition.id),
                },
            )
            self.session.add(rental)
            self._record_history(
                player_id=player.id,
                competition=competition,
                event_type="player_rented",
                event=f"Rented into {competition.name}.",
                timeline_json={"rental_fee_minor": payload.rental_fee_minor},
            )
        else:
            rental.rental_fee_minor = payload.rental_fee_minor
            rental.performance_score = max(rental.performance_score, payload.performance_score)

        evolution, promotion_payload = self._apply_regen_evolution(
            player=player,
            competition=competition,
            performance_score=payload.performance_score,
            title_awarded=False,
        )
        self.session.flush()

        self._emit_player_event(
            competition=competition,
            player=player,
            performance_score=payload.performance_score,
            evolution=evolution,
        )
        if promotion_payload is not None:
            self._emit_event(
                name=REGEN_PROMOTED,
                payload=promotion_payload,
                aggregate_id=player.id,
                aggregate_type="player_regen",
            )

        return PlayerRentResultView(
            rental_id=rental.id,
            competition_id=competition.id,
            global_competition_id=global_competition_id(competition.id),
            competition_name=competition.name,
            player_id=player.id,
            global_player_id=global_player_id(player.id),
            rental_fee_minor=rental.rental_fee_minor,
            status=rental.status,
            performance_score=rental.performance_score,
            evolution=evolution,
        )

    def list_national_pool(
        self,
        *,
        country_code: str | None = None,
        competition_id: str | None = None,
        limit: int = 50,
    ) -> tuple[NationalPoolPlayerView, ...]:
        stmt = (
            select(Player, Country.alpha2_code, RegenProfile, GlobalRegenEvolution)
            .outerjoin(Country, Country.id == Player.country_id)
            .outerjoin(RegenProfile, RegenProfile.player_id == Player.id)
            .outerjoin(GlobalRegenEvolution, GlobalRegenEvolution.player_id == Player.id)
            .order_by(Player.full_name.asc())
            .limit(limit)
        )
        if country_code:
            stmt = stmt.where(func.upper(Country.alpha2_code) == country_code.upper())
        if competition_id:
            stmt = stmt.where(Player.current_competition_id == competition_id)

        rows = self.session.execute(stmt).all()
        return tuple(
            NationalPoolPlayerView(
                player_id=player.id,
                global_player_id=global_player_id(player.id),
                display_name=player.full_name,
                country_code=resolved_country_code,
                current_club_id=player.current_club_profile_id,
                current_competition_id=player.current_competition_id,
                is_regen=regen is not None,
                tradable=evolution.is_tradable if evolution is not None else player.is_tradable,
                unique=evolution.is_unique if evolution is not None else False,
                hall_of_fame=evolution.hall_of_fame if evolution is not None else False,
                gsi=(
                    evolution.current_gsi
                    if evolution is not None
                    else (regen.current_gsi if regen is not None else None)
                ),
                scarcity_tier=evolution.scarcity_tier if evolution is not None else None,
            )
            for player, resolved_country_code, regen, evolution in rows
        )

    def get_player_history(self, player_id: str) -> PlayerHistoryResponseView:
        player = self._require_player(player_id)
        history = self.session.scalars(
            select(PlayerHistory).where(PlayerHistory.player_id == player.id).order_by(PlayerHistory.created_at.desc())
        ).all()
        lifecycle_summary = self._safe_career_summary(player.id)
        from app.services.player_lifecycle_service import PlayerLifecycleService

        lifecycle_events = PlayerLifecycleService(self.session).list_events(player.id, limit=20)
        evolution = self.session.scalar(select(GlobalRegenEvolution).where(GlobalRegenEvolution.player_id == player.id))

        club_rows = self._club_history(player=player, lifecycle_summary=lifecycle_summary)
        competition_rows = self._competition_history(
            player=player,
            history=history,
            lifecycle_summary=lifecycle_summary,
        )
        performance_timeline = self._performance_timeline(lifecycle_summary)
        title_count = int(evolution.title_count) if evolution is not None else 0
        if title_count <= 0:
            title_count = sum(1 for item in history if item.event_type == "competition_won")

        rendered_history: list[PlayerHistoryEntryView] = [
            PlayerHistoryEntryView(
                event_type=item.event_type,
                event=item.event,
                competition=item.competition,
                global_player_id=item.global_player_id or global_player_id(player.id),
                global_competition_id=item.global_competition_id,
                global_match_id=item.global_match_id,
                timeline_json=dict(item.timeline_json or {}),
                created_at=item.created_at,
            )
            for item in history
        ]
        rendered_history.extend(
            PlayerHistoryEntryView(
                event_type=item.event_type,
                event=item.summary,
                competition=str((item.details_json or {}).get("competition_name") or ""),
                global_player_id=global_player_id(player.id),
                global_competition_id=(
                    global_competition_id(str(item.related_entity_id))
                    if item.related_entity_type == "competition" and item.related_entity_id
                    else None
                ),
                global_match_id=None,
                timeline_json=dict(item.details_json or {}),
                created_at=item.created_at,
            )
            for item in lifecycle_events
        )
        rendered_history.sort(key=lambda item: item.created_at, reverse=True)

        return PlayerHistoryResponseView(
            player_id=player.id,
            global_player_id=global_player_id(player.id),
            display_name=player.full_name,
            clubs=tuple(club_rows),
            competitions=tuple(competition_rows),
            titles=title_count,
            performance_timeline=tuple(performance_timeline),
            career_arc=self._career_arc(player),
            history=tuple(rendered_history),
            evolution=self._to_evolution_view(evolution) if evolution is not None else None,
        )

    def get_dynasty(self, user_id: str) -> UserDynastyView:
        self._require_user(user_id)
        dynasty = self.session.scalar(select(UserDynasty).where(UserDynasty.user_id == user_id))
        if dynasty is None:
            dynasty = UserDynasty(user_id=user_id)
        return self._to_dynasty_view(dynasty)

    def list_dynasty_leaderboard(self, *, limit: int = 50) -> tuple[DynastyLeaderboardEntryView, ...]:
        dynasties = self.session.scalars(
            select(UserDynasty)
            .order_by(
                UserDynasty.total_titles.desc(),
                UserDynasty.player_development_score.desc(),
                UserDynasty.earnings_minor.desc(),
                UserDynasty.legacy_boost_score.desc(),
                UserDynasty.updated_at.desc(),
            )
            .limit(limit)
        ).all()
        return tuple(
            DynastyLeaderboardEntryView(
                rank=index,
                user_id=item.user_id,
                total_titles=item.total_titles,
                player_development_score=item.player_development_score,
                earnings_minor=item.earnings_minor,
                legacy_boost_score=item.legacy_boost_score,
                dynasty_label=self._dynasty_label(item.total_titles),
            )
            for index, item in enumerate(dynasties, start=1)
        )

    def list_hall_of_fame(self, *, limit: int = 50) -> tuple[HallOfFamePlayerView, ...]:
        rows = self.session.execute(
            select(ClubHallOfFameEntry, Player, ClubProfile, GlobalRegenEvolution)
            .outerjoin(Player, Player.id == ClubHallOfFameEntry.player_id)
            .outerjoin(ClubProfile, ClubProfile.id == ClubHallOfFameEntry.club_id)
            .outerjoin(GlobalRegenEvolution, GlobalRegenEvolution.player_id == ClubHallOfFameEntry.player_id)
            .order_by(ClubHallOfFameEntry.inducted_at.desc())
            .limit(limit)
        ).all()
        return tuple(
            HallOfFamePlayerView(
                player_id=player.id,
                global_player_id=global_player_id(player.id),
                display_name=player.full_name,
                club_id=club.id if club is not None else None,
                club_name=club.club_name if club is not None else None,
                inducted_at=entry.inducted_at,
                scarcity_tier=(evolution.scarcity_tier if evolution is not None else "legendary"),
                legacy_boost_score=(evolution.legacy_boost_score if evolution is not None else 0.2),
                immutable_record=bool((entry.metadata_json or {}).get("immutable_record", True)),
            )
            for entry, player, club, evolution in rows
            if player is not None
        )

    def _apply_regen_evolution(
        self,
        *,
        player: Player,
        competition: Competition,
        performance_score: float,
        title_awarded: bool,
    ) -> tuple[RegenEvolutionView | None, dict[str, Any] | None]:
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player.id))
        if regen is None:
            return None, None

        onboarding = self.session.scalar(select(RegenOnboardingFlag).where(RegenOnboardingFlag.regen_id == regen.id))
        evolution = self.session.scalar(select(GlobalRegenEvolution).where(GlobalRegenEvolution.player_id == player.id))
        if evolution is None:
            evolution = GlobalRegenEvolution(
                player_id=player.id,
                regen_profile_id=regen.id,
                regen_type=self._resolve_regen_type(regen, onboarding),
                performance_score=0.0,
                performance_threshold=80.0,
                title_count=0,
                current_gsi=regen.current_gsi,
                is_tradable=(not onboarding.is_non_tradable) if onboarding is not None else player.is_tradable,
                is_unique=False,
                hall_of_fame=False,
                scarcity_tier="rare",
                unique_traits_json=[],
                legacy_boost_score=0.0,
                metadata_json={},
            )
            self.session.add(evolution)

        was_unique = bool(evolution.is_unique)
        was_hall_of_fame = bool(evolution.hall_of_fame)
        evolution.performance_score = max(evolution.performance_score, performance_score)
        evolution.current_gsi = regen.current_gsi
        evolution.last_evolved_at = _utcnow()

        if title_awarded:
            evolution.title_count += 1

        evolution.scarcity_tier = self._resolve_scarcity_tier(evolution)
        evolution.unique_traits_json = self._resolve_unique_traits(player=player, evolution=evolution)
        evolution.legacy_boost_score = self._legacy_boost_score(evolution)

        if (
            evolution.regen_type == "preseeded"
            and performance_score > evolution.performance_threshold
            and not evolution.is_tradable
            and not self._is_starter_regen(regen, onboarding)
        ):
            evolution.is_tradable = True
            evolution.is_unique = True
            player.is_tradable = True
            if onboarding is not None:
                onboarding.is_non_tradable = False
                onboarding.replacement_only = False
            card = self.session.get(PlayerCard, regen.linked_unique_card_id)
            if card is not None:
                metadata = dict(card.metadata_json or {})
                metadata["global_unique_asset"] = True
                metadata["scarcity_tier"] = evolution.scarcity_tier
                card.metadata_json = metadata
            self._record_history(
                player_id=player.id,
                competition=competition,
                event_type="player_promoted",
                event=f"Became a tradable unique asset after starring in {competition.name}.",
                timeline_json={"scarcity_tier": evolution.scarcity_tier},
            )

        if evolution.title_count > 5 and (evolution.current_gsi or 0) > 90 and not evolution.hall_of_fame:
            evolution.hall_of_fame = True
            evolution.scarcity_tier = "legendary"
            evolution.unique_traits_json = self._resolve_unique_traits(player=player, evolution=evolution)
            evolution.legacy_boost_score = self._legacy_boost_score(evolution)
            self._induct_hall_of_fame(regen=regen, player=player, competition_name=competition.name)
            self._record_history(
                player_id=player.id,
                competition=competition,
                event_type="hall_of_fame_inducted",
                event=f"Entered the Hall of Fame through {competition.name}.",
                timeline_json={"legacy_boost_score": evolution.legacy_boost_score},
            )

        promotion_payload: dict[str, Any] | None = None
        if (not was_unique and evolution.is_unique) or (not was_hall_of_fame and evolution.hall_of_fame):
            promotion_payload = {
                "player_id": player.id,
                "global_player_id": global_player_id(player.id),
                "competition_id": competition.id,
                "global_competition_id": global_competition_id(competition.id),
                "scarcity_tier": evolution.scarcity_tier,
                "unique_traits": list(evolution.unique_traits_json or []),
                "legacy_boost_score": evolution.legacy_boost_score,
                "legacy_boost_delta": (
                    evolution.legacy_boost_score if evolution.hall_of_fame and not was_hall_of_fame else 0.0
                ),
                "hall_of_fame": evolution.hall_of_fame,
            }

        return self._to_evolution_view(evolution), promotion_payload

    def _safe_career_summary(self, player_id: str) -> PlayerCareerSummaryView | None:
        try:
            from app.services.player_lifecycle_service import PlayerLifecycleService

            return PlayerLifecycleService(self.session).get_career_summary(player_id)
        except Exception:
            return None

    def _career_arc(self, player: Player) -> PlayerCareerArcView:
        age = self._age_from_date_of_birth(player.date_of_birth)
        position = str(player.normalized_position or player.position or "").upper()
        peak_age_range = _PEAK_AGE_BY_POSITION.get(position, (24, 29))
        if age is None:
            decline_curve = "balanced"
        elif age < peak_age_range[0]:
            decline_curve = "pre-peak growth"
        elif age <= peak_age_range[1]:
            decline_curve = "prime window"
        elif age <= peak_age_range[1] + 3:
            decline_curve = "managed decline"
        else:
            decline_curve = "late-career decline"

        injury_cases = int(
            self.session.scalar(
                select(func.count())
                .select_from(PlayerLifecycleEvent)
                .where(
                    PlayerLifecycleEvent.player_id == player.id,
                    PlayerLifecycleEvent.event_type.like("%injury%"),
                )
            )
            or 0
        )
        injury_risk = "low"
        if injury_cases >= 3:
            injury_risk = "high"
        elif injury_cases >= 1 or (age is not None and age >= 30):
            injury_risk = "medium"
        return PlayerCareerArcView(
            age=age,
            peak_age_range=peak_age_range,
            decline_curve=decline_curve,
            injury_risk=injury_risk,
        )

    def _club_history(
        self,
        *,
        player: Player,
        lifecycle_summary: PlayerCareerSummaryView | None,
    ) -> list[ClubHistoryView]:
        ordered: list[ClubHistoryView] = []
        seen: set[str] = set()

        def add(club_id: str | None, club_name: str | None) -> None:
            resolved_name = str(club_name or "").strip()
            resolved_id = str(club_id or "")
            token = f"{resolved_id}:{resolved_name.lower()}"
            if not resolved_name or token in seen:
                return
            seen.add(token)
            ordered.append(ClubHistoryView(club_id=club_id, club_name=resolved_name))

        if lifecycle_summary is not None:
            for item in lifecycle_summary.seasonal_progression:
                add(item.club_id, item.club_name)
            add(lifecycle_summary.current_club_id, lifecycle_summary.current_club_name)
        elif player.current_club_profile_id:
            club = self.session.get(ClubProfile, player.current_club_profile_id)
            add(player.current_club_profile_id, club.club_name if club is not None else None)
        return ordered

    def _competition_history(
        self,
        *,
        player: Player,
        history: list[PlayerHistory],
        lifecycle_summary: PlayerCareerSummaryView | None,
    ) -> list[CompetitionHistoryView]:
        ordered: list[CompetitionHistoryView] = []
        seen: set[str] = set()

        def add(competition_id: str | None, competition_name: str | None) -> None:
            resolved_name = str(competition_name or "").strip()
            if not resolved_name:
                return
            token = f"{competition_id or ''}:{resolved_name.lower()}"
            if token in seen:
                return
            seen.add(token)
            ordered.append(
                CompetitionHistoryView(
                    competition_id=competition_id,
                    global_competition_id=global_competition_id(competition_id) if competition_id else None,
                    competition_name=resolved_name,
                )
            )

        if lifecycle_summary is not None:
            add(lifecycle_summary.current_competition_id, lifecycle_summary.current_competition_name)
            for item in lifecycle_summary.seasonal_progression:
                add(item.competition_id, item.competition_name)
        for item in history:
            add(None, item.competition)
        if player.current_competition_id and player.current_competition is not None:
            add(player.current_competition_id, player.current_competition.name)
        return ordered

    def _performance_timeline(
        self,
        lifecycle_summary: PlayerCareerSummaryView | None,
    ) -> list[PlayerPerformanceTimelineEntryView]:
        if lifecycle_summary is None:
            return []
        return [
            PlayerPerformanceTimelineEntryView(
                season_label=item.season_label,
                club_id=item.club_id,
                club_name=item.club_name,
                competition_id=item.competition_id,
                competition_name=item.competition_name,
                appearances=item.appearances,
                goals=item.goals,
                assists=item.assists,
                average_rating=item.average_rating,
            )
            for item in lifecycle_summary.seasonal_progression
        ]

    def _ensure_user_dynasty(self, user_id: str) -> UserDynasty:
        dynasty = self.session.scalar(select(UserDynasty).where(UserDynasty.user_id == user_id))
        if dynasty is not None:
            return dynasty
        dynasty = UserDynasty(user_id=user_id)
        self.session.add(dynasty)
        self.session.flush()
        return dynasty

    def _increment_dynasty(
        self,
        dynasty: UserDynasty,
        *,
        competition: Competition,
        performance_score: float,
        legacy_boost_delta: float = 0.0,
    ) -> None:
        dynasty.total_titles += 1
        dynasty.player_development_score += max(0.0, float(performance_score))
        dynasty.legacy_boost_score += max(0.0, float(legacy_boost_delta))
        bracket = (competition.age_bracket or competition.competition_type or "").lower()
        if bracket in {"u17", "u20"}:
            dynasty.youth_titles += 1
            return
        dynasty.senior_titles += 1

    def _record_history(
        self,
        *,
        player_id: str,
        competition: Competition,
        event_type: str,
        event: str,
        timeline_json: dict[str, object] | None = None,
        global_match_identifier: str | None = None,
    ) -> None:
        self.session.add(
            PlayerHistory(
                player_id=player_id,
                event_type=event_type,
                global_player_id=global_player_id(player_id),
                global_competition_id=global_competition_id(competition.id),
                global_match_id=global_match_identifier,
                event=event,
                competition=competition.name,
                timeline_json=timeline_json or {},
            )
        )

    def _induct_hall_of_fame(self, *, regen: RegenProfile, player: Player, competition_name: str) -> None:
        club_id = player.current_club_profile_id or regen.generated_for_club_id
        if club_id is None:
            return
        existing = self.session.scalar(
            select(ClubHallOfFameEntry).where(
                ClubHallOfFameEntry.club_id == club_id,
                ClubHallOfFameEntry.regen_id == regen.id,
            )
        )
        if existing is not None:
            metadata = dict(existing.metadata_json or {})
            metadata["immutable_record"] = True
            if existing.player_id is None:
                existing.player_id = player.id
            existing.metadata_json = metadata
            return
        ClubHallOfFameService(self.session).add_entry(
            club_id=club_id,
            entry_category="Legends",
            player_id=player.id,
            regen_id=regen.id,
            narrative_summary=f"{player.full_name} became immortal after {competition_name}.",
            source_scope="global_memory",
            metadata={"competition_name": competition_name, "immutable_record": True},
        )

    def _to_dynasty_view(self, dynasty: UserDynasty) -> UserDynastyView:
        title_rows = self.session.execute(
            select(GlobalCompetitionEntry, Competition)
            .join(Competition, Competition.id == GlobalCompetitionEntry.competition_id)
            .where(
                GlobalCompetitionEntry.user_id == dynasty.user_id,
                GlobalCompetitionEntry.title_awarded.is_(True),
            )
            .order_by(GlobalCompetitionEntry.updated_at.desc())
        ).all()
        return UserDynastyView(
            user_id=dynasty.user_id,
            total_titles=dynasty.total_titles,
            youth_titles=dynasty.youth_titles,
            senior_titles=dynasty.senior_titles,
            earnings_minor=dynasty.earnings_minor,
            player_development_score=round(float(dynasty.player_development_score), 2),
            legacy_boost_score=round(float(dynasty.legacy_boost_score), 4),
            dynasty_label=self._dynasty_label(dynasty.total_titles),
            title_history=tuple(
                DynastyTitleView(
                    competition_id=competition.id,
                    global_competition_id=global_competition_id(competition.id),
                    competition_name=competition.name,
                    age_bracket=competition.age_bracket,
                    won_at=entry.updated_at,
                )
                for entry, competition in title_rows
            ),
        )

    def _to_evolution_view(self, evolution: GlobalRegenEvolution) -> RegenEvolutionView:
        return RegenEvolutionView(
            regen_profile_id=evolution.regen_profile_id,
            regen_type=evolution.regen_type,
            performance_score=evolution.performance_score,
            performance_threshold=evolution.performance_threshold,
            titles=evolution.title_count,
            gsi=evolution.current_gsi,
            tradable=evolution.is_tradable,
            unique=evolution.is_unique,
            hall_of_fame=evolution.hall_of_fame,
            scarcity_tier=evolution.scarcity_tier,
            unique_traits=tuple(str(item) for item in list(evolution.unique_traits_json or [])),
            legacy_boost_score=evolution.legacy_boost_score,
        )

    def _resolve_regen_type(
        self,
        regen: RegenProfile,
        onboarding: RegenOnboardingFlag | None,
    ) -> str:
        onboarding_type = (onboarding.onboarding_type if onboarding is not None else "").lower()
        generation_source = (regen.generation_source or "").lower()
        if onboarding_type in _PRESEEDED_TYPES or generation_source in _PRESEEDED_TYPES:
            return "preseeded"
        return "academy"

    def _is_starter_regen(self, regen: RegenProfile, onboarding: RegenOnboardingFlag | None) -> bool:
        onboarding_type = (onboarding.onboarding_type if onboarding is not None else "").lower()
        generation_source = (regen.generation_source or "").lower()
        return onboarding_type in _STARTER_REGEN_TYPES or generation_source in _STARTER_REGEN_TYPES

    def _resolve_scarcity_tier(self, evolution: GlobalRegenEvolution) -> str:
        gsi = int(evolution.current_gsi or 0)
        titles = int(evolution.title_count or 0)
        if gsi >= 92 and titles >= 6:
            return "legendary"
        if gsi >= 86 or titles >= 3:
            return "elite"
        return "rare"

    def _resolve_unique_traits(self, *, player: Player, evolution: GlobalRegenEvolution) -> list[str]:
        traits: list[str] = []
        position = str(player.normalized_position or player.position or "").upper()
        if position == "GK":
            traits.append("penalty wall")
        elif position in {"CB", "RB", "LB"}:
            traits.append("lockdown defender")
        elif position in {"CM", "DM", "AM"}:
            traits.append("tempo controller")
        elif position in {"RW", "LW"}:
            traits.append("isolation dribbler")
        elif position == "ST":
            traits.append("ice-veins finisher")
        if evolution.title_count >= 1:
            traits.append("big-match aura")
        if evolution.title_count >= 5:
            traits.append("dynasty carrier")
        if evolution.hall_of_fame:
            traits.append("legacy spark")
        return traits[:3]

    def _legacy_boost_score(self, evolution: GlobalRegenEvolution) -> float:
        if evolution.hall_of_fame or evolution.scarcity_tier == "legendary":
            return 0.2
        if evolution.scarcity_tier == "elite":
            return 0.12
        return 0.05 if evolution.is_unique else 0.0

    def _dynasty_label(self, total_titles: int) -> str:
        if total_titles >= 10:
            return "Global Dynasty"
        if total_titles >= 6:
            return "Established Dynasty"
        if total_titles >= 3:
            return "Rising Dynasty"
        if total_titles >= 1:
            return "First Legacy"
        return "Unproven"

    def _emit_player_event(
        self,
        *,
        competition: Competition,
        player: Player,
        performance_score: float,
        evolution: RegenEvolutionView | None,
    ) -> None:
        payload = {
            "player_id": player.id,
            "global_player_id": global_player_id(player.id),
            "competition_id": competition.id,
            "global_competition_id": global_competition_id(competition.id),
            "performance_score": performance_score,
            "event_name": PLAYER_EVOLVED,
        }
        if evolution is not None:
            payload.update(
                {
                    "scarcity_tier": evolution.scarcity_tier,
                    "unique_traits": list(evolution.unique_traits),
                    "legacy_boost_score": evolution.legacy_boost_score,
                }
            )
        self._emit_event(
            name=PLAYER_EVOLVED,
            payload=payload,
            aggregate_id=player.id,
            aggregate_type="player",
        )

    def _emit_event(
        self,
        *,
        name: str,
        payload: dict[str, Any],
        aggregate_id: str,
        aggregate_type: str,
    ) -> None:
        if self.event_publisher is None:
            return
        event = DomainEvent(
            name=name,
            payload=payload,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            producer="global_memory",
            partition_key=aggregate_id,
        )
        self.session.add(build_outbox_event(domain_event=event))
        defer_event_publish_until_commit(self.session, publisher=self.event_publisher, event=event)

    def _require_user(self, user_id: str) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise GlobalMemoryNotFoundError("user_not_found")
        return user

    def _require_competition(self, competition_id: str) -> Competition:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            raise GlobalMemoryNotFoundError("competition_not_found")
        return competition

    def _require_player(self, player_id: str) -> Player:
        player = self.session.get(Player, player_id)
        if player is None:
            raise GlobalMemoryNotFoundError("player_not_found")
        return player

    @staticmethod
    def _age_from_date_of_birth(date_of_birth: date | None) -> int | None:
        if date_of_birth is None:
            return None
        today = date.today()
        return today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))


__all__ = ["GlobalMemoryError", "GlobalMemoryNotFoundError", "GlobalMemoryService"]
