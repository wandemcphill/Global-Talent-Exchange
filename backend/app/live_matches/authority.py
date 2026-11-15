from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


@dataclass(frozen=True, slots=True)
class MatchTacticalAuthority:
    match_id: str
    home_club_id: str | None
    away_club_id: str | None
    home_manager_user_ids: frozenset[str]
    away_manager_user_ids: frozenset[str]
    authorized_sides: tuple[str, ...]

    @property
    def authorized_side(self) -> str | None:
        return self.authorized_sides[0] if self.authorized_sides else None


def _extract_non_empty_user_ids(record: dict[str, object] | None) -> set[str]:
    if not isinstance(record, dict) or record.get("is_vacant"):
        return set()
    user_ids: set[str] = set()
    for key in ("user_id", "delegate_user_id"):
        value = str(record.get(key) or "").strip()
        if value:
            user_ids.add(value)
    return user_ids


def _appointed_first_team_manager_user_ids(session: Session, club_ids: set[str]) -> frozenset[str]:
    cleaned_club_ids = {str(cid).strip() for cid in club_ids if str(cid or "").strip()}
    if not cleaned_club_ids:
        return frozenset()

    resolved_ids: set[str] = set()

    try:
        from app.owner_console.models import OwnerClubState

        states = session.scalars(select(OwnerClubState).where(OwnerClubState.club_id.in_(cleaned_club_ids))).all()
        for state in states:
            resolved_ids.update(_extract_non_empty_user_ids(state.manager_json))
            facilities = state.facilities_json if isinstance(state.facilities_json, dict) else {}
            executive_staff = facilities.get("_executive_staff")
            if isinstance(executive_staff, dict):
                first_team_manager = executive_staff.get("first_team_manager")
                resolved_ids.update(_extract_non_empty_user_ids(first_team_manager))
    except Exception:
        pass

    try:
        from app.models.club_growth import (
            ClubStaffAssignment,
            ClubStaffContract,
            ClubStaffProfile,
            PersonalManager,
        )

        assignments = session.scalars(
            select(ClubStaffAssignment).where(
                ClubStaffAssignment.club_id.in_(cleaned_club_ids),
                ClubStaffAssignment.role_key == "first_team_manager",
                ClubStaffAssignment.active.is_(True),
            )
        ).all()
        for assignment in assignments:
            contract = session.get(ClubStaffContract, assignment.staff_contract_id)
            if (
                contract is None
                or contract.club_id not in cleaned_club_ids
                or str(contract.status or "").strip().lower() != "active"
            ):
                continue
            profile = session.get(ClubStaffProfile, contract.staff_profile_id)
            if profile is None or not bool(profile.active):
                continue

            market_key = str(profile.market_key or "").strip()
            if market_key.startswith("personal-manager:"):
                market_user_id = market_key.split("personal-manager:", 1)[1].strip()
                if market_user_id:
                    resolved_ids.add(market_user_id)

            for meta in (
                assignment.metadata_json,
                contract.metadata_json,
                profile.metadata_json,
            ):
                if not isinstance(meta, dict):
                    continue
                for key in ("user_id", "delegate_user_id"):
                    candidate = str(meta.get(key) or "").strip()
                    if candidate:
                        resolved_ids.add(candidate)
                personal_manager_id = str(meta.get("personal_manager_id") or "").strip()
                if personal_manager_id:
                    personal_manager = session.get(PersonalManager, personal_manager_id)
                    if personal_manager is not None and str(personal_manager.user_id or "").strip():
                        resolved_ids.add(str(personal_manager.user_id).strip())
    except Exception:
        pass

    return frozenset(resolved_ids)


def resolve_match_tactical_authority(
    *,
    match_id: str,
    user: User | None,
    session_factory=None,
    session: Session | None = None,
    home_team_id: str | None = None,
    away_team_id: str | None = None,
) -> MatchTacticalAuthority:
    home_club_ids: set[str] = set()
    away_club_ids: set[str] = set()
    if str(home_team_id or "").strip():
        home_club_ids.add(str(home_team_id).strip())
    if str(away_team_id or "").strip():
        away_club_ids.add(str(away_team_id).strip())

    def _resolve_with_session(active_session: Session) -> MatchTacticalAuthority:
        try:
            from app.models.competition_match import CompetitionMatch

            comp_match = active_session.get(CompetitionMatch, match_id)
            if comp_match is not None:
                if str(comp_match.home_club_id or "").strip():
                    home_club_ids.add(str(comp_match.home_club_id).strip())
                if str(comp_match.away_club_id or "").strip():
                    away_club_ids.add(str(comp_match.away_club_id).strip())
        except Exception:
            pass

        home_managers = _appointed_first_team_manager_user_ids(active_session, home_club_ids)
        away_managers = _appointed_first_team_manager_user_ids(active_session, away_club_ids)

        user_id = str(getattr(user, "id", "") or "").strip()
        sides: list[str] = []
        if user_id:
            if user_id in home_managers:
                sides.append("home")
            if user_id in away_managers:
                sides.append("away")

        resolved_home = next(iter(sorted(home_club_ids)), None)
        resolved_away = next(iter(sorted(away_club_ids)), None)
        return MatchTacticalAuthority(
            match_id=match_id,
            home_club_id=resolved_home,
            away_club_id=resolved_away,
            home_manager_user_ids=home_managers,
            away_manager_user_ids=away_managers,
            authorized_sides=tuple(sides),
        )

    if session is not None:
        return _resolve_with_session(session)
    if session_factory is not None:
        with session_factory() as opened_session:
            return _resolve_with_session(opened_session)

    resolved_home = next(iter(sorted(home_club_ids)), None)
    resolved_away = next(iter(sorted(away_club_ids)), None)
    return MatchTacticalAuthority(
        match_id=match_id,
        home_club_id=resolved_home,
        away_club_id=resolved_away,
        home_manager_user_ids=frozenset(),
        away_manager_user_ids=frozenset(),
        authorized_sides=(),
    )
