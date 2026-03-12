from __future__ import annotations

from backend.app.common.enums.replay_visibility import ReplayVisibility
from backend.app.replay_archive.policy import SpectatorVisibilityPolicyService


def test_visibility_policy_keeps_early_rounds_private_without_public_opt_in() -> None:
    decision = SpectatorVisibilityPolicyService().resolve(
        replay_visibility=ReplayVisibility.COMPETITION,
        round_number=1,
        stage_name="Group Stage",
        is_final=False,
        competition_allows_public=False,
        allow_early_round_public=False,
    )

    assert decision.resolved_visibility is ReplayVisibility.PARTICIPANTS
    assert decision.public_metadata_visible is False
    assert decision.featured_public is False


def test_visibility_policy_promotes_later_rounds_when_public_spectating_is_enabled() -> None:
    decision = SpectatorVisibilityPolicyService().resolve(
        replay_visibility=ReplayVisibility.COMPETITION,
        round_number=4,
        stage_name="Quarterfinal",
        is_final=False,
        competition_allows_public=True,
        allow_early_round_public=False,
    )

    assert decision.resolved_visibility is ReplayVisibility.PUBLIC
    assert decision.public_metadata_visible is True
    assert decision.featured_public is True


def test_visibility_policy_exposes_final_metadata_even_when_full_replay_is_not_public() -> None:
    decision = SpectatorVisibilityPolicyService().resolve(
        replay_visibility=ReplayVisibility.COMPETITION,
        round_number=6,
        stage_name="Final",
        is_final=True,
        competition_allows_public=False,
        allow_early_round_public=False,
    )

    assert decision.resolved_visibility is ReplayVisibility.COMPETITION
    assert decision.public_metadata_visible is True
    assert decision.featured_public is True
