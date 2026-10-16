from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import re
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.calendar_engine.service import CalendarEngineService
from app.ingestion.models import MarketSignal, Player
from app.models.base import utcnow
from app.models.player_cards import PlayerCard, PlayerCardFormBuff
from app.models.real_world_football import (
    EffectRecordStatus,
    EventEffectRule,
    EventIngestionJob,
    EventIngestionJobStatus,
    PlayerDemandSignal,
    PlayerFormModifier,
    RealWorldEventApprovalStatus,
    RealWorldEventSourceType,
    RealWorldFootballEvent,
    TrendingPlayerFlag,
)
from app.models.user import User
from app.story_feed_engine.service import StoryFeedService


_ENGINE_SOURCE = "football_event_engine"
_NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")
_ALLOWED_EVENT_TYPES = frozenset(
    {
        "hat_trick",
        "breakout_performance",
        "transfer_rumor",
        "confirmed_transfer",
        "major_trophy_win",
        "injury",
        "form_surge",
        "notable_streak",
        "big_debut",
    }
)
_ALLOWED_SOURCE_TYPES = frozenset(item.value for item in RealWorldEventSourceType)
_SENSITIVE_EVENT_TYPES = frozenset({"transfer_rumor", "confirmed_transfer", "injury"})
_DEFAULT_EVENT_TITLES = {
    "hat_trick": "{player_name} hit a hat trick",
    "breakout_performance": "{player_name} delivered a breakout performance",
    "transfer_rumor": "{player_name} is drawing transfer rumor heat",
    "confirmed_transfer": "{player_name} completed a transfer move",
    "major_trophy_win": "{player_name} lifted a major trophy",
    "injury": "{player_name} suffered an injury setback",
    "form_surge": "{player_name} is on a form surge",
    "notable_streak": "{player_name} extended a notable streak",
    "big_debut": "{player_name} made a big debut",
}
_CALENDAR_EVENT_TYPES = frozenset({"confirmed_transfer", "major_trophy_win"})


class RealWorldFootballEventError(ValueError):
    pass


class RealWorldFootballEventValidationError(RealWorldFootballEventError):
    pass


class RealWorldFootballEventNotFoundError(RealWorldFootballEventError):
    pass


@dataclass(frozen=True, slots=True)
class RealWorldFootballEventCreate:
    event_type: str
    player_id: str
    occurred_at: datetime
    source_type: str = RealWorldEventSourceType.MANUAL.value
    source_label: str = "admin_manual"
    external_event_id: str | None = None
    title: str | None = None
    summary: str | None = None
    severity: float = 1.0
    current_club_id: str | None = None
    competition_id: str | None = None
    requires_admin_review: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EventFeedIngestionRequest:
    source_label: str
    source_type: str = RealWorldEventSourceType.IMPORT_FEED.value
    events: tuple[RealWorldFootballEventCreate, ...] = ()


@dataclass(frozen=True, slots=True)
class EventEffectRuleUpsert:
    event_type: str
    effect_type: str
    effect_code: str
    label: str
    is_enabled: bool = True
    approval_required: bool = False
    base_magnitude: float = 0.0
    duration_hours: int = 0
    priority: int = 0
    gameplay_enabled: bool = False
    market_enabled: bool = False
    recommendation_enabled: bool = False
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EventCategoryToggle:
    event_type: str
    is_enabled: bool


@dataclass(frozen=True, slots=True)
class NormalizedRealWorldFootballEvent:
    player_id: str
    current_club_id: str | None
    competition_id: str | None
    event_type: str
    source_type: str
    source_label: str
    external_event_id: str | None
    dedupe_key: str
    title: str
    summary: str | None
    severity: float
    occurred_at: datetime
    requires_admin_review: bool
    metadata_json: dict[str, Any]
    raw_payload_json: dict[str, Any]
    normalized_payload_json: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PlayerRealWorldImpact:
    player_id: str
    active_flags: tuple[TrendingPlayerFlag, ...]
    active_form_modifiers: tuple[PlayerFormModifier, ...]
    active_demand_signals: tuple[PlayerDemandSignal, ...]
    active_flag_codes: tuple[str, ...]
    affected_card_ids: tuple[str, ...]
    recommendation_priority_delta: float
    market_buzz_score: float
    gameplay_effect_total: float
    market_effect_total: float


def _default_rule(
    event_type: str,
    effect_type: str,
    effect_code: str,
    label: str,
    base_magnitude: float,
    duration_hours: int,
    priority: int,
    *,
    gameplay_enabled: bool = False,
    market_enabled: bool = False,
    recommendation_enabled: bool = False,
    approval_required: bool = False,
    config: dict[str, Any] | None = None,
) -> EventEffectRuleUpsert:
    return EventEffectRuleUpsert(
        event_type=event_type,
        effect_type=effect_type,
        effect_code=effect_code,
        label=label,
        is_enabled=True,
        approval_required=approval_required,
        base_magnitude=base_magnitude,
        duration_hours=duration_hours,
        priority=priority,
        gameplay_enabled=gameplay_enabled,
        market_enabled=market_enabled,
        recommendation_enabled=recommendation_enabled,
        config=config or {},
    )


_DEFAULT_RULES: tuple[EventEffectRuleUpsert, ...] = (
    _default_rule(
        "hat_trick",
        "form_modifier",
        "hot_player_week",
        "Hot Player of the Week",
        9.0,
        168,
        90,
        gameplay_enabled=True,
        market_enabled=True,
        recommendation_enabled=True,
        config={"modifier_type": "hot_player_of_the_week", "card_buff_type": "hot_player_of_the_week", "gameplay_scale": 1.0, "market_scale": 0.7, "recommendation_scale": 0.8},
    ),
    _default_rule(
        "hat_trick",
        "trending_flag",
        "spotlight",
        "Spotlight",
        14.0,
        72,
        100,
        market_enabled=True,
        recommendation_enabled=True,
        config={"flag_type": "spotlight", "flag_label": "Spotlight", "priority_base": 80},
    ),
    _default_rule(
        "hat_trick",
        "demand_signal",
        "hat_trick_buzz",
        "Hat-trick buzz",
        11.0,
        96,
        80,
        market_enabled=True,
        recommendation_enabled=True,
        config={"signal_type": "major_performance_buzz", "signal_label": "Major performance buzz", "market_buzz_scale": 1.0, "scouting_scale": 0.5, "recommendation_scale": 0.9, "market_signal_scale": 1.0},
    ),
    _default_rule(
        "breakout_performance",
        "form_modifier",
        "confidence_bump",
        "Confidence bump",
        6.0,
        120,
        75,
        gameplay_enabled=True,
        market_enabled=True,
        recommendation_enabled=True,
        config={"modifier_type": "confidence_bump", "card_buff_type": "confidence_bump", "gameplay_scale": 0.9, "market_scale": 0.7, "recommendation_scale": 0.8},
    ),
    _default_rule(
        "breakout_performance",
        "demand_signal",
        "scouting_surge",
        "Scouting surge",
        8.0,
        120,
        60,
        market_enabled=True,
        recommendation_enabled=True,
        config={"signal_type": "breakout_attention", "signal_label": "Breakout attention", "market_buzz_scale": 0.7, "scouting_scale": 1.2, "recommendation_scale": 0.9, "market_signal_scale": 0.9},
    ),
    _default_rule(
        "transfer_rumor",
        "demand_signal",
        "rumor_heat",
        "Rumor heat",
        7.0,
        168,
        65,
        market_enabled=True,
        recommendation_enabled=True,
        approval_required=True,
        config={"signal_type": "transfer_rumor_heat", "signal_label": "Transfer rumor heat", "market_buzz_scale": 1.1, "scouting_scale": 0.7, "recommendation_scale": 0.9, "market_signal_scale": 0.8},
    ),
    _default_rule(
        "confirmed_transfer",
        "trending_flag",
        "spotlight",
        "Spotlight",
        12.0,
        120,
        85,
        market_enabled=True,
        recommendation_enabled=True,
        approval_required=True,
        config={"flag_type": "spotlight", "flag_label": "Spotlight", "priority_base": 70},
    ),
    _default_rule(
        "confirmed_transfer",
        "form_modifier",
        "transfer_excitement",
        "Transfer excitement",
        5.0,
        168,
        70,
        gameplay_enabled=True,
        market_enabled=True,
        recommendation_enabled=True,
        approval_required=True,
        config={"modifier_type": "transfer_excitement", "card_buff_type": "transfer_excitement", "gameplay_scale": 0.6, "market_scale": 0.9, "recommendation_scale": 0.9},
    ),
    _default_rule(
        "major_trophy_win",
        "form_modifier",
        "winner_confidence",
        "Winner confidence",
        7.0,
        168,
        75,
        gameplay_enabled=True,
        market_enabled=True,
        recommendation_enabled=True,
        config={"modifier_type": "confidence_bump", "card_buff_type": "confidence_bump", "gameplay_scale": 0.9, "market_scale": 0.7, "recommendation_scale": 0.8},
    ),
    _default_rule(
        "major_trophy_win",
        "trending_flag",
        "spotlight",
        "Spotlight",
        10.0,
        96,
        85,
        market_enabled=True,
        recommendation_enabled=True,
        config={"flag_type": "spotlight", "flag_label": "Spotlight", "priority_base": 75},
    ),
    _default_rule(
        "injury",
        "form_modifier",
        "injury_drag",
        "Injury drag",
        -8.0,
        336,
        95,
        gameplay_enabled=True,
        market_enabled=True,
        recommendation_enabled=True,
        approval_required=True,
        config={"modifier_type": "injury_drag", "card_buff_type": "injury_drag", "gameplay_scale": 1.0, "market_scale": 0.8, "recommendation_scale": 0.5},
    ),
    _default_rule(
        "injury",
        "demand_signal",
        "availability_drop",
        "Availability drop",
        -5.0,
        336,
        85,
        market_enabled=True,
        recommendation_enabled=True,
        approval_required=True,
        config={"signal_type": "injury_availability_drop", "signal_label": "Availability drop", "market_buzz_scale": -0.4, "scouting_scale": -0.3, "recommendation_scale": -0.8, "market_signal_scale": 0.0},
    ),
    _default_rule(
        "form_surge",
        "form_modifier",
        "form_surge",
        "Form surge",
        7.0,
        168,
        80,
        gameplay_enabled=True,
        market_enabled=True,
        recommendation_enabled=True,
        config={"modifier_type": "form_surge", "card_buff_type": "form_surge", "gameplay_scale": 1.0, "market_scale": 0.8, "recommendation_scale": 0.8},
    ),
    _default_rule(
        "form_surge",
        "trending_flag",
        "trending",
        "Trending",
        8.0,
        96,
        70,
        market_enabled=True,
        recommendation_enabled=True,
        config={"flag_type": "trending", "flag_label": "Trending", "priority_base": 55},
    ),
    _default_rule(
        "notable_streak",
        "form_modifier",
        "streak_confidence",
        "Streak confidence",
        5.0,
        144,
        65,
        gameplay_enabled=True,
        market_enabled=True,
        recommendation_enabled=True,
        config={"modifier_type": "confidence_bump", "card_buff_type": "confidence_bump", "gameplay_scale": 0.8, "market_scale": 0.6, "recommendation_scale": 0.7},
    ),
    _default_rule(
        "notable_streak",
        "demand_signal",
        "streak_buzz",
        "Streak buzz",
        6.0,
        144,
        60,
        market_enabled=True,
        recommendation_enabled=True,
        config={"signal_type": "notable_streak", "signal_label": "Notable streak", "market_buzz_scale": 0.7, "scouting_scale": 0.4, "recommendation_scale": 0.7, "market_signal_scale": 0.7},
    ),
    _default_rule(
        "big_debut",
        "form_modifier",
        "big_debut_bump",
        "Big debut bump",
        6.0,
        120,
        70,
        gameplay_enabled=True,
        market_enabled=True,
        recommendation_enabled=True,
        config={"modifier_type": "big_debut_bump", "card_buff_type": "big_debut_bump", "gameplay_scale": 0.9, "market_scale": 0.8, "recommendation_scale": 0.9},
    ),
    _default_rule(
        "big_debut",
        "trending_flag",
        "spotlight",
        "Spotlight",
        9.0,
        72,
        78,
        market_enabled=True,
        recommendation_enabled=True,
        config={"flag_type": "spotlight", "flag_label": "Spotlight", "priority_base": 65},
    ),
    _default_rule(
        "big_debut",
        "demand_signal",
        "debut_attention",
        "Debut attention",
        7.0,
        96,
        68,
        market_enabled=True,
        recommendation_enabled=True,
        config={"signal_type": "big_debut_attention", "signal_label": "Big debut attention", "market_buzz_scale": 0.8, "scouting_scale": 0.8, "recommendation_scale": 0.9, "market_signal_scale": 0.8},
    ),
)


@dataclass(slots=True)
class RealWorldFootballEventService:
    session: Session

    def seed_defaults(self) -> None:
        for payload in _DEFAULT_RULES:
            self._upsert_effect_rule_entity(payload, reapply_existing=False)
        self.session.flush()

    def list_events(
        self,
        *,
        approval_status: str | None = None,
        player_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[RealWorldFootballEvent]:
        statement = select(RealWorldFootballEvent)
        if approval_status:
            statement = statement.where(RealWorldFootballEvent.approval_status == approval_status)
        if player_id:
            statement = statement.where(RealWorldFootballEvent.player_id == player_id)
        if event_type:
            statement = statement.where(RealWorldFootballEvent.event_type == self._normalize_event_type(event_type))
        statement = statement.order_by(RealWorldFootballEvent.occurred_at.desc(), RealWorldFootballEvent.created_at.desc()).limit(limit)
        return list(self.session.scalars(statement))

    def list_player_events(self, player_id: str, *, approved_only: bool = True, limit: int = 20) -> list[RealWorldFootballEvent]:
        statement = select(RealWorldFootballEvent).where(RealWorldFootballEvent.player_id == player_id)
        if approved_only:
            statement = statement.where(RealWorldFootballEvent.approval_status == RealWorldEventApprovalStatus.APPROVED.value)
        statement = statement.order_by(RealWorldFootballEvent.occurred_at.desc(), RealWorldFootballEvent.created_at.desc()).limit(limit)
        return list(self.session.scalars(statement))

    def list_rules(self, *, event_type: str | None = None, active_only: bool = False) -> list[EventEffectRule]:
        statement = select(EventEffectRule)
        if event_type:
            statement = statement.where(EventEffectRule.event_type == self._normalize_event_type(event_type))
        if active_only:
            statement = statement.where(EventEffectRule.is_enabled.is_(True))
        statement = statement.order_by(EventEffectRule.event_type.asc(), EventEffectRule.priority.desc(), EventEffectRule.effect_code.asc())
        return list(self.session.scalars(statement))

    def normalize_event(self, payload: RealWorldFootballEventCreate) -> NormalizedRealWorldFootballEvent:
        player = self._get_player(payload.player_id)
        event_type = self._normalize_event_type(payload.event_type)
        source_type = self._normalize_source_type(payload.source_type)
        source_label = (payload.source_label or source_type).strip()
        if not source_label:
            raise RealWorldFootballEventValidationError("source_label is required")
        occurred_at = self._coerce_datetime(payload.occurred_at)
        severity = self._clamp_severity(payload.severity)
        title = (payload.title or _DEFAULT_EVENT_TITLES[event_type].format(player_name=player.full_name)).strip()
        if not title:
            raise RealWorldFootballEventValidationError("title is required")
        summary = payload.summary.strip() if payload.summary else None
        rules = self.list_rules(event_type=event_type)
        requires_admin_review = (
            payload.requires_admin_review
            if payload.requires_admin_review is not None
            else event_type in _SENSITIVE_EVENT_TYPES or any(rule.approval_required and rule.is_enabled for rule in rules)
        )
        external_event_id = payload.external_event_id.strip() if payload.external_event_id else None
        dedupe_key = self._build_dedupe_key(
            source_type=source_type,
            source_label=source_label,
            external_event_id=external_event_id,
            player_id=player.id,
            event_type=event_type,
            occurred_at=occurred_at,
            title=title,
        )
        return NormalizedRealWorldFootballEvent(
            player_id=player.id,
            current_club_id=payload.current_club_id or player.current_club_id,
            competition_id=payload.competition_id or player.current_competition_id,
            event_type=event_type,
            source_type=source_type,
            source_label=source_label,
            external_event_id=external_event_id,
            dedupe_key=dedupe_key,
            title=title,
            summary=summary,
            severity=severity,
            occurred_at=occurred_at,
            requires_admin_review=requires_admin_review,
            metadata_json=dict(payload.metadata),
            raw_payload_json=dict(payload.raw_payload),
            normalized_payload_json={
                "event_type": event_type,
                "source_type": source_type,
                "source_label": source_label,
                "player_id": player.id,
                "player_name": player.full_name,
                "severity": severity,
                "requires_admin_review": requires_admin_review,
                "rule_effect_codes": [rule.effect_code for rule in rules if rule.is_enabled],
            },
        )

    def create_event(
        self,
        payload: RealWorldFootballEventCreate,
        *,
        actor: User | None = None,
        ingestion_job_id: str | None = None,
    ) -> RealWorldFootballEvent:
        normalized = self.normalize_event(payload)
        event = self.session.scalar(
            select(RealWorldFootballEvent).where(RealWorldFootballEvent.dedupe_key == normalized.dedupe_key)
        )
        now = utcnow()
        if event is None:
            approval_status = (
                RealWorldEventApprovalStatus.PENDING_REVIEW.value
                if normalized.requires_admin_review
                else RealWorldEventApprovalStatus.APPROVED.value
            )
            event = RealWorldFootballEvent(
                ingestion_job_id=ingestion_job_id,
                player_id=normalized.player_id,
                current_club_id=normalized.current_club_id,
                competition_id=normalized.competition_id,
                event_type=normalized.event_type,
                source_type=normalized.source_type,
                source_label=normalized.source_label,
                external_event_id=normalized.external_event_id,
                dedupe_key=normalized.dedupe_key,
                approval_status=approval_status,
                requires_admin_review=normalized.requires_admin_review,
                title=normalized.title,
                summary=normalized.summary,
                severity=normalized.severity,
                occurred_at=normalized.occurred_at,
                approved_by_user_id=actor.id if approval_status == RealWorldEventApprovalStatus.APPROVED.value and actor is not None else None,
                approved_at=now if approval_status == RealWorldEventApprovalStatus.APPROVED.value else None,
                metadata_json=normalized.metadata_json,
                raw_payload_json=normalized.raw_payload_json,
                normalized_payload_json=normalized.normalized_payload_json,
            )
            self.session.add(event)
            self.session.flush()
        else:
            existing_metadata = dict(event.metadata_json or {})
            event.ingestion_job_id = ingestion_job_id or event.ingestion_job_id
            event.current_club_id = normalized.current_club_id
            event.competition_id = normalized.competition_id
            event.event_type = normalized.event_type
            event.source_type = normalized.source_type
            event.source_label = normalized.source_label
            event.external_event_id = normalized.external_event_id
            event.requires_admin_review = normalized.requires_admin_review
            event.title = normalized.title
            event.summary = normalized.summary
            event.severity = normalized.severity
            event.occurred_at = normalized.occurred_at
            event.metadata_json = {**existing_metadata, **normalized.metadata_json}
            event.raw_payload_json = normalized.raw_payload_json
            event.normalized_payload_json = normalized.normalized_payload_json
        if event.approval_status == RealWorldEventApprovalStatus.APPROVED.value:
            self._apply_event_effects(event, applied_at=now)
            self._publish_event_surfaces(event, actor=actor)
        return event

    def ingest_feed(self, payload: EventFeedIngestionRequest, *, actor: User | None = None) -> EventIngestionJob:
        source_type = self._normalize_source_type(payload.source_type)
        source_label = (payload.source_label or source_type).strip()
        if not source_label:
            raise RealWorldFootballEventValidationError("source_label is required")
        job = EventIngestionJob(
            source_type=source_type,
            source_label=source_label,
            status=EventIngestionJobStatus.RUNNING.value,
            submitted_by_user_id=actor.id if actor is not None else None,
            started_at=utcnow(),
            total_received=len(payload.events),
            summary_json={"event_type_counts": {}},
        )
        self.session.add(job)
        self.session.flush()
        type_counts: dict[str, int] = {}
        try:
            for event_payload in payload.events:
                normalized_payload = RealWorldFootballEventCreate(
                    event_type=event_payload.event_type,
                    player_id=event_payload.player_id,
                    occurred_at=event_payload.occurred_at,
                    source_type=source_type,
                    source_label=source_label,
                    external_event_id=event_payload.external_event_id,
                    title=event_payload.title,
                    summary=event_payload.summary,
                    severity=event_payload.severity,
                    current_club_id=event_payload.current_club_id,
                    competition_id=event_payload.competition_id,
                    requires_admin_review=event_payload.requires_admin_review,
                    metadata=event_payload.metadata,
                    raw_payload=event_payload.raw_payload,
                )
                try:
                    event = self.create_event(normalized_payload, actor=actor, ingestion_job_id=job.id)
                except Exception as exc:
                    job.failed_count += 1
                    job.processed_count += 1
                    job.error_message = str(exc)
                    continue
                job.success_count += 1
                job.processed_count += 1
                if event.approval_status == RealWorldEventApprovalStatus.PENDING_REVIEW.value:
                    job.pending_review_count += 1
                type_counts[event.event_type] = type_counts.get(event.event_type, 0) + 1
            job.completed_at = utcnow()
            job.summary_json = {"event_type_counts": type_counts}
            if job.success_count == 0 and job.failed_count > 0:
                job.status = EventIngestionJobStatus.FAILED.value
            elif job.failed_count > 0:
                job.status = EventIngestionJobStatus.COMPLETED_WITH_ERRORS.value
            else:
                job.status = EventIngestionJobStatus.COMPLETED.value
            self.session.flush()
            return job
        except Exception:
            job.completed_at = utcnow()
            job.status = EventIngestionJobStatus.FAILED.value
            self.session.flush()
            raise

    def review_event(
        self,
        event_id: str,
        *,
        actor: User,
        approve: bool,
        notes: str | None = None,
    ) -> RealWorldFootballEvent:
        event = self._get_event(event_id)
        now = utcnow()
        if approve:
            event.approval_status = RealWorldEventApprovalStatus.APPROVED.value
            event.approved_by_user_id = actor.id
            event.approved_at = now
            event.rejected_by_user_id = None
            event.rejected_at = None
            event.review_notes = notes
            self._apply_event_effects(event, applied_at=now)
            self._publish_event_surfaces(event, actor=actor)
        else:
            event.approval_status = RealWorldEventApprovalStatus.REJECTED.value
            event.rejected_by_user_id = actor.id
            event.rejected_at = now
            event.review_notes = notes
            self._retire_event_effects(event, retired_at=now, status=EffectRecordStatus.REVOKED.value)
        self.session.flush()
        return event

    def override_event_severity(
        self,
        event_id: str,
        *,
        actor: User,
        severity: float | None,
    ) -> RealWorldFootballEvent:
        event = self._get_event(event_id)
        event.effect_severity_override = None if severity is None else self._clamp_severity(severity)
        event.metadata_json = {**event.metadata_json, "last_severity_override_by_user_id": actor.id}
        if event.approval_status == RealWorldEventApprovalStatus.APPROVED.value:
            self._apply_event_effects(event, applied_at=utcnow())
            self._publish_event_surfaces(event, actor=actor)
        self.session.flush()
        return event

    def set_event_category_enabled(self, payload: EventCategoryToggle, *, actor: User) -> list[EventEffectRule]:
        event_type = self._normalize_event_type(payload.event_type)
        rules = self.list_rules(event_type=event_type)
        if not rules:
            raise RealWorldFootballEventValidationError(f"no rules exist for event type '{event_type}'")
        for rule in rules:
            rule.is_enabled = payload.is_enabled
            rule.config_json = {**rule.config_json, "last_updated_by_user_id": actor.id}
        self._reapply_existing_events(event_type)
        self.session.flush()
        return rules

    def upsert_effect_rule(self, payload: EventEffectRuleUpsert, *, actor: User) -> EventEffectRule:
        rule = self._upsert_effect_rule_entity(payload, reapply_existing=True)
        rule.config_json = {**rule.config_json, "last_updated_by_user_id": actor.id}
        self.session.flush()
        return rule

    def expire_effects(self, *, as_of: datetime | None = None) -> dict[str, int]:
        current = self._coerce_datetime(as_of or utcnow())
        expired_modifiers = list(
            self.session.scalars(
                select(PlayerFormModifier).where(
                    PlayerFormModifier.status == EffectRecordStatus.ACTIVE.value,
                    PlayerFormModifier.expires_at.is_not(None),
                    PlayerFormModifier.expires_at <= current,
                )
            )
        )
        expired_flags = list(
            self.session.scalars(
                select(TrendingPlayerFlag).where(
                    TrendingPlayerFlag.status == EffectRecordStatus.ACTIVE.value,
                    TrendingPlayerFlag.expires_at.is_not(None),
                    TrendingPlayerFlag.expires_at <= current,
                )
            )
        )
        expired_signals = list(
            self.session.scalars(
                select(PlayerDemandSignal).where(
                    PlayerDemandSignal.status == EffectRecordStatus.ACTIVE.value,
                    PlayerDemandSignal.expires_at.is_not(None),
                    PlayerDemandSignal.expires_at <= current,
                )
            )
        )
        for modifier in expired_modifiers:
            modifier.status = EffectRecordStatus.EXPIRED.value
            self._remove_card_buff_mirror(modifier)
        for flag in expired_flags:
            flag.status = EffectRecordStatus.EXPIRED.value
        for signal in expired_signals:
            signal.status = EffectRecordStatus.EXPIRED.value
            self._remove_market_signal_mirror(signal)
        self.session.flush()
        return {
            "expired_form_modifiers": len(expired_modifiers),
            "expired_trending_flags": len(expired_flags),
            "expired_demand_signals": len(expired_signals),
        }

    def get_player_impact(self, player_id: str, *, as_of: datetime | None = None) -> PlayerRealWorldImpact:
        self._get_player(player_id)
        current = self._coerce_datetime(as_of or utcnow())
        active_flags = tuple(
            self.session.scalars(
                select(TrendingPlayerFlag).where(
                    TrendingPlayerFlag.player_id == player_id,
                    TrendingPlayerFlag.status == EffectRecordStatus.ACTIVE.value,
                    or_(TrendingPlayerFlag.expires_at.is_(None), TrendingPlayerFlag.expires_at > current),
                ).order_by(TrendingPlayerFlag.priority.desc(), TrendingPlayerFlag.started_at.desc())
            )
        )
        active_form_modifiers = tuple(
            self.session.scalars(
                select(PlayerFormModifier).where(
                    PlayerFormModifier.player_id == player_id,
                    PlayerFormModifier.status == EffectRecordStatus.ACTIVE.value,
                    or_(PlayerFormModifier.expires_at.is_(None), PlayerFormModifier.expires_at > current),
                ).order_by(PlayerFormModifier.started_at.desc(), PlayerFormModifier.created_at.desc())
            )
        )
        active_demand_signals = tuple(
            self.session.scalars(
                select(PlayerDemandSignal).where(
                    PlayerDemandSignal.player_id == player_id,
                    PlayerDemandSignal.status == EffectRecordStatus.ACTIVE.value,
                    or_(PlayerDemandSignal.expires_at.is_(None), PlayerDemandSignal.expires_at > current),
                ).order_by(PlayerDemandSignal.started_at.desc(), PlayerDemandSignal.created_at.desc())
            )
        )
        active_flag_codes = tuple(dict.fromkeys(flag.flag_type for flag in active_flags))
        affected_card_ids = tuple(self._active_player_card_ids(player_id))
        return PlayerRealWorldImpact(
            player_id=player_id,
            active_flags=active_flags,
            active_form_modifiers=active_form_modifiers,
            active_demand_signals=active_demand_signals,
            active_flag_codes=active_flag_codes,
            affected_card_ids=affected_card_ids,
            recommendation_priority_delta=round(
                sum(signal.recommendation_priority_delta for signal in active_demand_signals)
                + sum(modifier.recommendation_effect_value for modifier in active_form_modifiers),
                4,
            ),
            market_buzz_score=round(sum(signal.market_buzz_score for signal in active_demand_signals), 4),
            gameplay_effect_total=round(sum(modifier.gameplay_effect_value for modifier in active_form_modifiers), 4),
            market_effect_total=round(sum(modifier.market_effect_value for modifier in active_form_modifiers), 4),
        )

    @staticmethod
    def _story_type_for_event(event_type: str) -> str:
        if event_type == "confirmed_transfer":
            return "transfer_news"
        if event_type == "major_trophy_win":
            return "major_club_event"
        if event_type == "transfer_rumor":
            return "transfer_rumor"
        if event_type == "injury":
            return "player_update"
        return "player_spotlight"

    def _publish_event_surfaces(self, event: RealWorldFootballEvent, *, actor: User | None) -> None:
        if event.approval_status != RealWorldEventApprovalStatus.APPROVED.value:
            return
        metadata = dict(event.metadata_json or {})
        player = self._get_player(event.player_id)
        if not metadata.get("story_feed_item_id"):
            story_item = StoryFeedService(self.session).publish(
                story_type=self._story_type_for_event(event.event_type),
                title=event.title,
                body=event.summary or event.title,
                subject_type="real_world_football_event",
                subject_id=event.id,
                country_code=metadata.get("country_code"),
                metadata_json={
                    "event_id": event.id,
                    "event_type": event.event_type,
                    "player_id": event.player_id,
                    "player_name": player.full_name,
                    "current_club_id": event.current_club_id,
                    "competition_id": event.competition_id,
                    "occurred_at": event.occurred_at.isoformat(),
                    "severity": event.effect_severity_override or event.severity,
                },
                featured=event.event_type in _CALENDAR_EVENT_TYPES or (event.effect_severity_override or event.severity) >= 1.5,
                published_by_user_id=actor.id if actor is not None else None,
            )
            metadata["story_feed_item_id"] = story_item.id
        if event.event_type in _CALENDAR_EVENT_TYPES and not metadata.get("calendar_event_id"):
            calendar_event = CalendarEngineService(self.session).upsert_sourced_event(
                event_key=f"football-event:{event.id}",
                title=event.title,
                description=event.summary or f"{player.full_name} generated a major football event.",
                source_type="real_world_football_event",
                source_id=event.id,
                starts_on=event.occurred_at.date(),
                ends_on=event.occurred_at.date(),
                family="global_football",
                status="live",
                metadata_json={
                    "event_id": event.id,
                    "event_type": event.event_type,
                    "player_id": event.player_id,
                    "player_name": player.full_name,
                    "current_club_id": event.current_club_id,
                    "story_feed_item_id": metadata.get("story_feed_item_id"),
                },
                actor=actor,
            )
            metadata["calendar_event_id"] = calendar_event.id
        event.metadata_json = metadata

    def _upsert_effect_rule_entity(self, payload: EventEffectRuleUpsert, *, reapply_existing: bool) -> EventEffectRule:
        event_type = self._normalize_event_type(payload.event_type)
        effect_type = self._normalize_effect_type(payload.effect_type)
        effect_code = self._normalize_slug(payload.effect_code)
        if not payload.label.strip():
            raise RealWorldFootballEventValidationError("rule label is required")
        rule = self.session.scalar(
            select(EventEffectRule).where(
                EventEffectRule.event_type == event_type,
                EventEffectRule.effect_type == effect_type,
                EventEffectRule.effect_code == effect_code,
            )
        )
        if rule is None:
            rule = EventEffectRule(
                event_type=event_type,
                effect_type=effect_type,
                effect_code=effect_code,
                label=payload.label.strip(),
                is_enabled=payload.is_enabled,
                approval_required=payload.approval_required,
                base_magnitude=payload.base_magnitude,
                duration_hours=max(payload.duration_hours, 0),
                priority=payload.priority,
                gameplay_enabled=payload.gameplay_enabled,
                market_enabled=payload.market_enabled,
                recommendation_enabled=payload.recommendation_enabled,
                config_json=dict(payload.config),
            )
            self.session.add(rule)
            self.session.flush()
        else:
            rule.label = payload.label.strip()
            rule.is_enabled = payload.is_enabled
            rule.approval_required = payload.approval_required
            rule.base_magnitude = payload.base_magnitude
            rule.duration_hours = max(payload.duration_hours, 0)
            rule.priority = payload.priority
            rule.gameplay_enabled = payload.gameplay_enabled
            rule.market_enabled = payload.market_enabled
            rule.recommendation_enabled = payload.recommendation_enabled
            rule.config_json = dict(payload.config)
        if reapply_existing:
            self._reapply_existing_events(event_type)
        return rule

    def _reapply_existing_events(self, event_type: str) -> None:
        current = utcnow()
        approved_events = list(
            self.session.scalars(
                select(RealWorldFootballEvent).where(
                    RealWorldFootballEvent.event_type == event_type,
                    RealWorldFootballEvent.approval_status == RealWorldEventApprovalStatus.APPROVED.value,
                )
            )
        )
        for event in approved_events:
            self._apply_event_effects(event, applied_at=current)
        self.expire_effects(as_of=current)

    def _apply_event_effects(self, event: RealWorldFootballEvent, *, applied_at: datetime) -> None:
        self._retire_event_effects(event, retired_at=applied_at, status=EffectRecordStatus.REVOKED.value)
        if event.approval_status != RealWorldEventApprovalStatus.APPROVED.value:
            return
        rules = self.list_rules(event_type=event.event_type, active_only=True)
        effective_severity = event.effect_severity_override if event.effect_severity_override is not None else event.severity
        applied_effect_count = 0
        for rule in rules:
            config = dict(rule.config_json or {})
            started_at = event.occurred_at
            expires_at = started_at + timedelta(hours=rule.duration_hours) if rule.duration_hours > 0 else None
            magnitude = round(rule.base_magnitude * self._clamp_severity(effective_severity), 4)
            if rule.effect_type == "form_modifier":
                modifier = PlayerFormModifier(
                    player_id=event.player_id,
                    event_id=event.id,
                    modifier_type=str(config.get("modifier_type", rule.effect_code)),
                    modifier_label=str(config.get("modifier_label", rule.label)),
                    modifier_score=magnitude,
                    gameplay_effect_value=round(magnitude * self._config_float(config, "gameplay_scale", default=1.0), 4),
                    market_effect_value=round(magnitude * self._config_float(config, "market_scale", default=0.0), 4),
                    recommendation_effect_value=round(magnitude * self._config_float(config, "recommendation_scale", default=0.0), 4),
                    visible_to_users=bool(config.get("visible_to_users", True)),
                    status=EffectRecordStatus.ACTIVE.value,
                    started_at=started_at,
                    expires_at=expires_at,
                    source=_ENGINE_SOURCE,
                    metadata_json={"event_type": event.event_type, "effect_code": rule.effect_code, "rule_id": rule.id},
                )
                self.session.add(modifier)
                self.session.flush()
                self._mirror_modifier_to_card_buffs(modifier, rule)
                applied_effect_count += 1
            elif rule.effect_type == "trending_flag":
                self.session.add(
                    TrendingPlayerFlag(
                        player_id=event.player_id,
                        event_id=event.id,
                        flag_type=str(config.get("flag_type", rule.effect_code)),
                        flag_label=str(config.get("flag_label", rule.label)),
                        trend_score=round(magnitude * self._config_float(config, "trend_scale", default=1.0), 4),
                        priority=int(round(self._config_float(config, "priority_base", default=0.0) + max(magnitude, 0.0))),
                        status=EffectRecordStatus.ACTIVE.value,
                        started_at=started_at,
                        expires_at=expires_at,
                        source=_ENGINE_SOURCE,
                        metadata_json={"event_type": event.event_type, "effect_code": rule.effect_code, "rule_id": rule.id},
                    )
                )
                applied_effect_count += 1
            elif rule.effect_type == "demand_signal":
                signal = PlayerDemandSignal(
                    player_id=event.player_id,
                    event_id=event.id,
                    signal_type=str(config.get("signal_type", rule.effect_code)),
                    signal_label=str(config.get("signal_label", rule.label)),
                    demand_score=magnitude,
                    scouting_interest_delta=round(magnitude * self._config_float(config, "scouting_scale", default=0.0), 4),
                    recommendation_priority_delta=round(magnitude * self._config_float(config, "recommendation_scale", default=0.0), 4),
                    market_buzz_score=round(magnitude * self._config_float(config, "market_buzz_scale", default=0.0), 4),
                    status=EffectRecordStatus.ACTIVE.value,
                    started_at=started_at,
                    expires_at=expires_at,
                    source=_ENGINE_SOURCE,
                    metadata_json={"event_type": event.event_type, "effect_code": rule.effect_code, "rule_id": rule.id},
                )
                self.session.add(signal)
                self.session.flush()
                self._mirror_demand_signal_to_market_signal(signal, rule)
                applied_effect_count += 1
        event.effects_applied_at = applied_at
        event.metadata_json = {**event.metadata_json, "applied_effect_count": applied_effect_count}
        self.session.flush()

    def _retire_event_effects(self, event: RealWorldFootballEvent, *, retired_at: datetime, status: str) -> None:
        active_modifiers = list(
            self.session.scalars(
                select(PlayerFormModifier).where(
                    PlayerFormModifier.event_id == event.id,
                    PlayerFormModifier.status == EffectRecordStatus.ACTIVE.value,
                )
            )
        )
        active_flags = list(
            self.session.scalars(
                select(TrendingPlayerFlag).where(
                    TrendingPlayerFlag.event_id == event.id,
                    TrendingPlayerFlag.status == EffectRecordStatus.ACTIVE.value,
                )
            )
        )
        active_signals = list(
            self.session.scalars(
                select(PlayerDemandSignal).where(
                    PlayerDemandSignal.event_id == event.id,
                    PlayerDemandSignal.status == EffectRecordStatus.ACTIVE.value,
                )
            )
        )
        for modifier in active_modifiers:
            modifier.status = status
            if modifier.expires_at is None or self._coerce_datetime(modifier.expires_at) > retired_at:
                modifier.expires_at = retired_at
            self._remove_card_buff_mirror(modifier)
        for flag in active_flags:
            flag.status = status
            if flag.expires_at is None or self._coerce_datetime(flag.expires_at) > retired_at:
                flag.expires_at = retired_at
        for signal in active_signals:
            signal.status = status
            if signal.expires_at is None or self._coerce_datetime(signal.expires_at) > retired_at:
                signal.expires_at = retired_at
            self._remove_market_signal_mirror(signal)
        self.session.flush()

    def _mirror_modifier_to_card_buffs(self, modifier: PlayerFormModifier, rule: EventEffectRule) -> None:
        if not rule.gameplay_enabled or modifier.gameplay_effect_value == 0:
            return
        for player_card_id in self._active_player_card_ids(modifier.player_id):
            self.session.add(
                PlayerCardFormBuff(
                    player_card_id=player_card_id,
                    buff_type=modifier.modifier_type,
                    buff_value=modifier.gameplay_effect_value,
                    started_at=modifier.started_at,
                    expires_at=modifier.expires_at,
                    source=self._modifier_mirror_source(modifier.id),
                    metadata_json={"player_form_modifier_id": modifier.id, "event_id": modifier.event_id},
                )
            )
        self.session.flush()

    def _mirror_demand_signal_to_market_signal(self, signal: PlayerDemandSignal, rule: EventEffectRule) -> None:
        if not rule.market_enabled:
            return
        score = round(max(signal.demand_score, 0.0) * self._config_float(rule.config_json or {}, "market_signal_scale", default=1.0), 4)
        if score <= 0:
            return
        existing = self.session.scalar(
            select(MarketSignal).where(
                MarketSignal.source_provider == _ENGINE_SOURCE,
                MarketSignal.provider_external_id == signal.id,
            )
        )
        if existing is None:
            self.session.add(
                MarketSignal(
                    source_provider=_ENGINE_SOURCE,
                    provider_external_id=signal.id,
                    player_id=signal.player_id,
                    signal_type=signal.signal_type,
                    score=score,
                    as_of=signal.started_at,
                    notes=signal.signal_label,
                )
            )
        else:
            existing.score = score
            existing.as_of = signal.started_at
            existing.notes = signal.signal_label
        self.session.flush()

    def _remove_card_buff_mirror(self, modifier: PlayerFormModifier) -> None:
        for buff in self.session.scalars(
            select(PlayerCardFormBuff).where(PlayerCardFormBuff.source == self._modifier_mirror_source(modifier.id))
        ):
            self.session.delete(buff)

    def _remove_market_signal_mirror(self, signal: PlayerDemandSignal) -> None:
        for market_signal in self.session.scalars(
            select(MarketSignal).where(
                MarketSignal.source_provider == _ENGINE_SOURCE,
                MarketSignal.provider_external_id == signal.id,
            )
        ):
            self.session.delete(market_signal)

    def _active_player_card_ids(self, player_id: str) -> list[str]:
        return list(
            self.session.scalars(
                select(PlayerCard.id).where(
                    PlayerCard.player_id == player_id,
                    PlayerCard.is_active.is_(True),
                )
            )
        )

    def _get_player(self, player_id: str) -> Player:
        player = self.session.get(Player, player_id)
        if player is None:
            raise RealWorldFootballEventValidationError(f"player '{player_id}' was not found")
        return player

    def _get_event(self, event_id: str) -> RealWorldFootballEvent:
        event = self.session.get(RealWorldFootballEvent, event_id)
        if event is None:
            raise RealWorldFootballEventNotFoundError(f"event '{event_id}' was not found")
        return event

    def _build_dedupe_key(
        self,
        *,
        source_type: str,
        source_label: str,
        external_event_id: str | None,
        player_id: str,
        event_type: str,
        occurred_at: datetime,
        title: str,
    ) -> str:
        raw_key = "|".join([source_type, source_label, external_event_id or "", player_id, event_type, occurred_at.isoformat(), title.lower()])
        return sha256(raw_key.encode("utf-8")).hexdigest()

    def _normalize_event_type(self, value: str) -> str:
        normalized = self._normalize_slug(value)
        if normalized not in _ALLOWED_EVENT_TYPES:
            raise RealWorldFootballEventValidationError(f"unsupported event_type '{value}'")
        return normalized

    def _normalize_source_type(self, value: str) -> str:
        normalized = self._normalize_slug(value)
        if normalized not in _ALLOWED_SOURCE_TYPES:
            raise RealWorldFootballEventValidationError(f"unsupported source_type '{value}'")
        return normalized

    def _normalize_effect_type(self, value: str) -> str:
        normalized = self._normalize_slug(value)
        if normalized not in {"form_modifier", "trending_flag", "demand_signal"}:
            raise RealWorldFootballEventValidationError("effect_type must be form_modifier, trending_flag, or demand_signal")
        return normalized

    def _normalize_slug(self, value: str) -> str:
        normalized = _NORMALIZE_PATTERN.sub("_", value.strip().lower()).strip("_")
        if not normalized:
            raise RealWorldFootballEventValidationError("value cannot be empty")
        return normalized

    def _coerce_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _clamp_severity(self, value: float) -> float:
        if value < 0 or value > 3:
            raise RealWorldFootballEventValidationError("severity must be between 0 and 3")
        return round(float(value), 4)

    def _config_float(self, config: dict[str, Any], key: str, *, default: float) -> float:
        raw = config.get(key, default)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return float(default)

    def _modifier_mirror_source(self, modifier_id: str) -> str:
        return f"rwe:{modifier_id}"
