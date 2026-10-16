"""Behavioral proof for EA-P0-2: WalletRailService must consult the SAME
persisted Admin GodMode commission state that AdminGodModeService.update_commissions
writes to, instead of a hardcoded DEFAULT_COMMISSION_SETTINGS constant.

These tests exercise the real AdminGodModeService.update_commissions and
WalletRailService.quote_purchase_order against the full app's database (via
the shared `app`/`app_session_factory` fixtures in tests/conftest.py), reading
back through a BRAND-NEW session each time to prove this is genuine cross-request
DB persistence and not an in-process cache. They also prove withdrawal fees stay
on the canonical Admin economic policy (AdminRewardRule), untouched by this fix.
"""

from __future__ import annotations

from decimal import Decimal
import os

import pytest
from sqlalchemy import select

from app.admin_godmode.schemas import CommissionSettingsUpdate
from app.admin_godmode.service import (
    ADMIN_GODMODE_STATE_KEY,
    AdminGodModeService,
    CommissionSettingsUnavailableError,
    resolve_commission_settings,
)
from app.models.admin_runtime_state import AdminRuntimeState
from app.models.treasury import RateDirection
from app.models.user import User
from app.models.wallet import LedgerUnit
from app.treasury.commission_policy import resolve_commission_policy
from app.treasury.service import TreasuryService
from app.wallets.rail_service import WalletRailError, WalletRailService
from app.wallets.service import WalletService
from backend.tests.support.economic_policy import seed_economic_policy


def _configure_deposit_settings(session) -> None:
    treasury = TreasuryService()
    settings = treasury.ensure_settings(session)
    settings.deposit_rate_value = Decimal("1.0000")
    settings.deposit_rate_direction = RateDirection.FIAT_PER_COIN
    settings.min_deposit = Decimal("0.0000")
    settings.max_deposit = Decimal("100000.0000")
    session.commit()


def _bootstrap_admin(session) -> User:
    admin = session.scalar(select(User).where(User.email == os.environ["GTE_BOOTSTRAP_ADMIN_EMAIL"]))
    assert admin is not None
    return admin


def _set_commissions(app, session, admin, *, buy_bps: int, reason: str) -> None:
    AdminGodModeService(wallet_service=WalletService()).update_commissions(
        app,
        admin,
        CommissionSettingsUpdate(
            buy_commission_bps=buy_bps,
            sell_commission_bps=150,
            instant_sell_fee_bps=75,
            withdrawal_fee_bps=1000,
            minimum_withdrawal_fee_credits=Decimal("5.0000"),
            reason=reason,
        ),
    )
    session.commit()


def _quote_buy_fee(session) -> Decimal:
    treasury = TreasuryService()
    settings = treasury.ensure_settings(session)
    rail_service = WalletRailService(session)
    quote = rail_service.quote_purchase_order(
        settings=settings,
        amount=Decimal("100.0000"),
        input_unit="fiat",
        provider_key="cards",
        source_scope="wallet",
        unit=LedgerUnit.CREDIT,
        processor_mode="automatic_gateway",
        payout_channel="gateway",
    )
    return quote.fee_amount


def test_admin_buy_commission_is_reflected_in_purchase_quote(app, app_session_factory, bootstrap_admin_headers) -> None:
    del bootstrap_admin_headers
    with app_session_factory() as session:
        admin = _bootstrap_admin(session)
        _configure_deposit_settings(session)
        _set_commissions(app, session, admin, buy_bps=500, reason="P0-2 regression: 5% buy commission")

    # Brand-new session/service instance: proves this reads persisted DB state.
    with app_session_factory() as session:
        assert _quote_buy_fee(session) == Decimal("5.0000")


def test_admin_buy_commission_change_takes_effect_on_next_quote(
    app, app_session_factory, bootstrap_admin_headers
) -> None:
    del bootstrap_admin_headers
    with app_session_factory() as session:
        admin = _bootstrap_admin(session)
        _configure_deposit_settings(session)
        _set_commissions(app, session, admin, buy_bps=500, reason="P0-2 regression: initial 5%")
    with app_session_factory() as session:
        assert _quote_buy_fee(session) == Decimal("5.0000")

    with app_session_factory() as session:
        admin = _bootstrap_admin(session)
        _set_commissions(app, session, admin, buy_bps=250, reason="P0-2 regression: lowered to 2.5%")
    with app_session_factory() as session:
        assert _quote_buy_fee(session) == Decimal("2.5000")


def test_withdrawal_fee_still_uses_canonical_economic_policy_not_godmode_commissions(
    app, app_session_factory, bootstrap_admin_headers
) -> None:
    del bootstrap_admin_headers
    with app_session_factory() as session:
        admin = _bootstrap_admin(session)
        seed_economic_policy(session, withdrawal_fee_bps=1000)  # canonical policy = 10%
        session.commit()
        # AdminGodModeService.update_commissions manages its own session
        # internally (via app.state.session_factory), so the outer session's
        # write above must be committed first or the two collide on SQLite.
        # GodMode's own withdrawal_fee_bps is set to something wildly different -
        # it must have zero effect on the real withdrawal fee.
        AdminGodModeService(wallet_service=WalletService()).update_commissions(
            app,
            admin,
            CommissionSettingsUpdate(
                buy_commission_bps=500,
                sell_commission_bps=500,
                instant_sell_fee_bps=500,
                withdrawal_fee_bps=4999,
                minimum_withdrawal_fee_credits=Decimal("5.0000"),
                reason="P0-2 regression: withdrawal isolation",
            ),
        )
        session.commit()

    with app_session_factory() as session:
        policy = resolve_commission_policy(session)
    assert policy.withdrawal_fee_bps == 1000


def test_corrupt_commission_state_fails_closed_instead_of_reverting_to_stale_default(
    app, app_session_factory, bootstrap_admin_headers
) -> None:
    del bootstrap_admin_headers
    with app_session_factory() as session:
        admin = _bootstrap_admin(session)
        _configure_deposit_settings(session)
        _set_commissions(app, session, admin, buy_bps=500, reason="P0-2 regression: pre-corruption baseline")

    with app_session_factory() as session:
        row = session.scalar(select(AdminRuntimeState).where(AdminRuntimeState.state_key == ADMIN_GODMODE_STATE_KEY))
        assert row is not None
        corrupted = dict(row.payload_json)
        corrupted.pop("commissions", None)
        row.payload_json = corrupted
        session.commit()

    with app_session_factory() as session:
        with pytest.raises(CommissionSettingsUnavailableError):
            resolve_commission_settings(session)

    with app_session_factory() as session:
        with pytest.raises(WalletRailError):
            _quote_buy_fee(session)
