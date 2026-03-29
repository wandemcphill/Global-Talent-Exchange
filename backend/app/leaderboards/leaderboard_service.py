from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import logging
from typing import Iterable

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.leaderboards.models import LeaderboardPlayerRating
from app.leaderboards.season_config import rank_tier_for_rating
from app.leaderboards.schemas import LeaderboardEntryView, LeaderboardView, PlayerRanksView

logger = logging.getLogger(__name__)

GLOBAL_LEADERBOARD_KEY = "leaderboard:global"
REGION_LEADERBOARD_KEY_TEMPLATE = "leaderboard:region:{region}"
DIVISION_LEADERBOARD_KEY_TEMPLATE = "leaderboard:division:{division}"
PLAYER_METADATA_KEY = "leaderboard:player:meta"


class LeaderboardError(ValueError):
    pass


class LeaderboardNotFoundError(LeaderboardError):
    pass


@dataclass(slots=True)
class LeaderboardService:
    session: Session
    redis_url: str | None = None
    _redis: Redis | None = field(init=False, default=None, repr=False)
    _redis_ready: bool = field(init=False, default=False, repr=False)
    _redis_attempted: bool = field(init=False, default=False, repr=False)

    def update_player_rank(
        self,
        player_id: str,
        score: float | int,
        *,
        region: str | None = None,
        division: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        redis_client = self._redis_client()
        if redis_client is None:
            return
        resolved_player_id = str(player_id or "").strip()
        if not resolved_player_id:
            raise ValueError("player_id is required")
        previous_region: str | None = None
        previous_division: str | None = None
        try:
            cached_metadata = redis_client.hget(PLAYER_METADATA_KEY, resolved_player_id)
        except RedisError:
            cached_metadata = None
        if cached_metadata:
            try:
                previous_payload = dict(json.loads(cached_metadata))
                previous_region = self._normalize_bucket(str(previous_payload.get("region") or "")) or None
                previous_division = self._normalize_bucket(str(previous_payload.get("division") or "")) or None
            except (TypeError, ValueError):
                previous_region = None
                previous_division = None
        pipeline = redis_client.pipeline(transaction=False)
        resolved_score = float(score)
        normalized_region = self._normalize_bucket(region) if region else None
        normalized_division = self._normalize_bucket(division) if division else None
        pipeline.zadd(GLOBAL_LEADERBOARD_KEY, {resolved_player_id: resolved_score})
        if previous_region and previous_region != normalized_region:
            pipeline.zrem(self._region_key(previous_region), resolved_player_id)
        if previous_division and previous_division != normalized_division:
            pipeline.zrem(self._division_key(previous_division), resolved_player_id)
        if normalized_region:
            pipeline.zadd(self._region_key(normalized_region), {resolved_player_id: resolved_score})
        if normalized_division:
            pipeline.zadd(self._division_key(normalized_division), {resolved_player_id: resolved_score})
        if metadata:
            pipeline.hset(PLAYER_METADATA_KEY, resolved_player_id, json.dumps(metadata, default=str))
        pipeline.execute()

    def sync_player(self, entry: LeaderboardPlayerRating) -> None:
        self.update_player_rank(
            entry.player_id,
            entry.rating,
            region=entry.region,
            division=entry.division,
            metadata=self._metadata_for_entry(entry),
        )

    def sync_players(self, entries: Iterable[LeaderboardPlayerRating]) -> None:
        for entry in entries:
            self.sync_player(entry)

    def get_top_players(
        self,
        limit: int,
        *,
        season_id: str,
        region: str | None = None,
        division: str | None = None,
    ) -> list[LeaderboardEntryView]:
        return self._query_top_players(
            season_id=season_id,
            limit=max(1, int(limit)),
            region=region,
            division=division,
        )

    def get_player_rank(
        self,
        player_id: str,
        *,
        season_id: str,
        region: str | None = None,
        division: str | None = None,
    ) -> int | None:
        resolved_player_id = str(player_id or "").strip()
        if not resolved_player_id:
            raise ValueError("player_id is required")
        entry = self._player_entry(season_id=season_id, player_id=resolved_player_id)
        if entry is None:
            return None
        filters = [LeaderboardPlayerRating.season_id == season_id]
        if region is not None:
            filters.append(LeaderboardPlayerRating.region == self._normalize_bucket(region))
        if division is not None:
            filters.append(LeaderboardPlayerRating.division == self._normalize_bucket(division))
        better_count = self.session.scalar(
            select(func.count())
            .select_from(LeaderboardPlayerRating)
            .where(
                *filters,
                or_(
                    LeaderboardPlayerRating.rating > entry.rating,
                    and_(
                        LeaderboardPlayerRating.rating == entry.rating,
                        LeaderboardPlayerRating.points > entry.points,
                    ),
                    and_(
                        LeaderboardPlayerRating.rating == entry.rating,
                        LeaderboardPlayerRating.points == entry.points,
                        LeaderboardPlayerRating.player_id < entry.player_id,
                    ),
                ),
            )
        )
        return int(better_count or 0) + 1

    def build_player_ranks(self, player_id: str, *, season_id: str) -> PlayerRanksView:
        entry = self._player_entry(season_id=season_id, player_id=player_id)
        if entry is None:
            raise LeaderboardNotFoundError(f"Leaderboard player {player_id} was not found.")
        season_stats = self._season_stats(entry.metadata_json or {})
        tier = rank_tier_for_rating(entry.rating)
        return PlayerRanksView(
            season_id=season_id,
            player_id=entry.player_id,
            display_name=entry.display_name,
            region=entry.region,
            division=entry.division,
            tier=tier.label,
            rating=entry.rating,
            points=entry.points,
            matches_played=entry.matches_played,
            wins=entry.wins,
            losses=entry.losses,
            draws=entry.draws,
            win_rate=self._win_rate(wins=entry.wins, matches_played=entry.matches_played),
            earnings=season_stats["earnings"],
            tournament_entries=season_stats["tournament_entries"],
            tournament_titles=season_stats["tournament_titles"],
            podium_finishes=season_stats["podium_finishes"],
            best_placement=season_stats["best_placement"],
            visibility_boost=season_stats["visibility_boost"],
            exclusive_tournament_access=season_stats["exclusive_tournament_access"],
            last_rating_delta=entry.last_rating_delta,
            global_rank=self.get_player_rank(entry.player_id, season_id=season_id),
            region_rank=(
                self.get_player_rank(entry.player_id, season_id=season_id, region=entry.region)
                if entry.region
                else None
            ),
            division_rank=(
                self.get_player_rank(entry.player_id, season_id=season_id, division=entry.division)
                if entry.division
                else None
            ),
            updated_at=entry.updated_at,
        )

    def build_board_view(
        self,
        *,
        season_id: str,
        limit: int,
        region: str | None = None,
        division: str | None = None,
    ) -> LeaderboardView:
        board = self._board_name(region=region, division=division)
        return LeaderboardView(
            season_id=season_id,
            board=board,
            limit=int(limit),
            generated_at=datetime.now(timezone.utc),
            entries=self.get_top_players(limit, season_id=season_id, region=region, division=division),
        )

    def rebuild_for_season(self, season_id: str) -> None:
        redis_client = self._redis_client()
        if redis_client is None:
            return
        rows = list(
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
        keys_to_delete = [
            GLOBAL_LEADERBOARD_KEY,
            PLAYER_METADATA_KEY,
            *list(redis_client.scan_iter(match=REGION_LEADERBOARD_KEY_TEMPLATE.format(region="*"))),
            *list(redis_client.scan_iter(match=DIVISION_LEADERBOARD_KEY_TEMPLATE.format(division="*"))),
        ]
        if keys_to_delete:
            redis_client.delete(*keys_to_delete)
        if not rows:
            return
        pipeline = redis_client.pipeline(transaction=False)
        for row in rows:
            pipeline.zadd(GLOBAL_LEADERBOARD_KEY, {row.player_id: float(row.rating)})
            if row.region:
                pipeline.zadd(self._region_key(row.region), {row.player_id: float(row.rating)})
            if row.division:
                pipeline.zadd(self._division_key(row.division), {row.player_id: float(row.rating)})
            pipeline.hset(PLAYER_METADATA_KEY, row.player_id, json.dumps(self._metadata_for_entry(row), default=str))
        pipeline.execute()

    def _query_top_players(
        self,
        *,
        season_id: str,
        limit: int,
        region: str | None,
        division: str | None,
    ) -> list[LeaderboardEntryView]:
        stmt = (
            select(LeaderboardPlayerRating)
            .where(*self._board_filters(season_id=season_id, region=region, division=division))
            .order_by(
                LeaderboardPlayerRating.rating.desc(),
                LeaderboardPlayerRating.points.desc(),
                LeaderboardPlayerRating.player_id.asc(),
            )
            .limit(limit)
        )
        board = self._board_name(region=region, division=division)
        return [
            self._entry_view_from_row(row=row, board=board, rank=index, score=float(row.rating))
            for index, row in enumerate(self.session.scalars(stmt).all(), start=1)
        ]

    def _player_entry(self, *, season_id: str, player_id: str) -> LeaderboardPlayerRating | None:
        return self.session.scalar(
            select(LeaderboardPlayerRating).where(
                LeaderboardPlayerRating.season_id == season_id,
                LeaderboardPlayerRating.player_id == str(player_id or "").strip(),
            )
        )

    def _metadata_for_ids(self, *, player_ids: list[str], season_id: str) -> dict[str, dict[str, object]]:
        metadata_map: dict[str, dict[str, object]] = {}
        redis_client = self._redis_client()
        if redis_client is not None and player_ids:
            try:
                cached_values = redis_client.hmget(PLAYER_METADATA_KEY, player_ids)
            except RedisError:
                cached_values = []
            for player_id, cached_value in zip(player_ids, cached_values, strict=False):
                if cached_value is None:
                    continue
                try:
                    metadata_map[player_id] = dict(json.loads(cached_value))
                except (TypeError, ValueError):
                    continue
        missing_ids = [player_id for player_id in player_ids if player_id not in metadata_map]
        if missing_ids:
            rows = list(
                self.session.scalars(
                    select(LeaderboardPlayerRating).where(
                        LeaderboardPlayerRating.season_id == season_id,
                        LeaderboardPlayerRating.player_id.in_(tuple(missing_ids)),
                    )
                ).all()
            )
            for row in rows:
                metadata_map[row.player_id] = self._metadata_for_entry(row)
        return metadata_map

    @staticmethod
    def _metadata_for_entry(entry: LeaderboardPlayerRating) -> dict[str, object]:
        season_stats = LeaderboardService._season_stats(entry.metadata_json or {})
        tier = rank_tier_for_rating(entry.rating)
        return {
            "player_id": entry.player_id,
            "display_name": entry.display_name,
            "region": entry.region,
            "division": entry.division,
            "tier": tier.label,
            "rating": entry.rating,
            "points": entry.points,
            "matches_played": entry.matches_played,
            "wins": entry.wins,
            "losses": entry.losses,
            "draws": entry.draws,
            "win_rate": LeaderboardService._win_rate(wins=entry.wins, matches_played=entry.matches_played),
            "earnings": str(season_stats["earnings"]),
            "tournament_entries": season_stats["tournament_entries"],
            "tournament_titles": season_stats["tournament_titles"],
            "podium_finishes": season_stats["podium_finishes"],
            "best_placement": season_stats["best_placement"],
            "visibility_boost": season_stats["visibility_boost"],
            "exclusive_tournament_access": season_stats["exclusive_tournament_access"],
            "last_rating_delta": entry.last_rating_delta,
            "last_active_at": entry.last_active_at.isoformat() if entry.last_active_at else None,
        }

    @staticmethod
    def _entry_view_from_row(
        *,
        row: LeaderboardPlayerRating,
        board: str,
        rank: int,
        score: float,
    ) -> LeaderboardEntryView:
        season_stats = LeaderboardService._season_stats(row.metadata_json or {})
        tier = rank_tier_for_rating(row.rating)
        return LeaderboardEntryView(
            board=board,
            player_id=row.player_id,
            display_name=row.display_name,
            region=row.region,
            division=row.division,
            tier=tier.label,
            rating=row.rating,
            points=row.points,
            matches_played=row.matches_played,
            wins=row.wins,
            losses=row.losses,
            draws=row.draws,
            win_rate=LeaderboardService._win_rate(wins=row.wins, matches_played=row.matches_played),
            earnings=season_stats["earnings"],
            tournament_entries=season_stats["tournament_entries"],
            tournament_titles=season_stats["tournament_titles"],
            podium_finishes=season_stats["podium_finishes"],
            best_placement=season_stats["best_placement"],
            visibility_boost=season_stats["visibility_boost"],
            exclusive_tournament_access=season_stats["exclusive_tournament_access"],
            rank=rank,
            score=score,
            last_rating_delta=row.last_rating_delta,
            last_active_at=row.last_active_at,
        )

    @staticmethod
    def _entry_view_from_payload(
        *,
        payload: dict[str, object],
        board: str,
        rank: int,
        score: float,
    ) -> LeaderboardEntryView:
        last_active_at = payload.get("last_active_at")
        resolved_last_active_at = None
        if isinstance(last_active_at, str) and last_active_at.strip():
            resolved_last_active_at = datetime.fromisoformat(last_active_at.replace("Z", "+00:00"))
        wins = int(payload.get("wins") or 0)
        matches_played = int(payload.get("matches_played") or 0)
        return LeaderboardEntryView(
            board=board,
            player_id=str(payload.get("player_id") or ""),
            display_name=str(payload.get("display_name") or payload.get("player_id") or ""),
            region=(str(payload.get("region")).strip() or None) if payload.get("region") is not None else None,
            division=(str(payload.get("division")).strip() or None) if payload.get("division") is not None else None,
            tier=str(payload.get("tier") or rank_tier_for_rating(int(payload.get("rating") or 0)).label),
            rating=int(payload.get("rating") or 0),
            points=int(payload.get("points") or 0),
            matches_played=matches_played,
            wins=wins,
            losses=int(payload.get("losses") or 0),
            draws=int(payload.get("draws") or 0),
            win_rate=float(payload.get("win_rate") or LeaderboardService._win_rate(wins=wins, matches_played=matches_played)),
            earnings=LeaderboardService._decimal_value(payload.get("earnings")),
            tournament_entries=int(payload.get("tournament_entries") or 0),
            tournament_titles=int(payload.get("tournament_titles") or 0),
            podium_finishes=int(payload.get("podium_finishes") or 0),
            best_placement=int(payload["best_placement"]) if payload.get("best_placement") is not None else None,
            visibility_boost=int(payload.get("visibility_boost") or 0),
            exclusive_tournament_access=[str(item) for item in (payload.get("exclusive_tournament_access") or [])],
            rank=rank,
            score=score,
            last_rating_delta=int(payload.get("last_rating_delta") or 0),
            last_active_at=resolved_last_active_at,
        )

    @staticmethod
    def _season_stats(metadata_json: dict[str, object] | None) -> dict[str, object]:
        payload = dict(metadata_json or {})
        season_competition = payload.get("season_competition")
        reward_entitlements = payload.get("reward_entitlements")
        season_competition = season_competition if isinstance(season_competition, dict) else {}
        reward_entitlements = reward_entitlements if isinstance(reward_entitlements, dict) else {}
        return {
            "earnings": LeaderboardService._decimal_value(season_competition.get("earnings_total")),
            "tournament_entries": int(season_competition.get("tournament_entries", 0) or 0),
            "tournament_titles": int(season_competition.get("tournament_titles", 0) or 0),
            "podium_finishes": int(season_competition.get("podium_finishes", 0) or 0),
            "best_placement": (
                int(season_competition["best_placement"])
                if season_competition.get("best_placement") is not None
                else None
            ),
            "visibility_boost": int(reward_entitlements.get("visibility_boost_total", 0) or 0),
            "exclusive_tournament_access": [
                str(item) for item in (reward_entitlements.get("exclusive_tournament_access") or [])
            ],
        }

    @staticmethod
    def _win_rate(*, wins: int, matches_played: int) -> float:
        if int(matches_played or 0) <= 0:
            return 0.0
        return round(float(int(wins or 0) / int(matches_played)), 4)

    @staticmethod
    def _decimal_value(value: object) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return Decimal("0.0000")

    @staticmethod
    def _board_name(*, region: str | None, division: str | None) -> str:
        if region is not None:
            return f"region:{LeaderboardService._normalize_bucket(region)}"
        if division is not None:
            return f"division:{LeaderboardService._normalize_bucket(division)}"
        return "global"

    @staticmethod
    def _board_key(*, region: str | None, division: str | None) -> str:
        if region is not None:
            return LeaderboardService._region_key(region)
        if division is not None:
            return LeaderboardService._division_key(division)
        return GLOBAL_LEADERBOARD_KEY

    @staticmethod
    def _board_filters(*, season_id: str, region: str | None, division: str | None) -> list[object]:
        filters: list[object] = [LeaderboardPlayerRating.season_id == season_id]
        if region is not None:
            filters.append(LeaderboardPlayerRating.region == LeaderboardService._normalize_bucket(region))
        if division is not None:
            filters.append(LeaderboardPlayerRating.division == LeaderboardService._normalize_bucket(division))
        return filters

    @staticmethod
    def _normalize_bucket(value: str) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def _region_key(region: str) -> str:
        return REGION_LEADERBOARD_KEY_TEMPLATE.format(region=LeaderboardService._normalize_bucket(region))

    @staticmethod
    def _division_key(division: str) -> str:
        return DIVISION_LEADERBOARD_KEY_TEMPLATE.format(division=LeaderboardService._normalize_bucket(division))

    def _redis_client(self) -> Redis | None:
        if self._redis_attempted:
            return self._redis if self._redis_ready else None
        self._redis_attempted = True
        if not self.redis_url:
            return None
        try:
            self._redis = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                health_check_interval=30,
            )
            self._redis.ping()
            self._redis_ready = True
            return self._redis
        except Exception:
            logger.warning("leaderboard.redis.unavailable")
            self._redis = None
            self._redis_ready = False
            return None

    def _should_bypass_redis(self) -> bool:
        return bool(self.session.info.get("leaderboard.redis_needs_rebuild"))


__all__ = [
    "DIVISION_LEADERBOARD_KEY_TEMPLATE",
    "GLOBAL_LEADERBOARD_KEY",
    "LeaderboardError",
    "LeaderboardNotFoundError",
    "LeaderboardService",
    "PLAYER_METADATA_KEY",
    "REGION_LEADERBOARD_KEY_TEMPLATE",
]
