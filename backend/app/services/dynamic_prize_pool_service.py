from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.competition import Competition
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_reward import CompetitionReward
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.fancoin_purchase_order import FancoinPurchaseOrder
from app.models.gift_transaction import GiftTransaction
from app.models.manager_market import ManagerTradeRecord
from app.models.user import User

AMOUNT_QUANTUM = Decimal("0.0001")
ACTIVITY_WINDOW = timedelta(minutes=5)
DEFAULT_PLATFORM_BASE_FUNDING_PER_SLOT = Decimal("1.2500")
MIN_PLATFORM_BASE_FUNDING = Decimal("25.0000")
ACTIVE_USER_BOOST_MULTIPLIER = Decimal("0.1000")
TRADE_VOLUME_BOOST_MULTIPLIER = Decimal("0.0005")
PLATFORM_SOURCE_TYPES = frozenset(
    {"gtex", "platform", "gtex_platform", "gtex_competition", "gtex_hosted"}
)


@dataclass(frozen=True, slots=True)
class DynamicPrizePoolSnapshot:
    enabled: bool
    base_funding: Decimal
    activity_boost: Decimal
    jackpot_rollover: Decimal
    total_pool: Decimal
    active_users_5min: int
    trade_volume_5min: Decimal

    @property
    def base_funding_minor(self) -> int:
        return _to_minor_units(self.base_funding)

    @property
    def activity_boost_minor(self) -> int:
        return _to_minor_units(self.activity_boost)

    @property
    def jackpot_rollover_minor(self) -> int:
        return _to_minor_units(self.jackpot_rollover)

    @property
    def total_pool_minor(self) -> int:
        return _to_minor_units(self.total_pool)

    def metadata_json(self) -> dict[str, object]:
        return {
            "dynamic_prize_pool": {
                "enabled": self.enabled,
                "base_funding_minor": self.base_funding_minor,
                "activity_boost_minor": self.activity_boost_minor,
                "jackpot_rollover_minor": self.jackpot_rollover_minor,
                "total_pool_minor": self.total_pool_minor,
                "active_users_5min": self.active_users_5min,
                "trade_volume_5min": str(self.trade_volume_5min),
                "calculated_at": datetime.now(timezone.utc).isoformat(),
            }
        }


@dataclass(slots=True)
class DynamicPrizePoolService:
    session: Session

    def snapshot(
        self,
        *,
        competition: Competition,
        rule_set: CompetitionRuleSet,
        exclude_competition_id: str | None = None,
    ) -> DynamicPrizePoolSnapshot:
        if not self.is_enabled_for(competition):
            return DynamicPrizePoolSnapshot(
                enabled=False,
                base_funding=Decimal("0.0000"),
                activity_boost=Decimal("0.0000"),
                jackpot_rollover=Decimal("0.0000"),
                total_pool=Decimal("0.0000"),
                active_users_5min=0,
                trade_volume_5min=Decimal("0.0000"),
            )

        base_funding = self._base_funding(competition=competition, rule_set=rule_set)
        active_users = self._active_users_5min()
        trade_volume = self._trade_volume_5min()
        activity_boost = _normalize_amount(
            (Decimal(active_users) * ACTIVE_USER_BOOST_MULTIPLIER)
            + (trade_volume * TRADE_VOLUME_BOOST_MULTIPLIER)
        )
        jackpot_rollover = self._jackpot_rollover(exclude_competition_id=exclude_competition_id)
        total_pool = _normalize_amount(base_funding + activity_boost + jackpot_rollover)
        return DynamicPrizePoolSnapshot(
            enabled=True,
            base_funding=base_funding,
            activity_boost=activity_boost,
            jackpot_rollover=jackpot_rollover,
            total_pool=total_pool,
            active_users_5min=active_users,
            trade_volume_5min=trade_volume,
        )

    def is_enabled_for(self, competition: Competition) -> bool:
        source_type = (competition.source_type or "").strip().lower()
        return source_type in PLATFORM_SOURCE_TYPES

    def apply_to_reward_pool(self, *, metadata_json: dict[str, object] | None, snapshot: DynamicPrizePoolSnapshot) -> dict[str, object]:
        return {
            **dict(metadata_json or {}),
            **snapshot.metadata_json(),
        }

    def _base_funding(self, *, competition: Competition, rule_set: CompetitionRuleSet) -> Decimal:
        metadata = dict(competition.metadata_json or {})
        configured = metadata.get("dynamic_prize_pool")
        if isinstance(configured, dict):
            base_minor = configured.get("base_funding_minor")
            if base_minor is not None:
                parsed_minor = _parse_int(base_minor)
                if parsed_minor is not None and parsed_minor >= 0:
                    return _from_minor_units(parsed_minor)
            base_amount = configured.get("base_funding")
            if base_amount is not None:
                parsed_amount = _parse_decimal(base_amount)
                if parsed_amount is not None and parsed_amount >= Decimal("0.0000"):
                    return _normalize_amount(parsed_amount)

        capacity = max(2, int(rule_set.max_participants or 2))
        derived = Decimal(capacity) * DEFAULT_PLATFORM_BASE_FUNDING_PER_SLOT
        return _normalize_amount(max(derived, MIN_PLATFORM_BASE_FUNDING))

    def _active_users_5min(self) -> int:
        window_start = datetime.now(timezone.utc) - ACTIVITY_WINDOW
        identifiers: set[str] = set()

        login_rows = self.session.scalars(
            select(User.id).where(
                User.is_active.is_(True),
                User.last_login_at.is_not(None),
                User.last_login_at >= window_start,
            )
        ).all()
        identifiers.update(item for item in login_rows if item)

        participant_rows = self.session.scalars(
            select(CompetitionParticipant.club_id).where(CompetitionParticipant.joined_at >= window_start)
        ).all()
        identifiers.update(item for item in participant_rows if item)

        purchase_rows = self.session.scalars(
            select(FancoinPurchaseOrder.user_id).where(FancoinPurchaseOrder.created_at >= window_start)
        ).all()
        identifiers.update(item for item in purchase_rows if item)

        gift_sender_rows = self.session.scalars(
            select(GiftTransaction.sender_user_id).where(GiftTransaction.created_at >= window_start)
        ).all()
        identifiers.update(item for item in gift_sender_rows if item)

        gift_recipient_rows = self.session.scalars(
            select(GiftTransaction.recipient_user_id).where(GiftTransaction.created_at >= window_start)
        ).all()
        identifiers.update(item for item in gift_recipient_rows if item)

        return len(identifiers)

    def _trade_volume_5min(self) -> Decimal:
        window_start = datetime.now(timezone.utc) - ACTIVITY_WINDOW
        values = self.session.scalars(
            select(ManagerTradeRecord.gross_credits).where(
                ManagerTradeRecord.created_at >= window_start,
                func.lower(ManagerTradeRecord.settlement_status) == "settled",
            )
        ).all()
        total = Decimal("0.0000")
        for value in values:
            parsed = _parse_decimal(value)
            if parsed is None:
                continue
            total += parsed
        return _normalize_amount(total)

    def _jackpot_rollover(self, *, exclude_competition_id: str | None = None) -> Decimal:
        stmt = (
            select(CompetitionReward.amount_minor)
            .join(Competition, Competition.id == CompetitionReward.competition_id)
            .where(
                Competition.source_type.is_not(None),
                func.lower(Competition.source_type).in_(tuple(PLATFORM_SOURCE_TYPES)),
                func.lower(CompetitionReward.status) != "settled",
            )
        )
        if exclude_competition_id:
            stmt = stmt.where(CompetitionReward.competition_id != exclude_competition_id)
        pending_minor = self.session.scalars(stmt).all()
        total_minor = sum(int(value or 0) for value in pending_minor)
        return _from_minor_units(max(total_minor, 0))


def _normalize_amount(value: Decimal) -> Decimal:
    return Decimal(value).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)


def _to_minor_units(value: Decimal) -> int:
    return int(_normalize_amount(value) * Decimal("10000"))


def _from_minor_units(value: int) -> Decimal:
    return _normalize_amount(Decimal(value) / Decimal("10000"))


def _parse_decimal(value: object) -> Decimal | None:
    try:
        return _normalize_amount(Decimal(str(value)))
    except Exception:
        return None


def _parse_int(value: object) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


__all__ = [
    "ACTIVE_USER_BOOST_MULTIPLIER",
    "ACTIVITY_WINDOW",
    "DEFAULT_PLATFORM_BASE_FUNDING_PER_SLOT",
    "DynamicPrizePoolService",
    "DynamicPrizePoolSnapshot",
    "MIN_PLATFORM_BASE_FUNDING",
    "TRADE_VOLUME_BOOST_MULTIPLIER",
]
