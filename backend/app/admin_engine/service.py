from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.admin_engine.schemas import (
    AdminCalendarRuleUpsertRequest,
    AdminFeatureFlagUpsertRequest,
    AdminRewardRuleUpsertRequest,
    AdminRewardRuleStabilityControls,
)
from backend.app.competition_engine.scheduler import CompetitionScheduler
from backend.app.models.admin_rules import AdminCalendarRule, AdminFeatureFlag, AdminRewardRule
from backend.app.models.user import User

DEFAULT_FEATURE_FLAGS: tuple[dict[str, object], ...] = (
    {
        "feature_key": "story-feed",
        "title": "Story Feed",
        "description": "Surface giant-killer stories, rivalries, and major tournament narratives.",
        "enabled": True,
        "audience": "global",
    },
    {
        "feature_key": "daily-challenges",
        "title": "Daily Challenges",
        "description": "Enable small FanCoin daily engagement rewards.",
        "enabled": True,
        "audience": "global",
    },
    {
        "feature_key": "national-team-engine",
        "title": "National Team Engine",
        "description": "Expose national team tournament entry surfaces.",
        "enabled": False,
        "audience": "global",
    },
)

DEFAULT_CALENDAR_RULES: tuple[dict[str, object], ...] = (
    {
        "rule_key": "world-cup-exclusive-senior-windows",
        "title": "World Cup Exclusive Senior Windows",
        "description": "Pause GTEX leagues and champions competitions when GTEX World Cup or World Championship occupies the same senior windows.",
        "world_cup_exclusive": True,
        "active": True,
        "priority": 10,
        "config_json": {
            "pause_competition_types": ["league", "champions_league"],
            "exclusive_competition_types": ["world_super_cup"],
        },
    },
    {
        "rule_key": "youth-tournaments-share-weeks",
        "title": "Youth Tournaments Share Weeks",
        "description": "Keep U17, U20 and U21 continental/youth competitions aligned in the same calendar week.",
        "world_cup_exclusive": False,
        "active": True,
        "priority": 20,
        "config_json": {
            "competition_families": ["academy"],
            "same_week_groups": ["u17", "u20", "u21"],
        },
    },
)

DEFAULT_REWARD_RULES: tuple[dict[str, object], ...] = (
    {
        "rule_key": "platform-economy-defaults",
        "title": "Platform Economy Defaults",
        "description": "Default fee and rake envelope for trading, gifting and withdrawals.",
        "trading_fee_bps": 2000,
        "gift_platform_rake_bps": 3000,
        "withdrawal_fee_bps": 1000,
        "minimum_withdrawal_fee_credits": Decimal("5.0000"),
        "competition_platform_fee_bps": 1000,
        "stability_controls_json": AdminRewardRuleStabilityControls().model_dump(mode="json"),
        "active": True,
    },
)


@dataclass(slots=True)
class AdminEngineService:
    session: Session

    @staticmethod
    def normalize_stability_controls(
        payload: AdminRewardRuleStabilityControls | dict[str, object] | None = None,
    ) -> AdminRewardRuleStabilityControls:
        return AdminRewardRuleStabilityControls.model_validate(payload or {})

    @classmethod
    def normalize_stability_controls_payload(
        cls,
        payload: AdminRewardRuleStabilityControls | dict[str, object] | None = None,
    ) -> dict[str, object]:
        return cls.normalize_stability_controls(payload).model_dump(mode="json")

    def seed_defaults(self) -> None:
        self._seed_feature_flags()
        self._seed_calendar_rules()
        self._seed_reward_rules()
        self.session.flush()

    def _seed_feature_flags(self) -> None:
        existing = {item.feature_key for item in self.session.scalars(select(AdminFeatureFlag)).all()}
        for payload in DEFAULT_FEATURE_FLAGS:
            if payload["feature_key"] in existing:
                continue
            self.session.add(AdminFeatureFlag(**payload))

    def _seed_calendar_rules(self) -> None:
        existing = {item.rule_key for item in self.session.scalars(select(AdminCalendarRule)).all()}
        for payload in DEFAULT_CALENDAR_RULES:
            if payload["rule_key"] in existing:
                continue
            self.session.add(AdminCalendarRule(**payload))

    def _seed_reward_rules(self) -> None:
        existing = {item.rule_key for item in self.session.scalars(select(AdminRewardRule)).all()}
        for payload in DEFAULT_REWARD_RULES:
            if payload["rule_key"] in existing:
                continue
            self.session.add(AdminRewardRule(**payload))

    def list_feature_flags(self, *, active_only: bool = False) -> list[AdminFeatureFlag]:
        statement = select(AdminFeatureFlag).order_by(AdminFeatureFlag.feature_key.asc())
        if active_only:
            statement = statement.where(AdminFeatureFlag.enabled.is_(True))
        return list(self.session.scalars(statement).all())

    def upsert_feature_flag(self, *, actor: User, payload: AdminFeatureFlagUpsertRequest) -> AdminFeatureFlag:
        record = self.session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == payload.feature_key))
        if record is None:
            record = AdminFeatureFlag(feature_key=payload.feature_key)
            self.session.add(record)
        record.title = payload.title
        record.description = payload.description
        record.enabled = payload.enabled
        record.audience = payload.audience
        record.updated_by_user_id = actor.id
        self.session.flush()
        return record

    def list_calendar_rules(self, *, active_only: bool = False) -> list[AdminCalendarRule]:
        statement = select(AdminCalendarRule).order_by(AdminCalendarRule.priority.asc(), AdminCalendarRule.rule_key.asc())
        if active_only:
            statement = statement.where(AdminCalendarRule.active.is_(True))
        return list(self.session.scalars(statement).all())

    def upsert_calendar_rule(self, *, actor: User, payload: AdminCalendarRuleUpsertRequest) -> AdminCalendarRule:
        record = self.session.scalar(select(AdminCalendarRule).where(AdminCalendarRule.rule_key == payload.rule_key))
        if record is None:
            record = AdminCalendarRule(rule_key=payload.rule_key)
            self.session.add(record)
        record.title = payload.title
        record.description = payload.description
        record.world_cup_exclusive = payload.world_cup_exclusive
        record.active = payload.active
        record.priority = payload.priority
        record.config_json = dict(payload.config_json)
        record.updated_by_user_id = actor.id
        self.session.flush()
        return record

    def list_reward_rules(self, *, active_only: bool = False) -> list[AdminRewardRule]:
        statement = select(AdminRewardRule).order_by(AdminRewardRule.rule_key.asc())
        if active_only:
            statement = statement.where(AdminRewardRule.active.is_(True))
        return list(self.session.scalars(statement).all())

    def get_active_reward_rule(self) -> AdminRewardRule | None:
        return next(iter(self.list_reward_rules(active_only=True)), None)

    def get_active_stability_controls(self) -> AdminRewardRuleStabilityControls:
        rule = self.get_active_reward_rule()
        payload = None if rule is None else rule.stability_controls_json
        return self.normalize_stability_controls(payload)

    def upsert_reward_rule(self, *, actor: User, payload: AdminRewardRuleUpsertRequest) -> AdminRewardRule:
        record = self.session.scalar(select(AdminRewardRule).where(AdminRewardRule.rule_key == payload.rule_key))
        if record is None:
            record = AdminRewardRule(rule_key=payload.rule_key)
            self.session.add(record)
        record.title = payload.title
        record.description = payload.description
        record.trading_fee_bps = payload.trading_fee_bps
        record.gift_platform_rake_bps = payload.gift_platform_rake_bps
        record.withdrawal_fee_bps = payload.withdrawal_fee_bps
        record.minimum_withdrawal_fee_credits = payload.minimum_withdrawal_fee_credits
        record.competition_platform_fee_bps = payload.competition_platform_fee_bps
        record.stability_controls_json = self.normalize_stability_controls_payload(payload.stability_controls)
        record.active = payload.active
        record.updated_by_user_id = actor.id
        self.session.flush()
        return record

    def schedule_preview(self, requests: Iterable, /):
        scheduler = CompetitionScheduler()
        return scheduler.build_schedule(tuple(requests))
