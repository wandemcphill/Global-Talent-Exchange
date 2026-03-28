from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.fairness.fairness_guard import FairnessGuard, FairnessViolation, LockedMatchContext
    from app.fairness.match_integrity_service import MatchIntegrityService, MatchIntegrityViolation
    from app.fairness.spend_balance_controller import (
        FairnessModePolicy,
        SpendBalanceController,
        SpendTier,
        TournamentFairnessMode,
    )


def __getattr__(name: str) -> Any:
    if name in {"FairnessGuard", "FairnessViolation", "LockedMatchContext"}:
        from app.fairness.fairness_guard import FairnessGuard, FairnessViolation, LockedMatchContext

        exported = {
            "FairnessGuard": FairnessGuard,
            "FairnessViolation": FairnessViolation,
            "LockedMatchContext": LockedMatchContext,
        }
        return exported[name]
    if name in {"MatchIntegrityService", "MatchIntegrityViolation"}:
        from app.fairness.match_integrity_service import MatchIntegrityService, MatchIntegrityViolation

        exported = {
            "MatchIntegrityService": MatchIntegrityService,
            "MatchIntegrityViolation": MatchIntegrityViolation,
        }
        return exported[name]
    if name in {
        "FairnessModePolicy",
        "SpendBalanceController",
        "SpendTier",
        "TournamentFairnessMode",
    }:
        from app.fairness.spend_balance_controller import (
            FairnessModePolicy,
            SpendBalanceController,
            SpendTier,
            TournamentFairnessMode,
        )

        exported = {
            "FairnessModePolicy": FairnessModePolicy,
            "SpendBalanceController": SpendBalanceController,
            "SpendTier": SpendTier,
            "TournamentFairnessMode": TournamentFairnessMode,
        }
        return exported[name]
    raise AttributeError(name)


__all__ = [
    "FairnessGuard",
    "FairnessModePolicy",
    "FairnessViolation",
    "LockedMatchContext",
    "MatchIntegrityService",
    "MatchIntegrityViolation",
    "SpendBalanceController",
    "SpendTier",
    "TournamentFairnessMode",
]
