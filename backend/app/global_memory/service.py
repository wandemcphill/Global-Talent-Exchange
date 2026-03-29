from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.global_memory.models import (
    GlobalCompetitionEntry,
    GlobalPlayerRental,
    GlobalRegenEvolution,
    PlayerHistory,
    UserDynasty,
)
from app.global_memory.schemas import (
    CompetitionEntryResultView,
    CompetitionEnterRequest,
    CompetitionListItemView,
    DynastyTitleView,
    NationalPoolPlayerView,
    PlayerHistoryEntryView,
    PlayerHistoryResponseView,
    PlayerRentRequest,
    PlayerRentResultView,
    RegenEvolutionView,
    UserDynastyView,
)
from app.ingestion.models import Competition, Country, Player
from app.models.club_hall_of_fame import ClubHallOfFameEntry
from app.models.player_cards import PlayerCard
from app.models.regen import RegenOnboardingFlag, RegenProfile
from app.models.user import User
from app.services.club_hall_of_fame_service import ClubHallOfFameService

_PRESEEDED_TYPES = {"starter_bundle", "starter_regen", "preseeded"}


class GlobalMemoryError(ValueError):
    pass


class GlobalMemoryNotFoundError(GlobalMemoryError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class GlobalMemoryService:
    session: Session

    def list_competitions(
        self,
        *,
        limit: int = 50,
        country_code: str | None = None,
        age_bracket: str | None = None,
    ) -> tuple[CompetitionListItemView, ...]:
        stmt = (
            select(Competition, Country.alpha2_code)
            .outerjoin(Country, Country.id == Competition.country_id)
            .order_by(Competition.is_major.desc(), Competition.competition_strength.desc(), Competition.name.asc())
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
                metadata_json={"age_bracket": competition.age_bracket},
            )
            self.session.add(entry)
            self._record_history(player.id, f"Entered {competition.name}.", competition.name)
        else:
            entry.performance_score = max(entry.performance_score, payload.performance_score)

        title_granted = payload.won_title and not entry.title_awarded
        if title_granted:
            entry.title_awarded = True
            entry.status = "champion"
            self._increment_dynasty(dynasty, competition)
            self._record_history(player.id, f"Won {competition.name}.", competition.name)

        evolution = self._apply_regen_evolution(
            player=player,
            competition=competition,
            performance_score=payload.performance_score,
            title_awarded=title_granted,
        )
        self.session.flush()
        return CompetitionEntryResultView(
            entry_id=entry.id,
            competition_id=competition.id,
            competition_name=competition.name,
            player_id=player.id,
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
            )
            self.session.add(rental)
            self._record_history(player.id, f"Rented into {competition.name}.", competition.name)
        else:
            rental.rental_fee_minor = payload.rental_fee_minor
            rental.performance_score = max(rental.performance_score, payload.performance_score)

        evolution = self._apply_regen_evolution(
            player=player,
            competition=competition,
            performance_score=payload.performance_score,
            title_awarded=False,
        )
        self.session.flush()
        return PlayerRentResultView(
            rental_id=rental.id,
            competition_id=competition.id,
            competition_name=competition.name,
            player_id=player.id,
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
                display_name=player.full_name,
                country_code=resolved_country_code,
                current_club_id=player.current_club_profile_id,
                current_competition_id=player.current_competition_id,
                is_regen=regen is not None,
                tradable=evolution.is_tradable if evolution is not None else player.is_tradable,
                unique=evolution.is_unique if evolution is not None else False,
                hall_of_fame=evolution.hall_of_fame if evolution is not None else False,
                gsi=evolution.current_gsi if evolution is not None else (regen.current_gsi if regen is not None else None),
            )
            for player, resolved_country_code, regen, evolution in rows
        )

    def get_player_history(self, player_id: str) -> PlayerHistoryResponseView:
        player = self._require_player(player_id)
        history = self.session.scalars(
            select(PlayerHistory).where(PlayerHistory.player_id == player.id).order_by(PlayerHistory.created_at.desc())
        ).all()
        evolution = self.session.scalar(
            select(GlobalRegenEvolution).where(GlobalRegenEvolution.player_id == player.id)
        )
        return PlayerHistoryResponseView(
            player_id=player.id,
            display_name=player.full_name,
            history=tuple(
                PlayerHistoryEntryView(
                    event=item.event,
                    competition=item.competition,
                    created_at=item.created_at,
                )
                for item in history
            ),
            evolution=self._to_evolution_view(evolution) if evolution is not None else None,
        )

    def get_dynasty(self, user_id: str) -> UserDynastyView:
        self._require_user(user_id)
        dynasty = self.session.scalar(select(UserDynasty).where(UserDynasty.user_id == user_id))
        if dynasty is None:
            dynasty = UserDynasty(
                user_id=user_id,
                total_titles=0,
                youth_titles=0,
                senior_titles=0,
            )
        return self._to_dynasty_view(dynasty)

    def _apply_regen_evolution(
        self,
        *,
        player: Player,
        competition: Competition,
        performance_score: float,
        title_awarded: bool,
    ) -> RegenEvolutionView | None:
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player.id))
        if regen is None:
            return None

        onboarding = self.session.scalar(
            select(RegenOnboardingFlag).where(RegenOnboardingFlag.regen_id == regen.id)
        )
        evolution = self.session.scalar(
            select(GlobalRegenEvolution).where(GlobalRegenEvolution.player_id == player.id)
        )
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
                metadata_json={},
            )
            self.session.add(evolution)

        evolution.performance_score = max(evolution.performance_score, performance_score)
        evolution.current_gsi = regen.current_gsi
        evolution.last_evolved_at = _utcnow()

        if title_awarded:
            evolution.title_count += 1

        if (
            evolution.regen_type == "preseeded"
            and performance_score > evolution.performance_threshold
            and not evolution.is_tradable
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
                card.metadata_json = metadata
            self._record_history(
                player.id,
                f"Became a tradable unique asset after starring in {competition.name}.",
                competition.name,
            )

        if evolution.title_count > 5 and (evolution.current_gsi or 0) > 90 and not evolution.hall_of_fame:
            evolution.hall_of_fame = True
            self._induct_hall_of_fame(regen=regen, player=player, competition_name=competition.name)
            self._record_history(
                player.id,
                f"Entered the Hall of Fame through {competition.name}.",
                competition.name,
            )

        return self._to_evolution_view(evolution)

    def _ensure_user_dynasty(self, user_id: str) -> UserDynasty:
        dynasty = self.session.scalar(select(UserDynasty).where(UserDynasty.user_id == user_id))
        if dynasty is not None:
            return dynasty
        dynasty = UserDynasty(
            user_id=user_id,
            total_titles=0,
            youth_titles=0,
            senior_titles=0,
        )
        self.session.add(dynasty)
        self.session.flush()
        return dynasty

    def _increment_dynasty(self, dynasty: UserDynasty, competition: Competition) -> None:
        dynasty.total_titles += 1
        bracket = (competition.age_bracket or competition.competition_type or "").lower()
        if bracket in {"u17", "u20"}:
            dynasty.youth_titles += 1
            return
        dynasty.senior_titles += 1

    def _record_history(self, player_id: str, event: str, competition_name: str) -> None:
        self.session.add(
            PlayerHistory(
                player_id=player_id,
                event=event,
                competition=competition_name,
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
            return
        ClubHallOfFameService(self.session).add_entry(
            club_id=club_id,
            entry_category="Legends",
            regen_id=regen.id,
            narrative_summary=f"{player.full_name} became immortal after {competition_name}.",
            source_scope="global_memory",
            metadata={"competition_name": competition_name},
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
            dynasty_label=self._dynasty_label(dynasty.total_titles),
            title_history=tuple(
                DynastyTitleView(
                    competition_id=competition.id,
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
