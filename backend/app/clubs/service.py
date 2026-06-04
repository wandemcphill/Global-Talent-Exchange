from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.clubs.schemas import (
    AvailabilityCellView,
    AvailabilityFixtureView,
    AvailabilityMatrixPlayerView,
    AvailabilityMatrixView,
    AvailabilityRowView,
    ChemistryFitView,
    ChemistryReportView,
    ContractStatusView,
    FormationBlockedResponse,
    FormationEnvelope,
    FormationHistoryView,
    FormationSaveRequest,
    FormationSelectionReadyPlayerView,
    FormationSelectionReadyView,
    FormationSlotView,
    FormationView,
    InjuryView,
    MoraleScoreView,
    PlayerStatsView,
    ScoutingNoteView,
    SquadContractsView,
    SquadInjuriesView,
    SquadPlayerView,
    SquadRosterView,
    SquadScoutingView,
)
from app.ingestion.models import Club, Country, InjuryStatus, Player
from app.models.base import utcnow
from app.models.club_formation import ClubFormation
from app.models.club_profile import ClubProfile
from app.models.club_squad_source import ClubSquadPlayerSourceRecord
from app.models.player_contract import PlayerContract
from app.services.club_squad_sources_service import (
    PLAYER_CONTRACT_SOURCE,
    PLAYER_MEDICAL_AVAILABILITY_SOURCE,
    TEAM_CHEMISTRY_SOURCE,
    TEAM_MORALE_SOURCE,
    ClubSquadSourcesService,
)


@dataclass(slots=True)
class ClubSnapshot:
    id: str
    name: str
    slug: str
    short_name: str | None
    country_name: str | None
    player_count: int
    updated_at: object


@dataclass(slots=True)
class ClubQueryService:
    session: Session

    def get_club(self, club_id: str) -> ClubSnapshot | None:
        club = self.session.get(Club, club_id)
        if club is None:
            return None
        country_name = None
        if club.country_id is not None:
            country = self.session.get(Country, club.country_id)
            country_name = country.name if country is not None else None
        player_count = self.session.scalar(
            select(func.count(Player.id)).where(Player.current_club_id == club_id)
        ) or 0
        return ClubSnapshot(
            id=club.id,
            name=club.name,
            slug=club.slug,
            short_name=club.short_name,
            country_name=country_name,
            player_count=int(player_count),
            updated_at=club.updated_at,
        )

    def get_squad_roster(self, club_id: str) -> SquadRosterView:
        players = self._players_for_club(club_id)
        sources = ClubSquadSourcesService(self.session).sources_for_roster(club_id, players)
        roster = [
            self._squad_player(
                player,
                sources.medical_by_player.get(player.id),
                sources.contract_by_player.get(player.id),
                sources.player_source_by_player.get(player.id),
            )
            for player in players
        ]
        return SquadRosterView(
            players=roster,
            selection_ready_count=sum(1 for player in roster if player.selection_ready),
        )

    def get_availability_matrix(self, club_id: str) -> AvailabilityMatrixView:
        roster = self.get_squad_roster(club_id).players
        fixture = AvailabilityFixtureView(fixture_id="next", label="Next match")
        return AvailabilityMatrixView(
            players=[
                AvailabilityMatrixPlayerView(player_id=player.id, name=player.name, position=player.position)
                for player in roster
            ],
            fixtures=[fixture] if roster else [],
            cells=[
                AvailabilityCellView(player_id=player.id, fixture_id=fixture.fixture_id, status=player.availability)
                for player in roster
            ],
            rows=[
                AvailabilityRowView(
                    player_id=player.id,
                    name=player.name,
                    position=player.position,
                    statuses=[player.availability],
                )
                for player in roster
            ],
        )

    def get_injuries(self, club_id: str) -> SquadInjuriesView:
        roster = self.get_squad_roster(club_id).players
        return SquadInjuriesView(
            injuries=[player.injury_detail for player in roster if player.injury_detail is not None],
        )

    def get_chemistry_report(self, club_id: str) -> ChemistryReportView:
        roster = self.get_squad_roster(club_id).players
        chemistry_players = [player for player in roster if player.chemistry_fit is not None]
        if not chemistry_players:
            return ChemistryReportView(overall_score=None, warnings=[])
        score = round(sum(player.chemistry_fit.overall_score for player in chemistry_players) / len(chemistry_players))
        warnings: list[str] = []
        if len(chemistry_players) < len(roster):
            warnings.append("chemistry_source_missing_for_some_players")
        for player in chemistry_players:
            warnings.extend(player.chemistry_fit.warnings)
        return ChemistryReportView(overall_score=score, warnings=list(dict.fromkeys(warnings)))

    def get_contracts(self, club_id: str) -> SquadContractsView:
        return SquadContractsView(
            contracts=[
                player.contract_status
                for player in self.get_squad_roster(club_id).players
                if player.contract_status is not None
            ],
        )

    def get_scouting_notes(self, club_id: str) -> SquadScoutingView:
        notes: list[ScoutingNoteView] = []
        for player in self.get_squad_roster(club_id).players:
            notes.extend(player.scouting_notes)
        return SquadScoutingView(scouting_notes=notes)

    def get_selection_ready_players(self, club_id: str) -> FormationSelectionReadyView:
        return FormationSelectionReadyView(
            players=[
                FormationSelectionReadyPlayerView(
                    id=player.id,
                    name=player.name,
                    position=player.position,
                    eligible=player.selection_ready,
                )
                for player in self.get_squad_roster(club_id).players
            ],
        )

    def get_active_formation(self, club_id: str) -> FormationView | None:
        formation = self.session.scalar(
            select(ClubFormation)
            .where(ClubFormation.club_id == club_id, ClubFormation.status == "published")
            .order_by(ClubFormation.published_at.desc(), ClubFormation.updated_at.desc())
        )
        return self._formation_view(formation) if formation is not None else None

    def list_formations(self, club_id: str) -> FormationHistoryView:
        formations = list(
            self.session.scalars(
                select(ClubFormation)
                .where(ClubFormation.club_id == club_id)
                .order_by(ClubFormation.updated_at.desc())
            ).all()
        )
        return FormationHistoryView(formations=[self._formation_view(item) for item in formations])

    def get_formation(self, formation_id: str) -> FormationView | None:
        formation = self.session.get(ClubFormation, formation_id)
        return self._formation_view(formation) if formation is not None else None

    def save_formation_draft(self, club_id: str, request: FormationSaveRequest) -> FormationEnvelope:
        self._require_club_profile(club_id)
        now = utcnow()
        formation = ClubFormation(
            id=str(uuid4()),
            club_id=club_id,
            name=request.name,
            scheme=request.scheme,
            status="draft",
            slots_json=[slot.model_dump(mode="json") for slot in request.slots],
            chemistry_score=self._formation_chemistry_score(club_id, request.slots),
            warnings_json=self._formation_warnings(club_id, request.slots),
            source_formation_id=request.source_formation_id,
            created_at=now,
            updated_at=now,
        )
        self.session.add(formation)
        self.session.commit()
        self.session.refresh(formation)
        return FormationEnvelope(formation=self._formation_view(formation))

    def publish_formation(self, club_id: str, formation_id: str, *, actor_user_id: str | None = None) -> FormationEnvelope:
        formation = self.session.get(ClubFormation, formation_id)
        if formation is None or formation.club_id != club_id:
            raise ClubFormationNotFoundError(f"Formation {formation_id} was not found.")
        readiness = self._formation_publish_block(club_id, self._formation_slots(formation))
        if readiness is not None:
            raise ClubFormationBlockedError(readiness)
        now = utcnow()
        for previous in self.session.scalars(
            select(ClubFormation).where(ClubFormation.club_id == club_id, ClubFormation.status == "published")
        ).all():
            previous.status = "archived"
            previous.updated_at = now
        formation.status = "published"
        formation.published_at = now
        formation.updated_at = now
        formation.chemistry_score = self._formation_chemistry_score(club_id, self._formation_slots(formation))
        formation.warnings_json = self._formation_warnings(club_id, self._formation_slots(formation))
        formation.audit_ref = f"formation-publish:{formation.id}:{int(now.timestamp())}"
        del actor_user_id
        self.session.commit()
        self.session.refresh(formation)
        return FormationEnvelope(formation=self._formation_view(formation))

    def restore_formation_draft(self, club_id: str, source_formation_id: str) -> FormationEnvelope:
        source = self.session.get(ClubFormation, source_formation_id)
        if source is None or source.club_id != club_id:
            raise ClubFormationNotFoundError(f"Formation {source_formation_id} was not found.")
        return self.save_formation_draft(
            club_id,
            FormationSaveRequest(
                name=f"{source.name} draft",
                scheme=source.scheme,
                slots=self._formation_slots(source),
                source_formation_id=source.id,
            ),
        )

    def _players_for_club(self, club_id: str) -> list[Player]:
        self._require_any_club(club_id)
        return list(
            self.session.scalars(
                select(Player)
                .where(or_(Player.current_club_profile_id == club_id, Player.current_club_id == club_id))
                .order_by(Player.full_name.asc())
            ).all()
        )

    def _require_any_club(self, club_id: str) -> None:
        if self.session.get(ClubProfile, club_id) is not None:
            return
        if self.session.get(Club, club_id) is not None:
            return
        raise ClubNotFoundError(f"Club {club_id} was not found")

    def _require_club_profile(self, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise ClubNotFoundError(f"Club profile {club_id} was not found")
        return club

    def _squad_player(
        self,
        player: Player,
        injury: InjuryStatus | None,
        contract: PlayerContract | None,
        source: ClubSquadPlayerSourceRecord | None,
    ) -> SquadPlayerView:
        availability = self._availability_for(player, injury)
        position = player.normalized_position or player.position or "N/A"
        chemistry = self._chemistry_fit(source, position=position)
        contract_status = self._contract_status(player, contract)
        injury_view = self._injury_view(player, injury) if availability == "injured" and injury is not None else None
        has_position = bool(player.normalized_position or player.position)
        has_active_contract = contract_status is not None and contract_status.status == "active"
        return SquadPlayerView(
            id=player.id,
            name=player.canonical_display_name or player.full_name,
            position=position,
            age=self._age(player.date_of_birth),
            nationality=player.country.name if player.country is not None else None,
            availability=availability,
            injury_detail=injury_view,
            medical_status=injury.status if injury is not None else None,
            medical_source=PLAYER_MEDICAL_AVAILABILITY_SOURCE if injury is not None else None,
            morale=self._morale(source),
            chemistry_fit=chemistry,
            contract_status=contract_status,
            selection_ready=availability == "available" and has_position and has_active_contract,
            scouting_notes=self._scouting_notes(player),
            stats=PlayerStatsView(),
        )

    def _availability_for(self, player: Player, injury: InjuryStatus | None) -> str:
        del player
        if injury is None:
            return "unknown"
        status = injury.status.strip().lower()
        if status in {"suspended", "ban", "banned"}:
            return "suspended"
        if status in {"away", "international_duty"}:
            return "away"
        if status in {"unfit", "doubtful"}:
            return "unfit"
        if status in {"fit", "available", "cleared", "resolved"}:
            return "available"
        if injury.expected_return_at is not None and injury.expected_return_at >= utcnow().date():
            return "injured"
        return "injured"

    def _injury_view(self, player: Player, injury: InjuryStatus) -> InjuryView:
        return InjuryView(
            player_id=player.id,
            player_name=player.canonical_display_name or player.full_name,
            type=injury.status,
            expected_return=self._date_to_datetime(injury.expected_return_at),
            severity=injury.detail,
            injury_date=None,
        )

    def _morale(self, source: ClubSquadPlayerSourceRecord | None) -> MoraleScoreView | None:
        if source is None or source.morale_score is None:
            return None
        resolved = max(0, min(100, round(source.morale_score)))
        label = source.morale_label or ("strong" if resolved >= 70 else "stable" if resolved >= 40 else "low")
        return MoraleScoreView(score=resolved, label=label, trend=source.morale_trend, source=TEAM_MORALE_SOURCE)

    def _chemistry_fit(
        self,
        source: ClubSquadPlayerSourceRecord | None,
        *,
        position: str,
    ) -> ChemistryFitView | None:
        if source is None or source.chemistry_overall_score is None:
            return None
        resolved = max(0, min(100, round(source.chemistry_overall_score)))
        position_fit = max(0, min(100, round(source.chemistry_position_fit if source.chemistry_position_fit is not None else resolved)))
        team_fit = max(0, min(100, round(source.chemistry_team_fit if source.chemistry_team_fit is not None else resolved)))
        warnings = [] if position != "N/A" else ["missing_position"]
        warnings.extend(str(item) for item in source.chemistry_warnings_json or ())
        return ChemistryFitView(
            overall_score=resolved,
            position_fit=position_fit,
            team_fit=team_fit,
            warnings=list(dict.fromkeys(warnings)),
            source=TEAM_CHEMISTRY_SOURCE,
        )

    def _contract_status(self, player: Player, contract: PlayerContract | None) -> ContractStatusView | None:
        if contract is None:
            return None
        contract_end = contract.ends_on
        weeks_remaining = None
        alert = None
        today = utcnow().date()
        weeks_remaining = max(0, (contract_end - today).days // 7)
        if contract_end < today:
            resolved_status = "expired"
            alert = "expired"
        elif contract.starts_on > today:
            resolved_status = "pending"
        else:
            resolved_status = contract.status
            if weeks_remaining < 26:
                alert = "renewal_risk"
        return ContractStatusView(
            player_id=player.id,
            player_name=player.canonical_display_name or player.full_name,
            end_date=self._date_to_datetime(contract_end),
            status=resolved_status,
            weeks_remaining=weeks_remaining,
            alert=alert,
            source=PLAYER_CONTRACT_SOURCE,
        )

    def _scouting_notes(self, player: Player) -> list[ScoutingNoteView]:
        raw_notes = (player.dna_profile or {}).get("scouting_notes")
        if not isinstance(raw_notes, list):
            return []
        notes: list[ScoutingNoteView] = []
        for item in raw_notes:
            if isinstance(item, dict):
                content = str(item.get("content") or item.get("note") or "").strip()
                if content:
                    tags = item.get("tags") if isinstance(item.get("tags"), list) else []
                    notes.append(
                        ScoutingNoteView(
                            player_id=player.id,
                            author_id=str(item.get("author_id") or "") or None,
                            content=content,
                            created_at=self._parse_datetime(item.get("created_at")),
                            tags=[str(tag) for tag in tags],
                        )
                    )
            elif str(item).strip():
                notes.append(ScoutingNoteView(player_id=player.id, content=str(item).strip()))
        return notes

    def _formation_slots(self, formation: ClubFormation) -> list[FormationSlotView]:
        return [FormationSlotView.model_validate(slot) for slot in list(formation.slots_json or [])]

    def _formation_view(self, formation: ClubFormation) -> FormationView:
        return FormationView(
            id=formation.id,
            club_id=formation.club_id,
            name=formation.name,
            scheme=formation.scheme,
            slots=self._formation_slots(formation),
            chemistry_score=formation.chemistry_score,
            warnings=list(formation.warnings_json or []),
            status=formation.status,  # type: ignore[arg-type]
            created_at=formation.created_at,
            updated_at=formation.updated_at,
            published_at=formation.published_at,
            audit_ref=formation.audit_ref,
        )

    def _formation_publish_block(self, club_id: str, slots: list[FormationSlotView]) -> FormationBlockedResponse | None:
        eligible = {
            player.id
            for player in self.get_squad_roster(club_id).players
            if player.selection_ready
        }
        if len(eligible) < 11:
            return FormationBlockedResponse(
                reason="Insufficient eligible players - update squad before editing formation.",
                eligible_player_count=len(eligible),
                details={"blocked_by": "eligible_player_count"},
            )
        assigned = {
            slot.assigned_player_id
            for slot in slots
            if slot.filled and slot.assigned_player_id and slot.assigned_player_id in eligible
        }
        if len(assigned) < 11:
            return FormationBlockedResponse(
                reason="Publish requires 11 filled formation slots.",
                eligible_player_count=len(eligible),
                details={"blocked_by": "filled_eligible_slots", "filled_eligible_slots": len(assigned)},
            )
        return None

    def _formation_chemistry_score(self, club_id: str, slots: list[FormationSlotView]) -> float:
        eligible = {
            player.id
            for player in self.get_squad_roster(club_id).players
            if player.selection_ready
        }
        assigned = {
            slot.assigned_player_id
            for slot in slots
            if slot.filled and slot.assigned_player_id and slot.assigned_player_id in eligible
        }
        return min(100.0, round((len(assigned) / 11) * 100, 2)) if assigned else 0.0

    def _formation_warnings(self, club_id: str, slots: list[FormationSlotView]) -> list[str]:
        eligible = {
            player.id
            for player in self.get_squad_roster(club_id).players
            if player.selection_ready
        }
        warnings: list[str] = []
        if len(eligible) < 11:
            warnings.append("insufficient_eligible_players")
        if len({slot.assigned_player_id for slot in slots if slot.filled and slot.assigned_player_id}) < 11:
            warnings.append("incomplete_starting_xi")
        invalid = [
            slot.assigned_player_id
            for slot in slots
            if slot.assigned_player_id and slot.assigned_player_id not in eligible
        ]
        if invalid:
            warnings.append("contains_ineligible_players")
        return warnings

    def _date_from_metadata(self, metadata: dict[str, object] | None, key: str) -> date | None:
        value = (metadata or {}).get(key)
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                return None
        return None

    def _parse_datetime(self, value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    def _date_to_datetime(self, value: date | None) -> datetime | None:
        if value is None:
            return None
        return datetime.combine(value, time.min, tzinfo=timezone.utc)

    def _age(self, born: date | None) -> int | None:
        if born is None:
            return None
        today = utcnow().date()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class ClubNotFoundError(Exception):
    pass


class ClubFormationNotFoundError(Exception):
    pass


class ClubFormationBlockedError(Exception):
    def __init__(self, response: FormationBlockedResponse) -> None:
        super().__init__(response.reason)
        self.response = response
