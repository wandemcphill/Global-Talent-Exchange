"""Admin tooling: verification ladder, moderation, correction and audit.

These tests run the real pipeline against real canonical rows (players,
matches, match stats) rather than pre-seeded scores, so they also cover the
projection from `ingestion_*` into ranking inputs.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import UserRole
from app.talent.admin_service import TalentAdminService, resolve_effective_tier
from app.talent.constants import (
    ModerationState,
    VERIFICATION_TIER_SCORE,
    VerificationDecision,
    VerificationTier,
    VisibilityState,
)
from app.talent.models import TalentProfile, TalentRankingSnapshot, TalentVerificationRecord
from app.talent.service import TalentExchangeService

from .conftest import (
    REFERENCE_TODAY,
    days_before,
    make_club,
    make_competition,
    make_match,
    make_match_stat,
    make_player,
    make_user,
)


@pytest.fixture()
def admin_user(session: Session, identity):
    admin = make_user(session, username="talent_admin", role=UserRole.ADMIN)
    session.commit()
    identity.admin = admin
    identity.user = admin
    return admin


@pytest.fixture()
def seeded_player(session: Session):
    """A player with a real, three-season competitive record."""

    competition = make_competition(session, key="prem", strength=85.0)
    home = make_club(session, key="home", competition=competition)
    away = make_club(session, key="away", competition=competition)
    player = make_player(
        session,
        key="record",
        full_name="Ibrahim Sesay",
        position="CM",
        date_of_birth=date(2003, 4, 2),
        club=home,
    )
    for index in range(14):
        match = make_match(
            session,
            key=f"m{index:02d}",
            competition=competition,
            home_club=home,
            away_club=away,
            kickoff=days_before(30 + index * 14),
        )
        make_match_stat(
            session,
            key=f"s{index:02d}",
            player=player,
            match=match,
            minutes=90,
            rating=7.2,
            goals=1 if index % 3 == 0 else 0,
        )
    session.commit()
    return player


@pytest.fixture()
def profile(session: Session, seeded_player) -> TalentProfile:
    service = TalentExchangeService(session, today=REFERENCE_TODAY)
    row = service.sync_profile_from_player(seeded_player.id)
    row.visibility_state = VisibilityState.PUBLISHED.value
    session.commit()
    service.recompute_ranking(seeded_player.id, as_of=REFERENCE_TODAY)
    session.commit()
    return row


# ----------------------------------------------------------------------
# Profile sync from canonical rows
# ----------------------------------------------------------------------


def test_sync_copies_canonical_facts_without_inventing_any(session: Session, seeded_player) -> None:
    service = TalentExchangeService(session, today=REFERENCE_TODAY)
    row = service.sync_profile_from_player(seeded_player.id)
    session.commit()

    assert row.display_name == "Ibrahim Sesay"
    assert row.position_code == "CM"
    assert row.date_of_birth == date(2003, 4, 2)
    assert row.age_years == 23
    assert row.preferred_foot == "right"
    # Nothing was fabricated: a brand new profile is a draft with no attributes
    # and no verification.
    assert row.visibility_state == VisibilityState.DRAFT.value
    assert row.verification_tier == VerificationTier.UNVERIFIED.value
    assert row.technical_attributes_json == {}


def test_sync_is_idempotent(session: Session, seeded_player) -> None:
    service = TalentExchangeService(session, today=REFERENCE_TODAY)
    first = service.sync_profile_from_player(seeded_player.id)
    session.commit()
    second = service.sync_profile_from_player(seeded_player.id)
    session.commit()

    assert first.id == second.id
    assert session.query(TalentProfile).count() == 1


def test_sync_of_an_unknown_player_is_a_not_found(session: Session) -> None:
    from app.talent.service import TalentNotFoundError

    with pytest.raises(TalentNotFoundError):
        TalentExchangeService(session).sync_profile_from_player("nope")


# ----------------------------------------------------------------------
# Ranking persistence
# ----------------------------------------------------------------------


def test_recompute_persists_lineage_and_denormalised_scores(session: Session, profile: TalentProfile) -> None:
    snapshot = session.query(TalentRankingSnapshot).one()

    assert snapshot.player_id == profile.player_id
    assert snapshot.as_of == REFERENCE_TODAY
    assert snapshot.inputs_digest
    assert len(snapshot.components_json) == 8
    assert profile.composite_score == snapshot.composite_score
    assert profile.ranking_inputs_digest == snapshot.inputs_digest
    assert profile.ranking_sample_size == 14


def test_recompute_on_the_same_day_updates_in_place(session: Session, profile: TalentProfile) -> None:
    service = TalentExchangeService(session, today=REFERENCE_TODAY)
    first = service.recompute_ranking(profile.player_id, as_of=REFERENCE_TODAY)
    session.commit()
    second = service.recompute_ranking(profile.player_id, as_of=REFERENCE_TODAY)
    session.commit()

    assert session.query(TalentRankingSnapshot).count() == 1
    assert first.composite_score == second.composite_score
    assert first.inputs_digest == second.inputs_digest


def test_recompute_on_a_later_date_keeps_the_earlier_snapshot(session: Session, profile: TalentProfile) -> None:
    service = TalentExchangeService(session)
    service.recompute_ranking(profile.player_id, as_of=REFERENCE_TODAY + timedelta(days=1))
    session.commit()

    assert session.query(TalentRankingSnapshot).count() == 2


def test_ranking_endpoint_returns_the_persisted_explanation(client: TestClient, profile: TalentProfile) -> None:
    response = client.get(f"/talent/{profile.player_id}/ranking")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["config_version"] == "talent_rank_v1"
    assert len(payload["components"]) == 8
    assert all(component["explanation"] for component in payload["components"])
    assert payload["composite_score"] == round(payload["base_score"] + payload["adjustments_total"], 2)


def test_competition_level_is_derived_from_the_competition_row(session: Session) -> None:
    from app.talent.service import derive_competition_level

    assert derive_competition_level(None) == "unknown"
    assert derive_competition_level(make_competition(session, key="elite", strength=95.0)) == "elite"
    assert derive_competition_level(make_competition(session, key="low", strength=30.0)) == "semi_pro"
    assert derive_competition_level(make_competition(session, key="youth", strength=90.0, age_bracket="U19")) == "youth"


# ----------------------------------------------------------------------
# Verification ladder
# ----------------------------------------------------------------------


def test_a_profile_existing_grants_no_verification(session: Session, profile: TalentProfile) -> None:
    assert profile.verification_tier == VerificationTier.UNVERIFIED.value
    assert session.query(TalentVerificationRecord).count() == 0


def test_granting_a_tier_records_an_auditable_decision(
    client: TestClient, session: Session, profile: TalentProfile, admin_user
) -> None:
    response = client.post(
        f"/admin/talent/{profile.player_id}/verification",
        json={
            "tier": "identity_verified",
            "decision": "granted",
            "evidence_kind": "federation_registry",
            "evidence_reference": "REVIEW-4821",
            "reviewer_notes": "Registry entry matched.",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["profile"]["verification_tier"] == "identity_verified"

    record = session.query(TalentVerificationRecord).one()
    assert record.decided_by_user_id == admin_user.id
    assert record.evidence_reference == "REVIEW-4821"
    assert record.decided_at is not None


def test_tiers_stack_and_the_highest_live_grant_wins(client: TestClient, profile: TalentProfile, admin_user) -> None:
    for tier in ("identity_verified", "profile_verified", "credentials_verified"):
        response = client.post(
            f"/admin/talent/{profile.player_id}/verification",
            json={"tier": tier, "decision": "granted"},
        )
        assert response.status_code == 200, response.text

    assert response.json()["profile"]["verification_tier"] == "credentials_verified"


def test_revocation_drops_back_to_the_next_live_tier(client: TestClient, profile: TalentProfile, admin_user) -> None:
    client.post(
        f"/admin/talent/{profile.player_id}/verification",
        json={"tier": "identity_verified", "decision": "granted"},
    )
    client.post(
        f"/admin/talent/{profile.player_id}/verification",
        json={"tier": "credentials_verified", "decision": "granted"},
    )
    revoked = client.post(
        f"/admin/talent/{profile.player_id}/verification",
        json={"tier": "credentials_verified", "decision": "revoked", "reviewer_notes": "Letter withdrawn."},
    )

    assert revoked.json()["profile"]["verification_tier"] == "identity_verified"


def test_an_expired_grant_stops_counting(session: Session, profile: TalentProfile, admin_user) -> None:
    service = TalentAdminService(session, today=REFERENCE_TODAY)
    service.record_verification(
        profile.player_id,
        actor=admin_user,
        tier=VerificationTier.PROFILE_VERIFIED,
        expires_at=date(2020, 1, 1),
    )
    session.commit()

    assert profile.verification_tier == VerificationTier.UNVERIFIED.value


def test_effective_tier_ignores_rejected_decisions() -> None:
    granted = TalentVerificationRecord(
        profile_id="p",
        player_id="x",
        tier=VerificationTier.IDENTITY_VERIFIED.value,
        decision=VerificationDecision.GRANTED.value,
        id="1",
    )
    rejected = TalentVerificationRecord(
        profile_id="p",
        player_id="x",
        tier=VerificationTier.STAFF_VERIFIED.value,
        decision=VerificationDecision.REJECTED.value,
        id="2",
    )

    assert resolve_effective_tier([granted, rejected]) == VerificationTier.IDENTITY_VERIFIED.value


def test_granting_the_unverified_tier_is_rejected(client: TestClient, profile: TalentProfile, admin_user) -> None:
    response = client.post(
        f"/admin/talent/{profile.player_id}/verification",
        json={"tier": "unverified", "decision": "granted"},
    )
    assert response.status_code == 422


def test_verification_change_immediately_moves_the_ranking(
    client: TestClient, session: Session, profile: TalentProfile, admin_user
) -> None:
    before = profile.composite_score

    client.post(
        f"/admin/talent/{profile.player_id}/verification",
        json={"tier": "staff_verified", "decision": "granted"},
    )
    session.expire_all()
    after = session.get(TalentProfile, profile.id)

    assert after.verification_tier == VerificationTier.STAFF_VERIFIED.value
    assert after.composite_score > before
    assert after.composite_score - before == pytest.approx(
        VERIFICATION_TIER_SCORE[VerificationTier.STAFF_VERIFIED.value] * 0.04, abs=0.05
    )


def test_verification_history_is_readable_by_admins(client: TestClient, profile: TalentProfile, admin_user) -> None:
    client.post(
        f"/admin/talent/{profile.player_id}/verification",
        json={"tier": "identity_verified", "decision": "granted", "evidence_kind": "club_letter"},
    )

    response = client.get(f"/admin/talent/{profile.player_id}/verification")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["current_tier"] == "identity_verified"
    assert payload["records"][0]["evidence_kind"] == "club_letter"


# ----------------------------------------------------------------------
# Visibility, moderation, featuring
# ----------------------------------------------------------------------


def test_suspension_requires_a_reason_and_hides_the_profile(
    client: TestClient, profile: TalentProfile, admin_user, identity
) -> None:
    missing_reason = client.post(
        f"/admin/talent/{profile.player_id}/visibility", json={"visibility_state": "suspended"}
    )
    assert missing_reason.status_code == 400

    suspended = client.post(
        f"/admin/talent/{profile.player_id}/visibility",
        json={"visibility_state": "suspended", "reason": "Impersonation report upheld."},
    )
    assert suspended.status_code == 200, suspended.text

    identity.user = None
    assert client.get(f"/talent/{profile.player_id}").status_code == 404


def test_moderation_flag_and_clear_round_trip(
    client: TestClient, session: Session, profile: TalentProfile, admin_user
) -> None:
    flagged = client.post(
        f"/admin/talent/{profile.player_id}/moderation",
        json={"action": "flag", "reason": "Disputed club history.", "internal_notes": "Awaiting club reply."},
    )
    assert flagged.json()["profile"]["moderation_state"] == ModerationState.FLAGGED.value
    assert flagged.json()["profile"]["internal_notes"] == "Awaiting club reply."

    cleared = client.post(f"/admin/talent/{profile.player_id}/moderation", json={"action": "clear_flag"})
    assert cleared.json()["profile"]["moderation_state"] == ModerationState.CLEAR.value


def test_restricted_profiles_drop_out_of_discovery(
    client: TestClient, profile: TalentProfile, admin_user, identity
) -> None:
    client.post(
        f"/admin/talent/{profile.player_id}/moderation",
        json={"action": "flag", "moderation_state": "restricted", "reason": "Under review."},
    )

    identity.user = None
    payload = client.get("/talent/search").json()
    assert payload["items"] == []


def test_suspend_then_restore(client: TestClient, profile: TalentProfile, admin_user, identity) -> None:
    client.post(
        f"/admin/talent/{profile.player_id}/moderation",
        json={"action": "suspend", "reason": "Duplicate profile."},
    )
    restored = client.post(f"/admin/talent/{profile.player_id}/moderation", json={"action": "restore"})

    assert restored.json()["profile"]["visibility_state"] == VisibilityState.PUBLISHED.value
    assert restored.json()["profile"]["suspension_reason"] is None

    identity.user = None
    assert client.get(f"/talent/{profile.player_id}").status_code == 200


def test_only_published_profiles_can_be_featured(client: TestClient, profile: TalentProfile, admin_user) -> None:
    client.post(f"/admin/talent/{profile.player_id}/visibility", json={"visibility_state": "hidden"})
    refused = client.post(f"/admin/talent/{profile.player_id}/feature", json={"is_featured": True, "featured_rank": 1})
    assert refused.status_code == 400

    client.post(f"/admin/talent/{profile.player_id}/visibility", json={"visibility_state": "published"})
    accepted = client.post(f"/admin/talent/{profile.player_id}/feature", json={"is_featured": True, "featured_rank": 1})
    assert accepted.status_code == 200
    assert accepted.json()["profile"]["is_featured"] is True


# ----------------------------------------------------------------------
# Correction
# ----------------------------------------------------------------------


def test_correction_updates_facts_and_re_derives_the_score(
    client: TestClient, session: Session, profile: TalentProfile, admin_user
) -> None:
    before = profile.composite_score

    response = client.post(
        f"/admin/talent/{profile.player_id}/correction",
        json={
            "technical_attributes": {
                "passing": 90.0,
                "first_touch": 88.0,
                "ball_control": 86.0,
                "dribbling": 84.0,
                "finishing": 70.0,
                "crossing": 72.0,
            },
            "reason": "Club submitted a verified attribute assessment.",
        },
    )

    assert response.status_code == 200, response.text
    session.expire_all()
    after = session.get(TalentProfile, profile.id)
    assert after.technical_attributes_json["passing"] == 90.0
    assert after.composite_score > before


def test_correction_rejects_unknown_attribute_keys(client: TestClient, profile: TalentProfile, admin_user) -> None:
    response = client.post(
        f"/admin/talent/{profile.player_id}/correction",
        json={"technical_attributes": {"vibes": 99.0}},
    )
    assert response.status_code == 400


def test_correction_rejects_an_empty_payload(client: TestClient, profile: TalentProfile, admin_user) -> None:
    assert client.post(f"/admin/talent/{profile.player_id}/correction", json={}).status_code == 400


def test_correction_validates_against_the_bounded_vocabulary(
    client: TestClient, profile: TalentProfile, admin_user
) -> None:
    assert client.post(f"/admin/talent/{profile.player_id}/correction", json={"position_code": "QB"}).status_code == 422
    assert (
        client.post(f"/admin/talent/{profile.player_id}/correction", json={"tactical_roles": ["libero"]}).status_code
        == 422
    )


def test_a_correction_survives_the_next_ingestion_sync(
    client: TestClient, session: Session, profile: TalentProfile, seeded_player, admin_user
) -> None:
    client.post(
        f"/admin/talent/{profile.player_id}/correction",
        json={"display_name": "Ibrahim A. Sesay", "reason": "Legal name."},
    )
    session.expire_all()

    TalentExchangeService(session, today=REFERENCE_TODAY).sync_profile_from_player(seeded_player.id)
    session.commit()
    session.expire_all()

    assert session.get(TalentProfile, profile.id).display_name == "Ibrahim A. Sesay"


def test_there_is_no_way_for_an_admin_to_write_a_score_directly(
    client: TestClient, profile: TalentProfile, admin_user
) -> None:
    response = client.post(f"/admin/talent/{profile.player_id}/correction", json={"composite_score": 99.0})
    assert response.status_code == 422


# ----------------------------------------------------------------------
# Audit
# ----------------------------------------------------------------------


def test_every_admin_action_is_written_to_the_moderation_log(
    client: TestClient, profile: TalentProfile, admin_user
) -> None:
    client.post(
        f"/admin/talent/{profile.player_id}/verification",
        json={"tier": "identity_verified", "decision": "granted"},
    )
    client.post(
        f"/admin/talent/{profile.player_id}/moderation",
        json={"action": "flag", "reason": "Spot check."},
    )
    client.post(f"/admin/talent/{profile.player_id}/correction", json={"headline": "Box-to-box midfielder"})

    response = client.get(f"/admin/talent/{profile.player_id}/moderation-log")

    assert response.status_code == 200, response.text
    entries = response.json()["entries"]
    assert {entry["action"] for entry in entries} == {"verify", "flag", "correct"}
    for entry in entries:
        assert entry["actor_user_id"] == admin_user.id
        assert entry["before"] and entry["after"]


def test_the_log_captures_the_state_transition(client: TestClient, profile: TalentProfile, admin_user) -> None:
    client.post(
        f"/admin/talent/{profile.player_id}/visibility",
        json={"visibility_state": "suspended", "reason": "Report upheld."},
    )

    entry = client.get(f"/admin/talent/{profile.player_id}/moderation-log").json()["entries"][0]

    assert entry["before"]["visibility_state"] == VisibilityState.PUBLISHED.value
    assert entry["after"]["visibility_state"] == VisibilityState.SUSPENDED.value
    assert entry["reason"] == "Report upheld."


def test_admin_recompute_endpoint_is_deterministic(client: TestClient, profile: TalentProfile, admin_user) -> None:
    first = client.post(f"/admin/talent/{profile.player_id}/recompute", json={"as_of": REFERENCE_TODAY.isoformat()})
    second = client.post(f"/admin/talent/{profile.player_id}/recompute", json={"as_of": REFERENCE_TODAY.isoformat()})

    assert first.status_code == 200, first.text
    assert first.json() == second.json()
