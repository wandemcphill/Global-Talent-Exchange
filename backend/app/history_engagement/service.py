from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.models.broadcast_rights import ViewSession
from app.models.club_profile import ClubProfile
from app.models.club_social import RivalryProfile
from app.models.club_trophy import ClubTrophy
from app.models.competition_match import CompetitionMatch
from app.models.history_engagement import (
    Achievement,
    DailyTask,
    FollowTargetType,
    HistoricalLeaderboardEntry,
    HistoricalRecord,
    HistoricalRecordType,
    MilestoneProgress,
    ObjectiveFrequency,
    SeasonPassMission,
    SeasonPassReward,
    SeasonPassSeason,
    SocialActivity,
    UserAchievement,
    UserFollow,
    UserObjectiveProgress,
    UserProfile,
    UserSeasonMissionProgress,
    UserSeasonProgress,
    UserSeasonRewardClaim,
    UserStreak,
    WeeklyTask,
)
from app.models.media_engine import MatchRevenueSnapshot
from app.models.notification_record import NotificationRecord
from app.models.national_team import NationalTeamCompetition, NationalTeamEntry
from app.models.regen import (
    RegenAward,
    RegenDiscoveryBadge,
    RegenGenerationEvent,
    RegenLegacyRecord,
    RegenProfile,
)
from app.models.story_feed import StoryFeedItem
from app.models.transfer_market import MarketWatchlistEntry, TransferNegotiation
from app.models.user import User
from app.predictions.models import Prediction


DEFAULT_ACHIEVEMENTS: tuple[dict[str, Any], ...] = (
    {
        "achievement_key": "win-10-matches",
        "name": "Tenacious Gaffer",
        "description": "Win 10 matches as a manager.",
        "category": "performance",
        "condition": {"metric_key": "match_wins_total", "threshold": 10},
        "reward": {"coins": 100, "badges": ["tenacious-gaffer"]},
    },
    {
        "achievement_key": "develop-regen-90",
        "name": "Wonderkid Whisperer",
        "description": "Develop a regen to 90+ current ability.",
        "category": "progression",
        "condition": {"metric_key": "regen_90_plus_total", "threshold": 1},
        "reward": {"coins": 180, "badges": ["wonderkid-whisperer"], "profile_boost": 15},
    },
    {
        "achievement_key": "discover-generational-talent",
        "name": "Talent Oracle",
        "description": "Discover a generational talent in your pipeline.",
        "category": "rare",
        "condition": {"metric_key": "generational_talent_total", "threshold": 1},
        "reward": {"coins": 250, "badges": ["talent-oracle"], "cosmetics": ["gold-scout-banner"]},
    },
    {
        "achievement_key": "gain-25-followers",
        "name": "Crowd Favorite",
        "description": "Gain 25 followers across your manager profile.",
        "category": "social",
        "condition": {"metric_key": "followers_total", "threshold": 25},
        "reward": {"coins": 75, "badges": ["crowd-favorite"], "profile_boost": 25},
    },
)

DEFAULT_DAILY_TASKS: tuple[dict[str, Any], ...] = (
    {
        "task_key": "win-one-match",
        "description": "Win 1 match.",
        "reward": {"coins": 40},
        "condition": {"metric_key": "daily_match_wins", "threshold": 1},
        "sort_order": 10,
    },
    {
        "task_key": "scout-a-player",
        "description": "Scout a player.",
        "reward": {"coins": 30},
        "condition": {"metric_key": "daily_players_scouted", "threshold": 1},
        "sort_order": 20,
    },
    {
        "task_key": "place-a-prediction",
        "description": "Place a prediction.",
        "reward": {"coins": 25},
        "condition": {"metric_key": "daily_predictions_placed", "threshold": 1},
        "sort_order": 30,
    },
)

DEFAULT_WEEKLY_TASKS: tuple[dict[str, Any], ...] = (
    {
        "task_key": "reach-finals",
        "description": "Reach finals.",
        "reward": {"coins": 120, "badges": ["final-stage-specialist"]},
        "condition": {"metric_key": "weekly_finals_reached", "threshold": 1},
        "sort_order": 10,
    },
    {
        "task_key": "complete-transfers",
        "description": "Complete transfers.",
        "reward": {"coins": 140},
        "condition": {"metric_key": "weekly_transfers_completed", "threshold": 2},
        "sort_order": 20,
    },
    {
        "task_key": "develop-youth-player",
        "description": "Develop youth player.",
        "reward": {"coins": 160, "profile_boost": 10},
        "condition": {"metric_key": "weekly_youth_development", "threshold": 1},
        "sort_order": 30,
    },
)

DEFAULT_MILESTONES: tuple[dict[str, Any], ...] = (
    {
        "milestone_key": "matches-managed-100",
        "name": "Century On The Touchline",
        "description": "Manage 100 matches.",
        "metric_key": "matches_managed_total",
        "target_value": 100,
    },
    {
        "milestone_key": "transfers-completed-50",
        "name": "Market Veteran",
        "description": "Complete 50 transfers.",
        "metric_key": "transfers_completed_total",
        "target_value": 50,
    },
    {
        "milestone_key": "trophies-won-10",
        "name": "Cabinet Builder",
        "description": "Win 10 trophies.",
        "metric_key": "trophies_won_total",
        "target_value": 10,
    },
)

DEFAULT_SEASON_PASS: dict[str, Any] = {
    "season_id": "S1",
    "title": "Season 1: Opening Exchange",
    "duration_days": 30,
    "levels": 50,
    "xp_rules_json": {
        "play_match": 10,
        "win_match": 25,
        "trade": 5,
        "watch_match": 2,
    },
    "premium_enabled": False,
    "metadata_json": {"journey_style": "battle_pass"},
}

DEFAULT_SEASON_REWARDS: tuple[dict[str, Any], ...] = (
    {
        "level": 5,
        "title": "5 GTex",
        "description": "A quick GTex drop for staying in the loop.",
        "reward_payload_json": {"gtex": 5},
        "sort_order": 10,
    },
    {
        "level": 10,
        "title": "Player Pack",
        "description": "Unlock a fresh player pack for the market grind.",
        "reward_payload_json": {"player_pack": 1},
        "sort_order": 20,
    },
    {
        "level": 20,
        "title": "20 GTex",
        "description": "A deeper GTex payout for sustained season play.",
        "reward_payload_json": {"gtex": 20},
        "sort_order": 30,
    },
    {
        "level": 50,
        "title": "Rare Player",
        "description": "Claim a rare player reward at the end of the pass.",
        "reward_payload_json": {"rare_player": 1},
        "sort_order": 40,
    },
)

DEFAULT_SEASON_MISSIONS: tuple[dict[str, Any], ...] = (
    {
        "mission_key": "play-two-matches",
        "frequency": "daily",
        "description": "Play 2 matches.",
        "condition": {"metric_key": "daily_matches_played", "threshold": 2},
        "reward_payload_json": {"season_xp": 20},
        "sort_order": 10,
    },
    {
        "mission_key": "win-one-match",
        "frequency": "daily",
        "description": "Win 1 match.",
        "condition": {"metric_key": "daily_match_wins", "threshold": 1},
        "reward_payload_json": {"season_xp": 25},
        "sort_order": 20,
    },
    {
        "mission_key": "buy-one-player",
        "frequency": "daily",
        "description": "Buy 1 player.",
        "condition": {"metric_key": "daily_players_bought", "threshold": 1},
        "reward_payload_json": {"season_xp": 15},
        "sort_order": 30,
    },
)

SEASON_XP_PER_LEVEL = 100
COMPLETED_MATCH_STATUSES = {"completed", "settled", "final"}


class HistoryEngagementError(ValueError):
    pass


@dataclass(slots=True)
class HistoryEngagementService:
    session: Session

    def seed_defaults(self) -> None:
        season = self._ensure_default_season()
        existing_achievement_keys = {
            item.achievement_key: item for item in self.session.scalars(select(Achievement)).all()
        }
        for payload in DEFAULT_ACHIEVEMENTS:
            item = existing_achievement_keys.get(payload["achievement_key"])
            if item is None:
                self.session.add(Achievement(**payload))
                continue
            item.name = payload["name"]
            item.description = payload["description"]
            item.category = payload["category"]
            item.condition = dict(payload["condition"])
            item.reward = dict(payload["reward"])
            item.active = True

        existing_daily_keys = {item.task_key: item for item in self.session.scalars(select(DailyTask)).all()}
        for payload in DEFAULT_DAILY_TASKS:
            item = existing_daily_keys.get(payload["task_key"])
            if item is None:
                self.session.add(DailyTask(**payload))
                continue
            item.description = payload["description"]
            item.reward = dict(payload["reward"])
            item.condition = dict(payload["condition"])
            item.sort_order = int(payload["sort_order"])
            item.active = True

        existing_weekly_keys = {item.task_key: item for item in self.session.scalars(select(WeeklyTask)).all()}
        for payload in DEFAULT_WEEKLY_TASKS:
            item = existing_weekly_keys.get(payload["task_key"])
            if item is None:
                self.session.add(WeeklyTask(**payload))
                continue
            item.description = payload["description"]
            item.reward = dict(payload["reward"])
            item.condition = dict(payload["condition"])
            item.sort_order = int(payload["sort_order"])
            item.active = True

        existing_reward_keys = {
            (item.level, bool(item.premium_only)): item
            for item in self.session.scalars(
                select(SeasonPassReward).where(SeasonPassReward.season_id == season.id)
            ).all()
        }
        for payload in DEFAULT_SEASON_REWARDS:
            reward = existing_reward_keys.get((int(payload["level"]), bool(payload.get("premium_only", False))))
            if reward is None:
                self.session.add(SeasonPassReward(season_id=season.id, **payload))
                continue
            reward.title = payload["title"]
            reward.description = payload["description"]
            reward.reward_payload_json = dict(payload["reward_payload_json"])
            reward.sort_order = int(payload["sort_order"])
            reward.active = True
            reward.premium_only = bool(payload.get("premium_only", False))

        existing_mission_keys = {
            (item.mission_key, item.frequency): item
            for item in self.session.scalars(
                select(SeasonPassMission).where(SeasonPassMission.season_id == season.id)
            ).all()
        }
        for payload in DEFAULT_SEASON_MISSIONS:
            mission = existing_mission_keys.get((payload["mission_key"], payload["frequency"]))
            if mission is None:
                self.session.add(SeasonPassMission(season_id=season.id, **payload))
                continue
            mission.description = payload["description"]
            mission.frequency = payload["frequency"]
            mission.condition = dict(payload["condition"])
            mission.reward_payload_json = dict(payload["reward_payload_json"])
            mission.sort_order = int(payload["sort_order"])
            mission.active = True
        self.session.flush()

    def rebuild_history(self) -> dict[str, int]:
        clubs = {item.id: item for item in self.session.scalars(select(ClubProfile)).all()}
        users = {item.id: item for item in self.session.scalars(select(User)).all()}
        players = {item.id: item for item in self.session.scalars(select(Player)).all()}
        completed_matches = self._completed_matches()
        trophies = list(self.session.scalars(select(ClubTrophy).order_by(ClubTrophy.awarded_at.asc())).all())
        completed_transfers = list(
            self.session.scalars(
                select(TransferNegotiation)
                .where(TransferNegotiation.status == "completed")
                .order_by(TransferNegotiation.resolved_at.asc(), TransferNegotiation.updated_at.asc())
            ).all()
        )
        regen_awards = list(
            self.session.scalars(select(RegenAward).order_by(RegenAward.awarded_at.asc(), RegenAward.created_at.asc())).all()
        )
        completed_federation_competitions = list(
            self.session.scalars(
                select(NationalTeamCompetition)
                .where(NationalTeamCompetition.status == "completed")
                .order_by(NationalTeamCompetition.completed_at.asc(), NationalTeamCompetition.created_at.asc())
            ).all()
        )

        self.session.execute(delete(HistoricalRecord))
        self.session.execute(delete(HistoricalLeaderboardEntry))

        records: list[HistoricalRecord] = []
        for match in completed_matches:
            home_name = clubs.get(match.home_club_id).club_name if clubs.get(match.home_club_id) else "Home club"
            away_name = clubs.get(match.away_club_id).club_name if clubs.get(match.away_club_id) else "Away club"
            records.append(
                HistoricalRecord(
                    type=HistoricalRecordType.MATCH,
                    subject_type="match",
                    subject_id=match.id,
                    headline=f"{home_name} {match.home_score}-{match.away_score} {away_name}",
                    narrative=self._match_narrative(match=match, home_name=home_name, away_name=away_name),
                    data={
                        "match_id": match.id,
                        "competition_id": match.competition_id,
                        "home_club_id": match.home_club_id,
                        "away_club_id": match.away_club_id,
                        "winner_club_id": match.winner_club_id,
                        "scoreline": f"{match.home_score}-{match.away_score}",
                    },
                    timestamp=match.completed_at or match.updated_at,
                )
            )

        regen_profiles = {item.id: item for item in self.session.scalars(select(RegenProfile)).all()}
        for trophy in trophies:
            club = clubs.get(trophy.club_id)
            if club is None:
                continue
            records.append(
                HistoricalRecord(
                    type=HistoricalRecordType.CLUB,
                    subject_type="club",
                    subject_id=club.id,
                    headline=f"{club.club_name} won {trophy.trophy_name}",
                    narrative=f"{club.club_name} added {trophy.trophy_name} to the cabinet in {trophy.season_label}.",
                    data={
                        "club_id": club.id,
                        "trophy_name": trophy.trophy_name,
                        "season_label": trophy.season_label,
                        "competition_source": trophy.competition_source,
                        "prestige_weight": trophy.prestige_weight,
                    },
                    timestamp=trophy.awarded_at,
                )
            )

        for transfer in completed_transfers:
            player = players.get(transfer.player_id)
            selling_club = clubs.get(transfer.selling_club_id)
            buying_club = clubs.get(transfer.bidder_club_id)
            if player is None or selling_club is None or buying_club is None:
                continue
            records.append(
                HistoricalRecord(
                    type=HistoricalRecordType.PLAYER,
                    subject_type="player",
                    subject_id=player.id,
                    headline=f"{player.full_name} completed a move to {buying_club.club_name}",
                    narrative=f"{selling_club.club_name} sanctioned the move as {buying_club.club_name} won the race.",
                    data={
                        "player_id": player.id,
                        "selling_club_id": selling_club.id,
                        "buying_club_id": buying_club.id,
                        "negotiation_id": transfer.id,
                        "status": transfer.status,
                    },
                    timestamp=transfer.resolved_at or transfer.updated_at,
                )
            )

        for award in regen_awards:
            regen_profile = regen_profiles.get(award.regen_id)
            player = players.get(regen_profile.player_id) if regen_profile is not None else None
            if player is None:
                continue
            records.append(
                HistoricalRecord(
                    type=HistoricalRecordType.PLAYER,
                    subject_type="player",
                    subject_id=player.id,
                    headline=f"{player.full_name} won {award.award_name}",
                    narrative=f"A peak season saw {player.full_name} land {award.award_name}.",
                    data={
                        "player_id": player.id,
                        "regen_id": award.regen_id,
                        "award_code": award.award_code,
                        "award_name": award.award_name,
                        "season_label": award.season_label,
                        "impact_score": award.impact_score,
                    },
                    timestamp=award.awarded_at,
                )
            )

        for competition in completed_federation_competitions:
            records.append(
                HistoricalRecord(
                    type=HistoricalRecordType.COMPETITION,
                    subject_type="competition",
                    subject_id=competition.id,
                    headline=f"{competition.title} concluded",
                    narrative=f"{competition.title} completed its {competition.season_label} federation campaign.",
                    data={
                        "competition_id": competition.id,
                        "key": competition.key,
                        "season_label": competition.season_label,
                        "region_type": competition.region_type,
                    },
                    timestamp=competition.completed_at or competition.updated_at,
                )
            )

        records.extend(self._build_tracked_records(clubs=clubs, players=players, completed_matches=completed_matches))
        self.session.add_all(records)

        leaderboard_entries = self._build_leaderboard_entries(
            users=users,
            clubs=clubs,
            players=players,
            completed_matches=completed_matches,
        )
        self.session.add_all(leaderboard_entries)
        self.session.flush()
        return {"history_records": len(records), "leaderboard_entries": len(leaderboard_entries)}

    def list_records(
        self,
        *,
        limit: int = 50,
        record_type: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
    ) -> list[HistoricalRecord]:
        if not self.session.scalar(select(HistoricalRecord.id).limit(1)):
            self.rebuild_history()
        stmt = select(HistoricalRecord)
        if record_type:
            stmt = stmt.where(HistoricalRecord.type == record_type)
        if subject_type:
            stmt = stmt.where(HistoricalRecord.subject_type == subject_type)
        if subject_id:
            stmt = stmt.where(HistoricalRecord.subject_id == subject_id)
        stmt = stmt.order_by(HistoricalRecord.timestamp.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def history_leaderboards(self, *, limit: int = 20) -> dict[str, Any]:
        if not self.session.scalar(select(HistoricalLeaderboardEntry.id).limit(1)):
            self.rebuild_history()
        return {
            "generated_at": self._latest_generated_at(),
            "top_players_ever": self._leaderboard("top_players_ever", limit=limit),
            "top_clubs_ever": self._leaderboard("top_clubs_ever", limit=limit),
            "top_managers": self._leaderboard("top_managers_ever", limit=limit),
            "tracked_records": self.list_records(limit=10),
        }

    def goat_rankings(self, *, entity_type: str, limit: int = 20) -> dict[str, Any]:
        board_map = {"player": "goat_players", "club": "goat_clubs", "manager": "goat_managers"}
        board_key = board_map.get(entity_type.strip().lower())
        if board_key is None:
            raise HistoryEngagementError("Unsupported GOAT entity type.")
        if not self.session.scalar(select(HistoricalLeaderboardEntry.id).limit(1)):
            self.rebuild_history()
        return {
            "entity_type": entity_type,
            "generated_at": self._latest_generated_at(),
            "entries": self._leaderboard(board_key, limit=limit),
        }

    def timeline(self, *, subject_type: str, subject_id: str, limit: int = 50) -> dict[str, Any]:
        if not self.session.scalar(select(HistoricalRecord.id).limit(1)):
            self.rebuild_history()
        normalized = subject_type.strip().lower()
        if normalized == "player":
            return self._player_timeline(player_id=subject_id, limit=limit)
        if normalized == "club":
            return self._club_timeline(club_id=subject_id, limit=limit)
        raise HistoryEngagementError("Timeline is currently supported for player and club subjects.")

    def list_achievements(self) -> list[Achievement]:
        self.seed_defaults()
        return list(
            self.session.scalars(select(Achievement).where(Achievement.active.is_(True)).order_by(Achievement.name.asc())).all()
        )

    def achievements_for_user(self, *, actor: User) -> list[UserAchievement]:
        return list(
            self.session.scalars(
                select(UserAchievement)
                .where(UserAchievement.user_id == actor.id)
                .order_by(UserAchievement.unlocked_at.desc())
            ).all()
        )

    def milestones_for_user(self, *, actor: User) -> list[MilestoneProgress]:
        self.reconcile_user(actor=actor)
        return list(
            self.session.scalars(
                select(MilestoneProgress)
                .where(MilestoneProgress.user_id == actor.id)
                .order_by(MilestoneProgress.target_value.asc(), MilestoneProgress.name.asc())
            ).all()
        )

    def profile_for_user(self, *, actor: User) -> UserProfile:
        sync = self.reconcile_user(actor=actor)
        return sync["profile"]

    def follow(self, *, actor: User, target_type: str, target_id: str) -> UserFollow:
        normalized_type = target_type.strip().lower()
        if normalized_type == FollowTargetType.MANAGER.value:
            if target_id == actor.id:
                raise HistoryEngagementError("You cannot follow yourself.")
            target_user = self.session.get(User, target_id)
            if target_user is None:
                raise HistoryEngagementError("Manager was not found.")
            target_key = f"manager:{target_id}"
            payload = {
                "follower_user_id": actor.id,
                "target_key": target_key,
                "target_type": FollowTargetType.MANAGER,
                "target_user_id": target_id,
            }
            notification_user_id = target_user.id
            headline = f"{self._display_name(actor)} followed manager {self._display_name(target_user)}."
        elif normalized_type == FollowTargetType.CLUB.value:
            club = self.session.get(ClubProfile, target_id)
            if club is None:
                raise HistoryEngagementError("Club was not found.")
            target_key = f"club:{target_id}"
            payload = {
                "follower_user_id": actor.id,
                "target_key": target_key,
                "target_type": FollowTargetType.CLUB,
                "target_club_id": target_id,
            }
            notification_user_id = club.owner_user_id
            headline = f"{self._display_name(actor)} followed club {club.club_name}."
        else:
            raise HistoryEngagementError("Unsupported follow target type.")

        existing = self.session.scalar(select(UserFollow).where(UserFollow.follower_user_id == actor.id, UserFollow.target_key == target_key))
        if existing is not None:
            return existing
        item = UserFollow(**payload)
        self.session.add(item)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise HistoryEngagementError("Follow relationship already exists.") from exc
        self._sync_profile_counters(actor.id)
        if item.target_user_id is not None:
            self._sync_profile_counters(item.target_user_id)
        self._notify(
            user_id=notification_user_id,
            topic="social",
            template_key="NEW_FOLLOWER",
            message=f"{self._display_name(actor)} started following you."[:255],
            resource_type="follow",
            resource_id=item.id,
            metadata_json={"follow_id": item.id, "target_type": normalized_type},
        )
        self._record_activity(
            actor_user_id=actor.id,
            activity_type="follow",
            target_user_id=item.target_user_id,
            target_club_id=item.target_club_id,
            headline=headline,
            body=None,
            metadata_json={"follow_id": item.id, "target_type": normalized_type},
        )
        self.session.flush()
        return item

    def unfollow(self, *, actor: User, target_type: str, target_id: str) -> None:
        target_key = f"{target_type.strip().lower()}:{target_id}"
        item = self.session.scalar(select(UserFollow).where(UserFollow.follower_user_id == actor.id, UserFollow.target_key == target_key))
        if item is None:
            raise HistoryEngagementError("Follow relationship was not found.")
        target_user_id = item.target_user_id
        self.session.delete(item)
        self.session.flush()
        self._sync_profile_counters(actor.id)
        if target_user_id is not None:
            self._sync_profile_counters(target_user_id)

    def list_feed(self, *, actor: User, limit: int = 40) -> list[dict[str, Any] | SocialActivity]:
        followed = list(
            self.session.scalars(select(UserFollow).where(UserFollow.follower_user_id == actor.id)).all()
        )
        followed_user_ids = {item.target_user_id for item in followed if item.target_user_id}
        followed_club_ids = {item.target_club_id for item in followed if item.target_club_id}
        social_items = list(
            self.session.scalars(select(SocialActivity).order_by(SocialActivity.created_at.desc()).limit(limit * 2)).all()
        )
        filtered_social = [
            item
            for item in social_items
            if not followed
            or item.actor_user_id == actor.id
            or (item.target_user_id and item.target_user_id in followed_user_ids)
            or (item.target_club_id and item.target_club_id in followed_club_ids)
        ]
        dynamic_items = self._dynamic_feed_items(
            followed_user_ids=followed_user_ids,
            followed_club_ids=followed_club_ids,
            limit=limit * 2,
        )
        combined: list[dict[str, Any] | SocialActivity] = [*filtered_social, *dynamic_items]
        combined.sort(key=self._activity_timestamp, reverse=True)
        return combined[:limit]

    def club_community(self, *, club_id: str, limit: int = 20) -> dict[str, Any]:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise HistoryEngagementError("Club was not found.")
        follower_count = int(
            self.session.scalar(select(func.count(UserFollow.id)).where(UserFollow.target_club_id == club_id)) or 0
        )
        fan_chat = list(
            self.session.scalars(
                select(SocialActivity)
                .where(SocialActivity.target_club_id == club_id, SocialActivity.activity_type == "fan_chat")
                .order_by(SocialActivity.created_at.desc())
                .limit(limit)
            ).all()
        )
        return {
            "club_id": club_id,
            "follower_count": follower_count,
            "fan_chat": fan_chat,
            "activity_wall": self._club_activity_wall(club_id=club_id, limit=limit),
        }

    def post_club_message(self, *, actor: User, club_id: str, body: str) -> SocialActivity:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise HistoryEngagementError("Club was not found.")
        message = self._record_activity(
            actor_user_id=actor.id,
            activity_type="fan_chat",
            target_club_id=club_id,
            headline=f"{self._display_name(actor)} posted in {club.club_name} fan chat.",
            body=body.strip(),
            metadata_json={"club_id": club_id},
        )
        self._increment_reputation(actor.id, delta=1)
        self.session.flush()
        return message

    def rivalry_page(self, *, club_a_id: str, club_b_id: str, limit: int = 20) -> dict[str, Any]:
        profile = self._find_rivalry_profile(club_a_id=club_a_id, club_b_id=club_b_id)
        if profile is None:
            raise HistoryEngagementError("Rivalry profile was not found.")
        rivalry_key = self._rivalry_key(profile.club_a_id, profile.club_b_id)
        banter = list(
            self.session.scalars(
                select(SocialActivity)
                .where(SocialActivity.rivalry_key == rivalry_key, SocialActivity.activity_type == "banter")
                .order_by(SocialActivity.created_at.desc())
                .limit(limit)
            ).all()
        )
        return {
            "rivalry_key": rivalry_key,
            "club_a_id": profile.club_a_id,
            "club_b_id": profile.club_b_id,
            "label": profile.label,
            "intensity_score": profile.intensity_score,
            "streak_length": profile.streak_length,
            "streak_holder_club_id": profile.streak_holder_club_id,
            "notable_moments": list(profile.notable_moments_json or []),
            "banter": banter,
        }

    def post_banter(self, *, actor: User, club_a_id: str, club_b_id: str, body: str) -> SocialActivity:
        profile = self._find_rivalry_profile(club_a_id=club_a_id, club_b_id=club_b_id)
        if profile is None:
            raise HistoryEngagementError("Rivalry profile was not found.")
        rivalry_key = self._rivalry_key(profile.club_a_id, profile.club_b_id)
        club_a = self.session.get(ClubProfile, profile.club_a_id)
        club_b = self.session.get(ClubProfile, profile.club_b_id)
        message = self._record_activity(
            actor_user_id=actor.id,
            activity_type="banter",
            rivalry_key=rivalry_key,
            headline=f"{self._display_name(actor)} added rivalry banter to {club_a.club_name if club_a else 'club'} vs {club_b.club_name if club_b else 'club'}.",
            body=body.strip(),
            metadata_json={"club_a_id": profile.club_a_id, "club_b_id": profile.club_b_id},
        )
        self._increment_reputation(actor.id, delta=2)
        self.session.flush()
        return message

    def objectives_for_user(self, *, actor: User) -> dict[str, Any]:
        sync = self.reconcile_user(actor=actor)
        return {
            "streak": sync["streak"],
            "daily_tasks": sync["daily_tasks"],
            "weekly_tasks": sync["weekly_tasks"],
        }

    def season_pass_for_user(self, *, actor: User) -> dict[str, Any]:
        sync = self.reconcile_user(actor=actor)
        return dict(sync["season_pass"])

    def claim_season_reward(self, *, actor: User, reward_id: str) -> UserSeasonRewardClaim:
        self.seed_defaults()
        reward = self.session.get(SeasonPassReward, reward_id)
        if reward is None or not reward.active:
            raise HistoryEngagementError("Season reward was not found.")
        season = self.session.get(SeasonPassSeason, reward.season_id)
        if season is None or not season.active:
            raise HistoryEngagementError("Season reward was not found.")
        season_payload = self.season_pass_for_user(actor=actor)
        reward_view = next((item for item in season_payload["rewards"] if item["id"] == reward_id), None)
        if reward_view is None:
            raise HistoryEngagementError("Season reward was not found.")
        if reward_view["premium_only"] and not season_payload["has_premium"]:
            raise HistoryEngagementError("Premium season pass is required for this reward.")
        if not reward_view["unlocked"]:
            raise HistoryEngagementError("Reward is not unlocked yet.")
        if reward_view["claimed"]:
            raise HistoryEngagementError("Reward has already been claimed.")

        claim = UserSeasonRewardClaim(
            user_id=actor.id,
            season_id=season.id,
            reward_id=reward.id,
            granted_payload_json=dict(reward.reward_payload_json or {}),
            metadata_json={
                "season_id": season.season_id,
                "level": reward.level,
                "premium_only": bool(reward.premium_only),
            },
        )
        self.session.add(claim)
        self._notify(
            user_id=actor.id,
            topic="season_pass",
            template_key="SEASON_REWARD_CLAIMED",
            message=f"Claimed season reward: {reward.title}"[:255],
            resource_type="season_reward",
            resource_id=reward.id,
            metadata_json={"season_id": season.season_id, "level": reward.level},
        )
        self._record_activity(
            actor_user_id=actor.id,
            activity_type="season_reward",
            target_user_id=actor.id,
            headline=f"{self._display_name(actor)} claimed {reward.title}.",
            body=reward.description,
            metadata_json={"season_id": season.season_id, "level": reward.level},
        )
        self.session.flush()
        return claim

    def reconcile_user(self, *, actor: User) -> dict[str, Any]:
        self.seed_defaults()
        profile = self._ensure_profile(actor.id)
        streak = self._ensure_streak(actor.id)
        today = datetime.now(UTC).date()
        now = datetime.now(UTC)
        self._reset_streak_if_expired(streak=streak, today=today, now=now)
        metrics = self._collect_metrics(user_id=actor.id, today=today)
        unlocked_achievements = self._sync_achievements(actor=actor, profile=profile, metrics=metrics, now=now)
        self._sync_milestones(actor=actor, metrics=metrics, now=now)

        daily_tasks = list(
            self.session.scalars(select(DailyTask).where(DailyTask.active.is_(True)).order_by(DailyTask.sort_order.asc())).all()
        )
        weekly_tasks = list(
            self.session.scalars(select(WeeklyTask).where(WeeklyTask.active.is_(True)).order_by(WeeklyTask.sort_order.asc())).all()
        )
        synced_daily, new_daily = self._sync_objectives(
            actor=actor,
            tasks=daily_tasks,
            frequency=ObjectiveFrequency.DAILY,
            period_key=today.isoformat(),
            metrics=metrics,
            now=now,
        )
        synced_weekly, _ = self._sync_objectives(
            actor=actor,
            tasks=weekly_tasks,
            frequency=ObjectiveFrequency.WEEKLY,
            period_key=self._week_key(today),
            metrics=metrics,
            now=now,
        )
        if new_daily and streak.last_completed_on != today:
            self._advance_streak(streak=streak, today=today)
        self._refresh_streak_multipliers(streak)
        for item in [*synced_daily, *synced_weekly]:
            item.reward_multiplier = float(streak.reward_multiplier)
            if item.completed and item.reward_granted_at is None:
                self._grant_progress_reward(progress=item, profile=profile)
        self._sync_profile_counters(actor.id)
        community_posts = int(
            self.session.scalar(select(func.count(SocialActivity.id)).where(SocialActivity.actor_user_id == actor.id)) or 0
        )
        unlocked_count = int(
            self.session.scalar(select(func.count(UserAchievement.id)).where(UserAchievement.user_id == actor.id)) or 0
        )
        profile.reputation_score = (
            int(metrics["match_wins_total"]) * 2
            + int(metrics["trophies_won_total"]) * 10
            + int(metrics["followers_total"])
            + unlocked_count * 25
            + community_posts * 3
            + int(profile.profile_boost_total)
        )
        season_pass = self._sync_season_pass(actor=actor, profile=profile, streak=streak, today=today, now=now)
        self.session.flush()
        return {
            "profile": profile,
            "streak": streak,
            "unlocked_achievements": unlocked_achievements,
            "daily_tasks": synced_daily,
            "weekly_tasks": synced_weekly,
            "season_pass": season_pass,
        }

    def run_workers_once(self) -> dict[str, int]:
        self.seed_defaults()
        history_summary = self.rebuild_history()
        notifications_created = 0
        reconciled_users = 0
        users = list(self.session.scalars(select(User).where(User.is_active.is_(True))).all())
        for user in users:
            self.reconcile_user(actor=user)
            notifications_created += self._ensure_daily_task_notification(user_id=user.id)
            notifications_created += self._ensure_streak_warning(user_id=user.id)
            reconciled_users += 1
        self.session.flush()
        return {
            "history_records": history_summary["history_records"],
            "leaderboard_entries": history_summary["leaderboard_entries"],
            "reconciled_users": reconciled_users,
            "notifications_created": notifications_created,
        }

    def _completed_matches(self) -> list[CompetitionMatch]:
        stmt = (
            select(CompetitionMatch)
            .where(
                CompetitionMatch.completed_at.is_not(None)
                | CompetitionMatch.status.in_(tuple(COMPLETED_MATCH_STATUSES))
            )
            .order_by(CompetitionMatch.completed_at.asc(), CompetitionMatch.updated_at.asc())
        )
        return list(self.session.scalars(stmt).all())

    def _build_tracked_records(
        self,
        *,
        clubs: dict[str, ClubProfile],
        players: dict[str, Player],
        completed_matches: list[CompetitionMatch],
    ) -> list[HistoricalRecord]:
        records: list[HistoricalRecord] = []
        now = datetime.now(UTC)
        highest_scoring = max(
            completed_matches,
            key=lambda item: (item.home_score + item.away_score, item.completed_at or item.updated_at),
            default=None,
        )
        if highest_scoring is not None:
            home_name = clubs.get(highest_scoring.home_club_id).club_name if clubs.get(highest_scoring.home_club_id) else "Home club"
            away_name = clubs.get(highest_scoring.away_club_id).club_name if clubs.get(highest_scoring.away_club_id) else "Away club"
            records.append(
                HistoricalRecord(
                    type=HistoricalRecordType.MATCH,
                    subject_type="match",
                    subject_id=highest_scoring.id,
                    headline="Highest scoring match",
                    narrative=f"{home_name} and {away_name} combined for {highest_scoring.home_score + highest_scoring.away_score} goals.",
                    data={
                        "record_key": "highest_scoring_match",
                        "match_id": highest_scoring.id,
                        "goals_total": highest_scoring.home_score + highest_scoring.away_score,
                        "scoreline": f"{highest_scoring.home_score}-{highest_scoring.away_score}",
                    },
                    timestamp=highest_scoring.completed_at or highest_scoring.updated_at,
                )
            )

        longest_streak = self._compute_club_win_streaks(completed_matches=completed_matches)
        if longest_streak:
            club_id, streak_length = max(longest_streak.items(), key=lambda item: item[1])
            club = clubs.get(club_id)
            if club is not None:
                records.append(
                    HistoricalRecord(
                        type=HistoricalRecordType.CLUB,
                        subject_type="club",
                        subject_id=club.id,
                        headline="Longest win streak",
                        narrative=f"{club.club_name} put together a {streak_length}-match winning run.",
                        data={"record_key": "longest_win_streak", "club_id": club.id, "streak_length": streak_length},
                        timestamp=now,
                    )
                )

        trophy_counts = self._club_trophy_counts()
        if trophy_counts:
            club_id, trophy_count = max(trophy_counts.items(), key=lambda item: item[1])
            club = clubs.get(club_id)
            if club is not None:
                records.append(
                    HistoricalRecord(
                        type=HistoricalRecordType.CLUB,
                        subject_type="club",
                        subject_id=club.id,
                        headline="Most trophies",
                        narrative=f"{club.club_name} lead the historical cabinet count with {trophy_count} trophies.",
                        data={"record_key": "most_trophies", "club_id": club.id, "trophy_count": trophy_count},
                        timestamp=now,
                    )
                )

        best_player_seasons = self._best_player_season_rows()
        if best_player_seasons:
            best = best_player_seasons[0]
            player = players.get(best["player_id"])
            if player is not None:
                record_payload = {**best, "timestamp": best["timestamp"].isoformat()}
                records.append(
                    HistoricalRecord(
                        type=HistoricalRecordType.SEASON,
                        subject_type="player",
                        subject_id=player.id,
                        headline="Best player season",
                        narrative=f"{player.full_name} delivered a standout {best['season_label']} campaign.",
                        data=record_payload,
                        timestamp=best["timestamp"],
                    )
                )
        return records

    def _build_leaderboard_entries(
        self,
        *,
        users: dict[str, User],
        clubs: dict[str, ClubProfile],
        players: dict[str, Player],
        completed_matches: list[CompetitionMatch],
    ) -> list[HistoricalLeaderboardEntry]:
        generated_at = datetime.now(UTC)
        club_rows = self._club_leaderboard_rows(clubs=clubs, completed_matches=completed_matches)
        manager_rows = self._manager_leaderboard_rows(users=users, clubs=clubs, club_rows=club_rows, completed_matches=completed_matches)
        player_rows = self._player_leaderboard_rows(players=players)
        entries: list[HistoricalLeaderboardEntry] = []
        for rank, row in enumerate(player_rows, start=1):
            entries.append(
                HistoricalLeaderboardEntry(
                    board_key="top_players_ever",
                    entity_type="player",
                    entity_id=row["entity_id"],
                    entity_name=row["entity_name"],
                    rank=rank,
                    score=row["score"],
                    score_breakdown_json=row["breakdown"],
                    generated_at=generated_at,
                    metadata_json={"leaderboard": "top_players_ever"},
                )
            )
            entries.append(
                HistoricalLeaderboardEntry(
                    board_key="goat_players",
                    entity_type="player",
                    entity_id=row["entity_id"],
                    entity_name=row["entity_name"],
                    rank=rank,
                    score=row["goat_score"],
                    score_breakdown_json=row["goat_breakdown"],
                    generated_at=generated_at,
                    metadata_json={"leaderboard": "goat_players"},
                )
            )
        for rank, row in enumerate(club_rows, start=1):
            entries.append(
                HistoricalLeaderboardEntry(
                    board_key="top_clubs_ever",
                    entity_type="club",
                    entity_id=row["entity_id"],
                    entity_name=row["entity_name"],
                    rank=rank,
                    score=row["score"],
                    score_breakdown_json=row["breakdown"],
                    generated_at=generated_at,
                    metadata_json={"leaderboard": "top_clubs_ever"},
                )
            )
            entries.append(
                HistoricalLeaderboardEntry(
                    board_key="goat_clubs",
                    entity_type="club",
                    entity_id=row["entity_id"],
                    entity_name=row["entity_name"],
                    rank=rank,
                    score=row["goat_score"],
                    score_breakdown_json=row["goat_breakdown"],
                    generated_at=generated_at,
                    metadata_json={"leaderboard": "goat_clubs"},
                )
            )
        for rank, row in enumerate(manager_rows, start=1):
            entries.append(
                HistoricalLeaderboardEntry(
                    board_key="top_managers_ever",
                    entity_type="manager",
                    entity_id=row["entity_id"],
                    entity_name=row["entity_name"],
                    rank=rank,
                    score=row["score"],
                    score_breakdown_json=row["breakdown"],
                    generated_at=generated_at,
                    metadata_json={"leaderboard": "top_managers_ever"},
                )
            )
            entries.append(
                HistoricalLeaderboardEntry(
                    board_key="goat_managers",
                    entity_type="manager",
                    entity_id=row["entity_id"],
                    entity_name=row["entity_name"],
                    rank=rank,
                    score=row["goat_score"],
                    score_breakdown_json=row["goat_breakdown"],
                    generated_at=generated_at,
                    metadata_json={"leaderboard": "goat_managers"},
                )
            )
        return entries

    def _club_leaderboard_rows(self, *, clubs: dict[str, ClubProfile], completed_matches: list[CompetitionMatch]) -> list[dict[str, Any]]:
        trophy_counts = self._club_trophy_counts()
        trophy_weights = self._club_trophy_weights()
        win_counts = self._club_win_counts(completed_matches=completed_matches)
        streak_counts = self._compute_club_win_streaks(completed_matches=completed_matches)
        media_rows = self._club_media_rows()
        rows: list[dict[str, Any]] = []
        for club_id, club in clubs.items():
            trophies = float(trophy_counts.get(club_id, 0))
            longevity = float(max(trophy_counts.get(club_id, 0), 0) + max(win_counts.get(club_id, 0), 0) / 10.0)
            peak_performance = float(streak_counts.get(club_id, 0) * 2 + win_counts.get(club_id, 0) / 4.0)
            legacy_score = float(media_rows.get(club_id, {}).get("legacy_score", 0.0) + trophy_weights.get(club_id, 0) / 25.0)
            rows.append(
                {
                    "entity_id": club.id,
                    "entity_name": club.club_name,
                    "score": round(trophy_weights.get(club_id, 0) + win_counts.get(club_id, 0) + legacy_score * 5, 2),
                    "goat_score": round(trophies + longevity + peak_performance + legacy_score, 2),
                    "breakdown": {
                        "trophies": trophy_counts.get(club_id, 0),
                        "trophy_weight": trophy_weights.get(club_id, 0),
                        "wins": win_counts.get(club_id, 0),
                        "media_impact": media_rows.get(club_id, {}),
                    },
                    "goat_breakdown": {
                        "trophies": trophies,
                        "longevity": longevity,
                        "peak_performance": peak_performance,
                        "legacy_score": legacy_score,
                    },
                }
            )
        rows.sort(key=lambda item: (item["score"], item["goat_score"], item["entity_name"]), reverse=True)
        return rows[:50]

    def _manager_leaderboard_rows(
        self,
        *,
        users: dict[str, User],
        clubs: dict[str, ClubProfile],
        club_rows: list[dict[str, Any]],
        completed_matches: list[CompetitionMatch],
    ) -> list[dict[str, Any]]:
        club_rows_by_id = {item["entity_id"]: item for item in club_rows}
        user_club_ids: dict[str, list[str]] = {}
        for club in clubs.values():
            user_club_ids.setdefault(club.owner_user_id, []).append(club.id)
        win_counts = self._club_win_counts(completed_matches=completed_matches)
        streak_counts = self._compute_club_win_streaks(completed_matches=completed_matches)
        federation_rows = self._manager_federation_rows()
        rows: list[dict[str, Any]] = []
        for user_id, user in users.items():
            club_ids = user_club_ids.get(user_id, [])
            club_trophies = sum(int(club_rows_by_id.get(club_id, {}).get("breakdown", {}).get("trophies", 0)) for club_id in club_ids)
            match_wins = sum(win_counts.get(club_id, 0) for club_id in club_ids)
            peak_performance = max([streak_counts.get(club_id, 0) for club_id in club_ids] or [0]) * 2.0
            profile = self._ensure_profile(user_id)
            longevity = len(club_ids) + federation_rows.get(user_id, {}).get("campaigns", 0)
            legacy_score = float(profile.followers + profile.reputation_score / 25.0 + federation_rows.get(user_id, {}).get("titles", 0) * 10)
            rows.append(
                {
                    "entity_id": user.id,
                    "entity_name": self._display_name(user),
                    "score": round(club_trophies * 10 + match_wins + legacy_score * 2, 2),
                    "goat_score": round(float(club_trophies) + float(longevity) + float(peak_performance) + legacy_score, 2),
                    "breakdown": {
                        "trophies": club_trophies,
                        "match_wins": match_wins,
                        "followers": profile.followers,
                        "federation": federation_rows.get(user_id, {}),
                    },
                    "goat_breakdown": {
                        "trophies": float(club_trophies),
                        "longevity": float(longevity),
                        "peak_performance": float(peak_performance),
                        "legacy_score": legacy_score,
                    },
                }
            )
        rows.sort(key=lambda item: (item["score"], item["goat_score"], item["entity_name"]), reverse=True)
        return rows[:50]

    def _player_leaderboard_rows(self, *, players: dict[str, Player]) -> list[dict[str, Any]]:
        legacy_by_player = {item.player_id: item for item in self.session.scalars(select(RegenLegacyRecord)).all()}
        regen_profiles = list(self.session.scalars(select(RegenProfile)).all())
        regen_by_player = {item.player_id: item for item in regen_profiles}
        regen_by_id = {item.id: item for item in regen_profiles}
        award_counts: dict[str, int] = {}
        award_peaks: dict[str, float] = {}
        for award in self.session.scalars(select(RegenAward)).all():
            regen_profile = regen_by_id.get(award.regen_id)
            if regen_profile is None:
                continue
            award_counts[regen_profile.player_id] = award_counts.get(regen_profile.player_id, 0) + 1
            award_peaks[regen_profile.player_id] = max(award_peaks.get(regen_profile.player_id, 0.0), float(award.impact_score or 0.0))
        rows: list[dict[str, Any]] = []
        for player_id, player in players.items():
            legacy = legacy_by_player.get(player_id)
            regen = regen_by_player.get(player_id)
            trophies = float((legacy.awards_total if legacy is not None else 0) + award_counts.get(player_id, 0))
            longevity = float((legacy.seasons_total if legacy is not None else 0) + award_counts.get(player_id, 0) / 2.0)
            peak_performance = float(max((regen.current_gsi if regen is not None else 0) / 10.0, award_peaks.get(player_id, 0.0) * 10.0))
            legacy_score = float(legacy.legacy_score if legacy is not None else 0.0)
            rows.append(
                {
                    "entity_id": player.id,
                    "entity_name": player.full_name,
                    "score": round(trophies + longevity + peak_performance + legacy_score + float((legacy.goals_total if legacy is not None else 0) / 10.0), 2),
                    "goat_score": round(trophies + longevity + peak_performance + legacy_score, 2),
                    "breakdown": {
                        "awards_total": legacy.awards_total if legacy is not None else 0,
                        "seasons_total": legacy.seasons_total if legacy is not None else 0,
                        "current_gsi": regen.current_gsi if regen is not None else 0,
                        "legacy_score": legacy_score,
                    },
                    "goat_breakdown": {
                        "trophies": trophies,
                        "longevity": longevity,
                        "peak_performance": peak_performance,
                        "legacy_score": legacy_score,
                    },
                }
            )
        rows.sort(key=lambda item: (item["goat_score"], item["score"], item["entity_name"]), reverse=True)
        return rows[:50]

    def _player_timeline(self, *, player_id: str, limit: int) -> dict[str, Any]:
        player = self.session.get(Player, player_id)
        if player is None:
            raise HistoryEngagementError("Player was not found.")
        regen_profile = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player_id))
        timeline: list[dict[str, Any]] = []
        if regen_profile is not None:
            for event in self.session.scalars(
                select(RegenGenerationEvent)
                .where(RegenGenerationEvent.regen_profile_id == regen_profile.id)
                .order_by(RegenGenerationEvent.created_at.asc())
            ).all():
                timeline.append(
                    {
                        "timestamp": event.created_at,
                        "headline": f"{player.full_name} entered the world",
                        "narrative": f"Generated for season {event.season_label}.",
                        "event_type": "generation",
                        "data": {
                            "club_id": event.club_id,
                            "season_label": event.season_label,
                            "generation_source": event.generation_source,
                        },
                    }
                )
            for award in self.session.scalars(
                select(RegenAward).where(RegenAward.regen_id == regen_profile.id).order_by(RegenAward.awarded_at.asc())
            ).all():
                timeline.append(
                    {
                        "timestamp": award.awarded_at,
                        "headline": f"{player.full_name} won {award.award_name}",
                        "narrative": f"Season {award.season_label or 'unknown'} pushed the player into the conversation.",
                        "event_type": "award",
                        "data": {
                            "award_name": award.award_name,
                            "season_label": award.season_label,
                            "impact_score": award.impact_score,
                        },
                    }
                )
            for badge in self.session.scalars(
                select(RegenDiscoveryBadge).where(RegenDiscoveryBadge.regen_id == regen_profile.id).order_by(RegenDiscoveryBadge.awarded_at.asc())
            ).all():
                timeline.append(
                    {
                        "timestamp": badge.awarded_at,
                        "headline": f"{player.full_name} earned {badge.badge_name}",
                        "narrative": f"The discovery signal around {player.full_name} started to spike.",
                        "event_type": "discovery_badge",
                        "data": {
                            "badge_code": badge.badge_code,
                            "badge_name": badge.badge_name,
                            "club_id": badge.club_id,
                        },
                    }
                )
        legacy = self.session.scalar(select(RegenLegacyRecord).where(RegenLegacyRecord.player_id == player_id))
        if legacy is not None and legacy.retired_on is not None:
            timeline.append(
                {
                    "timestamp": datetime.combine(legacy.retired_on, datetime.min.time(), tzinfo=UTC),
                    "headline": f"{player.full_name} closed the career chapter",
                    "narrative": legacy.narrative_summary or f"Legacy tier: {legacy.legacy_tier}.",
                    "event_type": "retirement",
                    "data": {
                        "legacy_tier": legacy.legacy_tier,
                        "legacy_score": legacy.legacy_score,
                        "appearances_total": legacy.appearances_total,
                    },
                }
            )
        timeline.sort(key=lambda item: item["timestamp"], reverse=True)
        historical_ranking = next(iter(self._leaderboard_lookup(entity_type="player", entity_id=player_id)), None)
        return {
            "subject_type": "player",
            "subject_id": player_id,
            "narrative": self._player_narrative(player=player, ranking=historical_ranking, legacy=legacy),
            "historical_ranking": historical_ranking,
            "major_milestones": timeline[: min(5, len(timeline))],
            "career_timeline": timeline[:limit],
        }

    def _club_timeline(self, *, club_id: str, limit: int) -> dict[str, Any]:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise HistoryEngagementError("Club was not found.")
        timeline: list[dict[str, Any]] = []
        for trophy in self.session.scalars(
            select(ClubTrophy).where(ClubTrophy.club_id == club_id).order_by(ClubTrophy.awarded_at.asc())
        ).all():
            timeline.append(
                {
                    "timestamp": trophy.awarded_at,
                    "headline": f"{club.club_name} won {trophy.trophy_name}",
                    "narrative": f"The club lifted {trophy.trophy_name} in {trophy.season_label}.",
                    "event_type": "trophy",
                    "data": {
                        "trophy_name": trophy.trophy_name,
                        "season_label": trophy.season_label,
                        "prestige_weight": trophy.prestige_weight,
                    },
                }
            )
        other_clubs = {item.id: item for item in self.session.scalars(select(ClubProfile)).all()}
        completed_matches = [item for item in self._completed_matches() if item.home_club_id == club_id or item.away_club_id == club_id]
        for match in completed_matches:
            opponent_id = match.away_club_id if match.home_club_id == club_id else match.home_club_id
            opponent = other_clubs.get(opponent_id)
            timeline.append(
                {
                    "timestamp": match.completed_at or match.updated_at,
                    "headline": f"{club.club_name} played {opponent.club_name if opponent else 'an opponent'}",
                    "narrative": self._match_narrative(
                        match=match,
                        home_name=other_clubs.get(match.home_club_id).club_name if other_clubs.get(match.home_club_id) else "Home club",
                        away_name=other_clubs.get(match.away_club_id).club_name if other_clubs.get(match.away_club_id) else "Away club",
                    ),
                    "event_type": "match",
                    "data": {
                        "match_id": match.id,
                        "winner_club_id": match.winner_club_id,
                        "competition_id": match.competition_id,
                    },
                }
            )
        players = {item.id: item for item in self.session.scalars(select(Player)).all()}
        for transfer in self.session.scalars(
            select(TransferNegotiation)
            .where(
                TransferNegotiation.status == "completed",
                (TransferNegotiation.selling_club_id == club_id) | (TransferNegotiation.bidder_club_id == club_id),
            )
            .order_by(TransferNegotiation.resolved_at.asc(), TransferNegotiation.updated_at.asc())
        ).all():
            player = players.get(transfer.player_id)
            if player is None:
                continue
            direction = "signed" if transfer.bidder_club_id == club_id else "sold"
            timeline.append(
                {
                    "timestamp": transfer.resolved_at or transfer.updated_at,
                    "headline": f"{club.club_name} {direction} {player.full_name}",
                    "narrative": f"The transfer market wrote another chapter for {club.club_name}.",
                    "event_type": "transfer",
                    "data": {"player_id": player.id, "direction": direction, "negotiation_id": transfer.id},
                }
            )
        timeline.sort(key=lambda item: item["timestamp"], reverse=True)
        historical_ranking = next(iter(self._leaderboard_lookup(entity_type="club", entity_id=club_id)), None)
        return {
            "subject_type": "club",
            "subject_id": club_id,
            "narrative": self._club_narrative(club=club, ranking=historical_ranking),
            "historical_ranking": historical_ranking,
            "major_milestones": timeline[: min(5, len(timeline))],
            "career_timeline": timeline[:limit],
        }

    def _leaderboard(self, board_key: str, *, limit: int) -> list[HistoricalLeaderboardEntry]:
        return list(
            self.session.scalars(
                select(HistoricalLeaderboardEntry)
                .where(HistoricalLeaderboardEntry.board_key == board_key)
                .order_by(HistoricalLeaderboardEntry.rank.asc())
                .limit(limit)
            ).all()
        )

    def _leaderboard_lookup(self, *, entity_type: str, entity_id: str) -> list[HistoricalLeaderboardEntry]:
        board_key = {"player": "goat_players", "club": "goat_clubs", "manager": "goat_managers"}.get(entity_type)
        if board_key is None:
            return []
        return list(
            self.session.scalars(
                select(HistoricalLeaderboardEntry)
                .where(
                    HistoricalLeaderboardEntry.board_key == board_key,
                    HistoricalLeaderboardEntry.entity_id == entity_id,
                )
                .limit(1)
            ).all()
        )

    def _latest_generated_at(self) -> datetime | None:
        return self.session.scalar(select(func.max(HistoricalLeaderboardEntry.generated_at)))

    def _club_trophy_counts(self) -> dict[str, int]:
        rows = self.session.execute(
            select(ClubTrophy.club_id, func.count(ClubTrophy.id)).group_by(ClubTrophy.club_id)
        ).all()
        return {club_id: int(total) for club_id, total in rows}

    def _club_trophy_weights(self) -> dict[str, int]:
        rows = self.session.execute(
            select(ClubTrophy.club_id, func.coalesce(func.sum(ClubTrophy.prestige_weight), 0)).group_by(ClubTrophy.club_id)
        ).all()
        return {club_id: int(total or 0) for club_id, total in rows}

    def _club_media_rows(self) -> dict[str, dict[str, float]]:
        aggregates: dict[str, dict[str, float]] = {}
        for row in self.session.scalars(select(MatchRevenueSnapshot)).all():
            for club_id in filter(None, [row.home_club_id, row.away_club_id]):
                payload = aggregates.setdefault(club_id, {"views": 0.0, "premium_purchases": 0.0, "legacy_score": 0.0})
                payload["views"] += float(row.total_views or 0)
                payload["premium_purchases"] += float(row.premium_purchases or 0)
                payload["legacy_score"] += float(row.total_views or 0) / 100.0 + float(row.premium_purchases or 0)
        return aggregates

    def _club_win_counts(self, *, completed_matches: list[CompetitionMatch]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for match in completed_matches:
            if match.winner_club_id:
                counts[match.winner_club_id] = counts.get(match.winner_club_id, 0) + 1
        return counts

    def _compute_club_win_streaks(self, *, completed_matches: list[CompetitionMatch]) -> dict[str, int]:
        streaks: dict[str, int] = {}
        active: dict[str, int] = {}
        ordered = sorted(completed_matches, key=lambda item: (item.completed_at or item.updated_at, item.id))
        for match in ordered:
            home_id = match.home_club_id
            away_id = match.away_club_id
            if match.winner_club_id == home_id:
                active[home_id] = active.get(home_id, 0) + 1
                active[away_id] = 0
            elif match.winner_club_id == away_id:
                active[away_id] = active.get(away_id, 0) + 1
                active[home_id] = 0
            else:
                active[home_id] = 0
                active[away_id] = 0
            streaks[home_id] = max(streaks.get(home_id, 0), active.get(home_id, 0))
            streaks[away_id] = max(streaks.get(away_id, 0), active.get(away_id, 0))
        return streaks

    def _best_player_season_rows(self) -> list[dict[str, Any]]:
        regen_profiles = {item.id: item for item in self.session.scalars(select(RegenProfile)).all()}
        rows: dict[tuple[str, str], dict[str, Any]] = {}
        for award in self.session.scalars(select(RegenAward)).all():
            season_label = award.season_label or "unknown"
            regen_profile = regen_profiles.get(award.regen_id)
            if regen_profile is None:
                continue
            key = (regen_profile.player_id, season_label)
            row = rows.setdefault(
                key,
                {
                    "record_key": "best_player_season",
                    "player_id": regen_profile.player_id,
                    "season_label": season_label,
                    "award_count": 0,
                    "impact_score_total": 0.0,
                    "timestamp": award.awarded_at,
                },
            )
            row["award_count"] += 1
            row["impact_score_total"] += float(award.impact_score or 0.0)
            row["timestamp"] = max(row["timestamp"], award.awarded_at)
        values = list(rows.values())
        values.sort(key=lambda item: (item["impact_score_total"], item["award_count"]), reverse=True)
        return values[:10]

    def _manager_federation_rows(self) -> dict[str, dict[str, int]]:
        rows: dict[str, dict[str, int]] = {}
        competitions = {item.id: item for item in self.session.scalars(select(NationalTeamCompetition)).all()}
        for entry in self.session.scalars(select(NationalTeamEntry)).all():
            if entry.manager_user_id is None:
                continue
            payload = rows.setdefault(entry.manager_user_id, {"campaigns": 0, "titles": 0})
            payload["campaigns"] += 1
            competition = competitions.get(entry.competition_id)
            if competition is None:
                continue
            winner_manager = (competition.metadata_json or {}).get("winner_manager_user_id")
            winner_entry_id = (competition.metadata_json or {}).get("winner_entry_id")
            if winner_manager == entry.manager_user_id or winner_entry_id == entry.id:
                payload["titles"] += 1
        return rows

    def _find_rivalry_profile(self, *, club_a_id: str, club_b_id: str) -> RivalryProfile | None:
        ordered_a, ordered_b = sorted([club_a_id, club_b_id])
        return self.session.scalar(
            select(RivalryProfile).where(RivalryProfile.club_a_id == ordered_a, RivalryProfile.club_b_id == ordered_b)
        )

    def _club_activity_wall(self, *, club_id: str, limit: int) -> list[dict[str, Any] | SocialActivity]:
        social_items = list(
            self.session.scalars(
                select(SocialActivity)
                .where(SocialActivity.target_club_id == club_id)
                .order_by(SocialActivity.created_at.desc())
                .limit(limit * 2)
            ).all()
        )
        dynamic_items = self._dynamic_feed_items(
            followed_user_ids=set(),
            followed_club_ids={club_id},
            limit=limit * 2,
        )
        combined: list[dict[str, Any] | SocialActivity] = [*social_items, *dynamic_items]
        combined.sort(key=self._activity_timestamp, reverse=True)
        return combined[:limit]

    def _dynamic_feed_items(
        self,
        *,
        followed_user_ids: set[str],
        followed_club_ids: set[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        clubs = {item.id: item for item in self.session.scalars(select(ClubProfile)).all()}
        players = {item.id: item for item in self.session.scalars(select(Player)).all()}
        items: list[dict[str, Any]] = []

        for transfer in self.session.scalars(
            select(TransferNegotiation)
            .where(TransferNegotiation.status == "completed")
            .order_by(TransferNegotiation.resolved_at.desc(), TransferNegotiation.updated_at.desc())
            .limit(limit)
        ).all():
            if followed_club_ids and transfer.selling_club_id not in followed_club_ids and transfer.bidder_club_id not in followed_club_ids:
                continue
            player = players.get(transfer.player_id)
            buying_club = clubs.get(transfer.bidder_club_id)
            selling_club = clubs.get(transfer.selling_club_id)
            if player is None or buying_club is None or selling_club is None:
                continue
            created_at = transfer.resolved_at or transfer.updated_at
            items.append(
                {
                    "id": f"transfer:{transfer.id}",
                    "actor_user_id": buying_club.owner_user_id,
                    "activity_type": "transfer",
                    "target_user_id": None,
                    "target_club_id": buying_club.id,
                    "rivalry_key": None,
                    "headline": f"{player.full_name} joined {buying_club.club_name}",
                    "body": f"{selling_club.club_name} completed the outgoing deal.",
                    "metadata_json": {
                        "player_id": player.id,
                        "selling_club_id": selling_club.id,
                        "buying_club_id": buying_club.id,
                    },
                    "created_at": created_at,
                    "updated_at": created_at,
                }
            )

        for match in reversed(self._completed_matches()[-limit:]):
            if not match.winner_club_id:
                continue
            if followed_club_ids and match.winner_club_id not in followed_club_ids:
                continue
            winning_club = clubs.get(match.winner_club_id)
            home_name = clubs.get(match.home_club_id).club_name if clubs.get(match.home_club_id) else "Home club"
            away_name = clubs.get(match.away_club_id).club_name if clubs.get(match.away_club_id) else "Away club"
            if winning_club is None:
                continue
            created_at = match.completed_at or match.updated_at
            items.append(
                {
                    "id": f"match:{match.id}",
                    "actor_user_id": winning_club.owner_user_id,
                    "activity_type": "match_win",
                    "target_user_id": None,
                    "target_club_id": winning_club.id,
                    "rivalry_key": None,
                    "headline": f"{winning_club.club_name} won {home_name} {match.home_score}-{match.away_score} {away_name}",
                    "body": self._match_narrative(match=match, home_name=home_name, away_name=away_name),
                    "metadata_json": {
                        "match_id": match.id,
                        "winner_club_id": winning_club.id,
                        "competition_id": match.competition_id,
                    },
                    "created_at": created_at,
                    "updated_at": created_at,
                }
            )

        for story in self.session.scalars(select(StoryFeedItem).order_by(StoryFeedItem.created_at.desc()).limit(limit)).all():
            if followed_club_ids and story.subject_type == "club" and story.subject_id not in followed_club_ids:
                continue
            if followed_user_ids and story.subject_type in {"manager", "user"} and story.subject_id not in followed_user_ids:
                continue
            items.append(
                {
                    "id": f"story:{story.id}",
                    "actor_user_id": story.published_by_user_id,
                    "activity_type": "story_event",
                    "target_user_id": story.subject_id if story.subject_type in {"manager", "user"} else None,
                    "target_club_id": story.subject_id if story.subject_type == "club" else None,
                    "rivalry_key": None,
                    "headline": story.title,
                    "body": story.body,
                    "metadata_json": {
                        "story_id": story.id,
                        "subject_type": story.subject_type,
                        "subject_id": story.subject_id,
                    },
                    "created_at": story.created_at,
                    "updated_at": story.updated_at,
                }
            )
        return items

    def _sync_achievements(
        self,
        *,
        actor: User,
        profile: UserProfile,
        metrics: dict[str, float],
        now: datetime,
    ) -> list[UserAchievement]:
        unlocked: list[UserAchievement] = []
        existing_ids = {
            item.achievement_id
            for item in self.session.scalars(select(UserAchievement).where(UserAchievement.user_id == actor.id)).all()
        }
        for achievement in self.list_achievements():
            if achievement.id in existing_ids:
                continue
            threshold = float((achievement.condition or {}).get("threshold", 0))
            metric_key = str((achievement.condition or {}).get("metric_key", ""))
            if float(metrics.get(metric_key, 0.0)) < threshold:
                continue
            unlock = UserAchievement(
                user_id=actor.id,
                achievement_id=achievement.id,
                unlocked_at=now,
                reward_payload_json=dict(achievement.reward or {}),
                metadata_json={"achievement_key": achievement.achievement_key},
            )
            self.session.add(unlock)
            self._apply_profile_reward(profile=profile, reward=dict(achievement.reward or {}))
            self._notify(
                user_id=actor.id,
                topic="engagement",
                template_key="ACHIEVEMENT_UNLOCKED",
                message=f"Achievement unlocked: {achievement.name}"[:255],
                resource_type="achievement",
                resource_id=achievement.id,
                metadata_json={"achievement_key": achievement.achievement_key},
            )
            self._record_activity(
                actor_user_id=actor.id,
                activity_type="achievement",
                target_user_id=actor.id,
                headline=f"{self._display_name(actor)} unlocked {achievement.name}.",
                body=achievement.description,
                metadata_json={"achievement_key": achievement.achievement_key},
            )
            unlocked.append(unlock)
            self._increment_reputation(actor.id, delta=10)
        self.session.flush()
        return unlocked

    def _sync_milestones(self, *, actor: User, metrics: dict[str, float], now: datetime) -> None:
        existing = {
            item.milestone_key: item
            for item in self.session.scalars(select(MilestoneProgress).where(MilestoneProgress.user_id == actor.id)).all()
        }
        for definition in DEFAULT_MILESTONES:
            item = existing.get(definition["milestone_key"])
            if item is None:
                item = MilestoneProgress(
                    user_id=actor.id,
                    milestone_key=definition["milestone_key"],
                    name=definition["name"],
                    description=definition["description"],
                    target_value=int(definition["target_value"]),
                )
                self.session.add(item)
            current_value = int(metrics.get(definition["metric_key"], 0))
            item.current_value = current_value
            item.best_value = max(int(item.best_value or 0), current_value)
            if current_value >= item.target_value and item.reached_at is None:
                item.reached_at = now
        self.session.flush()

    def _sync_season_pass(
        self,
        *,
        actor: User,
        profile: UserProfile,
        streak: UserStreak,
        today: date,
        now: datetime,
    ) -> dict[str, Any]:
        del profile, streak
        season = self._active_season(now=now)
        progress = self._ensure_user_season_progress(actor.id, season.id)
        previous_level = int(progress.current_level or 1)
        metrics = self._collect_season_metrics(user_id=actor.id, season=season, today=today)
        missions = list(
            self.session.scalars(
                select(SeasonPassMission)
                .where(
                    SeasonPassMission.season_id == season.id,
                    SeasonPassMission.active.is_(True),
                    SeasonPassMission.frequency == "daily",
                )
                .order_by(SeasonPassMission.sort_order.asc(), SeasonPassMission.mission_key.asc())
            ).all()
        )
        synced_missions = self._sync_season_missions(
            actor=actor,
            season=season,
            missions=missions,
            period_key=today.isoformat(),
            metrics=metrics,
            now=now,
        )
        activity_xp = self._season_activity_xp_total(metrics=metrics, xp_rules=dict(season.xp_rules_json or {}))
        mission_bonus_xp = self._season_bonus_xp(user_id=actor.id, season_id=season.id)
        total_xp = activity_xp + mission_bonus_xp
        current_level = self._season_level_for_xp(xp_total=total_xp, levels=season.levels)
        progress.xp_total = total_xp
        progress.current_level = current_level
        progress.last_synced_at = now
        progress.metadata_json = {
            "activity_xp": activity_xp,
            "mission_bonus_xp": mission_bonus_xp,
            "season_id": season.season_id,
        }
        if current_level > previous_level:
            self._notify(
                user_id=actor.id,
                topic="season_pass",
                template_key="SEASON_LEVEL_UP",
                message=f"Season pass reached level {current_level}."[:255],
                resource_type="season",
                resource_id=season.id,
                metadata_json={"season_id": season.season_id, "level": current_level},
            )
        claimed_reward_ids = {
            item.reward_id
            for item in self.session.scalars(
                select(UserSeasonRewardClaim).where(
                    UserSeasonRewardClaim.user_id == actor.id,
                    UserSeasonRewardClaim.season_id == season.id,
                )
            ).all()
        }
        rewards = list(
            self.session.scalars(
                select(SeasonPassReward)
                .where(SeasonPassReward.season_id == season.id, SeasonPassReward.active.is_(True))
                .order_by(SeasonPassReward.level.asc(), SeasonPassReward.sort_order.asc())
            ).all()
        )
        reward_views = [
            {
                "id": reward.id,
                "level": reward.level,
                "premium_only": bool(reward.premium_only),
                "title": reward.title,
                "description": reward.description,
                "reward_payload_json": dict(reward.reward_payload_json or {}),
                "unlocked": current_level >= reward.level,
                "claimable": current_level >= reward.level
                and reward.id not in claimed_reward_ids
                and (not reward.premium_only or progress.has_premium),
                "claimed": reward.id in claimed_reward_ids,
            }
            for reward in rewards
        ]
        xp_into_current_level, xp_for_next_level, xp_progress = self._season_progress_snapshot(
            xp_total=total_xp,
            current_level=current_level,
            levels=season.levels,
        )
        self.session.flush()
        return {
            "season_id": season.season_id,
            "title": season.title,
            "duration_days": season.duration_days,
            "levels": season.levels,
            "starts_at": season.starts_at,
            "ends_at": season.ends_at,
            "current_level": current_level,
            "current_xp": total_xp,
            "xp_per_level": SEASON_XP_PER_LEVEL,
            "xp_into_current_level": xp_into_current_level,
            "xp_for_next_level": xp_for_next_level,
            "xp_progress": xp_progress,
            "premium_enabled": bool(season.premium_enabled),
            "has_premium": bool(progress.has_premium),
            "xp_rules": {
                key: int(value)
                for key, value in dict(season.xp_rules_json or {}).items()
            },
            "daily_missions": synced_missions,
            "rewards": reward_views,
        }

    def _sync_season_missions(
        self,
        *,
        actor: User,
        season: SeasonPassSeason,
        missions: list[SeasonPassMission],
        period_key: str,
        metrics: dict[str, float],
        now: datetime,
    ) -> list[dict[str, Any]]:
        existing = {
            item.mission_id: item
            for item in self.session.scalars(
                select(UserSeasonMissionProgress).where(
                    UserSeasonMissionProgress.user_id == actor.id,
                    UserSeasonMissionProgress.season_id == season.id,
                    UserSeasonMissionProgress.period_key == period_key,
                )
            ).all()
        }
        synced: list[tuple[SeasonPassMission, UserSeasonMissionProgress]] = []
        for mission in missions:
            metric_key = str((mission.condition or {}).get("metric_key", ""))
            threshold = float((mission.condition or {}).get("threshold", 1))
            progress_value = float(metrics.get(metric_key, 0.0))
            progress = existing.get(mission.id)
            if progress is None:
                progress = UserSeasonMissionProgress(
                    user_id=actor.id,
                    season_id=season.id,
                    mission_id=mission.id,
                    period_key=period_key,
                    frequency=mission.frequency,
                    description=mission.description,
                    threshold_value=threshold,
                    progress_value=progress_value,
                    reward_payload_json=dict(mission.reward_payload_json or {}),
                    metadata_json={"metric_key": metric_key},
                )
                self.session.add(progress)
            else:
                progress.frequency = mission.frequency
                progress.description = mission.description
                progress.threshold_value = threshold
                progress.progress_value = progress_value
                progress.reward_payload_json = dict(mission.reward_payload_json or {})
                progress.metadata_json = {"metric_key": metric_key}
            if not progress.completed and progress_value >= threshold:
                progress.completed = True
                progress.completed_at = now
            if progress.completed and progress.reward_granted_at is None:
                progress.reward_granted_at = now
            synced.append((mission, progress))
        self.session.flush()
        synced.sort(key=lambda item: (item[0].sort_order, item[0].mission_key))
        return [
            {
                "id": progress.id,
                "mission_key": mission.mission_key,
                "frequency": progress.frequency,
                "period_key": progress.period_key,
                "description": progress.description,
                "threshold_value": progress.threshold_value,
                "progress_value": progress.progress_value,
                "reward_payload_json": dict(progress.reward_payload_json or {}),
                "completed": progress.completed,
                "completed_at": progress.completed_at,
                "reward_granted_at": progress.reward_granted_at,
                "metadata_json": dict(progress.metadata_json or {}),
            }
            for mission, progress in synced
        ]

    def _collect_season_metrics(
        self,
        *,
        user_id: str,
        season: SeasonPassSeason,
        today: date,
    ) -> dict[str, float]:
        club_ids = self._club_ids_for_user(user_id)
        season_start = season.starts_at.date()
        season_end = season.ends_at.date()
        next_day = today + timedelta(days=1)
        daily_start = max(today, season_start)
        daily_end = min(next_day, season_end)
        has_daily_window = daily_start < daily_end
        return {
            "season_matches_played": float(len(self._user_matches(club_ids=club_ids, start=season_start, end=season_end))),
            "season_match_wins": float(self._user_match_wins(club_ids=club_ids, start=season_start, end=season_end)),
            "season_trades": float(self._user_transfers(club_ids=club_ids, start=season_start, end=season_end)),
            "season_matches_watched": float(self._user_match_views(user_id=user_id, start=season.starts_at, end=season.ends_at)),
            "daily_matches_played": float(
                len(self._user_matches(club_ids=club_ids, start=daily_start, end=daily_end)) if has_daily_window else 0
            ),
            "daily_match_wins": float(
                self._user_match_wins(club_ids=club_ids, start=daily_start, end=daily_end) if has_daily_window else 0
            ),
            "daily_players_bought": float(
                self._user_player_buys(club_ids=club_ids, start=daily_start, end=daily_end) if has_daily_window else 0
            ),
        }

    def _season_activity_xp_total(self, *, metrics: dict[str, float], xp_rules: dict[str, Any]) -> int:
        return int(
            round(float(metrics.get("season_matches_played", 0.0)) * float(xp_rules.get("play_match", 0)))
            + round(float(metrics.get("season_match_wins", 0.0)) * float(xp_rules.get("win_match", 0)))
            + round(float(metrics.get("season_trades", 0.0)) * float(xp_rules.get("trade", 0)))
            + round(float(metrics.get("season_matches_watched", 0.0)) * float(xp_rules.get("watch_match", 0)))
        )

    def _season_bonus_xp(self, *, user_id: str, season_id: str) -> int:
        total = 0
        for progress in self.session.scalars(
            select(UserSeasonMissionProgress).where(
                UserSeasonMissionProgress.user_id == user_id,
                UserSeasonMissionProgress.season_id == season_id,
                UserSeasonMissionProgress.completed.is_(True),
            )
        ).all():
            total += int((progress.reward_payload_json or {}).get("season_xp", 0) or 0)
        return total

    def _ensure_default_season(self) -> SeasonPassSeason:
        season = self.session.scalar(
            select(SeasonPassSeason).where(SeasonPassSeason.season_id == DEFAULT_SEASON_PASS["season_id"])
        )
        if season is None:
            now = datetime.now(UTC)
            season_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
            season = SeasonPassSeason(
                season_id=DEFAULT_SEASON_PASS["season_id"],
                title=DEFAULT_SEASON_PASS["title"],
                starts_at=season_start,
                ends_at=season_start + timedelta(days=int(DEFAULT_SEASON_PASS["duration_days"])),
                duration_days=int(DEFAULT_SEASON_PASS["duration_days"]),
                levels=int(DEFAULT_SEASON_PASS["levels"]),
                xp_rules_json=dict(DEFAULT_SEASON_PASS["xp_rules_json"]),
                premium_enabled=bool(DEFAULT_SEASON_PASS["premium_enabled"]),
                metadata_json=dict(DEFAULT_SEASON_PASS["metadata_json"]),
            )
            self.session.add(season)
            self.session.flush()
            return season
        season.title = DEFAULT_SEASON_PASS["title"]
        season.duration_days = int(DEFAULT_SEASON_PASS["duration_days"])
        season.levels = int(DEFAULT_SEASON_PASS["levels"])
        season.xp_rules_json = dict(DEFAULT_SEASON_PASS["xp_rules_json"])
        season.premium_enabled = bool(DEFAULT_SEASON_PASS["premium_enabled"])
        season.active = True
        season.metadata_json = dict(DEFAULT_SEASON_PASS["metadata_json"])
        return season

    def _active_season(self, *, now: datetime) -> SeasonPassSeason:
        season = self.session.scalar(
            select(SeasonPassSeason)
            .where(
                SeasonPassSeason.active.is_(True),
                SeasonPassSeason.starts_at <= now,
                SeasonPassSeason.ends_at > now,
            )
            .order_by(SeasonPassSeason.starts_at.desc())
            .limit(1)
        )
        if season is not None:
            return season
        return self._ensure_default_season()

    def _ensure_user_season_progress(self, user_id: str, season_row_id: str) -> UserSeasonProgress:
        progress = self.session.scalar(
            select(UserSeasonProgress).where(
                UserSeasonProgress.user_id == user_id,
                UserSeasonProgress.season_id == season_row_id,
            )
        )
        if progress is not None:
            return progress
        progress = UserSeasonProgress(user_id=user_id, season_id=season_row_id)
        self.session.add(progress)
        self.session.flush()
        return progress

    @staticmethod
    def _season_level_for_xp(*, xp_total: int, levels: int) -> int:
        if levels <= 1:
            return 1
        return max(1, min(levels, int(xp_total // SEASON_XP_PER_LEVEL) + 1))

    @staticmethod
    def _season_progress_snapshot(*, xp_total: int, current_level: int, levels: int) -> tuple[int, int, float]:
        if current_level >= levels:
            return SEASON_XP_PER_LEVEL, 0, 1.0
        level_floor = max(0, (current_level - 1) * SEASON_XP_PER_LEVEL)
        xp_into_current_level = max(0, xp_total - level_floor)
        xp_for_next_level = max(0, SEASON_XP_PER_LEVEL - xp_into_current_level)
        xp_progress = min(1.0, max(0.0, xp_into_current_level / float(SEASON_XP_PER_LEVEL)))
        return xp_into_current_level, xp_for_next_level, xp_progress

    def _sync_objectives(
        self,
        *,
        actor: User,
        tasks: list[DailyTask | WeeklyTask],
        frequency: ObjectiveFrequency,
        period_key: str,
        metrics: dict[str, float],
        now: datetime,
    ) -> tuple[list[UserObjectiveProgress], bool]:
        existing = {
            item.task_key: item
            for item in self.session.scalars(
                select(UserObjectiveProgress).where(
                    UserObjectiveProgress.user_id == actor.id,
                    UserObjectiveProgress.task_frequency == frequency,
                    UserObjectiveProgress.period_key == period_key,
                )
            ).all()
        }
        synced: list[UserObjectiveProgress] = []
        any_new_completion = False
        for task in tasks:
            metric_key = str((task.condition or {}).get("metric_key", ""))
            threshold = float((task.condition or {}).get("threshold", 1))
            progress_value = float(metrics.get(metric_key, 0.0))
            progress = existing.get(task.task_key)
            if progress is None:
                progress = UserObjectiveProgress(
                    user_id=actor.id,
                    task_frequency=frequency,
                    task_key=task.task_key,
                    period_key=period_key,
                    description=task.description,
                    threshold_value=threshold,
                    progress_value=progress_value,
                    reward_payload_json=dict(task.reward or {}),
                    metadata_json={"metric_key": metric_key},
                )
                self.session.add(progress)
            else:
                progress.description = task.description
                progress.threshold_value = threshold
                progress.progress_value = progress_value
                progress.reward_payload_json = dict(task.reward or {})
                progress.metadata_json = {"metric_key": metric_key}
            if not progress.completed and progress_value >= threshold:
                progress.completed = True
                progress.completed_at = now
                any_new_completion = True
            synced.append(progress)
        self.session.flush()
        synced.sort(key=lambda item: item.task_key)
        return synced, any_new_completion

    def _grant_progress_reward(self, *, progress: UserObjectiveProgress, profile: UserProfile) -> None:
        reward = self._multiplied_reward(dict(progress.reward_payload_json or {}), multiplier=float(progress.reward_multiplier or 1.0))
        self._apply_profile_reward(profile=profile, reward=reward)
        progress.reward_payload_json = reward
        progress.reward_granted_at = datetime.now(UTC)

    def _multiplied_reward(self, reward: dict[str, Any], *, multiplier: float) -> dict[str, Any]:
        adjusted = dict(reward)
        if "coins" in adjusted:
            adjusted["coins"] = int(round(float(adjusted["coins"]) * multiplier))
        return adjusted

    def _apply_profile_reward(self, *, profile: UserProfile, reward: dict[str, Any]) -> None:
        badges = list(profile.badge_inventory_json or [])
        for badge in reward.get("badges", []) or []:
            if badge not in badges:
                badges.append(str(badge))
        profile.badge_inventory_json = badges
        cosmetics = list(profile.cosmetic_inventory_json or [])
        for cosmetic in reward.get("cosmetics", []) or []:
            if cosmetic not in cosmetics:
                cosmetics.append(str(cosmetic))
        profile.cosmetic_inventory_json = cosmetics
        profile.profile_boost_total += int(reward.get("profile_boost", 0) or 0)

    def _collect_metrics(self, *, user_id: str, today: date) -> dict[str, float]:
        club_ids = self._club_ids_for_user(user_id)
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=7)
        next_day = today + timedelta(days=1)
        return {
            "matches_managed_total": float(len(self._user_matches(club_ids=club_ids))),
            "match_wins_total": float(self._user_match_wins(club_ids=club_ids)),
            "transfers_completed_total": float(self._user_transfers(club_ids=club_ids)),
            "trophies_won_total": float(self._user_trophies(club_ids=club_ids)),
            "followers_total": float(self._follower_count(user_id=user_id)),
            "regen_90_plus_total": float(self._user_regen_90_plus(club_ids=club_ids)),
            "generational_talent_total": float(self._user_generational_talents(club_ids=club_ids)),
            "daily_match_wins": float(self._user_match_wins(club_ids=club_ids, start=today, end=next_day)),
            "daily_players_scouted": float(self._user_scouting_events(club_ids=club_ids, start=today, end=next_day)),
            "daily_predictions_placed": float(self._user_predictions(user_id=user_id, start=today, end=next_day)),
            "weekly_finals_reached": float(self._user_finals_reached(club_ids=club_ids, start=week_start, end=week_end)),
            "weekly_transfers_completed": float(self._user_transfers(club_ids=club_ids, start=week_start, end=week_end)),
            "weekly_youth_development": float(self._user_youth_development(club_ids=club_ids, start=week_start, end=week_end)),
        }

    def _club_ids_for_user(self, user_id: str) -> list[str]:
        return [
            item.id
            for item in self.session.scalars(select(ClubProfile).where(ClubProfile.owner_user_id == user_id)).all()
        ]

    def _user_matches(self, *, club_ids: list[str], start: date | None = None, end: date | None = None) -> list[CompetitionMatch]:
        if not club_ids:
            return []
        stmt = select(CompetitionMatch).where(
            (CompetitionMatch.home_club_id.in_(tuple(club_ids))) | (CompetitionMatch.away_club_id.in_(tuple(club_ids)))
        )
        if start is not None:
            stmt = stmt.where(CompetitionMatch.match_date >= start)
        if end is not None:
            stmt = stmt.where(CompetitionMatch.match_date < end)
        stmt = stmt.where((CompetitionMatch.completed_at.is_not(None)) | CompetitionMatch.status.in_(tuple(COMPLETED_MATCH_STATUSES)))
        return list(self.session.scalars(stmt).all())

    def _user_match_wins(self, *, club_ids: list[str], start: date | None = None, end: date | None = None) -> int:
        club_id_set = set(club_ids)
        return len([item for item in self._user_matches(club_ids=club_ids, start=start, end=end) if item.winner_club_id in club_id_set])

    def _user_transfers(self, *, club_ids: list[str], start: date | None = None, end: date | None = None) -> int:
        if not club_ids:
            return 0
        items = list(
            self.session.scalars(
                select(TransferNegotiation).where(
                    TransferNegotiation.status == "completed",
                    (TransferNegotiation.selling_club_id.in_(tuple(club_ids))) | (TransferNegotiation.bidder_club_id.in_(tuple(club_ids))),
                )
            ).all()
        )
        if start is None and end is None:
            return len(items)
        filtered = []
        for item in items:
            when = (item.resolved_at or item.updated_at).date()
            if start is not None and when < start:
                continue
            if end is not None and when >= end:
                continue
            filtered.append(item)
        return len(filtered)

    def _user_player_buys(self, *, club_ids: list[str], start: date | None = None, end: date | None = None) -> int:
        if not club_ids:
            return 0
        items = list(
            self.session.scalars(
                select(TransferNegotiation).where(
                    TransferNegotiation.status == "completed",
                    TransferNegotiation.bidder_club_id.in_(tuple(club_ids)),
                )
            ).all()
        )
        if start is None and end is None:
            return len(items)
        filtered = []
        for item in items:
            when = (item.resolved_at or item.updated_at).date()
            if start is not None and when < start:
                continue
            if end is not None and when >= end:
                continue
            filtered.append(item)
        return len(filtered)

    def _user_match_views(
        self,
        *,
        user_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> int:
        stmt = select(ViewSession).where(ViewSession.user_id == user_id)
        if start is not None:
            stmt = stmt.where(ViewSession.timestamp >= start)
        if end is not None:
            stmt = stmt.where(ViewSession.timestamp < end)
        return len(list(self.session.scalars(stmt).all()))

    def _user_trophies(self, *, club_ids: list[str]) -> int:
        if not club_ids:
            return 0
        return int(self.session.scalar(select(func.count(ClubTrophy.id)).where(ClubTrophy.club_id.in_(tuple(club_ids)))) or 0)

    def _follower_count(self, *, user_id: str) -> int:
        return int(
            self.session.scalar(
                select(func.count(UserFollow.id)).where(
                    UserFollow.target_user_id == user_id,
                    UserFollow.target_type == FollowTargetType.MANAGER,
                )
            )
            or 0
        )

    def _user_regen_90_plus(self, *, club_ids: list[str]) -> int:
        if not club_ids:
            return 0
        return int(
            self.session.scalar(
                select(func.count(RegenProfile.id)).where(
                    RegenProfile.generated_for_club_id.in_(tuple(club_ids)),
                    RegenProfile.current_gsi >= 90,
                )
            )
            or 0
        )

    def _user_generational_talents(self, *, club_ids: list[str]) -> int:
        if not club_ids:
            return 0
        badge_count = int(
            self.session.scalar(
                select(func.count(RegenDiscoveryBadge.id)).where(
                    RegenDiscoveryBadge.club_id.in_(tuple(club_ids)),
                    RegenDiscoveryBadge.badge_code.like("%generational%"),
                )
            )
            or 0
        )
        high_potential = len(
            [
                item
                for item in self.session.scalars(select(RegenProfile).where(RegenProfile.generated_for_club_id.in_(tuple(club_ids)))).all()
                if int((item.potential_range_json or {}).get("max", 0)) >= 95
            ]
        )
        return badge_count + high_potential

    def _user_scouting_events(self, *, club_ids: list[str], start: date, end: date) -> int:
        if not club_ids:
            return 0
        return len(
            [
                item
                for item in self.session.scalars(select(MarketWatchlistEntry).where(MarketWatchlistEntry.club_id.in_(tuple(club_ids)))).all()
                if start <= item.created_at.date() < end
            ]
        )

    def _user_predictions(self, *, user_id: str, start: date, end: date) -> int:
        return len(
            [
                item
                for item in self.session.scalars(select(Prediction).where(Prediction.user_id == user_id)).all()
                if start <= item.created_at.date() < end
            ]
        )

    def _user_finals_reached(self, *, club_ids: list[str], start: date, end: date) -> int:
        return len([item for item in self._user_matches(club_ids=club_ids, start=start, end=end) if item.stage == "final"])

    def _user_youth_development(self, *, club_ids: list[str], start: date, end: date) -> int:
        if not club_ids:
            return 0
        award_count = len(
            [
                item
                for item in self.session.scalars(select(RegenAward).where(RegenAward.club_id.in_(tuple(club_ids)))).all()
                if start <= item.awarded_at.date() < end
            ]
        )
        badge_count = len(
            [
                item
                for item in self.session.scalars(select(RegenDiscoveryBadge).where(RegenDiscoveryBadge.club_id.in_(tuple(club_ids)))).all()
                if start <= item.awarded_at.date() < end
            ]
        )
        return award_count + badge_count

    def _ensure_profile(self, user_id: str) -> UserProfile:
        profile = self.session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
        if profile is not None:
            return profile
        profile = UserProfile(user_id=user_id)
        self.session.add(profile)
        self.session.flush()
        return profile

    def _ensure_streak(self, user_id: str) -> UserStreak:
        streak = self.session.scalar(select(UserStreak).where(UserStreak.user_id == user_id))
        if streak is not None:
            return streak
        streak = UserStreak(user_id=user_id)
        self.session.add(streak)
        self.session.flush()
        return streak

    def _sync_profile_counters(self, user_id: str) -> None:
        profile = self._ensure_profile(user_id)
        profile.followers = self._follower_count(user_id=user_id)
        profile.following = int(self.session.scalar(select(func.count(UserFollow.id)).where(UserFollow.follower_user_id == user_id)) or 0)

    def _advance_streak(self, *, streak: UserStreak, today: date) -> None:
        if streak.last_completed_on == today - timedelta(days=1):
            streak.streak_days += 1
        else:
            streak.streak_days = 1
        streak.last_completed_on = today
        streak.longest_streak_days = max(streak.longest_streak_days, streak.streak_days)
        streak.warning_sent_on = None

    def _reset_streak_if_expired(self, *, streak: UserStreak, today: date, now: datetime) -> None:
        if streak.last_completed_on is None or (today - streak.last_completed_on).days <= 1:
            return
        streak.streak_days = 0
        streak.reward_multiplier = Decimal("1.0000")
        streak.xp_boost_multiplier = Decimal("1.0000")
        streak.coin_boost_multiplier = Decimal("1.0000")
        streak.last_reset_at = now
        streak.warning_sent_on = None

    def _refresh_streak_multipliers(self, streak: UserStreak) -> None:
        streak.reward_multiplier = Decimal(str(round(1 + min(streak.streak_days, 10) * 0.05, 4)))
        streak.coin_boost_multiplier = Decimal(str(round(1 + min(streak.streak_days, 10) * 0.05, 4)))
        streak.xp_boost_multiplier = Decimal(str(round(1 + min(streak.streak_days, 10) * 0.03, 4)))

    def _ensure_daily_task_notification(self, *, user_id: str) -> int:
        today = datetime.now(UTC).date()
        existing = self.session.scalar(
            select(NotificationRecord)
            .where(NotificationRecord.user_id == user_id, NotificationRecord.template_key == "DAILY_TASK_AVAILABLE")
            .order_by(NotificationRecord.created_at.desc())
            .limit(1)
        )
        if existing is not None and existing.created_at.date() == today:
            return 0
        self._notify(
            user_id=user_id,
            topic="objectives",
            template_key="DAILY_TASK_AVAILABLE",
            message="Daily tasks are available for your manager profile.",
            resource_type="daily_task",
            resource_id=today.isoformat(),
            metadata_json={"date": today.isoformat()},
        )
        return 1

    def _ensure_streak_warning(self, *, user_id: str) -> int:
        streak = self._ensure_streak(user_id)
        today = datetime.now(UTC).date()
        if streak.streak_days <= 0 or streak.last_completed_on != today - timedelta(days=1) or streak.warning_sent_on == today:
            return 0
        self._notify(
            user_id=user_id,
            topic="objectives",
            template_key="STREAK_WARNING",
            message="Your daily streak is at risk if you miss today.",
            resource_type="streak",
            resource_id=streak.id,
            metadata_json={"streak_days": streak.streak_days},
        )
        streak.warning_sent_on = today
        return 1

    def _notify(
        self,
        *,
        user_id: str | None,
        topic: str,
        template_key: str,
        message: str,
        resource_type: str | None,
        resource_id: str | None,
        metadata_json: dict[str, Any],
    ) -> None:
        self.session.add(
            NotificationRecord(
                user_id=user_id,
                topic=topic,
                template_key=template_key,
                resource_type=resource_type,
                resource_id=resource_id,
                message=message[:255],
                metadata_json=metadata_json,
            )
        )

    def _record_activity(
        self,
        *,
        actor_user_id: str | None,
        activity_type: str,
        headline: str,
        body: str | None = None,
        target_user_id: str | None = None,
        target_club_id: str | None = None,
        rivalry_key: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> SocialActivity:
        item = SocialActivity(
            actor_user_id=actor_user_id,
            activity_type=activity_type,
            target_user_id=target_user_id,
            target_club_id=target_club_id,
            rivalry_key=rivalry_key,
            headline=headline,
            body=body,
            metadata_json=metadata_json or {},
        )
        self.session.add(item)
        self.session.flush()
        return item

    def _increment_reputation(self, user_id: str, *, delta: int) -> None:
        self._ensure_profile(user_id).reputation_score += delta

    @staticmethod
    def _display_name(user: User) -> str:
        return user.display_name or user.full_name or user.username

    @staticmethod
    def _rivalry_key(club_a_id: str, club_b_id: str) -> str:
        ordered_a, ordered_b = sorted([club_a_id, club_b_id])
        return f"{ordered_a}:{ordered_b}"

    @staticmethod
    def _week_key(day: date) -> str:
        iso_year, iso_week, _ = day.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"

    @staticmethod
    def _activity_timestamp(item: dict[str, Any] | SocialActivity) -> datetime:
        return item["created_at"] if isinstance(item, dict) else item.created_at

    @staticmethod
    def _match_narrative(*, match: CompetitionMatch, home_name: str, away_name: str) -> str:
        goals = match.home_score + match.away_score
        if match.home_score == match.away_score:
            return f"{home_name} and {away_name} fought to a {match.home_score}-{match.away_score} draw."
        winner = home_name if match.home_score > match.away_score else away_name
        if goals >= 6:
            return f"{winner} emerged from a goal-fest as {home_name} and {away_name} lit up the scoreline."
        return f"{winner} took control and turned the result into another piece of club history."

    @staticmethod
    def _player_narrative(
        *,
        player: Player,
        ranking: HistoricalLeaderboardEntry | None,
        legacy: RegenLegacyRecord | None,
    ) -> str:
        if ranking is not None and ranking.rank <= 3:
            return f"{player.full_name} sits in the elite tier of the all-time conversation."
        if legacy is not None and legacy.is_legend:
            return legacy.narrative_summary or f"{player.full_name} built a legend-tier legacy across multiple seasons."
        return f"{player.full_name} is still writing a career arc with room to climb the historical ladder."

    @staticmethod
    def _club_narrative(*, club: ClubProfile, ranking: HistoricalLeaderboardEntry | None) -> str:
        if ranking is not None and ranking.rank == 1:
            return f"{club.club_name} currently sit at the summit of the all-time club rankings."
        if ranking is not None and ranking.rank <= 3:
            return f"{club.club_name} have become one of the era-defining clubs in the save."
        return f"{club.club_name} are building a timeline that still has major chapters left to write."
