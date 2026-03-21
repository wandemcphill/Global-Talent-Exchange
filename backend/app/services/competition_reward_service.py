from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from app.models.competition_reward import CompetitionReward
from app.models.competition_reward_pool import CompetitionRewardPool
from app.models.competition_prize_rule import CompetitionPrizeRule
from app.models.competition_participant import CompetitionParticipant


@dataclass(slots=True)
class CompetitionRewardService:
    def build_rewards(
        self,
        *,
        competition_id: str,
        pool: CompetitionRewardPool,
        prize_rule: CompetitionPrizeRule,
        standings: Iterable[CompetitionParticipant],
        settle: bool,
    ) -> list[CompetitionReward]:
        percentages = list(prize_rule.payout_percentages or [])
        if prize_rule.top_n:
            percentages = percentages[: prize_rule.top_n]
        if not percentages:
            return []

        total_pool = pool.amount_minor
        rewards: list[CompetitionReward] = []
        distributed = 0
        for index, (participant, percent) in enumerate(zip(standings, percentages, strict=False), start=1):
            amount = (total_pool * int(percent)) // 100
            distributed += amount
            reward = CompetitionReward(
                competition_id=competition_id,
                reward_pool_id=pool.id,
                participant_id=participant.id,
                club_id=participant.club_id,
                placement=index,
                reward_type="prize",
                currency=pool.currency,
                amount_minor=amount,
                status="settled" if settle else "pending",
                settled_at=datetime.now(timezone.utc) if settle else None,
                metadata_json={"percent": percent},
            )
            rewards.append(reward)
        remainder = total_pool - distributed
        if rewards and remainder > 0:
            rewards[0].amount_minor += remainder
        return rewards


__all__ = ["CompetitionRewardService"]
