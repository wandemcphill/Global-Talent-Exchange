from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.app.admin_godmode.service import ADMIN_GODMODE_FILE, DEFAULT_PAYMENT_RAILS
from backend.app.core.config import Settings
from backend.app.models.wallet import LedgerUnit
from backend.app.treasury.service import TreasuryService
from backend.app.wallets.rail_service import PurchaseOrderQuote, WalletRailService


@dataclass(frozen=True, slots=True)
class PaymentMethod:
    method_key: str
    display_name: str
    provider_key: str
    method_group: str
    unit: LedgerUnit
    deposits_enabled: bool
    withdrawals_enabled: bool
    is_live: bool
    maintenance_message: str | None


class PaymentGatewayError(ValueError):
    pass


@dataclass(slots=True)
class PaymentGatewayService:
    session: Session
    settings: Settings

    def list_methods(self) -> list[PaymentMethod]:
        rails = self._load_payment_rails()
        live_deposit = any(bool(rail.get("is_live")) and bool(rail.get("deposits_enabled")) for rail in rails)
        methods: list[PaymentMethod] = []

        for rail in rails:
            provider_key = str(rail.get("provider") or "")
            if not provider_key:
                continue
            methods.append(
                PaymentMethod(
                    method_key=provider_key,
                    display_name=self._display_name(provider_key),
                    provider_key=provider_key,
                    method_group="regional_processor",
                    unit=LedgerUnit.COIN,
                    deposits_enabled=bool(rail.get("deposits_enabled")),
                    withdrawals_enabled=bool(rail.get("withdrawals_enabled")),
                    is_live=bool(rail.get("is_live")),
                    maintenance_message=rail.get("maintenance_message"),
                )
            )

        methods.extend(
            [
                PaymentMethod(
                    method_key="cards",
                    display_name="Cards",
                    provider_key="cards",
                    method_group="card_wallet",
                    unit=LedgerUnit.COIN,
                    deposits_enabled=live_deposit,
                    withdrawals_enabled=False,
                    is_live=live_deposit,
                    maintenance_message=None,
                ),
                PaymentMethod(
                    method_key="apple_pay",
                    display_name="Apple Pay",
                    provider_key="apple_pay",
                    method_group="card_wallet",
                    unit=LedgerUnit.COIN,
                    deposits_enabled=live_deposit,
                    withdrawals_enabled=False,
                    is_live=live_deposit,
                    maintenance_message=None,
                ),
                PaymentMethod(
                    method_key="google_pay",
                    display_name="Google Pay",
                    provider_key="google_pay",
                    method_group="card_wallet",
                    unit=LedgerUnit.COIN,
                    deposits_enabled=live_deposit,
                    withdrawals_enabled=False,
                    is_live=live_deposit,
                    maintenance_message=None,
                ),
            ]
        )

        if self.settings.crypto_deposit_enabled:
            methods.append(
                PaymentMethod(
                    method_key="crypto_deposit",
                    display_name="Crypto Deposit",
                    provider_key=self.settings.crypto_provider_key,
                    method_group="crypto",
                    unit=LedgerUnit.CREDIT,
                    deposits_enabled=True,
                    withdrawals_enabled=False,
                    is_live=True,
                    maintenance_message=None,
                )
            )
        return methods

    def quote_deposit(
        self,
        *,
        amount: Any,
        input_unit: str,
        provider_key: str | None = None,
        method_key: str | None = None,
        unit: LedgerUnit | None = None,
        processor_mode: str = "automatic_gateway",
        payout_channel: str = "gateway",
        source_scope: str = "wallet",
    ) -> PurchaseOrderQuote:
        provider_key = provider_key or self._resolve_provider(method_key)
        if unit is None:
            unit = LedgerUnit.CREDIT if method_key == "crypto_deposit" else LedgerUnit.COIN
        self._assert_provider_enabled(provider_key)
        settings = TreasuryService().ensure_settings(self.session)
        rail_service = WalletRailService(self.session)
        return rail_service.quote_purchase_order(
            settings=settings,
            amount=amount,
            input_unit=input_unit,
            provider_key=provider_key,
            source_scope=source_scope,
            unit=unit,
            processor_mode=processor_mode,
            payout_channel=payout_channel,
        )

    def create_purchase_order(
        self,
        *,
        user,
        amount: Any,
        input_unit: str,
        provider_key: str | None = None,
        method_key: str | None = None,
        unit: LedgerUnit | None = None,
        processor_mode: str = "automatic_gateway",
        payout_channel: str = "gateway",
        source_scope: str = "wallet",
        provider_reference: str | None = None,
        notes: str | None = None,
    ):
        provider_key = provider_key or self._resolve_provider(method_key)
        if unit is None:
            unit = LedgerUnit.CREDIT if method_key == "crypto_deposit" else LedgerUnit.COIN
        self._assert_provider_enabled(provider_key)
        settings = TreasuryService().ensure_settings(self.session)
        rail_service = WalletRailService(self.session)
        return rail_service.create_purchase_order(
            user=user,
            settings=settings,
            amount=amount,
            input_unit=input_unit,
            provider_key=provider_key,
            source_scope=source_scope,
            unit=unit,
            processor_mode=processor_mode,
            payout_channel=payout_channel,
            provider_reference=provider_reference,
            notes=notes,
        )

    def _load_payment_rails(self) -> list[dict[str, Any]]:
        path = self._state_path()
        if not path.exists():
            return list(DEFAULT_PAYMENT_RAILS)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return list(DEFAULT_PAYMENT_RAILS)
        rails = payload.get("payment_rails")
        if isinstance(rails, list):
            return rails
        return list(DEFAULT_PAYMENT_RAILS)

    def _state_path(self) -> Path:
        return self.settings.config_root / ADMIN_GODMODE_FILE

    def _resolve_provider(self, method_key: str | None) -> str:
        if method_key == "crypto_deposit":
            if not self.settings.crypto_deposit_enabled:
                raise PaymentGatewayError("Crypto deposit rail is disabled.")
            return self.settings.crypto_provider_key
        if method_key in {"cards", "apple_pay", "google_pay"}:
            return method_key
        if method_key:
            return method_key
        rails = self._load_payment_rails()
        for rail in rails:
            if rail.get("deposits_enabled") and rail.get("is_live"):
                return str(rail.get("provider"))
        raise PaymentGatewayError("No active payment provider is configured.")

    def _assert_provider_enabled(self, provider_key: str) -> None:
        if provider_key in {"cards", "apple_pay", "google_pay"}:
            return
        if provider_key == self.settings.crypto_provider_key:
            if not self.settings.crypto_deposit_enabled:
                raise PaymentGatewayError("Crypto deposit rail is disabled.")
            return
        rails = self._load_payment_rails()
        for rail in rails:
            if str(rail.get("provider")) == provider_key:
                if not rail.get("is_live") or not rail.get("deposits_enabled"):
                    raise PaymentGatewayError("Selected payment provider is not live for deposits.")
                return
        raise PaymentGatewayError("Unknown payment provider.")

    @staticmethod
    def _display_name(provider_key: str) -> str:
        label = provider_key.replace("_", " ").title()
        return label


__all__ = ["PaymentGatewayError", "PaymentGatewayService", "PaymentMethod"]
