from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

from sqlalchemy import String, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.launch_control.service import COMMAND_ROUTE_CATALOG
from app.models.broadcast_rights import BroadcastRight, BroadcastRightsAuction
from app.models.clip_variant import ClipVariant
from app.models.coin_trader import CoinTradeOrder, CoinTraderProfile
from app.models.club_growth import AcademyProspect, ClubStaffProfile
from app.models.club_profile import ClubProfile
from app.models.club_sponsorship_package import ClubSponsorshipPackage
from app.models.competition import UserCompetition
from app.models.creator_profile import CreatorProfile
from app.models.dispute import Dispute
from app.models.fan_prediction import FanPredictionFixture
from app.models.fan_war import FanWarProfile
from app.models.federation import Federation
from app.models.news_article import NewsArticle
from app.models.notification_record import NotificationRecord
from app.models.player_cards import PlayerCard, PlayerCardListing, PlayerCardTier
from app.models.sponsored_clip import SponsoredClip
from app.models.ticketing import StadiumEvent, StadiumTicket
from app.models.transfer_market import TransferListing
from app.models.user import User, UserRole

from .schemas import GlobalSearchResultView, GlobalSearchSuggestionView


@dataclass(slots=True)
class GlobalSearchService:
    session: Session

    def search(self, *, actor: User, query: str, limit: int = 20, admin: bool = False) -> list[GlobalSearchResultView]:
        term = query.strip()
        if len(term) < 2:
            return []
        results: list[GlobalSearchResultView] = []
        self._collect(results, lambda: self._search_players(term, limit))
        self._collect(results, lambda: self._search_regens(term, limit))
        self._collect(results, lambda: self._search_clubs(term, limit))
        self._collect(results, lambda: self._search_competitions(term, limit))
        self._collect(results, lambda: self._search_news(term, limit))
        self._collect(results, lambda: self._search_creators(term, limit))
        self._collect(results, lambda: self._search_staff(term, limit))
        self._collect(results, lambda: self._search_sponsorships(term, limit))
        self._collect(results, lambda: self._search_federations(term, limit))
        self._collect(results, lambda: self._search_fan_predictions(term, limit))
        self._collect(results, lambda: self._search_fan_wars(term, limit))
        self._collect(results, lambda: self._search_broadcast_rights(term, limit))
        self._collect(results, lambda: self._search_viral_clips(term, limit))
        self._collect(results, lambda: self._search_transfer_listings(term, limit))
        self._collect(results, lambda: self._search_coin_traders(term, limit))
        self._collect(results, lambda: self._search_ticketing(term, limit))
        self._collect(results, lambda: self._search_player_card_listings(term, limit))
        if admin and self._can_admin(actor):
            self._collect(results, lambda: self._search_admin_command_routes(term, limit))
            self._collect(results, lambda: self._search_admin_users(term, limit))
            self._collect(results, lambda: self._search_admin_disputes(term, limit))
            self._collect(results, lambda: self._search_admin_notifications(term, limit))
            self._collect(results, lambda: self._search_admin_coin_orders(term, limit))
        results.sort(key=lambda item: (item.score, item.title.lower()), reverse=True)
        return self._dedupe(results)[:limit]

    def suggest(self, *, actor: User, query: str, limit: int = 8) -> list[GlobalSearchSuggestionView]:
        results = self.search(actor=actor, query=query, limit=limit, admin=False)
        return [
            GlobalSearchSuggestionView(
                label=item.title,
                type=item.type,
                route=item.route,
                score=item.score,
            )
            for item in results[:limit]
        ]

    def _collect(
        self,
        output: list[GlobalSearchResultView],
        collector: Callable[[], list[GlobalSearchResultView]],
    ) -> None:
        try:
            output.extend(collector())
        except SQLAlchemyError:
            self.session.rollback()

    def _search_players(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(Player)
            .where(
                or_(
                    Player.full_name.ilike(f"%{term}%"),
                    Player.canonical_display_name.ilike(f"%{term}%"),
                    Player.real_world_club_name.ilike(f"%{term}%"),
                    Player.real_world_league_name.ilike(f"%{term}%"),
                    Player.normalized_position.ilike(f"%{term}%"),
                )
            )
            .order_by(Player.is_real_player.desc(), Player.updated_at.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="player",
                id=item.id,
                title=item.canonical_display_name or item.full_name,
                subtitle=" - ".join(
                    part
                    for part in (item.normalized_position, item.real_world_club_name, item.real_world_league_name)
                    if part
                ),
                image_url=None,
                route=f"/app/market?player={item.id}",
                score=self._score(term, item.full_name, item.canonical_display_name, item.real_world_club_name),
                metadata={
                    "is_real_player": item.is_real_player,
                    "market_value_eur": item.market_value_eur,
                    "provider": item.source_provider,
                },
            )
            for item in self.session.scalars(statement).all()
        ]

    def _search_regens(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(AcademyProspect)
            .where(
                or_(
                    AcademyProspect.display_name.ilike(f"%{term}%"),
                    AcademyProspect.nationality.ilike(f"%{term}%"),
                    AcademyProspect.position.ilike(f"%{term}%"),
                )
            )
            .order_by(AcademyProspect.updated_at.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="regen",
                id=item.id,
                title=item.display_name,
                subtitle=f"{item.position} - {item.nationality or 'academy'} - {item.status}",
                image_url=item.portrait_asset_ref,
                route="/world/regens",
                score=self._score(term, item.display_name, item.nationality, item.position),
                metadata={"club_id": item.club_id, "status": item.status},
            )
            for item in self.session.scalars(statement).all()
        ]

    def _search_clubs(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(ClubProfile)
            .where(
                or_(
                    ClubProfile.club_name.ilike(f"%{term}%"),
                    ClubProfile.short_name.ilike(f"%{term}%"),
                    ClubProfile.slug.ilike(f"%{term}%"),
                    ClubProfile.country_code.ilike(f"%{term}%"),
                    ClubProfile.city_name.ilike(f"%{term}%"),
                )
            )
            .order_by(ClubProfile.updated_at.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="club",
                id=item.id,
                title=item.club_name,
                subtitle=item.club_address or item.slug,
                image_url=item.crest_asset_ref,
                route=f"/app/club?club={item.id}",
                score=self._score(term, item.club_name, item.short_name, item.slug),
                metadata={"slug": item.slug, "visibility": item.visibility},
            )
            for item in self.session.scalars(statement).all()
        ]

    def _search_competitions(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(UserCompetition)
            .where(or_(UserCompetition.name.ilike(f"%{term}%"), UserCompetition.description.ilike(f"%{term}%")))
            .order_by(UserCompetition.updated_at.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="competition",
                id=item.id,
                title=item.name,
                subtitle=item.description or item.status,
                route=f"/app/play?competition={item.id}",
                score=self._score(term, item.name, item.description),
                metadata={"status": item.status, "visibility": item.visibility, "format": item.format},
            )
            for item in self.session.scalars(statement).all()
        ]

    def _search_news(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(NewsArticle)
            .where(or_(NewsArticle.title.ilike(f"%{term}%"), NewsArticle.body.ilike(f"%{term}%"), NewsArticle.summary.ilike(f"%{term}%")))
            .order_by(NewsArticle.trend_score.desc(), NewsArticle.created_at.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="news",
                id=item.id,
                title=item.title,
                subtitle=item.summary or item.body[:140],
                route=f"/news/{item.id}",
                score=self._score(term, item.title, item.summary, item.body),
                metadata={"article_type": item.article_type, "tags": item.tags_json},
            )
            for item in self.session.scalars(statement).all()
        ]

    def _search_creators(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(CreatorProfile)
            .where(or_(CreatorProfile.handle.ilike(f"%{term}%"), CreatorProfile.display_name.ilike(f"%{term}%")))
            .order_by(CreatorProfile.updated_at.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="creator",
                id=item.id,
                title=item.display_name,
                subtitle=f"@{item.handle} - {item.tier}",
                route=f"/creators/{item.handle}",
                score=self._score(term, item.display_name, item.handle),
                metadata={"status": str(item.status), "user_id": item.user_id},
            )
            for item in self.session.scalars(statement).all()
        ]

    def _search_staff(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(ClubStaffProfile)
            .where(or_(ClubStaffProfile.display_name.ilike(f"%{term}%"), ClubStaffProfile.staff_type.ilike(f"%{term}%")))
            .order_by(ClubStaffProfile.rating.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="staff",
                id=item.id,
                title=item.display_name,
                subtitle=f"{item.staff_type} - rating {item.rating}",
                route="/app/club",
                score=self._score(term, item.display_name, item.staff_type),
                metadata={"skills": item.skills_json, "rarity": item.rarity},
            )
            for item in self.session.scalars(statement).all()
        ]

    def _search_sponsorships(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(ClubSponsorshipPackage)
            .where(or_(ClubSponsorshipPackage.name.ilike(f"%{term}%"), ClubSponsorshipPackage.code.ilike(f"%{term}%"), ClubSponsorshipPackage.description.ilike(f"%{term}%")))
            .order_by(ClubSponsorshipPackage.updated_at.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="sponsor_package",
                id=item.id,
                title=item.name,
                subtitle=item.description,
                route="/app/club",
                score=self._score(term, item.name, item.code, item.description),
                metadata={"asset_type": str(item.asset_type), "amount_minor": item.base_amount_minor},
            )
            for item in self.session.scalars(statement).all()
        ]

    def _search_federations(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(Federation)
            .where(
                Federation.is_public.is_(True),
                or_(
                    Federation.name.ilike(f"%{term}%"),
                    Federation.default_reality_mode.ilike(f"%{term}%"),
                ),
            )
            .order_by(Federation.ranking_score.desc(), Federation.updated_at.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="federation",
                id=item.id,
                title=item.name,
                subtitle=f"{item.default_reality_mode} federation - ranking {item.ranking_score:.1f} - audience {item.audience_size}",
                route=f"/app/play?federation={item.id}",
                score=self._score(term, item.name, item.default_reality_mode),
                metadata={
                    "ranking_score": item.ranking_score,
                    "reputation_score": item.reputation_score,
                    "audience_size": item.audience_size,
                },
            )
            for item in self.session.scalars(statement).all()
        ]

    def _search_fan_predictions(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(FanPredictionFixture)
            .where(
                or_(
                    FanPredictionFixture.title.ilike(f"%{term}%"),
                    FanPredictionFixture.description.ilike(f"%{term}%"),
                    FanPredictionFixture.status.cast(String).ilike(f"%{term}%"),
                    FanPredictionFixture.match_id.ilike(f"%{term}%"),
                )
            )
            .order_by(FanPredictionFixture.locks_at.asc(), FanPredictionFixture.updated_at.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="fan_prediction",
                id=item.id,
                title=item.title,
                subtitle=f"{item.status.value if hasattr(item.status, 'value') else item.status} - costs {item.token_cost} token(s)",
                route=f"/fan-predictions/matches/{item.match_id}",
                score=self._score(term, item.title, item.description, item.match_id),
                metadata={
                    "match_id": item.match_id,
                    "competition_id": item.competition_id,
                    "status": item.status.value if hasattr(item.status, "value") else str(item.status),
                    "promo_pool_fancoin": str(item.promo_pool_fancoin),
                },
            )
            for item in self.session.scalars(statement).all()
        ]

    def _search_fan_wars(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(FanWarProfile)
            .where(
                or_(
                    FanWarProfile.display_name.ilike(f"%{term}%"),
                    FanWarProfile.slug.ilike(f"%{term}%"),
                    FanWarProfile.entity_key.ilike(f"%{term}%"),
                    FanWarProfile.country_code.ilike(f"%{term}%"),
                    FanWarProfile.country_name.ilike(f"%{term}%"),
                    FanWarProfile.tagline.ilike(f"%{term}%"),
                )
            )
            .order_by(FanWarProfile.prestige_points.desc(), FanWarProfile.updated_at.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="fan_war",
                id=item.id,
                title=item.display_name,
                subtitle=f"{item.profile_type} - {item.country_name or item.country_code or 'global'} - {item.prestige_points} prestige",
                route=f"/app/community?fanWar={item.slug}",
                score=self._score(term, item.display_name, item.slug, item.entity_key, item.country_name, item.tagline),
                metadata={
                    "slug": item.slug,
                    "profile_type": item.profile_type,
                    "club_id": item.club_id,
                    "country_code": item.country_code,
                    "prestige_points": item.prestige_points,
                },
            )
            for item in self.session.scalars(statement).all()
        ]

    def _search_broadcast_rights(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        output: list[GlobalSearchResultView] = []
        auction_statement = (
            select(BroadcastRightsAuction, UserCompetition)
            .join(UserCompetition, BroadcastRightsAuction.competition_id == UserCompetition.id)
            .where(
                or_(
                    BroadcastRightsAuction.id.ilike(f"%{term}%"),
                    BroadcastRightsAuction.status.ilike(f"%{term}%"),
                    UserCompetition.name.ilike(f"%{term}%"),
                    UserCompetition.description.ilike(f"%{term}%"),
                )
            )
            .order_by(BroadcastRightsAuction.ends_at.desc())
            .limit(limit)
        )
        for auction, competition in self.session.execute(auction_statement).all():
            output.append(
                GlobalSearchResultView(
                    type="broadcast_auction",
                    id=auction.id,
                    title=f"{competition.name} broadcast auction",
                    subtitle=f"{auction.status} - reserve {auction.reserve_price} credits",
                    route=f"/broadcast/live?competition={competition.id}",
                    score=self._derivative_score(term, auction.id, auction.status, competition.name, competition.description),
                    metadata={
                        "competition_id": competition.id,
                        "status": auction.status,
                        "reserve_price": str(auction.reserve_price),
                        "exclusivity": auction.exclusivity,
                    },
                )
            )

        rights_statement = (
            select(BroadcastRight, UserCompetition)
            .join(UserCompetition, BroadcastRight.competition_id == UserCompetition.id)
            .where(
                or_(
                    BroadcastRight.id.ilike(f"%{term}%"),
                    BroadcastRight.owner_id.ilike(f"%{term}%"),
                    UserCompetition.name.ilike(f"%{term}%"),
                    UserCompetition.description.ilike(f"%{term}%"),
                )
            )
            .order_by(BroadcastRight.end_date.desc(), BroadcastRight.updated_at.desc())
            .limit(limit)
        )
        for right, competition in self.session.execute(rights_statement).all():
            output.append(
                GlobalSearchResultView(
                    type="broadcast_right",
                    id=right.id,
                    title=f"{competition.name} broadcast right",
                    subtitle=f"{'exclusive' if right.exclusivity else 'non-exclusive'} - share {right.revenue_share_percentage}%",
                    route=f"/broadcast/live?competition={competition.id}",
                    score=self._derivative_score(term, right.id, right.owner_id, competition.name, competition.description),
                    metadata={
                        "competition_id": competition.id,
                        "owner_id": right.owner_id,
                        "acquisition_price": str(right.acquisition_price),
                        "revenue_share_percentage": str(right.revenue_share_percentage),
                    },
                )
            )
        return output

    def _search_viral_clips(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        output: list[GlobalSearchResultView] = []
        variant_statement = (
            select(ClipVariant)
            .where(
                or_(
                    ClipVariant.variant_id.ilike(f"%{term}%"),
                    ClipVariant.base_clip_id.ilike(f"%{term}%"),
                    ClipVariant.format_type.ilike(f"%{term}%"),
                    ClipVariant.promotion_status.ilike(f"%{term}%"),
                )
            )
            .order_by(ClipVariant.viral_score.desc(), ClipVariant.updated_at.desc())
            .limit(limit)
        )
        for variant in self.session.scalars(variant_statement).all():
            output.append(
                GlobalSearchResultView(
                    type="viral_clip",
                    id=variant.variant_id,
                    title=f"{variant.base_clip_id} {variant.format_type}",
                    subtitle=f"{variant.promotion_status} - score {variant.viral_score:.1f} - {variant.view_count} views",
                    route=f"/news?clip={variant.base_clip_id}",
                    score=self._derivative_score(term, variant.variant_id, variant.base_clip_id, variant.format_type, variant.promotion_status),
                    metadata={
                        "base_clip_id": variant.base_clip_id,
                        "format_type": variant.format_type,
                        "viral_score": variant.viral_score,
                        "is_winner": variant.is_winner,
                    },
                )
            )

        sponsored_statement = (
            select(SponsoredClip)
            .where(
                or_(
                    SponsoredClip.clip_id.ilike(f"%{term}%"),
                    SponsoredClip.advertiser_id.ilike(f"%{term}%"),
                )
            )
            .order_by(SponsoredClip.is_active.desc(), SponsoredClip.updated_at.desc())
            .limit(limit)
        )
        for clip in self.session.scalars(sponsored_statement).all():
            output.append(
                GlobalSearchResultView(
                    type="sponsored_clip",
                    id=clip.id,
                    title=f"Sponsored clip {clip.clip_id}",
                    subtitle=f"budget {clip.budget} credits - {clip.impressions_served} impressions",
                    route=f"/news?clip={clip.clip_id}",
                    score=self._derivative_score(term, clip.clip_id, clip.advertiser_id),
                    metadata={
                        "clip_id": clip.clip_id,
                        "advertiser_id": clip.advertiser_id,
                        "is_active": clip.is_active,
                        "budget": str(clip.budget),
                    },
                )
            )
        return output

    def _search_transfer_listings(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(TransferListing, Player, ClubProfile)
            .join(Player, TransferListing.player_id == Player.id)
            .outerjoin(ClubProfile, TransferListing.selling_club_id == ClubProfile.id)
            .where(
                TransferListing.visibility == "public",
                or_(
                    TransferListing.id.ilike(f"%{term}%"),
                    TransferListing.listing_type.ilike(f"%{term}%"),
                    TransferListing.status.ilike(f"%{term}%"),
                    TransferListing.asset_type.ilike(f"%{term}%"),
                    Player.full_name.ilike(f"%{term}%"),
                    Player.canonical_display_name.ilike(f"%{term}%"),
                    Player.real_world_club_name.ilike(f"%{term}%"),
                    ClubProfile.club_name.ilike(f"%{term}%"),
                    ClubProfile.short_name.ilike(f"%{term}%"),
                ),
            )
            .order_by(TransferListing.updated_at.desc())
            .limit(limit)
        )
        output: list[GlobalSearchResultView] = []
        for listing, player, club in self.session.execute(statement).all():
            player_name = player.canonical_display_name or player.full_name
            club_name = club.club_name if club is not None else "selling club"
            listing_label = listing.listing_type.replace("_", " ").title()
            score = self._derivative_score(
                term,
                listing.id,
                listing.listing_type,
                listing.status,
                player_name,
                player.real_world_club_name,
                club_name,
            )
            output.append(
                GlobalSearchResultView(
                    type="transfer_listing",
                    id=listing.id,
                    title=f"{player_name} {listing_label}",
                    subtitle=f"{club_name} - {listing.status} - {listing.base_price} credits",
                    route=f"/app/market?transferListing={listing.id}",
                    score=score,
                    metadata={
                        "player_id": listing.player_id,
                        "selling_club_id": listing.selling_club_id,
                        "listing_type": listing.listing_type,
                        "asset_type": listing.asset_type,
                        "status": listing.status,
                        "base_price": str(listing.base_price),
                    },
                )
            )
        return output

    def _search_coin_traders(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(CoinTraderProfile)
            .where(
                CoinTraderProfile.status == "approved",
                or_(
                    CoinTraderProfile.display_name.ilike(f"%{term}%"),
                    CoinTraderProfile.country_code.ilike(f"%{term}%"),
                    CoinTraderProfile.tier.ilike(f"%{term}%"),
                ),
            )
            .order_by(CoinTraderProfile.rating.desc(), CoinTraderProfile.updated_at.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="coin_trader",
                id=item.id,
                title=item.display_name,
                subtitle=f"{item.tier} trader - {item.country_code or 'global'} - rating {item.rating:.1f}",
                route=f"/app/coin-traders?trader={item.id}",
                score=self._score(term, item.display_name, item.country_code, item.tier),
                metadata={
                    "user_id": item.user_id,
                    "country_code": item.country_code,
                    "tier": item.tier,
                    "completion_rate": item.completion_rate,
                    "available_liquidity": item.liquidity_snapshot_json,
                },
            )
            for item in self.session.scalars(statement).all()
        ]

    def _search_ticketing(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        output: list[GlobalSearchResultView] = []
        event_statement = (
            select(StadiumEvent)
            .where(
                or_(
                    StadiumEvent.title.ilike(f"%{term}%"),
                    StadiumEvent.venue_name.ilike(f"%{term}%"),
                    StadiumEvent.match_id.ilike(f"%{term}%"),
                    StadiumEvent.event_type.ilike(f"%{term}%"),
                    StadiumEvent.event_status.ilike(f"%{term}%"),
                )
            )
            .order_by(StadiumEvent.public_sales_starts_at.desc().nullslast(), StadiumEvent.updated_at.desc())
            .limit(limit)
        )
        for event in self.session.scalars(event_statement).all():
            output.append(
                GlobalSearchResultView(
                    type="ticket_event",
                    id=event.id,
                    title=event.title,
                    subtitle=f"{event.venue_name} - {event.event_status} - {event.tickets_sold}/{event.capacity} sold",
                    route=f"/creator-stadium/matches/{event.match_id}",
                    score=self._score(term, event.title, event.venue_name, event.match_id, event.event_type),
                    metadata={
                        "match_id": event.match_id,
                        "stadium_id": event.stadium_id,
                        "event_status": event.event_status,
                        "resale_ticket_count": event.resale_ticket_count,
                    },
                )
            )

        resale_statement = (
            select(StadiumTicket, StadiumEvent)
            .join(StadiumEvent, StadiumTicket.event_id == StadiumEvent.id)
            .where(
                StadiumTicket.status == "available",
                StadiumTicket.resale_listing_price.is_not(None),
                or_(
                    StadiumEvent.title.ilike(f"%{term}%"),
                    StadiumEvent.venue_name.ilike(f"%{term}%"),
                    StadiumTicket.match_id.ilike(f"%{term}%"),
                    StadiumTicket.seat_tier.ilike(f"%{term}%"),
                    StadiumTicket.seat_code.ilike(f"%{term}%"),
                ),
            )
            .order_by(StadiumTicket.listed_at.desc().nullslast(), StadiumTicket.updated_at.desc())
            .limit(limit)
        )
        for ticket, event in self.session.execute(resale_statement).all():
            output.append(
                GlobalSearchResultView(
                    type="ticket_resale",
                    id=ticket.id,
                    title=f"{event.title} resale ticket",
                    subtitle=f"{ticket.seat_tier.title()} {ticket.seat_code} - {ticket.resale_listing_price} credits",
                    route=f"/creator-stadium/matches/{ticket.match_id}",
                    score=self._score(term, event.title, event.venue_name, ticket.match_id, ticket.seat_tier, ticket.seat_code),
                    metadata={
                        "match_id": ticket.match_id,
                        "event_id": event.id,
                        "seat_tier": ticket.seat_tier,
                        "resale_listing_price": str(ticket.resale_listing_price),
                    },
                )
            )
        return output

    def _search_player_card_listings(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        now = datetime.now(UTC)
        statement = (
            select(PlayerCardListing, PlayerCard, Player, PlayerCardTier)
            .join(PlayerCard, PlayerCardListing.player_card_id == PlayerCard.id)
            .join(Player, PlayerCard.player_id == Player.id)
            .join(PlayerCardTier, PlayerCard.tier_id == PlayerCardTier.id)
            .where(
                PlayerCardListing.status == "open",
                PlayerCardListing.quantity > 0,
                or_(PlayerCardListing.expires_at.is_(None), PlayerCardListing.expires_at > now),
                or_(
                    PlayerCardListing.listing_id.ilike(f"%{term}%"),
                    PlayerCard.display_name.ilike(f"%{term}%"),
                    PlayerCard.edition_code.ilike(f"%{term}%"),
                    PlayerCard.card_variant.ilike(f"%{term}%"),
                    PlayerCardTier.code.ilike(f"%{term}%"),
                    PlayerCardTier.name.ilike(f"%{term}%"),
                    Player.full_name.ilike(f"%{term}%"),
                    Player.canonical_display_name.ilike(f"%{term}%"),
                ),
            )
            .order_by(PlayerCardListing.updated_at.desc())
            .limit(limit)
        )
        output: list[GlobalSearchResultView] = []
        for listing, card, player, tier in self.session.execute(statement).all():
            player_name = player.canonical_display_name or player.full_name or card.display_name
            score = self._derivative_score(
                term,
                listing.listing_id,
                card.display_name,
                card.edition_code,
                card.card_variant,
                tier.name,
                tier.code,
                player_name,
            )
            output.append(
                GlobalSearchResultView(
                    type="player_card_listing",
                    id=listing.listing_id,
                    title=card.display_name or player_name,
                    subtitle=f"{tier.name} - {card.edition_code} - {listing.quantity} listed at {listing.price_per_card_credits} credits",
                    route=f"/player-cards/players/{player.id}",
                    score=score,
                    metadata={
                        "player_id": player.id,
                        "player_card_id": card.id,
                        "tier": tier.code,
                        "quantity": listing.quantity,
                        "price_per_card_credits": str(listing.price_per_card_credits),
                        "is_negotiable": listing.is_negotiable,
                    },
                )
            )
        return output

    def _search_admin_users(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(User)
            .where(or_(User.email.ilike(f"%{term}%"), User.username.ilike(f"%{term}%"), User.display_name.ilike(f"%{term}%")))
            .order_by(User.updated_at.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="admin_user",
                id=item.id,
                title=item.email,
                subtitle=f"{item.username} - {item.role} - KYC {item.kyc_status}",
                image_url=item.avatar_url,
                route=f"/admin?user={item.id}",
                score=self._score(term, item.email, item.username, item.display_name),
                permission_required="admin",
                metadata={"role": str(item.role), "kyc_status": str(item.kyc_status), "active": item.is_active},
            )
            for item in self.session.scalars(statement).all()
        ]

    def _search_admin_command_routes(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        output: list[GlobalSearchResultView] = []
        for item in COMMAND_ROUTE_CATALOG:
            module_key = item["module_key"]
            feature_key = item.get("feature_key")
            title = item["title"]
            description = item["description"]
            route = item["route"]
            score = self._score(term, module_key, feature_key, title, description, route)
            if score <= 0:
                continue
            output.append(
                GlobalSearchResultView(
                    type="admin_command_route",
                    id=module_key,
                    title=title,
                    subtitle=description,
                    route=route,
                    score=score,
                    permission_required="admin",
                    metadata={
                        "module_key": module_key,
                        "feature_key": feature_key,
                    },
                )
            )
        output.sort(key=lambda item: (item.score, item.title.lower()), reverse=True)
        return output[:limit]

    def _search_admin_coin_orders(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(CoinTradeOrder, CoinTraderProfile, User)
            .join(CoinTraderProfile, CoinTradeOrder.trader_profile_id == CoinTraderProfile.id)
            .join(User, CoinTradeOrder.user_id == User.id)
            .where(
                or_(
                    CoinTradeOrder.id.ilike(f"%{term}%"),
                    CoinTradeOrder.status.ilike(f"%{term}%"),
                    CoinTradeOrder.direction.ilike(f"%{term}%"),
                    CoinTradeOrder.fiat_currency.ilike(f"%{term}%"),
                    CoinTraderProfile.display_name.ilike(f"%{term}%"),
                    User.email.ilike(f"%{term}%"),
                    User.username.ilike(f"%{term}%"),
                )
            )
            .order_by(CoinTradeOrder.updated_at.desc())
            .limit(limit)
        )
        output: list[GlobalSearchResultView] = []
        for order, trader, user in self.session.execute(statement).all():
            output.append(
                GlobalSearchResultView(
                    type="admin_coin_order",
                    id=order.id,
                    title=f"{order.direction.replace('_', ' ').title()} - {order.status}",
                    subtitle=f"{user.email} via {trader.display_name} - {order.coin_amount} {order.coin_unit.value}",
                    route=f"/admin?coinOrder={order.id}",
                    score=self._score(
                        term,
                        order.id,
                        order.status,
                        order.direction,
                        trader.display_name,
                        user.email,
                        user.username,
                    ),
                    permission_required="admin",
                    metadata={
                        "user_id": order.user_id,
                        "trader_profile_id": order.trader_profile_id,
                        "coin_unit": order.coin_unit.value,
                        "coin_amount": str(order.coin_amount),
                        "fiat_total": str(order.fiat_total),
                        "fiat_currency": order.fiat_currency,
                    },
                )
            )
        return output

    def _search_admin_disputes(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(Dispute)
            .where(
                or_(
                    Dispute.id.ilike(f"%{term}%"),
                    Dispute.subject.ilike(f"%{term}%"),
                    Dispute.reference.ilike(f"%{term}%"),
                    Dispute.resource_type.ilike(f"%{term}%"),
                    Dispute.resource_id.ilike(f"%{term}%"),
                )
            )
            .order_by(Dispute.updated_at.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="admin_dispute",
                id=item.id,
                title=item.subject or item.reference,
                subtitle=f"{item.resource_type} - {item.status}",
                route=f"/admin?dispute={item.id}",
                score=self._score(term, item.id, item.subject, item.reference, item.resource_type, item.resource_id),
                permission_required="admin",
                metadata={"status": str(item.status), "user_id": item.user_id, "reference": item.reference},
            )
            for item in self.session.scalars(statement).all()
        ]

    def _search_admin_notifications(self, term: str, limit: int) -> list[GlobalSearchResultView]:
        statement = (
            select(NotificationRecord)
            .where(or_(NotificationRecord.topic.ilike(f"%{term}%"), NotificationRecord.message.ilike(f"%{term}%"), NotificationRecord.resource_id.ilike(f"%{term}%")))
            .order_by(NotificationRecord.created_at.desc())
            .limit(limit)
        )
        return [
            GlobalSearchResultView(
                type="admin_notification",
                id=item.id,
                title=item.topic,
                subtitle=item.message,
                route="/admin/notifications",
                score=self._score(term, item.topic, item.message, item.resource_id),
                permission_required="admin",
                metadata={"user_id": item.user_id, "template_key": item.template_key},
            )
            for item in self.session.scalars(statement).all()
        ]

    @staticmethod
    def _can_admin(actor: User) -> bool:
        role = actor.role.value if hasattr(actor.role, "value") else str(actor.role)
        return role in {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}

    @staticmethod
    def _dedupe(results: list[GlobalSearchResultView]) -> list[GlobalSearchResultView]:
        seen: set[tuple[str, str]] = set()
        output: list[GlobalSearchResultView] = []
        for item in results:
            marker = (item.type, item.id)
            if marker in seen:
                continue
            seen.add(marker)
            output.append(item)
        return output

    @staticmethod
    def _score(term: str, *texts: str | None) -> float:
        normalized = term.strip().lower()
        score = 0.0
        for text in texts:
            if not text:
                continue
            lowered = text.lower()
            if lowered == normalized:
                score += 20.0
            elif lowered.startswith(normalized):
                score += 12.0
            elif normalized in lowered:
                score += 6.0
            score += min(len(normalized) / max(len(lowered), 1), 0.5)
        return score

    @staticmethod
    def _derivative_score(term: str, *texts: str | None) -> float:
        return GlobalSearchService._score(term, *texts) * 0.65
