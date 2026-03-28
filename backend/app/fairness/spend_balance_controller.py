from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.competition_engine.queue_contracts import MatchSimulationJob
from app.models.creator_monetization import CreatorBroadcastPurchase, CreatorSeasonPass
from app.models.gift_transaction import GiftTransaction
from app.models.media_engine import PremiumVideoPurchase
from app.models.wallet import LedgerUnit

if TYPE_CHECKING:
    from app.match_engine.schemas import MatchClubContextInput, MatchSimulationRequest, MatchTeamInput

_ZERO = Decimal("0.0000")
_CASUAL_THRESHOLD = Decimal("250.0000")
_WHALE_THRESHOLD = Decimal("1500.0000")
_UNDERDOG_MAX_BPS = 75
_COIN_COMPATIBLE_UNITS = {LedgerUnit.COIN}


def _fairness_violation(detail: str, *, reason: str) -> Exception:
    from app.fairness.fairness_guard import FairnessViolation

    return FairnessViolation(detail, reason=reason)


class SpendTier(StrEnum):
    CASUAL = "casual"
    COMPETITIVE = "competitive"
    WHALE = "whale"


class TournamentFairnessMode(StrEnum):
    BALANCED = "balanced"
    OPEN = "open"


@dataclass(frozen=True, slots=True)
class FairnessModePolicy:
    mode: TournamentFairnessMode
    max_s_plus_players: int
    max_team_rating_spread: int


@dataclass(frozen=True, slots=True)
class SpendProfile:
    user_id: str | None
    tier: SpendTier
    compatible_total_coin: Decimal
    excluded_sources: tuple[str, ...]


@dataclass(slots=True)
class SpendBalanceController:
    session: Session | None = None

    @staticmethod
    def policy_for_mode(mode: TournamentFairnessMode) -> FairnessModePolicy:
        if mode is TournamentFairnessMode.BALANCED:
            return FairnessModePolicy(mode=mode, max_s_plus_players=4, max_team_rating_spread=6)
        return FairnessModePolicy(mode=mode, max_s_plus_players=5, max_team_rating_spread=12)

    def apply_balance_controls(
        self,
        *,
        request: MatchSimulationRequest,
        job: MatchSimulationJob,
        match_seed: int,
        competition_metadata_json: dict[str, Any] | None,
    ) -> tuple[MatchSimulationRequest, dict[str, Any]]:
        policy = self._resolve_policy(competition_metadata_json)
        self._enforce_s_plus_cap(request.home_team, policy=policy)
        self._enforce_s_plus_cap(request.away_team, policy=policy)
        team_rating_spread = abs(self._average_team_rating(request.home_team) - self._average_team_rating(request.away_team))
        if team_rating_spread > policy.max_team_rating_spread:
            raise _fairness_violation(
                f"Balanced squad spread exceeded the {policy.max_team_rating_spread}-point limit for this match.",
                reason="team_rating_spread_exceeded",
            )

        home_spend = self._classify_user(job.home_user_id)
        away_spend = self._classify_user(job.away_user_id)
        normalized_request, soft_balance_metadata = self._apply_underdog_bonus(request, match_seed=match_seed)

        metadata = {
            "mode": policy.mode.value,
            "squad_balance": {
                "policy": "s_plus_cap",
                "max_s_plus_players": policy.max_s_plus_players,
                "max_team_rating_spread": policy.max_team_rating_spread,
                "home_s_plus_players": self._count_s_plus_players(request.home_team),
                "away_s_plus_players": self._count_s_plus_players(request.away_team),
                "team_rating_spread": round(team_rating_spread, 2),
            },
            "spend_tiers": {
                "home": self._spend_profile_view(home_spend),
                "away": self._spend_profile_view(away_spend),
                "similar_pairing_preferred": self._tier_distance(home_spend.tier, away_spend.tier) <= 1,
            },
            "soft_balance": soft_balance_metadata,
        }
        return normalized_request, metadata

    def _resolve_policy(self, competition_metadata_json: dict[str, Any] | None) -> FairnessModePolicy:
        fairness_payload = {}
        if isinstance(competition_metadata_json, dict):
            raw_fairness = competition_metadata_json.get("fairness")
            if isinstance(raw_fairness, dict):
                fairness_payload = raw_fairness
        raw_mode = fairness_payload.get("mode", TournamentFairnessMode.OPEN.value)
        try:
            mode = TournamentFairnessMode(str(raw_mode))
        except ValueError:
            mode = TournamentFairnessMode.OPEN
        return self.policy_for_mode(mode)

    def _classify_user(self, user_id: str | None) -> SpendProfile:
        if self.session is None or user_id is None:
            return SpendProfile(user_id=user_id, tier=SpendTier.CASUAL, compatible_total_coin=_ZERO, excluded_sources=())
        window_start = datetime.now(UTC) - timedelta(days=30)
        compatible_total = self._coalesce_sum(PremiumVideoPurchase.price_coin, PremiumVideoPurchase.user_id == user_id, PremiumVideoPurchase.created_at >= window_start)
        compatible_total += self._coalesce_sum(CreatorBroadcastPurchase.price_coin, CreatorBroadcastPurchase.user_id == user_id, CreatorBroadcastPurchase.created_at >= window_start)
        compatible_total += self._coalesce_sum(CreatorSeasonPass.price_coin, CreatorSeasonPass.user_id == user_id, CreatorSeasonPass.created_at >= window_start)
        compatible_total += self._coalesce_sum(
            GiftTransaction.gross_amount,
            GiftTransaction.sender_user_id == user_id,
            GiftTransaction.created_at >= window_start,
            GiftTransaction.ledger_unit.in_(_COIN_COMPATIBLE_UNITS),
        )
        excluded_sources: list[str] = []
        incompatible_gifts = self.session.scalar(
            select(func.count(GiftTransaction.id)).where(
                GiftTransaction.sender_user_id == user_id,
                GiftTransaction.created_at >= window_start,
                GiftTransaction.ledger_unit.not_in(_COIN_COMPATIBLE_UNITS),
            )
        )
        if int(incompatible_gifts or 0) > 0:
            excluded_sources.append("gift_transactions_incompatible_unit")
        if compatible_total >= _WHALE_THRESHOLD:
            tier = SpendTier.WHALE
        elif compatible_total >= _CASUAL_THRESHOLD:
            tier = SpendTier.COMPETITIVE
        else:
            tier = SpendTier.CASUAL
        return SpendProfile(
            user_id=user_id,
            tier=tier,
            compatible_total_coin=compatible_total.quantize(Decimal("0.0001")),
            excluded_sources=tuple(excluded_sources),
        )

    def _coalesce_sum(self, field, *criteria) -> Decimal:
        if self.session is None:
            return _ZERO
        value = self.session.scalar(select(func.coalesce(func.sum(field), 0)).where(*criteria))
        return Decimal(str(value or 0)).quantize(Decimal("0.0001"))

    def _enforce_s_plus_cap(self, team: MatchTeamInput, *, policy: FairnessModePolicy) -> None:
        s_plus_count = self._count_s_plus_players(team)
        if s_plus_count > policy.max_s_plus_players:
            raise _fairness_violation(
                f"{team.team_name} exceeds the {policy.max_s_plus_players} S+ player cap for {policy.mode.value} fairness mode.",
                reason="s_plus_cap_exceeded",
            )

    def _apply_underdog_bonus(
        self,
        request: MatchSimulationRequest,
        *,
        match_seed: int,
    ) -> tuple[MatchSimulationRequest, dict[str, Any]]:
        home_rating = self._average_team_rating(request.home_team)
        away_rating = self._average_team_rating(request.away_team)
        rating_gap = abs(home_rating - away_rating)
        if rating_gap < 2.0:
            return request, {"applied": False, "bonus_bps": 0, "bonus_points": 0}

        home_is_underdog = home_rating < away_rating
        variant = match_seed % 7
        bonus_bps = min(_UNDERDOG_MAX_BPS, max(5, int(rating_gap * 8) + variant))
        bonus_points = max(1, min(3, round(bonus_bps / 25)))
        beneficiary = request.home_team if home_is_underdog else request.away_team
        boosted_team = self._boost_team_context(beneficiary, bonus_points=bonus_points)
        normalized_request = request.model_copy(
            update={
                "home_team": boosted_team if home_is_underdog else request.home_team,
                "away_team": boosted_team if not home_is_underdog else request.away_team,
            }
        )
        return normalized_request, {
            "applied": True,
            "beneficiary_team_id": beneficiary.team_id,
            "bonus_bps": bonus_bps,
            "bonus_points": bonus_points,
            "rating_gap": round(rating_gap, 2),
        }

    def _boost_team_context(self, team: MatchTeamInput, *, bonus_points: int) -> MatchTeamInput:
        from app.match_engine.schemas import MatchClubContextInput

        context = team.club_context
        boosted_context = MatchClubContextInput(
            club_tier=context.club_tier,
            competition_tier=context.competition_tier,
            team_chemistry=context.team_chemistry,
            recent_form=self._clamp_context(context.recent_form + bonus_points),
            morale=self._clamp_context(context.morale + bonus_points),
            motivation=self._clamp_context(context.motivation + bonus_points),
            fatigue_load=context.fatigue_load,
            travel_load=context.travel_load,
            rivalry_intensity=context.rivalry_intensity,
            schedule_pressure=context.schedule_pressure,
        )
        return team.model_copy(update={"club_context": boosted_context})

    @staticmethod
    def _clamp_context(value: int) -> int:
        return max(1, min(100, int(value)))

    def _count_s_plus_players(self, team: MatchTeamInput) -> int:
        return sum(1 for player in [*team.starters, *team.bench] if self._player_rating(player) >= 90)

    def _average_team_rating(self, team: MatchTeamInput) -> float:
        starters = list(team.starters)
        if not starters:
            return 0.0
        return sum(self._player_rating(player) for player in starters) / len(starters)

    @staticmethod
    def _player_rating(player) -> int:
        overall = getattr(player, "overall", None)
        if overall is not None:
            return int(overall)
        current_gsi = getattr(player, "current_gsi", None)
        if current_gsi is not None:
            return int(current_gsi)
        return 0

    @staticmethod
    def _tier_distance(left: SpendTier, right: SpendTier) -> int:
        rank = {
            SpendTier.CASUAL: 0,
            SpendTier.COMPETITIVE: 1,
            SpendTier.WHALE: 2,
        }
        return abs(rank[left] - rank[right])

    @staticmethod
    def _spend_profile_view(profile: SpendProfile) -> dict[str, Any]:
        return {
            "user_id": profile.user_id,
            "tier": profile.tier.value,
            "compatible_total_coin": str(profile.compatible_total_coin),
            "excluded_sources": list(profile.excluded_sources),
        }


__all__ = [
    "FairnessModePolicy",
    "SpendBalanceController",
    "SpendTier",
    "TournamentFairnessMode",
]
