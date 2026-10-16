from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.club_growth.service import ClubGrowthService
from app.club_identity.models.reputation import ClubReputationProfile
from app.club_infra_engine.schemas import ClubInfraDashboardResponse
from app.club_infra_engine.service import ClubInfraService
from app.club_lifecycle.service import ClubLifecycleService
from app.ingestion.models import Country, Player
from app.models.base import utcnow
from app.models.club_profile import ClubProfile
from app.models.club_ranking_integrity import ClubRankingAbuseFlag, ClubRankingEvent
from app.models.competition import Competition
from app.models.competition_entry import CompetitionEntry
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.player_cards import PlayerMarketValueSnapshot
from app.models.transfer_market import (
    MarketWatchlistEntry,
    TransferHubOffer,
    TransferListing,
    TransferListingBid,
    TransferRequest,
)
from app.models.user import User
from app.models.wallet import LedgerAccount, LedgerAccountKind, LedgerBalanceProjection, LedgerEntry, LedgerUnit
from app.schemas.club_v2_snapshot import (
    ClubV2ClubView,
    ClubV2CompetitionView,
    ClubV2CompetitionsView,
    ClubV2RankingView,
    ClubV2SnapshotView,
    ClubV2SquadPlayerView,
    ClubV2SquadView,
    ClubV2TransferActivityView,
    ClubV2TransfersView,
    ClubV2WalletBalanceView,
    ClubV2WalletView,
)

_DECIMAL_ZERO = Decimal("0.0000")


@dataclass(slots=True)
class ClubV2SnapshotService:
    session: Session

    def build_snapshot(self, *, club: ClubProfile, viewer: User) -> ClubV2SnapshotView:
        generated_at = utcnow()
        squad = self._squad(club.id, generated_on=generated_at.date())
        return ClubV2SnapshotView(
            club_id=club.id,
            generated_at=generated_at,
            club=self._club(club),
            squad=squad,
            competitions=self._competitions(club.id),
            wallet=self._wallet(club),
            ranking=self._ranking(club.id),
            facilities=self._facilities(club=club, viewer=viewer),
            transfers=self._transfers(club.id),
            growth=ClubGrowthService(self.session).get_dashboard(club_id=club.id),
            lifecycle=ClubLifecycleService(self.session).operating_dashboard(club.id),
            metadata={
                "schema_version": "club_v2_snapshot.1",
                "live_authority": "club_v2_snapshot_service",
                "fake_context": False,
            },
        )

    def _club(self, club: ClubProfile) -> ClubV2ClubView:
        owner = self.session.get(User, club.owner_user_id)
        return ClubV2ClubView(
            id=club.id,
            club_name=club.club_name,
            short_name=club.short_name,
            slug=club.slug,
            owner_user_id=club.owner_user_id,
            owner_display_name=(
                getattr(owner, "display_name", None)
                or getattr(owner, "username", None)
                or getattr(owner, "email", None)
                if owner is not None
                else None
            ),
            lifecycle_status=self._value(club.lifecycle_status),
            club_type=self._value(club.club_type),
            visibility=str(club.visibility),
            crest_asset_ref=club.crest_asset_ref,
            primary_color=club.primary_color,
            secondary_color=club.secondary_color,
            accent_color=club.accent_color,
            home_venue_name=club.home_venue_name,
            country_code=club.country_code,
            region_name=club.region_name,
            city_name=club.city_name,
            description=club.description,
            created_at=club.created_at,
            updated_at=club.updated_at,
        )

    def _squad(self, club_id: str, *, generated_on: date) -> ClubV2SquadView:
        players = list(
            self.session.scalars(
                select(Player)
                .where(Player.current_club_profile_id == club_id)
                .order_by(Player.normalized_position.asc(), Player.full_name.asc())
                .limit(60)
            ).all()
        )
        market_snapshots = self._latest_market_snapshots([player.id for player in players])
        countries = self._countries_by_id([player.country_id for player in players if player.country_id])
        mapped_players: list[ClubV2SquadPlayerView] = []
        squad_value = 0
        for player in players:
            value_credits, value_source = self._player_value_credits(player, market_snapshots.get(player.id))
            squad_value += value_credits
            country = countries.get(player.country_id or "")
            mapped_players.append(
                ClubV2SquadPlayerView(
                    player_id=player.id,
                    name=player.canonical_display_name or player.full_name,
                    short_name=player.short_name,
                    position=player.normalized_position or player.position,
                    position_group=self._position_group(player.normalized_position or player.position),
                    nationality=self._country_label(country),
                    age=self._age(player.date_of_birth, generated_on=generated_on),
                    shirt_number=player.shirt_number,
                    market_value_credits=value_credits,
                    market_value_source=value_source,
                    market_value_eur=float(player.market_value_eur) if player.market_value_eur is not None else None,
                    rating=(
                        float(player.profile_completeness_score)
                        if player.profile_completeness_score is not None
                        else None
                    ),
                    is_regen=not bool(player.is_real_player),
                    is_tradable=bool(player.is_tradable),
                    updated_at=player.updated_at,
                )
            )
        return ClubV2SquadView(
            player_count=len(players),
            registered_player_count=len(players),
            squad_value_credits=squad_value,
            players=mapped_players,
        )

    def _competitions(self, club_id: str) -> ClubV2CompetitionsView:
        rows = self.session.execute(
            select(CompetitionParticipant, Competition)
            .join(Competition, Competition.id == CompetitionParticipant.competition_id)
            .where(CompetitionParticipant.club_id == club_id)
            .order_by(Competition.updated_at.desc(), CompetitionParticipant.updated_at.desc())
            .limit(20)
        ).all()
        items = [
            ClubV2CompetitionView(
                competition_id=competition.id,
                name=competition.name,
                status=str(competition.status),
                stage=str(competition.stage),
                format=str(competition.format),
                visibility=str(competition.visibility),
                participant_status=participant.status,
                seed=participant.seed,
                played=int(participant.played),
                wins=int(participant.wins),
                draws=int(participant.draws),
                losses=int(participant.losses),
                goals_for=int(participant.goals_for),
                goals_against=int(participant.goals_against),
                goal_diff=int(participant.goal_diff),
                points=int(participant.points),
                entry_fee_minor=int(competition.entry_fee_minor),
                currency=str(competition.currency),
                scheduled_start_at=competition.scheduled_start_at,
                updated_at=max(competition.updated_at, participant.updated_at),
            )
            for participant, competition in rows
        ]
        pending_entries = int(
            self.session.scalar(
                select(func.count(CompetitionEntry.id)).where(
                    CompetitionEntry.club_id == club_id,
                    CompetitionEntry.status.in_(("pending", "invited", "requested")),
                )
            )
            or 0
        )
        upcoming_matches = int(
            self.session.scalar(
                select(func.count(CompetitionMatch.id)).where(
                    or_(CompetitionMatch.home_club_id == club_id, CompetitionMatch.away_club_id == club_id),
                    CompetitionMatch.status.notin_(("completed", "cancelled", "abandoned")),
                )
            )
            or 0
        )
        active_count = sum(1 for item in items if item.status not in {"completed", "cancelled", "settled"})
        return ClubV2CompetitionsView(
            active_count=active_count,
            pending_entries_count=pending_entries,
            upcoming_match_count=upcoming_matches,
            items=items,
        )

    def _wallet(self, club: ClubProfile) -> ClubV2WalletView:
        balances = [
            self._wallet_balance(club.owner_user_id, unit=LedgerUnit.CREDIT),
            self._wallet_balance(club.owner_user_id, unit=LedgerUnit.COIN),
        ]
        credit_balance = next(
            (item.total_balance for item in balances if item.unit == LedgerUnit.CREDIT.value), Decimal("0")
        )
        return ClubV2WalletView(
            owner_user_id=club.owner_user_id,
            wallet_credits=max(0, int(credit_balance)),
            balances=balances,
        )

    def _wallet_balance(self, owner_user_id: str, *, unit: LedgerUnit) -> ClubV2WalletBalanceView:
        available_accounts = self._wallet_accounts(owner_user_id, unit=unit, kind=LedgerAccountKind.USER)
        reserved_accounts = self._wallet_accounts(owner_user_id, unit=unit, kind=LedgerAccountKind.ESCROW)
        available = sum((self._account_balance(account) for account in available_accounts), _DECIMAL_ZERO)
        reserved = sum((self._account_balance(account) for account in reserved_accounts), _DECIMAL_ZERO)
        return ClubV2WalletBalanceView(
            unit=unit.value,
            available_balance=available,
            reserved_balance=reserved,
            total_balance=available + reserved,
        )

    def _ranking(self, club_id: str) -> ClubV2RankingView:
        reputation = self.session.scalar(select(ClubReputationProfile).where(ClubReputationProfile.club_id == club_id))
        events = list(
            self.session.scalars(
                select(ClubRankingEvent)
                .where(ClubRankingEvent.club_id == club_id)
                .order_by(ClubRankingEvent.created_at.asc(), ClubRankingEvent.id.asc())
            ).all()
        )
        ranking_points = sum((Decimal(event.final_points_delta or 0) for event in events), _DECIMAL_ZERO)
        wins = sum(1 for event in events if event.event_kind == "match_result" and event.result == "win")
        draws = sum(1 for event in events if event.event_kind == "match_result" and event.result == "draw")
        losses = sum(1 for event in events if event.event_kind == "match_result" and event.result == "loss")
        form = [
            {"win": "W", "draw": "D", "loss": "L"}.get(event.result, "")
            for event in events
            if event.event_kind == "match_result"
        ]
        open_flags = int(
            self.session.scalar(
                select(func.count(ClubRankingAbuseFlag.id)).where(
                    ClubRankingAbuseFlag.club_id == club_id,
                    ClubRankingAbuseFlag.status == "open",
                )
            )
            or 0
        )
        trophies = sum(
            1
            for event in events
            if event.event_kind == "placement_bonus" and int((event.metadata_json or {}).get("placement") or 0) == 1
        )
        return ClubV2RankingView(
            reputation_score=int(reputation.current_score if reputation is not None else 0),
            highest_reputation_score=int(reputation.highest_score if reputation is not None else 0),
            prestige_tier=str(reputation.prestige_tier if reputation is not None else "Local"),
            ranking_points=ranking_points,
            global_rank=self._global_rank(club_id),
            wins=wins,
            draws=draws,
            losses=losses,
            trophies=trophies,
            recent_form="".join(form[-5:]),
            event_count=len(events),
            open_integrity_flags=open_flags,
        )

    def _facilities(self, *, club: ClubProfile, viewer: User) -> ClubInfraDashboardResponse:
        payload = ClubInfraService(self.session).dashboard_for_club(club_id=club.id, viewer=viewer)
        stadium = payload["stadium"]
        facilities = payload["facilities"]
        token = payload["supporter_token"]
        holding = payload.get("my_holding")
        return ClubInfraDashboardResponse(
            club_id=str(payload["club_id"]),
            club_name=str(payload["club_name"]),
            stadium={
                "id": stadium.id,
                "club_id": stadium.club_id,
                "name": stadium.name,
                "level": stadium.level,
                "capacity": stadium.capacity,
                "theme_key": stadium.theme_key,
                "gift_retention_bonus_bps": stadium.gift_retention_bonus_bps,
                "revenue_multiplier_bps": stadium.revenue_multiplier_bps,
                "prestige_bonus_bps": stadium.prestige_bonus_bps,
            },
            facilities={
                "id": facilities.id,
                "club_id": facilities.club_id,
                "training_level": facilities.training_level,
                "academy_level": facilities.academy_level,
                "medical_level": facilities.medical_level,
                "branding_level": facilities.branding_level,
                "upkeep_cost_fancoin": facilities.upkeep_cost_fancoin,
            },
            supporter_token={
                "id": token.id,
                "club_id": token.club_id,
                "token_name": token.token_name,
                "token_symbol": token.token_symbol,
                "circulating_supply": token.circulating_supply,
                "holder_count": token.holder_count,
                "influence_points": token.influence_points,
                "status": self._value(token.status),
                "description": token.description,
                "metadata_json": token.metadata_json,
            },
            my_holding=(
                None
                if holding is None
                else {
                    "id": holding.id,
                    "club_id": holding.club_id,
                    "user_id": holding.user_id,
                    "token_balance": holding.token_balance,
                    "influence_points": holding.influence_points,
                    "is_founding_supporter": holding.is_founding_supporter,
                    "metadata_json": holding.metadata_json,
                }
            ),
            projected_matchday_revenue_coin=payload["projected_matchday_revenue_coin"],
            projected_gift_retention_ratio=payload["projected_gift_retention_ratio"],
            prestige_index=int(payload["prestige_index"]),
            insights=list(payload["insights"]),
        )

    def _transfers(self, club_id: str) -> ClubV2TransfersView:
        listings = list(
            self.session.scalars(
                select(TransferListing)
                .where(or_(TransferListing.selling_club_id == club_id, TransferListing.highest_bidder_id == club_id))
                .order_by(TransferListing.updated_at.desc())
                .limit(20)
            ).all()
        )
        listing_by_id = {listing.id: listing for listing in listings}
        bids = list(
            self.session.scalars(
                select(TransferListingBid)
                .where(TransferListingBid.bidder_club_id == club_id)
                .order_by(TransferListingBid.updated_at.desc())
                .limit(20)
            ).all()
        )
        missing_listing_ids = [bid.listing_id for bid in bids if bid.listing_id not in listing_by_id]
        if missing_listing_ids:
            for listing in self.session.scalars(
                select(TransferListing).where(TransferListing.id.in_(missing_listing_ids))
            ).all():
                listing_by_id[listing.id] = listing
        offers = list(
            self.session.scalars(
                select(TransferHubOffer)
                .where(or_(TransferHubOffer.seller_club_id == club_id, TransferHubOffer.bidder_club_id == club_id))
                .order_by(TransferHubOffer.updated_at.desc())
                .limit(20)
            ).all()
        )
        requests = list(
            self.session.scalars(
                select(TransferRequest)
                .where(TransferRequest.current_club_id == club_id)
                .order_by(TransferRequest.updated_at.desc())
                .limit(10)
            ).all()
        )
        player_ids = {listing.player_id for listing in list(listing_by_id.values()) if listing.player_id} | {
            request.player_id for request in requests if request.player_id
        }
        player_names = self._player_names(player_ids)
        activity: list[ClubV2TransferActivityView] = []
        for listing in listings:
            direction = "outgoing" if listing.selling_club_id == club_id else "incoming"
            activity.append(
                ClubV2TransferActivityView(
                    id=listing.id,
                    kind="listing",
                    status=listing.status,
                    player_id=listing.player_id,
                    player_name=player_names.get(listing.player_id),
                    amount_credits=Decimal(listing.current_highest_bid or listing.base_price or 0),
                    counterparty_club_id=(
                        listing.highest_bidder_id if direction == "outgoing" else listing.selling_club_id
                    ),
                    direction=direction,
                    updated_at=listing.updated_at,
                )
            )
        for bid in bids:
            listing = listing_by_id.get(bid.listing_id)
            activity.append(
                ClubV2TransferActivityView(
                    id=bid.id,
                    kind="bid",
                    status="submitted",
                    player_id=listing.player_id if listing is not None else None,
                    player_name=player_names.get(listing.player_id) if listing is not None else None,
                    amount_credits=Decimal(bid.amount or 0),
                    counterparty_club_id=listing.selling_club_id if listing is not None else None,
                    direction="incoming",
                    updated_at=bid.updated_at,
                )
            )
        for offer in offers:
            listing = listing_by_id.get(offer.listing_id)
            direction = "outgoing" if offer.seller_club_id == club_id else "incoming"
            activity.append(
                ClubV2TransferActivityView(
                    id=offer.id,
                    kind="offer",
                    status=offer.status,
                    player_id=listing.player_id if listing is not None else None,
                    player_name=player_names.get(listing.player_id) if listing is not None else None,
                    amount_credits=Decimal(offer.cash_amount or 0),
                    counterparty_club_id=offer.bidder_club_id if direction == "outgoing" else offer.seller_club_id,
                    direction=direction,
                    updated_at=offer.updated_at,
                )
            )
        for request in requests:
            activity.append(
                ClubV2TransferActivityView(
                    id=request.id,
                    kind="request",
                    status=request.status,
                    player_id=request.player_id,
                    player_name=player_names.get(request.player_id),
                    amount_credits=None,
                    counterparty_club_id=None,
                    direction="outgoing",
                    updated_at=request.updated_at,
                )
            )
        activity.sort(key=lambda item: item.updated_at, reverse=True)
        watchlist_count = int(
            self.session.scalar(
                select(func.count(MarketWatchlistEntry.id)).where(MarketWatchlistEntry.club_id == club_id)
            )
            or 0
        )
        return ClubV2TransfersView(
            outgoing_listing_count=sum(1 for listing in listings if listing.selling_club_id == club_id),
            incoming_bid_count=len(bids),
            outgoing_offer_count=sum(1 for offer in offers if offer.seller_club_id == club_id),
            incoming_offer_count=sum(1 for offer in offers if offer.bidder_club_id == club_id),
            transfer_request_count=len(requests),
            watchlist_count=watchlist_count,
            activity=activity[:20],
        )

    def _wallet_accounts(self, owner_user_id: str, *, unit: LedgerUnit, kind: LedgerAccountKind) -> list[LedgerAccount]:
        return list(
            self.session.scalars(
                select(LedgerAccount).where(
                    LedgerAccount.owner_user_id == owner_user_id,
                    LedgerAccount.unit == unit,
                    LedgerAccount.kind == kind,
                    LedgerAccount.is_active.is_(True),
                )
            ).all()
        )

    def _account_balance(self, account: LedgerAccount) -> Decimal:
        projection = self.session.scalar(
            select(LedgerBalanceProjection).where(LedgerBalanceProjection.account_id == account.id)
        )
        if projection is not None:
            return Decimal(projection.balance or 0)
        total = self.session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(LedgerEntry.account_id == account.id)
        )
        return Decimal(total or 0)

    def _latest_market_snapshots(self, player_ids: list[str]) -> dict[str, PlayerMarketValueSnapshot]:
        if not player_ids:
            return {}
        snapshots: dict[str, PlayerMarketValueSnapshot] = {}
        rows = self.session.scalars(
            select(PlayerMarketValueSnapshot)
            .where(PlayerMarketValueSnapshot.player_id.in_(player_ids))
            .order_by(PlayerMarketValueSnapshot.player_id.asc(), PlayerMarketValueSnapshot.as_of.desc())
        ).all()
        for snapshot in rows:
            snapshots.setdefault(snapshot.player_id, snapshot)
        return snapshots

    def _player_value_credits(
        self,
        player: Player,
        latest_snapshot: PlayerMarketValueSnapshot | None,
    ) -> tuple[int, str | None]:
        if latest_snapshot is not None:
            for field_name in ("avg_trade_price_credits", "last_trade_price_credits", "listing_floor_price_credits"):
                raw_value = getattr(latest_snapshot, field_name)
                if raw_value is not None:
                    return max(0, int(Decimal(raw_value))), f"player_market_value_snapshots.{field_name}"
        currency = (player.market_reference_currency or "").strip().lower()
        if currency in {"credit", "credits", "fancoin", "fan_coin", "coin"} and player.current_market_reference_value:
            return (
                max(0, int(Decimal(str(player.current_market_reference_value)))),
                "ingestion_players.current_market_reference_value",
            )
        return 0, None

    def _countries_by_id(self, country_ids: list[str]) -> dict[str, Country]:
        if not country_ids:
            return {}
        return {
            country.id: country
            for country in self.session.scalars(select(Country).where(Country.id.in_(set(country_ids)))).all()
        }

    def _player_names(self, player_ids: set[str]) -> dict[str, str]:
        if not player_ids:
            return {}
        return {
            player.id: player.canonical_display_name or player.full_name
            for player in self.session.scalars(select(Player).where(Player.id.in_(player_ids))).all()
        }

    def _global_rank(self, club_id: str) -> int | None:
        rows = self.session.execute(
            select(
                ClubRankingEvent.club_id,
                func.coalesce(func.sum(ClubRankingEvent.final_points_delta), 0),
                func.max(ClubRankingEvent.updated_at),
            ).group_by(ClubRankingEvent.club_id)
        ).all()
        if not rows:
            return None
        ranked = sorted(
            rows,
            key=lambda row: (Decimal(row[1] or 0), row[2]),
            reverse=True,
        )
        for index, row in enumerate(ranked, start=1):
            if row[0] == club_id:
                return index
        return None

    @staticmethod
    def _country_label(country: Country | None) -> str | None:
        if country is None:
            return None
        return country.name or country.alpha3_code or country.alpha2_code or country.fifa_code

    @staticmethod
    def _age(born_on: date | None, *, generated_on: date) -> int | None:
        if born_on is None:
            return None
        years = generated_on.year - born_on.year
        if (generated_on.month, generated_on.day) < (born_on.month, born_on.day):
            years -= 1
        return max(0, years)

    @staticmethod
    def _position_group(position: str | None) -> str:
        value = (position or "").strip().lower()
        if not value:
            return "unknown"
        if value in {"gk", "goalkeeper"}:
            return "goalkeeper"
        if value in {"cb", "lb", "rb", "lwb", "rwb", "defender"} or value.startswith("d"):
            return "defender"
        if value in {"dm", "cm", "am", "lm", "rm", "midfielder"} or value.endswith("m"):
            return "midfielder"
        if value in {"st", "cf", "fw", "lw", "rw", "forward", "winger"}:
            return "forward"
        return "unknown"

    @staticmethod
    def _value(value: Any) -> str:
        return str(value.value if hasattr(value, "value") else value)
