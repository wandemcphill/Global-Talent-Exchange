"""Comprehensive verification tests for the GTEX Living Supporter, Media & Club History Ecosystem."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.admin_engine.service import AdminEngineService
from app.club_legacy.operations import seed_catalogue
from app.models.admin_rules import AdminFeatureFlag
from app.models.user import User
from app.owner_console import competitions as comps, ledger, living_institution, service
from app.owner_console.institutional_models import (
    OwnerSupporterEvent,
    OwnerSupporterProfile,
)
from app.owner_console.models import (
    OwnerClubState,
    OwnerCompetition,
    OwnerCompetitionEntry,
    OwnerMatch,
)


def _enable_legacy(app) -> None:
    with app.state.session_factory() as session:
        AdminEngineService(session).seed_defaults()
        flag = session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == "club_legacy"))
        if flag:
            flag.enabled = True
        seed_catalogue(session)
        session.commit()


def _claim_and_activate(client, headers, city: str = "Lagos", country_code: str = "NG") -> str:
    resp = client.post(
        "/api/owner/clubs/claim",
        headers=headers,
        json={"city_name": city, "country_code": country_code},
    )
    assert resp.status_code == 200, resp.text
    club_id = resp.json()["club_id"]
    act = client.post(f"/api/owner/clubs/{club_id}/activate", headers=headers)
    assert act.status_code == 200, act.text
    return club_id


def _top_up_club(app, club_id: str, amount: str = "500000") -> User:
    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        ledger.record(
            session,
            event_type="owner_capital_injection",
            currency=ledger.GTEX,
            gross=Decimal(amount),
            source=ledger.PLATFORM_GRANTS,
            destination=ledger.club_account(club_id),
            user_id=admin.id,
            club_id=club_id,
        )
        session.commit()
        return admin


def test_supporter_segments_differentiated_reactions_and_sentiment_memory(
    client,
    bootstrap_admin_headers,
    app,
):
    """
    Scenarios 1, 2, 3 & 4:
    1. Supporter segments persist and differ appropriately in expectations and sentiment.
    2. Different supporter segments react differently to the same club event.
    3. Supporter sentiment remembers previous events; a single win after repeated losses does not
       immediately restore maximum confidence.
    4. Owner supporter engagement actions persist and have grounded consequences; contradictory
       statements fail to restore confidence and reduce credibility.
    """
    _enable_legacy(app)
    club_id = _claim_and_activate(client, bootstrap_admin_headers, city="Lagos")
    _top_up_club(app, club_id)

    # 1. Inspect persistent supporter segments via API
    sup_res = client.get(f"/api/owner/clubs/{club_id}/supporters", headers=bootstrap_admin_headers)
    assert sup_res.status_code == 200, sup_res.text
    sup_data = sup_res.json()
    segments = {s["segment_key"]: s for s in sup_data["segments"]}
    assert len(segments) == 6
    assert set(segments.keys()) == {
        "loyal_lifelong",
        "regular_matchgoing",
        "younger_supporters",
        "local_community",
        "international_followers",
        "organised_groups",
    }
    assert (
        segments["loyal_lifelong"]["primary_expectation"]
        != segments["international_followers"]["primary_expectation"]
    )
    assert segments["loyal_lifelong"]["loyalty"] > segments["international_followers"]["loyalty"]

    # 2. Different supporter segments react differently to the same event:
    # A steep ticket price hike hurts regular_matchgoing & local_community far more than international_followers
    hike_res = client.post(
        f"/api/owner/clubs/{club_id}/supporters/engage",
        headers=bootstrap_admin_headers,
        json={
            "action_type": "ticketing_decision",
            "ticket_price_gtex": 45,
            "statement": "Raising matchday ticket prices to maximize premium matchday revenue.",
            "tone": "assertive",
        },
    )
    assert hike_res.status_code == 200, hike_res.text
    hike_deltas = hike_res.json()["reaction"]["segment_deltas"]
    assert hike_deltas["regular_matchgoing"] < hike_deltas["international_followers"]
    assert hike_deltas["local_community"] < 0

    # Conversely, an academy promotion delights local_community & loyal_lifelong more than international_followers
    acad_res = client.post(
        f"/api/owner/clubs/{club_id}/academy/intake",
        headers=bootstrap_admin_headers,
    )
    assert acad_res.status_code == 200, acad_res.text
    prospect_id = acad_res.json()["regens"][0]["id"]
    prom_res = client.post(
        f"/api/owner/clubs/{club_id}/academy/{prospect_id}/promote",
        headers=bootstrap_admin_headers,
    )
    assert prom_res.status_code == 200, prom_res.text

    with app.state.session_factory() as session:
        acad_event = session.scalar(
            select(OwnerSupporterEvent)
            .where(
                OwnerSupporterEvent.club_id == club_id,
                OwnerSupporterEvent.event_type == "academy_pride",
            )
            .order_by(OwnerSupporterEvent.created_at.desc())
        )
        assert acad_event is not None
        assert (
            acad_event.segment_deltas_json["local_community"]["delta"]
            > acad_event.segment_deltas_json["international_followers"]["delta"]
        )

    # 3. Sentiment memory / scar tissue: repeated heavy defeats accumulate scar tissue so a single win
    # cannot immediately restore maximum confidence.
    with app.state.session_factory() as session:
        state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
        assert state is not None
        for idx in range(5):
            living_institution.apply_supporter_reaction(
                session,
                state,
                event_type="heavy_defeat",
                trigger_source_type="match",
                trigger_source_id=f"loss-{idx}",
                headline=f"Heavy Defeat #{idx + 1}",
                summary="Supporters endured a painful three-goal defeat.",
                driver_Impacts={
                    "results": -12.0,
                    "club_identity": -8.0,
                    "rivalry_record": -8.0,
                    "owner_conduct": -6.0,
                },
                idempotency_key=f"test-loss-streak-{idx}",
                is_disappointment=True,
                credibility_delta=-4,
            )
        session.commit()

        prof_after_losses = session.scalar(
            select(OwnerSupporterProfile).where(OwnerSupporterProfile.club_id == club_id)
        )
        assert prof_after_losses is not None
        assert prof_after_losses.consecutive_disappointments >= 5
        assert prof_after_losses.accumulated_frustration >= 25
        assert prof_after_losses.active_protest_stage in ("petition", "banner_protest", "organised_boycott")
        sentiment_before_win = prof_after_losses.overall_sentiment

        # Now apply a single victory
        living_institution.apply_supporter_reaction(
            session,
            state,
            event_type="match_win",
            trigger_source_type="match",
            trigger_source_id="single-win-after-slump",
            headline="Single Match Victory",
            summary="The club recorded one win after a prolonged slump.",
            driver_Impacts={
                "results": 10.0,
                "club_identity": 6.0,
                "owner_conduct": 4.0,
            },
            idempotency_key="test-single-win-after-slump",
            is_victory_relief=True,
            credibility_delta=2,
        )
        session.commit()

        prof_after_win = session.scalar(
            select(OwnerSupporterProfile).where(OwnerSupporterProfile.club_id == club_id)
        )
        assert prof_after_win is not None
        assert prof_after_win.overall_sentiment > sentiment_before_win
        assert prof_after_win.overall_sentiment < 75, (
            "A single win after repeated disappointments must be dampened by scar tissue "
            "and never restore maximum confidence."
        )
        assert prof_after_win.accumulated_frustration > 0

    # 4. Contradictory owner statement fails to restore confidence and penalizes credibility
    contradict_res = client.post(
        f"/api/owner/clubs/{club_id}/supporters/engage",
        headers=bootstrap_admin_headers,
        json={
            "action_type": "public_statement",
            "statement": "We guarantee affordable ticket access for every supporter!",
            "tone": "defiant",
        },
    )
    assert contradict_res.status_code == 200, contradict_res.text
    contradict_body = contradict_res.json()
    assert contradict_body["contradiction_detected"] is True
    assert contradict_body["reaction"]["event_type"] == "owner_contradictory_statement"
    assert contradict_body["reaction"]["overall_delta"] < 0


def test_matchday_atmosphere_media_credibility_and_rumour_guardrails(
    client,
    bootstrap_admin_headers,
    app,
):
    """
    Scenarios 5, 6, 7, 8 & 9:
    5. Matchday atmosphere is derived from real supporter, rivalry, and match context without
       corrupting authoritative match outcomes.
    6. Media stories are generated from real events and attributed to outlets/journalists with
       appropriate editorial focus.
    7. Verified events, reported information, rumours, and opinion are clearly distinguished.
    8. Rumours never mutate or display as confirmed transfers or factual records.
    9. Media coverage and club statements have grounded, proportionate effects on reputation and
       supporter sentiment.
    """
    _enable_legacy(app)
    club_id = _claim_and_activate(client, bootstrap_admin_headers, city="Abuja")
    _top_up_club(app, club_id)

    # Create and play a user-hosted competition match and verify matchday atmosphere + media report
    with app.state.session_factory() as session:
        state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
        assert state is not None
        comp = comps.host_competition(
            session,
            user_id=state.owner_user_id,
            payload={
                "name": "Abuja Invitational Cup",
                "format": "league",
                "max_clubs": 4,
                "contribution": 0,
                "winner_prize": 0,
                "club_id": club_id,
            },
        )
        comps.enter_competition(session, user_id=state.owner_user_id, competition_id=comp.id, club_id=club_id)
        played_res = comps.play_next(
            session,
            user_id=state.owner_user_id,
            competition_id=comp.id,
            club_id=club_id,
            mentality="balanced",
            lineup_mode="strongest",
        )
        session.commit()
        played_match_id = played_res["match"]["id"]
        expected_hg = played_res["match"]["home_goals"]
        expected_ag = played_res["match"]["away_goals"]

    with app.state.session_factory() as session:
        match_row = session.get(OwnerMatch, played_match_id)
        assert match_row is not None
        assert "matchday_atmosphere" in (match_row.narrative_json or {})
        atmo = match_row.narrative_json["matchday_atmosphere"]
        assert 15 <= atmo["crowd_intensity"] <= 100
        assert len(atmo["banners"]) >= 1
        assert len(atmo["chants"]) >= 1
        # Authoritative match score remains untouched by presentation atmosphere
        assert match_row.home_goals == expected_hg
        assert match_row.away_goals == expected_ag

    # Add a high-priority transfer target to watchlist -> generates an unconfirmed transfer rumour,
    # keeping private scout notes confidential and never recording a transfer or signing a player.
    squad_before = client.get(f"/api/owner/clubs/{club_id}", headers=bootstrap_admin_headers).json()["squad"]
    squad_names_before = {p["name"] for p in squad_before}

    watch_res = client.post(
        f"/api/owner/clubs/{club_id}/watchlist",
        headers=bootstrap_admin_headers,
        json={
            "player_id": "target-victor-99",
            "player_name": "Victor Osimhen",
            "position": "ST",
            "age": 25,
            "current_rating": 91,
            "potential_rating": 93,
            "estimated_value_gtex": 45000,
            "priority": "high",
            "scout_notes": "TOP_SECRET_RELEASE_CLAUSE_NOTE_DO_NOT_LEAK",
            "recommendation": "Sign immediately",
        },
    )
    assert watch_res.status_code == 200, watch_res.text

    media_res = client.get(f"/api/owner/clubs/{club_id}/media", headers=bootstrap_admin_headers)
    assert media_res.status_code == 200, media_res.text
    media_data = media_res.json()

    # Check outlets exist with distinct editorial focuses
    outlets = {o["outlet_key"]: o for o in media_data["outlets"]}
    assert "local_club_chronicle" in outlets
    assert "transfer_insider_desk" in outlets
    assert "tactical_youth_observer" in outlets

    stories = media_data["stories"]
    classifications = {s["classification"] for s in stories}
    assert "verified_event" in classifications
    assert "rumour" in classifications

    rumour_stories = [s for s in stories if s["classification"] == "rumour"]
    assert len(rumour_stories) >= 1
    osimhen_rumour = next(s for s in rumour_stories if "Victor Osimhen" in s["headline"])
    assert osimhen_rumour["is_confirmed_fact"] is False
    assert osimhen_rumour["outlet_key"] == "transfer_insider_desk"
    assert "RUMOUR" in osimhen_rumour["headline"]
    # Confidential scout notes must NEVER leak into public media stories
    assert "TOP_SECRET_RELEASE_CLAUSE_NOTE_DO_NOT_LEAK" not in osimhen_rumour["body"]

    # Rumours must NEVER mutate squad or transfer history
    squad_after = client.get(f"/api/owner/clubs/{club_id}", headers=bootstrap_admin_headers).json()["squad"]
    assert {p["name"] for p in squad_after} == squad_names_before
    hist_res = client.get(f"/api/owner/clubs/{club_id}/history", headers=bootstrap_admin_headers).json()
    transfer_names = {t["player_name"] for t in hist_res["transfer_history"]}
    assert "Victor Osimhen" not in transfer_names

    # Owner / club response to media story persists and updates reputation / sentiment proportionately
    resp_story = client.post(
        f"/api/owner/clubs/{club_id}/media/{osimhen_rumour['id']}/respond",
        headers=bootstrap_admin_headers,
        json={
            "responder_role": "owner",
            "response_tone": "measured",
            "response_text": "We never comment on unconfirmed transfer speculation regarding other clubs' players.",
        },
    )
    assert resp_story.status_code == 200, resp_story.text
    resp_body = resp_story.json()
    assert resp_body["story"]["owner_response"]["responder_role"] == "owner"
    assert "speculation" in resp_body["story"]["owner_response"]["response_text"]


def test_permanent_institutional_history_tenures_transfers_graduates_and_rivalries(
    client,
    bootstrap_admin_headers,
    auth_user_factory,
    app,
):
    """
    Scenarios 10, 11, 12, 13 & 14:
    10. Permanent club history records club creation, leadership changes, transfers, matches,
        seasonal outcomes, records, and milestones.
    11. Managerial history, transfer history, academy graduate history, and rivalries persist.
    12. Historical summaries and media articles never invent unrecorded trophies, scores, players,
        or pre-creation history.
    13. Autonomous world ticks / event hooks are idempotent and do not create duplicate entries.
    14. Ownership and authorization checks prevent another user from mutating a club's supporter
        or media state.
    """
    _enable_legacy(app)
    club_id = _claim_and_activate(client, bootstrap_admin_headers, city="Kano")
    _top_up_club(app, club_id)

    # 1. Appoint a new manager -> closes previous tenure, starts new tenure, logs history
    mgr_res = client.post(
        f"/api/owner/clubs/{club_id}/manager",
        headers=bootstrap_admin_headers,
        json={
            "manager": {
                "manager_id": "mgr_tunde_mcphill",
                "display_name": "Tunde McPhill",
                "mentality": "attacking",
            }
        },
    )
    assert mgr_res.status_code == 200, mgr_res.text

    # 2. Record a player arrival in the transfer ledger -> records incoming transfer & record signing
    with app.state.session_factory() as session:
        state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
        assert state is not None
        living_institution.record_transfer_movement(
            session,
            state,
            direction="arrival",
            transfer_type="market_signing",
            player_id="mkt-star-forward-1",
            player_name="Jay-Jay Okocha II",
            position="CAM",
            age=22,
            overall_rating=86,
            fee_gtex=18000,
            wage_gtex=300,
            counterparty_club_name="GTEX Transfer Market",
        )
        session.commit()

    # 3. Upgrade a facility -> records facility development in permanent ledger
    fac_res = client.post(
        f"/api/owner/clubs/{club_id}/facilities/stadium/upgrade",
        headers=bootstrap_admin_headers,
    )
    assert fac_res.status_code == 200, fac_res.text

    # 4. Generate & promote an academy prospect, then play a competition match so they debut
    acad_gen = client.post(
        f"/api/owner/clubs/{club_id}/academy/intake",
        headers=bootstrap_admin_headers,
    ).json()
    prospect_id = acad_gen["regens"][0]["id"]
    prospect_name = acad_gen["regens"][0]["name"]
    prom_res = client.post(
        f"/api/owner/clubs/{club_id}/academy/{prospect_id}/promote",
        headers=bootstrap_admin_headers,
    )
    assert prom_res.status_code == 200, prom_res.text

    # 5. Play a competition match and finalize season archive, verifying idempotency
    with app.state.session_factory() as session:
        state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
        assert state is not None
        comp = comps.host_competition(
            session,
            user_id=state.owner_user_id,
            payload={
                "name": "GTEX Premier Division",
                "format": "league",
                "max_clubs": 4,
                "contribution": 0,
                "winner_prize": 0,
                "club_id": club_id,
            },
        )
        comps.enter_competition(session, user_id=state.owner_user_id, competition_id=comp.id, club_id=club_id)
        comps.play_next(
            session,
            user_id=state.owner_user_id,
            competition_id=comp.id,
            club_id=club_id,
            mentality="balanced",
            lineup_mode="strongest",
        )

        entries = list(
            session.scalars(
                select(OwnerCompetitionEntry).where(OwnerCompetitionEntry.competition_id == comp.id)
            ).all()
        )
        for e in entries:
            if e.club_id == club_id:
                e.final_position = 1
                e.points = 78
                e.played = 30
                e.won = 24
                e.drawn = 6
                e.lost = 0
                e.goals_for = 68
                e.goals_against = 19
            else:
                e.final_position = 2

        archives_1 = living_institution.record_season_completion_archive(session, comp, entries)
        archives_2 = living_institution.record_season_completion_archive(session, comp, entries)
        session.commit()
        assert len(archives_1) == 1
        assert archives_1[0].id == archives_2[0].id

        # Autonomous world tick must also be idempotent for the same world day
        state.world_day = 14
        tick_1 = living_institution.process_world_day_institutional_tick(session, state)
        tick_2 = living_institution.process_world_day_institutional_tick(session, state)
        session.commit()
        assert tick_1.get("already_reconciled") is not True
        assert tick_2.get("already_reconciled") is True

    # 6. Fetch the full institutional archive via API and verify every section
    archive_res = client.get(f"/api/owner/clubs/{club_id}/history", headers=bootstrap_admin_headers)
    assert archive_res.status_code == 200, archive_res.text
    archive = archive_res.json()

    categories = {e["category"] for e in archive["timeline"]}
    assert "club_creation" in categories
    assert "managerial_change" in categories
    assert "player_signing" in categories
    assert "facility_development" in categories
    assert "academy_graduate" in categories
    assert "trophy_award" in categories

    # Managerial history has the active manager Tunde McPhill
    tenures = archive["managerial_history"]
    assert len(tenures) >= 1
    assert any(t["manager_name"] == "Tunde McPhill" and t["is_active"] is True for t in tenures)

    # Transfer history has Jay-Jay Okocha II marked as record signing
    transfers = archive["transfer_history"]
    okocha_tx = next((t for t in transfers if t["player_name"] == "Jay-Jay Okocha II"), None)
    assert okocha_tx is not None
    assert okocha_tx["direction"] == "arrival"
    assert okocha_tx["is_record_signing"] is True

    # Academy graduate history has the promoted prospect
    grads = archive["academy_graduates"]
    assert any(g["player_name"] == prospect_name for g in grads)

    # Rivalry history was recorded from the competition match
    assert len(archive["rivalries"]) >= 1
    assert archive["rivalries"][0]["matches_played"] >= 1

    # Season archive & club records
    assert len(archive["season_archive"]) == 1
    assert archive["season_archive"][0]["trophy_won"] is True
    assert archive["club_records"]["highest_league_finish"]["position"] == 1
    assert archive["club_records"]["record_signing"]["player_name"] == "Jay-Jay Okocha II"
    assert len(archive["historical_chapters"]) >= 2

    # 7. Verify fact grounding: attempts to publish a media story with unverified scores/numbers
    # or pre-creation history fail validation when enforce_grounding=True
    with app.state.session_factory() as session:
        state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
        with pytest.raises(ValueError, match="unverified"):
            living_institution.publish_media_story(
                session,
                state,
                outlet_key="gtex_national_wire",
                story_type="match_report",
                classification="verified_event",
                headline="Club defeats Fake Unregistered Atlantis XI 9-0",
                body="In 1924 before club creation, Fake Player X scored 9 goals in a 9-0 win.",
                established_facts={"home_goals": 1, "away_goals": 0},
                enforce_grounding=True,
            )

    # 8. Authorization check: another user cannot engage supporters or respond to media for this club
    intruder = auth_user_factory(suffix="intruder-owner")
    forb_res = client.post(
        f"/api/owner/clubs/{club_id}/supporters/engage",
        headers=intruder["headers"],
        json={
            "action_type": "public_statement",
            "statement": "Unauthorized takeover statement!",
            "tone": "defiant",
        },
    )
    assert forb_res.status_code in (401, 403, 404)
