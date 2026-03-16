"""GTEX club finances, sponsorships, academy progression, and youth scouting are transparent club-management and development systems tied to catalog/contract-based operations and rule-based player progression. They are not wagering products, hidden-odds mechanics, or luck-based cash systems."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from threading import RLock
from uuid import uuid4

from backend.app.common.enums.club_finance_account_type import ClubFinanceAccountType
from backend.app.common.enums.club_finance_entry_type import ClubFinanceEntryType
from backend.app.schemas.club_finance_core import (
    ClubBudgetSnapshotView,
    ClubCashflowSummaryView,
    ClubFinanceAccountView,
    ClubFinanceLedgerEntryView,
)
from backend.app.schemas.club_ops_responses import ClubFinanceLedgerResponse, ClubFinanceOverviewResponse

_DEFAULT_CURRENCY = "USD"
_OPENING_BALANCE_MINOR = 1_500_000


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _titleize_club_label(club_id: str) -> str:
    words = [word for word in club_id.replace("_", "-").split("-") if word]
    return " ".join(word.capitalize() for word in words) or club_id


def _account_allows_negative(account_type: ClubFinanceAccountType) -> bool:
    return account_type in {
        ClubFinanceAccountType.ACADEMY_SPEND,
        ClubFinanceAccountType.SCOUTING_SPEND,
        ClubFinanceAccountType.BRANDING_SPEND,
        ClubFinanceAccountType.FACILITIES_SPEND,
        ClubFinanceAccountType.TRANSFER_SPEND,
    }


@dataclass(slots=True)
class FinanceAccountRecord:
    id: str
    club_id: str
    account_type: ClubFinanceAccountType
    currency: str
    balance_minor: int = 0
    allow_negative: bool = False
    is_active: bool = True


@dataclass(slots=True)
class LedgerEntryRecord:
    id: str
    transaction_id: str
    club_id: str
    account_type: ClubFinanceAccountType
    entry_type: ClubFinanceEntryType
    amount_minor: int
    currency: str
    description: str | None
    reference_id: str | None
    created_at: datetime
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ClubOpsStore:
    accounts_by_club: dict[str, dict[ClubFinanceAccountType, FinanceAccountRecord]] = field(default_factory=dict)
    ledger_by_club: dict[str, list[LedgerEntryRecord]] = field(default_factory=dict)
    budgets_by_club: dict[str, ClubBudgetSnapshotView] = field(default_factory=dict)
    cashflows_by_club: dict[str, ClubCashflowSummaryView] = field(default_factory=dict)
    sponsorship_packages: dict[str, object] = field(default_factory=dict)
    sponsorship_contracts_by_club: dict[str, dict[str, object]] = field(default_factory=dict)
    sponsorship_assets_by_club: dict[str, dict[str, object]] = field(default_factory=dict)
    academy_programs_by_club: dict[str, dict[str, object]] = field(default_factory=dict)
    academy_players_by_club: dict[str, dict[str, object]] = field(default_factory=dict)
    academy_progress_by_player: dict[str, list[object]] = field(default_factory=dict)
    academy_training_cycles_by_club: dict[str, dict[str, object]] = field(default_factory=dict)
    academy_graduations_by_club: dict[str, list[object]] = field(default_factory=dict)
    scouting_regions: dict[str, object] = field(default_factory=dict)
    scouting_assignments_by_club: dict[str, dict[str, object]] = field(default_factory=dict)
    prospects_by_club: dict[str, dict[str, object]] = field(default_factory=dict)
    prospect_reports_by_prospect: dict[str, list[object]] = field(default_factory=dict)
    youth_pipeline_by_club: dict[str, object] = field(default_factory=dict)
    regen_profiles_by_club: dict[str, dict[str, object]] = field(default_factory=dict)
    academy_intake_batches_by_club: dict[str, dict[str, object]] = field(default_factory=dict)
    academy_candidates_by_club: dict[str, dict[str, object]] = field(default_factory=dict)
    regen_generation_events_by_club: dict[str, list[object]] = field(default_factory=dict)
    season_regen_generation_counts: dict[str, int] = field(default_factory=dict)
    owner_son_lifetime_counts_by_user: dict[str, int] = field(default_factory=dict)
    owner_son_pending_requests_by_club: dict[str, list[object]] = field(default_factory=dict)
    owner_son_fulfilled_requests_by_club: dict[str, list[object]] = field(default_factory=dict)
    club_labels: dict[str, str] = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock)


class ClubFinanceService:
    def __init__(self, *, store: ClubOpsStore | None = None) -> None:
        self.store = store or get_club_ops_store()

    def tracked_club_ids(self) -> tuple[str, ...]:
        with self.store.lock:
            club_ids = set(self.store.accounts_by_club)
            club_ids.update(self.store.sponsorship_contracts_by_club)
            club_ids.update(self.store.academy_players_by_club)
            club_ids.update(self.store.scouting_assignments_by_club)
            club_ids.update(self.store.prospects_by_club)
            club_ids.update(self.store.regen_profiles_by_club)
            club_ids.update(self.store.academy_intake_batches_by_club)
        return tuple(sorted(club_ids))

    def get_finance_overview(self, club_id: str) -> ClubFinanceOverviewResponse:
        self.ensure_club_setup(club_id)
        accounts = tuple(self._account_view(record) for record in self._accounts_for_club(club_id).values())
        return ClubFinanceOverviewResponse(
            club_id=club_id,
            currency=_DEFAULT_CURRENCY,
            accounts=accounts,
            budget=self.get_budget_snapshot(club_id),
            cashflow=self.get_cashflow_summary(club_id),
        )

    def get_ledger(self, club_id: str) -> ClubFinanceLedgerResponse:
        self.ensure_club_setup(club_id)
        with self.store.lock:
            entries = tuple(self._ledger_view(entry) for entry in self.store.ledger_by_club.get(club_id, ()))
        return ClubFinanceLedgerResponse(club_id=club_id, entries=entries)

    def get_budget_snapshot(self, club_id: str) -> ClubBudgetSnapshotView:
        self.ensure_club_setup(club_id)
        with self.store.lock:
            accounts = self._accounts_for_club(club_id)
            operating_balance_minor = accounts[ClubFinanceAccountType.OPERATING_BALANCE].balance_minor
            academy_allocation_minor = sum(
                int(getattr(program, "budget_minor", 0))
                for program in self.store.academy_programs_by_club.get(club_id, {}).values()
                if getattr(program, "is_active", False)
            )
            scouting_allocation_minor = sum(
                int(getattr(assignment, "budget_minor", 0))
                for assignment in self.store.scouting_assignments_by_club.get(club_id, {}).values()
                if getattr(getattr(assignment, "status", None), "value", getattr(assignment, "status", None))
                not in {"completed", "cancelled"}
            )
            sponsorship_commitment_minor = sum(
                int(getattr(contract, "outstanding_amount_minor", 0))
                for contract in self.store.sponsorship_contracts_by_club.get(club_id, {}).values()
            )
            snapshot = ClubBudgetSnapshotView(
                club_id=club_id,
                total_budget_minor=operating_balance_minor,
                academy_allocation_minor=academy_allocation_minor,
                scouting_allocation_minor=scouting_allocation_minor,
                sponsorship_commitment_minor=sponsorship_commitment_minor,
                available_budget_minor=operating_balance_minor - academy_allocation_minor - scouting_allocation_minor,
                captured_at=_utcnow(),
            )
            self.store.budgets_by_club[club_id] = snapshot
            return snapshot

    def get_cashflow_summary(self, club_id: str) -> ClubCashflowSummaryView:
        self.ensure_club_setup(club_id)
        with self.store.lock:
            ledger = tuple(self.store.ledger_by_club.get(club_id, ()))
        operating_entries = [entry for entry in ledger if entry.account_type == ClubFinanceAccountType.OPERATING_BALANCE]
        total_income_minor = sum(entry.amount_minor for entry in operating_entries if entry.amount_minor > 0)
        total_expense_minor = abs(sum(entry.amount_minor for entry in operating_entries if entry.amount_minor < 0))
        sponsorship_income_minor = sum(
            entry.amount_minor
            for entry in ledger
            if entry.account_type == ClubFinanceAccountType.SPONSORSHIP_INCOME and entry.amount_minor > 0
        )
        competition_income_minor = sum(
            entry.amount_minor
            for entry in ledger
            if entry.account_type == ClubFinanceAccountType.COMPETITION_INCOME and entry.amount_minor > 0
        )
        academy_spend_minor = abs(
            sum(
                entry.amount_minor
                for entry in ledger
                if entry.account_type == ClubFinanceAccountType.ACADEMY_SPEND and entry.amount_minor < 0
            )
        )
        scouting_spend_minor = abs(
            sum(
                entry.amount_minor
                for entry in ledger
                if entry.account_type == ClubFinanceAccountType.SCOUTING_SPEND and entry.amount_minor < 0
            )
        )
        summary = ClubCashflowSummaryView(
            club_id=club_id,
            currency=_DEFAULT_CURRENCY,
            total_income_minor=total_income_minor,
            total_expense_minor=total_expense_minor,
            net_cashflow_minor=total_income_minor - total_expense_minor,
            sponsorship_income_minor=sponsorship_income_minor,
            competition_income_minor=competition_income_minor,
            academy_spend_minor=academy_spend_minor,
            scouting_spend_minor=scouting_spend_minor,
            as_of=_utcnow(),
        )
        with self.store.lock:
            self.store.cashflows_by_club[club_id] = summary
        return summary

    def record_manual_adjustment(
        self,
        club_id: str,
        *,
        amount_minor: int,
        description: str,
        reference_id: str | None = None,
    ) -> tuple[ClubFinanceLedgerEntryView, ...]:
        return self._record_entries(
            club_id,
            entry_type=ClubFinanceEntryType.MANUAL_ADMIN_ADJUSTMENT,
            postings=((ClubFinanceAccountType.OPERATING_BALANCE, amount_minor),),
            description=description,
            reference_id=reference_id,
            metadata={"source": "manual_adjustment"},
        )

    def record_competition_reward(
        self,
        club_id: str,
        *,
        amount_minor: int,
        reference_id: str | None = None,
    ) -> tuple[ClubFinanceLedgerEntryView, ...]:
        return self._record_entries(
            club_id,
            entry_type=ClubFinanceEntryType.COMPETITION_REWARD_CREDIT,
            postings=(
                (ClubFinanceAccountType.COMPETITION_INCOME, amount_minor),
                (ClubFinanceAccountType.OPERATING_BALANCE, amount_minor),
            ),
            description="Transparent competition income posted to club operations.",
            reference_id=reference_id,
            metadata={"source": "competition_income"},
        )

    def record_sponsorship_credit(
        self,
        club_id: str,
        *,
        amount_minor: int,
        reference_id: str | None = None,
        description: str | None = None,
    ) -> tuple[ClubFinanceLedgerEntryView, ...]:
        return self._record_entries(
            club_id,
            entry_type=ClubFinanceEntryType.SPONSORSHIP_CREDIT,
            postings=(
                (ClubFinanceAccountType.SPONSORSHIP_INCOME, amount_minor),
                (ClubFinanceAccountType.OPERATING_BALANCE, amount_minor),
            ),
            description=description or "Sponsor contract payout credited to the club budget.",
            reference_id=reference_id,
            metadata={"source": "sponsorship_catalog"},
        )

    def record_catalog_purchase(
        self,
        club_id: str,
        *,
        amount_minor: int,
        reference_id: str | None = None,
        description: str = "Club operations catalog purchase recorded.",
    ) -> tuple[ClubFinanceLedgerEntryView, ...]:
        return self._record_entries(
            club_id,
            entry_type=ClubFinanceEntryType.CATALOG_PURCHASE_DEBIT,
            postings=(
                (ClubFinanceAccountType.BRANDING_SPEND, -abs(amount_minor)),
                (ClubFinanceAccountType.OPERATING_BALANCE, -abs(amount_minor)),
            ),
            description=description,
            reference_id=reference_id,
            metadata={"source": "catalog_purchase"},
        )

    def record_academy_program_debit(
        self,
        club_id: str,
        *,
        amount_minor: int,
        reference_id: str | None = None,
        description: str | None = None,
    ) -> tuple[ClubFinanceLedgerEntryView, ...]:
        return self._record_entries(
            club_id,
            entry_type=ClubFinanceEntryType.ACADEMY_PROGRAM_DEBIT,
            postings=(
                (ClubFinanceAccountType.ACADEMY_SPEND, -abs(amount_minor)),
                (ClubFinanceAccountType.OPERATING_BALANCE, -abs(amount_minor)),
            ),
            description=description or "Academy development spend allocated from the club budget.",
            reference_id=reference_id,
            metadata={"source": "academy_program"},
        )

    def record_scouting_assignment_debit(
        self,
        club_id: str,
        *,
        amount_minor: int,
        reference_id: str | None = None,
        description: str | None = None,
    ) -> tuple[ClubFinanceLedgerEntryView, ...]:
        return self._record_entries(
            club_id,
            entry_type=ClubFinanceEntryType.SCOUTING_ASSIGNMENT_DEBIT,
            postings=(
                (ClubFinanceAccountType.SCOUTING_SPEND, -abs(amount_minor)),
                (ClubFinanceAccountType.OPERATING_BALANCE, -abs(amount_minor)),
            ),
            description=description or "Youth scouting assignment spend allocated from the club budget.",
            reference_id=reference_id,
            metadata={"source": "scouting_assignment"},
        )

    def record_refund(
        self,
        club_id: str,
        *,
        amount_minor: int,
        reference_id: str | None = None,
        description: str | None = None,
    ) -> tuple[ClubFinanceLedgerEntryView, ...]:
        return self._record_entries(
            club_id,
            entry_type=ClubFinanceEntryType.REFUND,
            postings=((ClubFinanceAccountType.OPERATING_BALANCE, abs(amount_minor)),),
            description=description or "Refund returned to the club operating balance.",
            reference_id=reference_id,
            metadata={"source": "refund"},
        )

    def record_reserve_hold(
        self,
        club_id: str,
        *,
        amount_minor: int,
        reference_id: str | None = None,
    ) -> tuple[ClubFinanceLedgerEntryView, ...]:
        return self._record_entries(
            club_id,
            entry_type=ClubFinanceEntryType.RESERVE_HOLD,
            postings=((ClubFinanceAccountType.OPERATING_BALANCE, -abs(amount_minor)),),
            description="Reserve hold applied to preserve club liquidity for committed operations.",
            reference_id=reference_id,
            metadata={"source": "reserve_hold"},
        )

    def ensure_club_setup(self, club_id: str) -> None:
        with self.store.lock:
            if club_id in self.store.accounts_by_club:
                return
            self.store.club_labels.setdefault(club_id, _titleize_club_label(club_id))
            self.store.accounts_by_club[club_id] = {
                account_type: FinanceAccountRecord(
                    id=f"acc-{uuid4().hex[:12]}",
                    club_id=club_id,
                    account_type=account_type,
                    currency=_DEFAULT_CURRENCY,
                    allow_negative=_account_allows_negative(account_type),
                )
                for account_type in ClubFinanceAccountType
            }
            self.store.ledger_by_club[club_id] = []
            self.store.sponsorship_contracts_by_club.setdefault(club_id, {})
            self.store.sponsorship_assets_by_club.setdefault(club_id, {})
            self.store.academy_programs_by_club.setdefault(club_id, {})
            self.store.academy_players_by_club.setdefault(club_id, {})
            self.store.academy_training_cycles_by_club.setdefault(club_id, {})
            self.store.academy_graduations_by_club.setdefault(club_id, [])
            self.store.scouting_assignments_by_club.setdefault(club_id, {})
            self.store.prospects_by_club.setdefault(club_id, {})
            self.store.youth_pipeline_by_club.setdefault(club_id, None)
            self.store.regen_profiles_by_club.setdefault(club_id, {})
            self.store.academy_intake_batches_by_club.setdefault(club_id, {})
            self.store.academy_candidates_by_club.setdefault(club_id, {})
            self.store.regen_generation_events_by_club.setdefault(club_id, [])

        self.record_manual_adjustment(
            club_id,
            amount_minor=_OPENING_BALANCE_MINOR,
            description="Opening club budget set for transparent club operations.",
            reference_id="opening-budget",
        )

    def _record_entries(
        self,
        club_id: str,
        *,
        entry_type: ClubFinanceEntryType,
        postings: tuple[tuple[ClubFinanceAccountType, int], ...],
        description: str,
        reference_id: str | None,
        metadata: dict[str, object],
    ) -> tuple[ClubFinanceLedgerEntryView, ...]:
        if not postings or all(amount == 0 for _, amount in postings):
            return ()
        self.ensure_club_setup(club_id)
        created_at = _utcnow()
        transaction_id = f"clubtx-{uuid4().hex[:14]}"
        with self.store.lock:
            entries: list[LedgerEntryRecord] = []
            accounts = self._accounts_for_club(club_id)
            for account_type, amount_minor in postings:
                if amount_minor == 0:
                    continue
                account = accounts[account_type]
                if not account.allow_negative and account.balance_minor + amount_minor < 0:
                    raise ValueError("insufficient_operating_balance")
                account.balance_minor += amount_minor
                entry = LedgerEntryRecord(
                    id=f"fin-{uuid4().hex[:12]}",
                    transaction_id=transaction_id,
                    club_id=club_id,
                    account_type=account_type,
                    entry_type=entry_type,
                    amount_minor=amount_minor,
                    currency=account.currency,
                    description=description,
                    reference_id=reference_id,
                    created_at=created_at,
                    metadata=dict(metadata),
                )
                self.store.ledger_by_club[club_id].append(entry)
                entries.append(entry)
        self.get_budget_snapshot(club_id)
        self.get_cashflow_summary(club_id)
        return tuple(self._ledger_view(entry) for entry in entries)

    def _accounts_for_club(self, club_id: str) -> dict[ClubFinanceAccountType, FinanceAccountRecord]:
        return self.store.accounts_by_club.setdefault(club_id, {})

    def _account_view(self, record: FinanceAccountRecord) -> ClubFinanceAccountView:
        return ClubFinanceAccountView(
            id=record.id,
            club_id=record.club_id,
            account_type=record.account_type,
            currency=record.currency,
            balance_minor=record.balance_minor,
            allow_negative=record.allow_negative,
            is_active=record.is_active,
        )

    def _ledger_view(self, record: LedgerEntryRecord) -> ClubFinanceLedgerEntryView:
        return ClubFinanceLedgerEntryView(
            id=record.id,
            transaction_id=record.transaction_id,
            club_id=record.club_id,
            account_type=record.account_type,
            entry_type=record.entry_type,
            amount_minor=record.amount_minor,
            currency=record.currency,
            description=record.description,
            reference_id=record.reference_id,
            created_at=record.created_at,
            metadata=dict(record.metadata),
        )


_STORE = ClubOpsStore()


def get_club_ops_store() -> ClubOpsStore:
    return _STORE


@lru_cache
def get_club_finance_service() -> ClubFinanceService:
    return ClubFinanceService(store=get_club_ops_store())


__all__ = ["ClubFinanceService", "ClubOpsStore", "get_club_finance_service", "get_club_ops_store"]
