from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin_engine.service import AdminEngineService
from app.models.daily_challenge import DailyChallenge, DailyChallengeClaim, DailyChallengeStatus
from app.models.user import User
from app.models.wallet import LedgerUnit
from app.reward_engine.service import RewardEngineService

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

    def build_login_streak(self, *, user: User) -> dict[str, object]:
        daily_login = self.session.scalar(
            select(DailyChallenge).where(DailyChallenge.challenge_key == "daily-login")
        )
        if daily_login is None:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "today_claimed": False,
                "next_bonus_amount": Decimal("0.0000"),
            }
        claimed_dates = sorted(
            {
                item.claim_date
                for item in self.session.scalars(
                    select(DailyChallengeClaim)
                    .where(
                        DailyChallengeClaim.user_id == user.id,
                        DailyChallengeClaim.challenge_id == daily_login.id,
                    )
                    .order_by(DailyChallengeClaim.claim_date.desc())
                ).all()
            }
        )
        today = datetime.now(UTC).date()
        claimed_lookup = set(claimed_dates)
        today_claimed = today in claimed_lookup
        cursor = today if today_claimed else today - timedelta(days=1)
        current_streak = 0
        while cursor in claimed_lookup:
            current_streak += 1
            cursor -= timedelta(days=1)

        longest_streak = 0
        running = 0
        previous = None
        for claim_date in claimed_dates:
            if previous is not None and claim_date == previous + timedelta(days=1):
                running += 1
            else:
                running = 1
            longest_streak = max(longest_streak, running)
            previous = claim_date

        next_bonus_amount = min(Decimal(current_streak) * Decimal("5.0000"), Decimal("25.0000"))
        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "today_claimed": today_claimed,
            "next_bonus_amount": next_bonus_amount.quantize(Decimal("0.0001")),
        }

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
        streak_snapshot = self.build_login_streak(user=user)
        bonus_amount = Decimal("0.0000")
        reward_amount = challenge.reward_amount
        if challenge.challenge_key == "daily-login":
            bonus_amount = Decimal(str(streak_snapshot["next_bonus_amount"]))
            reward_amount = (Decimal(challenge.reward_amount) + bonus_amount).quantize(Decimal("0.0001"))
        reward_unit = str(challenge.reward_unit or "").strip().lower()
        settlement = reward_service.settle_reward(
            actor=user,
            user_id=user.id,
            competition_key=f'daily:{challenge.challenge_key}:{today.isoformat()}',
            title=challenge.title,
            gross_amount=reward_amount,
            reward_source='daily_challenge',
            note='Daily challenge reward',
            ledger_unit=LedgerUnit.CREDIT if reward_unit == "credit" else LedgerUnit.COIN,
        )
        claim = DailyChallengeClaim(
            user_id=user.id,
            challenge_id=challenge.id,
            claim_date=today,
            reward_amount=reward_amount,
            reward_unit=challenge.reward_unit,
            reward_settlement_id=settlement.id,
            metadata_json={
                'challenge_key': challenge.challenge_key,
                'streak_before_claim': streak_snapshot["current_streak"],
                'bonus_amount': str(bonus_amount.quantize(Decimal("0.0001"))),
            },
        )
        self.session.add(claim)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise DailyChallengeError('Daily challenge has already been claimed for today.') from exc
        return claim
