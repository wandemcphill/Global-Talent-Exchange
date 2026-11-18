from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai_gateway.config import SAFE_MESSAGES
from app.ai_gateway.features import (
    announcement,
    competition_summary,
    fraud_review,
    market_insight,
    match_report,
    moderation_review,
    ops_summary,
    public_payload,
    scouting_brief,
    youth_development,
)
from app.ai_gateway.legacy_bridge import iter_announcement
from app.ai_gateway.repository import AiSettingsRepository, overlay_from_session
from app.ai_gateway.schemas import (
    AiFeatureUpdate,
    AiLimitUpdate,
    AiProviderUpdate,
    AiPublicResponse,
    AiStatusView,
    AnnouncementRequest,
    CompetitionSummaryRequest,
    FraudReviewRequest,
    MarketInsightRequest,
    MatchReportRequest,
    ModerationRequest,
    OpsSummaryRequest,
    ScoutingBriefRequest,
    YouthDevelopmentRequest,
)
from app.ai_gateway.service import AiCallResult, GtexAiService
from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.models.user import User

user_router = APIRouter(prefix="/ai", tags=["ai"])
admin_router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])
router = APIRouter()


def get_ai_service() -> GtexAiService:
    return GtexAiService()


def _respond(result: AiCallResult) -> AiPublicResponse:
    if result.error_code == "rate_limited":
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limited", "message": SAFE_MESSAGES["rate_limited"]},
        )
    return AiPublicResponse.model_validate(public_payload(result))


async def reject_client_secrets(request: Request) -> None:
    if request.method not in {"POST", "PUT", "PATCH"}:
        return
    try:
        body = await request.json()
    except Exception:
        return
    if not isinstance(body, dict):
        return
    blocked = {"api_key", "openai_api_key", "secret", "authorization", "access_token"}
    if any(str(key).lower() in blocked for key in body):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API credentials cannot be set from the dashboard.",
        )


def _status_payload(service: GtexAiService, session: Session) -> dict:
    payload = service.status()
    try:
        overlay = overlay_from_session(session)
    except Exception:
        overlay = None
    if overlay:
        if "admin_enabled" in overlay:
            payload["admin_enabled"] = overlay["admin_enabled"]
        for key in (
            "model",
            "daily_budget_usd",
            "monthly_budget_usd",
            "max_input_tokens",
            "max_output_tokens",
            "user_requests_per_minute",
            "global_requests_per_minute",
        ):
            if overlay.get(key) is not None:
                payload[key] = overlay[key]
        features = overlay.get("features")
        if features:
            payload["features"] = [
                {
                    "feature_key": feature.feature_key,
                    "enabled": feature.enabled,
                    "audience": feature.audience,
                    "complexity": feature.complexity,
                    "model": feature.model,
                    "max_requests_per_day": feature.max_requests_per_day,
                    "max_output_tokens": feature.max_output_tokens,
                    "cache_ttl_seconds": feature.cache_ttl_seconds,
                }
                for feature in features.values()
            ]
        payload["effective_enabled"] = bool(
            payload["environment_enabled"] and payload["admin_enabled"] and not payload["config_errors"]
        )
        if payload["config_errors"]:
            payload["integration_status"] = "misconfigured"
        elif not payload["effective_enabled"]:
            payload["integration_status"] = "disabled"
        elif not payload["api_key_configured"]:
            payload["integration_status"] = "missing_api_key"
        else:
            payload["integration_status"] = "ready"
    try:
        payload["limits"] = AiSettingsRepository(session).list_limits()
    except Exception:
        payload["limits"] = []
    return payload


@user_router.post("/recommendations/match-report", response_model=AiPublicResponse)
def post_match_report(
    payload: MatchReportRequest,
    current_user: User = Depends(get_current_user),
    service: GtexAiService = Depends(get_ai_service),
) -> AiPublicResponse:
    return _respond(match_report(service, payload, current_user.id))


@user_router.post("/recommendations/scouting-brief", response_model=AiPublicResponse)
def post_scouting_brief(
    payload: ScoutingBriefRequest,
    current_user: User = Depends(get_current_user),
    service: GtexAiService = Depends(get_ai_service),
) -> AiPublicResponse:
    return _respond(scouting_brief(service, payload, current_user.id))


@user_router.post("/recommendations/competition-summary", response_model=AiPublicResponse)
def post_competition_summary(
    payload: CompetitionSummaryRequest,
    current_user: User = Depends(get_current_user),
    service: GtexAiService = Depends(get_ai_service),
) -> AiPublicResponse:
    return _respond(competition_summary(service, payload, current_user.id))


@user_router.post("/recommendations/youth-development", response_model=AiPublicResponse)
def post_youth_development(
    payload: YouthDevelopmentRequest,
    current_user: User = Depends(get_current_user),
    service: GtexAiService = Depends(get_ai_service),
) -> AiPublicResponse:
    return _respond(youth_development(service, payload, current_user.id))


@user_router.post("/recommendations/announcement", response_model=AiPublicResponse)
def post_announcement(
    payload: AnnouncementRequest,
    current_user: User = Depends(get_current_user),
    service: GtexAiService = Depends(get_ai_service),
) -> AiPublicResponse:
    return _respond(announcement(service, payload, current_user.id))


@user_router.post("/recommendations/announcement/stream")
def post_announcement_stream(
    payload: AnnouncementRequest,
    current_user: User = Depends(get_current_user),
    service: GtexAiService = Depends(get_ai_service),
) -> StreamingResponse:
    return StreamingResponse(
        iter_announcement(
            service,
            club_name=payload.club_name,
            purpose=payload.purpose,
            facts=payload.facts,
            user_id=current_user.id,
        ),
        media_type="text/plain",
    )


@admin_router.get("/status", response_model=AiStatusView)
def get_ai_status(
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    service: GtexAiService = Depends(get_ai_service),
) -> AiStatusView:
    return AiStatusView.model_validate(_status_payload(service, session))


@admin_router.put("/settings", response_model=AiStatusView, dependencies=[Depends(reject_client_secrets)])
def put_ai_settings(
    payload: AiProviderUpdate,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    service: GtexAiService = Depends(get_ai_service),
) -> AiStatusView:
    _reject_secret_model(payload.model)
    if payload.monthly_budget_usd < payload.daily_budget_usd:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Monthly budget must cover the daily budget.")
    AiSettingsRepository(session).upsert_provider(
        {
            "enabled": payload.enabled,
            "model": payload.model,
            "daily_budget_usd": payload.daily_budget_usd,
            "monthly_budget_usd": payload.monthly_budget_usd,
            "max_input_tokens": payload.max_input_tokens,
            "max_output_tokens": payload.max_output_tokens,
            "user_requests_per_minute": payload.user_requests_per_minute,
            "global_requests_per_minute": payload.global_requests_per_minute,
        },
        current_user.id,
    )
    session.commit()
    return AiStatusView.model_validate(_status_payload(service, session))


@admin_router.put("/features/{feature_key}", response_model=AiStatusView, dependencies=[Depends(reject_client_secrets)])
def put_ai_feature(
    feature_key: str,
    payload: AiFeatureUpdate,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    service: GtexAiService = Depends(get_ai_service),
) -> AiStatusView:
    _reject_secret_model(payload.model_override)
    try:
        AiSettingsRepository(session).upsert_feature(
            feature_key,
            {
                "enabled": payload.enabled,
                "model_override": payload.model_override,
                "max_requests_per_day": payload.max_requests_per_day,
                "max_output_tokens": payload.max_output_tokens,
                "cache_ttl_seconds": payload.cache_ttl_seconds,
            },
            current_user.id,
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown AI feature.") from None
    session.commit()
    return AiStatusView.model_validate(_status_payload(service, session))


@admin_router.put("/limits", response_model=AiStatusView, dependencies=[Depends(reject_client_secrets)])
def put_ai_limit(
    payload: AiLimitUpdate,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    service: GtexAiService = Depends(get_ai_service),
) -> AiStatusView:
    if payload.subject_key.lower().startswith("sk-"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That limit key is not allowed.")
    if payload.subject_type == "global" and payload.subject_key != "requests":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The global limit key must be requests.")
    AiSettingsRepository(session).upsert_limit(payload.model_dump(), current_user.id)
    session.commit()
    return AiStatusView.model_validate(_status_payload(service, session))


@admin_router.post("/moderation", response_model=AiPublicResponse)
def post_moderation(
    payload: ModerationRequest,
    current_user: User = Depends(get_current_admin),
    service: GtexAiService = Depends(get_ai_service),
) -> AiPublicResponse:
    return _respond(moderation_review(service, payload, current_user.id))


@admin_router.post("/ops-summary", response_model=AiPublicResponse)
def post_ops_summary(
    payload: OpsSummaryRequest,
    current_user: User = Depends(get_current_admin),
    service: GtexAiService = Depends(get_ai_service),
) -> AiPublicResponse:
    return _respond(ops_summary(service, payload, current_user.id))


@admin_router.post("/market-insight", response_model=AiPublicResponse)
def post_market_insight(
    payload: MarketInsightRequest,
    current_user: User = Depends(get_current_admin),
    service: GtexAiService = Depends(get_ai_service),
) -> AiPublicResponse:
    return _respond(market_insight(service, payload, current_user.id))


@admin_router.post("/fraud-review", response_model=AiPublicResponse)
def post_fraud_review(
    payload: FraudReviewRequest,
    current_user: User = Depends(get_current_admin),
    service: GtexAiService = Depends(get_ai_service),
) -> AiPublicResponse:
    return _respond(fraud_review(service, payload, current_user.id))


def _reject_secret_model(model: str | None) -> None:
    if model and model.lower().startswith(("sk-", "rk-")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Model name is not valid.")


router.include_router(user_router)
router.include_router(admin_router)
