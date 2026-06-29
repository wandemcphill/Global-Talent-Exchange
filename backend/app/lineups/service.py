from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.lineups.schemas import ClubMatchPlanView
from app.models.club_match_plan import ClubMatchPlan

FORMATION_OUTFIELD_TOTAL = 10


class ClubMatchPlanError(ValueError):
    """Raised on an invalid lineup/formation."""


def validate_formation(formation: str) -> str:
    text = (formation or "").strip()
    parts = text.split("-")
    if len(parts) < 2:
        raise ClubMatchPlanError("Formation must use at least two lines, e.g. 4-3-3.")
    try:
        lines = [int(part) for part in parts]
    except ValueError as exc:
        raise ClubMatchPlanError("Formation must contain only integers.") from exc
    if any(line <= 0 for line in lines):
        raise ClubMatchPlanError("Formation line counts must be positive.")
    if sum(lines) != FORMATION_OUTFIELD_TOTAL:
        raise ClubMatchPlanError(
            f"Formation outfield lines must sum to {FORMATION_OUTFIELD_TOTAL} (got {sum(lines)})."
        )
    return text


class ClubMatchPlanService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_plan(self, club_id: str) -> ClubMatchPlanView:
        plan = self._plan_for(club_id)
        if plan is None:
            return ClubMatchPlanView(club_id=club_id, formation="4-3-3")
        return self._view(plan)

    def save_plan(
        self,
        *,
        club_id: str,
        formation: str,
        starter_player_ids: list[str],
        bench_player_ids: list[str],
        actor_user_id: str | None = None,
    ) -> ClubMatchPlanView:
        formation = validate_formation(formation)
        if len(starter_player_ids) > 11:
            raise ClubMatchPlanError("A starting lineup can name at most 11 players.")
        plan = self._plan_for(club_id)
        if plan is None:
            plan = ClubMatchPlan(
                club_id=club_id,
                formation=formation,
                starter_player_ids_json=list(starter_player_ids),
                bench_player_ids_json=list(bench_player_ids),
                updated_by_user_id=actor_user_id,
            )
            self.session.add(plan)
        else:
            plan.formation = formation
            plan.starter_player_ids_json = list(starter_player_ids)
            plan.bench_player_ids_json = list(bench_player_ids)
            plan.updated_by_user_id = actor_user_id
        self.session.flush()
        return self._view(plan)

    def _plan_for(self, club_id: str) -> ClubMatchPlan | None:
        return self.session.scalar(
            select(ClubMatchPlan).where(ClubMatchPlan.club_id == club_id)
        )

    def _view(self, plan: ClubMatchPlan) -> ClubMatchPlanView:
        return ClubMatchPlanView(
            club_id=plan.club_id,
            formation=plan.formation,
            starter_player_ids=list(plan.starter_player_ids_json or []),
            bench_player_ids=list(plan.bench_player_ids_json or []),
        )
