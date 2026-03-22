from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from app.services.avatar_service import AvatarIdentityInput, AvatarService


@dataclass
class _DummyCountry:
    name: str | None = None
    alpha2_code: str | None = None
    alpha3_code: str | None = None
    fifa_code: str | None = None


@dataclass
class _DummyPlayer:
    id: str
    full_name: str
    position: str
    normalized_position: str
    preferred_foot: str | None = None
    date_of_birth: object | None = None
    country: _DummyCountry | None = None


def test_avatar_service_is_deterministic_for_same_identity() -> None:
    service = AvatarService()
    identity = AvatarIdentityInput(
        player_id="player-001",
        player_name="Adaeze Forward",
        nationality_code="NG",
        position="ST",
        normalized_position="ST",
        birth_year=2002,
        preferred_foot="right",
    )

    first = service.build_avatar(identity)
    second = service.build_avatar(identity)

    assert first == second
    assert first.seed_token == "player-001"
    assert first.avatar_version == 1


def test_avatar_service_uses_explicit_seed_token_first() -> None:
    service = AvatarService()
    first = service.build_avatar(
        AvatarIdentityInput(
            player_id="player-001",
            player_name="Different Name",
            nationality_code="PT",
            position="CM",
            birth_year=1999,
            avatar_seed_token="thread-a-token",
        )
    )
    second = service.build_avatar(
        AvatarIdentityInput(
            player_id="player-777",
            player_name="Another Player",
            nationality_code="BR",
            position="GK",
            birth_year=1988,
            avatar_seed_token="thread-a-token",
        )
    )

    assert first == second
    assert first.seed_token == "thread-a-token"


def test_avatar_service_keeps_existing_player_avatar_stable_when_profile_traits_change() -> None:
    service = AvatarService()
    first = service.build_avatar(
        AvatarIdentityInput(
            player_id="player-immovable",
            player_name="Original Name",
            nationality_code="NG",
            position="ST",
            normalized_position="ST",
            birth_year=2003,
            preferred_foot="right",
        )
    )
    second = service.build_avatar(
        AvatarIdentityInput(
            player_id="player-immovable",
            player_name="Updated Name",
            nationality_code="PT",
            position="CB",
            normalized_position="CB",
            birth_year=1991,
            preferred_foot="left",
        )
    )

    assert first == second
    assert second.seed_token == "player-immovable"


def test_avatar_service_preserves_stored_seed_from_creation_payload() -> None:
    service = AvatarService()
    player = _DummyPlayer(
        id="player-777",
        full_name="Legacy Midfielder",
        position="CM",
        normalized_position="CM",
        preferred_foot="right",
        country=_DummyCountry(name="Nigeria", alpha2_code="NG"),
    )

    baseline = service.build_from_player(
        player,
        summary_payload={
            "avatar_seed_token": "seed-locked-at-creation",
            "avatar_dna_seed": "feed-face-cafe-babe",
        },
    )
    player.full_name = "Renamed Veteran"
    player.position = "GK"
    player.normalized_position = "GK"
    player.preferred_foot = "left"
    player.country = _DummyCountry(name="Portugal", alpha2_code="PT")
    replayed = service.build_from_player(
        player,
        summary_payload={
            "avatar_seed_token": "seed-locked-at-creation",
            "avatar_dna_seed": "feed-face-cafe-babe",
        },
    )

    assert baseline == replayed
    assert replayed.seed_token == "seed-locked-at-creation"


def test_avatar_service_changes_when_canonical_identity_changes() -> None:
    service = AvatarService()
    baseline = service.build_avatar(
        AvatarIdentityInput(
            player_id="player-010",
            nationality_code="AR",
            position="RW",
            birth_year=2001,
        )
    )
    variant = service.build_avatar(
        AvatarIdentityInput(
            player_id="player-011",
            nationality_code="AR",
            position="CB",
            birth_year=2001,
        )
    )

    assert baseline.seed_token != ""
    assert baseline != variant


def test_avatar_service_reduces_beard_styles_for_younger_players() -> None:
    service = AvatarService()
    youth = service.build_avatar(
        AvatarIdentityInput(
            player_id="player-020",
            nationality_code="GH",
            position="ST",
            birth_year=2009,
        )
    )
    veteran = service.build_avatar(
        AvatarIdentityInput(
            player_id="player-021",
            nationality_code="GH",
            position="ST",
            birth_year=1990,
        )
    )

    assert youth.beard_style in {0, 1, 2, 3}
    assert veteran.beard_style in {0, 1, 2, 3, 4, 5}


def test_avatar_service_trait_distribution_stays_diverse() -> None:
    service = AvatarService()
    sample_size = 1000
    skin_counts: Counter[int] = Counter()
    hair_counts: Counter[int] = Counter()
    face_counts: Counter[int] = Counter()

    for index in range(sample_size):
        avatar = service.build_avatar(
            AvatarIdentityInput(
                player_id=f"player-{index:04d}",
            )
        )
        skin_counts[avatar.skin_tone] += 1
        hair_counts[avatar.hair_style] += 1
        face_counts[avatar.face_shape] += 1

    assert max(skin_counts.values()) / sample_size <= 0.40
    assert max(hair_counts.values()) / sample_size <= 0.40
    assert max(face_counts.values()) / sample_size <= 0.40
