from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.event_backbone import defer_event_publish_until_commit, defer_session_callback_until_commit
from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from app.leaderboards.leaderboard_service import LeaderboardService
from app.leaderboards.models import (
    LeaderboardPlayerRating,
    LeaderboardSeason,
    LeaderboardSeasonReward,
    LeaderboardSeasonSnapshot,
    ResetStrategy,
    RewardDeliveryStatus,
    SeasonStatus,
)
from app.leaderboards.ranking_service import DEFAULT_K_FACTOR, DEFAULT_RATING, RankingService
from app.models.history_engagement import UserProfile
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService

DEFAULT_SEASON_DURATION_DAYS = 90
DEFAULT_SOFT_RESET_FACTOR = 0.5
DEFAULT_REWARD_BOARD = "global"


class SeasonError(ValueError):
    pass


class SeasonNotFoundError(SeasonError):
    pass


@dataclass(frozen=True, slots=True)
class SeasonRewardTier:
    rank_position: int
    coins: Decimal
    trophies: int
    badges: tuple[str, ...]


DEFAULT_REWARD_TIERS: tuple[SeasonRewardTier, ...] = (
    SeasonRewardTier(rank_position=1, coins=Decimal("1000.0000"), trophies=3, badges=("season_champion",)),
    SeasonRewardTier(rank_position=2, coins=Decimal("500.0000"), trophies=2, badges=("season_finalist",)),
    SeasonRewardTier(rank_position=3, coins=Decimal("250.0000"), trophies=1, badges=("season_podium",)),
)


@dataclass(frozen=True, slots=True)
class SeasonLifecycleResult:
    ended_season: LeaderboardSeason
    next_season: LeaderboardSeason | None
    rewards: tuple[LeaderboardSeasonReward, ...]


@dataclass(slots=True)
class SeasonService:
    session: Session
    event_publisher: EventPublisher | None = None
    redis_url: str | None = None
    session_factory: sessionmaker[Session] | None = None
    wallet_service: WalletService | None = None
    leaderboard_service: LeaderboardService | None = None

    def __post_init__(self) -> None:
        if self.event_publisher is None:
            self.event_publisher = InMemoryEventPublisher()
        if self.wallet_service is None:
            self.wallet_service = WalletService(event_publisher=self.event_publisher)
        if self.leaderboard_service is None:
            self.leaderboard_service = LeaderboardService(session=self.session, redis_url=self.redis_url)

    def get_current_season(self, *, auto_rollover: bool = True) -> LeaderboardSeason:
        current = self.session.scalar(
            select(LeaderboardSeason)
            .where(LeaderboardSeason.status == SeasonStatus.ACTIVE)
            .order_by(LeaderboardSeason.start_date.desc(), LeaderboardSeason.created_at.desc())
        )
        now = self._now()
        if current is None:
            return self.start_new_season(start_date=now)
        if auto_rollover and self._normalize_timestamp(current.end_date) <= now:
            lifecycle = self.end_season(season_id=current.id, create_next_season=True)
            return lifecycle.next_season or lifecycle.ended_season
        return current

    def get_history(self, *, limit: int = 20) -> list[LeaderboardSeason]:
        return list(
            self.session.scalars(
                select(LeaderboardSeason)
                .order_by(LeaderboardSeason.start_date.desc(), LeaderboardSeason.created_at.desc())
                .limit(max(1, int(limit)))
            ).all()
        )

    def start_new_season(
        self,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        reset_strategy: ResetStrategy | str | None = None,
        soft_reset_factor: float | None = None,
        seed_previous: bool = True,
    ) -> LeaderboardSeason:
        active = self.session.scalar(
            select(LeaderboardSeason).where(LeaderboardSeason.status == SeasonStatus.ACTIVE)
        )
        if active is not None:
            raise SeasonError("An active leaderboard season already exists.")

        now = self._normalize_timestamp(start_date or self._now())
        duration_days = max(1, int(os.getenv("GTE_LEADERBOARD_SEASON_DURATION_DAYS", DEFAULT_SEASON_DURATION_DAYS)))
        resolved_end_date = self._normalize_timestamp(end_date or (now + timedelta(days=duration_days)))
        latest_ended = self.session.scalar(
            select(LeaderboardSeason)
            .where(LeaderboardSeason.status == SeasonStatus.ENDED)
            .order_by(LeaderboardSeason.end_date.desc(), LeaderboardSeason.updated_at.desc())
        )
        resolved_default_rating = int(latest_ended.default_rating) if latest_ended is not None else DEFAULT_RATING
        resolved_k_factor = int(latest_ended.k_factor) if latest_ended is not None else DEFAULT_K_FACTOR
        resolved_reset_strategy = self._resolve_reset_strategy(
            reset_strategy or (latest_ended.reset_strategy if latest_ended is not None else ResetStrategy.SOFT)
        )
        resolved_soft_reset_factor = float(
            soft_reset_factor
            if soft_reset_factor is not None
            else (latest_ended.soft_reset_factor if latest_ended is not None else DEFAULT_SOFT_RESET_FACTOR)
        )

        season = LeaderboardSeason(
            start_date=now,
            end_date=resolved_end_date,
            status=SeasonStatus.ACTIVE,
            default_rating=resolved_default_rating,
            k_factor=resolved_k_factor,
            reset_strategy=resolved_reset_strategy,
            soft_reset_factor=resolved_soft_reset_factor,
            metadata_json={},
        )
        self.session.add(season)
        self.session.flush()
        self.session.info["leaderboard.redis_needs_rebuild"] = True

        if seed_previous and latest_ended is not None:
            previous_rows = list(
                self.session.scalars(
                    select(LeaderboardPlayerRating)
                    .where(LeaderboardPlayerRating.season_id == latest_ended.id)
                    .order_by(LeaderboardPlayerRating.rating.desc(), LeaderboardPlayerRating.player_id.asc())
                ).all()
            )
            for row in previous_rows:
                seeded_rating = self._reset_rating(
                    old_rating=row.rating,
                    default_rating=season.default_rating,
                    strategy=season.reset_strategy,
                    soft_reset_factor=season.soft_reset_factor,
                )
                self.session.add(
                    LeaderboardPlayerRating(
                        season_id=season.id,
                        player_id=row.player_id,
                        display_name=row.display_name,
                        region=row.region,
                        division=RankingService.division_for_rating(seeded_rating),
                        rating=seeded_rating,
                        points=0,
                        matches_played=0,
                        wins=0,
                        losses=0,
                        draws=0,
                        highest_rating=seeded_rating,
                        last_rating_delta=0,
                        last_match_id=None,
                        last_result=None,
                        last_active_at=None,
                        metadata_json=dict(row.metadata_json or {}),
                    )
                )
            self.session.flush()

        self._defer_event(
            DomainEvent(
                name="season.started",
                payload={
                    "season_id": season.id,
                    "start_date": season.start_date,
                    "end_date": season.end_date,
                    "default_rating": season.default_rating,
                    "k_factor": season.k_factor,
                    "reset_strategy": season.reset_strategy,
                    "soft_reset_factor": season.soft_reset_factor,
                },
                aggregate_id=season.id,
                aggregate_type="leaderboard_season",
                partition_key=season.id,
                producer="leaderboard-service",
            )
        )
        self._defer_redis_rebuild(season.id)
        return season

    def end_season(
        self,
        *,
        season_id: str | None = None,
        create_next_season: bool = True,
    ) -> SeasonLifecycleResult:
        season = self._season_for_update(season_id=season_id)
        if season.status == SeasonStatus.ENDED:
            next_season = self.session.scalar(
                select(LeaderboardSeason)
                .where(LeaderboardSeason.status == SeasonStatus.ACTIVE)
                .order_by(LeaderboardSeason.start_date.desc())
            )
            rewards = tuple(
                self.session.scalars(
                    select(LeaderboardSeasonReward).where(LeaderboardSeasonReward.season_id == season.id)
                ).all()
            )
            return SeasonLifecycleResult(ended_season=season, next_season=next_season, rewards=rewards)

        ranked_rows = self._ordered_rows(season.id)
        self._snapshot_leaderboards(season=season, rows=ranked_rows)
        rewards = tuple(self._distribute_rewards(season=season, rows=ranked_rows))
        now = self._now()
        season.status = SeasonStatus.ENDED
        season.ended_at = now
        season.rewards_distributed_at = now
        self.session.info["leaderboard.redis_needs_rebuild"] = True
        self.session.flush()

        next_season: LeaderboardSeason | None = None
        if create_next_season:
            next_start = max(now, self._normalize_timestamp(season.end_date))
            next_season = self.start_new_season(
                start_date=next_start,
                reset_strategy=season.reset_strategy,
                soft_reset_factor=season.soft_reset_factor,
                seed_previous=True,
            )
        else:
            self._defer_redis_clear()

        self._defer_event(
            DomainEvent(
                name="season.rewards.distributed",
                payload={
                    "season_id": season.id,
                    "reward_count": len(rewards),
                    "board_key": DEFAULT_REWARD_BOARD,
                    "rewards": [
                        {
                            "player_id": reward.player_id,
                            "display_name": reward.display_name,
                            "rank_position": reward.rank_position,
                            "coins": str(reward.coins),
                            "trophies": reward.trophies,
                            "badges": list(reward.badges_json or []),
                            "status": reward.status,
                        }
                        for reward in rewards
                    ],
                },
                aggregate_id=season.id,
                aggregate_type="leaderboard_season",
                partition_key=season.id,
                producer="leaderboard-service",
            )
        )
        self._defer_event(
            DomainEvent(
                name="season.ended",
                payload={
                    "season_id": season.id,
                    "ended_at": season.ended_at,
                    "next_season_id": next_season.id if next_season is not None else None,
                },
                aggregate_id=season.id,
                aggregate_type="leaderboard_season",
                partition_key=season.id,
                producer="leaderboard-service",
            )
        )
        return SeasonLifecycleResult(ended_season=season, next_season=next_season, rewards=rewards)

    def _snapshot_leaderboards(self, *, season: LeaderboardSeason, rows: list[LeaderboardPlayerRating]) -> None:
        if self.session.scalar(
            select(LeaderboardSeasonSnapshot.id).where(LeaderboardSeasonSnapshot.season_id == season.id)
        ) is not None:
            return
        captured_at = self._now()
        self._snapshot_board(season_id=season.id, board_key="global", rows=rows, captured_at=captured_at)
        region_groups: dict[str, list[LeaderboardPlayerRating]] = defaultdict(list)
        division_groups: dict[str, list[LeaderboardPlayerRating]] = defaultdict(list)
        for row in rows:
            if row.region:
                region_groups[row.region].append(row)
            if row.division:
                division_groups[row.division].append(row)
        for region, grouped_rows in sorted(region_groups.items()):
            self._snapshot_board(
                season_id=season.id,
                board_key=f"region:{region}",
                rows=grouped_rows,
                captured_at=captured_at,
            )
        for division, grouped_rows in sorted(division_groups.items()):
            self._snapshot_board(
                season_id=season.id,
                board_key=f"division:{division}",
                rows=grouped_rows,
                captured_at=captured_at,
            )
        self.session.flush()

    def _snapshot_board(
        self,
        *,
        season_id: str,
        board_key: str,
        rows: list[LeaderboardPlayerRating],
        captured_at: datetime,
    ) -> None:
        for rank_position, row in enumerate(rows, start=1):
            self.session.add(
                LeaderboardSeasonSnapshot(
                    season_id=season_id,
                    board_key=board_key,
                    player_id=row.player_id,
                    display_name=row.display_name,
                    region=row.region,
                    division=row.division,
                    rank_position=rank_position,
                    score=float(row.rating),
                    rating=row.rating,
                    points=row.points,
                    matches_played=row.matches_played,
                    wins=row.wins,
                    losses=row.losses,
                    draws=row.draws,
                    captured_at=captured_at,
                    metadata_json={
                        "last_rating_delta": row.last_rating_delta,
                        "last_match_id": row.last_match_id,
                    },
                )
            )

    def _distribute_rewards(
        self,
        *,
        season: LeaderboardSeason,
        rows: list[LeaderboardPlayerRating],
    ) -> list[LeaderboardSeasonReward]:
        rewards: list[LeaderboardSeasonReward] = []
        tiers_by_rank = {tier.rank_position: tier for tier in DEFAULT_REWARD_TIERS}
        max_rank = max(tiers_by_rank) if tiers_by_rank else 0
        if max_rank <= 0:
            return rewards
        for rank_position, row in enumerate(rows[:max_rank], start=1):
            tier = tiers_by_rank.get(rank_position)
            if tier is None:
                continue
            reward = self.session.scalar(
                select(LeaderboardSeasonReward).where(
                    LeaderboardSeasonReward.season_id == season.id,
                    LeaderboardSeasonReward.board_key == DEFAULT_REWARD_BOARD,
                    LeaderboardSeasonReward.player_id == row.player_id,
                )
            )
            if reward is None:
                reward = LeaderboardSeasonReward(
                    season_id=season.id,
                    board_key=DEFAULT_REWARD_BOARD,
                    player_id=row.player_id,
                    display_name=row.display_name,
                    rank_position=rank_position,
                    coins=tier.coins,
                    trophies=tier.trophies,
                    badges_json=list(tier.badges),
                    status=RewardDeliveryStatus.PENDING,
                    metadata_json={"season_id": season.id},
                )
                self.session.add(reward)
                self.session.flush()
            self._deliver_reward(season=season, reward=reward, row=row)
            rewards.append(reward)
        return rewards

    def _deliver_reward(
        self,
        *,
        season: LeaderboardSeason,
        reward: LeaderboardSeasonReward,
        row: LeaderboardPlayerRating,
    ) -> None:
        user = self.session.get(User, row.player_id)
        if user is None:
            reward.status = RewardDeliveryStatus.FAILED
            reward.metadata_json = {
                **(reward.metadata_json or {}),
                "failure_reason": "user_not_found",
            }
            return

        ledger_transaction_id = None
        if reward.coins > Decimal("0.0000"):
            user_account = self.wallet_service.get_user_account(self.session, user, LedgerUnit.COIN)
            platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.COIN)
            entries = self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(
                        account=user_account,
                        amount=reward.coins,
                        source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
                        transaction_type=LedgerTransactionType.MATCH_REWARD,
                    ),
                    LedgerPosting(
                        account=platform_account,
                        amount=-reward.coins,
                        source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
                        transaction_type=LedgerTransactionType.MATCH_REWARD,
                    ),
                ],
                reason=LedgerEntryReason.COMPETITION_REWARD,
                source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
                transaction_type=LedgerTransactionType.MATCH_REWARD,
                reference=f"leaderboard-season:{season.id}:{reward.player_id}",
                description=f"Leaderboard season reward for rank #{reward.rank_position}",
                idempotency_key=f"leaderboard-season:{season.id}:{reward.board_key}:{reward.player_id}",
                metadata={
                    "reward_source": "leaderboard_season",
                    "season_id": season.id,
                    "rank_position": reward.rank_position,
                    "board_key": reward.board_key,
                },
            )
            if entries:
                ledger_transaction_id = entries[0].transaction_id

        profile = self._ensure_user_profile(user.id)
        badges = list(profile.badge_inventory_json or [])
        for badge in reward.badges_json or []:
            if badge not in badges:
                badges.append(str(badge))
        profile.badge_inventory_json = badges
        metadata = dict(profile.metadata_json or {})
        metadata["season_trophies_total"] = int(metadata.get("season_trophies_total", 0) or 0) + int(reward.trophies)
        metadata["last_leaderboard_reward"] = {
            "season_id": season.id,
            "rank_position": reward.rank_position,
            "board_key": reward.board_key,
            "coins": str(reward.coins),
            "trophies": reward.trophies,
            "badges": list(reward.badges_json or []),
        }
        profile.metadata_json = metadata

        reward.ledger_transaction_id = ledger_transaction_id
        reward.distributed_at = self._now()
        reward.status = RewardDeliveryStatus.DISTRIBUTED
        reward.metadata_json = {
            **(reward.metadata_json or {}),
            "region": row.region,
            "division": row.division,
            "rating": row.rating,
            "points": row.points,
        }

    def _ordered_rows(self, season_id: str) -> list[LeaderboardPlayerRating]:
        return list(
            self.session.scalars(
                select(LeaderboardPlayerRating)
                .where(LeaderboardPlayerRating.season_id == season_id)
                .order_by(
                    LeaderboardPlayerRating.rating.desc(),
                    LeaderboardPlayerRating.points.desc(),
                    LeaderboardPlayerRating.player_id.asc(),
                )
            ).all()
        )

    def _season_for_update(self, *, season_id: str | None) -> LeaderboardSeason:
        if season_id is not None:
            season = self.session.get(LeaderboardSeason, season_id)
        else:
            season = self.session.scalar(
                select(LeaderboardSeason)
                .where(LeaderboardSeason.status == SeasonStatus.ACTIVE)
                .order_by(LeaderboardSeason.start_date.desc())
            )
        if season is None:
            raise SeasonNotFoundError("No leaderboard season was found.")
        return season

    @staticmethod
    def _resolve_reset_strategy(value: ResetStrategy | str) -> ResetStrategy:
        if isinstance(value, ResetStrategy):
            return value
        return ResetStrategy(str(value).strip().lower())

    @staticmethod
    def _reset_rating(
        *,
        old_rating: int,
        default_rating: int,
        strategy: ResetStrategy,
        soft_reset_factor: float,
    ) -> int:
        if strategy == ResetStrategy.HARD:
            return int(default_rating)
        return int(round(default_rating + ((int(old_rating) - int(default_rating)) * float(soft_reset_factor))))

    def _ensure_user_profile(self, user_id: str) -> UserProfile:
        profile = self.session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
        if profile is not None:
            return profile
        profile = UserProfile(user_id=user_id)
        self.session.add(profile)
        self.session.flush()
        return profile

    def _defer_event(self, event: DomainEvent) -> None:
        defer_event_publish_until_commit(self.session, publisher=self.event_publisher, event=event)

    def _defer_redis_rebuild(self, season_id: str) -> None:
        if self.session_factory is None:
            return
        redis_url = self.redis_url
        session_factory = self.session_factory

        def _callback() -> None:
            with session_factory() as managed_session:
                LeaderboardService(session=managed_session, redis_url=redis_url).rebuild_for_season(season_id)

        defer_session_callback_until_commit(self.session, callback=_callback)

    def _defer_redis_clear(self) -> None:
        if self.session_factory is None:
            return
        redis_url = self.redis_url
        session_factory = self.session_factory

        def _callback() -> None:
            with session_factory() as managed_session:
                LeaderboardService(session=managed_session, redis_url=redis_url).rebuild_for_season("__empty__")

        defer_session_callback_until_commit(self.session, callback=_callback)

    @staticmethod
    def _normalize_timestamp(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


__all__ = [
    "DEFAULT_REWARD_TIERS",
    "SeasonError",
    "SeasonLifecycleResult",
    "SeasonNotFoundError",
    "SeasonRewardTier",
    "SeasonService",
]
