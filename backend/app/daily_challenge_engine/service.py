from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.admin_engine.service import AdminEngineService
from backend.app.models.daily_challenge import DailyChallenge, DailyChallengeClaim, DailyChallengeStatus
from backend.app.models.user import User
from backend.app.reward_engine.service import RewardEngineService

DEFAULT_DAILY_CHALLENGES: tuple[dict[str, object], ...] = (
    {
        'challenge_key': 'daily-login',
        'title': 'Daily Login Bonus',
        'description': 'Check in once per day to keep your club heartbeat alive.',
        'reward_amount': Decimal('25.0000'),
        'reward_unit': 'credit',
        'claim_limit_per_day': 1,
        'sort_order': 10,
        'status': DailyChallengeStatus.ACTIVE,
        'metadata_json': {'action': 'login'},
    },
    {
        'challenge_key': 'story-feed-reader',
        'title': 'Read the Story Feed',
        'description': 'Catch up on rivalries, giant killers, and match drama once per day.',
        'reward_amount': Decimal('15.0000'),
        'reward_unit': 'credit',
        'claim_limit_per_day': 1,
        'sort_order': 20,
        'status': DailyChallengeStatus.ACTIVE,
        'metadata_json': {'action': 'story_feed_open'},
    },
    {
        'challenge_key': 'watch-highlight',
        'title': 'Watch a Highlight',
        'description': 'Replay one match highlight to earn a small FanCoin nudge.',
        'reward_amount': Decimal('20.0000'),
        'reward_unit': 'credit',
        'claim_limit_per_day': 1,
        'sort_order': 30,
        'status': DailyChallengeStatus.ACTIVE,
        'metadata_json': {'action': 'highlight_watch'},
    },
)


class DailyChallengeError(ValueError):
    pass


@dataclass(slots=True)
class DailyChallengeService:
    session: Session

    def seed_defaults(self) -> None:
        existing = {item.challenge_key for item in self.session.scalars(select(DailyChallenge)).all()}
        for payload in DEFAULT_DAILY_CHALLENGES:
            if payload['challenge_key'] in existing:
                continue
            self.session.add(DailyChallenge(**payload))
        self.session.flush()

    def feature_enabled(self) -> bool:
        flags = AdminEngineService(self.session).list_feature_flags(active_only=True)
        return any(item.feature_key == 'daily-challenges' for item in flags)

    def list_challenges(self) -> list[DailyChallenge]:
        stmt = select(DailyChallenge).where(DailyChallenge.status == DailyChallengeStatus.ACTIVE).order_by(DailyChallenge.sort_order.asc(), DailyChallenge.challenge_key.asc())
        return list(self.session.scalars(stmt).all())

    def claims_for_user_on(self, *, user: User, claim_day) -> list[DailyChallengeClaim]:
        stmt = select(DailyChallengeClaim).where(DailyChallengeClaim.user_id == user.id, DailyChallengeClaim.claim_date == claim_day).order_by(DailyChallengeClaim.claimed_at.desc())
        return list(self.session.scalars(stmt).all())

    def claim(self, *, user: User, challenge_key: str) -> DailyChallengeClaim:
        if not self.feature_enabled():
            raise DailyChallengeError('Daily challenges are disabled by admin feature flag.')
        challenge = self.session.scalar(select(DailyChallenge).where(DailyChallenge.challenge_key == challenge_key, DailyChallenge.status == DailyChallengeStatus.ACTIVE))
        if challenge is None:
            raise DailyChallengeError('Daily challenge was not found.')
        today = datetime.now(UTC).date()
        existing_count = self.session.scalar(select(func.count(DailyChallengeClaim.id)).where(DailyChallengeClaim.user_id == user.id, DailyChallengeClaim.challenge_id == challenge.id, DailyChallengeClaim.claim_date == today)) or 0
        if int(existing_count) >= int(challenge.claim_limit_per_day):
            raise DailyChallengeError('Daily challenge has already been claimed for today.')

        reward_service = RewardEngineService(self.session)
        settlement = reward_service.settle_reward(
            actor=user,
            user_id=user.id,
            competition_key=f'daily:{challenge.challenge_key}:{today.isoformat()}',
            title=challenge.title,
            gross_amount=challenge.reward_amount,
            reward_source='daily_challenge',
            note='Daily challenge reward',
        )
        claim = DailyChallengeClaim(
            user_id=user.id,
            challenge_id=challenge.id,
            claim_date=today,
            reward_amount=challenge.reward_amount,
            reward_unit=challenge.reward_unit,
            reward_settlement_id=settlement.id,
            metadata_json={'challenge_key': challenge.challenge_key},
        )
        self.session.add(claim)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise DailyChallengeError('Daily challenge has already been claimed for today.') from exc
        return claim
