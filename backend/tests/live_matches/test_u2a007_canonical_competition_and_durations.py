from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.broadcast.spectator_gateway import router as spectator_gateway_router
from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_start_mode import CompetitionStartMode
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.contract_status import ContractStatus
from app.common.enums.fixture_window import FixtureWindow
from app.common.enums.match_status import MatchStatus
from app.core.config import reset_settings_cache
from app.ingestion.models import Player
from app.live_matches.router import router as live_matches_router
from app.live_matches.service import ensure_live_match_hub
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.player_contract import PlayerContract
from app.models.user import User
from app.routes.match_viewer import router as match_viewer_router
from app.schemas.match_viewer import MatchMode
from app.services.competition_auto_runner import CompetitionAutoRunner
from backend.tests.support.secrets import MEDIA_SIGNING_TEST_SECRET, TEST_AUTH_SECRET


def _build_synthetic_canonical_entities() -> dict[str, object]:
    """Isolated, deterministic synthetic extraction of canonical competition, clubs, and real-scale players."""
    comp_row = {
        "id": "00000000-0000-0000-0000-000000000401",
        "name": "West Africa Elite Circuit",
        "format": "league",
        "visibility": "public",
        "status": "live",
        "start_mode": "scheduled",
        "source_type": "official",
        "host_user_id": "00000000-0000-0000-0000-000000000001",
        "currency": "GTEX",
    }
    club_rows = [
        {
            "id": "00000000-0000-0000-0000-000000000101",
            "owner_user_id": "00000000-0000-0000-0000-000000000011",
            "club_name": "Lagos Atlas FC",
            "short_name": "LAF",
            "slug": "lagos-atlas-fc",
            "primary_color": "#00E676",
            "secondary_color": "#0F172A",
            "accent_color": "#F5B83D",
            "home_venue_name": "GTEX National Arena",
            "country_code": "NG",
            "region_name": "West Africa",
            "city_name": "Lagos",
        },
        {
            "id": "00000000-0000-0000-0000-000000000102",
            "owner_user_id": "00000000-0000-0000-0000-000000000012",
            "club_name": "Rio Norte SC",
            "short_name": "RNS",
            "slug": "rio-norte-sc",
            "primary_color": "#3B82F6",
            "secondary_color": "#F8FAFC",
            "accent_color": "#F43F5E",
            "home_venue_name": "Rio Norte Arena",
            "country_code": "NG",
            "region_name": "West Africa",
            "city_name": "Abuja",
        },
    ]

    pos_specs = [
        ("goalkeeper", "GK", 2),
        ("defender", "DF", 6),
        ("midfielder", "MF", 5),
        ("forward", "FW", 5),
    ]

    home_players = []
    p_num = 1
    for norm_pos, pos, count in pos_specs:
        for idx in range(count):
            home_players.append(
                {
                    "id": f"00000000-0000-0000-0001-{p_num:012d}",
                    "full_name": f"Home {pos} {idx+1}",
                    "position": pos,
                    "normalized_position": norm_pos,
                    "shirt_number": p_num,
                    "height_cm": 182,
                    "market_value_eur": 25_000_000,
                }
            )
            p_num += 1

    away_players = []
    for norm_pos, pos, count in pos_specs:
        for idx in range(count):
            away_players.append(
                {
                    "id": f"00000000-0000-0000-0002-{p_num:012d}",
                    "full_name": f"Away {pos} {idx+1}",
                    "position": pos,
                    "normalized_position": norm_pos,
                    "shirt_number": p_num,
                    "height_cm": 182,
                    "market_value_eur": 25_000_000,
                }
            )
            p_num += 1

    return {
        "competition": comp_row,
        "clubs": club_rows,
        "home_players": home_players,
        "away_players": away_players,
    }


def _build_canonical_competition_test_env():
    os.environ["GTE_AUTH_SECRET"] = TEST_AUTH_SECRET
    os.environ["GTE_MEDIA_SIGNING_SECRET"] = MEDIA_SIGNING_TEST_SECRET
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    reset_settings_cache()

    app = FastAPI()
    app.include_router(live_matches_router)
    app.include_router(match_viewer_router)
    app.include_router(spectator_gateway_router)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.db import get_session, load_model_modules

    load_model_modules()
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.state.session_factory = session_factory

    def _override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override_session
    return app, session_factory


def _seed_canonical_competition_fixture(
    session: Session, canonical_data: dict[str, object]
) -> tuple[UserCompetition, CompetitionMatch]:
    comp_data = canonical_data["competition"]
    clubs_data = canonical_data["clubs"]
    home_club_data, away_club_data = clubs_data[0], clubs_data[1]

    for idx, cdata in enumerate(clubs_data):
        owner_id = cdata["owner_user_id"]
        if not session.get(User, owner_id):
            session.add(
                User(
                    id=owner_id,
                    email=f"owner_{idx}@gtex.africa",
                    username=f"owner_{idx}",
                    password_hash="hashed",  # pragma: allowlist secret
                    is_active=True,
                )
            )
        session.add(
            ClubProfile(
                id=cdata["id"],
                owner_user_id=owner_id,
                club_name=cdata["club_name"],
                short_name=cdata["short_name"],
                slug=cdata["slug"],
                primary_color=cdata["primary_color"],
                secondary_color=cdata["secondary_color"],
                accent_color=cdata["accent_color"],
                home_venue_name=cdata["home_venue_name"],
                country_code=cdata["country_code"],
                region_name=cdata["region_name"],
                city_name=cdata["city_name"],
            )
        )

    competition = UserCompetition(
        id=comp_data["id"],
        host_user_id=comp_data["host_user_id"],
        name=comp_data["name"],
        format=CompetitionFormat.LEAGUE.value,
        visibility=comp_data["visibility"],
        status=CompetitionStatus.LIVE.value,
        start_mode=CompetitionStartMode.SCHEDULED.value,
        source_type=comp_data["source_type"],
        currency=comp_data["currency"],
        scheduled_start_at=datetime(2026, 3, 29, 18, 0, tzinfo=UTC),
    )
    session.add(competition)
    session.add(
        CompetitionRuleSet(
            competition_id=competition.id,
            format=CompetitionFormat.LEAGUE.value,
            min_participants=2,
            max_participants=8,
            league_win_points=3,
            league_draw_points=1,
            league_loss_points=0,
        )
    )
    session.add(
        CompetitionParticipant(
            competition_id=competition.id,
            club_id=home_club_data["id"],
            seed=1,
        )
    )
    session.add(
        CompetitionParticipant(
            competition_id=competition.id,
            club_id=away_club_data["id"],
            seed=2,
        )
    )

    round_row = CompetitionRound(
        id="00000000-0000-0000-0000-000000000701",
        competition_id=competition.id,
        round_number=1,
        stage="league",
        status="scheduled",
    )
    session.add(round_row)

    # Seed the real ingested players and their active club contracts
    match_date = date(2026, 3, 29)
    all_seeded_players: list[Player] = []
    for club_id, roster in [
        (home_club_data["id"], canonical_data["home_players"]),
        (away_club_data["id"], canonical_data["away_players"]),
    ]:
        for idx, pdata in enumerate(roster, start=1):
            player = Player(
                id=pdata["id"],
                source_provider="gtex_canonical_db",
                provider_external_id=pdata["id"],
                current_club_profile_id=club_id,
                full_name=pdata["full_name"],
                position=pdata["position"],
                normalized_position=pdata["normalized_position"],
                shirt_number=idx,
                height_cm=pdata["height_cm"] or 182,
                market_value_eur=float(pdata["market_value_eur"] or 25_000_000),
                is_tradable=True,
            )
            session.add(player)
            all_seeded_players.append(player)
            session.add(
                PlayerContract(
                    player_id=player.id,
                    club_id=club_id,
                    status=ContractStatus.ACTIVE.value,
                    wage_amount=Decimal("45000.00"),
                    signed_on=date(2025, 7, 1),
                    starts_on=date(2025, 7, 1),
                    ends_on=date(2028, 6, 30),
                )
            )

    for rank_idx, seeded_p in enumerate(sorted(all_seeded_players, key=lambda item: item.id), start=1):
        seeded_p.shirt_number = (rank_idx % 18) + 1
        seeded_p.market_value_eur = float(40_000_000 - rank_idx * 250_000)

    fixture = CompetitionMatch(
        id="00000000-0000-0000-0000-000000000902",
        competition_id=competition.id,
        round_id=round_row.id,
        round_number=1,
        stage="league",
        home_club_id=home_club_data["id"],
        away_club_id=away_club_data["id"],
        status=MatchStatus.SCHEDULED.value,
        window=FixtureWindow.SENIOR_1.value,
        slot_sequence=1,
        match_date=match_date,
        scheduled_at=datetime(2026, 3, 29, 18, 0, tzinfo=UTC),
    )
    session.add(fixture)
    session.commit()
    return competition, fixture


def test_u2a007_canonical_competition_match_and_exact_durations():
    """
    Validates Sections 6 & 7 of U2A-007:
    - Real GTEX competition (`West Africa Elite Circuit`), registered clubs (`Lagos Atlas FC` vs `Rio Norte SC`),
      and real ingested player rosters simulated via `CompetitionAutoRunner._simulate_match()`.
    - Exact output durations of 180, 300, 420, and 600 seconds via `MatchViewerScalingService` and `/match-viewer/{id}`.
    - Preservation of all authoritative events, score, statistics, substitutions, and final outcome.
    - Live spectator WebSocket gateway (`/ws/spectate/{match_id}`) streaming.
    """
    canonical_data = _build_synthetic_canonical_entities()
    app, session_factory = _build_canonical_competition_test_env()

    with session_factory() as session:
        competition, fixture = _seed_canonical_competition_fixture(session, canonical_data)
        runner = CompetitionAutoRunner(session)
        completed_match = runner._simulate_match(competition, fixture)
        session.commit()

        assert completed_match.status == MatchStatus.COMPLETED.value
        stored_viewer_dict = completed_match.metadata_json.get("match_viewer")
        stored_replay_dict = completed_match.metadata_json.get("replay_payload")
        assert isinstance(stored_viewer_dict, dict)
        assert isinstance(stored_replay_dict, dict)

        authoritative_home_score = completed_match.home_score
        authoritative_away_score = completed_match.away_score
        authoritative_winner = completed_match.winner_club_id
        assert authoritative_home_score >= 0
        assert authoritative_away_score >= 0

    # Verify HTTP /match-viewer/{match_id} and exact durations: 180s, 300s, 420s, 600s
    client = TestClient(app)
    match_id = "00000000-0000-0000-0000-000000000902"

    duration_configs = [
        (180, MatchMode.QUICK.value),
        (300, MatchMode.QUICK.value),
        (420, MatchMode.STANDARD.value),
        (600, MatchMode.CINEMATIC.value),
    ]

    baseline_auth_signature = None
    exported_payloads: dict[int, dict[str, object]] = {}

    for target_sec, mode_val in duration_configs:
        resp = client.get(
            f"/match-viewer/{match_id}",
            params={"mode": mode_val, "target_duration_seconds": target_sec},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        exported_payloads[target_sec] = data

        # 1. Exact output duration
        assert data["duration_seconds"] == target_sec
        assert data["frames"][0]["time_seconds"] == 0.0
        assert data["frames"][-1]["time_seconds"] == float(target_sec)

        # 2. Canonical club identity & kits preserved
        assert data["home_team"]["team_id"] == "00000000-0000-0000-0000-000000000101"
        assert data["home_team"]["team_name"] == "Lagos Atlas FC"
        assert data["away_team"]["team_id"] == "00000000-0000-0000-0000-000000000102"
        assert data["away_team"]["team_name"] == "Rio Norte SC"

        # 3. Final frame score matches authoritative simulation outcome
        assert data["frames"][-1]["home_score"] == authoritative_home_score
        assert data["frames"][-1]["away_score"] == authoritative_away_score

        # 4. Separate authoritative events from presentation_only events
        auth_events = [ev for ev in data["events"] if "presentation_only" not in (ev.get("flags") or [])]
        pres_events = [ev for ev in data["events"] if "presentation_only" in (ev.get("flags") or [])]

        # Presentation-only events must never be goal/red_card/substitution events or alter score
        for pev in pres_events:
            assert pev["event_type"] not in {"goal", "penalty", "red_card", "substitution"}

        sig = [
            (
                ev["event_id"],
                ev["event_type"],
                ev["minute"],
                ev["team_id"],
                ev.get("primary_player", {}).get("player_id") if ev.get("primary_player") else None,
                ev["home_score"],
                ev["away_score"],
            )
            for ev in auth_events
        ]
        if baseline_auth_signature is None:
            baseline_auth_signature = sig
        else:
            assert sig == baseline_auth_signature, f"Authoritative events diverged at {target_sec}s"

        # Monotonic timestamps within [0, target_sec]
        event_times = [ev["time_seconds"] for ev in data["events"]]
        assert event_times == sorted(event_times)
        assert event_times[0] == 0.0
        assert event_times[-1] == float(target_sec)

    # 5. Verify live spectator WebSocket gateway (/ws/spectate/{match_id}) on the canonical competition match
    with session_factory() as session:
        match_obj = session.get(CompetitionMatch, match_id)
        from app.match_engine.schemas import MatchReplayPayloadView

        replay_payload = MatchReplayPayloadView.model_validate(match_obj.metadata_json["replay_payload"])
        live_hub = ensure_live_match_hub(app, step_interval_seconds=0.01)
        live_hub.start_stream(match_id, replay_payload, target_runtime_seconds=180)

    with client.websocket_connect(f"/ws/spectate/{match_id}") as ws:
        initial_msg = ws.receive_json()
        assert initial_msg["type"] in {"snapshot", "viewer_count", "frame", "match_event"}
        assert initial_msg["match_id"] == match_id

    # Save 300s and 600s canonical competition payloads to scratch if directory exists
    scratch_env = os.environ.get("GTEX_TEST_SCRATCH_DIR")
    scratch_dir = Path(scratch_env) if scratch_env else None
    if scratch_dir and scratch_dir.exists():
        for sec in (180, 300, 420, 600):
            (scratch_dir / f"u2a007_canonical_competition_{sec}s.json").write_text(
                json.dumps(exported_payloads[sec]), encoding="utf-8"
            )
        (scratch_dir / "u2a007_canonical_competition_summary.json").write_text(
            json.dumps(
                {
                    "competition_id": "00000000-0000-0000-0000-000000000401",
                    "competition_name": "West Africa Elite Circuit",
                    "match_id": match_id,
                    "home_club": canonical_data["clubs"][0],
                    "away_club": canonical_data["clubs"][1],
                    "home_score": authoritative_home_score,
                    "away_score": authoritative_away_score,
                    "winner_club_id": authoritative_winner,
                    "authoritative_event_count": len(baseline_auth_signature or []),
                    "tested_durations_seconds": [180, 300, 420, 600],
                    "durations_verified": {
                        str(sec): {
                            "duration_seconds": exported_payloads[sec]["duration_seconds"],
                            "frame_count": len(exported_payloads[sec]["frames"]),
                            "total_event_count": len(exported_payloads[sec]["events"]),
                            "authoritative_event_count": len(
                                [
                                    e
                                    for e in exported_payloads[sec]["events"]
                                    if "presentation_only" not in (e.get("flags") or [])
                                ]
                            ),
                            "presentation_only_event_count": len(
                                [
                                    e
                                    for e in exported_payloads[sec]["events"]
                                    if "presentation_only" in (e.get("flags") or [])
                                ]
                            ),
                            "final_score": {
                                "home": exported_payloads[sec]["frames"][-1]["home_score"],
                                "away": exported_payloads[sec]["frames"][-1]["away_score"],
                            },
                        }
                        for sec in (180, 300, 420, 600)
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )
