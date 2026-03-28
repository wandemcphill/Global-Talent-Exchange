from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from threading import RLock
from typing import Any

from fastapi import FastAPI


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class ManualPriceOverride:
    asset_type: str
    asset_id: str
    override_price: Decimal
    currency: str
    reason: str | None
    updated_by_user_id: str | None
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass(slots=True)
class AccountControlState:
    user_id: str
    freeze_login: bool = False
    freeze_wallet: bool = False
    freeze_matches: bool = False
    freeze_social: bool = False
    reason: str | None = None
    updated_by_user_id: str | None = None
    updated_at: datetime = field(default_factory=_utcnow)

    @property
    def any_freeze_enabled(self) -> bool:
        return any(
            (
                self.freeze_login,
                self.freeze_wallet,
                self.freeze_matches,
                self.freeze_social,
            )
        )


@dataclass(slots=True)
class MatchKillSwitchState:
    match_id: str
    enabled: bool = True
    reason: str | None = None
    updated_by_user_id: str | None = None
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass(slots=True)
class RuntimeControlRegistry:
    lock: RLock = field(default_factory=RLock)
    price_overrides: dict[str, ManualPriceOverride] = field(default_factory=dict)
    account_controls: dict[str, AccountControlState] = field(default_factory=dict)
    match_kill_switches: dict[str, MatchKillSwitchState] = field(default_factory=dict)

    @staticmethod
    def price_override_key(asset_type: str, asset_id: str) -> str:
        return f"{asset_type.strip().lower()}:{asset_id.strip()}"


class RuntimeControlService:
    def __init__(self, app: FastAPI) -> None:
        self.app = app

    @property
    def registry(self) -> RuntimeControlRegistry:
        registry = getattr(self.app.state, "runtime_control_registry", None)
        if registry is None:
            registry = RuntimeControlRegistry()
            self.app.state.runtime_control_registry = registry
        return registry

    def list_price_overrides(self) -> list[ManualPriceOverride]:
        with self.registry.lock:
            return sorted(
                self.registry.price_overrides.values(),
                key=lambda item: (item.asset_type, item.asset_id),
            )

    def upsert_price_override(
        self,
        *,
        asset_type: str,
        asset_id: str,
        override_price: Decimal,
        currency: str,
        reason: str | None,
        updated_by_user_id: str | None,
    ) -> ManualPriceOverride:
        item = ManualPriceOverride(
            asset_type=asset_type.strip().lower(),
            asset_id=asset_id.strip(),
            override_price=Decimal(str(override_price)).quantize(Decimal("0.0001")),
            currency=currency.strip().lower(),
            reason=(reason or "").strip() or None,
            updated_by_user_id=updated_by_user_id,
        )
        with self.registry.lock:
            self.registry.price_overrides[self.registry.price_override_key(item.asset_type, item.asset_id)] = item
        return item

    def remove_price_override(self, *, asset_type: str, asset_id: str) -> ManualPriceOverride | None:
        with self.registry.lock:
            return self.registry.price_overrides.pop(
                self.registry.price_override_key(asset_type, asset_id),
                None,
            )

    def get_price_override(self, *, asset_type: str, asset_id: str) -> ManualPriceOverride | None:
        with self.registry.lock:
            return self.registry.price_overrides.get(
                self.registry.price_override_key(asset_type, asset_id)
            )

    def list_account_controls(self) -> list[AccountControlState]:
        with self.registry.lock:
            return sorted(
                self.registry.account_controls.values(),
                key=lambda item: item.user_id,
            )

    def upsert_account_control(
        self,
        *,
        user_id: str,
        freeze_login: bool,
        freeze_wallet: bool,
        freeze_matches: bool,
        freeze_social: bool,
        reason: str | None,
        updated_by_user_id: str | None,
    ) -> AccountControlState:
        item = AccountControlState(
            user_id=user_id.strip(),
            freeze_login=bool(freeze_login),
            freeze_wallet=bool(freeze_wallet),
            freeze_matches=bool(freeze_matches),
            freeze_social=bool(freeze_social),
            reason=(reason or "").strip() or None,
            updated_by_user_id=updated_by_user_id,
        )
        with self.registry.lock:
            self.registry.account_controls[item.user_id] = item
        return item

    def get_account_control(self, *, user_id: str) -> AccountControlState | None:
        with self.registry.lock:
            return self.registry.account_controls.get(user_id)

    def clear_account_control(self, *, user_id: str) -> AccountControlState | None:
        with self.registry.lock:
            return self.registry.account_controls.pop(user_id, None)

    def set_match_kill_switch(
        self,
        *,
        match_id: str,
        enabled: bool,
        reason: str | None,
        updated_by_user_id: str | None,
    ) -> MatchKillSwitchState:
        item = MatchKillSwitchState(
            match_id=match_id.strip(),
            enabled=bool(enabled),
            reason=(reason or "").strip() or None,
            updated_by_user_id=updated_by_user_id,
        )
        with self.registry.lock:
            if item.enabled:
                self.registry.match_kill_switches[item.match_id] = item
            else:
                self.registry.match_kill_switches.pop(item.match_id, None)
        return item

    def get_match_kill_switch(self, *, match_id: str) -> MatchKillSwitchState | None:
        with self.registry.lock:
            return self.registry.match_kill_switches.get(match_id)

    def list_match_kill_switches(self) -> list[MatchKillSwitchState]:
        with self.registry.lock:
            return sorted(
                self.registry.match_kill_switches.values(),
                key=lambda item: item.match_id,
            )

    def summary(self) -> dict[str, int]:
        with self.registry.lock:
            frozen_accounts = sum(
                1 for item in self.registry.account_controls.values() if item.any_freeze_enabled
            )
            return {
                "manual_price_override_count": len(self.registry.price_overrides),
                "frozen_account_count": frozen_accounts,
                "match_kill_switch_count": len(self.registry.match_kill_switches),
            }

    def build_audit_metadata(self) -> dict[str, Any]:
        summary = self.summary()
        return {
            "manual_price_override_count": summary["manual_price_override_count"],
            "frozen_account_count": summary["frozen_account_count"],
            "match_kill_switch_count": summary["match_kill_switch_count"],
        }


__all__ = [
    "AccountControlState",
    "ManualPriceOverride",
    "MatchKillSwitchState",
    "RuntimeControlRegistry",
    "RuntimeControlService",
]
