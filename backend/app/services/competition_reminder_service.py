from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.competition import Competition
from app.models.competition_participant import CompetitionParticipant
from app.models.notification_record import NotificationRecord

_REMINDER_WINDOWS = (
    ("competition_start_24h", timedelta(hours=24), "24 hours"),
    ("competition_start_1h", timedelta(hours=1), "1 hour"),
    ("competition_start_10m", timedelta(minutes=10), "10 minutes"),
)


@dataclass(slots=True)
class CompetitionReminderService:
    session: Session

    def dispatch_due_reminders(self, *, now: datetime | None = None) -> int:
        resolved_now = _as_utc(now or datetime.now(timezone.utc))
        created = 0
        competitions = self.session.scalars(
            select(Competition).where(Competition.scheduled_start_at.is_not(None))
        ).all()
        for competition in competitions:
            start_at = _as_utc(competition.scheduled_start_at)
            if start_at is None or resolved_now >= start_at:
                continue
            participants = tuple(
                self.session.scalars(
                    select(CompetitionParticipant).where(CompetitionParticipant.competition_id == competition.id)
                ).all()
            )
            if not participants:
                continue
            for template_key, offset, label in _REMINDER_WINDOWS:
                if resolved_now < start_at - offset:
                    continue
                for participant in participants:
                    if self._reminder_exists(
                        user_id=participant.club_id,
                        competition_id=competition.id,
                        template_key=template_key,
                    ):
                        continue
                    self.session.add(
                        NotificationRecord(
                            user_id=participant.club_id,
                            topic="competition_reminder",
                            template_key=template_key,
                            resource_type="competition",
                            resource_id=competition.id,
                            competition_id=competition.id,
                            message=f"{competition.name} starts in {label}.",
                            metadata_json={
                                "competition_id": competition.id,
                                "scheduled_start_at": start_at.isoformat(),
                                "reminder_window": template_key,
                            },
                        )
                    )
                    created += 1
        if created:
            self.session.commit()
        return created

    def _reminder_exists(self, *, user_id: str, competition_id: str, template_key: str) -> bool:
        return (
            self.session.scalar(
                select(NotificationRecord.id).where(
                    NotificationRecord.user_id == user_id,
                    NotificationRecord.competition_id == competition_id,
                    NotificationRecord.template_key == template_key,
                )
            )
            is not None
        )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
