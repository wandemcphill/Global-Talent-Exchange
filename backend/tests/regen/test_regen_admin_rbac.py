from __future__ import annotations

from datetime import date
import os
from uuid import uuid4

from backend.tests.support.secrets import TEST_PASSWORD
from app.admin_godmode.service import REGEN_OPS_ADMIN_ROLE_NAME
from app.ingestion.models import Player
from app.models.club_profile import ClubProfile
from app.models.player_cards import PlayerCard, PlayerCardTier
from app.models.regen import RegenProfile
from app.models.user import User


def _create_scoped_admin_headers(
    client,
    bootstrap_admin_headers: dict[str, str],
    *,
    role_name: str,
) -> dict[str, str]:
    suffix = uuid4().hex[:8]
    email = f"{role_name}-{suffix}@example.com"
    username = f"{role_name}_{suffix}".replace("-", "_")
    response = client.post(
        "/api/admin/access",
        headers=bootstrap_admin_headers,
        json={
            "email": email,
            "username": username,
            "password": TEST_PASSWORD,
            "display_name": f"Scoped {role_name} {suffix}",
            "role_name": role_name,
            "permissions": [],
        },
    )
    assert response.status_code == 201, response.text

    login = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": TEST_PASSWORD,
        },
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_inactive_regen_season(client, headers: dict[str, str]) -> str:
    season_number = 100_000 + int(uuid4().hex[:6], 16)
    response = client.post(
        "/admin/regen-universe/seasons",
        headers=headers,
        json={
            "season_number": season_number,
            "start_date": date(2032, 1, 1).isoformat(),
            "end_date": date(2032, 12, 31).isoformat(),
            "is_active": False,
            "source_ingestion_season_ids": [],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _seed_regen_player_for_portraits(client, *, prefix: str) -> str:
    rarity_rank = 500 + int(uuid4().hex[:4], 16)
    with client.app.state.session_factory() as session:
        owner = User(
            id=f"{prefix}-owner",
            email=f"{prefix}-owner@example.com",
            username=f"{prefix}_owner",
            password_hash="hash",
            full_name="Portrait Owner",
        )
        session.add(owner)

        club_profile = ClubProfile(
            id=f"{prefix}-club-profile",
            owner_user_id=owner.id,
            club_name="Portrait FC",
            short_name="PFC",
            slug=f"{prefix}-portrait-fc",
            primary_color="#0B5FFF",
            secondary_color="#F5F7FA",
            accent_color="#14B86A",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
            visibility="public",
        )
        session.add(club_profile)

        tier = PlayerCardTier(
            id=f"{prefix}-tier",
            code=f"{prefix.upper()}_LAUNCH",
            name=f"{prefix} Launch Tier",
            rarity_rank=rarity_rank,
        )
        session.add(tier)

        player = Player(
            id=f"{prefix}-player",
            source_provider="gtex_regen",
            provider_external_id=f"{prefix}-player",
            full_name="Portrait Prospect",
            position="AM",
            normalized_position="midfielder",
            date_of_birth=date(2010, 6, 18),
            current_club_profile_id=club_profile.id,
            market_value_eur=4_500_000,
            current_market_reference_value=4_500_000,
            is_real_player=False,
            dna_profile={},
        )
        session.add(player)

        card = PlayerCard(
            id=f"{prefix}-card",
            player_id=player.id,
            tier_id=tier.id,
            edition_code="launch",
            display_name=player.full_name,
            card_variant="base",
            supply_total=1,
            supply_available=1,
        )
        session.add(card)

        session.add(
            RegenProfile(
                id=f"{prefix}-regen-profile",
                regen_id=f"{prefix}-regen",
                player_id=player.id,
                linked_unique_card_id=card.id,
                generated_for_club_id=club_profile.id,
                birth_country_code="NG",
                birth_region="Lagos",
                birth_city="Lagos",
                primary_position="AM",
                secondary_positions_json=[],
                current_gsi=74,
                current_ability_range_json={"minimum": 68, "maximum": 79},
                potential_range_json={"minimum": 82, "maximum": 91},
                scout_confidence="high",
                generation_source="academy",
                metadata_json={},
            )
        )
        session.commit()
        return player.id


def test_super_admin_can_run_regen_admin_routes(client, bootstrap_admin_headers) -> None:
    season_id = _create_inactive_regen_season(client, bootstrap_admin_headers)

    preseed_response = client.post(
        "/admin/regen-universe/national-regens/preseed",
        headers=bootstrap_admin_headers,
        json={
            "country_codes": ["NG"],
            "age_band": "u17",
            "preseed_batch": f"rbac-super-{uuid4().hex[:8]}",
        },
    )
    assert preseed_response.status_code == 201, preseed_response.text
    preseed_payload = preseed_response.json()
    assert preseed_payload["summary"] is not None
    assert preseed_payload["summary"]["created"] + preseed_payload["summary"]["skipped_existing"] >= 1

    story_job_response = client.post(
        "/admin/regen-universe/jobs/story-regeneration",
        headers=bootstrap_admin_headers,
    )
    assert story_job_response.status_code in {200, 202}, story_job_response.text
    assert story_job_response.json()["name"] == "regen_universe.story_regeneration"

    close_response = client.post(
        f"/admin/regen-universe/seasons/{season_id}/close",
        headers=bootstrap_admin_headers,
        json={"start_next_season": False},
    )
    assert close_response.status_code == 200, close_response.text
    assert close_response.json()["season_id"] == season_id


def test_regen_ops_admin_can_preseed_national_regens_and_close_seasons(
    client,
    bootstrap_admin_headers,
) -> None:
    regen_ops_headers = _create_scoped_admin_headers(
        client,
        bootstrap_admin_headers,
        role_name=REGEN_OPS_ADMIN_ROLE_NAME,
    )
    season_id = _create_inactive_regen_season(client, bootstrap_admin_headers)

    preseed_response = client.post(
        "/admin/regen-universe/national-regens/preseed",
        headers=regen_ops_headers,
        json={
            "country_codes": ["GH"],
            "age_band": "u20",
            "preseed_batch": f"rbac-regen-ops-{uuid4().hex[:8]}",
        },
    )
    assert preseed_response.status_code == 201, preseed_response.text

    close_response = client.post(
        f"/admin/regen-universe/seasons/{season_id}/close",
        headers=regen_ops_headers,
        json={"start_next_season": False},
    )
    assert close_response.status_code == 200, close_response.text
    assert close_response.json()["season_id"] == season_id


def test_regen_ops_admin_can_manage_regen_portraits(
    client,
    bootstrap_admin_headers,
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("GTE_GENERATED_MEDIA_ROOT", os.fspath(tmp_path))
    monkeypatch.setenv("GTE_GENERATED_MEDIA_BASE_URL", "http://portrait.test")
    regen_ops_headers = _create_scoped_admin_headers(
        client,
        bootstrap_admin_headers,
        role_name=REGEN_OPS_ADMIN_ROLE_NAME,
    )
    player_id = _seed_regen_player_for_portraits(
        client,
        prefix=f"portrait-{uuid4().hex[:8]}",
    )

    regenerate_response = client.post(
        f"/admin/regen-universe/players/{player_id}/portrait/regenerate",
        headers=regen_ops_headers,
    )
    assert regenerate_response.status_code == 200, regenerate_response.text
    regenerate_payload = regenerate_response.json()
    assert regenerate_payload["player_id"] == player_id
    assert regenerate_payload["status"] == "ready"
    assert regenerate_payload["face_seed"]
    assert regenerate_payload["face_recipe"]["seed"] == regenerate_payload["face_seed"]
    assert regenerate_payload["portrait_url"].startswith("http://portrait.test/generated-media/")

    override_response = client.post(
        f"/admin/regen-universe/players/{player_id}/portrait/override",
        headers=regen_ops_headers,
        json={"portrait_url": "https://cdn.example.test/portraits/override.png"},
    )
    assert override_response.status_code == 200, override_response.text
    override_payload = override_response.json()
    assert override_payload["player_id"] == player_id
    assert override_payload["status"] == "override"
    assert override_payload["portrait_url"] == "https://cdn.example.test/portraits/override.png"

    ban_response = client.post(
        f"/admin/regen-universe/players/{player_id}/portrait/ban",
        headers=regen_ops_headers,
        json={"reason": "launch moderation"},
    )
    assert ban_response.status_code == 200, ban_response.text
    ban_payload = ban_response.json()
    assert ban_payload["player_id"] == player_id
    assert ban_payload["status"] == "banned"
    assert ban_payload["portrait_url"] is None


def test_support_admin_cannot_manage_regen_portraits(
    client,
    bootstrap_admin_headers,
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("GTE_GENERATED_MEDIA_ROOT", os.fspath(tmp_path))
    monkeypatch.setenv("GTE_GENERATED_MEDIA_BASE_URL", "http://portrait.test")
    support_headers = _create_scoped_admin_headers(
        client,
        bootstrap_admin_headers,
        role_name="support_admin",
    )
    player_id = _seed_regen_player_for_portraits(
        client,
        prefix=f"portrait-support-{uuid4().hex[:8]}",
    )

    response = client.post(
        f"/admin/regen-universe/players/{player_id}/portrait/regenerate",
        headers=support_headers,
    )
    assert response.status_code == 403
    assert response.json()["message"] == "Permission manage_regen_generation is required for this action."


def test_support_admin_cannot_preseed_or_close_regen_seasons(
    client,
    bootstrap_admin_headers,
) -> None:
    support_headers = _create_scoped_admin_headers(
        client,
        bootstrap_admin_headers,
        role_name="support_admin",
    )
    season_id = _create_inactive_regen_season(client, bootstrap_admin_headers)

    preseed_response = client.post(
        "/admin/regen-universe/national-regens/preseed",
        headers=support_headers,
        json={
            "country_codes": ["SN"],
            "age_band": "senior",
            "preseed_batch": f"rbac-support-{uuid4().hex[:8]}",
        },
    )
    assert preseed_response.status_code == 403
    assert preseed_response.json()["message"] == "Permission manage_national_regens is required for this action."

    close_response = client.post(
        f"/admin/regen-universe/seasons/{season_id}/close",
        headers=support_headers,
        json={"start_next_season": False},
    )
    assert close_response.status_code == 403
    assert close_response.json()["message"] == "Permission manage_regen_universe is required for this action."
