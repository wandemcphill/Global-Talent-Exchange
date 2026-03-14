from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.economy.service import EconomyConfigService
from backend.app.models.media_engine import MatchRevenueSnapshot, MatchView, PremiumVideoPurchase
from backend.app.models.user import User


class MediaEngineError(ValueError):
    pass


@dataclass(slots=True)
class MediaEngineService:
    session: Session

    def record_view(self, *, actor: User, match_key: str, competition_key: str | None, watch_seconds: int, premium_unlocked: bool) -> MatchView:
        item = MatchView(
            user_id=actor.id,
            match_key=match_key.strip(),
            competition_key=(competition_key or '').strip() or None,
            view_date_key=datetime.now(UTC).date().isoformat(),
            watch_seconds=watch_seconds,
            premium_unlocked=premium_unlocked,
            metadata_json={'watch_seconds': watch_seconds},
        )
        self.session.add(item)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise MediaEngineError('A view for this match has already been recorded today for this user.') from exc
        return item

    def purchase_video(self, *, actor: User, match_key: str, competition_key: str | None) -> PremiumVideoPurchase:
        existing = self.session.scalar(select(PremiumVideoPurchase).where(PremiumVideoPurchase.user_id == actor.id, PremiumVideoPurchase.match_key == match_key))
        if existing is not None:
            return existing
        pricing = {item.service_key: item for item in EconomyConfigService(self.session).list_service_pricing(active_only=False)}
        rule = pricing.get('premium-video-view')
        purchase = PremiumVideoPurchase(
            user_id=actor.id,
            match_key=match_key.strip(),
            competition_key=(competition_key or '').strip() or None,
            price_coin=rule.price_coin if rule is not None else Decimal('2.5000'),
            price_fancoin_equivalent=rule.price_fancoin_equivalent if rule is not None else Decimal('250.0000'),
            metadata_json={'unlock': 'premium_highlight'},
        )
        self.session.add(purchase)
        self.session.flush()
        return purchase

    def list_purchases(self, *, actor: User) -> list[PremiumVideoPurchase]:
        return list(self.session.scalars(select(PremiumVideoPurchase).where(PremiumVideoPurchase.user_id == actor.id).order_by(PremiumVideoPurchase.created_at.desc())).all())

    def build_snapshot(self, *, match_key: str, competition_key: str | None = None, home_club_id: str | None = None, away_club_id: str | None = None) -> MatchRevenueSnapshot:
        view_count = int(self.session.scalar(select(func.count()).select_from(MatchView).where(MatchView.match_key == match_key)) or 0)
        premium_count = int(self.session.scalar(select(func.count()).select_from(PremiumVideoPurchase).where(PremiumVideoPurchase.match_key == match_key)) or 0)
        premium_revenue = self.session.scalar(select(func.coalesce(func.sum(PremiumVideoPurchase.price_coin), 0)).where(PremiumVideoPurchase.match_key == match_key)) or Decimal('0.0000')
        ad_revenue = Decimal(view_count) * Decimal('0.0100')
        total = (Decimal(premium_revenue) + ad_revenue).quantize(Decimal('0.0001'))
        home_share = (total * Decimal('0.8')).quantize(Decimal('0.0001'))
        away_share = (total - home_share).quantize(Decimal('0.0001'))
        snapshot = self.session.scalar(select(MatchRevenueSnapshot).where(MatchRevenueSnapshot.match_key == match_key))
        if snapshot is None:
            snapshot = MatchRevenueSnapshot(match_key=match_key.strip())
            self.session.add(snapshot)
        snapshot.competition_key = (competition_key or '').strip() or snapshot.competition_key
        snapshot.home_club_id = home_club_id or snapshot.home_club_id
        snapshot.away_club_id = away_club_id or snapshot.away_club_id
        snapshot.total_views = view_count
        snapshot.premium_purchases = premium_count
        snapshot.total_revenue_coin = total
        snapshot.home_club_share_coin = home_share
        snapshot.away_club_share_coin = away_share
        snapshot.metadata_json = {'ad_revenue_coin': str(ad_revenue), 'revenue_split': {'home': '80%', 'away': '20%'}}
        self.session.flush()
        return snapshot
