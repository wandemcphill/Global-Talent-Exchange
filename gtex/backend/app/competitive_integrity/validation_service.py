from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.competitive_integrity import Match, MatchControlLog, MatchControllerType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class CompetitiveIntegrityValidationService:
    session: Session

    def build_match_validation(self, match_id: str) -> dict[str, object]:
        match = self.session.get(Match, match_id)
        if match is None:
            raise ValueError("Competitive match was not found.")
        control_logs = list(
            self.session.scalars(
                select(MatchControlLog)
                .where(MatchControlLog.match_id == match.id)
                .order_by(MatchControlLog.timestamp.asc())
            ).all()
        )
        signals: list[dict[str, str]] = []
        anti_cheat_score = 100

        if not control_logs:
            anti_cheat_score -= 25
            signals.append(
                {
                    "code": "missing_control_logs",
                    "severity": "high",
                    "detail": "No controller audit trail was recorded for this match.",
                }
            )

        frozen_controls = sum(1 for item in control_logs if item.controller_type == MatchControllerType.FROZEN)
        if frozen_controls >= 2:
            anti_cheat_score -= 20
            signals.append(
                {
                    "code": "frozen_controller_heavy",
                    "severity": "medium",
                    "detail": "Both sides relied heavily on frozen control states.",
                }
            )

        if match.started_at is None or match.completed_at is None:
            anti_cheat_score -= 20
            signals.append(
                {
                    "code": "incomplete_match_timestamps",
                    "severity": "medium",
                    "detail": "The match timeline is incomplete or missing key timestamps.",
                }
            )
        elif match.completed_at < match.started_at:
            anti_cheat_score -= 40
            signals.append(
                {
                    "code": "invalid_match_timeline",
                    "severity": "high",
                    "detail": "The recorded completion time predates the start time.",
                }
            )

        payload = dict(match.result_payload or {})
        summary = dict(payload.get("summary") or {})
        home_score = int(summary.get("home_score") or 0)
        away_score = int(summary.get("away_score") or 0)
        total_goals = home_score + away_score
        if total_goals >= 10:
            anti_cheat_score -= 15
            signals.append(
                {
                    "code": "extreme_scoreline",
                    "severity": "medium",
                    "detail": "The scoreline crossed the extreme goal threshold and needs review.",
                }
            )

        if match.kickoff_at is not None and match.started_at is not None and match.started_at < match.kickoff_at:
            anti_cheat_score -= 10
            signals.append(
                {
                    "code": "early_start_offset",
                    "severity": "low",
                    "detail": "The match started before the scheduled kickoff.",
                }
            )

        tampering_risk = "low"
        if anti_cheat_score < 55:
            tampering_risk = "high"
        elif anti_cheat_score < 75:
            tampering_risk = "medium"

        recommended_action = "allow"
        if tampering_risk == "high":
            recommended_action = "freeze_rewards_and_review"
        elif tampering_risk == "medium":
            recommended_action = "manual_review"

        return {
            "match_id": match.id,
            "anti_cheat_score": max(0, anti_cheat_score),
            "tampering_risk": tampering_risk,
            "recommended_action": recommended_action,
            "signals": signals,
            "validated_at": _utcnow(),
        }


__all__ = ["CompetitiveIntegrityValidationService"]
