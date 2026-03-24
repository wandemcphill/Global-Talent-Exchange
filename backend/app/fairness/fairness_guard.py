from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from app.match_engine.schemas import MatchSimulationRequest

_MONETIZATION_TERMS = (
    "gift",
    "gifting",
    "premium",
    "unlock",
    "paid",
    "purchase",
    "coin",
    "credit",
    "sponsor",
    "sponsorship",
    "boost",
    "camera",
    "3d",
    "three_d",
    "three-d",
)
_OUTCOME_TERMS = (
    "result",
    "winner",
    "score",
    "scoreline",
    "timeline",
    "playback",
    "event",
    "events",
    "replay",
    "summary",
    "outcome",
)


class FairnessViolation(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(frozen=True, slots=True)
class LockedMatchContext:
    request: MatchSimulationRequest
    locked_payload: dict[str, Any]
    match_hash: str
    match_seed: int


@dataclass(slots=True)
class FairnessGuard:
    def validate_public_request(self, request: MatchSimulationRequest) -> None:
        self._validate_no_pay_to_win(request)

    def lock_official_request(self, request: MatchSimulationRequest) -> LockedMatchContext:
        self._validate_no_pay_to_win(request)
        if request.tactical_changes:
            raise FairnessViolation(
                "Official GTEX matches reject mid-match tactical changes after integrity lock.",
                reason="mid_match_mutation_blocked",
            )
        locked_payload = self._canonical_locked_payload(request)
        match_hash = self._hash_payload(locked_payload)
        match_seed = int(match_hash[:16], 16)
        locked_request = request.model_copy(update={"seed": match_seed, "tactical_changes": []})
        return LockedMatchContext(
            request=locked_request,
            locked_payload=locked_payload,
            match_hash=match_hash,
            match_seed=match_seed,
        )

    def _validate_no_pay_to_win(self, request: MatchSimulationRequest) -> None:
        for label, fragment in self._match_affecting_fragments(request):
            self._scan_fragment(fragment, label=label)

    def _match_affecting_fragments(self, request: MatchSimulationRequest) -> list[tuple[str, Any]]:
        return [
            ("home.manager_profile", request.home_team.manager_profile or {}),
            ("away.manager_profile", request.away_team.manager_profile or {}),
            ("home.player_instructions", request.home_team.tactics.player_instructions or {}),
            ("away.player_instructions", request.away_team.tactics.player_instructions or {}),
            ("home.game_state_adjustments", request.home_team.tactics.game_state_adjustments or {}),
            ("away.game_state_adjustments", request.away_team.tactics.game_state_adjustments or {}),
            ("tactical_changes", [item.model_dump(mode="python") for item in request.tactical_changes]),
        ]

    def _scan_fragment(self, fragment: Any, *, label: str, path: str = "") -> None:
        if isinstance(fragment, dict):
            for key, value in fragment.items():
                key_path = f"{path}.{key}" if path else str(key)
                normalized = self._normalize_token(str(key))
                if self._contains_banned_term(normalized, _MONETIZATION_TERMS):
                    raise FairnessViolation(
                        f"Monetization cannot affect match logic. Rejected field {label}:{key_path}.",
                        reason="pay_to_win_injection_rejected",
                    )
                if self._contains_banned_term(normalized, _OUTCOME_TERMS):
                    raise FairnessViolation(
                        f"Client-side result or timeline injection is not allowed in match logic. Rejected field {label}:{key_path}.",
                        reason="result_injection_rejected",
                    )
                self._scan_fragment(value, label=label, path=key_path)
            return
        if isinstance(fragment, (list, tuple)):
            for index, value in enumerate(fragment):
                self._scan_fragment(value, label=label, path=f"{path}[{index}]")

    def _canonical_locked_payload(self, request: MatchSimulationRequest) -> dict[str, Any]:
        payload = request.model_dump(
            mode="json",
            exclude={
                "seed": True,
                "tactical_changes": True,
                "home_team": {"identity": True},
                "away_team": {"identity": True},
            },
        )
        payload["integrity_lock"] = {
            "squad_locked": True,
            "tactics_locked": True,
            "player_selection_locked": True,
            "frontend_view_only": True,
        }
        return payload

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return sha256(encoded).hexdigest()

    @staticmethod
    def _normalize_token(value: str) -> str:
        return (
            value.strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

    @staticmethod
    def _contains_banned_term(value: str, banned_terms: tuple[str, ...]) -> bool:
        return any(term in value for term in banned_terms)


__all__ = ["FairnessGuard", "FairnessViolation", "LockedMatchContext"]
