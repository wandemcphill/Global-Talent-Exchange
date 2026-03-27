from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.club_finance.models import ClubFinanceProfile, ClubFinanceTransaction, Sponsor, SponsorTier
from app.ingestion.models import Player
from app.live_ops.service import LiveOpsService
from app.models.club_profile import ClubProfile
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.notification_record import NotificationRecord
from app.models.player_contract import PlayerContract
from app.models.user import User

DECIMAL_QUANTUM = Decimal("0.0001")
BASE_MATCH_INCOME = Decimal("8.0000")
WIN_BONUS = Decimal("5.0000")
DRAW_BONUS = Decimal("2.0000")


class ClubFinanceError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(slots=True)
class ClubFinanceService:
    session: Session
    live_ops_service: LiveOpsService | None = None

    def __post_init__(self) -> None:
        if self.live_ops_service is None:
            self.live_ops_service = LiveOpsService(self.session)

    def seed_defaults(self) -> None:
        if self.session.scalar(select(Sponsor.id).limit(1)) is not None:
            return
        self.session.add_all(
            [
                Sponsor(
                    name="Lagos Local Works",
                    tier=SponsorTier.LOCAL,
                    payout=Decimal("75.0000"),
                    requirements_json={"min_wins": 2},
                ),
                Sponsor(
                    name="Coastal Telecom",
                    tier=SponsorTier.REGIONAL,
                    payout=Decimal("150.0000"),
                    requirements_json={"min_goals": 5},
                ),
                Sponsor(
                    name="Global Flight Group",
                    tier=SponsorTier.GLOBAL,
                    payout=Decimal("300.0000"),
                    requirements_json={"max_league_position": 3, "min_wins": 4},
                ),
            ]
        )
        self.session.flush()

    def get_or_create_profile(self, *, user_id: str) -> ClubFinanceProfile:
        profile = self.session.scalar(select(ClubFinanceProfile).where(ClubFinanceProfile.user_id == user_id))
        if profile is None:
            profile = ClubFinanceProfile(user_id=user_id)
            self.session.add(profile)
            self.session.flush()
        return profile

    def get_finance_view(self, *, actor: User, limit: int = 20) -> dict[str, object]:
        profile = self.get_or_create_profile(user_id=actor.id)
        transactions = list(
            self.session.scalars(
                select(ClubFinanceTransaction)
                .where(ClubFinanceTransaction.finance_profile_id == profile.id)
                .order_by(ClubFinanceTransaction.created_at.desc())
                .limit(limit)
            ).all()
        )
        return {"profile": profile, "transactions": transactions}

    def list_sponsors_for_user(self, *, actor: User) -> list[dict[str, object]]:
        sponsors = list(
            self.session.scalars(
                select(Sponsor).where(Sponsor.active.is_(True)).order_by(Sponsor.payout.asc())
            ).all()
        )
        return [self.evaluate_sponsor(user_id=actor.id, sponsor=sponsor) for sponsor in sponsors]

    def evaluate_sponsor(self, *, user_id: str, sponsor: Sponsor) -> dict[str, object]:
        metrics = self._build_user_metrics(user_id=user_id)
        requirements = dict(sponsor.requirements_json or {})
        requirements_met = True
        if int(requirements.get("min_wins", 0)) > int(metrics["wins"]):
            requirements_met = False
        if int(requirements.get("min_goals", 0)) > int(metrics["goals_scored"]):
            requirements_met = False
        max_position = requirements.get("max_league_position")
        if max_position is not None:
            best_position = metrics["best_league_position"]
            if best_position is None or int(best_position) > int(max_position):
                requirements_met = False
        return {
            "sponsor": sponsor,
            "requirements_met": requirements_met,
            "metrics_json": metrics,
        }

    def run_weekly_cycle(self, *, as_of: date | None = None) -> dict[str, int]:
        reference_date = as_of or datetime.now(UTC).date()
        profiles = list(self.session.scalars(select(ClubFinanceProfile)).all())
        sponsor_payouts = 0
        processed = 0
        for profile in profiles:
            if profile.last_weekly_cycle_on == reference_date:
                continue
            for sponsor_payload in self.list_sponsors_for_user(actor=self._require_user(profile.user_id)):
                sponsor = sponsor_payload["sponsor"]
                if not sponsor_payload["requirements_met"]:
                    continue
                created = self._record_finance_delta(
                    profile=profile,
                    amount=Decimal(sponsor.payout).quantize(DECIMAL_QUANTUM),
                    transaction_type="sponsor_payout",
                    reference_key=f"sponsor:{sponsor.id}:{profile.user_id}:{reference_date.isoformat()}",
                    sponsor_id=sponsor.id,
                    metadata={
                        "requirements": sponsor.requirements_json,
                        "metrics": sponsor_payload["metrics_json"],
                    },
                    bucket="sponsorship_income",
                )
                if created:
                    sponsor_payouts += 1
                    self.session.add(
                        NotificationRecord(
                            user_id=profile.user_id,
                            topic="sponsor_reward",
                            template_key="SPONSOR_REWARD",
                            resource_type="sponsor",
                            resource_id=sponsor.id,
                            message=f"Sponsor reward paid: {sponsor.name}."[:255],
                            metadata_json={
                                "sponsor_id": sponsor.id,
                                "payout": str(sponsor.payout),
                                "requirements": sponsor.requirements_json,
                            },
                        )
                    )
            cycle_reference = f"weekly-cycle:{profile.user_id}:{reference_date.isoformat()}"
            if self.session.scalar(select(ClubFinanceTransaction).where(ClubFinanceTransaction.reference_key == cycle_reference)) is not None:
                continue
            net_delta = (
                Decimal(profile.sponsorship_income)
                + Decimal(profile.match_income)
                + Decimal(profile.transfer_profit)
                - Decimal(profile.weekly_wages)
                - Decimal(profile.expenses)
            ).quantize(DECIMAL_QUANTUM)
            self.session.add(
                ClubFinanceTransaction(
                    finance_profile_id=profile.id,
                    user_id=profile.user_id,
                    transaction_type="weekly_cycle",
                    amount=net_delta,
                    reference_key=cycle_reference,
                    metadata_json={
                        "weekly_wages": str(profile.weekly_wages),
                        "sponsorship_income": str(profile.sponsorship_income),
                        "match_income": str(profile.match_income),
                        "transfer_profit": str(profile.transfer_profit),
                        "expenses": str(profile.expenses),
                    },
                    created_at=self._coerce_datetime(None),
                )
            )
            profile.balance = (Decimal(profile.balance) + net_delta).quantize(DECIMAL_QUANTUM)
            profile.sponsorship_income = Decimal("0.0000")
            profile.match_income = Decimal("0.0000")
            profile.transfer_profit = Decimal("0.0000")
            profile.expenses = Decimal("0.0000")
            profile.last_weekly_cycle_on = reference_date
            self._enforce_constraints(profile)
            processed += 1
        self.session.flush()
        return {"profiles_processed": processed, "sponsor_payouts": sponsor_payouts}

    def record_match_result(
        self,
        *,
        match_id: str,
        home_club_id: str | None,
        away_club_id: str | None,
        home_score: int,
        away_score: int,
        home_user_id: str | None = None,
        away_user_id: str | None = None,
    ) -> None:
        snapshot = self.live_ops_service.multiplier_snapshot()
        owners = {
            home_club_id: home_user_id or self._club_owner_id(home_club_id),
            away_club_id: away_user_id or self._club_owner_id(away_club_id),
        }
        for club_id in (home_club_id, away_club_id):
            user_id = owners.get(club_id)
            if user_id is None:
                continue
            bonus = DRAW_BONUS
            if home_score != away_score:
                winner_club_id = home_club_id if home_score > away_score else away_club_id
                bonus = WIN_BONUS if club_id == winner_club_id else Decimal("0.0000")
            amount = ((BASE_MATCH_INCOME + bonus) * Decimal(str(snapshot.match_income_multiplier))).quantize(DECIMAL_QUANTUM)
            self._record_finance_delta(
                profile=self.get_or_create_profile(user_id=user_id),
                amount=amount,
                transaction_type="match_income",
                reference_key=f"match-income:{match_id}:{club_id}",
                metadata={
                    "match_id": match_id,
                    "club_id": club_id,
                    "home_score": home_score,
                    "away_score": away_score,
                },
                bucket="match_income",
            )
        self.session.flush()

    def record_transfer_movement(
        self,
        *,
        buying_club_id: str | None,
        selling_club_id: str | None,
        amount: Decimal,
        reference_key: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        normalized_amount = Decimal(amount).quantize(DECIMAL_QUANTUM)
        if buying_club_id is not None:
            owner_id = self._club_owner_id(buying_club_id)
            if owner_id is not None:
                self._record_finance_delta(
                    profile=self.get_or_create_profile(user_id=owner_id),
                    amount=normalized_amount,
                    transaction_type="transfer_expense",
                    reference_key=f"{reference_key}:buyer",
                    metadata={"club_id": buying_club_id, **dict(metadata or {})},
                    bucket="expenses",
                )
        if selling_club_id is not None:
            owner_id = self._club_owner_id(selling_club_id)
            if owner_id is not None:
                self._record_finance_delta(
                    profile=self.get_or_create_profile(user_id=owner_id),
                    amount=normalized_amount,
                    transaction_type="transfer_profit",
                    reference_key=f"{reference_key}:seller",
                    metadata={"club_id": selling_club_id, **dict(metadata or {})},
                    bucket="transfer_profit",
                )
        self.session.flush()

    def assert_transfer_allowed_for_club(self, *, club_id: str) -> None:
        owner_id = self._club_owner_id(club_id)
        if owner_id is None:
            return
        profile = self.get_or_create_profile(user_id=owner_id)
        self._enforce_constraints(profile)
        if profile.transfers_blocked or Decimal(profile.balance) < Decimal("0.0000"):
            raise ClubFinanceError("Transfers are blocked while club finances are below zero.")

    def apply_season_pass_currency_bonus(
        self,
        *,
        user_id: str,
        amount: float,
        reference_key: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        if self.session.scalar(select(ClubFinanceTransaction).where(ClubFinanceTransaction.reference_key == reference_key)) is not None:
            return
        profile = self.get_or_create_profile(user_id=user_id)
        normalized_amount = Decimal(str(amount)).quantize(DECIMAL_QUANTUM)
        self.session.add(
            ClubFinanceTransaction(
                finance_profile_id=profile.id,
                user_id=user_id,
                transaction_type="season_pass_reward",
                amount=normalized_amount,
                reference_key=reference_key,
                metadata_json=dict(metadata or {}),
                created_at=self._coerce_datetime(None),
            )
        )
        profile.balance = (Decimal(profile.balance) + normalized_amount).quantize(DECIMAL_QUANTUM)
        self.session.flush()

    def _record_finance_delta(
        self,
        *,
        profile: ClubFinanceProfile,
        amount: Decimal,
        transaction_type: str,
        reference_key: str,
        metadata: dict[str, object] | None = None,
        bucket: str,
        sponsor_id: str | None = None,
    ) -> bool:
        if self.session.scalar(select(ClubFinanceTransaction).where(ClubFinanceTransaction.reference_key == reference_key)) is not None:
            return False
        self.session.add(
            ClubFinanceTransaction(
                finance_profile_id=profile.id,
                user_id=profile.user_id,
                sponsor_id=sponsor_id,
                transaction_type=transaction_type,
                amount=amount,
                reference_key=reference_key,
                metadata_json=dict(metadata or {}),
                created_at=self._coerce_datetime(None),
            )
        )
        setattr(profile, bucket, (Decimal(getattr(profile, bucket)) + amount).quantize(DECIMAL_QUANTUM))
        return True

    def _enforce_constraints(self, profile: ClubFinanceProfile) -> None:
        if Decimal(profile.balance) < Decimal("0.0000"):
            profile.transfers_blocked = True
            profile.forced_sale_required = True
            profile.forced_sale_player_id = self._forced_sale_candidate(profile.user_id)
            self.session.add(
                NotificationRecord(
                    user_id=profile.user_id,
                    topic="low_balance_alert",
                    template_key="LOW_BALANCE_ALERT",
                    resource_type="club_finance_profile",
                    resource_id=profile.id,
                    message="Club balance is below zero. Transfers are blocked."[:255],
                    metadata_json={
                        "finance_profile_id": profile.id,
                        "forced_sale_player_id": profile.forced_sale_player_id,
                        "balance": str(profile.balance),
                    },
                )
            )
        else:
            profile.transfers_blocked = False
            profile.forced_sale_required = False
            profile.forced_sale_player_id = None

    def _forced_sale_candidate(self, user_id: str) -> str | None:
        club_ids = list(self._owned_club_ids(user_id=user_id))
        if not club_ids:
            return None
        row = self.session.execute(
            select(Player.id)
            .join(PlayerContract, PlayerContract.player_id == Player.id)
            .where(
                PlayerContract.club_id.in_(club_ids),
                PlayerContract.status.in_(("active", "expiring")),
            )
            .order_by(Player.market_value_eur.desc(), Player.full_name.asc())
            .limit(1)
        ).first()
        return row[0] if row is not None else None

    def _build_user_metrics(self, *, user_id: str) -> dict[str, object]:
        club_ids = tuple(self._owned_club_ids(user_id=user_id))
        if not club_ids:
            return {"wins": 0, "goals_scored": 0, "best_league_position": None}
        wins = int(
            self.session.scalar(
                select(func.coalesce(func.sum(CompetitionParticipant.wins), 0)).where(
                    CompetitionParticipant.club_id.in_(club_ids)
                )
            )
            or 0
        )
        matches = list(
            self.session.scalars(
                select(CompetitionMatch).where(
                    CompetitionMatch.status == "completed",
                    (CompetitionMatch.home_club_id.in_(club_ids)) | (CompetitionMatch.away_club_id.in_(club_ids)),
                )
            ).all()
        )
        goals_scored = 0
        for match in matches:
            if match.home_club_id in club_ids:
                goals_scored += int(match.home_score or 0)
            if match.away_club_id in club_ids:
                goals_scored += int(match.away_score or 0)
        best_position: int | None = None
        participants = list(
            self.session.scalars(
                select(CompetitionParticipant).where(CompetitionParticipant.club_id.in_(club_ids))
            ).all()
        )
        competition_ids = {participant.competition_id for participant in participants}
        for competition_id in competition_ids:
            standings = list(
                self.session.scalars(
                    select(CompetitionParticipant)
                    .where(CompetitionParticipant.competition_id == competition_id)
                    .order_by(
                        CompetitionParticipant.points.desc(),
                        CompetitionParticipant.goal_diff.desc(),
                        CompetitionParticipant.goals_for.desc(),
                    )
                ).all()
            )
            for index, participant in enumerate(standings, start=1):
                if participant.club_id in club_ids and (best_position is None or index < best_position):
                    best_position = index
        return {"wins": wins, "goals_scored": goals_scored, "best_league_position": best_position}

    def _owned_club_ids(self, user_id: str) -> list[str]:
        return list(self.session.scalars(select(ClubProfile.id).where(ClubProfile.owner_user_id == user_id)).all())

    def _club_owner_id(self, club_id: str | None) -> str | None:
        if not club_id:
            return None
        club = self.session.get(ClubProfile, club_id)
        return club.owner_user_id if club is not None else None

    def _require_user(self, user_id: str) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise ClubFinanceError(f"User {user_id} was not found.")
        return user

    @staticmethod
    def _coerce_datetime(value: datetime | None) -> datetime:
        resolved = value or datetime.now(UTC)
        if resolved.tzinfo is None:
            return resolved.replace(tzinfo=UTC)
        return resolved.astimezone(UTC)


__all__ = ["ClubFinanceError", "ClubFinanceService"]
