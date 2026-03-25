from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from typing import Any

from app.auth.security import get_settings
from app.fairness.fairness_guard import LockedMatchContext
from app.schemas.match_viewer import (
    FairnessIndicatorStatus,
    MatchFairnessIndicatorView,
    MatchMode,
    MatchTimelineProofStatus,
    MatchTimelineProofView,
    MatchViewerSessionView,
    MatchViewStateView,
)
from app.services.signing_service import SignatureError, SignedTokenService

_SEGMENT_WINDOW_SECONDS = 120
_SESSION_TTL_SECONDS = 1800


class MatchIntegrityViolation(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(slots=True)
class MatchIntegrityService:
    signer: SignedTokenService | None = None
    segment_window_seconds: int = _SEGMENT_WINDOW_SECONDS
    session_ttl_seconds: int = _SESSION_TTL_SECONDS

    def __post_init__(self) -> None:
        if self.signer is None:
            self.signer = SignedTokenService(
                get_settings().auth_secret,
                purpose="match_viewer_segment",
            )

    def build_fairness_envelope(
        self,
        *,
        locked_context: LockedMatchContext,
        view_state: MatchViewStateView,
        balance_metadata: dict[str, Any] | None,
        competition_metadata_json: dict[str, Any] | None,
    ) -> dict[str, Any]:
        fairness_payload = {}
        if isinstance(competition_metadata_json, dict):
            raw_fairness = competition_metadata_json.get("fairness")
            if isinstance(raw_fairness, dict):
                fairness_payload = raw_fairness
        timeline_hash = self._sha_hash_view_state(view_state)
        visible_hash = self._visible_hash_view_state(view_state)
        return {
            "match_hash": locked_context.match_hash,
            "match_seed": locked_context.match_seed,
            "timeline_hash": timeline_hash,
            "visible_timeline_hash": visible_hash,
            "no_pay_to_win": True,
            "visual_only_monetization": True,
            "server_authoritative": True,
            "timeline_signed": True,
            "balance": balance_metadata or {},
            "mode": fairness_payload.get("mode", "open"),
        }

    def validate_view_state(self, *, view_state: MatchViewStateView, fairness_metadata: dict[str, Any] | None) -> None:
        if not isinstance(fairness_metadata, dict):
            return
        expected_timeline_hash = fairness_metadata.get("timeline_hash")
        if not expected_timeline_hash:
            return
        actual_timeline_hash = self._sha_hash_view_state(view_state)
        if actual_timeline_hash != expected_timeline_hash:
            raise MatchIntegrityViolation(
                "Stored match timeline proof does not match the replay payload.",
                reason="timeline_hash_mismatch",
            )

    def build_viewer_session(
        self,
        *,
        match_id: str,
        view_state: MatchViewStateView,
        fairness_metadata: dict[str, Any] | None,
        mode: MatchMode,
        continuation_token: str | None = None,
        canonical_view_state: MatchViewStateView | None = None,
    ) -> MatchViewerSessionView:
        verified = isinstance(fairness_metadata, dict)
        if verified:
            self.validate_view_state(
                view_state=canonical_view_state or view_state,
                fairness_metadata=fairness_metadata,
            )

        segment_start_seconds = 0
        if continuation_token:
            try:
                token_payload = self.signer.verify(continuation_token)
            except SignatureError as exc:
                raise MatchIntegrityViolation("Segment continuation token is invalid.", reason="invalid_segment_token") from exc
            if token_payload.get("match_id") != match_id:
                raise MatchIntegrityViolation("Continuation token does not belong to this match.", reason="segment_token_match_mismatch")
            if token_payload.get("mode") != mode.value:
                raise MatchIntegrityViolation("Continuation token mode does not match the requested playback mode.", reason="segment_token_mode_mismatch")
            segment_start_seconds = int(token_payload.get("revealed_through_seconds") or 0)

        segment_end_seconds = min(
            int(view_state.duration_seconds),
            segment_start_seconds + self.segment_window_seconds,
        )
        has_more_segments = segment_end_seconds < int(view_state.duration_seconds)
        visible_view_state = self._slice_view_state(
            view_state,
            revealed_through_seconds=segment_end_seconds,
        )
        visible_hash = self._visible_hash_view_state(visible_view_state)
        fairness = fairness_metadata or {
            "match_hash": self._sha_hash({"match_id": match_id, "mode": mode.value}),
            "timeline_hash": self._sha_hash_view_state(view_state),
            "mode": "open",
            "no_pay_to_win": True,
            "visual_only_monetization": True,
            "server_authoritative": True,
            "timeline_signed": True,
            "balance": {},
        }

        next_segment_token = None
        if has_more_segments:
            signed = self.signer.sign(
                {
                    "match_id": match_id,
                    "mode": mode.value,
                    "revealed_through_seconds": segment_end_seconds,
                },
                expires_in_seconds=self.session_ttl_seconds,
            )
            next_segment_token = signed.token

        indicator = MatchFairnessIndicatorView(
            status=FairnessIndicatorStatus.VERIFIED if verified else FairnessIndicatorStatus.UNVERIFIED,
            label="Fair Play Verified" if verified else "Fair Play Pending",
            message=(
                "Server-authoritative playback. Monetization remains visual only."
                if verified
                else "Playback is server-delivered, but persisted proof metadata was not found."
            ),
            no_pay_to_win=bool(fairness.get("no_pay_to_win", True)),
            visual_only_monetization=bool(fairness.get("visual_only_monetization", True)),
            server_authoritative=bool(fairness.get("server_authoritative", True)),
            tournament_fairness_mode=str(fairness.get("mode", "open")),
            home_spend_tier=self._nested_value(fairness, ("balance", "spend_tiers", "home", "tier")),
            away_spend_tier=self._nested_value(fairness, ("balance", "spend_tiers", "away", "tier")),
            squad_balance_policy=self._nested_value(fairness, ("balance", "squad_balance", "policy")) or "s_plus_cap",
            soft_balance_applied=bool(self._nested_value(fairness, ("balance", "soft_balance", "applied"))),
        )
        proof = MatchTimelineProofView(
            status=MatchTimelineProofStatus.VERIFIED if verified else MatchTimelineProofStatus.UNVERIFIED,
            match_hash=str(fairness.get("match_hash", "")),
            timeline_hash=str(fairness.get("timeline_hash", "")),
            visible_timeline_hash=visible_hash,
            signed=bool(fairness.get("timeline_signed", True)),
            revealed_through_seconds=segment_end_seconds,
        )
        return MatchViewerSessionView(
            **visible_view_state.model_dump(mode="python", exclude={"deterministic_seed"}),
            deterministic_seed=None,
            fairness_indicator=indicator,
            timeline_proof=proof,
            score_reveal_locked=has_more_segments,
            segment_start_seconds=segment_start_seconds,
            segment_end_seconds=segment_end_seconds,
            has_more_segments=has_more_segments,
            next_segment_token=next_segment_token,
        )

    def _slice_view_state(
        self,
        view_state: MatchViewStateView,
        *,
        revealed_through_seconds: int,
    ) -> MatchViewStateView:
        visible_events = [
            item for item in view_state.events
            if float(item.time_seconds) <= float(revealed_through_seconds)
        ]
        visible_frames = [
            item for item in view_state.frames
            if float(item.time_seconds) <= float(revealed_through_seconds)
        ]
        if not visible_frames and view_state.frames:
            visible_frames = [view_state.frames[0]]
        return MatchViewStateView(
            match_id=view_state.match_id,
            source=view_state.source,
            match_mode=view_state.match_mode,
            supports_offside=view_state.supports_offside,
            deterministic_seed=None,
            duration_seconds=revealed_through_seconds,
            home_team=view_state.home_team,
            away_team=view_state.away_team,
            events=visible_events,
            frames=visible_frames,
        )

    def _sha_hash_view_state(self, view_state: MatchViewStateView) -> str:
        payload = view_state.model_dump(
            mode="json",
            exclude={"deterministic_seed", "match_mode"},
        )
        return self._sha_hash(payload)

    def _visible_hash_view_state(self, view_state: MatchViewStateView) -> str:
        payload = view_state.model_dump(
            mode="json",
            exclude={"deterministic_seed", "match_mode"},
        )
        canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        return f"{self._fnv1a_32(canonical.encode('utf-8')):08x}"

    @staticmethod
    def _sha_hash(payload: Any) -> str:
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return sha256(encoded).hexdigest()

    @staticmethod
    def _fnv1a_32(payload: bytes) -> int:
        value = 0x811C9DC5
        for item in payload:
            value ^= item
            value = (value * 0x01000193) & 0xFFFFFFFF
        return value

    @staticmethod
    def _nested_value(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
        current: Any = payload
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current


__all__ = ["MatchIntegrityService", "MatchIntegrityViolation"]
