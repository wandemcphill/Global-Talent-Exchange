from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.service import AnalyticsService
from app.club_identity.models.reputation import ClubReputationProfile
from app.ingestion.models import Player
from app.models.analytics_event import AnalyticsEvent
from app.models.club_profile import ClubProfile
from app.models.club_sponsor import ClubSponsor, SponsorOffer, SponsorOfferRule
from app.models.club_infra import ClubSupporterHolding, ClubSupporterToken
from app.models.competition_participant import CompetitionParticipant
from app.models.media_engine import MatchRevenueSnapshot
from app.models.user import User


@dataclass(frozen=True, slots=True)
class ClubSponsorMetricsSnapshot:
    club_id: str
    fan_count: int
    reputation_score: int
    prestige_tier: str
    club_valuation: float
    media_popularity: int
    competition_count: int
    rivalry_visibility: int
    competition_ids: tuple[str, ...]


class ClubSponsorOfferError(ValueError):
    pass


@dataclass(slots=True)
class ClubSponsorOfferService:
    session: Session
    analytics: AnalyticsService | None = None

    def __post_init__(self) -> None:
        if self.analytics is None:
            self.analytics = AnalyticsService()

    def list_offers(self, *, active_only: bool = True) -> list[SponsorOffer]:
        stmt = select(SponsorOffer).order_by(SponsorOffer.base_value_minor.desc(), SponsorOffer.created_at.desc())
        if active_only:
            stmt = stmt.where(SponsorOffer.is_active.is_(True), SponsorOffer.category_enabled.is_(True))
        return list(self.session.scalars(stmt).all())

    def create_offer(self, payload) -> SponsorOffer:
        offer = SponsorOffer(
            code=payload.code,
            offer_name=payload.offer_name,
            sponsor_name=payload.sponsor_name,
            category=payload.category,
            base_value_minor=payload.base_value_minor,
            currency=payload.currency,
            default_duration_months=payload.default_duration_months,
            approved_surfaces_json=list(payload.approved_surfaces_json),
            creative_url=payload.creative_url,
            category_enabled=payload.category_enabled,
            is_active=payload.is_active,
            metadata_json=dict(payload.metadata_json),
        )
        self.session.add(offer)
        self.session.flush()
        return offer

    def upsert_offer_rule(self, *, offer_id: str, payload) -> SponsorOfferRule:
        offer = self._require_offer(offer_id)
        rule = self.session.scalar(
            select(SponsorOfferRule)
            .where(SponsorOfferRule.sponsor_offer_id == offer.id)
            .order_by(SponsorOfferRule.updated_at.desc())
        )
        if rule is None:
            rule = SponsorOfferRule(sponsor_offer_id=offer.id)
            self.session.add(rule)

        rule.min_fan_count = payload.min_fan_count
        rule.min_reputation_score = payload.min_reputation_score
        rule.min_club_valuation = payload.min_club_valuation
        rule.min_media_popularity = payload.min_media_popularity
        rule.min_competition_count = payload.min_competition_count
        rule.min_rivalry_visibility = payload.min_rivalry_visibility
        rule.required_prestige_tier = payload.required_prestige_tier
        rule.competition_allowlist_json = list(payload.competition_allowlist_json)
        rule.metadata_json = dict(payload.metadata_json)
        rule.is_active = payload.is_active
        self.session.flush()
        return rule

    def set_category_enabled(self, *, category: str, enabled: bool) -> list[SponsorOffer]:
        offers = list(self.session.scalars(select(SponsorOffer).where(SponsorOffer.category == category)).all())
        for offer in offers:
            offer.category_enabled = enabled
        self.session.flush()
        return offers

    def evaluate_club_metrics(self, club_id: str) -> ClubSponsorMetricsSnapshot:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise ClubSponsorOfferError("Club was not found.")

        supporter_token = self.session.scalar(select(ClubSupporterToken).where(ClubSupporterToken.club_id == club_id))
        holdings_count = self.session.scalar(select(func.count(ClubSupporterHolding.id)).where(ClubSupporterHolding.club_id == club_id)) or 0
        fan_count = max(int(getattr(supporter_token, "holder_count", 0) or 0), int(holdings_count))

        reputation = self.session.scalar(select(ClubReputationProfile).where(ClubReputationProfile.club_id == club_id))
        reputation_score = int(getattr(reputation, "current_score", 0) or 0)
        prestige_tier = str(getattr(reputation, "prestige_tier", "Local") or "Local")

        club_valuation = float(
            self.session.scalar(
                select(func.coalesce(func.sum(Player.market_value_eur), 0)).where(Player.current_club_profile_id == club_id)
            )
            or 0
        )

        snapshots = list(
            self.session.scalars(
                select(MatchRevenueSnapshot).where(
                    (MatchRevenueSnapshot.home_club_id == club_id) | (MatchRevenueSnapshot.away_club_id == club_id)
                )
            ).all()
        )
        media_popularity = sum(int(snapshot.total_views or 0) for snapshot in snapshots)
        rivalry_visibility = sum(int((snapshot.metadata_json or {}).get("rivalry_visibility", 0) or 0) for snapshot in snapshots)

        participants = list(
            self.session.scalars(
                select(CompetitionParticipant).where(
                    CompetitionParticipant.club_id == club_id,
                    CompetitionParticipant.status.in_(("joined", "active", "completed")),
                )
            ).all()
        )
        competition_ids = tuple(participant.competition_id for participant in participants)

        return ClubSponsorMetricsSnapshot(
            club_id=club_id,
            fan_count=fan_count,
            reputation_score=reputation_score,
            prestige_tier=prestige_tier,
            club_valuation=club_valuation,
            media_popularity=media_popularity,
            competition_count=len(participants),
            rivalry_visibility=rivalry_visibility,
            competition_ids=competition_ids,
        )

    def list_eligible_offers(self, *, club_id: str) -> list[dict[str, Any]]:
        metrics = self.evaluate_club_metrics(club_id)
        offers = self.list_offers(active_only=True)
        return [self._eligibility_payload(offer, metrics) for offer in offers]

    def list_club_sponsors(self, *, club_id: str) -> list[ClubSponsor]:
        return list(
            self.session.scalars(
                select(ClubSponsor).where(ClubSponsor.club_id == club_id).order_by(ClubSponsor.created_at.desc())
            ).all()
        )

    def assign_offer_to_club(self, *, actor: User, offer_id: str, payload) -> ClubSponsor:
        metrics = self.evaluate_club_metrics(payload.club_id)
        offer = self._require_offer(offer_id)
        unmet = self._evaluate_offer(offer, metrics)["unmet_rules"]
        if unmet:
            raise ClubSponsorOfferError("Club does not meet sponsor eligibility requirements.")

        start_at = payload.start_at or datetime.now(UTC)
        duration_months = payload.duration_months or offer.default_duration_months
        value_minor = payload.contract_value_minor or offer.base_value_minor
        sponsor = ClubSponsor(
            club_id=payload.club_id,
            sponsor_offer_id=offer.id,
            contract_id=None,
            sponsor_name=offer.sponsor_name,
            category=offer.category,
            status="active",
            contract_value_minor=value_minor,
            currency=payload.currency or offer.currency,
            duration_months=duration_months,
            start_at=start_at,
            end_at=start_at + timedelta(days=30 * duration_months),
            approved_surfaces_json=list(offer.approved_surfaces_json or []),
            creative_url=offer.creative_url,
            analytics_json={"assigned_by_user_id": actor.id},
            metadata_json={"offer_code": offer.code, "offer_name": offer.offer_name},
        )
        self.session.add(sponsor)
        self.session.flush()
        self.analytics.track_event(
            self.session,
            name="club_sponsor.assigned",
            user_id=actor.id,
            metadata={"club_id": sponsor.club_id, "club_sponsor_id": sponsor.id, "offer_id": offer.id},
        )
        return sponsor

    def sponsorship_analytics(self) -> dict[str, Any]:
        offers = self.list_offers(active_only=False)
        sponsors = list(self.session.scalars(select(ClubSponsor)).all())
        render_events = list(
            self.session.scalars(select(AnalyticsEvent).where(AnalyticsEvent.name == "club_sponsor.rendered")).all()
        )
        placements_by_surface: dict[str, int] = {}
        for event in render_events:
            surface = str((event.metadata_json or {}).get("surface") or "unknown")
            placements_by_surface[surface] = placements_by_surface.get(surface, 0) + 1
        return {
            "offer_count": len(offers),
            "active_offer_count": sum(1 for offer in offers if offer.is_active and offer.category_enabled),
            "assignment_count": len(sponsors),
            "active_sponsor_count": sum(1 for sponsor in sponsors if sponsor.status == "active"),
            "render_event_count": len(render_events),
            "placements_by_surface": placements_by_surface,
        }

    def _eligibility_payload(self, offer: SponsorOffer, metrics: ClubSponsorMetricsSnapshot) -> dict[str, Any]:
        evaluation = self._evaluate_offer(offer, metrics)
        return {
            "offer": offer,
            "club_metrics": {
                "club_id": metrics.club_id,
                "fan_count": metrics.fan_count,
                "reputation_score": metrics.reputation_score,
                "prestige_tier": metrics.prestige_tier,
                "club_valuation": metrics.club_valuation,
                "media_popularity": metrics.media_popularity,
                "competition_count": metrics.competition_count,
                "rivalry_visibility": metrics.rivalry_visibility,
            },
            "eligible": not evaluation["unmet_rules"],
            "unmet_rules": evaluation["unmet_rules"],
        }

    def _evaluate_offer(self, offer: SponsorOffer, metrics: ClubSponsorMetricsSnapshot) -> dict[str, list[str]]:
        unmet: list[str] = []
        rule = self.session.scalar(
            select(SponsorOfferRule)
            .where(SponsorOfferRule.sponsor_offer_id == offer.id, SponsorOfferRule.is_active.is_(True))
            .order_by(SponsorOfferRule.updated_at.desc())
        )
        if not offer.is_active:
            unmet.append("offer_inactive")
        if not offer.category_enabled:
            unmet.append("category_disabled")
        if rule is None:
            return {"unmet_rules": unmet}

        if metrics.fan_count < rule.min_fan_count:
            unmet.append("fan_count")
        if metrics.reputation_score < rule.min_reputation_score:
            unmet.append("reputation_score")
        if metrics.club_valuation < float(rule.min_club_valuation):
            unmet.append("club_valuation")
        if metrics.media_popularity < rule.min_media_popularity:
            unmet.append("media_popularity")
        if metrics.competition_count < rule.min_competition_count:
            unmet.append("competition_count")
        if metrics.rivalry_visibility < rule.min_rivalry_visibility:
            unmet.append("rivalry_visibility")
        if rule.required_prestige_tier and metrics.prestige_tier.lower() != rule.required_prestige_tier.lower():
            unmet.append("prestige_tier")
        if rule.competition_allowlist_json:
            allowed = set(rule.competition_allowlist_json or [])
            if not allowed.intersection(metrics.competition_ids):
                unmet.append("competition_allowlist")
        return {"unmet_rules": unmet}

    def _require_offer(self, offer_id: str) -> SponsorOffer:
        offer = self.session.get(SponsorOffer, offer_id)
        if offer is None:
            raise ClubSponsorOfferError("Sponsor offer was not found.")
        return offer


__all__ = ["ClubSponsorMetricsSnapshot", "ClubSponsorOfferError", "ClubSponsorOfferService"]
