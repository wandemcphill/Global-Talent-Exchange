from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.common.enums.contract_status import ContractStatus
from backend.app.common.enums.injury_severity import InjurySeverity
from backend.app.common.enums.transfer_bid_status import TransferBidStatus
from backend.app.common.enums.transfer_window_status import TransferWindowStatus
from backend.app.ingestion.models import (
    Club as IngestionClub,
    Competition as IngestionCompetition,
    Player,
    Season,
)
from backend.app.match_engine.schemas import MatchReplayPayloadView
from backend.app.models.base import utcnow
from backend.app.models.club_profile import ClubProfile
from backend.app.models.player_career_entry import PlayerCareerEntry
from backend.app.models.player_contract import PlayerContract
from backend.app.models.player_injury_case import PlayerInjuryCase
from backend.app.models.player_lifecycle_event import PlayerLifecycleEvent
from backend.app.models.transfer_bid import TransferBid
from backend.app.models.transfer_window import TransferWindow
from backend.app.schemas.player_lifecycle import (
    AvailabilityBadgeView,
    CareerEntryView,
    CareerTotalsView,
    ContractBadgeView,
    ContractCreateRequest,
    ContractRenewRequest,
    ContractSummaryView,
    ContractView,
    InjuryCaseView,
    InjuryCreateRequest,
    InjuryRecoveryRequest,
    InjurySummaryView,
    PlayerAvailabilityView,
    PlayerCareerSummaryView,
    PlayerLifecycleEventView,
    PlayerOverviewView,
    PlayerLifecycleSnapshotView,
    SeasonProgressionView,
    TransferBidAcceptRequest,
    TransferBidCreateRequest,
    TransferBidRejectRequest,
    TransferBidView,
    TransferSummaryView,
    TransferWindowEligibilityView,
    TransferWindowView,
)

CONTRACT_EXPIRING_SOON_DAYS = 90
DEFAULT_INJURY_RECOVERY_DAYS: dict[InjurySeverity, int] = {
    InjurySeverity.MINOR: 7,
    InjurySeverity.MODERATE: 21,
    InjurySeverity.MAJOR: 56,
    InjurySeverity.SEASON_ENDING: 180,
}
DEFAULT_MATCH_INJURY_RECOVERY_DAYS = 14
PLAYER_TRANSFER_RECENT_LIMIT = 5
PLAYER_EVENT_LIMIT_DEFAULT = 20
RECENT_OVERVIEW_EVENT_LIMIT = 8
RED_CARD_SUSPENSION_DAYS = 7

SUSPENSION_EVENT_TYPE = "suspension_created"
INJURY_CREATED_EVENT_TYPE = "injury_created"
INJURY_RECOVERED_EVENT_TYPE = "injury_recovered"
CONTRACT_CREATED_EVENT_TYPE = "contract_created"
CONTRACT_RENEWED_EVENT_TYPE = "contract_renewed"
CONTRACT_TERMINATED_EVENT_TYPE = "contract_terminated"
TRANSFER_BID_ACCEPTED_EVENT_TYPE = "transfer_bid_accepted"
TRANSFER_BID_REJECTED_EVENT_TYPE = "transfer_bid_rejected"


class PlayerLifecycleError(Exception):
    """Base lifecycle error."""


class PlayerLifecycleNotFoundError(PlayerLifecycleError):
    """Raised when a lifecycle resource cannot be found."""


class PlayerLifecycleValidationError(PlayerLifecycleError):
    """Raised when lifecycle rules reject a request."""


@dataclass(slots=True)
class ClubSquadEligibilityRecord:
    player: Player
    contract: PlayerContract
    available: bool
    reason: str | None = None
    active_injury: PlayerInjuryCase | None = None
    active_suspension: PlayerLifecycleEvent | None = None


@dataclass(slots=True)
class PlayerLifecycleService:
    session: Session

    def get_career(self, player_id: str) -> list[PlayerCareerEntry]:
        statement = (
            select(PlayerCareerEntry)
            .where(PlayerCareerEntry.player_id == player_id)
            .order_by(PlayerCareerEntry.season_label.desc(), PlayerCareerEntry.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def get_contracts(self, player_id: str) -> list[PlayerContract]:
        statement = (
            select(PlayerContract)
            .where(PlayerContract.player_id == player_id)
            .order_by(PlayerContract.starts_on.desc(), PlayerContract.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def get_club_contracts(self, club_id: str) -> list[PlayerContract]:
        statement = (
            select(PlayerContract)
            .where(PlayerContract.club_id == club_id)
            .order_by(PlayerContract.starts_on.desc(), PlayerContract.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def get_injuries(self, player_id: str) -> list[PlayerInjuryCase]:
        statement = (
            select(PlayerInjuryCase)
            .where(PlayerInjuryCase.player_id == player_id)
            .order_by(PlayerInjuryCase.occurred_on.desc(), PlayerInjuryCase.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def list_events(
        self,
        player_id: str,
        *,
        limit: int = PLAYER_EVENT_LIMIT_DEFAULT,
        event_types: tuple[str, ...] | None = None,
    ) -> list[PlayerLifecycleEvent]:
        self._require_player(player_id)
        statement = select(PlayerLifecycleEvent).where(PlayerLifecycleEvent.player_id == player_id)
        if event_types:
            statement = statement.where(PlayerLifecycleEvent.event_type.in_(event_types))
        statement = statement.order_by(PlayerLifecycleEvent.occurred_on.desc(), PlayerLifecycleEvent.created_at.desc()).limit(limit)
        return list(self.session.scalars(statement))

    def list_transfer_windows(
        self,
        *,
        territory_code: str | None = None,
        active_on: date | None = None,
    ) -> list[TransferWindow]:
        statement = select(TransferWindow).order_by(TransferWindow.opens_on.desc(), TransferWindow.created_at.desc())
        if territory_code:
            statement = statement.where(TransferWindow.territory_code == territory_code)
        if active_on:
            statement = statement.where(TransferWindow.opens_on <= active_on, TransferWindow.closes_on >= active_on)
        return list(self.session.scalars(statement))

    def get_transfer_window(self, window_id: str) -> TransferWindow:
        window = self.session.get(TransferWindow, window_id)
        if window is None:
            raise PlayerLifecycleNotFoundError(f"Transfer window {window_id} was not found")
        return window

    def list_window_bids(self, window_id: str) -> list[TransferBid]:
        statement = (
            select(TransferBid)
            .where(TransferBid.window_id == window_id)
            .order_by(TransferBid.updated_at.desc(), TransferBid.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def list_player_transfer_bids(self, player_id: str) -> list[TransferBid]:
        statement = (
            select(TransferBid)
            .where(TransferBid.player_id == player_id)
            .order_by(TransferBid.updated_at.desc(), TransferBid.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def list_club_squad_status(
        self,
        club_id: str,
        *,
        on_date: date | None = None,
    ) -> tuple[ClubSquadEligibilityRecord, ...]:
        reference_on = on_date or date.today()
        self.apply_pending_transfer_activations(as_of=reference_on)
        active_contracts = [
            contract
            for contract in self.get_club_contracts(club_id)
            if self._resolve_contract_status(contract, reference_on=reference_on) in {ContractStatus.ACTIVE, ContractStatus.EXPIRING}
        ]
        if not active_contracts:
            return ()

        players = self._load_players(contract.player_id for contract in active_contracts)
        records: list[ClubSquadEligibilityRecord] = []
        for contract in active_contracts:
            player = players.get(contract.player_id)
            if player is None:
                continue
            injuries = self.get_injuries(player.id)
            active_injury = self._select_active_injury(injuries, reference_on=reference_on)
            active_suspension = self._select_active_suspension(
                self.list_events(player.id, limit=PLAYER_EVENT_LIMIT_DEFAULT, event_types=(SUSPENSION_EVENT_TYPE,)),
                reference_on=reference_on,
            )
            if active_injury is not None:
                available = False
                reason = f"injured until {(self._resolve_unavailable_until(active_injury) or reference_on).isoformat()}"
            elif active_suspension is not None:
                available = False
                reason = f"suspended until {(active_suspension.effective_to or active_suspension.occurred_on).isoformat()}"
            else:
                available = True
                reason = None
            records.append(
                ClubSquadEligibilityRecord(
                    player=player,
                    contract=contract,
                    available=available,
                    reason=reason,
                    active_injury=active_injury,
                    active_suspension=active_suspension,
                )
            )
        return tuple(
            sorted(
                records,
                key=lambda record: self._club_squad_sort_key(record.player),
                reverse=True,
            )
        )

    def apply_pending_transfer_activations(
        self,
        *,
        as_of: date | None = None,
        player_id: str | None = None,
    ) -> int:
        reference_on = as_of or date.today()
        statement = select(TransferBid).where(TransferBid.status == TransferBidStatus.ACCEPTED.value)
        if player_id is not None:
            statement = statement.where(TransferBid.player_id == player_id)
        activated = 0
        for bid in self.session.scalars(statement):
            terms = dict(bid.structured_terms_json or {})
            contract_starts_raw = terms.get("contract_starts_on")
            if not contract_starts_raw:
                continue
            contract_starts_on = date.fromisoformat(contract_starts_raw)
            if contract_starts_on > reference_on:
                continue
            contract = self.session.get(PlayerContract, terms.get("contract_id")) if terms.get("contract_id") else None
            if contract is None:
                continue
            player = self._require_player(bid.player_id)
            previous_contract = None
            for existing in self.get_contracts(bid.player_id):
                if existing.id == contract.id:
                    continue
                if existing.club_id == bid.selling_club_id and existing.status != ContractStatus.TERMINATED.value:
                    previous_contract = existing
                    break
            if previous_contract is not None and previous_contract.status != ContractStatus.TERMINATED.value:
                previous_contract.status = ContractStatus.TERMINATED.value
                previous_contract.ends_on = min(previous_contract.ends_on, contract_starts_on - timedelta(days=1))
                self._record_event(
                    player_id=player.id,
                    club_id=previous_contract.club_id,
                    event_type=CONTRACT_TERMINATED_EVENT_TYPE,
                    event_status=ContractStatus.TERMINATED.value,
                    occurred_on=reference_on,
                    effective_from=previous_contract.starts_on,
                    effective_to=previous_contract.ends_on,
                    related_entity_type="contract",
                    related_entity_id=previous_contract.id,
                    summary=f"{player.full_name} contract terminated",
                    details={
                        "buying_club_id": bid.buying_club_id,
                        "transfer_bid_id": bid.id,
                    },
                    notes=bid.notes,
                )
            contract.status = self._resolve_new_contract_status(contract.starts_on, contract.ends_on, reference_on=reference_on).value
            bid.status = TransferBidStatus.COMPLETED.value
            terms.setdefault("completed_on", reference_on.isoformat())
            bid.structured_terms_json = terms
            self._sync_player_active_club_affiliation(bid.player_id, reference_on=reference_on)
            activated += 1
        if activated:
            self.session.commit()
        return activated

    def get_career_summary(
        self,
        player_id: str,
        *,
        on_date: date | None = None,
    ) -> PlayerCareerSummaryView:
        reference_on = on_date or date.today()
        self.apply_pending_transfer_activations(as_of=reference_on, player_id=player_id)
        player = self._require_player(player_id)
        career_entries = self.get_career(player_id)
        contracts = self.get_contracts(player_id)
        injuries = self.get_injuries(player_id)
        transfer_bids = self.list_player_transfer_bids(player_id)

        current_contract = self._select_current_contract(contracts, reference_on=reference_on)
        managed_club = self._get_club_profile(
            current_contract.club_id if current_contract is not None and current_contract.club_id else player.current_club_profile_id
        )
        seasonal_progression = self._build_season_progression(player, career_entries)

        return PlayerCareerSummaryView(
            player_id=player.id,
            player_name=player.full_name,
            current_club_id=(
                current_contract.club_id
                if current_contract is not None and current_contract.club_id
                else player.current_club_profile_id or player.current_club_id
            ),
            current_club_name=managed_club.club_name if managed_club is not None else (player.current_club.name if player.current_club is not None else None),
            current_competition_id=player.current_competition_id,
            current_competition_name=player.current_competition.name if player.current_competition is not None else None,
            totals=self._build_career_totals(player, career_entries, progression=seasonal_progression),
            seasonal_progression=seasonal_progression,
            injury_summary=self._build_injury_summary(injuries, reference_on=reference_on),
            contract_summary=self.get_contract_summary(player_id, on_date=reference_on),
            transfer_summary=self._build_transfer_summary(transfer_bids),
            availability=self.get_player_availability(player_id, on_date=reference_on),
        )

    def get_contract_summary(
        self,
        player_id: str,
        *,
        on_date: date | None = None,
    ) -> ContractSummaryView | None:
        reference_on = on_date or date.today()
        self.apply_pending_transfer_activations(as_of=reference_on, player_id=player_id)
        self._require_player(player_id)
        contracts = self.get_contracts(player_id)
        primary_contract = self._select_primary_contract(contracts, reference_on=reference_on)
        if primary_contract is None:
            return None
        status = self._resolve_contract_status(primary_contract, reference_on=reference_on)
        days_remaining = max(0, (primary_contract.ends_on - reference_on).days)
        return ContractSummaryView(
            active_contract=self.to_contract_view(primary_contract, reference_on=reference_on),
            status=status,
            ends_on=primary_contract.ends_on,
            days_remaining=days_remaining,
            expiring_soon=status is ContractStatus.EXPIRING,
        )

    def get_player_availability(
        self,
        player_id: str,
        *,
        on_date: date | None = None,
    ) -> PlayerAvailabilityView:
        reference_on = on_date or date.today()
        self.apply_pending_transfer_activations(as_of=reference_on, player_id=player_id)
        self._require_player(player_id)
        injuries = self.get_injuries(player_id)
        active_injury = self._select_active_injury(injuries, reference_on=reference_on)
        active_suspension = self._select_active_suspension(
            self.list_events(player_id, limit=PLAYER_EVENT_LIMIT_DEFAULT, event_types=(SUSPENSION_EVENT_TYPE,)),
            reference_on=reference_on,
        )
        unavailable_until = self._resolve_unavailable_until(active_injury) if active_injury is not None else None
        suspended_until = active_suspension.effective_to if active_suspension is not None else None
        available = active_injury is None and active_suspension is None
        if active_suspension is not None:
            status_reason = (
                f"Suspended until {suspended_until.isoformat()}"
                if suspended_until is not None
                else "Suspended"
            )
        elif active_injury is not None:
            status_reason = (
                f"Injured until {unavailable_until.isoformat()}"
                if unavailable_until is not None
                else "Injured"
            )
        else:
            status_reason = None
        return PlayerAvailabilityView(
            player_id=player_id,
            available=available,
            checked_on=reference_on,
            active_injury=self.to_injury_view(active_injury) if active_injury is not None else None,
            active_suspension=self.to_event_view(active_suspension) if active_suspension is not None else None,
            unavailable_until=unavailable_until,
            suspended_until=suspended_until,
            status_reason=status_reason,
        )

    def get_transfer_status(
        self,
        player_id: str,
        *,
        on_date: date | None = None,
        territory_code: str | None = None,
    ) -> TransferWindowEligibilityView:
        reference_on = on_date or date.today()
        self.apply_pending_transfer_activations(as_of=reference_on, player_id=player_id)
        player = self._require_player(player_id)
        availability = self.get_player_availability(player_id, on_date=reference_on)
        contract_summary = self.get_contract_summary(player_id, on_date=reference_on)
        bids = self.list_player_transfer_bids(player_id)
        selected_window = self._select_relevant_transfer_window(
            player,
            reference_on=reference_on,
            territory_code=territory_code,
        )
        window_status = (
            self._resolve_window_status(selected_window, reference_on=reference_on)
            if selected_window is not None
            else None
        )
        last_bid = bids[0] if bids else None
        eligible = (
            selected_window is not None
            and window_status is TransferWindowStatus.OPEN
            and contract_summary is not None
            and availability.available
        )
        if selected_window is None:
            reason = "No transfer window configured"
        elif window_status is not TransferWindowStatus.OPEN:
            reason = f"Window is {window_status.value}"
        elif contract_summary is None:
            reason = "Player is not under contract"
        elif not availability.available:
            reason = availability.status_reason or "Player unavailable"
        else:
            reason = None
        return TransferWindowEligibilityView(
            window_id=selected_window.id if selected_window is not None else None,
            window_label=selected_window.label if selected_window is not None else None,
            territory_code=selected_window.territory_code if selected_window is not None else territory_code,
            window_status=window_status,
            window_open=window_status is TransferWindowStatus.OPEN,
            eligible=eligible,
            reason=reason,
            last_bid_status=TransferBidStatus(last_bid.status) if last_bid is not None else None,
            outside_window_exempt=bool((last_bid.structured_terms_json or {}).get("outside_window_exempt")) if last_bid is not None else False,
        )

    def get_player_overview(
        self,
        player_id: str,
        *,
        on_date: date | None = None,
        territory_code: str | None = None,
        event_limit: int = RECENT_OVERVIEW_EVENT_LIMIT,
    ) -> PlayerOverviewView:
        reference_on = on_date or date.today()
        player = self._require_player(player_id)
        career_summary = self.get_career_summary(player_id, on_date=reference_on)
        transfer_status = self.get_transfer_status(player_id, on_date=reference_on, territory_code=territory_code)
        return PlayerOverviewView(
            player_id=player.id,
            player_name=player.full_name,
            position=player.normalized_position or player.position,
            market_value_eur=player.market_value_eur,
            overview_generated_on=reference_on,
            career_summary=career_summary,
            availability_badge=self._build_availability_badge(career_summary.availability),
            contract_badge=self._build_contract_badge(career_summary.contract_summary),
            transfer_status=transfer_status,
            recent_events=tuple(
                self.to_event_view(event)
                for event in self.list_events(player_id, limit=event_limit)
            ),
        )

    def get_player_lifecycle_snapshot(
        self,
        player_id: str,
        *,
        on_date: date | None = None,
        territory_code: str | None = None,
        event_limit: int = RECENT_OVERVIEW_EVENT_LIMIT,
    ) -> PlayerLifecycleSnapshotView:
        overview = self.get_player_overview(
            player_id,
            on_date=on_date,
            territory_code=territory_code,
            event_limit=event_limit,
        )
        return PlayerLifecycleSnapshotView(
            player_id=overview.player_id,
            player_name=overview.player_name,
            position=overview.position,
            market_value_eur=overview.market_value_eur,
            snapshot_generated_on=overview.overview_generated_on,
            career_summary=overview.career_summary,
            availability_badge=overview.availability_badge,
            contract_badge=overview.contract_badge,
            transfer_status=overview.transfer_status,
            recent_events=overview.recent_events,
        )

    def create_injury_case(
        self,
        player_id: str,
        payload: InjuryCreateRequest,
        *,
        reference_on: date | None = None,
    ) -> PlayerInjuryCase:
        player = self._require_player(player_id)
        resolved_club_id = payload.club_id or player.current_club_profile_id
        if resolved_club_id is not None:
            self._require_club_profile(resolved_club_id)
        occurred_on = payload.occurred_on or reference_on or date.today()
        if self._select_active_injury(self.get_injuries(player_id), reference_on=occurred_on) is not None:
            raise PlayerLifecycleValidationError(f"Player {player_id} already has an active injury")

        expected_return_on, recovery_days = self._resolve_recovery_schedule(
            occurred_on=occurred_on,
            severity=payload.severity,
            expected_return_on=payload.expected_return_on,
            recovery_days=payload.recovery_days,
        )
        injury = PlayerInjuryCase(
            player_id=player.id,
            club_id=resolved_club_id,
            severity=payload.severity.value,
            injury_type=payload.injury_type,
            occurred_on=occurred_on,
            expected_return_on=expected_return_on,
            recovered_on=None,
            source_match_id=payload.source_match_id,
            recovery_days=recovery_days,
            notes=payload.notes,
            last_availability_sync_at=utcnow(),
        )
        self.session.add(injury)
        self.session.flush()
        self._record_event(
            player_id=player.id,
            club_id=injury.club_id,
            event_type=INJURY_CREATED_EVENT_TYPE,
            event_status="active",
            occurred_on=occurred_on,
            effective_from=occurred_on,
            effective_to=expected_return_on,
            related_entity_type="injury_case",
            related_entity_id=injury.id,
            summary=f"{player.full_name} injured: {payload.injury_type}",
            details={
                "severity": payload.severity.value,
                "expected_return_on": expected_return_on.isoformat(),
                "recovery_days": recovery_days,
                "source_match_id": payload.source_match_id,
            },
            notes=payload.notes,
        )
        self.session.commit()
        self.session.refresh(injury)
        return injury

    def recover_injury(
        self,
        player_id: str,
        injury_id: str,
        payload: InjuryRecoveryRequest,
        *,
        reference_on: date | None = None,
    ) -> PlayerInjuryCase:
        player = self._require_player(player_id)
        injury = self._require_injury(player_id, injury_id)
        recovered_on = payload.recovered_on or reference_on or date.today()
        if recovered_on < injury.occurred_on:
            raise PlayerLifecycleValidationError("Recovery date cannot be before the injury occurred")
        injury.recovered_on = recovered_on
        injury.notes = self._merge_notes(injury.notes, payload.notes)
        injury.last_availability_sync_at = utcnow()
        self._resolve_related_event(
            player_id=player_id,
            event_type=INJURY_CREATED_EVENT_TYPE,
            related_entity_type="injury_case",
            related_entity_id=injury.id,
            resolved_at=utcnow(),
        )
        self._record_event(
            player_id=player.id,
            club_id=injury.club_id,
            event_type=INJURY_RECOVERED_EVENT_TYPE,
            event_status="resolved",
            occurred_on=recovered_on,
            effective_from=injury.occurred_on,
            effective_to=recovered_on,
            related_entity_type="injury_case",
            related_entity_id=injury.id,
            summary=f"{player.full_name} recovered from {injury.injury_type}",
            details={
                "injury_type": injury.injury_type,
                "original_return_on": self._serialize_date(self._resolve_unavailable_until(injury)),
            },
            notes=payload.notes,
        )
        self.session.commit()
        self.session.refresh(injury)
        return injury

    def create_contract(
        self,
        player_id: str,
        payload: ContractCreateRequest,
        *,
        reference_on: date | None = None,
    ) -> PlayerContract:
        player = self._require_player(player_id)
        self._require_club_profile(payload.club_id)
        reference_date = reference_on or payload.signed_on or payload.starts_on
        self._validate_contract_dates(starts_on=payload.starts_on, ends_on=payload.ends_on)
        self._validate_contract_overlap(
            player_id,
            starts_on=payload.starts_on,
            ends_on=payload.ends_on,
        )
        contract = PlayerContract(
            player_id=player_id,
            club_id=payload.club_id,
            status=(payload.status or self._resolve_new_contract_status(payload.starts_on, payload.ends_on, reference_on=reference_date)).value,
            wage_amount=payload.wage_amount,
            bonus_terms=payload.bonus_terms,
            release_clause_amount=payload.release_clause_amount,
            signed_on=payload.signed_on or reference_date,
            starts_on=payload.starts_on,
            ends_on=payload.ends_on,
            extension_option_until=payload.extension_option_until,
        )
        self.session.add(contract)
        self.session.flush()
        if contract.club_id is not None and self._resolve_contract_status(contract, reference_on=reference_date) in {
            ContractStatus.ACTIVE,
            ContractStatus.EXPIRING,
        }:
            player.current_club_profile_id = contract.club_id
        self._record_event(
            player_id=player.id,
            club_id=contract.club_id,
            event_type=CONTRACT_CREATED_EVENT_TYPE,
            event_status=contract.status,
            occurred_on=contract.signed_on,
            effective_from=contract.starts_on,
            effective_to=contract.ends_on,
            related_entity_type="contract",
            related_entity_id=contract.id,
            summary=f"{player.full_name} contract created",
            details={
                "wage_amount": self._serialize_decimal(contract.wage_amount),
                "release_clause_amount": self._serialize_decimal(contract.release_clause_amount),
                "extension_option_until": self._serialize_date(contract.extension_option_until),
            },
            notes=contract.bonus_terms,
        )
        self.session.commit()
        self.session.refresh(contract)
        return contract

    def renew_contract(
        self,
        player_id: str,
        contract_id: str,
        payload: ContractRenewRequest,
        *,
        reference_on: date | None = None,
    ) -> PlayerContract:
        player = self._require_player(player_id)
        contract = self._require_contract(player_id, contract_id)
        if payload.new_ends_on <= contract.ends_on:
            raise PlayerLifecycleValidationError("Contract renewals must extend the current contract end date")
        self._validate_contract_dates(starts_on=contract.starts_on, ends_on=payload.new_ends_on)
        self._validate_contract_overlap(
            player_id,
            starts_on=contract.starts_on,
            ends_on=payload.new_ends_on,
            exclude_contract_id=contract.id,
        )
        contract.ends_on = payload.new_ends_on
        if payload.wage_amount is not None:
            contract.wage_amount = payload.wage_amount
        if payload.bonus_terms is not None:
            contract.bonus_terms = payload.bonus_terms
        if payload.release_clause_amount is not None:
            contract.release_clause_amount = payload.release_clause_amount
        if payload.extension_option_until is not None:
            contract.extension_option_until = payload.extension_option_until
        resolved_status = self._resolve_contract_status(contract, reference_on=reference_on or date.today())
        contract.status = resolved_status.value
        if contract.club_id is not None and resolved_status in {ContractStatus.ACTIVE, ContractStatus.EXPIRING}:
            player.current_club_profile_id = contract.club_id
        self._record_event(
            player_id=player.id,
            club_id=contract.club_id,
            event_type=CONTRACT_RENEWED_EVENT_TYPE,
            event_status=resolved_status.value,
            occurred_on=reference_on or date.today(),
            effective_from=contract.starts_on,
            effective_to=contract.ends_on,
            related_entity_type="contract",
            related_entity_id=contract.id,
            summary=f"{player.full_name} contract renewed",
            details={
                "new_ends_on": contract.ends_on.isoformat(),
                "wage_amount": self._serialize_decimal(contract.wage_amount),
                "release_clause_amount": self._serialize_decimal(contract.release_clause_amount),
            },
            notes=payload.bonus_terms,
        )
        self.session.commit()
        self.session.refresh(contract)
        return contract

    def create_bid(
        self,
        window_id: str,
        payload: TransferBidCreateRequest,
        *,
        submitted_on: date | None = None,
    ) -> TransferBid:
        self._require_player(payload.player_id)
        if payload.buying_club_id is None:
            raise PlayerLifecycleValidationError("Transfer bids require a buying club")
        self._require_club_profile(payload.buying_club_id)
        if payload.selling_club_id is not None:
            self._require_club_profile(payload.selling_club_id)

        reference_on = submitted_on or date.today()
        window = self.get_transfer_window(window_id)
        self._validate_window_access(
            window,
            reference_on=reference_on,
            allow_outside_window=payload.allow_outside_window,
            exemption_reason=payload.exemption_reason,
        )

        active_contract = self._select_current_contract(self.get_contracts(payload.player_id), reference_on=reference_on)
        selling_club_id = payload.selling_club_id
        if active_contract is not None:
            if selling_club_id is not None and selling_club_id != active_contract.club_id:
                raise PlayerLifecycleValidationError("Selling club must match the player's current active contract")
            selling_club_id = active_contract.club_id
        elif selling_club_id is not None:
            raise PlayerLifecycleValidationError("Selling club cannot be set when the player has no active contract")

        if selling_club_id is not None and payload.buying_club_id == selling_club_id:
            raise PlayerLifecycleValidationError("Buying club must be different from the selling club")

        bid = TransferBid(
            window_id=window_id,
            player_id=payload.player_id,
            selling_club_id=selling_club_id,
            buying_club_id=payload.buying_club_id,
            status=TransferBidStatus.SUBMITTED.value,
            bid_amount=payload.bid_amount,
            wage_offer_amount=payload.wage_offer_amount,
            sell_on_clause_pct=payload.sell_on_clause_pct,
            notes=payload.notes,
            structured_terms_json={
                "submitted_on": reference_on.isoformat(),
                "outside_window_exempt": payload.allow_outside_window,
                "exemption_reason": payload.exemption_reason,
            },
        )
        self.session.add(bid)
        self.session.commit()
        self.session.refresh(bid)
        return bid

    def accept_bid(
        self,
        window_id: str,
        bid_id: str,
        payload: TransferBidAcceptRequest,
        *,
        reference_on: date | None = None,
    ) -> TransferBid:
        bid = self._require_bid(window_id, bid_id)
        if bid.status != TransferBidStatus.SUBMITTED.value:
            raise PlayerLifecycleValidationError("Only submitted transfer bids can be accepted")
        if bid.buying_club_id is None:
            raise PlayerLifecycleValidationError("Transfer bid is missing a buying club")
        self._require_club_profile(bid.buying_club_id)

        player = self._require_player(bid.player_id)
        acceptance_on = reference_on or payload.signed_on or payload.contract_starts_on or date.today()
        contract_starts_on = payload.contract_starts_on or acceptance_on
        self._validate_contract_dates(starts_on=contract_starts_on, ends_on=payload.contract_ends_on)
        self._validate_window_access(
            self.get_transfer_window(window_id),
            reference_on=acceptance_on,
            allow_outside_window=bool((bid.structured_terms_json or {}).get("outside_window_exempt")),
            exemption_reason=(bid.structured_terms_json or {}).get("exemption_reason"),
        )

        current_contract = self._select_primary_contract(self.get_contracts(bid.player_id), reference_on=contract_starts_on)
        if current_contract is not None:
            if bid.selling_club_id is not None and current_contract.club_id != bid.selling_club_id:
                raise PlayerLifecycleValidationError("Transfer bid selling club no longer matches the player's contract")
            if current_contract.club_id == bid.buying_club_id:
                raise PlayerLifecycleValidationError("Player is already contracted to the buying club")
            if current_contract.starts_on <= contract_starts_on and current_contract.ends_on >= contract_starts_on:
                current_contract.ends_on = contract_starts_on - timedelta(days=1)
            if contract_starts_on <= acceptance_on:
                current_contract.status = ContractStatus.TERMINATED.value
                self._record_event(
                    player_id=player.id,
                    club_id=current_contract.club_id,
                    event_type=CONTRACT_TERMINATED_EVENT_TYPE,
                    event_status=ContractStatus.TERMINATED.value,
                    occurred_on=acceptance_on,
                    effective_from=current_contract.starts_on,
                    effective_to=current_contract.ends_on,
                    related_entity_type="contract",
                    related_entity_id=current_contract.id,
                    summary=f"{player.full_name} contract terminated",
                    details={
                        "buying_club_id": bid.buying_club_id,
                        "transfer_bid_id": bid.id,
                    },
                    notes=bid.notes,
                )

        self._validate_contract_overlap(
            bid.player_id,
            starts_on=contract_starts_on,
            ends_on=payload.contract_ends_on,
        )

        new_contract = PlayerContract(
            player_id=bid.player_id,
            club_id=bid.buying_club_id,
            status=self._resolve_new_contract_status(
                contract_starts_on,
                payload.contract_ends_on,
                reference_on=acceptance_on,
            ).value,
            wage_amount=payload.wage_amount if payload.wage_amount is not None else (bid.wage_offer_amount or 0),
            bonus_terms=payload.bonus_terms,
            release_clause_amount=payload.release_clause_amount,
            signed_on=payload.signed_on or acceptance_on,
            starts_on=contract_starts_on,
            ends_on=payload.contract_ends_on,
            extension_option_until=payload.extension_option_until,
        )
        self.session.add(new_contract)
        self.session.flush()

        terms = dict(bid.structured_terms_json or {})
        terms.update(
            {
                "accepted_on": acceptance_on.isoformat(),
                "contract_id": new_contract.id,
                "contract_starts_on": contract_starts_on.isoformat(),
                "contract_ends_on": payload.contract_ends_on.isoformat(),
            }
        )
        if contract_starts_on <= acceptance_on:
            bid.status = TransferBidStatus.COMPLETED.value
            terms["completed_on"] = acceptance_on.isoformat()
            self._sync_player_active_club_affiliation(player.id, reference_on=acceptance_on, preferred_profile_id=bid.buying_club_id)
        else:
            bid.status = TransferBidStatus.ACCEPTED.value
            self._sync_player_active_club_affiliation(player.id, reference_on=acceptance_on)
        bid.structured_terms_json = terms

        self._record_event(
            player_id=player.id,
            club_id=new_contract.club_id,
            event_type=CONTRACT_CREATED_EVENT_TYPE,
            event_status=new_contract.status,
            occurred_on=new_contract.signed_on,
            effective_from=new_contract.starts_on,
            effective_to=new_contract.ends_on,
            related_entity_type="contract",
            related_entity_id=new_contract.id,
            summary=f"{player.full_name} contract created",
            details={
                "source": "transfer_acceptance",
                "transfer_bid_id": bid.id,
                "wage_amount": self._serialize_decimal(new_contract.wage_amount),
                "release_clause_amount": self._serialize_decimal(new_contract.release_clause_amount),
            },
            notes=new_contract.bonus_terms,
        )
        self._record_event(
            player_id=player.id,
            club_id=new_contract.club_id,
            event_type=TRANSFER_BID_ACCEPTED_EVENT_TYPE,
            event_status=bid.status,
            occurred_on=acceptance_on,
            effective_from=contract_starts_on,
            effective_to=payload.contract_ends_on,
            related_entity_type="transfer_bid",
            related_entity_id=bid.id,
            summary=f"{player.full_name} transfer accepted",
            details={
                "selling_club_id": bid.selling_club_id,
                "buying_club_id": bid.buying_club_id,
                "bid_amount": self._serialize_decimal(bid.bid_amount),
                "contract_id": new_contract.id,
            },
            notes=bid.notes,
        )
        self.session.commit()
        self.session.refresh(bid)
        self.session.expunge(bid)
        return bid

    def reject_bid(
        self,
        window_id: str,
        bid_id: str,
        payload: TransferBidRejectRequest,
    ) -> TransferBid:
        bid = self._require_bid(window_id, bid_id)
        if bid.status != TransferBidStatus.SUBMITTED.value:
            raise PlayerLifecycleValidationError("Only submitted transfer bids can be rejected")
        player = self._require_player(bid.player_id)
        terms = dict(bid.structured_terms_json or {})
        if payload.reason:
            terms["rejection_reason"] = payload.reason
        bid.status = TransferBidStatus.REJECTED.value
        bid.structured_terms_json = terms
        self._record_event(
            player_id=player.id,
            club_id=bid.selling_club_id or bid.buying_club_id,
            event_type=TRANSFER_BID_REJECTED_EVENT_TYPE,
            event_status=TransferBidStatus.REJECTED.value,
            occurred_on=date.today(),
            effective_from=None,
            effective_to=None,
            related_entity_type="transfer_bid",
            related_entity_id=bid.id,
            summary=f"{player.full_name} transfer rejected",
            details={
                "selling_club_id": bid.selling_club_id,
                "buying_club_id": bid.buying_club_id,
                "bid_amount": self._serialize_decimal(bid.bid_amount),
            },
            notes=payload.reason or bid.notes,
        )
        self.session.commit()
        self.session.refresh(bid)
        return bid

    def persist_match_incidents(
        self,
        *,
        fixture_id: str,
        match_date: date,
        replay_payload: MatchReplayPayloadView,
    ) -> None:
        player_ids = [item.player_id for item in replay_payload.summary.player_stats]
        players = self._load_players(player_ids)
        injury_commentary = self._injury_commentary_by_player(replay_payload)

        for player_stat in replay_payload.summary.player_stats:
            player = players.get(player_stat.player_id)
            if player is None:
                continue

            if player_stat.injured and not self._has_match_injury(player.id, fixture_id):
                if self._select_active_injury(self.get_injuries(player.id), reference_on=match_date) is None:
                    injury = PlayerInjuryCase(
                        player_id=player.id,
                        club_id=player_stat.team_id,
                        severity=InjurySeverity.MODERATE.value,
                        injury_type="Match injury",
                        occurred_on=match_date,
                        expected_return_on=match_date + timedelta(days=DEFAULT_MATCH_INJURY_RECOVERY_DAYS),
                        recovered_on=None,
                        source_match_id=fixture_id,
                        recovery_days=DEFAULT_MATCH_INJURY_RECOVERY_DAYS,
                        notes=injury_commentary.get(player.id),
                        last_availability_sync_at=utcnow(),
                    )
                    self.session.add(injury)
                    self.session.flush()
                    self._record_event(
                        player_id=player.id,
                        club_id=player_stat.team_id,
                        event_type=INJURY_CREATED_EVENT_TYPE,
                        event_status="active",
                        occurred_on=match_date,
                        effective_from=match_date,
                        effective_to=injury.expected_return_on,
                        related_entity_type="injury_case",
                        related_entity_id=injury.id,
                        summary=f"{player.full_name} injured during match",
                        details={
                            "severity": InjurySeverity.MODERATE.value,
                            "source_match_id": fixture_id,
                            "recovery_days": DEFAULT_MATCH_INJURY_RECOVERY_DAYS,
                        },
                        notes=injury.notes,
                    )

            if player_stat.red_card and not self._has_match_suspension(player.id, fixture_id):
                suspension_start = match_date + timedelta(days=1)
                suspension_end = suspension_start + timedelta(days=RED_CARD_SUSPENSION_DAYS)
                self._record_event(
                    player_id=player.id,
                    club_id=player_stat.team_id,
                    event_type=SUSPENSION_EVENT_TYPE,
                    event_status="active",
                    occurred_on=match_date,
                    effective_from=suspension_start,
                    effective_to=suspension_end,
                    related_entity_type="match",
                    related_entity_id=fixture_id,
                    summary=f"{player.full_name} suspended after red card",
                    details={
                        "reason": "red_card",
                        "source_match_id": fixture_id,
                        "suspension_days": RED_CARD_SUSPENSION_DAYS,
                    },
                    notes=None,
                )

        self.session.commit()

    def to_career_entry_view(self, entry: PlayerCareerEntry) -> CareerEntryView:
        return CareerEntryView.model_validate(entry, from_attributes=True)

    def to_contract_view(
        self,
        contract: PlayerContract,
        *,
        reference_on: date | None = None,
    ) -> ContractView:
        return ContractView.model_validate(
            {
                "id": contract.id,
                "player_id": contract.player_id,
                "club_id": contract.club_id,
                "status": self._resolve_contract_status(contract, reference_on=reference_on or date.today()),
                "wage_amount": contract.wage_amount,
                "bonus_terms": contract.bonus_terms,
                "release_clause_amount": contract.release_clause_amount,
                "signed_on": contract.signed_on,
                "starts_on": contract.starts_on,
                "ends_on": contract.ends_on,
                "extension_option_until": contract.extension_option_until,
                "updated_at": contract.updated_at,
            }
        )

    def to_injury_view(self, injury: PlayerInjuryCase | None) -> InjuryCaseView | None:
        if injury is None:
            return None
        return InjuryCaseView.model_validate(
            {
                "id": injury.id,
                "player_id": injury.player_id,
                "club_id": injury.club_id,
                "severity": InjurySeverity(injury.severity),
                "injury_type": injury.injury_type,
                "occurred_on": injury.occurred_on,
                "expected_return_on": self._resolve_unavailable_until(injury),
                "recovered_on": injury.recovered_on,
                "source_match_id": injury.source_match_id,
                "recovery_days": injury.recovery_days,
                "notes": injury.notes,
                "updated_at": injury.updated_at,
            }
        )

    def to_event_view(self, event: PlayerLifecycleEvent | None) -> PlayerLifecycleEventView | None:
        if event is None:
            return None
        return PlayerLifecycleEventView.model_validate(
            {
                "id": event.id,
                "player_id": event.player_id,
                "club_id": event.club_id,
                "event_type": event.event_type,
                "event_status": event.event_status,
                "occurred_on": event.occurred_on,
                "effective_from": event.effective_from,
                "effective_to": event.effective_to,
                "related_entity_type": event.related_entity_type,
                "related_entity_id": event.related_entity_id,
                "summary": event.summary,
                "details_json": event.details_json or {},
                "notes": event.notes,
                "resolved_at": event.resolved_at,
                "updated_at": event.updated_at,
            }
        )

    def to_transfer_window_view(
        self,
        window: TransferWindow,
        *,
        reference_on: date | None = None,
    ) -> TransferWindowView:
        return TransferWindowView.model_validate(
            {
                "id": window.id,
                "territory_code": window.territory_code,
                "label": window.label,
                "status": self._resolve_window_status(window, reference_on=reference_on or date.today()),
                "opens_on": window.opens_on,
                "closes_on": window.closes_on,
                "updated_at": window.updated_at,
            }
        )

    def to_transfer_bid_view(self, bid: TransferBid) -> TransferBidView:
        return TransferBidView.model_validate(
            {
                "id": bid.id,
                "window_id": bid.window_id,
                "player_id": bid.player_id,
                "selling_club_id": bid.selling_club_id,
                "buying_club_id": bid.buying_club_id,
                "status": TransferBidStatus(bid.status),
                "bid_amount": bid.bid_amount,
                "wage_offer_amount": bid.wage_offer_amount,
                "sell_on_clause_pct": bid.sell_on_clause_pct,
                "structured_terms_json": bid.structured_terms_json or {},
                "notes": bid.notes,
                "updated_at": bid.updated_at,
            }
        )

    def _sync_player_active_club_affiliation(
        self,
        player_id: str,
        *,
        reference_on: date,
        preferred_profile_id: str | None = None,
    ) -> None:
        player = self._require_player(player_id)
        contract = self._select_current_contract(self.get_contracts(player_id), reference_on=reference_on)
        if contract is None:
            return
        profile_id = preferred_profile_id or contract.club_id
        if profile_id is not None:
            player.current_club_profile_id = profile_id
            ingestion_club = self._resolve_ingestion_club_for_profile(profile_id)
            if ingestion_club is not None:
                player.current_club_id = ingestion_club.id

    def _resolve_ingestion_club_for_profile(self, club_profile_id: str | None) -> IngestionClub | None:
        profile = self._get_club_profile(club_profile_id)
        if profile is None:
            return None
        candidates = [
            profile.slug,
            profile.club_name,
            profile.short_name,
        ]
        normalized = {item.strip().lower() for item in candidates if item}
        if not normalized:
            return None
        statement = select(IngestionClub)
        for club in self.session.scalars(statement):
            club_tokens = {
                value.strip().lower()
                for value in (club.slug, club.name, getattr(club, "provider_external_id", None))
                if value
            }
            if normalized & club_tokens:
                return club
        return None

    def _require_player(self, player_id: str) -> Player:
        statement = (
            select(Player)
            .options(
                selectinload(Player.current_club).selectinload(IngestionClub.country),
                selectinload(Player.current_competition),
                selectinload(Player.match_stats),
                selectinload(Player.season_stats),
            )
            .where(Player.id == player_id)
        )
        player = self.session.scalar(statement)
        if player is None:
            raise PlayerLifecycleNotFoundError(f"Player {player_id} was not found")
        return player

    def _load_players(self, player_ids) -> dict[str, Player]:
        resolved_ids = tuple(dict.fromkeys(player_ids))
        if not resolved_ids:
            return {}
        statement = (
            select(Player)
            .options(
                selectinload(Player.current_club).selectinload(IngestionClub.country),
                selectinload(Player.current_competition),
                selectinload(Player.match_stats),
                selectinload(Player.season_stats),
            )
            .where(Player.id.in_(resolved_ids))
        )
        return {player.id: player for player in self.session.scalars(statement)}

    def _require_contract(self, player_id: str, contract_id: str) -> PlayerContract:
        contract = self.session.get(PlayerContract, contract_id)
        if contract is None or contract.player_id != player_id:
            raise PlayerLifecycleNotFoundError(f"Contract {contract_id} was not found for player {player_id}")
        return contract

    def _require_injury(self, player_id: str, injury_id: str) -> PlayerInjuryCase:
        injury = self.session.get(PlayerInjuryCase, injury_id)
        if injury is None or injury.player_id != player_id:
            raise PlayerLifecycleNotFoundError(f"Injury case {injury_id} was not found for player {player_id}")
        return injury

    def _require_bid(self, window_id: str, bid_id: str) -> TransferBid:
        bid = self.session.get(TransferBid, bid_id)
        if bid is None or bid.window_id != window_id:
            raise PlayerLifecycleNotFoundError(f"Transfer bid {bid_id} was not found in window {window_id}")
        return bid

    def _get_club_profile(self, club_id: str | None) -> ClubProfile | None:
        if club_id is None:
            return None
        return self.session.get(ClubProfile, club_id)

    def _require_club_profile(self, club_id: str | None) -> ClubProfile:
        profile = self._get_club_profile(club_id)
        if profile is None or not club_id:
            raise PlayerLifecycleNotFoundError(f"Club profile {club_id} was not found")
        return profile

    def _resolve_window_status(
        self,
        window: TransferWindow,
        *,
        reference_on: date,
    ) -> TransferWindowStatus:
        if reference_on < window.opens_on:
            return TransferWindowStatus.UPCOMING
        if reference_on > window.closes_on:
            return TransferWindowStatus.CLOSED
        return TransferWindowStatus.OPEN

    def _resolve_contract_status(
        self,
        contract: PlayerContract,
        *,
        reference_on: date,
    ) -> ContractStatus:
        if contract.status == ContractStatus.TERMINATED.value:
            return ContractStatus.TERMINATED
        if reference_on < contract.starts_on:
            return ContractStatus.AGREED
        if reference_on > contract.ends_on:
            return ContractStatus.EXPIRED
        if (contract.ends_on - reference_on).days <= CONTRACT_EXPIRING_SOON_DAYS:
            return ContractStatus.EXPIRING
        return ContractStatus.ACTIVE

    def _resolve_new_contract_status(
        self,
        starts_on: date,
        ends_on: date,
        *,
        reference_on: date,
    ) -> ContractStatus:
        if reference_on < starts_on:
            return ContractStatus.AGREED
        if reference_on > ends_on:
            return ContractStatus.EXPIRED
        if (ends_on - reference_on).days <= CONTRACT_EXPIRING_SOON_DAYS:
            return ContractStatus.EXPIRING
        return ContractStatus.ACTIVE

    def _resolve_recovery_schedule(
        self,
        *,
        occurred_on: date,
        severity: InjurySeverity,
        expected_return_on: date | None,
        recovery_days: int | None,
    ) -> tuple[date, int]:
        resolved_days = recovery_days or DEFAULT_INJURY_RECOVERY_DAYS[severity]
        resolved_return = expected_return_on or occurred_on + timedelta(days=resolved_days)
        if resolved_return < occurred_on:
            raise PlayerLifecycleValidationError("Expected return date cannot be before the injury occurred")
        if recovery_days is None:
            resolved_days = max(1, (resolved_return - occurred_on).days)
        return resolved_return, resolved_days

    def _resolve_unavailable_until(self, injury: PlayerInjuryCase | None) -> date | None:
        if injury is None:
            return None
        if injury.expected_return_on is not None:
            return injury.expected_return_on
        if injury.recovery_days is not None:
            return injury.occurred_on + timedelta(days=injury.recovery_days)
        severity = InjurySeverity(injury.severity)
        return injury.occurred_on + timedelta(days=DEFAULT_INJURY_RECOVERY_DAYS[severity])

    def _select_active_injury(
        self,
        injuries: list[PlayerInjuryCase],
        *,
        reference_on: date,
    ) -> PlayerInjuryCase | None:
        candidates = [
            injury
            for injury in injuries
            if (injury.recovered_on is None or injury.recovered_on > reference_on)
            and (self._resolve_unavailable_until(injury) or reference_on) >= reference_on
        ]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda injury: (
                self._resolve_unavailable_until(injury) or injury.occurred_on,
                injury.occurred_on,
                injury.created_at,
            ),
        )

    def _select_active_suspension(
        self,
        events: list[PlayerLifecycleEvent],
        *,
        reference_on: date,
    ) -> PlayerLifecycleEvent | None:
        candidates = [
            event
            for event in events
            if event.event_type == SUSPENSION_EVENT_TYPE
            and reference_on >= (event.effective_from or event.occurred_on)
            and (event.effective_to is None or reference_on <= event.effective_to)
            and (event.resolved_at is None or event.resolved_at.date() > reference_on)
        ]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda event: (
                event.effective_to or event.occurred_on,
                event.occurred_on,
                event.created_at,
            ),
        )

    def _select_current_contract(
        self,
        contracts: list[PlayerContract],
        *,
        reference_on: date,
    ) -> PlayerContract | None:
        current = [
            contract
            for contract in contracts
            if self._resolve_contract_status(contract, reference_on=reference_on) in {ContractStatus.ACTIVE, ContractStatus.EXPIRING}
        ]
        if not current:
            return None
        return max(current, key=lambda contract: (contract.starts_on, contract.created_at))

    def _select_primary_contract(
        self,
        contracts: list[PlayerContract],
        *,
        reference_on: date,
    ) -> PlayerContract | None:
        current = self._select_current_contract(contracts, reference_on=reference_on)
        if current is not None:
            return current
        agreed = [
            contract
            for contract in contracts
            if self._resolve_contract_status(contract, reference_on=reference_on) is ContractStatus.AGREED
        ]
        if agreed:
            return min(agreed, key=lambda contract: (contract.starts_on, contract.created_at))
        historical = [contract for contract in contracts if contract.status != ContractStatus.TERMINATED.value]
        if not historical:
            return None
        return max(historical, key=lambda contract: (contract.ends_on, contract.created_at))

    def _validate_contract_dates(self, *, starts_on: date, ends_on: date) -> None:
        if ends_on < starts_on:
            raise PlayerLifecycleValidationError("Contract end date cannot be before the start date")

    def _validate_contract_overlap(
        self,
        player_id: str,
        *,
        starts_on: date,
        ends_on: date,
        exclude_contract_id: str | None = None,
    ) -> None:
        for existing in self.get_contracts(player_id):
            if existing.id == exclude_contract_id or existing.status == ContractStatus.TERMINATED.value:
                continue
            if starts_on <= existing.ends_on and ends_on >= existing.starts_on:
                raise PlayerLifecycleValidationError("Player already has a contract covering that date range")

    def _validate_window_access(
        self,
        window: TransferWindow,
        *,
        reference_on: date,
        allow_outside_window: bool,
        exemption_reason: str | None,
    ) -> None:
        if self._resolve_window_status(window, reference_on=reference_on) is TransferWindowStatus.OPEN:
            return
        if not allow_outside_window:
            raise PlayerLifecycleValidationError(
                f"Transfer window {window.id} is closed on {reference_on.isoformat()}"
            )
        if not exemption_reason:
            raise PlayerLifecycleValidationError("Outside-window transfers require an exemption reason")

    def _build_career_totals(
        self,
        player: Player,
        career_entries: list[PlayerCareerEntry],
        *,
        progression: tuple[SeasonProgressionView, ...] | None = None,
    ) -> CareerTotalsView:
        if progression:
            return CareerTotalsView(
                appearances=sum(item.appearances for item in progression),
                starts=sum(item.starts for item in progression),
                goals=sum(item.goals for item in progression),
                assists=sum(item.assists for item in progression),
                clean_sheets=sum(item.clean_sheets for item in progression),
                saves=sum(item.saves for item in progression),
                minutes=sum(item.minutes for item in progression),
            )
        if player.season_stats:
            return CareerTotalsView(
                appearances=sum(item.appearances or 0 for item in player.season_stats),
                starts=sum(item.starts or 0 for item in player.season_stats),
                goals=sum(item.goals or 0 for item in player.season_stats),
                assists=sum(item.assists or 0 for item in player.season_stats),
                clean_sheets=sum(item.clean_sheets or 0 for item in player.season_stats),
                saves=sum(item.saves or 0 for item in player.season_stats),
                minutes=sum(item.minutes or 0 for item in player.season_stats),
            )
        if player.match_stats:
            return CareerTotalsView(
                appearances=sum(item.appearances or 0 for item in player.match_stats),
                starts=sum(item.starts or 0 for item in player.match_stats),
                goals=sum(item.goals or 0 for item in player.match_stats),
                assists=sum(item.assists or 0 for item in player.match_stats),
                clean_sheets=sum(1 if item.clean_sheet else 0 for item in player.match_stats),
                saves=sum(item.saves or 0 for item in player.match_stats),
                minutes=sum(item.minutes or 0 for item in player.match_stats),
            )
        return CareerTotalsView(
            appearances=sum(item.appearances for item in career_entries),
            starts=0,
            goals=sum(item.goals for item in career_entries),
            assists=sum(item.assists for item in career_entries),
            clean_sheets=0,
            saves=0,
            minutes=0,
        )

    def _build_season_progression(
        self,
        player: Player,
        career_entries: list[PlayerCareerEntry],
    ) -> tuple[SeasonProgressionView, ...]:
        season_ids = {item.season_id for item in player.season_stats if item.season_id}
        club_ids = {item.club_id for item in player.season_stats if item.club_id}
        competition_ids = {item.competition_id for item in player.season_stats if item.competition_id}
        if not player.season_stats:
            season_ids.update({item.season_id for item in player.match_stats if item.season_id})
            club_ids.update({item.club_id for item in player.match_stats if item.club_id})
            competition_ids.update({item.competition_id for item in player.match_stats if item.competition_id})

        season_lookup = {
            season.id: season
            for season in self.session.scalars(select(Season).where(Season.id.in_(season_ids)))
        } if season_ids else {}
        club_lookup = {
            club.id: club.name
            for club in self.session.scalars(select(IngestionClub).where(IngestionClub.id.in_(club_ids)))
        } if club_ids else {}
        competition_lookup = {
            competition.id: competition.name
            for competition in self.session.scalars(select(IngestionCompetition).where(IngestionCompetition.id.in_(competition_ids)))
        } if competition_ids else {}

        rows: dict[tuple[str, str | None, str | None], dict[str, Any]] = {}

        def ensure_row(*, season_label: str, competition_id: str | None, club_id: str | None) -> dict[str, Any]:
            key = (season_label, competition_id, club_id)
            row = rows.get(key)
            if row is None:
                row = {
                    "season_label": season_label,
                    "competition_id": competition_id,
                    "competition_name": competition_lookup.get(competition_id),
                    "club_id": club_id,
                    "club_name": club_lookup.get(club_id),
                    "appearances": 0,
                    "starts": 0,
                    "goals": 0,
                    "assists": 0,
                    "clean_sheets": 0,
                    "saves": 0,
                    "minutes": 0,
                    "average_rating": None,
                    "_season_sort": self._season_sort_key(season_label, season_lookup),
                }
                rows[key] = row
            return row

        if player.season_stats:
            for item in player.season_stats:
                season_label = season_lookup.get(item.season_id).label if item.season_id in season_lookup else "career"
                row = ensure_row(season_label=season_label, competition_id=item.competition_id, club_id=item.club_id)
                row["appearances"] += item.appearances or 0
                row["starts"] += item.starts or 0
                row["goals"] += item.goals or 0
                row["assists"] += item.assists or 0
                row["clean_sheets"] += item.clean_sheets or 0
                row["saves"] += item.saves or 0
                row["minutes"] += item.minutes or 0
                if item.average_rating is not None:
                    row["average_rating"] = item.average_rating
        elif player.match_stats:
            for item in player.match_stats:
                season_label = season_lookup.get(item.season_id).label if item.season_id in season_lookup else "match-log"
                row = ensure_row(season_label=season_label, competition_id=item.competition_id, club_id=item.club_id)
                row["appearances"] += item.appearances or 0
                row["starts"] += item.starts or 0
                row["goals"] += item.goals or 0
                row["assists"] += item.assists or 0
                row["clean_sheets"] += 1 if item.clean_sheet else 0
                row["saves"] += item.saves or 0
                row["minutes"] += item.minutes or 0
                if item.rating is not None:
                    row["average_rating"] = item.rating

        for entry in career_entries:
            row = ensure_row(season_label=entry.season_label, competition_id=None, club_id=entry.club_id)
            row["club_name"] = row["club_name"] or entry.club_name
            row["appearances"] = max(row["appearances"], entry.appearances)
            row["goals"] = max(row["goals"], entry.goals)
            row["assists"] = max(row["assists"], entry.assists)
            if row["average_rating"] is None and entry.average_rating is not None:
                row["average_rating"] = float(entry.average_rating)

        ordered_rows = sorted(
            rows.values(),
            key=lambda row: (row["_season_sort"], row["season_label"], row["competition_name"] or "", row["club_name"] or ""),
            reverse=True,
        )
        return tuple(
            SeasonProgressionView.model_validate(
                {
                    key: value
                    for key, value in row.items()
                    if not key.startswith("_")
                }
            )
            for row in ordered_rows
        )

    def _season_sort_key(
        self,
        season_label: str,
        season_lookup: dict[str, Season],
    ) -> int:
        for season in season_lookup.values():
            if season.label == season_label and season.year_start is not None:
                return season.year_start
        digits = "".join(character for character in season_label if character.isdigit())
        if len(digits) >= 4:
            return int(digits[:4])
        return 0

    def _build_injury_summary(
        self,
        injuries: list[PlayerInjuryCase],
        *,
        reference_on: date,
    ) -> InjurySummaryView:
        active_injury = self._select_active_injury(injuries, reference_on=reference_on)
        return InjurySummaryView(
            active=self.to_injury_view(active_injury),
            total_cases=len(injuries),
            last_occurred_on=injuries[0].occurred_on if injuries else None,
            unavailable_until=self._resolve_unavailable_until(active_injury),
        )

    def _build_transfer_summary(self, bids: list[TransferBid]) -> TransferSummaryView:
        accepted_or_completed = [
            bid
            for bid in bids
            if bid.status in {TransferBidStatus.ACCEPTED.value, TransferBidStatus.COMPLETED.value}
        ]
        completed = [bid for bid in bids if bid.status == TransferBidStatus.COMPLETED.value]
        latest_transfer = max(accepted_or_completed, key=self._transfer_sort_key, default=None)
        return TransferSummaryView(
            total_bids=len(bids),
            accepted_bids=len(accepted_or_completed),
            completed_bids=len(completed),
            last_transfer_on=self._extract_transfer_date(latest_transfer),
            last_transfer_bid_id=latest_transfer.id if latest_transfer is not None else None,
            last_selling_club_id=latest_transfer.selling_club_id if latest_transfer is not None else None,
            last_buying_club_id=latest_transfer.buying_club_id if latest_transfer is not None else None,
            recent_bids=tuple(self.to_transfer_bid_view(bid) for bid in bids[:PLAYER_TRANSFER_RECENT_LIMIT]),
        )

    def _transfer_sort_key(self, bid: TransferBid) -> tuple[date, datetime]:
        return (self._extract_transfer_date(bid) or bid.updated_at.date(), bid.updated_at)

    def _extract_transfer_date(self, bid: TransferBid | None) -> date | None:
        if bid is None:
            return None
        terms = bid.structured_terms_json or {}
        for key in ("completed_on", "accepted_on", "submitted_on"):
            value = terms.get(key)
            if isinstance(value, str):
                try:
                    return date.fromisoformat(value[:10])
                except ValueError:
                    continue
        return bid.updated_at.date()

    def _build_availability_badge(self, availability: PlayerAvailabilityView) -> AvailabilityBadgeView:
        if availability.available:
            return AvailabilityBadgeView(status="available", label="Available", available=True, until=None, reason=None)
        if availability.active_suspension is not None:
            return AvailabilityBadgeView(
                status="suspended",
                label="Suspended",
                available=False,
                until=availability.suspended_until,
                reason=availability.status_reason,
            )
        return AvailabilityBadgeView(
            status="injured",
            label="Injured",
            available=False,
            until=availability.unavailable_until,
            reason=availability.status_reason,
        )

    def _build_contract_badge(self, summary: ContractSummaryView | None) -> ContractBadgeView:
        if summary is None or summary.active_contract is None or summary.status is None:
            return ContractBadgeView(
                status="uncontracted",
                label="No contract",
                club_id=None,
                club_name=None,
                ends_on=None,
                days_remaining=None,
            )
        club = self._get_club_profile(summary.active_contract.club_id) if summary.active_contract.club_id else None
        club_name = club.club_name if club is not None else None
        labels = {
            ContractStatus.ACTIVE: "Active contract",
            ContractStatus.EXPIRING: "Contract expiring",
            ContractStatus.EXPIRED: "Contract expired",
            ContractStatus.TERMINATED: "Contract terminated",
            ContractStatus.AGREED: "Contract agreed",
        }
        return ContractBadgeView(
            status=summary.status.value,
            label=labels.get(summary.status, "Contract"),
            club_id=summary.active_contract.club_id,
            club_name=club_name,
            ends_on=summary.ends_on,
            days_remaining=summary.days_remaining,
        )

    def _select_relevant_transfer_window(
        self,
        player: Player,
        *,
        reference_on: date,
        territory_code: str | None,
    ) -> TransferWindow | None:
        resolved_territory = territory_code or self._infer_territory_code(player)
        windows = self.list_transfer_windows(territory_code=resolved_territory) if resolved_territory else self.list_transfer_windows()
        if not windows:
            return None
        active = [
            window
            for window in windows
            if self._resolve_window_status(window, reference_on=reference_on) is TransferWindowStatus.OPEN
        ]
        if active:
            return min(active, key=lambda window: (window.opens_on, window.created_at))
        upcoming = [window for window in windows if window.opens_on >= reference_on]
        if upcoming:
            return min(upcoming, key=lambda window: (window.opens_on, window.created_at))
        return max(windows, key=lambda window: (window.closes_on, window.created_at))

    def _infer_territory_code(self, player: Player) -> str | None:
        club = player.current_club
        if club is not None and club.country is not None:
            return club.country.fifa_code or club.country.alpha3_code or club.country.alpha2_code
        return None

    def _record_event(
        self,
        *,
        player_id: str,
        club_id: str | None,
        event_type: str,
        event_status: str,
        occurred_on: date,
        effective_from: date | None,
        effective_to: date | None,
        related_entity_type: str | None,
        related_entity_id: str | None,
        summary: str,
        details: dict[str, object] | None,
        notes: str | None,
    ) -> PlayerLifecycleEvent:
        event = PlayerLifecycleEvent(
            player_id=player_id,
            club_id=club_id,
            event_type=event_type,
            event_status=event_status,
            occurred_on=occurred_on,
            effective_from=effective_from,
            effective_to=effective_to,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            summary=summary,
            details_json=details or {},
            notes=notes,
            resolved_at=None,
        )
        self.session.add(event)
        return event

    def _resolve_related_event(
        self,
        *,
        player_id: str,
        event_type: str,
        related_entity_type: str,
        related_entity_id: str,
        resolved_at: datetime,
    ) -> None:
        statement = (
            select(PlayerLifecycleEvent)
            .where(
                PlayerLifecycleEvent.player_id == player_id,
                PlayerLifecycleEvent.event_type == event_type,
                PlayerLifecycleEvent.related_entity_type == related_entity_type,
                PlayerLifecycleEvent.related_entity_id == related_entity_id,
            )
            .order_by(PlayerLifecycleEvent.created_at.desc())
        )
        event = self.session.scalar(statement)
        if event is None:
            return
        event.event_status = "resolved"
        event.resolved_at = resolved_at

    def _has_match_injury(self, player_id: str, fixture_id: str) -> bool:
        statement = select(PlayerInjuryCase.id).where(
            PlayerInjuryCase.player_id == player_id,
            PlayerInjuryCase.source_match_id == fixture_id,
        )
        return self.session.scalar(statement) is not None

    def _has_match_suspension(self, player_id: str, fixture_id: str) -> bool:
        statement = select(PlayerLifecycleEvent.id).where(
            PlayerLifecycleEvent.player_id == player_id,
            PlayerLifecycleEvent.event_type == SUSPENSION_EVENT_TYPE,
            PlayerLifecycleEvent.related_entity_type == "match",
            PlayerLifecycleEvent.related_entity_id == fixture_id,
        )
        return self.session.scalar(statement) is not None

    def _injury_commentary_by_player(self, replay_payload: MatchReplayPayloadView) -> dict[str, str]:
        commentary: dict[str, str] = {}
        for event in replay_payload.timeline.events:
            if event.event_type.value != "injury" or event.primary_player is None:
                continue
            commentary[event.primary_player.player_id] = event.commentary
        return commentary

    def _club_squad_sort_key(self, player: Player) -> tuple[float, float, int]:
        ratings = [stat.average_rating or 0.0 for stat in player.season_stats if stat.average_rating is not None]
        average_rating = max(ratings, default=0.0)
        return (
            float(player.market_value_eur or 0.0),
            average_rating,
            -(player.shirt_number or 999),
        )

    def _merge_notes(self, existing: str | None, new_note: str | None) -> str | None:
        if not new_note:
            return existing
        if not existing:
            return new_note
        return f"{existing}\n{new_note}"

    @staticmethod
    def _serialize_decimal(value: Any) -> str | None:
        return None if value is None else str(value)

    @staticmethod
    def _serialize_date(value: date | None) -> str | None:
        return None if value is None else value.isoformat()
