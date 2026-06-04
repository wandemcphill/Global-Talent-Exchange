from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.access_control.dependencies import require_bound_organization_access
from app.auth.dependencies import get_current_user, get_session
from app.clubs.schemas import FormationSaveRequest as ClubFormationSaveRequest
from app.clubs.schemas import FormationView
from app.clubs.service import ClubFormationBlockedError, ClubFormationNotFoundError, ClubNotFoundError, ClubQueryService
from app.common.enums.academy_player_status import AcademyPlayerStatus
from app.models.access_control import OrganizationRole
from app.schemas.club_ops_requests import PublishFormationRequest, SaveFormationDraftRequest
from app.schemas.club_ops_responses import (
    ClubOpsContractLaneResponse,
    ClubOpsMissingDataResponse,
    FormationCoordinatesResponse,
    FormationContractEnvelopeResponse,
    FormationContractResponse,
    FormationHealthResponse,
    FormationHistoryResponse,
    FormationSlotResponse,
    SquadReadinessResponse,
)
from app.segments.clubs.segment_club_ops import router as club_ops_router
from app.services.academy_service import AcademyService, get_academy_service
from app.services.club_formation_service import (
    ClubFormationContractError,
    ClubFormationService,
    get_club_formation_service,
)
from app.services.scouting_service import ScoutingService, get_scouting_service

_FORMATION_STORAGE_SOURCE = "club_ops_formation_store"
_FORMATION_VALIDATION_SOURCE = "club_ops_formation_validation"
_SENIOR_SQUAD_SOURCE = "senior_squad_roster"
_MEDICAL_SOURCE = "player_medical_availability"
_MORALE_SOURCE = "team_morale_state"
_CHEMISTRY_SOURCE = "team_chemistry_model"
_PLAYER_CONTRACT_SOURCE = "player_contracts"


squad_contract_router = APIRouter(
    prefix="/api/clubs/{club_id}",
    tags=["club-ops"],
    include_in_schema=False,
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)


@squad_contract_router.get("/squad")
def get_hardened_squad_roster(
    club_id: str,
    session: Session = Depends(get_session),
    academy_service: AcademyService = Depends(get_academy_service),
) -> dict[str, object]:
    try:
        players, eligible_count, _source = _squad_contract_players(
            club_id,
            session=session,
            academy_service=academy_service,
        )
    except ClubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    state = "ready" if players else "empty"
    return {
        "club_id": club_id,
        "state": state,
        "status": state,
        "players": players,
        "selection_ready_count": eligible_count,
    }


@squad_contract_router.get("/squad/selection-ready")
def get_hardened_selection_ready_players(
    club_id: str,
    session: Session = Depends(get_session),
    academy_service: AcademyService = Depends(get_academy_service),
) -> dict[str, object]:
    try:
        players, _eligible_count, _source = _squad_contract_players(
            club_id,
            session=session,
            academy_service=academy_service,
        )
    except ClubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    ready_players = tuple(
        {
            "id": _player_id(player),
            "player_id": _player_id(player),
            "name": _player_name(player),
            "position": player.get("position"),
            "eligible": True,
        }
        for player in players
        if bool(player.get("selection_ready"))
    )
    state = "ready" if ready_players else "blocked"
    return {
        "club_id": club_id,
        "state": state,
        "status": state,
        "players": ready_players,
        "missing_data": () if ready_players else (_missing(_SENIOR_SQUAD_SOURCE, "No backend-owned players are selection-ready."),),
    }


@squad_contract_router.get("/squad/readiness", response_model=SquadReadinessResponse)
def get_hardened_squad_readiness(
    club_id: str,
    session: Session = Depends(get_session),
    academy_service: AcademyService = Depends(get_academy_service),
    scouting_service: ScoutingService = Depends(get_scouting_service),
) -> SquadReadinessResponse:
    try:
        return _build_squad_readiness_contract(
            club_id,
            session=session,
            academy_service=academy_service,
            scouting_service=scouting_service,
        )
    except ClubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@squad_contract_router.get("/squad/availability")
def get_hardened_squad_availability(
    club_id: str,
    session: Session = Depends(get_session),
    academy_service: AcademyService = Depends(get_academy_service),
) -> dict[str, object]:
    try:
        players, _eligible_count, _source = _squad_contract_players(
            club_id,
            session=session,
            academy_service=academy_service,
        )
    except ClubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _availability_payload(club_id, players)


@squad_contract_router.get("/squad/injuries")
def get_hardened_squad_injuries(
    club_id: str,
    session: Session = Depends(get_session),
    academy_service: AcademyService = Depends(get_academy_service),
) -> dict[str, object]:
    try:
        players, _eligible_count, _source = _squad_contract_players(
            club_id,
            session=session,
            academy_service=academy_service,
        )
    except ClubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    lane = _medical_lane(players)
    injuries = tuple(player.get("injury_detail") for player in players if player.get("injury_detail") is not None)
    state = _endpoint_state_from_lane(lane)
    return {
        "club_id": club_id,
        "state": state,
        "status": state,
        "injuries": injuries,
        "medical": lane.model_dump(mode="json"),
        "missing_data": lane.missing_data,
        "blockers": lane.blockers,
        "warnings": lane.warnings,
    }


@squad_contract_router.get("/squad/chemistry")
def get_hardened_squad_chemistry(
    club_id: str,
    session: Session = Depends(get_session),
    academy_service: AcademyService = Depends(get_academy_service),
) -> dict[str, object]:
    try:
        players, _eligible_count, _source = _squad_contract_players(
            club_id,
            session=session,
            academy_service=academy_service,
        )
    except ClubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    lane = _chemistry_lane(players)
    scores = tuple(
        score
        for player in players
        if (score := _nested_score(player.get("chemistry_fit"), "overall_score")) is not None
    )
    state = _endpoint_state_from_lane(lane)
    return {
        "club_id": club_id,
        "state": state,
        "status": state,
        "overall_score": round(sum(scores) / len(scores)) if scores else None,
        "chemistry": lane.model_dump(mode="json"),
        "players": lane.items,
        "missing_data": lane.missing_data,
        "blockers": lane.blockers,
        "warnings": lane.warnings,
    }


@squad_contract_router.get("/squad/contracts")
def get_hardened_squad_contracts(
    club_id: str,
    session: Session = Depends(get_session),
    academy_service: AcademyService = Depends(get_academy_service),
) -> dict[str, object]:
    try:
        players, _eligible_count, _source = _squad_contract_players(
            club_id,
            session=session,
            academy_service=academy_service,
        )
    except ClubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    lane = _contracts_lane(players)
    contracts = tuple(player.get("contract_status") for player in players if player.get("contract_status") is not None)
    state = _endpoint_state_from_lane(lane)
    return {
        "club_id": club_id,
        "state": state,
        "status": state,
        "contracts": contracts,
        "contract_readiness": lane.model_dump(mode="json"),
        "missing_data": lane.missing_data,
        "blockers": lane.blockers,
        "warnings": lane.warnings,
    }


@squad_contract_router.get("/squad/scouting")
def get_hardened_squad_scouting(
    club_id: str,
    session: Session = Depends(get_session),
    scouting_service: ScoutingService = Depends(get_scouting_service),
) -> dict[str, object]:
    try:
        backend_notes = ClubQueryService(session).get_scouting_notes(club_id).scouting_notes
    except SQLAlchemyError:
        backend_notes = ()
    except ClubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    notes = tuple(note.model_dump(mode="json") for note in backend_notes) or _scouting_notes(club_id, scouting_service)
    state = "ready" if notes else "empty"
    return {
        "club_id": club_id,
        "state": state,
        "status": state,
        "scouting_notes": notes,
        "missing_data": (),
        "reason": None if notes else "No scouting notes are currently recorded for this club.",
    }


formation_router = APIRouter(
    prefix="/api/v2/clubs/{club_id}",
    tags=["club-formation"],
    dependencies=[
        Depends(require_bound_organization_access(OrganizationRole.CLUB, forbidden_detail="club_access_required"))
    ],
)


@formation_router.get("/formation", response_model=FormationContractResponse)
def get_canonical_formation(
    club_id: str,
    session: Session = Depends(get_session),
    formation_service: ClubFormationService = Depends(get_club_formation_service),
) -> FormationContractResponse:
    active = formation_service.get_active(club_id, session=session)
    if active is None:
        return _blocked_formation_contract(club_id, action="read")
    return active


@formation_router.patch("/formation/draft", response_model=FormationContractResponse)
def save_canonical_formation_draft(
    club_id: str,
    payload: SaveFormationDraftRequest | None = Body(default=None),
    current_user: Any = Depends(get_current_user),
    academy_service: AcademyService = Depends(get_academy_service),
    formation_service: ClubFormationService = Depends(get_club_formation_service),
    session: Session = Depends(get_session),
) -> FormationContractResponse:
    try:
        return formation_service.save_draft(
            club_id,
            payload,
            actor_id=_actor_id(current_user),
            selection_ready_player_ids=_selection_ready_player_ids(club_id, academy_service),
            session=session,
        )
    except ClubFormationContractError as error:
        _raise_formation_contract_error(error)


@formation_router.post("/formation/publish", response_model=FormationContractResponse)
def publish_canonical_formation(
    club_id: str,
    payload: PublishFormationRequest | None = Body(default=None),
    current_user: Any = Depends(get_current_user),
    academy_service: AcademyService = Depends(get_academy_service),
    formation_service: ClubFormationService = Depends(get_club_formation_service),
    session: Session = Depends(get_session),
) -> FormationContractResponse:
    formation_id = payload.formation_id if payload is not None else None
    try:
        return formation_service.publish(
            club_id,
            formation_id,
            actor_id=_actor_id(current_user),
            selection_ready_player_ids=_selection_ready_player_ids(club_id, academy_service),
            session=session,
        )
    except ClubFormationContractError as error:
        _raise_formation_contract_error(error)


@formation_router.get("/formation/active", response_model=FormationContractEnvelopeResponse)
def get_active_formation(
    club_id: str,
    session: Session = Depends(get_session),
    formation_service: ClubFormationService = Depends(get_club_formation_service),
) -> FormationContractEnvelopeResponse:
    active = formation_service.get_active(club_id, session=session)
    if active is None:
        _raise_active_formation_missing(club_id)
    return _formation_envelope(active, code="formation_active_ready")


@formation_router.get("/formations", response_model=FormationHistoryResponse)
def list_formation_history(
    club_id: str,
    session: Session = Depends(get_session),
    formation_service: ClubFormationService = Depends(get_club_formation_service),
) -> FormationHistoryResponse:
    return formation_service.list_history(club_id, session=session)


@formation_router.post("/formations/draft", response_model=FormationContractEnvelopeResponse)
def save_formation_draft(
    club_id: str,
    payload: SaveFormationDraftRequest | None = Body(default=None),
    current_user: Any = Depends(get_current_user),
    academy_service: AcademyService = Depends(get_academy_service),
    formation_service: ClubFormationService = Depends(get_club_formation_service),
    session: Session = Depends(get_session),
) -> FormationContractEnvelopeResponse:
    try:
        formation = formation_service.save_draft(
            club_id,
            payload,
            actor_id=_actor_id(current_user),
            selection_ready_player_ids=_selection_ready_player_ids(club_id, academy_service),
            session=session,
        )
    except ClubFormationContractError as error:
        _raise_formation_contract_error(error)
    return _formation_envelope(formation, code="formation_draft_saved")


@formation_router.post("/formations/{formation_id}/publish", response_model=FormationContractEnvelopeResponse)
def publish_formation(
    club_id: str,
    formation_id: str,
    current_user: Any = Depends(get_current_user),
    academy_service: AcademyService = Depends(get_academy_service),
    formation_service: ClubFormationService = Depends(get_club_formation_service),
    session: Session = Depends(get_session),
) -> FormationContractEnvelopeResponse:
    try:
        formation = formation_service.publish(
            club_id,
            formation_id,
            actor_id=_actor_id(current_user),
            selection_ready_player_ids=_selection_ready_player_ids(club_id, academy_service),
            session=session,
        )
    except ClubFormationContractError as error:
        _raise_formation_contract_error(error)
    return _formation_envelope(formation, code="formation_published")


@formation_router.post("/formations/{source_formation_id}/restore", response_model=FormationContractEnvelopeResponse)
def restore_formation_draft(
    club_id: str,
    source_formation_id: str,
    current_user: Any = Depends(get_current_user),
    academy_service: AcademyService = Depends(get_academy_service),
    formation_service: ClubFormationService = Depends(get_club_formation_service),
    session: Session = Depends(get_session),
) -> FormationContractEnvelopeResponse:
    try:
        formation = formation_service.restore(
            club_id,
            source_formation_id,
            actor_id=_actor_id(current_user),
            selection_ready_player_ids=_selection_ready_player_ids(club_id, academy_service),
            session=session,
        )
    except ClubFormationContractError as error:
        _raise_formation_contract_error(error)
    return _formation_envelope(formation, code="formation_restored")


formation_detail_router = APIRouter(
    prefix="/api/v2/formations",
    tags=["club-formation"],
    dependencies=[Depends(get_current_user)],
)


@formation_detail_router.get("/{formation_id}", response_model=FormationContractEnvelopeResponse)
def get_formation_detail(
    formation_id: str,
    session: Session = Depends(get_session),
    formation_service: ClubFormationService = Depends(get_club_formation_service),
) -> FormationContractEnvelopeResponse:
    formation = formation_service.get_detail(formation_id, session=session)
    if formation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "state": "empty",
                "formation_id": formation_id,
                "code": "formation_not_found",
                "reason": "No authoritative formation record exists for this identifier.",
            },
        )
    return _formation_envelope(formation, code="formation_detail_ready")


def _actor_id(current_user: Any) -> str | None:
    actor_id = getattr(current_user, "id", None)
    return str(actor_id) if actor_id is not None else None


def _club_save_request(payload: SaveFormationDraftRequest | None, club_id: str) -> ClubFormationSaveRequest:
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "formation_draft_payload_required",
                "club_id": club_id,
                "reason": "Formation draft payload is required.",
            },
        )
    if not (payload.name or "").strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "formation_name_required",
                "club_id": club_id,
                "reason": "Formation draft name is required.",
            },
        )
    if not payload.slots:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "formation_slots_required",
                "club_id": club_id,
                "reason": "Formation draft requires backend-submitted slots.",
            },
        )
    return ClubFormationSaveRequest(
        name=payload.name,
        scheme=payload.scheme or payload.shape or "4-3-3",
        slots=[dict(slot) for slot in payload.slots],
        source_formation_id=payload.formation_id,
    )


def _formation_contract_from_view(formation: FormationView) -> FormationContractResponse:
    slots = tuple(
        FormationSlotResponse(
            id=slot.slot_id,
            slot_id=slot.slot_id,
            position=slot.position,
            role=slot.role,
            role_code=slot.position,
            role_label=slot.role,
            player_id=slot.assigned_player_id,
            assigned_player_id=slot.assigned_player_id,
            position_group=slot.position,
            coordinates=FormationCoordinatesResponse(x=slot.x, y=slot.y),
            x=slot.x,
            y=slot.y,
            filled=slot.filled,
        )
        for slot in formation.slots
    )
    blockers = tuple(formation.warnings if formation.status == "draft" else ())
    return FormationContractResponse(
        club_id=formation.club_id,
        id=formation.id,
        formation_id=formation.id,
        version=None,
        name=formation.name,
        shape=formation.scheme,
        scheme=formation.scheme,
        formation=formation.scheme,
        status=formation.status,
        state=formation.status,
        slots=slots,
        chemistry_score=formation.chemistry_score,
        warnings=tuple(formation.warnings),
        health=FormationHealthResponse(
            score=round(formation.chemistry_score),
            blockers=blockers,
            warnings=tuple(formation.warnings),
            missing_data=(),
        ),
        audit_trail=(),
        audit_ref=formation.audit_ref,
        sync_token=f"formation:{formation.club_id}:{formation.id}:{formation.updated_at.isoformat()}",
        can_save_draft=formation.status == "draft",
        can_publish=formation.status == "draft" and not blockers,
        missing_data=(),
        created_at=formation.created_at,
        updated_at=formation.updated_at,
        published_at=formation.published_at,
    )


def _formation_history_item(formation: FormationView) -> dict[str, object]:
    return {
        "id": formation.id,
        "name": formation.name,
        "scheme": formation.scheme,
        "published_at": formation.published_at,
        "updated_at": formation.updated_at,
        "chemistry_score": formation.chemistry_score,
        "status": formation.status,
        "audit_ref": formation.audit_ref,
    }


def _selection_ready_player_ids(
    club_id: str,
    academy_service: AcademyService,
) -> tuple[str, ...]:
    return tuple(
        str(player["id"])
        for player in _squad_players_from_academy(club_id, academy_service)
        if bool(player.get("selection_ready"))
    )


def _raise_formation_contract_error(error: ClubFormationContractError) -> None:
    raise HTTPException(status_code=error.status_code, detail=error.detail())


def _raise_active_formation_missing(club_id: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "state": "empty",
            "club_id": club_id,
            "code": "formation_active_not_found",
            "reason": "No authoritative active formation is mounted for this club yet.",
        },
    )


def _blocked_formation_contract(
    club_id: str,
    *,
    action: str,
    formation_id: str | None = None,
) -> FormationContractResponse:
    missing_data = _formation_missing_data()
    action_label = action.replace("_", " ")
    return FormationContractResponse(
        club_id=club_id,
        id=formation_id,
        formation_id=formation_id,
        version=None,
        shape=None,
        formation=None,
        status="blocked",
        state="blocked",
        slots=(),
        health=FormationHealthResponse(
            score=None,
            blockers=(
                "Formation source data is not mounted; backend cannot assert slots, player assignments, or coordinates.",
            ),
            warnings=(),
            missing_data=missing_data,
        ),
        audit_trail=(),
        sync_token=_blocked_sync_token(club_id),
        can_save_draft=False,
        can_publish=False,
        missing_data=missing_data,
        code=f"formation_{action}_source_missing",
        reason=(
            f"Formation {action_label} is blocked until authoritative draft, publish, validation, slot, and audit data are mounted."
        ),
    )


def _formation_envelope(
    formation: FormationContractResponse,
    *,
    code: str,
) -> FormationContractEnvelopeResponse:
    return FormationContractEnvelopeResponse(
        club_id=formation.club_id,
        state=formation.state,
        status=formation.status,
        formation=formation,
        missing_data=formation.missing_data,
        code=code,
        reason=formation.reason,
    )


def _formation_missing_data() -> tuple[ClubOpsMissingDataResponse, ...]:
    return (
        _missing(
            _FORMATION_STORAGE_SOURCE,
            "No authoritative formation draft, active formation, history, or publish store is mounted.",
        ),
        _missing(
            _FORMATION_VALIDATION_SOURCE,
            "No backend formation validator is mounted to derive slots, coordinates, health, or audit state.",
        ),
    )


def _blocked_sync_token(club_id: str) -> str:
    return f"blocked:{club_id}:{_FORMATION_STORAGE_SOURCE}:missing"


def _raise_formation_backend_gap(club_id: str, *, formation_id: str | None = None) -> None:
    detail: dict[str, object] = {
        "state": "blocked",
        "club_id": club_id,
        "code": "formation_contract_pending",
        "reason": "Formation contract is declared, but authoritative formation draft, publish, validation, and audit data are not mounted yet.",
    }
    if formation_id is not None:
        detail["formation_id"] = formation_id
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=detail,
    )


def _build_squad_readiness_contract(
    club_id: str,
    *,
    session: Session,
    academy_service: AcademyService,
    scouting_service: ScoutingService,
) -> SquadReadinessResponse:
    players, eligible_count, source = _squad_contract_players(
        club_id,
        session=session,
        academy_service=academy_service,
    )
    availability = _legacy_academy_availability_lane(players) if source == "academy_service" else _availability_lane(players)
    medical = _medical_lane(players)
    morale = _morale_lane(players)
    chemistry = _chemistry_lane(players)
    contracts = _contracts_lane(players)
    notes = _scouting_notes(club_id, scouting_service)
    scouting = _lane(
        lane="scouting_notes",
        state="ready" if notes else "empty",
        source="scouting_service",
        items=notes,
        warnings=() if notes else ("No scouting notes are recorded for this squad.",),
    )
    lanes = {
        "availability": availability,
        "medical": medical,
        "morale": morale,
        "chemistry": chemistry,
        "contracts": contracts,
        "scouting_notes": scouting,
    }
    missing_data = _unique_missing_data(lane.missing_data for lane in lanes.values())
    blockers: list[str] = []
    if eligible_count < 11:
        blockers.append("Formation publish requires 11 backend-eligible players.")
    blockers.extend(blocker for lane in lanes.values() for blocker in lane.blockers)
    warnings = tuple(warning for lane in lanes.values() for warning in lane.warnings)
    state = "blocked" if blockers else "degraded" if missing_data or warnings else "ready"
    readiness_score = round(min(100.0, (eligible_count / 11) * 100), 2) if players else None
    has_medical_source = medical.state != "missing"
    has_contract_source = contracts.state != "missing"
    injured_count = (
        sum(1 for player in players if _availability(player) == "injured")
        if players and has_medical_source
        else None
    )
    suspended_count = (
        sum(1 for player in players if _availability(player) == "suspended")
        if players and has_medical_source
        else None
    )
    available_for_next_fixture = (
        sum(1 for player in players if _availability(player) == "available" and bool(player.get("selection_ready")))
        if players and has_medical_source and has_contract_source
        else None
    )
    return SquadReadinessResponse(
        club_id=club_id,
        state=state,
        status=state,
        eligible_count=eligible_count,
        injured_count=injured_count,
        suspended_count=suspended_count,
        available_for_next_fixture=available_for_next_fixture,
        readiness_score=readiness_score,
        warnings=warnings,
        blockers=tuple(dict.fromkeys(blockers)),
        missing_data=missing_data,
        lanes=lanes,
        players=players,
    )


def _squad_contract_players(
    club_id: str,
    *,
    session: Session,
    academy_service: AcademyService,
) -> tuple[tuple[dict[str, object], ...], int, str]:
    try:
        roster = ClubQueryService(session).get_squad_roster(club_id)
    except SQLAlchemyError:
        players = _squad_players_from_academy(club_id, academy_service)
        return players, sum(1 for player in players if bool(player.get("selection_ready"))), "academy_service"
    except ClubNotFoundError:
        players = _squad_players_from_academy(club_id, academy_service)
        if players:
            return players, sum(1 for player in players if bool(player.get("selection_ready"))), "academy_service"
        raise
    return (
        tuple(player.model_dump(mode="json") for player in roster.players),
        roster.selection_ready_count,
        "senior_squad_roster",
    )


def _squad_players_from_academy(
    club_id: str,
    academy_service: AcademyService,
) -> tuple[dict[str, object], ...]:
    academy = academy_service.get_overview(club_id)
    return tuple(_academy_player_to_contract_player(player) for player in academy.players)


def _academy_player_to_contract_player(player: Any) -> dict[str, object]:
    status = getattr(player, "status", None)
    if isinstance(status, AcademyPlayerStatus):
        status_value = status.value
    else:
        status_value = str(status) if status is not None else "unknown"
    selection_ready = status_value == AcademyPlayerStatus.PROMOTED.value
    availability = "available" if selection_ready else "unknown"
    return {
        "id": player.id,
        "player_id": player.id,
        "name": player.display_name,
        "player_name": player.display_name,
        "position": player.primary_position,
        "age": player.age,
        "availability": availability,
        "selection_ready": selection_ready,
        "squad_eligible": selection_ready,
        "readiness_score": player.readiness_score,
        "status": status_value,
        "source": "academy_service",
        "medical_status": None,
        "morale": None,
        "chemistry_fit": None,
        "contract_status": None,
    }


def _availability_lane(players: tuple[dict[str, object], ...]) -> ClubOpsContractLaneResponse:
    if not players:
        return _lane(
            lane="availability",
            state="blocked",
            source="senior_squad_roster",
            missing_data=(
                _missing(
                    _SENIOR_SQUAD_SOURCE,
                    "No backend-owned senior squad players are available for squad readiness.",
                ),
            ),
            blockers=("No backend-owned players are available for selection readiness.",),
        )
    return _lane(
        lane="availability",
        state="ready",
        source="senior_squad_roster",
        items=players,
        missing_data=(),
        warnings=(),
    )


def _availability_payload(club_id: str, players: tuple[dict[str, object], ...]) -> dict[str, object]:
    lane = _availability_lane(players)
    if not players:
        return {
            "club_id": club_id,
            "state": "blocked",
            "status": "blocked",
            "players": (),
            "fixtures": (),
            "cells": (),
            "rows": (),
            "missing_data": lane.missing_data,
            "blockers": lane.blockers,
            "warnings": lane.warnings,
        }
    fixture = {"fixture_id": "next", "label": "Next match"}
    return {
        "club_id": club_id,
        "state": lane.state,
        "status": lane.status,
        "players": tuple(
            {
                "player_id": _player_id(player),
                "name": _player_name(player),
                "position": player.get("position"),
            }
            for player in players
        ),
        "fixtures": (fixture,),
        "cells": tuple(
            {
                "player_id": _player_id(player),
                "fixture_id": fixture["fixture_id"],
                "status": _availability(player),
            }
            for player in players
        ),
        "rows": tuple(
            {
                "player_id": _player_id(player),
                "name": _player_name(player),
                "position": player.get("position"),
                "statuses": (_availability(player),),
            }
            for player in players
        ),
        "missing_data": lane.missing_data,
        "blockers": lane.blockers,
        "warnings": lane.warnings,
    }


def _legacy_academy_availability_lane(players: tuple[dict[str, object], ...]) -> ClubOpsContractLaneResponse:
    if not players:
        return _availability_lane(players)
    return _lane(
        lane="availability",
        state="ready",
        source="academy_service",
        items=players,
    )


def _medical_lane(players: tuple[dict[str, object], ...]) -> ClubOpsContractLaneResponse:
    if not players:
        return _lane(
            lane="medical",
            state="missing",
            source=None,
            missing_data=(
                _missing(
                    _MEDICAL_SOURCE,
                    "No authoritative injury, suspension, or medical clearance source is mounted for club ops.",
                ),
            ),
            blockers=("Medical clearance cannot be asserted for match readiness.",),
        )
    sourced = tuple(
        player
        for player in players
        if player.get("medical_source") or player.get("medical_status") is not None or player.get("injury_detail") is not None
    )
    if not sourced:
        return _lane(
            lane="medical",
            state="missing",
            source=None,
            missing_data=(
                _missing(
                    _MEDICAL_SOURCE,
                    "No authoritative injury, suspension, or medical clearance source is mounted for club ops.",
                ),
            ),
            blockers=("Medical clearance cannot be asserted for match readiness.",),
        )
    unavailable = tuple(
        player
        for player in players
        if _availability(player) in {"injured", "suspended", "unfit", "away"}
        or player.get("injury_detail") is not None
    )
    blockers = (
        (f"{len(unavailable)} player(s) are not medically cleared for the next fixture.",)
        if unavailable
        else ()
    )
    missing_count = len(players) - len(sourced)
    warnings = (
        (f"Medical availability source is missing for {missing_count} player(s).",)
        if missing_count
        else ()
    )
    state = "blocked" if blockers else "degraded" if warnings else "ready"
    return _lane(
        lane="medical",
        state=state,
        source=_MEDICAL_SOURCE,
        items=tuple(
            {
                "player_id": _player_id(player),
                "player_name": _player_name(player),
                "availability": _availability(player),
                "medical_status": player.get("medical_status"),
                "injury_detail": player.get("injury_detail"),
            }
            for player in players
        ),
        blockers=blockers,
        warnings=warnings,
    )


def _morale_lane(players: tuple[dict[str, object], ...]) -> ClubOpsContractLaneResponse:
    if not players:
        return _lane(
            lane="morale",
            state="missing",
            source=None,
            missing_data=(
                _missing(
                    _MORALE_SOURCE,
                    "No authoritative morale source is mounted for club ops.",
                ),
            ),
            warnings=("Morale is omitted rather than synthesized from local defaults.",),
        )
    items = tuple(
        {
            "player_id": _player_id(player),
            "player_name": _player_name(player),
            "score": _nested_score(player.get("morale"), "score"),
            "label": _nested_value(player.get("morale"), "label"),
            "trend": _nested_value(player.get("morale"), "trend"),
            "source": _nested_value(player.get("morale"), "source"),
        }
        for player in players
        if _nested_score(player.get("morale"), "score") is not None
    )
    if not items:
        return _lane(
            lane="morale",
            state="missing",
            source=None,
            missing_data=(
                _missing(
                    _MORALE_SOURCE,
                    "No authoritative morale source is mounted for club ops.",
                ),
            ),
            warnings=("Morale is omitted rather than synthesized from local defaults.",),
        )
    low = tuple(item for item in items if isinstance(item.get("score"), (int, float)) and float(item["score"]) < 40)
    missing_count = len(players) - len(items)
    warnings = tuple(
        dict.fromkeys(
            (
                *((f"Morale source is missing for {missing_count} player(s).",) if missing_count else ()),
                *((f"{len(low)} player(s) have low morale.",) if low else ()),
            )
        )
    )
    return _lane(
        lane="morale",
        state="degraded" if warnings else "ready",
        source=_MORALE_SOURCE,
        items=items,
        warnings=warnings,
    )


def _chemistry_lane(players: tuple[dict[str, object], ...]) -> ClubOpsContractLaneResponse:
    if not players:
        return _lane(
            lane="chemistry",
            state="missing",
            source=None,
            missing_data=(
                _missing(
                    _CHEMISTRY_SOURCE,
                    "No authoritative chemistry model is mounted for club ops.",
                ),
            ),
            warnings=("Chemistry score is omitted rather than synthesized from local defaults.",),
        )
    items = tuple(
        {
            "player_id": _player_id(player),
            "player_name": _player_name(player),
            "overall_score": _nested_score(player.get("chemistry_fit"), "overall_score"),
            "position_fit": _nested_score(player.get("chemistry_fit"), "position_fit"),
            "team_fit": _nested_score(player.get("chemistry_fit"), "team_fit"),
            "warnings": _nested_sequence(player.get("chemistry_fit"), "warnings"),
            "source": _nested_value(player.get("chemistry_fit"), "source"),
        }
        for player in players
        if _nested_score(player.get("chemistry_fit"), "overall_score") is not None
    )
    if not items:
        return _lane(
            lane="chemistry",
            state="missing",
            source=None,
            missing_data=(
                _missing(
                    _CHEMISTRY_SOURCE,
                    "No authoritative chemistry model is mounted for club ops.",
                ),
            ),
            warnings=("Chemistry score is omitted rather than synthesized from local defaults.",),
        )
    missing_count = len(players) - len(items)
    model_warnings = tuple(
        str(warning)
        for item in items
        for warning in _nested_sequence(item, "warnings")
        if str(warning).strip()
    )
    warnings = tuple(
        dict.fromkeys(
            (
                *((f"Chemistry model is missing for {missing_count} player(s).",) if missing_count else ()),
                *model_warnings,
            )
        )
    )
    return _lane(
        lane="chemistry",
        state="degraded" if warnings else "ready",
        source=_CHEMISTRY_SOURCE,
        items=items,
        warnings=warnings,
    )


def _contracts_lane(players: tuple[dict[str, object], ...]) -> ClubOpsContractLaneResponse:
    if not players:
        return _lane(
            lane="contracts",
            state="missing",
            source=None,
            missing_data=(
                _missing(
                    _PLAYER_CONTRACT_SOURCE,
                    "No authoritative player contract source is mounted for club ops.",
                ),
            ),
            blockers=("Contract readiness cannot be asserted without player contract data.",),
        )
    items = tuple(
        {
            "player_id": _player_id(player),
            "player_name": _player_name(player),
            "status": _nested_value(player.get("contract_status"), "status"),
            "end_date": _nested_value(player.get("contract_status"), "end_date"),
            "weeks_remaining": _nested_value(player.get("contract_status"), "weeks_remaining"),
            "alert": _nested_value(player.get("contract_status"), "alert"),
            "source": _nested_value(player.get("contract_status"), "source"),
        }
        for player in players
        if player.get("contract_status") is not None
    )
    if not items:
        return _lane(
            lane="contracts",
            state="missing",
            source=None,
            missing_data=(
                _missing(
                    _PLAYER_CONTRACT_SOURCE,
                    "No authoritative player contract source is mounted for club ops.",
                ),
            ),
            blockers=("Contract readiness cannot be asserted without player contract data.",),
        )
    missing_count = len(players) - len(items)
    inactive = tuple(
        item
        for item in items
        if str(item.get("status") or "").strip().lower() not in {"active"}
    )
    renewal_alerts = tuple(item for item in items if item.get("alert"))
    blockers = tuple(
        dict.fromkeys(
            (
                *((f"Player contract source is missing for {missing_count} player(s).",) if missing_count else ()),
                *((f"{len(inactive)} player(s) do not have active contracts.",) if inactive else ()),
            )
        )
    )
    warnings = (
        (f"{len(renewal_alerts)} player contract(s) require renewal review.",)
        if renewal_alerts
        else ()
    )
    return _lane(
        lane="contracts",
        state="blocked" if blockers else "degraded" if warnings else "ready",
        source=_PLAYER_CONTRACT_SOURCE,
        items=items,
        blockers=blockers,
        warnings=warnings,
    )


def _endpoint_state_from_lane(lane: ClubOpsContractLaneResponse) -> str:
    if lane.state in {"missing", "blocked"}:
        return "blocked"
    return lane.state


def _player_id(player: dict[str, object]) -> str | None:
    value = player.get("player_id") or player.get("id")
    return str(value) if value is not None else None


def _player_name(player: dict[str, object]) -> str | None:
    value = player.get("player_name") or player.get("name")
    return str(value) if value is not None else None


def _availability(player: dict[str, object]) -> str:
    value = player.get("availability")
    return str(value).strip().lower() if value is not None else "unknown"


def _nested_value(value: object, key: str) -> object | None:
    if isinstance(value, dict):
        return value.get(key)
    return None


def _nested_score(value: object, key: str) -> int | float | None:
    raw = _nested_value(value, key)
    if isinstance(raw, (int, float)):
        return raw
    return None


def _nested_sequence(value: object, key: str) -> tuple[object, ...]:
    raw = _nested_value(value, key)
    if isinstance(raw, (list, tuple)):
        return tuple(raw)
    return ()


def _scouting_notes(
    club_id: str,
    scouting_service: ScoutingService,
) -> tuple[dict[str, object], ...]:
    scouting = scouting_service.get_overview(club_id)
    notes: list[dict[str, object]] = []
    for prospect in scouting.prospects:
        for report in prospect.reports:
            notes.append(
                {
                    "player_id": prospect.academy_player_id or prospect.id,
                    "author_id": report.assignment_id,
                    "content": report.summary_text,
                    "created_at": report.created_at,
                    "tags": (*report.strengths, *report.development_flags),
                    "source": "scouting_service",
                }
            )
    return tuple(notes)


def _lane(
    *,
    lane: str,
    state: str,
    source: str | None,
    items: tuple[dict[str, object], ...] = (),
    missing_data: tuple[ClubOpsMissingDataResponse, ...] = (),
    blockers: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> ClubOpsContractLaneResponse:
    return ClubOpsContractLaneResponse(
        lane=lane,
        state=state,
        status=state,
        source=source,
        items=items,
        missing_data=missing_data,
        blockers=blockers,
        warnings=warnings,
    )


def _missing(source: str, reason: str) -> ClubOpsMissingDataResponse:
    return ClubOpsMissingDataResponse(source=source, reason=reason)


def _unique_missing_data(
    groups: Any,
) -> tuple[ClubOpsMissingDataResponse, ...]:
    seen: set[str] = set()
    unique: list[ClubOpsMissingDataResponse] = []
    for group in groups:
        for item in group:
            key = f"{item.source}:{item.reason}"
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
    return tuple(unique)


router = APIRouter()
router.include_router(squad_contract_router)
router.include_router(club_ops_router)
router.include_router(formation_router)
router.include_router(formation_detail_router)

__all__ = ["formation_detail_router", "formation_router", "router", "squad_contract_router"]
