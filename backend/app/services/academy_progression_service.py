from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from uuid import uuid4

from backend.app.common.enums.academy_player_status import AcademyPlayerStatus
from backend.app.schemas.academy_core import AcademyPlayerProgressView, AcademyPlayerView
from backend.app.schemas.club_ops_requests import UpdateAcademyPlayerRequest


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AcademyProgressionService:
    def apply_progress(
        self,
        *,
        player: AcademyPlayerView,
        payload: UpdateAcademyPlayerRequest,
        training_cycle_id: str | None,
    ) -> AcademyPlayerProgressView:
        previous_overall = player.overall_rating
        attributes = dict(player.development_attributes or {})
        if not attributes:
            attributes = {
                "technical": 55,
                "tactical": 54,
                "physical": 56,
                "mentality": 55,
            }

        attendance = payload.attendance_score if payload.attendance_score is not None else 70
        coach_assessment = payload.coach_assessment if payload.coach_assessment is not None else 65
        completed_cycles = player.completed_cycles + payload.completed_cycles_delta
        base_delta = max(-2, min(6, ((attendance - 65) // 10) + ((coach_assessment - 60) // 15) + payload.completed_cycles_delta))

        if payload.attribute_deltas:
            for key, delta in payload.attribute_deltas.items():
                current = attributes.get(key, 55)
                attributes[key] = max(35, min(99, current + delta))
        else:
            for key, current in attributes.items():
                attributes[key] = max(35, min(99, current + base_delta))

        overall_rating = round(sum(attributes.values()) / len(attributes))
        readiness_score = round((overall_rating + attendance + coach_assessment) / 3)

        status_before = player.status
        player.completed_cycles = completed_cycles
        player.development_attributes = attributes
        player.overall_rating = overall_rating
        player.readiness_score = readiness_score
        player.last_progressed_at = _utcnow()
        if payload.pathway_note is not None:
            player.pathway_note = payload.pathway_note

        player.status = self._resolve_status(
            requested_status=payload.status,
            current_status=player.status,
            readiness_score=readiness_score,
            completed_cycles=completed_cycles,
        )

        return AcademyPlayerProgressView(
            id=f"apr-{uuid4().hex[:12]}",
            player_id=player.id,
            training_cycle_id=training_cycle_id,
            status_before=status_before,
            status_after=player.status,
            delta_overall=overall_rating - previous_overall,
            metrics={
                "attendance_score": attendance,
                "coach_assessment": coach_assessment,
                "completed_cycles": completed_cycles,
                "overall_rating": overall_rating,
                "readiness_score": readiness_score,
            },
            created_at=player.last_progressed_at,
        )

    def _resolve_status(
        self,
        *,
        requested_status: AcademyPlayerStatus | None,
        current_status: AcademyPlayerStatus,
        readiness_score: int,
        completed_cycles: int,
    ) -> AcademyPlayerStatus:
        if requested_status in {AcademyPlayerStatus.PROMOTED, AcademyPlayerStatus.RELEASED}:
            return requested_status
        if requested_status in {
            AcademyPlayerStatus.TRIALIST,
            AcademyPlayerStatus.ENROLLED,
            AcademyPlayerStatus.DEVELOPING,
            AcademyPlayerStatus.STANDOUT,
        }:
            return requested_status
        if readiness_score >= 85 and completed_cycles >= 3:
            return AcademyPlayerStatus.PROMOTED
        if readiness_score >= 78:
            return AcademyPlayerStatus.STANDOUT
        if completed_cycles >= 1 or readiness_score >= 60:
            return AcademyPlayerStatus.DEVELOPING
        if current_status == AcademyPlayerStatus.TRIALIST and readiness_score < 55:
            return AcademyPlayerStatus.TRIALIST
        return AcademyPlayerStatus.ENROLLED


@lru_cache
def get_academy_progression_service() -> AcademyProgressionService:
    return AcademyProgressionService()


__all__ = ["AcademyProgressionService", "get_academy_progression_service"]
