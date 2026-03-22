from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from uuid import uuid4

from app.common.enums.academy_player_status import AcademyPlayerStatus
from app.schemas.academy_core import AcademyPlayerView, AcademyProgramView
from app.schemas.club_ops_requests import (
    CreateAcademyPlayerRequest,
    CreateAcademyProgramRequest,
    UpdateAcademyPlayerRequest,
)
from app.schemas.club_ops_responses import AcademyOverviewResponse, AcademyPlayersResponse, AcademyTrainingCyclesResponse
from app.services.academy_graduation_service import AcademyGraduationService, get_academy_graduation_service
from app.services.academy_progression_service import AcademyProgressionService, get_academy_progression_service
from app.services.academy_training_service import AcademyTrainingService, get_academy_training_service
from app.services.club_finance_service import ClubFinanceService, ClubOpsStore, get_club_finance_service, get_club_ops_store


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AcademyService:
    def __init__(
        self,
        *,
        store: ClubOpsStore | None = None,
        finance_service: ClubFinanceService | None = None,
        progression_service: AcademyProgressionService | None = None,
        training_service: AcademyTrainingService | None = None,
        graduation_service: AcademyGraduationService | None = None,
    ) -> None:
        self.store = store or get_club_ops_store()
        self.finance_service = finance_service or get_club_finance_service()
        self.progression_service = progression_service or get_academy_progression_service()
        self.training_service = training_service or get_academy_training_service()
        self.graduation_service = graduation_service or get_academy_graduation_service()

    def get_overview(self, club_id: str) -> AcademyOverviewResponse:
        self._ensure_club_setup(club_id)
        with self.store.lock:
            programs = tuple(self.store.academy_programs_by_club.get(club_id, {}).values())
            players = tuple(self.store.academy_players_by_club.get(club_id, {}).values())
            training_cycles = tuple(self.store.academy_training_cycles_by_club.get(club_id, {}).values())
            graduation_events = tuple(self.store.academy_graduations_by_club.get(club_id, ()))
        return AcademyOverviewResponse(
            club_id=club_id,
            programs=programs,
            players=players,
            training_cycles=training_cycles,
            graduation_events=graduation_events,
            active_enrollment_count=sum(
                1
                for player in players
                if player.status not in {AcademyPlayerStatus.PROMOTED, AcademyPlayerStatus.RELEASED}
            ),
            promoted_count=sum(1 for player in players if player.status == AcademyPlayerStatus.PROMOTED),
        )

    def list_players(self, club_id: str) -> AcademyPlayersResponse:
        self._ensure_club_setup(club_id)
        with self.store.lock:
            players = tuple(self.store.academy_players_by_club.get(club_id, {}).values())
        return AcademyPlayersResponse(club_id=club_id, players=players)

    def list_training_cycles(self, club_id: str) -> AcademyTrainingCyclesResponse:
        self._ensure_club_setup(club_id)
        with self.store.lock:
            cycles = tuple(self.store.academy_training_cycles_by_club.get(club_id, {}).values())
        return AcademyTrainingCyclesResponse(club_id=club_id, training_cycles=cycles)

    def create_program(self, club_id: str, payload: CreateAcademyProgramRequest) -> AcademyProgramView:
        self._ensure_club_setup(club_id)
        program = AcademyProgramView(
            id=f"acp-{uuid4().hex[:12]}",
            club_id=club_id,
            name=payload.name,
            program_type=payload.program_type,
            budget_minor=payload.budget_minor,
            cycle_length_weeks=payload.cycle_length_weeks,
            focus_attributes=payload.focus_attributes or ("technical", "tactical", "physical", "mentality"),
            is_active=True,
            created_at=_utcnow(),
        )
        cycle = self.training_service.create_cycle(club_id=club_id, program=program, cycle_index=1)
        with self.store.lock:
            self.store.academy_programs_by_club.setdefault(club_id, {})[program.id] = program
            self.store.academy_training_cycles_by_club.setdefault(club_id, {})[cycle.id] = cycle
        self.finance_service.record_academy_program_debit(
            club_id,
            amount_minor=payload.budget_minor,
            reference_id=program.id,
            description=f"Academy program budget reserved for {payload.name}.",
        )
        return program

    def create_player(self, club_id: str, payload: CreateAcademyPlayerRequest) -> AcademyPlayerView:
        self._ensure_club_setup(club_id)
        if payload.program_id is not None and payload.program_id not in self.store.academy_programs_by_club.get(club_id, {}):
            raise ValueError("academy_program_not_found")

        development_attributes = dict(payload.development_attributes or {})
        if not development_attributes:
            development_attributes = {
                "technical": 55,
                "tactical": 54,
                "physical": 56,
                "mentality": 55,
            }
        overall_rating = round(sum(development_attributes.values()) / len(development_attributes))
        player = AcademyPlayerView(
            id=f"acpl-{uuid4().hex[:12]}",
            club_id=club_id,
            program_id=payload.program_id,
            display_name=payload.display_name,
            age=payload.age,
            primary_position=payload.primary_position,
            secondary_position=payload.secondary_position,
            status=AcademyPlayerStatus.ENROLLED if payload.program_id else AcademyPlayerStatus.TRIALIST,
            overall_rating=overall_rating,
            readiness_score=overall_rating,
            completed_cycles=0,
            development_attributes=development_attributes,
            last_progressed_at=_utcnow(),
            pathway_note="Academy player registered through the club development pathway.",
        )
        with self.store.lock:
            self.store.academy_players_by_club.setdefault(club_id, {})[player.id] = player
            self.store.academy_progress_by_player.setdefault(player.id, [])
            if payload.program_id is not None:
                latest_cycle = self._latest_cycle_for_program(club_id, payload.program_id)
                if latest_cycle is not None:
                    players_in_program = sum(
                        1
                        for academy_player in self.store.academy_players_by_club[club_id].values()
                        if academy_player.program_id == payload.program_id
                    )
                    self.training_service.refresh_cycle_player_count(
                        cycle=latest_cycle,
                        players_in_program=players_in_program,
                    )
        return player

    def update_player(self, club_id: str, player_id: str, payload: UpdateAcademyPlayerRequest) -> AcademyPlayerView:
        self._ensure_club_setup(club_id)
        with self.store.lock:
            player = self.store.academy_players_by_club.get(club_id, {}).get(player_id)
            if player is None:
                raise ValueError("academy_player_not_found")
        status_before = player.status
        cycle = self._latest_cycle_for_program(club_id, player.program_id) if player.program_id is not None else None
        progress = self.progression_service.apply_progress(
            player=player,
            payload=payload,
            training_cycle_id=cycle.id if cycle is not None else None,
        )
        with self.store.lock:
            self.store.academy_progress_by_player.setdefault(player.id, []).append(progress)
            if cycle is not None:
                self.training_service.register_progress(cycle=cycle, delta_overall=progress.delta_overall)
            if player.status != status_before and player.status in {AcademyPlayerStatus.PROMOTED, AcademyPlayerStatus.RELEASED}:
                reason = (
                    "Promoted through performance-based academy progression."
                    if player.status == AcademyPlayerStatus.PROMOTED
                    else "Released after transparent academy pathway review."
                )
                event = self.graduation_service.build_event(
                    club_id=club_id,
                    player=player,
                    from_status=status_before,
                    to_status=player.status,
                    reason=reason,
                )
                self.store.academy_graduations_by_club.setdefault(club_id, []).append(event)
        return player

    def enroll_prospect(
        self,
        *,
        club_id: str,
        display_name: str,
        age: int,
        primary_position: str,
        secondary_position: str | None,
        program_id: str | None,
        pathway_note: str,
    ) -> AcademyPlayerView:
        player = self.create_player(
            club_id,
            CreateAcademyPlayerRequest(
                program_id=program_id,
                display_name=display_name,
                age=age,
                primary_position=primary_position,
                secondary_position=secondary_position,
                development_attributes={"technical": 58, "tactical": 57, "physical": 60, "mentality": 56},
            ),
        )
        player.status = AcademyPlayerStatus.ENROLLED
        player.pathway_note = pathway_note
        return player

    def _ensure_club_setup(self, club_id: str) -> None:
        self.finance_service.ensure_club_setup(club_id)
        with self.store.lock:
            self.store.academy_programs_by_club.setdefault(club_id, {})
            self.store.academy_players_by_club.setdefault(club_id, {})
            self.store.academy_training_cycles_by_club.setdefault(club_id, {})
            self.store.academy_graduations_by_club.setdefault(club_id, [])

    def _latest_cycle_for_program(self, club_id: str, program_id: str | None):
        if program_id is None:
            return None
        with self.store.lock:
            cycles = [
                cycle
                for cycle in self.store.academy_training_cycles_by_club.get(club_id, {}).values()
                if cycle.program_id == program_id
            ]
        if not cycles:
            return None
        return max(cycles, key=lambda cycle: cycle.cycle_index)


@lru_cache
def get_academy_service() -> AcademyService:
    return AcademyService(
        store=get_club_ops_store(),
        finance_service=get_club_finance_service(),
        progression_service=get_academy_progression_service(),
        training_service=get_academy_training_service(),
        graduation_service=get_academy_graduation_service(),
    )


__all__ = ["AcademyService", "get_academy_service"]
