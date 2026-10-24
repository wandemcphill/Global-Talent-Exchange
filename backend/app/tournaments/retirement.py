from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.risk_ops import AuditLog
from app.models.tournament import Tournament, TournamentPlayer
from app.models.user import User
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerEntry,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerTransaction,
    LedgerTransactionStatus,
    LedgerTransactionType,
    LedgerUnit,
)
from app.models.base import utcnow
from app.wallets.service import LedgerError, LedgerPosting, WalletService

LEGACY_TOURNAMENT_REFUND_CONFIRMATION = "REFUND_LEGACY_TOURNAMENT_FEES"
_AMOUNT_QUANTUM = Decimal("0.0001")


class LegacyTournamentNotFound(LookupError):
    """A requested retired-engine tournament does not exist."""


def _value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _amount(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value)).quantize(_AMOUNT_QUANTUM)


def _pool_code(tournament_id: str) -> str:
    return f"tournament:{tournament_id}:pool:credit"


def _user_code(user_id: str) -> str:
    return f"user:{user_id}:credit"


def _entry_key(tournament_id: str, user_id: str) -> str:
    return f"tournament:{tournament_id}:entry:{user_id}"


def _refund_key(tournament_id: str, user_id: str) -> str:
    return f"tournament:{tournament_id}:refund:{user_id}"


def _validate_ledger_pair(
    session: Session,
    transaction: LedgerTransaction,
    *,
    reference: str,
    idempotency_key: str,
    expected_accounts: dict[str, Decimal],
) -> tuple[bool, str | None]:
    if _value(transaction.status) != LedgerTransactionStatus.COMMITTED.value:
        return False, "ledger_transaction_not_committed"
    if _value(transaction.reason) != LedgerEntryReason.COMPETITION_ENTRY.value:
        return False, "ledger_transaction_reason_mismatch"
    if _value(transaction.source_tag) != LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND.value:
        return False, "ledger_transaction_source_mismatch"
    if transaction.reference != reference or transaction.idempotency_key != idempotency_key:
        return False, "ledger_reference_or_idempotency_key_mismatch"

    entries = list(
        session.scalars(
            select(LedgerEntry)
            .where(LedgerEntry.transaction_id == transaction.id)
            .order_by(LedgerEntry.created_at.asc(), LedgerEntry.id.asc())
        ).all()
    )
    if len(entries) != 2:
        return False, "ledger_transaction_must_have_two_postings"

    account_ids = {entry.account_id for entry in entries}
    accounts = {
        account.id: account
        for account in session.scalars(select(LedgerAccount).where(LedgerAccount.id.in_(account_ids))).all()
    }
    if set(accounts) != account_ids:
        return False, "ledger_posting_account_missing"

    actual: dict[str, Decimal] = {}
    for entry in entries:
        account = accounts[entry.account_id]
        if _value(entry.unit) != LedgerUnit.CREDIT.value or _value(account.unit) != LedgerUnit.CREDIT.value:
            return False, "ledger_currency_mismatch"
        if _value(entry.reason) != LedgerEntryReason.COMPETITION_ENTRY.value:
            return False, "ledger_entry_reason_mismatch"
        if _value(entry.source_tag) != LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND.value:
            return False, "ledger_entry_source_mismatch"
        if _value(entry.transaction_type) != LedgerTransactionType.MATCH_ENTRY_FEE.value:
            return False, "ledger_entry_type_mismatch"
        if account.code in actual:
            return False, "duplicate_ledger_account_posting"
        actual[account.code] = _amount(entry.amount)

    normalized_expected = {code: _amount(amount) for code, amount in expected_accounts.items()}
    if actual != normalized_expected:
        return False, "ledger_postings_do_not_match_expected_entry"
    return True, None


def _validate_original_entry(
    session: Session,
    tournament: Tournament,
    player: TournamentPlayer,
) -> tuple[bool, str | None]:
    if not player.entry_transaction_id:
        return False, "entry_transaction_reference_missing"
    transaction = session.get(LedgerTransaction, player.entry_transaction_id)
    if transaction is None:
        return False, "entry_transaction_not_found"

    expected_key = _entry_key(tournament.id, player.user_id)
    fee = _amount(tournament.entry_fee)
    return _validate_ledger_pair(
        session,
        transaction,
        reference=expected_key,
        idempotency_key=expected_key,
        expected_accounts={
            _user_code(player.user_id): -fee,
            _pool_code(tournament.id): fee,
        },
    )


def _validate_existing_refund(
    session: Session,
    tournament: Tournament,
    player: TournamentPlayer,
    transaction: LedgerTransaction,
) -> tuple[bool, str | None]:
    expected_key = _refund_key(tournament.id, player.user_id)
    fee = _amount(tournament.entry_fee)
    return _validate_ledger_pair(
        session,
        transaction,
        reference=expected_key,
        idempotency_key=expected_key,
        expected_accounts={
            _pool_code(tournament.id): -fee,
            _user_code(player.user_id): fee,
        },
    )


def _pool_balance(session: Session, tournament_id: str) -> Decimal:
    pool = session.scalar(select(LedgerAccount).where(LedgerAccount.code == _pool_code(tournament_id)))
    if pool is None or _value(pool.unit) != LedgerUnit.CREDIT.value or _value(pool.kind) != LedgerAccountKind.SYSTEM.value:
        return Decimal("0.0000")
    total = session.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.account_id == pool.id,
            LedgerEntry.unit == LedgerUnit.CREDIT,
        )
    )
    return _amount(total or 0)


def build_legacy_tournament_refund_report(
    session: Session,
    *,
    tournament_id: str | None = None,
) -> dict[str, Any]:
    """Read-only reconciliation report. This function never creates ledger accounts or writes entries."""
    if tournament_id is not None and session.get(Tournament, tournament_id) is None:
        raise LegacyTournamentNotFound(tournament_id)

    statement = (
        select(TournamentPlayer, Tournament)
        .join(Tournament, Tournament.id == TournamentPlayer.tournament_id)
        .where(Tournament.entry_fee > 0)
        .order_by(Tournament.created_at.asc(), TournamentPlayer.joined_at.asc(), TournamentPlayer.id.asc())
    )
    if tournament_id is not None:
        statement = statement.where(Tournament.id == tournament_id)

    rows = session.execute(statement).all()
    items: list[dict[str, Any]] = []
    tournament_ids: list[str] = []
    proposed_amounts: dict[str, Decimal] = {}

    for player, tournament in rows:
        if tournament.id not in tournament_ids:
            tournament_ids.append(tournament.id)
        refund_key = _refund_key(tournament.id, player.user_id)
        refund_transaction = session.scalar(
            select(LedgerTransaction).where(LedgerTransaction.idempotency_key == refund_key)
        )
        fee = _amount(tournament.entry_fee)
        item: dict[str, Any] = {
            "entry_id": player.id,
            "tournament_id": tournament.id,
            "tournament_name": tournament.name,
            "tournament_status": _value(tournament.status),
            "user_id": player.user_id,
            "entry_transaction_id": player.entry_transaction_id,
            "refund_idempotency_key": refund_key,
            "amount": format(fee, "f"),
            "currency": LedgerUnit.CREDIT.value,
            "status": "eligible",
            "reason": None,
        }

        if refund_transaction is not None:
            valid, reason = _validate_existing_refund(session, tournament, player, refund_transaction)
            if valid:
                item["status"] = "already_refunded"
                item["reason"] = "validated_refund_ledger_entry_exists"
            else:
                item["status"] = "blocked"
                item["reason"] = f"existing_refund_cannot_be_verified:{reason}"
        else:
            valid, reason = _validate_original_entry(session, tournament, player)
            if valid:
                proposed_amounts[tournament.id] = proposed_amounts.get(tournament.id, Decimal("0.0000")) + fee
            else:
                item["status"] = "unverified"
                item["reason"] = reason
        items.append(item)

    tournament_reports: list[dict[str, Any]] = []
    for tid in tournament_ids:
        tournament_items = [item for item in items if item["tournament_id"] == tid]
        pool_balance = _pool_balance(session, tid)
        proposed = _amount(proposed_amounts.get(tid, Decimal("0.0000")))
        if proposed > pool_balance:
            for item in tournament_items:
                if item["status"] == "eligible":
                    item["status"] = "blocked"
                    item["reason"] = "insufficient_pool_balance_for_refund_batch"
        final_eligible = sum(
            (_amount(item["amount"]) for item in tournament_items if item["status"] == "eligible"),
            Decimal("0.0000"),
        )
        tournament_blockers = [
            item for item in tournament_items if item["status"] in {"blocked", "unverified"}
        ]
        tournament_reports.append(
            {
                "tournament_id": tid,
                "tournament_name": tournament_items[0]["tournament_name"],
                "tournament_status": tournament_items[0]["tournament_status"],
                "entry_count": len(tournament_items),
                "eligible_count": sum(item["status"] == "eligible" for item in tournament_items),
                "already_refunded_count": sum(item["status"] == "already_refunded" for item in tournament_items),
                "unverified_count": sum(item["status"] == "unverified" for item in tournament_items),
                "blocked_count": sum(item["status"] == "blocked" for item in tournament_items),
                "proposed_refund_amount": format(proposed, "f"),
                "eligible_refund_amount": format(_amount(final_eligible), "f"),
                "pool_balance": format(pool_balance, "f"),
                "pool_shortfall": format(max(Decimal("0.0000"), proposed - pool_balance), "f"),
                "execution_blocked": bool(tournament_blockers),
            }
        )

    status_counts = {
        state: sum(item["status"] == state for item in items)
        for state in ("eligible", "already_refunded", "unverified", "blocked")
    }
    blocker_count = status_counts["unverified"] + status_counts["blocked"]
    eligible_total = sum(
        (_amount(item["amount"]) for item in items if item["status"] == "eligible"),
        Decimal("0.0000"),
    )
    proposed_total = sum(proposed_amounts.values(), Decimal("0.0000"))
    if blocker_count:
        report_status = "blocked"
    elif status_counts["eligible"]:
        report_status = "ready"
    elif status_counts["already_refunded"]:
        report_status = "already_refunded"
    else:
        report_status = "nothing_to_refund"

    return {
        "status": report_status,
        "mutation_performed": False,
        "execution_allowed": blocker_count == 0 and bool(items),
        "checked_at": utcnow().isoformat(),
        "tournament_id": tournament_id,
        "summary": {
            "entry_count": len(items),
            **status_counts,
            "proposed_refund_amount": format(_amount(proposed_total), "f"),
            "eligible_refund_amount": format(_amount(eligible_total), "f"),
            "currency": LedgerUnit.CREDIT.value,
        },
        "tournaments": tournament_reports,
        "items": items,
    }


def execute_legacy_tournament_refunds(
    session: Session,
    *,
    actor: User,
    tournament_id: str,
    reason: str,
) -> dict[str, Any]:
    """Refund verified outstanding entries for one tournament, atomically and idempotently."""
    tournament = session.scalar(
        select(Tournament).where(Tournament.id == tournament_id).with_for_update()
    )
    if tournament is None:
        raise LegacyTournamentNotFound(tournament_id)

    # Serialize same-tournament execution in databases that support row locks.
    list(
        session.scalars(
            select(TournamentPlayer.id)
            .where(TournamentPlayer.tournament_id == tournament_id)
            .with_for_update()
        ).all()
    )
    report = build_legacy_tournament_refund_report(session, tournament_id=tournament_id)
    if report["status"] == "blocked":
        return {**report, "mutation_performed": False, "status": "blocked"}
    eligible_items = [item for item in report["items"] if item["status"] == "eligible"]
    if not eligible_items:
        return {
            **report,
            "mutation_performed": False,
            "status": "already_refunded" if report["summary"]["already_refunded"] else "nothing_to_refund",
            "refunded_count": 0,
            "refunded_amount": "0.0000",
        }

    wallet_service = WalletService()
    refunded_amount = Decimal("0.0000")
    results: list[dict[str, Any]] = []

    for item in eligible_items:
        player = session.get(TournamentPlayer, item["entry_id"])
        if player is None:
            raise LedgerError("Legacy tournament entry disappeared during refund processing.")
        valid, validation_reason = _validate_original_entry(session, tournament, player)
        if not valid:
            raise LedgerError(f"Legacy tournament entry failed final verification: {validation_reason}")
        user = session.get(User, player.user_id)
        if user is None:
            raise LedgerError("Cannot refund a legacy entry whose user record is missing.")

        pool_account = session.scalar(
            select(LedgerAccount).where(LedgerAccount.code == _pool_code(tournament_id))
        )
        user_account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == _user_code(player.user_id)))
        if pool_account is None or user_account is None:
            raise LedgerError("Required legacy tournament or user ledger account is missing.")
        if (
            _value(pool_account.unit) != LedgerUnit.CREDIT.value
            or _value(pool_account.kind) != LedgerAccountKind.SYSTEM.value
            or _value(user_account.unit) != LedgerUnit.CREDIT.value
        ):
            raise LedgerError("Legacy refund ledger account currency or type failed verification.")

        amount = _amount(tournament.entry_fee)
        reference = _refund_key(tournament_id, player.user_id)
        entries = wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(
                    account=pool_account,
                    amount=-amount,
                    source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                    transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                ),
                LedgerPosting(
                    account=user_account,
                    amount=amount,
                    source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                    transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                ),
            ],
            reason=LedgerEntryReason.COMPETITION_ENTRY,
            source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
            transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
            reference=reference,
            description=f"Verified legacy tournament entry fee refund: {tournament.name}",
            actor=actor,
            idempotency_key=reference,
            metadata={
                "legacy_tournament_retirement_refund": True,
                "tournament_id": tournament_id,
                "tournament_entry_id": player.id,
                "user_id": player.user_id,
                "original_entry_transaction_id": player.entry_transaction_id,
                "reason": reason,
            },
        )
        refund_transaction_id = entries[0].transaction_id
        session.add(
            AuditLog(
                actor_user_id=actor.id,
                action_key="legacy_tournament.entry_fee_refund",
                resource_type="tournament_entry",
                resource_id=player.id,
                outcome="success",
                detail=reason,
                metadata_json={
                    "tournament_id": tournament_id,
                    "tournament_name": tournament.name,
                    "entry_id": player.id,
                    "user_id": player.user_id,
                    "amount": format(amount, "f"),
                    "currency": LedgerUnit.CREDIT.value,
                    "original_entry_transaction_id": player.entry_transaction_id,
                    "refund_transaction_id": refund_transaction_id,
                    "refund_idempotency_key": reference,
                    "reason": reason,
                    "actor_user_id": actor.id,
                },
            )
        )
        refunded_amount += amount
        results.append(
            {
                "entry_id": player.id,
                "user_id": player.user_id,
                "amount": format(amount, "f"),
                "currency": LedgerUnit.CREDIT.value,
                "original_entry_transaction_id": player.entry_transaction_id,
                "refund_transaction_id": refund_transaction_id,
                "refund_idempotency_key": reference,
            }
        )

    session.flush()
    return {
        "status": "refunded",
        "mutation_performed": bool(results),
        "tournament_id": tournament_id,
        "tournament_name": tournament.name,
        "refunded_count": len(results),
        "already_refunded_count": report["summary"]["already_refunded"],
        "refunded_amount": format(_amount(refunded_amount), "f"),
        "currency": LedgerUnit.CREDIT.value,
        "reason": reason,
        "results": results,
    }
