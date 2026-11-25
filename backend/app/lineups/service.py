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


def filed_sheet_view(
    club_id: str,
    selection: object,
    *,
    canonical_ids: dict[str, str] | None = None,
) -> ClubMatchPlanView | None:
    """The lineup screen shows the saved matchday sheet, in the ids that screen already uses."""

    if not isinstance(selection, dict):
        return None
    starter_ids = [str(pid) for pid in (selection.get("starting_xi_ids") or []) if str(pid or "").strip()]
    formation = str(selection.get("formation") or "").strip()
    if len(starter_ids) < 11 or not formation:
        return None
    try:
        formation = validate_formation(formation)
    except ClubMatchPlanError:
        return None

    def show(player_id: str) -> str:
        return (canonical_ids or {}).get(player_id, player_id)

    bench_ids = [str(pid) for pid in (selection.get("bench_ids") or []) if str(pid or "").strip()]
    note = str(selection.get("verdict_reason") or "").strip()
    return ClubMatchPlanView(
        club_id=club_id,
        formation=formation,
        starter_player_ids=[show(player_id) for player_id in starter_ids[:11]],
        bench_player_ids=[show(player_id) for player_id in bench_ids[:7]],
        **({"manager_note": note} if note else {}),
    )


class ClubMatchPlanService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_plan(self, club_id: str) -> ClubMatchPlanView:
        filed = self._filed_sheet(club_id)
        if filed is not None:
            return filed
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
        self._file_with_manager(
            club_id=club_id,
            formation=formation,
            starter_player_ids=list(starter_player_ids),
            bench_player_ids=list(bench_player_ids),
        )
        filed = self._filed_sheet(club_id)
        return filed or self._view(plan)

    def _filed_sheet(self, club_id: str) -> ClubMatchPlanView | None:
        from app.owner_console.models import OwnerClubState, OwnerSquadPlayer

        state = self.session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
        if state is None:
            return None
        selection = dict((state.facilities_json or {}).get("_last_manager_matchday_selection") or {})
        rows = list(
            self.session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all()
        )
        canonical = {
            str(row.id): str(row.player_ref)
            for row in rows
            if row.player_ref
        }
        return filed_sheet_view(club_id, selection, canonical_ids=canonical)

    def _file_with_manager(
        self,
        *,
        club_id: str,
        formation: str,
        starter_player_ids: list[str],
        bench_player_ids: list[str],
    ) -> None:
        from sqlalchemy.orm.attributes import flag_modified

        from app.owner_console.autonomous_staff_engine import select_manager_matchday_lineup
        from app.owner_console.models import OwnerClubState

        state = self.session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
        if state is None:
            return
        facilities = dict(state.facilities_json or {})
        facilities["_owner_lineup_preference"] = {
            "preferred_formation": formation,
            "preferred_player_ids": list(starter_player_ids),
            "preferred_bench_ids": list(bench_player_ids),
            "note": "Owner lineup request from the club lineup",
            "is_non_binding_preference": True,
        }
        state.facilities_json = facilities
        flag_modified(state, "facilities_json")
        try:
            select_manager_matchday_lineup(self.session, state)
        except Exception:
            return

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
