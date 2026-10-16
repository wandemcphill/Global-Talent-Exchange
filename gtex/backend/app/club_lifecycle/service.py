from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.models.base import utcnow
from app.models.club_jersey_design import ClubJerseyDesign
from app.models.club_lifecycle import (
    ClubEligibilityFlag,
    ClubLifecycleAuditEvent,
    ClubLifecycleState,
    ClubOperatingStatus,
    ClubReadinessStatus,
    ClubRegistrationSlot,
    ClubSquadRegistration,
)
from app.models.club_profile import ClubProfile
from app.models.user import KycStatus, User
from app.models.wallet import LedgerBalanceProjection

from .schemas import (
    ClubLifecycleStatus,
    ClubLifecycleView,
    ClubOperatingDashboardView,
    ClubReadinessItemView,
    ClubReadinessView,
    SquadPlayerView,
    SquadRegistrationStatus,
    SquadRegistrationUpsertRequest,
    SquadRegistrationView,
)

MIN_SQUAD_SIZE = 11
POSITION_REQUIREMENTS = {"goalkeeper": 1, "defender": 3, "midfielder": 3, "forward": 1}
TERMINAL_STATES = {
    ClubLifecycleStatus.RESTRICTED,
    ClubLifecycleStatus.SUSPENDED,
    ClubLifecycleStatus.SOLD,
    ClubLifecycleStatus.ARCHIVED,
}


class ClubLifecycleError(ValueError):
    pass


@dataclass(slots=True)
class ClubLifecycleService:
    session: Session

    def get_lifecycle(self, club_id: str) -> ClubLifecycleView:
        club = self._require_club(club_id)
        readiness = self.evaluate_readiness(club_id)
        state = self._get_or_create_lifecycle(club)
        if self._status(state.state) not in TERMINAL_STATES and state.state != readiness.recommended_state.value:
            state.previous_state = state.state
            state.state = readiness.recommended_state.value
            state.readiness_score = readiness.readiness_score
            state.blocked_reason = readiness.blockers[0] if readiness.blockers else None
            self.session.flush()
        return self._map_lifecycle(state, readiness)

    def advance_lifecycle(self, *, actor: User, club_id: str, target_state: ClubLifecycleStatus | None, reason: str | None) -> ClubLifecycleView:
        club = self._require_club(club_id)
        readiness = self.evaluate_readiness(club_id)
        state = self._get_or_create_lifecycle(club)
        previous = self._lifecycle_snapshot(state)
        resolved_state = target_state or readiness.recommended_state
        if resolved_state == ClubLifecycleStatus.ACTIVE and not readiness.competition_eligible:
            raise ClubLifecycleError("club_not_competition_ready")
        if resolved_state == ClubLifecycleStatus.COMPETITION_READY and not readiness.competition_eligible:
            raise ClubLifecycleError("club_not_competition_ready")
        state.previous_state = state.state
        state.state = resolved_state.value
        state.readiness_score = readiness.readiness_score
        state.blocked_reason = readiness.blockers[0] if readiness.blockers else None
        state.advanced_by_user_id = actor.id
        state.metadata_json = {
            **dict(state.metadata_json or {}),
            "last_readiness_recommendation": readiness.recommended_state.value,
        }
        self.session.flush()
        self._add_audit(
            actor=actor,
            club_id=club_id,
            action="lifecycle_advanced",
            previous=previous,
            next_snapshot=self._lifecycle_snapshot(state),
            reason=reason,
        )
        self.session.flush()
        return self._map_lifecycle(state, readiness)

    def evaluate_readiness(self, club_id: str) -> ClubReadinessView:
        club = self._require_club(club_id)
        owner = self.session.get(User, club.owner_user_id)
        squad_players = self._squad_players(club_id)
        registration = self._latest_registration(club_id)
        position_summary = self._position_summary(squad_players)
        eligibility_blocks = self._blocking_eligibility_flags(club_id)
        checklist = [
            self._item(
                "profile_complete",
                "Club profile complete",
                self._profile_complete(club),
                "Name, slug, colors, and home venue are present.",
            ),
            self._item(
                "identity_ready",
                "Badge or kit identity selected",
                self._identity_ready(club),
                "Crest or jersey design is present.",
            ),
            self._item(
                "wallet_funded",
                "Wallet funded",
                self._wallet_funded(club.owner_user_id),
                "Owner wallet has positive projected coin or credit balance.",
            ),
            self._item(
                "minimum_squad",
                "Minimum squad size reached",
                len(squad_players) >= MIN_SQUAD_SIZE,
                f"{len(squad_players)} of {MIN_SQUAD_SIZE} required players assigned.",
            ),
            self._item(
                "position_balance",
                "Position balance valid",
                self._position_balance_valid(position_summary),
                self._position_balance_detail(position_summary),
            ),
            self._item(
                "owner_kyc_verified",
                "Owner KYC verified",
                self._owner_kyc_verified(owner),
                "Owner must have a full verified KYC state.",
            ),
            self._item(
                "no_outstanding_blocks",
                "No outstanding disputes or restrictions",
                not eligibility_blocks,
                "Eligibility flags must be clear.",
            ),
            self._item(
                "squad_registered",
                "Squad registration submitted",
                registration is not None and registration.status in {SquadRegistrationStatus.SUBMITTED.value, SquadRegistrationStatus.LOCKED.value},
                "Submit and lock the launch squad before competition entry.",
            ),
        ]
        complete_count = sum(1 for item in checklist if item.complete)
        readiness_score = int(round((complete_count / len(checklist)) * 100))
        blockers = [item.key for item in checklist if not item.complete]
        competition_eligible = not blockers
        recommended_state = self._recommended_state(checklist, registration)
        status = self._get_or_create_readiness(club_id)
        status.readiness_score = readiness_score
        status.checklist_json = {item.key: item.model_dump(mode="json") for item in checklist}
        status.blockers_json = blockers
        status.recommended_state = recommended_state.value
        status.competition_eligible = competition_eligible
        self.session.flush()
        return ClubReadinessView(
            club_id=club_id,
            readiness_score=readiness_score,
            recommended_state=recommended_state,
            competition_eligible=competition_eligible,
            checklist=checklist,
            blockers=blockers,
            updated_at=status.updated_at,
        )

    def get_squad_registration(self, club_id: str, *, season_label: str = "launch") -> SquadRegistrationView | None:
        registration = self._registration(club_id, season_label)
        return None if registration is None else self._map_registration(registration)

    def upsert_squad_registration(
        self,
        *,
        actor: User,
        club_id: str,
        payload: SquadRegistrationUpsertRequest,
    ) -> SquadRegistrationView:
        self._require_club(club_id)
        registration = self._registration(club_id, payload.season_label)
        if registration is not None and registration.status == SquadRegistrationStatus.LOCKED.value:
            raise ClubLifecycleError("squad_registration_locked")
        player_ids = self._normalize_player_ids(payload.player_ids)
        if not player_ids:
            player_ids = [player.id for player in self._squad_players(club_id)]
        players = self._players_for_registration(club_id, player_ids)
        if len(players) != len(player_ids):
            raise ClubLifecycleError("squad_player_not_found_or_not_owned_by_club")
        if registration is None:
            registration = ClubSquadRegistration(club_id=club_id, season_label=payload.season_label)
            self.session.add(registration)
            self.session.flush()
        previous = self._registration_snapshot(registration)
        registration.status = SquadRegistrationStatus.DRAFT.value
        registration.player_ids_json = player_ids
        registration.position_summary_json = self._position_summary(players)
        registration.submitted_at = None
        self._replace_slots(registration, players, slot_status=SquadRegistrationStatus.DRAFT.value)
        self.session.flush()
        self._add_audit(
            actor=actor,
            club_id=club_id,
            action="squad_registration_upserted",
            previous=previous,
            next_snapshot=self._registration_snapshot(registration),
        )
        self.session.flush()
        self.evaluate_readiness(club_id)
        return self._map_registration(registration)

    def submit_squad_registration(self, *, actor: User, club_id: str, season_label: str = "launch") -> SquadRegistrationView:
        registration = self._require_registration(club_id, season_label)
        if registration.status == SquadRegistrationStatus.LOCKED.value:
            raise ClubLifecycleError("squad_registration_locked")
        players = self._players_for_registration(club_id, list(registration.player_ids_json or []))
        self._validate_registration(players)
        previous = self._registration_snapshot(registration)
        registration.status = SquadRegistrationStatus.SUBMITTED.value
        registration.submitted_at = utcnow()
        registration.position_summary_json = self._position_summary(players)
        self._replace_slots(registration, players, slot_status=SquadRegistrationStatus.SUBMITTED.value)
        self.session.flush()
        self._add_audit(
            actor=actor,
            club_id=club_id,
            action="squad_registration_submitted",
            previous=previous,
            next_snapshot=self._registration_snapshot(registration),
        )
        self.session.flush()
        self.evaluate_readiness(club_id)
        return self._map_registration(registration)

    def lock_squad_registration(self, *, actor: User, club_id: str, season_label: str = "launch") -> SquadRegistrationView:
        registration = self._require_registration(club_id, season_label)
        players = self._players_for_registration(club_id, list(registration.player_ids_json or []))
        self._validate_registration(players)
        previous = self._registration_snapshot(registration)
        registration.status = SquadRegistrationStatus.LOCKED.value
        registration.locked_at = utcnow()
        registration.locked_by_user_id = actor.id
        registration.position_summary_json = self._position_summary(players)
        self._replace_slots(registration, players, slot_status=SquadRegistrationStatus.LOCKED.value)
        self.session.flush()
        self._add_audit(
            actor=actor,
            club_id=club_id,
            action="squad_registration_locked",
            previous=previous,
            next_snapshot=self._registration_snapshot(registration),
        )
        self.session.flush()
        self.evaluate_readiness(club_id)
        return self._map_registration(registration)

    def operating_dashboard(self, club_id: str) -> ClubOperatingDashboardView:
        lifecycle = self.get_lifecycle(club_id)
        registration = self.get_squad_registration(club_id)
        players = self._squad_players(club_id)
        status = self._get_or_create_operating_status(club_id)
        alerts = list(lifecycle.readiness.blockers)
        status.operating_state = "competition_ready" if lifecycle.readiness.competition_eligible else "setup"
        status.dashboard_json = {
            "player_count": len(players),
            "registered_player_count": len(registration.players) if registration is not None else 0,
            "readiness_score": lifecycle.readiness_score,
        }
        self.session.flush()
        return ClubOperatingDashboardView(
            club_id=club_id,
            lifecycle=lifecycle,
            squad_registration=registration,
            module_links=[
                {"label": "Squad registration", "route": f"/clubs/{club_id}/lifecycle"},
                {"label": "Transfer hub", "route": "/app/market"},
                {"label": "Academy", "route": f"/clubs/{club_id}/academy"},
                {"label": "Sponsorships", "route": f"/clubs/{club_id}/sponsorships"},
            ],
            counts={"players": len(players), "registered": len(registration.players) if registration is not None else 0},
            alerts=alerts,
            updated_at=status.updated_at,
        )

    def _require_club(self, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise LookupError("club_not_found")
        return club

    def _get_or_create_lifecycle(self, club: ClubProfile) -> ClubLifecycleState:
        state = self.session.scalar(select(ClubLifecycleState).where(ClubLifecycleState.club_id == club.id))
        if state is None:
            state = ClubLifecycleState(club_id=club.id, state=ClubLifecycleStatus.CREATED.value)
            self.session.add(state)
            self.session.flush()
        return state

    def _get_or_create_readiness(self, club_id: str) -> ClubReadinessStatus:
        status = self.session.scalar(select(ClubReadinessStatus).where(ClubReadinessStatus.club_id == club_id))
        if status is None:
            status = ClubReadinessStatus(club_id=club_id)
            self.session.add(status)
            self.session.flush()
        return status

    def _get_or_create_operating_status(self, club_id: str) -> ClubOperatingStatus:
        status = self.session.scalar(select(ClubOperatingStatus).where(ClubOperatingStatus.club_id == club_id))
        if status is None:
            status = ClubOperatingStatus(club_id=club_id)
            self.session.add(status)
            self.session.flush()
        return status

    def _registration(self, club_id: str, season_label: str) -> ClubSquadRegistration | None:
        return self.session.scalar(
            select(ClubSquadRegistration).where(
                ClubSquadRegistration.club_id == club_id,
                ClubSquadRegistration.season_label == season_label,
            )
        )

    def _latest_registration(self, club_id: str) -> ClubSquadRegistration | None:
        return self.session.scalar(
            select(ClubSquadRegistration)
            .where(ClubSquadRegistration.club_id == club_id)
            .order_by(ClubSquadRegistration.updated_at.desc())
        )

    def _require_registration(self, club_id: str, season_label: str) -> ClubSquadRegistration:
        registration = self._registration(club_id, season_label)
        if registration is None:
            raise ClubLifecycleError("squad_registration_not_found")
        return registration

    def _squad_players(self, club_id: str) -> list[Player]:
        return list(
            self.session.scalars(
                select(Player)
                .where(Player.current_club_profile_id == club_id)
                .order_by(Player.normalized_position.asc(), Player.full_name.asc())
            ).all()
        )

    def _players_for_registration(self, club_id: str, player_ids: list[str]) -> list[Player]:
        if not player_ids:
            return []
        players = list(
            self.session.scalars(
                select(Player).where(Player.id.in_(player_ids), Player.current_club_profile_id == club_id)
            ).all()
        )
        by_id = {player.id: player for player in players}
        return [by_id[player_id] for player_id in player_ids if player_id in by_id]

    def _replace_slots(self, registration: ClubSquadRegistration, players: list[Player], *, slot_status: str) -> None:
        self.session.execute(delete(ClubRegistrationSlot).where(ClubRegistrationSlot.registration_id == registration.id))
        for player in players:
            self.session.add(
                ClubRegistrationSlot(
                    registration_id=registration.id,
                    club_id=registration.club_id,
                    player_id=player.id,
                    position_group=self._position_group(player.normalized_position or player.position),
                    slot_status=slot_status,
                )
            )

    def _validate_registration(self, players: list[Player]) -> None:
        if len(players) < MIN_SQUAD_SIZE:
            raise ClubLifecycleError("minimum_squad_size_not_met")
        summary = self._position_summary(players)
        if not self._position_balance_valid(summary):
            raise ClubLifecycleError("position_balance_invalid")

    @staticmethod
    def _normalize_player_ids(player_ids: list[str]) -> list[str]:
        normalized: list[str] = []
        for player_id in player_ids:
            item = player_id.strip()
            if item and item not in normalized:
                normalized.append(item)
        return normalized

    def _profile_complete(self, club: ClubProfile) -> bool:
        return all(
            bool((value or "").strip())
            for value in (club.club_name, club.slug, club.primary_color, club.secondary_color, club.accent_color)
        )

    def _identity_ready(self, club: ClubProfile) -> bool:
        if club.crest_asset_ref:
            return True
        jersey_count = self.session.scalar(
            select(func.count(ClubJerseyDesign.id)).where(ClubJerseyDesign.club_id == club.id)
        )
        return bool(jersey_count)

    def _wallet_funded(self, owner_user_id: str) -> bool:
        balances = self.session.scalars(
            select(LedgerBalanceProjection.balance).where(LedgerBalanceProjection.owner_user_id == owner_user_id)
        ).all()
        return any(Decimal(str(balance)) > Decimal("0") for balance in balances)

    @staticmethod
    def _owner_kyc_verified(owner: User | None) -> bool:
        if owner is None:
            return False
        return str(owner.kyc_status) in {
            KycStatus.FULLY_VERIFIED.value,
            KycStatus.VERIFIED.value,
            "KycStatus.FULLY_VERIFIED",
            "KycStatus.VERIFIED",
        }

    def _blocking_eligibility_flags(self, club_id: str) -> list[ClubEligibilityFlag]:
        return list(
            self.session.scalars(
                select(ClubEligibilityFlag).where(
                    ClubEligibilityFlag.club_id == club_id,
                    ClubEligibilityFlag.status.in_(["blocked", "restricted", "suspended"]),
                )
            ).all()
        )

    def _position_summary(self, players: list[Player]) -> dict[str, int]:
        summary = {"goalkeeper": 0, "defender": 0, "midfielder": 0, "forward": 0, "other": 0}
        for player in players:
            group = self._position_group(player.normalized_position or player.position)
            summary[group] = summary.get(group, 0) + 1
        return summary

    @staticmethod
    def _position_group(position: str | None) -> str:
        normalized = (position or "").strip().upper()
        if normalized in {"GK", "GOALKEEPER"}:
            return "goalkeeper"
        if normalized in {"CB", "RB", "LB", "RWB", "LWB", "DEFENDER", "DEF"}:
            return "defender"
        if normalized in {"CM", "DM", "CDM", "AM", "CAM", "LM", "RM", "MIDFIELDER", "MID"}:
            return "midfielder"
        if normalized in {"ST", "CF", "RW", "LW", "SS", "FORWARD", "FW", "ATTACKER"}:
            return "forward"
        return "other"

    @staticmethod
    def _position_balance_valid(summary: dict[str, int]) -> bool:
        return all(summary.get(group, 0) >= required for group, required in POSITION_REQUIREMENTS.items())

    @staticmethod
    def _position_balance_detail(summary: dict[str, int]) -> str:
        return ", ".join(f"{group}: {summary.get(group, 0)}/{required}" for group, required in POSITION_REQUIREMENTS.items())

    @staticmethod
    def _item(key: str, label: str, complete: bool, detail: str) -> ClubReadinessItemView:
        return ClubReadinessItemView(key=key, label=label, complete=complete, detail=detail)

    @staticmethod
    def _recommended_state(
        checklist: list[ClubReadinessItemView],
        registration: ClubSquadRegistration | None,
    ) -> ClubLifecycleStatus:
        by_key = {item.key: item.complete for item in checklist}
        if not by_key.get("profile_complete", False):
            return ClubLifecycleStatus.DRAFT
        if not by_key.get("identity_ready", False):
            return ClubLifecycleStatus.IDENTITY_PENDING
        if not by_key.get("wallet_funded", False):
            return ClubLifecycleStatus.WALLET_REQUIRED
        if not by_key.get("minimum_squad", False) or not by_key.get("position_balance", False):
            return ClubLifecycleStatus.SQUAD_BUILDING
        if registration is None or registration.status == SquadRegistrationStatus.DRAFT.value:
            return ClubLifecycleStatus.SQUAD_READY
        if all(item.complete for item in checklist):
            return ClubLifecycleStatus.COMPETITION_READY
        return ClubLifecycleStatus.SQUAD_READY

    @staticmethod
    def _status(value: str | None) -> ClubLifecycleStatus:
        try:
            return ClubLifecycleStatus(value or ClubLifecycleStatus.CREATED.value)
        except ValueError:
            return ClubLifecycleStatus.CREATED

    def _map_lifecycle(self, state: ClubLifecycleState, readiness: ClubReadinessView) -> ClubLifecycleView:
        return ClubLifecycleView(
            club_id=state.club_id,
            state=self._status(state.state),
            previous_state=None if state.previous_state is None else self._status(state.previous_state),
            readiness_score=readiness.readiness_score,
            blocked_reason=state.blocked_reason,
            metadata=dict(state.metadata_json or {}),
            updated_at=state.updated_at,
            readiness=readiness,
        )

    def _map_registration(self, registration: ClubSquadRegistration) -> SquadRegistrationView:
        players = self._players_for_registration(registration.club_id, list(registration.player_ids_json or []))
        return SquadRegistrationView(
            id=registration.id,
            club_id=registration.club_id,
            season_label=registration.season_label,
            status=SquadRegistrationStatus(registration.status),
            players=[
                SquadPlayerView(
                    player_id=player.id,
                    name=player.canonical_display_name or player.full_name,
                    position=player.normalized_position or player.position,
                    position_group=self._position_group(player.normalized_position or player.position),
                )
                for player in players
            ],
            position_summary=dict(registration.position_summary_json or {}),
            submitted_at=registration.submitted_at,
            locked_at=registration.locked_at,
            updated_at=registration.updated_at,
        )

    @staticmethod
    def _lifecycle_snapshot(state: ClubLifecycleState) -> dict[str, Any]:
        return {
            "state": state.state,
            "previous_state": state.previous_state,
            "readiness_score": state.readiness_score,
            "blocked_reason": state.blocked_reason,
            "metadata": dict(state.metadata_json or {}),
        }

    @staticmethod
    def _registration_snapshot(registration: ClubSquadRegistration) -> dict[str, Any]:
        return {
            "season_label": registration.season_label,
            "status": registration.status,
            "player_ids": list(registration.player_ids_json or []),
            "position_summary": dict(registration.position_summary_json or {}),
        }

    def _add_audit(
        self,
        *,
        actor: User,
        club_id: str,
        action: str,
        previous: dict[str, Any],
        next_snapshot: dict[str, Any],
        reason: str | None = None,
    ) -> None:
        self.session.add(
            ClubLifecycleAuditEvent(
                club_id=club_id,
                action=action,
                previous_json=previous,
                next_json=next_snapshot,
                actor_user_id=actor.id,
                reason=reason,
            )
        )
