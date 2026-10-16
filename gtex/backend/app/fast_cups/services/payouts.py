from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, ROUND_DOWN

from app.fast_cups.models.domain import (
    CupReward,
    FastCup,
    FastCupBracket,
    FastCupResultSummary,
    PayoutLedgerEvent,
)

_FOUR_PLACES = Decimal("0.0001")
_REWARD_POOL_SHARE = Decimal("0.8500")
_CHAMPION_SHARE = Decimal("0.6000")
_RUNNER_UP_SHARE = Decimal("0.2500")
_SEMIFINAL_SHARE = Decimal("0.0750")


class FastCupRewardPayoutService:
    def build_result_summary(
        self,
        *,
        cup: FastCup,
        bracket: FastCupBracket,
        concluded_at: datetime,
    ) -> FastCupResultSummary:
        if bracket.champion is None or bracket.runner_up is None or len(bracket.semifinalists) != 2:
            raise ValueError("A completed fast cup bracket is required to settle rewards.")

        prize_pool = (cup.buy_in * Decimal(cup.size)).quantize(_FOUR_PLACES, rounding=ROUND_DOWN)
        reward_pool = (prize_pool * _REWARD_POOL_SHARE).quantize(_FOUR_PLACES, rounding=ROUND_DOWN)
        platform_fee = (prize_pool - reward_pool).quantize(_FOUR_PLACES, rounding=ROUND_DOWN)

        champion_reward = (reward_pool * _CHAMPION_SHARE).quantize(_FOUR_PLACES, rounding=ROUND_DOWN)
        runner_up_reward = (reward_pool * _RUNNER_UP_SHARE).quantize(_FOUR_PLACES, rounding=ROUND_DOWN)
        semifinal_reward = (reward_pool * _SEMIFINAL_SHARE).quantize(_FOUR_PLACES, rounding=ROUND_DOWN)

        rewards = (
            CupReward(
                club_id=bracket.champion.club_id,
                club_name=bracket.champion.club_name,
                finish="champion",
                amount=champion_reward,
                currency=cup.currency,
            ),
            CupReward(
                club_id=bracket.runner_up.club_id,
                club_name=bracket.runner_up.club_name,
                finish="runner_up",
                amount=runner_up_reward,
                currency=cup.currency,
            ),
            CupReward(
                club_id=bracket.semifinalists[0].club_id,
                club_name=bracket.semifinalists[0].club_name,
                finish="semifinalist",
                amount=semifinal_reward,
                currency=cup.currency,
            ),
            CupReward(
                club_id=bracket.semifinalists[1].club_id,
                club_name=bracket.semifinalists[1].club_name,
                finish="semifinalist",
                amount=semifinal_reward,
                currency=cup.currency,
            ),
        )
        events = (
            _event(
                cup=cup,
                suffix="pool-funded",
                event_type="fast_cup.prize_pool_funded",
                amount=prize_pool,
                payload={"division": cup.division.value, "size": str(cup.size)},
            ),
            _event(
                cup=cup,
                suffix="champion",
                event_type="fast_cup.champion_paid",
                amount=champion_reward,
                payload={"club_id": bracket.champion.club_id, "finish": "champion"},
            ),
            _event(
                cup=cup,
                suffix="runner-up",
                event_type="fast_cup.runner_up_paid",
                amount=runner_up_reward,
                payload={"club_id": bracket.runner_up.club_id, "finish": "runner_up"},
            ),
            _event(
                cup=cup,
                suffix="semi-1",
                event_type="fast_cup.semifinal_paid",
                amount=semifinal_reward,
                payload={"club_id": bracket.semifinalists[0].club_id, "finish": "semifinalist"},
            ),
            _event(
                cup=cup,
                suffix="semi-2",
                event_type="fast_cup.semifinal_paid",
                amount=semifinal_reward,
                payload={"club_id": bracket.semifinalists[1].club_id, "finish": "semifinalist"},
            ),
            _event(
                cup=cup,
                suffix="platform-fee",
                event_type="fast_cup.platform_fee_reserved",
                amount=platform_fee,
                payload={"division": cup.division.value, "size": str(cup.size)},
            ),
        )
        penalty_shootouts = sum(
            1
            for round_entry in bracket.rounds
            for match in round_entry.matches
            if match.decided_by_penalties
        )
        return FastCupResultSummary(
            cup_id=cup.cup_id,
            division=cup.division,
            size=cup.size,
            champion=bracket.champion,
            runner_up=bracket.runner_up,
            semifinalists=bracket.semifinalists,
            total_rounds=bracket.total_rounds,
            total_matches=bracket.total_matches,
            expected_duration_minutes=bracket.expected_duration_minutes,
            concluded_at=_normalize_timestamp(concluded_at),
            prize_pool=prize_pool,
            reward_pool=reward_pool,
            platform_fee=platform_fee,
            currency=cup.currency,
            penalty_shootouts=penalty_shootouts,
            rewards=rewards,
            events=events,
        )


def _event(
    *,
    cup: FastCup,
    suffix: str,
    event_type: str,
    amount: Decimal,
    payload: dict[str, str],
) -> PayoutLedgerEvent:
    return PayoutLedgerEvent(
        event_key=f"{cup.cup_id}:{suffix}",
        event_type=event_type,
        aggregate_id=cup.cup_id,
        amount=amount,
        currency=cup.currency,
        payload=payload,
    )


def _normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
