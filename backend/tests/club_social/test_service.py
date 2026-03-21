from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.club_social.service import ClubSocialService
from app.models.club_social import ClubChallenge
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.user import User
from app.services.competition_match_service import CompetitionMatchService


def _seed_match_context(session: Session) -> CompetitionMatch:
    competition = UserCompetition(
        id="competition-1",
        host_user_id="user-alpha",
        name="City Clash",
        format="league",
        visibility="public",
        status="live",
        start_mode="scheduled",
        currency="coin",
        metadata_json={},
    )
    round_ = CompetitionRound(
        id="round-1",
        competition_id=competition.id,
        round_number=1,
        stage="league",
        status="live",
        metadata_json={},
    )
    rule_set = CompetitionRuleSet(
        id="rules-1",
        competition_id=competition.id,
        format="league",
        min_participants=2,
        max_participants=20,
        league_win_points=3,
        league_draw_points=1,
        league_loss_points=0,
        league_tie_break_order=["points", "goal_diff", "goals_for"],
        cup_allowed_participant_sizes=[],
    )
    participants = [
        CompetitionParticipant(id="participant-1", competition_id=competition.id, club_id="club-alpha"),
        CompetitionParticipant(id="participant-2", competition_id=competition.id, club_id="club-bravo"),
    ]
    match = CompetitionMatch(
        id="match-1",
        competition_id=competition.id,
        round_id=round_.id,
        round_number=1,
        stage="final",
        home_club_id="club-alpha",
        away_club_id="club-bravo",
        status="in_progress",
        metadata_json={"view_count": 650, "gift_count": 42},
    )
    session.add_all([competition, round_, rule_set, match, *participants])
    session.commit()
    return match


def _seed_legacy_match_context(session: Session) -> CompetitionMatch:
    competition = UserCompetition(
        id="competition-legacy",
        host_user_id="user-alpha",
        name="Legacy Clubs Cup",
        format="league",
        visibility="public",
        status="live",
        start_mode="scheduled",
        currency="coin",
        metadata_json={},
    )
    round_ = CompetitionRound(
        id="round-legacy",
        competition_id=competition.id,
        round_number=1,
        stage="league",
        status="live",
        metadata_json={},
    )
    rule_set = CompetitionRuleSet(
        id="rules-legacy",
        competition_id=competition.id,
        format="league",
        min_participants=2,
        max_participants=20,
        league_win_points=3,
        league_draw_points=1,
        league_loss_points=0,
        league_tie_break_order=["points", "goal_diff", "goals_for"],
        cup_allowed_participant_sizes=[],
    )
    participants = [
        CompetitionParticipant(id="participant-legacy-1", competition_id=competition.id, club_id="legacy-club-a"),
        CompetitionParticipant(id="participant-legacy-2", competition_id=competition.id, club_id="legacy-club-b"),
    ]
    match = CompetitionMatch(
        id="match-legacy",
        competition_id=competition.id,
        round_id=round_.id,
        round_number=1,
        stage="league",
        home_club_id="legacy-club-a",
        away_club_id="legacy-club-b",
        status="in_progress",
        metadata_json={},
    )
    session.add_all([competition, round_, rule_set, match, *participants])
    session.commit()
    return match


def test_identity_metrics_and_status_transitions(session: Session, service: ClubSocialService) -> None:
    actor = session.get(User, "user-alpha")
    assert actor is not None
    challenge = service.create_challenge(
        actor=actor,
        club_id="club-alpha",
        title="Alpha calls out Charlie",
        message="Regional bragging rights are on the line.",
        stakes_text="Statewide bragging rights",
        target_club_id="club-charlie",
        visibility="public",
        country_code="US",
        region_name="Texas",
        city_name="Austin",
        competition_id=None,
        accept_by=None,
        scheduled_for=datetime.now(UTC) - timedelta(hours=1),
        metadata_json={},
    )
    challenge.accepted_club_id = "club-charlie"
    service._sync_challenge_status(challenge)
    service.record_share_event(
        challenge_id=challenge.id,
        link_id=None,
        link_code=None,
        actor_user_id=None,
        event_type="share",
        source_platform="social",
        country_code="US",
        metadata_json={},
    )
    metrics = service.refresh_identity_metrics(club_id="club-alpha")
    session.commit()

    assert challenge.status == "live"
    assert metrics.reputation_score == 260
    assert metrics.fan_count > 100
    assert metrics.media_popularity_score > 0
    assert metrics.club_valuation_minor > metrics.media_value_minor


def test_reactions_and_rivalry_accumulate_from_match_flow(session: Session, service: ClubSocialService) -> None:
    match = _seed_match_context(session)
    alpha_user = session.get(User, "user-alpha")
    bravo_user = session.get(User, "user-bravo")
    assert alpha_user is not None
    assert bravo_user is not None

    challenge = service.create_challenge(
        actor=alpha_user,
        club_id="club-alpha",
        title="Alpha vs Bravo Derby",
        message="Winner owns the city.",
        stakes_text="City bragging rights",
        target_club_id="club-bravo",
        visibility="public",
        country_code="US",
        region_name="California",
        city_name="Los Angeles",
        competition_id="competition-1",
        accept_by=None,
        scheduled_for=datetime.now(UTC) - timedelta(minutes=30),
        metadata_json={},
    )
    service.accept_challenge(
        actor=bravo_user,
        challenge_id=challenge.id,
        responding_club_id="club-bravo",
        message="Accepted.",
        scheduled_for=datetime.now(UTC) - timedelta(minutes=30),
        competition_id="competition-1",
        linked_match_id="match-1",
        metadata_json={},
    )
    session.commit()

    match_service = CompetitionMatchService(session)
    match_service.record_event(
        competition_id="competition-1",
        match_id="match-1",
        event_type="goal",
        minute=12,
        added_time=None,
        club_id="club-bravo",
        player_id=None,
        secondary_player_id=None,
        card_type=None,
        highlight=True,
        metadata_json={},
    )
    match_service.record_event(
        competition_id="competition-1",
        match_id="match-1",
        event_type="card",
        minute=67,
        added_time=None,
        club_id="club-alpha",
        player_id=None,
        secondary_player_id=None,
        card_type="red",
        highlight=True,
        metadata_json={},
    )
    session.commit()

    pre_completion_reactions = service.list_match_reactions("match-1")
    reaction_types = {item["reaction_type"] for item in pre_completion_reactions}
    assert "what_a_goal" in reaction_types
    assert "red_card_chaos" in reaction_types

    rule_set = session.get(CompetitionRuleSet, "rules-1")
    assert rule_set is not None
    match = session.get(CompetitionMatch, "match-1")
    assert match is not None
    match_service.complete_match(
        match=match,
        rule_set=rule_set,
        home_score=0,
        away_score=2,
        winner_club_id="club-bravo",
    )
    session.commit()

    rivalry = service.rivalry_detail(club_id="club-alpha", opponent_club_id="club-bravo")
    summary = rivalry["summary"]
    history = rivalry["history"][0]
    challenge_row = session.get(ClubChallenge, challenge.id)
    assert challenge_row is not None
    bravo_metrics = service.refresh_identity_metrics(club_id="club-bravo")
    session.commit()

    assert summary["matches_played"] == 1
    assert summary["losses"] == 1
    assert summary["challenge_matches"] == 1
    assert summary["high_view_matches"] == 1
    assert summary["high_gift_matches"] == 1
    assert summary["giant_killer_flag"] is True
    assert history["upset_flag"] is True
    assert history["final_flag"] is True
    assert challenge_row.status == "settled"
    assert challenge_row.winner_club_id == "club-bravo"
    final_reaction_types = {item["reaction_type"] for item in service.list_match_reactions("match-1")}
    assert "giant_killer_alert" in final_reaction_types
    assert bravo_metrics.challenge_history_json["wins"] >= 1


def test_match_completion_with_legacy_club_ids_does_not_break(session: Session) -> None:
    match = _seed_legacy_match_context(session)
    match_service = CompetitionMatchService(session)
    rule_set = session.get(CompetitionRuleSet, "rules-legacy")
    assert rule_set is not None

    updated = match_service.complete_match(
        match=match,
        rule_set=rule_set,
        home_score=1,
        away_score=0,
        winner_club_id="legacy-club-a",
    )
    session.commit()

    assert updated.status == "completed"
    social_service = ClubSocialService(session)
    assert social_service.list_match_reactions("match-legacy") == []
    assert social_service._rivalry_profile("legacy-club-a", "legacy-club-b") is None
