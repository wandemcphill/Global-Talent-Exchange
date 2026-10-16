from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.market.models import ListingStatus, OfferStatus, TradeIntentStatus, utcnow
from app.market.read_models import MarketSummaryReadModel


@dataclass(slots=True)
class MarketSummaryProjector:
    session_factory: sessionmaker[Session]

    def rebuild_asset_summary(
        self,
        *,
        asset_id: str,
        listings: tuple,
        offers: tuple,
        trade_intents: tuple,
    ) -> None:
        open_listings = [listing for listing in listings if listing.status == ListingStatus.OPEN]
        pending_offers = [offer for offer in offers if offer.status == OfferStatus.PENDING]
        active_trade_intents = [intent for intent in trade_intents if intent.status == TradeIntentStatus.ACTIVE]
        last_activity_candidates = [
            *(listing.updated_at for listing in listings),
            *(offer.updated_at for offer in offers),
            *(intent.updated_at for intent in trade_intents),
        ]
        last_activity_at = max(last_activity_candidates) if last_activity_candidates else utcnow()
        open_listing = max(open_listings, key=lambda item: item.updated_at) if open_listings else None
        best_offer_price = max((offer.cash_amount for offer in pending_offers), default=None)

        with self.session_factory() as session:
            summary = session.get(MarketSummaryReadModel, asset_id)
            if summary is None:
                summary = MarketSummaryReadModel(asset_id=asset_id, last_activity_at=last_activity_at)
                session.add(summary)
            summary.open_listing_id = open_listing.listing_id if open_listing is not None else None
            summary.open_listing_type = open_listing.listing_type.value if open_listing is not None else None
            summary.seller_user_id = open_listing.seller_user_id if open_listing is not None else None
            summary.ask_price = open_listing.ask_price if open_listing is not None else None
            summary.pending_offer_count = len(pending_offers)
            summary.best_offer_price = best_offer_price
            summary.active_trade_intent_count = len(active_trade_intents)
            summary.last_activity_at = last_activity_at
            session.commit()
