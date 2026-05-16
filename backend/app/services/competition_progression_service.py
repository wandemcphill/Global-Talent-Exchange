from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.competition import Competition
from app.models.competition_entry import CompetitionEntry
from app.models.competition_history_entry import CompetitionHistoryEntry
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_progress_profile import CompetitionProgressProfile
from app.models.competition_reward import CompetitionReward
from app.models.user import User

AMOUNT_QUANTUM = Decimal("0.0001")
TITLE_ORDER = {
    "Rising Challenger": 0,
    "Contender": 1,
    "Podium Finisher": 2,
    "Finalist": 3,
    "Champion": 4,
    "Master": 5,
    "Legend": 6,
}
BADGES_BY_PLACEMENT = {
    1: "treasure_chest_gold",
    2: "treasure_chest_silver",
    3: "treasure_chest_bronze",
}
TITLES_BY_PLACEMENT = {
    1: "Champion",
    2: "Finalist",
    3: "Podium Finisher",
}


@dataclass(slots=True)
class CompetitionProgressionService:
    session: Session

    def sync_competition_results(
        self,
        *,
        competition: Competition,
        standings: Iterable[CompetitionParticipant],
        rewards: Iterable[CompetitionReward],
        resolved_users: dict[str, User | None],
    ) -> list[CompetitionHistoryEntry]:
        standings_list = list(standings)
        reward_by_participant = {reward.participant_id: reward for reward in rewards if reward.participant_id}
        existing_entries = {
            item.subject_id: item
            for item in self.session.scalars(
                select(CompetitionHistoryEntry).where(CompetitionHistoryEntry.competition_id == competition.id)
            ).all()
        }
        updated: list[CompetitionHistoryEntry] = []
        for placement, participant in enumerate(standings_list, start=1):
            reward = reward_by_participant.get(participant.id)
            resolved_user = resolved_users.get(participant.id)
            subject_id = participant.club_id
            history_entry = existing_entries.get(subject_id)
            if history_entry is None:
                history_entry = CompetitionHistoryEntry(
                    competition_id=competition.id,
                    subject_id=subject_id,
                    competition_name=competition.name,
                    currency=competition.currency,
                )
                self.session.add(history_entry)
            badge_code = self._badge_for_placement(placement)
            title_awarded = self._title_for_placement(placement)
            is_ranked = bool(getattr(competition, "is_ranked", True))
            ranking_points_delta = (
                self._ranking_points_for_placement(
                    placement=placement,
                    field_size=len(standings_list),
                )
                if is_ranked
                else 0
            )
            display_name = self._display_name_for(participant=participant, resolved_user=resolved_user)
            history_entry.participant_id = participant.id
            history_entry.reward_id = reward.id if reward is not None else None
            history_entry.resolved_user_id = resolved_user.id if resolved_user is not None else None
            history_entry.competition_name = competition.name
            history_entry.placement = placement
            history_entry.played = int(participant.played or 0)
            history_entry.wins = int(participant.wins or 0)
            history_entry.draws = int(participant.draws or 0)
            history_entry.losses = int(participant.losses or 0)
            history_entry.points = int(participant.points or 0)
            history_entry.earnings_minor = int(reward.amount_minor if reward is not None else 0)
            history_entry.currency = competition.currency
            history_entry.reward_status = reward.status if reward is not None else "not_rewarded"
            history_entry.ledger_transaction_id = reward.ledger_transaction_id if reward is not None else None
            history_entry.badge_code = badge_code
            history_entry.title_awarded = title_awarded
            history_entry.ranking_points_delta = ranking_points_delta
            history_entry.completed_at = competition.completed_at or competition.settled_at
            history_entry.metadata_json = {
                **dict(history_entry.metadata_json or {}),
                "display_name": display_name,
                "ranked": is_ranked,
                "goal_diff": participant.goal_diff,
                "goals_for": participant.goals_for,
                "goals_against": participant.goals_against,
            }
            if reward is not None:
                reward.metadata_json = {
                    **dict(reward.metadata_json or {}),
                    "subject_id": subject_id,
                    "resolved_user_id": resolved_user.id if resolved_user is not None else None,
                    "display_name": display_name,
                    "badge_code": badge_code,
                    "title_awarded": title_awarded,
                    "ranking_points_delta": ranking_points_delta,
                }
            updated.append(history_entry)
        self.session.flush()
        for subject_id in {item.subject_id for item in updated}:
            self._rebuild_profile(subject_id)
        self.session.flush()
        return updated

    def history_for_competition(self, competition_id: str) -> list[CompetitionHistoryEntry]:
        return list(
            self.session.scalars(
                select(CompetitionHistoryEntry)
                .where(CompetitionHistoryEntry.competition_id == competition_id)
                .order_by(CompetitionHistoryEntry.placement.asc(), CompetitionHistoryEntry.created_at.asc())
            ).all()
        )

    def history_map_for_competition(self, competition_id: str) -> dict[str, CompetitionHistoryEntry]:
        return {item.subject_id: item for item in self.history_for_competition(competition_id)}

    def profile_for_subject(self, subject_id: str) -> CompetitionProgressProfile | None:
        return self.session.scalar(
            select(CompetitionProgressProfile).where(CompetitionProgressProfile.subject_id == subject_id)
        )

    def profile_map(self, subject_ids: Iterable[str]) -> dict[str, CompetitionProgressProfile]:
        subject_ids = [item for item in subject_ids if item]
        if not subject_ids:
            return {}
        profiles = self.session.scalars(
            select(CompetitionProgressProfile).where(CompetitionProgressProfile.subject_id.in_(subject_ids))
        ).all()
        return {item.subject_id: item for item in profiles}

    def history_for_subject(self, subject_id: str, *, limit: int = 25) -> list[CompetitionHistoryEntry]:
        return list(
            self.session.scalars(
                select(CompetitionHistoryEntry)
                .where(CompetitionHistoryEntry.subject_id == subject_id)
                .order_by(CompetitionHistoryEntry.completed_at.desc(), CompetitionHistoryEntry.updated_at.desc())
                .limit(limit)
            ).all()
        )

    def _rebuild_profile(self, subject_id: str) -> CompetitionProgressProfile:
        rows = self.history_for_subject(subject_id, limit=500)
        profile = self.profile_for_subject(subject_id)
        if profile is None:
            profile = CompetitionProgressProfile(subject_id=subject_id)
            self.session.add(profile)
        ranking_points = sum(int(item.ranking_points_delta or 0) for item in rows)
        total_wins = sum(int(item.wins or 0) for item in rows)
        championships = sum(1 for item in rows if item.placement == 1)
        podiums = sum(1 for item in rows if item.placement is not None and item.placement <= 3)
        total_earnings_minor = sum(int(item.earnings_minor or 0) for item in rows)
        best_placement = min((item.placement for item in rows if item.placement is not None), default=None)
        badges = {item.badge_code for item in rows if item.badge_code}
        if championships >= 1:
            badges.add("treasure_chest_breakthrough")
        if podiums >= 3:
            badges.add("treasure_chest_consistent")
        if ranking_points >= 250:
            badges.add("treasure_chest_ranked")
        titles = {item.title_awarded for item in rows if item.title_awarded}
        current_title = self._current_title_for(
            championships=championships,
            podiums=podiums,
            ranking_points=ranking_points,
        )
        titles.add(current_title)
        if current_title == "Master":
            titles.add("Champion")
        if current_title == "Legend":
            titles.update({"Champion", "Master"})
        latest_resolved_user_id = next((item.resolved_user_id for item in rows if item.resolved_user_id), None)
        latest_display_name = next(
            (
                str((item.metadata_json or {}).get("display_name"))
                for item in rows
                if (item.metadata_json or {}).get("display_name")
            ),
            None,
        )
        profile.resolved_user_id = latest_resolved_user_id or profile.resolved_user_id
        profile.display_name = latest_display_name or profile.display_name or subject_id
        profile.current_title = current_title
        profile.ranking_points = ranking_points
        profile.total_wins = total_wins
        profile.total_championships = championships
        profile.total_podiums = podiums
        profile.total_competitions = len(rows)
        profile.total_earnings_minor = total_earnings_minor
        profile.best_placement = best_placement
        profile.badges_json = sorted(badges)
        profile.titles_json = sorted(titles, key=lambda item: TITLE_ORDER.get(item, 999))
        profile.metadata_json = {
            **dict(profile.metadata_json or {}),
            "latest_competition_id": rows[0].competition_id if rows else None,
        }
        return profile

    def _display_name_for(self, *, participant: CompetitionParticipant, resolved_user: User | None) -> str:
        if resolved_user is not None and resolved_user.username:
            return resolved_user.username
        if participant.entry_id:
            entry = self.session.get(CompetitionEntry, participant.entry_id)
            if entry is not None:
                user_name = (entry.metadata_json or {}).get("user_name")
                if isinstance(user_name, str) and user_name.strip():
                    return user_name.strip()
        return participant.club_id

    @staticmethod
    def _badge_for_placement(placement: int) -> str | None:
        return BADGES_BY_PLACEMENT.get(placement)

    @staticmethod
    def _title_for_placement(placement: int) -> str | None:
        return TITLES_BY_PLACEMENT.get(placement)

    @staticmethod
    def _ranking_points_for_placement(*, placement: int, field_size: int) -> int:
        if placement == 1:
            return 100
        if placement == 2:
            return 70
        if placement == 3:
            return 50
        scaled = max(field_size - placement + 1, 1)
        return max(10, scaled * 5)

    @staticmethod
    def _current_title_for(*, championships: int, podiums: int, ranking_points: int) -> str:
        if championships >= 10 or ranking_points >= 1000:
            return "Legend"
        if championships >= 5 or ranking_points >= 500:
            return "Master"
        if championships >= 1:
            return "Champion"
        if podiums >= 1:
            return "Contender"
        return "Rising Challenger"

    @staticmethod
    def minor_to_decimal(amount_minor: int) -> Decimal:
        return (Decimal(amount_minor) / Decimal("10000")).quantize(AMOUNT_QUANTUM)


__all__ = ["CompetitionProgressionService"]
