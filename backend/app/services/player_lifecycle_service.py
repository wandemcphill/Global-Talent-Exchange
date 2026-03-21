from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.common.enums.contract_status import ContractStatus
from app.common.enums.injury_severity import InjurySeverity
from app.common.enums.transfer_bid_status import TransferBidStatus
from app.common.enums.transfer_window_status import TransferWindowStatus
from app.core.config import Settings, get_settings
from app.ingestion.models import (
    Club as IngestionClub,
    Competition as IngestionCompetition,
    Player,
    Season,
)
from app.match_engine.schemas import MatchReplayPayloadView
from app.models.notification_center import PlatformAnnouncement
from app.models.notification_record import NotificationRecord
from app.models.base import utcnow
from app.models.club_infra import ClubFacility
from app.models.club_profile import ClubProfile
from app.models.player_career_entry import PlayerCareerEntry
from app.models.player_contract import PlayerContract
from app.models.player_injury_case import PlayerInjuryCase
from app.models.player_lifecycle_event import PlayerLifecycleEvent
from app.models.regen import (
    CurrencyConversionQuote,
    MajorTransferAnnouncement,
    RegenBigClubApproach,
    RegenContractOffer,
    RegenOfferVisibilityState,
    RegenOriginMetadata,
    RegenPersonalityProfile,
    RegenProfile,
    RegenTeamDynamicsEffect,
    RegenTransferPressureState,
    RegenUnsettlingEvent,
    TransferHeadlineMediaRecord,
)
from app.models.transfer_bid import TransferBid
from app.models.transfer_window import TransferWindow
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.club_identity.models.reputation import ClubReputationProfile
from app.schemas.player_lifecycle import (
    AvailabilityBadgeView,
    BigClubApproachRequest,
    CareerEntryView,
    CareerTotalsView,
    ContractBadgeView,
    ContractCreateRequest,
    CurrencyBrandingView,
    CurrencyConversionQuoteView,
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
    RegenBidEvaluationView,
    RegenBidResolutionView,
    RegenContractOfferMarketView,
    RegenContractOfferQuoteRequest,
    RegenContractOfferView,
    RegenLifecycleView,
    RegenPressureResolutionRequest,
    RegenPressureStateView,
    RegenSpecialTrainingRequest,
    RegenSpecialTrainingSummaryView,
    RegenTraitSetView,
    RegenTransferListingRequest,
    PlayerOverviewView,
    PlayerLifecycleSnapshotView,
    SeasonProgressionView,
    TeamDynamicsEffectView,
    TransferHeadlineView,
    TransferBidAcceptRequest,
    TransferBidCreateRequest,
    TransferBidRejectRequest,
    TransferBidView,
    TransferSummaryView,
    TransferWindowEligibilityView,
    TransferWindowView,
)
from app.services.regen_transfer_addon import (
    AUTO_CONVERSION_PREMIUM_BPS,
    BigClubApproachInputs,
    ContractOfferScoreInputs,
    TeamDynamicsInputs,
    TransferPressureInputs,
    build_team_dynamics,
    compute_transfer_pressure,
    default_minimum_salary_fancoin,
    default_training_fee_gtex,
    evaluate_big_club_approach,
    quote_conversion,
    render_transfer_headline,
    resolution_for_event,
    score_contract_offer,
    unresolved_days_since,
)
from app.story_feed_engine.service import StoryFeedService
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

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
REGEN_MAX_LIFECYCLE_MONTHS = 36
REGEN_DEVELOPMENT_MONTHS = 9
REGEN_PEAK_MONTHS = 21
REGEN_DECLINE_MONTHS = 30
REGEN_CONTRACT_MIN_DAYS = 300
REGEN_CONTRACT_MAX_DAYS = 366 * 3 + 7
REGEN_FREE_AGENT_PLATFORM_SHARE_PCT = 70
REGEN_FREE_AGENT_PREVIOUS_CLUB_SHARE_PCT = 30
REGEN_SPECIAL_TRAINING_MINOR_MAX = 2
REGEN_SPECIAL_TRAINING_MAJOR_MAX = 1
REGEN_SPECIAL_TRAINING_COOLDOWN_DAYS = 120
REGEN_SPECIAL_TRAINING_SEASON_CAP = 3
REGEN_SPECIAL_TRAINING_CONCURRENT_CAP = 2
REGEN_CONTRACT_OFFER_DECISION_DAYS = 5

GTEX_CURRENCY_BRANDING = CurrencyBrandingView(
    currency_code="coin",
    display_name="GTex Coin",
    icon_key="gtex_coin",
    accent_color="#C49B2C",
    surface_tone="metallic_gold",
)
FANCOIN_CURRENCY_BRANDING = CurrencyBrandingView(
    currency_code="credit",
    display_name="Fan Coin",
    icon_key="fan_coin",
    accent_color="#127A6B",
    surface_tone="supporter_green",
)

SUSPENSION_EVENT_TYPE = "suspension_created"
INJURY_CREATED_EVENT_TYPE = "injury_created"
INJURY_RECOVERED_EVENT_TYPE = "injury_recovered"
CONTRACT_CREATED_EVENT_TYPE = "contract_created"
CONTRACT_RENEWED_EVENT_TYPE = "contract_renewed"
CONTRACT_TERMINATED_EVENT_TYPE = "contract_terminated"
TRANSFER_BID_ACCEPTED_EVENT_TYPE = "transfer_bid_accepted"
TRANSFER_BID_REJECTED_EVENT_TYPE = "transfer_bid_rejected"
REGEN_FREE_AGENCY_EVENT_TYPE = "regen_free_agency_entered"
REGEN_RETIREMENT_EVENT_TYPE = "regen_retired"
REGEN_TRANSFER_LIST_EVENT_TYPE = "regen_transfer_listed"
REGEN_SPECIAL_TRAINING_EVENT_TYPE = "regen_special_training_applied"
REGEN_PLAYING_TIME_REQUEST_EVENT_TYPE = "regen_playing_time_request"
REGEN_CONTRACT_DISSATISFACTION_EVENT_TYPE = "regen_contract_dissatisfaction"
REGEN_BIG_CLUB_APPROACH_EVENT_TYPE = "regen_big_club_approach"
REGEN_PRESSURE_RESOLUTION_EVENT_TYPE = "regen_pressure_resolution"


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
    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

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
        regen = self._get_regen_profile(player_id)
        if regen is not None:
            self._sync_regen_state(
                player,
                regen,
                reference_on=reference_on,
                contract_summary=self.get_contract_summary(player_id, on_date=reference_on),
                bids=transfer_bids,
            )
            self.session.commit()
            self.session.refresh(player)
            self.session.refresh(regen)
            contracts = self.get_contracts(player_id)

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
        regen_summary = self.get_regen_summary(player_id, on_date=reference_on)
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
            and availability.available
            and (contract_summary is not None or (regen_summary is not None and regen_summary.free_agent))
        )
        if selected_window is None:
            reason = "No transfer window configured"
        elif window_status is not TransferWindowStatus.OPEN:
            reason = f"Window is {window_status.value}"
        elif contract_summary is None and not (regen_summary is not None and regen_summary.free_agent):
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
        regen_summary = self.get_regen_summary(player_id, on_date=reference_on)
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
            regen_summary=regen_summary,
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
            regen_summary=overview.regen_summary,
            recent_events=overview.recent_events,
        )

    def get_regen_summary(
        self,
        player_id: str,
        *,
        on_date: date | None = None,
    ) -> RegenLifecycleView | None:
        reference_on = on_date or date.today()
        player = self._require_player(player_id)
        regen = self._get_regen_profile(player_id)
        if regen is None:
            return None
        contract_summary = self.get_contract_summary(player_id, on_date=reference_on)
        bids = self.list_player_transfer_bids(player_id)
        state = self._sync_regen_state(
            player,
            regen,
            reference_on=reference_on,
            contract_summary=contract_summary,
            bids=bids,
        )
        self.session.commit()
        self.session.refresh(regen)
        state = self._regen_career_state(regen)
        traits = RegenTraitSetView.model_validate(self._resolve_regen_traits(regen))
        projected_ceiling = int((regen.potential_range_json or {}).get("maximum", regen.current_gsi))
        current_ceiling = int((regen.current_ability_range_json or {}).get("maximum", regen.current_gsi))
        training_state = self._regen_training_state(regen)
        club_id_for_caps = contract_summary.active_contract.club_id if contract_summary and contract_summary.active_contract else player.current_club_profile_id
        pressure_state = self._ensure_pressure_state(player, regen, reference_on=reference_on, contract_summary=contract_summary)
        offer_market = self._ensure_offer_visibility_state(
            regen,
            reference_on=reference_on,
            current_salary=contract_summary.active_contract.wage_amount if contract_summary and contract_summary.active_contract else Decimal("0.0000"),
        )
        dynamics = self._sync_team_dynamics_effect(player, regen, pressure_state, reference_on=reference_on)
        self.session.commit()
        return RegenLifecycleView(
            regen_id=regen.regen_id,
            status=regen.status,
            lifecycle_phase=str(state.get("lifecycle_phase", "development")),
            lifecycle_age_months=int(state.get("lifecycle_age_months", 0)),
            contract_currency="FanCoin",
            retirement_pressure=bool(state.get("retirement_pressure", False)),
            retired=bool(state.get("retired", False)),
            free_agent=bool(state.get("free_agent", False)),
            free_agent_since=date.fromisoformat(state["free_agent_since"]) if state.get("free_agent_since") else None,
            previous_club_id=state.get("previous_club_id"),
            transfer_listed=bool(state.get("transfer_listed", False)),
            agency_message=state.get("agency_message"),
            personality=traits,
            special_training=RegenSpecialTrainingSummaryView(
                eligible=projected_ceiling <= 75 and not bool(state.get("retired", False)),
                projected_ceiling=projected_ceiling,
                current_ceiling=current_ceiling,
                major_used_count=int(training_state.get("major_used_count", 0)),
                minor_used_count=int(training_state.get("minor_used_count", 0)),
                cooldown_until=date.fromisoformat(training_state["cooldown_until"]) if training_state.get("cooldown_until") else None,
                club_season_slots_used=self._count_regen_special_training_for_club(
                    club_id_for_caps,
                    season_label=self._season_label(reference_on),
                ),
                club_concurrent_slots_used=self._count_regen_special_training_for_club(
                    club_id_for_caps,
                    season_label=self._season_label(reference_on),
                    active_only=True,
                    reference_on=reference_on,
                ),
            ),
            pressure_state=self._to_pressure_state_view(pressure_state),
            team_dynamics=self._to_team_dynamics_view(dynamics),
            free_agent_offer_count=int(offer_market.visible_offer_count if offer_market is not None else 0),
            offer_market=self._to_regen_offer_market_view(offer_market),
        )

    def get_regen_offer_market(
        self,
        player_id: str,
        *,
        on_date: date | None = None,
    ) -> RegenContractOfferMarketView:
        reference_on = on_date or date.today()
        player = self._require_player(player_id)
        regen = self._require_regen_profile(player_id)
        contract_summary = self.get_contract_summary(player_id, on_date=reference_on)
        self._sync_regen_state(
            player,
            regen,
            reference_on=reference_on,
            contract_summary=contract_summary,
            bids=self.list_player_transfer_bids(player_id),
        )
        visibility = self._ensure_offer_visibility_state(
            regen,
            reference_on=reference_on,
            current_salary=contract_summary.active_contract.wage_amount if contract_summary and contract_summary.active_contract else Decimal("0.0000"),
        )
        self.session.commit()
        return self._to_regen_offer_market_view(visibility)

    def quote_regen_contract_offer(
        self,
        player_id: str,
        payload: RegenContractOfferQuoteRequest,
        *,
        reference_on: date | None = None,
    ) -> CurrencyConversionQuoteView:
        effective_date = reference_on or date.today()
        player = self._require_player(player_id)
        regen = self._require_regen_profile(player_id)
        contract_summary = self.get_contract_summary(player_id, on_date=effective_date)
        state = self._sync_regen_state(
            player,
            regen,
            reference_on=effective_date,
            contract_summary=contract_summary,
            bids=self.list_player_transfer_bids(player_id),
        )
        if not bool(state.get("free_agent", False)):
            raise PlayerLifecycleValidationError("Contract-offer quoting is only available for regens in free agency")
        club = self._require_club_profile(payload.offering_club_id)
        owner = self._require_user(club.owner_user_id)
        visibility = self._ensure_offer_visibility_state(
            regen,
            reference_on=effective_date,
            current_salary=contract_summary.active_contract.wage_amount if contract_summary and contract_summary.active_contract else Decimal("0.0000"),
        )
        if payload.offered_salary_fancoin_per_year < visibility.minimum_salary_fancoin_per_year:
            raise PlayerLifecycleValidationError("Salary offer is below the regen minimum for the current market")
        wallet_service = WalletService()
        fancoin_balance = wallet_service.get_wallet_summary(self.session, owner, currency=LedgerUnit.CREDIT).available_balance
        gtex_balance = wallet_service.get_wallet_summary(self.session, owner, currency=LedgerUnit.COIN).available_balance
        conversion = quote_conversion(
            required_fancoin=payload.offered_salary_fancoin_per_year * payload.contract_years,
            current_fancoin_balance=fancoin_balance,
            current_gtex_balance=gtex_balance,
        )
        quote = CurrencyConversionQuote(
            regen_id=regen.id,
            offering_club_id=club.id,
            owner_user_id=owner.id,
            source_unit=LedgerUnit.COIN.value,
            target_unit=LedgerUnit.CREDIT.value,
            required_target_amount=conversion.required_fancoin,
            available_target_amount=conversion.current_fancoin_balance,
            shortfall_target_amount=conversion.shortfall_fancoin,
            available_source_amount=conversion.current_gtex_balance,
            direct_source_equivalent=conversion.direct_gtex_equivalent,
            source_amount_required=conversion.gtex_required_for_conversion,
            premium_bps=conversion.conversion_premium_bps,
            can_cover_shortfall=conversion.can_cover_shortfall,
            expires_on=datetime.combine(effective_date + timedelta(days=1), datetime.min.time()),
            metadata_json={
                "training_fee_gtex_coin": str(visibility.training_fee_gtex_coin),
                "minimum_salary_fancoin_per_year": str(visibility.minimum_salary_fancoin_per_year),
                "premium_note": conversion.premium_note,
            },
        )
        self.session.add(quote)
        self.session.commit()
        self.session.refresh(quote)
        return self._to_conversion_quote_view(quote)

    def record_big_club_approach(
        self,
        player_id: str,
        payload: BigClubApproachRequest,
        *,
        reference_on: date | None = None,
    ) -> RegenLifecycleView:
        effective_date = reference_on or date.today()
        player = self._require_player(player_id)
        regen = self._require_regen_profile(player_id)
        current_contract = self._select_current_contract(self.get_contracts(player_id), reference_on=effective_date)
        current_club_id = current_contract.club_id if current_contract is not None else player.current_club_profile_id
        if current_club_id is None:
            raise PlayerLifecycleValidationError("Only contracted regens can be unsettled by another club")
        approaching_club = self._require_club_profile(payload.approaching_club_id)
        pressure = self._ensure_pressure_state(
            player,
            regen,
            reference_on=effective_date,
            contract_summary=self.get_contract_summary(player_id, on_date=effective_date),
        )
        current_context = self._regen_club_context(current_club_id, regen)
        approaching_context = self._regen_club_context(approaching_club.id, regen)
        if approaching_club.id == current_club_id:
            raise PlayerLifecycleValidationError("A club cannot unsettle its own contracted regen")
        if float(approaching_context["prestige"]) <= float(current_context["prestige"]) and float(approaching_context["trophy_score"]) <= float(current_context["trophy_score"]):
            raise PlayerLifecycleValidationError("Only materially bigger clubs can trigger an unsettling approach")
        current_reputation = self.session.scalar(select(ClubReputationProfile).where(ClubReputationProfile.club_id == current_club_id))
        traits = self._resolve_regen_traits(regen)
        tenure_months = self._months_between((current_contract.starts_on if current_contract is not None else regen.generated_at.date()), effective_date)
        approach = evaluate_big_club_approach(
            BigClubApproachInputs(
                approaching_prestige=float(approaching_context["prestige"]),
                approaching_trophies=float(approaching_context["trophy_score"]),
                current_prestige=float(current_context["prestige"]),
                current_trophies=float(current_context["trophy_score"]),
                tenure_months=tenure_months,
                ambition=traits["ambition"],
                loyalty=traits["loyalty"],
                hometown_resistance=float(current_context["hometown_score"]),
                rising_club_resistance=75.0 if getattr(current_reputation, "prestige_tier", "") == "Rising" else 10.0,
                already_considering_move=pressure.current_state in {"attracted_by_bigger_club", "considering_transfer", "transfer_requested", "unsettled"},
            )
        )
        pressure.ambition_pressure = min(100.0, pressure.ambition_pressure + approach.ambition_pressure_delta)
        pressure.transfer_desire = min(100.0, pressure.transfer_desire + approach.transfer_desire_delta)
        pressure.prestige_dissatisfaction = min(100.0, pressure.prestige_dissatisfaction + approach.prestige_dissatisfaction_delta)
        pressure.title_frustration = min(100.0, pressure.title_frustration + approach.title_frustration_delta)
        pressure.pressure_score = min(100.0, max(pressure.pressure_score, approach.effect_score))
        pressure.current_state = approach.resulting_state
        pressure.last_big_club_id = approaching_club.id
        if not approach.resisted and pressure.unresolved_since is None:
            pressure.unresolved_since = datetime.combine(effective_date, datetime.min.time())
        current_salary = current_contract.wage_amount if current_contract is not None else Decimal("0.0000")
        uplift_multiplier = Decimal("1.0") + (Decimal(str(approach.salary_expectation_delta_pct)) / Decimal("100"))
        pressure.salary_expectation_fancoin_per_year = max(
            pressure.salary_expectation_fancoin_per_year,
            (current_salary * uplift_multiplier).quantize(Decimal("0.0001")),
        )
        self.session.add(
            RegenBigClubApproach(
                regen_id=regen.id,
                current_club_id=current_club_id,
                approaching_club_id=approaching_club.id,
                prestige_gap_score=max(0.0, float(approaching_context["prestige"]) - float(current_context["prestige"])),
                trophy_gap_score=max(0.0, float(approaching_context["trophy_score"]) - float(current_context["trophy_score"])),
                resistance_score=approach.resistance_score,
                contract_tenure_months=tenure_months,
                effect_score=approach.effect_score,
                resisted=approach.resisted,
                resulting_state=approach.resulting_state,
                metadata_json={"notes": payload.notes or "", "player_id": player.id},
            )
        )
        self.session.add(
            RegenUnsettlingEvent(
                regen_id=regen.id,
                current_club_id=current_club_id,
                approaching_club_id=approaching_club.id,
                previous_state=self._regen_career_state(regen).get("pressure_state", "content"),
                resulting_state=approach.resulting_state,
                effect_score=approach.effect_score,
                resisted=approach.resisted,
                metadata_json={"notes": payload.notes or "", "player_id": player.id},
            )
        )
        self._record_event(
            player_id=player.id,
            club_id=current_club_id,
            event_type=REGEN_BIG_CLUB_APPROACH_EVENT_TYPE,
            event_status="resisted" if approach.resisted else "active",
            occurred_on=effective_date,
            effective_from=effective_date,
            effective_to=None,
            related_entity_type="regen_profile",
            related_entity_id=regen.id,
            summary=f"{player.full_name} was approached by {approaching_club.club_name}",
            details={
                "approaching_club_id": approaching_club.id,
                "effect_score": approach.effect_score,
                "resulting_state": approach.resulting_state,
                "resisted": approach.resisted,
            },
            notes=payload.notes,
        )
        self.session.commit()
        return self.get_regen_summary(player_id, on_date=effective_date)

    def apply_regen_pressure_resolution(
        self,
        player_id: str,
        payload: RegenPressureResolutionRequest,
        *,
        reference_on: date | None = None,
    ) -> RegenLifecycleView:
        effective_date = reference_on or date.today()
        player = self._require_player(player_id)
        regen = self._require_regen_profile(player_id)
        contract_summary = self.get_contract_summary(player_id, on_date=effective_date)
        pressure = self._ensure_pressure_state(player, regen, reference_on=effective_date, contract_summary=contract_summary)
        current_salary = contract_summary.active_contract.wage_amount if contract_summary and contract_summary.active_contract else Decimal("0.0000")
        resolution = resolution_for_event(
            payload.resolution_type,
            salary_raise_pct=payload.salary_raise_pct,
            ambition_signal=payload.ambition_signal,
            relationship_boost=payload.relationship_boost,
            trophy_credit=payload.trophy_credit,
        )
        pressure.ambition_pressure = max(
            0.0,
            min(100.0, pressure.ambition_pressure + (resolution.transfer_desire_delta * 0.65)),
        )
        pressure.transfer_desire = max(0.0, min(100.0, pressure.transfer_desire + resolution.transfer_desire_delta))
        pressure.prestige_dissatisfaction = max(0.0, min(100.0, pressure.prestige_dissatisfaction + resolution.prestige_dissatisfaction_delta))
        pressure.title_frustration = max(0.0, min(100.0, pressure.title_frustration + resolution.title_frustration_delta))
        metadata = dict(pressure.metadata_json or {})
        metadata["relief_score"] = float(metadata.get("relief_score", 0.0)) + resolution.relief_score_delta
        metadata["unresolved_bonus"] = max(0.0, float(metadata.get("unresolved_bonus", 0.0)) + resolution.unresolved_bonus_delta)
        if resolution.relief_score_delta >= 10.0:
            metadata["manual_transfer_request"] = False
        pressure.metadata_json = metadata
        if payload.resolution_type == "salary_improved" and payload.salary_raise_pct > 0:
            improved_salary = current_salary * (Decimal("1.0") + (Decimal(str(payload.salary_raise_pct)) / Decimal("100")))
            pressure.salary_expectation_fancoin_per_year = max(current_salary, min(pressure.salary_expectation_fancoin_per_year, improved_salary))
        if resolution.unresolved_bonus_delta < 0:
            pressure.last_resolved_at = datetime.combine(effective_date, datetime.min.time())
        if resolution.relief_score_delta >= 10.0:
            pressure.transfer_desire = min(pressure.transfer_desire, 18.0)
            pressure.ambition_pressure = min(pressure.ambition_pressure, 22.0)
            pressure.prestige_dissatisfaction = min(pressure.prestige_dissatisfaction, 12.0)
            pressure.title_frustration = min(pressure.title_frustration, 10.0)
            pressure.active_transfer_request = False
            pressure.current_state = "monitoring_situation"
        self._record_event(
            player_id=player.id,
            club_id=player.current_club_profile_id,
            event_type=REGEN_PRESSURE_RESOLUTION_EVENT_TYPE,
            event_status="resolved" if resolution.relief_score_delta >= 0 else "active",
            occurred_on=effective_date,
            effective_from=effective_date,
            effective_to=None,
            related_entity_type="regen_profile",
            related_entity_id=regen.id,
            summary=f"{player.full_name} pressure update: {payload.resolution_type}",
            details={
                "resolution_type": payload.resolution_type,
                "salary_raise_pct": payload.salary_raise_pct,
                "ambition_signal": payload.ambition_signal,
                "relationship_boost": payload.relationship_boost,
                "trophy_credit": payload.trophy_credit,
            },
            notes=payload.notes,
        )
        self._ensure_pressure_state(player, regen, reference_on=effective_date, contract_summary=contract_summary)
        self.session.commit()
        return self.get_regen_summary(player_id, on_date=effective_date)

    def update_regen_transfer_listing(
        self,
        player_id: str,
        payload: RegenTransferListingRequest,
        *,
        reference_on: date | None = None,
    ) -> RegenLifecycleView:
        effective_date = reference_on or date.today()
        player = self._require_player(player_id)
        regen = self._require_regen_profile(player_id)
        state = self._regen_career_state(regen)
        listed_before = bool(state.get("transfer_listed", False))
        state["transfer_listed"] = payload.listed
        state["agency_message"] = (
            "Requested to be transfer listed."
            if payload.listed
            else "Transfer-list request withdrawn."
        )
        self._set_regen_career_state(regen, state)
        pressure = self._ensure_pressure_state(
            player,
            regen,
            reference_on=effective_date,
            contract_summary=self.get_contract_summary(player_id, on_date=effective_date),
        )
        pressure.active_transfer_request = payload.listed
        pressure.current_state = "transfer_requested" if payload.listed else "monitoring_situation"
        if payload.listed and pressure.unresolved_since is None:
            pressure.unresolved_since = datetime.combine(effective_date, datetime.min.time())
        metadata = dict(pressure.metadata_json or {})
        if payload.listed:
            pressure.ambition_pressure = max(pressure.ambition_pressure, 72.0)
            pressure.transfer_desire = max(pressure.transfer_desire, 74.0)
            pressure.prestige_dissatisfaction = max(pressure.prestige_dissatisfaction, 58.0)
            pressure.title_frustration = max(pressure.title_frustration, 42.0)
            metadata["manual_transfer_request"] = True
            metadata["unresolved_bonus"] = max(float(metadata.get("unresolved_bonus", 0.0)), 16.0)
        if not payload.listed:
            pressure.last_resolved_at = datetime.combine(effective_date, datetime.min.time())
            pressure.transfer_desire = min(pressure.transfer_desire, 20.0)
            pressure.prestige_dissatisfaction = min(pressure.prestige_dissatisfaction, 15.0)
            pressure.title_frustration = min(pressure.title_frustration, 12.0)
            metadata["manual_transfer_request"] = False
            metadata["unresolved_bonus"] = 0.0
        pressure.metadata_json = metadata
        if listed_before != payload.listed:
            self._record_event(
                player_id=player.id,
                club_id=player.current_club_profile_id,
                event_type=REGEN_TRANSFER_LIST_EVENT_TYPE,
                event_status="active" if payload.listed else "resolved",
                occurred_on=effective_date,
                effective_from=effective_date,
                effective_to=None,
                related_entity_type="regen_profile",
                related_entity_id=regen.id,
                summary=f"{player.full_name} {'requested' if payload.listed else 'withdrew'} transfer listing",
                details={"listed": payload.listed},
                notes=payload.reason,
            )
        self.session.commit()
        return self.get_regen_summary(player_id, on_date=effective_date)

    def apply_regen_special_training(
        self,
        player_id: str,
        payload: RegenSpecialTrainingRequest,
        *,
        reference_on: date | None = None,
    ) -> RegenLifecycleView:
        effective_date = reference_on or date.today()
        player = self._require_player(player_id)
        regen = self._require_regen_profile(player_id)
        self._validate_regen_special_training(player, regen, payload, reference_on=effective_date)
        potential = dict(regen.potential_range_json or {})
        current_ability = dict(regen.current_ability_range_json or {})
        training_state = self._regen_training_state(regen)
        maximum_key = int(potential.get("maximum", regen.current_gsi))
        minimum_key = int(potential.get("minimum", max(regen.current_gsi - 5, 0)))
        delta = 6 if payload.package_type == "major" else 3
        floor_delta = 3 if payload.package_type == "major" else 1
        potential["maximum"] = min(85, maximum_key + delta)
        potential["minimum"] = min(potential["maximum"], minimum_key + floor_delta)
        current_ability["maximum"] = min(int(potential["maximum"]), int(current_ability.get("maximum", regen.current_gsi)) + 1)
        regen.potential_range_json = potential
        regen.current_ability_range_json = current_ability
        regen.current_gsi = min(int(potential["maximum"]), regen.current_gsi + (2 if payload.package_type == "major" else 1))
        if payload.package_type == "major":
            training_state["major_used_count"] = int(training_state.get("major_used_count", 0)) + 1
        else:
            training_state["minor_used_count"] = int(training_state.get("minor_used_count", 0)) + 1
        training_state["last_trained_on"] = effective_date.isoformat()
        training_state["cooldown_until"] = (effective_date + timedelta(days=REGEN_SPECIAL_TRAINING_COOLDOWN_DAYS)).isoformat()
        training_state["last_package_type"] = payload.package_type
        training_state["season_label"] = self._season_label(effective_date)
        self._set_regen_training_state(regen, training_state)
        self._record_event(
            player_id=player.id,
            club_id=payload.club_id or player.current_club_profile_id,
            event_type=REGEN_SPECIAL_TRAINING_EVENT_TYPE,
            event_status="applied",
            occurred_on=effective_date,
            effective_from=effective_date,
            effective_to=date.fromisoformat(training_state["cooldown_until"]),
            related_entity_type="regen_profile",
            related_entity_id=regen.id,
            summary=f"{player.full_name} completed {payload.package_type} special training",
            details={
                "package_type": payload.package_type,
                "projected_ceiling": potential["maximum"],
                "current_gsi": regen.current_gsi,
                "season_label": self._season_label(effective_date),
            },
            notes=payload.notes,
        )
        self.session.commit()
        return self.get_regen_summary(player_id, on_date=effective_date)

    def evaluate_regen_bids(
        self,
        window_id: str,
        player_id: str,
        *,
        reference_on: date | None = None,
    ) -> tuple[RegenBidEvaluationView, ...]:
        effective_date = reference_on or date.today()
        regen = self._require_regen_profile(player_id)
        state = self._sync_regen_state(
            self._require_player(player_id),
            regen,
            reference_on=effective_date,
            contract_summary=self.get_contract_summary(player_id, on_date=effective_date),
            bids=self.list_player_transfer_bids(player_id),
        )
        self.session.commit()
        if not bool(state.get("free_agent", False)):
            raise PlayerLifecycleValidationError("Regen bid auto-selection requires the player to be in free agency")
        submitted_bids = [
            bid
            for bid in self.list_window_bids(window_id)
            if bid.player_id == player_id and bid.status == TransferBidStatus.SUBMITTED.value
        ]
        if not submitted_bids:
            return ()
        traits = self._resolve_regen_traits(regen)
        evaluations: list[RegenBidEvaluationView] = []
        offers_by_bid_id = {
            offer.transfer_bid_id: offer
            for offer in self.session.scalars(
                select(RegenContractOffer).where(
                    RegenContractOffer.transfer_bid_id.in_([bid.id for bid in submitted_bids])
                )
            ).all()
            if offer.transfer_bid_id is not None
        }
        wage_anchor = max(
            float((offers_by_bid_id.get(bid.id).offered_salary_fancoin_per_year if offers_by_bid_id.get(bid.id) is not None else (bid.wage_offer_amount or 0)))
            for bid in submitted_bids
        ) or 1.0
        bid_anchor = max(float((offers_by_bid_id.get(bid.id).training_fee_gtex_coin if offers_by_bid_id.get(bid.id) is not None else (bid.bid_amount or 0))) for bid in submitted_bids) or 1.0
        contract_anchor = max(int(offers_by_bid_id.get(bid.id).contract_years if offers_by_bid_id.get(bid.id) is not None else 1) for bid in submitted_bids) or 1
        for bid in submitted_bids:
            offer = offers_by_bid_id.get(bid.id)
            offered_salary = float(offer.offered_salary_fancoin_per_year if offer is not None else (bid.wage_offer_amount or 0))
            fee_amount = float(offer.training_fee_gtex_coin if offer is not None else (bid.bid_amount or 0))
            salary_score = min(100.0, ((offered_salary / wage_anchor) * 82.0) + ((fee_amount / bid_anchor) * 18.0))
            contract_length_score = min(100.0, ((offer.contract_years if offer is not None else 1) / contract_anchor) * 100.0)
            club_context = self._regen_club_context(bid.buying_club_id, regen)
            prestige_score = club_context["prestige"]
            trophy_score = club_context["trophy_score"]
            development_score = club_context["development_score"]
            hometown_score = club_context["hometown_score"]
            playing_time_score = club_context["playing_time_score"]
            manager_fit_score = min(100.0, round((development_score * 0.55) + (playing_time_score * 0.45), 2))
            ambition_alignment_score = min(
                100.0,
                round(
                    (prestige_score * (0.45 + (traits["ambition"] / 2000.0)))
                    + (trophy_score * (0.25 + (traits["trophy_hunger"] / 2200.0)))
                    + (playing_time_score * 0.18),
                    2,
                ),
            )
            score_input = ContractOfferScoreInputs(
                salary_score=salary_score,
                contract_length_score=contract_length_score,
                prestige_score=prestige_score,
                trophy_score=trophy_score,
                playing_time_score=playing_time_score,
                hometown_score=hometown_score,
                manager_fit_score=manager_fit_score,
                ambition_alignment_score=ambition_alignment_score,
                greed=traits["greed"],
                ambition=traits["ambition"],
                loyalty=traits["loyalty"],
                professionalism=traits["professionalism"],
                trophy_hunger=traits["trophy_hunger"],
            )
            scored_offer = score_contract_offer(score_input)
            score = scored_offer.total_score
            if club_context["cross_border"] and traits["adaptability"] < 45:
                score -= 6.0
            reasons = scored_offer.reasons or self._top_regen_bid_reasons(
                salary_score=salary_score,
                prestige_score=prestige_score,
                playing_time_score=playing_time_score,
                development_score=development_score,
                hometown_score=hometown_score,
                trophy_score=trophy_score,
            )
            evaluations.append(
                RegenBidEvaluationView(
                    bid_id=bid.id,
                    buying_club_id=bid.buying_club_id,
                    score=round(score, 2),
                    preferred=False,
                    salary_score=round(salary_score, 2),
                    contract_length_score=round(contract_length_score, 2),
                    prestige_score=round(prestige_score, 2),
                    playing_time_score=round(playing_time_score, 2),
                    development_score=round(development_score, 2),
                    hometown_score=round(hometown_score, 2),
                    trophy_score=round(trophy_score, 2),
                    manager_fit_score=round(manager_fit_score, 2),
                    ambition_alignment_score=round(ambition_alignment_score, 2),
                    reasons=reasons,
                )
            )
        ordered = sorted(
            evaluations,
            key=lambda item: (
                item.score,
                item.salary_score,
                item.contract_length_score,
                item.development_score,
                item.prestige_score,
            ),
            reverse=True,
        )
        if ordered:
            ordered[0] = ordered[0].model_copy(update={"preferred": True})
        return tuple(ordered)

    def resolve_regen_bid(
        self,
        window_id: str,
        player_id: str,
        *,
        reference_on: date | None = None,
    ) -> RegenBidResolutionView:
        effective_date = reference_on or date.today()
        evaluations = self.evaluate_regen_bids(window_id, player_id, reference_on=effective_date)
        if not evaluations:
            raise PlayerLifecycleValidationError("No submitted bids are available for regen resolution")
        preferred = evaluations[0]
        bid = self._require_bid(window_id, preferred.bid_id)
        regen = self._require_regen_profile(player_id)
        offer = self._get_contract_offer_by_bid_id(bid.id)
        duration_days = (
            (365 * offer.contract_years)
            if offer is not None
            else self._preferred_regen_contract_days(regen, effective_date)
        )
        accepted = self.accept_bid(
            window_id,
            bid.id,
            TransferBidAcceptRequest(
                contract_ends_on=effective_date + timedelta(days=duration_days - 1),
                contract_starts_on=effective_date,
                wage_amount=(
                    offer.offered_salary_fancoin_per_year
                    if offer is not None
                    else (bid.wage_offer_amount or Decimal("0"))
                ),
                signed_on=effective_date,
            ),
            reference_on=effective_date,
        )
        headline = self._latest_transfer_headline_for_entity("transfer_bid", bid.id)
        return RegenBidResolutionView(
            accepted_bid=self.to_transfer_bid_view(accepted),
            evaluations=evaluations,
            headline=self._to_transfer_headline_view(headline),
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
        regen = self._get_regen_profile(player_id)
        self._require_club_profile(payload.club_id)
        reference_date = reference_on or payload.signed_on or payload.starts_on
        self._validate_contract_dates(starts_on=payload.starts_on, ends_on=payload.ends_on)
        if regen is not None:
            self._validate_regen_contract_duration(payload.starts_on, payload.ends_on)
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
        if regen is not None:
            state = self._regen_career_state(regen)
            state["free_agent"] = False
            state["free_agent_since"] = None
            state["transfer_listed"] = False
            state["previous_club_id"] = payload.club_id
            state["agency_message"] = "Committed to a FanCoin contract."
            self._set_regen_career_state(regen, state)
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
        player = self._require_player(payload.player_id)
        regen = self._get_regen_profile(payload.player_id)
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
        current_contract_summary = self.get_contract_summary(payload.player_id, on_date=reference_on)
        is_regen_free_agent_offer = regen is not None and active_contract is None
        offer_market: RegenOfferVisibilityState | None = None
        offered_salary: Decimal | None = payload.wage_offer_amount
        if active_contract is not None:
            if selling_club_id is not None and selling_club_id != active_contract.club_id:
                raise PlayerLifecycleValidationError("Selling club must match the player's current active contract")
            selling_club_id = active_contract.club_id
        elif selling_club_id is not None:
            raise PlayerLifecycleValidationError("Selling club cannot be set when the player has no active contract")

        if selling_club_id is not None and payload.buying_club_id == selling_club_id:
            raise PlayerLifecycleValidationError("Buying club must be different from the selling club")

        structured_terms = {
            "submitted_on": reference_on.isoformat(),
            "outside_window_exempt": payload.allow_outside_window,
            "exemption_reason": payload.exemption_reason,
        }
        if is_regen_free_agent_offer:
            if payload.contract_years is None:
                raise PlayerLifecycleValidationError("Free-agent regen offers must include contract_years")
            state = self._sync_regen_state(
                player,
                regen,
                reference_on=reference_on,
                contract_summary=current_contract_summary,
                bids=self.list_player_transfer_bids(payload.player_id),
            )
            offered_salary = offered_salary or Decimal("0.0000")
            offer_market = self._ensure_offer_visibility_state(
                regen,
                reference_on=reference_on,
                current_salary=Decimal("0.0000"),
            )
            if offered_salary < offer_market.minimum_salary_fancoin_per_year:
                raise PlayerLifecycleValidationError("Salary offer is below the regen minimum for the current market")
            previous_club_id = state.get("previous_club_id")
            structured_terms["free_agent_capture_split"] = {
                "platform_pct": REGEN_FREE_AGENT_PLATFORM_SHARE_PCT,
                "previous_club_pct": REGEN_FREE_AGENT_PREVIOUS_CLUB_SHARE_PCT,
                "previous_club_id": previous_club_id,
                "fee_kind": "training_fee",
            }
            structured_terms["contract_offer"] = {
                "training_fee_gtex_coin": str(offer_market.training_fee_gtex_coin),
                "minimum_salary_fancoin_per_year": str(offer_market.minimum_salary_fancoin_per_year),
                "offered_salary_fancoin_per_year": str(offered_salary),
                "contract_years": payload.contract_years,
                "salary_offer_hidden": True,
            }

        bid = TransferBid(
            window_id=window_id,
            player_id=payload.player_id,
            selling_club_id=selling_club_id,
            buying_club_id=payload.buying_club_id,
            status=TransferBidStatus.SUBMITTED.value,
            bid_amount=offer_market.training_fee_gtex_coin if offer_market is not None else payload.bid_amount,
            wage_offer_amount=offered_salary if offer_market is not None else payload.wage_offer_amount,
            sell_on_clause_pct=payload.sell_on_clause_pct,
            notes=payload.notes,
            structured_terms_json=structured_terms,
        )
        self.session.add(bid)
        self.session.flush()
        if offer_market is not None and regen is not None and payload.buying_club_id is not None and offered_salary is not None and payload.contract_years is not None:
            club = self._require_club_profile(payload.buying_club_id)
            owner = self._require_user(club.owner_user_id)
            wallet_service = WalletService()
            fancoin_balance = wallet_service.get_wallet_summary(self.session, owner, currency=LedgerUnit.CREDIT).available_balance
            gtex_balance = wallet_service.get_wallet_summary(self.session, owner, currency=LedgerUnit.COIN).available_balance
            conversion = quote_conversion(
                required_fancoin=offered_salary * payload.contract_years,
                current_fancoin_balance=fancoin_balance,
                current_gtex_balance=gtex_balance,
            )
            quote = CurrencyConversionQuote(
                regen_id=regen.id,
                offering_club_id=club.id,
                owner_user_id=owner.id,
                source_unit=LedgerUnit.COIN.value,
                target_unit=LedgerUnit.CREDIT.value,
                required_target_amount=conversion.required_fancoin,
                available_target_amount=conversion.current_fancoin_balance,
                shortfall_target_amount=conversion.shortfall_fancoin,
                available_source_amount=gtex_balance,
                direct_source_equivalent=conversion.direct_gtex_equivalent,
                source_amount_required=conversion.gtex_required_for_conversion,
                premium_bps=conversion.conversion_premium_bps,
                can_cover_shortfall=conversion.can_cover_shortfall,
                expires_on=datetime.combine(reference_on + timedelta(days=1), datetime.min.time()),
                metadata_json={
                    "training_fee_gtex_coin": str(offer_market.training_fee_gtex_coin),
                    "minimum_salary_fancoin_per_year": str(offer_market.minimum_salary_fancoin_per_year),
                    "premium_note": conversion.premium_note,
                },
            )
            self.session.add(quote)
            self.session.flush()
            offer = RegenContractOffer(
                regen_id=regen.id,
                transfer_bid_id=bid.id,
                offering_club_id=club.id,
                training_fee_gtex_coin=offer_market.training_fee_gtex_coin,
                minimum_salary_fancoin_per_year=offer_market.minimum_salary_fancoin_per_year,
                offered_salary_fancoin_per_year=offered_salary,
                contract_years=payload.contract_years,
                current_offer_count_visible=0,
                decision_deadline=datetime.combine(
                    reference_on + timedelta(days=REGEN_CONTRACT_OFFER_DECISION_DAYS),
                    datetime.min.time(),
                ),
                status=TransferBidStatus.SUBMITTED.value,
                metadata_json={
                    "conversion_quote_id": quote.id,
                    "hidden_competing_salary_amounts": True,
                },
            )
            self.session.add(offer)
            self.session.flush()
            visibility = self._sync_offer_visibility_counts(regen.id)
            if visibility is not None:
                offer.current_offer_count_visible = visibility.visible_offer_count
            refreshed_terms = dict(bid.structured_terms_json or {})
            refreshed_contract_terms = dict(refreshed_terms.get("contract_offer") or {})
            refreshed_contract_terms["current_offer_count_visible"] = offer.current_offer_count_visible
            refreshed_contract_terms["conversion_quote_id"] = quote.id
            refreshed_terms["contract_offer"] = refreshed_contract_terms
            bid.structured_terms_json = refreshed_terms
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
        regen = self._get_regen_profile(bid.player_id)
        offer = self._get_contract_offer_by_bid_id(bid.id)
        acceptance_on = reference_on or payload.signed_on or payload.contract_starts_on or date.today()
        contract_starts_on = payload.contract_starts_on or acceptance_on
        self._validate_contract_dates(starts_on=contract_starts_on, ends_on=payload.contract_ends_on)
        if regen is not None:
            self._validate_regen_contract_duration(contract_starts_on, payload.contract_ends_on)
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
            wage_amount=(
                payload.wage_amount
                if payload.wage_amount is not None
                else (
                    offer.offered_salary_fancoin_per_year
                    if offer is not None
                    else (bid.wage_offer_amount or 0)
                )
            ),
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

        if offer is not None and regen is not None:
            offer.status = bid.status
            offer.metadata_json = {
                **dict(offer.metadata_json or {}),
                "accepted_on": acceptance_on.isoformat(),
                "contract_id": new_contract.id,
            }
            self._settle_regen_contract_offer(
                bid=bid,
                offer=offer,
                new_contract=new_contract,
                acceptance_on=acceptance_on,
            )
            self._reject_competing_regen_bids(window_id=window_id, player_id=player.id, accepted_bid_id=bid.id)
            self._sync_offer_visibility_counts(regen.id)

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
        if regen is not None:
            state = self._regen_career_state(regen)
            state["free_agent"] = False
            state["free_agent_since"] = None
            state["transfer_listed"] = False
            state["previous_club_id"] = new_contract.club_id
            state["agency_message"] = "Accepted a new FanCoin contract."
            state["pressure_state"] = "content"
            self._set_regen_career_state(regen, state)
            pressure = self._get_pressure_state(regen.id)
            if pressure is not None:
                pressure.current_state = "content"
                pressure.active_transfer_request = False
                pressure.refuses_new_contract = False
                pressure.end_of_contract_pressure = False
                pressure.transfer_desire = max(0.0, pressure.transfer_desire - 35.0)
                pressure.pressure_score = max(0.0, pressure.pressure_score - 40.0)
                pressure.unresolved_since = None
                pressure.last_resolved_at = datetime.combine(acceptance_on, datetime.min.time())
            effect = self._get_team_dynamics_effect(regen.id, bid.selling_club_id)
            if effect is not None:
                effect.active = False
                effect.morale_penalty = 0.0
                effect.chemistry_penalty = 0.0
                effect.tactical_cohesion_penalty = 0.0
                effect.performance_penalty = 0.0
                effect.influences_younger_players = False
                effect.unresolved_since = None
            self._publish_transfer_headline(
                player=player,
                regen=regen,
                bid=bid,
                offer=offer,
                contract=new_contract,
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
        offer = self._get_contract_offer_by_bid_id(bid.id)
        if offer is not None:
            offer.status = TransferBidStatus.REJECTED.value
            offer.metadata_json = {
                **dict(offer.metadata_json or {}),
                "rejection_reason": payload.reason or "",
            }
            self._sync_offer_visibility_counts(offer.regen_id)
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
        offer = self._get_contract_offer_by_bid_id(bid.id)
        structured_terms = self._transfer_bid_terms_for_view(bid, offer)
        wage_offer_amount = bid.wage_offer_amount
        if offer is not None and bid.status == TransferBidStatus.SUBMITTED.value:
            wage_offer_amount = None
        return TransferBidView.model_validate(
            {
                "id": bid.id,
                "window_id": bid.window_id,
                "player_id": bid.player_id,
                "selling_club_id": bid.selling_club_id,
                "buying_club_id": bid.buying_club_id,
                "status": TransferBidStatus(bid.status),
                "bid_amount": bid.bid_amount,
                "wage_offer_amount": wage_offer_amount,
                "sell_on_clause_pct": bid.sell_on_clause_pct,
                "structured_terms_json": structured_terms,
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

    def _get_regen_profile(self, player_id: str) -> RegenProfile | None:
        return self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player_id))

    def _require_regen_profile(self, player_id: str) -> RegenProfile:
        regen = self._get_regen_profile(player_id)
        if regen is None:
            raise PlayerLifecycleNotFoundError(f"Regen profile for player {player_id} was not found")
        return regen

    def _get_regen_origin(self, regen_profile_id: str) -> RegenOriginMetadata | None:
        return self.session.scalar(select(RegenOriginMetadata).where(RegenOriginMetadata.regen_profile_id == regen_profile_id))

    def _get_regen_personality(self, regen_profile_id: str) -> RegenPersonalityProfile | None:
        return self.session.scalar(select(RegenPersonalityProfile).where(RegenPersonalityProfile.regen_profile_id == regen_profile_id))

    def _regen_career_state(self, regen: RegenProfile) -> dict[str, Any]:
        metadata = dict(regen.metadata_json or {})
        return dict(metadata.get("career_state") or {})

    def _set_regen_career_state(self, regen: RegenProfile, state: dict[str, Any]) -> None:
        metadata = dict(regen.metadata_json or {})
        metadata["career_state"] = state
        regen.metadata_json = metadata

    def _regen_training_state(self, regen: RegenProfile) -> dict[str, Any]:
        metadata = dict(regen.metadata_json or {})
        return dict(metadata.get("special_training") or {})

    def _set_regen_training_state(self, regen: RegenProfile, training_state: dict[str, Any]) -> None:
        metadata = dict(regen.metadata_json or {})
        metadata["special_training"] = training_state
        regen.metadata_json = metadata

    def _require_user(self, user_id: str | None) -> User:
        user = self.session.get(User, user_id) if user_id else None
        if user is None:
            raise PlayerLifecycleNotFoundError(f"User {user_id} was not found")
        return user

    def _get_pressure_state(self, regen_profile_id: str) -> RegenTransferPressureState | None:
        return self.session.scalar(select(RegenTransferPressureState).where(RegenTransferPressureState.regen_id == regen_profile_id))

    def _get_offer_visibility_state(self, regen_profile_id: str) -> RegenOfferVisibilityState | None:
        return self.session.scalar(select(RegenOfferVisibilityState).where(RegenOfferVisibilityState.regen_id == regen_profile_id))

    def _get_team_dynamics_effect(self, regen_profile_id: str, club_id: str | None) -> RegenTeamDynamicsEffect | None:
        if club_id is None:
            return None
        return self.session.scalar(
            select(RegenTeamDynamicsEffect)
            .where(
                RegenTeamDynamicsEffect.regen_id == regen_profile_id,
                RegenTeamDynamicsEffect.club_id == club_id,
            )
            .order_by(RegenTeamDynamicsEffect.updated_at.desc())
        )

    def _count_visible_contract_offers(self, regen_profile_id: str) -> int:
        offers = self.session.scalars(select(RegenContractOffer).where(RegenContractOffer.regen_id == regen_profile_id)).all()
        return sum(1 for offer in offers if offer.status not in {"rejected", "withdrawn", "expired"})

    def _get_contract_offer_by_bid_id(self, bid_id: str) -> RegenContractOffer | None:
        return self.session.scalar(
            select(RegenContractOffer)
            .where(RegenContractOffer.transfer_bid_id == bid_id)
            .order_by(RegenContractOffer.created_at.desc())
        )

    def _sync_offer_visibility_counts(self, regen_profile_id: str) -> RegenOfferVisibilityState | None:
        visibility = self._get_offer_visibility_state(regen_profile_id)
        if visibility is None:
            return None
        offers = self.session.scalars(select(RegenContractOffer).where(RegenContractOffer.regen_id == regen_profile_id)).all()
        visible_count = sum(1 for offer in offers if offer.status not in {"rejected", "withdrawn", "expired"})
        visibility.visible_offer_count = visible_count
        if visible_count > 0:
            visibility.last_offer_received_at = utcnow()
        for offer in offers:
            if offer.status not in {"rejected", "withdrawn", "expired"}:
                offer.current_offer_count_visible = visible_count
        self.session.flush()
        return visibility

    def _transfer_bid_terms_for_view(
        self,
        bid: TransferBid,
        offer: RegenContractOffer | None,
    ) -> dict[str, object]:
        terms = dict(bid.structured_terms_json or {})
        if offer is None:
            return terms
        contract_offer_terms = dict(terms.get("contract_offer") or {})
        contract_offer_terms.update(
            {
                "training_fee_gtex_coin": str(offer.training_fee_gtex_coin),
                "minimum_salary_fancoin_per_year": str(offer.minimum_salary_fancoin_per_year),
                "contract_years": offer.contract_years,
                "current_offer_count_visible": offer.current_offer_count_visible,
                "salary_offer_hidden": True,
            }
        )
        if bid.status == TransferBidStatus.SUBMITTED.value:
            contract_offer_terms.pop("offered_salary_fancoin_per_year", None)
        else:
            contract_offer_terms["offered_salary_fancoin_per_year"] = str(offer.offered_salary_fancoin_per_year)
        terms["contract_offer"] = contract_offer_terms
        terms["offer_market"] = {
            "training_fee_gtex_coin": str(offer.training_fee_gtex_coin),
            "minimum_salary_fancoin_per_year": str(offer.minimum_salary_fancoin_per_year),
            "current_offer_count_visible": offer.current_offer_count_visible,
            "hidden_competing_salary_amounts": True,
        }
        return terms

    def _ensure_offer_visibility_state(
        self,
        regen: RegenProfile,
        *,
        reference_on: date,
        current_salary: Decimal,
    ) -> RegenOfferVisibilityState:
        del reference_on
        visibility = self._get_offer_visibility_state(regen.id)
        traits = self._resolve_regen_traits(regen)
        training_fee = default_training_fee_gtex(
            current_gsi=regen.current_gsi,
            potential_maximum=int((regen.potential_range_json or {}).get("maximum", regen.current_gsi)),
        )
        minimum_salary = default_minimum_salary_fancoin(
            current_gsi=regen.current_gsi,
            ambition=traits["ambition"],
            greed=traits["greed"],
            current_salary=current_salary,
        )
        if visibility is None:
            visibility = RegenOfferVisibilityState(
                regen_id=regen.id,
                training_fee_gtex_coin=training_fee,
                minimum_salary_fancoin_per_year=minimum_salary,
                visible_offer_count=0,
                metadata_json={},
            )
            self.session.add(visibility)
        visibility.training_fee_gtex_coin = training_fee
        visibility.minimum_salary_fancoin_per_year = max(visibility.minimum_salary_fancoin_per_year, minimum_salary)
        visibility.visible_offer_count = self._count_visible_contract_offers(regen.id)
        if visibility.visible_offer_count > 0:
            visibility.last_offer_received_at = utcnow()
        self.session.flush()
        return visibility

    def _ensure_pressure_state(
        self,
        player: Player,
        regen: RegenProfile,
        *,
        reference_on: date,
        contract_summary: ContractSummaryView | None,
    ) -> RegenTransferPressureState:
        pressure = self._get_pressure_state(regen.id)
        if pressure is None:
            pressure = RegenTransferPressureState(
                regen_id=regen.id,
                current_club_id=player.current_club_profile_id,
                current_state="content",
                salary_expectation_fancoin_per_year=Decimal("0.0000"),
                metadata_json={},
            )
            self.session.add(pressure)
        traits = self._resolve_regen_traits(regen)
        current_contract = contract_summary.active_contract if contract_summary is not None else None
        current_salary = current_contract.wage_amount if current_contract is not None else Decimal("0.0000")
        visibility = self._ensure_offer_visibility_state(regen, reference_on=reference_on, current_salary=current_salary)
        current_club_id = current_contract.club_id if current_contract is not None else player.current_club_profile_id
        current_context = self._regen_club_context(current_club_id, regen)
        metadata = dict(pressure.metadata_json or {})
        computation = compute_transfer_pressure(
            TransferPressureInputs(
                current_state=pressure.current_state,
                ambition_pressure=pressure.ambition_pressure,
                transfer_desire=pressure.transfer_desire,
                prestige_dissatisfaction=pressure.prestige_dissatisfaction,
                title_frustration=pressure.title_frustration,
                salary_expectation_fancoin_per_year=max(pressure.salary_expectation_fancoin_per_year, visibility.minimum_salary_fancoin_per_year),
                current_salary_fancoin_per_year=current_salary,
                ambition=traits["ambition"],
                loyalty=traits["loyalty"],
                trophy_hunger=traits["trophy_hunger"],
                greed=traits["greed"],
                current_club_prestige=float(current_context["prestige"]),
                current_club_trophies=float(current_context["trophy_score"]),
                days_remaining=contract_summary.days_remaining if contract_summary is not None else None,
                unresolved_bonus=float(metadata.get("unresolved_bonus", 0.0)),
                relief_score=float(metadata.get("relief_score", 0.0)),
            )
        )
        pressure.current_club_id = current_club_id
        pressure.current_state = computation.current_state
        pressure.ambition_pressure = computation.ambition_pressure
        pressure.transfer_desire = computation.transfer_desire
        pressure.prestige_dissatisfaction = computation.prestige_dissatisfaction
        pressure.title_frustration = computation.title_frustration
        pressure.pressure_score = computation.pressure_score
        pressure.salary_expectation_fancoin_per_year = computation.salary_expectation_fancoin_per_year
        pressure.active_transfer_request = computation.active_transfer_request
        pressure.refuses_new_contract = computation.refuses_new_contract
        pressure.end_of_contract_pressure = computation.end_of_contract_pressure
        if pressure.active_transfer_request and pressure.unresolved_since is None:
            pressure.unresolved_since = datetime.combine(reference_on, datetime.min.time())
        if not pressure.active_transfer_request and computation.current_state in {"content", "monitoring_situation"}:
            pressure.last_resolved_at = datetime.combine(reference_on, datetime.min.time())
        pressure.metadata_json = metadata
        self.session.flush()
        return pressure

    def _sync_team_dynamics_effect(
        self,
        player: Player,
        regen: RegenProfile,
        pressure: RegenTransferPressureState,
        *,
        reference_on: date,
    ) -> RegenTeamDynamicsEffect | None:
        club_id = player.current_club_profile_id or pressure.current_club_id
        effect = self._get_team_dynamics_effect(regen.id, club_id)
        personality = self._get_regen_personality(regen.id)
        leadership = int(getattr(personality, "leadership", 50) if personality is not None else 50)
        importance_score = float(regen.current_gsi) + (leadership * 0.35)
        unresolved_date = pressure.unresolved_since.date() if pressure.unresolved_since is not None else None
        computed = build_team_dynamics(
            TeamDynamicsInputs(
                pressure_score=pressure.pressure_score,
                leadership=leadership,
                importance_score=importance_score,
                unresolved_days=unresolved_days_since(unresolved_date, reference_on=reference_on),
                active_transfer_request=bool(pressure.active_transfer_request and club_id is not None),
            )
        )
        if effect is None and not computed.active:
            return None
        if effect is None:
            effect = RegenTeamDynamicsEffect(regen_id=regen.id, club_id=club_id, metadata_json={})
            self.session.add(effect)
        effect.active = computed.active
        effect.triggered_state = pressure.current_state
        effect.morale_penalty = computed.morale_penalty
        effect.chemistry_penalty = computed.chemistry_penalty
        effect.tactical_cohesion_penalty = computed.tactical_cohesion_penalty
        effect.performance_penalty = computed.performance_penalty
        effect.influences_younger_players = computed.influences_younger_players
        effect.unresolved_since = pressure.unresolved_since
        self.session.flush()
        return effect

    def _to_pressure_state_view(self, pressure: RegenTransferPressureState | None) -> RegenPressureStateView | None:
        if pressure is None:
            return None
        return RegenPressureStateView(
            current_state=pressure.current_state,
            ambition_pressure=pressure.ambition_pressure,
            transfer_desire=pressure.transfer_desire,
            salary_expectation_fancoin_per_year=pressure.salary_expectation_fancoin_per_year,
            prestige_dissatisfaction=pressure.prestige_dissatisfaction,
            title_frustration=pressure.title_frustration,
            active_transfer_request=pressure.active_transfer_request,
            refuses_new_contract=pressure.refuses_new_contract,
            end_of_contract_pressure=pressure.end_of_contract_pressure,
            pressure_score=pressure.pressure_score,
            unresolved_since=pressure.unresolved_since.date() if pressure.unresolved_since is not None else None,
            last_big_club_id=pressure.last_big_club_id,
        )

    def _to_team_dynamics_view(self, effect: RegenTeamDynamicsEffect | None) -> TeamDynamicsEffectView | None:
        if effect is None:
            return None
        return TeamDynamicsEffectView(
            active=effect.active,
            morale_penalty=effect.morale_penalty,
            chemistry_penalty=effect.chemistry_penalty,
            tactical_cohesion_penalty=effect.tactical_cohesion_penalty,
            performance_penalty=effect.performance_penalty,
            influences_younger_players=effect.influences_younger_players,
        )

    def _to_regen_offer_market_view(self, visibility: RegenOfferVisibilityState | None) -> RegenContractOfferMarketView | None:
        if visibility is None:
            return None
        return RegenContractOfferMarketView(
            training_fee_gtex_coin=visibility.training_fee_gtex_coin,
            minimum_salary_fancoin_per_year=visibility.minimum_salary_fancoin_per_year,
            visible_offer_count=visibility.visible_offer_count,
            hidden_competing_salary_amounts=True,
            fee_currency=GTEX_CURRENCY_BRANDING,
            salary_currency=FANCOIN_CURRENCY_BRANDING,
        )

    def _to_conversion_quote_view(self, quote: CurrencyConversionQuote) -> CurrencyConversionQuoteView:
        return CurrencyConversionQuoteView(
            quote_id=quote.id,
            required_fancoin=quote.required_target_amount,
            current_fancoin_balance=quote.available_target_amount,
            shortfall_fancoin=quote.shortfall_target_amount,
            current_gtex_balance=quote.available_source_amount,
            direct_gtex_equivalent=quote.direct_source_equivalent,
            gtex_required_for_conversion=quote.source_amount_required,
            conversion_premium_bps=quote.premium_bps,
            can_cover_shortfall=quote.can_cover_shortfall,
            premium_note=str((quote.metadata_json or {}).get("premium_note") or "Direct Fan Coin purchase remains cheaper than GTex Coin auto-conversion."),
            fee_currency=GTEX_CURRENCY_BRANDING,
            salary_currency=FANCOIN_CURRENCY_BRANDING,
        )

    def _to_transfer_headline_view(self, record: TransferHeadlineMediaRecord | None) -> TransferHeadlineView | None:
        if record is None:
            return None
        return TransferHeadlineView(
            category=record.headline_category,
            announcement_tier=record.announcement_tier,
            headline=record.headline_text,
            detail_text=record.detail_text,
            estimated_transfer_fee_eur=record.estimated_transfer_fee_eur,
            estimated_salary_package_eur=record.estimated_salary_package_eur,
            estimated_total_value_eur=record.estimated_total_value_eur,
            transfer_fee_gtex_coin=record.transfer_fee_gtex_coin,
            salary_package_fancoin=record.salary_package_fancoin,
            fee_currency=GTEX_CURRENCY_BRANDING,
            salary_currency=FANCOIN_CURRENCY_BRANDING,
        )

    def _latest_transfer_headline_for_entity(
        self,
        related_entity_type: str,
        related_entity_id: str,
    ) -> TransferHeadlineMediaRecord | None:
        return self.session.scalar(
            select(TransferHeadlineMediaRecord)
            .where(
                TransferHeadlineMediaRecord.related_entity_type == related_entity_type,
                TransferHeadlineMediaRecord.related_entity_id == related_entity_id,
            )
            .order_by(TransferHeadlineMediaRecord.created_at.desc())
        )

    def _reject_competing_regen_bids(
        self,
        *,
        window_id: str,
        player_id: str,
        accepted_bid_id: str,
    ) -> None:
        competing_bids = self.session.scalars(
            select(TransferBid).where(
                TransferBid.window_id == window_id,
                TransferBid.player_id == player_id,
                TransferBid.id != accepted_bid_id,
                TransferBid.status == TransferBidStatus.SUBMITTED.value,
            )
        ).all()
        for competing_bid in competing_bids:
            terms = dict(competing_bid.structured_terms_json or {})
            terms["auto_rejected_reason"] = "player_signed_elsewhere"
            competing_bid.status = TransferBidStatus.REJECTED.value
            competing_bid.structured_terms_json = terms
            competing_offer = self._get_contract_offer_by_bid_id(competing_bid.id)
            if competing_offer is not None:
                competing_offer.status = TransferBidStatus.REJECTED.value
                competing_offer.metadata_json = {
                    **dict(competing_offer.metadata_json or {}),
                    "auto_rejected_reason": "player_signed_elsewhere",
                }
        self.session.flush()

    def _settle_regen_contract_offer(
        self,
        *,
        bid: TransferBid,
        offer: RegenContractOffer,
        new_contract: PlayerContract,
        acceptance_on: date,
    ) -> None:
        if bid.buying_club_id is None:
            raise PlayerLifecycleValidationError("Transfer bid is missing a buying club")
        buying_club = self._require_club_profile(bid.buying_club_id)
        owner = self._require_user(buying_club.owner_user_id)
        wallet_service = WalletService()
        salary_package = (offer.offered_salary_fancoin_per_year * offer.contract_years).quantize(Decimal("0.0001"))
        fancoin_summary = wallet_service.get_wallet_summary(self.session, owner, currency=LedgerUnit.CREDIT)
        gtex_summary = wallet_service.get_wallet_summary(self.session, owner, currency=LedgerUnit.COIN)
        conversion = quote_conversion(
            required_fancoin=salary_package,
            current_fancoin_balance=fancoin_summary.available_balance,
            current_gtex_balance=gtex_summary.available_balance,
        )
        total_gtex_required = offer.training_fee_gtex_coin + conversion.gtex_required_for_conversion
        if gtex_summary.available_balance < total_gtex_required:
            raise PlayerLifecycleValidationError(
                "Buying club owner does not have enough GTex Coin for the training fee and required Fan Coin auto-conversion"
            )
        if conversion.shortfall_fancoin > 0 and not conversion.can_cover_shortfall:
            raise PlayerLifecycleValidationError("Buying club owner cannot cover the Fan Coin salary shortfall")
        if conversion.shortfall_fancoin > 0:
            wallet_service.settle_available_funds(
                self.session,
                user=owner,
                amount=conversion.gtex_required_for_conversion,
                reference=f"regen-offer:{offer.id}:conversion",
                description=f"Auto-convert GTex Coin for {new_contract.player_id} contract salary",
                external_reference=offer.id,
                unit=LedgerUnit.COIN,
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            )
            wallet_service.credit_trade_proceeds(
                self.session,
                user=owner,
                amount=conversion.shortfall_fancoin,
                reference=f"regen-offer:{offer.id}:conversion-credit",
                description=f"Fan Coin credited from GTex auto-conversion for {new_contract.player_id}",
                external_reference=offer.id,
                unit=LedgerUnit.CREDIT,
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            )
        refreshed_fancoin_balance = wallet_service.get_wallet_summary(
            self.session,
            owner,
            currency=LedgerUnit.CREDIT,
        ).available_balance
        if refreshed_fancoin_balance < salary_package:
            raise PlayerLifecycleValidationError("Buying club owner does not have enough Fan Coin for the salary package")

        free_agent_terms = dict((bid.structured_terms_json or {}).get("free_agent_capture_split") or {})
        previous_club_id = bid.selling_club_id or free_agent_terms.get("previous_club_id")
        previous_owner: User | None = None
        if previous_club_id:
            previous_club = self._get_club_profile(previous_club_id)
            if previous_club is not None and previous_club.owner_user_id:
                previous_owner = self._require_user(previous_club.owner_user_id)
        platform_share = offer.training_fee_gtex_coin
        previous_share = Decimal("0.0000")
        if previous_owner is not None:
            previous_share = (
                offer.training_fee_gtex_coin
                * Decimal(str(REGEN_FREE_AGENT_PREVIOUS_CLUB_SHARE_PCT))
                / Decimal("100")
            ).quantize(Decimal("0.0001"))
            platform_share = offer.training_fee_gtex_coin - previous_share
        payer_account = wallet_service.get_user_account(self.session, owner, LedgerUnit.COIN)
        platform_coin_account = wallet_service.ensure_platform_account(self.session, LedgerUnit.COIN)
        postings = [
            LedgerPosting(
                account=payer_account,
                amount=-offer.training_fee_gtex_coin,
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            ),
            LedgerPosting(
                account=platform_coin_account,
                amount=platform_share,
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            ),
        ]
        if previous_share > 0 and previous_owner is not None:
            postings.append(
                LedgerPosting(
                    account=wallet_service.get_user_account(self.session, previous_owner, LedgerUnit.COIN),
                    amount=previous_share,
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                )
            )
        else:
            postings[1] = LedgerPosting(
                account=platform_coin_account,
                amount=offer.training_fee_gtex_coin,
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            )
        wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.TRADE_SETTLEMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            reference=f"regen-offer:{offer.id}:training-fee",
            description=f"Training fee settlement for regen {offer.regen_id}",
            external_reference=offer.id,
            actor=owner,
        )
        wallet_service.settle_available_funds(
            self.session,
            user=owner,
            amount=salary_package,
            reference=f"regen-offer:{offer.id}:salary",
            description=f"Fan Coin salary package for regen {offer.regen_id}",
            external_reference=offer.id,
            unit=LedgerUnit.CREDIT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        )
        offer.metadata_json = {
            **dict(offer.metadata_json or {}),
            "settled_on": acceptance_on.isoformat(),
            "salary_package_fancoin": str(salary_package),
            "conversion_shortfall_fancoin": str(conversion.shortfall_fancoin),
            "conversion_gtex_used": str(conversion.gtex_required_for_conversion),
            "previous_club_id": previous_club_id,
        }

    def _publish_transfer_headline(
        self,
        *,
        player: Player,
        regen: RegenProfile,
        bid: TransferBid,
        offer: RegenContractOffer | None,
        contract: PlayerContract,
    ) -> TransferHeadlineMediaRecord:
        if bid.buying_club_id is None:
            raise PlayerLifecycleValidationError("Transfer bid is missing a buying club")
        buying_club = self._require_club_profile(bid.buying_club_id)
        selling_club = self._get_club_profile(bid.selling_club_id)
        transfer_fee = offer.training_fee_gtex_coin if offer is not None else bid.bid_amount
        contract_years = (
            offer.contract_years
            if offer is not None
            else max(1, round((((contract.ends_on - contract.starts_on).days + 1) / 365)))
        )
        previous_buying_record = self.session.scalar(
            select(TransferHeadlineMediaRecord)
            .where(TransferHeadlineMediaRecord.buying_club_id == buying_club.id)
            .order_by(
                TransferHeadlineMediaRecord.transfer_fee_gtex_coin.desc(),
                TransferHeadlineMediaRecord.created_at.desc(),
            )
        )
        previous_selling_record = (
            self.session.scalar(
                select(TransferHeadlineMediaRecord)
                .where(TransferHeadlineMediaRecord.selling_club_id == selling_club.id)
                .order_by(
                    TransferHeadlineMediaRecord.transfer_fee_gtex_coin.desc(),
                    TransferHeadlineMediaRecord.created_at.desc(),
                )
            )
            if selling_club is not None
            else None
        )
        club_record_signing = bool(
            previous_buying_record is not None and transfer_fee > previous_buying_record.transfer_fee_gtex_coin
        )
        biggest_sale = bool(
            previous_selling_record is not None and transfer_fee > previous_selling_record.transfer_fee_gtex_coin
        )
        headline = render_transfer_headline(
            player_name=player.full_name,
            selling_club_name=selling_club.club_name if selling_club is not None else None,
            buying_club_name=buying_club.club_name,
            transfer_fee_gtex_coin=transfer_fee,
            salary_fancoin_per_year=contract.wage_amount,
            contract_years=contract_years,
            eur_per_gtex=self.settings.value_engine_weighting.baseline_eur_per_credit,
            free_agent=offer is not None and bid.selling_club_id is None,
            wonderkid=int((regen.potential_range_json or {}).get("maximum", regen.current_gsi)) >= 82,
            legend_tagged=bool(regen.is_special_lineage),
            club_record_signing=club_record_signing,
            biggest_sale=biggest_sale,
        )
        record = TransferHeadlineMediaRecord(
            regen_id=regen.id,
            buying_club_id=buying_club.id,
            selling_club_id=selling_club.id if selling_club is not None else None,
            related_entity_type="transfer_bid",
            related_entity_id=bid.id,
            headline_category=headline.category,
            announcement_tier=headline.announcement_tier,
            estimated_transfer_fee_eur=headline.estimated_transfer_fee_eur,
            estimated_salary_package_eur=headline.estimated_salary_package_eur,
            estimated_total_value_eur=headline.estimated_total_value_eur,
            transfer_fee_gtex_coin=transfer_fee,
            salary_package_fancoin=headline.salary_package_fancoin,
            headline_text=headline.headline,
            detail_text=headline.detail_text,
            metadata_json={
                "player_id": player.id,
                "buying_club_id": buying_club.id,
                "selling_club_id": selling_club.id if selling_club is not None else None,
            },
        )
        self.session.add(record)
        self.session.flush()
        surfaces = ["global_news_feed", "club_pages", "player_page", "transfer_center"]
        if selling_club is not None:
            surfaces.append("rivalry_pages")
        if headline.announcement_tier != "feed_card":
            surfaces.append("follower_notifications")
        if headline.announcement_tier == "platform_headline":
            surfaces.append("record_history")
        story = StoryFeedService(self.session).publish(
            story_type="transfer",
            title=headline.headline[:200],
            body=headline.detail_text,
            audience="public",
            subject_type="player",
            subject_id=player.id,
            metadata_json={
                "transfer_headline_record_id": record.id,
                "announcement_tier": headline.announcement_tier,
                "category": headline.category,
                "surfaces": surfaces,
            },
            featured=headline.announcement_tier != "feed_card",
            published_by_user_id=buying_club.owner_user_id,
        )
        platform_announcement: PlatformAnnouncement | None = None
        if headline.announcement_tier == "platform_headline":
            platform_announcement = PlatformAnnouncement(
                announcement_key=f"regen-transfer:{record.id}",
                title=headline.headline[:180],
                body=headline.detail_text,
                audience="all",
                severity="info",
                active=True,
                deliver_as_notification=True,
                metadata_json={
                    "transfer_headline_record_id": record.id,
                    "player_id": player.id,
                    "regen_id": regen.id,
                },
                published_by_user_id=buying_club.owner_user_id,
            )
            self.session.add(platform_announcement)
            self.session.flush()
        recipient_user_ids = {
            user_id
            for user_id in {buying_club.owner_user_id, selling_club.owner_user_id if selling_club is not None else None}
            if user_id
        }
        for user_id in recipient_user_ids:
            self.session.add(
                NotificationRecord(
                    user_id=user_id,
                    topic="major_transfer",
                    template_key="regen_transfer_headline",
                    resource_type="transfer_headline_media_record",
                    resource_id=record.id,
                    message=headline.headline[:255],
                    metadata_json={
                        "announcement_tier": headline.announcement_tier,
                        "category": headline.category,
                        "player_id": player.id,
                    },
                )
            )
        self.session.add(
            MajorTransferAnnouncement(
                regen_id=regen.id,
                headline_record_id=record.id,
                story_feed_item_id=story.id,
                platform_announcement_id=platform_announcement.id if platform_announcement is not None else None,
                announcement_category=headline.category,
                announcement_tier=headline.announcement_tier,
                status="published",
                surfaces_json=surfaces,
                metadata_json={
                    "player_id": player.id,
                    "buying_club_id": buying_club.id,
                    "selling_club_id": selling_club.id if selling_club is not None else None,
                },
            )
        )
        self.session.flush()
        return record

    def _resolve_regen_traits(self, regen: RegenProfile) -> dict[str, int]:
        metadata = dict(regen.metadata_json or {})
        decision_traits = dict(metadata.get("decision_traits") or {})
        personality = self._get_regen_personality(regen.id)
        resolved = {
            "ambition": int(decision_traits.get("ambition", getattr(personality, "ambition", 50) if personality is not None else 50)),
            "loyalty": int(decision_traits.get("loyalty", getattr(personality, "loyalty", 50) if personality is not None else 50)),
            "professionalism": int(decision_traits.get("professionalism", getattr(personality, "work_rate", 50) if personality is not None else 50)),
            "greed": int(decision_traits.get("greed", 50)),
            "patience": int(decision_traits.get("patience", getattr(personality, "resilience", 50) if personality is not None else 50)),
            "hometown_affinity": int(decision_traits.get("hometown_affinity", 50)),
            "trophy_hunger": int(decision_traits.get("trophy_hunger", 50)),
            "media_appetite": int(decision_traits.get("media_appetite", 50)),
            "temperament": int(decision_traits.get("temperament", getattr(personality, "temperament", 50) if personality is not None else 50)),
            "adaptability": int(decision_traits.get("adaptability", 50)),
        }
        return {key: max(0, min(100, value)) for key, value in resolved.items()}

    def _sync_regen_state(
        self,
        player: Player,
        regen: RegenProfile,
        *,
        reference_on: date,
        contract_summary: ContractSummaryView | None,
        bids: list[TransferBid],
    ) -> dict[str, Any]:
        del bids
        state = self._regen_career_state(regen)
        traits = self._resolve_regen_traits(regen)
        lifecycle_age_months = self._months_between(regen.generated_at.date(), reference_on)
        phase = self._regen_phase_for_age(lifecycle_age_months)
        retired = lifecycle_age_months >= self.settings.regen_generation.regen_lifecycle_retirement_months
        state["lifecycle_age_months"] = lifecycle_age_months
        state["lifecycle_phase"] = "retired" if retired else phase
        state["retirement_pressure"] = phase == "retirement_pressure"
        if contract_summary is not None and contract_summary.active_contract is not None:
            state["previous_club_id"] = contract_summary.active_contract.club_id
        elif not state.get("previous_club_id"):
            last_contract = self._select_primary_contract(self.get_contracts(player.id), reference_on=reference_on)
            state["previous_club_id"] = last_contract.club_id if last_contract is not None else regen.generated_for_club_id
        free_agent = not retired and (contract_summary is None or contract_summary.active_contract is None)
        state["free_agent"] = free_agent
        if free_agent and not state.get("free_agent_since"):
            state["free_agent_since"] = reference_on.isoformat()
        elif not free_agent:
            state["free_agent_since"] = None
        pressure = None
        if not retired:
            pressure = self._ensure_pressure_state(
                player,
                regen,
                reference_on=reference_on,
                contract_summary=contract_summary,
            )
            state["pressure_state"] = pressure.current_state
            state["pressure_score"] = pressure.pressure_score

        playing_time_ratio = self._current_playing_time_ratio(player)
        wants_transfer = (
            not retired
            and not free_agent
            and (
                (pressure.active_transfer_request if pressure is not None else False)
                or (
                    pressure is not None
                    and pressure.current_state in {"attracted_by_bigger_club", "considering_transfer", "transfer_requested", "unsettled"}
                )
                or
                (playing_time_ratio < 0.45 and traits["ambition"] >= 68 and traits["patience"] <= 58)
                or (
                    contract_summary is not None
                    and contract_summary.expiring_soon
                    and traits["loyalty"] <= 48
                    and (traits["ambition"] >= 65 or traits["greed"] >= 65)
                )
            )
        )
        transfer_listed_before = bool(state.get("transfer_listed", False))
        state["transfer_listed"] = bool(wants_transfer)
        if retired:
            state["retired"] = True
            state["agency_message"] = "Retired from the active football economy."
            regen.status = "retired"
            player.is_tradable = False
            player.current_club_profile_id = None
            if not state.get("retired_on"):
                state["retired_on"] = reference_on.isoformat()
                self._record_event(
                    player_id=player.id,
                    club_id=state.get("previous_club_id"),
                    event_type=REGEN_RETIREMENT_EVENT_TYPE,
                    event_status="archived",
                    occurred_on=reference_on,
                    effective_from=reference_on,
                    effective_to=None,
                    related_entity_type="regen_profile",
                    related_entity_id=regen.id,
                    summary=f"{player.full_name} retired",
                    details={"regen_id": regen.regen_id, "lifecycle_age_months": lifecycle_age_months},
                    notes=None,
                )
                from app.services.regen_legacy_service import RegenLegacyService

                RegenLegacyService(self.session).snapshot_legacy(
                    regen.id,
                    club_id=state.get("previous_club_id"),
                    retired_on=reference_on,
                )
            active_contract = self._select_current_contract(self.get_contracts(player.id), reference_on=reference_on)
            if active_contract is not None and active_contract.status != ContractStatus.TERMINATED.value:
                active_contract.status = ContractStatus.TERMINATED.value
                active_contract.ends_on = min(active_contract.ends_on, reference_on)
        elif free_agent:
            regen.status = "free_agent"
            state["agency_message"] = "Open to free-agent offers."
            player.current_club_profile_id = None
            if state.get("free_agent_since") == reference_on.isoformat():
                self._record_regen_agency_event(
                    player_id=player.id,
                    club_id=state.get("previous_club_id"),
                    event_type=REGEN_FREE_AGENCY_EVENT_TYPE,
                    reference_on=reference_on,
                    regen=regen,
                    summary=f"{player.full_name} entered free agency",
                    details={
                        "regen_id": regen.regen_id,
                        "platform_pct": REGEN_FREE_AGENT_PLATFORM_SHARE_PCT,
                        "previous_club_pct": REGEN_FREE_AGENT_PREVIOUS_CLUB_SHARE_PCT,
                    },
                )
        else:
            regen.status = "active"
            if pressure is not None and state.get("transfer_listed") and bool((pressure.metadata_json or {}).get("manual_transfer_request")):
                state["agency_message"] = "Requested to be transfer listed."
            elif pressure is not None and pressure.current_state == "unsettled":
                state["agency_message"] = "Unsettled after interest from a bigger club."
            elif pressure is not None and pressure.active_transfer_request:
                state["agency_message"] = "Requested to be transfer listed."
            elif pressure is not None and pressure.refuses_new_contract:
                state["agency_message"] = "Refuses to renew without a bigger project."
            elif pressure is not None and pressure.current_state == "considering_transfer":
                state["agency_message"] = "Considering a move."
            elif pressure is not None and pressure.current_state == "attracted_by_bigger_club":
                state["agency_message"] = "Attracted by bigger-club interest."
            elif playing_time_ratio < 0.45 and traits["ambition"] >= 68:
                state["agency_message"] = "Requests more playing time."
                self._record_regen_agency_event(
                    player_id=player.id,
                    club_id=player.current_club_profile_id,
                    event_type=REGEN_PLAYING_TIME_REQUEST_EVENT_TYPE,
                    reference_on=reference_on,
                    regen=regen,
                    summary=f"{player.full_name} wants more playing time",
                    details={"playing_time_ratio": round(playing_time_ratio, 2)},
                )
            elif contract_summary is not None and contract_summary.expiring_soon and (traits["greed"] >= 65 or traits["ambition"] >= 70):
                state["agency_message"] = "Wants an improved contract offer."
                self._record_regen_agency_event(
                    player_id=player.id,
                    club_id=player.current_club_profile_id,
                    event_type=REGEN_CONTRACT_DISSATISFACTION_EVENT_TYPE,
                    reference_on=reference_on,
                    regen=regen,
                    summary=f"{player.full_name} is dissatisfied with contract terms",
                    details={"days_remaining": contract_summary.days_remaining},
                )
            else:
                state["agency_message"] = "Settled in the squad."
        if state.get("transfer_listed") and not transfer_listed_before:
            self._record_event(
                player_id=player.id,
                club_id=player.current_club_profile_id,
                event_type=REGEN_TRANSFER_LIST_EVENT_TYPE,
                event_status="active",
                occurred_on=reference_on,
                effective_from=reference_on,
                effective_to=None,
                related_entity_type="regen_profile",
                related_entity_id=regen.id,
                summary=f"{player.full_name} requested transfer listing",
                details={"playing_time_ratio": round(playing_time_ratio, 2)},
                notes=None,
            )
        elif transfer_listed_before and not state.get("transfer_listed"):
            self._resolve_related_event(
                player_id=player.id,
                event_type=REGEN_TRANSFER_LIST_EVENT_TYPE,
                related_entity_type="regen_profile",
                related_entity_id=regen.id,
                resolved_at=datetime.combine(reference_on, datetime.min.time()),
            )
        self._set_regen_career_state(regen, state)
        self.session.flush()
        return state

    def _record_regen_agency_event(
        self,
        *,
        player_id: str,
        club_id: str | None,
        event_type: str,
        reference_on: date,
        regen: RegenProfile,
        summary: str,
        details: dict[str, Any],
    ) -> None:
        recent = self.session.scalar(
            select(PlayerLifecycleEvent).where(
                PlayerLifecycleEvent.player_id == player_id,
                PlayerLifecycleEvent.event_type == event_type,
                PlayerLifecycleEvent.occurred_on == reference_on,
                PlayerLifecycleEvent.related_entity_id == regen.id,
            )
        )
        if recent is not None:
            return
        self._record_event(
            player_id=player_id,
            club_id=club_id,
            event_type=event_type,
            event_status="active",
            occurred_on=reference_on,
            effective_from=reference_on,
            effective_to=None,
            related_entity_type="regen_profile",
            related_entity_id=regen.id,
            summary=summary,
            details=details,
            notes=None,
        )

    def _months_between(self, start_on: date, end_on: date) -> int:
        months = (end_on.year - start_on.year) * 12 + (end_on.month - start_on.month)
        if end_on.day < start_on.day:
            months -= 1
        return max(0, months)

    def _regen_phase_for_age(self, lifecycle_age_months: int) -> str:
        if lifecycle_age_months >= self.settings.regen_generation.regen_lifecycle_decline_months:
            return "retirement_pressure"
        if lifecycle_age_months >= self.settings.regen_generation.regen_lifecycle_peak_months:
            return "decline"
        if lifecycle_age_months >= self.settings.regen_generation.regen_lifecycle_growth_months:
            return "peak"
        return "development"

    def _current_playing_time_ratio(self, player: Player) -> float:
        if not player.season_stats:
            return 1.0
        latest = max(player.season_stats, key=lambda item: (item.season_id or "", item.updated_at))
        appearances = latest.appearances or 0
        starts = latest.starts or 0
        if appearances <= 0:
            return 1.0
        return starts / appearances

    def _validate_regen_contract_duration(self, starts_on: date, ends_on: date) -> None:
        duration_days = (ends_on - starts_on).days + 1
        if duration_days < REGEN_CONTRACT_MIN_DAYS or duration_days > REGEN_CONTRACT_MAX_DAYS:
            raise PlayerLifecycleValidationError("Regen contracts must be between one and three seasons in length")

    def _season_label(self, reference_on: date) -> str:
        start_year = reference_on.year if reference_on.month >= 7 else reference_on.year - 1
        return f"{start_year}/{start_year + 1}"

    def _validate_regen_special_training(
        self,
        player: Player,
        regen: RegenProfile,
        payload: RegenSpecialTrainingRequest,
        *,
        reference_on: date,
    ) -> None:
        projected_ceiling = int((regen.potential_range_json or {}).get("maximum", regen.current_gsi))
        if projected_ceiling > 75:
            raise PlayerLifecycleValidationError("Only regens with projected future potential of 75 or lower are eligible")
        state = self._regen_career_state(regen)
        if bool(state.get("retired", False)):
            raise PlayerLifecycleValidationError("Retired regens cannot receive special training")
        training_state = self._regen_training_state(regen)
        cooldown_until = training_state.get("cooldown_until")
        if cooldown_until and reference_on < date.fromisoformat(cooldown_until):
            raise PlayerLifecycleValidationError("Special training is on cooldown for this regen")
        if payload.package_type == "major" and int(training_state.get("major_used_count", 0)) >= REGEN_SPECIAL_TRAINING_MAJOR_MAX:
            raise PlayerLifecycleValidationError("A regen can only receive one major special training package")
        if payload.package_type == "minor" and int(training_state.get("minor_used_count", 0)) >= REGEN_SPECIAL_TRAINING_MINOR_MAX:
            raise PlayerLifecycleValidationError("A regen can only receive two minor special training packages")
        club_id = payload.club_id or player.current_club_profile_id
        season_label = self._season_label(reference_on)
        if self._count_regen_special_training_for_club(club_id, season_label=season_label) >= REGEN_SPECIAL_TRAINING_SEASON_CAP:
            raise PlayerLifecycleValidationError("Club special-training season cap reached")
        if self._count_regen_special_training_for_club(club_id, season_label=season_label, active_only=True, reference_on=reference_on) >= REGEN_SPECIAL_TRAINING_CONCURRENT_CAP:
            raise PlayerLifecycleValidationError("Club concurrent special-training cap reached")

    def _count_regen_special_training_for_club(
        self,
        club_id: str | None,
        *,
        season_label: str,
        active_only: bool = False,
        reference_on: date | None = None,
    ) -> int:
        if club_id is None:
            return 0
        statement = select(PlayerLifecycleEvent).where(
            PlayerLifecycleEvent.club_id == club_id,
            PlayerLifecycleEvent.event_type == REGEN_SPECIAL_TRAINING_EVENT_TYPE,
        )
        count = 0
        for event in self.session.scalars(statement):
            details = event.details_json or {}
            if details.get("season_label") not in {None, season_label}:
                continue
            if active_only and reference_on is not None and event.effective_to is not None and event.effective_to < reference_on:
                continue
            count += 1
        return count

    def _regen_club_context(self, club_id: str | None, regen: RegenProfile) -> dict[str, float | bool]:
        if club_id is None:
            return {
                "prestige": 0.0,
                "trophy_score": 0.0,
                "development_score": 0.0,
                "hometown_score": 0.0,
                "playing_time_score": 0.0,
                "cross_border": False,
            }
        profile = self._get_club_profile(club_id)
        reputation = self.session.scalar(select(ClubReputationProfile).where(ClubReputationProfile.club_id == club_id))
        facility = self.session.scalar(select(ClubFacility).where(ClubFacility.club_id == club_id))
        origin = self._get_regen_origin(regen.id)
        reputation_score = float(reputation.current_score if reputation is not None else 45)
        trophy_score = min(
            100.0,
            float(
                ((reputation.total_league_titles if reputation is not None else 0) * 8)
                + ((reputation.total_continental_titles if reputation is not None else 0) * 12)
                + ((reputation.total_world_super_cup_titles if reputation is not None else 0) * 20)
            ),
        )
        development_score = float(
            (((facility.training_level if facility is not None else 1) + (facility.academy_level if facility is not None else 1)) / 2) * 20
        )
        hometown_score = 0.0
        cross_border = False
        if profile is not None and origin is not None:
            cross_border = bool(profile.country_code and profile.country_code != origin.country_code)
            if profile.city_name and origin.city_name and profile.city_name.lower() == origin.city_name.lower():
                hometown_score = 100.0
            elif profile.region_name and origin.region_name and profile.region_name.lower() == origin.region_name.lower():
                hometown_score = 80.0
            elif profile.country_code and profile.country_code == origin.country_code:
                hometown_score = 45.0
        playing_time_score = max(15.0, min(100.0, 95.0 - (reputation_score * 0.45) + (development_score * 0.2)))
        return {
            "prestige": min(100.0, (reputation_score * 0.7) + (trophy_score * 0.3)),
            "trophy_score": trophy_score,
            "development_score": development_score,
            "hometown_score": hometown_score,
            "playing_time_score": playing_time_score,
            "cross_border": cross_border,
        }

    def _top_regen_bid_reasons(
        self,
        *,
        salary_score: float,
        prestige_score: float,
        playing_time_score: float,
        development_score: float,
        hometown_score: float,
        trophy_score: float,
    ) -> tuple[str, ...]:
        ranked = sorted(
            [
                ("salary", salary_score),
                ("prestige", prestige_score),
                ("playing_time", playing_time_score),
                ("development", development_score),
                ("hometown", hometown_score),
                ("trophies", trophy_score),
            ],
            key=lambda item: item[1],
            reverse=True,
        )
        return tuple(label for label, value in ranked[:3] if value > 0)

    def _preferred_regen_contract_days(self, regen: RegenProfile, reference_on: date) -> int:
        traits = self._resolve_regen_traits(regen)
        phase = self._regen_phase_for_age(self._months_between(regen.generated_at.date(), reference_on))
        if phase == "retirement_pressure":
            return 365
        if phase == "decline":
            return 730 if traits["professionalism"] >= 60 else 365
        if phase == "peak":
            return 730 if traits["patience"] >= 50 else 365
        return 1095 if traits["professionalism"] >= 55 else 730

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
