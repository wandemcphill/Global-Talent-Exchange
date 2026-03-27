from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from math import exp

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.live_ops.service import LiveOpsService
from app.models.club_profile import ClubProfile
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.notification_record import NotificationRecord
from app.models.user import User
from app.predictions.models import Prediction, PredictionOutcome

BASE_REWARD = 10.0


class PredictionError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(slots=True)
class PredictionService:
    session: Session
    live_ops_service: LiveOpsService | None = None

    def __post_init__(self) -> None:
        if self.live_ops_service is None:
            self.live_ops_service = LiveOpsService(self.session)

    def list_predictions(
        self,
        *,
        actor: User,
        match_id: str | None = None,
        limit: int = 100,
    ) -> list[Prediction]:
        stmt = select(Prediction).where(Prediction.user_id == actor.id).order_by(Prediction.created_at.desc())
        if match_id is not None:
            stmt = stmt.where(Prediction.match_id == match_id)
        return list(self.session.scalars(stmt.limit(limit)).all())

    def submit_prediction(
        self,
        *,
        actor: User,
        match_id: str,
        predicted_outcome: PredictionOutcome,
        confidence_level: float,
        now: datetime | None = None,
    ) -> Prediction:
        match = self._require_match(match_id)
        current_time = self._coerce_datetime(now)
        if current_time >= self._resolve_kickoff(match):
            raise PredictionError("Predictions lock at kickoff.")
        if match.status != "scheduled":
            raise PredictionError("Predictions can only be submitted before the match starts.")

        prediction = self.session.scalar(
            select(Prediction).where(
                Prediction.user_id == actor.id,
                Prediction.match_id == match_id,
            )
        )
        if prediction is None:
            prediction = Prediction(
                user_id=actor.id,
                match_id=match_id,
                predicted_outcome=predicted_outcome,
                confidence_level=confidence_level,
                difficulty_multiplier=self._difficulty_multiplier(match, predicted_outcome),
            )
            self.session.add(prediction)
        else:
            if prediction.resolved_at is not None:
                raise PredictionError("Resolved predictions cannot be changed.")
            prediction.predicted_outcome = predicted_outcome
            prediction.confidence_level = confidence_level
            prediction.difficulty_multiplier = self._difficulty_multiplier(match, predicted_outcome)
        self.session.flush()
        return prediction

    def resolve_match(
        self,
        *,
        match_id: str,
        actual_outcome: PredictionOutcome | None = None,
        resolved_at: datetime | None = None,
    ) -> list[Prediction]:
        match = self.session.get(CompetitionMatch, match_id)
        outcome = actual_outcome or self._derive_actual_outcome(match)
        if outcome is None:
            return []
        moment = self._coerce_datetime(resolved_at)
        active_events = self.live_ops_service.multiplier_snapshot(as_of=moment)
        predictions = list(
            self.session.scalars(
                select(Prediction).where(
                    Prediction.match_id == match_id,
                    Prediction.resolved_at.is_(None),
                )
            ).all()
        )
        for prediction in predictions:
            correct = prediction.predicted_outcome == outcome
            reward = 0.0
            if correct:
                reward = round(
                    BASE_REWARD
                    * (1 + prediction.confidence_level)
                    * prediction.difficulty_multiplier
                    * active_events.prediction_reward_multiplier,
                    4,
                )
            prediction.actual_outcome = outcome
            prediction.reward_earned = reward
            prediction.resolved_at = moment
            self._store_result_notification(prediction=prediction, correct=correct, reward=reward)
            self.live_ops_service.award_prediction_xp(
                user_id=prediction.user_id,
                prediction_id=prediction.id,
                correct=correct,
                reward=reward,
            )
        self.session.flush()
        return predictions

    def leaderboard(self, *, limit: int = 100) -> list[dict[str, object]]:
        correct_predictions = func.coalesce(
            func.sum(
                case(
                    (Prediction.actual_outcome == Prediction.predicted_outcome, 1),
                    else_=0,
                )
            ),
            0,
        )
        total_rewards = func.coalesce(func.sum(Prediction.reward_earned), 0.0)
        rows = self.session.execute(
            select(
                User.id,
                User.username,
                User.display_name,
                correct_predictions.label("total_correct_predictions"),
                total_rewards.label("total_rewards_earned"),
            )
            .join(Prediction, Prediction.user_id == User.id)
            .group_by(User.id, User.username, User.display_name)
            .order_by(correct_predictions.desc(), total_rewards.desc(), User.username.asc())
            .limit(limit)
        ).all()
        leaderboard: list[dict[str, object]] = []
        for index, row in enumerate(rows, start=1):
            leaderboard.append(
                {
                    "rank": index,
                    "user_id": row.id,
                    "username": row.username,
                    "display_name": row.display_name,
                    "total_correct_predictions": int(row.total_correct_predictions or 0),
                    "total_rewards_earned": float(row.total_rewards_earned or 0.0),
                }
            )
        return leaderboard

    def _require_match(self, match_id: str) -> CompetitionMatch:
        match = self.session.get(CompetitionMatch, match_id)
        if match is None:
            raise PredictionError("Match was not found.")
        return match

    def _resolve_kickoff(self, match: CompetitionMatch) -> datetime:
        if match.scheduled_at is not None:
            return self._coerce_datetime(match.scheduled_at)
        if match.match_date is not None:
            return datetime.combine(match.match_date, time(hour=12, minute=0), tzinfo=UTC)
        return self._coerce_datetime(match.created_at)

    def _derive_actual_outcome(self, match: CompetitionMatch | None) -> PredictionOutcome | None:
        if match is None or match.status != "completed":
            return None
        if match.home_score > match.away_score:
            return PredictionOutcome.HOME_WIN
        if match.away_score > match.home_score:
            return PredictionOutcome.AWAY_WIN
        return PredictionOutcome.DRAW

    def _difficulty_multiplier(self, match: CompetitionMatch, predicted_outcome: PredictionOutcome) -> float:
        probabilities = self._outcome_probabilities(match)
        probability = probabilities[predicted_outcome]
        return round(max(0.8, min(2.5, 0.85 + ((1 - probability) * 1.8))), 4)

    def _outcome_probabilities(self, match: CompetitionMatch) -> dict[PredictionOutcome, float]:
        home_participant = self.session.scalar(
            select(CompetitionParticipant).where(
                CompetitionParticipant.competition_id == match.competition_id,
                CompetitionParticipant.club_id == match.home_club_id,
            )
        )
        away_participant = self.session.scalar(
            select(CompetitionParticipant).where(
                CompetitionParticipant.competition_id == match.competition_id,
                CompetitionParticipant.club_id == match.away_club_id,
            )
        )
        home_strength = self._participant_strength(home_participant, home=True)
        away_strength = self._participant_strength(away_participant, home=False)
        delta = home_strength - away_strength
        home_probability = 1 / (1 + exp(-delta / 14))
        draw_probability = max(0.16, 0.3 - (abs(delta) / 120))
        remaining = max(0.08, 1 - draw_probability)
        home_probability *= remaining
        away_probability = max(0.08, remaining - home_probability)
        total = home_probability + away_probability + draw_probability
        return {
            PredictionOutcome.HOME_WIN: home_probability / total,
            PredictionOutcome.AWAY_WIN: away_probability / total,
            PredictionOutcome.DRAW: draw_probability / total,
        }

    @staticmethod
    def _participant_strength(participant: CompetitionParticipant | None, *, home: bool) -> float:
        if participant is None:
            return 52.0 + (3.0 if home else 0.0)
        return (
            50.0
            + float(participant.points or 0) * 1.6
            + float(participant.goal_diff or 0) * 0.55
            + float(participant.wins or 0) * 0.8
            + (3.0 if home else 0.0)
        )

    def _store_result_notification(self, *, prediction: Prediction, correct: bool, reward: float) -> None:
        self.session.add(
            NotificationRecord(
                user_id=prediction.user_id,
                topic="prediction_result",
                template_key="PREDICTION_RESULT",
                resource_type="prediction",
                resource_id=prediction.id,
                fixture_id=prediction.match_id,
                message=(
                    f"Prediction {'correct' if correct else 'missed'}."
                    + (f" Reward earned: {reward:.2f}." if correct else "")
                )[:255],
                metadata_json={
                    "match_id": prediction.match_id,
                    "prediction_id": prediction.id,
                    "correct": correct,
                    "reward_earned": reward,
                    "non_gambling_reward": True,
                },
            )
        )

    @staticmethod
    def _coerce_datetime(value: datetime | None) -> datetime:
        resolved = value or datetime.now(UTC)
        if resolved.tzinfo is None:
            return resolved.replace(tzinfo=UTC)
        return resolved.astimezone(UTC)


__all__ = ["PredictionError", "PredictionService"]
