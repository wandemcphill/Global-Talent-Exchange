from __future__ import annotations

from dataclasses import dataclass

from app.common.enums.replay_visibility import ReplayVisibility


@dataclass(frozen=True, slots=True)
class SpectatorVisibilityDecision:
    resolved_visibility: ReplayVisibility
    public_metadata_visible: bool
    featured_public: bool


class SpectatorVisibilityPolicyService:
    def resolve(
        self,
        *,
        replay_visibility: ReplayVisibility,
        round_number: int | None,
        stage_name: str | None,
        is_final: bool,
        competition_allows_public: bool,
        allow_early_round_public: bool,
    ) -> SpectatorVisibilityDecision:
        if replay_visibility is ReplayVisibility.PRIVATE:
            return SpectatorVisibilityDecision(
                resolved_visibility=ReplayVisibility.PRIVATE,
                public_metadata_visible=is_final,
                featured_public=is_final,
            )

        early_round = self._is_early_round(
            round_number=round_number,
            stage_name=stage_name,
            allow_early_round_public=allow_early_round_public,
        )
        late_round = self._is_late_round(round_number=round_number, stage_name=stage_name, is_final=is_final)

        if is_final:
            resolved_visibility = replay_visibility
            if replay_visibility is ReplayVisibility.PUBLIC or competition_allows_public:
                resolved_visibility = ReplayVisibility.PUBLIC
            return SpectatorVisibilityDecision(
                resolved_visibility=resolved_visibility,
                public_metadata_visible=True,
                featured_public=True,
            )

        if early_round and not competition_allows_public:
            return SpectatorVisibilityDecision(
                resolved_visibility=ReplayVisibility.PARTICIPANTS,
                public_metadata_visible=False,
                featured_public=False,
            )

        if late_round and competition_allows_public:
            if replay_visibility in {ReplayVisibility.PUBLIC, ReplayVisibility.COMPETITION}:
                return SpectatorVisibilityDecision(
                    resolved_visibility=ReplayVisibility.PUBLIC,
                    public_metadata_visible=True,
                    featured_public=True,
                )

        return SpectatorVisibilityDecision(
            resolved_visibility=replay_visibility,
            public_metadata_visible=replay_visibility is ReplayVisibility.PUBLIC,
            featured_public=replay_visibility is ReplayVisibility.PUBLIC and late_round,
        )

    @staticmethod
    def _is_early_round(
        *,
        round_number: int | None,
        stage_name: str | None,
        allow_early_round_public: bool,
    ) -> bool:
        if allow_early_round_public:
            return False
        if round_number is not None and round_number <= 2:
            return True
        normalized = (stage_name or "").strip().lower()
        return any(
            marker in normalized
            for marker in (
                "qualifier",
                "qualification",
                "group",
                "league phase",
                "opening",
                "round of 64",
                "round of 32",
            )
        )

    @staticmethod
    def _is_late_round(*, round_number: int | None, stage_name: str | None, is_final: bool) -> bool:
        if is_final:
            return True
        if round_number is not None and round_number >= 3:
            return True
        normalized = (stage_name or "").strip().lower()
        return any(
            marker in normalized
            for marker in (
                "playoff",
                "knockout",
                "quarter",
                "semi",
                "final",
            )
        )
