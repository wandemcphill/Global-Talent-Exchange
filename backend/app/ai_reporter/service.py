from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai_reporter.schemas import AIReporterRunResponse, AIReporterStoryView
from app.ingestion.models import Player
from app.models.base import utcnow
from app.models.card_access import CardLoanListing
from app.models.club_profile import ClubProfile
from app.models.club_sale_market import ClubSaleListing, ClubSaleOffer, ClubSaleTransfer
from app.models.competition import UserCompetition
from app.models.manager_market import ManagerCatalogEntry, ManagerHolding, ManagerTradeListing
from app.models.player_cards import PlayerCard, PlayerCardListing
from app.models.regen import RegenAward, RegenProfile
from app.models.story_feed import StoryFeedItem
from app.models.wallet import LedgerUnit
from app.story_feed_engine.service import StoryFeedService

REPORTER_NAME = "GTEX Wire"
AI_PROVIDER = "local-template-reporter"
COST_TIER = "zero-cost"
DEFAULT_BEATS = (
    "regen_awards",
    "regen_rising",
    "transfer_listings",
    "loan_listings",
    "manager_market",
    "club_sales",
    "competition_news",
)
BEAT_STORY_TYPES = {
    "regen_awards": ("ai_reporter_regen_award",),
    "regen_rising": ("ai_reporter_regen_rising",),
    "transfer_listings": ("ai_reporter_transfer_listing",),
    "loan_listings": ("ai_reporter_loan_listing",),
    "manager_market": ("ai_reporter_manager_market",),
    "club_sales": (
        "ai_reporter_club_sale",
        "ai_reporter_club_sale_listing",
        "ai_reporter_club_sale_handshake",
    ),
    "competition_news": ("ai_reporter_competition_news",),
}


@dataclass(frozen=True, slots=True)
class ReporterDraft:
    story_type: str
    title: str
    body: str
    subject_type: str | None = None
    subject_id: str | None = None
    country_code: str | None = None
    metadata_json: dict[str, Any] | None = None
    featured: bool = False


@dataclass(slots=True)
class AIReporterService:
    session: Session

    def run_daily_digest(
        self,
        *,
        beats: list[str] | None = None,
        limit_per_beat: int = 3,
        dry_run: bool = False,
    ) -> AIReporterRunResponse:
        normalized_beats = tuple(beats or DEFAULT_BEATS)
        drafts: list[ReporterDraft] = []
        for beat in normalized_beats:
            drafts.extend(self._drafts_for_beat(beat, limit=max(1, min(limit_per_beat, 10))))

        items: list[AIReporterStoryView] = []
        skipped = 0
        story_service = StoryFeedService(self.session)
        for draft in drafts:
            if self._already_reported(draft):
                skipped += 1
                continue
            if dry_run:
                items.append(self._draft_view(draft))
                continue
            item = story_service.publish(
                story_type=draft.story_type,
                title=draft.title,
                body=draft.body,
                audience="public",
                subject_type=draft.subject_type,
                subject_id=draft.subject_id,
                country_code=draft.country_code,
                metadata_json=self._metadata(draft),
                featured=draft.featured,
                published_by_user_id=None,
            )
            items.append(self._item_view(item))
        return AIReporterRunResponse(
            reporter_name=REPORTER_NAME,
            ai_provider=AI_PROVIDER,
            cost_tier=COST_TIER,
            generated_count=len(items),
            skipped_duplicate_count=skipped,
            dry_run=dry_run,
            items=items,
        )

    def list_reporter_feed(self, *, limit: int = 50, beat: str | None = None) -> list[AIReporterStoryView]:
        stmt = select(StoryFeedItem).where(StoryFeedItem.story_type.like("ai_reporter_%"))
        if beat:
            story_types = BEAT_STORY_TYPES.get(beat.strip().lower(), ())
            if story_types:
                stmt = stmt.where(StoryFeedItem.story_type.in_(story_types))
        stmt = stmt.order_by(StoryFeedItem.featured.desc(), StoryFeedItem.created_at.desc()).limit(max(1, min(limit, 100)))
        return [self._item_view(item) for item in self.session.scalars(stmt).all()]

    def _drafts_for_beat(self, beat: str, *, limit: int) -> list[ReporterDraft]:
        normalized = beat.strip().lower()
        if normalized == "regen_awards":
            return self._regen_award_drafts(limit=limit)
        if normalized == "regen_rising":
            return self._regen_rising_drafts(limit=limit)
        if normalized == "transfer_listings":
            return self._transfer_listing_drafts(limit=limit)
        if normalized == "loan_listings":
            return self._loan_listing_drafts(limit=limit)
        if normalized == "manager_market":
            return self._manager_market_drafts(limit=limit)
        if normalized == "club_sales":
            return self._club_sale_drafts(limit=limit)
        if normalized == "competition_news":
            return self._competition_drafts(limit=limit)
        return []

    def _already_reported(self, draft: ReporterDraft) -> bool:
        if not draft.subject_id:
            return False
        cutoff = utcnow() - timedelta(hours=20)
        return (
            self.session.scalar(
                select(StoryFeedItem.id)
                .where(
                    StoryFeedItem.story_type == draft.story_type,
                    StoryFeedItem.subject_id == draft.subject_id,
                    StoryFeedItem.created_at >= cutoff,
                )
                .limit(1)
            )
            is not None
        )

    def _regen_award_drafts(self, *, limit: int) -> list[ReporterDraft]:
        rows = self.session.execute(
            select(RegenAward, RegenProfile, Player, ClubProfile)
            .join(RegenProfile, RegenAward.regen_id == RegenProfile.id)
            .join(Player, RegenProfile.player_id == Player.id)
            .outerjoin(ClubProfile, RegenAward.club_id == ClubProfile.id)
            .order_by(RegenAward.awarded_at.desc(), RegenAward.impact_score.desc().nullslast())
            .limit(limit)
        ).all()
        drafts: list[ReporterDraft] = []
        for award, regen, player, club in rows:
            club_name = club.club_name if club is not None else "the regen circuit"
            player_name = self._player_name(player)
            title = f"{player_name} takes {award.award_name}"
            body = (
                f"{REPORTER_NAME} has {player_name} collecting {award.award_name} for {club_name}. "
                f"The regen desk rates the story at GSI {regen.current_gsi}, with scouts now watching the next jump."
            )
            drafts.append(
                ReporterDraft(
                    story_type="ai_reporter_regen_award",
                    title=title,
                    body=body,
                    subject_type="regen_award",
                    subject_id=award.id,
                    country_code=regen.birth_country_code,
                    metadata_json={
                        "beat": "regen_awards",
                        "regen_id": regen.id,
                        "player_id": player.id,
                        "club_id": club.id if club is not None else None,
                        "award_code": award.award_code,
                        "impact_score": award.impact_score,
                    },
                    featured=bool((award.impact_score or 0) >= 80),
                )
            )
        return drafts

    def _regen_rising_drafts(self, *, limit: int) -> list[ReporterDraft]:
        rows = self.session.execute(
            select(RegenProfile, Player, ClubProfile)
            .join(Player, RegenProfile.player_id == Player.id)
            .outerjoin(ClubProfile, RegenProfile.generated_for_club_id == ClubProfile.id)
            .where(RegenProfile.status == "active")
            .order_by(RegenProfile.current_gsi.desc(), RegenProfile.generated_at.desc())
            .limit(limit)
        ).all()
        drafts: list[ReporterDraft] = []
        for regen, player, club in rows:
            potential = dict(regen.potential_range_json or {}).get("maximum") or dict(regen.potential_range_json or {}).get("max")
            club_name = club.club_name if club is not None else "an unsigned pathway"
            player_name = self._player_name(player)
            title = f"Rare-gem watch: {player_name}"
            body = (
                f"{player_name}, a {regen.primary_position} out of {club_name}, is getting heavier regen coverage today. "
                f"Current GSI is {regen.current_gsi}"
                + (f" with a projected ceiling near {potential}" if potential else "")
                + ". This is the kind of profile managers circle before the room gets noisy."
            )
            drafts.append(
                ReporterDraft(
                    story_type="ai_reporter_regen_rising",
                    title=title,
                    body=body,
                    subject_type="regen",
                    subject_id=regen.id,
                    country_code=regen.birth_country_code,
                    metadata_json={
                        "beat": "regen_rising",
                        "regen_id": regen.id,
                        "player_id": player.id,
                        "club_id": club.id if club is not None else None,
                        "gsi": regen.current_gsi,
                        "potential": potential,
                    },
                    featured=regen.current_gsi >= 85,
                )
            )
        return drafts

    def _transfer_listing_drafts(self, *, limit: int) -> list[ReporterDraft]:
        rows = self.session.execute(
            select(PlayerCardListing, PlayerCard, Player)
            .join(PlayerCard, PlayerCardListing.player_card_id == PlayerCard.id)
            .join(Player, PlayerCard.player_id == Player.id)
            .where(PlayerCardListing.status == "open")
            .order_by(PlayerCardListing.updated_at.desc())
            .limit(limit)
        ).all()
        drafts: list[ReporterDraft] = []
        for listing, card, player in rows:
            player_name = self._player_name(player)
            price = self._amount(listing.price_per_card_credits)
            title = f"Transfer list: {player_name} appears at {price} GTEX Coin"
            body = (
                f"{player_name} has hit the user-to-user market through card {card.edition_code}. "
                f"The ask is {price} GTEX Coin, and settlement on this desk is GTEX Coin only."
            )
            drafts.append(
                ReporterDraft(
                    story_type="ai_reporter_transfer_listing",
                    title=title,
                    body=body,
                    subject_type="player_card_listing",
                    subject_id=listing.listing_id,
                    country_code=None,
                    metadata_json={
                        "beat": "transfer_listings",
                        "player_id": player.id,
                        "player_card_id": card.id,
                        "listing_id": listing.listing_id,
                        "price_gtex_coin": price,
                        "asset_origin": "regen" if not player.is_real_player else "real_player",
                    },
                    featured=not bool(player.is_real_player),
                )
            )
        return drafts

    def _loan_listing_drafts(self, *, limit: int) -> list[ReporterDraft]:
        rows = self.session.execute(
            select(CardLoanListing, PlayerCard, Player)
            .join(PlayerCard, CardLoanListing.player_card_id == PlayerCard.id)
            .join(Player, PlayerCard.player_id == Player.id)
            .where(CardLoanListing.status == "open", CardLoanListing.available_slots > 0)
            .order_by(CardLoanListing.updated_at.desc())
            .limit(limit)
        ).all()
        drafts: list[ReporterDraft] = []
        for listing, card, player in rows:
            player_name = self._player_name(player)
            fee = self._amount(listing.loan_fee_credits)
            title = f"Loan desk: {player_name} is available for {listing.duration_days} days"
            body = (
                f"{player_name} can be borrowed for {listing.duration_days} days at {fee} GTEX Coin. "
                f"Clubs needing a quick tactical lift will be watching this listing."
            )
            drafts.append(
                ReporterDraft(
                    story_type="ai_reporter_loan_listing",
                    title=title,
                    body=body,
                    subject_type="card_loan_listing",
                    subject_id=listing.id,
                    metadata_json={
                        "beat": "loan_listings",
                        "player_id": player.id,
                        "player_card_id": card.id,
                        "loan_fee_gtex_coin": fee,
                        "duration_days": listing.duration_days,
                    },
                    featured=not bool(player.is_real_player),
                )
            )
        return drafts

    def _manager_market_drafts(self, *, limit: int) -> list[ReporterDraft]:
        rows = self.session.execute(
            select(ManagerTradeListing, ManagerHolding, ManagerCatalogEntry)
            .join(ManagerHolding, ManagerTradeListing.asset_id == ManagerHolding.asset_id)
            .join(ManagerCatalogEntry, ManagerHolding.manager_id == ManagerCatalogEntry.manager_id)
            .where(ManagerTradeListing.status == "open")
            .order_by(ManagerTradeListing.updated_at.desc())
            .limit(limit)
        ).all()
        drafts: list[ReporterDraft] = []
        for listing, holding, manager in rows:
            price = self._amount(listing.asking_price_credits)
            tactics = ", ".join(list(manager.tactics or [])[:2]) or manager.mentality
            title = f"Manager card watch: {manager.display_name}"
            body = (
                f"{manager.display_name} is live on the manager market at {price} GTEX Coin. "
                f"The tactical fit reads {tactics}, with traits that could swing close tournament ties."
            )
            drafts.append(
                ReporterDraft(
                    story_type="ai_reporter_manager_market",
                    title=title,
                    body=body,
                    subject_type="manager_listing",
                    subject_id=listing.listing_id,
                    metadata_json={
                        "beat": "manager_market",
                        "manager_id": manager.manager_id,
                        "asset_id": holding.asset_id,
                        "price_gtex_coin": price,
                        "rarity": manager.rarity,
                    },
                    featured=manager.rarity.lower() in {"legendary", "mythic", "elite"},
                )
            )
        return drafts

    def _club_sale_drafts(self, *, limit: int) -> list[ReporterDraft]:
        drafts: list[ReporterDraft] = []
        transfer_rows = self.session.execute(
            select(ClubSaleTransfer, ClubProfile)
            .join(ClubProfile, ClubSaleTransfer.club_id == ClubProfile.id)
            .where(ClubSaleTransfer.status == "settled")
            .order_by(ClubSaleTransfer.created_at.desc())
            .limit(limit)
        ).all()
        for transfer, club in transfer_rows:
            price = self._amount(transfer.executed_sale_price)
            drafts.append(
                ReporterDraft(
                    story_type="ai_reporter_club_sale",
                    title=f"New ownership at {club.club_name}",
                    body=(
                        f"{club.club_name} has changed hands for {price} GTEX Coin. "
                        f"{REPORTER_NAME} welcomes the new owner and will track how the club moves from {club.club_address or 'its home base'}."
                    ),
                    subject_type="club_sale_transfer",
                    subject_id=transfer.transfer_id,
                    country_code=club.country_code,
                    metadata_json={
                        "beat": "club_sales",
                        "club_id": club.id,
                        "transfer_id": transfer.transfer_id,
                        "price_gtex_coin": price,
                    },
                    featured=True,
                )
            )

        listing_rows = self.session.execute(
            select(ClubSaleListing, ClubProfile)
            .join(ClubProfile, ClubSaleListing.club_id == ClubProfile.id)
            .where(ClubSaleListing.status.in_(("active", "under_offer")))
            .order_by(ClubSaleListing.updated_at.desc())
            .limit(limit)
        ).all()
        for listing, club in listing_rows:
            price = self._amount(listing.asking_price)
            state = "under offer" if str(listing.status) == "under_offer" else "open to offers"
            drafts.append(
                ReporterDraft(
                    story_type="ai_reporter_club_sale_listing",
                    title=f"Club sale desk: {club.club_name} is {state}",
                    body=(
                        f"{club.club_name} is {state} at {price} GTEX Coin. "
                        f"The club address is {club.club_address or 'not yet published'}, and any sale settles in GTEX Coin."
                    ),
                    subject_type="club_sale_listing",
                    subject_id=listing.listing_id,
                    country_code=club.country_code,
                    metadata_json={
                        "beat": "club_sales",
                        "club_id": club.id,
                        "listing_id": listing.listing_id,
                        "asking_price_gtex_coin": price,
                    },
                    featured=str(listing.status) == "under_offer",
                )
            )

        offer_rows = self.session.execute(
            select(ClubSaleOffer, ClubProfile)
            .join(ClubProfile, ClubSaleOffer.club_id == ClubProfile.id)
            .where(ClubSaleOffer.status == "accepted")
            .order_by(ClubSaleOffer.accepted_at.desc().nullslast(), ClubSaleOffer.updated_at.desc())
            .limit(limit)
        ).all()
        for offer, club in offer_rows:
            price = self._amount(offer.offered_price)
            drafts.append(
                ReporterDraft(
                    story_type="ai_reporter_club_sale_handshake",
                    title=f"Handshake watch around {club.club_name}",
                    body=(
                        f"An accepted offer path is live for {club.club_name} around {price} GTEX Coin. "
                        f"No private message is being published, but the market now knows a settlement route exists."
                    ),
                    subject_type="club_sale_offer",
                    subject_id=offer.offer_id,
                    country_code=club.country_code,
                    metadata_json={
                        "beat": "club_sales",
                        "club_id": club.id,
                        "offer_id": offer.offer_id,
                        "offer_price_gtex_coin": price,
                    },
                    featured=True,
                )
            )
        return drafts[: max(limit, 1) * 3]

    def _competition_drafts(self, *, limit: int) -> list[ReporterDraft]:
        rows = self.session.scalars(
            select(UserCompetition)
            .where(
                UserCompetition.status.in_(("registration", "open", "launched", "active", "running")),
                or_(UserCompetition.visibility == "public", UserCompetition.visibility.is_(None)),
            )
            .order_by(UserCompetition.updated_at.desc())
            .limit(limit)
        ).all()
        drafts: list[ReporterDraft] = []
        for competition in rows:
            fee = self._amount(Decimal(int(competition.entry_fee_minor or 0)) / Decimal("100"))
            title = f"Competition watch: {competition.name}"
            body = (
                f"{competition.name} is in {competition.status} stage with a {competition.format} format. "
                f"Entry is {fee} {competition.currency or LedgerUnit.COIN.value}, and the room is one result away from a storyline."
            )
            drafts.append(
                ReporterDraft(
                    story_type="ai_reporter_competition_news",
                    title=title,
                    body=body,
                    subject_type="competition",
                    subject_id=competition.id,
                    metadata_json={
                        "beat": "competition_news",
                        "competition_id": competition.id,
                        "format": competition.format,
                        "status": competition.status,
                        "currency": competition.currency,
                    },
                    featured=competition.status in {"launched", "active", "running"},
                )
            )
        return drafts

    def _metadata(self, draft: ReporterDraft) -> dict[str, Any]:
        metadata = dict(draft.metadata_json or {})
        metadata.update(
            {
                "reporter": REPORTER_NAME,
                "ai_provider": AI_PROVIDER,
                "cost_tier": COST_TIER,
                "generated_at": utcnow().isoformat(),
            }
        )
        return metadata

    def _draft_view(self, draft: ReporterDraft) -> AIReporterStoryView:
        return AIReporterStoryView(
            story_type=draft.story_type,
            title=draft.title,
            body=draft.body,
            subject_type=draft.subject_type,
            subject_id=draft.subject_id,
            country_code=draft.country_code,
            metadata_json=self._metadata(draft),
            featured=draft.featured,
            created_at=None,
        )

    @staticmethod
    def _item_view(item: StoryFeedItem) -> AIReporterStoryView:
        return AIReporterStoryView(
            id=item.id,
            story_type=item.story_type,
            audience=item.audience,
            title=item.title,
            body=item.body,
            subject_type=item.subject_type,
            subject_id=item.subject_id,
            country_code=item.country_code,
            metadata_json=dict(item.metadata_json or {}),
            featured=item.featured,
            created_at=item.created_at,
        )

    @staticmethod
    def _player_name(player: Player) -> str:
        return player.canonical_display_name or player.full_name or player.short_name or player.id

    @staticmethod
    def _amount(value: Any) -> str:
        return format(Decimal(str(value or 0)).quantize(Decimal("0.0001")), "f")
