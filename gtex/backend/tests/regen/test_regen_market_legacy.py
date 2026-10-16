from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.ingestion.models import Player
from app.models.club_hall_of_fame import ClubHallOfFameEntry
from app.models.club_profile import ClubProfile
from app.models.player_cards import PlayerCard, PlayerCardTier
from app.models.player_career_entry import PlayerCareerEntry
from app.models.regen import (
    RegenAward,
    RegenLegacyRecord,
    RegenLineageProfile,
    RegenOriginMetadata,
    RegenProfile,
    RegenTwinsGroup,
)
from app.models.user import KycStatus, User, UserRole
from app.services.regen_legacy_service import RegenLegacyService
from app.services.regen_market_service import RegenMarketService, RegenSearchFilters, _validate_award_name


def _make_user(session, *, user_id: str, email: str, username: str) -> User:
    user = User(
        id=user_id,
        email=email,
        username=username,
        password_hash="hash",
        role=UserRole.USER,
        kyc_status=KycStatus.UNVERIFIED,
    )
    session.add(user)
    return user


def _make_club(session, *, club_id: str, owner_user_id: str, name: str) -> ClubProfile:
    club = ClubProfile(
        id=club_id,
        owner_user_id=owner_user_id,
        club_name=name,
        short_name=name[:12],
        slug=name.lower().replace(" ", "-"),
        primary_color="#111111",
        secondary_color="#eeeeee",
        accent_color="#ff5500",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
    )
    session.add(club)
    return club


def _make_player(session, *, player_id: str, full_name: str, dob: date) -> Player:
    player = Player(
        id=player_id,
        source_provider="gtex_regen",
        provider_external_id=f"regen:{player_id}",
        full_name=full_name,
        position="ST",
        normalized_position="forward",
        date_of_birth=dob,
        is_tradable=True,
    )
    session.add(player)
    return player


def _make_card_tier(session) -> PlayerCardTier:
    tier = PlayerCardTier(
        id="tier-regen",
        code="regen_unique",
        name="Regen Unique",
        rarity_rank=1,
    )
    session.add(tier)
    return tier


def _make_card(session, *, card_id: str, player: Player, tier: PlayerCardTier) -> PlayerCard:
    card = PlayerCard(
        id=card_id,
        player_id=player.id,
        tier_id=tier.id,
        edition_code="regen_unique",
        display_name=player.full_name,
        season_label="2025/2026",
        card_variant="regen_unique",
        supply_total=1,
        supply_available=1,
    )
    session.add(card)
    return card


def _make_regen_profile(
    session,
    *,
    regen_id: str,
    player: Player,
    card: PlayerCard,
    club: ClubProfile,
    potential_max: int,
    generation_source: str = "academy",
    is_special_lineage: bool = False,
) -> RegenProfile:
    regen = RegenProfile(
        id=f"regen-{regen_id}",
        regen_id=regen_id,
        player_id=player.id,
        linked_unique_card_id=card.id,
        generated_for_club_id=club.id,
        birth_country_code="NG",
        birth_region="Lagos",
        birth_city="Lagos",
        primary_position="ST",
        secondary_positions_json=["RW"],
        generated_at=datetime.now(timezone.utc),
        current_gsi=60,
        current_ability_range_json={"minimum": 55, "maximum": 65},
        potential_range_json={"minimum": 70, "maximum": potential_max},
        scout_confidence="High",
        generation_source=generation_source,
        status="active",
        club_quality_score=70.0,
        metadata_json={},
        is_special_lineage=is_special_lineage,
    )
    session.add(regen)
    return regen


def test_award_name_rejects_regen_label():
    _validate_award_name("GTEX Best Player")
    with pytest.raises(ValueError, match="award_name_contains_regen"):
        _validate_award_name("Regen Golden Boot")


def test_hall_of_fame_insertion_on_legend_retirement(session):
    user = _make_user(session, user_id="user-hof", email="hof@example.com", username="hof")
    club = _make_club(session, club_id="club-hof", owner_user_id=user.id, name="Hall FC")
    player = _make_player(session, player_id="player-hof", full_name="Legacy Star", dob=date(1990, 5, 12))
    tier = _make_card_tier(session)
    card = _make_card(session, card_id="card-hof", player=player, tier=tier)
    regen = _make_regen_profile(
        session,
        regen_id="rgn-hof",
        player=player,
        card=card,
        club=club,
        potential_max=88,
        generation_source="academy",
        is_special_lineage=True,
    )
    session.add_all(
        [
            PlayerCareerEntry(
                player_id=player.id,
                club_id=club.id,
                club_name=club.club_name,
                season_label="2021/2022",
                appearances=140,
                goals=55,
                assists=30,
            ),
            PlayerCareerEntry(
                player_id=player.id,
                club_id=club.id,
                club_name=club.club_name,
                season_label="2022/2023",
                appearances=120,
                goals=40,
                assists=24,
            ),
        ]
    )
    session.add(
        RegenAward(
            regen_id=regen.id,
            club_id=club.id,
            award_code="gtex_best_player",
            award_name="GTEX Best Player",
            award_category="gtex",
            season_label="2022/2023",
            awarded_at=datetime.now(timezone.utc),
            rank=1,
            source_scope="gtex",
            impact_score=16.0,
            metadata_json={},
        )
    )
    session.commit()

    record = RegenLegacyService(session).snapshot_legacy(regen.id, club_id=club.id, retired_on=date(2025, 6, 1))
    session.commit()

    assert record.is_legend is True
    entry = session.query(ClubHallOfFameEntry).filter_by(club_id=club.id, regen_id=regen.id).first()
    assert entry is not None
    assert entry.entry_category == "Legends"


def test_regen_search_filters_cover_lineage_and_legacy(session):
    user = _make_user(session, user_id="user-search", email="search@example.com", username="search")
    club = _make_club(session, club_id="club-search", owner_user_id=user.id, name="Search FC")
    tier = _make_card_tier(session)

    player_legend = _make_player(session, player_id="player-legend", full_name="Legend Son", dob=date(2008, 1, 1))
    card_legend = _make_card(session, card_id="card-legend", player=player_legend, tier=tier)
    regen_legend = _make_regen_profile(
        session,
        regen_id="rgn-legend",
        player=player_legend,
        card=card_legend,
        club=club,
        potential_max=92,
        generation_source="academy",
        is_special_lineage=True,
    )
    session.add(
        RegenOriginMetadata(
            regen_profile_id=regen_legend.id,
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
            hometown_club_affinity=club.club_name,
            metadata_json={},
        )
    )
    session.add(
        RegenLineageProfile(
            regen_id=regen_legend.id,
            relationship_type="son_of_legend",
            related_legend_type="real_legend",
            related_legend_ref_id="legend-1",
            lineage_country_code="NG",
            lineage_hometown_code="Lagos",
            is_owner_son=False,
            is_retired_regen_lineage=False,
            is_real_legend_lineage=True,
            is_celebrity_lineage=True,
            is_celebrity_licensed=True,
            lineage_tier="rare",
            narrative_text="Son of a legend.",
            metadata_json={},
        )
    )
    session.add(
        RegenTwinsGroup(
            twins_group_key="twins-search",
            regen_id=regen_legend.id,
            club_id=club.id,
            season_label="2025/2026",
            visual_seed="seed",
            similarity_score=0.86,
            metadata_json={},
        )
    )
    session.add(
        RegenAward(
            regen_id=regen_legend.id,
            club_id=club.id,
            award_code="gtex_golden_boy",
            award_name="GTEX Golden Boy",
            award_category="gtex",
            season_label="2025/2026",
            awarded_at=datetime.now(timezone.utc),
            rank=1,
            source_scope="gtex",
            impact_score=12.5,
            metadata_json={},
        )
    )
    session.add(
        RegenLegacyRecord(
            regen_id=regen_legend.id,
            player_id=player_legend.id,
            club_id=club.id,
            appearances_total=120,
            goals_total=45,
            assists_total=20,
            awards_total=2,
            seasons_total=4,
            legacy_score=150.0,
            legacy_tier="legend",
            is_legend=True,
            metadata_json={},
        )
    )

    player_plain = _make_player(session, player_id="player-plain", full_name="Plain Regen", dob=date(1998, 1, 1))
    card_plain = _make_card(session, card_id="card-plain", player=player_plain, tier=tier)
    _make_regen_profile(
        session,
        regen_id="rgn-plain",
        player=player_plain,
        card=card_plain,
        club=club,
        potential_max=78,
        generation_source="academy",
        is_special_lineage=False,
    )
    session.commit()

    service = RegenMarketService(session)
    legend_only = service.search_regens(RegenSearchFilters(sons_of_legends_only=True))
    assert {item.profile.regen_id for item in legend_only} == {"rgn-legend"}

    twins_only = service.search_regens(RegenSearchFilters(twins_only=True))
    assert {item.profile.regen_id for item in twins_only} == {"rgn-legend"}

    award_only = service.search_regens(RegenSearchFilters(award_winners_only=True))
    assert {item.profile.regen_id for item in award_only} == {"rgn-legend"}

    hometown_only = service.search_regens(RegenSearchFilters(hometown_heroes_only=True))
    assert {item.profile.regen_id for item in hometown_only} == {"rgn-legend"}

    celebrity_only = service.search_regens(RegenSearchFilters(celebrity_linked_only=True))
    assert {item.profile.regen_id for item in celebrity_only} == {"rgn-legend"}

    legacy_filtered = service.search_regens(RegenSearchFilters(min_goals=30, min_appearances=80))
    assert {item.profile.regen_id for item in legacy_filtered} == {"rgn-legend"}

    wonderkids = service.search_regens(RegenSearchFilters(wonderkid_only=True))
    assert {item.profile.regen_id for item in wonderkids} == {"rgn-legend"}
