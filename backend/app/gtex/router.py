from __future__ import annotations

from typing import Never

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_admin,
    get_current_match_user,
    get_current_trading_user,
    get_current_wallet_user,
    get_optional_current_user,
    get_session,
)
from app.gtex.runtime import apply_gtex_runtime_settings, ensure_gtex_runtime
from app.gtex.schemas import (
    AdminBanUserRequest,
    AdminBanUserView,
    AdminFlagView,
    AiLeaguesView,
    AiLeagueView,
    AiMatchView,
    CreatorPlayerView,
    CreatorTradeRequest,
    CreatorTradeView,
    JackpotContributionRequest,
    JackpotContributionView,
    JackpotAdminActionView,
    JackpotAdminBalanceUpdateRequest,
    JackpotAdminRuntimeUpdateRequest,
    JackpotAdminRuntimeView,
    JackpotHistoryItemView,
    JackpotPayoutView,
    JackpotStateView,
    MarketTrendingView,
    MatchFindRequest,
    MatchFindResponse,
)
from app.gtex.service import GtexConflictError, GtexError, GtexNotFoundError, GtexValidationError
from app.models.gtex_economy import GtexRiskFlag, GtexRiskFlagStatus
from app.models.risk_ops import RiskActionType
from app.models.user import User
from app.risk_ops_engine.service import RiskOpsService

router = APIRouter(tags=["gtex"])


def get_runtime(request: Request):
    return ensure_gtex_runtime(request.app)


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("cf-connecting-ip")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or None
    if request.client is not None and request.client.host:
        return str(request.client.host)
    return None


def raise_gtex_http_exception(exc: GtexError) -> Never:
    if isinstance(exc, GtexNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, GtexConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, GtexValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/jackpot/state", response_model=JackpotStateView)
def get_jackpot_state(
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> JackpotStateView:
    return JackpotStateView.model_validate(runtime.jackpot.get_state(session))


@router.post("/jackpot/contribute", response_model=JackpotContributionView, status_code=status.HTTP_201_CREATED)
def create_jackpot_contribution(
    payload: JackpotContributionRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_wallet_user),
    runtime=Depends(get_runtime),
) -> JackpotContributionView:
    try:
        contribution = runtime.jackpot.contribute_from_wallet(
            session,
            actor=current_user,
            source_type=payload.source_type,
            source_id=payload.source_id,
            entry_fee=payload.entry_fee,
            contribution_amount=payload.contribution_amount,
            eligibility_score=payload.eligibility_score,
            metadata=payload.metadata,
        )
        session.commit()
    except GtexError as exc:
        session.rollback()
        raise_gtex_http_exception(exc)
    return JackpotContributionView.model_validate(contribution)


@router.get("/admin/jackpot/runtime", response_model=JackpotAdminRuntimeView)
def get_admin_jackpot_runtime(
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> JackpotAdminRuntimeView:
    del _
    return JackpotAdminRuntimeView.model_validate(runtime.jackpot.get_runtime_state(session))


@router.post("/admin/jackpot/runtime", response_model=JackpotAdminRuntimeView)
def update_admin_jackpot_runtime(
    payload: JackpotAdminRuntimeUpdateRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> JackpotAdminRuntimeView:
    try:
        updated_settings = runtime.jackpot.apply_runtime_settings(
            session,
            threshold_amount=payload.threshold_amount,
            probability_limit=payload.probability_limit,
            probability_cap=payload.probability_cap,
            failsafe_hours=payload.failsafe_hours,
            contribution_rate=payload.contribution_rate,
            distribution_mode=payload.distribution_mode,
            top_split_percent=payload.top_split_percent,
            min_activity_score=payload.min_activity_score,
        )
        apply_gtex_runtime_settings(runtime, updated_settings)
        runtime.jackpot._audit_log(
            session,
            actor_user_id=current_admin.id,
            action_key="gtex.jackpot.runtime.updated",
            resource_type="gtex_jackpot",
            resource_id="global",
            detail="Admin updated the live GTEX jackpot runtime settings.",
            metadata_json=payload.model_dump(mode="json"),
        )
        session.commit()
    except GtexError as exc:
        session.rollback()
        raise_gtex_http_exception(exc)
    return JackpotAdminRuntimeView.model_validate(runtime.jackpot.get_runtime_state(session))


@router.patch("/admin/jackpot/balance", response_model=JackpotAdminRuntimeView)
def update_admin_jackpot_balance(
    payload: JackpotAdminBalanceUpdateRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> JackpotAdminRuntimeView:
    try:
        runtime.jackpot.set_current_balance(
            session,
            balance=payload.balance,
            actor=current_admin,
            reason=payload.reason,
        )
        session.commit()
    except GtexError as exc:
        session.rollback()
        raise_gtex_http_exception(exc)
    return JackpotAdminRuntimeView.model_validate(runtime.jackpot.get_runtime_state(session))


@router.post("/admin/jackpot/trigger", response_model=JackpotAdminActionView)
def trigger_admin_jackpot_round(
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> JackpotAdminActionView:
    try:
        result = runtime.jackpot.manual_trigger(session)
        runtime.jackpot._audit_log(
            session,
            actor_user_id=current_admin.id,
            action_key="gtex.jackpot.manual_trigger",
            resource_type="gtex_jackpot",
            resource_id=result["triggered_round_id"],
            detail="Admin manually triggered the current GTEX jackpot round.",
            metadata_json=result,
        )
        session.commit()
    except GtexError as exc:
        session.rollback()
        raise_gtex_http_exception(exc)
    return JackpotAdminActionView.model_validate(result)


@router.get("/jackpot/history", response_model=list[JackpotHistoryItemView])
def get_jackpot_history(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> list[JackpotHistoryItemView]:
    items = []
    for round_record in runtime.jackpot.list_history(session, limit=limit):
        items.append(
            JackpotHistoryItemView(
                id=round_record.id,
                round_number=round_record.round_number,
                status=round_record.status.value,
                distribution_mode=round_record.distribution_mode.value,
                trigger_mode=round_record.trigger_mode.value if round_record.trigger_mode else None,
                current_balance=round_record.current_balance,
                winning_user_id=round_record.winning_user_id,
                triggered_at=round_record.triggered_at,
                settled_at=round_record.settled_at,
                payouts=[
                    JackpotPayoutView.model_validate(payout)
                    for payout in sorted(round_record.payouts, key=lambda item: item.rank)
                ],
            )
        )
    return items


@router.get("/players/{player_id}", response_model=CreatorPlayerView)
def get_creator_player(
    player_id: str,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
    runtime=Depends(get_runtime),
) -> CreatorPlayerView:
    try:
        return CreatorPlayerView.model_validate(
            runtime.creator_market.get_view(session, player_id=player_id, viewer=current_user)
        )
    except GtexError as exc:
        raise_gtex_http_exception(exc)


@router.post("/gtex/market/buy", response_model=CreatorTradeView, status_code=status.HTTP_201_CREATED)
def buy_creator_shares(
    payload: CreatorTradeRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trading_user),
    runtime=Depends(get_runtime),
) -> CreatorTradeView:
    try:
        trade = runtime.creator_market.buy_shares(
            session,
            buyer=current_user,
            player_id=payload.player_id,
            shares=payload.shares,
            client_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        session.commit()
    except GtexError as exc:
        session.rollback()
        raise_gtex_http_exception(exc)
    return CreatorTradeView.model_validate(trade)


@router.post("/gtex/market/sell", response_model=CreatorTradeView, status_code=status.HTTP_201_CREATED)
def sell_creator_shares(
    payload: CreatorTradeRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trading_user),
    runtime=Depends(get_runtime),
) -> CreatorTradeView:
    try:
        trade = runtime.creator_market.sell_shares(
            session,
            seller=current_user,
            player_id=payload.player_id,
            shares=payload.shares,
            client_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        session.commit()
    except GtexError as exc:
        session.rollback()
        raise_gtex_http_exception(exc)
    return CreatorTradeView.model_validate(trade)


@router.get("/market/trending", response_model=MarketTrendingView)
def get_market_trending(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
    runtime=Depends(get_runtime),
) -> MarketTrendingView:
    return MarketTrendingView(
        items=[
            CreatorPlayerView.model_validate(item)
            for item in runtime.creator_market.list_trending(session, limit=limit, viewer=current_user)
        ]
    )


@router.get("/admin/flags", response_model=list[AdminFlagView])
def list_admin_flags(
    limit: int = Query(default=100, ge=1, le=500),
    user_id: str | None = Query(default=None),
    status_filter: GtexRiskFlagStatus | None = Query(default=None, alias="status"),
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[AdminFlagView]:
    del _
    stmt = select(GtexRiskFlag)
    if user_id:
        stmt = stmt.where(GtexRiskFlag.subject_key == f"user:{user_id}")
    if status_filter is not None:
        stmt = stmt.where(GtexRiskFlag.status == status_filter)
    else:
        stmt = stmt.where(GtexRiskFlag.status.in_((GtexRiskFlagStatus.OPEN, GtexRiskFlagStatus.REVIEWING)))
    items = session.scalars(
        stmt.order_by(GtexRiskFlag.created_at.desc(), GtexRiskFlag.updated_at.desc()).limit(limit)
    ).all()
    payload: list[AdminFlagView] = []
    for item in items:
        extracted_user_id = item.subject_key.split(":", 1)[1] if item.subject_key.startswith("user:") else None
        payload.append(
            AdminFlagView(
                id=item.id,
                category=item.category,
                subject_key=item.subject_key,
                user_id=extracted_user_id,
                reference_id=item.reference_id,
                severity=item.severity,
                signal_score=item.signal_score,
                status=item.status.value if hasattr(item.status, "value") else str(item.status),
                detail=item.detail,
                metadata_json=dict(item.metadata_json or {}),
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )
    return payload


@router.post("/admin/ban-user", response_model=AdminBanUserView)
def ban_user_account(
    payload: AdminBanUserRequest,
    current_admin: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AdminBanUserView:
    user = session.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found.")

    risk_service = RiskOpsService(session)
    applied_actions: list[str] = []
    if payload.freeze_wallet:
        _, created = risk_service.create_action(
            actor_user_id=current_admin.id,
            user_id=user.id,
            action_type=RiskActionType.FREEZE_WALLET,
            reason=payload.reason,
            source_rule_key="admin_ban_user",
            metadata_json={"reason": payload.reason},
        )
        if created:
            applied_actions.append(RiskActionType.FREEZE_WALLET.value)
    if payload.block_trading:
        _, created = risk_service.create_action(
            actor_user_id=current_admin.id,
            user_id=user.id,
            action_type=RiskActionType.BLOCK_TRADING,
            reason=payload.reason,
            source_rule_key="admin_ban_user",
            metadata_json={"reason": payload.reason},
        )
        if created:
            applied_actions.append(RiskActionType.BLOCK_TRADING.value)
    if payload.block_withdrawals:
        _, created = risk_service.create_action(
            actor_user_id=current_admin.id,
            user_id=user.id,
            action_type=RiskActionType.BLOCK_WITHDRAWAL,
            reason=payload.reason,
            source_rule_key="admin_ban_user",
            metadata_json={"reason": payload.reason},
        )
        if created:
            applied_actions.append(RiskActionType.BLOCK_WITHDRAWAL.value)
    if payload.require_manual_review:
        _, created = risk_service.create_action(
            actor_user_id=current_admin.id,
            user_id=user.id,
            action_type=RiskActionType.MANUAL_REVIEW,
            reason=payload.reason,
            source_rule_key="admin_ban_user",
            metadata_json={"reason": payload.reason},
        )
        if created:
            applied_actions.append(RiskActionType.MANUAL_REVIEW.value)
    if payload.deactivate_account:
        user.is_active = False

    risk_service.log_audit(
        actor_user_id=current_admin.id,
        action_key="admin.user.banned",
        resource_type="user",
        resource_id=user.id,
        detail="Admin banned a user account.",
        metadata_json={
            "reason": payload.reason,
            "deactivate_account": payload.deactivate_account,
            "freeze_wallet": payload.freeze_wallet,
            "block_trading": payload.block_trading,
            "block_withdrawals": payload.block_withdrawals,
            "require_manual_review": payload.require_manual_review,
            "actions_applied": applied_actions,
        },
    )
    session.commit()
    active_flag_count = int(
        session.scalar(
            select(func.count())
            .select_from(GtexRiskFlag)
            .where(
                GtexRiskFlag.subject_key == f"user:{user.id}",
                GtexRiskFlag.status.in_((GtexRiskFlagStatus.OPEN, GtexRiskFlagStatus.REVIEWING)),
            )
        )
        or 0
    )
    return AdminBanUserView(
        user_id=user.id,
        banned=not bool(user.is_active),
        reason=payload.reason,
        actions_applied=applied_actions,
        active_flag_count=active_flag_count,
    )


@router.post("/match/find", response_model=MatchFindResponse, status_code=status.HTTP_202_ACCEPTED)
def find_match(
    payload: MatchFindRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_match_user),
    runtime=Depends(get_runtime),
) -> MatchFindResponse:
    try:
        queue_entry = runtime.ai_leagues.queue_match_request(
            session,
            user=current_user,
            league_ref=payload.league_id,
            entry_fee=payload.entry_fee,
            metadata=payload.metadata,
        )
        session.commit()
    except GtexError as exc:
        session.rollback()
        raise_gtex_http_exception(exc)
    return MatchFindResponse(
        queue_entry_id=queue_entry.id,
        match_id=queue_entry.match_id,
        status=queue_entry.status.value,
        league_id=queue_entry.league_id,
        expires_at=queue_entry.expires_at,
    )


@router.get("/ai/leagues", response_model=AiLeaguesView)
def list_ai_leagues(
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> AiLeaguesView:
    leagues = [AiLeagueView.model_validate(item) for item in runtime.ai_leagues.list_leagues(session)]
    return AiLeaguesView(leagues=leagues)


@router.get("/ai/match/{match_id}", response_model=AiMatchView)
def get_ai_match(
    match_id: str,
    session: Session = Depends(get_session),
    runtime=Depends(get_runtime),
) -> AiMatchView:
    try:
        return AiMatchView.model_validate(runtime.ai_leagues.get_match_view(session, match_id=match_id))
    except GtexError as exc:
        raise_gtex_http_exception(exc)
