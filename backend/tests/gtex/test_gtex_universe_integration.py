from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select

from app.auth.service import AuthService
from app.gtex.runtime import ensure_gtex_runtime
from app.models.base import utcnow
from app.models.gtex_economy import GtexMatch
from app.models.gtex_universe import CareerDecision, CareerLegacyRecord, CareerTrainingSession, ManagerMatchHistory
from app.models.player_career_entry import PlayerCareerEntry
from app.models.player_contract import PlayerContract
from app.models.user import User


def _register_user(app_session_factory, *, label: str) -> tuple[User, dict[str, str]]:
    with app_session_factory() as session:
        auth = AuthService()
        suffix = uuid4().hex[:8]
        user = auth.register_user(
            session,
            email=f"{label}-{suffix}@example.com",
            username=f"{label}_{suffix}",
            password="TestPass123!",
            display_name=f"{label.title()} {suffix}",
        )
        session.commit()
        token, _ = auth.issue_access_token(user, session=session)
        session.commit()
        return user, {"Authorization": f"Bearer {token}"}


def _create_career_player(client, headers: dict[str, str], *, player_name: str, current_club: str) -> dict[str, object]:
    response = client.post(
        "/career/create",
        headers=headers,
        json={
            "player_name": player_name,
            "position": "AM",
            "current_club": current_club,
            "growth_rate": 0.12,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _sync_completed_mirror_match(
    client,
    headers: dict[str, str],
    *,
    provider_name: str,
    career_user_id: str,
    player_name: str,
    home_club: str,
    away_club: str,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    suffix = uuid4().hex[:6]
    competition_key = f"ucl-{suffix}"
    home_key = f"home-{suffix}"
    away_key = f"away-{suffix}"
    player_key = f"player-{suffix}"
    event_key = f"event-{suffix}"
    scheduled_at = (utcnow() - timedelta(hours=1)).isoformat()
    sync_payload = {
        "provider_name": provider_name,
        "provider_endpoint": f"manual://{suffix}",
        "optional_sync": True,
        "mirror_into_gtex": True,
        "career_user_id": career_user_id,
        "competitions": [
            {
                "external_key": competition_key,
                "name": "UEFA Champions League",
                "country_name": "Europe",
                "competition_type": "cup",
            }
        ],
        "clubs": [
            {
                "external_key": home_key,
                "competition_external_key": competition_key,
                "name": home_club,
                "country_name": "Nigeria",
            },
            {
                "external_key": away_key,
                "competition_external_key": competition_key,
                "name": away_club,
                "country_name": "Nigeria",
            },
        ],
        "players": [
            {
                "external_key": player_key,
                "name": player_name,
                "club_external_key": home_key,
                "competition_external_key": competition_key,
                "nationality": "Nigeria",
                "position": "AM",
                "real_world_rating": 89.0,
                "market_value": 125000000,
                "stats_json": {
                    "goals": 2,
                    "assists": 1,
                    "match_rating": 9.1,
                    "minutes": 90,
                },
            }
        ],
        "events": [
            {
                "external_key": event_key,
                "competition_external_key": competition_key,
                "home_club_external_key": home_key,
                "away_club_external_key": away_key,
                "headline": f"{home_club} vs {away_club}",
                "event_type": "fixture",
                "status": "completed",
                "scheduled_at": scheduled_at,
                "home_score": 3,
                "away_score": 1,
                "featured_player_keys": [player_key],
                "importance": 0.95,
            }
        ],
    }
    response = client.post("/sync/update", headers=headers, json=sync_payload)
    assert response.status_code == 200, response.text
    sync_data = response.json()
    assert sync_data["mirrored_match_ids"]
    match_id = sync_data["mirrored_match_ids"][0]
    match_response = client.get(f"/ai/match/{match_id}")
    assert match_response.status_code == 200, match_response.text
    return sync_payload, sync_data, match_response.json()


def test_career_mode_progression_updates_player_state_and_market(client, app, app_session_factory):
    runtime = ensure_gtex_runtime(app)
    user, headers = _register_user(app_session_factory, label="career-mode")
    player_name = f"Career Pulse {uuid4().hex[:6]}"

    created = _create_career_player(client, headers, player_name=player_name, current_club="Lagos Comets")
    assert created["user_id"] == user.id
    assert created["current_club"] == "Lagos Comets"
    assert created["career_stats"]["training_sessions"] == 0

    train_response = client.post(
        "/career/train",
        headers=headers,
        json={"focus": "finishing", "intensity": "high"},
    )
    assert train_response.status_code == 200, train_response.text
    trained = train_response.json()
    assert trained["xp"] > created["xp"]
    assert trained["training_focus"] == "finishing"
    assert trained["career_stats"]["training_sessions"] == 1
    assert trained["marketability_score"] > created["marketability_score"]

    transfer_response = client.post(
        "/career/transfer",
        headers=headers,
        json={
            "current_club": "Abuja Arrows",
            "wage_amount": 9500,
            "contract_days": 730,
            "notes": "Step up contract",
        },
    )
    assert transfer_response.status_code == 200, transfer_response.text
    transferred = transfer_response.json()
    assert transferred["current_club"] == "Abuja Arrows"
    assert transferred["career_stats"]["transfers"] == 1
    assert transferred["prestige_score"] >= trained["prestige_score"]

    get_response = client.get(f"/career/{user.id}")
    assert get_response.status_code == 200, get_response.text
    stored = get_response.json()
    assert stored["id"] == created["id"]
    assert stored["current_club"] == "Abuja Arrows"
    assert stored["career_stats"]["training_sessions"] == 1
    assert stored["career_stats"]["transfers"] == 1

    with app_session_factory() as session:
        user_model = session.get(User, user.id)
        assert user_model is not None
        asset = runtime.creator_market.ensure_asset_for_user(session, user_model)
        assert Decimal(asset.demand_score) > Decimal("0")
        assert Decimal(asset.momentum_score) > Decimal("0")
        assert (
            session.scalar(
                select(func.count())
                .select_from(CareerTrainingSession)
                .where(CareerTrainingSession.career_player_id == created["id"])
            )
            == 1
        )
        decision = session.scalar(select(CareerDecision).where(CareerDecision.career_player_id == created["id"]))
        assert decision is not None
        assert decision.decision_type.value == "transfer"
        entries = session.scalars(
            select(PlayerCareerEntry)
            .where(PlayerCareerEntry.player_id == created["player_id"])
            .order_by(PlayerCareerEntry.created_at.asc())
        ).all()
        assert len(entries) == 2
        assert entries[0].end_on is not None
        active_contract = session.scalar(
            select(PlayerContract).where(
                PlayerContract.player_id == created["player_id"],
                PlayerContract.status == "active",
            )
        )
        assert active_contract is not None
        assert Decimal(active_contract.wage_amount) == Decimal("9500.00")

    retire_response = client.post(
        "/career/retire",
        headers=headers,
        json={"legacy_role": "hall_of_fame", "legacy_headline": "Career Pulse steps into legend"},
    )
    assert retire_response.status_code == 200, retire_response.text
    retired = retire_response.json()
    assert retired["status"] == "retired"
    assert retired["retired_at"] is not None
    assert retired["legacy_summary_json"]["hall_of_fame"] is True
    assert retired["legacy_summary_json"]["ai_player"] is True
    assert retired["legacy_summary_json"]["legacy_headline"] == "Career Pulse steps into legend"

    retired_get_response = client.get(f"/career/{user.id}")
    assert retired_get_response.status_code == 200, retired_get_response.text
    assert retired_get_response.json()["status"] == "retired"

    with app_session_factory() as session:
        legacy_record = session.scalar(
            select(CareerLegacyRecord).where(CareerLegacyRecord.career_player_id == created["id"])
        )
        assert legacy_record is not None
        assert legacy_record.legacy_role == "hall_of_fame"
        assert legacy_record.summary_json["ai_player"] is True
        assert (
            session.scalar(
                select(func.count())
                .select_from(PlayerContract)
                .where(
                    PlayerContract.player_id == created["player_id"],
                    PlayerContract.status == "active",
                )
            )
            == 0
        )


def test_real_world_sync_creates_mirror_match_with_manager_career_and_economy_outputs(client, app, app_session_factory):
    runtime = ensure_gtex_runtime(app)
    user, headers = _register_user(app_session_factory, label="mirror-sync")
    player_name = f"Mirror Star {uuid4().hex[:6]}"
    home_club = f"Lagos Comets {uuid4().hex[:4]}"
    away_club = f"Kano Kings {uuid4().hex[:4]}"
    _create_career_player(client, headers, player_name=player_name, current_club=home_club)

    _, sync_data, match = _sync_completed_mirror_match(
        client,
        headers,
        provider_name=f"manual-sync-{uuid4().hex[:6]}",
        career_user_id=user.id,
        player_name=player_name,
        home_club=home_club,
        away_club=away_club,
    )

    match_id = sync_data["mirrored_match_ids"][0]
    events_response = client.get("/real-world/events")
    assert events_response.status_code == 200, events_response.text
    mirrored_event = next(item for item in events_response.json() if item["mirror_match_id"] == match_id)
    assert mirrored_event["status"] == "completed"
    assert mirrored_event["influence_applied_at"] is not None

    assert match["id"] == match_id
    assert match["status"] == "completed"
    assert match["home_manager"]["id"]
    assert match["home_manager"]["tactical_style"] in {"attacking", "defensive", "balanced"}
    assert match["away_manager"]["formation_preferences"]
    assert match["commentary"]
    assert match["broadcast_package"]["headline"]
    assert match["news_article"]["title"]
    assert match["career_summary"]["player_name"] == player_name
    assert match["career_summary"]["side"] == "home"
    assert match["real_world_sync"]["mirror_match_id"] == match_id
    assert match["match_context"]["manager_intensity_score"] > 0
    assert match["match_context"]["career_side"] == "home"

    career_response = client.get(f"/career/{user.id}")
    assert career_response.status_code == 200, career_response.text
    career_payload = career_response.json()
    assert career_payload["career_stats"]["real_world_sync_hits"] >= 1
    assert career_payload["career_stats"]["appearances"] >= 1
    assert career_payload["prestige_score"] > 0

    with app_session_factory() as session:
        user_model = session.get(User, user.id)
        assert user_model is not None
        asset = runtime.creator_market.ensure_asset_for_user(session, user_model)
        assert asset.total_matches >= 1
        assert Decimal(asset.demand_score) > Decimal("0")
        stored_match = session.get(GtexMatch, match_id)
        assert stored_match is not None
        assert stored_match.metadata_json["mirror_source"] == "real_world_sync"


def test_manager_history_endpoint_exposes_tactical_identity_and_rivalry_snapshots(client, app, app_session_factory):
    ensure_gtex_runtime(app)
    user, headers = _register_user(app_session_factory, label="manager-history")
    player_name = f"Tactical Star {uuid4().hex[:6]}"
    home_club = f"Port Harcourt Waves {uuid4().hex[:4]}"
    away_club = f"Enugu Steel {uuid4().hex[:4]}"
    _create_career_player(client, headers, player_name=player_name, current_club=home_club)

    _, sync_data, match = _sync_completed_mirror_match(
        client,
        headers,
        provider_name=f"manager-sync-{uuid4().hex[:6]}",
        career_user_id=user.id,
        player_name=player_name,
        home_club=home_club,
        away_club=away_club,
    )

    manager_id = match["home_manager"]["id"]
    opponent_id = match["away_manager"]["id"]
    profile_response = client.get(f"/managers/{manager_id}")
    assert profile_response.status_code == 200, profile_response.text
    profile = profile_response.json()
    assert profile["gtex_ai_id"] == match["home_ai_id"]
    assert profile["formation_preferences"]
    assert profile["substitution_logic"]
    assert profile["tempo_control"]

    history_response = client.get(f"/managers/{manager_id}/history")
    assert history_response.status_code == 200, history_response.text
    history = history_response.json()
    entry = next(item for item in history if item["source_match_id"] == sync_data["mirrored_match_ids"][0])
    assert entry["opponent_manager_id"] == opponent_id
    assert entry["tactical_snapshot"]["tempo_control"] == profile["tempo_control"]
    assert entry["tactical_snapshot"]["formation_preferences"]
    assert entry["rivalry"] is not None
    assert entry["rivalry"]["meetings"] >= 1
    assert entry["rivalry"]["rivalry_score"] > 0


def test_completed_mirror_match_resimulation_is_idempotent_for_manager_history(client, app, app_session_factory):
    runtime = ensure_gtex_runtime(app)
    user, headers = _register_user(app_session_factory, label="idempotent-manager")
    player_name = f"Repeat Star {uuid4().hex[:6]}"
    home_club = f"Abuja Orbit {uuid4().hex[:4]}"
    away_club = f"Ibadan Forge {uuid4().hex[:4]}"
    _create_career_player(client, headers, player_name=player_name, current_club=home_club)

    _, sync_data, match = _sync_completed_mirror_match(
        client,
        headers,
        provider_name=f"idempotent-sync-{uuid4().hex[:6]}",
        career_user_id=user.id,
        player_name=player_name,
        home_club=home_club,
        away_club=away_club,
    )

    match_id = sync_data["mirrored_match_ids"][0]
    with app_session_factory() as session:
        before_count = session.scalar(
            select(func.count()).select_from(ManagerMatchHistory).where(ManagerMatchHistory.source_match_id == match_id)
        )
        stored_match = runtime.ai_leagues.simulate_match(session, match_id=match_id)
        session.commit()
        assert stored_match.id == match_id

    with app_session_factory() as session:
        after_count = session.scalar(
            select(func.count()).select_from(ManagerMatchHistory).where(ManagerMatchHistory.source_match_id == match_id)
        )
        stored_match = session.get(GtexMatch, match_id)
        assert stored_match is not None
        assert stored_match.home_score == match["home_score"]
        assert stored_match.away_score == match["away_score"]
        assert before_count == after_count == 2
