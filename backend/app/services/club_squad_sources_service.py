from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import InjuryStatus, Player
from app.models.base import utcnow
from app.models.club_squad_source import ClubSquadPlayerSourceRecord
from app.models.player_contract import PlayerContract


CLUB_SQUAD_MEDICAL_SOURCE_PROVIDER = "club_squad_sources"
PLAYER_MEDICAL_AVAILABILITY_SOURCE = "player_medical_availability"
TEAM_MORALE_SOURCE = "team_morale_state"
TEAM_CHEMISTRY_SOURCE = "team_chemistry_model"
PLAYER_CONTRACT_SOURCE = "player_contracts"


@dataclass(frozen=True, slots=True)
class ClubSquadRosterSources:
    medical_by_player: dict[str, InjuryStatus]
    contract_by_player: dict[str, PlayerContract]
    player_source_by_player: dict[str, ClubSquadPlayerSourceRecord]


class ClubSquadSourcesService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def sources_for_roster(self, club_id: str, players: Iterable[Player]) -> ClubSquadRosterSources:
        player_ids = tuple(player.id for player in players)
        if not player_ids:
            return ClubSquadRosterSources({}, {}, {})
        return ClubSquadRosterSources(
            medical_by_player=self.latest_medical_by_player(player_ids),
            contract_by_player=self.active_contracts_by_player(club_id, player_ids),
            player_source_by_player=self.player_sources_by_player(club_id, player_ids),
        )

    def player_sources_by_player(
        self,
        club_id: str,
        player_ids: Iterable[str],
    ) -> dict[str, ClubSquadPlayerSourceRecord]:
        ids = tuple(player_ids)
        if not ids:
            return {}
        records = self.session.scalars(
            select(ClubSquadPlayerSourceRecord).where(
                ClubSquadPlayerSourceRecord.club_id == club_id,
                ClubSquadPlayerSourceRecord.player_id.in_(ids),
            )
        ).all()
        return {record.player_id: record for record in records}

    def latest_medical_by_player(self, player_ids: Iterable[str]) -> dict[str, InjuryStatus]:
        ids = tuple(player_ids)
        if not ids:
            return {}
        records = self.session.scalars(
            select(InjuryStatus)
            .where(InjuryStatus.player_id.in_(ids))
            .order_by(InjuryStatus.expected_return_at.desc().nullslast(), InjuryStatus.updated_at.desc())
        ).all()
        result: dict[str, InjuryStatus] = {}
        for record in records:
            result.setdefault(record.player_id, record)
        return result

    def active_contracts_by_player(
        self,
        club_id: str,
        player_ids: Iterable[str],
        *,
        reference_on: date | None = None,
    ) -> dict[str, PlayerContract]:
        ids = tuple(player_ids)
        if not ids:
            return {}
        today = reference_on or utcnow().date()
        contracts = self.session.scalars(
            select(PlayerContract)
            .where(
                PlayerContract.club_id == club_id,
                PlayerContract.player_id.in_(ids),
                PlayerContract.starts_on <= today,
                PlayerContract.ends_on >= today,
            )
            .order_by(PlayerContract.ends_on.desc(), PlayerContract.updated_at.desc())
        ).all()
        result: dict[str, PlayerContract] = {}
        for contract in contracts:
            result.setdefault(contract.player_id, contract)
        return result

    def upsert_player_sources(
        self,
        *,
        club_id: str,
        player_id: str,
        morale_score: float | None = None,
        morale_label: str | None = None,
        morale_trend: str | None = None,
        chemistry_overall_score: float | None = None,
        chemistry_position_fit: float | None = None,
        chemistry_team_fit: float | None = None,
        chemistry_warnings: Iterable[str] = (),
        source_ref: str | None = None,
    ) -> ClubSquadPlayerSourceRecord:
        record = self.session.scalar(
            select(ClubSquadPlayerSourceRecord).where(
                ClubSquadPlayerSourceRecord.club_id == club_id,
                ClubSquadPlayerSourceRecord.player_id == player_id,
            )
        )
        if record is None:
            record = ClubSquadPlayerSourceRecord(club_id=club_id, player_id=player_id)
            self.session.add(record)
        record.morale_score = _clamp_score(morale_score)
        record.morale_label = morale_label or _morale_label(record.morale_score)
        record.morale_trend = morale_trend
        record.chemistry_overall_score = _clamp_score(chemistry_overall_score)
        record.chemistry_position_fit = _clamp_score(chemistry_position_fit)
        record.chemistry_team_fit = _clamp_score(chemistry_team_fit)
        record.chemistry_warnings_json = [str(item) for item in chemistry_warnings if str(item).strip()]
        record.source_ref = source_ref
        self.session.flush()
        return record

    def upsert_medical_status(
        self,
        *,
        club_id: str,
        player_id: str,
        status: str,
        detail: str | None = None,
        expected_return_at: date | None = None,
    ) -> InjuryStatus:
        provider_external_id = f"{club_id}:{player_id}:medical"
        record = self.session.scalar(
            select(InjuryStatus).where(
                InjuryStatus.source_provider == CLUB_SQUAD_MEDICAL_SOURCE_PROVIDER,
                InjuryStatus.provider_external_id == provider_external_id,
            )
        )
        if record is None:
            record = InjuryStatus(
                source_provider=CLUB_SQUAD_MEDICAL_SOURCE_PROVIDER,
                provider_external_id=provider_external_id,
                player_id=player_id,
                status=status,
            )
            self.session.add(record)
        record.player_id = player_id
        record.club_id = _ingestion_club_id(self.session.get(Player, player_id), club_id)
        record.status = status
        record.detail = detail
        record.expected_return_at = expected_return_at
        self.session.flush()
        return record

    def upsert_contract(
        self,
        *,
        club_id: str,
        player_id: str,
        signed_on: date,
        starts_on: date,
        ends_on: date,
        status: str = "active",
        wage_amount: Decimal | int | str = Decimal("0.00"),
        bonus_terms: str | None = None,
    ) -> PlayerContract:
        contract = self.session.scalar(
            select(PlayerContract).where(
                PlayerContract.club_id == club_id,
                PlayerContract.player_id == player_id,
                PlayerContract.starts_on == starts_on,
            )
        )
        if contract is None:
            contract = PlayerContract(
                club_id=club_id,
                player_id=player_id,
                signed_on=signed_on,
                starts_on=starts_on,
                ends_on=ends_on,
            )
            self.session.add(contract)
        contract.status = status
        contract.wage_amount = Decimal(str(wage_amount))
        contract.bonus_terms = bonus_terms
        contract.ends_on = ends_on
        self.session.flush()
        return contract


def _clamp_score(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(100.0, float(value)))


def _morale_label(score: float | None) -> str | None:
    if score is None:
        return None
    return "strong" if score >= 70 else "stable" if score >= 40 else "low"


def _ingestion_club_id(player: Player | None, requested_club_id: str) -> str | None:
    if player is None:
        return None
    return player.current_club_id if player.current_club_id == requested_club_id else None
