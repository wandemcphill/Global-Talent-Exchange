"""Backend-owned club formation draft, publish, restore, and audit contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Iterable
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.clubs.service import ClubNotFoundError, ClubQueryService
from app.ingestion.models import Player
from app.models.base import utcnow
from app.models.club_formation import ClubFormation, ClubFormationAuditEvent
from app.models.club_profile import ClubProfile
from app.schemas.club_ops_requests import SaveFormationDraftRequest
from app.schemas.club_ops_responses import (
    FormationAuditEventResponse,
    FormationContractResponse,
    FormationCoordinatesResponse,
    FormationHealthResponse,
    FormationHistoryResponse,
    FormationSlotResponse,
)
from app.services.club_finance_service import ClubOpsStore, get_club_ops_store


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ClubFormationContractError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        reason: str,
        state: str = "blocked",
        club_id: str | None = None,
        formation_id: str | None = None,
        blockers: Iterable[str] = (),
        extra_detail: dict[str, object] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.reason = reason
        self.state = state
        self.club_id = club_id
        self.formation_id = formation_id
        self.blockers = tuple(blockers)
        self.extra_detail = dict(extra_detail or {})
        super().__init__(reason)

    def detail(self) -> dict[str, object]:
        detail: dict[str, object] = {
            "state": self.state,
            "status": self.state,
            "code": self.code,
            "reason": self.reason,
        }
        if self.club_id is not None:
            detail["club_id"] = self.club_id
        if self.formation_id is not None:
            detail["formation_id"] = self.formation_id
        if self.blockers:
            detail["blockers"] = self.blockers
        detail.update(self.extra_detail)
        return detail


@dataclass(frozen=True, slots=True)
class FormationSlotRecord:
    slot_id: str
    position: str
    assigned_player_id: str | None
    x: float | None
    y: float | None
    role: str
    filled: bool


@dataclass(slots=True)
class FormationRecord:
    id: str
    club_id: str
    name: str
    scheme: str
    slots: tuple[FormationSlotRecord, ...]
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    chemistry_score: float
    warnings: tuple[str, ...]
    validation_blockers: tuple[str, ...] = ()
    source_formation_id: str | None = None
    published_at: datetime | None = None
    published_by: str | None = None
    audit_ref: str | None = None


@dataclass(frozen=True, slots=True)
class FormationValidationResult:
    score: float
    warnings: tuple[str, ...]
    blockers: tuple[str, ...]


class ClubFormationService:
    def __init__(self, *, store: ClubOpsStore | None = None) -> None:
        self.store = store or get_club_ops_store()

    def get_active(self, club_id: str, *, session: Session | None = None) -> FormationContractResponse | None:
        if session is not None:
            try:
                response = self._db_get_active(session, club_id)
            except SQLAlchemyError:
                response = None
            if response is not None:
                return response
        with self.store.lock:
            formation_id = self.store.active_formation_id_by_club.get(club_id)
            record = self.store.formation_records_by_club.get(club_id, {}).get(formation_id or "")
            if not isinstance(record, FormationRecord):
                return None
            return self._to_response(record)

    def list_history(self, club_id: str, *, session: Session | None = None) -> FormationHistoryResponse:
        if session is not None:
            try:
                response = self._db_list_history(session, club_id)
            except SQLAlchemyError:
                response = None
            if response is not None:
                return response
        with self.store.lock:
            records = tuple(self._records_for_club(club_id).values())
            items = tuple(self._history_item(record) for record in sorted(records, key=lambda item: item.updated_at, reverse=True))
        state = "ready" if items else "empty"
        return FormationHistoryResponse(
            club_id=club_id,
            state=state,
            status=state,
            formations=items,
            items=items,
            missing_data=(),
            sync_token=f"formation:{club_id}:history:{len(items)}",
            code=None if items else "formation_history_empty",
            reason=None if items else "No backend-owned formation drafts or published shapes exist for this club yet.",
        )

    def get_detail(self, formation_id: str, *, session: Session | None = None) -> FormationContractResponse | None:
        if session is not None:
            try:
                response = self._db_get_detail(session, formation_id)
            except SQLAlchemyError:
                response = None
            if response is not None:
                return response
        with self.store.lock:
            for records in self.store.formation_records_by_club.values():
                record = records.get(formation_id)
                if isinstance(record, FormationRecord):
                    return self._to_response(record)
        return None

    def save_draft(
        self,
        club_id: str,
        payload: SaveFormationDraftRequest | None,
        *,
        actor_id: str | None,
        selection_ready_player_ids: Iterable[str] = (),
        session: Session | None = None,
    ) -> FormationContractResponse:
        if session is not None:
            try:
                response = self._db_save_draft(
                    session,
                    club_id,
                    payload,
                    actor_id=actor_id,
                )
            except SQLAlchemyError:
                response = None
            if response is not None:
                return response
        if payload is None:
            raise self._bad_request(
                club_id=club_id,
                code="formation_draft_payload_required",
                reason="Formation draft payload is required.",
            )
        name = (payload.name or "").strip()
        scheme = (payload.scheme or payload.shape or "").strip()
        if not name:
            raise self._bad_request(
                club_id=club_id,
                code="formation_name_required",
                reason="Formation draft name is required.",
            )
        if not scheme:
            raise self._bad_request(
                club_id=club_id,
                code="formation_scheme_required",
                reason="Formation scheme is required.",
            )
        slots = tuple(self._slot_from_payload(index, slot) for index, slot in enumerate(payload.slots, start=1))
        if not slots:
            raise self._bad_request(
                club_id=club_id,
                code="formation_slots_required",
                reason="Formation draft requires backend-submitted slots.",
            )
        now = _utcnow()
        with self.store.lock:
            records = self._records_for_club(club_id)
            existing = records.get(payload.formation_id or "")
            if isinstance(existing, FormationRecord) and existing.status == "draft":
                record = existing
                record.name = name
                record.scheme = scheme
                record.slots = slots
                record.version += 1
                record.updated_at = now
                record.source_formation_id = payload.formation_id
            else:
                record = FormationRecord(
                    id=f"form-{uuid4().hex[:12]}",
                    club_id=club_id,
                    name=name,
                    scheme=scheme,
                    slots=slots,
                    status="draft",
                    version=1,
                    created_at=now,
                    updated_at=now,
                    chemistry_score=0,
                    warnings=(),
                    source_formation_id=payload.formation_id,
                )
                records[record.id] = record
            self._refresh_record_validation(record, selection_ready_player_ids=selection_ready_player_ids)
            self._append_audit(record, action="draft_saved", actor_id=actor_id)
            return self._to_response(record)

    def publish(
        self,
        club_id: str,
        formation_id: str | None,
        *,
        actor_id: str | None,
        selection_ready_player_ids: Iterable[str],
        session: Session | None = None,
    ) -> FormationContractResponse:
        if session is not None:
            try:
                response = self._db_publish(
                    session,
                    club_id,
                    formation_id,
                    actor_id=actor_id,
                )
            except SQLAlchemyError:
                response = None
            if response is not None:
                return response
        normalized_id = (formation_id or "").strip()
        if not normalized_id:
            raise self._bad_request(
                club_id=club_id,
                code="formation_id_required",
                reason="Formation id is required before publish.",
            )
        with self.store.lock:
            record = self._records_for_club(club_id).get(normalized_id)
            if not isinstance(record, FormationRecord):
                raise ClubFormationContractError(
                    status_code=404,
                    code="formation_not_found",
                    reason="No backend-owned formation draft exists for this identifier.",
                    state="empty",
                    club_id=club_id,
                    formation_id=normalized_id,
                )
            blockers = self._publish_blockers(record, selection_ready_player_ids)
            if blockers:
                self._refresh_record_validation(record, selection_ready_player_ids=selection_ready_player_ids)
                raise ClubFormationContractError(
                    status_code=409,
                    code="formation_publish_blocked",
                    reason="Formation publish requires backend-eligible unique starting XI assignments.",
                    state="blocked",
                    club_id=club_id,
                    formation_id=record.id,
                    blockers=blockers,
                )
            for other in self._records_for_club(club_id).values():
                if isinstance(other, FormationRecord) and other.status == "published" and other.id != record.id:
                    other.status = "archived"
                    other.updated_at = _utcnow()
            now = _utcnow()
            record.status = "published"
            record.version += 1
            record.updated_at = now
            record.published_at = now
            record.published_by = actor_id
            self._refresh_record_validation(record, selection_ready_player_ids=selection_ready_player_ids)
            self._append_audit(record, action="published", actor_id=actor_id)
            self.store.active_formation_id_by_club[club_id] = record.id
            return self._to_response(record)

    def restore(
        self,
        club_id: str,
        source_formation_id: str,
        *,
        actor_id: str | None,
        selection_ready_player_ids: Iterable[str] = (),
        session: Session | None = None,
    ) -> FormationContractResponse:
        if session is not None:
            try:
                response = self._db_restore(
                    session,
                    club_id,
                    source_formation_id,
                    actor_id=actor_id,
                )
            except SQLAlchemyError:
                response = None
            if response is not None:
                return response
        with self.store.lock:
            source = self._records_for_club(club_id).get(source_formation_id)
            if not isinstance(source, FormationRecord):
                raise ClubFormationContractError(
                    status_code=404,
                    code="formation_not_found",
                    reason="No backend-owned formation exists to restore.",
                    state="empty",
                    club_id=club_id,
                    formation_id=source_formation_id,
                )
            now = _utcnow()
            record = FormationRecord(
                id=f"form-{uuid4().hex[:12]}",
                club_id=club_id,
                name=f"{source.name} restored",
                scheme=source.scheme,
                slots=source.slots,
                status="draft",
                version=1,
                created_at=now,
                updated_at=now,
                chemistry_score=source.chemistry_score,
                warnings=source.warnings,
                source_formation_id=source.id,
            )
            self._records_for_club(club_id)[record.id] = record
            self._refresh_record_validation(record, selection_ready_player_ids=selection_ready_player_ids)
            self._append_audit(record, action="restored", actor_id=actor_id, note=f"Restored from {source.id}.")
            return self._to_response(record)

    def _db_get_active(self, session: Session, club_id: str) -> FormationContractResponse | None:
        if session.get(ClubProfile, club_id) is None:
            return None
        formation = session.scalar(
            select(ClubFormation)
            .where(ClubFormation.club_id == club_id, ClubFormation.status == "published")
            .order_by(ClubFormation.published_at.desc(), ClubFormation.updated_at.desc())
        )
        return self._db_to_response(session, formation) if formation is not None else None

    def _db_list_history(self, session: Session, club_id: str) -> FormationHistoryResponse | None:
        if session.get(ClubProfile, club_id) is None:
            return None
        formations = tuple(
            session.scalars(
                select(ClubFormation)
                .where(ClubFormation.club_id == club_id)
                .order_by(ClubFormation.updated_at.desc())
            ).all()
        )
        items = tuple(self._db_history_item(formation) for formation in formations)
        state = "ready" if items else "empty"
        return FormationHistoryResponse(
            club_id=club_id,
            state=state,
            status=state,
            formations=items,
            items=items,
            missing_data=(),
            sync_token=f"formation:{club_id}:history:{len(items)}",
            code=None if items else "formation_history_empty",
            reason=None if items else "No backend-owned formation drafts or published shapes exist for this club yet.",
        )

    def _db_get_detail(self, session: Session, formation_id: str) -> FormationContractResponse | None:
        formation = session.get(ClubFormation, formation_id)
        return self._db_to_response(session, formation) if formation is not None else None

    def _db_save_draft(
        self,
        session: Session,
        club_id: str,
        payload: SaveFormationDraftRequest | None,
        *,
        actor_id: str | None,
    ) -> FormationContractResponse | None:
        if session.get(ClubProfile, club_id) is None:
            return None
        name, scheme, slots = self._draft_components(club_id, payload)
        now = utcnow()
        existing = session.get(ClubFormation, payload.formation_id) if payload is not None and payload.formation_id else None
        if existing is not None and existing.club_id != club_id:
            raise ClubFormationContractError(
                status_code=404,
                code="formation_not_found",
                reason="No backend-owned formation draft exists for this club.",
                state="empty",
                club_id=club_id,
                formation_id=payload.formation_id,
            )
        if existing is not None and existing.status == "draft":
            formation = existing
            formation.name = name
            formation.scheme = scheme
            formation.slots_json = [self._slot_record_to_json(slot) for slot in slots]
            formation.version += 1
            formation.updated_at = now
            formation.updated_by_user_id = actor_id
        else:
            formation = ClubFormation(
                id=str(uuid4()),
                club_id=club_id,
                name=name,
                scheme=scheme,
                status="draft",
                version=1,
                slots_json=[self._slot_record_to_json(slot) for slot in slots],
                chemistry_score=0.0,
                warnings_json=[],
                validation_blockers_json=[],
                source_formation_id=payload.formation_id if payload is not None else None,
                created_at=now,
                updated_at=now,
                updated_by_user_id=actor_id,
            )
            session.add(formation)
        self._db_refresh_validation(session, formation)
        self._db_append_audit(session, formation, action="draft_saved", actor_id=actor_id)
        session.commit()
        session.refresh(formation)
        return self._db_to_response(session, formation)

    def _db_publish(
        self,
        session: Session,
        club_id: str,
        formation_id: str | None,
        *,
        actor_id: str | None,
    ) -> FormationContractResponse | None:
        if session.get(ClubProfile, club_id) is None:
            return None
        normalized_id = (formation_id or "").strip()
        if not normalized_id:
            raise self._bad_request(
                club_id=club_id,
                code="formation_id_required",
                reason="Formation id is required before publish.",
            )
        formation = session.get(ClubFormation, normalized_id)
        if formation is None or formation.club_id != club_id:
            raise ClubFormationContractError(
                status_code=404,
                code="formation_not_found",
                reason="No backend-owned formation draft exists for this identifier.",
                state="empty",
                club_id=club_id,
                formation_id=normalized_id,
            )
        validation = self._db_refresh_validation(session, formation)
        if validation.blockers:
            session.commit()
            eligible_player_count = len(self._db_selection_ready_player_ids(session, club_id))
            reason = (
                "Insufficient eligible players - update squad before editing formation."
                if eligible_player_count < 11
                else "Formation publish requires backend-eligible unique starting XI assignments with coordinates."
            )
            raise ClubFormationContractError(
                status_code=409,
                code="formation_publish_blocked",
                reason=reason,
                state="blocked",
                club_id=club_id,
                formation_id=formation.id,
                blockers=validation.blockers,
                extra_detail={"eligible_player_count": eligible_player_count},
            )
        now = utcnow()
        for previous in session.scalars(
            select(ClubFormation).where(ClubFormation.club_id == club_id, ClubFormation.status == "published")
        ).all():
            if previous.id == formation.id:
                continue
            previous.status = "archived"
            previous.updated_at = now
        formation.status = "published"
        formation.version += 1
        formation.updated_at = now
        formation.published_at = now
        formation.published_by_user_id = actor_id
        formation.updated_by_user_id = actor_id
        self._db_refresh_validation(session, formation)
        self._db_append_audit(session, formation, action="published", actor_id=actor_id)
        session.commit()
        session.refresh(formation)
        return self._db_to_response(session, formation)

    def _db_restore(
        self,
        session: Session,
        club_id: str,
        source_formation_id: str,
        *,
        actor_id: str | None,
    ) -> FormationContractResponse | None:
        if session.get(ClubProfile, club_id) is None:
            return None
        source = session.get(ClubFormation, source_formation_id)
        if source is None or source.club_id != club_id:
            raise ClubFormationContractError(
                status_code=404,
                code="formation_not_found",
                reason="No backend-owned formation exists to restore.",
                state="empty",
                club_id=club_id,
                formation_id=source_formation_id,
            )
        now = utcnow()
        formation = ClubFormation(
            id=str(uuid4()),
            club_id=club_id,
            name=f"{source.name} restored",
            scheme=source.scheme,
            status="draft",
            version=1,
            slots_json=list(source.slots_json or []),
            chemistry_score=0.0,
            warnings_json=[],
            validation_blockers_json=[],
            source_formation_id=source.id,
            created_at=now,
            updated_at=now,
            updated_by_user_id=actor_id,
        )
        session.add(formation)
        self._db_refresh_validation(session, formation)
        self._db_append_audit(session, formation, action="restored", actor_id=actor_id, note=f"Restored from {source.id}.")
        session.commit()
        session.refresh(formation)
        return self._db_to_response(session, formation)

    def _records_for_club(self, club_id: str) -> dict[str, object]:
        return self.store.formation_records_by_club.setdefault(club_id, {})

    def _slot_from_payload(self, index: int, payload: dict[str, object]) -> FormationSlotRecord:
        slot_id = self._text(payload.get("slot_id") or payload.get("slotId") or payload.get("id")) or f"slot-{index}"
        position = self._text(payload.get("position") or payload.get("role_code") or payload.get("position_group")) or "UNK"
        assigned_player_id = self._text(
            payload.get("assigned_player_id") or payload.get("assignedPlayerId") or payload.get("player_id")
        )
        coordinates = payload.get("coordinates")
        coordinates_payload = coordinates if isinstance(coordinates, dict) else {}
        x = self._optional_float(payload.get("x") if payload.get("x") is not None else coordinates_payload.get("x"))
        y = self._optional_float(payload.get("y") if payload.get("y") is not None else coordinates_payload.get("y"))
        role = self._text(payload.get("role") or payload.get("role_label")) or "balanced"
        filled_value = payload.get("filled")
        filled = bool(filled_value) if filled_value is not None else bool(assigned_player_id)
        return FormationSlotRecord(
            slot_id=slot_id,
            position=position,
            assigned_player_id=assigned_player_id,
            x=x,
            y=y,
            role=role,
            filled=filled,
        )

    def _draft_components(
        self,
        club_id: str,
        payload: SaveFormationDraftRequest | None,
    ) -> tuple[str, str, tuple[FormationSlotRecord, ...]]:
        if payload is None:
            raise self._bad_request(
                club_id=club_id,
                code="formation_draft_payload_required",
                reason="Formation draft payload is required.",
            )
        name = (payload.name or "").strip()
        scheme = (payload.scheme or payload.shape or "").strip()
        if not name:
            raise self._bad_request(
                club_id=club_id,
                code="formation_name_required",
                reason="Formation draft name is required.",
            )
        if not scheme:
            raise self._bad_request(
                club_id=club_id,
                code="formation_scheme_required",
                reason="Formation scheme is required.",
            )
        if not payload.slots:
            raise self._bad_request(
                club_id=club_id,
                code="formation_slots_required",
                reason="Formation draft requires backend-submitted slots.",
            )
        return name, scheme, tuple(self._slot_from_payload(index, slot) for index, slot in enumerate(payload.slots, start=1))

    def _db_refresh_validation(self, session: Session, formation: ClubFormation) -> FormationValidationResult:
        validation = self._validate_slots(
            self._slots_from_json(formation.slots_json),
            selection_ready_player_ids=self._db_selection_ready_player_ids(session, formation.club_id),
        )
        formation.chemistry_score = validation.score
        formation.warnings_json = list(validation.warnings)
        formation.validation_blockers_json = list(validation.blockers)
        return validation

    def _db_selection_ready_player_ids(self, session: Session, club_id: str) -> tuple[str, ...]:
        try:
            roster = ClubQueryService(session).get_squad_roster(club_id)
        except (ClubNotFoundError, SQLAlchemyError):
            players = tuple(
                session.scalars(
                    select(Player)
                    .where(or_(Player.current_club_profile_id == club_id, Player.current_club_id == club_id))
                    .order_by(Player.full_name.asc())
                ).all()
            )
            return tuple(
                player.id
                for player in players
                if bool(player.normalized_position or player.position)
            )
        return tuple(player.id for player in roster.players if player.selection_ready)

    def _slots_from_json(self, slots_json: Iterable[dict[str, object]] | None) -> tuple[FormationSlotRecord, ...]:
        return tuple(self._slot_from_payload(index, dict(slot)) for index, slot in enumerate(slots_json or (), start=1))

    def _slot_record_to_json(self, slot: FormationSlotRecord) -> dict[str, object]:
        return {
            "slot_id": slot.slot_id,
            "position": slot.position,
            "assigned_player_id": slot.assigned_player_id,
            "x": slot.x,
            "y": slot.y,
            "role": slot.role,
            "filled": slot.filled,
        }

    def _db_append_audit(
        self,
        session: Session,
        formation: ClubFormation,
        *,
        action: str,
        actor_id: str | None,
        note: str | None = None,
    ) -> None:
        formation.audit_ref = f"formation:{formation.id}:{action}:v{formation.version}"
        session.add(
            ClubFormationAuditEvent(
                id=f"form-audit-{uuid4().hex[:12]}",
                formation_id=formation.id,
                club_id=formation.club_id,
                action=f"club_formation.{action}",
                actor_user_id=actor_id,
                version=formation.version,
                note=note,
                metadata_json={},
                created_at=utcnow(),
            )
        )

    def _db_audit_events(self, session: Session, formation_id: str) -> tuple[FormationAuditEventResponse, ...]:
        events = tuple(
            session.scalars(
                select(ClubFormationAuditEvent)
                .where(ClubFormationAuditEvent.formation_id == formation_id)
                .order_by(ClubFormationAuditEvent.created_at.asc(), ClubFormationAuditEvent.id.asc())
            ).all()
        )
        return tuple(
            FormationAuditEventResponse(
                id=event.id,
                action=event.action,
                actor=event.actor_user_id,
                occurred_at=event.created_at,
                note=event.note,
                version=event.version,
            )
            for event in events
        )

    def _db_to_response(self, session: Session, formation: ClubFormation) -> FormationContractResponse:
        slots = self._slots_from_json(formation.slots_json)
        blockers = tuple(formation.validation_blockers_json or ())
        slot_responses = tuple(self._slot_to_response(slot) for slot in slots)
        return FormationContractResponse(
            club_id=formation.club_id,
            id=formation.id,
            formation_id=formation.id,
            version=formation.version,
            name=formation.name,
            shape=formation.scheme,
            scheme=formation.scheme,
            formation=formation.scheme,
            status=formation.status,
            state=formation.status,
            slots=slot_responses,
            chemistry_score=formation.chemistry_score,
            warnings=tuple(formation.warnings_json or ()),
            health=FormationHealthResponse(
                score=round(formation.chemistry_score),
                blockers=blockers if formation.status == "draft" else (),
                warnings=tuple(formation.warnings_json or ()),
                missing_data=(),
            ),
            audit_trail=self._db_audit_events(session, formation.id),
            audit_ref=formation.audit_ref,
            sync_token=f"formation:{formation.club_id}:{formation.id}:v{formation.version}",
            can_save_draft=formation.status == "draft",
            can_publish=formation.status == "draft" and not blockers,
            missing_data=(),
            created_at=formation.created_at,
            updated_at=formation.updated_at,
            updated_by=formation.updated_by_user_id,
            published_at=formation.published_at,
            published_by=formation.published_by_user_id,
        )

    def _db_history_item(self, formation: ClubFormation) -> dict[str, object]:
        return {
            "id": formation.id,
            "name": formation.name,
            "scheme": formation.scheme,
            "published_at": formation.published_at,
            "updated_at": formation.updated_at,
            "chemistry_score": formation.chemistry_score,
            "status": formation.status,
            "version": formation.version,
            "audit_ref": formation.audit_ref,
        }

    def _slot_to_response(self, slot: FormationSlotRecord) -> FormationSlotResponse:
        return FormationSlotResponse(
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

    def _refresh_record_validation(
        self,
        record: FormationRecord,
        *,
        selection_ready_player_ids: Iterable[str],
    ) -> None:
        validation = self._validate_slots(record.slots, selection_ready_player_ids=selection_ready_player_ids)
        record.chemistry_score = validation.score
        record.warnings = validation.warnings
        record.validation_blockers = validation.blockers

    def _publish_blockers(
        self,
        record: FormationRecord,
        selection_ready_player_ids: Iterable[str],
    ) -> tuple[str, ...]:
        return self._validate_slots(record.slots, selection_ready_player_ids=selection_ready_player_ids).blockers

    def _validate_slots(
        self,
        slots: Iterable[FormationSlotRecord],
        *,
        selection_ready_player_ids: Iterable[str],
    ) -> FormationValidationResult:
        slot_tuple = tuple(slots)
        assigned = self._assigned_player_ids_from_slots(slot_tuple)
        blockers: list[str] = []
        if len(slot_tuple) != 11:
            blockers.append("Publish requires exactly 11 formation slots.")
        if len(assigned) != 11:
            blockers.append("Publish requires 11 filled player assignments.")
        if len(set(assigned)) != len(assigned):
            blockers.append("Publish requires unique player assignments.")
        missing_coordinate_slots = tuple(slot.slot_id for slot in slot_tuple if slot.x is None or slot.y is None)
        if missing_coordinate_slots:
            blockers.append(
                "Publish requires coordinates for every formation slot: "
                + ", ".join(missing_coordinate_slots)
                + "."
            )
        eligible_ids = {player_id for player_id in selection_ready_player_ids if player_id}
        if not eligible_ids:
            blockers.append("No backend selection-ready squad source is available for publish validation.")
        else:
            missing_ids = sorted({player_id for player_id in assigned if player_id not in eligible_ids})
            if missing_ids:
                blockers.append(f"Assigned players are not backend selection-ready: {', '.join(missing_ids)}.")
        valid_assigned_ids = tuple(
            player_id
            for player_id in dict.fromkeys(assigned)
            if player_id in eligible_ids
        )
        valid_coordinate_count = sum(1 for slot in slot_tuple if slot.x is not None and slot.y is not None)
        valid_slot_count = min(len(valid_assigned_ids), valid_coordinate_count, 11)
        score = min(100.0, round((valid_slot_count / 11) * 100, 2)) if slot_tuple else 0.0
        unique_blockers = tuple(dict.fromkeys(blockers))
        warnings = unique_blockers or ("Chemistry model is not mounted; score reflects backend slot readiness only.",)
        return FormationValidationResult(score=score, warnings=tuple(dict.fromkeys(warnings)), blockers=unique_blockers)

    def _assigned_player_ids(self, record: FormationRecord) -> tuple[str, ...]:
        return self._assigned_player_ids_from_slots(record.slots)

    def _assigned_player_ids_from_slots(self, slots: Iterable[FormationSlotRecord]) -> tuple[str, ...]:
        return tuple(
            slot.assigned_player_id
            for slot in slots
            if slot.filled and slot.assigned_player_id is not None and slot.assigned_player_id.strip()
        )

    def _append_audit(
        self,
        record: FormationRecord,
        *,
        action: str,
        actor_id: str | None,
        note: str | None = None,
    ) -> None:
        occurred_at = _utcnow()
        audit_id = f"form-audit-{uuid4().hex[:12]}"
        record.audit_ref = f"formation:{record.id}:{action}:v{record.version}"
        event = FormationAuditEventResponse(
            id=audit_id,
            action=f"club_formation.{action}",
            actor=actor_id,
            occurred_at=occurred_at,
            note=note,
            version=record.version,
        )
        self.store.formation_audit_by_id.setdefault(record.id, []).append(event)

    def _to_response(self, record: FormationRecord) -> FormationContractResponse:
        blockers = record.validation_blockers
        audit_events = tuple(
            event
            for event in self.store.formation_audit_by_id.get(record.id, ())
            if isinstance(event, FormationAuditEventResponse)
        )
        slot_responses = tuple(self._slot_to_response(slot) for slot in record.slots)
        can_publish = record.status == "draft" and not blockers
        return FormationContractResponse(
            club_id=record.club_id,
            id=record.id,
            formation_id=record.id,
            version=record.version,
            name=record.name,
            shape=record.scheme,
            scheme=record.scheme,
            formation=record.scheme,
            status=record.status,
            state=record.status,
            slots=slot_responses,
            chemistry_score=record.chemistry_score,
            warnings=record.warnings,
            health=FormationHealthResponse(
                score=round(record.chemistry_score),
                blockers=blockers if record.status == "draft" else (),
                warnings=record.warnings,
                missing_data=(),
            ),
            audit_trail=audit_events,
            audit_ref=record.audit_ref,
            sync_token=f"formation:{record.club_id}:{record.id}:v{record.version}",
            can_save_draft=record.status == "draft",
            can_publish=can_publish,
            missing_data=(),
            created_at=record.created_at,
            updated_at=record.updated_at,
            published_at=record.published_at,
            published_by=record.published_by,
        )

    def _history_item(self, record: FormationRecord) -> dict[str, object]:
        return {
            "id": record.id,
            "name": record.name,
            "scheme": record.scheme,
            "published_at": record.published_at,
            "updated_at": record.updated_at,
            "chemistry_score": record.chemistry_score,
            "status": record.status,
            "version": record.version,
            "audit_ref": record.audit_ref,
        }

    @staticmethod
    def _bad_request(*, club_id: str, code: str, reason: str) -> ClubFormationContractError:
        return ClubFormationContractError(
            status_code=422,
            code=code,
            reason=reason,
            state="blocked",
            club_id=club_id,
        )

    @staticmethod
    def _text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _optional_float(value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


@lru_cache
def get_club_formation_service() -> ClubFormationService:
    return ClubFormationService(store=get_club_ops_store())


__all__ = [
    "ClubFormationContractError",
    "ClubFormationService",
    "FormationRecord",
    "FormationSlotRecord",
    "get_club_formation_service",
]
