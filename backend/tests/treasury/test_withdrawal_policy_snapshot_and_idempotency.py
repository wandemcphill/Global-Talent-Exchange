"""Withdrawal requests snapshot their fee policy and resist replay.

PHASE_A_WITHDRAWAL_CONTRACT requires every withdrawal to record the policy
id/version and rate it was priced under (so a later Admin change cannot rewrite
history), and requires submission to be idempotent.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.economy.economic_policy import resolve_economic_policy
from app.models import Base, LedgerEntryReason, LedgerUnit, PayoutRequest
from app.wallets.service import LedgerPosting, WalletService
from backend.tests.support.economic_policy import seed_economic_policy


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    seed_economic_policy(session)
    session.commit()
    return session


def _funded_user(session, wallet, *, coin: Decimal):
    user = AuthService().register_user(
        session,
        email="withdrawer@example.com",
        username="withdrawer",
        password="SuperSecret1",  # pragma: allowlist secret
    )
    session.commit()
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=wallet.get_user_account(session, user, LedgerUnit.COIN), amount=coin),
            LedgerPosting(account=wallet.ensure_platform_account(session, LedgerUnit.COIN), amount=-coin),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-withdrawal-coin",
        actor=user,
    )
    session.commit()
    return user


def test_repeated_withdrawal_submission_creates_one_hold_and_one_payout() -> None:
    session = _make_session()
    try:
        wallet = WalletService()
        user = _funded_user(session, wallet, coin=Decimal("500.0000"))
        account = wallet.get_user_account(session, user, LedgerUnit.COIN)
        before = wallet.get_balance(session, account)

        first = wallet.request_payout(
            session,
            user=user,
            amount=Decimal("100.0000"),
            destination_reference="bank:acct-1",
            unit=LedgerUnit.COIN,
            withdrawal_fee_bps=1000,
            minimum_fee=Decimal("5.0000"),
            idempotency_key="withdrawal-intent-abc",
        )
        session.commit()
        after_first = wallet.get_balance(session, account)

        second = wallet.request_payout(
            session,
            user=user,
            amount=Decimal("100.0000"),
            destination_reference="bank:acct-1",
            unit=LedgerUnit.COIN,
            withdrawal_fee_bps=1000,
            minimum_fee=Decimal("5.0000"),
            idempotency_key="withdrawal-intent-abc",
        )
        session.commit()

        assert second.payout_request.id == first.payout_request.id
        # No second hold: the balance did not move again.
        assert wallet.get_balance(session, account) == after_first
        assert after_first < before
        assert session.scalar(select(func.count(PayoutRequest.id))) == 1
    finally:
        session.close()


def test_distinct_intents_still_create_distinct_withdrawals() -> None:
    session = _make_session()
    try:
        wallet = WalletService()
        user = _funded_user(session, wallet, coin=Decimal("500.0000"))

        first = wallet.request_payout(
            session,
            user=user,
            amount=Decimal("100.0000"),
            destination_reference="bank:acct-1",
            unit=LedgerUnit.COIN,
            withdrawal_fee_bps=1000,
            minimum_fee=Decimal("5.0000"),
            idempotency_key="withdrawal-intent-one",
        )
        second = wallet.request_payout(
            session,
            user=user,
            amount=Decimal("100.0000"),
            destination_reference="bank:acct-1",
            unit=LedgerUnit.COIN,
            withdrawal_fee_bps=1000,
            minimum_fee=Decimal("5.0000"),
            idempotency_key="withdrawal-intent-two",
        )
        session.commit()

        assert first.payout_request.id != second.payout_request.id
        assert session.scalar(select(func.count(PayoutRequest.id))) == 2
    finally:
        session.close()


def test_withdrawal_without_intent_key_is_unaffected() -> None:
    session = _make_session()
    try:
        wallet = WalletService()
        user = _funded_user(session, wallet, coin=Decimal("500.0000"))

        first = wallet.request_payout(
            session,
            user=user,
            amount=Decimal("50.0000"),
            destination_reference="bank:acct-1",
            unit=LedgerUnit.COIN,
            withdrawal_fee_bps=1000,
            minimum_fee=Decimal("5.0000"),
        )
        second = wallet.request_payout(
            session,
            user=user,
            amount=Decimal("50.0000"),
            destination_reference="bank:acct-1",
            unit=LedgerUnit.COIN,
            withdrawal_fee_bps=1000,
            minimum_fee=Decimal("5.0000"),
        )
        session.commit()

        # Null keys must not collide under the unique index.
        assert first.payout_request.id != second.payout_request.id
        assert first.payout_request.idempotency_key is None
        assert session.scalar(select(func.count(PayoutRequest.id))) == 2
    finally:
        session.close()


def test_policy_snapshot_is_recorded_and_survives_a_later_rate_change() -> None:
    session = _make_session()
    try:
        wallet = WalletService()
        user = _funded_user(session, wallet, coin=Decimal("500.0000"))
        policy_at_request = resolve_economic_policy(session)
        # Capture as plain values: policy_at_request.rule is a live ORM row that
        # the later rate change below will mutate in place.
        original_version = policy_at_request.policy_version
        original_rule_key = policy_at_request.rule.rule_key
        original_bps = int(policy_at_request.withdrawal_fee_bps)

        result = wallet.request_payout(
            session,
            user=user,
            amount=Decimal("100.0000"),
            destination_reference="bank:acct-1",
            unit=LedgerUnit.COIN,
            withdrawal_fee_bps=policy_at_request.withdrawal_fee_bps,
            minimum_fee=policy_at_request.minimum_withdrawal_fee_credits,
            idempotency_key="withdrawal-snapshot",
            extra_meta={
                "fee_policy_rule_key": policy_at_request.rule.rule_key,
                "fee_policy_version": policy_at_request.policy_version,
                "fee_policy_withdrawal_fee_bps": int(policy_at_request.withdrawal_fee_bps),
            },
        )
        session.commit()
        recorded = json.loads(result.payout_request.notes)
        assert recorded["fee_policy_rule_key"] == original_rule_key
        assert recorded["fee_policy_version"] == original_version
        assert recorded["fee_policy_withdrawal_fee_bps"] == original_bps

        # Admin changes the rate afterwards.
        seed_economic_policy(session, withdrawal_fee_bps=2500)
        session.commit()
        assert resolve_economic_policy(session).policy_version != original_version
        assert resolve_economic_policy(session).withdrawal_fee_bps == 2500

        session.refresh(result.payout_request)
        still = json.loads(result.payout_request.notes)
        # The historical record still shows the policy that actually priced it.
        assert still["fee_policy_version"] == original_version
        assert still["fee_policy_withdrawal_fee_bps"] == original_bps == 1000
    finally:
        session.close()
