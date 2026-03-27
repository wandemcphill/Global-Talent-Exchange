from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.common.enums.match_status import MatchStatus
from app.models.club_profile import ClubProfile
from app.models.competition_match import CompetitionMatch
from app.models.manager_marketplace import (
    ManagerContract,
    ManagerContractStatus,
    ManagerControlMode,
    ManagerProfile,
)
from app.models.user import User, UserRole
from app.replay_archive.persistence import ReplayArchiveRecordRow

from .schemas import (
    ManagerCardView,
    ManagerContractView,
    ManagerHireResponse,
    ManagerLeaderboardEntryView,
    ManagerProfileView,
    ManagerReleaseResponse,
)


class ManagerMarketplaceError(ValueError):
    pass


@dataclass(slots=True)
class ManagerMarketplaceService:
    session: Session

    def list_managers(self, *, available_only: bool = True) -> list[ManagerCardView]:
        profiles = list(self.session.scalars(select(ManagerProfile).order_by(ManagerProfile.updated_at.desc())).all())
        cards = [self._card_view(profile) for profile in profiles]
        if available_only:
            cards = [card for card in cards if card.availability]
        return cards

    def get_manager(self, profile_id: str) -> ManagerProfileView:
        return self._profile_view(self._profile(profile_id))

    def hire_manager(self, actor: User, profile_id: str, *, end_date=None) -> ManagerHireResponse:
        club = self._club_for_user(actor)
        self._assert_club_not_busy(actor, club)
        profile = self._profile(profile_id)
        manager_user = self._manager_user(profile)
        if profile.control_mode not in {ManagerControlMode.HUMAN, ManagerControlMode.REAL_MANAGER}:
            raise ManagerMarketplaceError("AI managers cannot control GTEX competition matches.")
        if manager_user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise ManagerMarketplaceError("Administrative accounts cannot be hired as match managers.")
        self._require_no_active_club_contract(actor.id)
        self._require_manager_available(profile)

        today = datetime.now(UTC).date()
        contract = ManagerContract(
            manager_id=profile.manager_id,
            club_user_id=actor.id,
            start_date=today,
            end_date=end_date or (today + timedelta(days=30)),
            agreed_fee=profile.hourly_fee,
            status=ManagerContractStatus.ACTIVE,
        )
        profile.is_available = False
        self.session.add(contract)
        self.session.flush()
        return ManagerHireResponse(profile=self._profile_view(profile), contract=self._contract_view(contract))

    def release_manager(self, actor: User, profile_id: str) -> ManagerReleaseResponse:
        club = self._club_for_user(actor)
        self._assert_club_not_busy(actor, club)
        profile = self._profile(profile_id)
        contract = self.session.scalar(
            select(ManagerContract).where(
                ManagerContract.manager_id == profile.manager_id,
                ManagerContract.club_user_id == actor.id,
                ManagerContract.status == ManagerContractStatus.ACTIVE,
            )
        )
        if contract is None:
            raise ManagerMarketplaceError("Active manager contract was not found for this club.")
        contract.status = ManagerContractStatus.ENDED
        contract.end_date = datetime.now(UTC).date()
        profile.is_available = True
        self.session.flush()
        return ManagerReleaseResponse(profile=self._profile_view(profile), contract=self._contract_view(contract))

    def leaderboard(self) -> list[ManagerLeaderboardEntryView]:
        profiles = list(self.session.scalars(select(ManagerProfile)).all())
        ordered = sorted(
            profiles,
            key=lambda item: (
                -self._win_rate(item),
                -item.reputation_score,
                -item.matches_managed,
                self._manager_name(item).lower(),
            ),
        )
        return [
            ManagerLeaderboardEntryView(
                rank=index + 1,
                id=profile.id,
                manager_id=profile.manager_id,
                name=self._manager_name(profile),
                rating=self._rating(profile),
                win_rate=self._win_rate(profile),
                preferred_style=profile.preferred_style,
                matches_managed=profile.matches_managed,
                reputation_score=profile.reputation_score,
                fee=self._normalized_fee(profile.hourly_fee),
            )
            for index, profile in enumerate(ordered)
        ]

    def record_match_outcome(
        self,
        *,
        home_club_id: str | None,
        away_club_id: str | None,
        winner_club_id: str | None,
    ) -> None:
        club_user_ids = {
            "home": self._owner_user_id_for_club(home_club_id),
            "away": self._owner_user_id_for_club(away_club_id),
        }
        contracts = {
            side: self._active_contract_for_club_user(user_id)
            for side, user_id in club_user_ids.items()
        }
        for side, contract in contracts.items():
            if contract is None:
                continue
            profile = self.session.scalar(select(ManagerProfile).where(ManagerProfile.manager_id == contract.manager_id))
            if profile is None:
                continue
            profile.matches_managed += 1
            club_id = home_club_id if side == "home" else away_club_id
            if winner_club_id is None:
                profile.current_losing_streak = 0
            elif club_id == winner_club_id:
                profile.wins += 1
                profile.reputation_score += 10
                profile.current_losing_streak = 0
            else:
                profile.losses += 1
                profile.reputation_score -= 5
                profile.current_losing_streak += 1
            profile.hourly_fee = self._dynamic_fee(profile)
        self.session.flush()

    def build_match_manager_profile(self, *, club_id: str | None) -> dict[str, object] | None:
        club_user_id = self._owner_user_id_for_club(club_id)
        if club_user_id is None:
            return None
        contract = self._active_contract_for_club_user(club_user_id)
        if contract is None:
            return None
        profile = self.session.scalar(select(ManagerProfile).where(ManagerProfile.manager_id == contract.manager_id))
        if profile is None:
            return None
        user = self._manager_user(profile)
        style = self._style_contract(profile.preferred_style)
        return {
            "display_name": self._display_name(user),
            "preferred_style": profile.preferred_style,
            "control_mode": profile.control_mode.value,
            "mentality": style["mentality"],
            "tactics": style["tactics"],
            "traits": style["traits"],
            "rating": self._rating(profile),
            "reputation_score": profile.reputation_score,
        }

    def _club_for_user(self, actor: User) -> ClubProfile:
        club = self.session.scalar(
            select(ClubProfile).where(ClubProfile.owner_user_id == actor.id).order_by(ClubProfile.created_at.asc())
        )
        if club is None:
            raise ManagerMarketplaceError("Club account is required to hire a manager.")
        return club

    def _assert_club_not_busy(self, actor: User, club: ClubProfile) -> None:
        live_match = self.session.scalar(
            select(CompetitionMatch).where(
                or_(CompetitionMatch.home_club_id == club.id, CompetitionMatch.away_club_id == club.id),
                CompetitionMatch.status.in_([MatchStatus.IN_PROGRESS.value, MatchStatus.PAUSED.value]),
            )
        )
        if live_match is not None:
            raise ManagerMarketplaceError("Cannot change manager during an active match.")
        live_replay = next(
            (
                row
                for row in self.session.scalars(select(ReplayArchiveRecordRow).where(ReplayArchiveRecordRow.live.is_(True))).all()
                if actor.id in set(row.participant_user_ids_json or [])
            ),
            None,
        )
        if live_replay is not None:
            raise ManagerMarketplaceError("Cannot change manager during an active fast game run.")

    def _profile(self, profile_id: str) -> ManagerProfile:
        profile = self.session.get(ManagerProfile, profile_id)
        if profile is None:
            raise ManagerMarketplaceError("Manager profile was not found.")
        return profile

    def _manager_user(self, profile: ManagerProfile) -> User:
        user = self.session.get(User, profile.manager_id)
        if user is None or not user.is_active:
            raise ManagerMarketplaceError("Manager account is unavailable.")
        return user

    def _require_no_active_club_contract(self, club_user_id: str) -> None:
        if self._active_contract_for_club_user(club_user_id) is not None:
            raise ManagerMarketplaceError("Only one active manager can be assigned to a club at a time.")

    def _require_manager_available(self, profile: ManagerProfile) -> None:
        active_contract = self.session.scalar(
            select(ManagerContract).where(
                ManagerContract.manager_id == profile.manager_id,
                ManagerContract.status == ManagerContractStatus.ACTIVE,
            )
        )
        if active_contract is not None or not profile.is_available:
            raise ManagerMarketplaceError("Manager is not currently available for hire.")

    def _active_contract_for_club_user(self, club_user_id: str | None) -> ManagerContract | None:
        if club_user_id is None:
            return None
        return self.session.scalar(
            select(ManagerContract).where(
                ManagerContract.club_user_id == club_user_id,
                ManagerContract.status == ManagerContractStatus.ACTIVE,
            )
        )

    def _owner_user_id_for_club(self, club_id: str | None) -> str | None:
        if club_id is None:
            return None
        club = self.session.get(ClubProfile, club_id)
        return club.owner_user_id if club is not None else None

    def _card_view(self, profile: ManagerProfile) -> ManagerCardView:
        return ManagerCardView(
            id=profile.id,
            manager_id=profile.manager_id,
            name=self._manager_name(profile),
            rating=self._rating(profile),
            win_rate=self._win_rate(profile),
            preferred_style=profile.preferred_style,
            fee=self._normalized_fee(profile.hourly_fee),
            availability=self._availability(profile),
        )

    def _profile_view(self, profile: ManagerProfile) -> ManagerProfileView:
        contract = self.session.scalar(
            select(ManagerContract).where(
                ManagerContract.manager_id == profile.manager_id,
                ManagerContract.status == ManagerContractStatus.ACTIVE,
            )
        )
        card = self._card_view(profile)
        return ManagerProfileView(
            **card.model_dump(),
            bio=profile.bio,
            matches_managed=profile.matches_managed,
            wins=profile.wins,
            losses=profile.losses,
            reputation_score=profile.reputation_score,
            control_mode=profile.control_mode,
            active_contract=self._contract_view(contract) if contract is not None else None,
        )

    @staticmethod
    def _contract_view(contract: ManagerContract) -> ManagerContractView:
        return ManagerContractView.model_validate(contract, from_attributes=True)

    def _availability(self, profile: ManagerProfile) -> bool:
        active_contract = self.session.scalar(
            select(ManagerContract).where(
                ManagerContract.manager_id == profile.manager_id,
                ManagerContract.status == ManagerContractStatus.ACTIVE,
            )
        )
        return bool(profile.is_available and active_contract is None)

    def _manager_name(self, profile: ManagerProfile) -> str:
        return self._display_name(self._manager_user(profile))

    @staticmethod
    def _display_name(user: User) -> str:
        return user.display_name or user.full_name or user.username

    @staticmethod
    def _rating(profile: ManagerProfile) -> float:
        return round(max(0.0, min(100.0, 50.0 + (profile.reputation_score * 0.5))), 1)

    @staticmethod
    def _win_rate(profile: ManagerProfile) -> float:
        if profile.matches_managed <= 0:
            return 0.0
        return round((profile.wins / profile.matches_managed) * 100, 1)

    @staticmethod
    def _normalized_fee(value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _dynamic_fee(self, profile: ManagerProfile) -> Decimal:
        fee = Decimal(profile.hourly_fee)
        win_rate = self._win_rate(profile)
        if profile.matches_managed >= 3 and win_rate >= 60.0:
            fee *= Decimal("1.05")
        if profile.current_losing_streak >= 2:
            fee *= Decimal("0.92")
        return max(Decimal("0.00"), fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _style_contract(preferred_style: str) -> dict[str, object]:
        style = preferred_style.strip().lower()
        if style in {"attack", "attacking", "front-foot"}:
            return {
                "mentality": "attacking",
                "tactics": ["high_press_attack", "vertical_passing"],
                "traits": ["quick_substitution", "in_game_adjustments"],
            }
        if style in {"defense", "defensive", "low_block"}:
            return {
                "mentality": "defensive",
                "tactics": ["low_block_counter", "compact_midblock"],
                "traits": ["defensive_organization", "strict_structure"],
            }
        if style in {"possession", "control"}:
            return {
                "mentality": "possession",
                "tactics": ["tiki_taka", "possession_control"],
                "traits": ["tactical_flexibility", "in_game_adjustments"],
            }
        if style in {"counter", "counter_attack", "transition"}:
            return {
                "mentality": "pragmatic",
                "tactics": ["low_block_counter", "direct_transition"],
                "traits": ["quick_substitution", "defensive_organization"],
            }
        return {
            "mentality": "balanced",
            "tactics": ["balanced_shape"],
            "traits": ["in_game_adjustments"],
        }
