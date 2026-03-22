from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.models.user import User

from .schemas import (
    AdminRoleCatalogUpdate,
    AdminRoleCatalogView,
    AuditEventView,
    AuditQueryView,
    CommissionSettingsUpdate,
    CommissionSettingsView,
    CompetitionControlUpdate,
    CompetitionControlView,
    GodModeBootstrapView,
    HighRiskActionView,
    LiquidityInterventionRequest,
    LiquidityInterventionView,
    PaymentRailHealthView,
    PaymentRailsPayload,
    PaymentRailsUpdate,
    TreasuryDashboardView,
    TreasurySummaryView,
    WithdrawalControlUpdate,
    WithdrawalControlView,
    TreasuryWithdrawalRequest,
    TreasuryWithdrawalView,
    WithdrawalAdminView,
    WithdrawalStatusUpdate,
    WithdrawalSummaryView,
)
from .service import AdminGodModeService, GodModeError, IntegrityBoundError, PermissionDeniedError
from app.wallets.service import InsufficientBalanceError, WalletService

router = APIRouter(prefix="/api/admin/god-mode", tags=["admin-god-mode"])


def get_service(request: Request) -> AdminGodModeService:
    publisher = request.app.state.event_publisher if hasattr(request.app.state, "event_publisher") else None
    return AdminGodModeService(wallet_service=WalletService(event_publisher=publisher))


@router.get("/bootstrap", response_model=GodModeBootstrapView)
def read_bootstrap(
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> GodModeBootstrapView:
    return service.load_bootstrap(request.app, session, actor)


@router.get("/roles", response_model=AdminRoleCatalogView)
def read_roles(
    request: Request,
    _: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> AdminRoleCatalogView:
    return service.get_role_catalog(request.app)


@router.put("/roles", response_model=AdminRoleCatalogView)
def update_roles(
    payload: AdminRoleCatalogUpdate,
    request: Request,
    actor: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> AdminRoleCatalogView:
    try:
        return service.update_role_catalog(request.app, actor, payload)
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc




@router.get("/audit-events", response_model=list[AuditEventView])
def read_audit_events(
    request: Request,
    query: str | None = None,
    event_type: str | None = None,
    limit: int = 30,
    _: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> list[AuditEventView]:
    return service.list_audit_events(request.app, limit=limit, query=query, event_type=event_type)


@router.get("/withdrawals/summary", response_model=WithdrawalSummaryView)
def read_withdrawal_summary(
    request: Request,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> WithdrawalSummaryView:
    return service.get_withdrawal_summary(request.app, session)


@router.get("/payment-rails/health", response_model=PaymentRailHealthView)
def read_payment_rail_health(
    request: Request,
    _: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> PaymentRailHealthView:
    return service.get_payment_rail_health(request.app)


@router.get("/treasury/dashboard", response_model=TreasuryDashboardView)
def read_treasury_dashboard(
    request: Request,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> TreasuryDashboardView:
    return service.get_treasury_dashboard(request.app, session)


@router.get("/high-risk-actions", response_model=list[HighRiskActionView])
def read_high_risk_actions(
    request: Request,
    _: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> list[HighRiskActionView]:
    return service.list_high_risk_actions(request.app)

@router.get("/commissions", response_model=CommissionSettingsView)
def read_commissions(
    request: Request,
    _: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> CommissionSettingsView:
    return service.get_commissions(request.app)


@router.put("/commissions", response_model=CommissionSettingsView)
def update_commissions(
    payload: CommissionSettingsUpdate,
    request: Request,
    actor: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> CommissionSettingsView:
    try:
        return service.update_commissions(request.app, actor, payload)
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/payment-rails", response_model=PaymentRailsPayload)
def read_payment_rails(
    request: Request,
    _: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> PaymentRailsPayload:
    return service.get_payment_rails(request.app)


@router.put("/payment-rails", response_model=PaymentRailsPayload)
def update_payment_rails(
    payload: PaymentRailsUpdate,
    request: Request,
    actor: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> PaymentRailsPayload:
    try:
        return service.update_payment_rails(request.app, actor, payload)
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/withdrawal-controls", response_model=WithdrawalControlView)
def read_withdrawal_controls(
    request: Request,
    _: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> WithdrawalControlView:
    return service.get_withdrawal_controls(request.app)


@router.put("/withdrawal-controls", response_model=WithdrawalControlView)
def update_withdrawal_controls(
    payload: WithdrawalControlUpdate,
    request: Request,
    actor: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> WithdrawalControlView:
    try:
        return service.update_withdrawal_controls(request.app, actor, payload)
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/competition-controls", response_model=CompetitionControlView)
def read_competition_controls(
    request: Request,
    _: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> CompetitionControlView:
    return service.get_competition_controls(request.app)


@router.put("/competition-controls", response_model=CompetitionControlView)
def update_competition_controls(
    payload: CompetitionControlUpdate,
    request: Request,
    actor: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> CompetitionControlView:
    try:
        return service.update_competition_controls(request.app, actor, payload)
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/treasury", response_model=TreasurySummaryView)
def read_treasury(
    request: Request,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> TreasurySummaryView:
    return service.get_treasury_summary(request.app, session)


@router.post("/liquidity/interventions", response_model=LiquidityInterventionView, status_code=status.HTTP_201_CREATED)
def create_liquidity_intervention(
    payload: LiquidityInterventionRequest,
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> LiquidityInterventionView:
    try:
        view = service.execute_liquidity_intervention(request.app, session, actor, payload)
        session.commit()
        return view
    except PermissionDeniedError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except IntegrityBoundError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (GodModeError, InsufficientBalanceError) as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/withdrawals", response_model=list[WithdrawalAdminView])
def list_withdrawals(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> list[WithdrawalAdminView]:
    return service.list_withdrawals(session)


@router.patch("/withdrawals/{payout_request_id}", response_model=WithdrawalAdminView)
def update_withdrawal(
    payout_request_id: str,
    payload: WithdrawalStatusUpdate,
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> WithdrawalAdminView:
    try:
        view = service.update_withdrawal_status(request.app, session, actor, payout_request_id, payload)
        session.commit()
        return view
    except PermissionDeniedError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except GodModeError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/treasury/withdrawals", response_model=TreasuryWithdrawalView, status_code=status.HTTP_201_CREATED)
def create_treasury_withdrawal(
    payload: TreasuryWithdrawalRequest,
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
    service: AdminGodModeService = Depends(get_service),
) -> TreasuryWithdrawalView:
    try:
        view = service.create_treasury_withdrawal(request.app, session, actor, payload)
        session.commit()
        return view
    except PermissionDeniedError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (GodModeError, InsufficientBalanceError) as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
