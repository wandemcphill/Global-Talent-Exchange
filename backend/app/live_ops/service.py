from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.live_ops.models import LiveEvent, SeasonPass, SeasonPassClaim, SeasonPassTier, SeasonPassXpGrant
from app.models.notification_record import NotificationRecord
from app.models.user import User


class LiveOpsError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(frozen=True, slots=True)
class LiveOpsMultiplierSnapshot:
    reward_multiplier: float = 1.0
    xp_multiplier: float = 1.0
    entry_cost_multiplier: float = 1.0
    prediction_reward_multiplier: float = 1.0
    match_income_multiplier: float = 1.0


@dataclass(slots=True)
class LiveOpsService:
    session: Session

    def seed_defaults(self) -> None:
        if self.session.scalar(select(LiveEvent.id).limit(1)) is not None:
            return
        now = self._coerce_datetime(None)
        self.session.add_all(
            [
                LiveEvent(
                    name="Prediction Boost Weekend",
                    start_date=now.replace(hour=0, minute=0, second=0, microsecond=0),
                    end_date=(now + timedelta(days=2)).replace(hour=23, minute=59, second=59, microsecond=0),
                    rules_json={
                        "prediction_reward_multiplier": 1.5,
                        "xp_multiplier": 1.25,
                    },
                    rewards_json={"label": "Prediction boost"},
                ),
                LiveEvent(
                    name="Double Rewards Weekend",
                    start_date=(now + timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0),
                    end_date=(now + timedelta(days=9)).replace(hour=23, minute=59, second=59, microsecond=0),
                    rules_json={
                        "reward_multiplier": 2.0,
                        "match_income_multiplier": 1.5,
                    },
                    rewards_json={"label": "Double rewards"},
                ),
            ]
        )
        self.session.flush()

    def list_events(self, *, as_of: datetime | None = None, include_inactive: bool = False) -> list[LiveEvent]:
        stmt = select(LiveEvent).order_by(LiveEvent.start_date.asc(), LiveEvent.name.asc())
        if not include_inactive:
            point_in_time = self._coerce_datetime(as_of)
            stmt = stmt.where(
                LiveEvent.active.is_(True),
                LiveEvent.end_date >= point_in_time,
            )
        return list(self.session.scalars(stmt).all())

    def active_events(self, *, as_of: datetime | None = None) -> list[LiveEvent]:
        point_in_time = self._coerce_datetime(as_of)
        return list(
            self.session.scalars(
                select(LiveEvent).where(
                    LiveEvent.active.is_(True),
                    LiveEvent.start_date <= point_in_time,
                    LiveEvent.end_date >= point_in_time,
                )
            ).all()
        )

    def multiplier_snapshot(self, *, as_of: datetime | None = None) -> LiveOpsMultiplierSnapshot:
        reward_multiplier = 1.0
        xp_multiplier = 1.0
        entry_cost_multiplier = 1.0
        prediction_reward_multiplier = 1.0
        match_income_multiplier = 1.0
        for event in self.active_events(as_of=as_of):
            rules = dict(event.rules_json or {})
            reward_multiplier *= float(rules.get("reward_multiplier", 1.0))
            xp_multiplier *= float(rules.get("xp_multiplier", 1.0))
            entry_cost_multiplier *= float(rules.get("entry_cost_multiplier", 1.0))
            prediction_reward_multiplier *= float(rules.get("prediction_reward_multiplier", 1.0))
            match_income_multiplier *= float(rules.get("match_income_multiplier", 1.0))
        return LiveOpsMultiplierSnapshot(
            reward_multiplier=reward_multiplier,
            xp_multiplier=xp_multiplier,
            entry_cost_multiplier=entry_cost_multiplier,
            prediction_reward_multiplier=prediction_reward_multiplier,
            match_income_multiplier=match_income_multiplier,
        )

    def get_or_create_season_pass(self, *, user_id: str, season_id: str | None = None) -> SeasonPass:
        resolved_season_id = season_id or self.default_season_id()
        season_pass = self.session.scalar(
            select(SeasonPass).where(
                SeasonPass.user_id == user_id,
                SeasonPass.season_id == resolved_season_id,
            )
        )
        if season_pass is None:
            season_pass = SeasonPass(
                user_id=user_id,
                season_id=resolved_season_id,
                tier=SeasonPassTier.FREE,
                rewards_json=self._default_reward_track(),
            )
            self.session.add(season_pass)
            self.session.flush()
        return season_pass

    def get_pass_view(self, *, actor: User, season_id: str | None = None, grant_limit: int = 10) -> dict[str, object]:
        season_pass = self.get_or_create_season_pass(user_id=actor.id, season_id=season_id)
        claims = list(
            self.session.scalars(
                select(SeasonPassClaim)
                .where(SeasonPassClaim.season_pass_id == season_pass.id)
                .order_by(SeasonPassClaim.level.asc())
            ).all()
        )
        grants = list(
            self.session.scalars(
                select(SeasonPassXpGrant)
                .where(SeasonPassXpGrant.season_pass_id == season_pass.id)
                .order_by(SeasonPassXpGrant.created_at.desc())
                .limit(grant_limit)
            ).all()
        )
        return {
            "season_pass": season_pass,
            "claims": claims,
            "recent_xp_grants": grants,
        }

    def claim_reward(self, *, actor: User, level: int, season_id: str | None = None) -> SeasonPassClaim:
        season_pass = self.get_or_create_season_pass(user_id=actor.id, season_id=season_id)
        if level > season_pass.level:
            raise LiveOpsError("Season pass level is not unlocked yet.")
        existing = self.session.scalar(
            select(SeasonPassClaim).where(
                SeasonPassClaim.season_pass_id == season_pass.id,
                SeasonPassClaim.level == level,
            )
        )
        if existing is not None:
            raise LiveOpsError("Reward level has already been claimed.")
        reward = self._reward_for_level(season_pass=season_pass, level=level)
        claim = SeasonPassClaim(
            season_pass_id=season_pass.id,
            user_id=actor.id,
            level=level,
            reward_payload_json=reward,
            claimed_at=self._coerce_datetime(None),
        )
        self.session.add(claim)
        currency_amount = float(reward.get("currency", 0) or 0)
        if currency_amount > 0:
            from app.club_finance.service import ClubFinanceService

            ClubFinanceService(self.session).apply_season_pass_currency_bonus(
                user_id=actor.id,
                amount=currency_amount,
                reference_key=f"season-pass-claim:{season_pass.id}:{level}",
                metadata={"season_id": season_pass.season_id, "level": level},
            )
        self.session.flush()
        return claim

    def award_prediction_xp(self, *, user_id: str, prediction_id: str, correct: bool, reward: float) -> None:
        amount = 10 + (10 if correct else 0) + min(10, int(round(reward / 5)))
        self.award_xp(
            user_id=user_id,
            source_type="prediction",
            amount=amount,
            reference_key=f"prediction:{prediction_id}",
            metadata={"prediction_id": prediction_id, "correct": correct, "reward_earned": reward},
        )

    def record_match_xp(
        self,
        *,
        match_id: str,
        home_user_id: str | None,
        away_user_id: str | None,
        winner_user_id: str | None,
    ) -> None:
        participants = [user_id for user_id in (home_user_id, away_user_id) if user_id]
        for user_id in participants:
            self.award_xp(
                user_id=user_id,
                source_type="match_played",
                amount=25,
                reference_key=f"match-played:{match_id}:{user_id}",
                metadata={"match_id": match_id},
            )
            if user_id == winner_user_id:
                streak_bonus = 10 if self._recent_win_count(user_id=user_id) >= 2 else 0
                self.award_xp(
                    user_id=user_id,
                    source_type="match_win",
                    amount=20 + streak_bonus,
                    reference_key=f"match-win:{match_id}:{user_id}",
                    metadata={"match_id": match_id, "streak_bonus": streak_bonus},
                )

    def award_xp(
        self,
        *,
        user_id: str,
        source_type: str,
        amount: int,
        reference_key: str,
        metadata: dict[str, object] | None = None,
        season_id: str | None = None,
    ) -> SeasonPassXpGrant:
        existing = self.session.scalar(select(SeasonPassXpGrant).where(SeasonPassXpGrant.reference_key == reference_key))
        if existing is not None:
            return existing
        season_pass = self.get_or_create_season_pass(user_id=user_id, season_id=season_id)
        snapshot = self.multiplier_snapshot()
        applied_amount = max(1, int(round(amount * snapshot.xp_multiplier)))
        previous_level = season_pass.level
        season_pass.xp += applied_amount
        season_pass.level = 1 + (season_pass.xp // 100)
        grant = SeasonPassXpGrant(
            season_pass_id=season_pass.id,
            user_id=user_id,
            source_type=source_type,
            amount=applied_amount,
            reference_key=reference_key,
            metadata_json=dict(metadata or {}),
            created_at=self._coerce_datetime(None),
        )
        self.session.add(grant)
        self.session.flush()
        if season_pass.level > previous_level:
            self.session.add(
                NotificationRecord(
                    user_id=user_id,
                    topic="season_pass_level_up",
                    template_key="SEASON_PASS_LEVEL_UP",
                    resource_type="season_pass",
                    resource_id=season_pass.id,
                    message=f"Season pass reached level {season_pass.level}."[:255],
                    metadata_json={
                        "season_pass_id": season_pass.id,
                        "season_id": season_pass.season_id,
                        "previous_level": previous_level,
                        "new_level": season_pass.level,
                    },
                )
            )
        return grant

    def run_live_event_cycle(self, *, as_of: datetime | None = None) -> dict[str, int]:
        point_in_time = self._coerce_datetime(as_of)
        active_events = self.active_events(as_of=point_in_time)
        users = list(self.session.scalars(select(User).where(User.is_active.is_(True))).all())
        notifications_created = 0
        events_started = 0
        for event in active_events:
            if event.started_notification_sent_at is not None:
                continue
            for user in users:
                self.session.add(
                    NotificationRecord(
                        user_id=user.id,
                        topic="live_event_started",
                        template_key="LIVE_EVENT_STARTED",
                        resource_type="live_event",
                        resource_id=event.id,
                        message=f"Live event started: {event.name}."[:255],
                        metadata_json={
                            "live_event_id": event.id,
                            "name": event.name,
                            "rules": event.rules_json,
                            "rewards": event.rewards_json,
                        },
                    )
                )
                notifications_created += 1
            event.started_notification_sent_at = point_in_time
            events_started += 1
        self.session.flush()
        return {"events_started": events_started, "notifications_created": notifications_created}

    def default_season_id(self) -> str:
        today = datetime.now(UTC).date()
        return f"{today.year}-season-pass"

    def _recent_win_count(self, *, user_id: str) -> int:
        recent = list(
            self.session.scalars(
                select(SeasonPassXpGrant)
                .where(
                    SeasonPassXpGrant.user_id == user_id,
                    SeasonPassXpGrant.source_type == "match_win",
                )
                .order_by(SeasonPassXpGrant.created_at.desc())
                .limit(2)
            ).all()
        )
        return len(recent)

    @staticmethod
    def _default_reward_track() -> dict[str, object]:
        return {
            "levels": [
                {"level": 1, "currency": 25, "badge": "starter-manager"},
                {"level": 2, "currency": 40, "cosmetic": "touchline-jacket"},
                {"level": 3, "currency": 60, "badge": "prediction-scout"},
                {"level": 4, "currency": 80, "manager_perk": "extra-scouting-report-slot"},
                {"level": 5, "currency": 120, "cosmetic": "club-bus-livery"},
            ],
            "non_gameplay_advantage_only": True,
        }

    @staticmethod
    def _coerce_datetime(value: datetime | None) -> datetime:
        resolved = value or datetime.now(UTC)
        if resolved.tzinfo is None:
            return resolved.replace(tzinfo=UTC)
        return resolved.astimezone(UTC)

    @staticmethod
    def _reward_for_level(*, season_pass: SeasonPass, level: int) -> dict[str, object]:
        for entry in list((season_pass.rewards_json or {}).get("levels") or []):
            if int(entry.get("level", 0)) == level:
                return dict(entry)
        raise LiveOpsError("Season pass reward level is not configured.")


__all__ = ["LiveOpsError", "LiveOpsMultiplierSnapshot", "LiveOpsService"]
