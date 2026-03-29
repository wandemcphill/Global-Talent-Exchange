from __future__ import annotations

from sqlalchemy import select

from app.leaderboards.models import LeaderboardPlayerRating, LeaderboardSeason
from app.models.reward_settlement import RewardSettlement
from app.models.competition import Competition
from app.models.creator_share_market import (
    CreatorClubShareHolding,
    CreatorClubShareMarket,
    CreatorClubShareMarketControl,
)
from app.models.history_engagement import UserFollow, UserProfile
from app.models.streamer_tournament import (
    StreamerTournamentApprovalStatus,
    StreamerTournamentRewardGrant,
    StreamerTournamentStatus,
)
from app.models.wallet import LedgerUnit
from app.reward_engine.service import RewardEngineService
from app.streamer_tournament_engine.schemas import (
    StreamerTournamentCreateRequest,
    StreamerTournamentJoinRequest,
    StreamerTournamentPublishRequest,
    StreamerTournamentReviewRequest,
    StreamerTournamentRewardInput,
    StreamerTournamentSettleRequest,
    StreamerTournamentSettlementPlacement,
)
from app.streamer_tournament_engine.service import StreamerTournamentService


def test_high_reward_tournament_requires_admin_review_and_settles_rewards(session, seeded_context) -> None:
    service = StreamerTournamentService(session)
    creator = seeded_context["creator"]
    admin = seeded_context["admin"]
    invitee = seeded_context["invitee"]

    tournament = service.create_tournament(
        actor=creator,
        payload=StreamerTournamentCreateRequest(
            title="Creator Finals",
            tournament_type="creator_invitation",
            max_participants=8,
            rewards=[
                StreamerTournamentRewardInput(
                    title="Champion GTEX",
                    reward_type="gtex_coin",
                    placement_start=1,
                    placement_end=1,
                    amount="750.0000",
                ),
                StreamerTournamentRewardInput(
                    title="Champion FanCoin",
                    reward_type="fan_coin",
                    placement_start=1,
                    placement_end=1,
                    amount="250.0000",
                ),
            ],
            invite_user_ids=[invitee.id],
        ),
    )
    session.commit()
    assert tournament["approval_status"] == StreamerTournamentApprovalStatus.PENDING

    pending = service.publish_tournament(
        actor=creator,
        tournament_id=tournament["id"],
        submission_notes=StreamerTournamentPublishRequest(submission_notes="ready").submission_notes,
    )
    session.commit()
    assert pending["status"] == StreamerTournamentStatus.PENDING_APPROVAL

    approved = service.review_tournament(
        actor=admin,
        tournament_id=tournament["id"],
        approve=StreamerTournamentReviewRequest(approve=True, notes="approved").approve,
        notes="approved",
    )
    RewardEngineService(session).credit_promo_pool(actor=admin, amount="2000.0000", unit=LedgerUnit.COIN, note="coin seeding")
    RewardEngineService(session).credit_promo_pool(actor=admin, amount="2000.0000", unit=LedgerUnit.CREDIT, note="credit seeding")
    session.commit()
    assert approved["status"] == StreamerTournamentStatus.PUBLISHED

    service.join_tournament(
        actor=invitee,
        tournament_id=tournament["id"],
        payload=StreamerTournamentJoinRequest(),
    )
    result = service.settle_tournament(
        actor=admin,
        tournament_id=tournament["id"],
        placements=StreamerTournamentSettleRequest(
            placements=[StreamerTournamentSettlementPlacement(user_id=invitee.id, placement=1)],
            note="finalized",
        ).placements,
        note="finalized",
    )
    session.commit()

    settlements = session.query(RewardSettlement).all()
    grants = session.query(StreamerTournamentRewardGrant).all()
    assert result["tournament"]["status"] == StreamerTournamentStatus.COMPLETED
    assert len(settlements) == 1
    assert settlements[0].gross_amount == 750
    assert len(grants) == 2
    assert all(item.ledger_transaction_id is not None or item.reward_settlement_id is not None for item in grants)


def test_settlement_updates_season_stats_and_creator_growth(session, seeded_context) -> None:
    service = StreamerTournamentService(session)
    admin = seeded_context["admin"]
    creator = seeded_context["creator"]
    invitee = seeded_context["invitee"]

    tournament = service.create_tournament(
        actor=creator,
        payload=StreamerTournamentCreateRequest(
            title="Creator Ladder",
            tournament_type="creator_invitation",
            max_participants=8,
            rewards=[
                StreamerTournamentRewardInput(
                    title="Ladder purse",
                    reward_type="gtex_coin",
                    placement_start=1,
                    placement_end=1,
                    amount="100.0000",
                ),
            ],
            invite_user_ids=[invitee.id],
        ),
    )
    service.publish_tournament(
        actor=creator,
        tournament_id=tournament["id"],
        submission_notes=None,
    )
    service.join_tournament(
        actor=invitee,
        tournament_id=tournament["id"],
        payload=StreamerTournamentJoinRequest(),
    )
    RewardEngineService(session).credit_promo_pool(
        actor=admin,
        amount="500.0000",
        unit=LedgerUnit.COIN,
        note="test seeding",
    )

    result = service.settle_tournament(
        actor=creator,
        tournament_id=tournament["id"],
        placements=[
            StreamerTournamentSettlementPlacement(user_id=invitee.id, placement=1),
        ],
        note="settled",
    )
    session.commit()

    leaderboard_season = session.scalar(select(LeaderboardSeason))
    invitee_rating = session.scalar(
        select(LeaderboardPlayerRating).where(LeaderboardPlayerRating.player_id == invitee.id)
    )
    creator_profile = session.scalar(select(UserProfile).where(UserProfile.user_id == creator.id))
    creator_follow = session.scalar(
        select(UserFollow).where(
            UserFollow.follower_user_id == invitee.id,
            UserFollow.target_user_id == creator.id,
        )
    )

    assert leaderboard_season is not None
    assert invitee_rating is not None
    assert invitee_rating.metadata_json["season_competition"]["tournament_entries"] == 1
    assert invitee_rating.metadata_json["season_competition"]["tournament_titles"] == 1
    assert invitee_rating.metadata_json["season_competition"]["best_placement"] == 1
    assert invitee_rating.metadata_json["season_competition"]["earnings_total"] == "100.0000"
    assert creator_profile is not None
    assert creator_profile.followers == 1
    assert creator_profile.profile_boost_total == 3
    assert creator_profile.metadata_json["creator_tournament_earnings_total"] == "10.0000"
    assert creator_profile.metadata_json["creator_tournament_followers_gained"] == 1
    assert creator_follow is not None
    assert result["tournament"]["metadata_json"]["creator_growth"]["participant_count"] == 1
    assert result["tournament"]["metadata_json"]["creator_growth"]["new_followers"] == 1
    assert result["tournament"]["metadata_json"]["creator_growth"]["payout_coin"] == "10.0000"


def test_shareholders_can_join_shareholder_qualified_tournaments(session, seeded_context) -> None:
    service = StreamerTournamentService(session)
    creator = seeded_context["creator"]
    shareholder = seeded_context["season_fan"]

    session.add(
        CreatorClubShareMarketControl(
            id="share-control",
            control_key="default",
            max_shares_per_club=100,
            max_shares_per_fan=10,
            shareholder_revenue_share_bps=2000,
            metadata_json={},
        )
    )
    session.add(
        CreatorClubShareMarket(
            id="share-market",
            club_id="creator-club",
            creator_user_id=creator.id,
            issued_by_user_id=creator.id,
            status="active",
            share_price_coin="5.0000",
            max_shares_issued=20,
            shares_sold=2,
            max_shares_per_fan=5,
            creator_controlled_shares=21,
            shareholder_revenue_share_bps=2000,
            metadata_json={},
        )
    )
    session.add(
        CreatorClubShareHolding(
            id="share-holding",
            market_id="share-market",
            club_id="creator-club",
            user_id=shareholder.id,
            share_count=2,
            total_spent_coin="10.0000",
            revenue_earned_coin="0.0000",
            metadata_json={},
        )
    )
    session.flush()

    tournament = service.create_tournament(
        actor=creator,
        payload=StreamerTournamentCreateRequest(
            title="Shareholder Cup",
            tournament_type="fan_qualifier",
            max_participants=8,
            qualification_methods=["shareholder"],
            rewards=[
                StreamerTournamentRewardInput(
                    title="Champion cosmetic",
                    reward_type="exclusive_cosmetic",
                    placement_start=1,
                    placement_end=1,
                    cosmetic_sku="cup_skin",
                )
            ],
        ),
    )
    published = service.publish_tournament(
        actor=creator,
        tournament_id=tournament["id"],
        submission_notes=None,
    )

    joined = service.join_tournament(
        actor=shareholder,
        tournament_id=tournament["id"],
        payload=StreamerTournamentJoinRequest(qualification_source_hint="shareholder"),
    )
    session.commit()

    assert published["status"] == StreamerTournamentStatus.PUBLISHED
    assert joined["entries"][0]["qualification_source"] == "shareholder"
    assert joined["entries"][0]["qualification_snapshot_json"]["share_count"] == 2


def test_streamer_tournament_fairness_mode_is_serialized_and_mirrored_to_linked_competition(session, seeded_context) -> None:
    service = StreamerTournamentService(session)
    creator = seeded_context["creator"]
    competition = session.get(Competition, "competition-1")

    tournament = service.create_tournament(
        actor=creator,
        payload=StreamerTournamentCreateRequest(
            title="Balanced Invitational",
            tournament_type="creator_invitation",
            linked_competition_id=competition.id,
            fairness_mode="balanced",
            rewards=[
                StreamerTournamentRewardInput(
                    title="Champion cosmetic",
                    reward_type="exclusive_cosmetic",
                    placement_start=1,
                    placement_end=1,
                    cosmetic_sku="balanced-skin",
                )
            ],
        ),
    )
    session.commit()
    session.refresh(competition)

    assert tournament["fairness_mode"] == "balanced"
    assert tournament["entry_rules_json"]["fairness_mode"] == "balanced"
    assert competition.metadata_json["fairness"]["mode"] == "balanced"
    assert competition.metadata_json["fairness"]["max_s_plus_players"] == 4
    assert competition.metadata_json["fairness"]["max_team_rating_spread"] == 6
