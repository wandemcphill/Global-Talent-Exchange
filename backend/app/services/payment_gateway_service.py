from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.admin_godmode.runtime_paths import admin_godmode_state_path
from app.admin_godmode.service import DEFAULT_PAYMENT_RAILS
from app.core.config import Settings
from app.models.treasury import PaymentMode
from app.models.wallet import LedgerUnit
from app.treasury.service import TreasuryService
from app.wallets.providers.registry import paystack_enabled, provider_live_deposit_ready, provider_secret_configured
from app.wallets.rail_service import PurchaseOrderQuote, WalletRailService


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
        treasury_settings = TreasuryService().ensure_settings(self.session)
        automatic_deposits_enabled = treasury_settings.deposit_mode in {PaymentMode.AUTOMATIC, PaymentMode.HYBRID}
        manual_deposits_enabled = treasury_settings.deposit_mode in {PaymentMode.MANUAL, PaymentMode.HYBRID}
        methods: list[PaymentMethod] = []

        for rail in rails:
            provider_key = str(rail.get("provider") or "")
            if not provider_key:
                continue
            if provider_key == "bank_transfer_manual":
                deposits_enabled = manual_deposits_enabled and bool(rail.get("deposits_enabled"))
                is_live = manual_deposits_enabled and bool(rail.get("is_live"))
                method_group = "manual_bank_transfer"
            else:
                provider_ready = provider_live_deposit_ready(provider_key)
                deposits_enabled = automatic_deposits_enabled and bool(rail.get("deposits_enabled")) and provider_ready
                is_live = automatic_deposits_enabled and bool(rail.get("is_live")) and provider_ready
                method_group = "regional_processor"
                if not provider_ready:
                    rail = {
                        **rail,
                        "maintenance_message": rail.get("maintenance_message")
                        or (
                            f"{self._display_name(provider_key)} requires live provider credentials before checkout "
                            "is available."
                        ),
                    }
            methods.append(
                PaymentMethod(
                    method_key=provider_key,
                    display_name=self._display_name(provider_key),
                    provider_key=provider_key,
                    method_group=method_group,
                    unit=LedgerUnit.COIN,
                    deposits_enabled=deposits_enabled,
                    withdrawals_enabled=bool(rail.get("withdrawals_enabled")),
                    is_live=is_live,
                    maintenance_message=rail.get("maintenance_message"),
                )
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
        if provider_key == "bank_transfer_manual":
            raise PaymentGatewayError(
                "Manual bank transfer uses the treasury deposit request flow, not automatic purchase orders."
            )
        if provider_key == "paystack" and not paystack_enabled():
            raise PaymentGatewayError("Paystack is unavailable. Use KoraPay checkout or manual bank transfer.")
        if provider_key == "korapay" and not provider_secret_configured("korapay"):
            raise PaymentGatewayError(
                "KoraPay is not configured. Set the live KoraPay secret before accepting payments."
            )
        if provider_key == "korapay" and not provider_live_deposit_ready("korapay"):
            raise PaymentGatewayError(
                "KoraPay webhook verification is not configured. Set the live KoraPay webhook or encryption key before accepting payments."
            )
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
        if provider_key == "bank_transfer_manual":
            raise PaymentGatewayError(
                "Manual bank transfer uses the treasury deposit request flow, not automatic purchase orders."
            )
        if provider_key in {"korapay", "paystack"}:
            if provider_key == "paystack" and not paystack_enabled():
                raise PaymentGatewayError("Paystack is unavailable. Use KoraPay checkout or manual bank transfer.")
            raise PaymentGatewayError(
                "Automatic checkout orders must be initiated through the wallet top-up flow so a live checkout session "
                "is created before settlement."
            )
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
        default_rails = self._default_payment_rails()
        if not path.exists():
            return default_rails
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default_rails
        rails = payload.get("payment_rails")
        if isinstance(rails, list):
            defaults_by_provider = {rail["provider"]: dict(rail) for rail in default_rails}
            for rail in rails:
                if not isinstance(rail, dict):
                    continue
                provider = str(rail.get("provider") or "").strip().lower()
                if provider not in defaults_by_provider:
                    continue
                merged = dict(defaults_by_provider[provider])
                merged.update(
                    {
                        "provider": provider,
                        "deposits_enabled": bool(rail.get("deposits_enabled", merged["deposits_enabled"])),
                        "withdrawals_enabled": bool(rail.get("withdrawals_enabled", merged["withdrawals_enabled"])),
                        "is_live": bool(rail.get("is_live", merged["is_live"])),
                        "maintenance_message": rail.get("maintenance_message", merged["maintenance_message"]),
                    }
                )
                if provider == "korapay" and not provider_live_deposit_ready("korapay"):
                    merged["deposits_enabled"] = False
                    merged["withdrawals_enabled"] = False
                    merged["is_live"] = False
                    merged["maintenance_message"] = (
                        merged.get("maintenance_message")
                        or "KoraPay requires live checkout and webhook credentials before it can accept deposits."
                    )
                if provider == "paystack" and not paystack_enabled():
                    merged["deposits_enabled"] = False
                    merged["withdrawals_enabled"] = False
                    merged["is_live"] = False
                    merged["maintenance_message"] = (
                        merged.get("maintenance_message")
                        or "Paystack is unavailable for production. Use KoraPay or manual bank transfer."
                    )
                defaults_by_provider[provider] = merged
            return [defaults_by_provider[rail["provider"]] for rail in default_rails]
        return default_rails

    def _state_path(self) -> Path:
        return admin_godmode_state_path(self.settings.config_root)

    @staticmethod
    def _default_payment_rails() -> list[dict[str, Any]]:
        rails = [dict(rail) for rail in DEFAULT_PAYMENT_RAILS]
        for rail in rails:
            provider = str(rail.get("provider") or "").strip().lower()
            if provider == "korapay" and provider_live_deposit_ready("korapay"):
                rail["deposits_enabled"] = True
                rail["is_live"] = True
                rail["maintenance_message"] = None
            elif provider == "paystack" and not paystack_enabled():
                rail["deposits_enabled"] = False
                rail["withdrawals_enabled"] = False
                rail["is_live"] = False
                rail["maintenance_message"] = (
                    rail.get("maintenance_message")
                    or "Paystack is unavailable for production. Use KoraPay or manual bank transfer."
                )
        return rails

    def _resolve_provider(self, method_key: str | None) -> str:
        if method_key == "crypto_deposit":
            if not self.settings.crypto_deposit_enabled:
                raise PaymentGatewayError("Crypto deposit rail is disabled.")
            return self.settings.crypto_provider_key
        if method_key:
            return method_key
        rails = self._load_payment_rails()
        for rail in rails:
            if str(rail.get("provider")) == "bank_transfer_manual":
                continue
            if rail.get("deposits_enabled") and rail.get("is_live"):
                return str(rail.get("provider"))
        raise PaymentGatewayError("No active payment provider is configured.")

    def _assert_provider_enabled(self, provider_key: str) -> None:
        if provider_key == self.settings.crypto_provider_key:
            if not self.settings.crypto_deposit_enabled:
                raise PaymentGatewayError("Crypto deposit rail is disabled.")
            return
        if provider_key == "bank_transfer_manual":
            raise PaymentGatewayError("Manual bank transfer must be handled through the treasury deposit flow.")
        rails = self._load_payment_rails()
        for rail in rails:
            if str(rail.get("provider")) == provider_key:
                if not rail.get("is_live") or not rail.get("deposits_enabled"):
                    raise PaymentGatewayError("Selected payment provider is not live for deposits.")
                return
        raise PaymentGatewayError("Unknown payment provider.")

    @staticmethod
    def _display_name(provider_key: str) -> str:
        if provider_key == "bank_transfer_manual":
            return "Bank Transfer"
        label = provider_key.replace("_", " ").title()
        return label


__all__ = ["PaymentGatewayError", "PaymentGatewayService", "PaymentMethod"]
