from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.admin_engine.schemas import (
    AdminCalendarRuleUpsertRequest,
    AdminCalendarRuleView,
    AdminFeatureFlagUpsertRequest,
    AdminFeatureFlagView,
    AdminRewardRuleUpsertRequest,
    AdminRewardRuleView,
    CompetitionScheduleBootstrapView,
    CompetitionSchedulePreviewRequest,
    CompetitionSchedulePreviewResponse,
)
from backend.app.admin_engine.service import AdminEngineService
from backend.app.auth.dependencies import get_current_admin, get_session
from backend.app.models.user import User

router = APIRouter(prefix="/admin-engine", tags=["admin-engine"])
admin_router = APIRouter(prefix="/admin/admin-engine", tags=["admin-admin-engine"])


def _map_feature_flag(item) -> AdminFeatureFlagView:
    return AdminFeatureFlagView.model_validate(item, from_attributes=True)


def _map_calendar_rule(item) -> AdminCalendarRuleView:
    return AdminCalendarRuleView.model_validate(item, from_attributes=True)


def _map_reward_rule(item) -> AdminRewardRuleView:
    return AdminRewardRuleView.model_validate(item, from_attributes=True)


@router.get("/bootstrap", response_model=CompetitionScheduleBootstrapView)
def get_admin_engine_bootstrap(session: Session = Depends(get_session)) -> CompetitionScheduleBootstrapView:
    service = AdminEngineService(session)
    return CompetitionScheduleBootstrapView(
        active_feature_flags=[_map_feature_flag(item) for item in service.list_feature_flags(active_only=True)],
        active_calendar_rules=[_map_calendar_rule(item) for item in service.list_calendar_rules(active_only=True)],
        active_reward_rules=[_map_reward_rule(item) for item in service.list_reward_rules(active_only=True)],
    )


@admin_router.get("/feature-flags", response_model=list[AdminFeatureFlagView])
def list_feature_flags(_: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> list[AdminFeatureFlagView]:
    service = AdminEngineService(session)
    return [_map_feature_flag(item) for item in service.list_feature_flags()]


@admin_router.post("/feature-flags", response_model=AdminFeatureFlagView)
def upsert_feature_flag(
    payload: AdminFeatureFlagUpsertRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AdminFeatureFlagView:
    service = AdminEngineService(session)
    item = service.upsert_feature_flag(actor=actor, payload=payload)
    session.commit()
    session.refresh(item)
    return _map_feature_flag(item)


@admin_router.get("/calendar-rules", response_model=list[AdminCalendarRuleView])
def list_calendar_rules(_: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> list[AdminCalendarRuleView]:
    service = AdminEngineService(session)
    return [_map_calendar_rule(item) for item in service.list_calendar_rules()]


@admin_router.post("/calendar-rules", response_model=AdminCalendarRuleView)
def upsert_calendar_rule(
    payload: AdminCalendarRuleUpsertRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AdminCalendarRuleView:
    service = AdminEngineService(session)
    item = service.upsert_calendar_rule(actor=actor, payload=payload)
    session.commit()
    session.refresh(item)
    return _map_calendar_rule(item)


@admin_router.get("/reward-rules", response_model=list[AdminRewardRuleView])
def list_reward_rules(_: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> list[AdminRewardRuleView]:
    service = AdminEngineService(session)
    return [_map_reward_rule(item) for item in service.list_reward_rules()]


@admin_router.post("/reward-rules", response_model=AdminRewardRuleView)
def upsert_reward_rule(
    payload: AdminRewardRuleUpsertRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AdminRewardRuleView:
    service = AdminEngineService(session)
    item = service.upsert_reward_rule(actor=actor, payload=payload)
    session.commit()
    session.refresh(item)
    return _map_reward_rule(item)


@admin_router.post("/schedule-preview", response_model=CompetitionSchedulePreviewResponse)
def preview_schedule(
    payload: CompetitionSchedulePreviewRequest,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> CompetitionSchedulePreviewResponse:
    service = AdminEngineService(session)
    active_rule_keys = [item.rule_key for item in service.list_calendar_rules(active_only=True)]
    active_world_cup_exclusive = any(item.world_cup_exclusive for item in service.list_calendar_rules(active_only=True))
    plan = service.schedule_preview(tuple(payload.requests))
    return CompetitionSchedulePreviewResponse(
        applied_rule_keys=active_rule_keys,
        world_cup_exclusive_rule_active=active_world_cup_exclusive,
        plan=plan,
    )
