from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user
from app.db import get_session
from app.models.risk_ops import AuditLog
from app.models.user import User, UserRole
from app.tournaments.schemas import (
    TournamentCreateRequest,
    TournamentJoinRequest,
    TournamentListView,
    TournamentMatchResultRequest,
    TournamentView,
    LegacyTournamentRefundExecuteRequest,
)
from app.tournaments.retirement import (
    LegacyTournamentNotFound,
    build_legacy_tournament_refund_report,
    execute_legacy_tournament_refunds,
)
from app.wallets.service import LedgerError
from app.tournaments.service import (
    TournamentError,
    TournamentNotFoundError,
    TournamentService,
    TournamentValidationError,
)

router = APIRouter(prefix="/api/tournaments", tags=["tournaments"])

LEGACY_RETIREMENT_DETAIL = (
    "The legacy /api/tournaments engine is retired. Use the hosted-competition engine. "
    "Administrators can reconcile historical entry fees through "
    "/api/tournaments/admin/retirement/refunds/dry-run."
)


def _legacy_engine_retired() -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=LEGACY_RETIREMENT_DETAIL,
        headers={"Deprecation": "true"},
    )


def _service(session: Session = Depends(get_session)) -> TournamentService:
    return TournamentService(session=session)


def _raise_http(exc: TournamentError) -> None:
    if isinstance(exc, TournamentNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    if isinstance(exc, TournamentValidationError):
        if exc.reason in {"not_a_participant", "actor_not_participant"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.detail) from exc
        conflict_reasons = {
            "immutable_tournament",
            "insufficient_balance",
            "operation_busy",
            "registration_closed",
            "round_locked",
            "round_not_ready",
            "tournament_full",
        }
        status_code = status.HTTP_409_CONFLICT if exc.reason in conflict_reasons else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=exc.detail) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


@router.get("", response_model=TournamentListView)
def list_tournaments(
    session: Session = Depends(get_session),
    service: TournamentService = Depends(_service),
) -> TournamentListView:
    try:
        tournaments = service.list_tournaments()
        session.commit()
    except TournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return TournamentListView(tournaments=[TournamentView.model_validate(item) for item in tournaments])


@router.post(
    "",
    response_model=TournamentView,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
    responses={410: {"description": "Legacy tournament engine retired"}},
)
def create_tournament(
    payload: TournamentCreateRequest,
    current_user: User = Depends(get_current_user),
) -> TournamentView:
    del payload
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators may create platform tournaments.",
        )
    _legacy_engine_retired()


@router.post(
    "/{tournament_id}/cancel",
    response_model=TournamentView,
    deprecated=True,
    responses={410: {"description": "Legacy tournament engine retired"}},
)
def cancel_tournament(
    tournament_id: str,
    current_user: User = Depends(get_current_user),
) -> TournamentView:
    del tournament_id
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators may cancel platform tournaments.",
        )
    _legacy_engine_retired()



@router.get("/admin/retirement/refunds/dry-run")
def dry_run_legacy_tournament_refunds(
    tournament_id: str | None = None,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> dict:
    del current_user
    try:
        return build_legacy_tournament_refund_report(session, tournament_id=tournament_id)
    except LegacyTournamentNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found.") from exc


@router.post("/admin/retirement/refunds/execute")
def execute_legacy_tournament_refund_batch(
    payload: LegacyTournamentRefundExecuteRequest,
    current_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> dict:
    if payload.confirmation != "REFUND_LEGACY_TOURNAMENT_FEES":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Explicit refund confirmation is required.")

    try:
        result = execute_legacy_tournament_refunds(
            session,
            actor=current_user,
            tournament_id=payload.tournament_id,
            reason=payload.reason.strip(),
        )
    except LegacyTournamentNotFound as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found.") from exc
    except LedgerError as exc:
        session.rollback()
        try:
            report = build_legacy_tournament_refund_report(session, tournament_id=payload.tournament_id)
        except LegacyTournamentNotFound:
            report = {"tournament_id": payload.tournament_id, "status": "blocked"}
        session.add(
            AuditLog(
                actor_user_id=current_user.id,
                action_key="legacy_tournament.refund_batch",
                resource_type="tournament",
                resource_id=payload.tournament_id,
                outcome="blocked",
                detail="Legacy tournament refund batch stopped; no changes were committed.",
                metadata_json={
                    "reason": payload.reason.strip(),
                    "failure": str(exc)[:500],
                    "report_summary": report.get("summary", {}),
                },
            )
        )
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "blocked",
                "mutation_performed": False,
                "message": "Refund batch stopped safely; no changes were committed.",
                "failure": str(exc)[:500],
                "report": report,
            },
        ) from exc

    if result["status"] == "blocked":
        session.add(
            AuditLog(
                actor_user_id=current_user.id,
                action_key="legacy_tournament.refund_batch",
                resource_type="tournament",
                resource_id=payload.tournament_id,
                outcome="blocked",
                detail="Legacy tournament refund batch blocked by reconciliation; no refunds were issued.",
                metadata_json={
                    "reason": payload.reason.strip(),
                    "report_summary": result.get("summary", {}),
                    "blockers": [
                        {
                            "entry_id": item.get("entry_id"),
                            "status": item.get("status"),
                            "reason": item.get("reason"),
                        }
                        for item in result.get("items", [])
                        if item.get("status") in {"blocked", "unverified"}
                    ][:100],
                },
            )
        )
        session.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result)

    session.commit()
    return result


@router.get("/{tournament_id}", response_model=TournamentView)
def get_tournament(
    tournament_id: str,
    session: Session = Depends(get_session),
    service: TournamentService = Depends(_service),
) -> TournamentView:
    try:
        tournament = service.get_tournament(tournament_id)
        session.commit()
    except TournamentError as exc:
        session.rollback()
        _raise_http(exc)
    return TournamentView.model_validate(tournament)


@router.post(
    "/{tournament_id}/join",
    response_model=TournamentView,
    deprecated=True,
    responses={410: {"description": "Legacy tournament engine retired"}},
)
def join_tournament(
    tournament_id: str,
    payload: TournamentJoinRequest,
    current_user: User = Depends(get_current_user),
) -> TournamentView:
    del tournament_id
    if payload.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tournament joins must be performed for the authenticated user.",
        )
    _legacy_engine_retired()


@router.post(
    "/{tournament_id}/matches/{match_id}/result",
    response_model=TournamentView,
    deprecated=True,
    responses={410: {"description": "Legacy tournament engine retired"}},
)
def report_match_result(
    tournament_id: str,
    match_id: str,
    payload: TournamentMatchResultRequest,
    current_user: User = Depends(get_current_user),
) -> TournamentView:
    del tournament_id, match_id, payload, current_user
    _legacy_engine_retired()


@router.post(
    "/{tournament_id}/advance",
    response_model=TournamentView,
    deprecated=True,
    responses={410: {"description": "Legacy tournament engine retired"}},
)
def advance_tournament(
    tournament_id: str,
    current_user: User = Depends(get_current_user),
) -> TournamentView:
    del tournament_id, current_user
    _legacy_engine_retired()
