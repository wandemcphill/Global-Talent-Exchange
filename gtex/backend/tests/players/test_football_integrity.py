from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.players.football_integrity import (
    FootballPosition,
    calculate_gsi,
    infer_position_from_stat_profile,
    normalize_position,
    repairPlayerPositions,
    repair_gsi_clusters,
    validate_position_profile,
)


def test_position_normalization_accepts_common_football_aliases() -> None:
    assert normalize_position("goal keeper") is FootballPosition.GK
    assert normalize_position("centre-back") is FootballPosition.CB
    assert normalize_position("left full back") is FootballPosition.LB
    assert normalize_position("right wing") is FootballPosition.RW
    assert normalize_position("attacking mid") is FootballPosition.CAM


def test_position_validation_flags_misclassified_outfield_profiles() -> None:
    forward_profile = {
        "finishing": 91,
        "shooting": 88,
        "movement": 86,
        "pace": 90,
        "dribbling": 84,
        "composure": 87,
        "defending": 34,
        "tackling": 31,
        "interceptions": 28,
        "strength": 49,
        "aerials": 44,
    }
    defender_reasons = validate_position_profile(FootballPosition.CB, forward_profile)

    assert defender_reasons == ("defender_profile_has_forward_attributes",)
    assert infer_position_from_stat_profile(forward_profile, stable_key="st") is FootballPosition.ST


def test_position_weighted_gsi_uses_role_specific_attributes() -> None:
    goalkeeper = {
        "id": "keeper-1",
        "position": "GK",
        "reflexes": 93,
        "diving": 91,
        "handling": 88,
        "positioning": 87,
        "finishing": 21,
        "shooting": 24,
    }
    forward = {
        "id": "forward-1",
        "position": "ST",
        "finishing": 93,
        "shooting": 90,
        "movement": 88,
        "pace": 86,
        "composure": 91,
        "reflexes": 19,
        "handling": 16,
    }

    assert calculate_gsi(goalkeeper, apply_variance=False) >= 89
    assert calculate_gsi(forward, apply_variance=False) >= 89
    assert calculate_gsi(goalkeeper, position="ST", apply_variance=False) < 45
    assert calculate_gsi(forward, position="GK", apply_variance=False) < 45


def test_repair_player_positions_updates_invalid_defender_profile() -> None:
    player = _FakePlayer(
        id="player-1",
        full_name="Misfiled Forward",
        position="Center Back",
        normalized_position="CB",
        dna_profile={
            "finishing": 92,
            "shooting": 89,
            "movement": 87,
            "pace": 88,
            "dribbling": 83,
            "composure": 90,
            "defending": 33,
            "tackling": 29,
            "interceptions": 31,
            "strength": 47,
            "aerials": 41,
        },
    )
    session = _FakeSession(players=[player])

    changes = repairPlayerPositions(session, dry_run=False)

    assert len(changes) == 1
    assert changes[0].previous_normalized_position == "CB"
    assert changes[0].repaired_code == "ST"
    assert changes[0].reason == "defender_profile_has_forward_attributes"
    assert player.position == FootballPosition.ST.value
    assert player.normalized_position == FootballPosition.ST.name
    assert session.flushed is True


def test_repair_gsi_clusters_replaces_static_values_with_dynamic_score() -> None:
    player = _FakePlayer(
        id="player-2",
        full_name="Clustered Striker",
        position="Striker",
        normalized_position="ST",
        dna_profile={
            "finishing": 88,
            "shooting": 84,
            "movement": 86,
            "pace": 82,
            "composure": 87,
            "physical": 74,
            "mentality": 80,
        },
    )
    summary = _FakeSummary(summary_json={"global_scouting_index": 75})
    session = _FakeSession(gsi_rows=[(player, summary)])

    changes = repair_gsi_clusters(session, dry_run=False)

    assert len(changes) == 1
    assert changes[0]["previous_gsi"] == 75
    assert summary.summary_json["global_scouting_index"] != 75
    assert summary.summary_json["gsi_repair_source"] == "position_weighted_integrity_engine"
    assert session.flushed is True


@dataclass
class _FakePlayer:
    id: str
    full_name: str
    position: str | None
    normalized_position: str | None
    dna_profile: dict[str, Any]
    height_cm: int | None = None
    weight_kg: int | None = None
    market_value_eur: float | None = None


@dataclass
class _FakeSummary:
    summary_json: dict[str, Any]


@dataclass
class _FakeSession:
    players: list[_FakePlayer] = field(default_factory=list)
    gsi_rows: list[tuple[_FakePlayer, _FakeSummary]] = field(default_factory=list)
    flushed: bool = False

    def scalars(self, _statement: object) -> list[_FakePlayer]:
        return self.players

    def execute(self, _statement: object) -> list[tuple[_FakePlayer, _FakeSummary]]:
        return self.gsi_rows

    def flush(self) -> None:
        self.flushed = True
