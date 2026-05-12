from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import Select, func, inspect, select
from sqlalchemy.orm import Session

from app.models.admin_rules import AdminFeatureFlag
from app.models.base import utcnow
from app.models.broadcast_rights import (
    BroadcastAccessGrant,
    BroadcastRevenueDistribution,
    BroadcastRight,
    BroadcastRightsAuction,
    ViewSession,
)
from app.models.broadcast_watch_session import BroadcastWatchSession
from app.models.clip_variant import ClipVariant
from app.models.creator_clip_monetization import CreatorClipRevenueAttribution
from app.models.fan_prediction import (
    FanPredictionFixture,
    FanPredictionFixtureStatus,
    FanPredictionLeaderboardScope,
    FanPredictionRewardGrant,
    FanPredictionRewardType,
    FanPredictionSubmission,
    FanPredictionSubmissionStatus,
)
from app.models.fan_war import FanWarPoint, FanWarProfile, FanbaseRanking, NationsCupEntry
from app.models.federation import Federation, FederationLeague, FederationMembership, FederationProposal, FederationSanction
from app.models.club_profile import ClubProfile
from app.models.notification_center import NotificationPreference
from app.models.notification_record import NotificationRecord
from app.models.player_cards import (
    PlayerCard,
    PlayerCardHolding,
    PlayerCardListing,
    PlayerCardOwnerHistory,
    PlayerCardSale,
)
from app.models.scale_backbone import OrchestratorClipStateRecord, ViralDispatchPoolEntryRecord, ViralLeaderboardEntryRecord
from app.models.sponsored_clip import SponsoredClip
from app.models.ticketing import StadiumEvent, StadiumTicket, TicketReaction, TicketWaitlist
from app.models.user import User, UserRole
from app.notifications.service import NotificationEventMatrixService, NotificationServiceError

from .schemas import (
    CardListingSettlementRequest,
    FederationSanctionResolutionRequest,
    MatchdayEconomyActionView,
    MatchdayEconomyMetricView,
    MatchdayEconomyOverviewView,
    MatchdayEconomySectionView,
    PredictionRewardSettlementRequest,
    TicketCheckInRequest,
)


SECTION_CATALOG: tuple[dict[str, str], ...] = (
    {
        "key": "federation_governance",
        "title": "Federation Governance",
        "description": "National associations, rankings, rules, votes, sanctions, and federation competitions.",
        "feature_key": "federations",
        "route": "/app/play",
    },
    {
        "key": "fan_economy",
        "title": "Fan Economy",
        "description": "Predictions, fan wars, reward grants, supporter points, and Fan Coin-adjacent activity.",
        "feature_key": "fan_coin",
        "route": "/app/community",
    },
    {
        "key": "viral_broadcast",
        "title": "Viral Clips And Broadcast",
        "description": "Highlight variants, viral ranking pools, broadcast rights, view sessions, and creator revenue.",
        "feature_key": "broadcast",
        "route": "/broadcast/live",
    },
    {
        "key": "ticketing_stadium",
        "title": "Ticketing And Stadium",
        "description": "Stadium events, sold inventory, resale queues, crowd reactions, and attendance rewards.",
        "feature_key": "ticketing",
        "route": "/app/play",
    },
    {
        "key": "player_card_collectibles",
        "title": "Player Card Collectibles",
        "description": "Card supply, holdings, listings, settled sales, and collectible market depth.",
        "feature_key": "player_card_marketplace",
        "route": "/player-cards",
    },
)


class MatchdayEconomyActionError(ValueError):
    """Raised when a matchday economy admin action cannot be completed."""


@dataclass(slots=True)
class MatchdayEconomyService:
    session: Session

    def resolve_federation_sanction(
        self,
        sanction_id: str,
        payload: FederationSanctionResolutionRequest,
        *,
        actor: User,
    ) -> MatchdayEconomyActionView:
        sanction = self.session.get(FederationSanction, sanction_id)
        if sanction is None:
            raise MatchdayEconomyActionError("Federation sanction was not found.")
        if sanction.status != "active":
            return MatchdayEconomyActionView(
                action="resolve_federation_sanction",
                status="noop",
                resource_id=sanction.id,
                message="Federation sanction is already resolved.",
                metadata={"status": sanction.status},
            )
        now = utcnow()
        sanction.status = "resolved"
        sanction.ends_at = sanction.ends_at or now
        sanction.metadata_json = {
            **dict(sanction.metadata_json or {}),
            "resolved_by_user_id": actor.id,
            "resolved_at": now.isoformat(),
            "resolution_note": payload.note or "",
            **payload.metadata_json,
        }
        self.session.commit()
        self.session.refresh(sanction)
        target_user_ids = self._club_owner_targets(sanction.club_id) or [actor.id]
        self._publish_notification_event(
            event_key="federation_sanction_resolved",
            target_user_ids=target_user_ids,
            resource_id=sanction.id,
            metadata_json={
                "federation_id": sanction.federation_id,
                "club_id": sanction.club_id,
                "resolved_by_user_id": actor.id,
            },
        )
        self.session.commit()
        return MatchdayEconomyActionView(
            action="resolve_federation_sanction",
            status="resolved",
            resource_id=sanction.id,
            message="Federation sanction resolved.",
            metrics={"active_sanctions": float(self._count(FederationSanction, FederationSanction.status == "active"))},
            metadata={"federation_id": sanction.federation_id, "club_id": sanction.club_id},
        )

    def settle_prediction_rewards(
        self,
        fixture_id: str,
        payload: PredictionRewardSettlementRequest,
        *,
        actor: User,
    ) -> MatchdayEconomyActionView:
        fixture = self.session.get(FanPredictionFixture, fixture_id)
        if fixture is None:
            raise MatchdayEconomyActionError("Fan prediction fixture was not found.")
        submissions = list(
            self.session.scalars(
                select(FanPredictionSubmission)
                .where(FanPredictionSubmission.fixture_id == fixture.id)
                .order_by(
                    FanPredictionSubmission.points_awarded.desc(),
                    FanPredictionSubmission.correct_pick_count.desc(),
                    FanPredictionSubmission.created_at.asc(),
                )
            ).all()
        )
        if not submissions:
            raise MatchdayEconomyActionError("Fan prediction fixture has no submissions to settle.")
        now = utcnow()
        winners = submissions[: payload.max_winners]
        grants_created = 0
        for rank, submission in enumerate(winners, start=1):
            unique_key = f"matchday_prediction:{fixture.id}:{submission.user_id}"
            existing_grant = self.session.scalar(
                select(FanPredictionRewardGrant).where(FanPredictionRewardGrant.unique_key == unique_key)
            )
            if existing_grant is None and payload.fancoin_amount > Decimal("0"):
                self.session.add(
                    FanPredictionRewardGrant(
                        user_id=submission.user_id,
                        fixture_id=fixture.id,
                        submission_id=submission.id,
                        club_id=submission.fan_segment_club_id,
                        awarded_by_user_id=actor.id,
                        leaderboard_scope=FanPredictionLeaderboardScope.MATCH,
                        reward_type=FanPredictionRewardType.FANCOIN,
                        rank=rank,
                        week_start=submission.leaderboard_week_start,
                        fancoin_amount=payload.fancoin_amount,
                        promo_pool_reference=f"matchday:{fixture.id}",
                        unique_key=unique_key,
                        metadata_json={"note": payload.note or "", **payload.metadata_json},
                    )
                )
                grants_created += 1
            submission.status = FanPredictionSubmissionStatus.SETTLED
            submission.reward_rank = rank
            submission.settled_at = now
        for submission in submissions[payload.max_winners :]:
            submission.status = FanPredictionSubmissionStatus.SETTLED
            submission.settled_at = now
        fixture.status = FanPredictionFixtureStatus.SETTLED
        fixture.settled_at = now
        fixture.rewards_disbursed_at = now
        fixture.metadata_json = {
            **dict(fixture.metadata_json or {}),
            "settled_by_user_id": actor.id,
            "settlement_note": payload.note or "",
        }
        self._publish_notification_event(
            event_key="prediction_settled",
            target_user_ids=[submission.user_id for submission in submissions],
            resource_id=fixture.id,
            metadata_json={
                "fixture_id": fixture.id,
                "match_id": fixture.match_id,
                "competition_id": fixture.competition_id,
                "settled_by_user_id": actor.id,
            },
        )
        self.session.commit()
        return MatchdayEconomyActionView(
            action="settle_prediction_rewards",
            status="settled",
            resource_id=fixture.id,
            message="Fan prediction rewards settled.",
            metrics={
                "submissions_settled": float(len(submissions)),
                "winners": float(len(winners)),
                "reward_grants_created": float(grants_created),
            },
            metadata={"fixture_id": fixture.id, "title": fixture.title},
        )

    def check_in_ticket(
        self,
        ticket_id: str,
        payload: TicketCheckInRequest,
        *,
        actor: User,
    ) -> MatchdayEconomyActionView:
        ticket = self.session.get(StadiumTicket, ticket_id)
        if ticket is None:
            raise MatchdayEconomyActionError("Stadium ticket was not found.")
        event = self.session.get(StadiumEvent, ticket.event_id)
        if event is None:
            raise MatchdayEconomyActionError("Stadium event was not found for this ticket.")
        first_check_in = ticket.status != "used"
        now = utcnow()
        ticket.status = "used"
        ticket.used_at = ticket.used_at or now
        if ticket.rewarded_at is None:
            ticket.rewarded_at = now
            ticket.loyalty_points_awarded += payload.loyalty_points
            ticket.xp_awarded += payload.xp_awarded
            event.loyalty_points_distributed += payload.loyalty_points
        if first_check_in:
            event.tickets_used += 1
        ticket.metadata_json = {
            **dict(ticket.metadata_json or {}),
            "checked_in_by_user_id": actor.id,
            **payload.metadata_json,
        }
        reaction_created = False
        if payload.reaction_type:
            self.session.add(
                TicketReaction(
                    ticket_id=ticket.id,
                    match_id=ticket.match_id,
                    user_id=ticket.user_id,
                    reaction_type=payload.reaction_type,
                    crowd_delta=payload.crowd_delta,
                    influence_multiplier=payload.influence_multiplier,
                    metadata_json={"source": "admin_matchday_check_in"},
                )
            )
            reaction_created = True
        self._publish_notification_event(
            event_key="ticket_attendance_reward",
            target_user_ids=[ticket.user_id],
            resource_id=ticket.id,
            metadata_json={
                "event_id": event.id,
                "match_id": ticket.match_id,
                "loyalty_points": payload.loyalty_points,
                "xp_awarded": payload.xp_awarded,
                "checked_in_by_user_id": actor.id,
            },
        )
        self.session.commit()
        self.session.refresh(ticket)
        return MatchdayEconomyActionView(
            action="check_in_ticket",
            status="checked_in" if first_check_in else "already_checked_in",
            resource_id=ticket.id,
            message="Ticket attendance recorded.",
            metrics={
                "loyalty_points_awarded": float(ticket.loyalty_points_awarded),
                "xp_awarded": float(ticket.xp_awarded),
                "event_tickets_used": float(event.tickets_used),
            },
            metadata={"event_id": event.id, "reaction_created": reaction_created},
        )

    def settle_card_listing(
        self,
        listing_id: str,
        payload: CardListingSettlementRequest,
        *,
        actor: User,
    ) -> MatchdayEconomyActionView:
        listing = self._card_listing(listing_id)
        if listing.status != "open":
            raise MatchdayEconomyActionError("Player card listing is not open.")
        if listing.seller_user_id == payload.buyer_user_id:
            raise MatchdayEconomyActionError("Buyer cannot settle their own card listing.")
        if payload.quantity > listing.quantity:
            raise MatchdayEconomyActionError("Settlement quantity exceeds listing quantity.")
        seller_holding = self._card_holding(listing.seller_user_id, listing.player_card_id)
        if seller_holding.quantity_total - seller_holding.quantity_reserved < payload.quantity:
            raise MatchdayEconomyActionError("Seller does not have enough available card quantity.")
        buyer_holding = self.session.scalar(
            select(PlayerCardHolding).where(
                PlayerCardHolding.owner_user_id == payload.buyer_user_id,
                PlayerCardHolding.player_card_id == listing.player_card_id,
            )
        )
        if buyer_holding is None:
            buyer_holding = PlayerCardHolding(
                player_card_id=listing.player_card_id,
                owner_user_id=payload.buyer_user_id,
                quantity_total=0,
                quantity_reserved=0,
            )
            self.session.add(buyer_holding)
        gross = Decimal(str(listing.price_per_card_credits)) * Decimal(payload.quantity)
        fee = (gross * Decimal(payload.fee_bps) / Decimal(10000)).quantize(Decimal("0.0001"))
        seller_net = gross - fee
        seller_holding.quantity_total -= payload.quantity
        buyer_holding.quantity_total += payload.quantity
        buyer_holding.last_acquired_at = utcnow()
        listing.quantity -= payload.quantity
        listing.status = "settled" if listing.quantity == 0 else "open"
        sale = PlayerCardSale(
            sale_id=f"sale_{uuid4().hex[:24]}",
            listing_id=listing.listing_id,
            player_card_id=listing.player_card_id,
            seller_user_id=listing.seller_user_id,
            buyer_user_id=payload.buyer_user_id,
            quantity=payload.quantity,
            price_per_card_credits=listing.price_per_card_credits,
            gross_credits=gross,
            fee_credits=fee,
            seller_net_credits=seller_net,
            settlement_reference=payload.settlement_reference or f"matchday:{listing.listing_id}:{uuid4().hex[:12]}",
            metadata_json={"settled_by_user_id": actor.id, **payload.metadata_json},
        )
        self.session.add(sale)
        self.session.add(
            PlayerCardOwnerHistory(
                player_card_id=listing.player_card_id,
                from_user_id=listing.seller_user_id,
                to_user_id=payload.buyer_user_id,
                quantity=payload.quantity,
                event_type="market_sale",
                reference_id=sale.sale_id,
                metadata_json={"listing_id": listing.listing_id},
            )
        )
        self._publish_notification_event(
            event_key="card_listing_sold",
            target_user_ids=[listing.seller_user_id, payload.buyer_user_id],
            resource_id=listing.listing_id,
            metadata_json={
                "player_card_id": listing.player_card_id,
                "sale_id": sale.sale_id,
                "quantity": payload.quantity,
                "gross_credits": str(gross),
                "settled_by_user_id": actor.id,
            },
        )
        self.session.commit()
        return MatchdayEconomyActionView(
            action="settle_card_listing",
            status="settled",
            resource_id=listing.listing_id,
            message="Player card listing settled.",
            metrics={
                "quantity": float(payload.quantity),
                "gross_credits": float(gross),
                "fee_credits": float(fee),
                "seller_net_credits": float(seller_net),
            },
            metadata={"sale_id": sale.sale_id, "listing_status": listing.status},
        )

    def overview(self, *, user: User | None = None, admin: bool = False) -> MatchdayEconomyOverviewView:
        sections = [
            self._federation_section(),
            self._fan_economy_section(),
            self._viral_broadcast_section(),
            self._ticketing_section(),
            self._cards_section(),
        ]
        if not admin:
            sections = [section for section in sections if self._section_visible_to_client(section, user)]
        return MatchdayEconomyOverviewView(
            generated_at=utcnow(),
            audience="admin" if admin else self._audience_for(user),
            sections=sections,
            totals={
                "sections": float(len(sections)),
                "metrics": float(sum(len(section.metrics) for section in sections)),
                "alerts": float(sum(len(section.alerts) for section in sections)),
            },
        )

    def _federation_section(self) -> MatchdayEconomySectionView:
        federations = self._count(Federation)
        open_proposals = self._count(FederationProposal, FederationProposal.status == "open")
        active_sanctions = self._count(FederationSanction, FederationSanction.status == "active")
        active_memberships = self._count(FederationMembership, FederationMembership.status == "active")
        leagues = self._count(FederationLeague)
        return self._section(
            "federation_governance",
            metrics=[
                self._metric("federations", "Federations", federations, route="/app/play"),
                self._metric("leagues", "Federation leagues", leagues, route="/app/play"),
                self._metric("memberships", "Active memberships", active_memberships, route="/app/play"),
                self._metric("proposals", "Open proposals", open_proposals, status="attention" if open_proposals else "ok"),
                self._metric("sanctions", "Active sanctions", active_sanctions, status="attention" if active_sanctions else "ok"),
            ],
            alerts=self._alerts_for_counts(
                ("No federation profiles have been created yet.", federations == 0),
                ("Governance proposals need review.", open_proposals > 0),
                ("Active federation sanctions are affecting eligibility.", active_sanctions > 0),
            ),
        )

    def _fan_economy_section(self) -> MatchdayEconomySectionView:
        fixtures = self._count(FanPredictionFixture)
        open_fixtures = self._count(FanPredictionFixture, FanPredictionFixture.status.in_(("scheduled", "open")))
        submissions = self._count(FanPredictionSubmission)
        rewards = self._count(FanPredictionRewardGrant)
        profiles = self._count(FanWarProfile)
        point_events = self._count(FanWarPoint)
        rankings = self._count(FanbaseRanking)
        nations_entries = self._count(NationsCupEntry)
        return self._section(
            "fan_economy",
            metrics=[
                self._metric("prediction_fixtures", "Prediction fixtures", fixtures, route="/app/community"),
                self._metric("open_predictions", "Open predictions", open_fixtures, status="live" if open_fixtures else "ok"),
                self._metric("submissions", "Prediction submissions", submissions),
                self._metric("reward_grants", "Reward grants", rewards, unit="grants"),
                self._metric("fan_profiles", "Fan war profiles", profiles, route="/app/community"),
                self._metric("fan_points", "Fan war point events", point_events),
                self._metric("rankings", "Fanbase rankings", rankings),
                self._metric("nations_cup_entries", "Nations Cup entries", nations_entries),
            ],
            alerts=self._alerts_for_counts(
                ("Fan economy has no active prediction fixtures yet.", fixtures == 0),
                ("Prediction rewards have not been issued yet.", submissions > 0 and rewards == 0),
                ("Fan war profiles need seed data before leaderboards feel alive.", profiles == 0),
            ),
        )

    def _viral_broadcast_section(self) -> MatchdayEconomySectionView:
        clip_variants = self._count(ClipVariant)
        viral_entries = self._count(ViralLeaderboardEntryRecord)
        dispatch_pool = self._count(ViralDispatchPoolEntryRecord)
        orchestrated = self._count(OrchestratorClipStateRecord)
        rights = self._count(BroadcastRight)
        auctions = self._count(BroadcastRightsAuction, BroadcastRightsAuction.status == "open")
        grants = self._count(BroadcastAccessGrant)
        view_sessions = self._count(ViewSession) + self._count(BroadcastWatchSession)
        revenue_rows = self._count(BroadcastRevenueDistribution) + self._count(CreatorClipRevenueAttribution)
        sponsored = self._count(SponsoredClip, SponsoredClip.is_active.is_(True))
        return self._section(
            "viral_broadcast",
            metrics=[
                self._metric("clip_variants", "Clip variants", clip_variants, route="/app/community"),
                self._metric("viral_entries", "Viral leaderboard entries", viral_entries),
                self._metric("dispatch_pool", "Dispatch pool", dispatch_pool),
                self._metric("orchestrated_clips", "Orchestrated clips", orchestrated),
                self._metric("broadcast_rights", "Broadcast rights", rights, route="/broadcast"),
                self._metric("open_auctions", "Open rights auctions", auctions, status="live" if auctions else "ok"),
                self._metric("access_grants", "Broadcast grants", grants),
                self._metric("view_sessions", "View sessions", view_sessions),
                self._metric("revenue_rows", "Revenue records", revenue_rows),
                self._metric("sponsored_clips", "Sponsored clips", sponsored),
            ],
            alerts=self._alerts_for_counts(
                ("No clip variants have entered the viral pipeline.", clip_variants == 0),
                ("Broadcast rights exist without revenue records yet.", rights > 0 and revenue_rows == 0),
                ("Open rights auctions need settlement attention.", auctions > 0),
            ),
        )

    def _ticketing_section(self) -> MatchdayEconomySectionView:
        events = self._count(StadiumEvent)
        on_sale = self._count(StadiumEvent, StadiumEvent.event_status == "on_sale")
        tickets = self._count(StadiumTicket)
        resale = self._count(StadiumTicket, StadiumTicket.status == "resale")
        used = self._count(StadiumTicket, StadiumTicket.status == "used")
        waitlist = self._count(TicketWaitlist, TicketWaitlist.status == "queued")
        reactions = self._count(TicketReaction)
        gross_revenue = self._sum(StadiumEvent.gross_revenue)
        return self._section(
            "ticketing_stadium",
            metrics=[
                self._metric("stadium_events", "Stadium events", events, route="/app/play"),
                self._metric("on_sale", "On sale", on_sale, status="live" if on_sale else "ok"),
                self._metric("tickets", "Tickets sold", tickets),
                self._metric("resale", "Resale tickets", resale, status="attention" if resale else "ok"),
                self._metric("used", "Attendance scans", used),
                self._metric("waitlist", "Queued waitlist", waitlist, status="attention" if waitlist else "ok"),
                self._metric("reactions", "Crowd reactions", reactions),
                self._metric("gross_revenue", "Gross revenue", gross_revenue, unit="credits"),
            ],
            alerts=self._alerts_for_counts(
                ("No stadium events are available for ticket sales yet.", events == 0),
                ("Ticket waitlist demand is queued.", waitlist > 0),
                ("Ticket revenue has not started for the current event set.", tickets > 0 and gross_revenue <= 0),
            ),
        )

    def _cards_section(self) -> MatchdayEconomySectionView:
        cards = self._count(PlayerCard)
        active_cards = self._count(PlayerCard, PlayerCard.is_active.is_(True))
        holdings = self._count(PlayerCardHolding)
        listings = self._count(PlayerCardListing, PlayerCardListing.status == "open")
        sales = self._count(PlayerCardSale, PlayerCardSale.status == "settled")
        gross = self._sum(PlayerCardSale.gross_credits)
        supply = self._sum(PlayerCard.supply_total)
        available = self._sum(PlayerCard.supply_available)
        return self._section(
            "player_card_collectibles",
            metrics=[
                self._metric("cards", "Card templates", cards, route="/player-cards"),
                self._metric("active_cards", "Active cards", active_cards),
                self._metric("supply", "Total supply", supply),
                self._metric("available_supply", "Available supply", available),
                self._metric("holdings", "User holdings", holdings),
                self._metric("open_listings", "Open listings", listings, status="live" if listings else "ok"),
                self._metric("settled_sales", "Settled sales", sales),
                self._metric("gross_sales", "Gross sales", gross, unit="credits"),
            ],
            alerts=self._alerts_for_counts(
                ("No player card templates exist yet.", cards == 0),
                ("Cards exist but there is no open collectible liquidity.", cards > 0 and listings == 0),
                ("Card sales are not settling yet.", listings > 0 and sales == 0),
            ),
        )

    def _section(
        self,
        key: str,
        *,
        metrics: list[MatchdayEconomyMetricView],
        alerts: list[str],
    ) -> MatchdayEconomySectionView:
        catalog = next(item for item in SECTION_CATALOG if item["key"] == key)
        flag = self._feature_flag(catalog["feature_key"])
        launch_state = self._launch_state(flag)
        enabled = self._flag_enabled(flag)
        return MatchdayEconomySectionView(
            key=catalog["key"],
            title=catalog["title"],
            description=catalog["description"],
            feature_key=catalog["feature_key"],
            route=self._route_for(flag) or catalog["route"],
            launch_state=launch_state,
            enabled=enabled,
            health_status=self._health_status(flag),
            metrics=metrics,
            alerts=alerts,
        )

    def _metric(
        self,
        key: str,
        label: str,
        value: float | int | Decimal,
        *,
        unit: str | None = None,
        status: str = "ok",
        route: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MatchdayEconomyMetricView:
        number = float(value)
        return MatchdayEconomyMetricView(
            key=key,
            label=label,
            value=number,
            display_value=self._display_value(number, unit=unit),
            unit=unit,
            status=status,
            route=route,
            metadata=metadata or {},
        )

    def _count(self, model: type[Any], *criteria: Any) -> int:
        if not self._has_table(model):
            return 0
        statement = select(func.count()).select_from(model)
        if criteria:
            statement = statement.where(*criteria)
        value = self.session.scalar(statement)
        return int(value or 0)

    def _sum(self, column: Any, *criteria: Any) -> float:
        model = column.class_
        if not self._has_table(model):
            return 0.0
        statement: Select[Any] = select(func.coalesce(func.sum(column), 0))
        if criteria:
            statement = statement.where(*criteria)
        value = self.session.scalar(statement)
        return float(value or 0)

    def _has_table(self, model: type[Any]) -> bool:
        try:
            return bool(inspect(self.session.get_bind()).has_table(model.__table__.name))
        except Exception:
            return False

    def _card_listing(self, listing_id: str) -> PlayerCardListing:
        listing = self.session.scalar(
            select(PlayerCardListing).where(
                (PlayerCardListing.id == listing_id) | (PlayerCardListing.listing_id == listing_id)
            )
        )
        if listing is None:
            raise MatchdayEconomyActionError("Player card listing was not found.")
        return listing

    def _card_holding(self, owner_user_id: str, player_card_id: str) -> PlayerCardHolding:
        holding = self.session.scalar(
            select(PlayerCardHolding).where(
                PlayerCardHolding.owner_user_id == owner_user_id,
                PlayerCardHolding.player_card_id == player_card_id,
            )
        )
        if holding is None:
            raise MatchdayEconomyActionError("Player card holding was not found.")
        return holding

    def _feature_flag(self, feature_key: str) -> AdminFeatureFlag | None:
        if not self._has_table(AdminFeatureFlag):
            return None
        return self.session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == feature_key))

    @staticmethod
    def _alerts_for_counts(*items: tuple[str, bool]) -> list[str]:
        return [message for message, condition in items if condition]

    @staticmethod
    def _display_value(value: float, *, unit: str | None = None) -> str:
        if unit == "credits":
            return f"{value:,.0f}"
        if value == round(value):
            return f"{int(value):,}"
        return f"{value:,.2f}"

    @staticmethod
    def _route_for(flag: AdminFeatureFlag | None) -> str | None:
        metadata = getattr(flag, "metadata_json", None) or {}
        route = metadata.get("route")
        return route if isinstance(route, str) and route.strip() else None

    @staticmethod
    def _launch_state(flag: AdminFeatureFlag | None) -> str:
        raw = getattr(flag, "launch_state", None)
        return raw if isinstance(raw, str) and raw.strip() else "not_configured"

    @classmethod
    def _flag_enabled(cls, flag: AdminFeatureFlag | None) -> bool:
        if flag is None:
            return False
        state = cls._launch_state(flag)
        return bool(flag.enabled) and not bool(flag.kill_switch_enabled) and state not in {
            "hidden",
            "disabled",
            "paused",
            "maintenance",
        }

    @classmethod
    def _health_status(cls, flag: AdminFeatureFlag | None) -> str:
        if flag is None:
            return "not_configured"
        state = cls._launch_state(flag)
        if flag.kill_switch_enabled:
            return "kill_switch"
        if state in {"hidden", "disabled", "paused", "maintenance"}:
            return state
        if not flag.enabled:
            return "off"
        if state in {"internal", "beta"} or flag.beta_only:
            return "gated"
        return "online"

    def _section_visible_to_client(self, section: MatchdayEconomySectionView, user: User | None) -> bool:
        flag = self._feature_flag(section.feature_key)
        if flag is None:
            return True
        state = self._launch_state(flag)
        if state in {"hidden", "disabled"}:
            return False
        if state == "internal" and not self._is_admin(user):
            return False
        if (state == "beta" or flag.beta_only) and not self._is_admin(user):
            return False
        return True

    @staticmethod
    def _audience_for(user: User | None) -> str:
        if user is None:
            return "guest"
        role = getattr(user.role, "value", str(user.role)).lower()
        return role or "user"

    @staticmethod
    def _is_admin(user: User | None) -> bool:
        role = getattr(getattr(user, "role", None), "value", getattr(user, "role", "")).lower()
        return role in {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}

    def _club_owner_targets(self, club_id: str | None) -> list[str]:
        if not club_id or not self._has_table(ClubProfile):
            return []
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            return []
        return [club.owner_user_id]

    def _publish_notification_event(
        self,
        *,
        event_key: str,
        target_user_ids: list[str],
        resource_id: str,
        metadata_json: dict[str, Any],
    ) -> None:
        if not self._has_table(NotificationRecord) or not self._has_table(NotificationPreference):
            return
        try:
            NotificationEventMatrixService(self.session).publish_event(
                event_key=event_key,
                target_user_ids=tuple(target_user_ids),
                resource_id=resource_id,
                metadata_json=metadata_json,
            )
        except NotificationServiceError:
            return
